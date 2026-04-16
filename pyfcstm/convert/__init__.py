"""
Public conversion entry points exposed by :mod:`pyfcstm.convert`.

This package currently re-exports the SysDeSim phase0-6 conversion helpers from
:mod:`pyfcstm.convert.sysdesim`. The exported functions cover the full
``XML -> IR -> normalized IR -> FCSTM AST -> DSL`` pipeline for the supported
SysDeSim subset.

The package exports:

* :func:`build_machine_ast` - Build an FCSTM DSL AST from normalized IR.
* :func:`build_sysdesim_conversion_report` - Build a structured conversion validation report.
* :func:`convert_sysdesim_xml_to_ast` - Perform the full XML-to-AST conversion.
* :func:`convert_sysdesim_xml_to_asts` - Perform split-aware XML-to-AST conversion.
* :func:`convert_sysdesim_xml_to_dsl` - Perform the full XML-to-DSL conversion.
* :func:`convert_sysdesim_xml_to_dsls` - Perform split-aware XML-to-DSL conversion.
* :func:`emit_program` - Serialize a DSL AST to FCSTM source text.
* :func:`load_sysdesim_machine` - Load one state machine from a SysDeSim file.
* :func:`load_sysdesim_xml` - Load all state machines from a SysDeSim file.
* :func:`normalize_machine` - Normalize names and guards in IR.
* :func:`prepare_sysdesim_output_machines` - Normalize one SysDeSim machine into a main output plus any region-level split views.
* :func:`validate_program_roundtrip` - Validate emitted DSL through the parser.

Example::

    >>> from pyfcstm.convert import convert_sysdesim_xml_to_dsl
    >>> dsl_code = convert_sysdesim_xml_to_dsl("sample.sysdesim.xml")
    >>> isinstance(dsl_code, str)
    True
"""

from .sysdesim import (
    SysDeSimConversionReport,
    SysDeSimOutputValidationReport,
    SysDeSimPreparedMachine,
    build_machine_ast,
    build_sysdesim_conversion_report,
    build_sysdesim_timeline_import_report,
    convert_sysdesim_xml_to_ast,
    convert_sysdesim_xml_to_asts,
    convert_sysdesim_xml_to_dsl,
    convert_sysdesim_xml_to_dsls,
    emit_program,
    load_sysdesim_machine,
    load_sysdesim_xml,
    normalize_machine,
    prepare_sysdesim_output_machines,
    validate_program_roundtrip,
)

__all__ = [
    "SysDeSimConversionReport",
    "SysDeSimOutputValidationReport",
    "SysDeSimPreparedMachine",
    "build_machine_ast",
    "build_sysdesim_conversion_report",
    "build_sysdesim_timeline_import_report",
    "convert_sysdesim_xml_to_ast",
    "convert_sysdesim_xml_to_asts",
    "convert_sysdesim_xml_to_dsl",
    "convert_sysdesim_xml_to_dsls",
    "emit_program",
    "load_sysdesim_machine",
    "load_sysdesim_xml",
    "normalize_machine",
    "prepare_sysdesim_output_machines",
    "validate_program_roundtrip",
]
