"""Catalog contract tests for C/C++ numeric inspect diagnostics."""

from __future__ import annotations

from textwrap import dedent

import pytest

from pyfcstm.diagnostics import CODE_REGISTRY, inspect_model
from pyfcstm.diagnostics.inspect import _catalog_emittable_diagnostics
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.utils import ModelDiagnostic

from ._schema_check import assert_refs_match_schema


MIN_SIGNED_INT64_TEXT = "-9223372036854775808"
MAX_SIGNED_INT64_TEXT = "9223372036854775807"
TOO_LARGE_SIGNED_INT64_TEXT = "9223372036854775808"
TOO_SMALL_SIGNED_INT64_TEXT = "-9223372036854775809"


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
OPERAND_TYPE_ENUM = ("int", "float", "unknown")
OPERAND_TYPE_SOURCE_ENUM = ("literal", "declared_var", "local_expression")
RUNTIME_NOTE_REQUIRED_TEXT = ("C/C++", "Python")
SIGNED_INT64_BOUNDARY_CASES = (
    (TOO_LARGE_SIGNED_INT64_TEXT, "warning"),
    (MIN_SIGNED_INT64_TEXT, "no_warning"),
    (TOO_SMALL_SIGNED_INT64_TEXT, "warning"),
)


SYNTHETIC_REFS = {
    "W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE": {
        "target_family": "c_family",
        "target_templates": C_FAMILY_TARGET_TEMPLATES,
        "runtime_note": "C/C++ deployment profile risk; Python generated runtime may not have the same risk.",
        "context": "var_initializer",
        "expr_text": TOO_LARGE_SIGNED_INT64_TEXT,
        "literal_text": TOO_LARGE_SIGNED_INT64_TEXT,
        "target_bits": 64,
        "signed": True,
        "min_value_text": MIN_SIGNED_INT64_TEXT,
        "max_value_text": MAX_SIGNED_INT64_TEXT,
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


def test_catalog_only_diagnostics_are_filtered_from_inspect_output():
    diagnostic = ModelDiagnostic(
        code="W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE",
        severity="warning",
        message="synthetic catalog-only diagnostic",
        span=None,
        refs=SYNTHETIC_REFS["W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE"],
    )

    assert _catalog_emittable_diagnostics((diagnostic,)) == ()


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
    target_templates = spec.refs_schema["target_templates"]
    assert target_templates.type == "list[str]"
    assert target_templates.item_enum == tuple(C_FAMILY_TARGET_TEMPLATES)
    assert target_templates.exact_values == tuple(C_FAMILY_TARGET_TEMPLATES)
    refs = SYNTHETIC_REFS[code]
    assert refs["target_templates"] == list(target_templates.exact_values)
    assert "python" not in target_templates.exact_values
    assert spec.refs_schema["context"].enum == CONTEXT_ENUM
    assert refs["context"] in CONTEXT_ENUM
    for snippet in RUNTIME_NOTE_REQUIRED_TEXT:
        assert snippet in refs["runtime_note"]


def test_literal_range_code_locks_signed_int64_boundary_refs():
    spec = CODE_REGISTRY["W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE"]
    refs = SYNTHETIC_REFS["W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE"]
    assert refs["target_bits"] == 64
    assert refs["signed"] is True
    assert refs["min_value_text"] == MIN_SIGNED_INT64_TEXT
    assert refs["max_value_text"] == MAX_SIGNED_INT64_TEXT
    assert any(MIN_SIGNED_INT64_TEXT in item for item in spec.for_llm.do_not)
    assert spec.example_dsl is not None
    assert TOO_LARGE_SIGNED_INT64_TEXT in spec.example_dsl
    assert MIN_SIGNED_INT64_TEXT == str(-(2 ** 63))
    assert MAX_SIGNED_INT64_TEXT == str(2 ** 63 - 1)
    assert TOO_LARGE_SIGNED_INT64_TEXT == str(2 ** 63)
    assert TOO_SMALL_SIGNED_INT64_TEXT == str(-(2 ** 63) - 1)


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
    operand_types = spec.refs_schema["operand_types"]
    operand_type_sources = spec.refs_schema["operand_type_sources"]
    assert operand_types.item_enum == OPERAND_TYPE_ENUM
    assert operand_type_sources.item_enum == OPERAND_TYPE_SOURCE_ENUM
    assert (
        set(SYNTHETIC_REFS["W_NUMERIC_FLOAT_BITWISE"]["operand_types"]) <= OPERAND_TYPES
    )
    assert (
        set(SYNTHETIC_REFS["W_NUMERIC_FLOAT_BITWISE"]["operand_type_sources"])
        <= OPERAND_TYPE_SOURCES
    )


def test_numeric_schema_rejects_target_templates_outside_c_family():
    spec = CODE_REGISTRY["W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE"]
    refs = dict(SYNTHETIC_REFS["W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE"])
    refs["target_templates"] = ["python"]

    with pytest.raises(AssertionError, match="item_enum|exact_values"):
        assert_refs_match_schema(
            ModelDiagnostic(
                code=spec.code,
                severity=spec.severity,
                message="synthetic invalid target templates",
                span=None,
                refs=refs,
            ),
            context="invalid target_templates",
        )


def test_numeric_schema_rejects_float_bitwise_unknown_list_members():
    spec = CODE_REGISTRY["W_NUMERIC_FLOAT_BITWISE"]
    refs = dict(SYNTHETIC_REFS["W_NUMERIC_FLOAT_BITWISE"])
    refs["operand_types"] = ["number"]
    refs["operand_type_sources"] = ["magic"]

    with pytest.raises(AssertionError, match="item_enum"):
        assert_refs_match_schema(
            ModelDiagnostic(
                code=spec.code,
                severity=spec.severity,
                message="synthetic invalid operand vocab",
                span=None,
                refs=refs,
            ),
            context="invalid operand vocab",
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
