import os
import pathlib
import textwrap

import pytest
from hbutils.testing import isolated_directory

from pyfcstm.dsl import parse_state_machine_dsl
from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.dsl.node import INIT_STATE
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.model.model import Event


def _write_text_file(path: str, content: str) -> pathlib.Path:
    file_path = pathlib.Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(textwrap.dedent(content).strip() + os.linesep, encoding="utf-8")
    return file_path


@pytest.fixture()
def import_phase2_demo_model():
    with isolated_directory():
        root_file = _write_text_file(
            "root.fcstm",
            """
            state System {
                import "./modules/motor.fcstm" as LeftMotor named "Left Motor";
                [*] -> LeftMotor;
            }
            """,
        )
        _write_text_file(
            "modules/motor.fcstm",
            """
            state MotorRoot named "Motor Module" {
                enter abstract InitMotor;
                state Idle;
                state Running {
                    state Spin;
                    [*] -> Spin;
                }
                [*] -> Idle;
                Idle -> Running :: Start;
                Running -> Idle : /Reset;
            }
            """,
        )

        ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
        model = parse_dsl_node_to_state_machine(ast_node, path=root_file)
        return model


@pytest.fixture()
def import_phase2_demo_root(import_phase2_demo_model):
    return import_phase2_demo_model.root_state


@pytest.fixture()
def import_phase2_demo_left_motor(import_phase2_demo_root):
    return import_phase2_demo_root.substates["LeftMotor"]


@pytest.fixture()
def import_phase2_demo_idle(import_phase2_demo_left_motor):
    return import_phase2_demo_left_motor.substates["Idle"]


@pytest.fixture()
def import_phase2_demo_running(import_phase2_demo_left_motor):
    return import_phase2_demo_left_motor.substates["Running"]


@pytest.fixture()
def import_phase2_demo_spin(import_phase2_demo_running):
    return import_phase2_demo_running.substates["Spin"]


@pytest.mark.unittest
class TestImportPhase2Assembly:
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
            (None, None, None),
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

        assert (
            state_machine.root_state.substates["Alias"].extra_name
            == expected_display_name
        )

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

    def test_import_demo_model(self, import_phase2_demo_model):
        assert import_phase2_demo_model.defines == {}
        assert import_phase2_demo_model.root_state.name == "System"
        assert import_phase2_demo_model.root_state.path == ("System",)

    def test_import_demo_model_to_ast(self, import_phase2_demo_model):
        ast_node = import_phase2_demo_model.to_ast_node()
        assert ast_node.definitions == []
        assert ast_node.root_state.name == "System"

    def test_import_demo_root_state(self, import_phase2_demo_root):
        assert import_phase2_demo_root.name == "System"
        assert import_phase2_demo_root.extra_name is None
        assert import_phase2_demo_root.path == ("System",)
        assert sorted(import_phase2_demo_root.substates.keys()) == ["LeftMotor"]
        assert import_phase2_demo_root.events == {}
        assert import_phase2_demo_root.named_functions == {}
        assert import_phase2_demo_root.on_enters == []
        assert import_phase2_demo_root.on_durings == []
        assert import_phase2_demo_root.on_exits == []
        assert import_phase2_demo_root.on_during_aspects == []
        assert len(import_phase2_demo_root.transitions) == 1
        assert import_phase2_demo_root.transitions[0].from_state == INIT_STATE
        assert import_phase2_demo_root.transitions[0].to_state == "LeftMotor"
        assert import_phase2_demo_root.transitions[0].event is None
        assert import_phase2_demo_root.transitions[0].guard is None
        assert import_phase2_demo_root.transitions[0].effects == []
        assert import_phase2_demo_root.transitions[0].parent_ref().name == "System"
        assert import_phase2_demo_root.transitions[0].parent_ref().path == ("System",)

    def test_import_demo_left_motor_state(self, import_phase2_demo_left_motor):
        assert import_phase2_demo_left_motor.name == "LeftMotor"
        assert import_phase2_demo_left_motor.extra_name == "Left Motor"
        assert import_phase2_demo_left_motor.path == ("System", "LeftMotor")
        assert not import_phase2_demo_left_motor.is_pseudo
        assert sorted(import_phase2_demo_left_motor.substates.keys()) == [
            "Idle",
            "Running",
        ]
        assert import_phase2_demo_left_motor.events == {
            "Reset": Event(
                name="Reset",
                state_path=("System", "LeftMotor"),
                extra_name=None,
            )
        }
        assert sorted(import_phase2_demo_left_motor.named_functions.keys()) == [
            "InitMotor"
        ]
        assert import_phase2_demo_left_motor.named_functions["InitMotor"].stage == "enter"
        assert import_phase2_demo_left_motor.named_functions["InitMotor"].aspect is None
        assert import_phase2_demo_left_motor.named_functions["InitMotor"].name == "InitMotor"
        assert import_phase2_demo_left_motor.named_functions["InitMotor"].doc is None
        assert import_phase2_demo_left_motor.named_functions["InitMotor"].operations == []
        assert import_phase2_demo_left_motor.named_functions["InitMotor"].is_abstract
        assert (
            import_phase2_demo_left_motor.named_functions["InitMotor"].state_path
            == ("System", "LeftMotor", "InitMotor")
        )
        assert import_phase2_demo_left_motor.named_functions["InitMotor"].ref is None
        assert (
            import_phase2_demo_left_motor.named_functions["InitMotor"].ref_state_path
            is None
        )
        assert (
            import_phase2_demo_left_motor.named_functions["InitMotor"].parent_ref().name
            == "LeftMotor"
        )
        assert (
            import_phase2_demo_left_motor.named_functions["InitMotor"].parent_ref().path
            == ("System", "LeftMotor")
        )
        assert (
            import_phase2_demo_left_motor.named_functions["InitMotor"].func_name
            == "System.LeftMotor.InitMotor"
        )
        assert not import_phase2_demo_left_motor.named_functions["InitMotor"].is_aspect
        assert not import_phase2_demo_left_motor.named_functions["InitMotor"].is_ref
        assert (
            import_phase2_demo_left_motor.named_functions["InitMotor"].parent.name
            == "LeftMotor"
        )
        assert (
            import_phase2_demo_left_motor.named_functions["InitMotor"].parent.path
            == ("System", "LeftMotor")
        )
        assert len(import_phase2_demo_left_motor.on_enters) == 1
        assert import_phase2_demo_left_motor.on_enters[0].stage == "enter"
        assert import_phase2_demo_left_motor.on_enters[0].aspect is None
        assert import_phase2_demo_left_motor.on_enters[0].name == "InitMotor"
        assert import_phase2_demo_left_motor.on_enters[0].doc is None
        assert import_phase2_demo_left_motor.on_enters[0].operations == []
        assert import_phase2_demo_left_motor.on_enters[0].is_abstract
        assert import_phase2_demo_left_motor.on_enters[0].state_path == (
            "System",
            "LeftMotor",
            "InitMotor",
        )
        assert import_phase2_demo_left_motor.on_enters[0].ref is None
        assert import_phase2_demo_left_motor.on_enters[0].ref_state_path is None
        assert (
            import_phase2_demo_left_motor.on_enters[0].parent_ref().name == "LeftMotor"
        )
        assert (
            import_phase2_demo_left_motor.on_enters[0].parent_ref().path
            == ("System", "LeftMotor")
        )
        assert (
            import_phase2_demo_left_motor.on_enters[0].func_name
            == "System.LeftMotor.InitMotor"
        )
        assert not import_phase2_demo_left_motor.on_enters[0].is_aspect
        assert not import_phase2_demo_left_motor.on_enters[0].is_ref
        assert import_phase2_demo_left_motor.on_enters[0].parent.name == "LeftMotor"
        assert import_phase2_demo_left_motor.on_enters[0].parent.path == (
            "System",
            "LeftMotor",
        )
        assert import_phase2_demo_left_motor.on_durings == []
        assert import_phase2_demo_left_motor.on_exits == []
        assert import_phase2_demo_left_motor.on_during_aspects == []
        assert len(import_phase2_demo_left_motor.transitions) == 3
        assert import_phase2_demo_left_motor.transitions[0].from_state == INIT_STATE
        assert import_phase2_demo_left_motor.transitions[0].to_state == "Idle"
        assert import_phase2_demo_left_motor.transitions[0].event is None
        assert import_phase2_demo_left_motor.transitions[0].guard is None
        assert import_phase2_demo_left_motor.transitions[0].effects == []
        assert (
            import_phase2_demo_left_motor.transitions[0].parent_ref().name
            == "LeftMotor"
        )
        assert (
            import_phase2_demo_left_motor.transitions[0].parent_ref().path
            == ("System", "LeftMotor")
        )
        assert import_phase2_demo_left_motor.transitions[1].from_state == "Idle"
        assert import_phase2_demo_left_motor.transitions[1].to_state == "Running"
        assert (
            import_phase2_demo_left_motor.transitions[1].event
            == Event(
                name="Start",
                state_path=("System", "LeftMotor", "Idle"),
                extra_name=None,
            )
        )
        assert import_phase2_demo_left_motor.transitions[1].guard is None
        assert import_phase2_demo_left_motor.transitions[1].effects == []
        assert (
            import_phase2_demo_left_motor.transitions[1].parent_ref().name
            == "LeftMotor"
        )
        assert (
            import_phase2_demo_left_motor.transitions[1].parent_ref().path
            == ("System", "LeftMotor")
        )
        assert import_phase2_demo_left_motor.transitions[2].from_state == "Running"
        assert import_phase2_demo_left_motor.transitions[2].to_state == "Idle"
        assert (
            import_phase2_demo_left_motor.transitions[2].event
            == Event(
                name="Reset",
                state_path=("System", "LeftMotor"),
                extra_name=None,
            )
        )
        assert import_phase2_demo_left_motor.transitions[2].guard is None
        assert import_phase2_demo_left_motor.transitions[2].effects == []
        assert (
            import_phase2_demo_left_motor.transitions[2].parent_ref().name
            == "LeftMotor"
        )
        assert (
            import_phase2_demo_left_motor.transitions[2].parent_ref().path
            == ("System", "LeftMotor")
        )
        assert len(import_phase2_demo_left_motor.init_transitions) == 1
        assert import_phase2_demo_left_motor.init_transitions[0].from_state == INIT_STATE
        assert import_phase2_demo_left_motor.init_transitions[0].to_state == "Idle"
        assert import_phase2_demo_left_motor.init_transitions[0].event is None

    def test_import_demo_idle_state(self, import_phase2_demo_idle):
        assert import_phase2_demo_idle.name == "Idle"
        assert import_phase2_demo_idle.extra_name is None
        assert import_phase2_demo_idle.path == ("System", "LeftMotor", "Idle")
        assert import_phase2_demo_idle.substates == {}
        assert import_phase2_demo_idle.events == {
            "Start": Event(
                name="Start",
                state_path=("System", "LeftMotor", "Idle"),
                extra_name=None,
            )
        }
        assert import_phase2_demo_idle.transitions == []
        assert import_phase2_demo_idle.named_functions == {}
        assert import_phase2_demo_idle.on_enters == []
        assert import_phase2_demo_idle.on_durings == []
        assert import_phase2_demo_idle.on_exits == []
        assert import_phase2_demo_idle.on_during_aspects == []

    def test_import_demo_running_state(self, import_phase2_demo_running):
        assert import_phase2_demo_running.name == "Running"
        assert import_phase2_demo_running.extra_name is None
        assert import_phase2_demo_running.path == ("System", "LeftMotor", "Running")
        assert sorted(import_phase2_demo_running.substates.keys()) == ["Spin"]
        assert import_phase2_demo_running.events == {}
        assert len(import_phase2_demo_running.transitions) == 1
        assert import_phase2_demo_running.transitions[0].from_state == INIT_STATE
        assert import_phase2_demo_running.transitions[0].to_state == "Spin"
        assert import_phase2_demo_running.transitions[0].event is None
        assert import_phase2_demo_running.transitions[0].guard is None
        assert import_phase2_demo_running.transitions[0].effects == []
        assert (
            import_phase2_demo_running.transitions[0].parent_ref().name == "Running"
        )
        assert (
            import_phase2_demo_running.transitions[0].parent_ref().path
            == ("System", "LeftMotor", "Running")
        )
        assert import_phase2_demo_running.named_functions == {}
        assert import_phase2_demo_running.on_enters == []
        assert import_phase2_demo_running.on_durings == []
        assert import_phase2_demo_running.on_exits == []
        assert import_phase2_demo_running.on_during_aspects == []
        assert len(import_phase2_demo_running.init_transitions) == 1
        assert import_phase2_demo_running.init_transitions[0].from_state == INIT_STATE
        assert import_phase2_demo_running.init_transitions[0].to_state == "Spin"

    def test_import_demo_spin_state(self, import_phase2_demo_spin):
        assert import_phase2_demo_spin.name == "Spin"
        assert import_phase2_demo_spin.extra_name is None
        assert import_phase2_demo_spin.path == (
            "System",
            "LeftMotor",
            "Running",
            "Spin",
        )
        assert import_phase2_demo_spin.substates == {}
        assert import_phase2_demo_spin.events == {}
        assert import_phase2_demo_spin.transitions == []
        assert import_phase2_demo_spin.named_functions == {}
        assert import_phase2_demo_spin.on_enters == []
        assert import_phase2_demo_spin.on_durings == []
        assert import_phase2_demo_spin.on_exits == []
        assert import_phase2_demo_spin.on_during_aspects == []

    def test_import_demo_ast_export(
        self, import_phase2_demo_model, text_aligner
    ):
        ast_export = import_phase2_demo_model.to_ast_node()
        assert ast_export.definitions == []
        assert ast_export.root_state == dsl_nodes.StateDefinition(
            name="System",
            extra_name=None,
            events=[],
            imports=[],
            substates=[
                dsl_nodes.StateDefinition(
                    name="LeftMotor",
                    extra_name="Left Motor",
                    events=[dsl_nodes.EventDefinition(name="Reset", extra_name=None)],
                    imports=[],
                    substates=[
                        dsl_nodes.StateDefinition(
                            name="Idle",
                            extra_name=None,
                            events=[dsl_nodes.EventDefinition(name="Start", extra_name=None)],
                            imports=[],
                            substates=[],
                            transitions=[],
                            enters=[],
                            durings=[],
                            exits=[],
                            during_aspects=[],
                            force_transitions=[],
                            is_pseudo=False,
                        ),
                        dsl_nodes.StateDefinition(
                            name="Running",
                            extra_name=None,
                            events=[],
                            imports=[],
                            substates=[
                                dsl_nodes.StateDefinition(
                                    name="Spin",
                                    extra_name=None,
                                    events=[],
                                    imports=[],
                                    substates=[],
                                    transitions=[],
                                    enters=[],
                                    durings=[],
                                    exits=[],
                                    during_aspects=[],
                                    force_transitions=[],
                                    is_pseudo=False,
                                )
                            ],
                            transitions=[
                                dsl_nodes.TransitionDefinition(
                                    from_state=INIT_STATE,
                                    to_state="Spin",
                                    event_id=None,
                                    condition_expr=None,
                                    post_operations=[],
                                )
                            ],
                            enters=[],
                            durings=[],
                            exits=[],
                            during_aspects=[],
                            force_transitions=[],
                            is_pseudo=False,
                        ),
                    ],
                    transitions=[
                        dsl_nodes.TransitionDefinition(
                            from_state=INIT_STATE,
                            to_state="Idle",
                            event_id=None,
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Idle",
                            to_state="Running",
                            event_id=dsl_nodes.ChainID(
                                path=["Idle", "Start"],
                                is_absolute=False,
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                        dsl_nodes.TransitionDefinition(
                            from_state="Running",
                            to_state="Idle",
                            event_id=dsl_nodes.ChainID(
                                path=["Reset"],
                                is_absolute=False,
                            ),
                            condition_expr=None,
                            post_operations=[],
                        ),
                    ],
                    enters=[
                        dsl_nodes.EnterAbstractFunction(
                            name="InitMotor",
                            doc=None,
                        )
                    ],
                    durings=[],
                    exits=[],
                    during_aspects=[],
                    force_transitions=[],
                    is_pseudo=False,
                )
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state=INIT_STATE,
                    to_state="LeftMotor",
                    event_id=None,
                    condition_expr=None,
                    post_operations=[],
                )
            ],
            enters=[],
            durings=[],
            exits=[],
            during_aspects=[],
            force_transitions=[],
            is_pseudo=False,
        )
        text_aligner.assert_equal(
            expect=textwrap.dedent(
                """
                state System {
                    state LeftMotor named 'Left Motor' {
                        enter abstract InitMotor;
                        state Idle {
                            event Start;
                        }
                        state Running {
                            state Spin;
                            [*] -> Spin;
                        }
                        event Reset;
                        [*] -> Idle;
                        Idle -> Running :: Start;
                        Running -> Idle : Reset;
                    }
                    [*] -> LeftMotor;
                }
                """
            ).strip(),
            actual=str(ast_export),
        )
