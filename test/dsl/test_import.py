import pytest

from pyfcstm.dsl import (
    GrammarParseError,
    parse_state_machine_dsl,
    parse_with_grammar_entry,
)
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLImport:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                'import "./worker.fcstm" as Worker;',
                ImportStatement(
                    source_path="./worker.fcstm",
                    alias="Worker",
                    extra_name=None,
                    mappings=[],
                ),
            ),
            # Simple import without mapping block
            (
                'import "./motor.fcstm" as Motor named "Left Motor";',
                ImportStatement(
                    source_path="./motor.fcstm",
                    alias="Motor",
                    extra_name="Left Motor",
                    mappings=[],
                ),
            ),
            # Named import without mapping block
            (
                """
                import "./motor.fcstm" as Motor named "Left Motor" {
                    def counter -> left_counter;
                    event /Start -> Start named "Motor Start";
                }
                """,
                ImportStatement(
                    source_path="./motor.fcstm",
                    alias="Motor",
                    extra_name="Left Motor",
                    mappings=[
                        ImportDefMapping(
                            selector=ImportDefExactSelector(name="counter"),
                            target_template=ImportDefTargetTemplate(
                                template="left_counter"
                            ),
                        ),
                        ImportEventMapping(
                            source_event=ChainID(path=["Start"], is_absolute=True),
                            target_event=ChainID(path=["Start"]),
                            extra_name="Motor Start",
                        ),
                    ],
                ),
            ),
            # Import with exact variable mapping and relative event mapping
            (
                """
                import "./pair.fcstm" as Pair {
                    def {a, b, c} -> pair_*;
                    def a_*_b_* -> pair_${1}_${2};
                    def * -> pair_$0;
                    event /Stop -> /System.Stop;
                }
                """,
                ImportStatement(
                    source_path="./pair.fcstm",
                    alias="Pair",
                    extra_name=None,
                    mappings=[
                        ImportDefMapping(
                            selector=ImportDefSetSelector(names=["a", "b", "c"]),
                            target_template=ImportDefTargetTemplate(template="pair_*"),
                        ),
                        ImportDefMapping(
                            selector=ImportDefPatternSelector(pattern="a_*_b_*"),
                            target_template=ImportDefTargetTemplate(
                                template="pair_${1}_${2}"
                            ),
                        ),
                        ImportDefMapping(
                            selector=ImportDefFallbackSelector(),
                            target_template=ImportDefTargetTemplate(template="pair_$0"),
                        ),
                        ImportEventMapping(
                            source_event=ChainID(path=["Stop"], is_absolute=True),
                            target_event=ChainID(
                                path=["System", "Stop"],
                                is_absolute=True,
                            ),
                            extra_name=None,
                        ),
                    ],
                ),
            ),
            # Import with set selector, multi-wildcard selector, fallback, and absolute event target
            (
                """
                import "./complex.fcstm" as Complex named "Complex Module" {
                    ;
                    def sensor_* -> io_$1;
                    ;
                    def x_*_y_*_z_* -> xyz_${1}_${2}_${3};
                    event /Start -> Start;
                    ;
                    event /Reset -> /Plant.Reset named "Plant Reset";
                }
                """,
                ImportStatement(
                    source_path="./complex.fcstm",
                    alias="Complex",
                    extra_name="Complex Module",
                    mappings=[
                        ImportDefMapping(
                            selector=ImportDefPatternSelector(pattern="sensor_*"),
                            target_template=ImportDefTargetTemplate(template="io_$1"),
                        ),
                        ImportDefMapping(
                            selector=ImportDefPatternSelector(pattern="x_*_y_*_z_*"),
                            target_template=ImportDefTargetTemplate(
                                template="xyz_${1}_${2}_${3}"
                            ),
                        ),
                        ImportEventMapping(
                            source_event=ChainID(path=["Start"], is_absolute=True),
                            target_event=ChainID(path=["Start"]),
                            extra_name=None,
                        ),
                        ImportEventMapping(
                            source_event=ChainID(path=["Reset"], is_absolute=True),
                            target_event=ChainID(
                                path=["Plant", "Reset"],
                                is_absolute=True,
                            ),
                            extra_name="Plant Reset",
                        ),
                    ],
                ),
            ),
            # Import with empty statements in the block and multiple complex mappings
        ],
    )
    def test_positive_cases(self, input_text, expected):
        assert (
            parse_with_grammar_entry(input_text, entry_name="import_statement")
            == expected
        )

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            (
                'import "./worker.fcstm" as Worker;',
                "import './worker.fcstm' as Worker;",
            ),
            (
                'import "./motor.fcstm" as Motor named "Left Motor";',
                "import './motor.fcstm' as Motor named 'Left Motor';",
            ),
            (
                """
                import "./motor.fcstm" as Motor named "Left Motor" {
                    def counter -> left_counter;
                    event /Start -> Start named "Motor Start";
                }
                """,
                "import './motor.fcstm' as Motor named 'Left Motor' {\n"
                "    def counter -> left_counter;\n"
                "    event /Start -> Start named 'Motor Start';\n"
                "}",
            ),
            (
                """
                import "./pair.fcstm" as Pair {
                    def {a, b, c} -> pair_*;
                    def a_*_b_* -> pair_${1}_${2};
                    def * -> pair_$0;
                    event /Stop -> /System.Stop;
                }
                """,
                "import './pair.fcstm' as Pair {\n"
                "    def {a, b, c} -> pair_*;\n"
                "    def a_*_b_* -> pair_${1}_${2};\n"
                "    def * -> pair_$0;\n"
                "    event /Stop -> /System.Stop;\n"
                "}",
            ),
        ],
    )
    def test_positive_cases_str(self, input_text, expected_str):
        assert (
            str(parse_with_grammar_entry(input_text, entry_name="import_statement"))
            == expected_str
        )

    @pytest.mark.parametrize(
        "input_text",
        [
            'import "./worker.fcstm" Worker;',
            "import ./worker.fcstm as Worker;",
            'import "./worker.fcstm" as 123Worker;',
            'import "./worker.fcstm" as Worker { def a_ * -> out_$1; }',
            'import "./worker.fcstm" as Worker { def a_* -> out_ $1; }',
            'import "./worker.fcstm" as Worker { def a_* -> ${1} 2; }',
            'import "./worker.fcstm" as Worker { event /Start -> ; }',
            'import "./worker.fcstm" as Worker { def {a, b,} -> out_*; }',
        ],
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError):
            parse_with_grammar_entry(input_text, entry_name="import_statement")

    @pytest.mark.parametrize(
        ["input_text", "path", "expected"],
        [
            (
                """
                def int global_counter = 0;
                state Root {
                    import "./worker.fcstm" as Worker;
                    state Local;
                }
                """,
                None,
                StateMachineDSLProgram(
                    definitions=[
                        DefAssignment(
                            name="global_counter",
                            type="int",
                            expr=Integer(raw="0"),
                        )
                    ],
                    root_state=StateDefinition(
                        name="Root",
                        imports=[
                            ImportStatement(
                                source_path="./worker.fcstm",
                                alias="Worker",
                                extra_name=None,
                                mappings=[],
                            )
                        ],
                        substates=[
                            StateDefinition(
                                name="Local",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                            )
                        ],
                        transitions=[],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
                    source_path=None,
                ),
            ),
            # Program with a simple import inside the root state
            (
                """
                def int global_counter = 0;
                state Root {
                    event Shared;
                    import "./pair.fcstm" as Pair named "Pair Module" {
                        def counter -> pair_counter;
                        def {a, b, c} -> pair_*;
                        def a_*_b_* -> pair_${1}_${2};
                        def * -> pair_$0;
                        event /Start -> Start named "Pair Start";
                        event /Stop -> /System.Stop;
                    }
                    import "./worker.fcstm" as Worker;
                    [*] -> Local;
                    state Local;
                }
                """,
                "/tmp/root.fcstm",
                StateMachineDSLProgram(
                    definitions=[
                        DefAssignment(
                            name="global_counter",
                            type="int",
                            expr=Integer(raw="0"),
                        )
                    ],
                    root_state=StateDefinition(
                        name="Root",
                        events=[
                            EventDefinition(name="Shared", extra_name=None),
                        ],
                        imports=[
                            ImportStatement(
                                source_path="./pair.fcstm",
                                alias="Pair",
                                extra_name="Pair Module",
                                mappings=[
                                    ImportDefMapping(
                                        selector=ImportDefExactSelector(name="counter"),
                                        target_template=ImportDefTargetTemplate(
                                            template="pair_counter"
                                        ),
                                    ),
                                    ImportDefMapping(
                                        selector=ImportDefSetSelector(
                                            names=["a", "b", "c"]
                                        ),
                                        target_template=ImportDefTargetTemplate(
                                            template="pair_*"
                                        ),
                                    ),
                                    ImportDefMapping(
                                        selector=ImportDefPatternSelector(
                                            pattern="a_*_b_*"
                                        ),
                                        target_template=ImportDefTargetTemplate(
                                            template="pair_${1}_${2}"
                                        ),
                                    ),
                                    ImportDefMapping(
                                        selector=ImportDefFallbackSelector(),
                                        target_template=ImportDefTargetTemplate(
                                            template="pair_$0"
                                        ),
                                    ),
                                    ImportEventMapping(
                                        source_event=ChainID(
                                            path=["Start"],
                                            is_absolute=True,
                                        ),
                                        target_event=ChainID(path=["Start"]),
                                        extra_name="Pair Start",
                                    ),
                                    ImportEventMapping(
                                        source_event=ChainID(
                                            path=["Stop"],
                                            is_absolute=True,
                                        ),
                                        target_event=ChainID(
                                            path=["System", "Stop"],
                                            is_absolute=True,
                                        ),
                                        extra_name=None,
                                    ),
                                ],
                            ),
                            ImportStatement(
                                source_path="./worker.fcstm",
                                alias="Worker",
                                extra_name=None,
                                mappings=[],
                            ),
                        ],
                        substates=[
                            StateDefinition(
                                name="Local",
                                substates=[],
                                transitions=[],
                                enters=[],
                                durings=[],
                                exits=[],
                            )
                        ],
                        transitions=[
                            TransitionDefinition(
                                from_state=INIT_STATE,
                                to_state="Local",
                                event_id=None,
                                condition_expr=None,
                                post_operations=[],
                            )
                        ],
                        enters=[],
                        durings=[],
                        exits=[],
                    ),
                    source_path="/tmp/root.fcstm",
                ),
            ),
            # Program with multiple imports, root event, transition, and source path
        ],
    )
    def test_state_machine_positive_cases(self, input_text, path, expected):
        assert parse_state_machine_dsl(input_text, path=path) == expected
