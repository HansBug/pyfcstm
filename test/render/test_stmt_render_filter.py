"""The ``stmt_render`` template filter renders one operation statement through the public renderer."""

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.render import StateMachineCodeRenderer

pytestmark = pytest.mark.unittest


def test_a_custom_template_renders_a_single_statement_in_the_target_style(tmp_path):
    templates = tmp_path / "templates"
    templates.mkdir()
    (templates / "config.yaml").write_text("{}", encoding="utf-8")
    (templates / "enter.txt.j2").write_text(
        "{% for item in model.root_state.on_enters %}"
        "{% for stmt in item.operations %}{{ stmt | stmt_render(style='python') }}\n{% endfor %}"
        "{% endfor %}",
        encoding="utf-8",
    )
    model = load_state_machine_from_text(
        "def int x = 0; state Root { enter { x = x + 1; } }"
    )
    output = tmp_path / "output"
    StateMachineCodeRenderer(str(templates)).render(model, str(output))
    assert (output / "enter.txt").read_text(encoding="utf-8").strip() == 'scope["x"] = scope["x"] + 1'
