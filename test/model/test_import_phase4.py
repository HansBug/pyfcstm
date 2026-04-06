import os
import pathlib
import textwrap

import pytest
from hbutils.testing import isolated_directory

from pyfcstm.dsl import parse_state_machine_dsl
from pyfcstm.model import parse_dsl_node_to_state_machine


def _write_text_file(path: str, content: str) -> pathlib.Path:
    file_path = pathlib.Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(textwrap.dedent(content).strip() + os.linesep, encoding="utf-8")
    return file_path


def _build_state_machine(root_content: str, **extra_files):
    with isolated_directory():
        root_file = _write_text_file("root.fcstm", root_content)
        for relative_path, content in extra_files.items():
            _write_text_file(relative_path, content)

        ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
        return parse_dsl_node_to_state_machine(ast_node, path=root_file)


@pytest.mark.unittest
class TestImportPhase4Assembly:
    def test_event_mapping_relative_target_promotes_to_owner_scope(self):
        state_machine = _build_state_machine(
            """
            state Root {
                state System {
                    import "./worker.fcstm" as Worker {
                        event /Start -> Start;
                    }
                    [*] -> Worker;
                }
                [*] -> System;
            }
            """,
            **{
                "worker.fcstm": """
                state WorkerRoot {
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : /Start;
                }
                """,
            },
        )

        system_state = state_machine.root_state.substates["System"]
        worker_state = system_state.substates["Worker"]
        assert "Start" in system_state.events
        promoted_event = system_state.events["Start"]
        assert worker_state.transitions[1].event is promoted_event
        assert promoted_event.path == ("Root", "System", "Start")

    def test_event_mapping_absolute_target_promotes_to_root_scope(self):
        state_machine = _build_state_machine(
            """
            state Root {
                state Motors;
                state System {
                    import "./worker.fcstm" as Worker {
                        event /Start -> /Motors.Start;
                    }
                    [*] -> Worker;
                }
                [*] -> System;
            }
            """,
            **{
                "worker.fcstm": """
                state WorkerRoot {
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : /Start;
                }
                """,
            },
        )

        motors_state = state_machine.root_state.substates["Motors"]
        worker_state = state_machine.root_state.substates["System"].substates["Worker"]
        assert "Start" in motors_state.events
        promoted_event = motors_state.events["Start"]
        assert worker_state.transitions[1].event is promoted_event
        assert promoted_event.path == ("Root", "Motors", "Start")

    def test_unmapped_module_absolute_event_stays_in_instance_scope(self):
        state_machine = _build_state_machine(
            """
            state Root {
                import "./worker.fcstm" as Worker;
                [*] -> Worker;
            }
            """,
            **{
                "worker.fcstm": """
                state WorkerRoot {
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : /Start;
                }
                """,
            },
        )

        worker_state = state_machine.root_state.substates["Worker"]
        assert "Start" in worker_state.events
        assert worker_state.transitions[1].event is worker_state.events["Start"]
        assert "Start" not in state_machine.root_state.events

    def test_event_mapping_preserves_shared_event_identity_for_multiple_transitions(self):
        state_machine = _build_state_machine(
            """
            state Root {
                import "./worker.fcstm" as Worker {
                    event /Tick -> SharedTick;
                }
                [*] -> Worker;
            }
            """,
            **{
                "worker.fcstm": """
                state WorkerRoot {
                    state Idle;
                    state Running;
                    state Done;
                    [*] -> Idle;
                    Idle -> Running : /Tick;
                    Running -> Done : /Tick;
                    Done -> Idle : /Tick;
                }
                """,
            },
        )

        worker_state = state_machine.root_state.substates["Worker"]
        shared_event = state_machine.root_state.events["SharedTick"]
        assert worker_state.transitions[1].event is shared_event
        assert worker_state.transitions[2].event is shared_event
        assert worker_state.transitions[3].event is shared_event

    def test_multiple_imports_can_share_same_host_event(self):
        state_machine = _build_state_machine(
            """
            state Root {
                import "./worker.fcstm" as LeftWorker {
                    event /Start -> Start;
                }
                import "./worker.fcstm" as RightWorker {
                    event /Start -> Start;
                }
                [*] -> LeftWorker;
            }
            """,
            **{
                "worker.fcstm": """
                state WorkerRoot {
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : /Start;
                }
                """,
            },
        )

        shared_event = state_machine.root_state.events["Start"]
        left_worker = state_machine.root_state.substates["LeftWorker"]
        right_worker = state_machine.root_state.substates["RightWorker"]
        assert left_worker.transitions[1].event is shared_event
        assert right_worker.transitions[1].event is shared_event

    def test_event_mapping_named_override_applies_to_target_event(self):
        state_machine = _build_state_machine(
            """
            state Root {
                import "./worker.fcstm" as Worker {
                    event /Start -> Start named "Mapped Start";
                }
                [*] -> Worker;
            }
            """,
            **{
                "worker.fcstm": """
                state WorkerRoot {
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : /Start;
                }
                """,
            },
        )

        assert state_machine.root_state.events["Start"].extra_name == "Mapped Start"

    def test_event_mapping_moves_explicit_source_event_definition_to_host_target(self):
        state_machine = _build_state_machine(
            """
            state Root {
                state System {
                    import "./worker.fcstm" as Worker {
                        event /Start -> Start named "Mapped Start";
                    }
                    [*] -> Worker;
                }
                [*] -> System;
            }
            """,
            **{
                "worker.fcstm": """
                state WorkerRoot {
                    event Start named "Source Start";
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : Start;
                }
                """,
            },
        )

        system_state = state_machine.root_state.substates["System"]
        worker_state = system_state.substates["Worker"]

        assert "Start" in system_state.events
        assert system_state.events["Start"].extra_name == "Mapped Start"
        assert "Start" not in worker_state.events
        assert worker_state.transitions[1].event is system_state.events["Start"]

    def test_event_mapping_applies_to_force_transitions(self):
        state_machine = _build_state_machine(
            """
            state Root {
                state Bus;
                import "./worker.fcstm" as Worker {
                    event /Alarm -> /Bus.Alarm;
                }
                [*] -> Worker;
            }
            """,
            **{
                "worker.fcstm": """
                state WorkerRoot {
                    state Idle;
                    state Running;
                    state Error;
                    [*] -> Idle;
                    Idle -> Running;
                    ! * -> Error : /Alarm;
                }
                """,
            },
        )

        bus_alarm = state_machine.root_state.substates["Bus"].events["Alarm"]
        worker_state = state_machine.root_state.substates["Worker"]

        alarm_transitions = [
            transition
            for transition in worker_state.transitions
            if transition.event is bus_alarm
        ]
        assert [(item.from_state, item.to_state) for item in alarm_transitions] == [
            ("Idle", "Error"),
            ("Running", "Error"),
            ("Error", "Error"),
        ]

    def test_event_mapping_conflicting_named_override_is_rejected(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    import "./left.fcstm" as Left {
                        event /Start -> Start named "Left Start";
                    }
                    import "./right.fcstm" as Right {
                        event /Start -> Start named "Right Start";
                    }
                    [*] -> Left;
                }
                """,
            )
            _write_text_file(
                "left.fcstm",
                """
                state LeftRoot {
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : /Start;
                }
                """,
            )
            _write_text_file(
                "right.fcstm",
                """
                state RightRoot {
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : /Start;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        assert "receives conflicting display names" in str(exc_info.value)

    def test_event_mapping_rejects_non_absolute_source_path(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    import "./worker.fcstm" as Worker {
                        event Start -> SharedStart;
                    }
                    [*] -> Worker;
                }
                """,
            )
            _write_text_file("worker.fcstm", "state Worker;")

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        assert "must be a module-absolute path" in str(exc_info.value)

    def test_phase4_complete_example_to_ast_node_str(self, text_aligner):
        state_machine = _build_state_machine(
            """
            state Root {
                state Bus;
                state System {
                    import "./worker.fcstm" as Worker named "Promoted Worker" {
                        event /Start -> Start named "Shared Start";
                        event /Stop -> /Bus.Stop;
                    }
                    [*] -> Worker;
                }
                [*] -> System;
            }
            """,
            **{
                "worker.fcstm": """
                state WorkerRoot {
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : /Start;
                    Running -> Idle : /Stop;
                }
                """,
            },
        )

        text_aligner.assert_equal(
            expect=textwrap.dedent(
                """
                state Root {
                    state Bus {
                        event Stop;
                    }
                    state System {
                        state Worker named 'Promoted Worker' {
                            state Idle;
                            state Running;
                            [*] -> Idle;
                            Idle -> Running : /System.Start;
                            Running -> Idle : /Bus.Stop;
                        }
                        event Start named 'Shared Start';
                        [*] -> Worker;
                    }
                    [*] -> System;
                }
                """
            ).strip(),
            actual=str(state_machine.to_ast_node()),
        )

    def test_phase4_unmapped_instance_local_event_to_ast_node_str(self, text_aligner):
        state_machine = _build_state_machine(
            """
            state Root {
                import "./worker.fcstm" as Worker;
                [*] -> Worker;
            }
            """,
            **{
                "worker.fcstm": """
                state WorkerRoot {
                    event Start named "Worker Start";
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : Start;
                }
                """,
            },
        )

        text_aligner.assert_equal(
            expect=textwrap.dedent(
                """
                state Root {
                    state Worker {
                        state Idle;
                        state Running;
                        event Start named 'Worker Start';
                        [*] -> Idle;
                        Idle -> Running : Start;
                    }
                    [*] -> Worker;
                }
                """
            ).strip(),
            actual=str(state_machine.to_ast_node()),
        )

    def test_phase4_relative_nested_target_and_absolute_root_target_to_ast_node_str(
        self, text_aligner
    ):
        state_machine = _build_state_machine(
            """
            state Root {
                state Plant {
                    state Bus;
                    import "./worker.fcstm" as Worker {
                        event /Stop -> Bus.Stop named "Plant Stop";
                        event /Fault -> /GlobalFault named "Global Fault";
                    }
                    [*] -> Worker;
                }
                [*] -> Plant;
            }
            """,
            **{
                "worker.fcstm": """
                state WorkerRoot {
                    event Fault named "Local Fault";
                    state Idle;
                    state Failed;
                    [*] -> Idle;
                    Idle -> Failed : Fault;
                    Failed -> Idle : /Stop;
                }
                """,
            },
        )

        plant_state = state_machine.root_state.substates["Plant"]
        worker_state = plant_state.substates["Worker"]
        assert worker_state.transitions[1].event is state_machine.root_state.events[
            "GlobalFault"
        ]
        assert worker_state.transitions[2].event is plant_state.substates["Bus"].events[
            "Stop"
        ]

        text_aligner.assert_equal(
            expect=textwrap.dedent(
                """
                state Root {
                    state Plant {
                        state Worker {
                            state Idle;
                            state Failed;
                            [*] -> Idle;
                            Idle -> Failed : /GlobalFault;
                            Failed -> Idle : /Plant.Bus.Stop;
                        }
                        state Bus {
                            event Stop named 'Plant Stop';
                        }
                        [*] -> Worker;
                    }
                    event GlobalFault named 'Global Fault';
                    [*] -> Plant;
                }
                """
            ).strip(),
            actual=str(state_machine.to_ast_node()),
        )

    def test_phase4_shared_host_events_across_multiple_imports_to_ast_node_str(
        self, text_aligner
    ):
        state_machine = _build_state_machine(
            """
            state Root {
                state Bus;
                import "./worker.fcstm" as LeftWorker {
                    event /Start -> Start named "Shared Start";
                    event /Stop -> /Bus.Stop;
                }
                import "./worker.fcstm" as RightWorker {
                    event /Start -> Start named "Shared Start";
                    event /Stop -> /Bus.Stop;
                }
                [*] -> LeftWorker;
            }
            """,
            **{
                "worker.fcstm": """
                state WorkerRoot {
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : /Start;
                    Running -> Idle : /Stop;
                }
                """,
            },
        )

        shared_start = state_machine.root_state.events["Start"]
        shared_stop = state_machine.root_state.substates["Bus"].events["Stop"]
        left_worker = state_machine.root_state.substates["LeftWorker"]
        right_worker = state_machine.root_state.substates["RightWorker"]

        assert left_worker.transitions[1].event is shared_start
        assert left_worker.transitions[2].event is shared_stop
        assert right_worker.transitions[1].event is shared_start
        assert right_worker.transitions[2].event is shared_stop

        text_aligner.assert_equal(
            expect=textwrap.dedent(
                """
                state Root {
                    state LeftWorker {
                        state Idle;
                        state Running;
                        [*] -> Idle;
                        Idle -> Running : /Start;
                        Running -> Idle : /Bus.Stop;
                    }
                    state RightWorker {
                        state Idle;
                        state Running;
                        [*] -> Idle;
                        Idle -> Running : /Start;
                        Running -> Idle : /Bus.Stop;
                    }
                    state Bus {
                        event Stop;
                    }
                    event Start named 'Shared Start';
                    [*] -> LeftWorker;
                }
                """
            ).strip(),
            actual=str(state_machine.to_ast_node()),
        )

    def test_phase4_nested_event_remap_chain_to_ast_node_str(self, text_aligner):
        state_machine = _build_state_machine(
            """
            state Root {
                state Bus;
                import "./child.fcstm" as Child {
                    event /Start -> /Bus.Start named "Top Start";
                    event /InnerBus.Stop -> /Bus.Stop named "Top Stop";
                }
                [*] -> Child;
            }
            """,
            **{
                "child.fcstm": """
                state ChildRoot {
                    state InnerBus;
                    import "./grand.fcstm" as Grand {
                        event /Pulse -> Start named "Child Start";
                        event /Halt -> /InnerBus.Stop named "Child Stop";
                    }
                    [*] -> Grand;
                }
                """,
                "grand.fcstm": """
                state GrandRoot {
                    event Pulse named "Pulse Source";
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : Pulse;
                    Running -> Idle : /Halt;
                }
                """,
            },
        )

        bus_state = state_machine.root_state.substates["Bus"]
        child_state = state_machine.root_state.substates["Child"]
        grand_state = child_state.substates["Grand"]

        assert grand_state.transitions[1].event is bus_state.events["Start"]
        assert grand_state.transitions[2].event is bus_state.events["Stop"]
        assert bus_state.events["Start"].extra_name == "Top Start"
        assert bus_state.events["Stop"].extra_name == "Top Stop"
        assert "Start" not in child_state.events
        assert "Stop" not in child_state.substates["InnerBus"].events

        text_aligner.assert_equal(
            expect=textwrap.dedent(
                """
                state Root {
                    state Child {
                        state Grand {
                            state Idle;
                            state Running;
                            [*] -> Idle;
                            Idle -> Running : /Bus.Start;
                            Running -> Idle : /Bus.Stop;
                        }
                        state InnerBus;
                        [*] -> Grand;
                    }
                    state Bus {
                        event Start named 'Top Start';
                        event Stop named 'Top Stop';
                    }
                    [*] -> Child;
                }
                """
            ).strip(),
            actual=str(state_machine.to_ast_node()),
        )
