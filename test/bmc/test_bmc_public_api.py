"""Public API tests for the BMC query model package."""

import importlib
import json
import subprocess
import sys
from pathlib import Path

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
        "CallStepPoint",
        "CallStepSelector",
        "CallFilter",
        "CallCount",
        "Active",
        "Terminated",
        "Event",
        "Case",
        "Called",
        "InitialVariablePolicy",
        "InitialSpec",
        "BmcAssumption",
        "FrameAssumption",
        "EventAssumption",
        "EventCardinalityAssumption",
        "BmcProperty",
        "BmcQuery",
        "BmcBindingDiagnostic",
        "BoundReference",
        "BoundInitialSpec",
        "BoundAssumption",
        "BoundProperty",
        "BoundBmcQuery",
        "bind_bmc_query_structure",
        "bind_bmc_query",
        "STATE_INIT_ID",
        "STATE_TERMINATE_ID",
        "StateDomainEntry",
        "EventDomainEntry",
        "VarDomainEntry",
        "FrameRef",
        "StepRef",
        "EventInputRef",
        "BmcDomain",
        "build_bmc_domain",
        "INIT_CASE_PATH",
        "TERMINATE_CASE_PATH",
        "MacroStepSource",
        "init_source",
        "entry_source",
        "stable_leaf_source",
        "terminated_source",
        "source_from_initial_spec",
        "BoolTemplate",
        "EventUse",
        "GuardRequirement",
        "PriorityExclusion",
        "ActionBlock",
        "CycleCase",
        "PartitionCheckResult",
        "MacroStepFormal",
        "case_path_condition",
        "terminated_absorb_case",
        "build_fallback_case",
        "build_semantic_delta_case",
        "verify_boolean_partition",
        "verify_source_partition",
        "MacroExpansionOptions",
        "expand_macro_step_cases",
        "BmcOptions",
        "BmcPreparedContext",
        "BmcEngine",
        "prepare_bmc_query",
        "BmcAbstractCallRecord",
        "BmcTraceSymbols",
        "BmcCaseRelation",
        "BmcStepRelation",
        "BmcCoreFormula",
        "build_bmc_core_formula",
        "BmcPropertyFormula",
        "compile_bmc_property",
        "compile_bmc_query",
        "solve_bmc_property",
        "decode_bmc_result_trace",
        "decode_bmc_witness",
        "replay_bmc_witness",
        "BmcSolveStatus",
        "BmcEventDecodePolicy",
        "BmcFeasibilityCheck",
        "BmcFeasibilityRefinementCheck",
        "BmcFeasibilityResult",
        "BmcSolveResult",
        "BmcWitnessEvent",
        "BmcWitnessCallRecord",
        "BmcWitnessFrame",
        "BmcWitnessStep",
        "BmcWitnessTrace",
        "BmcRuntimeFrame",
        "BmcRuntimeStep",
        "BmcRuntimeTrace",
        "BmcReplayMismatch",
        "BmcReplayResult",
        "BmcConflictCore",
        "BmcConflictNarrative",
        "BmcConflictProof",
        "BmcProofNode",
        "BmcProofNodeKind",
        "BmcProofRuleId",
        "BmcProofVerificationMethod",
        "BmcProofInputMinimality",
        "BmcProofGraphMinimality",
        "BmcProofVerificationStatus",
        "BmcSourceRef",
        "BmcConflictCoreScope",
        "BmcConstraintRef",
        "BmcConstraintStage",
        "BmcCoreGranularity",
        "BmcCoreItem",
        "BmcCoreReduction",
        "BmcDerivationStatus",
        "BmcInfeasibilityClassification",
        "BmcInfeasibilityExplanation",
        "BmcInfeasibilityExplanationMode",
        "BmcInfeasibilityExplanationStatus",
        "BmcReasoningStep",
        "BmcReasoningStepKind",
        "BmcSemanticRole",
        "BmcSubsetMinimality",
    }

    assert set(bmc.__all__) == expected
    assert bmc._PIPELINE_EXPORTS == {"compile_bmc_query"}
    assert bmc._LAZY_EXPORT_MODULES["pyfcstm.bmc.pipeline"] is bmc._PIPELINE_EXPORTS
    lazy_names = {
        "STATE_INIT_ID",
        "STATE_TERMINATE_ID",
        "StateDomainEntry",
        "EventDomainEntry",
        "VarDomainEntry",
        "FrameRef",
        "StepRef",
        "EventInputRef",
        "BmcDomain",
        "build_bmc_domain",
        "INIT_CASE_PATH",
        "TERMINATE_CASE_PATH",
        "MacroStepSource",
        "init_source",
        "entry_source",
        "stable_leaf_source",
        "terminated_source",
        "source_from_initial_spec",
        "BoolTemplate",
        "EventUse",
        "GuardRequirement",
        "PriorityExclusion",
        "ActionBlock",
        "CycleCase",
        "PartitionCheckResult",
        "MacroStepFormal",
        "case_path_condition",
        "terminated_absorb_case",
        "build_fallback_case",
        "build_semantic_delta_case",
        "verify_boolean_partition",
        "verify_source_partition",
        "MacroExpansionOptions",
        "expand_macro_step_cases",
        "BmcOptions",
        "BmcPreparedContext",
        "BmcEngine",
        "prepare_bmc_query",
        "BmcAbstractCallRecord",
        "BmcTraceSymbols",
        "BmcCaseRelation",
        "BmcStepRelation",
        "BmcCoreFormula",
        "build_bmc_core_formula",
        "BmcPropertyFormula",
        "compile_bmc_property",
        "compile_bmc_query",
        "BmcSolveStatus",
        "BmcEventDecodePolicy",
        "BmcSolveResult",
        "BmcWitnessEvent",
        "BmcWitnessCallRecord",
        "BmcWitnessFrame",
        "BmcWitnessStep",
        "BmcWitnessTrace",
        "BmcRuntimeFrame",
        "BmcRuntimeStep",
        "BmcRuntimeTrace",
        "BmcReplayMismatch",
        "BmcReplayResult",
        "BmcConflictCore",
        "BmcConflictNarrative",
        "BmcSourceRef",
        "BmcConflictCoreScope",
        "BmcConstraintRef",
        "BmcConstraintStage",
        "BmcCoreGranularity",
        "BmcCoreItem",
        "BmcCoreReduction",
        "BmcDerivationStatus",
        "BmcProofNodeKind",
        "BmcProofRuleId",
        "BmcProofVerificationMethod",
        "BmcProofInputMinimality",
        "BmcProofGraphMinimality",
        "BmcProofVerificationStatus",
        "BmcInfeasibilityClassification",
        "BmcInfeasibilityExplanation",
        "BmcInfeasibilityExplanationMode",
        "BmcInfeasibilityExplanationStatus",
        "BmcReasoningStep",
        "BmcReasoningStepKind",
        "BmcSemanticRole",
        "BmcSubsetMinimality",
        "solve_bmc_property",
        "decode_bmc_witness",
        "replay_bmc_witness",
    }
    function_names = {
        "parse_bmc_query",
        "parse_bmc_num_expression",
        "parse_bmc_cond_expression",
        "parse_with_bmc_grammar_entry",
        "build_bmc_ast_from_parse_tree",
        "init_source",
        "entry_source",
        "stable_leaf_source",
        "terminated_source",
        "source_from_initial_spec",
        "case_path_condition",
        "terminated_absorb_case",
        "build_fallback_case",
        "build_semantic_delta_case",
        "verify_boolean_partition",
        "verify_source_partition",
        "build_bmc_domain",
        "expand_macro_step_cases",
        "prepare_bmc_query",
        "build_bmc_core_formula",
        "compile_bmc_property",
        "compile_bmc_query",
        "solve_bmc_property",
        "decode_bmc_witness",
        "replay_bmc_witness",
    }
    for name in expected - lazy_names - function_names:
        assert getattr(bmc, name).__name__ == name
    for name in function_names:
        assert callable(getattr(bmc, name))
    assert bmc.STATE_INIT_ID == -3
    assert bmc.STATE_TERMINATE_ID == -1
    assert bmc.INIT_CASE_PATH == "__init__"
    assert bmc.TERMINATE_CASE_PATH == "__terminate__"
    assert bmc.BmcEngine.__name__ == "BmcEngine"
    assert bmc.BmcOptions().__class__.__name__ == "BmcOptions"
    assert "BmcDomain" in dir(bmc)
    assert "BmcEngine" in dir(bmc)
    assert "compile_bmc_query" in dir(bmc)

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
    binding = importlib.import_module("pyfcstm.bmc.binding")
    source = importlib.import_module("pyfcstm.bmc.source")
    macro = importlib.import_module("pyfcstm.bmc.macro")
    expand = importlib.import_module("pyfcstm.bmc.expand")
    engine = importlib.import_module("pyfcstm.bmc.engine")
    relation = importlib.import_module("pyfcstm.bmc.relation")
    properties = importlib.import_module("pyfcstm.bmc.properties")
    pipeline = importlib.import_module("pyfcstm.bmc.pipeline")
    witness = importlib.import_module("pyfcstm.bmc.witness")

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
        "CallStepPoint",
        "CallStepSelector",
        "CallFilter",
        "CallCount",
        "Active",
        "Terminated",
        "Event",
        "Case",
        "Called",
    }
    assert set(query.__all__) == {
        "InitialVariablePolicy",
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
        "STATE_INIT_ID",
        "STATE_TERMINATE_ID",
        "StateDomainEntry",
        "EventDomainEntry",
        "VarDomainEntry",
        "FrameRef",
        "StepRef",
        "EventInputRef",
        "BmcDomain",
        "build_bmc_domain",
    }
    assert set(binding.__all__) == {
        "BmcBindingDiagnostic",
        "BoundReference",
        "BoundInitialSpec",
        "BoundAssumption",
        "BoundProperty",
        "BoundBmcQuery",
        "bind_bmc_query_structure",
        "bind_bmc_query",
    }
    assert set(source.__all__) == {
        "INIT_CASE_PATH",
        "TERMINATE_CASE_PATH",
        "MacroStepSource",
        "init_source",
        "entry_source",
        "stable_leaf_source",
        "terminated_source",
        "source_from_initial_spec",
    }
    assert set(macro.__all__) == {
        "BoolTemplate",
        "EventUse",
        "GuardRequirement",
        "PriorityExclusion",
        "ActionBlock",
        "CycleCase",
        "PartitionCheckResult",
        "MacroStepFormal",
        "case_path_condition",
        "terminated_absorb_case",
        "build_fallback_case",
        "build_semantic_delta_case",
        "verify_boolean_partition",
        "verify_source_partition",
    }
    assert set(expand.__all__) == {
        "MacroExpansionOptions",
        "expand_macro_step_cases",
    }
    assert set(engine.__all__) == {
        "BmcOptions",
        "BmcPreparedContext",
        "BmcEngine",
        "prepare_bmc_query",
    }
    assert set(relation.__all__) == {
        "BmcAbstractCallRecord",
        "BmcTraceSymbols",
        "BmcCaseRelation",
        "BmcStepRelation",
        "BmcCoreFormula",
        "build_bmc_core_formula",
    }
    assert set(properties.__all__) == {
        "BmcPropertyFormula",
        "compile_bmc_property",
    }
    assert pipeline.__all__ == ["compile_bmc_query"]
    assert set(witness.__all__) == {
        "BmcSolveStatus",
        "BmcEventDecodePolicy",
        "BmcFeasibilityCheck",
        "BmcFeasibilityRefinementCheck",
        "BmcFeasibilityResult",
        "BmcSolveResult",
        "BmcWitnessEvent",
        "BmcWitnessCallRecord",
        "BmcWitnessFrame",
        "BmcWitnessStep",
        "BmcWitnessTrace",
        "BmcRuntimeFrame",
        "BmcRuntimeStep",
        "BmcRuntimeTrace",
        "BmcReplayMismatch",
        "BmcReplayResult",
        "solve_bmc_property",
        "decode_bmc_result_trace",
        "decode_bmc_witness",
        "replay_bmc_witness",
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
    """Importing BMC in a fresh process keeps model and verify internals unloaded."""
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


@pytest.mark.unittest
def test_bmc_schema_freezes_role_channel_contract():
    """The published schema contains fail-closed role/channel branches."""
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "source"
        / "reference"
        / "bmc_results"
        / "bmc_cli.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    current_result = schema["$defs"]["currentResult"]
    role_aware_witness = schema["$defs"]["roleAwareWitness"]

    assert current_result["allOf"]
    assert role_aware_witness["allOf"]
    result_text = json.dumps(current_result["allOf"], sort_keys=True)
    witness_text = json.dumps(role_aware_witness["allOf"], sort_keys=True)
    for role in ("primary_witness", "primary_counterexample", "incomplete_suffix"):
        assert role in result_text
        assert role in witness_text
    assert '"const": "response"' in result_text
    assert '"const": "unsat"' in witness_text


@pytest.mark.unittest
def test_bmc_schema_uses_shape_discriminators_without_version_fields():
    """Legacy and role-aware branches are distinguished by payload shape."""
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "source"
        / "reference"
        / "bmc_results"
        / "bmc_cli.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema_text = json.dumps(schema, sort_keys=True)
    assert "schema_version" not in schema_text
    assert "model_role" not in schema["$defs"]["legacyWitness"]["properties"]
    assert {"model_role", "verdict"}.issubset(
        schema["$defs"]["roleAwareWitness"]["required"]
    )


@pytest.mark.unittest
def test_bmc_schema_freezes_feasibility_localization_contract():
    """The published schema records cumulative feasibility invariants."""
    schema_path = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "source"
        / "reference"
        / "bmc_results"
        / "bmc_cli.schema.json"
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    feasibility_text = json.dumps(
        schema["$defs"]["feasibility"]["allOf"], sort_keys=True
    )
    inconclusive_text = json.dumps(
        schema["$defs"]["checkedInconclusiveFeasibilityCheck"], sort_keys=True
    )

    assert '"infeasible_stage": {"const": "kernel"}' in feasibility_text
    assert '"infeasible_stage": {"const": "initialization"}' in feasibility_text
    assert '"infeasible_stage": {"const": "assumptions"}' in feasibility_text
    assert (
        '"localization_status": {"enum": ["not_checked", "unknown", "timeout"]}'
        in feasibility_text
    )
    assert '"status": {"enum": ["unknown", "timeout"]}' in inconclusive_text


@pytest.mark.unittest
def test_every_lazy_export_is_reachable_named_and_discoverable() -> None:
    """``__getattr__``, ``__all__`` and ``__dir__`` must agree on one name set.

    The three are maintained separately, so a layer can be wired into the lazy
    resolver and left out of discovery: the name then imports fine, which is
    what a test usually checks, while ``dir()``, tab completion, ``help()`` and
    autodoc cannot see it.  That is exactly what happened to the explanation
    layer -- resolvable and listed in ``__all__``, absent from ``__dir__``.
    """
    import pyfcstm.bmc as bmc

    lazy_names = set()
    for exports in bmc._LAZY_EXPORT_MODULES.values():
        lazy_names |= set(exports)

    listed = set(bmc.__all__)
    discoverable = set(dir(bmc))

    # Every lazily wired name is listed and discoverable.
    assert lazy_names - listed == set(), "lazy exports missing from __all__"
    assert lazy_names - discoverable == set(), "lazy exports missing from __dir__"
    # And every listed name actually resolves, so __all__ cannot promise a name
    # the resolver does not know.
    for name in sorted(listed):
        assert hasattr(bmc, name), name


@pytest.mark.unittest
def test_the_frozen_narrative_literals_are_public_types() -> None:
    """The narrative's two vocabularies are published types, not private tuples.

    Every other frozen vocabulary in this contract is exported as a ``Literal``
    a caller can annotate against -- reductions, minimality, roles, stages.  The
    two the narrative introduced were implemented as module-private tuples only,
    so a consumer typing a ``derivation_status`` had nothing to import and the
    exact-name test could not notice the omission.
    """
    from pyfcstm.bmc import BmcDerivationStatus, BmcReasoningStepKind

    assert BmcDerivationStatus is not None
    assert BmcReasoningStepKind is not None


@pytest.mark.unittest
def test_the_narrative_parameter_documents_that_it_is_published() -> None:
    """The class pydoc must not still say a narrative is refused.

    A caller reads ``:param narrative:`` to find out whether they may pass one.
    Publishing the slot while the docstring says it is rejected tells them the
    opposite of what the constructor does.
    """
    import inspect

    from pyfcstm.bmc import BmcInfeasibilityExplanation

    line = next(
        line
        for line in inspect.getdoc(BmcInfeasibilityExplanation).splitlines()
        if line.startswith(":param narrative:")
    )

    assert "rejected" not in line
    assert "Reserved for a later stage" not in line
