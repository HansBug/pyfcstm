"""BMC witness pretty-print presentation tests."""

from __future__ import annotations

import io

import pytest
from hbutils.testing import TextAligner

import pyfcstm.bmc.witness as witness_module
from pyfcstm.bmc import (
    BmcBuildError,
    BmcEngine,
    build_bmc_core_formula,
    compile_bmc_property,
)
from pyfcstm.bmc.witness import (
    BmcEventDecodePolicy,
    BmcReplayMismatch,
    BmcReplayResult,
    BmcRuntimeFrame,
    BmcRuntimeStep,
    BmcRuntimeTrace,
    BmcSolveResult,
    BmcWitnessCallRecord,
    BmcWitnessEvent,
    BmcWitnessFrame,
    BmcWitnessStep,
    BmcWitnessTrace,
)
from pyfcstm.model import load_state_machine_from_text


pytestmark = pytest.mark.unittest
_TEXT = TextAligner().multiple_lines()


def _assert_text_equal(expected: str, actual: str) -> None:
    """Assert full pretty text with line-aligned diagnostics."""
    _TEXT.assert_equal(expected, actual, max_diff=20, max_extra=20)


def _sample_trace() -> BmcWitnessTrace:
    """Build a compact trace that exercises event and call presentation."""
    return BmcWitnessTrace(
        {"kind": "reach", "bound": 2},
        {"status": "sat"},
        {"mode": "cold"},
        (
            BmcWitnessFrame(0, 1, "Root.A", None, False, {"x": 1, "y": 1}),
            BmcWitnessFrame(1, 1, "Root.A", None, False, {"x": 2, "y": 1}),
            BmcWitnessFrame(2, 2, "Root.B", None, False, {"x": 12, "y": 1}),
        ),
        (
            BmcWitnessStep(
                0,
                0,
                1,
                "Root.A::fallback::0",
                "fallback",
                "fallback_gamma",
                "Root.A",
                "Root.A",
                False,
                True,
                (BmcWitnessEvent("Root.tick", "case_positive"),),
                (BmcWitnessEvent("Root.A.go", "negative_case_read", False),),
                (
                    BmcWitnessCallRecord(
                        0,
                        "Root.A.Touch",
                        "during",
                        "leaf_during",
                        "Root.A",
                        "Root.A",
                        snapshot={"x": 2, "y": 1},
                    ),
                    BmcWitnessCallRecord(
                        1,
                        "Root.Shared",
                        "during",
                        "leaf_during",
                        "Root.A",
                        "Root.A",
                        snapshot={"x": 2, "y": 1},
                    ),
                    BmcWitnessCallRecord(
                        2,
                        "Root.Shared",
                        "during",
                        "leaf_during",
                        "Root.A",
                        "Root.A",
                        snapshot={"x": 2, "y": 1},
                    ),
                ),
            ),
            BmcWitnessStep(
                1,
                1,
                2,
                "Root.A::transition::Root.B::1",
                "transition",
                "transition",
                "Root.A",
                "Root.B",
                False,
                False,
                (
                    BmcWitnessEvent("Root.A.go", "explicit_true_assumption"),
                    BmcWitnessEvent("Root.B.ready", "property_support"),
                ),
                (),
                (
                    BmcWitnessCallRecord(
                        0,
                        "Root.A.ExitHook",
                        "exit",
                        "state_exit",
                        "Root.A",
                        "Root.A",
                    ),
                    BmcWitnessCallRecord(
                        1,
                        "Root.B.EnterHook",
                        "enter",
                        "state_enter",
                        "Root.B",
                        "Root.B",
                    ),
                ),
            ),
        ),
    )


def _event_priority_trace() -> BmcWitnessTrace:
    """Build a canonical event trace with replay provenance and debug reads."""
    return BmcWitnessTrace(
        {"kind": "reach", "bound": 1},
        {"status": "sat"},
        {"mode": "cold"},
        (
            BmcWitnessFrame(0, 1, "Root.A", None, False, {}),
            BmcWitnessFrame(1, 1, "Root.A", None, False, {}),
        ),
        (
            BmcWitnessStep(
                0,
                0,
                1,
                "case",
                "fallback",
                "fallback_gamma",
                "Root.A",
                "Root.A",
                False,
                True,
                (
                    BmcWitnessEvent("Root.dup", "explicit_true_assumption"),
                    BmcWitnessEvent("Root.prop", "property_support"),
                ),
                (BmcWitnessEvent("Root.false", "explicit_false_assumption", False),),
                (),
            ),
        ),
    )


def _edge_trace() -> BmcWitnessTrace:
    """Build a trace covering sentinel and sparse edge presentation."""
    return BmcWitnessTrace(
        {"kind": "reach"},
        {"status": "sat"},
        {"mode": "hot"},
        (
            BmcWitnessFrame(0, None, None, "init", False, {}),
            BmcWitnessFrame(1, None, None, None, False, {}),
            BmcWitnessFrame(
                2, 3, "Root.C", None, True, {"count": 1, "ratio": 0.5, "score": 2}
            ),
        ),
        (
            BmcWitnessStep(
                0,
                0,
                2,
                "delta-case",
                "delta",
                "delta",
                "init",
                "Root.C",
                True,
                False,
                (),
                (),
                (
                    BmcWitnessCallRecord(
                        0,
                        "Root.C.Named",
                        "enter",
                        "state_enter",
                        "Root.C",
                        "Root.C",
                        named_ref="Root.Ref",
                        snapshot={"count": 1, "ratio": 0.5, "score": 2},
                    ),
                ),
            ),
        ),
    )


def _sample_formula():
    """Compile a tiny property formula for solve-result presentation tests."""
    state_machine = load_state_machine_from_text("state Root;")
    context = BmcEngine(state_machine).prepare('check reach <= 1: active("Root");')
    return compile_bmc_property(build_bmc_core_formula(context))


def test_witness_trace_default_output_is_single_frame_table() -> None:
    """Witness traces print as one frame-indexed table with clean events."""
    expected = """
    BmcWitnessTrace[reach<=2, sat] frames=3 steps=2

    frame    via                state    progress        [x]    [y]    events              calls                extra
    -------  -----------------  -------  --------------  -----  -----  ------------------  -------------------  -------
    0        -                  Root.A   initial         1      1      -                   -                    I
    1        Root.A --> Root.A  Root.A   fallback_gamma  2      1      Root.tick           Root.A.Touch(1)      GR
                                                                                           Root.Shared(2)
    2        Root.A --> Root.B  Root.B   transition      12     1      Root.A.go[assume]   Root.A.ExitHook(1)   -
                                                                       Root.B.ready[prop]  Root.B.EnterHook(1)

    extra: I=initial D=delta G=gamma T=terminated N=rows truncated V=vars hidden E=events truncated C=calls truncated W=cell width truncated P=full path unavailable R=hidden event reads
    """
    trace = _sample_trace()
    buffer = io.StringIO()
    trace.pretty_print(file=buffer, end="")

    _assert_text_equal(expected, buffer.getvalue())
    _assert_text_equal(expected, trace.to_text())
    _assert_text_equal(expected, str(trace))


def test_witness_trace_expanded_calls_keep_one_calls_column() -> None:
    """Expanded calls stay in one cell and avoid ``vars=`` or subcolumns."""
    expected = """
    BmcWitnessTrace[reach<=2, sat] frames=3 steps=2

    frame    via                state    progress        [x]    [y]    events              calls                                 extra
    -------  -----------------  -------  --------------  -----  -----  ------------------  ------------------------------------  -------
    0        -                  Root.A   initial         1      1      -                   -                                     I
    1        Root.A --> Root.A  Root.A   fallback_gamma  2      1      Root.tick           Root.A.Touch{state=Root.A, x=2, y=1}  GR
                                                                                           Root.Shared{state=Root.A, x=2, y=1}
                                                                                           Root.Shared{state=Root.A, x=2, y=1}
    2        Root.A --> Root.B  Root.B   transition      12     1      Root.A.go[assume]   Root.A.ExitHook{state=Root.A}         -
                                                                       Root.B.ready[prop]  Root.B.EnterHook{state=Root.B}
    """
    text = _sample_trace().to_text(calls_mode="expanded", show_legend=False)

    _assert_text_equal(expected, text)


def test_witness_trace_event_modes_and_canonical_reasons_are_stable() -> None:
    """Event tags follow canonical replay provenance and debug-read rules."""
    trace = _event_priority_trace()
    expected_default = """
    BmcWitnessTrace[reach<=1, sat] frames=2 steps=1

    frame    via                state    progress        events            calls    extra
    -------  -----------------  -------  --------------  ----------------  -------  -------
    0        -                  Root.A   initial         -                 -        I
    1        Root.A --> Root.A  Root.A   fallback_gamma  Root.dup[assume]  -        GR
                                                         Root.prop[prop]
    """
    expected_debug = """
    BmcWitnessTrace[reach<=1, sat] frames=2 steps=1

    frame    via                state    progress        events                    calls    extra
    -------  -----------------  -------  --------------  ------------------------  -------  -------
    0        -                  Root.A   initial         -                         -        I
    1        Root.A --> Root.A  Root.A   fallback_gamma  Root.dup                  -        G
                                                         Root.prop
                                                         Root.false[assume=false]
    """

    _assert_text_equal(expected_default, trace.to_text(show_legend=False))
    _assert_text_equal(
        expected_debug,
        trace.to_text(events_mode="all", event_reason="never", show_legend=False),
    )


def test_witness_trace_full_via_falls_back_without_reexpanding() -> None:
    """Full via mode marks unavailable path metadata instead of expanding."""
    expected = """
    BmcWitnessTrace[reach<=2, sat] frames=3 steps=2

    frame    via                state    progress        [x]    [y]    events              calls                extra
    -------  -----------------  -------  --------------  -----  -----  ------------------  -------------------  -------
    0        -                  Root.A   initial         1      1      -                   -                    I
    1        Root.A --> Root.A  Root.A   fallback_gamma  2      1      Root.tick           Root.A.Touch(1)      GPR
                                                                                           Root.Shared(2)
    2        Root.A --> Root.B  Root.B   transition      12     1      Root.A.go[assume]   Root.A.ExitHook(1)   P
                                                                       Root.B.ready[prop]  Root.B.EnterHook(1)
    """
    _assert_text_equal(
        expected, _sample_trace().to_text(via_mode="full", show_legend=False)
    )


def test_witness_trace_verbose_mode_pins_audit_columns_and_full_calls() -> None:
    """Verbose mode force-enables audit columns and full call details."""
    expected = """
    BmcWitnessTrace[reach<=2, sat] frames=3 steps=2

    frame    step    source_frame    target_frame    case_kind    case                           via                state    progress        [x]    [y]    events                 calls                                                                                extra
    -------  ------  --------------  --------------  -----------  -----------------------------  -----------------  -------  --------------  -----  -----  ---------------------  -----------------------------------------------------------------------------------  -------
    0        -       -               -               -            -                              -                  Root.A   initial         1      1      -                      -                                                                                    I
    1        0       0               1               fallback     Root.A::fallback::0            Root.A --> Root.A  Root.A   fallback_gamma  2      1      Root.tick[case]        Root.A.Touch{stage=during, role=leaf_during, state=Root.A, active=Root.A, x=2, y=1}  GP
                                                                                                                                                           Root.A.go[read=false]  Root.Shared{stage=during, role=leaf_during, state=Root.A, active=Root.A, x=2, y=1}
                                                                                                                                                                                  Root.Shared{stage=during, role=leaf_during, state=Root.A, active=Root.A, x=2, y=1}
    2        1       1               2               transition   Root.A::transition::Root.B::1  Root.A --> Root.B  Root.B   transition      12     1      Root.A.go[assume]      Root.A.ExitHook{stage=exit, role=state_exit, state=Root.A, active=Root.A}            P
                                                                                                                                                           Root.B.ready[prop]     Root.B.EnterHook{stage=enter, role=state_enter, state=Root.B, active=Root.B}

    extra: I=initial D=delta G=gamma T=terminated N=rows truncated V=vars hidden E=events truncated C=calls truncated W=cell width truncated P=full path unavailable R=hidden event reads
    """

    _assert_text_equal(
        expected,
        _sample_trace().to_text(
            verbose=True,
            events_mode="input",
            calls_mode="summary",
            max_cell_width=None,
            show_legend=False,
        ),
    )


def test_witness_trace_short_call_paths_are_golden_pinned() -> None:
    """Short call paths alter display names without changing one-table shape."""
    expected = """
    BmcWitnessTrace[reach<=2, sat] frames=3 steps=2

    frame    via                state    progress        [x]    [y]    events              calls         extra
    -------  -----------------  -------  --------------  -----  -----  ------------------  ------------  -------
    0        -                  Root.A   initial         1      1      -                   -             I
    1        Root.A --> Root.A  Root.A   fallback_gamma  2      1      Root.tick           Touch(1)      GR
                                                                                           Shared(2)
    2        Root.A --> Root.B  Root.B   transition      12     1      Root.A.go[assume]   ExitHook(1)   -
                                                                       Root.B.ready[prop]  EnterHook(1)
    """

    _assert_text_equal(
        expected,
        _sample_trace().to_text(
            call_path="short", vars_order="alpha", show_legend=False
        ),
    )


def test_witness_trace_can_hide_events_and_calls_by_option() -> None:
    """Event and call columns have a fully pinned hidden-output mode."""
    expected = """
    BmcWitnessTrace[reach<=2, sat] frames=3 steps=2

    frame    via                state    progress        [x]    [y]    events    calls    extra
    -------  -----------------  -------  --------------  -----  -----  --------  -------  -------
    0        -                  Root.A   initial         1      1      -         -        I
    1        Root.A --> Root.A  Root.A   fallback_gamma  2      1      -         -        G
    2        Root.A --> Root.B  Root.B   transition      12     1      -         -        -
    """

    _assert_text_equal(
        expected,
        _sample_trace().to_text(
            events_mode="none", calls_mode="none", show_legend=False
        ),
    )


def test_witness_trace_edge_rows_and_full_call_details_are_golden_pinned() -> None:
    """Sentinels, no-step frames, finite values, and named refs are pinned."""
    expected = """
    BmcWitnessTrace[reach, sat] frames=3 steps=1

    frame    step    source_frame    target_frame    case_kind    case        via              state    progress    [count]    [ratio]    [score]    events    calls                                                                                                                      extra
    -------  ------  --------------  --------------  -----------  ----------  ---------------  -------  ----------  ---------  ---------  ---------  --------  -------------------------------------------------------------------------------------------------------------------------  -------
    0        -       -               -               -            -           -                init     initial     -          -          -          -         -                                                                                                                          I
    1        -       -               -               -            -           -                -        frame       -          -          -          -         -                                                                                                                          -
    2        0       0               2               delta        delta-case  init --> Root.C  Root.C   delta       1          0.5        2          -         Root.C.Named{stage=enter, role=state_enter, state=Root.C, active=Root.C, named_ref=Root.Ref, count=1, ratio=0.5, score=2}  DTP

    extra: I=initial D=delta G=gamma T=terminated N=rows truncated V=vars hidden E=events truncated C=calls truncated W=cell width truncated P=full path unavailable R=hidden event reads
    """

    _assert_text_equal(
        expected,
        _edge_trace().to_text(verbose=True, max_cell_width=None, show_legend=False),
    )


def test_witness_trace_edge_width_and_empty_event_cells_are_golden_pinned() -> None:
    """Width-one truncation and empty event cells have exact output contracts."""
    expected_width = """
    BmcWitnessTrace[reach, sat] frames=3 steps=1

    frame    via    state    progress    [count]    [ratio]    [score]    events    calls    extra
    -------  -----  -------  ----------  ---------  ---------  ---------  --------  -------  -------
    0        -      …        initial     -          -          -          -         -        IW
    1        -      -        frame       -          -          -          -         -        -
    2        …      …        …           1          …          2          -         …        DTW
    """
    expected_empty_events = """
    BmcWitnessTrace[reach, sat] frames=3 steps=1

    frame    via              state    progress    [count]    [ratio]    [score]    events    calls            extra
    -------  ---------------  -------  ----------  ---------  ---------  ---------  --------  ---------------  -------
    0        -                init     initial     -          -          -          -         -                I
    1        -                -        frame       -          -          -          -         -                -
    2        init --> Root.C  Root.C   delta       1          0.5        2          -         Root.C.Named(1)  DT
    """

    _assert_text_equal(
        expected_width, _edge_trace().to_text(max_cell_width=1, show_legend=False)
    )
    _assert_text_equal(
        expected_empty_events,
        _edge_trace().to_text(events_mode="all", show_legend=False),
    )


def test_single_object_edge_outputs_are_field_value_golden_pinned() -> None:
    """Non-trace pretty objects also have exact field/value contracts."""
    expected_runtime = """
    BmcRuntimeTrace frames=1 steps=0

    frame    via    state    progress    events    calls    extra
    -------  -----  -------  ----------  --------  -------  -------
    0        -      -        initial     -         -        I
    """
    expected_policy = """
    BmcEventDecodePolicy
    field                     value
    include_debug_reads       true
    include_property_support  true
    """
    expected_mismatch = """
    BmcReplayMismatch
    field      value
    path       p
    expected   -
    actual     -
    message    m
    tolerance  -
    """

    _assert_text_equal(
        expected_runtime,
        BmcRuntimeTrace((BmcRuntimeFrame(0, None, False, {}),), ()).to_text(
            show_legend=False
        ),
    )
    _assert_text_equal(
        expected_policy, BmcEventDecodePolicy().to_text(tablefmt="plain")
    )
    _assert_text_equal(
        expected_mismatch,
        BmcReplayMismatch("p", None, [], "m", None).to_text(tablefmt="plain"),
    )


def test_runtime_trace_debug_options_are_golden_pinned() -> None:
    """Runtime trace show_ids, legend, alpha vars, and hidden vars are pinned."""
    expected = """
    BmcRuntimeTrace frames=2 steps=0

    frame    step    via    state    progress       [a]    events    calls    extra
    -------  ------  -----  -------  -------------  -----  --------  -------  -------
    0        -       -      A        initial        2      -         -        IV
    2        -       -      -        runtime_frame  4      -         -        V

    extra: I=initial D=delta G=gamma T=terminated N=rows truncated V=vars hidden E=events truncated C=calls truncated W=cell width truncated P=full path unavailable R=hidden event reads
    """
    trace = BmcRuntimeTrace(
        (
            BmcRuntimeFrame(0, "A", False, {"z": 1, "a": 2}),
            BmcRuntimeFrame(2, None, False, {"z": 3, "a": 4}),
        ),
        (),
    )

    _assert_text_equal(
        expected,
        trace.to_text(show_ids=True, max_var_columns=1, vars_order="alpha"),
    )


def test_runtime_trace_blank_step_via_is_golden_pinned() -> None:
    """Runtime rows with no visible source or target keep a plain dash via."""
    expected = """
    BmcRuntimeTrace frames=2 steps=1

    frame    via    state    progress      events    calls    extra
    -------  -----  -------  ------------  --------  -------  -------
    0        -      -        initial       -         -        I
    1        -      -        runtime_step  -         -        -
    """
    trace = BmcRuntimeTrace(
        (
            BmcRuntimeFrame(0, None, False, {}),
            BmcRuntimeFrame(1, None, False, {}),
        ),
        (BmcRuntimeStep(0, (), (), (), ()),),
    )

    _assert_text_equal(expected, trace.to_text(show_legend=False))


def test_public_non_trace_objects_are_field_value_golden_pinned() -> None:
    """Every public witness/replay record type has exact standalone output."""
    expected_solve = """
    BmcSolveResult
    field                  value
    schema_version         bmc-solve-result/v2
    kind                   reach
    polarity               witness
    status                 unknown
    property_satisfied     -
    witness_found          false
    counterexample_found   false
    incomplete             true
    outcome                unknown
    reason                 because
    elapsed_ms             1.25
    timeout_ms             10
    has_model              false
    incomplete_status      -
    incomplete_reason      -
    incomplete_elapsed_ms  -
    has_incomplete_model   false
    total_elapsed_ms       1.25
    feasibility            assumptions=elapsed_ms=-, origin=not_checked, reason=-, status=-, infeasible_stage=-, initialization=elapsed_ms=-, origin=not_checked, reason=-, status=-, kernel=elapsed_ms=-, origin=not_checked, reason=-, status=-, localization_status=not_checked, refinement_checks=-, refinement_reason=-, refinement_status=not_needed
    available_model_roles  -
    diagnostics            diag
    """
    expected_event = """
    BmcWitnessEvent
    field        value
    path         Root.Go
    reason       property_support
    model_value  true
    """
    expected_frame = """
    BmcWitnessFrame
    field       value
    index       0
    state_id    -
    state       -
    sentinel    init
    terminated  false
    vars        -
    """
    expected_step = """
    BmcWitnessStep
    field              value
    index              0
    source_frame       0
    target_frame       1
    case_label         case
    case_kind          fallback
    progress           fallback_gamma
    source_state       Root.A
    target_state       Root.A
    delta              false
    gamma              true
    input_events       -
    event_reads        -
    abstract_calls     -
    consumed_events    -
    unconsumed_events  -
    """
    expected_runtime_frame = """
    BmcRuntimeFrame
    field       value
    index       0
    state       -
    terminated  true
    vars        -
    """
    expected_runtime_step = """
        BmcRuntimeStep
        field              value
        index              0
        input_events       A
        consumed_events    A
        unconsumed_events  -
        abstract_calls     -
        delta              false
    """

    _assert_text_equal(
        expected_solve,
        BmcSolveResult(
            _sample_formula(),
            "unknown",
            reason="because",
            elapsed_ms=1.25,
            timeout_ms=10,
            diagnostics=("diag",),
        ).to_text(tablefmt="plain"),
    )
    _assert_text_equal(
        expected_event,
        BmcWitnessEvent("Root.Go", "property_support").to_text(tablefmt="plain"),
    )
    _assert_text_equal(
        expected_frame,
        BmcWitnessFrame(0, None, None, "init", False, {}).to_text(tablefmt="plain"),
    )
    _assert_text_equal(
        expected_step,
        BmcWitnessStep(
            0,
            0,
            1,
            "case",
            "fallback",
            "fallback_gamma",
            "Root.A",
            "Root.A",
            False,
            True,
        ).to_text(tablefmt="plain"),
    )
    _assert_text_equal(
        expected_runtime_frame,
        BmcRuntimeFrame(0, None, True, {}).to_text(tablefmt="plain"),
    )
    _assert_text_equal(
        expected_runtime_step,
        BmcRuntimeStep(0, ("A",), ("A",), (), ()).to_text(tablefmt="plain"),
    )


def test_pretty_print_default_stdout_and_invalid_end_are_pinned(capsys) -> None:
    """Direct pretty printing uses stdout by default and validates ``end``."""
    expected = """
    BmcWitnessEvent
    field        value
    -----------  -------------
    path         Root.Go
    reason       case_positive
    model_value  true
    """

    BmcWitnessEvent("Root.Go", "case_positive").pretty_print()

    _assert_text_equal(expected, capsys.readouterr().out)
    with pytest.raises(BmcBuildError, match="end"):
        BmcWitnessEvent("Root.Go", "case_positive").pretty_print(end=1)


def test_runtime_trace_uses_same_single_table_shape() -> None:
    """Runtime replay traces share the frame-indexed table formatter."""
    expected = """
    BmcRuntimeTrace frames=4 steps=3

    frame    via                    state       progress      [x]    events                  calls            extra
    -------  ---------------------  ----------  ------------  -----  ----------------------  ---------------  -------
    0        -                      Root.A      initial       1      -                       -                I
    1        Root.A --> Root.A      Root.A      runtime_step  2      Root.tick               Root.A.Touch(1)  R
                                                                     Root.noise[unconsumed]
    2        Root.A --> terminated  terminated  runtime_step  2      -                       -                T
    3        -                      terminated  runtime_step  2      -                       -                T
    """
    trace = BmcRuntimeTrace(
        (
            BmcRuntimeFrame(0, "Root.A", False, {"x": 1}),
            BmcRuntimeFrame(1, "Root.A", False, {"x": 2}),
            BmcRuntimeFrame(2, None, True, {"x": 2}),
            BmcRuntimeFrame(3, None, True, {"x": 2}),
        ),
        (
            BmcRuntimeStep(
                0,
                ("Root.tick", "Root.noise"),
                ("Root.tick",),
                ("Root.noise",),
                (
                    BmcWitnessCallRecord(
                        0,
                        "Root.A.Touch",
                        "during",
                        "leaf_during",
                        "Root.A",
                        "Root.A",
                        snapshot={"x": 2},
                    ),
                ),
            ),
            BmcRuntimeStep(1, (), (), (), ()),
            BmcRuntimeStep(2, (), (), (), ()),
        ),
    )

    _assert_text_equal(expected, trace.to_text(show_legend=False))


def test_replay_result_prints_mismatch_summary_after_trace() -> None:
    """Replay mismatch text fixes witness-expected before runtime-actual."""
    expected = """
    BmcReplayResult[mismatch] mismatches=1

    BmcRuntimeTrace frames=1 steps=0

    frame    via    state    progress    [x]    events    calls    extra
    -------  -----  -------  ----------  -----  --------  -------  -------
    0        -      Root.A   initial     1      -         -        I

    MISMATCH frames[2].vars.x: 11 != 12
    """
    witness = _sample_trace()
    runtime = BmcRuntimeTrace((BmcRuntimeFrame(0, "Root.A", False, {"x": 1}),), ())
    result = BmcReplayResult(
        witness,
        runtime,
        (BmcReplayMismatch("frames[2].vars.x", 11, 12, "value mismatch"),),
    )

    _assert_text_equal(expected, result.to_text(show_legend=False))


def test_single_call_record_prints_field_value_table() -> None:
    """Single call records use a Series-like field/value table."""
    expected = """
    BmcWitnessCallRecord
    field        value
    ordinal      0
    action_name  Root.A.Touch
    stage        during
    role         leaf_during
    state        Root.A
    active_leaf  Root.A
    named_ref    -
    snapshot     x=1, y=1
    """
    record = BmcWitnessCallRecord(
        0,
        "Root.A.Touch",
        "during",
        "leaf_during",
        "Root.A",
        "Root.A",
        snapshot={"x": 1, "y": 1},
    )

    _assert_text_equal(expected, record.to_text(tablefmt="plain"))


def test_github_tablefmt_uses_br_for_multiline_cells() -> None:
    """Markdown table output keeps multiline cells inside one table row."""
    expected = """
    BmcWitnessTrace[reach<=2, sat] frames=3 steps=2

    | frame   | via               | state   | progress       | [x]   | [y]   | events                                  | calls                                     | extra   |
    |---------|-------------------|---------|----------------|-------|-------|-----------------------------------------|-------------------------------------------|---------|
    | 0       | -                 | Root.A  | initial        | 1     | 1     | -                                       | -                                         | I       |
    | 1       | Root.A --> Root.A | Root.A  | fallback_gamma | 2     | 1     | Root.tick                               | Root.A.Touch(1)<br>Root.Shared(2)         | GR      |
    | 2       | Root.A --> Root.B | Root.B  | transition     | 12    | 1     | Root.A.go[assume]<br>Root.B.ready[prop] | Root.A.ExitHook(1)<br>Root.B.EnterHook(1) | -       |
    """
    _assert_text_equal(
        expected, _sample_trace().to_text(tablefmt="github", show_legend=False)
    )


def test_pretty_print_truncation_and_text_validation_are_explicit(monkeypatch) -> None:
    """Presentation truncation markers and invalid text kwargs are pinned."""
    trace = _sample_trace()
    expected_rows = """
    BmcWitnessTrace[reach<=2, sat] frames=3 steps=2

    frame    via                state    progress          [x]    [y]    events     calls            extra
    -------  -----------------  -------  ----------------  -----  -----  ---------  ---------------  -------
    0        -                  Root.A   initial           1      1      -          -                I
    1        Root.A --> Root.A  Root.A   fallback_gamma    2      1      Root.tick  Root.A.Touch(1)  GR
                                                                                    Root.Shared(2)
    …        -                  -        … (+1 more rows)  -      -      -          -                N
    """
    expected_str_rows = """
    BmcWitnessTrace[reach<=2, sat] frames=3 steps=2

    frame    via                state    progress          [x]    [y]    events     calls            extra
    -------  -----------------  -------  ----------------  -----  -----  ---------  ---------------  -------
    0        -                  Root.A   initial           1      1      -          -                I
    1        Root.A --> Root.A  Root.A   fallback_gamma    2      1      Root.tick  Root.A.Touch(1)  GR
                                                                                    Root.Shared(2)
    …        -                  -        … (+1 more rows)  -      -      -          -                N

    extra: I=initial D=delta G=gamma T=terminated N=rows truncated V=vars hidden E=events truncated C=calls truncated W=cell width truncated P=full path unavailable R=hidden event reads
    """
    expected_items = """
    BmcWitnessTrace[reach<=2, sat] frames=3 steps=2

    frame    via                state    progress        [x]    events             calls               extra
    -------  -----------------  -------  --------------  -----  -----------------  ------------------  -------
    0        -                  Root.A   initial         1      -                  -                   IV
    1        Root.A --> Root.A  Root.A   fallback_gamma  2      Root.tick          Root.A.Touch(1)     GVCR
                                                                                   … (+1 more)
    2        Root.A --> Root.B  Root.B   transition      12     Root.A.go[assume]  Root.A.ExitHook(1)  VEC
                                                                … (+1 more)        … (+1 more)
    """
    expected_width = """
    BmcWitnessTrace[reach<=2, sat] frames=3 steps=2

    frame    via         state    progress    [x]    [y]    events      calls       extra
    -------  ----------  -------  ----------  -----  -----  ----------  ----------  -------
    0        -           Root.A   initial     1      1      -           -           I
    1        Root.A --…  Root.A   fallback_…  2      1      Root.tick   Root.A.To…  GWR
                                                                        Root.Shar…
    2        Root.A --…  Root.B   transition  12     1      Root.A.go…  Root.A.Ex…  W
                                                            Root.B.re…  Root.B.En…
    """

    _assert_text_equal(expected_rows, trace.to_text(max_rows=2, show_legend=False))
    monkeypatch.setattr(witness_module, "_PRETTY_STR_MAX_ROWS", 2)
    _assert_text_equal(expected_str_rows, str(trace))
    _assert_text_equal(
        expected_items,
        trace.to_text(
            max_events=1,
            max_call_groups=1,
            max_var_columns=1,
            show_legend=False,
        ),
    )
    _assert_text_equal(
        expected_width, trace.to_text(max_cell_width=10, show_legend=False)
    )
    with pytest.raises(BmcBuildError, match="file or end"):
        trace.to_text(file=io.StringIO())


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"tablefmt": ""}, "tablefmt"),
        ({"tablefmt": "not_a_tabulate_format"}, "tablefmt"),
        ({"verbose": "yes"}, "verbose"),
        ({"show_case": 1}, "show_case"),
        ({"show_ids": 1}, "show_ids"),
        ({"show_legend": 1}, "show_legend"),
        ({"max_rows": -1}, "max_rows"),
        ({"max_events": True}, "max_events"),
        ({"max_call_groups": -1}, "max_call_groups"),
        ({"max_cell_width": 0}, "max_cell_width"),
        ({"max_var_columns": -1}, "max_var_columns"),
        ({"vars_order": "locale"}, "vars_order"),
        ({"events_mode": "debug"}, "events_mode"),
        ({"event_reason": "sometimes"}, "event_reason"),
        ({"calls_mode": "table"}, "calls_mode"),
        ({"call_path": "middle"}, "call_path"),
        ({"call_details": "minimal"}, "call_details"),
        ({"via_mode": "tree"}, "via_mode"),
        ({"end": 1}, "end"),
    ],
)
def test_pretty_print_rejects_invalid_public_options(kwargs, message) -> None:
    """Public pretty-print options fail loudly before emitting loose output."""
    with pytest.raises(BmcBuildError, match=message):
        _sample_trace().to_text(**kwargs)
