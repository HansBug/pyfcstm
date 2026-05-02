"""
Public API for SysDeSim conversion helpers.

This package exposes the phase0-6 conversion pipeline for the subset of
SysDeSim UML state machines that can be mapped directly into FCSTM. The public
surface is intentionally small:

* :func:`load_sysdesim_xml` and :func:`load_sysdesim_machine` load the XML/XMI
  source into the dataclass IR.
* :func:`load_sysdesim_raw_xmi` and :func:`summarize_sysdesim_raw_xmi` expose a
  reusable raw XMI index and structure summary for timeline-oriented import
  work.
* :func:`normalize_machine` prepares names, variables, and guard expressions
  for FCSTM export.
* :func:`prepare_sysdesim_output_machines` normalizes one SysDeSim machine into
  one main-machine output plus any required region-level split views.
* :func:`build_machine_ast`, :func:`emit_program`,
  :func:`convert_sysdesim_xml_to_ast`, and
  :func:`convert_sysdesim_xml_to_dsl` produce single-output FCSTM results when
  the selected machine does not split.
* :func:`convert_sysdesim_xml_to_asts` and
  :func:`convert_sysdesim_xml_to_dsls` produce multi-output FCSTM results for
  parallel-split machines.
* :func:`make_internal_name` provides deterministic reserved names for
  converter-generated artifacts.
* :func:`validate_program_roundtrip` verifies that emitted DSL can be parsed
  back through the existing parser/model stack.
* :func:`build_sysdesim_conversion_report` produces a structured phase6
  diagnostics report for CLI and regression use.
* :func:`extract_sysdesim_interactions` and
  :func:`build_sysdesim_phase56_report` expose the current timeline-oriented
  Phase5/6 intermediate extraction layer.
* :func:`build_sysdesim_phase78_report` exposes the current timeline-first
  import IR for machine graph, input/event bindings, and ordered step
  candidates.
* :func:`build_sysdesim_timeline_plantuml` and
  :func:`build_sysdesim_timeline_plantuml_from_xml` expose the current
  review-oriented Phase12 timeline visualization export.

Internals are kept in six files to avoid unnecessary fragmentation:

- ``ir.py`` for the dataclass IR
- ``xmi.py`` for the raw XML/XMI index layer
- ``timeline.py`` for interaction extraction and unified trigger reporting
- ``timeline_plantuml.py`` for Phase12 review-oriented PlantUML export
- ``convert.py`` for loading, normalization, AST building, and validation
- ``__init__.py`` for the stable public surface

Example::

    >>> from pyfcstm.convert.sysdesim import load_sysdesim_machine, normalize_machine
    >>> machine = load_sysdesim_machine("sample.sysdesim.xml")
    >>> normalize_machine(machine)
    IrMachine(...)
"""

from __future__ import annotations

from .convert import (
    SysDeSimConversionReport,
    SysDeSimOutputValidationReport,
    SysDeSimPreparedMachine,
    build_machine_ast,
    build_sysdesim_conversion_report,
    convert_sysdesim_xml_to_ast,
    convert_sysdesim_xml_to_asts,
    convert_sysdesim_xml_to_dsl,
    convert_sysdesim_xml_to_dsls,
    emit_program,
    load_sysdesim_machine,
    load_sysdesim_xml,
    make_internal_name,
    normalize_machine,
    prepare_sysdesim_output_machines,
    validate_program_roundtrip,
)
from .xmi import (
    SysDeSimRawXmiDocument,
    SysDeSimRawXmiSummary,
    load_sysdesim_raw_xmi,
    summarize_sysdesim_raw_xmi,
)
from .timeline import (
    SysDeSimActivityAssignmentObservation,
    SysDeSimDurationConstraintObservation,
    SysDeSimInteractionExtract,
    SysDeSimMessageObservation,
    SysDeSimNameBindingHint,
    SysDeSimPhase56Report,
    SysDeSimPhase78Report,
    SysDeSimStateInvariantObservation,
    SysDeSimTimeConstraintObservation,
    SysDeSimTimelineDurationConstraint,
    SysDeSimTimelineEmitAction,
    SysDeSimTimelineEventCandidate,
    SysDeSimTimelineInputCandidate,
    SysDeSimTimelineLifeline,
    SysDeSimTimelineMachineTransition,
    SysDeSimTimelineSetInputAction,
    SysDeSimTimelineStepCandidate,
    SysDeSimTimelineStepTimeWindow,
    SysDeSimTimelineTransitionView,
    SysDeSimTriggerCondition,
    SysDeSimTriggerNone,
    SysDeSimTriggerSignal,
    build_sysdesim_phase56_report,
    build_sysdesim_phase78_report,
    extract_sysdesim_interactions,
)
from .timeline_verify import (
    SysDeSimNormalizedTemporalConstraint,
    SysDeSimPhase10Report,
    SysDeSimPhase9Output,
    SysDeSimPhase9Report,
    SysDeSimStateCoexistenceConstraintPreview,
    SysDeSimStateCoexistenceResult,
    SysDeSimStateCoexistenceTimelinePoint,
    SysDeSimStateCoexistenceTimelineReport,
    SysDeSimTimelineAutoOccurrence,
    SysDeSimTimelineMachineBinding,
    SysDeSimTimelineMachineTrace,
    SysDeSimTimelineScenario,
    SysDeSimTimelineScenarioEmitAction,
    SysDeSimTimelineScenarioSetInputAction,
    SysDeSimTimelineScenarioStep,
    SysDeSimTimelineStateWindow,
    SysDeSimTimelineStepExecution,
    SysDeSimTimelineWitnessStep,
    build_sysdesim_state_coexistence_constraint_preview,
    build_sysdesim_state_coexistence_timeline_report,
    build_sysdesim_phase10_report,
    build_sysdesim_phase9_report,
    build_sysdesim_timeline_import_report,
    solve_sysdesim_state_coexistence,
)
from .timeline_plantuml import (
    SysDeSimTimelinePlantumlOptions,
    build_sysdesim_timeline_plantuml,
    build_sysdesim_timeline_plantuml_from_xml,
)
from .static_check import (
    detect_query_state_name_unknown,
    detect_signal_dropped_in_state,
    detect_target_state_never_entered,
    detect_temporal_constraints_unsat,
    run_sysdesim_static_pre_checks,
)
from .render import (
    SysdesimRenderError,
    render_sysdesim_timeline_png,
    render_sysdesim_timeline_svg,
)


__all__ = [
    "SysDeSimConversionReport",
    "SysDeSimOutputValidationReport",
    "SysDeSimPreparedMachine",
    "SysDeSimActivityAssignmentObservation",
    "SysDeSimDurationConstraintObservation",
    "SysDeSimInteractionExtract",
    "SysDeSimMessageObservation",
    "SysDeSimNameBindingHint",
    "SysDeSimPhase56Report",
    "SysDeSimPhase78Report",
    "SysDeSimRawXmiDocument",
    "SysDeSimRawXmiSummary",
    "SysDeSimStateInvariantObservation",
    "SysDeSimTimeConstraintObservation",
    "SysDeSimNormalizedTemporalConstraint",
    "SysDeSimPhase10Report",
    "SysDeSimPhase9Output",
    "SysDeSimPhase9Report",
    "SysDeSimStateCoexistenceConstraintPreview",
    "SysDeSimStateCoexistenceResult",
    "SysDeSimStateCoexistenceTimelinePoint",
    "SysDeSimStateCoexistenceTimelineReport",
    "SysDeSimTimelineAutoOccurrence",
    "SysDeSimTimelineMachineBinding",
    "SysDeSimTimelineMachineTrace",
    "SysDeSimTimelinePlantumlOptions",
    "SysDeSimTimelineScenario",
    "SysDeSimTimelineScenarioEmitAction",
    "SysDeSimTimelineScenarioSetInputAction",
    "SysDeSimTimelineScenarioStep",
    "SysDeSimTimelineStateWindow",
    "SysDeSimTimelineStepExecution",
    "SysDeSimTimelineWitnessStep",
    "SysDeSimTimelineDurationConstraint",
    "SysDeSimTimelineEmitAction",
    "SysDeSimTimelineEventCandidate",
    "SysDeSimTimelineInputCandidate",
    "SysDeSimTimelineLifeline",
    "SysDeSimTimelineMachineTransition",
    "SysDeSimTimelineSetInputAction",
    "SysDeSimTimelineStepCandidate",
    "SysDeSimTimelineStepTimeWindow",
    "SysDeSimTimelineTransitionView",
    "SysDeSimTriggerCondition",
    "SysDeSimTriggerNone",
    "SysDeSimTriggerSignal",
    "build_machine_ast",
    "build_sysdesim_conversion_report",
    "build_sysdesim_phase10_report",
    "build_sysdesim_phase56_report",
    "build_sysdesim_phase9_report",
    "build_sysdesim_phase78_report",
    "build_sysdesim_timeline_plantuml",
    "build_sysdesim_timeline_plantuml_from_xml",
    "build_sysdesim_state_coexistence_constraint_preview",
    "build_sysdesim_state_coexistence_timeline_report",
    "convert_sysdesim_xml_to_ast",
    "convert_sysdesim_xml_to_asts",
    "convert_sysdesim_xml_to_dsl",
    "convert_sysdesim_xml_to_dsls",
    "emit_program",
    "extract_sysdesim_interactions",
    "load_sysdesim_machine",
    "load_sysdesim_raw_xmi",
    "load_sysdesim_xml",
    "make_internal_name",
    "normalize_machine",
    "prepare_sysdesim_output_machines",
    "build_sysdesim_timeline_import_report",
    "solve_sysdesim_state_coexistence",
    "summarize_sysdesim_raw_xmi",
    "validate_program_roundtrip",
    "detect_query_state_name_unknown",
    "detect_signal_dropped_in_state",
    "detect_target_state_never_entered",
    "detect_temporal_constraints_unsat",
    "run_sysdesim_static_pre_checks",
    "SysdesimRenderError",
    "render_sysdesim_timeline_png",
    "render_sysdesim_timeline_svg",
]
