"""
Validate C-family helper scope for built-in templates.

This module keeps C-family helper boundary checks separate from the broad
built-in template structure tests so target-language template structure changes
can advance independently from renderer-boundary cleanup.
"""

from pathlib import Path

import pytest
import yaml

from pyfcstm.render import StateMachineCodeRenderer


_REPO_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_DIR = _REPO_ROOT / "templates"

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


def _read_text(path: Path) -> str:
    """
    Read UTF-8 text from a repository file.

    :param path: Path to the text file.
    :type path: pathlib.Path
    :return: File contents decoded as UTF-8.
    :rtype: str

    Example::

        >>> text = _read_text(_TEMPLATES_DIR / 'python' / 'config.yaml')
        >>> 'expr_styles' in text
        True
    """
    return path.read_text(encoding="utf-8")


def _load_config(name: str) -> dict:
    """
    Load a built-in template configuration file.

    :param name: Built-in template directory name.
    :type name: str
    :return: Parsed YAML configuration mapping.
    :rtype: dict

    Example::

        >>> config = _load_config('c')
        >>> 'globals' in config
        True
    """
    with (_TEMPLATES_DIR / name / "config.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


@pytest.mark.unittest
def test_c_family_helpers_are_template_scoped():
    render_source = _read_text(_REPO_ROOT / "pyfcstm" / "render" / "render.py")
    for helper_name in _C_HELPER_NAMES:
        assert helper_name not in render_source

    python_renderer = StateMachineCodeRenderer(str(_TEMPLATES_DIR / "python"))
    assert not (_C_HELPER_NAMES & set(python_renderer.env.filters))
    assert not (_C_HELPER_NAMES & set(python_renderer.env.globals))
    assert "c_public_identifier_reserved" not in python_renderer.env.tests

    for name in ["c", "c_poll"]:
        renderer = StateMachineCodeRenderer(str(_TEMPLATES_DIR / name))
        assert _C_HELPER_NAMES <= (
            set(renderer.env.filters) | set(renderer.env.globals)
        )
        assert "c_public_identifier_reserved" in renderer.env.tests

        config = _load_config(name)
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
