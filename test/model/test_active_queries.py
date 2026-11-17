"""Activity queries bind to States and lower without changing named actions."""

import pytest

from pyfcstm.model import Configuration, load_state_machine_from_file, load_state_machine_from_text
from pyfcstm.model.expr import parse_expr
from pyfcstm.utils import ModelValidationError

pytestmark = pytest.mark.unittest

SOURCE = '''def int value = 0;
state Root {
    state Job {
        enter Start { value = 1; }
        exit Stop { value = 2; }
        region Worker {
            state On { enter { if [active("Root.Job")] { value = 3; } } }
            state Off;
            [*] -> On;
            On -> Off : if [active("Root.Job.Worker.On") && active("Root.Job")];
            Off -> On :: Go + [active("Root.Job.Worker.On")];
        }
    }
    state Idle { enter ref /Job.Start; exit ref /Job.Stop; }
    [*] -> Idle;
    Idle -> Job : if [!active("Root.Job")];
}'''


def test_active_queries_are_deduplicated_and_flags_use_configuration():
    machine = load_state_machine_from_text(SOURCE)
    queries = {'.'.join(item.state_path): item for item in machine.active_queries}
    assert list(queries) == ['Root.Job', 'Root.Job.Worker.On']
    assert set(machine.defines) == {'value', *(item.variable_name for item in queries.values())}
    active = Configuration.parse(machine, 'Root.Job{Worker: On}')
    idle = Configuration.parse(machine, 'Root.Idle')
    assert machine.active_variables(active) == {item.variable_name: 1 for item in queries.values()}
    assert machine.active_variables(idle) == {item.variable_name: 0 for item in queries.values()}
    owner_pending = Configuration.parse(machine, 'Root.Job', mode='initialization')
    assert machine.active_variables(owner_pending) == {
        queries['Root.Job'].variable_name: 1, queries['Root.Job.Worker.On'].variable_name: 0,
    }
    guard = machine.root_state.substates['Job'].regions['Worker'].transitions[1].guard
    assert guard(**machine.active_variables(active)) is True
    assert guard(**machine.active_variables(idle)) is False


def test_flag_actions_surround_user_actions_without_polluting_named_refs():
    machine = load_state_machine_from_text(SOURCE)
    job, idle = machine.root_state.substates.values()
    flag = machine.active_queries[0].variable_name
    assert [action.name for action in job.on_enters] == [None, 'Start']
    assert [action.name for action in job.on_exits] == ['Stop', None]
    assert job.on_enters[0].parent is job
    assert job.on_exits[-1].parent is job
    assert job.on_enters[0].operations[0].var_name == flag
    assert job.on_enters[0].operations[0].expr() == 1
    assert job.on_exits[-1].operations[0].expr() == 0
    assert idle.on_enters[0].ref is job.named_functions['Start']
    assert idle.on_exits[0].ref is job.named_functions['Stop']
    assert [item.var_name for item in idle.on_enters[0].ref.operations] == ['value']
    assert [item.var_name for item in idle.on_exits[0].ref.operations] == ['value']


def test_authored_view_preserves_queries_and_history_without_generated_actions():
    machine = load_state_machine_from_text('''def int value = 0;
state Root {
    state Group {
        state On { exit End { value = 1; } }
        [*] -> On;
        [H] -> On;
    }
    state Idle;
    [*] -> Idle;
    Idle -> Group.[H] : if [!active("Root.Group.On")];
}''')
    assert machine.history_owners and machine.active_queries
    group = machine.root_state.substates['Group']
    leaf = group.substates['On']
    assert leaf.on_exits[-1].operations[0].var_name == machine.active_queries[0].variable_name
    authored = machine._as_written()
    assert authored is machine._as_written()
    assert list(authored.defines) == ['value']
    assert 'active("Root.Group.On")' in str(authored.to_ast_node())
    assert authored.root_state.transitions[1].target_history == 'shallow'
    assert authored.history_owners[0].owner_path == ('Root', 'Group')
    assert [action.name for action in authored.root_state.substates['Group'].substates['On'].on_exits] == ['End']


def test_query_lowering_covers_actions_conditionals_aspects_and_initial_guards():
    machine = load_state_machine_from_text('''input int sampled;
def int value = 0;
state Root {
    enter { value = (active("Root")) ? 1 : 2; }
    during before { if [active("Root")] { value = 3; } else { value = 4; } }
    >> during after { if [!active("Root.A")] { value = 5; } }
    state A { during { if [active("/A")] { value = 6; } } }
    [*] -> A : if [active("Root") && sampled >= 0];
    A -> [*] effect { if [active("Root.A")] { value = 7; } }
}''')
    assert [item.state_path for item in machine.active_queries] == [('Root',), ('Root', 'A')]
    assert 'active(' not in str(machine.to_ast_node())
    assert 'active(' in str(machine._as_written().to_ast_node())


@pytest.mark.parametrize('target,reason', [
    ('Root.Missing', 'not_found'), ('Root.Worker', 'region'),
    ('Root.Worker.Gate', 'pseudo'), ('Root..Worker.On', 'invalid_path'),
    ('On', 'invalid_path'), ('', 'invalid_path'),
])
@pytest.mark.parametrize('collect', [False, True])
def test_invalid_active_target_has_structured_source_diagnostic(target, reason, collect):
    source = '''state Root { region Worker {
        state On; pseudo state Gate; [*] -> On;
        On -> [*] : if [active("%s")];
    } }''' % target
    if collect:
        machine, diagnostics = load_state_machine_from_text(source, collect=True)
        assert machine is None
    else:
        with pytest.raises(ModelValidationError) as error:
            load_state_machine_from_text(source)
        diagnostics = error.value.diagnostics
    assert len(diagnostics) == 1
    assert diagnostics[0].code == 'E_ACTIVE_QUERY_TARGET'
    assert diagnostics[0].refs['reason'] == reason
    assert diagnostics[0].span.line == 3


def test_activity_flag_names_avoid_user_definitions_deterministically():
    original = 'state Root { during { if [active("Root")] {} } }'
    first = load_state_machine_from_text(original)
    name = first.active_queries[0].variable_name
    source = 'def int %s = 5;\n%s' % (name, original)
    second = load_state_machine_from_text(source)
    third = load_state_machine_from_text(source)
    assert second.active_queries == third.active_queries
    assert second.active_queries[0].variable_name != name
    assert second.defines[name].init() == 5


@pytest.mark.parametrize('body', [
    'enter Named { __active_Root = 0; __active_Root_2 = 1; }',
    'exit { __active_Root = 0; __active_Root_2 = 1; }',
    'state A; [*] -> A; during before { if [1 == 1] { __active_Root = 0; } '
    'else { __active_Root_2 = 1; } }',
    'state A; [*] -> A; A -> [*] effect { __active_Root = 0; __active_Root_2 = 1; }',
    'region Worker { >> during after { __active_Root = 0; } '
    'state A; [*] -> A effect { __active_Root_2 = 1; } }',
])
def test_activity_flags_do_not_capture_block_local_temporaries(body):
    source = 'state Root { enter Query { if [active("Root")] {} } %s }' % body
    model = load_state_machine_from_text(source)
    assert model.active_queries[0].variable_name == '__active_Root_3'
    assert list(model.defines) == ['__active_Root_3']
    assert '__active_Root = 0;' in str(model.to_ast_node())
    assert '__active_Root_2 = 1;' in str(model.to_ast_node())
    assert '__active_Root_3 != 0' in str(model.to_ast_node())


def test_imported_queries_rebase_internal_paths_and_bind_explicit_host_paths(tmp_path):
    (tmp_path / 'module.fcstm').write_text('''state Module { during {
        __active_Host_First = 0;
        if [active("Module") && active("Host.Idle")] {}
    } }''', encoding='utf-8')
    host = tmp_path / 'host.fcstm'
    host.write_text('''state Host {
        import "module.fcstm" as First;
        import "module.fcstm" as Second;
        state Idle;
        [*] -> Idle;
    }''', encoding='utf-8')
    model = load_state_machine_from_file(host)
    queries = {item.state_path: item.variable_name for item in model.active_queries}
    assert set(queries) == {('Host', 'Idle'), ('Host', 'First'), ('Host', 'Second')}
    assert queries[('Host', 'First')] != '__active_Host_First'
    assert '__active_Host_First' not in model.defines
    config = Configuration.parse(model, 'Host.Idle')
    assert model.active_variables(config) == {
        name: int(path == ('Host', 'Idle')) for path, name in queries.items()
    }


def test_repeated_nested_imports_rebase_activity_paths_and_source(tmp_path):
    child = tmp_path / 'child.fcstm'
    child.write_text('''state Child { region Worker {
        state On;
        [*] -> On;
        On -> [*] : if [active("Child.Worker.On")];
    } }''', encoding='utf-8')
    (tmp_path / 'middle.fcstm').write_text('state Middle { import "child.fcstm" as Inner; [*] -> Inner; }', encoding='utf-8')
    host = tmp_path / 'host.fcstm'
    host.write_text('''state Host {
        import "middle.fcstm" as First;
        import "middle.fcstm" as Second;
        [*] -> First;
    }''', encoding='utf-8')
    machine = load_state_machine_from_file(host)
    assert [item.state_path for item in machine.active_queries] == [
        ('Host', 'First', 'Inner', 'Worker', 'On'),
        ('Host', 'Second', 'Inner', 'Worker', 'On'),
    ]
    authored = machine._as_written()
    query = authored.root_state.substates['First'].substates['Inner'].regions['Worker'].transitions[1].guard
    assert query.path == 'Host.First.Inner.Worker.On'
    assert query._source_path == str(child)
    assert query._span.line == 4


@pytest.mark.parametrize('text', ['active("Root")', '!active("Root")', '(active("Root")) ? 1 : 0'])
def test_unbound_query_is_inspectable_but_cannot_execute(text):
    expression = parse_expr(text)
    assert 'active("Root")' in str(expression)
    with pytest.raises(TypeError, match='ActiveStateQuery'):
        expression()


def test_active_query_is_not_allowed_in_persistent_initializer():
    from pyfcstm.dsl import node as ast
    from pyfcstm.model import parse_dsl_node_to_state_machine

    program = ast.StateMachineDSLProgram(
        [ast.DefAssignment('value', 'int', ast.ActiveStateQuery('Root'))],
        ast.StateDefinition('Root'),
    )
    with pytest.raises(ModelValidationError) as error:
        parse_dsl_node_to_state_machine(program)
    assert error.value.diagnostics[0].code == 'E_ACTIVE_QUERY_TARGET'
    assert error.value.diagnostics[0].refs['reason'] == 'initializer'


@pytest.mark.parametrize('consumer', ['simulate', 'bmc', 'plantuml', 'diagram'])
def test_active_only_models_remain_refused_by_execution_consumers(consumer):
    machine = load_state_machine_from_text('state Root { during { if [active("Root")] {} } }')
    with pytest.raises(ModelValidationError) as error:
        if consumer == 'simulate':
            from pyfcstm.simulate import SimulationRuntime
            SimulationRuntime(machine)
        elif consumer == 'bmc':
            from pyfcstm.bmc import build_bmc_domain
            build_bmc_domain(machine, bound=1)
        elif consumer == 'plantuml':
            machine.to_plantuml()
        else:
            machine.diagram()
    assert error.value.diagnostics[0].code == 'E_UNSUPPORTED_FEATURE'
    assert error.value.diagnostics[0].refs['feature'] == 'active'


@pytest.mark.parametrize('imported', [False, True])
def test_invalid_query_shared_by_combo_fields_is_reported_once(tmp_path, imported):
    source = 'state Root { state On; [*] -> On; On -> [*] : [active("Root.Missing")]; }'
    if imported:
        (tmp_path / 'child.fcstm').write_text(source, encoding='utf-8')
        source = 'state Host { import "child.fcstm" as Child; [*] -> Child; }'
    host = tmp_path / 'host.fcstm'
    host.write_text(source, encoding='utf-8')
    model, diagnostics = load_state_machine_from_file(host, collect=True)
    assert model is None
    assert [item.code for item in diagnostics] == ['E_ACTIVE_QUERY_TARGET']
    assert diagnostics[0].refs['source_path'] == str(tmp_path / ('child.fcstm' if imported else 'host.fcstm'))


def test_configuration_from_another_machine_is_not_used_for_flags():
    first = load_state_machine_from_text('state Root;')
    second = load_state_machine_from_text('state Root;')
    with pytest.raises(ValueError, match='different'):
        first.active_variables(Configuration.parse(second, 'Root'))
    assert first.active_variables(Configuration.parse(first, 'Root')) == {}


@pytest.mark.parametrize('collect', [False, True])
def test_ordinary_identifier_prefixes_remain_available(collect):
    model = load_state_machine_from_text('''def int active_flag = 0;
        state Controller { state Running; [*] -> Running;
            Running -> [*] : if [active_flag > 0];
        }''', collect=collect)
    if collect:
        model, diagnostics = model
        assert diagnostics == []
    assert not model.active_queries


@pytest.mark.parametrize('root', ['Child', 'Host'])
@pytest.mark.parametrize('query', ['{root}.Worker.On', '/Worker.On'])
def test_import_activity_binding_handles_shared_root_names(tmp_path, root, query):
    (tmp_path / 'child.fcstm').write_text('''state %s { region Worker {
        state On; [*] -> On; On -> [*] : [active("%s")];
    } }''' % (root, query.format(root=root)), encoding='utf-8')
    host = tmp_path / 'host.fcstm'
    host.write_text('state Host { import "child.fcstm" as Child; [*] -> Child; }', encoding='utf-8')
    model = load_state_machine_from_file(host)
    assert model.active_queries[0].state_path == ('Host', 'Child', 'Worker', 'On')


def test_distinct_programmatic_queries_without_spans_are_not_deduplicated():
    from pyfcstm.dsl import node as ast
    from pyfcstm.model import parse_dsl_node_to_state_machine

    program = ast.StateMachineDSLProgram([
        ast.DefAssignment('first', 'int', ast.ActiveStateQuery('Root')),
        ast.DefAssignment('second', 'int', ast.ActiveStateQuery('Root')),
    ], ast.StateDefinition('Root'))
    machine, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)
    assert machine is None
    assert [item.code for item in diagnostics] == ['E_ACTIVE_QUERY_TARGET', 'E_ACTIVE_QUERY_TARGET']


def test_inherited_forced_query_reports_one_authored_error():
    machine, diagnostics = load_state_machine_from_text('''state Root {
        state Group { state On; state Off; [*] -> On; }
        state Idle;
        [*] -> Group;
        !Group -> Idle : if [active("Root.Missing")];
    }''', collect=True)
    assert machine is None
    assert [item.code for item in diagnostics] == ['E_ACTIVE_QUERY_TARGET']
    assert diagnostics[0].span.line == 5
