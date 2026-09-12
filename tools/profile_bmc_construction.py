#!/usr/bin/env python3
"""Diagnose BMC construction using isolated, process-local cache experiments.

No production file is changed. Every arm runs the public file API and retains
partition validation, solving and ordinary replay. These are experimental
prototypes, not supported execution modes or evidence of production readiness.
"""

import argparse
import contextlib
import cProfile
import hashlib
import json
import os
from pathlib import Path
import pstats
import platform
import re
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch


ARMS = ("baseline", "canonical_cache", "accepted_cache", "combined_cache")


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def _install_caches(stack, arm):
    from pyfcstm.bmc import macro

    original_key = macro._canonical_key
    original_resolve = macro._resolve_accepted_atoms
    keys, registries = {}, {}
    counts = {"key_hits": 0, "resolve_hits": 0}

    def canonical_key(item):
        if not isinstance(item, macro.BoolTemplate):
            return original_key(item)
        ident = id(item)
        if ident not in keys:
            # Retaining the object prevents id reuse; immutable templates only.
            keys[ident] = (item, original_key(item))
        else:
            counts["key_hits"] += 1
        return keys[ident][1]

    def resolve(condition, registry, active=None):
        registry_id = id(registry)
        if registry_id not in registries:
            registries[registry_id] = (registry, {})
        cache = registries[registry_id][1]
        ident = id(condition)
        if ident not in cache:
            # Only completed resolutions enter the cache. Original recursion
            # still validates missing references and cycles; registries are
            # fixed for each source partition produced by the real compiler.
            cache[ident] = (condition, original_resolve(condition, registry, active))
        else:
            counts["resolve_hits"] += 1
        return cache[ident][1]

    if arm in ("canonical_cache", "combined_cache"):
        stack.enter_context(patch.object(macro, "_canonical_key", canonical_key))
    if arm in ("accepted_cache", "combined_cache"):
        stack.enter_context(patch.object(macro, "_resolve_accepted_atoms", resolve))
    return keys, registries, counts


def _sample(spec):
    sys.path.insert(0, os.getcwd())
    import pyfcstm
    import z3
    from pyfcstm.bmc import macro, pipeline, relation
    from pyfcstm.entry import bmc as entry

    root = Path("benchmarks/bmc/solving/cases") / spec["case"]
    source = (root / (spec["query"] + ".fbmcq")).read_text()
    if spec.get("bound") is not None:
        source, count = re.subn(
            r"(check\s+\w+\s*<=\s*)\d+",
            lambda match: match[1] + str(spec["bound"]),
            source,
        )
        if count != 1:
            raise ValueError("Bound experiment requires one bounded property.")
    phases, nesting, formulas, partitions = {}, [], [], []

    def observe(label, function, retain=None):
        def measured(*args, **kwargs):
            frame = [time.perf_counter(), 0.0]
            nesting.append(frame)
            try:
                result = function(*args, **kwargs)
                if retain is not None:
                    retain.append(result)
                return result
            finally:
                elapsed = time.perf_counter() - frame[0]
                nesting.pop()
                phases[label] = phases.get(label, 0.0) + elapsed - frame[1]
                if nesting:
                    nesting[-1][1] += elapsed

        return measured

    targets = [
        (entry, "_load_model", "loading", None),
        (entry, "_read_query_file", "loading", None),
        (entry, "_compile_query", "compile_other", formulas),
        (pipeline, "prepare_bmc_query", "prepare", None),
        (pipeline, "build_bmc_core_formula", "core_other", None),
        (pipeline, "compile_bmc_property", "property", None),
        (relation, "_formals_by_step", "macro_expansion", None),
        (macro, "verify_source_partition", "partition_validation", partitions),
        (relation, "_build_step_relation", "relation_steps", None),
        (entry, "_solve_bmc_property", "solve_including_verification", None),
        (entry, "_decode_bmc_result_trace", "external_decode", None),
        (entry, "_replay_bmc_witness", "external_replay", None),
    ]
    profiler = cProfile.Profile() if spec.get("profile") else None
    # The temporary input and experiment patches have explicit ownership. All
    # imports, input preparation and fingerprinting are outside call timing.
    with tempfile.TemporaryDirectory(prefix="bmc-construction-") as directory:
        query = root / (spec["query"] + ".fbmcq")
        if spec.get("bound") is not None:
            query = Path(directory) / "bound.fbmcq"
            query.write_text(source)
        with contextlib.ExitStack() as stack:
            keys, registries, counts = _install_caches(stack, spec["arm"])
            for module, name, label, retain in targets:
                stack.enter_context(
                    patch.object(
                        module, name, observe(label, getattr(module, name), retain)
                    )
                )
            if profiler:
                profiler.enable()
            started = time.perf_counter()
            body, code = entry.build_bmc_output(
                str(root / "model.fcstm"),
                str(query),
                json_output=True,
                cone_slicing=spec.get("cone_slicing", False),
            )
            elapsed = time.perf_counter() - started
            if profiler:
                profiler.disable()
            counts.update(
                key_entries=len(keys),
                resolve_entries=sum(len(item[1]) for item in registries.values()),
                registries=len(registries),
            )
            try:
                import resource
            except ImportError:
                # ImportError: Windows does not provide the resource module.
                rss = None
            else:
                rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
                rss *= 1 if sys.platform == "darwin" else 1024
    payload = json.loads(body)
    result = payload["result"]
    assert payload["exit_code"] == code
    assert payload["replay"] is None or payload["replay"]["ok"]
    if spec.get("bound") is None:
        expected = next(
            q["expected"]
            for q in json.loads((root / "case.json").read_text())["queries"]
            if Path(q["file"]).stem == spec["query"]
        )
        assert all(result[key] == value for key, value in expected.items())
    assert len(formulas) == 1
    formula = formulas[0]
    witness = payload["witness"]
    if witness is not None:
        # These two documented solver timing fields are nondeterministic;
        # user variables and all other witness content remain in the digest.
        witness["solver"].pop("primary_elapsed_ms", None)
        witness["solver"].pop("incomplete_elapsed_ms", None)
    phases["report_other"] = elapsed - sum(phases.values())
    assert all(value >= -0.00001 for value in phases.values())
    record = dict(
        spec,
        call_ms=elapsed * 1000,
        phases_ms={key: value * 1000 for key, value in phases.items()},
        peak_rss_bytes=rss,
        cache=counts,
        package=str(Path(pyfcstm.__file__).resolve()),
        python=sys.version,
        z3=z3.get_version_string(),
        input_sha256=_digest([(root / "model.fcstm").read_text(), source]),
        status=result["status"],
        outcome=result["outcome"],
        property_satisfied=result["property_satisfied"],
        replay_ok=None if payload["replay"] is None else payload["replay"]["ok"],
        fingerprints={
            "core": _digest(formula.core.core.sexpr()),
            "objective": _digest(formula.objective_formula.sexpr()),
            "macro_contracts": _digest(
                [
                    [formal.to_canonical() for formal in step.formals]
                    for step in formula.core.steps
                ]
            ),
            "partition_checks": _digest([item.to_canonical() for item in partitions]),
            "witness": _digest(witness),
        },
        partition_count=len(partitions),
        partition_assignments=sum(item.assignment_count for item in partitions),
    )
    if profiler:
        stats = pstats.Stats(profiler).stats
        selected = set(sorted(stats, key=lambda key: stats[key][3], reverse=True)[:60])
        selected.update(sorted(stats, key=lambda key: stats[key][2], reverse=True)[:30])
        record["profile_functions"] = [
            dict(
                file=os.path.relpath(filename),
                line=line,
                function=name,
                primitive_calls=stats[(filename, line, name)][0],
                calls=stats[(filename, line, name)][1],
                self_ms=stats[(filename, line, name)][2] * 1000,
                inclusive_ms=stats[(filename, line, name)][3] * 1000,
            )
            for filename, line, name in sorted(selected)
        ]
    return record


def _check():
    from pyfcstm.bmc import macro
    from pyfcstm.bmc.errors import BmcBuildError

    original = macro._resolve_accepted_atoms
    for arm in ARMS:
        with contextlib.ExitStack() as stack:
            _install_caches(stack, arm)
            atom = macro.BoolTemplate.atom("event:x")
            registry = {"a": atom, "b": macro.BoolTemplate.atom("accepted:a")}
            value = macro.BoolTemplate.atom("accepted:b")
            assert macro._resolve_accepted_atoms(value, registry) == atom
            assert macro._resolve_accepted_atoms(value, registry) == atom
            assert macro._canonical_key(value) == json.dumps(
                value.to_canonical(), sort_keys=True, separators=(",", ":")
            )
            for invalid in ({}, {"b": value}):
                try:
                    macro._resolve_accepted_atoms(value, invalid)
                except BmcBuildError:
                    # BmcBuildError: unknown accepted label or an accepted cycle.
                    pass
                else:
                    raise AssertionError(
                        "Experiment suppressed an invalid accepted reference."
                    )
        assert macro._resolve_accepted_atoms is original
    print("Experiment hooks restore state and preserve reference/cycle rejection.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkout", type=Path, default=Path.cwd())
    parser.add_argument("--specs", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--child")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.child:
        print(json.dumps(_sample(json.loads(args.child))))
        return
    if args.check:
        sys.path.insert(0, str(args.checkout.resolve()))
        _check()
        return
    if args.specs is None or args.output is None or args.output.exists():
        parser.error("Supply --specs and a new --output directory.")
    checkout = args.checkout.resolve()
    if subprocess.check_output(
        ["git", "status", "--porcelain"], cwd=str(checkout), text=True
    ):
        parser.error("The measured checkout must be clean, including untracked files.")
    specs = json.loads(args.specs.read_text())
    for spec in specs:
        if spec["arm"] not in ARMS:
            parser.error("Unknown experimental arm.")
    args.output.mkdir(parents=True)
    manifest = {
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(checkout), text=True
        ).strip(),
        "dirty": False,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "specs": specs,
        "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "timing_contract": "Fresh processes; pre-imported dependencies; public file API including serialization. Low-frequency phase observers are shared by all arms. Input preparation and fingerprints excluded. cProfile runs separate from ordinary wall measurements; inclusive function times overlap. Caches exist only for one call, retain object identities, and are experimental.",
    }
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    references = {}
    with (args.output / "raw.jsonl").open("x") as stream:
        for spec in specs:
            run = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--child",
                    json.dumps(spec),
                ],
                cwd=str(checkout),
                text=True,
                capture_output=True,
                check=True,
                timeout=300,
            )
            record = json.loads(run.stdout)
            assert Path(record["package"]).parent == checkout / "pyfcstm"
            key = (
                spec["case"],
                spec["query"],
                spec.get("bound"),
                spec.get("cone_slicing", False),
            )
            contract = {
                name: record[name]
                for name in (
                    "input_sha256",
                    "fingerprints",
                    "status",
                    "outcome",
                    "property_satisfied",
                    "replay_ok",
                    "partition_count",
                    "partition_assignments",
                )
            }
            if key in references:
                assert contract == references[key], (
                    "Arm changed measured semantics: %r" % (spec,)
                )
            else:
                assert spec["arm"] == "baseline", "Run baseline first for each input."
                references[key] = contract
            stream.write(json.dumps(record, sort_keys=True) + "\n")
            stream.flush()
            print(
                "Measured %s/%s %s bound=%s profile=%s"
                % (
                    spec["case"],
                    spec["query"],
                    spec["arm"],
                    spec.get("bound"),
                    bool(spec.get("profile")),
                ),
                flush=True,
            )


if __name__ == "__main__":
    main()
