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

Internals are kept in four files to avoid unnecessary fragmentation:

- ``ir.py`` for the dataclass IR
- ``xmi.py`` for the raw XML/XMI index layer
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


__all__ = [
    "SysDeSimConversionReport",
    "SysDeSimOutputValidationReport",
    "SysDeSimPreparedMachine",
    "SysDeSimRawXmiDocument",
    "SysDeSimRawXmiSummary",
    "build_machine_ast",
    "build_sysdesim_conversion_report",
    "convert_sysdesim_xml_to_ast",
    "convert_sysdesim_xml_to_asts",
    "convert_sysdesim_xml_to_dsl",
    "convert_sysdesim_xml_to_dsls",
    "emit_program",
    "load_sysdesim_machine",
    "load_sysdesim_raw_xmi",
    "load_sysdesim_xml",
    "make_internal_name",
    "normalize_machine",
    "prepare_sysdesim_output_machines",
    "summarize_sysdesim_raw_xmi",
    "validate_program_roundtrip",
]
