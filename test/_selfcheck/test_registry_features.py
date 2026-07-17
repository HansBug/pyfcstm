"""Contract tests for functional self-check probes."""

import json
import runpy
from types import SimpleNamespace

import pytest

from pyfcstm._selfcheck import registry


def _raiser(error):
    """Return a callable that raises one deterministic expected error."""

    def raise_error(*args, **kwargs):
        del args, kwargs
        raise error

    return raise_error


def _assert_exception(outcome, reason, message):
    """Assert one probe preserves its semantic reason and traceback."""
    assert outcome.status == "FAIL"
    assert outcome.reason == reason
    assert "Traceback (most recent call last)" in outcome.exception
    assert message in outcome.exception
    assert message in outcome.evidence


@pytest.mark.unittest
def test_dsl_probe_covers_type_mismatch_semantic_mismatch_and_exception(monkeypatch):
    """The DSL probe diagnoses every branch around the real public parser."""
    from pyfcstm.dsl.error import GrammarParseError
    import pyfcstm.dsl.parse as dsl_parse

    real_parse = dsl_parse.parse_state_machine_dsl
    monkeypatch.setattr(dsl_parse, "parse_state_machine_dsl", lambda text: object())
    outcome = registry._core_dsl_parse()
    assert outcome.reason == "dsl_parse_failed"
    assert outcome.observed == "object"

    minimal = real_parse("state Root;")
    monkeypatch.setattr(dsl_parse, "parse_state_machine_dsl", lambda text: minimal)
    outcome = registry._core_dsl_parse()
    assert outcome.reason == "dsl_parse_failed"
    assert "Idle -> Done :: Go" in outcome.observed

    monkeypatch.setattr(
        dsl_parse,
        "parse_state_machine_dsl",
        _raiser(ValueError("dsl branch failed")),
    )
    _assert_exception(registry._core_dsl_parse(), "dsl_parse_failed", "dsl branch failed")
    monkeypatch.setattr(
        dsl_parse,
        "parse_state_machine_dsl",
        _raiser(GrammarParseError([])),
    )
    _assert_exception(
        registry._core_dsl_parse(), "dsl_parse_failed", "Found 0 errors"
    )


@pytest.mark.unittest
def test_model_probe_covers_type_mismatch_semantic_mismatch_and_exception(monkeypatch):
    """The model probe validates more than a loader return marker."""
    from pyfcstm.dsl.error import GrammarParseError
    import pyfcstm.model as model_module

    real_load = model_module.load_state_machine_from_text
    monkeypatch.setattr(model_module, "load_state_machine_from_text", lambda text: object())
    outcome = registry._core_model_build()
    assert outcome.reason == "model_invalid"
    assert outcome.observed == "object"

    minimal = real_load("state Root;")
    monkeypatch.setattr(model_module, "load_state_machine_from_text", lambda text: minimal)
    outcome = registry._core_model_build()
    assert outcome.reason == "model_invalid"
    assert "paths=" in outcome.observed

    monkeypatch.setattr(
        model_module,
        "load_state_machine_from_text",
        _raiser(ValueError("model branch failed")),
    )
    _assert_exception(registry._core_model_build(), "model_build_failed", "model branch failed")
    monkeypatch.setattr(
        model_module,
        "load_state_machine_from_text",
        _raiser(GrammarParseError([])),
    )
    _assert_exception(
        registry._core_model_build(), "model_build_failed", "Found 0 errors"
    )


@pytest.mark.unittest
def test_roundtrip_and_render_probes_cover_mismatch_and_exception(monkeypatch):
    """Roundtrip and renderer probes retain exact mismatch diagnostics."""
    from jinja2 import TemplateError
    import pyfcstm.model as model_module
    import pyfcstm.render as render_module

    real_parse_model = model_module.parse_dsl_node_to_state_machine
    minimal = model_module.load_state_machine_from_text("state Other;")
    monkeypatch.setattr(
        model_module,
        "parse_dsl_node_to_state_machine",
        lambda node: minimal,
    )
    outcome = registry._core_model_roundtrip()
    assert outcome.reason == "model_invalid"
    assert "plantuml_transition=False" in outcome.observed
    monkeypatch.setattr(
        model_module,
        "parse_dsl_node_to_state_machine",
        _raiser(ValueError("roundtrip branch failed")),
    )
    _assert_exception(
        registry._core_model_roundtrip(),
        "model_roundtrip_failed",
        "roundtrip branch failed",
    )
    monkeypatch.setattr(
        model_module, "parse_dsl_node_to_state_machine", real_parse_model
    )

    real_expr = render_module.render_expr_node
    monkeypatch.setattr(render_module, "render_expr_node", lambda *args, **kwargs: "wrong")
    outcome = registry._render_expr()
    assert outcome.reason == "render_failed"
    assert outcome.observed == "wrong"
    monkeypatch.setattr(
        render_module,
        "render_expr_node",
        _raiser(ValueError("expression branch failed")),
    )
    _assert_exception(registry._render_expr(), "render_failed", "expression branch failed")
    monkeypatch.setattr(
        render_module,
        "render_expr_node",
        _raiser(TemplateError("expression template failed")),
    )
    _assert_exception(
        registry._render_expr(), "render_failed", "expression template failed"
    )
    monkeypatch.setattr(render_module, "render_expr_node", real_expr)

    monkeypatch.setattr(render_module, "render_stmt_nodes", lambda *args, **kwargs: "wrong")
    outcome = registry._render_statement()
    assert outcome.reason == "render_failed"
    assert outcome.observed == "wrong"
    monkeypatch.setattr(
        render_module,
        "render_stmt_nodes",
        _raiser(ValueError("statement branch failed")),
    )
    _assert_exception(registry._render_statement(), "render_failed", "statement branch failed")
    monkeypatch.setattr(
        render_module,
        "render_stmt_nodes",
        _raiser(TemplateError("statement template failed")),
    )
    _assert_exception(
        registry._render_statement(), "render_failed", "statement template failed"
    )


@pytest.mark.unittest
def test_template_probes_cover_runtime_catalog_and_exception_failures(monkeypatch):
    """Packaged template probes diagnose missing outputs and runtime drift."""
    from jinja2 import TemplateError
    import pyfcstm.render as render_module
    import pyfcstm.template as template_module

    real_run_path = runpy.run_path
    real_renderer = render_module.StateMachineCodeRenderer
    monkeypatch.setattr(runpy, "run_path", lambda path: {})
    outcome = registry._template_python()
    assert outcome.reason == "template_invalid"
    assert outcome.expected == "RootMachine class"

    class BrokenMachine:
        current_state_path = ("Root", "Idle")
        vars = {"counter": 0}

        def cycle(self, events=None):
            del events

    monkeypatch.setattr(runpy, "run_path", lambda path: {"RootMachine": BrokenMachine})
    outcome = registry._template_python()
    assert outcome.reason == "template_invalid"
    assert outcome.observed == "state=Root.Idle counter=0"
    monkeypatch.setattr(runpy, "run_path", real_run_path)

    real_extract = template_module.extract_template
    monkeypatch.setattr(
        template_module,
        "extract_template",
        _raiser(OSError("template extraction failed")),
    )
    _assert_exception(
        registry._template_python(), "template_invalid", "template extraction failed"
    )
    monkeypatch.setattr(template_module, "extract_template", real_extract)

    class FailingRenderer:
        def __init__(self, template_dir):
            del template_dir

        def render(self, model, output_dir, clear_previous_directory=False):
            del model, output_dir, clear_previous_directory
            raise TemplateError("template render failed")

    monkeypatch.setattr(render_module, "StateMachineCodeRenderer", FailingRenderer)
    _assert_exception(
        registry._template_python(), "template_invalid", "template render failed"
    )
    monkeypatch.setattr(render_module, "StateMachineCodeRenderer", real_renderer)

    real_list = template_module.list_templates
    monkeypatch.setattr(template_module, "list_templates", lambda: [])
    outcome = registry._template_catalog()
    assert outcome.reason == "template_missing"

    class EmptyRenderer:
        def __init__(self, template_dir):
            del template_dir

        def render(self, model, output_dir, clear_previous_directory=False):
            del model, output_dir, clear_previous_directory

    monkeypatch.setattr(template_module, "list_templates", lambda: ["python"])
    monkeypatch.setattr(render_module, "StateMachineCodeRenderer", EmptyRenderer)
    outcome = registry._template_catalog()
    assert outcome.reason == "template_invalid"
    assert outcome.observed == "template=python"
    monkeypatch.setattr(render_module, "StateMachineCodeRenderer", real_renderer)

    monkeypatch.setattr(render_module, "StateMachineCodeRenderer", FailingRenderer)
    _assert_exception(
        registry._template_catalog(), "template_invalid", "template render failed"
    )
    monkeypatch.setattr(render_module, "StateMachineCodeRenderer", real_renderer)
    monkeypatch.setattr(
        template_module,
        "list_templates",
        _raiser(ValueError("template catalog failed")),
    )
    _assert_exception(
        registry._template_catalog(), "template_invalid", "template catalog failed"
    )
    monkeypatch.setattr(template_module, "list_templates", real_list)


@pytest.mark.unittest
def test_simulator_solver_and_verify_probes_cover_mismatch_and_exception(monkeypatch):
    """Runtime, solver, and verify probes expose semantic disagreement."""
    import click.testing as click_testing
    import pyfcstm.simulate as simulate_module
    import pyfcstm.solver as solver_module
    import pyfcstm.verify as verify_module

    class BrokenRuntime:
        current_state = SimpleNamespace(path=("Root", "Idle"))
        vars = {"counter": 0}

        def __init__(self, model):
            del model

        def cycle(self, events=None):
            del events

    real_runtime = simulate_module.SimulationRuntime
    monkeypatch.setattr(simulate_module, "SimulationRuntime", BrokenRuntime)
    outcome = registry._simulate_cycle()
    assert outcome.reason == "simulation_failed"
    assert "final=Root.Idle/0" in outcome.observed
    monkeypatch.setattr(
        simulate_module,
        "SimulationRuntime",
        _raiser(ValueError("simulation branch failed")),
    )
    _assert_exception(
        registry._simulate_cycle(), "simulation_failed", "simulation branch failed"
    )
    monkeypatch.setattr(simulate_module, "SimulationRuntime", real_runtime)

    real_solve = solver_module.solve
    monkeypatch.setattr(
        solver_module,
        "solve",
        lambda constraints, max_solutions=1: SimpleNamespace(
            status="unsat", solutions=[]
        ),
    )
    outcome = registry._solver_translation()
    assert outcome.reason == "solver_translation_failed"
    assert outcome.observed == "status=unsat x=None"
    monkeypatch.setattr(
        solver_module,
        "expr_to_z3",
        _raiser(ValueError("solver translation failed")),
    )
    _assert_exception(
        registry._solver_translation(),
        "solver_translation_failed",
        "solver translation failed",
    )
    monkeypatch.setattr(solver_module, "solve", real_solve)

    real_algorithms = verify_module.run_inspect_algorithms
    monkeypatch.setattr(verify_module, "run_inspect_algorithms", lambda *args, **kwargs: [])
    outcome = registry._verify_solve()
    assert outcome.reason == "verify_failed"
    monkeypatch.setattr(
        verify_module,
        "run_inspect_algorithms",
        _raiser(ValueError("verify branch failed")),
    )
    _assert_exception(registry._verify_solve(), "verify_failed", "verify branch failed")
    monkeypatch.setattr(verify_module, "run_inspect_algorithms", real_algorithms)

    real_invoke = click_testing.CliRunner.invoke
    failed = SimpleNamespace(
        exit_code=7,
        output="inspect stdout",
        stderr="inspect stderr",
        exc_info=(ValueError, ValueError("inspect failed"), None),
    )
    monkeypatch.setattr(click_testing.CliRunner, "invoke", lambda *args, **kwargs: failed)
    outcome = registry._verify_solve()
    assert outcome.reason == "cli_failed"
    assert "inspect stderr" in outcome.evidence
    assert "inspect failed" in outcome.exception

    incomplete = SimpleNamespace(
        exit_code=0, output=json.dumps({}), stderr="", exc_info=None
    )
    monkeypatch.setattr(
        click_testing.CliRunner, "invoke", lambda *args, **kwargs: incomplete
    )
    outcome = registry._verify_solve()
    assert outcome.reason == "cli_failed"
    assert outcome.observed == "None"
    monkeypatch.setattr(click_testing.CliRunner, "invoke", real_invoke)


def _cli_result(exit_code=0, output="", error=None):
    """Build a minimal Click result for deterministic failure injection."""
    exc_info = None if error is None else (type(error), error, None)
    return SimpleNamespace(
        exit_code=exit_code,
        output=output,
        stderr="captured stderr",
        exc_info=exc_info,
    )


@pytest.mark.unittest
def test_cli_probes_cover_nonzero_mismatch_and_exception_paths(monkeypatch):
    """Every top-level CLI probe retains command and exception evidence."""
    import click.testing as click_testing

    real_invoke = click_testing.CliRunner.invoke
    callbacks = (
        registry._cli_help,
        registry._cli_generate,
        registry._cli_simulate,
        registry._cli_plantuml,
    )
    for callback in callbacks:
        failed = _cli_result(5, "cli stdout", ValueError("cli command failed"))
        monkeypatch.setattr(
            click_testing.CliRunner, "invoke", lambda *args, **kwargs: failed
        )
        outcome = callback()
        assert outcome.reason == "cli_failed"
        assert "returncode=5" in outcome.evidence
        assert "cli command failed" in outcome.exception

    mismatch_outputs = (
        (registry._cli_help, "Usage: pyfcstm"),
        (registry._cli_generate, ""),
        (registry._cli_simulate, "Current State: Root.Idle"),
        (registry._cli_plantuml, "@startuml\n@enduml"),
    )
    for callback, output in mismatch_outputs:
        monkeypatch.setattr(
            click_testing.CliRunner,
            "invoke",
            lambda *args, output=output, **kwargs: _cli_result(0, output),
        )
        outcome = callback()
        assert outcome.status == "FAIL"
        assert outcome.reason == "cli_failed"

    for callback in callbacks:
        monkeypatch.setattr(
            click_testing.CliRunner,
            "invoke",
            _raiser(ValueError("CLI invocation raised")),
        )
        _assert_exception(callback(), "cli_failed", "CLI invocation raised")
    monkeypatch.setattr(click_testing.CliRunner, "invoke", real_invoke)


@pytest.mark.unittest
def test_bmc_parse_and_prepare_cover_mismatch_solver_start_and_exception(monkeypatch):
    """BMC parse and preparation remain typed and solve-free."""
    import z3
    from pyfcstm.bmc.errors import BmcBuildError, BmcQueryParseError
    import pyfcstm.bmc.parse as bmc_parse
    import pyfcstm.bmc.pipeline as bmc_pipeline

    real_parse = bmc_parse.parse_bmc_query
    wrong_query = real_parse('check forbid <= 2: active("Root");')
    monkeypatch.setattr(bmc_parse, "parse_bmc_query", lambda text: wrong_query)
    outcome = registry._bmc_query_parse()
    assert outcome.reason == "bmc_parse_failed"
    assert "kind=forbid bound=2" in outcome.observed
    monkeypatch.setattr(
        bmc_parse,
        "parse_bmc_query",
        _raiser(ValueError("BMC parse failed")),
    )
    _assert_exception(registry._bmc_query_parse(), "bmc_parse_failed", "BMC parse failed")
    monkeypatch.setattr(
        bmc_parse,
        "parse_bmc_query",
        _raiser(BmcQueryParseError("BMC query syntax failed")),
    )
    _assert_exception(
        registry._bmc_query_parse(),
        "bmc_parse_failed",
        "BMC query syntax failed",
    )
    monkeypatch.setattr(bmc_parse, "parse_bmc_query", real_parse)

    real_compile = bmc_pipeline.compile_bmc_query
    existing_solver = z3.Solver()
    wrong_formula = SimpleNamespace(
        kind="forbid", polarity="counterexample", solve_formula=object()
    )
    monkeypatch.setattr(
        bmc_pipeline, "compile_bmc_query", lambda model, query: wrong_formula
    )
    outcome = registry._bmc_prepare()
    assert outcome.reason == "bmc_prepare_failed"
    assert "kind=forbid" in outcome.observed

    monkeypatch.setattr(
        bmc_pipeline,
        "compile_bmc_query",
        lambda model, query: z3.Solver(),
    )
    outcome = registry._bmc_prepare()
    assert outcome.reason == "bmc_prepare_solved"
    assert "BMC preparation constructed a solver" in outcome.exception

    monkeypatch.setattr(
        bmc_pipeline,
        "compile_bmc_query",
        lambda model, query: existing_solver.check(),
    )
    outcome = registry._bmc_prepare()
    assert outcome.reason == "bmc_prepare_solved"
    assert "BMC preparation called Solver.check" in outcome.exception

    monkeypatch.setattr(
        bmc_pipeline,
        "compile_bmc_query",
        _raiser(ValueError("BMC prepare failed")),
    )
    _assert_exception(
        registry._bmc_prepare(), "bmc_prepare_failed", "BMC prepare failed"
    )
    monkeypatch.setattr(
        bmc_pipeline,
        "compile_bmc_query",
        _raiser(BmcBuildError("BMC build failed")),
    )
    _assert_exception(
        registry._bmc_prepare(), "bmc_prepare_failed", "BMC build failed"
    )
    monkeypatch.setattr(bmc_pipeline, "compile_bmc_query", real_compile)


def _bmc_result(status, satisfied, outcome, witness_found=False):
    return SimpleNamespace(
        status=status,
        property_satisfied=satisfied,
        outcome=outcome,
        witness_found=witness_found,
    )


@pytest.mark.unittest
def test_bmc_solve_and_closure_cover_polarity_cli_and_exception_paths(monkeypatch):
    """BMC solving diagnoses polarity, CLI JSON, and lazy-module failures."""
    import click.testing as click_testing
    from pyfcstm.bmc.errors import BmcBuildError
    import pyfcstm.bmc.pipeline as bmc_pipeline
    import pyfcstm.bmc.witness as bmc_witness

    real_solve = bmc_witness.solve_bmc_property
    monkeypatch.setattr(
        bmc_witness,
        "solve_bmc_property",
        lambda formula: _bmc_result("unknown", None, "incomplete"),
    )
    outcome = registry._bmc_solve()
    assert outcome.reason == "bmc_solve_failed"
    assert outcome.observed == "unknown/None/incomplete"

    sequence = [
        _bmc_result("sat", True, "witness_found", True),
        _bmc_result("sat", True, "witness_found", True),
        _bmc_result("unsat", True, "no_witness"),
    ]
    monkeypatch.setattr(
        bmc_witness, "solve_bmc_property", lambda formula: sequence.pop(0)
    )
    outcome = registry._bmc_solve()
    assert outcome.reason == "bmc_solve_failed"
    assert "terminated=sat/True/witness_found" in outcome.observed

    def good_sequence():
        return [
            _bmc_result("sat", True, "witness_found", True),
            _bmc_result("unsat", False, "no_witness"),
            _bmc_result("sat", False, "property_violated", True),
        ]
    sequence = good_sequence()
    monkeypatch.setattr(
        bmc_witness, "solve_bmc_property", lambda formula: sequence.pop(0)
    )
    failed = _cli_result(6, "bmc stdout", ValueError("BMC CLI failed"))
    monkeypatch.setattr(
        click_testing.CliRunner, "invoke", lambda *args, **kwargs: failed
    )
    outcome = registry._bmc_solve()
    assert outcome.reason == "cli_failed"
    assert "BMC CLI failed" in outcome.exception

    sequence = good_sequence()
    monkeypatch.setattr(
        bmc_witness, "solve_bmc_property", lambda formula: sequence.pop(0)
    )
    payload = {"schema_version": "wrong", "result": {}}
    monkeypatch.setattr(
        click_testing.CliRunner,
        "invoke",
        lambda *args, **kwargs: _cli_result(0, json.dumps(payload)),
    )
    outcome = registry._bmc_solve()
    assert outcome.reason == "bmc_solve_failed"
    assert "schema_version" in outcome.observed

    sequence = good_sequence()
    monkeypatch.setattr(
        bmc_witness, "solve_bmc_property", lambda formula: sequence.pop(0)
    )
    payload = {
        "result": {
            "status": "sat",
            "property_satisfied": True,
            "outcome": "witness_found",
        }
    }
    monkeypatch.setattr(
        click_testing.CliRunner,
        "invoke",
        lambda *args, **kwargs: _cli_result(0, json.dumps(payload)),
    )
    outcome = registry._bmc_solve()
    assert outcome.status == "PASS"

    real_compile = bmc_pipeline.compile_bmc_query
    monkeypatch.setattr(bmc_witness, "solve_bmc_property", real_solve)
    monkeypatch.setattr(
        bmc_pipeline,
        "compile_bmc_query",
        _raiser(ValueError("BMC compilation failed")),
    )
    _assert_exception(
        registry._bmc_solve(), "bmc_solve_failed", "BMC compilation failed"
    )
    monkeypatch.setattr(
        bmc_pipeline,
        "compile_bmc_query",
        _raiser(BmcBuildError("BMC solve build failed")),
    )
    _assert_exception(
        registry._bmc_solve(), "bmc_solve_failed", "BMC solve build failed"
    )
    monkeypatch.setattr(bmc_pipeline, "compile_bmc_query", real_compile)

    real_probe = registry._probe_import
    monkeypatch.setattr(
        registry,
        "_probe_import",
        lambda module: registry._fail("missing module", "import_unavailable"),
    )
    outcome = registry._bmc_closure()
    assert outcome.reason == "import_unavailable"
    monkeypatch.setattr(registry, "_probe_import", real_probe)
