"""Expanded model operations retain authored locations and variable roles."""

import pytest

from pyfcstm.model import load_state_machine_from_file
from pyfcstm.model.model import IfBlock, Operation

pytestmark = pytest.mark.unittest


def test_imported_nested_accesses_keep_source_and_mapped_names(tmp_path):
    leaf = tmp_path / 'leaf.fcstm'
    leaf.write_text('input int sensor; param int limit = 1; output int result = 0; state Leaf { during { if [sensor > limit] { if [sensor > 2] { result = sensor; } } } }', encoding='utf-8')
    host = tmp_path / 'host.fcstm'
    host.write_text('input int shared; state Host { import "./leaf.fcstm" as A { var sensor -> shared; var limit -> A_limit; var result -> A_result; } import "./leaf.fcstm" as B { var sensor -> shared; var limit -> B_limit; var result -> B_result; } [*] -> A; A -> B; }', encoding='utf-8')
    model = load_state_machine_from_file(host)
    assert model.defines['shared'].role.value == 'input'
    for name in ['A', 'B']:
        state = model.root_state.substates[name]
        block = state.on_durings[0].operations[0]
        assert isinstance(block, IfBlock)
        assert str(block.branches[0].condition) == 'shared > %s_limit' % name
        nested = block.branches[0].statements[0]
        assert isinstance(nested, IfBlock)
        assignment = nested.branches[0].statements[0]
        assert isinstance(assignment, Operation)
        assert assignment.var_name == name + '_result'
        assert str(assignment.expr) == 'shared'
        for node in [block, block.branches[0], nested, nested.branches[0], assignment]:
            assert node._source_path == str(leaf)
            assert node._span.line == 1
        assert model.defines[name + '_limit'].role.value == 'param'
        assert model.defines[name + '_result'].role.value == 'output'
