"""
Public API for SysDeSim conversion helpers.

This package exposes the phase0-4 conversion pipeline for the subset of
SysDeSim UML state machines that can be mapped directly into FCSTM. The public
surface is intentionally small:

* :func:`load_sysdesim_xml` and :func:`load_sysdesim_machine` load the XML/XMI
  source into the dataclass IR.
* :func:`normalize_machine` prepares names, variables, and guard expressions
  for FCSTM export.
* :func:`build_machine_ast`, :func:`emit_program`,
  :func:`convert_sysdesim_xml_to_ast`, and
  :func:`convert_sysdesim_xml_to_dsl` produce FCSTM output, including
  ``uml:TimeEvent`` lowering when ``tick_duration_ms`` is supplied and
  supported single-region cross-level lowering.
* :func:`make_internal_name` provides deterministic reserved names for
  converter-generated artifacts.
* :func:`validate_program_roundtrip` verifies that emitted DSL can be parsed
  back through the existing parser/model stack.

Internals are kept in three files to avoid unnecessary fragmentation:

- ``ir.py`` for the dataclass IR
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
    build_machine_ast,
    convert_sysdesim_xml_to_ast,
    convert_sysdesim_xml_to_dsl,
    emit_program,
    load_sysdesim_machine,
    load_sysdesim_xml,
    make_internal_name,
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
    "make_internal_name",
    "normalize_machine",
    "validate_program_roundtrip",
]
