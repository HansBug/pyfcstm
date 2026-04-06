import os.path
import pathlib
import textwrap

import pytest
from hbutils.system import TemporaryDirectory
from hbutils.testing import simulate_entry, isolated_directory

from pyfcstm.entry import pyfcstmcli
from pyfcstm.entry.plantuml import build_plantuml_output


@pytest.fixture()
def input_code_file():
    with TemporaryDirectory() as td:
        code_file = os.path.join(td, "code.fcstm")
        with open(code_file, "w") as f:
            print(
                textwrap.dedent("""
    def int a = 0;
    def int b = 0x2 | 0x5;

    state LX {
        [*] -> LX1;
        [*] -> LX2 :: EEE;

        enter {
            b = 0 + b;
            b = 3 + a * (2 + b);
        }

        exit {
            b = 0;
            b = a << 2;
        }

        state LX1 {
            during before abstract BeforeLX1Enter;
            during after abstract AfterLX1Enter /*
                this is the comment line
            */
            during before {
                b = 1 + 2;
            }
            during after {
                b = 3 - 2;
                b = 3 + 2 + a;
            }

            state LX11 {
                enter abstract LX11Enter;
                exit abstract LX11Exit;
                during abstract LX11During; 
                enter abstract /*
                    This is X
                */
                during {
                    b = 0x2 << 0x3;
                    b = b + -1;
                }
            }
            state LX12;
            state LX13;
            state LX14;

            [*] -> LX11;
            LX11 -> LX12 :: E1;
            LX12 -> LX13 :: E1;
            LX12 -> LX14 :: E2;

            LX13 -> [*] :: E1 effect {
                a = 0x2;
            }
            LX13 -> [*] :: E2 effect {
                a = 0x3;
            }
            LX13 -> LX14 :: E3;
            LX13 -> LX14 :: E4;
            LX14 -> LX12 :: E1;
            LX14 -> [*] :: E2 effect {
                a = 0x1;
            }
        }

        state LX2 {
            [*] -> LX21;
            state LX21 {
                state LX211;
                state LX212;
                [*] -> LX211 : if [a == 0x2];
                [*] -> LX212 : if [a == 0x3];
                LX211 -> [*] :: E1 effect {
                    a = 0x1;
                }
                LX211 -> LX212 :: E2;
                LX212 -> [*] :: E1 effect {
                    a = 0x1;
                }
                LX212 -> LX211 : E2;
            }
            LX21 -> [*] : if [a == 0x1];
        }

        LX1 -> LX2 : if [a == 0x2 || a == 0x3];
        LX1 -> LX1 : if [a == 0x1];
        LX2 -> LX1 : if [a == 0x1];
    }
    """).strip(),
                file=f,
            )

        yield code_file


@pytest.fixture()
def expected_plantuml_code():
    return textwrap.dedent("""
@startuml
hide empty description

skinparam state {
  BackgroundColor<<pseudo>> LightGray
  BackgroundColor<<composite>> LightBlue
  BorderColor<<pseudo>> Gray
  FontStyle<<pseudo>> italic
}

legend top left
|= Variable |= Type |= Initial Value |
| a | int | 0 |
| b | int | 2 \\| 5 |
endlegend

state "LX" as lx <<composite>> {
    state "LX1" as lx__lx1 <<composite>> {
        state "LX11" as lx__lx1__lx11
        state "LX12" as lx__lx1__lx12
        state "LX13" as lx__lx1__lx13
        state "LX14" as lx__lx1__lx14
        [*] --> lx__lx1__lx11
        lx__lx1__lx11 --> lx__lx1__lx12 : LX11.E1
        lx__lx1__lx12 --> lx__lx1__lx13 : LX12.E1
        lx__lx1__lx12 --> lx__lx1__lx14 : LX12.E2
        lx__lx1__lx13 --> [*] : LX13.E1
        note on link
        effect {
            a = 2;
        }
        end note
        lx__lx1__lx13 --> [*] : LX13.E2
        note on link
        effect {
            a = 3;
        }
        end note
        lx__lx1__lx13 --> lx__lx1__lx14 : LX13.E3
        lx__lx1__lx13 --> lx__lx1__lx14 : LX13.E4
        lx__lx1__lx14 --> lx__lx1__lx12 : LX14.E1
        lx__lx1__lx14 --> [*] : LX14.E2
        note on link
        effect {
            a = 1;
        }
        end note
    }
    state "LX2" as lx__lx2 <<composite>> {
        state "LX21" as lx__lx2__lx21 <<composite>> {
            state "LX211" as lx__lx2__lx21__lx211
            state "LX212" as lx__lx2__lx21__lx212
            [*] --> lx__lx2__lx21__lx211 : a == 2
            [*] --> lx__lx2__lx21__lx212 : a == 3
            lx__lx2__lx21__lx211 --> [*] : LX211.E1
            note on link
            effect {
                a = 1;
            }
            end note
            lx__lx2__lx21__lx211 --> lx__lx2__lx21__lx212 : LX211.E2
            lx__lx2__lx21__lx212 --> [*] : LX212.E1
            note on link
            effect {
                a = 1;
            }
            end note
            lx__lx2__lx21__lx212 --> lx__lx2__lx21__lx211 : E2
        }
        [*] --> lx__lx2__lx21
        lx__lx2__lx21 --> [*] : a == 1
    }
    [*] --> lx__lx1
    [*] --> lx__lx2 : EEE
    lx__lx1 --> lx__lx2 : a == 2 || a == 3
    lx__lx1 --> lx__lx1 : a == 1
    lx__lx2 --> lx__lx1 : a == 1
}
[*] --> lx
lx --> [*]
@enduml
    """).strip()


@pytest.mark.unittest
class TestEntryPlantuml:
    def test_simple_plantuml_to_stdout(
        self, input_code_file, expected_plantuml_code, text_aligner
    ):
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
            ],
        )
        assert result.exitcode == 0
        text_aligner.assert_equal(
            expect=expected_plantuml_code,
            actual=result.stdout,
        )

    def test_simple_plantuml_to_file(
        self, input_code_file, expected_plantuml_code, text_aligner
    ):
        with isolated_directory():
            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "plantuml",
                    "-i",
                    input_code_file,
                    "-o",
                    "output_code.plantuml",
                ],
            )
            assert result.exitcode == 0

            text_aligner.assert_equal(
                expect=expected_plantuml_code,
                actual=pathlib.Path("output_code.plantuml").read_text(),
            )

    def test_plantuml_with_detail_level_minimal(self, input_code_file):
        """Test plantuml with minimal detail level."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-l",
                "minimal",
            ],
        )
        assert result.exitcode == 0
        assert "@startuml" in result.stdout
        assert "@enduml" in result.stdout

    def test_plantuml_with_detail_level_full(self, input_code_file):
        """Test plantuml with full detail level."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-l",
                "full",
            ],
        )
        assert result.exitcode == 0
        assert "@startuml" in result.stdout
        assert "@enduml" in result.stdout

    def test_plantuml_with_config_options(self, input_code_file):
        """Test plantuml with configuration options."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-c",
                "show_events=true",
                "-c",
                "max_depth=2",
            ],
        )
        assert result.exitcode == 0
        assert "@startuml" in result.stdout
        assert "@enduml" in result.stdout

    def test_plantuml_with_bool_config(self, input_code_file):
        """Test plantuml with boolean configuration options."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-c",
                "show_variable_definitions=true",
                "-c",
                "use_skinparam=false",
            ],
        )
        assert result.exitcode == 0
        assert "@startuml" in result.stdout

    def test_plantuml_with_int_config(self, input_code_file):
        """Test plantuml with integer configuration options."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-c",
                "max_depth=3",
                "-c",
                "max_action_lines=10",
            ],
        )
        assert result.exitcode == 0
        assert "@startuml" in result.stdout

    def test_plantuml_with_tuple_config(self, input_code_file):
        """Test plantuml with tuple configuration options."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-c",
                "state_name_format=name,path",
                "-c",
                "event_name_format=name,relpath",
            ],
        )
        assert result.exitcode == 0
        assert "@startuml" in result.stdout

    def test_plantuml_with_string_config(self, input_code_file):
        """Test plantuml with string configuration options."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-c",
                "event_visualization_mode=color",
                "-c",
                "variable_display_mode=legend",
            ],
        )
        assert result.exitcode == 0
        assert "@startuml" in result.stdout

    def test_plantuml_with_combined_level_and_config(self, input_code_file):
        """Test plantuml with both detail level and config options."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-l",
                "full",
                "-c",
                "max_depth=3",
                "-c",
                "event_visualization_mode=both",
            ],
        )
        assert result.exitcode == 0
        assert "@startuml" in result.stdout

    def test_plantuml_missing_input_file(self):
        """Test plantuml with missing required input file."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
            ],
        )
        assert result.exitcode != 0
        assert "Missing option" in result.stderr or "required" in result.stderr.lower()

    def test_plantuml_invalid_detail_level(self, input_code_file):
        """Test plantuml with invalid detail level."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-l",
                "invalid",
            ],
        )
        assert result.exitcode != 0

    def test_plantuml_invalid_config_format(self, input_code_file):
        """Test plantuml with invalid config format (missing equals sign)."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-c",
                "invalid_format",
            ],
        )
        assert result.exitcode != 0

    def test_plantuml_nonexistent_input_file(self):
        """Test plantuml with nonexistent input file."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                "/nonexistent/file.fcstm",
            ],
        )
        assert result.exitcode != 0

    def test_plantuml_output_to_nested_directory(self, input_code_file):
        """Test plantuml output to nested directory."""
        with isolated_directory():
            os.makedirs("output/nested", exist_ok=True)
            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "plantuml",
                    "-i",
                    input_code_file,
                    "-o",
                    "output/nested/result.puml",
                ],
            )
            assert result.exitcode == 0
            assert pathlib.Path("output/nested/result.puml").exists()
            content = pathlib.Path("output/nested/result.puml").read_text()
            assert "@startuml" in content
            assert "@enduml" in content

    def test_plantuml_multiple_config_options(self, input_code_file):
        """Test plantuml with many configuration options."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-c",
                "show_events=true",
                "-c",
                "max_depth=2",
                "-c",
                "use_skinparam=true",
                "-c",
                "use_stereotypes=true",
                "-c",
                "collapse_empty_states=false",
            ],
        )
        assert result.exitcode == 0
        assert "@startuml" in result.stdout

    def test_plantuml_case_insensitive_detail_level(self, input_code_file):
        """Test plantuml with case-insensitive detail level."""
        for level in ["MINIMAL", "Normal", "FuLl"]:
            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "plantuml",
                    "-i",
                    input_code_file,
                    "-l",
                    level,
                ],
            )
            assert result.exitcode == 0
            assert "@startuml" in result.stdout

    def test_plantuml_variable_legend_position(self, input_code_file):
        """Test plantuml with variable_legend_position configuration."""
        # Test default position (top left)
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-c",
                "show_variable_definitions=true",
                "-c",
                "variable_display_mode=legend",
            ],
        )
        assert result.exitcode == 0
        assert "legend top left" in result.stdout
        assert "@startuml" in result.stdout

        # Test custom position (bottom right)
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-c",
                "show_variable_definitions=true",
                "-c",
                "variable_display_mode=legend",
                "-c",
                "variable_legend_position=bottom right",
            ],
        )
        assert result.exitcode == 0
        assert "legend bottom right" in result.stdout
        assert "@startuml" in result.stdout

    def test_plantuml_event_legend_position(self, input_code_file):
        """Test plantuml with event_legend_position configuration."""
        # Test default position (right)
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-c",
                "event_visualization_mode=legend",
            ],
        )
        assert result.exitcode == 0
        # Event legend should be present (if there are events in the test file)
        assert "@startuml" in result.stdout

        # Test custom position (top left)
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-c",
                "event_visualization_mode=legend",
                "-c",
                "event_legend_position=top left",
            ],
        )
        assert result.exitcode == 0
        assert "@startuml" in result.stdout

    def test_plantuml_both_legend_positions(self, input_code_file):
        """Test plantuml with both variable and event legend positions."""
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "plantuml",
                "-i",
                input_code_file,
                "-c",
                "show_variable_definitions=true",
                "-c",
                "variable_display_mode=legend",
                "-c",
                "variable_legend_position=top left",
                "-c",
                "event_visualization_mode=legend",
                "-c",
                "event_legend_position=bottom right",
            ],
        )
        assert result.exitcode == 0
        assert "legend top left" in result.stdout
        assert "@startuml" in result.stdout

    def test_plantuml_all_legend_positions(self, input_code_file):
        """Test plantuml with all available legend positions."""
        positions = [
            "top left", "top center", "top right",
            "bottom left", "bottom center", "bottom right",
            "left", "right", "center"
        ]

        for position in positions:
            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "plantuml",
                    "-i",
                    input_code_file,
                    "-c",
                    "show_variable_definitions=true",
                    "-c",
                    "variable_display_mode=legend",
                    "-c",
                    f"variable_legend_position={position}",
                ],
            )
            assert result.exitcode == 0
            assert f"legend {position}" in result.stdout
            assert "@startuml" in result.stdout

    def test_plantuml_with_import_supports_multi_file_model(self, text_aligner):
        expected = textwrap.dedent(
            """
            @startuml
            hide empty description

            skinparam state {
              BackgroundColor<<pseudo>> LightGray
              BackgroundColor<<composite>> LightBlue
              BorderColor<<pseudo>> Gray
              FontStyle<<pseudo>> italic
            }

            state "Root" as root <<composite>> {
                state "Worker" as root__worker <<composite>> {
                    state "Idle" as root__worker__idle
                    state "Running" as root__worker__running
                    [*] --> root__worker__idle
                    root__worker__idle --> root__worker__running : Idle.Start
                }
                [*] --> root__worker
            }
            [*] --> root
            root --> [*]
            @enduml
            """
        ).strip()

        with isolated_directory():
            root_file = os.path.abspath("root.fcstm")
            with open(root_file, "w", encoding="utf-8") as f:
                print(
                    textwrap.dedent(
                        """
                        state Root {
                            import "./worker.fcstm" as Worker;
                            [*] -> Worker;
                        }
                        """
                    ).strip(),
                    file=f,
                )
            with open("worker.fcstm", "w", encoding="utf-8") as f:
                print(
                    textwrap.dedent(
                        """
                        state WorkerRoot {
                            state Idle;
                            state Running;
                            [*] -> Idle;
                            Idle -> Running :: Start;
                        }
                        """
                    ).strip(),
                    file=f,
                )

            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "plantuml",
                    "-i",
                    root_file,
                    "-l",
                    "full",
                ],
            )

            assert result.exitcode == 0
            text_aligner.assert_equal(expect=expected, actual=result.stdout)

    def test_build_plantuml_output_with_import_supports_multi_file_model(
        self, text_aligner
    ):
        expected = textwrap.dedent(
            """
            @startuml
            hide empty description

            skinparam state {
              BackgroundColor<<pseudo>> LightGray
              BackgroundColor<<composite>> LightBlue
              BorderColor<<pseudo>> Gray
              FontStyle<<pseudo>> italic
            }

            state "Root" as root <<composite>> {
                state "Worker" as root__worker <<composite>> {
                    state "Idle" as root__worker__idle
                    state "Running" as root__worker__running
                    [*] --> root__worker__idle
                    root__worker__idle --> root__worker__running : Idle.Start
                }
                [*] --> root__worker
            }
            [*] --> root
            root --> [*]
            @enduml
            """
        ).strip()

        with isolated_directory():
            root_file = os.path.abspath("root.fcstm")
            with open(root_file, "w", encoding="utf-8") as f:
                print(
                    textwrap.dedent(
                        """
                        state Root {
                            import "./worker.fcstm" as Worker;
                            [*] -> Worker;
                        }
                        """
                    ).strip(),
                    file=f,
                )
            with open("worker.fcstm", "w", encoding="utf-8") as f:
                print(
                    textwrap.dedent(
                        """
                        state WorkerRoot {
                            state Idle;
                            state Running;
                            [*] -> Idle;
                            Idle -> Running :: Start;
                        }
                        """
                    ).strip(),
                    file=f,
                )

            plantuml_text = build_plantuml_output(root_file, detail_level="full")

        text_aligner.assert_equal(expect=expected, actual=plantuml_text)
