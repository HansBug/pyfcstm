"""Catalog contract tests for C/C++ numeric inspect diagnostics."""

from __future__ import annotations

from textwrap import dedent

import pytest

from pyfcstm.diagnostics import CODE_REGISTRY, inspect_model
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.utils import ModelDiagnostic

from ._schema_check import assert_refs_match_schema


pytestmark = pytest.mark.unittest


NUMERIC_CODES = {
    "W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE",
    "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",
    "W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE",
    "W_NUMERIC_FLOAT_BITWISE",
}

C_FAMILY_TARGET_TEMPLATES = ["c", "c_poll", "cpp", "cpp_poll"]
CONTEXT_ENUM = ("var_initializer", "guard", "transition_effect", "lifecycle_action")
OPERAND_TYPES = {"int", "float", "unknown"}
OPERAND_TYPE_SOURCES = {"literal", "declared_var", "local_expression"}
RUNTIME_NOTE_REQUIRED_TEXT = ("C/C++", "Python")


SYNTHETIC_REFS = {
    "W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE": {
        "target_family": "c_family",
        "target_templates": C_FAMILY_TARGET_TEMPLATES,
        "runtime_note": "C/C++ deployment profile risk; Python generated runtime may not have the same risk.",
        "context": "var_initializer",
        "expr_text": "9223372036854775808",
        "literal_text": "9223372036854775808",
        "target_bits": 64,
        "signed": True,
        "min_value_text": "-9223372036854775808",
        "max_value_text": "9223372036854775807",
        "var_name": "too_large",
    },
    "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO": {
        "target_family": "c_family",
        "target_templates": C_FAMILY_TARGET_TEMPLATES,
        "runtime_note": "C/C++ deployment profile risk; Python generated runtime has different exception semantics.",
        "context": "transition_effect",
        "statement_kind": "operation_assignment",
        "expr_text": "input / (1 - 1)",
        "operator": "/",
        "rhs_text": "(1 - 1)",
    },
    "W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE": {
        "target_family": "c_family",
        "target_templates": C_FAMILY_TARGET_TEMPLATES,
        "runtime_note": "C/C++ deployment profile risk; Python generated runtime may not have the same fixed-width shift risk.",
        "context": "guard",
        "expr_text": "flags << 64",
        "operator": "<<",
        "target_bits": 64,
        "shift_count_text": "64",
    },
    "W_NUMERIC_FLOAT_BITWISE": {
        "target_family": "c_family",
        "target_templates": C_FAMILY_TARGET_TEMPLATES,
        "runtime_note": "C/C++ integer-operation profile risk; Python generated runtime may fail for a different reason.",
        "context": "lifecycle_action",
        "statement_kind": "operation_assignment",
        "expr_text": "flags & gain",
        "operator": "&",
        "operand_types": ["int", "float"],
        "operand_type_sources": ["declared_var", "declared_var"],
    },
}


SIGNED_INT64_BOUNDARY_CASES = [
    ("9223372036854775808", "warning"),
    ("-9223372036854775808", "no_warning"),
    ("-9223372036854775809", "warning"),
]


def _parse(source: str):
    ast = parse_with_grammar_entry(dedent(source), "state_machine_dsl")
    return parse_dsl_node_to_state_machine(ast)


def test_numeric_contract_declares_exact_code_set():
    assert NUMERIC_CODES <= set(CODE_REGISTRY)
    assert "W_NUMERIC_SHIFT_REQUIRES_PROOF" not in CODE_REGISTRY
    assert "I_NUMERIC_VERIFY_RECOMMENDED" not in CODE_REGISTRY


@pytest.mark.parametrize("code", sorted(NUMERIC_CODES))
def test_numeric_codes_are_catalog_only_warning_contracts(code):
    spec = CODE_REGISTRY[code]
    assert spec.severity == "warning"
    assert spec.emit_tier == "catalog_only"
    assert spec.span_object == "expression"
    assert spec.for_llm is not None
    assert spec.example_dsl
    _parse(spec.example_dsl)


@pytest.mark.parametrize("code", sorted(NUMERIC_CODES))
def test_numeric_codes_do_not_emit_before_analyzer_lands(code):
    spec = CODE_REGISTRY[code]
    report = inspect_model(_parse(spec.example_dsl))
    assert code not in {diag.code for diag in report.diagnostics}


@pytest.mark.parametrize("code", sorted(NUMERIC_CODES))
def test_numeric_refs_schema_accepts_representative_payloads(code):
    spec = CODE_REGISTRY[code]
    assert_refs_match_schema(
        ModelDiagnostic(
            code=code,
            severity=spec.severity,
            message=f"synthetic contract check for {code}",
            span=None,
            refs=SYNTHETIC_REFS[code],
        ),
        context=code,
    )


@pytest.mark.parametrize("code", sorted(NUMERIC_CODES))
def test_numeric_target_profile_fields_are_required_and_stable(code):
    spec = CODE_REGISTRY[code]
    required = set(spec.required_fields())
    assert {
        "target_family",
        "target_templates",
        "runtime_note",
        "context",
        "expr_text",
    } <= required
    assert spec.refs_schema["target_family"].enum == ("c_family",)
    assert spec.refs_schema["target_templates"].type == "list[str]"
    refs = SYNTHETIC_REFS[code]
    assert refs["target_templates"] == C_FAMILY_TARGET_TEMPLATES
    assert "python" not in refs["target_templates"]
    assert spec.refs_schema["context"].enum == CONTEXT_ENUM
    assert refs["context"] in CONTEXT_ENUM
    for snippet in RUNTIME_NOTE_REQUIRED_TEXT:
        assert snippet in refs["runtime_note"]


def test_literal_range_code_locks_signed_int64_boundary_refs():
    spec = CODE_REGISTRY["W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE"]
    refs = SYNTHETIC_REFS["W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE"]
    assert refs["target_bits"] == 64
    assert refs["signed"] is True
    assert refs["min_value_text"] == "-9223372036854775808"
    assert refs["max_value_text"] == "9223372036854775807"
    assert "-9223372036854775808" in spec.for_llm.do_not[1]
    assert SIGNED_INT64_BOUNDARY_CASES == [
        ("9223372036854775808", "warning"),
        ("-9223372036854775808", "no_warning"),
        ("-9223372036854775809", "warning"),
    ]


def test_numeric_boundary_example_dsl_variants_parse():
    for literal_text, _classification in SIGNED_INT64_BOUNDARY_CASES:
        _parse(f"""
            def int value = {literal_text};
            state Root {{ state A; [*] -> A; }}
        """)


def test_division_and_modulo_share_required_operator_contract():
    spec = CODE_REGISTRY["W_NUMERIC_CONSTANT_DIVISION_BY_ZERO"]
    assert "operator" in spec.required_fields()
    assert spec.refs_schema["operator"].enum == ("/", "%")


def test_shift_code_locks_target_bits_and_operator_contract():
    spec = CODE_REGISTRY["W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE"]
    assert "operator" in spec.required_fields()
    assert spec.refs_schema["operator"].enum == ("<<", ">>")
    assert "target_bits" in spec.required_fields()
    assert (
        SYNTHETIC_REFS["W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE"]["target_bits"] == 64
    )


def test_float_bitwise_locks_operand_type_vocabularies():
    spec = CODE_REGISTRY["W_NUMERIC_FLOAT_BITWISE"]
    assert spec.refs_schema["operator"].enum == ("&", "^", "|", "<<", ">>")
    assert (
        set(SYNTHETIC_REFS["W_NUMERIC_FLOAT_BITWISE"]["operand_types"]) <= OPERAND_TYPES
    )
    assert (
        set(SYNTHETIC_REFS["W_NUMERIC_FLOAT_BITWISE"]["operand_type_sources"])
        <= OPERAND_TYPE_SOURCES
    )


@pytest.mark.parametrize("code", sorted(NUMERIC_CODES))
def test_numeric_descriptions_are_target_specific(code):
    spec = CODE_REGISTRY[code]
    text = " ".join(
        [
            spec.description,
            spec.for_llm.summary if spec.for_llm is not None else "",
            " ".join(spec.for_llm.do_not) if spec.for_llm is not None else "",
        ]
    )
    assert "C/C++" in text
    assert "Python" in text
