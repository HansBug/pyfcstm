"""
Static audit of every ``_emit_import_diag`` call site in
``pyfcstm/model/imports.py``.

I-e from PR #115 review: the runtime parity tests can only catch
schema↔emit drift on emit paths that some fixture actually walks.
Several import-error code paths (E_IMPORT_MAPPING_INVALID variants,
specific E_IMPORT_DUPLICATE_MAPPING reachability) are not exercised
by the current showcase fixtures yet exist in the source — a static
scan over the AST is the only way to keep them honest until a fixture
catches up.

This test parses ``imports.py`` and asserts that every kwarg-style
call to ``_emit_import_diag`` includes the schema-required ``refs``
fields declared in ``codes.yaml``.
"""

import ast
from pathlib import Path

import pytest

from pyfcstm.diagnostics import CODE_REGISTRY

IMPORTS_PY = Path(__file__).resolve().parents[2] / 'pyfcstm' / 'model' / 'imports.py'


def _audit_imports_emits():
    tree = ast.parse(IMPORTS_PY.read_text(encoding='utf-8'))
    violations = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Name) and func.id == '_emit_import_diag'):
            continue
        if len(node.args) < 2:
            continue
        code_arg = node.args[1]
        if not isinstance(code_arg, ast.Constant) or not isinstance(code_arg.value, str):
            continue
        code = code_arg.value
        spec = CODE_REGISTRY.get(code)
        if spec is None:
            violations.append((node.lineno, code, 'UNKNOWN_CODE', '<no schema>'))
            continue
        provided = {kw.arg for kw in node.keywords if kw.arg is not None}
        for field in spec.required_fields():
            if field not in provided:
                violations.append((node.lineno, code, 'MISSING_REQUIRED', field))
    return violations


@pytest.mark.unittest
def test_imports_py_emits_match_schema_required_fields():
    violations = _audit_imports_emits()
    formatted = '\n'.join(
        f'  imports.py:{line} {code} {kind} {detail}'
        for line, code, kind, detail in violations
    )
    assert not violations, (
        f'Found {len(violations)} schema-required-field violation(s) in '
        f'pyfcstm/model/imports.py:\n{formatted}\n\n'
        f'Each ``_emit_import_diag(sink, CODE, message, **kwargs)`` call must '
        f'pass every required ``refs`` key declared for CODE in codes.yaml.'
    )
