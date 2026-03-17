"""
Public API for SysDeSim conversion helpers.

The package currently exposes the phase0-2 pipeline only. Internals are kept in
three files to avoid unnecessary fragmentation:

- ``ir.py`` for the dataclass IR
- ``convert.py`` for loading, normalization, AST building, and validation
- ``__init__.py`` for the stable public surface
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
