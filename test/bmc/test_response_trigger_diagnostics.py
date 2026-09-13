import pytest
from pathlib import Path
import time
import z3
from click.testing import CliRunner

from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
from pyfcstm.bmc.properties import BmcPropertyFormula
from pyfcstm.bmc.errors import BmcBuildError
from pyfcstm.entry import pyfcstmcli
from pyfcstm.bmc.witness import _SolveBudget, _diagnose_response_trigger
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest


def _solve(query, *, enabled=True):
    machine = load_state_machine_from_text("def int temperature = 20; state Root;")
    return solve_bmc_property(
        compile_bmc_query(machine, query), diagnose_response_trigger=enabled
    )


def test_unreachable_trigger_is_reported_for_satisfied_response():
    result = _solve(
        "check response <= 8: trigger temperature > 80 -> within 2 false;"
    )
    assert result.outcome == "property_satisfied"
    assert result.trigger_diagnostic_status == "unsat"
    assert result.trigger_diagnostic_reason is None
    assert result.to_canonical()["trigger_diagnostic_status"] == "unsat"


def test_reachable_trigger_is_not_reported_as_vacuous():
    result = _solve(
        "check response <= 8: trigger temperature == 20 -> within 2 temperature == 20;"
    )
    assert result.outcome == "property_satisfied"
    assert result.trigger_diagnostic_status == "sat"


def test_diagnostic_does_not_change_default_payload():
    query = "check response <= 8: trigger temperature > 80 -> within 2 false;"
    result = _solve(query, enabled=False)
    assert result.outcome == "property_satisfied"
    assert result.trigger_diagnostic_status is None
    assert "trigger_diagnostic_status" not in result.to_canonical()


def test_non_satisfied_response_is_not_probed():
    result = _solve("check response <= 8: trigger temperature == 20 -> within 2 false;")
    assert result.outcome == "property_violated"
    assert result.trigger_diagnostic_status is None
    assert result.trigger_diagnostic_reason == "not_applicable"


def test_cli_option_publishes_trigger_diagnostic(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    model = tmp_path / "model.fcstm"
    query = tmp_path / "query.fbmcq"
    model.write_text("def int temperature = 20; state Root;", encoding="utf-8")
    query.write_text(
        "check response <= 8: trigger temperature > 80 -> within 2 false;",
        encoding="utf-8",
    )
    result = CliRunner().invoke(
        pyfcstmcli,
        [
            "bmc",
            "-i",
            str(model),
            "-q",
            str(query),
            "--json",
            "--diagnose-response-trigger",
        ],
    )
    assert result.exit_code == 0, result.output
    assert result.exception is None
    payload = __import__("json").loads(result.output)
    assert payload["result"]["trigger_diagnostic_status"] == "unsat"
    schema = __import__("json").loads(
        (Path(__file__).resolve().parents[2] / "docs/source/reference/bmc_results/bmc_cli.schema.json").read_text()
    )
    jsonschema.Draft202012Validator(schema).validate(payload)
    human = CliRunner().invoke(
        pyfcstmcli,
        [
            "bmc", "-i", str(model), "-q", str(query),
            "--diagnose-response-trigger", "--color", "never",
        ],
    )
    assert human.exit_code == 0
    assert "Response trigger: unreachable" in human.output


def test_diagnostic_rejects_non_boolean_flag():
    with pytest.raises(BmcBuildError, match="must be bool"):
        _diagnose_response_trigger(None, 1, _SolveBudget(None))


def test_formula_rejects_non_boolean_or_non_response_trigger_formula():
    formula = compile_bmc_query(
        load_state_machine_from_text("state Root;"),
        'check reach <= 1: active("Root");',
    )
    props = formula
    with pytest.raises(BmcBuildError, match="must be Boolean"):
        BmcPropertyFormula(
            core=props.core,
            kind=props.kind,
            polarity=props.polarity,
            objective_formula=props.objective_formula,
            solve_formula=props.solve_formula,
            incomplete_formula=props.incomplete_formula,
            incomplete_solve_formula=props.incomplete_solve_formula,
            trigger_reachability_formula=z3.IntVal(1),
        )
    with pytest.raises(BmcBuildError, match="response-only"):
        BmcPropertyFormula(
            core=props.core,
            kind=props.kind,
            polarity=props.polarity,
            objective_formula=props.objective_formula,
            solve_formula=props.solve_formula,
            incomplete_formula=props.incomplete_formula,
            incomplete_solve_formula=props.incomplete_solve_formula,
            trigger_reachability_formula=z3.BoolVal(True),
        )


def test_diagnostic_budget_exhaustion_is_explicit():
    result = _solve(
        "check response <= 8: trigger temperature > 80 -> within 2 false;",
        enabled=False,
    )
    budget = _SolveBudget(1)
    budget.deadline = time.monotonic() - 1
    diagnosed = _diagnose_response_trigger(result, True, budget)
    assert diagnosed.trigger_diagnostic_status == "timeout"


def test_human_report_mentions_reachable_trigger(tmp_path):
    model = tmp_path / "model.fcstm"
    query = tmp_path / "query.fbmcq"
    model.write_text("def int temperature = 20; state Root;", encoding="utf-8")
    query.write_text(
        "check response <= 8: trigger temperature == 20 -> within 2 temperature == 20;",
        encoding="utf-8",
    )
    result = CliRunner().invoke(
        pyfcstmcli,
        ["bmc", "-i", str(model), "-q", str(query), "--diagnose-response-trigger", "--color", "never"],
    )
    assert result.exit_code == 0
    assert "Response trigger: reachable" in result.output


def test_unknown_trigger_diagnostic_is_not_called_unreachable(monkeypatch):
    result = _solve(
        "check response <= 8: trigger temperature > 80 -> within 2 false;",
        enabled=False,
    )
    monkeypatch.setattr(
        "pyfcstm.bmc.witness._check_with_budget",
        lambda solver, budget: ("unknown", None, "incomplete arithmetic", 0.0, True),
    )
    diagnosed = _diagnose_response_trigger(result, True, _SolveBudget(None))
    assert diagnosed.trigger_diagnostic_status == "unknown"
    assert diagnosed.trigger_diagnostic_reason == "incomplete arithmetic"
