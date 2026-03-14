from types import SimpleNamespace

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine, parse_expr
from pyfcstm.verify import search as verify_search


TEST_DSL = '''
def int counter = 0;
state Root {
    state Idle;
    [*] -> Idle;
}
'''


def build_state_machine(dsl_code: str = TEST_DSL):
    ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    return parse_dsl_node_to_state_machine(ast)


@pytest.mark.unittest
class TestBfsSearchErrors:
    def test_rejects_invalid_init_state_type(self):
        state_machine = build_state_machine()

        with pytest.raises(TypeError) as exc_info:
            verify_search.bfs_search(state_machine, 123)

        message = str(exc_info.value)
        assert "expected 'init_state' to be a State object or a full state path string" in message
        assert "got int: 123" in message
        assert "Root.System.Active" in message

    def test_rejects_state_from_other_machine(self):
        state_machine = build_state_machine()
        other_state_machine = build_state_machine()
        foreign_state = other_state_machine.resolve_state('Root.Idle')

        with pytest.raises(ValueError) as exc_info:
            verify_search.bfs_search(state_machine, foreign_state)

        message = str(exc_info.value)
        assert "does not belong to the provided state machine" in message
        assert "'Root.Idle'" in message
        assert "different parsed state machine instance" in message

    def test_wraps_invalid_init_state_path(self):
        state_machine = build_state_machine()

        with pytest.raises(LookupError) as exc_info:
            verify_search.bfs_search(state_machine, 'Root.Missing')

        message = str(exc_info.value)
        assert "Failed to resolve 'init_state' for bfs_search()" in message
        assert "'Root.Missing'" in message
        assert "starts from the state machine root" in message

    def test_rejects_invalid_init_constraints_type(self):
        state_machine = build_state_machine()

        with pytest.raises(TypeError) as exc_info:
            verify_search.bfs_search(state_machine, 'Root.Idle', init_constraints=['counter > 0'])

        message = str(exc_info.value)
        assert "expected 'init_constraints' to be None" in message
        assert "got list: ['counter > 0']" in message
        assert "logical condition such as 'counter > 0 && enabled'" in message

    def test_rejects_non_logical_constraint_string(self):
        state_machine = build_state_machine()

        with pytest.raises(ValueError) as exc_info:
            verify_search.bfs_search(state_machine, 'Root.Idle', init_constraints='counter + 1')

        message = str(exc_info.value)
        assert "Failed to parse 'init_constraints' for bfs_search()" in message
        assert "'counter + 1'" in message
        assert "must be a logical DSL condition" in message

    def test_rejects_non_boolean_constraint_expr(self):
        state_machine = build_state_machine()

        with pytest.raises(ValueError) as exc_info:
            verify_search.bfs_search(
                state_machine,
                'Root.Idle',
                init_constraints=parse_expr('counter + 1'),
            )

        message = str(exc_info.value)
        assert "produced a non-boolean constraint" in message
        assert "counter + 1" in message
        assert "use a comparison such as 'counter > 0'" in message

    def test_reports_unexpected_internal_frame_type(self, monkeypatch):
        state_machine = build_state_machine()

        def _broken_search_frame(**kwargs):
            frame = SimpleNamespace(**kwargs)
            frame.type = 'broken'
            return frame

        monkeypatch.setattr(verify_search, 'SearchFrame', _broken_search_frame)

        with pytest.raises(RuntimeError) as exc_info:
            verify_search.bfs_search(state_machine, 'Root.Idle')

        message = str(exc_info.value)
        assert "unsupported type 'broken'" in message
        assert "'Root.Idle'" in message
        assert "Supported frame types are 'leaf', 'composite_in', 'composite_out', and 'end'" in message
