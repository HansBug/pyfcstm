"""BMC witness replay tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from pyfcstm.bmc import (
    BmcEngine,
    build_bmc_core_formula,
    compile_bmc_property,
)
from pyfcstm.bmc.witness import (
    BmcWitnessCallRecord,
    BmcWitnessTrace,
    decode_bmc_witness,
    replay_bmc_witness,
    solve_bmc_property,
)
from pyfcstm.model import load_state_machine_from_text


pytestmark = pytest.mark.unittest


def _trace(dsl_text: str, query_text: str):
    model = load_state_machine_from_text(dsl_text)
    formula = compile_bmc_property(
        build_bmc_core_formula(BmcEngine(model).prepare(query_text))
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"
    return model, decode_bmc_witness(formula, result.model)


def test_replay_reports_structured_var_mismatch() -> None:
    """Replay mismatches point at the exact frame variable path."""
    model, trace = _trace(
        """
        def int x = 0;
        state Root {
            state A { during { x = x + 1; } }
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A") && x == 1;',
    )
    bad_frame = replace(
        trace.frames[1],
        vars={**trace.frames[1].vars, "x": trace.frames[1].vars["x"] + 1},
    )
    bad_trace = BmcWitnessTrace(
        trace.property,
        trace.solver,
        trace.initial,
        (trace.frames[0], bad_frame),
        trace.steps,
        trace.diagnostics,
    )
    replay = replay_bmc_witness(model, bad_trace)
    assert replay.ok is False
    assert replay.mismatches[0].path == "frames[1].vars.x"
    assert replay.mismatches[0].message == "value mismatch"


def test_replay_accepts_havoc_where_initial_values_through_public_constructor() -> None:
    """Witness ``F_0.vars`` can override declaration initializers for replay."""
    model, trace = _trace(
        """
        def int x = 0;
        state Root {
            state A { during { x = x + 1; } }
            [*] -> A;
        }
        """,
        "init cold havoc * where x == 7;\n"
        'check reach <= 1: active("Root.A") && x == 8;',
    )
    assert trace.frames[0].vars == {"x": 7}
    replay = replay_bmc_witness(model, trace)
    assert replay.ok is True
    assert replay.runtime_trace.frames[0].vars == {"x": 7}
    assert replay.runtime_trace.frames[1].vars == {"x": 8}


def test_replay_handles_initial_terminated_absorb_trace() -> None:
    """Initial terminated witnesses replay as synthetic terminated traces."""
    model, trace = _trace(
        """
        def int x = 0;
        state Root;
        """,
        "init terminated havoc * where x == 3;\ncheck reach <= 1: terminated();",
    )
    assert trace.frames[0].sentinel == "terminated"
    replay = replay_bmc_witness(model, trace)
    assert replay.ok is True
    assert len(replay.runtime_trace.frames) == len(trace.frames)
    assert len(replay.runtime_trace.steps) == len(trace.steps)
    assert all(frame.terminated for frame in replay.runtime_trace.frames)
    assert replay.runtime_trace.frames[0].vars == {"x": 3}
    assert replay.runtime_trace.frames[-1].vars == {"x": 3}


def test_replay_checks_abstract_call_role_metadata() -> None:
    """Replay rejects witness call records with a corrupted runtime role."""
    model, trace = _trace(
        """
        state Root {
            state A {
                during abstract Touch;
            }
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A") && '
        'called("Root.A.Touch", step=0, role="leaf_during");',
    )
    assert trace.steps[0].abstract_calls[0].role == "leaf_during"
    replay = replay_bmc_witness(model, trace)
    assert replay.ok is True
    assert replay.runtime_trace.steps[0].abstract_calls[0].role == "leaf_during"

    bad_call = BmcWitnessCallRecord(
        trace.steps[0].abstract_calls[0].ordinal,
        trace.steps[0].abstract_calls[0].action_name,
        trace.steps[0].abstract_calls[0].stage,
        "state_enter",
        trace.steps[0].abstract_calls[0].state,
        trace.steps[0].abstract_calls[0].active_leaf,
        trace.steps[0].abstract_calls[0].named_ref,
        trace.steps[0].abstract_calls[0].snapshot,
    )
    bad_step = replace(trace.steps[0], abstract_calls=(bad_call,))
    bad_trace = BmcWitnessTrace(
        trace.property,
        trace.solver,
        trace.initial,
        trace.frames,
        (bad_step,),
        trace.diagnostics,
    )
    bad_replay = replay_bmc_witness(model, bad_trace)
    assert bad_replay.ok is False
    assert bad_replay.mismatches[0].path == "steps[0].abstract_calls[0].role"


def test_replay_wraps_user_abstract_handlers_after_recording() -> None:
    """Custom replay handlers run after the recorder captures call metadata."""
    model, trace = _trace(
        """
        state Root {
            state A {
                during abstract Touch;
            }
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A") && called("Root.A.Touch", step=0);',
    )
    observed = []

    def user_handler(ctx):
        observed.append((ctx.abstract_target, dict(ctx.vars)))

    replay = replay_bmc_witness(
        model, trace, abstract_handlers={"Root.A.Touch": user_handler}
    )
    assert replay.ok is True
    assert observed == [("Root.A.Touch", {})]
    assert replay.runtime_trace.steps[0].abstract_calls[0].role == "leaf_during"


def test_replay_disambiguates_unnamed_ref_roles_from_witness_step() -> None:
    """Ordered witness calls disambiguate legal runtime contexts without roles."""
    model, trace = _trace(
        """
        state Root {
            state Library {
                during abstract Shared;
            }
            >> during before ref /Library.Shared;
            state A {
                during ref /Library.Shared;
            }
            [*] -> A;
        }
        """,
        'init state("Root.A");\n'
        'check reach <= 1: call_count("Root.Library.Shared", step=0) == 2 '
        '&& called("Root.Library.Shared", step=0, role="aspect_during_before") '
        '&& called("Root.Library.Shared", step=0, role="leaf_during");',
    )

    assert [item.role for item in trace.steps[0].abstract_calls] == [
        "aspect_during_before",
        "leaf_during",
    ]
    replay = replay_bmc_witness(model, trace)
    assert replay.ok is True
    assert [item.role for item in replay.runtime_trace.steps[0].abstract_calls] == [
        "aspect_during_before",
        "leaf_during",
    ]
