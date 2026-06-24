import os.path
import pathlib
import shutil
import textwrap
from unittest import mock

import jinja2
import pytest
from hbutils.system import TemporaryDirectory

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.render.render import (
    _ensure_output_parent_dir,
    _normalize_template_relpath,
    _output_relpath_to_native_path,
)
from ..testings import get_testfile, dir_compare, walk_files


@pytest.fixture()
def sample_model():
    ast_node = parse_with_grammar_entry(
        """
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
    """,
        entry_name="state_machine_dsl",
    )
    model = parse_dsl_node_to_state_machine(ast_node)
    return model


@pytest.mark.unittest
class TestRenderRender:
    @pytest.mark.parametrize(
        ["template_name", "result_name"],
        [
            ("template_1", "template_1_result"),
            ("template_1_with_static_file", "template_1_with_static_file_result"),
            ("template_1_with_ignore", "template_1_with_ignore_result"),
        ],
    )
    def test_actual_render(self, template_name, result_name, sample_model):
        template_dir = get_testfile(template_name)
        expected_result_dir = get_testfile(result_name)

        renderer = StateMachineCodeRenderer(template_dir)
        with TemporaryDirectory() as td:
            renderer.render(
                model=sample_model,
                output_dir=td,
            )
            dir_compare(expected_result_dir, td)

    @pytest.mark.parametrize(
        ["template_name", "result_name"],
        [
            ("template_1", "template_1_result"),
            ("template_1_with_static_file", "template_1_with_static_file_result"),
            ("template_1_with_ignore", "template_1_with_ignore_result"),
        ],
    )
    def test_actual_render_with_clear(self, template_name, result_name, sample_model):
        template_dir = get_testfile(template_name)
        expected_result_dir = get_testfile(result_name)

        renderer = StateMachineCodeRenderer(template_dir)
        with TemporaryDirectory() as td:
            for file in walk_files(get_testfile(".")):
                dst_file = os.path.join(td, file)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copyfile(get_testfile(file), dst_file)
            renderer.render(
                model=sample_model,
                output_dir=td,
                clear_previous_directory=True,
            )
            dir_compare(expected_result_dir, td)

    def test_rendered_template_files_use_lf_newlines(self, sample_model):
        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write("{}\n")
            with open(
                os.path.join(template_dir, "multiline.txt.j2"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as f:
                f.write("line1\n{{ model.root_state.name }}\nline3")

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=sample_model, output_dir=output_dir)
                with open(os.path.join(output_dir, "multiline.txt"), "rb") as f:
                    data = f.read()

        assert b"\r\n" not in data
        assert data == b"line1\nTrafficLight\nline3"

    def test_renderer_handles_nested_outputs_and_ignores(self, sample_model):
        with TemporaryDirectory() as template_dir:
            nested_template_dir = os.path.join(template_dir, "nested")
            nested_static_dir = os.path.join(template_dir, "assets", "nested")
            ignored_dir = os.path.join(template_dir, "assets", "ignored")
            os.makedirs(nested_template_dir, exist_ok=True)
            os.makedirs(nested_static_dir, exist_ok=True)
            os.makedirs(ignored_dir, exist_ok=True)

            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write("ignores:\n  - 'assets/ignored/**'\n")
            with open(os.path.join(nested_template_dir, "rendered.txt.j2"), "w") as f:
                f.write("state={{ model.root_state.name }}")
            with open(os.path.join(nested_static_dir, "static.txt"), "w") as f:
                f.write("static asset")
            with open(os.path.join(ignored_dir, "skip.txt"), "w") as f:
                f.write("ignored asset")

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=sample_model, output_dir=output_dir)

                with open(os.path.join(output_dir, "nested", "rendered.txt"), "r") as f:
                    rendered = f.read()
                with open(
                    os.path.join(output_dir, "assets", "nested", "static.txt"), "r"
                ) as f:
                    static = f.read()

                assert rendered == "state=TrafficLight"
                assert static == "static asset"
                assert not os.path.exists(
                    os.path.join(output_dir, "assets", "ignored", "skip.txt")
                )

    def test_renderer_recreates_nested_output_dirs_after_clear(self, sample_model):
        with TemporaryDirectory() as template_dir:
            nested_template_dir = os.path.join(template_dir, "nested")
            nested_static_dir = os.path.join(template_dir, "assets", "nested")
            os.makedirs(nested_template_dir, exist_ok=True)
            os.makedirs(nested_static_dir, exist_ok=True)

            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write("{}\n")
            with open(os.path.join(nested_template_dir, "rendered.txt.j2"), "w") as f:
                f.write("state={{ model.root_state.name }}")
            with open(os.path.join(nested_static_dir, "static.txt"), "w") as f:
                f.write("static asset")

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=sample_model, output_dir=output_dir)
                stale_file = os.path.join(output_dir, "nested", "stale.txt")
                with open(stale_file, "w") as f:
                    f.write("stale")

                renderer.render(
                    model=sample_model,
                    output_dir=output_dir,
                    clear_previous_directory=True,
                )

                with open(os.path.join(output_dir, "nested", "rendered.txt"), "r") as f:
                    rendered = f.read()
                with open(
                    os.path.join(output_dir, "assets", "nested", "static.txt"), "r"
                ) as f:
                    static = f.read()

                assert rendered == "state=TrafficLight"
                assert static == "static asset"
                assert not os.path.exists(stale_file)

    @pytest.mark.skipif(
        not hasattr(os, "symlink"),
        reason="symlink support is not available on this platform",
    )
    def test_renderer_clear_previous_directory_unlinks_directory_symlinks(
        self,
        sample_model,
    ):
        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write("{}\n")
            with open(os.path.join(template_dir, "rendered.txt.j2"), "w") as f:
                f.write("state={{ model.root_state.name }}")

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                with TemporaryDirectory() as external_dir:
                    external_file = os.path.join(external_dir, "keep.txt")
                    with open(external_file, "w") as f:
                        f.write("external")

                    stale_link = os.path.join(output_dir, "stale_link")
                    try:
                        os.symlink(external_dir, stale_link)
                    except OSError as err:
                        # OSError: some Windows runners expose os.symlink but
                        # deny creating directory symlinks without privilege.
                        pytest.skip(
                            "directory symlink creation is unavailable: %s" % err
                        )

                    renderer.render(
                        model=sample_model,
                        output_dir=output_dir,
                        clear_previous_directory=True,
                    )

                    assert os.path.exists(external_file)
                    assert not os.path.lexists(stale_link)
                    with open(os.path.join(output_dir, "rendered.txt"), "r") as f:
                        rendered = f.read()

                assert rendered == "state=TrafficLight"

    def test_renderer_normalizes_template_relative_paths_for_ignores(
        self, sample_model
    ):
        with TemporaryDirectory() as template_dir:
            nested_template_dir = os.path.join(template_dir, "nested")
            nested_static_dir = os.path.join(template_dir, "assets", "nested")
            ignored_dir = os.path.join(template_dir, "assets", "ignored")
            os.makedirs(nested_template_dir, exist_ok=True)
            os.makedirs(nested_static_dir, exist_ok=True)
            os.makedirs(ignored_dir, exist_ok=True)

            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write("ignores:\n  - 'assets/ignored/**'\n")
            with open(os.path.join(nested_template_dir, "rendered.txt.j2"), "w") as f:
                f.write("state={{ model.root_state.name }}")
            with open(os.path.join(nested_static_dir, "static.txt"), "w") as f:
                f.write("static asset")
            with open(os.path.join(ignored_dir, "skip.txt"), "w") as f:
                f.write("ignored asset")

            original_relpath = os.path.relpath
            original_sep = os.sep

            def _windows_relpath(path, start=None):
                return original_relpath(path, start).replace(original_sep, "\\")

            with mock.patch("pyfcstm.render.render.os.sep", "\\"):
                with mock.patch(
                    "pyfcstm.render.render.os.path.relpath",
                    side_effect=_windows_relpath,
                ):
                    renderer = StateMachineCodeRenderer(template_dir)

            assert "nested/rendered.txt" in renderer._file_mappings
            assert "assets/nested/static.txt" in renderer._file_mappings
            assert "assets/ignored/skip.txt" not in renderer._file_mappings
            assert all("\\" not in rel_file for rel_file in renderer._file_mappings)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=sample_model, output_dir=output_dir)

                assert os.path.exists(
                    os.path.join(output_dir, "nested", "rendered.txt")
                )
                assert os.path.exists(
                    os.path.join(output_dir, "assets", "nested", "static.txt")
                )
                assert not os.path.exists(
                    os.path.join(output_dir, "assets", "ignored", "skip.txt")
                )

    def test_output_path_helpers_handle_nested_and_separator_edges(self):
        assert (
            _normalize_template_relpath("assets/nested/static.txt")
            == "assets/nested/static.txt"
        )
        with mock.patch("pyfcstm.render.render.os.sep", "/"):
            assert (
                _normalize_template_relpath("assets\\nested\\static.txt")
                == "assets\\nested\\static.txt"
            )
        with mock.patch("pyfcstm.render.render.os.sep", "\\"):
            assert (
                _normalize_template_relpath("assets\\nested\\static.txt")
                == "assets/nested/static.txt"
            )

        with TemporaryDirectory() as output_dir:
            output_file = os.path.join(output_dir, "nested", "rendered.txt")

            _ensure_output_parent_dir(output_file)
            assert os.path.isdir(os.path.dirname(output_file))
            assert not os.path.exists(output_file)

            _ensure_output_parent_dir(output_file)
            _ensure_output_parent_dir("bare-file.txt")

        assert _output_relpath_to_native_path(
            "assets/nested/static.txt"
        ) == os.path.join(
            "assets",
            "nested",
            "static.txt",
        )
        with mock.patch("pyfcstm.render.render.os.sep", "/"):
            assert (
                _output_relpath_to_native_path("assets\\nested/static.txt")
                == "assets\\nested/static.txt"
            )
        with mock.patch("pyfcstm.render.render.os.sep", "\\"):
            assert (
                _output_relpath_to_native_path("assets/nested/static.txt")
                == "assets\\nested\\static.txt"
            )

    def test_renderer_has_no_template_file_name_postprocessing(self):
        render_source = (
            pathlib.Path(__file__).parents[2] / "pyfcstm" / "render" / "render.py"
        )

        source = render_source.read_text(encoding="utf-8")

        # This is an architectural boundary guard: the generic renderer must
        # not restore Python-template-only post-processing keyed by a concrete
        # built-in template file name. Behavioral tests cover rendering; this
        # source-level check keeps the boundary violation from reappearing.
        assert "machine.py.j2" not in source
        assert "os.path.basename(template_file)" not in source
        assert "re.sub" not in source
        assert "import re" not in source

    def test_renderer_expr_render_supports_language_aliases(self, sample_model):
        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write("{}\n")
            with open(os.path.join(template_dir, "expr.txt.j2"), "w") as f:
                f.write("{{ 2.0 | expr_render(style='javascript') }}")

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=sample_model, output_dir=output_dir)
                with open(os.path.join(output_dir, "expr.txt"), "r") as f:
                    rendered = f.read()

        assert rendered == "2.0"

    def test_renderer_expr_render_inherits_current_custom_style_recursively(
        self, sample_model
    ):
        ast_node = parse_with_grammar_entry(
            """
        def int counter = 0;
        state Root {
            state A {
                during {
                    counter = counter + 1;
                }
            }
            [*] -> A : if [counter >= 1];
        }
        """,
            entry_name="state_machine_dsl",
        )
        model = parse_dsl_node_to_state_machine(ast_node)

        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write(
                    "expr_styles:\n"
                    "  python_vars:\n"
                    "    base_lang: python\n"
                    '    Name: "vars_[{{ node.name | tojson }}]"\n'
                )
            with open(os.path.join(template_dir, "expr.txt.j2"), "w") as f:
                f.write(
                    "{{ model.root_state.init_transitions[0].guard.to_ast_node() "
                    "| expr_render(style='python_vars') }}"
                )

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=model, output_dir=output_dir)
                with open(os.path.join(output_dir, "expr.txt"), "r") as f:
                    rendered = f.read()

        assert rendered == 'vars_["counter"] >= 1'

    def test_renderer_expr_render_seeds_python_condition_helpers(self):
        ast_node = parse_with_grammar_entry(
            """
        def int a = 0;
        def int b = 0;
        def int c = 0;
        state Root {
            state A;
            [*] -> A : if [a > 0 iff b > 0 == c > 0];
        }
        """,
            entry_name="state_machine_dsl",
        )
        model = parse_dsl_node_to_state_machine(ast_node)

        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write(
                    "expr_styles:\n"
                    "  python_names:\n"
                    "    base_lang: python\n"
                    '    Name: "{{ node.name }}"\n'
                )
            with open(os.path.join(template_dir, "expr.txt.j2"), "w") as f:
                f.write(
                    "{{ model.root_state.init_transitions[0].guard.to_ast_node() "
                    "| expr_render(style='python_names') }}"
                )

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=model, output_dir=output_dir)
                with open(os.path.join(output_dir, "expr.txt"), "r") as f:
                    rendered = f.read()

        assert eval(rendered, {}, {"a": 1, "b": -1, "c": 0}) is True

    def test_renderer_rejects_unknown_config_keys_with_path_and_allowed_keys(self):
        with TemporaryDirectory() as template_dir:
            config_file = os.path.join(template_dir, "config.yaml")
            with open(config_file, "w") as f:
                f.write("globals_typo: {}\n")

            with pytest.raises(ValueError) as exc_info:
                StateMachineCodeRenderer(template_dir)

        message = str(exc_info.value)
        assert config_file in message
        assert "globals_typo" in message
        for key in (
            "expr_styles",
            "stmt_styles",
            "globals",
            "filters",
            "tests",
            "ignores",
        ):
            assert key in message

    @pytest.mark.parametrize(
        "config_text, section, expected_text",
        [
            ("expr_styles: []\n", "expr_styles", "mapping"),
            ("stmt_styles: []\n", "stmt_styles", "mapping"),
            ("globals: []\n", "globals", "mapping"),
            ("filters: []\n", "filters", "mapping"),
            ("tests: []\n", "tests", "mapping"),
            ("ignores: assets/**\n", "ignores", "list of string patterns"),
            ("ignores:\n  - 123\n", "ignores[0]", "string pattern"),
        ],
    )
    def test_renderer_rejects_invalid_top_level_config_section_types(
        self,
        config_text,
        section,
        expected_text,
    ):
        with TemporaryDirectory() as template_dir:
            config_file = os.path.join(template_dir, "config.yaml")
            with open(config_file, "w") as f:
                f.write(config_text)

            with pytest.raises(ValueError) as exc_info:
                StateMachineCodeRenderer(template_dir)

        message = str(exc_info.value)
        assert config_file in message
        assert section in message
        assert expected_text in message

    @pytest.mark.parametrize(
        "config_text, section, style_name",
        [
            ("expr_styles:\n  missing_base: {}\n", "expr_styles", "missing_base"),
            ("stmt_styles:\n  missing_base: {}\n", "stmt_styles", "missing_base"),
        ],
    )
    def test_renderer_rejects_style_without_base_lang(
        self,
        config_text,
        section,
        style_name,
    ):
        with TemporaryDirectory() as template_dir:
            config_file = os.path.join(template_dir, "config.yaml")
            with open(config_file, "w") as f:
                f.write(config_text)

            with pytest.raises(ValueError) as exc_info:
                StateMachineCodeRenderer(template_dir)

        message = str(exc_info.value)
        assert config_file in message
        assert section in message
        assert style_name in message
        assert "base_lang" in message

    @pytest.mark.parametrize(
        "config_text, section, style_name",
        [
            ("expr_styles:\n  invalid_style: python\n", "expr_styles", "invalid_style"),
            ("stmt_styles:\n  invalid_style: python\n", "stmt_styles", "invalid_style"),
        ],
    )
    def test_renderer_rejects_non_mapping_style_config(
        self,
        config_text,
        section,
        style_name,
    ):
        with TemporaryDirectory() as template_dir:
            config_file = os.path.join(template_dir, "config.yaml")
            with open(config_file, "w") as f:
                f.write(config_text)

            with pytest.raises(ValueError) as exc_info:
                StateMachineCodeRenderer(template_dir)

        message = str(exc_info.value)
        assert config_file in message
        assert section in message
        assert style_name in message
        assert "mapping" in message

    @pytest.mark.parametrize("config_text", ["", "# empty\n"])
    def test_renderer_accepts_empty_config_files(self, config_text, sample_model):
        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write(config_text)
            with open(os.path.join(template_dir, "state.txt.j2"), "w") as f:
                f.write("{{ model.root_state.name }}")

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=sample_model, output_dir=output_dir)
                with open(os.path.join(output_dir, "state.txt"), "r") as f:
                    rendered = f.read()

        assert rendered == "TrafficLight"

    @pytest.mark.parametrize("config_text", ["- globals\n", "[]\n", "false\n"])
    def test_renderer_rejects_non_mapping_config_root_with_path(self, config_text):
        with TemporaryDirectory() as template_dir:
            config_file = os.path.join(template_dir, "config.yaml")
            with open(config_file, "w") as f:
                f.write(config_text)

            with pytest.raises(ValueError) as exc_info:
                StateMachineCodeRenderer(template_dir)

        message = str(exc_info.value)
        assert config_file in message
        assert "mapping" in message

    def test_renderer_does_not_consume_config_item_dicts(self, sample_model):
        template_config = {
            "type": "template",
            "params": ["value"],
            "template": "{{ value }}!",
        }
        value_config = {
            "type": "value",
            "value": "OK",
        }

        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write(
                    textwrap.dedent(
                        """
                        globals:
                          shout:
                            type: template
                            params:
                              - value
                            template: "{{ value }}!"
                          literal:
                            type: value
                            value: OK
                        filters:
                          echo:
                            type: template
                            params:
                              - value
                            template: "{{ value }}"
                        tests:
                          always_true:
                            type: import
                            from: builtins.bool
                        """
                    ).lstrip()
                )
            with open(os.path.join(template_dir, "result.txt.j2"), "w") as f:
                f.write(
                    "{{ shout(literal) }} {{ 'x' | echo }} {{ 'non-empty' is always_true }}"
                )

            with mock.patch("pyfcstm.render.render.yaml.safe_load") as safe_load:
                loaded_config = {
                    "globals": {
                        "shout": template_config,
                        "literal": value_config,
                    },
                    "filters": {
                        "echo": {
                            "type": "template",
                            "params": ["value"],
                            "template": "{{ value }}",
                        },
                    },
                    "tests": {
                        "always_true": {
                            "type": "import",
                            "from": "builtins.bool",
                        },
                    },
                }
                safe_load.return_value = loaded_config
                renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=sample_model, output_dir=output_dir)
                with open(os.path.join(output_dir, "result.txt"), "r") as f:
                    rendered = f.read()

        assert rendered == "OK! x True"
        assert sorted(loaded_config) == ["filters", "globals", "tests"]
        assert template_config == {
            "type": "template",
            "params": ["value"],
            "template": "{{ value }}!",
        }
        assert value_config == {
            "type": "value",
            "value": "OK",
        }

    def test_statement_default_context_restores_after_template_error(
        self, sample_model
    ):
        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write("{}\n")
            template_file = os.path.join(template_dir, "broken.txt.j2")
            with open(template_file, "w") as f:
                f.write("{{ missing_call() }}")

            renderer = StateMachineCodeRenderer(template_dir)
            renderer.env.globals["_stmt_default_state_vars"] = ("previous",)
            renderer.env.globals["_stmt_default_var_types"] = {"previous": "int"}

            with TemporaryDirectory() as output_dir:
                with pytest.raises(jinja2.exceptions.UndefinedError):
                    renderer.render_one_file(
                        model=sample_model,
                        output_file=os.path.join(output_dir, "broken.txt"),
                        template_file=template_file,
                    )

        assert renderer.env.globals["_stmt_default_state_vars"] == ("previous",)
        assert renderer.env.globals["_stmt_default_var_types"] == {"previous": "int"}

    def test_statement_default_context_restores_explicit_none_values(
        self, sample_model
    ):
        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write("{}\n")
            with open(os.path.join(template_dir, "state.txt.j2"), "w") as f:
                f.write("{{ model.root_state.name }}")

            renderer = StateMachineCodeRenderer(template_dir)
            renderer.env.globals["_stmt_default_state_vars"] = None
            renderer.env.globals["_stmt_default_var_types"] = None

            with TemporaryDirectory() as output_dir:
                renderer.render(model=sample_model, output_dir=output_dir)

        assert "_stmt_default_state_vars" in renderer.env.globals
        assert "_stmt_default_var_types" in renderer.env.globals
        assert renderer.env.globals["_stmt_default_state_vars"] is None
        assert renderer.env.globals["_stmt_default_var_types"] is None

    def test_statement_default_context_does_not_leak_between_models(self):
        ast_node_a = parse_with_grammar_entry(
            """
        def int counter = 0;
        state RootA {
            state A {
                enter { counter = counter + 1; }
            }
            [*] -> A;
        }
        """,
            entry_name="state_machine_dsl",
        )
        ast_node_b = parse_with_grammar_entry(
            """
        def int other = 0;
        state RootB {
            state A {
                enter { tmp = other + 1; other = tmp + 2; }
            }
            [*] -> A;
        }
        """,
            entry_name="state_machine_dsl",
        )
        model_a = parse_dsl_node_to_state_machine(ast_node_a)
        model_b = parse_dsl_node_to_state_machine(ast_node_b)

        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write("{}\n")
            with open(os.path.join(template_dir, "stmt.txt.j2"), "w") as f:
                f.write(
                    "{{ model.root_state.substates['A'].on_enters[0].operations | stmts_render(style='c') }}"
                )

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(
                    model=model_a, output_dir=output_dir, clear_previous_directory=True
                )
                with open(os.path.join(output_dir, "stmt.txt"), "r") as f:
                    rendered_a = f.read()
                renderer.render(
                    model=model_b, output_dir=output_dir, clear_previous_directory=True
                )
                with open(os.path.join(output_dir, "stmt.txt"), "r") as f:
                    rendered_b = f.read()

        assert "scope->counter = scope->counter + 1;" == rendered_a
        assert (
            rendered_b == "int tmp;\ntmp = scope->other + 1;\nscope->other = tmp + 2;"
        )

    def test_explicit_statement_context_overrides_renderer_default(self):
        ast_node = parse_with_grammar_entry(
            """
        def int counter = 0;
        state Root {
            state A {
                enter { counter = counter + 1; }
            }
            [*] -> A;
        }
        """,
            entry_name="state_machine_dsl",
        )
        model = parse_dsl_node_to_state_machine(ast_node)

        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write("{}\n")
            with open(os.path.join(template_dir, "stmt.txt.j2"), "w") as f:
                f.write(
                    "{{ stmts_render(model.root_state.substates['A'].on_enters[0].operations, "
                    "style='c', state_vars=(), var_types={}) }}"
                )

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=model, output_dir=output_dir)
                with open(os.path.join(output_dir, "stmt.txt"), "r") as f:
                    rendered = f.read()

        assert rendered == "int counter;\ncounter = counter + 1;"
        assert "scope->counter" not in rendered

    def test_renderer_does_not_register_c_runtime_helpers_by_default(self):
        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write("{}\n")

            renderer = StateMachineCodeRenderer(template_dir)

        assert "render_c_action_body" not in renderer.env.globals
        assert "render_c_condition_body" not in renderer.env.globals
        assert "render_c_reset_vars_body" not in renderer.env.globals

    def test_renderer_injects_default_state_vars_and_var_types_for_default_cpp_stmt_rendering(
        self,
    ):
        ast_node = parse_with_grammar_entry(
            """
        def int counter = 0;
        state Root {
            state A {
                enter {
                    tmp = counter + 1;
                    counter = tmp + 2;
                }
            }
            [*] -> A;
        }
        """,
            entry_name="state_machine_dsl",
        )
        model = parse_dsl_node_to_state_machine(ast_node)

        with TemporaryDirectory() as template_dir:
            with open(os.path.join(template_dir, "config.yaml"), "w") as f:
                f.write("{}\n")
            with open(os.path.join(template_dir, "stmt.txt.j2"), "w") as f:
                f.write(
                    "Enter operations:\n"
                    "{{ model.root_state.substates['A'].on_enters[0].operations "
                    "| stmts_render(style='c++') }}"
                )

            renderer = StateMachineCodeRenderer(template_dir)

            with TemporaryDirectory() as output_dir:
                renderer.render(model=model, output_dir=output_dir)
                with open(os.path.join(output_dir, "stmt.txt"), "r") as f:
                    rendered = f.read()

        assert rendered == (
            "Enter operations:\n"
            "int tmp;\n"
            "tmp = scope->counter + 1;\n"
            "scope->counter = tmp + 2;"
        )
