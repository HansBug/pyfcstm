"""
Public conversion entry points exposed by :mod:`pyfcstm.convert`.

This package currently re-exports the SysDeSim phase0-3 conversion helpers from
:mod:`pyfcstm.convert.sysdesim`. The exported functions cover the full
``XML -> IR -> normalized IR -> FCSTM AST -> DSL`` pipeline for the supported
SysDeSim subset.

The package exports:

* :func:`build_machine_ast` - Build an FCSTM DSL AST from normalized IR.
* :func:`convert_sysdesim_xml_to_ast` - Perform the full XML-to-AST conversion.
* :func:`convert_sysdesim_xml_to_dsl` - Perform the full XML-to-DSL conversion.
* :func:`emit_program` - Serialize a DSL AST to FCSTM source text.
* :func:`load_sysdesim_machine` - Load one state machine from a SysDeSim file.
* :func:`load_sysdesim_xml` - Load all state machines from a SysDeSim file.
* :func:`normalize_machine` - Normalize names and guards in IR.
* :func:`validate_program_roundtrip` - Validate emitted DSL through the parser.

Example::

    >>> from pyfcstm.convert import convert_sysdesim_xml_to_dsl
    >>> dsl_code = convert_sysdesim_xml_to_dsl("sample.sysdesim.xml")
    >>> isinstance(dsl_code, str)
    True
"""

from .sysdesim import (
    build_machine_ast,
    convert_sysdesim_xml_to_ast,
    convert_sysdesim_xml_to_dsl,
    emit_program,
    load_sysdesim_machine,
    load_sysdesim_xml,
    normalize_machine,
    validate_program_roundtrip,
)

__all__ = [
    "build_machine_ast",
    "convert_sysdesim_xml_to_ast",
    "convert_sysdesim_xml_to_dsl",
    "emit_program",
    "load_sysdesim_machine",
    "load_sysdesim_xml",
    "normalize_machine",
    "validate_program_roundtrip",
]
