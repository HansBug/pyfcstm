"""High-level BMC query compilation pipeline tests."""

from __future__ import annotations

import ast
import inspect
import subprocess
import sys

import pytest
import z3

import pyfcstm.bmc.pipeline as pipeline_module
from pyfcstm.bmc import (
    BmcBuildError,
    BmcOptions,
    BmcPropertyFormula,
    BmcQueryParseError,
    InvalidBmcDomain,
    InvalidBmcQuery,
    UnsupportedBmcQuery,
    build_bmc_core_formula,
    compile_bmc_property,
    parse_bmc_query,
    prepare_bmc_query,
    solve_bmc_property,
)
from pyfcstm.bmc.pipeline import compile_bmc_query
from pyfcstm.model import load_state_machine_from_text


pytestmark = pytest.mark.unittest


def _model():
    return load_state_machine_from_text(
        """
        state Root {
            state Idle;
            state Done;
            [*] -> Idle;
            Idle -> Done;
        }
        """
    )


def _manual_compile(model, query, options=None):
    context = prepare_bmc_query(model, query, options=options)
    core = build_bmc_core_formula(context)
    return compile_bmc_property(core)


def test_pipeline_public_contract_is_exact() -> None:
    """The facade keeps one concise public function and a stable signature."""
    assert pipeline_module.__all__ == ["compile_bmc_query"]
    assert inspect.signature(compile_bmc_query) == inspect.Signature(
        parameters=[
            inspect.Parameter(
                "model",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation="StateMachine",
            ),
            inspect.Parameter(
                "query",
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation="Union[str, BmcQuery]",
            ),
            inspect.Parameter(
                "options",
                inspect.Parameter.KEYWORD_ONLY,
                default=None,
                annotation="Optional[BmcOptions]",
            ),
        ],
        return_annotation="BmcPropertyFormula",
    )


def test_pipeline_uses_explicit_relative_sibling_imports() -> None:
    """The facade follows the PR-12.1 BMC sibling-import contract."""
    tree = ast.parse(inspect.getsource(pipeline_module))
    sibling_modules = {"engine", "properties", "query", "relation"}

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(not alias.name.startswith("pyfcstm.bmc") for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            assert all(alias.name != "*" for alias in node.names)
            assert not (
                node.level == 0 and (node.module or "").startswith("pyfcstm.bmc")
            )
            if node.level:
                assert node.level == 1
                assert node.module in sibling_modules


@pytest.mark.parametrize("as_text", [True, False], ids=["text", "ast"])
def test_compile_bmc_query_matches_manual_pipeline(as_text: bool) -> None:
    """Text and AST inputs each match the existing three-stage truth source."""
    model = _model()
    query_text = 'check reach <= 1: active("Root.Done");'
    query = query_text if as_text else parse_bmc_query(query_text)

    actual = compile_bmc_query(model, query)
    expected = _manual_compile(model, query)

    assert isinstance(actual, BmcPropertyFormula)
    assert actual.to_canonical() == expected.to_canonical()
    if as_text:
        assert actual.core.context.source_text == query_text
    else:
        assert actual.core.context.source_text is None


def test_text_and_ast_inputs_share_semantics_but_keep_distinct_provenance() -> None:
    """Cross-input semantics match while source provenance stays contextual."""
    model = _model()
    query_text = 'check reach <= 1: active("Root.Done");'

    text_formula = compile_bmc_query(model, query_text)
    ast_formula = compile_bmc_query(model, parse_bmc_query(query_text))
    text_context = text_formula.core.context
    ast_context = ast_formula.core.context

    assert text_context.query.to_canonical() == ast_context.query.to_canonical()
    assert (
        text_context.bound_query.to_canonical()
        == ast_context.bound_query.to_canonical()
    )
    assert text_context.domain.to_canonical() == ast_context.domain.to_canonical()
    assert text_formula.to_canonical() == ast_formula.to_canonical()
    assert text_context.source_text == query_text
    assert ast_context.source_text is None


def test_compile_bmc_query_forwards_options_and_rejects_positional_options() -> None:
    """The facade forwards policy options through its keyword-only argument."""
    model = _model()
    query = 'check reach <= 2: active("Root.Done");'
    options = BmcOptions(max_bound=2)

    formula = compile_bmc_query(model, query, options=options)

    assert formula.bound == 2
    assert formula.core.context.options is options
    with pytest.raises(TypeError):
        compile_bmc_query(model, query, options)
    with pytest.raises(BmcBuildError, match="query_bound=2.*max_bound=1"):
        compile_bmc_query(model, query, options=BmcOptions(max_bound=1))


@pytest.mark.parametrize(
    ("stage_name", "error"),
    [
        ("prepare_bmc_query", BmcBuildError("build failure")),
        ("prepare_bmc_query", BmcQueryParseError("parse failure")),
        ("prepare_bmc_query", InvalidBmcQuery("query failure")),
        ("prepare_bmc_query", InvalidBmcDomain("domain failure")),
        ("build_bmc_core_formula", UnsupportedBmcQuery("lowering failure")),
        ("compile_bmc_property", BmcBuildError("property build failure")),
        ("compile_bmc_property", InvalidBmcQuery("property query failure")),
        (
            "compile_bmc_property",
            UnsupportedBmcQuery("property lowering failure"),
        ),
    ],
    ids=[
        "build-error",
        "parse-error",
        "invalid-query",
        "invalid-domain",
        "core-unsupported-query",
        "property-build-error",
        "property-invalid-query",
        "property-unsupported-query",
    ],
)
def test_compile_bmc_query_propagates_stage_errors_unchanged(
    monkeypatch: pytest.MonkeyPatch, stage_name: str, error: Exception
) -> None:
    """The facade does not wrap or rewrite public pipeline exceptions."""

    def fail(*args, **kwargs):
        raise error

    monkeypatch.setattr(pipeline_module, stage_name, fail)

    with pytest.raises(type(error)) as excinfo:
        compile_bmc_query(_model(), 'check reach <= 1: active("Root.Done");')

    assert excinfo.value is error
    assert str(excinfo.value) == str(error)


def test_compile_bmc_query_preserves_real_prepare_errors() -> None:
    """Real input failures retain their existing types and messages."""
    model = _model()

    with pytest.raises(BmcBuildError, match="query must be a str or BmcQuery"):
        compile_bmc_query(model, object())
    with pytest.raises(BmcQueryParseError):
        compile_bmc_query(model, "check reach <= ;")
    with pytest.raises(InvalidBmcQuery) as excinfo:
        compile_bmc_query(model, 'check reach <= 1: active("Root.Missing");')
    assert excinfo.value.diagnostic.code == "unknown_state"


def test_compile_bmc_query_preserves_real_unsupported_lowering_error() -> None:
    """A parser-supported operation without lowering keeps its public error."""
    model = load_state_machine_from_text("def int x = 4; state Root;")
    query = "assume always: sin(x) >= 0;\ncheck reach <= 1: terminated();"

    with pytest.raises(UnsupportedBmcQuery, match="unsupported function 'sin'"):
        compile_bmc_query(model, query)


def test_compile_bmc_query_does_not_construct_a_solver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Compilation remains usable while property solvers are fail-fast patched."""

    def fail_solver(*args, **kwargs):
        pytest.fail("compile_bmc_query must not construct a solver")

    monkeypatch.setattr(z3, "Solver", fail_solver)
    monkeypatch.setattr(z3, "Optimize", fail_solver)

    formula = compile_bmc_query(_model(), 'check reach <= 1: active("Root.Done");')

    assert formula.kind == "reach"
    assert formula.polarity == "witness"


@pytest.mark.parametrize(
    ("query", "expected_outcome", "satisfied", "witness", "counterexample"),
    [
        (
            'check reach <= 1: active("Root");',
            "witness_found",
            True,
            True,
            False,
        ),
        (
            'check forbid <= 1: active("Root");',
            "property_violated",
            False,
            False,
            True,
        ),
    ],
    ids=["reach-witness", "safety-counterexample"],
)
def test_compiled_formula_is_ready_for_explicit_solving(
    query: str,
    expected_outcome: str,
    satisfied: bool,
    witness: bool,
    counterexample: bool,
) -> None:
    """The returned formula supports the next explicit solver step."""
    formula = compile_bmc_query(_model(), query)

    result = solve_bmc_property(formula)

    assert result.outcome == expected_outcome
    assert result.property_satisfied is satisfied
    assert result.witness_found is witness
    assert result.counterexample_found is counterexample


def test_facade_call_keeps_witness_verify_and_cli_modules_unloaded() -> None:
    """A fresh facade call loads formula layers but not later consumers."""
    code = """
import sys
from pyfcstm.bmc import compile_bmc_query
from pyfcstm.model import load_state_machine_from_text

model = load_state_machine_from_text("state Root;")
formula = compile_bmc_query(model, 'check reach <= 1: active("Root");')
bad = [
    name for name in sys.modules
    if name == "pyfcstm.bmc.witness"
    or name.startswith("pyfcstm.verify")
    or name.startswith("pyfcstm.entry")
]
print(formula.kind, formula.polarity, bad)
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.stdout.strip() == "reach witness []"
