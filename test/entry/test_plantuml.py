import os.path
import pathlib
import textwrap

import pytest
from hbutils.system import TemporaryDirectory
from hbutils.testing import simulate_entry, isolated_directory

from pyfcstm.entry import pyfcstmcli


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
note as DefinitionNote
defines {
    def int a = 0;
    def int b = 2 | 5;
}
end note

state "LX" as lx {
    state "LX1" as lx__lx1 {
        state "LX11" as lx__lx1__lx11
        lx__lx1__lx11 : enter abstract LX11Enter;\\nenter abstract /*\\n    This is X\\n*/\\nduring abstract LX11During;\\nduring {\\n    b = 2 << 3;\\n    b = b + -1;\\n}\\nexit abstract LX11Exit;
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
    lx__lx1 : during before abstract BeforeLX1Enter;\\nduring after abstract AfterLX1Enter /*\\n    this is the comment line\\n*/\\nduring before {\\n    b = 1 + 2;\\n}\\nduring after {\\n    b = 3 - 2;\\n    b = 3 + 2 + a;\\n}
    state "LX2" as lx__lx2 {
        state "LX21" as lx__lx2__lx21 {
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
lx : enter {\\n    b = 0 + b;\\n    b = 3 + a * (2 + b);\\n}\\nexit {\\n    b = 0;\\n    b = a << 2;\\n}
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
