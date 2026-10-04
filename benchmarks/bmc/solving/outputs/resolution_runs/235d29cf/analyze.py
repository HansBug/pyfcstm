"""Check the independent semantic records and rebuild the CLI comparison."""

import hashlib
import json
from pathlib import Path
import statistics


def analyze(root):
    formal = json.loads((root / "manifest.json").read_text())
    semantic = {}
    for arm in ("baseline", "candidate"):
        directory = root / ("semantics-" + arm)
        manifest = json.loads((directory / "manifest.json").read_text())
        assert manifest["commit"] == formal["arms"][arm]["commit"]
        assert manifest["dirty"] is False
        rows = [
            json.loads(line)
            for line in (directory / "raw.jsonl").read_text().splitlines()
        ]
        assert len(rows) == len(manifest["specs"]) == 51
        semantic[arm] = {(row["case"], row["query"]): row for row in rows}
        assert len(semantic[arm]) == 51
        for spec, row in zip(manifest["specs"], rows):
            assert all(row[key] == value for key, value in spec.items())
            assert row["status"] != "sat" or row["replay_ok"] is True
            assert (
                Path(row["package"]).parent
                == Path(formal["arms"][arm]["path"]) / "pyfcstm"
            )
    assert semantic["baseline"].keys() == semantic["candidate"].keys()
    witness_changes = []
    for key, baseline in sorted(semantic["baseline"].items()):
        candidate = semantic["candidate"][key]
        for field in (
            "input_sha256",
            "status",
            "outcome",
            "property_satisfied",
            "replay_ok",
            "partition_count",
            "partition_assignments",
        ):
            assert baseline[field] == candidate[field], (key, field)
        assert baseline["fingerprints"].keys() == candidate["fingerprints"].keys()
        for field, value in baseline["fingerprints"].items():
            if field != "witness":
                assert value == candidate["fingerprints"][field], (key, field)
        if baseline["fingerprints"]["witness"] != candidate["fingerprints"]["witness"]:
            witness_changes.append({"case": key[0], "query": key[1]})
    directory = root / "cli"
    manifest = json.loads((directory / "manifest.json").read_text())
    rows = [
        json.loads(line) for line in (directory / "raw.jsonl").read_text().splitlines()
    ]
    assert len(rows) == len(manifest["samples"]) == 72
    for spec, row in zip(manifest["samples"], rows):
        assert all(row[key] == value for key, value in spec.items())
        reference = semantic[row["arm"]][row["case"], row["query"]]
        for field in ("status", "outcome", "property_satisfied"):
            assert row[field] == reference[field]
        assert (
            Path(row["package"]).parent
            == Path(manifest["arms"][row["arm"]]["path"]) / "pyfcstm"
        )
    comparisons = []
    for case, query in sorted({(row["case"], row["query"]) for row in rows}):
        item = {"case": case, "query": query}
        for metric in ("call_ms", "process_ms"):
            medians = {}
            for arm in ("baseline", "candidate"):
                values = [
                    row[metric]
                    for row in rows
                    if row["case"] == case
                    and row["query"] == query
                    and row["arm"] == arm
                    and not row["warmup"]
                ]
                assert len(values) == 5
                medians[arm] = statistics.median(values)
            medians["change_percent"] = (
                medians["candidate"] / medians["baseline"] - 1
            ) * 100
            item[metric] = medians
        comparisons.append(item)
    assert comparisons == json.loads((directory / "summary.json").read_text())
    result = {
        "formula_and_partition_matches": len(semantic["baseline"]),
        "semantic_sat_replays": sum(
            row["status"] == "sat" for arm in semantic.values() for row in arm.values()
        ),
        "legal_witness_changes": witness_changes,
        "cli_comparisons": comparisons,
        "input_hashes": {
            str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(root.glob("*/raw.jsonl"))
        },
    }
    (root / "assessment.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    return result


if __name__ == "__main__":
    print(json.dumps(analyze(Path(__file__).resolve().parent), indent=2))
