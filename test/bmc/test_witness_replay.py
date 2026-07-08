"""BMC witness replay tests."""

from __future__ import annotations

from dataclasses import replace

import pytest

from pyfcstm.bmc import (
    BmcBuildError,
    BmcEngine,
    build_bmc_core_formula,
    compile_bmc_property,
)
from pyfcstm.bmc.witness import (
    BmcWitnessCallRecord,
    BmcWitnessEvent,
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


def test_replay_rejects_tampered_initial_terminated_step_payload() -> None:
    """Synthetic terminated replay still compares step events and calls."""
    model, trace = _trace(
        """
        def int x = 0;
        state Root;
        """,
        "init terminated havoc * where x == 3;\ncheck reach <= 1: terminated();",
    )
    assert replay_bmc_witness(model, trace).ok is True
    bad_step = replace(
        trace.steps[0],
        input_events=(BmcWitnessEvent("Root.fake", "explicit_true_assumption"),),
        abstract_calls=(
            BmcWitnessCallRecord(
                0,
                "Root.fake.Abstract",
                "during",
                "leaf_during",
                "Root",
                "Root",
                snapshot={"x": 3},
            ),
        ),
    )
    bad_trace = BmcWitnessTrace(
        trace.property,
        trace.solver,
        trace.initial,
        trace.frames,
        (bad_step,) + trace.steps[1:],
        trace.diagnostics,
    )

    replay = replay_bmc_witness(model, bad_trace)
    assert replay.ok is False
    assert any(
        item.path == "steps[0].input_events" and item.message == "input events mismatch"
        for item in replay.mismatches
    )
    assert any(
        item.path == "steps[0].abstract_calls"
        and item.message == "abstract call count mismatch"
        for item in replay.mismatches
    )


def test_replay_reports_witness_trace_shape_mismatches() -> None:
    """Replay reports corrupted step indices and frame/step linkage."""
    model, trace = _trace(
        """
        state Root {
            state A;
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A");',
    )
    bad_step = replace(trace.steps[0], index=3, source_frame=2, target_frame=4)
    bad_trace = BmcWitnessTrace(
        trace.property,
        trace.solver,
        trace.initial,
        trace.frames,
        (bad_step,) + trace.steps,
        trace.diagnostics,
    )

    replay = replay_bmc_witness(model, bad_trace)
    assert replay.ok is False
    paths = {item.path for item in replay.mismatches}
    assert "frames" in paths
    assert "steps[0].index" in paths
    assert "steps[0].source_frame" in paths
    assert "steps[0].target_frame" in paths


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


def test_replay_rejects_unknown_user_abstract_handler_paths() -> None:
    """Replay validates custom handler paths before constructing runtime traces."""
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
    with pytest.raises(BmcBuildError, match="unknown abstract action paths"):
        replay_bmc_witness(
            model,
            trace,
            abstract_handlers={"Root.A.Missing": lambda ctx: None},
        )


def test_replay_rejects_swapped_valid_unnamed_ref_roles() -> None:
    """Runtime role resolution is independent from mutable witness role fields."""
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
    calls = trace.steps[0].abstract_calls
    swapped_calls = (
        replace(calls[0], role=calls[1].role),
        replace(calls[1], role=calls[0].role),
    )
    bad_step = replace(trace.steps[0], abstract_calls=swapped_calls)
    bad_trace = BmcWitnessTrace(
        trace.property,
        trace.solver,
        trace.initial,
        trace.frames,
        (bad_step,),
        trace.diagnostics,
    )

    replay = replay_bmc_witness(model, bad_trace)
    assert replay.ok is False
    assert replay.runtime_trace.steps[0].abstract_calls[0].role == (
        "aspect_during_before"
    )
    assert any(
        item.path == "steps[0].abstract_calls[0].role"
        and item.message == "abstract call metadata mismatch"
        for item in replay.mismatches
    )


def test_replay_reports_missing_frame_and_call_snapshot_keys() -> None:
    """Replay rejects truncated witness vars and abstract-call snapshots."""
    model, trace = _trace(
        """
        def int x = 0;
        def int y = 1;
        state Root {
            state A {
                during abstract Touch;
                during { x = x + 1; }
            }
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A") && '
        'called("Root.A.Touch", step=0) && x == 1 && y == 1;',
    )
    assert replay_bmc_witness(model, trace).ok is True
    bad_frame = replace(trace.frames[1], vars={"x": trace.frames[1].vars["x"]})
    bad_call = replace(
        trace.steps[0].abstract_calls[0],
        snapshot={"x": trace.steps[0].abstract_calls[0].snapshot["x"]},
    )
    bad_step = replace(trace.steps[0], abstract_calls=(bad_call,))
    bad_trace = BmcWitnessTrace(
        trace.property,
        trace.solver,
        trace.initial,
        (trace.frames[0], bad_frame),
        (bad_step,),
        trace.diagnostics,
    )

    replay = replay_bmc_witness(model, bad_trace)
    assert replay.ok is False
    assert any(
        item.path == "frames[1].vars" and item.message == "variable key set mismatch"
        for item in replay.mismatches
    )
    assert any(
        item.path == "steps[0].abstract_calls[0].snapshot"
        and item.message == "abstract call snapshot key set mismatch"
        for item in replay.mismatches
    )


def test_replay_reports_state_and_termination_mismatches() -> None:
    """Replay reports corrupted state and termination frame metadata."""
    model, trace = _trace(
        """
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B;
        }
        """,
        'init state("Root.A");\ncheck reach <= 1: active("Root.B");',
    )
    bad_frame = replace(trace.frames[1], state="Root.A", terminated=True)
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
    assert any(item.path == "frames[1].state" for item in replay.mismatches)
    assert any(item.path == "frames[1].terminated" for item in replay.mismatches)
