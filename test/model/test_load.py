import os
import pathlib
import textwrap

import pytest
from hbutils.testing import isolated_directory

from pyfcstm.model import (
    load_state_machine_from_file,
    load_state_machine_from_text,
)


def _write_text_file(path: str, content: str) -> pathlib.Path:
    file_path = pathlib.Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(textwrap.dedent(content).strip() + os.linesep, encoding="utf-8")
    return file_path


@pytest.mark.unittest
class TestImportPhase7ConvenienceLoaders:
    def test_load_state_machine_from_file_simple(self):
        with isolated_directory():
            root_file = _write_text_file(
                "root.fcstm",
                """
                state Root {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )

            state_machine = load_state_machine_from_file(root_file)

        assert state_machine.root_state.name == "Root"
        assert sorted(state_machine.root_state.substates.keys()) == ["Idle"]

    def test_load_state_machine_from_file_supports_import(self):
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
                    [*] -> Idle;
                }
                """,
            )

            state_machine = load_state_machine_from_file(root_file)

        assert state_machine.root_state.name == "Root"
        assert sorted(state_machine.root_state.substates.keys()) == ["Worker"]
        assert sorted(state_machine.root_state.substates["Worker"].substates.keys()) == [
            "Idle"
        ]

    def test_load_state_machine_from_text_uses_cwd_as_default_path(self):
        with isolated_directory():
            _write_text_file(
                "worker.fcstm",
                """
                state WorkerRoot {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )

            state_machine = load_state_machine_from_text(
                """
                state Root {
                    import "./worker.fcstm" as Worker;
                    [*] -> Worker;
                }
                """
            )

        assert state_machine.root_state.name == "Root"
        assert sorted(state_machine.root_state.substates.keys()) == ["Worker"]

    def test_load_state_machine_from_text_explicit_path_overrides_default(self):
        with isolated_directory():
            cwd_base = pathlib.Path("cwd-base")
            override_base = pathlib.Path("override-base")
            cwd_base.mkdir()
            override_base.mkdir()
            override_base_abs = override_base.resolve()

            _write_text_file(
                str(cwd_base / "worker.fcstm"),
                """
                state WorkerRoot {
                    state FromCwd;
                    [*] -> FromCwd;
                }
                """,
            )
            _write_text_file(
                str(override_base / "worker.fcstm"),
                """
                state WorkerRoot {
                    state FromOverride;
                    [*] -> FromOverride;
                }
                """,
            )

            previous_cwd = pathlib.Path.cwd()
            os.chdir(cwd_base.resolve())
            try:
                state_machine = load_state_machine_from_text(
                    """
                    state Root {
                        import "./worker.fcstm" as Worker;
                        [*] -> Worker;
                    }
                    """,
                    path=override_base_abs,
                )
            finally:
                os.chdir(previous_cwd)

        worker_state = state_machine.root_state.substates["Worker"]
        assert "FromOverride" in worker_state.substates
        assert "FromCwd" not in worker_state.substates

    def test_load_state_machine_from_text_reports_import_errors(self):
        with pytest.raises(SyntaxError) as exc_info:
            load_state_machine_from_text(
                """
                state Root {
                    import "./missing.fcstm" as Worker;
                    [*] -> Worker;
                }
                """
            )

        assert "Import source file not found" in str(exc_info.value)

    def test_complete_example_to_ast_node_str(self, text_aligner):
        with isolated_directory():
            _write_text_file(
                "worker.fcstm",
                """
                def int counter = 0;

                state WorkerRoot {
                    state Idle;
                    state Running;
                    [*] -> Idle;
                    Idle -> Running : /Start;
                }
                """,
            )

            state_machine = load_state_machine_from_text(
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
            )

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
