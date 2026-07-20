"""BMC engine preparation tests."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import replace

import pytest

import pyfcstm.bmc.engine as engine_module
from pyfcstm.bmc import (
    BmcBuildError,
    BmcEngine,
    BmcOptions,
    BmcPreparedContext,
    BmcQueryParseError,
    InvalidBmcQuery,
    bind_bmc_query,
    parse_bmc_query,
    prepare_bmc_query,
)
from pyfcstm.bmc.binding import BoundBmcQuery
from pyfcstm.bmc.domain import BmcDomain
from pyfcstm.model import StateMachine, load_state_machine_from_text


@pytest.fixture()
def engine_model() -> StateMachine:
    """Return a compact model with variables, events, and states for prepare."""
    return load_state_machine_from_text(
        """
        def int x = 0;
        def float pressure = 0.0;
        state Root {
            event Tick;
            event Reset;
            state Idle;
            state Done;
            [*] -> Idle;
            Idle -> Done :: Tick;
        }
        """
    )


@pytest.fixture()
def engine_query_text() -> str:
    """Return a representative query text with resolvable references."""
    return (
        "init cold;\n\n"
        "assume always: x >= 0;\n"
        'assume event("Root.Tick", 0) == true;\n\n'
        'check reach <= 1: active("Root.Done") or var("pressure") >= 0.0;'
    )


def _round_trip_bound_query(context: BmcPreparedContext) -> BoundBmcQuery:
    text = str(context.bound_query.to_ast_node())
    reparsed = parse_bmc_query(text)
    return bind_bmc_query(reparsed, domain=context.domain)


@pytest.mark.unittest
def test_engine_prepares_query_text_with_domain_references(
    engine_model: StateMachine, engine_query_text: str
) -> None:
    """Preparing text preserves source and resolves model/domain references."""
    context = BmcEngine(engine_model).prepare(engine_query_text)

    assert isinstance(context, BmcPreparedContext)
    assert context.model is engine_model
    assert context.source_text == engine_query_text
    assert context.bound == 1
    assert context.domain.bound == 1
    assert context.query.property.bound == 1
    assert context.bound_query.property.bound == 1
    assert context.options == BmcOptions()
    assert isinstance(context.domain, BmcDomain)
    assert isinstance(context.bound_query, BoundBmcQuery)

    references = {(ref.kind, ref.name): ref for ref in context.references}
    assert references[("state", "Root.Done")].resolved_id is not None
    assert references[("event", "Root.Tick")].resolved_id is not None
    assert references[("variable", "x")].declared_type == "int"
    assert references[("variable", "pressure")].declared_type == "float"

    canonical = context.to_canonical()
    assert list(canonical) == [
        "node",
        "options",
        "source_text",
        "query",
        "bound_query",
        "domain",
    ]
    assert canonical["node"] == "prepared_context"
    assert canonical["source_text"] == engine_query_text
    assert canonical["options"] == {"node": "bmc_options", "max_bound": None}
    assert canonical["domain"]["bound"] == 1
    json.dumps(canonical, sort_keys=True)

    rebound = _round_trip_bound_query(context)
    rebound_canonical = rebound.to_canonical()
    prepared_canonical = context.bound_query.to_canonical()
    for key in ("query", "initial", "assumptions", "property", "references"):
        assert rebound_canonical[key] == prepared_canonical[key]


@pytest.mark.unittest
def test_engine_prepares_ast_and_function_api_equivalently(
    engine_model: StateMachine,
) -> None:
    """AST and function-style preparation expose equivalent canonical output."""
    query = parse_bmc_query('check reach <= 2: active("Root.Done");')
    options = BmcOptions(max_bound=2)

    engine = BmcEngine(engine_model, options)
    method_context = engine.prepare(query)
    function_context = prepare_bmc_query(engine_model, query, options=options)

    assert engine.model is engine_model
    assert engine.options == options
    assert method_context.source_text is None
    assert function_context.source_text is None
    assert method_context.to_canonical() == function_context.to_canonical()
    assert method_context.query.to_canonical() == query.to_canonical()
    assert (
        method_context.bound_query.to_ast_node().to_canonical() == query.to_canonical()
    )


@pytest.mark.unittest
def test_prepare_call_options_override_engine_default(
    engine_model: StateMachine,
) -> None:
    """Per-call options replace default engine options instead of merging them."""
    query = parse_bmc_query('check reach <= 2: active("Root.Done");')
    engine = BmcEngine(engine_model, BmcOptions(max_bound=1))

    with pytest.raises(BmcBuildError, match="query_bound=2.*max_bound=1"):
        engine.prepare(query)

    context = engine.prepare(query, options=BmcOptions(max_bound=2))

    assert context.options == BmcOptions(max_bound=2)
    assert context.bound == 2


@pytest.mark.unittest
@pytest.mark.parametrize("max_bound", [0, -1, True, False, 1.5, "3"])
def test_bmc_options_reject_invalid_max_bound(max_bound) -> None:
    """Options reject non-positive, boolean, and non-integer max bounds."""
    with pytest.raises(BmcBuildError, match="max_bound"):
        BmcOptions(max_bound=max_bound)


@pytest.mark.unittest
def test_bmc_options_accept_none_and_positive_bounds() -> None:
    """Options keep a JSON-stable canonical shape for valid bounds."""
    assert BmcOptions().to_canonical() == {"node": "bmc_options", "max_bound": None}
    assert BmcOptions(max_bound=3).to_canonical() == {
        "node": "bmc_options",
        "max_bound": 3,
    }


@pytest.mark.unittest
@pytest.mark.parametrize("model", [None, object()])
def test_engine_rejects_invalid_model(model) -> None:
    """Engine construction rejects non-state-machine model objects."""
    with pytest.raises(BmcBuildError, match="model must be StateMachine"):
        BmcEngine(model)


@pytest.mark.unittest
def test_engine_rejects_invalid_options(engine_model: StateMachine) -> None:
    """Engine and prepare calls reject non-BmcOptions option objects."""
    with pytest.raises(BmcBuildError, match="options must be BmcOptions"):
        BmcEngine(engine_model, options=object())

    with pytest.raises(BmcBuildError, match="options must be BmcOptions"):
        BmcEngine(engine_model).prepare(
            'check reach <= 1: active("Root.Done");',
            options=object(),
        )


@pytest.mark.unittest
def test_engine_rejects_invalid_query_input(engine_model: StateMachine) -> None:
    """Prepare accepts only query text or parser-independent BmcQuery objects."""
    with pytest.raises(BmcBuildError, match="query must be a str or BmcQuery"):
        BmcEngine(engine_model).prepare(object())


@pytest.mark.unittest
@pytest.mark.parametrize("query_source_path", ["", 123])
def test_engine_rejects_invalid_query_source_path(
    engine_model: StateMachine, query_source_path
) -> None:
    """AST preparation rejects empty and non-string query source paths."""
    query = parse_bmc_query('check reach <= 1: active("Root.Done");')

    with pytest.raises(BmcBuildError, match="query_source_path"):
        BmcEngine(engine_model).prepare(query, query_source_path=query_source_path)


@pytest.mark.unittest
def test_prepared_context_rejects_invalid_query_source_path(
    engine_model: StateMachine,
) -> None:
    """The public prepared-context constructor validates explicit metadata."""
    prepared = BmcEngine(engine_model).prepare('check reach <= 1: active("Root.Done");')

    with pytest.raises(BmcBuildError, match="query_source_path"):
        BmcPreparedContext(
            model=prepared.model,
            query=prepared.query,
            bound_query=prepared.bound_query,
            domain=prepared.domain,
            options=prepared.options,
            source_text=prepared.source_text,
            query_source_path="",
        )


@pytest.mark.unittest
def test_engine_inherits_source_path_from_parsed_query(
    engine_model: StateMachine,
) -> None:
    """AST preparation keeps a source path already attached by the parser."""
    query = parse_bmc_query(
        'check reach <= 1: active("Root.Done");', source_path="query.fbmcq"
    )

    context = BmcEngine(engine_model).prepare(query)

    assert context.query_source_path == "query.fbmcq"


@pytest.mark.unittest
def test_engine_query_source_path_overrides_ast_metadata(
    engine_model: StateMachine,
) -> None:
    """An explicit source path replaces stale AST path metadata."""
    query = parse_bmc_query(
        'check reach <= 1: active("Root.Done");', source_path="old.fbmcq"
    )

    context = BmcEngine(engine_model).prepare(query, query_source_path="new.fbmcq")

    assert context.query_source_path == "new.fbmcq"
    assert context.query._source_path == "new.fbmcq"
    assert dict(context.query._source_spans).get(id(context.query)) is not None


@pytest.mark.unittest
def test_prepared_context_inherits_source_path_from_query_metadata(
    engine_model: StateMachine,
) -> None:
    """Direct context construction applies the query metadata fallback."""
    query = parse_bmc_query(
        'check reach <= 1: active("Root.Done");', source_path="query.fbmcq"
    )
    prepared = BmcEngine(engine_model).prepare(query)

    context = BmcPreparedContext(
        model=prepared.model,
        query=prepared.query,
        bound_query=prepared.bound_query,
        domain=prepared.domain,
        options=prepared.options,
    )

    assert context.query_source_path == "query.fbmcq"

    reused_registry = BmcPreparedContext(
        model=prepared.model,
        query=prepared.query,
        bound_query=prepared.bound_query,
        domain=prepared.domain,
        options=prepared.options,
        _source_registry=prepared._source_registry,
    )

    assert reused_registry._source_registry is prepared._source_registry


@pytest.mark.unittest
def test_engine_propagates_parse_errors_before_prepare(
    engine_model: StateMachine,
) -> None:
    """Invalid query text fails as a parse error before binding or domain work."""
    with pytest.raises(BmcQueryParseError):
        BmcEngine(engine_model).prepare("check reach <= ;")


@pytest.mark.unittest
def test_engine_rejects_malformed_query_before_domain_build(
    monkeypatch: pytest.MonkeyPatch, engine_model: StateMachine
) -> None:
    """Structure binding runs before domain construction for forged queries."""
    query = parse_bmc_query('check reach <= 1: active("Root.Done");')
    object.__setattr__(query, "assumptions", "not-a-sequence")

    def fail_build_domain(model, bound):
        pytest.fail("build_bmc_domain must not run before structure binding")

    monkeypatch.setattr(engine_module, "build_bmc_domain", fail_build_domain)

    with pytest.raises(InvalidBmcQuery, match="assumptions"):
        BmcEngine(engine_model).prepare(query)


@pytest.mark.unittest
def test_engine_reports_model_reference_errors_as_query_diagnostics(
    engine_model: StateMachine,
) -> None:
    """Unknown model references fail as InvalidBmcQuery diagnostics."""
    with pytest.raises(InvalidBmcQuery) as excinfo:
        BmcEngine(engine_model).prepare('check reach <= 1: active("Root.Missing");')

    diagnostic = getattr(excinfo.value, "diagnostic", None)
    assert diagnostic is not None
    assert diagnostic.code == "unknown_state"
    assert diagnostic.path == "property.predicate"


@pytest.mark.unittest
def test_prepared_context_rejects_invalid_field_types(
    engine_model: StateMachine,
) -> None:
    """Prepared context construction guards every public handoff field."""
    valid = BmcEngine(engine_model).prepare('check reach <= 1: active("Root.Done");')
    invalid_fields = {
        "model": object(),
        "query": object(),
        "bound_query": object(),
        "domain": object(),
        "options": object(),
        "source_text": object(),
    }

    for field_name, invalid_value in invalid_fields.items():
        kwargs = {
            "model": valid.model,
            "query": valid.query,
            "bound_query": valid.bound_query,
            "domain": valid.domain,
            "options": valid.options,
            "source_text": valid.source_text,
        }
        kwargs[field_name] = invalid_value
        with pytest.raises(BmcBuildError, match=field_name):
            BmcPreparedContext(**kwargs)

    with pytest.raises(BmcBuildError, match="source_text"):
        replace(valid, source_text=123)


@pytest.mark.unittest
def test_prepared_context_rejects_mismatched_handoff_objects(
    engine_model: StateMachine,
) -> None:
    """Prepared context rejects inconsistent query, bound query, and domain data."""
    query_one = parse_bmc_query('check reach <= 1: active("Root.Done");')
    query_two = parse_bmc_query('check reach <= 2: active("Root.Done");')
    context_one = BmcEngine(engine_model).prepare(query_one)
    context_two = BmcEngine(engine_model).prepare(query_two)
    same_bound_other_query = BmcEngine(engine_model).prepare(
        'check forbid <= 1: active("Root.Idle");'
    )

    with pytest.raises(BmcBuildError, match="domain bound"):
        BmcPreparedContext(
            context_one.model,
            context_one.query,
            context_one.bound_query,
            context_two.domain,
            context_one.options,
            context_one.source_text,
        )

    with pytest.raises(BmcBuildError, match="bound query bound"):
        BmcPreparedContext(
            context_one.model,
            context_one.query,
            context_two.bound_query,
            context_one.domain,
            context_one.options,
            context_one.source_text,
        )

    with pytest.raises(BmcBuildError, match="bound query source"):
        BmcPreparedContext(
            context_one.model,
            context_one.query,
            same_bound_other_query.bound_query,
            context_one.domain,
            context_one.options,
            context_one.source_text,
        )


@pytest.mark.unittest
def test_engine_import_boundaries_are_lazy_and_solver_independent() -> None:
    """Root BMC imports stay parser-only while engine access stays solver-free."""
    root_code = (
        "import sys; "
        "import pyfcstm.bmc; "
        "bad = [name for name in sys.modules "
        "if name == 'z3' "
        "or name == 'pyfcstm.bmc.engine' "
        "or name.startswith('pyfcstm.model') "
        "or name.startswith('pyfcstm.verify') "
        "or name.startswith('pyfcstm.solver')]; "
        "print(bad)"
    )
    engine_code = (
        "import sys; "
        "import pyfcstm.bmc as bmc; "
        "assert bmc.BmcEngine.__name__ == 'BmcEngine'; "
        "bad = [name for name in sys.modules "
        "if name == 'z3' "
        "or name.startswith('pyfcstm.verify') "
        "or name.startswith('pyfcstm.solver') "
        "or name in {"
        "'pyfcstm.bmc.macro', 'pyfcstm.bmc.source', "
        "'pyfcstm.bmc.relation', 'pyfcstm.bmc.properties', "
        "'pyfcstm.bmc.witness'"
        "}]; "
        "print('engine_loaded', 'pyfcstm.bmc.engine' in sys.modules); "
        "print('model_loaded', any(name.startswith('pyfcstm.model') for name in sys.modules)); "
        "print('bad', bad)"
    )

    root_result = subprocess.run(
        [sys.executable, "-c", root_code],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    engine_result = subprocess.run(
        [sys.executable, "-c", engine_code],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert root_result.stdout.strip() == "[]"
    assert engine_result.stdout.splitlines() == [
        "engine_loaded True",
        "model_loaded True",
        "bad []",
    ]


@pytest.mark.unittest
def test_prepare_does_not_load_later_bmc_or_solver_layers() -> None:
    """Preparation stays independent from macro, relation, solver, and verify."""
    code = r'''
import sys
from pyfcstm.bmc import BmcEngine
from pyfcstm.model import load_state_machine_from_text

model = load_state_machine_from_text("""
state Root {
    state A;
    [*] -> A;
}
""")
BmcEngine(model).prepare('check reach <= 1: active("Root.A");')
bad = [
    name for name in sys.modules
    if name == "z3"
    or name.startswith("pyfcstm.verify")
    or name.startswith("pyfcstm.solver")
    or name in {
        "pyfcstm.bmc.macro",
        "pyfcstm.bmc.source",
        "pyfcstm.bmc.relation",
        "pyfcstm.bmc.properties",
        "pyfcstm.bmc.witness",
    }
]
print(bad)
'''
    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.stdout.strip() == "[]"
