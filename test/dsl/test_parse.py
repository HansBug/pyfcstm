import pytest

import pyfcstm.dsl.parse as parse_module
from pyfcstm.dsl.node import StateDefinition


@pytest.mark.unittest
class TestDSLParse:
    def test_parse_state_machine_dsl_rejects_non_program_node(self, monkeypatch):
        def _mock_parse_with_grammar_entry(input_text, entry_name):
            assert input_text == "state Root;"
            assert entry_name == "state_machine_dsl"
            return StateDefinition(
                name="Root",
                substates=[],
                transitions=[],
                enters=[],
                durings=[],
                exits=[],
            )

        monkeypatch.setattr(
            parse_module,
            "parse_with_grammar_entry",
            _mock_parse_with_grammar_entry,
        )

        with pytest.raises(
            TypeError,
            match="Expected 'state_machine_dsl' to produce StateMachineDSLProgram",
        ):
            parse_module.parse_state_machine_dsl("state Root;")

    def test_parse_state_machine_dsl_path_does_not_pollute_ast(self):
        program = parse_module.parse_state_machine_dsl("state Root;")

        assert program.root_state.name == "Root"
        assert not hasattr(program, "source_path")
