"""BMC witness replay tests."""

from __future__ import annotations

import pathlib
from dataclasses import replace

import pytest
from hbutils.testing import TextAligner

from pyfcstm.bmc import (
    BmcBuildError,
    BmcEngine,
    UnsupportedBmcQuery,
    build_bmc_core_formula,
    compile_bmc_property,
)
from pyfcstm.bmc.witness import (
    BmcRuntimeStep,
    BmcWitnessCallRecord,
    BmcWitnessEvent,
    BmcWitnessFrame,
    BmcWitnessStep,
    BmcWitnessTrace,
    decode_bmc_witness,
    replay_bmc_witness,
    solve_bmc_property,
    _compare_step,
)
from pyfcstm.model import load_state_machine_from_text


pytestmark = pytest.mark.unittest
_TEXT = TextAligner().multiple_lines()


def _assert_text_equal(expected: str, actual: str) -> None:
    """Assert exact multiline text with aligned diff output."""
    _TEXT.assert_equal(expected, actual, max_diff=20, max_extra=20)


def _trace(dsl_text: str, query_text: str):
    model = load_state_machine_from_text(dsl_text)
    formula = compile_bmc_property(
        build_bmc_core_formula(BmcEngine(model).prepare(query_text))
    )
    result = solve_bmc_property(formula)
    assert result.status == "sat"
    return model, decode_bmc_witness(formula, result.model)


def test_replay_rejects_invalid_public_arguments() -> None:
    """The replay public API rejects invalid entry-point argument shapes."""
    model, trace = _trace("state Root;", 'check reach <= 1: active("Root");')

    with pytest.raises(BmcBuildError, match="state_machine must be StateMachine"):
        replay_bmc_witness(object(), trace)
    with pytest.raises(BmcBuildError, match="witness must be BmcWitnessTrace"):
        replay_bmc_witness(model, object())
    with pytest.raises(BmcBuildError, match="abstract_handlers must be a mapping"):
        replay_bmc_witness(model, trace, abstract_handlers=object())


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
    assert [item.to_canonical() for item in replay.mismatches] == [
        {
            "path": "frames[1].vars.x",
            "expected": 2,
            "actual": 1,
            "message": "value mismatch",
            "tolerance": None,
        }
    ]
    _assert_text_equal(
        """
        BmcReplayResult[mismatch] mismatches=1

        BmcRuntimeTrace frames=2 steps=1

        frame    via              state    progress      [x]    events    calls    extra
        -------  ---------------  -------  ------------  -----  --------  -------  -------
        0        -                Root     initial       0      -         -        I
        1        Root --> Root.A  Root.A   runtime_step  1      -         -        -

        MISMATCH frames[1].vars.x: 2 != 1
        """,
        replay.to_text(show_legend=False),
    )


def test_replay_rejects_non_finite_witness_variables_before_replay() -> None:
    """NaN/Inf witness payloads cannot forge successful replay comparisons."""
    _, trace = _trace(
        """
        def int x = 0;
        state Root {
            state A;
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A");',
    )

    with pytest.raises(BmcBuildError, match="vars.x"):
        replace(trace.frames[1], vars={"x": float("nan")})
    with pytest.raises(BmcBuildError, match="vars.x"):
        replace(trace.frames[1], vars={"x": float("inf")})
    with pytest.raises(BmcBuildError, match="snapshot.x"):
        BmcWitnessCallRecord(
            0,
            "Root.A.Touch",
            "during",
            "leaf_during",
            "Root.A",
            "Root.A",
            snapshot={"x": float("nan")},
        )


def test_replay_float_comparison_uses_tolerance() -> None:
    """Float replay compares with explicit tolerance and reports large drift."""
    model, trace = _trace(
        """
        def float x = 0.0;
        state Root {
            state A { during { x = x + 0.5; } }
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A") && x == 0.5;',
    )

    close_frame = replace(trace.frames[1], vars={"x": 0.5 + 1e-10})
    close_trace = BmcWitnessTrace(
        trace.property,
        trace.solver,
        trace.initial,
        (trace.frames[0], close_frame),
        trace.steps,
        trace.diagnostics,
    )
    assert replay_bmc_witness(model, close_trace).ok is True

    far_frame = replace(trace.frames[1], vars={"x": 0.5 + 1e-5})
    far_trace = BmcWitnessTrace(
        trace.property,
        trace.solver,
        trace.initial,
        (trace.frames[0], far_frame),
        trace.steps,
        trace.diagnostics,
    )
    replay = replay_bmc_witness(model, far_trace)
    assert replay.ok is False
    assert [item.to_canonical() for item in replay.mismatches] == [
        {
            "path": "frames[1].vars.x",
            "expected": 0.50001,
            "actual": 0.5,
            "message": "float value mismatch",
            "tolerance": 1e-9,
        }
    ]
    _assert_text_equal(
        """
        BmcReplayResult[mismatch] mismatches=1

        BmcRuntimeTrace frames=2 steps=1

        frame    via              state    progress      [x]    events    calls    extra
        -------  ---------------  -------  ------------  -----  --------  -------  -------
        0        -                Root     initial       0.0    -         -        I
        1        Root --> Root.A  Root.A   runtime_step  0.5    -         -        -

        MISMATCH frames[1].vars.x: 0.50001 != 0.5
        """,
        replay.to_text(show_legend=False),
    )


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
    _assert_text_equal(
        """
        BmcRuntimeTrace frames=2 steps=1

        frame    via              state    progress      [x]    events    calls    extra
        -------  ---------------  -------  ------------  -----  --------  -------  -------
        0        -                Root     initial       7      -         -        I
        1        Root --> Root.A  Root.A   runtime_step  8      -         -        -
        """,
        replay.runtime_trace.to_text(show_legend=False),
    )


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
    _assert_text_equal(
        """
        BmcRuntimeTrace frames=2 steps=1

        frame    via    state       progress      [x]    events    calls    extra
        -------  -----  ----------  ------------  -----  --------  -------  -------
        0        -      terminated  initial       3      -         -        IT
        1        -      terminated  runtime_step  3      -         -        T
        """,
        replay.runtime_trace.to_text(show_legend=False),
    )


def test_replay_uses_synthetic_observation_for_post_termination_absorb() -> None:
    """An absorb step after runtime termination has no cycle metadata."""
    model = load_state_machine_from_text(
        """
        state Root {
            state A;
            [*] -> A;
            A -> [*];
        }
        """
    )
    formula = compile_bmc_property(
        build_bmc_core_formula(
            BmcEngine(model).prepare(
                'init state("Root.A"); check reach <= 2: terminated();'
            )
        )
    )
    solved = solve_bmc_property(formula)
    assert solved.status == "sat"
    trace = decode_bmc_witness(formula, solved.model)
    assert trace.steps[-1].case_kind == "absorb"

    replay = replay_bmc_witness(model, trace)

    assert replay.ok is True
    absorb_step = replay.runtime_trace.steps[-1]
    assert absorb_step.delta is False

    forged_trace = replace(
        trace,
        steps=tuple(
            replace(step, delta=True) if step.case_kind == "absorb" else step
            for step in trace.steps
        ),
    )
    forged_replay = replay_bmc_witness(model, forged_trace)
    assert forged_replay.ok is False
    assert [mismatch.to_canonical() for mismatch in forged_replay.mismatches] == [
        {
            "path": "steps[%d].delta" % trace.steps[-1].index,
            "expected": True,
            "actual": False,
            "message": "delta mismatch",
            "tolerance": None,
        }
    ]


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
        input_events=(
            BmcWitnessEvent("Root.fake_consumed", "explicit_true_assumption"),
            BmcWitnessEvent("Root.fake_unconsumed", "explicit_true_assumption"),
        ),
        consumed_events=("Root.fake_consumed",),
        unconsumed_events=("Root.fake_unconsumed",),
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
    assert [item.to_canonical() for item in replay.mismatches] == [
        {
            "path": "steps[0].input_events",
            "expected": ["Root.fake_consumed", "Root.fake_unconsumed"],
            "actual": [],
            "message": "input events mismatch",
            "tolerance": None,
        },
        {
            "path": "steps[0].consumed_events",
            "expected": ["Root.fake_consumed"],
            "actual": [],
            "message": "consumed events mismatch",
            "tolerance": None,
        },
        {
            "path": "steps[0].unconsumed_events",
            "expected": ["Root.fake_unconsumed"],
            "actual": [],
            "message": "unconsumed events mismatch",
            "tolerance": None,
        },
        {
            "path": "steps[0].abstract_calls",
            "expected": 1,
            "actual": 0,
            "message": "abstract call count mismatch",
            "tolerance": None,
        },
    ]
    _assert_text_equal(
        """
        BmcReplayResult[mismatch] mismatches=4

        BmcRuntimeTrace frames=2 steps=1

        frame    via    state       progress      [x]    events    calls    extra
        -------  -----  ----------  ------------  -----  --------  -------  -------
        0        -      terminated  initial       3      -         -        IT
        1        -      terminated  runtime_step  3      -         -        T

        MISMATCH steps[0].input_events: Root.fake_consumed, Root.fake_unconsumed != -
        MISMATCH steps[0].consumed_events: Root.fake_consumed != -
        MISMATCH steps[0].unconsumed_events: Root.fake_unconsumed != -
        MISMATCH steps[0].abstract_calls: 1 != 0
        """,
        replay.to_text(show_legend=False),
    )


def test_replay_rejects_tampered_initial_terminated_frame_vars() -> None:
    """Synthetic terminated replay derives absorb vars from the initial frame."""
    model, trace = _trace(
        """
        def int x = 0;
        state Root;
        """,
        "init terminated havoc * where x == 3;\ncheck reach <= 1: terminated();",
    )
    assert replay_bmc_witness(model, trace).ok is True
    bad_frame = replace(trace.frames[1], vars={"x": 999})
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
    assert replay.runtime_trace.frames[1].vars == {"x": 3}
    assert [item.to_canonical() for item in replay.mismatches] == [
        {
            "path": "frames[1].vars.x",
            "expected": 999,
            "actual": 3,
            "message": "value mismatch",
            "tolerance": None,
        }
    ]


def test_replay_rejects_forged_non_initial_init_sentinel_frames() -> None:
    """Forged later ``init`` sentinels cannot hide real runtime states."""
    model, trace = _trace(
        """
        state Root {
            state A;
            [*] -> A;
        }
        """,
        'check reach <= 1: active("Root.A");',
    )
    with pytest.raises(BmcBuildError, match="sentinel frames"):
        replace(trace.frames[1], sentinel="init")
    with pytest.raises(BmcBuildError, match="init sentinel"):
        replace(
            trace.frames[1],
            state_id=None,
            state=None,
            sentinel="init",
            terminated=True,
        )

    forged_frame = BmcWitnessFrame(
        trace.frames[1].index,
        None,
        None,
        "init",
        False,
        dict(trace.frames[1].vars),
    )
    forged_trace = BmcWitnessTrace(
        trace.property,
        trace.solver,
        trace.initial,
        (trace.frames[0], forged_frame),
        trace.steps,
        trace.diagnostics,
    )

    result = replay_bmc_witness(model, forged_trace)

    assert [mismatch.to_canonical() for mismatch in result.mismatches] == [
        {
            "path": "frames[1].state",
            "expected": "Root",
            "actual": "Root.A",
            "message": "init sentinel state mismatch",
            "tolerance": None,
        }
    ]


def test_replay_accepts_later_init_sentinel_when_initial_cycle_stays_unstable() -> None:
    """Failed initial cycles may remain at the public ``init`` sentinel."""
    model = load_state_machine_from_text(
        """
        state Root {
            state A;
            [*] -> A :: Start;
        }
        """
    )
    trace = BmcWitnessTrace(
        {"kind": "reach"},
        {"status": "sat"},
        {"mode": "cold"},
        (
            BmcWitnessFrame(0, None, None, "init", False, {}),
            BmcWitnessFrame(1, None, None, "init", False, {}),
        ),
        (
            BmcWitnessStep(
                0,
                0,
                1,
                "Root::delta::0",
                "delta",
                "delta",
                None,
                None,
                True,
                False,
            ),
        ),
    )

    result = replay_bmc_witness(model, trace)

    assert result.ok
    assert result.to_canonical()["runtime_trace"] == {
        "frames": [
            {"index": 0, "state": "Root", "terminated": False, "vars": {}},
            {"index": 1, "state": "Root", "terminated": False, "vars": {}},
        ],
        "steps": [
            {
                "index": 0,
                "input_events": [],
                "consumed_events": [],
                "unconsumed_events": [],
                "abstract_calls": [],
                "delta": True,
            }
        ],
    }


def test_compare_step_reports_delta_forgery_path() -> None:
    """Replay comparison names the observable Delta field precisely."""
    witness_step = BmcWitnessStep(
        0,
        0,
        1,
        "Root::delta::0",
        "delta",
        "delta",
        None,
        None,
        True,
        False,
    )
    runtime_step = BmcRuntimeStep(
        0,
        (),
        (),
        (),
        (),
        delta=False,
    )
    mismatches = []
    _compare_step(mismatches, witness_step, runtime_step)
    assert [item.to_canonical() for item in mismatches] == [
        {
            "path": "steps[0].delta",
            "expected": True,
            "actual": False,
            "message": "delta mismatch",
            "tolerance": None,
        }
    ]


def test_replay_reports_init_sentinel_when_runtime_is_terminated() -> None:
    """An ``init`` sentinel cannot hide a terminated synthetic replay frame."""
    model = load_state_machine_from_text("state Root;")
    trace = BmcWitnessTrace(
        {"kind": "reach"},
        {"status": "sat"},
        {"mode": "cold"},
        (
            BmcWitnessFrame(0, None, None, "terminated", True, {}),
            BmcWitnessFrame(1, None, None, "init", False, {}),
        ),
        (),
    )

    result = replay_bmc_witness(model, trace)

    assert [mismatch.to_canonical() for mismatch in result.mismatches] == [
        {
            "path": "frames",
            "expected": 1,
            "actual": 2,
            "message": "frame/step length mismatch",
            "tolerance": None,
        },
        {
            "path": "frames[1].terminated",
            "expected": False,
            "actual": True,
            "message": "init sentinel terminated mismatch",
            "tolerance": None,
        },
    ]


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
    bad_frame = replace(trace.frames[1], index=7)
    bad_trace = BmcWitnessTrace(
        trace.property,
        trace.solver,
        trace.initial,
        (trace.frames[0], bad_frame),
        (bad_step,) + trace.steps,
        trace.diagnostics,
    )

    replay = replay_bmc_witness(model, bad_trace)
    assert replay.ok is False
    assert [item.to_canonical() for item in replay.mismatches] == [
        {
            "path": "frames",
            "expected": 3,
            "actual": 2,
            "message": "frame/step length mismatch",
            "tolerance": None,
        },
        {
            "path": "frames[1].index",
            "expected": 1,
            "actual": 7,
            "message": "frame index mismatch",
            "tolerance": None,
        },
        {
            "path": "steps[0].index",
            "expected": 0,
            "actual": 3,
            "message": "step index mismatch",
            "tolerance": None,
        },
        {
            "path": "steps[0].source_frame",
            "expected": 0,
            "actual": 2,
            "message": "step source frame mismatch",
            "tolerance": None,
        },
        {
            "path": "steps[0].target_frame",
            "expected": 1,
            "actual": 4,
            "message": "step target frame mismatch",
            "tolerance": None,
        },
        {
            "path": "steps[1].index",
            "expected": 1,
            "actual": 0,
            "message": "step index mismatch",
            "tolerance": None,
        },
        {
            "path": "steps[1].source_frame",
            "expected": 1,
            "actual": 0,
            "message": "step source frame mismatch",
            "tolerance": None,
        },
        {
            "path": "steps[1].target_frame",
            "expected": 2,
            "actual": 1,
            "message": "step target frame mismatch",
            "tolerance": None,
        },
    ]
    _assert_text_equal(
        """
        BmcReplayResult[mismatch] mismatches=8

        BmcRuntimeTrace frames=3 steps=2

        frame    via              state    progress       events    calls    extra
        -------  ---------------  -------  -------------  --------  -------  -------
        0        -                Root     initial        -         -        I
        4        -                Root.A   runtime_frame  -         -        -
        1        Root --> Root.A  Root.A   runtime_step   -         -        -

        MISMATCH frames: 3 != 2
        MISMATCH frames[1].index: 1 != 7
        MISMATCH steps[0].index: 0 != 3
        MISMATCH steps[0].source_frame: 0 != 2
        MISMATCH steps[0].target_frame: 1 != 4
        MISMATCH steps[1].index: 1 != 0
        MISMATCH steps[1].source_frame: 1 != 0
        MISMATCH steps[1].target_frame: 2 != 1
        """,
        replay.to_text(show_legend=False),
    )


def test_replay_reports_empty_witness_trace_shape_mismatch() -> None:
    """Replay rejects public traces without the required initial frame."""
    model = load_state_machine_from_text("state Root;")
    trace = BmcWitnessTrace(
        {"kind": "reach"},
        {"status": "sat"},
        {"mode": "cold"},
        (),
        (),
    )

    replay = replay_bmc_witness(model, trace)
    assert replay.ok is False
    assert [item.to_canonical() for item in replay.mismatches] == [
        {
            "path": "frames",
            "expected": 1,
            "actual": 0,
            "message": "frame/step length mismatch",
            "tolerance": None,
        }
    ]
    _assert_text_equal(
        """
        BmcReplayResult[mismatch] mismatches=1

        BmcRuntimeTrace frames=1 steps=0

        frame    via    state    progress    events    calls    extra
        -------  -----  -------  ----------  --------  -------  -------
        0        -      Root     initial     -         -        I

        MISMATCH frames: 1 != 0
        """,
        replay.to_text(show_legend=False),
    )


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
    assert [item.to_canonical() for item in bad_replay.mismatches] == [
        {
            "path": "steps[0].abstract_calls[0].role",
            "expected": "state_enter",
            "actual": "leaf_during",
            "message": "abstract call metadata mismatch",
            "tolerance": None,
        }
    ]


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
    """Replay validates custom handler mappings before constructing traces."""
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
    with pytest.raises(BmcBuildError, match="non-callable handlers"):
        replay_bmc_witness(model, trace, abstract_handlers={"Root.A.Touch": object()})


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
    assert [item.to_canonical() for item in replay.mismatches] == [
        {
            "path": "steps[0].abstract_calls[0].role",
            "expected": "leaf_during",
            "actual": "aspect_during_before",
            "message": "abstract call metadata mismatch",
            "tolerance": None,
        },
        {
            "path": "steps[0].abstract_calls[1].role",
            "expected": "aspect_during_before",
            "actual": "leaf_during",
            "message": "abstract call metadata mismatch",
            "tolerance": None,
        },
    ]


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
    assert [item.to_canonical() for item in replay.mismatches] == [
        {
            "path": "steps[0].abstract_calls[0].snapshot",
            "expected": ["x"],
            "actual": ["x", "y"],
            "message": "abstract call snapshot key set mismatch",
            "tolerance": None,
        },
        {
            "path": "frames[1].vars",
            "expected": ["x"],
            "actual": ["x", "y"],
            "message": "variable key set mismatch",
            "tolerance": None,
        },
    ]


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
    assert [item.to_canonical() for item in replay.mismatches] == [
        {
            "path": "frames[1].state",
            "expected": None,
            "actual": "Root.B",
            "message": "state mismatch",
            "tolerance": None,
        },
        {
            "path": "frames[1].terminated",
            "expected": True,
            "actual": False,
            "message": "terminated mismatch",
            "tolerance": None,
        },
    ]
    _assert_text_equal(
        """
        BmcReplayResult[mismatch] mismatches=2

        BmcRuntimeTrace frames=2 steps=1

        frame    via                state    progress      events    calls    extra
        -------  -----------------  -------  ------------  --------  -------  -------
        0        -                  Root.A   initial       -         -        I
        1        Root.A --> Root.B  Root.B   runtime_step  -         -        -

        MISMATCH frames[1].state: - != Root.B
        MISMATCH frames[1].terminated: true != false
        """,
        replay.to_text(show_legend=False),
    )


def _replay_call_records(dsl_text: str, query_text: str):
    """Replay a witness and return both sides' abstract call records.

    :param dsl_text: FCSTM source of the model under test.
    :type dsl_text: str
    :param query_text: FBMCQ query text driving the search.
    :type query_text: str
    :return: The replay result, the witness-side calls and the runtime-side ones.
    :rtype: Tuple[BmcReplayResult, Tuple[BmcWitnessCallRecord, ...], tuple]
    """
    model, trace = _trace(dsl_text, query_text)
    replay = replay_bmc_witness(model, trace)
    witness_calls = tuple(call for step in trace.steps for call in step.abstract_calls)
    runtime_calls = tuple(
        call for step in replay.runtime_trace.steps for call in step.abstract_calls
    )
    return replay, witness_calls, runtime_calls


_TERMINATES = "check reach <= 2: terminated();"

# A `ref` on a composite host, pointing at a named abstract action declared in a
# child. `_active_leaf_path` has no leaf on the stack while `Root` is being
# entered, so it falls back -- and the fallback used to read the `owner` a `ref`
# had already redirected to the declaring state. See issue #430.
_COMPOSITE_ENTER_REF = """
def int a = 0;
state Root {
    [*] -> Inner;
    Inner -> [*];
    enter ref Inner.act;
    state Inner {
        [*] -> Leaf;
        Leaf -> [*];
        enter abstract act;
        state Leaf;
    }
}
"""

_COMPOSITE_EXIT_REF = """
def int a = 0;
state Root {
    [*] -> Inner;
    Inner -> [*];
    exit abstract teardown;
    state Inner {
        [*] -> Leaf;
        Leaf -> [*];
        exit ref /teardown;
        state Leaf;
    }
}
"""


# `during before` / `during after` written without `>>` belong to the composite
# state itself, so they are recorded before any child leaf is on the stack. The
# `>>` aspect form runs for a descendant leaf's cycle and therefore never
# reaches the fallback -- that difference is why these cases cannot be replaced
# by an aspect model.
def _plain_during_ref(position: str) -> str:
    return (
        """
def int a = 0;
state Root {
    [*] -> Parent;
    Parent -> [*];
    state Library {
        [*] -> LL;
        LL -> [*];
        state LL { during abstract Shared; }
    }
    state Parent {
        [*] -> Leaf;
        Leaf -> [*];
        during %s ref /Library.LL.Shared;
        state Leaf;
    }
}
"""
        % position
    )


# The host is itself a leaf, so the stack has it and the main path returns it.
# Four of the conditions in issue #430 hold here and it still aligns, which is
# why the condition is "no non-pseudo leaf on the stack" and not "enter/exit".
_LEAF_HOST_REF = """
def int a = 0;
state Root {
    [*] -> L;
    L -> [*];
    enter abstract act;
    state L { enter ref /act; }
}
"""

# `>> during before` on two ancestors: recorded while the descendant leaf is on
# the stack, so both sides take the main path and read that leaf.
# `>> during before` on an ancestor: recorded while a descendant leaf is on the
# stack, so both sides take the main path of `_active_leaf_path`.
#
# This case cannot fail if the main path is deleted, and no case can: at the
# moment a block is recorded, the innermost non-pseudo leaf on the stack and the
# host state are the same state, so the two branches never disagree. A witness
# scan over the whole corpus finds `state == active_leaf` on every call (13 of
# 13). The main path is therefore unobservable through the public JSON, and this
# case pins the recorded value, not the branch that produced it.
_ASPECT_DURING_REF = """
def int a = 0;
state Root {
    [*] -> Parent;
    Parent -> [*];
    state Library {
        [*] -> LL;
        LL -> [*];
        state LL { during abstract Shared; }
    }
    state Parent {
        [*] -> Leaf;
        Leaf -> [*];
        >> during before ref /Library.LL.Shared;
        state Leaf;
    }
}
"""

# A composite host with a plain `during before abstract` -- the fallback branch
# again, but no `ref`, so `owner` is never redirected and the fallback value is
# already the host. This is the half of the fallback that was always correct.
_COMPOSITE_DURING_NO_REF = """
def int a = 0;
state Root {
    [*] -> Parent;
    Parent -> [*];
    state Parent {
        [*] -> Leaf;
        Leaf -> [*];
        during before abstract mock;
        state Leaf;
    }
}
"""


def test_composite_host_enter_ref_records_the_host_as_active_leaf() -> None:
    """A `ref` entered on a composite host reports the host, not the declarer."""
    replay, witness_calls, runtime_calls = _replay_call_records(
        _COMPOSITE_ENTER_REF, _TERMINATES
    )

    assert replay.ok is True, [item.to_canonical() for item in replay.mismatches]
    # The first call is the host's `ref`; `Root` is composite, so a witness that
    # said `Root.Inner` here is exactly the defect issue #430 reports.
    assert [call.active_leaf for call in witness_calls] == ["Root", "Root.Inner"]
    assert [call.active_leaf for call in runtime_calls] == ["Root", "Root.Inner"]
    assert [call.state for call in witness_calls] == ["Root", "Root.Inner"]


def test_composite_host_exit_ref_records_the_host_as_active_leaf() -> None:
    """The exit direction reports the host too, with the ref pointing outward."""
    replay, witness_calls, runtime_calls = _replay_call_records(
        _COMPOSITE_EXIT_REF, _TERMINATES
    )

    assert replay.ok is True, [item.to_canonical() for item in replay.mismatches]
    leaves = [call.active_leaf for call in witness_calls]
    assert leaves == [call.active_leaf for call in runtime_calls]
    # `Root.Inner` exits first and refers outward to `/teardown` on `Root`; the
    # recorded path must stay the host `Root.Inner`, never the declarer `Root`.
    assert "Root.Inner" in leaves
    assert all(leaf in {"Root", "Root.Inner"} for leaf in leaves)


@pytest.mark.parametrize("position", ["before", "after"])
def test_plain_during_ref_on_composite_host_records_the_host(position) -> None:
    """A plain `during` ref on a composite host reaches the same fallback."""
    replay, witness_calls, runtime_calls = _replay_call_records(
        _plain_during_ref(position), _TERMINATES
    )

    assert replay.ok is True, [item.to_canonical() for item in replay.mismatches]
    shared = [
        call for call in witness_calls if call.action_name == "Root.Library.LL.Shared"
    ]
    assert shared, [call.action_name for call in witness_calls]
    assert [call.active_leaf for call in shared] == ["Root.Parent"] * len(shared)
    assert [call.role for call in shared] == ["plain_during_%s" % position] * len(
        shared
    )
    assert [call.active_leaf for call in witness_calls] == [
        call.active_leaf for call in runtime_calls
    ]


def test_leaf_host_ref_takes_the_stack_leaf_which_is_the_host() -> None:
    """A cross-state ref whose host is a leaf aligned before the fix too.

    This pins the boundary of the defect: four of the conditions in issue #430
    hold and it still aligned before the fix, because the host is on the stack.
    """
    replay, witness_calls, runtime_calls = _replay_call_records(
        _LEAF_HOST_REF, _TERMINATES
    )

    assert replay.ok is True, [item.to_canonical() for item in replay.mismatches]
    assert [call.active_leaf for call in witness_calls] == ["Root", "Root.L"]
    assert [call.active_leaf for call in runtime_calls] == ["Root", "Root.L"]


def test_aspect_during_ref_takes_the_descendant_leaf() -> None:
    """An aspect ref runs for a leaf's cycle, so both sides read that leaf.

    Pins the recorded value, not the branch: see the note above
    `_ASPECT_DURING_REF` for why no witness-level case can distinguish
    `_active_leaf_path`'s two branches.
    """
    replay, witness_calls, runtime_calls = _replay_call_records(
        _ASPECT_DURING_REF, _TERMINATES
    )

    assert replay.ok is True, [item.to_canonical() for item in replay.mismatches]
    shared = [
        call for call in witness_calls if call.action_name == "Root.Library.LL.Shared"
    ]
    assert shared, [call.action_name for call in witness_calls]
    assert [call.active_leaf for call in shared] == ["Root.Parent.Leaf"] * len(shared)
    assert [call.role for call in shared] == ["aspect_during_before"] * len(shared)
    assert [call.active_leaf for call in witness_calls] == [
        call.active_leaf for call in runtime_calls
    ]


def test_composite_during_without_ref_falls_back_to_its_own_host() -> None:
    """The fallback is only wrong when a `ref` has redirected the owner."""
    replay, witness_calls, runtime_calls = _replay_call_records(
        _COMPOSITE_DURING_NO_REF, _TERMINATES
    )

    assert replay.ok is True, [item.to_canonical() for item in replay.mismatches]
    mock = [call for call in witness_calls if call.action_name == "Root.Parent.mock"]
    assert mock, [call.action_name for call in witness_calls]
    # No `ref`, so `owner` is the host and the fallback value is already right.
    assert [call.active_leaf for call in mock] == ["Root.Parent"] * len(mock)
    assert [call.active_leaf for call in witness_calls] == [
        call.active_leaf for call in runtime_calls
    ]


def test_active_leaf_matches_the_runtime_across_the_sample_corpus() -> None:
    """Every recorded ``active_leaf`` agrees with the runtime, corpus-wide.

    The six cases above pin named shapes. This one pins the field's contract
    over whatever the checked-in corpus happens to contain, so a future path
    that writes some third value -- neither the active leaf nor the host -- is
    caught even if no named case covers its shape.

    The oracle is the replay trace: ``SimulationRuntime`` computes the path from
    the real execution stack, which is the reference semantics the repository
    already treats as authoritative.
    """
    corpus = pathlib.Path(__file__).resolve().parents[1] / "testfile" / "sample_codes"
    sources = sorted(corpus.glob("*.fcstm"))
    assert sources, "the sample corpus should not be empty"

    # `dlc1.fcstm` shifts by a variable amount, which the core lowering does not
    # support. A model that compiles no core carries no witness and so no
    # recorded call to check.
    expected_skips = {"dlc1.fcstm"}
    skipped: list = []
    compared = 0
    checked_models = 0
    for source in sources:
        try:
            model = load_state_machine_from_text(source.read_text(encoding="utf-8"))
            formula = compile_bmc_property(
                build_bmc_core_formula(
                    BmcEngine(model).prepare("check reach <= 3: terminated();")
                )
            )
        except UnsupportedBmcQuery:
            # Only the models known to compile no core are allowed to drop out,
            # and the set is asserted below. Catching the class alone would let
            # any future lowering regression turn this scan into a silent skip:
            # `dlc3.fcstm` contributes a single call, so losing it still clears
            # both floors.
            skipped.append(source.name)
            continue
        result = solve_bmc_property(formula)
        if result.status != "sat":
            continue
        checked_models += 1
        trace = decode_bmc_witness(formula, result.model)
        replay = replay_bmc_witness(model, trace)
        assert replay.ok is True, (
            source.name,
            [item.to_canonical() for item in replay.mismatches],
        )
        for witness_step, runtime_step in zip(trace.steps, replay.runtime_trace.steps):
            assert len(witness_step.abstract_calls) == len(
                runtime_step.abstract_calls
            ), source.name
            for witness_call, runtime_call in zip(
                witness_step.abstract_calls, runtime_step.abstract_calls
            ):
                assert witness_call.active_leaf == runtime_call.active_leaf, (
                    source.name,
                    witness_call.action_name,
                    witness_call.active_leaf,
                    runtime_call.active_leaf,
                )
                # `named_ref` is decided by the same rule and from the same
                # recursion, so it is checked from the same scan. The corpus
                # carries no chain with an anonymous outermost hop, which is why
                # the named cases above exist -- but it does carry named single
                # hops, and this pins those against the runtime.
                assert witness_call.named_ref == runtime_call.named_ref, (
                    source.name,
                    witness_call.action_name,
                    witness_call.named_ref,
                    runtime_call.named_ref,
                )
                compared += 1

    assert set(skipped) == expected_skips, skipped
    assert checked_models >= 4, checked_models
    assert compared >= 10, compared


# A `ref` chain whose outermost hop is anonymous and whose second hop is a named
# `ref`. Only a callsite names its own call, so this call has no named `ref` --
# but the encoder used to scan the chain and let the first named hop win, which
# reported `Root.A.mid` where the runtime reported nothing. See issue #432.
_CHAINED_REF_ANONYMOUS_HEAD = """
state Root {
    [*] -> A;
    A -> [*];
    enter ref A.mid;
    state A {
        enter mid ref act;
        enter abstract act;
    }
}
"""

# The outermost hop is itself named, so both rules agree that it names the call.
_NAMED_REF_SINGLE_HOP = """
def int a = 0;
state Root {
    [*] -> Inner;
    Inner -> [*];
    enter outer ref Inner.act;
    state Inner {
        [*] -> Leaf;
        Leaf -> [*];
        enter abstract act;
        state Leaf;
    }
}
"""

# An anonymous hop straight onto the abstract action: there is no named hop
# anywhere, so both rules report nothing and the chain length is irrelevant.
_ANONYMOUS_REF_SINGLE_HOP = """
def int a = 0;
state Root {
    [*] -> Inner;
    Inner -> [*];
    enter ref Inner.act;
    state Inner {
        [*] -> Leaf;
        Leaf -> [*];
        enter abstract act;
        state Leaf;
    }
}
"""

# Both hops are named. This is the counterexample that shows the trigger is not
# "the chain is longer than one hop": deciding once at the callsite and scanning
# for the first named hop pick the same action here, so the two rules agree and
# the defect stays hidden. Only an anonymous outermost hop separates them.
_CHAINED_REF_NAMED_HEAD = """
def int a = 0;
state Root {
    [*] -> Inner;
    Inner -> [*];
    enter outer ref Inner.mid;
    state Inner {
        [*] -> Leaf;
        Leaf -> [*];
        enter mid ref Deep.act;
        state Deep {
            [*] -> L2;
            L2 -> [*];
            enter abstract act;
            state L2;
        }
        state Leaf;
    }
}
"""


def test_anonymous_head_of_a_ref_chain_reports_no_named_ref() -> None:
    """An anonymous callsite names nothing, whatever the chain passes through.

    This is the defect case. The chain is ``Root.enter`` (anonymous) ->
    ``Root.A.mid`` (named) -> ``Root.A.act``, and the call it produces belongs to
    a callsite that wrote no name. Reporting ``Root.A.mid`` here also collapsed
    two distinct callsites onto one value: the second call below comes from
    ``A``'s own ``enter mid``, which really is named, so a handler could no
    longer tell the two apart.
    """
    replay, witness_calls, runtime_calls = _replay_call_records(
        _CHAINED_REF_ANONYMOUS_HEAD, _TERMINATES
    )
    assert replay.ok is True, [item.to_canonical() for item in replay.mismatches]
    assert [call.named_ref for call in witness_calls] == [
        None,
        "Root.A.mid",
        None,
    ]
    assert [call.named_ref for call in runtime_calls] == [
        None,
        "Root.A.mid",
        None,
    ]
    # The states the three calls run in, so the sequence above cannot be read as
    # three anonymous callsites that happen to line up.
    assert [call.state for call in witness_calls] == ["Root", "Root.A", "Root.A"]


def test_named_head_of_a_single_hop_ref_names_the_call() -> None:
    """A named callsite names its call -- the positive half of the contract."""
    replay, witness_calls, runtime_calls = _replay_call_records(
        _NAMED_REF_SINGLE_HOP, _TERMINATES
    )
    assert replay.ok is True, [item.to_canonical() for item in replay.mismatches]
    assert witness_calls[0].named_ref == "Root.outer"
    assert runtime_calls[0].named_ref == "Root.outer"


def test_anonymous_single_hop_ref_reports_no_named_ref() -> None:
    """No named hop anywhere means no named ``ref`` on either side."""
    replay, witness_calls, runtime_calls = _replay_call_records(
        _ANONYMOUS_REF_SINGLE_HOP, _TERMINATES
    )
    assert replay.ok is True, [item.to_canonical() for item in replay.mismatches]
    assert [call.named_ref for call in witness_calls] == [None, None]
    assert [call.named_ref for call in runtime_calls] == [None, None]


def test_named_head_of_a_ref_chain_keeps_the_callsite_not_the_inner_name() -> None:
    """A named outermost hop wins over a named hop deeper in the chain.

    This pins the direction of the choice. Both rules report ``Root.outer``
    here, which is why this shape cannot expose the defect -- and why the
    trigger needs the outermost hop to be anonymous rather than merely to sit
    above another named hop.
    """
    replay, witness_calls, runtime_calls = _replay_call_records(
        _CHAINED_REF_NAMED_HEAD, _TERMINATES
    )
    assert replay.ok is True, [item.to_canonical() for item in replay.mismatches]
    assert witness_calls[0].named_ref == "Root.outer"
    assert runtime_calls[0].named_ref == "Root.outer"
    assert witness_calls[0].named_ref != "Root.Inner.mid"


def _ref_chain_model(depth: int, head_named: bool, stage: str) -> str:
    """Build a model whose lifecycle action reaches an abstract action by a ``ref`` chain.

    The chain runs ``S0`` -> ``S1`` -> ... -> ``Sdepth``, where ``Sdepth`` declares
    the abstract action and every state above it declares a named ``ref`` pointing
    one level down. Only the outermost hop varies: it is named ``h0`` or left
    anonymous. A ``ref`` target must itself be named -- the model rejects a
    reference to an anonymous action -- so the hops below the outermost one are
    necessarily named, and "the outermost hop is anonymous" is the only way the
    two rules for ``named_ref`` can disagree.

    Entering ``Si`` also executes that state's own hop, so one model yields one
    call per level and the whole ``named_ref`` sequence is observable at once.

    :param depth: Number of ``ref`` hops between the outermost callsite and the
        abstract action.
    :type depth: int
    :param head_named: Whether the outermost hop carries a name.
    :type head_named: bool
    :param stage: Lifecycle stage the chain is declared on, ``'enter'`` or
        ``'exit'``.
    :type stage: str
    :return: FCSTM source text.
    :rtype: str
    """
    names = ["S%d" % index for index in range(depth + 1)]

    def hop(index: int) -> str:
        below = names[index + 1]
        target = (
            "%s.h%d" % (below, index + 1) if index + 1 < depth else "%s.act" % below
        )
        return "%s h%d ref %s;" % (stage, index, target)

    head_target = "%s.h1" % names[1] if depth > 1 else "%s.act" % names[1]
    head = "%s %sref %s;" % (stage, "h0 " if head_named else "", head_target)

    def build(index: int, indent: int) -> list:
        pad = "    " * indent
        if index == depth:
            return [
                "%sstate %s {" % (pad, names[index]),
                "%s    %s abstract act;" % (pad, stage),
                "%s}" % pad,
            ]
        return (
            [
                "%sstate %s {" % (pad, names[index]),
                "%s    [*] -> %s;" % (pad, names[index + 1]),
                "%s    %s -> [*];" % (pad, names[index + 1]),
                "%s    %s" % (pad, head if index == 0 else hop(index)),
            ]
            + build(index + 1, indent + 1)
            + ["%s}" % pad]
        )

    return "def int a = 0;\n" + "\n".join(build(0, 0)) + "\n"


@pytest.mark.parametrize("stage", ["enter", "exit"])
@pytest.mark.parametrize("head_named", [True, False])
@pytest.mark.parametrize("depth", [1, 2, 3, 4, 5, 6, 7, 8])
def test_named_ref_follows_the_callsite_across_ref_chain_depths(
    depth, head_named, stage
) -> None:
    """``named_ref`` answers to the callsite at every chain depth and stage.

    The named cases above pin the shapes by hand; this one sweeps the space the
    hand-written ones sample from, so a rule that happens to be right for a
    two-hop chain but wrong for a four-hop one cannot pass. Restoring the defect
    -- letting the encoder scan the chain for the first named hop -- makes 21 of
    the 40 shapes in this file's two sweeps disagree between the two sides.
    """
    replay, witness_calls, runtime_calls = _replay_call_records(
        _ref_chain_model(depth, head_named, stage),
        "check reach <= %d: terminated();" % (depth + 4),
    )
    assert replay.ok is True, [item.to_canonical() for item in replay.mismatches]
    assert [call.named_ref for call in witness_calls] == [
        call.named_ref for call in runtime_calls
    ]
    # `enter` runs outermost-first and `exit` innermost-first, so the call made by
    # the outermost callsite sits at opposite ends of the sequence.
    outermost = witness_calls[0] if stage == "enter" else witness_calls[-1]
    assert outermost.named_ref == ("S0.h0" if head_named else None)
    assert outermost.state == "S0"


# Chain shapes the depth sweep cannot reach: a global `ref` through the root
# scope, aspect and plain `during` heads, two callsites sharing one chain, several
# chains in one model, a concrete action at the end of one chain beside an
# abstract one, and a named hop referenced both from inside the chain and from
# outside it. Every one of these has a named hop somewhere, so each is a place a
# chain-scanning rule could put that name on the wrong call.
_COMPLEX_REF_CHAINS = {
    "global_ref_through_root_scope": """
def int a = 0;
state Root {
    [*] -> A;
    A -> [*];
    exit gate ref A.mid;
    enter ref /gate;
    state A {
        [*] -> L;
        L -> [*];
        enter mid ref Deep.act;
        state Deep { [*] -> L2; L2 -> [*]; enter abstract act; state L2; }
        state L;
    }
}
""",
    "aspect_during_before_anonymous_head": """
def int a = 0;
state Root {
    [*] -> A;
    A -> [*];
    >> during before ref A.L.mid;
    state A {
        [*] -> L;
        L -> [*];
        state L {
            during mid ref act;
            during abstract act;
        }
    }
}
""",
    "aspect_during_after_named_head": """
def int a = 0;
state Root {
    [*] -> A;
    A -> [*];
    >> during after outer ref A.L.mid;
    state A {
        [*] -> L;
        L -> [*];
        state L {
            during mid ref act;
            during abstract act;
        }
    }
}
""",
    "plain_during_on_composite_host": """
def int a = 0;
state Root {
    [*] -> A;
    A -> [*];
    during before ref A.mid;
    state A {
        [*] -> L;
        L -> [*];
        enter mid ref Deep.act;
        state Deep { [*] -> L2; L2 -> [*]; enter abstract act; state L2; }
        state L;
    }
}
""",
    "two_callsites_share_one_chain": """
def int a = 0;
state Root {
    [*] -> A;
    A -> [*];
    enter ref A.mid;
    exit tail ref A.mid;
    state A {
        [*] -> L;
        L -> [*];
        enter mid ref Deep.act;
        state Deep { [*] -> L2; L2 -> [*]; enter abstract act; state L2; }
        state L;
    }
}
""",
    "several_chains_across_stages": """
def int a = 0;
state Root {
    [*] -> A;
    A -> [*];
    enter ref A.e1;
    exit ex0 ref A.x1;
    state A {
        [*] -> L;
        L -> [*];
        enter e1 ref Deep.eact;
        exit x1 ref Deep.xact;
        state Deep {
            [*] -> L2;
            L2 -> [*];
            enter abstract eact;
            exit abstract xact;
            state L2;
        }
        state L;
    }
}
""",
    "concrete_tail_beside_an_abstract_chain": """
def int a = 0;
state Root {
    [*] -> A;
    A -> [*];
    enter ref A.conc;
    exit ref A.mid;
    state A {
        [*] -> L;
        L -> [*];
        enter conc ref Deep.body;
        exit mid ref Deep.act;
        state Deep {
            [*] -> L2;
            L2 -> [*];
            enter body { a = a + 1; }
            exit abstract act;
            state L2;
        }
        state L;
    }
}
""",
    "named_hop_referenced_from_inside_and_outside": """
def int a = 0;
state Root {
    [*] -> A;
    A -> [*];
    enter ref A.h1;
    exit ref A.B.h2;
    state A {
        [*] -> B;
        B -> [*];
        enter h1 ref B.h2;
        state B {
            [*] -> L;
            L -> [*];
            enter h2 ref L.act;
            state L { enter abstract act; }
        }
    }
}
""",
}


@pytest.mark.parametrize("shape", sorted(_COMPLEX_REF_CHAINS))
def test_named_ref_agrees_with_the_runtime_across_complex_ref_chains(shape) -> None:
    """The two sides agree on ``named_ref`` for chains the depth sweep cannot build.

    The sweep varies one axis at a time on a single straight chain. These models
    vary the surrounding shape instead: the scope a hop is resolved through, the
    kind of action the head is declared as, how many callsites reach one chain,
    and whether a chain ends in an abstract or a concrete action.
    """
    replay, witness_calls, runtime_calls = _replay_call_records(
        _COMPLEX_REF_CHAINS[shape], "check reach <= 6: terminated();"
    )
    assert replay.ok is True, (
        shape,
        [item.to_canonical() for item in replay.mismatches],
    )
    assert [call.named_ref for call in witness_calls] == [
        call.named_ref for call in runtime_calls
    ]
    # Each of these models has at least one named hop, so a rule that reported
    # nothing everywhere would pass the equality above.
    assert any(call.named_ref is not None for call in witness_calls), shape
