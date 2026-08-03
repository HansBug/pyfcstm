"""The published schema and the Python constructor must agree on one payload set.

The upstream contract freezes this as a two-way requirement, so a payload that
one side accepts and the other rejects is a defect regardless of which side is
"right".  The corpus below deliberately mixes two kinds of dimension:

* scalar dimensions - modes, statuses, classifications, scopes, reductions;
* structural dimensions - how many core members there are, which stages they
  come from, and whether their provenance is well formed.

A cross product over scalar enums alone cannot reach a relational invariant: it
holds the member list fixed at one well-formed entry, so every rule about how
members relate to their scope or to each other stays untested no matter how
many thousands of combinations it produces.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import pytest

from pyfcstm.bmc.explanation import (
    _FACT_KINDS,
    CLASSIFICATION_SCOPES,
    STAGE_FALLBACK_SCOPES,
    BmcConflictCore,
    BmcConstraintRef,
    BmcCoreItem,
    BmcConflictNarrative,
    BmcInfeasibilityExplanation,
    BmcReasoningStep,
)
from pyfcstm.bmc.provenance import (
    MAX_METADATA_DEPTH as _MAX_METADATA_DEPTH,
)
from pyfcstm.bmc.provenance import (
    MAX_METADATA_INT_DIGITS as _MAX_METADATA_INT_DIGITS,
)
from pyfcstm.bmc.provenance import BmcSourceRef

pytestmark = pytest.mark.unittest

_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "source"
    / "reference"
    / "bmc_results"
    / "bmc_cli.schema.json"
)

#: One stage that every scope's target formula legitimately contains.
_SCOPE_MEMBER_STAGE = {
    "kernel": "kernel",
    "initialization_component": "initialization",
    "initialization_domain": "initialization",
    "initialization_prefix": "initialization",
    "assumptions_component": "assumptions",
    "assumptions_domain": "assumptions",
    "assumptions_prefix": "assumptions",
    "initialization_stage_fallback": "initialization",
    "assumptions_stage_fallback": "assumptions",
}

_STAGE_SHAPE = {
    "kernel": ("domain.frame_state", "domain_rule"),
    "initialization": ("initial.target", "initial_fact"),
    "assumptions": ("assumption.frame", "assumption"),
}

_ALL_SCOPES = tuple(CLASSIFICATION_SCOPES.values()) + STAGE_FALLBACK_SCOPES

#: Rules Draft 2020-12 cannot state, so the schema accepts a payload the Python
#: side refuses.  These are **known asymmetries, not agreement**: the schema is a
#: structural gate here and the constructor is the semantic one.  Each entry is
#: asserted rather than skipped, so tightening the schema later fails this list
#: instead of passing silently, and so no summary can quietly report the corpus
#: as fully equivalent.
_INEXPRESSIBLE = {
    "narrative step citing a member outside the core": (
        "Draft 2020-12 can constrain reasoning_steps[*].item_ids and core.items "
        "each on their own, but membership of one array's strings in a key of the "
        "other is a relation between siblings rather than a property of either; "
        "the constructor enforces it"
    ),
    "review surface naming a member that cannot be edited": (
        "the same cross-array relation, plus a condition on the referenced "
        "member's own editable flag; Draft 2020-12 cannot follow a string to the "
        "member it names, so the constructor checks both"
    ),
    "duplicate stable_id with differing content": (
        "uniqueness over a nested key (items[*].constraint.stable_id) has no "
        "Draft 2020-12 keyword; uniqueItems only catches identical members"
    ),
    "aggregate reason drift": (
        "Draft 2020-12 has no way to compare two arbitrary strings, so it "
        "cannot check that refinement_reason equals explanation.reason; the "
        "constructor enforces that equality on its own"
    ),
    "published metadata nested deeper than the published limit": (
        "Draft 2020-12 has no depth keyword at all, so a schema cannot state a "
        "nesting bound; the constructor refuses anything past "
        "MAX_METADATA_DEPTH because the recursive walk and the JSON encoder "
        "share the interpreter stack"
    ),
    "integer longer than the published digit limit": (
        "Draft 2020-12 bounds a number's value, not the digits it needs to be "
        "rendered; CPython refuses to render one past 4300 digits, so the "
        "constructor rejects it while a validator sees an ordinary integer"
    ),
    "duration past the float range": (
        "Draft 2020-12 bounds a number's value, but an integer larger than the "
        "float range is still a legal JSON number it accepts; a duration has to "
        "be representable as one, so the constructor refuses it"
    ),
    "non-finite number anywhere in a published mapping": (
        "NaN and Infinity are not JSON numbers, but a Draft 2020-12 validator "
        "walking Python objects sees float('nan') as a legal number, so it "
        "cannot refuse one; the constructor rejects them at every nesting depth"
    ),
    "non-JSON value anywhere in a published mapping": (
        "a value with no JSON counterpart, such as bytes or an arbitrary "
        "object, has no representation for a validator to reject -- by the time "
        "a payload reaches one it has already been parsed from JSON text; the "
        "constructor rejects them at every nesting depth"
    ),
    "non-string object key in any published mapping": (
        "JSON object keys are always strings, so a Python mapping keyed by 1 "
        'serializes to "1" and no validator can see the difference. This covers '
        "every published mapping -- refs, normalized_fact and their nested "
        "mappings -- because the same argument applies to all of them; the "
        "Python side rejects them so a key never changes shape silently"
    ),
}


@pytest.fixture(scope="module")
def validator():
    """Return a validator bound to the published explanation definition.

    ``jsonschema`` is a local development convenience rather than a declared
    test dependency, so this follows the repository's existing convention of
    skipping schema checks when it is absent.
    """
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(
        {"$ref": "#/$defs/infeasibilityExplanation", "$defs": schema["$defs"]}
    )


def _member(
    stable_id: str,
    stage: str,
    kind: str = "generated",
    frames=(),
    steps=(),
    span=None,
    refs=None,
    **overrides,
):
    """Build one canonical core member, allowing deliberate corruption."""
    category, role = _STAGE_SHAPE[stage]
    source = {"kind": kind, "path": None, "span": None}
    if span is not None:
        source = {"kind": "fbmcq", "path": "q.fbmcq", "span": dict(span)}
    constraint = {
        "stable_id": stable_id,
        "stage": stage,
        "category": category,
        "source": source,
        "summary": "group %s" % stable_id,
        "frames": list(frames),
        "steps": list(steps),
        "refs": dict(refs or {}),
    }
    member = {
        "constraint": constraint,
        "semantic_role": role,
        "source_excerpt": None,
        "source_excerpt_truncated": False,
        "normalized_fact": {"kind": "structural_constraint"},
        "human_text": "text for %s" % stable_id,
        "editable": False,
    }
    member.update(overrides)
    return member


def _payload(
    *,
    requested_mode="formal",
    achieved_mode="formal",
    status="partial",
    classification="initialization_self_conflict",
    scope="initialization_component",
    reduction="raw",
    subset_minimality="not_proven",
    members=None,
    reason="r",
    elapsed_ms=1.0,
):
    """Assemble one canonical explanation payload."""
    core = None
    if scope is not None:
        if members is None:
            members = [_member("g0", _SCOPE_MEMBER_STAGE[scope])]
        core = {
            "scope": scope,
            "formula_summary": "F",
            "granularity": "source_group",
            "reduction": reduction,
            "subset_minimality": subset_minimality,
            "items": members,
        }
    return {
        "requested_mode": requested_mode,
        "achieved_mode": achieved_mode,
        "status": status,
        "classification": classification,
        "core": core,
        "proof": None,
        "narrative": None,
        "reason": reason,
        "elapsed_ms": elapsed_ms,
    }


def _span(payload):
    """Rebuild a span from its canonical mapping, or ``None`` when absent."""
    if payload is None:
        return None
    from pyfcstm.utils.validate import Span

    return Span(
        payload["line"],
        payload["column"],
        payload["end_line"],
        payload["end_column"],
    )


def _constructor_accepts(payload) -> bool:
    """Report whether the public constructors accept a canonical payload."""
    try:
        core = None
        narrative = payload["narrative"]
        if isinstance(narrative, dict):
            # The corpus carries payloads, and this side has to build the objects
            # they describe -- passing the mapping through reached the constructor
            # as a mapping and raised AttributeError, which is outside the caught
            # set, so a narrative payload could not be judged at all.
            narrative = BmcConflictNarrative(
                narrative["derivation_status"],
                narrative["headline"],
                narrative["summary"],
                tuple(
                    BmcReasoningStep(
                        step["kind"],
                        tuple(step["item_ids"]),
                        tuple(step["proof_node_ids"]),
                        step["text"],
                    )
                    for step in narrative["reasoning_steps"]
                ),
                tuple(narrative["review_surfaces"]),
            )
        if payload["core"] is not None:
            raw = payload["core"]
            items = tuple(
                BmcCoreItem(
                    BmcConstraintRef(
                        entry["constraint"]["stable_id"],
                        entry["constraint"]["stage"],
                        entry["constraint"]["category"],
                        BmcSourceRef(
                            entry["constraint"]["source"]["kind"],
                            entry["constraint"]["source"]["path"],
                            _span(entry["constraint"]["source"]["span"]),
                        ),
                        entry["constraint"]["summary"],
                        tuple(entry["constraint"]["frames"]),
                        tuple(entry["constraint"]["steps"]),
                        entry["constraint"]["refs"],
                    ),
                    entry["semantic_role"],
                    entry["source_excerpt"],
                    entry["source_excerpt_truncated"],
                    entry["normalized_fact"],
                    entry["human_text"],
                    entry["editable"],
                )
                for entry in raw["items"]
            )
            core = BmcConflictCore(
                raw["scope"],
                raw["formula_summary"],
                raw["granularity"],
                raw["reduction"],
                raw["subset_minimality"],
                items,
            )
        BmcInfeasibilityExplanation(
            payload["requested_mode"],
            payload["achieved_mode"],
            payload["status"],
            payload["classification"],
            core,
            payload["proof"],
            narrative,
            payload["reason"],
            payload["elapsed_ms"],
        )
        return True
    except (ValueError, TypeError) as err:
        # ValueError: a frozen vocabulary or cross-field rule rejected it.
        # TypeError: a slot received a value of the wrong type.
        del err
        return False


def _scalar_corpus():
    """Yield the scalar cross product over every frozen vocabulary."""
    classifications = [None] + list(CLASSIFICATION_SCOPES)
    for requested, achieved in itertools.product(
        ["none", "formal", "proof"], ["none", "formal", "proof"]
    ):
        for status in ["complete", "partial", "unknown", "timeout"]:
            for classification in classifications:
                for scope in [None] + list(_ALL_SCOPES):
                    for reduction, minimality in [
                        ("raw", "not_proven"),
                        ("partial_minimized", "not_proven"),
                        ("subset_minimal", "proven"),
                    ]:
                        for reason in [None, "r"]:
                            yield (
                                "scalar",
                                _payload(
                                    requested_mode=requested,
                                    achieved_mode=achieved,
                                    status=status,
                                    classification=classification,
                                    scope=scope,
                                    reduction=reduction,
                                    subset_minimality=minimality,
                                    reason=reason,
                                ),
                            )


def _narrative_payload(**overrides):
    """Return a payload carrying a narrative, so the subobject enters the matrix.

    Every corpus entry hardcoded ``"narrative": None``, so the whole subobject
    this PR added -- five fields plus a step array -- had no bidirectional
    coverage at all: nothing proved the two gates agree about any narrative.
    """
    narrative = {
        "derivation_status": "structural_only",
        "headline": "The assumptions cannot hold together.",
        "summary": "The listed groups are jointly unsatisfiable.",
        "reasoning_steps": [
            {
                "kind": "fact",
                "item_ids": ["initial.target"],
                "proof_node_ids": [],
                "text": "At frame 0, the query requires state Root.A.",
            }
        ],
        "review_surfaces": ["initial.target"],
    }
    narrative.update(overrides)
    # An editable member, because review surfaces may only name members the
    # reader can open -- the default member is generated and not editable, and
    # naming it would exercise that rule rather than the narrative's own shape.
    member = _member("initial.target", "initialization")
    member["editable"] = True
    member["source_excerpt"] = 'init state("Root.A");'
    member["constraint"]["source"] = {
        "kind": "fbmcq",
        "path": "q.fbmcq",
        "span": {"line": 1, "column": 1, "end_line": 1, "end_column": 22},
    }
    payload = _payload(members=[member])
    payload["narrative"] = narrative
    return payload


def _narrative_corpus():
    """Yield payloads that differ only inside the narrative subobject."""
    yield ("narrative: structural only", _narrative_payload())
    yield (
        "narrative: complete without a conflict step",
        _narrative_payload(derivation_status="complete"),
    )
    yield (
        "narrative: blank headline",
        _narrative_payload(headline="   "),
    )
    yield (
        "narrative: blank summary",
        _narrative_payload(summary="   "),
    )
    yield (
        "narrative: step with a blank id",
        _narrative_payload(
            reasoning_steps=[
                {
                    "kind": "fact",
                    "item_ids": ["   "],
                    "proof_node_ids": [],
                    "text": "t",
                }
            ]
        ),
    )
    yield (
        "narrative: step kind outside the vocabulary",
        _narrative_payload(
            reasoning_steps=[
                {
                    "kind": "guidance",
                    "item_ids": ["initial.target"],
                    "proof_node_ids": [],
                    "text": "t",
                }
            ]
        ),
    )
    yield (
        "narrative: step with no ids at all",
        _narrative_payload(
            reasoning_steps=[
                {"kind": "fact", "item_ids": [], "proof_node_ids": [], "text": "t"}
            ]
        ),
    )


def _structural_corpus():
    """Yield payloads that only differ in how the core members relate."""
    yield (
        "two members",
        _payload(
            members=[
                _member("g1", "initialization"),
                _member("g0", "initialization"),
            ]
        ),
    )
    yield (
        "member outside a component scope",
        _payload(
            scope="assumptions_component",
            classification="assumptions_self_conflict",
            members=[_member("g0", "initialization")],
        ),
    )
    yield (
        "transition member inside a domain scope",
        _payload(
            scope="initialization_domain",
            classification="initialization_domain_conflict",
            members=[
                _member(
                    "g0",
                    "kernel",
                    category="transition.step",
                    semantic_role="transition_rule",
                )
            ],
        ),
    )
    yield (
        "kernel member inside a component scope",
        _payload(members=[_member("g0", "kernel")]),
    )
    yield (
        "prefix scope reaching earlier stages",
        _payload(
            scope="assumptions_prefix",
            classification="assumptions_prefix_conflict",
            members=[
                _member("g0", "kernel"),
                _member("g1", "initialization"),
                _member("g2", "assumptions"),
            ],
        ),
    )
    yield (
        "unsupported source kind",
        _payload(members=[_member("g0", "initialization", kind="bogus")]),
    )
    yield (
        "generated reference carrying a path",
        _payload(
            members=[
                _member(
                    "g0",
                    "initialization",
                    constraint={
                        "stable_id": "g0",
                        "stage": "initialization",
                        "category": "initial.target",
                        "source": {
                            "kind": "generated",
                            "path": "machine.fcstm",
                            "span": None,
                        },
                        "summary": "s",
                        "frames": [],
                        "steps": [],
                        "refs": {},
                    },
                )
            ]
        ),
    )
    yield (
        "identical duplicate members",
        _payload(
            members=[_member("g0", "initialization"), _member("g0", "initialization")]
        ),
    )
    yield "empty member list", _payload(members=[])
    yield "negative elapsed time", _payload(elapsed_ms=-1.0)
    yield (
        "negative frame index",
        _payload(members=[_member("g0", "initialization", frames=(-1,))]),
    )
    yield (
        "negative step index",
        _payload(members=[_member("g0", "initialization", steps=(-1,))]),
    )
    yield (
        "whole float index",
        _payload(members=[_member("g0", "initialization", frames=(1.0,))]),
    )
    yield (
        "valid frame and step indices",
        _payload(members=[_member("g0", "initialization", frames=(0, 2), steps=(1,))]),
    )
    yield (
        "zero span line",
        _payload(
            members=[
                _member(
                    "g0",
                    "initialization",
                    span={"line": 0, "column": 1, "end_line": 1, "end_column": 5},
                )
            ]
        ),
    )
    yield (
        "negative span column",
        _payload(
            members=[
                _member(
                    "g0",
                    "initialization",
                    span={"line": 1, "column": -2, "end_line": 1, "end_column": 5},
                )
            ]
        ),
    )
    yield (
        "anchor-only span",
        _payload(
            members=[
                _member(
                    "g0",
                    "initialization",
                    span={
                        "line": 1,
                        "column": 1,
                        "end_line": None,
                        "end_column": None,
                    },
                )
            ]
        ),
    )
    yield (
        "valid one-based span",
        _payload(
            members=[
                _member(
                    "g0",
                    "initialization",
                    span={"line": 1, "column": 1, "end_line": 1, "end_column": 5},
                )
            ]
        ),
    )
    for label, stable_id in (
        ("tab", "a\tb"),
        ("newline", "a\nb"),
        ("nul", "a\x00b"),
        ("delete", "a\x7fb"),
        ("non-ascii", "\u51b2\u7a81"),
        ("printable space", "a b"),
        ("printable tilde", "~max"),
    ):
        yield (
            "stable id: %s" % label,
            _payload(members=[_member(stable_id, "initialization")]),
        )
    yield (
        "structural refs mapping",
        _payload(members=[_member("g0", "initialization", refs={"frame": 0})]),
    )
    yield (
        "non-string object key in any published mapping",
        _payload(members=[_member("g0", "initialization", refs={1: "a"})]),
    )
    # The same argument applies to every published mapping, so vary the other
    # ones too.  Pinning only refs let normalized_fact drift with the exact
    # content assertion still green.
    yield (
        "non-string object key in any published mapping",
        _payload(members=[_member("g0", "initialization", refs={"nested": {2: "b"}})]),
    )
    yield (
        "non-string object key in any published mapping",
        _payload(
            members=[
                _member(
                    "g0",
                    "initialization",
                    normalized_fact={
                        "kind": "structural_constraint",
                        "nested": {3: "c"},
                    },
                )
            ]
        ),
    )
    deep = {"leaf": 1}
    for _ in range(_MAX_METADATA_DEPTH + 5):
        deep = {"n": deep}
    yield (
        "published metadata nested deeper than the published limit",
        _payload(members=[_member("g0", "initialization", refs=deep)]),
    )
    # The validator harness renders the payload, and CPython refuses to render an
    # integer this long under its default limit -- which is the very reason the
    # constructor rejects it.  Raising the interpreter limit for this one case
    # keeps the corpus able to state the asymmetry at all.
    # The limit itself only exists from Python 3.11 on; before that an integer of
    # any length renders, so there is nothing to raise.
    if hasattr(sys, "set_int_max_str_digits"):
        sys.set_int_max_str_digits(_MAX_METADATA_INT_DIGITS * 2)
    yield (
        "duration past the float range",
        _payload(elapsed_ms=10**400),
    )
    yield (
        "integer longer than the published digit limit",
        _payload(
            members=[
                _member(
                    "g0", "initialization", refs={"huge": 10**_MAX_METADATA_INT_DIGITS}
                )
            ]
        ),
    )
    yield (
        "non-finite number anywhere in a published mapping",
        _payload(
            members=[_member("g0", "initialization", refs={"n": {"x": float("nan")}})]
        ),
    )
    yield (
        "non-finite number anywhere in a published mapping",
        _payload(
            members=[
                _member(
                    "g0",
                    "initialization",
                    normalized_fact={
                        "kind": "structural_constraint",
                        "n": {"x": float("inf")},
                    },
                )
            ]
        ),
    )
    yield (
        "non-JSON value anywhere in a published mapping",
        _payload(
            members=[_member("g0", "initialization", refs={"n": {"x": b"bytes"}})]
        ),
    )
    yield (
        "refs given as an array",
        _payload(members=[_member("g0", "initialization", refs=[])]),
    )
    yield (
        "excerpt over the published bound",
        _payload(
            members=[
                _member(
                    "g0",
                    "initialization",
                    source_excerpt="x" * 4097,
                    source_excerpt_truncated=True,
                )
            ]
        ),
    )
    yield (
        "excerpt at the published bound",
        _payload(
            members=[
                _member(
                    "g0",
                    "initialization",
                    source_excerpt="x" * 4096,
                    source_excerpt_truncated=True,
                )
            ]
        ),
    )
    yield (
        "empty excerpt",
        _payload(members=[_member("g0", "initialization", source_excerpt="")]),
    )


def test_scalar_corpus_agrees(validator) -> None:
    """Every frozen vocabulary combination is judged the same by both sides."""
    disagreements = []
    accepted = 0
    total = 0
    for _, payload in _scalar_corpus():
        total += 1
        by_schema = validator.is_valid(payload)
        by_constructor = _constructor_accepts(payload)
        accepted += by_constructor
        if by_schema != by_constructor:
            disagreements.append((payload, by_schema, by_constructor))

    assert total > 5000
    assert accepted, "the corpus must contain payloads both sides accept"
    assert disagreements == [], (
        "the scalar corpus must agree exactly; only the structural cases named "
        "in _INEXPRESSIBLE are allowed to diverge"
    )


@pytest.mark.parametrize(
    "name, payload", list(_structural_corpus()) + list(_narrative_corpus())
)
def test_structural_corpus_agrees(validator, name, payload) -> None:
    """Relational rules about core members bind both sides equally.

    These are the cases a scalar cross product can never reach, because it
    never varies the member list.
    """
    by_schema = validator.is_valid(payload)
    by_constructor = _constructor_accepts(payload)

    if name in _INEXPRESSIBLE:
        # Pin the asymmetry instead of skipping it: the schema must accept and
        # the constructor must refuse.  Either side changing makes this fail and
        # sends the reader to the list above.
        assert by_schema is True, "%s: schema no longer accepts it" % name
        assert by_constructor is False, "%s: %s" % (name, _INEXPRESSIBLE[name])
        return
    assert by_schema == by_constructor, name


def test_a_duplicate_stable_id_is_still_refused_in_python() -> None:
    """The documented schema gap must not become a Python gap too.

    Draft 2020-12 has no keyword for uniqueness over a nested key, so two
    members sharing a ``stable_id`` while differing elsewhere pass the schema.
    The constructor is the only thing standing between that payload and a core
    that quotes one source group twice, so it is pinned here explicitly, on top
    of the bidirectional pinning every named asymmetry gets above.

    The frozen contract names this gap and eight others: the schema is the
    structural gate and the constructor the semantic gate, and each exception
    must be pinned from both sides.
    """
    payload = _payload(
        members=[
            _member("same", "initialization", human_text="first"),
            _member("same", "initialization", human_text="second"),
        ]
    )

    assert _constructor_accepts(payload) is False
    assert "duplicate stable_id with differing content" in _INEXPRESSIBLE


def _feasibility_payload():
    """Return a real solved feasibility payload carrying an explanation."""
    from pyfcstm.bmc import build_bmc_core_formula, compile_bmc_property
    from pyfcstm.bmc.engine import BmcEngine
    from pyfcstm.bmc.witness import solve_bmc_property
    from pyfcstm.model import load_state_machine_from_text

    machine = load_state_machine_from_text(
        "def int x = 0;\n"
        "state Root { event Go; state A; state B; [*] -> A; A -> B :: Go; }"
    )
    context = BmcEngine(machine).prepare(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="formal",
    )
    return result.feasibility.to_canonical()


@pytest.fixture(scope="module")
def feasibility_validator():
    """Return a validator bound to the published feasibility definition."""
    jsonschema = pytest.importorskip("jsonschema")
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    return jsonschema.Draft202012Validator(
        {"$ref": "#/$defs/feasibility", "$defs": schema["$defs"]}
    )


def test_a_real_solved_payload_is_schema_valid(feasibility_validator) -> None:
    """The payload the solver actually produces must satisfy the schema."""
    payload = _feasibility_payload()

    assert payload["explanation"] is not None
    assert list(feasibility_validator.iter_errors(payload)) == []


def _drift_cases():
    """Yield aggregate payloads that contradict the explanation beside them."""

    def status_drift(payload):
        payload["refinement_status"] = "timeout"

    def empty_ledger(payload):
        payload["refinement_checks"] = []

    def stage_drift(payload):
        payload["infeasible_stage"] = "initialization"

    def reason_drift(payload):
        # A complete explanation carries no reason at all, and a completed
        # refinement's own reason must be null, so the drift is staged on the
        # degraded delivery where both fields legitimately hold text.  Otherwise
        # the mutation trips the "completed refinement has no reason" rule and
        # never reaches the equality this case exists to pin.
        payload["explanation"]["status"] = "partial"
        payload["explanation"]["reason"] = "the derivation did not close"
        payload["refinement_status"] = "partial"
        payload["refinement_reason"] = "a different reason for the same stage"

    def member_outside_scope(payload):
        # Scope membership is judged at aggregate precision, so the escape has
        # to change the category family rather than only the stage.
        member = payload["explanation"]["core"]["items"][0]
        member["constraint"]["stage"] = "kernel"
        member["constraint"]["category"] = "transition.step"
        member["semantic_role"] = "transition_rule"

    def untyped_source(payload):
        member = payload["explanation"]["core"]["items"][0]
        member["constraint"]["source"] = {
            "kind": "bogus",
            "path": None,
            "span": None,
        }

    def step_outside_core(payload):
        # A step citing an id no member carries.  Both arrays stay individually
        # well formed, so only a relation between them can see the gap.
        payload["explanation"]["narrative"]["reasoning_steps"].append(
            {
                "kind": "fact",
                "item_ids": ["absent.member"],
                "proof_node_ids": [],
                "text": "a step pointing nowhere",
            }
        )

    def surface_not_editable(payload):
        # A surface naming a member that exists but carries editable=false.
        member = payload["explanation"]["core"]["items"][0]
        member["editable"] = False
        payload["explanation"]["narrative"]["review_surfaces"] = [
            member["constraint"]["stable_id"]
        ]

    def duplicate_member(payload):
        items = payload["explanation"]["core"]["items"]
        items.append(json.loads(json.dumps(items[0])))

    def proven_without_a_completed_minimization_record(payload):
        # A proven core whose minimization phase timed out.  Each array is
        # individually well formed -- the status is in the published vocabulary
        # and the reduction level is legal -- so only a conditional relation
        # between the two arrays can see that the proof was never closed.
        core = payload["explanation"]["core"]
        core["reduction"] = "subset_minimal"
        core["subset_minimality"] = "proven"
        # Replace the phase record rather than adding to it: a run that really
        # proved minimality already published a completed one, and leaving it in
        # place would make the payload consistent again.
        payload["refinement_checks"] = [
            check
            for check in payload["refinement_checks"]
            if check["name"] != "unsat_core_minimization"
        ] + [
            {
                "name": "unsat_core_minimization",
                "status": "timeout",
                "reason": "deletion trial timed out",
                "elapsed_ms": 1.0,
            }
        ]

    return [
        ("narrative step citing a member outside the core", step_outside_core),
        ("review surface naming a member that cannot be edited", surface_not_editable),
        ("aggregate status drift", status_drift),
        ("explanation without a ledger", empty_ledger),
        ("localized stage drift", stage_drift),
        ("aggregate reason drift", reason_drift),
        ("core member outside its scope", member_outside_scope),
        ("unsupported source kind", untyped_source),
        ("duplicate core member", duplicate_member),
        (
            "proven minimality without a completed minimization record",
            proven_without_a_completed_minimization_record,
        ),
    ]


@pytest.mark.parametrize("name, mutate", _drift_cases())
def test_aggregate_and_explanation_cannot_drift_apart(
    feasibility_validator, name, mutate
) -> None:
    """The schema rejects every contradiction the constructor rejects.

    These are cross-layer rules: the aggregate telemetry, the localized stage
    and the published explanation are three views of one run, so a payload
    that makes them disagree must fail on both sides rather than only in
    Python.
    """
    payload = _feasibility_payload()
    mutate(payload)

    if name in _INEXPRESSIBLE:
        # Pin the asymmetry rather than skipping it: the schema accepts this and
        # the constructor refuses it, so tightening either side fails here and
        # sends the reader to the list above.
        assert not list(feasibility_validator.iter_errors(payload)), (
            "%s: the schema now rejects it, so update _INEXPRESSIBLE" % name
        )
        return
    assert list(feasibility_validator.iter_errors(payload)), name


def test_the_constructor_still_enforces_every_named_asymmetry() -> None:
    """Each named asymmetry must be refused by the side that can express it.

    The list above records what the schema cannot check.  If the constructor
    ever stopped checking one of them too, the rule would hold nowhere at all
    while these tests kept passing, so each one is pinned on the Python side
    here as well.
    """
    from dataclasses import replace

    from pyfcstm.bmc.errors import BmcBuildError
    from pyfcstm.bmc.explanation import BmcConflictCore
    from pyfcstm.bmc.provenance import BmcSourceRef as _SourceRef

    # aggregate reason drift
    from pyfcstm.bmc import build_bmc_core_formula, compile_bmc_property
    from pyfcstm.bmc.engine import BmcEngine
    from pyfcstm.bmc.witness import solve_bmc_property
    from pyfcstm.model import load_state_machine_from_text

    machine = load_state_machine_from_text(
        "def int x = 0;\n"
        "state Root { event Go; state A; state B; [*] -> A; A -> B :: Go; }"
    )
    context = BmcEngine(machine).prepare(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    feasibility = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="formal",
    ).feasibility
    # Staged on the degraded delivery: a complete explanation carries no reason
    # and a completed refinement's own reason must be null, so on the real
    # complete payload a forged aggregate reason trips that rule first and never
    # reaches the equality this case exists to pin.
    degraded = replace(
        feasibility,
        refinement_status="partial",
        refinement_reason="the derivation did not close",
        explanation=replace(
            feasibility.explanation,
            status="partial",
            reason="the derivation did not close",
        ),
    )
    with pytest.raises(BmcBuildError, match="must match the explanation reason"):
        replace(degraded, refinement_reason="a forged aggregate reason")

    # narrative step citing a member outside the core, and a review surface that
    # names a member the reader cannot edit.  Both go through the public
    # constructor with a real published core beside them.
    narrative = feasibility.explanation.narrative
    with pytest.raises(ValueError, match="reasoning step cites"):
        replace(
            feasibility.explanation,
            narrative=replace(
                narrative,
                reasoning_steps=narrative.reasoning_steps
                + (BmcReasoningStep("fact", ("absent.member",), (), "text"),),
            ),
        )
    with pytest.raises(ValueError, match="not editable"):
        replace(
            feasibility.explanation,
            core=replace(
                feasibility.explanation.core,
                items=(replace(feasibility.explanation.core.items[0], editable=False),)
                + feasibility.explanation.core.items[1:],
            ),
            narrative=replace(
                narrative,
                review_surfaces=(
                    feasibility.explanation.core.items[0].constraint.stable_id,
                ),
            ),
        )

    # duplicate stable_id with differing content
    def member(text):
        reference = BmcConstraintRef(
            "same",
            "assumptions",
            "assumption.frame",
            _SourceRef("generated", None, None),
            "frame assumption",
        )
        return BmcCoreItem(
            reference,
            "assumption",
            None,
            False,
            {"kind": "structural_constraint"},
            text,
            False,
        )

    with pytest.raises(ValueError, match="duplicate stable ids"):
        BmcConflictCore(
            "assumptions_component",
            "ENV_N",
            "source_group",
            "raw",
            "not_proven",
            (member("first reading"), member("second reading")),
        )

    # published metadata nested deeper than the published limit
    deep_refs = {"leaf": 1}
    for _ in range(_MAX_METADATA_DEPTH + 5):
        deep_refs = {"n": deep_refs}
    with pytest.raises(ValueError, match="nests deeper than the published limit"):
        BmcConstraintRef(
            "g0",
            "assumptions",
            "assumption.frame",
            _SourceRef("generated", None, None),
            "s",
            refs=deep_refs,
        )

    # duration past the float range
    with pytest.raises(ValueError, match="too large to represent"):
        BmcInfeasibilityExplanation(
            requested_mode="formal",
            achieved_mode="none",
            status="unknown",
            classification=None,
            reason="probe unknown",
            elapsed_ms=10**400,
        )

    # integer longer than the published digit limit
    with pytest.raises(ValueError, match="exceeds the .* decimal digits"):
        BmcConstraintRef(
            "g0",
            "assumptions",
            "assumption.frame",
            _SourceRef("generated", None, None),
            "s",
            refs={"huge": 10**_MAX_METADATA_INT_DIGITS},
        )

    # non-finite number anywhere in a published mapping
    for bad_refs in ({"x": float("nan")}, {"n": {"x": float("inf")}}):
        with pytest.raises(ValueError, match="finite"):
            BmcConstraintRef(
                "g0",
                "assumptions",
                "assumption.frame",
                _SourceRef("generated", None, None),
                "s",
                refs=bad_refs,
            )

    # non-JSON value anywhere in a published mapping
    for bad_refs in ({"x": b"bytes"}, {"n": {"x": object()}}):
        with pytest.raises(TypeError, match="not JSON-compatible"):
            BmcConstraintRef(
                "g0",
                "assumptions",
                "assumption.frame",
                _SourceRef("generated", None, None),
                "s",
                refs=bad_refs,
            )

    # non-string object key in any published mapping.  One entry covers every
    # published mapping, so every one of them is pinned here; a rule checked on
    # refs alone would leave normalized_fact free to drift.
    with pytest.raises(TypeError, match="keys must be strings"):
        BmcConstraintRef(
            "g0",
            "assumptions",
            "assumption.frame",
            _SourceRef("generated", None, None),
            "s",
            refs={1: "a"},
        )
    with pytest.raises(TypeError, match="keys must be strings"):
        BmcConstraintRef(
            "g0",
            "assumptions",
            "assumption.frame",
            _SourceRef("generated", None, None),
            "s",
            refs={"nested": {2: "b"}},
        )
    for bad_fact in ({3: "c"}, {"kind": "structural_constraint", "nested": {4: "d"}}):
        with pytest.raises(TypeError, match="keys must be strings"):
            BmcCoreItem(
                BmcConstraintRef(
                    "g0",
                    "assumptions",
                    "assumption.frame",
                    _SourceRef("generated", None, None),
                    "s",
                ),
                "assumption",
                None,
                False,
                bad_fact,
                "frame assumption",
                False,
            )

    assert set(_INEXPRESSIBLE) == {
        "narrative step citing a member outside the core",
        "review surface naming a member that cannot be edited",
        "aggregate reason drift",
        "duplicate stable_id with differing content",
        "non-string object key in any published mapping",
        "published metadata nested deeper than the published limit",
        "integer longer than the published digit limit",
        "duration past the float range",
        "non-finite number anywhere in a published mapping",
        "non-JSON value anywhere in a published mapping",
    }


def test_the_schema_fact_kind_enum_is_neither_wider_nor_narrower() -> None:
    """The published ``kind`` enum has to be exactly what the package can emit.

    The corpus tests prove one direction -- every kind the package produces is
    accepted -- but they draw their values from ``_FACT_KINDS`` itself, so a schema
    listing a kind the code cannot emit passes all of them.  A consumer reading the
    published schema would write a branch for a case that never arrives.  Measured:
    adding a member to ``_FACT_KINDS`` alone fails the transcription guard, while
    adding the same member to the schema alone failed nothing before this test.

    Only this one enum is pinned.  A general "no schema enum may exceed its
    vocabulary" check needs a known-set assembled from every published vocabulary,
    and those live in several modules as a mix of tuples, ``Literal`` aliases and
    field annotations; a set gathered by scanning is a set that can silently
    over-collect, and a guard whose known-set is too wide passes everything.  The
    schema also narrows deliberately -- a conditional branch pins ``status`` to
    ``unknown``/``timeout`` where only those two occur -- so equality is not the
    right shape elsewhere either.  This is the site the gap was measured at, and
    the vocabulary a new fact kind extends.
    """
    schema = json.loads(_SCHEMA_PATH.read_text(encoding="utf-8"))
    published = schema["$defs"]["coreItem"]["properties"]["normalized_fact"][
        "properties"
    ]["kind"]["enum"]
    assert tuple(published) == _FACT_KINDS
