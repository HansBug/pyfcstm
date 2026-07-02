"""Public API tests for the BMC query model package."""

import importlib
import subprocess
import sys

import pytest


@pytest.mark.unittest
def test_bmc_public_api_exports_exact_names():
    """Top-level BMC imports expose the stable PR-1 public surface."""
    bmc = importlib.import_module("pyfcstm.bmc")

    expected = {
        "BmcError",
        "InvalidBmcQuery",
        "UnsupportedBmcQuery",
        "InvalidBmcEncoding",
        "BmcBuildError",
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
    }

    assert set(bmc.__all__) == expected
    for name in expected:
        assert getattr(bmc, name).__name__ == name


@pytest.mark.unittest
def test_submodule_all_exports_are_exact():
    """Submodules keep precise export sets for later parser and binder PRs."""
    errors = importlib.import_module("pyfcstm.bmc.errors")
    ast = importlib.import_module("pyfcstm.bmc.ast")
    query = importlib.import_module("pyfcstm.bmc.query")

    assert set(errors.__all__) == {
        "BmcError",
        "InvalidBmcQuery",
        "UnsupportedBmcQuery",
        "InvalidBmcEncoding",
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
        "print(any(name.startswith('pyfcstm.verify') for name in sys.modules))"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.stdout.strip() == "False"
