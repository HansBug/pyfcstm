import pathlib

import pytest
from hbutils.testing import isolated_directory

from pyfcstm.dsl import parse_state_machine_dsl
from pyfcstm.model import parse_dsl_node_to_state_machine


@pytest.mark.unittest
class TestImportPhase1PathContract:
    def test_parse_dsl_node_to_state_machine_remains_compatible_without_path(self):
        ast_node = parse_state_machine_dsl(
            """
            def int counter = 0;
            state Root;
            """
        )

        state_machine = parse_dsl_node_to_state_machine(ast_node)

        assert state_machine.root_state.name == "Root"
        assert state_machine.defines["counter"].type == "int"

    def test_parse_dsl_node_to_state_machine_accepts_pathlike_argument(self, tmp_path):
        ast_node = parse_state_machine_dsl(
            """
            def int counter = 0;
            state Root;
            """
        )

        state_machine = parse_dsl_node_to_state_machine(
            ast_node,
            path=pathlib.Path(tmp_path) / "root.fcstm",
        )

        assert state_machine.root_state.name == "Root"
        assert state_machine.defines["counter"].name == "counter"

    def test_parse_state_machine_dsl_accepts_import_when_target_file_exists(self):
        with isolated_directory():
            pathlib.Path("worker.fcstm").write_text(
                "state Worker;",
                encoding="utf-8",
            )

            ast_node = parse_state_machine_dsl(
                """
                state Root {
                    import "./worker.fcstm" as Worker;
                }
                """
            )

        assert ast_node.root_state.name == "Root"
        assert len(ast_node.root_state.imports) == 1
        assert ast_node.root_state.imports[0].source_path == "./worker.fcstm"
        assert ast_node.root_state.imports[0].alias == "Worker"
