import os.path
import shutil
import textwrap
from tempfile import TemporaryDirectory

import pytest
from hbutils.testing import isolated_directory, simulate_entry

from pyfcstm.entry.dispatch import pyfcstmcli
from pyfcstm.dsl import parse_state_machine_dsl
from pyfcstm.model import parse_dsl_node_to_state_machine
from test.testings import get_testfile, dir_compare, walk_files


@pytest.fixture()
def input_code_file():
    with TemporaryDirectory() as td:
        code_file = os.path.join(td, "code.fcstm")
        with open(code_file, "w") as f:
            print(
                textwrap.dedent("""
    def int a = 0;
    def int b = 0x0;
    def int round_count = 0;  // define variables
    state TrafficLight {
        state InService {
            enter {
                a = 0;
                b = 0;
                round_count = 0;
            }

            enter abstract InServiceAbstractEnter /*
                Abstract Operation When Entering State 'InService'
                TODO: Should be Implemented In Generated Code Framework
            */

            // for non-leaf state, either 'before' or 'after' aspect keyword should be used for during block
            during before abstract InServiceBeforeEnterChild /*
                Abstract Operation Before Entering Child States of State 'InService'
                TODO: Should be Implemented In Generated Code Framework
            */

            during after abstract InServiceAfterEnterChild /*
                Abstract Operation After Entering Child States of State 'InService'
                TODO: Should be Implemented In Generated Code Framework
            */

            exit abstract InServiceAbstractExit /*
                Abstract Operation When Leaving State 'InService'
                TODO: Should be Implemented In Generated Code Framework
            */

            state Red {
                during {  // no aspect keywords ('before', 'after') should be used for during block of leaf state
                    a = 0x1 << 2;
                }
            }
            state Yellow;
            state Green;
            [*] -> Red :: Start effect {
                b = 0x1;
            };
            Red -> Green effect {
                b = 0x3;
            };
            Green -> Yellow effect {
                b = 0x2;
            };
            Yellow -> Red : if [a >= 10] effect {
                b = 0x1;
                round_count = round_count + 1;
            };
        }
        state Idle;

        [*] -> InService;
        InService -> Idle :: Maintain;
        Idle -> [*];
    }
    """).strip(),
                file=f,
            )

        yield code_file


@pytest.mark.unittest
class TestEntryGenerate:
    @pytest.mark.parametrize(
        ["template_name", "result_name"],
        [
            ("template_1", "template_1_result"),
            ("template_1_with_static_file", "template_1_with_static_file_result"),
            ("template_1_with_ignore", "template_1_with_ignore_result"),
        ],
    )
    def test_actual_render(self, template_name, result_name, input_code_file):
        template_dir = os.path.abspath(get_testfile(template_name))
        expected_result_dir = os.path.abspath(get_testfile(result_name))

        with TemporaryDirectory() as td:
            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "generate",
                    "-i",
                    input_code_file,
                    "-t",
                    template_dir,
                    "-o",
                    td,
                ],
            )
            assert result.exitcode == 0
            dir_compare(expected_result_dir, td)

    @pytest.mark.parametrize(
        ["template_name", "result_name"],
        [
            ("template_1", "template_1_result"),
            ("template_1_with_static_file", "template_1_with_static_file_result"),
            ("template_1_with_ignore", "template_1_with_ignore_result"),
        ],
    )
    def test_actual_render_with_clear(
        self, template_name, result_name, input_code_file
    ):
        template_dir = os.path.abspath(get_testfile(template_name))
        expected_result_dir = os.path.abspath(get_testfile(result_name))

        with TemporaryDirectory() as td:
            for file in walk_files(get_testfile(".")):
                dst_file = os.path.join(td, file)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copyfile(get_testfile(file), dst_file)

            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "generate",
                    "-i",
                    input_code_file,
                    "-t",
                    template_dir,
                    "-o",
                    td,
                    "--clear",
                ],
            )
            assert result.exitcode == 0
            dir_compare(expected_result_dir, td)

    def test_generate_with_builtin_template(self, input_code_file):
        with TemporaryDirectory() as td:
            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "generate",
                    "-i",
                    input_code_file,
                    "--template",
                    "python",
                    "-o",
                    td,
                ],
            )
            assert result.exitcode == 0
            assert os.path.isfile(os.path.join(td, "machine.py"))
            assert os.path.isfile(os.path.join(td, "README.md"))
            assert os.path.isfile(os.path.join(td, "README_zh.md"))
            assert not os.path.exists(os.path.join(td, "__init__.py"))

            with open(os.path.join(td, "machine.py"), "r") as f:
                content = f.read()
            assert "class TrafficLightMachine" in content
            assert "Original DSL Source" in content
            assert "Abstract Hook Map" in content

            with open(os.path.join(td, "README.md"), "r", encoding="utf-8") as f:
                readme = f.read()
            with open(os.path.join(td, "README_zh.md"), "r", encoding="utf-8") as f:
                readme_zh = f.read()
            assert "# TrafficLightMachine" in readme
            assert "Overridable Abstract Hooks" in readme
            assert "可覆写的 Abstract Hook 清单" in readme_zh

    def test_generate_with_invalid_builtin_template_should_fail(self, input_code_file):
        with TemporaryDirectory() as td:
            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "generate",
                    "-i",
                    input_code_file,
                    "--template",
                    "not_exists",
                    "-o",
                    td,
                ],
            )
            assert result.exitcode != 0
            message = result.stderr or result.stdout
            assert "Invalid value for '--template'" in message
            assert "python" in message

    def test_generate_with_template_and_template_dir_should_fail(self, input_code_file):
        template_dir = os.path.abspath(get_testfile("template_1"))
        with TemporaryDirectory() as td:
            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "generate",
                    "-i",
                    input_code_file,
                    "--template",
                    "python",
                    "-t",
                    template_dir,
                    "-o",
                    td,
                ],
            )
            assert result.exitcode != 0
            assert "Exactly one of --template-dir/-t or --template must be provided." in (
                result.stderr or result.stdout
            )

    def test_generate_without_template_and_template_dir_should_fail(self, input_code_file):
        with TemporaryDirectory() as td:
            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "generate",
                    "-i",
                    input_code_file,
                    "-o",
                    td,
                ],
            )
            assert result.exitcode != 0
            assert "Exactly one of --template-dir/-t or --template must be provided." in (
                result.stderr or result.stdout
            )

    def test_generate_with_import_keeps_cli_contract_and_renders_builtin_template(self):
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
                            [*] -> Idle;
                        }
                        """
                    ).strip(),
                    file=f,
                )

            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "generate",
                    "-i",
                    root_file,
                    "--template",
                    "python",
                    "-o",
                    "out",
                ],
            )

            assert result.exitcode == 0
            assert os.path.isfile("out/machine.py")
            assert os.path.isfile("out/README.md")
            assert os.path.isfile("out/README_zh.md")

    def test_generate_import_phase6_to_ast_node_str(self, text_aligner):
        with isolated_directory():
            with open("root.fcstm", "w", encoding="utf-8") as f:
                print(
                    textwrap.dedent(
                        """
                        state Root {
                            state Bus;
                            import "./worker.fcstm" as Worker {
                                event /Start -> /Bus.Start named "Shared Start";
                                def counter -> host_counter;
                            }
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
                        def int counter = 0;

                        state WorkerRoot {
                            state Idle;
                            state Running;
                            [*] -> Idle;
                            Idle -> Running : /Start;
                        }
                        """
                    ).strip(),
                    file=f,
                )

            root_file = os.path.abspath("root.fcstm")
            ast_node = parse_state_machine_dsl(open(root_file, "r", encoding="utf-8").read())
            state_machine = parse_dsl_node_to_state_machine(ast_node, path=root_file)

        text_aligner.assert_equal(
            expect=textwrap.dedent(
                """
                def int host_counter = 0;
                state Root {
                    state Worker {
                        state Idle;
                        state Running;
                        [*] -> Idle;
                        Idle -> Running : /Bus.Start;
                    }
                    state Bus {
                        event Start named 'Shared Start';
                    }
                    [*] -> Worker;
                }
                """
            ).strip(),
            actual=str(state_machine.to_ast_node()),
        )

    def test_generate_with_directory_entry_import_renders_builtin_template(self):
        with isolated_directory():
            root_file = os.path.abspath("root.fcstm")
            os.makedirs("modules/subsystems", exist_ok=True)

            with open(root_file, "w", encoding="utf-8") as f:
                print(
                    textwrap.dedent(
                        """
                        state Root {
                            import "./modules/main.fcstm" as Line;
                            [*] -> Line;
                        }
                        """
                    ).strip(),
                    file=f,
                )

            with open("modules/main.fcstm", "w", encoding="utf-8") as f:
                print(
                    textwrap.dedent(
                        """
                        state LineRoot {
                            import "./subsystems/worker.fcstm" as Worker;
                            [*] -> Worker;
                        }
                        """
                    ).strip(),
                    file=f,
                )

            with open("modules/subsystems/worker.fcstm", "w", encoding="utf-8") as f:
                print(
                    textwrap.dedent(
                        """
                        state WorkerRoot {
                            state Idle;
                            [*] -> Idle;
                        }
                        """
                    ).strip(),
                    file=f,
                )

            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "generate",
                    "-i",
                    root_file,
                    "--template",
                    "python",
                    "-o",
                    "out",
                ],
            )

            assert result.exitcode == 0
            assert os.path.isfile("out/machine.py")
            with open("out/machine.py", "r", encoding="utf-8") as f:
                content = f.read()
            assert "class RootMachine" in content

    def test_generate_with_missing_import_fails(self):
        with isolated_directory():
            root_file = os.path.abspath("root.fcstm")
            with open(root_file, "w", encoding="utf-8") as f:
                print(
                    textwrap.dedent(
                        """
                        state Root {
                            import "./missing.fcstm" as Worker;
                            [*] -> Worker;
                        }
                        """
                    ).strip(),
                    file=f,
                )

            result = simulate_entry(
                pyfcstmcli,
                [
                    "pyfcstm",
                    "generate",
                    "-i",
                    root_file,
                    "--template",
                    "python",
                    "-o",
                    "out",
                ],
            )

            assert result.exitcode != 0
