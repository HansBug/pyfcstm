"""
Validate C-family helper scope for built-in templates.

This module keeps C-family helper boundary checks separate from the broad
built-in template structure tests so target-language template structure changes
can advance independently from renderer-boundary cleanup.
"""

import inspect
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import yaml

import pyfcstm.render.render as render_module
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.template import extract_template


_TEMPLATE_NAMES = ("c", "c_poll", "cpp", "cpp_poll")

_C_HELPER_NAMES = {
    "to_c_identifier",
    "to_c_path_identifier",
    "to_c_public_identifier",
    "to_c_public_macro_identifier",
    "is_c_public_identifier_reserved",
    "render_c_action_body",
    "render_c_condition_body",
    "render_c_reset_vars_body",
}


def _load_config(template_dir: Path) -> dict:
    """
    Load an extracted built-in template configuration file.

    :param template_dir: Extracted built-in template directory.
    :type template_dir: pathlib.Path
    :return: Parsed YAML configuration mapping.
    :rtype: dict

    Example::

        >>> with TemporaryDirectory() as td:
        ...     path = Path(extract_template('c', td))
        ...     config = _load_config(path)
        >>> 'globals' in config
        True
    """
    with (template_dir / "config.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _extract_templates(root: Path) -> dict:
    """
    Extract C-family and Python built-in templates for boundary checks.

    :param root: Temporary directory used as extraction root.
    :type root: pathlib.Path
    :return: Mapping from template names to extracted template directories.
    :rtype: dict

    Example::

        >>> with TemporaryDirectory() as td:
        ...     paths = _extract_templates(Path(td))
        >>> 'python' in paths
        True
    """
    names = ("python",) + _TEMPLATE_NAMES
    return {name: Path(extract_template(name, str(root / name))) for name in names}


@pytest.mark.unittest
def test_c_family_helpers_are_template_scoped():
    render_source = inspect.getsource(render_module)
    for helper_name in _C_HELPER_NAMES:
        assert helper_name not in render_source

    with TemporaryDirectory() as td:
        template_dirs = _extract_templates(Path(td))

        python_renderer = StateMachineCodeRenderer(str(template_dirs["python"]))
        assert not (_C_HELPER_NAMES & set(python_renderer.env.filters))
        assert not (_C_HELPER_NAMES & set(python_renderer.env.globals))
        assert "c_public_identifier_reserved" not in python_renderer.env.tests

        for name in _TEMPLATE_NAMES:
            renderer = StateMachineCodeRenderer(str(template_dirs[name]))
            assert _C_HELPER_NAMES <= (
                set(renderer.env.filters) | set(renderer.env.globals)
            )
            assert "c_public_identifier_reserved" in renderer.env.tests

            config = _load_config(template_dirs[name])
            globals_config = config["globals"]
            assert globals_config["render_c_action_body"] == {
                "type": "import",
                "from": "pyfcstm.render.c_runtime.render_c_action_body",
            }
            assert globals_config["render_c_condition_body"] == {
                "type": "import",
                "from": "pyfcstm.render.c_runtime.render_c_condition_body",
            }
            assert globals_config["render_c_reset_vars_body"] == {
                "type": "import",
                "from": "pyfcstm.render.c_runtime.render_c_reset_vars_body",
            }
            assert config["filters"]["to_c_identifier"] == {
                "type": "import",
                "from": "pyfcstm.utils.to_c_identifier",
            }
            assert config["tests"]["c_public_identifier_reserved"] == {
                "type": "import",
                "from": "pyfcstm.utils.is_c_public_identifier_reserved",
            }
