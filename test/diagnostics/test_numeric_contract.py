"""Contract and emission tests for C/C++ numeric inspect diagnostics."""

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
def test_numeric_codes_are_partial_static_warning_contracts(code):
    spec = CODE_REGISTRY[code]
    assert spec.severity == "warning"
    assert spec.emit_tier == "partial_static_pipeline"
    assert spec.span_object == "expression"
    assert spec.for_llm is not None
    assert spec.example_dsl
    _parse(spec.example_dsl)


@pytest.mark.parametrize("code", sorted(NUMERIC_CODES))
def test_numeric_example_dsls_emit_after_python_analyzer_lands(code):
    spec = CODE_REGISTRY[code]
    report = inspect_model(_parse(spec.example_dsl))
    emitted = [diag for diag in report.diagnostics if diag.code == code]
    assert emitted, [diag.code for diag in report.diagnostics]
    for diag in emitted:
        assert_refs_match_schema(diag, context=code)
        assert diag.span is not None
        assert "C/C++" in diag.message
        assert "Python" in diag.message


def test_catalog_filter_allows_partial_static_numeric_diagnostics():
    diagnostic = ModelDiagnostic(
        code="W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE",
        severity="warning",
        message="synthetic partial-static diagnostic",
        span=None,
        refs=SYNTHETIC_REFS["W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE"],
    )

    assert _catalog_emittable_diagnostics((diagnostic,)) == (diagnostic,)


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
    assert MIN_SIGNED_INT64_TEXT == str(-(2**63))
    assert MAX_SIGNED_INT64_TEXT == str(2**63 - 1)
    assert TOO_LARGE_SIGNED_INT64_TEXT == str(2**63)
    assert TOO_SMALL_SIGNED_INT64_TEXT == str(-(2**63) - 1)


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


def _diagnostics_for(source: str, code: str):
    report = inspect_model(_parse(source))
    return [diag for diag in report.diagnostics if diag.code == code]


def _single_diagnostic(source: str, code: str):
    diagnostics = _diagnostics_for(source, code)
    assert len(diagnostics) == 1, [diag.refs for diag in diagnostics]
    diagnostic = diagnostics[0]
    assert_refs_match_schema(diagnostic, context=code)
    assert diagnostic.span is not None
    return diagnostic


@pytest.mark.parametrize(
    ("literal_text", "expect_warning"),
    [
        (TOO_LARGE_SIGNED_INT64_TEXT, True),
        ("+" + TOO_LARGE_SIGNED_INT64_TEXT, True),
        (MIN_SIGNED_INT64_TEXT, False),
        (TOO_SMALL_SIGNED_INT64_TEXT, True),
    ],
)
def test_numeric_literal_range_int64_boundary_emission(
    literal_text,
    expect_warning,
):
    diagnostics = _diagnostics_for(
        f"""
        def int value = {literal_text};
        state Root {{ state A; [*] -> A; }}
        """,
        "W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE",
    )
    if expect_warning:
        assert len(diagnostics) == 1
        refs = diagnostics[0].refs
        assert refs["literal_text"] == literal_text
        assert refs["context"] == "var_initializer"
        assert refs["var_name"] == "value"
        assert refs["target_templates"] == C_FAMILY_TARGET_TEMPLATES
        assert_refs_match_schema(diagnostics[0], context=literal_text)
    else:
        assert diagnostics == []


@pytest.mark.parametrize(
    ("name", "source", "code", "expected_refs"),
    [
        (
            "var-literal-range",
            f"""
            def int value = {TOO_LARGE_SIGNED_INT64_TEXT};
            state Root {{ state A; [*] -> A; }}
            """,
            "W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE",
            {"context": "var_initializer", "var_name": "value"},
        ),
        (
            "guard-division",
            """
            def int input = 1;
            state Root {
                state A;
                state B;
                [*] -> A;
                A -> B : if [input / (1 - 1) > 0];
            }
            """,
            "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",
            {"context": "guard", "operator": "/", "rhs_text": "1 - 1"},
        ),
        (
            "transition-effect-shift",
            """
            def int flags = 1;
            state Root {
                state A;
                state B;
                [*] -> A;
                A -> B effect { flags = flags << 64; };
            }
            """,
            "W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE",
            {
                "context": "transition_effect",
                "statement_kind": "operation_assignment",
                "operator": "<<",
                "shift_count_text": "64",
            },
        ),
        (
            "lifecycle-float-bitwise",
            """
            def int flags = 1;
            def float gain = 1.5;
            state Root {
                state A { during { flags = flags & gain; } }
                [*] -> A;
            }
            """,
            "W_NUMERIC_FLOAT_BITWISE",
            {
                "context": "lifecycle_action",
                "statement_kind": "operation_assignment",
                "operator": "&",
                "operand_types": ["int", "float"],
                "operand_type_sources": ["declared_var", "declared_var"],
            },
        ),
    ],
)
def test_numeric_analyzer_emits_context_specific_refs(
    name,
    source,
    code,
    expected_refs,
):
    diagnostic = _single_diagnostic(source, code)
    for key, value in expected_refs.items():
        assert diagnostic.refs[key] == value, name
    assert diagnostic.refs["target_family"] == "c_family"
    assert diagnostic.refs["target_templates"] == C_FAMILY_TARGET_TEMPLATES
    assert "C/C++" in diagnostic.message
    assert "Python" in diagnostic.message


def test_numeric_division_by_zero_folds_rhs_even_when_lhs_is_dynamic():
    diagnostic = _single_diagnostic(
        """
        def int result = 0;
        def int input = 1;
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B effect { result = input / (1 - 1); };
        }
        """,
        "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",
    )
    assert diagnostic.refs["operator"] == "/"
    assert diagnostic.refs["rhs_text"] == "1 - 1"
    assert diagnostic.refs["expr_text"] == "input / (1 - 1)"


def test_numeric_modulo_by_zero_reports_operator_separately():
    diagnostic = _single_diagnostic(
        """
        def int result = 0;
        def int input = 1;
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B effect { result = input % (2 - 2); };
        }
        """,
        "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",
    )
    assert diagnostic.refs["operator"] == "%"
    assert diagnostic.refs["rhs_text"] == "2 - 2"


def test_numeric_division_dynamic_rhs_is_not_reported():
    diagnostics = _diagnostics_for(
        """
        def int result = 0;
        def int input = 1;
        def int denom = 0;
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B effect { result = input / denom; };
        }
        """,
        "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",
    )
    assert diagnostics == []


@pytest.mark.parametrize("shift_expr", ["flags << -1", "flags >> 64"])
def test_numeric_shift_constant_out_of_target_range_reports(shift_expr):
    diagnostic = _single_diagnostic(
        f"""
        def int flags = 1;
        state Root {{
            state A;
            state B;
            [*] -> A;
            A -> B effect {{ flags = {shift_expr}; }};
        }}
        """,
        "W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE",
    )
    assert diagnostic.refs["operator"] in {"<<", ">>"}
    assert diagnostic.refs["target_bits"] == 64


def test_numeric_shift_dynamic_rhs_is_not_reported():
    diagnostics = _diagnostics_for(
        """
        def int flags = 1;
        def int amount = 64;
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B effect { flags = flags << amount; };
        }
        """,
        "W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE",
    )
    assert diagnostics == []


@pytest.mark.parametrize(
    ("expr", "expected_types", "expected_sources"),
    [
        ("1.5 & flags", ["float", "int"], ["literal", "declared_var"]),
        ("gain | flags", ["float", "int"], ["declared_var", "declared_var"]),
        (
            "(gain + 1.0) ^ flags",
            ["float", "int"],
            ["local_expression", "declared_var"],
        ),
        (
            "(1 / 2) & flags",
            ["float", "int"],
            ["local_expression", "declared_var"],
        ),
        (
            "sin(1) & flags",
            ["float", "int"],
            ["local_expression", "declared_var"],
        ),
        (
            "abs(gain) & flags",
            ["float", "int"],
            ["local_expression", "declared_var"],
        ),
        (
            "((flags > 0) ? 1.0 : 0) & flags",
            ["float", "int"],
            ["local_expression", "declared_var"],
        ),
    ],
)
def test_numeric_float_bitwise_operand_evidence(
    expr,
    expected_types,
    expected_sources,
):
    diagnostic = _single_diagnostic(
        f"""
        def int flags = 1;
        def float gain = 1.5;
        state Root {{
            state A {{ during {{ flags = {expr}; }} }}
            [*] -> A;
        }}
        """,
        "W_NUMERIC_FLOAT_BITWISE",
    )
    assert diagnostic.refs["operand_types"] == expected_types
    assert diagnostic.refs["operand_type_sources"] == expected_sources


def test_numeric_float_bitwise_does_not_treat_int_local_expression_as_float():
    diagnostics = _diagnostics_for(
        """
        def int flags = 1;
        state Root {
            state A { during { flags = (1 + 2) & flags; } }
            [*] -> A;
        }
        """,
        "W_NUMERIC_FLOAT_BITWISE",
    )
    assert diagnostics == []


def test_numeric_float_shift_can_overlap_shift_count_warning():
    source = """
    def int flags = 1;
    def float gain = 1.5;
    state Root {
        state A { during { flags = gain << 64; } }
        [*] -> A;
    }
    """
    report = inspect_model(_parse(source))
    numeric_codes = [
        diag.code for diag in report.diagnostics if diag.code in NUMERIC_CODES
    ]
    assert numeric_codes.count("W_NUMERIC_FLOAT_BITWISE") == 1
    assert numeric_codes.count("W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE") == 1


def test_numeric_scans_operation_if_branch_conditions_and_nested_assignments():
    report = inspect_model(
        _parse("""
        def int flags = 1;
        state Root {
            state A {
                during {
                    if [flags > 0] {
                        flags = flags << 64;
                    }
                }
            }
            [*] -> A;
        }
    """)
    )
    diagnostics = [
        diag
        for diag in report.diagnostics
        if diag.code == "W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE"
    ]
    assert len(diagnostics) == 1
    assert diagnostics[0].refs["context"] == "lifecycle_action"
    assert diagnostics[0].refs["statement_kind"] == "operation_assignment"


def test_numeric_lifecycle_refs_do_not_duplicate_inline_action_warnings():
    diagnostics = _diagnostics_for(
        """
        def int value = 1;
        state Root {
            state A {
                enter abstract HardwareInit;
                enter Inline { value = value / 0; }
                enter ref Inline;
            }
            [*] -> A;
        }
        """,
        "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",
    )
    assert len(diagnostics) == 1
    assert diagnostics[0].refs["context"] == "lifecycle_action"
    assert diagnostics[0].refs["statement_kind"] == "operation_assignment"


@pytest.mark.parametrize(
    ("context_name", "source"),
    [
        (
            "var_initializer",
            """
            def int value = 1 / (1 - 1);
            state Root { state A; [*] -> A; }
            """,
        ),
        (
            "guard",
            """
            def int value = 1;
            state Root { state A; state B; [*] -> A; A -> B : if [value / 0 > 0]; }
            """,
        ),
        (
            "transition_effect",
            """
            def int value = 1;
            state Root { state A; state B; [*] -> A; A -> B effect { value = value / 0; }; }
            """,
        ),
        (
            "lifecycle_action",
            """
            def int value = 1;
            state Root { state A { exit { value = value / 0; } } [*] -> A; }
            """,
        ),
    ],
)
def test_numeric_division_warning_covers_all_expression_contexts(
    context_name,
    source,
):
    diagnostic = _single_diagnostic(
        source,
        "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",
    )
    assert diagnostic.refs["context"] == context_name
    if context_name in {"transition_effect", "lifecycle_action"}:
        assert diagnostic.refs["statement_kind"] == "operation_assignment"


@pytest.mark.parametrize(
    ("code", "context_name", "source", "statement_kind"),
    [
        (
            "W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE",
            "var_initializer",
            f"""
            def int value = {TOO_LARGE_SIGNED_INT64_TEXT};
            state Root {{ state A; [*] -> A; }}
            """,
            None,
        ),
        (
            "W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE",
            "guard",
            f"""
            state Root {{
                state A;
                state B;
                [*] -> A;
                A -> B : if [{TOO_LARGE_SIGNED_INT64_TEXT} > 0];
            }}
            """,
            None,
        ),
        (
            "W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE",
            "transition_effect",
            f"""
            def int value = 0;
            state Root {{
                state A;
                state B;
                [*] -> A;
                A -> B effect {{ value = {TOO_LARGE_SIGNED_INT64_TEXT}; }};
            }}
            """,
            "operation_assignment",
        ),
        (
            "W_NUMERIC_LITERAL_OUT_OF_TARGET_RANGE",
            "lifecycle_action",
            f"""
            def int value = 0;
            state Root {{
                state A {{ enter {{ value = {TOO_LARGE_SIGNED_INT64_TEXT}; }} }}
                [*] -> A;
            }}
            """,
            "operation_assignment",
        ),
        (
            "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",
            "var_initializer",
            """
            def int value = 1 / 0;
            state Root { state A; [*] -> A; }
            """,
            None,
        ),
        (
            "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",
            "guard",
            """
            def int value = 1;
            state Root { state A; state B; [*] -> A; A -> B : if [value / 0 > 0]; }
            """,
            None,
        ),
        (
            "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",
            "transition_effect",
            """
            def int value = 1;
            state Root { state A; state B; [*] -> A; A -> B effect { value = value / 0; }; }
            """,
            "operation_assignment",
        ),
        (
            "W_NUMERIC_CONSTANT_DIVISION_BY_ZERO",
            "lifecycle_action",
            """
            def int value = 1;
            state Root { state A { exit { value = value / 0; } } [*] -> A; }
            """,
            "operation_assignment",
        ),
        (
            "W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE",
            "var_initializer",
            """
            def int value = 1 << 64;
            state Root { state A; [*] -> A; }
            """,
            None,
        ),
        (
            "W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE",
            "guard",
            """
            state Root { state A; state B; [*] -> A; A -> B : if [(1 << 64) != 0]; }
            """,
            None,
        ),
        (
            "W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE",
            "transition_effect",
            """
            def int flags = 1;
            state Root { state A; state B; [*] -> A; A -> B effect { flags = flags << 64; }; }
            """,
            "operation_assignment",
        ),
        (
            "W_NUMERIC_SHIFT_COUNT_OUT_OF_TARGET_RANGE",
            "lifecycle_action",
            """
            def int flags = 1;
            state Root { state A { during { flags = flags << 64; } } [*] -> A; }
            """,
            "operation_assignment",
        ),
        (
            "W_NUMERIC_FLOAT_BITWISE",
            "var_initializer",
            """
            def int flags = 1.5 & 1;
            state Root { state A; [*] -> A; }
            """,
            None,
        ),
        (
            "W_NUMERIC_FLOAT_BITWISE",
            "guard",
            """
            def float gain = 1.5;
            state Root { state A; state B; [*] -> A; A -> B : if [(gain & 1) != 0]; }
            """,
            None,
        ),
        (
            "W_NUMERIC_FLOAT_BITWISE",
            "transition_effect",
            """
            def int flags = 1;
            def float gain = 1.5;
            state Root { state A; state B; [*] -> A; A -> B effect { flags = gain & flags; }; }
            """,
            "operation_assignment",
        ),
        (
            "W_NUMERIC_FLOAT_BITWISE",
            "lifecycle_action",
            """
            def int flags = 1;
            def float gain = 1.5;
            state Root { state A { during { flags = gain & flags; } } [*] -> A; }
            """,
            "operation_assignment",
        ),
    ],
)
def test_numeric_rules_cover_all_public_expression_contexts(
    code,
    context_name,
    source,
    statement_kind,
):
    diagnostics = _diagnostics_for(source, code)
    assert diagnostics, code
    assert any(
        diag.refs["context"] == context_name
        and (
            statement_kind is None or diag.refs.get("statement_kind") == statement_kind
        )
        for diag in diagnostics
    ), [diag.refs for diag in diagnostics]
    for diag in diagnostics:
        assert_refs_match_schema(diag, context=code)


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
