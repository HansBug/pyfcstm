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
class TestImportPhase3Assembly:
    def test_imported_top_level_definitions_use_default_alias_prefix_mapping(self):
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
            state_machine = parse_dsl_node_to_state_machine(ast_node, path=root_file)

        assert sorted(state_machine.defines.keys()) == ["Worker_counter"]
        assert state_machine.defines["Worker_counter"].type == "int"
        assert str(state_machine.defines["Worker_counter"].init.to_ast_node()) == "0"

    def test_def_mapping_rewrites_deep_variable_usage_consistently(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                def int host_counter = 0;
                def int host_guard = 1;
                def int host_limit = 10;
                def int host_result = 0;

                state Root {
                    import "./worker.fcstm" as Worker {
                        def counter -> host_counter;
                        def guard_flag -> host_guard;
                        def limit -> host_limit;
                        def result -> host_result;
                    }
                    [*] -> Worker;
                }
                """,
            )
            _write_text_file(
                "worker.fcstm",
                """
                def int counter = 0;
                def int guard_flag = 0;
                def int limit = 0;
                def int result = 0;

                state WorkerRoot {
                    enter {
                        counter = counter + 1;
                    }
                    state Idle {
                        during {
                            result = counter + limit;
                        }
                    }
                    state Busy {
                        enter {
                            counter = counter + 1;
                        }
                        during {
                            result = counter + guard_flag;
                        }
                    }
                    [*] -> Idle;
                    Idle -> Busy : if [guard_flag > 0];
                    Busy -> Idle : if [counter >= limit] effect {
                        result = counter;
                    }
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            state_machine = parse_dsl_node_to_state_machine(ast_node, path=root_file)

        assert sorted(state_machine.defines.keys()) == [
            "host_counter",
            "host_guard",
            "host_limit",
            "host_result",
        ]
        worker_state = state_machine.root_state.substates["Worker"]
        idle_state = worker_state.substates["Idle"]
        busy_state = worker_state.substates["Busy"]

        assert worker_state.on_enters[0].operations[0].var_name == "host_counter"
        assert (
            worker_state.on_enters[0].operations[0].expr.list_variables()[0].name
            == "host_counter"
        )

        assert idle_state.on_durings[0].operations[0].var_name == "host_result"
        assert sorted(
            v.name for v in idle_state.on_durings[0].operations[0].expr.list_variables()
        ) == [
            "host_counter",
            "host_limit",
        ]

        assert busy_state.on_enters[0].operations[0].var_name == "host_counter"
        assert busy_state.on_durings[0].operations[0].var_name == "host_result"
        assert sorted(
            v.name for v in busy_state.on_durings[0].operations[0].expr.list_variables()
        ) == [
            "host_counter",
            "host_guard",
        ]

        idle_to_busy = worker_state.transitions[1]
        busy_to_idle = worker_state.transitions[2]
        assert sorted(v.name for v in idle_to_busy.guard.list_variables()) == [
            "host_guard"
        ]
        assert sorted(v.name for v in busy_to_idle.guard.list_variables()) == [
            "host_counter",
            "host_limit",
        ]
        assert busy_to_idle.effects[0].var_name == "host_result"
        assert sorted(v.name for v in busy_to_idle.effects[0].expr.list_variables()) == [
            "host_counter"
        ]

    def test_default_mapping_isolates_same_module_imported_twice(self):
        state_machine = _build_state_machine(
            """
            state Root {
                import "./worker.fcstm" as LeftWorker;
                import "./worker.fcstm" as RightWorker;
                [*] -> LeftWorker;
            }
            """,
            **{
                "worker.fcstm": """
                def int counter = 1;
                def int threshold = 2;

                state WorkerRoot {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            },
        )

        assert sorted(state_machine.defines.keys()) == [
            "LeftWorker_counter",
            "LeftWorker_threshold",
            "RightWorker_counter",
            "RightWorker_threshold",
        ]

    def test_mapping_priority_and_placeholder_semantics(self):
        state_machine = _build_state_machine(
            """
            state Root {
                import "./worker.fcstm" as Worker {
                    def counter -> exact_counter;
                    def {status_flag, a, b, c} -> set_*;
                    def sensor_* -> sensor_$1;
                    def a_*_b_* -> pair_${1}_${2}_${0};
                    def * -> fallback_$0;
                }
                [*] -> Worker;
            }
            """,
            **{
                "worker.fcstm": """
                def int counter = 1;
                def int status_flag = 2;
                def int sensor_temp = 3;
                def int a_main_b_low = 4;
                def int timeout = 5;
                def int a = 6;
                def int b = 7;
                def int c = 8;

                state WorkerRoot {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            },
        )

        assert sorted(state_machine.defines.keys()) == [
            "exact_counter",
            "fallback_timeout",
            "pair_main_low_a_main_b_low",
            "sensor_temp",
            "set_a",
            "set_b",
            "set_c",
            "set_status_flag",
        ]

    @pytest.mark.parametrize(
        ["mapping_block", "message_fragment"],
        [
            (
                """
                def counter -> x1;
                def counter -> x2;
                """,
                "duplicated exact selector 'counter'",
            ),
            (
                """
                def {a, a} -> x;
                """,
                "duplicated selector name 'a' inside set rule",
            ),
            (
                """
                def {a, b} -> x1_*;
                def {b, c} -> x2_*;
                """,
                "selector name 'b' appears in multiple set rules",
            ),
            (
                """
                def * -> first_$0;
                def * -> second_$0;
                """,
                "multiple fallback rules found",
            ),
            (
                """
                def a_* -> left_$1;
                def *_b -> right_$1;
                def * -> passthrough_$0;
                """,
                "source variable 'a_b' matches multiple pattern rules",
            ),
        ],
    )
    def test_mapping_conflict_rules(self, mapping_block, message_fragment):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                f"""
                state Root {{
                    import "./worker.fcstm" as Worker {{
                        {textwrap.dedent(mapping_block).strip()}
                    }}
                    [*] -> Worker;
                }}
                """,
            )
            _write_text_file(
                "worker.fcstm",
                """
                def int counter = 0;
                def int a = 0;
                def int a_b = 0;
                def int b = 0;
                def int c = 0;

                state WorkerRoot {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        assert message_fragment in str(exc_info.value)

    @pytest.mark.parametrize(
        ["mapping_block", "message_fragment"],
        [
            (
                """
                def {a, b} -> shared_var;
                """,
                "maps multiple source variables to the same target variable 'shared_var'",
            ),
            (
                """
                def a_* -> shared_var;
                def * -> shared_var;
                """,
                "maps multiple source variables to the same target variable 'shared_var'",
            ),
            (
                """
                def * -> shared_var;
                """,
                "maps multiple source variables to the same target variable 'shared_var'",
            ),
        ],
    )
    def test_single_import_many_to_one_is_rejected(
        self, mapping_block, message_fragment
    ):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                f"""
                state Root {{
                    import "./worker.fcstm" as Worker {{
                        {textwrap.dedent(mapping_block).strip()}
                    }}
                    [*] -> Worker;
                }}
                """,
            )
            _write_text_file(
                "worker.fcstm",
                """
                def int a = 1;
                def int b = 2;

                state WorkerRoot {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        assert message_fragment in str(exc_info.value)

    def test_pattern_template_rejects_ambiguous_bare_star(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    import "./worker.fcstm" as Worker {
                        def a_*_b_* -> pair_*;
                    }
                    [*] -> Worker;
                }
                """,
            )
            _write_text_file(
                "worker.fcstm",
                """
                def int a_main_b_low = 0;

                state WorkerRoot {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        message = str(exc_info.value)
        assert "bare '*'" in message
        assert "ambiguous" in message

    def test_pattern_template_rejects_out_of_range_placeholder(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    import "./worker.fcstm" as Worker {
                        def sensor_* -> sensor_$2;
                    }
                    [*] -> Worker;
                }
                """,
            )
            _write_text_file(
                "worker.fcstm",
                """
                def int sensor_temp = 0;

                state WorkerRoot {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        message = str(exc_info.value)
        assert "placeholder $2 is out of range" in message
        assert "sensor_temp" in message

    def test_missing_mapping_match_is_rejected_without_fallback(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    import "./worker.fcstm" as Worker {
                        def counter -> host_counter;
                    }
                    [*] -> Worker;
                }
                """,
            )
            _write_text_file(
                "worker.fcstm",
                """
                def int counter = 0;
                def int timeout = 1;

                state WorkerRoot {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        message = str(exc_info.value)
        assert "source variable 'timeout'" in message
        assert "is not matched by any def mapping rule" in message

    def test_host_existing_variable_type_mismatch_is_rejected(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                def float shared_counter = 0.0;

                state Root {
                    import "./worker.fcstm" as Worker {
                        def counter -> shared_counter;
                    }
                    [*] -> Worker;
                }
                """,
            )
            _write_text_file(
                "worker.fcstm",
                """
                def int counter = 1;

                state WorkerRoot {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        message = str(exc_info.value)
        assert "already exists in host model as type 'float'" in message
        assert "cannot bind imported type 'int'" in message

    def test_cross_import_shared_target_with_same_type_and_init_is_allowed(self):
        state_machine = _build_state_machine(
            """
            state Root {
                import "./a.fcstm" as A {
                    def counter -> shared_counter;
                }
                import "./b.fcstm" as B {
                    def pulse_count -> shared_counter;
                }
                [*] -> A;
            }
            """,
            **{
                "a.fcstm": """
                def int counter = 7;

                state ModuleA {
                    state Idle;
                    [*] -> Idle;
                }
                """,
                "b.fcstm": """
                def int pulse_count = 7;

                state ModuleB {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            },
        )

        assert sorted(state_machine.defines.keys()) == ["shared_counter"]
        assert state_machine.defines["shared_counter"].type == "int"
        assert str(state_machine.defines["shared_counter"].init.to_ast_node()) == "7"

    def test_cross_import_shared_target_with_conflicting_init_is_rejected(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    import "./a.fcstm" as A {
                        def counter -> shared_counter;
                    }
                    import "./b.fcstm" as B {
                        def pulse_count -> shared_counter;
                    }
                    [*] -> A;
                }
                """,
            )
            _write_text_file(
                "a.fcstm",
                """
                def int counter = 1;

                state ModuleA {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )
            _write_text_file(
                "b.fcstm",
                """
                def int pulse_count = 2;

                state ModuleB {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        assert "target variable 'shared_counter' has conflicting initial values" in str(
            exc_info.value
        )

    def test_cross_import_shared_target_with_different_type_is_rejected(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    import "./a.fcstm" as A {
                        def counter -> shared_counter;
                    }
                    import "./b.fcstm" as B {
                        def pulse_count -> shared_counter;
                    }
                    [*] -> A;
                }
                """,
            )
            _write_text_file(
                "a.fcstm",
                """
                def int counter = 1;

                state ModuleA {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )
            _write_text_file(
                "b.fcstm",
                """
                def float pulse_count = 1.0;

                state ModuleB {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )

            ast_node = parse_state_machine_dsl(root_file.read_text(encoding="utf-8"))
            with pytest.raises(SyntaxError) as exc_info:
                parse_dsl_node_to_state_machine(ast_node, path=root_file)

        message = str(exc_info.value)
        assert (
            "target variable 'shared_counter' receives incompatible imported types"
            in message
        )
        assert "'int' and 'float'" in message

    def test_host_explicit_definition_overrides_import_initial_values(self):
        state_machine = _build_state_machine(
            """
            def int shared_counter = 99;

            state Root {
                import "./a.fcstm" as A {
                    def counter -> shared_counter;
                }
                import "./b.fcstm" as B {
                    def pulse_count -> shared_counter;
                }
                [*] -> A;
            }
            """,
            **{
                "a.fcstm": """
                def int counter = 1;

                state ModuleA {
                    state Idle;
                    [*] -> Idle;
                }
                """,
                "b.fcstm": """
                def int pulse_count = 2;

                state ModuleB {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            },
        )

        assert sorted(state_machine.defines.keys()) == ["shared_counter"]
        assert state_machine.defines["shared_counter"].type == "int"
        assert str(state_machine.defines["shared_counter"].init.to_ast_node()) == "99"

    def test_def_mapping_rewrites_nested_if_blocks_consistently(self):
        state_machine = _build_state_machine(
            """
            def int host_x = 0;
            def int host_y = 0;
            def int host_z = 0;
            def int host_flag = 0;

            state Root {
                import "./worker.fcstm" as Worker {
                    def x -> host_x;
                    def y -> host_y;
                    def z -> host_z;
                    def flag -> host_flag;
                }
                [*] -> Worker;
            }
            """,
            **{
                "worker.fcstm": """
                def int x = 0;
                def int y = 0;
                def int z = 0;
                def int flag = 0;

                state WorkerRoot {
                    state Active {
                        during {
                            if [flag > 0] {
                                x = y + 1;
                            } else if [x > 3] {
                                if [y > 5] {
                                    z = x + y;
                                } else {
                                    z = x - y;
                                }
                            } else {
                                z = x;
                            }
                        }
                    }

                    [*] -> Active;
                }
                """,
            },
        )

        worker_state = state_machine.root_state.substates["Worker"]
        active_state = worker_state.substates["Active"]
        top_if = active_state.on_durings[0].operations[0]

        assert top_if.branches[0].condition is not None
        assert sorted(v.name for v in top_if.branches[0].condition.list_variables()) == [
            "host_flag"
        ]
        assert top_if.branches[0].statements[0].var_name == "host_x"
        assert sorted(
            v.name for v in top_if.branches[0].statements[0].expr.list_variables()
        ) == ["host_y"]

        assert sorted(v.name for v in top_if.branches[1].condition.list_variables()) == [
            "host_x"
        ]
        nested_if = top_if.branches[1].statements[0]
        assert sorted(
            v.name for v in nested_if.branches[0].condition.list_variables()
        ) == ["host_y"]
        assert nested_if.branches[0].statements[0].var_name == "host_z"
        assert sorted(
            v.name for v in nested_if.branches[0].statements[0].expr.list_variables()
        ) == ["host_x", "host_y"]
        assert nested_if.branches[1].statements[0].var_name == "host_z"
        assert sorted(
            v.name for v in nested_if.branches[1].statements[0].expr.list_variables()
        ) == ["host_x", "host_y"]

        assert top_if.branches[2].condition is None
        assert top_if.branches[2].statements[0].var_name == "host_z"
        assert sorted(
            v.name for v in top_if.branches[2].statements[0].expr.list_variables()
        ) == ["host_x"]

    def test_phase3_complete_example_to_ast_node_str(self, text_aligner):
        state_machine = _build_state_machine(
            """
            def int host_counter = 0;
            def int host_guard = 1;
            def int host_limit = 10;
            def int host_result = 0;

            state Root {
                import "./worker.fcstm" as Worker named "Worker Module" {
                    def counter -> host_counter;
                    def guard_flag -> host_guard;
                    def limit -> host_limit;
                    def result -> host_result;
                }
                [*] -> Worker;
            }
            """,
            **{
                "worker.fcstm": """
                def int counter = 0;
                def int guard_flag = 0;
                def int limit = 0;
                def int result = 0;

                state WorkerRoot {
                    enter {
                        counter = counter + 1;
                    }
                    state Idle {
                        during {
                            result = counter + limit;
                        }
                    }
                    state Busy {
                        enter {
                            counter = counter + 1;
                        }
                        during {
                            result = counter + guard_flag;
                        }
                    }
                    [*] -> Idle;
                    Idle -> Busy : if [guard_flag > 0];
                    Busy -> Idle : if [counter >= limit] effect {
                        result = counter;
                    }
                }
                """,
            },
        )

        text_aligner.assert_equal(
            expect=textwrap.dedent(
                """
                def int host_counter = 0;
                def int host_guard = 1;
                def int host_limit = 10;
                def int host_result = 0;
                state Root {
                    state Worker named 'Worker Module' {
                        enter {
                            host_counter = host_counter + 1;
                        }
                        state Idle {
                            during {
                                host_result = host_counter + host_limit;
                            }
                        }
                        state Busy {
                            enter {
                                host_counter = host_counter + 1;
                            }
                            during {
                                host_result = host_counter + host_guard;
                            }
                        }
                        [*] -> Idle;
                        Idle -> Busy : if [host_guard > 0];
                        Busy -> Idle : if [host_counter >= host_limit] effect {
                            host_result = host_counter;
                        }
                    }
                    [*] -> Worker;
                }
                """
            ).strip(),
            actual=str(state_machine.to_ast_node()),
        )

    def test_phase3_default_mapping_to_ast_node_str(self, text_aligner):
        state_machine = _build_state_machine(
            """
            state Root {
                import "./worker.fcstm" as Worker;
                [*] -> Worker;
            }
            """,
            **{
                "worker.fcstm": """
                def int counter = 0;
                def int threshold = 3;

                state WorkerRoot {
                    state Idle;
                    [*] -> Idle;
                    Idle -> Idle : if [counter < threshold] effect {
                        counter = counter + 1;
                    }
                }
                """,
            },
        )

        text_aligner.assert_equal(
            expect=textwrap.dedent(
                """
                def int Worker_counter = 0;
                def int Worker_threshold = 3;
                state Root {
                    state Worker {
                        state Idle;
                        [*] -> Idle;
                        Idle -> Idle : if [Worker_counter < Worker_threshold] effect {
                            Worker_counter = Worker_counter + 1;
                        }
                    }
                    [*] -> Worker;
                }
                """
            ).strip(),
            actual=str(state_machine.to_ast_node()),
        )

    def test_phase3_shared_cross_import_mapping_to_ast_node_str(self, text_aligner):
        state_machine = _build_state_machine(
            """
            state Root {
                import "./left.fcstm" as A {
                    def counter -> shared_counter;
                    def ready_flag -> shared_flag;
                }
                import "./right.fcstm" as B {
                    def pulse_count -> shared_counter;
                    def armed_flag -> shared_flag;
                }
                [*] -> A;
            }
            """,
            **{
                "left.fcstm": """
                def int counter = 0;
                def int ready_flag = 1;

                state LeftRoot {
                    state Idle;
                    [*] -> Idle;
                    Idle -> Idle : if [ready_flag > 0] effect {
                        counter = counter + 1;
                    }
                }
                """,
                "right.fcstm": """
                def int pulse_count = 0;
                def int armed_flag = 1;

                state RightRoot {
                    state Idle;
                    [*] -> Idle;
                    Idle -> Idle : if [armed_flag > 0] effect {
                        pulse_count = pulse_count + 1;
                    }
                }
                """,
            },
        )

        text_aligner.assert_equal(
            expect=textwrap.dedent(
                """
                def int shared_counter = 0;
                def int shared_flag = 1;
                state Root {
                    state A {
                        state Idle;
                        [*] -> Idle;
                        Idle -> Idle : if [shared_flag > 0] effect {
                            shared_counter = shared_counter + 1;
                        }
                    }
                    state B {
                        state Idle;
                        [*] -> Idle;
                        Idle -> Idle : if [shared_flag > 0] effect {
                            shared_counter = shared_counter + 1;
                        }
                    }
                    [*] -> A;
                }
                """
            ).strip(),
            actual=str(state_machine.to_ast_node()),
        )

    def test_phase3_distinct_cross_import_mapping_to_ast_node_str(self, text_aligner):
        state_machine = _build_state_machine(
            """
            state Root {
                import "./worker.fcstm" as Left {
                    def counter -> left_counter;
                    def limit -> left_limit;
                }
                import "./worker.fcstm" as Right {
                    def counter -> right_counter;
                    def limit -> right_limit;
                }
                [*] -> Left;
            }
            """,
            **{
                "worker.fcstm": """
                def int counter = 0;
                def int limit = 5;

                state WorkerRoot {
                    state Idle;
                    [*] -> Idle;
                    Idle -> Idle : if [counter < limit] effect {
                        counter = counter + 1;
                    }
                }
                """,
            },
        )

        text_aligner.assert_equal(
            expect=textwrap.dedent(
                """
                def int left_counter = 0;
                def int left_limit = 5;
                def int right_counter = 0;
                def int right_limit = 5;
                state Root {
                    state Left {
                        state Idle;
                        [*] -> Idle;
                        Idle -> Idle : if [left_counter < left_limit] effect {
                            left_counter = left_counter + 1;
                        }
                    }
                    state Right {
                        state Idle;
                        [*] -> Idle;
                        Idle -> Idle : if [right_counter < right_limit] effect {
                            right_counter = right_counter + 1;
                        }
                    }
                    [*] -> Left;
                }
                """
            ).strip(),
            actual=str(state_machine.to_ast_node()),
        )

    def test_phase3_mapping_syntax_combo_to_ast_node_str(self, text_aligner):
        state_machine = _build_state_machine(
            """
            state Root {
                import "./worker.fcstm" as Worker {
                    def counter -> exact_counter;
                    def {status_flag, a, b, c} -> set_*;
                    def sensor_* -> sensor_$1;
                    def a_*_b_* -> pair_${1}_${2}_${0};
                    def * -> fallback_$0;
                }
                [*] -> Worker;
            }
            """,
            **{
                "worker.fcstm": """
                def int counter = 1;
                def int status_flag = 2;
                def int sensor_temp = 3;
                def int a_main_b_low = 4;
                def int timeout = 5;
                def int a = 6;
                def int b = 7;
                def int c = 8;

                state WorkerRoot {
                    state Idle {
                        during {
                            counter = counter + status_flag;
                            status_flag = status_flag + a + b + c;
                            sensor_temp = sensor_temp + 1;
                            timeout = timeout + a_main_b_low;
                        }
                    }
                    [*] -> Idle;
                }
                """,
            },
        )

        text_aligner.assert_equal(
            expect=textwrap.dedent(
                """
                def int exact_counter = 1;
                def int set_status_flag = 2;
                def int sensor_temp = 3;
                def int pair_main_low_a_main_b_low = 4;
                def int fallback_timeout = 5;
                def int set_a = 6;
                def int set_b = 7;
                def int set_c = 8;
                state Root {
                    state Worker {
                        state Idle {
                            during {
                                exact_counter = exact_counter + set_status_flag;
                                set_status_flag = set_status_flag + set_a + set_b + set_c;
                                sensor_temp = sensor_temp + 1;
                                fallback_timeout = fallback_timeout + pair_main_low_a_main_b_low;
                            }
                        }
                        [*] -> Idle;
                    }
                    [*] -> Worker;
                }
                """
            ).strip(),
            actual=str(state_machine.to_ast_node()),
        )
