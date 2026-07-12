"""Tests for the packaged FBMCQ language guide resource."""

import hashlib
import os
import pkgutil
import re

import pytest

import pyfcstm.llm as llm
import pyfcstm.llm.fbmcq as fbmcq_guide_api
import pyfcstm.llm.fcstm as fcstm_guide_api
from pyfcstm.llm import _resources as guide_resources
from pyfcstm.bmc.binding import bind_bmc_query, bind_bmc_query_structure
from pyfcstm.bmc.errors import (
    BmcQueryParseError,
    InvalidBmcQuery,
    UnsupportedBmcQuery,
)
from pyfcstm.bmc.parse import parse_bmc_query
from pyfcstm.bmc.pipeline import compile_bmc_query
from pyfcstm.bmc.witness import (
    decode_bmc_witness,
    replay_bmc_witness,
    solve_bmc_property,
)
from pyfcstm.model import load_state_machine_from_text


_FBMCQ_BLOCK_RE = re.compile(r"```fbmcq\n(.*?)\n```", re.DOTALL)
_EXECUTABLE_BLOCK_RE = re.compile(r"```fbmcq-executable\n(.*?)\n```", re.DOTALL)
_INVALID_PARSE_BLOCK_RE = re.compile(r"```fbmcq-invalid-parse\n(.*?)\n```", re.DOTALL)
_INVALID_STRUCTURE_BLOCK_RE = re.compile(
    r"```fbmcq-invalid-structure\n(.*?)\n```", re.DOTALL
)
_INVALID_MODEL_BLOCK_RE = re.compile(r"```fbmcq-invalid-model\n(.*?)\n```", re.DOTALL)
_INVALID_UNSUPPORTED_BLOCK_RE = re.compile(
    r"```fbmcq-invalid-unsupported\n(.*?)\n```", re.DOTALL
)


def _resource_loader(resources):
    """Return a pkgutil replacement backed by a resource mapping."""
    return lambda package, resource: resources.get(resource)


@pytest.fixture()
def fbmcq_model():
    """Return the model used by every executable Guide example."""
    return load_state_machine_from_text(
        """
        def int x = 0;

        state Root {
            event Go;

            state Idle {
                during abstract Tick;
            }

            state Done;

            [*] -> Idle;
            Idle -> Done :: Go;
        }
        """
    )


@pytest.mark.unittest
def test_fbmcq_language_guide_prompt_api_returns_packaged_text():
    """The text API returns the LF-normalized FBMCQ language guide."""
    guide = llm.get_fbmcq_language_guide_prompt_for_llm()

    assert guide.startswith("# FBMCQ Language Guide for LLMs")
    assert "\r" not in guide
    assert "Do not invent model facts" in guide
    assert "## Good And Bad Query Patterns" in guide
    assert "first non-whitespace character" in guide
    assert "last non-whitespace\ncharacter" in guide


@pytest.mark.unittest
def test_fbmcq_language_guide_is_available_as_package_data():
    """The Markdown resource and checksum are installed package data."""
    data = pkgutil.get_data(llm.__name__, "fbmcq_language_guide.md")
    checksum = pkgutil.get_data(llm.__name__, "fbmcq_language_guide.md.sha256")
    guide = llm.get_fbmcq_language_guide_prompt_for_llm()

    assert data is not None
    assert checksum is not None
    assert data.decode("utf-8").splitlines() == guide.splitlines()


@pytest.mark.unittest
def test_fbmcq_language_guide_normalizes_crlf_resource(monkeypatch):
    """FBMCQ guide hashing normalizes CRLF input before verification."""
    raw_text = "# FBMCQ\r\n\r\n## Section\r\nUse `reach`.\r\n"
    expected_text = "# FBMCQ\n\n## Section\nUse `reach`.\n"
    expected_digest = hashlib.sha256(expected_text.encode("utf-8")).hexdigest()
    monkeypatch.setattr(
        guide_resources.pkgutil,
        "get_data",
        _resource_loader(
            {
                "fbmcq_language_guide.md": raw_text.encode("utf-8"),
                "fbmcq_language_guide.md.sha256": expected_digest.encode("utf-8"),
            }
        ),
    )

    guide = llm.get_fbmcq_language_guide_prompt_for_llm()
    metadata = llm.get_fbmcq_language_guide_prompt_metadata_for_llm()

    assert guide == expected_text
    assert metadata["resource_name"] == "fbmcq_language_guide.md"
    assert metadata["checksum_resource_name"] == "fbmcq_language_guide.md.sha256"
    assert metadata["sha256"] == expected_digest
    assert metadata["expected_sha256"] == expected_digest


@pytest.mark.unittest
def test_fbmcq_language_guide_integrity_failure_is_actionable(monkeypatch):
    """A mismatched FBMCQ checksum names the resource and recovery paths."""
    monkeypatch.setattr(
        guide_resources.pkgutil,
        "get_data",
        _resource_loader(
            {
                "fbmcq_language_guide.md": b"# FBMCQ\n",
                "fbmcq_language_guide.md.sha256": (64 * "0").encode("utf-8"),
            }
        ),
    )

    with pytest.raises(llm.GrammarGuidePromptIntegrityError) as err_info:
        llm.get_fbmcq_language_guide_prompt_for_llm()

    message = str(err_info.value)
    assert "FBMCQ" in message
    assert "fbmcq_language_guide.md" in message
    assert "make sha256" in message
    assert "reinstall pyfcstm" in message


@pytest.mark.unittest
def test_fbmcq_language_guide_can_warn_on_integrity_failure(monkeypatch):
    """The warning fallback returns text but keeps the integrity failure visible."""
    monkeypatch.setattr(
        guide_resources.pkgutil,
        "get_data",
        _resource_loader(
            {
                "fbmcq_language_guide.md": b"# FBMCQ\n",
                "fbmcq_language_guide.md.sha256": (64 * "0").encode("utf-8"),
            }
        ),
    )

    with pytest.warns(RuntimeWarning) as warnings:
        guide = llm.get_fbmcq_language_guide_prompt_for_llm(
            raise_on_integrity_error=False
        )

    assert guide == "# FBMCQ\n"
    assert "FBMCQ" in str(warnings[0].message)
    assert "integrity verification failed" in str(warnings[0].message)


@pytest.mark.unittest
def test_fbmcq_language_guide_path_and_metadata_are_deterministic():
    """Path and metadata APIs mirror the existing FCSTM resource contracts."""
    guide = llm.get_fbmcq_language_guide_prompt_for_llm()
    guide_path = llm.get_fbmcq_language_guide_prompt_path_for_llm()
    metadata = llm.get_fbmcq_language_guide_prompt_metadata_for_llm()

    assert os.path.basename(guide_path) == "fbmcq_language_guide.md"
    assert os.path.isfile(guide_path)
    assert metadata["resource_name"] == "fbmcq_language_guide.md"
    assert metadata["byte_size"] == len(guide.encode("utf-8"))
    assert metadata["line_count"] == len(guide.splitlines())
    assert metadata["chapter_count"] == sum(
        1 for line in guide.splitlines() if line.startswith("## ")
    )
    assert re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"])


@pytest.mark.unittest
def test_fcstm_and_fbmcq_guides_keep_resource_identity_separate():
    """The two public guide APIs cannot accidentally verify each other's hash."""
    fcstm = llm.get_grammar_guide_prompt_metadata_for_llm()
    fbmcq = llm.get_fbmcq_language_guide_prompt_metadata_for_llm()

    assert fcstm["resource_name"] == "fcstm_grammar_guide.md"
    assert fbmcq["resource_name"] == "fbmcq_language_guide.md"
    assert fcstm["checksum_resource_name"] != fbmcq["checksum_resource_name"]
    assert fcstm["sha256"] != fbmcq["sha256"]


@pytest.mark.unittest
def test_llm_package_reexports_two_dedicated_guide_modules():
    """The clean package entry exposes both dedicated Guide module APIs."""
    assert (
        llm.get_grammar_guide_prompt_for_llm
        is fcstm_guide_api.get_grammar_guide_prompt_for_llm
    )
    assert (
        llm.get_fbmcq_language_guide_prompt_for_llm
        is fbmcq_guide_api.get_fbmcq_language_guide_prompt_for_llm
    )
    assert not hasattr(llm, "get_guide_prompt")


@pytest.mark.unittest
def test_fbmcq_guide_sections_cover_authoring_rules_not_bmc_internals():
    """The Guide teaches query authoring without becoming a BMC implementation manual."""
    guide = llm.get_fbmcq_language_guide_prompt_for_llm()
    expected_sections = {
        "## Purpose And Scope",
        "## Full Capability Map",
        "## Required Model Facts",
        "## Output Contract",
        "## Top-Level Query Structure",
        "## Initialization",
        "## Environment Assumptions",
        "## Expressions",
        "## Model Observation Atoms",
        "## Property Selection",
        "## Frames Steps And Bounds",
        "## Definedness",
        "## Response And Incomplete Windows",
        "## Avoiding Vacuous Queries",
        "## Complete Examples",
        "## Invalid Examples",
        "## Pre-Output Checklist",
        "## Good And Bad Query Patterns",
    }
    actual_sections = {line for line in guide.splitlines() if line.startswith("## ")}
    lowered = guide.lower()

    assert actual_sections == expected_sections
    assert 'var("...")' in guide
    assert "bare variable" in lowered
    assert "cycle" in guide
    assert "active()" in guide
    assert "terminated()" in guide
    assert "event()" in guide
    assert "case()" in guide
    assert "called()" in guide
    assert "call_count()" in guide
    assert "response incomplete" in lowered
    for forbidden_topic in {
        "bounded model checking",
        "transition relation",
        "solver algorithm",
        "smt-lib",
        "unsat-core",
        "z3",
        "cnf encoding",
    }:
        assert forbidden_topic not in lowered


@pytest.mark.unittest
def test_fbmcq_guide_describes_full_authoring_surface_when_facts_are_known():
    """The Guide presents available FBMCQ features without inviting fact invention."""
    guide = llm.get_fbmcq_language_guide_prompt_for_llm()

    assert "Do not invent model facts" in guide
    assert "## Full Capability Map" in guide
    assert "use every applicable documented\nfeature" in guide
    for init_form in {
        "omitted `init`",
        "`init cold`",
        "`init state(\"Root.Leaf\")`",
        "`init terminated`",
        "`havoc *`",
        "`where condition`",
    }:
        assert init_form in guide
    for assumption_form in {
        "`assume always: condition;`",
        "`assume at k: condition;`",
        "`assume event(\"Path\", selector) == true;`",
        "`!= false`",
        "`at_most_one`",
        "`any`",
    }:
        assert assumption_form in guide
    for numeric_feature in {
        "`0x2A`",
        "`pi`, `E`, and `tau`",
        "`**`",
        "`<< >>`",
        "`(condition) ? number : number`",
    }:
        assert numeric_feature in guide
    for function_name in {
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "sinh",
        "cosh",
        "tanh",
        "asinh",
        "acosh",
        "atanh",
        "sqrt",
        "cbrt",
        "exp",
        "log",
        "log10",
        "log2",
        "log1p",
        "abs",
        "ceil",
        "floor",
        "round",
        "trunc",
        "sign",
    }:
        assert function_name in guide
    assert "current executable expression profile supports" in guide
    assert "explicit\nunsupported diagnostic" in guide
    for boolean_operator in {
        "`!` / `not`",
        "`&&` / `and`",
        "`xor`",
        "`||` /\n`or`",
        "`=>` / `implies`",
        "`iff`",
    }:
        assert boolean_operator in guide
    for atom_or_filter in {
        "`active(\"State.Path\"[, current])`",
        "`event(\"Event.Path\", current)`",
        "`case(\"Public.Label\"[, current])`",
        "`called(filter?)` / `call_count(filter?)`",
        "`active_leaf=\"Root.A.Leaf\"`",
        "`named_ref=\"Root.A.Ref\"` or `named_ref=null`",
        "`step=-2..+0`",
    }:
        assert atom_or_filter in guide
    for property_shape in {
        "`reach`, `forbid`, `invariant`, `must_reach`, `exists_always`",
        "Exactly one naked `case(\"Public.Label\")` atom",
        "`trigger condition -> within positive_integer condition`",
    }:
        assert property_shape in guide
    assert "Ordinary `.fbmcq` files accept `//` line comments" in guide
    assert "raw LLM artifact accepts none of\nthem" in guide
    assert "including a response trigger" in guide
    assert 'source-valid but binding-invalid property expression' in guide
    assert '`called(*)` and `call_count(-1..+0)`' in guide


@pytest.mark.unittest
def test_fbmcq_guide_distinguishes_public_parse_and_binding_boundaries():
    """The Guide preserves source features while naming their execution boundary."""
    fixed_event = parse_bmc_query('check reach <= 1: event("Root.Go", 0);')
    with pytest.raises(InvalidBmcQuery, match="event_not_allowed"):
        bind_bmc_query_structure(fixed_event)

    fixed_response_event = parse_bmc_query(
        'check response <= 1: trigger event("Root.Go", 0) '
        '-> within 1 active("Root.Idle");'
    )
    with pytest.raises(InvalidBmcQuery, match="event_not_allowed"):
        bind_bmc_query_structure(fixed_response_event)

    current_response_event = parse_bmc_query(
        'check response <= 1: trigger event("Root.Go", current) '
        '-> within 1 active("Root.Idle");'
    )
    bind_bmc_query_structure(current_response_event)

    for source in (
        "check reach <= 1: called(*);",
        "check reach <= 1: call_count(-1..+0) >= 0;",
    ):
        bind_bmc_query_structure(parse_bmc_query(source))


@pytest.mark.unittest
def test_fbmcq_guide_capability_boundaries_bind_and_lower(fbmcq_model):
    """Representative full-surface forms keep their documented execution status."""
    executable = parse_bmc_query(
        'init cold havoc { x } where x == 7;\n'
        'check reach <= 1: x == 7;'
    )
    bind_bmc_query(executable, model=fbmcq_model)
    assert solve_bmc_property(compile_bmc_query(fbmcq_model, executable)).status == "sat"

    for source, code in (
        (
            "init cold where cycle == 0; check reach <= 1: true;",
            "cycle_not_allowed",
        ),
        (
            "init cold where called(); check reach <= 1: true;",
            "called_not_allowed",
        ),
        (
            'check response <= 1: trigger event("Root.Go", current) '
            '-> within 1 event("Root.Go", current);',
            "event_not_allowed",
        ),
    ):
        with pytest.raises(InvalidBmcQuery, match=code):
            bind_bmc_query(parse_bmc_query(source), model=fbmcq_model)

    for source in (
        "check reach <= 1: sin(x) > 0;",
        "check reach <= 1: (x << 1) >= 0;",
    ):
        query = parse_bmc_query(source)
        bind_bmc_query(query, model=fbmcq_model)
        with pytest.raises(UnsupportedBmcQuery):
            compile_bmc_query(fbmcq_model, query)


@pytest.mark.unittest
def test_fbmcq_guide_positive_blocks_parse_and_round_trip():
    """Every complete positive FBMCQ block parses and canonicalizes stably."""
    guide = llm.get_fbmcq_language_guide_prompt_for_llm()
    examples = _FBMCQ_BLOCK_RE.findall(guide) + _EXECUTABLE_BLOCK_RE.findall(guide)

    assert len(examples) >= 7
    for example in examples:
        parsed = parse_bmc_query(example)
        assert parse_bmc_query(str(parsed)).to_canonical() == parsed.to_canonical()


@pytest.mark.unittest
def test_fbmcq_guide_executable_examples_bind_compile_solve_and_replay(fbmcq_model):
    """Executable Guide examples use the real model, compiler, solver, and replay path."""
    guide = llm.get_fbmcq_language_guide_prompt_for_llm()
    examples = _EXECUTABLE_BLOCK_RE.findall(guide)

    assert len(examples) >= 8
    assert any(
        "trigger active(\"Root.Idle\") && cycle == 0"
        in example
        and 'called("Root.Idle.Tick", step=+0, role="leaf_during")' in example
        for example in examples
    )
    for example in examples:
        query = parse_bmc_query(example)
        bind_bmc_query_structure(query)
        bind_bmc_query(query, model=fbmcq_model)
        formula = compile_bmc_query(fbmcq_model, query)
        result = solve_bmc_property(formula)

        assert result.status in {"sat", "unsat"}
        if result.model is not None:
            trace = decode_bmc_witness(formula, result.model)
            assert replay_bmc_witness(fbmcq_model, trace).ok
        if result.incomplete_model is not None:
            trace = decode_bmc_witness(formula, result.incomplete_model)
            assert replay_bmc_witness(fbmcq_model, trace).ok


@pytest.mark.unittest
def test_fbmcq_guide_invalid_blocks_fail_at_their_declared_stage(fbmcq_model):
    """Invalid example fences distinguish parse, structure, model, and lowering failures."""
    guide = llm.get_fbmcq_language_guide_prompt_for_llm()
    parse_examples = _INVALID_PARSE_BLOCK_RE.findall(guide)
    structure_examples = _INVALID_STRUCTURE_BLOCK_RE.findall(guide)
    model_examples = _INVALID_MODEL_BLOCK_RE.findall(guide)
    unsupported_examples = _INVALID_UNSUPPORTED_BLOCK_RE.findall(guide)

    assert parse_examples
    assert structure_examples
    assert model_examples
    assert unsupported_examples
    for example in parse_examples:
        with pytest.raises(BmcQueryParseError):
            parse_bmc_query(example)
    for example in structure_examples:
        with pytest.raises(InvalidBmcQuery):
            bind_bmc_query_structure(parse_bmc_query(example))
    for example in model_examples:
        query = parse_bmc_query(example)
        bind_bmc_query_structure(query)
        with pytest.raises(InvalidBmcQuery):
            bind_bmc_query(query, model=fbmcq_model)
    for example in unsupported_examples:
        query = parse_bmc_query(example)
        bind_bmc_query(query, model=fbmcq_model)
        with pytest.raises(UnsupportedBmcQuery):
            compile_bmc_query(fbmcq_model, query)
