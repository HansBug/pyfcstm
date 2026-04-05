import os
import pathlib

import pytest
from hbutils.testing import isolated_directory

from pyfcstm.dsl import parse_state_machine_dsl
from pyfcstm.model import parse_dsl_node_to_state_machine


def _write_text_file(path: str, content: str) -> pathlib.Path:
    file_path = pathlib.Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.mark.unittest
class TestImportPhase2Assembly:
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
            _write_text_file("worker.fcstm", "state Worker;")

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

    def test_parse_dsl_node_to_state_machine_uses_cwd_for_import_context(self):
        with isolated_directory():
            _write_text_file(
                "worker.fcstm",
                """
                state Worker {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(
                """
                state Root {
                    import "./worker.fcstm" as Worker;
                    [*] -> Worker;
                }
                """
            )

            state_machine = parse_dsl_node_to_state_machine(ast_node)

        assert state_machine.root_state.name == "Root"
        assert "Worker" in state_machine.root_state.substates
        assert "Idle" in state_machine.root_state.substates["Worker"].substates

    def test_parse_dsl_node_to_state_machine_explicit_path_overrides_cwd(self):
        with isolated_directory():
            cwd_base = pathlib.Path("cwd-base")
            cwd_base.mkdir()
            _write_text_file(
                str(cwd_base / "worker.fcstm"),
                """
                state Worker {
                    state FromCwd;
                    [*] -> FromCwd;
                }
                """,
            )
            cwd_base_abs = cwd_base.resolve()

            override_dir = pathlib.Path("override-base")
            override_dir.mkdir()
            _write_text_file(
                str(override_dir / "worker.fcstm"),
                """
                state Worker {
                    state FromOverride;
                    [*] -> FromOverride;
                }
                """,
            )
            override_dir_abs = override_dir.resolve()

            previous_cwd = pathlib.Path.cwd()
            os.chdir(cwd_base_abs)

            try:
                ast_node = parse_state_machine_dsl(
                    """
                    state Root {
                        import "./worker.fcstm" as Worker;
                        [*] -> Worker;
                    }
                    """
                )

                state_machine = parse_dsl_node_to_state_machine(
                    ast_node,
                    path=override_dir_abs,
                )
            finally:
                os.chdir(previous_cwd)

        imported_state = state_machine.root_state.substates["Worker"]
        assert "FromOverride" in imported_state.substates
        assert "FromCwd" not in imported_state.substates

    def test_multilevel_relative_imports_resolve_per_declaring_file(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    import "./modules/a.fcstm" as A;
                    [*] -> A;
                }
                """,
            )
            _write_text_file(
                "modules/a.fcstm",
                """
                state ModuleA {
                    import "./nested/b.fcstm" as B;
                    [*] -> B;
                }
                """,
            )
            _write_text_file(
                "modules/nested/b.fcstm",
                """
                state ModuleB {
                    state Leaf;
                    [*] -> Leaf;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            state_machine = parse_dsl_node_to_state_machine(ast_node, path=root_file)

        assert "A" in state_machine.root_state.substates
        assert "B" in state_machine.root_state.substates["A"].substates
        assert (
            "Leaf"
            in state_machine.root_state.substates["A"].substates["B"].substates
        )

    def test_circular_import_detected(self):
        with isolated_directory():
            root_file = _write_text_file(
                "a.fcstm",
                """
                state RootA {
                    import "./b.fcstm" as B;
                    [*] -> B;
                }
                """,
            )
            _write_text_file(
                "b.fcstm",
                """
                state RootB {
                    import "./a.fcstm" as A;
                    [*] -> A;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        message = str(exc_info.value)
        assert "Circular import detected" in message
        assert "a.fcstm" in message
        assert "b.fcstm" in message

    def test_missing_import_file_reported(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    import "./missing.fcstm" as Missing;
                    [*] -> Missing;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        message = str(exc_info.value)
        assert "Import source file not found" in message
        assert "./missing.fcstm" in message
        assert "Missing" in message

    def test_import_alias_conflict_with_existing_child_state(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    import "./worker.fcstm" as Worker;
                    state Worker;
                    [*] -> Worker;
                }
                """,
            )
            _write_text_file("worker.fcstm", "state Worker;")

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        message = str(exc_info.value)
        assert "Import alias conflict" in message
        assert "Worker" in message
        assert "Root" in message

    @pytest.mark.parametrize(
        ["import_named", "module_named", "expected_display_name"],
        [
            ("Outer Name", "Inner Name", "Outer Name"),
            (None, "Inner Name", "Inner Name"),
            (None, None, "Alias"),
        ],
    )
    def test_import_display_name_priority(
        self,
        import_named,
        module_named,
        expected_display_name,
    ):
        with isolated_directory():
            if module_named is None:
                module_state_line = "state WorkerRoot;"
            else:
                module_state_line = f"state WorkerRoot named {module_named!r};"
            _write_text_file("worker.fcstm", module_state_line)

            import_named_clause = ""
            if import_named is not None:
                import_named_clause = f" named {import_named!r}"
            ast_node = parse_state_machine_dsl(
                f"""
                state Root {{
                    import "./worker.fcstm" as Alias{import_named_clause};
                    [*] -> Alias;
                }}
                """
            )

            state_machine = parse_dsl_node_to_state_machine(ast_node)

        assert state_machine.root_state.substates["Alias"].extra_name == expected_display_name

    def test_imported_module_absolute_event_rewrites_to_instance_scope(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    import "./worker.fcstm" as Worker;
                    [*] -> Worker;
                }
                """,
            )
            _write_text_file(
                "worker.fcstm",
                """
                state WorkerRoot {
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : /Start;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            state_machine = parse_dsl_node_to_state_machine(ast_node, path=root_file)

        worker_state = state_machine.root_state.substates["Worker"]
        assert "Start" in worker_state.events
        transition = worker_state.transitions[1]
        assert transition.event is worker_state.events["Start"]

    def test_import_mapping_remains_fail_fast_before_phase3_and_phase4(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    import "./worker.fcstm" as Worker {
                        def * -> worker_*;
                    }
                    [*] -> Worker;
                }
                """,
            )
            _write_text_file("worker.fcstm", "state Worker;")

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        message = str(exc_info.value)
        assert "Import mappings are parsed but not available" in message
        assert "./worker.fcstm" in message
        assert "Worker" in message

    def test_imported_top_level_definitions_remain_fail_fast_before_phase3(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    import "./worker.fcstm" as Worker;
                    [*] -> Worker;
                }
                """,
            )
            _write_text_file(
                "worker.fcstm",
                """
                def int counter = 0;
                state Worker;
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        message = str(exc_info.value)
        assert "Imported top-level variable definitions are not available" in message
        assert "./worker.fcstm" in message
        assert "Worker" in message
