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
    file_path.write_text(
        textwrap.dedent(content).strip() + os.linesep, encoding="utf-8"
    )
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
        assert sorted(
            state_machine.root_state.substates["Worker"].substates.keys()
        ) == ["Idle"]

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


@pytest.mark.unittest
def test_a_loaded_model_carries_both_source_mechanisms(text_aligner) -> None:
    """Two readers ask for the source in two shapes, and both must get it.

    BMC provenance slices spans out of ``_source_documents``, a path-keyed map,
    because an imported model has several files and a constraint can come from
    any of them. The diagram viewer and inspect read the ``source_text`` and
    ``source_path`` scalars for the one file the caller named.

    The two grew up in separate umbrellas and met in a merge. Keeping only one
    would have looked fine in whichever suite covered it, so this asserts both
    are populated from the same load.
    """
    with isolated_directory():
        source = textwrap.dedent(
            """
            def int x = 0;
            state Root {
                state A;
                [*] -> A;
            }
            """
        ).strip()
        _write_text_file("machine.fcstm", source)

        machine = load_state_machine_from_file("machine.fcstm")

        # Compared through the aligner rather than with ``==``: the helper ends the
        # file with ``os.linesep``, so a byte comparison would pass on Linux and
        # fail on Windows for a reason that has nothing to do with what is being
        # tested here.
        text_aligner.assert_equal(source, machine.source_text)
        assert machine.source_path == "machine.fcstm"
        documents = machine._source_documents
        text_aligner.assert_equal(source, documents[os.path.abspath("machine.fcstm")])


@pytest.mark.unittest
def test_text_loading_files_the_source_under_the_memory_key(text_aligner) -> None:
    """Loading from text still puts the source somewhere a reader can find it.

    There is no file to key the document map on, so the key is ``<memory>``.
    ``pyfcstm.diagram.api`` relies on exactly that: it distinguishes a model
    loaded from text -- whose ``source_path`` is the working directory used for
    import resolution -- from one loaded from a file, by asking whether the map
    holds a ``<memory>`` entry. Without it the viewer would show the working
    directory's basename as if it were a source file.

    The entry does not come from the loader writing it directly; the loader sets
    the scalar attributes on the AST and the model builder collects them into the
    map. Asserting the observable end of that chain is what keeps a change to
    either half from quietly breaking the other.
    """
    source = "def int x = 0;\nstate Root {\n    state A;\n    [*] -> A;\n}"

    machine = load_state_machine_from_text(source)

    text_aligner.assert_equal(source, machine.source_text)
    text_aligner.assert_equal(source, machine._source_documents["<memory>"])


@pytest.mark.unittest
class TestConvenienceLoadersCollectMode:
    """The convenience loaders can hand back model-build diagnostics.

    Strict mode stays the default so existing callers are unaffected. Collect
    mode mirrors :func:`pyfcstm.model.parse_dsl_node_to_state_machine`: it
    returns the partially-built model together with every diagnostic instead of
    raising on the first error.
    """

    _MULTI_ERROR = """
        state Root {
            state A;
            state A;
            NoSuch -> A;
            state Outer { state Inner; }
            [*] -> A;
        }
    """

    def test_from_file_collect_returns_all_diagnostics(self):
        with isolated_directory():
            _write_text_file("multi.fcstm", self._MULTI_ERROR)

            machine, diagnostics = load_state_machine_from_file(
                "multi.fcstm", collect=True
            )

        assert machine is not None
        assert [d.code for d in diagnostics] == [
            "E_DUPLICATE_STATE",
            "E_INITIAL_TRANSITION_INVALID",
            "E_DANGLING_TRANSITION",
        ]

    def test_from_file_collect_keeps_source_metadata(self):
        with isolated_directory():
            _write_text_file("multi.fcstm", self._MULTI_ERROR)

            machine, _ = load_state_machine_from_file("multi.fcstm", collect=True)

            assert machine.source_path == "multi.fcstm"
        assert "NoSuch -> A;" in machine.source_text

    def test_from_text_collect_returns_all_diagnostics(self):
        machine, diagnostics = load_state_machine_from_text(
            textwrap.dedent(self._MULTI_ERROR).strip(), collect=True
        )

        assert machine is not None
        assert {d.code for d in diagnostics} == {
            "E_DUPLICATE_STATE",
            "E_INITIAL_TRANSITION_INVALID",
            "E_DANGLING_TRANSITION",
        }

    def test_strict_mode_stays_the_default(self):
        from pyfcstm.utils.validate import ModelValidationError

        with pytest.raises(ModelValidationError):
            load_state_machine_from_text(
                textwrap.dedent(self._MULTI_ERROR).strip()
            )


@pytest.mark.unittest
class TestCollectModeKeepsAssemblingAfterAnError:
    """Emitting a diagnostic must not leave the caller mid-computation.

    Strict mode raises inside the sink, so code after an emit call is never
    reached. Collect mode keeps going, which turns any such follow-on statement
    into a crash that only the collecting path can hit.
    """

    def test_invalid_variable_mapping_template_does_not_raise_value_error(self):
        with isolated_directory():
            _write_text_file(
                "root.fcstm",
                """
                state Host {
                    import "./worker.fcstm" as Worker {
                        def sensor_* -> left_${x};
                    }
                    [*] -> Worker;
                }
                """,
            )
            _write_text_file(
                "worker.fcstm",
                """
                def int sensor_input = 0;
                state Worker {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )

            machine, diagnostics = load_state_machine_from_file(
                "root.fcstm", collect=True
            )

        assert "E_IMPORT_MAPPING_INVALID" in {d.code for d in diagnostics}

    def test_rejected_template_stays_traceable_without_cascading(self):
        """The rejected template becomes the variable name on purpose.

        It is not a legal identifier, but it matches the diagnostic's ``detail``
        so a reader can connect the two. Dropping the variable instead would make
        every later reference to it report a second, misleading error.
        """
        with isolated_directory():
            _write_text_file(
                "root.fcstm",
                """
                state Host {
                    import "./worker.fcstm" as Worker {
                        def sensor_* -> left_${x};
                    }
                    [*] -> Worker;
                }
                """,
            )
            _write_text_file(
                "worker.fcstm",
                """
                def int sensor_input = 0;
                state Worker {
                    state Idle;
                    [*] -> Idle;
                }
                """,
            )

            machine, diagnostics = load_state_machine_from_file(
                "root.fcstm", collect=True
            )

        mapping_errors = [
            d for d in diagnostics if d.code == "E_IMPORT_MAPPING_INVALID"
        ]
        assert len(mapping_errors) == 1
        assert list(machine.defines) == [mapping_errors[0].refs["detail"]]
        assert "E_UNDEFINED_VAR" not in {d.code for d in diagnostics}
