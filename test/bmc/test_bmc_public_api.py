"""Public API tests for the BMC query model package."""

import importlib
import subprocess
import sys

import pytest


@pytest.mark.unittest
def test_bmc_public_api_exports_exact_names():
    """Top-level BMC imports expose the stable public surface."""
    bmc = importlib.import_module("pyfcstm.bmc")

    expected = {
        "BmcError",
        "BmcQueryParseError",
        "InvalidBmcQuery",
        "UnsupportedBmcQuery",
        "InvalidBmcEncoding",
        "InvalidBmcDomain",
        "BmcBuildError",
        "parse_bmc_query",
        "parse_bmc_num_expression",
        "parse_bmc_cond_expression",
        "parse_with_bmc_grammar_entry",
        "build_bmc_ast_from_parse_tree",
        "BmcExpr",
        "BmcNumExpr",
        "BmcCondExpr",
        "IntLiteral",
        "FloatLiteral",
        "BoolLiteral",
        "NameRef",
        "MathConst",
        "NumUnaryOp",
        "NumBinaryOp",
        "NumConditionalOp",
        "UFuncCall",
        "CondUnaryOp",
        "NumericComparison",
        "CondBinaryOp",
        "CondConditionalOp",
        "FrameVar",
        "Cycle",
        "Active",
        "Terminated",
        "Event",
        "Case",
        "Called",
        "InitialSpec",
        "BmcAssumption",
        "FrameAssumption",
        "EventAssumption",
        "EventCardinalityAssumption",
        "BmcProperty",
        "BmcQuery",
        "STATE_TERMINATE_ID",
        "STATE_DIAGNOSTIC_ID",
        "StateDomainEntry",
        "EventDomainEntry",
        "VarDomainEntry",
        "FrameRef",
        "StepRef",
        "EventInputRef",
        "BmcDomain",
        "build_bmc_domain",
        "TERMINATE_CASE_PATH",
        "DIAGNOSTIC_CASE_PATH",
        "MacroStepSource",
        "entry_source",
        "stable_leaf_source",
        "terminated_source",
        "diagnostic_source",
        "source_from_initial_spec",
        "BoolTemplate",
        "EventUse",
        "VarUpdate",
        "CycleCase",
        "PartitionCheckResult",
        "MacroStepFormal",
        "carry_var_updates",
        "var_update_for",
        "build_var_updates",
        "case_antecedent_condition",
        "terminated_absorb_case",
        "diagnostic_absorb_case",
        "build_fallback_case",
        "build_semantic_delta_case",
        "verify_boolean_partition",
        "verify_source_partition",
    }

    assert set(bmc.__all__) == expected
    lazy_names = {
        "STATE_TERMINATE_ID",
        "STATE_DIAGNOSTIC_ID",
        "StateDomainEntry",
        "EventDomainEntry",
        "VarDomainEntry",
        "FrameRef",
        "StepRef",
        "EventInputRef",
        "BmcDomain",
        "build_bmc_domain",
        "TERMINATE_CASE_PATH",
        "DIAGNOSTIC_CASE_PATH",
        "MacroStepSource",
        "entry_source",
        "stable_leaf_source",
        "terminated_source",
        "diagnostic_source",
        "source_from_initial_spec",
        "BoolTemplate",
        "EventUse",
        "VarUpdate",
        "CycleCase",
        "PartitionCheckResult",
        "MacroStepFormal",
        "carry_var_updates",
        "var_update_for",
        "build_var_updates",
        "case_antecedent_condition",
        "terminated_absorb_case",
        "diagnostic_absorb_case",
        "build_fallback_case",
        "build_semantic_delta_case",
        "verify_boolean_partition",
        "verify_source_partition",
    }
    function_names = {
        "parse_bmc_query",
        "parse_bmc_num_expression",
        "parse_bmc_cond_expression",
        "parse_with_bmc_grammar_entry",
        "build_bmc_ast_from_parse_tree",
        "entry_source",
        "stable_leaf_source",
        "terminated_source",
        "diagnostic_source",
        "source_from_initial_spec",
        "carry_var_updates",
        "var_update_for",
        "build_var_updates",
        "case_antecedent_condition",
        "terminated_absorb_case",
        "diagnostic_absorb_case",
        "build_fallback_case",
        "build_semantic_delta_case",
        "verify_boolean_partition",
        "verify_source_partition",
        "build_bmc_domain",
    }
    for name in expected - lazy_names - function_names:
        assert getattr(bmc, name).__name__ == name
    for name in function_names:
        assert callable(getattr(bmc, name))
    assert bmc.STATE_TERMINATE_ID == -1
    assert bmc.STATE_DIAGNOSTIC_ID == -2
    assert bmc.TERMINATE_CASE_PATH == "__terminate__"
    assert bmc.DIAGNOSTIC_CASE_PATH == "__diagnostic__"
    assert "BmcDomain" in dir(bmc)

    with pytest.raises(AttributeError, match="NoSuchBmcExport"):
        getattr(bmc, "NoSuchBmcExport")


@pytest.mark.unittest
def test_submodule_all_exports_are_exact():
    """Submodules keep precise export sets for parser and binder layers."""
    errors = importlib.import_module("pyfcstm.bmc.errors")
    ast = importlib.import_module("pyfcstm.bmc.ast")
    query = importlib.import_module("pyfcstm.bmc.query")
    parse = importlib.import_module("pyfcstm.bmc.parse")
    domain = importlib.import_module("pyfcstm.bmc.domain")
    source = importlib.import_module("pyfcstm.bmc.source")
    macro = importlib.import_module("pyfcstm.bmc.macro")

    assert set(errors.__all__) == {
        "BmcError",
        "BmcQueryParseError",
        "InvalidBmcQuery",
        "UnsupportedBmcQuery",
        "InvalidBmcEncoding",
        "InvalidBmcDomain",
        "BmcBuildError",
    }
    assert set(ast.__all__) == {
        "BmcExpr",
        "BmcNumExpr",
        "BmcCondExpr",
        "IntLiteral",
        "FloatLiteral",
        "BoolLiteral",
        "NameRef",
        "MathConst",
        "NumUnaryOp",
        "NumBinaryOp",
        "NumConditionalOp",
        "UFuncCall",
        "CondUnaryOp",
        "NumericComparison",
        "CondBinaryOp",
        "CondConditionalOp",
        "FrameVar",
        "Cycle",
        "Active",
        "Terminated",
        "Event",
        "Case",
        "Called",
    }
    assert set(query.__all__) == {
        "InitialSpec",
        "BmcAssumption",
        "FrameAssumption",
        "EventAssumption",
        "EventCardinalityAssumption",
        "BmcProperty",
        "BmcQuery",
    }
    assert set(parse.__all__) == {
        "parse_bmc_query",
        "parse_bmc_num_expression",
        "parse_bmc_cond_expression",
        "parse_with_bmc_grammar_entry",
        "build_bmc_ast_from_parse_tree",
    }
    assert set(domain.__all__) == {
        "STATE_TERMINATE_ID",
        "STATE_DIAGNOSTIC_ID",
        "StateDomainEntry",
        "EventDomainEntry",
        "VarDomainEntry",
        "FrameRef",
        "StepRef",
        "EventInputRef",
        "BmcDomain",
        "build_bmc_domain",
    }
    assert set(source.__all__) == {
        "TERMINATE_CASE_PATH",
        "DIAGNOSTIC_CASE_PATH",
        "MacroStepSource",
        "entry_source",
        "stable_leaf_source",
        "terminated_source",
        "diagnostic_source",
        "source_from_initial_spec",
    }
    assert set(macro.__all__) == {
        "BoolTemplate",
        "EventUse",
        "VarUpdate",
        "CycleCase",
        "PartitionCheckResult",
        "MacroStepFormal",
        "carry_var_updates",
        "var_update_for",
        "build_var_updates",
        "case_antecedent_condition",
        "terminated_absorb_case",
        "diagnostic_absorb_case",
        "build_fallback_case",
        "build_semantic_delta_case",
        "verify_boolean_partition",
        "verify_source_partition",
    }


@pytest.mark.unittest
def test_bmc_does_not_import_verify_registry():
    """The BMC root package remains independent from verify registry wiring."""
    bmc = importlib.import_module("pyfcstm.bmc")

    assert not hasattr(bmc, "REGISTRY")

    with pytest.raises(ModuleNotFoundError):
        importlib.import_module("pyfcstm.verify.bmc")


@pytest.mark.unittest
def test_bmc_import_does_not_load_verify_modules():
    """Importing BMC in a fresh process keeps verify internals unloaded."""
    code = (
        "import sys; "
        "import pyfcstm.bmc; "
        "bad = ["
        "name for name in sys.modules "
        "if name == 'z3' "
        "or name.startswith('pyfcstm.model') "
        "or name.startswith('pyfcstm.verify')"
        "]; "
        "print(bad)"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.stdout.strip() == "[]"
