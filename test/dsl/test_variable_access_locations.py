"""AST locations used by static role-aware access reports."""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.dsl.node import OperationAssignment, OperationIf

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('owner', ['enter', 'during', 'exit', 'effect'])
def test_role_access_ast_keeps_nested_statement_and_branch_spans(owner):
    body = 'if [sensor > limit] { result = sensor; } else { result = counter; }'
    prefix = 'input int sensor; param int limit = 1; output int result = 0; control int counter = 0; '
    if owner == 'effect':
        source = prefix + 'state Root { state A; state B; [*] -> A; A -> B effect { ' + body + ' } }'
    else:
        source = prefix + 'state Root { ' + owner + ' { ' + body + ' } }'
    ast = parse_with_grammar_entry(source, 'state_machine_dsl')
    assert [d.role.value for d in ast.definitions] == ['input', 'param', 'output', 'control']
    statements = (ast.root_state.transitions[-1].post_operations if owner == 'effect'
                  else getattr(ast.root_state, {'enter': 'enters', 'during': 'durings', 'exit': 'exits'}[owner])[0].operations)
    conditional = statements[0]
    assert isinstance(conditional, OperationIf)
    assert source[conditional._span.column - 1:conditional._span.end_column - 1] == body
    assert str(conditional.branches[0].condition) == 'sensor > limit'
    assert conditional.branches[1].condition is None
    for branch, expression in zip(conditional.branches, ['sensor', 'counter']):
        assignment = branch.statements[0]
        assert isinstance(assignment, OperationAssignment)
        assert assignment.name == 'result'
        assert str(assignment.expr) == expression
        assert source[assignment._span.column - 1:assignment._span.end_column - 1] == 'result = %s;' % expression
        assert branch._span.column <= assignment._span.column < branch._span.end_column
