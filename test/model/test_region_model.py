"""Ordered regions remain real namespaces throughout public model operations."""

import pytest

from pyfcstm.dsl import parse_state_machine_dsl
from pyfcstm.dsl.node import RegionDefinition, StateDefinition, StateMachineDSLProgram
from pyfcstm.model import load_state_machine_from_text, parse_dsl_node_to_state_machine
from pyfcstm.utils import ModelValidationError

pytestmark = pytest.mark.unittest

ORDERED = '''state Root {
    state Job {
        enter abstract Start;
        during before abstract Initialize;
        region Right {
            event Go;
            >> during before abstract Tick;
            state On;
            state Off;
            [*] -> On;
            On -> Off : Go;
            Off -> [*] :: Finish;
        }
        exit abstract Stop;
        region Left {
            state On;
            [*] -> On;
            On -> [*] : Go;
        }
        during after abstract Complete;
    }
    state Idle;
    [*] -> Job;
    !Job -> Idle : Stop;
}'''


def test_regions_preserve_namespace_order_and_export():
    model = load_state_machine_from_text(ORDERED)
    assert model.has_regions
    assert [state.path for state in model.walk_states()] == [
        ('Root',), ('Root', 'Job'), ('Root', 'Job', 'Right', 'On'),
        ('Root', 'Job', 'Right', 'Off'), ('Root', 'Job', 'Left', 'On'),
        ('Root', 'Idle'),
    ]
    owner = model.root_state.substates['Job']
    assert not owner.is_leaf_state and not owner.is_stoppable
    assert not owner.substates
    assert list(owner.regions) == ['Right', 'Left']
    right = owner.regions['Right']
    assert right.parent is owner
    assert right.substates['On'].parent is right
    assert [region.path for region in model.walk_regions()] == [
        ('Root', 'Job', 'Right'), ('Root', 'Job', 'Left'),
    ]
    assert [action.name for action in owner.on_enters] == ['Start']
    assert [action.name for action in owner.on_exits] == ['Stop']
    assert [action.name for action in owner.on_durings] == ['Initialize', 'Complete']
    assert [action.name for action in right.on_during_aspects] == ['Tick']
    assert [transition.to_state for transition in right.init_transitions] == ['On']
    exported = str(model.to_ast_node())
    assert exported.index('region Right') < exported.index('region Left')
    assert str(load_state_machine_from_text(exported).to_ast_node()) == exported


def test_region_event_ownership_and_completion_edges():
    model = load_state_machine_from_text(ORDERED)
    owner = model.root_state.substates['Job']
    right, left = owner.regions.values()
    assert right.events['Go'].path_name == 'Root.Job.Right.Go'
    assert left.events['Go'].path_name == 'Root.Job.Left.Go'
    assert right.substates['Off'].events['Finish'].path_name == 'Root.Job.Right.Off.Finish'
    assert right.transitions[1].event is right.events['Go']
    assert right.transitions[2].parent is right
    assert right.substates['On'].transitions_from == [right.transitions[1]]


def test_owner_forced_edge_does_not_become_per_region_completion():
    model = load_state_machine_from_text(ORDERED)
    owner = model.root_state.substates['Job']
    assert [(edge.from_state, edge.to_state) for edge in model.root_state.transitions
            if edge.is_forced] == [('Job', 'Idle')]
    assert owner.transitions == []
    assert all(not edge.is_forced for region in owner.regions.values()
               for edge in region.transitions)
    assert model.forced_transitions[0]['from_path'] == 'Root.Job'


def test_nested_regions_have_ordered_state_and_region_walks():
    model = load_state_machine_from_text('''state Root {
        region Outer {
            state Nested {
                region Inner { state Leaf; [*] -> Leaf; }
            }
            [*] -> Nested;
        }
        region Sibling { state Leaf; [*] -> Leaf; }
    }''')
    assert [region.path for region in model.walk_regions()] == [
        ('Root', 'Outer'), ('Root', 'Outer', 'Nested', 'Inner'), ('Root', 'Sibling'),
    ]
    assert [state.path for state in model.walk_states()] == [
        ('Root',), ('Root', 'Outer', 'Nested'),
        ('Root', 'Outer', 'Nested', 'Inner', 'Leaf'), ('Root', 'Sibling', 'Leaf'),
    ]


@pytest.mark.parametrize('with_ids', [False, True])
def test_region_aspects_participate_in_public_action_traversal(with_ids):
    model = load_state_machine_from_text('''state Root {
        >> during before abstract RootBefore;
        >> during after abstract RootAfter;
        region Worker {
            >> during before abstract RegionBefore;
            >> during after abstract RegionAfter;
            state Leaf { during abstract Work; }
            [*] -> Leaf;
        }
    }''')
    region = model.root_state.regions['Worker']
    leaf = region.substates['Leaf']
    actions = leaf.list_on_during_aspect_recursively(with_ids=with_ids)
    assert [item[-1].name for item in actions] == [
        'RootBefore', 'RegionBefore', 'Work', 'RegionAfter', 'RootAfter',
    ]
    assert [item[-2].path for item in actions] == [
        ('Root',), ('Root', 'Worker'), ('Root', 'Worker', 'Leaf'),
        ('Root', 'Worker'), ('Root',),
    ]
    assert leaf.list_on_during_aspect_recursively(is_abstract=False, with_ids=with_ids) == []


def test_region_combo_relays_preserve_scope_and_ast_roundtrip():
    model = load_state_machine_from_text('''state Root {
        region Worker {
            state A;
            state B;
            [*] -> A;
            A -> B : First + Second;
        }
    }''')
    region = model.root_state.regions['Worker']
    relays = [state for state in region.walk_states() if state.is_combo_relay]
    assert len(relays) == 1
    assert relays[0].parent is region
    assert relays[0].path[:-1] == ('Root', 'Worker')
    assert [event.path_name for event in region.events.values()] == [
        'Root.Worker.First', 'Root.Worker.Second',
    ]
    restored = parse_dsl_node_to_state_machine(model.to_ast_node())
    assert [state.path for state in restored.walk_states() if state.is_combo_relay] == [relays[0].path]


@pytest.mark.parametrize('source,code', [
    ('state Root { region Empty {} }', 'E_REGION_STRUCTURE'),
    ('state Root { region A { state Leaf; } }', 'E_INITIAL_TRANSITION_INVALID'),
    ('state Root { region A { state Leaf; [*] -> Missing; } }', 'E_DANGLING_TRANSITION'),
    ('state Root { region A { state Leaf; state Leaf; [*] -> Leaf; } }', 'E_DUPLICATE_STATE'),
    ('state Root { region A { state Leaf; [*] -> Leaf; } '
     'region A { state Leaf; [*] -> Leaf; } }', 'E_DUPLICATE_REGION'),
    ('pseudo state Root { region A { state Leaf; [*] -> Leaf; } }', 'E_PSEUDO_NOT_LEAF'),
])
@pytest.mark.parametrize('collect', [False, True])
def test_region_structural_diagnostics(source, code, collect):
    program = parse_state_machine_dsl(source)
    if collect:
        _, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)
    else:
        with pytest.raises(ModelValidationError) as caught:
            parse_dsl_node_to_state_machine(program)
        diagnostics = caught.value.diagnostics
    assert code in [item.code for item in diagnostics]
    assert all(item.span is not None for item in diagnostics if item.code == code)


@pytest.mark.parametrize('collect', [False, True])
def test_public_ast_mixed_children_are_rejected_semantically(collect):
    program = StateMachineDSLProgram([], StateDefinition(
        'Root', substates=[StateDefinition('Child')],
        regions=[RegionDefinition('Workers')],
    ))
    if collect:
        model, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)
        assert model is None
    else:
        with pytest.raises(ModelValidationError) as caught:
            parse_dsl_node_to_state_machine(program)
        diagnostics = caught.value.diagnostics
    assert diagnostics[0].code == 'E_REGION_STRUCTURE'
    assert diagnostics[0].refs['reason'] == 'mixed_children'
    assert program.root_state.substates[0].name == 'Child'
    assert program.root_state.regions[0].name == 'Workers'


def test_ordinary_model_has_no_regions_and_keeps_export():
    model = load_state_machine_from_text('state Root { state Leaf; [*] -> Leaf; }')
    assert not model.has_regions
    assert list(model.walk_regions()) == []
    assert [state.path for state in model.walk_states()] == [('Root',), ('Root', 'Leaf')]
    assert model.root_state.substates['Leaf'].parent is model.root_state
    assert str(model.to_ast_node()) == 'state Root {\n    state Leaf;\n    [*] -> Leaf;\n}'


def test_region_subtree_walk_includes_only_its_own_nested_regions():
    model = load_state_machine_from_text('''state Root {
        region Worker {
            state Group { region Inner { state Leaf; [*] -> Leaf; } }
            [*] -> Group;
        }
        region Monitor { state Idle; [*] -> Idle; }
    }''')
    worker = model.root_state.regions['Worker']
    assert [region.path for region in worker.walk_regions()] == [
        ('Root', 'Worker'), ('Root', 'Worker', 'Group', 'Inner'),
    ]


@pytest.mark.parametrize('collect', [False, True])
def test_public_ast_parallel_owner_cannot_keep_local_transitions(collect):
    program = parse_state_machine_dsl('state Root { state Leaf; [*] -> Leaf; }')
    children = program.root_state.substates
    program.root_state.substates = []
    program.root_state.regions = [RegionDefinition('Worker', substates=children)]
    if collect:
        model, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)
        assert model is None
    else:
        with pytest.raises(ModelValidationError) as error:
            parse_dsl_node_to_state_machine(program)
        diagnostics = error.value.diagnostics
    assert diagnostics[0].code == 'E_REGION_STRUCTURE'
    assert diagnostics[0].refs['reason'] == 'owner_statements'


def test_interleaved_combo_alternatives_preserve_both_region_sources():
    model = load_state_machine_from_text('''state Root { region Worker {
        state A; state B; state C; state D; [*] -> A;
        A -> B : First + Second;
        C -> D : First + Second;
        A -> B : First + Third;
        C -> D : First + Third;
    } }''')
    region = model.root_state.regions['Worker']
    assert len([state for state in region.walk_states() if state.is_combo_relay]) == 2
    assert {edge.from_state for edge in region.transitions if edge.event
            and edge.event.name == 'First'} == {'A', 'C'}
    exported = str(model.to_ast_node())
    assert str(load_state_machine_from_text(exported).to_ast_node()) == exported


@pytest.mark.parametrize('collect', [False, True])
def test_leaf_inside_region_cannot_own_descendant_aspect(collect):
    source = '''state Root { region Worker {
        state Leaf { >> during before abstract Observe; }
        [*] -> Leaf;
    } }'''
    if collect:
        _, diagnostics = load_state_machine_from_text(source, collect=True)
    else:
        with pytest.raises(ModelValidationError) as error:
            load_state_machine_from_text(source)
        diagnostics = error.value.diagnostics
    diagnostic = next(item for item in diagnostics if item.code == 'E_DURING_ASPECT_INVALID')
    assert diagnostic.refs['state_kind'] == 'leaf'
    assert diagnostic.span is not None


@pytest.mark.parametrize('consumer', ['simulate', 'bmc', 'diagram'])
def test_unsupported_consumers_refuse_a_valid_region_model(consumer):
    model = load_state_machine_from_text(ORDERED)
    with pytest.raises(ModelValidationError) as caught:
        if consumer == 'simulate':
            from pyfcstm.simulate import SimulationRuntime
            SimulationRuntime(model)
        elif consumer == 'bmc':
            from pyfcstm.bmc import build_bmc_domain
            build_bmc_domain(model, 1)
        else:
            model.diagram()
    assert caught.value.diagnostics[0].code == 'E_UNSUPPORTED_FEATURE'
    assert caught.value.diagnostics[0].refs['feature'] == 'region'
