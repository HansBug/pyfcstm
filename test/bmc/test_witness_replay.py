"""BMC witness replay tests."""

from __future__ import annotations

from dataclasses import replace

import pytest
from hbutils.testing import TextAligner

from pyfcstm.bmc import (
    BmcBuildError,
    BmcEngine,
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
    assert [item.path for item in replay.mismatches] == ["frames[1].vars.x"]
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
    assert [item.path for item in replay.mismatches] == ["frames[1].vars.x"]
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

    assert [mismatch.path for mismatch in result.mismatches] == ["frames[1].state"]


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
    assert [item.path for item in mismatches] == ["steps[0].delta"]


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
    assert [item.path for item in replay.mismatches] == [
        "frames",
        "frames[1].index",
        "steps[0].index",
        "steps[0].source_frame",
        "steps[0].target_frame",
        "steps[1].index",
        "steps[1].source_frame",
        "steps[1].target_frame",
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
