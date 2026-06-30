"""PlantUML and visualize smoke tests for generated combo pseudo states."""

import pathlib
import re
import textwrap

import pytest
from hbutils.testing import isolated_directory, simulate_entry

from pyfcstm.entry import pyfcstmcli
from pyfcstm.entry.plantuml import build_plantuml_output
from pyfcstm.entry import visualize as visualize_module


pytestmark = pytest.mark.unittest


COMBO_SOURCE = """
def int x = 1;
state Root {
    state S;
    state T;
    [*] -> S;
    S -> T :: E1 + [x > 0] + E2;
}
"""


def _write_combo_file(path):
    path.write_text(textwrap.dedent(COMBO_SOURCE).strip(), encoding="utf-8")


def _assert_combo_plantuml_contract(plantuml_text):
    assert plantuml_text.startswith("@startuml")
    assert re.search(r"root___combo_.*_h[0-9a-f]{12}", plantuml_text)
    assert 'state "combo after E1"' in plantuml_text
    assert 'state "combo after E1 + [x > 0]"' in plantuml_text
    assert "<<pseudo>> #line.dotted" in plantuml_text
    assert "S.E1" in plantuml_text
    assert "x > 0" in plantuml_text
    assert "S.E2" in plantuml_text


def test_build_plantuml_output_shows_combo_pseudo_chain(tmp_path):
    source_file = tmp_path / "combo.fcstm"
    _write_combo_file(source_file)

    plantuml_text = build_plantuml_output(str(source_file))

    _assert_combo_plantuml_contract(plantuml_text)


def test_plantuml_cli_writes_combo_pseudo_chain(tmp_path):
    source_file = tmp_path / "combo.fcstm"
    output_file = tmp_path / "combo.puml"
    _write_combo_file(source_file)

    result = simulate_entry(
        pyfcstmcli,
        ["pyfcstm", "plantuml", "-i", str(source_file), "-o", str(output_file)],
    )

    assert result.exitcode == 0
    _assert_combo_plantuml_contract(output_file.read_text(encoding="utf-8"))


def test_visualize_reuses_combo_plantuml_text_without_binary_snapshot(
    tmp_path, monkeypatch
):
    source_file = tmp_path / "combo.fcstm"
    _write_combo_file(source_file)
    captured = []

    def _render(plantuml_output, output_file, render_type, renderer, **kwargs):
        _assert_combo_plantuml_contract(plantuml_output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("%s:%s" % (render_type, renderer), encoding="utf-8")
        captured.append((plantuml_output, output_file, render_type, renderer, kwargs))
        return renderer

    monkeypatch.setattr(visualize_module, "render_plantuml_diagram", _render)

    with isolated_directory():
        result = simulate_entry(
            pyfcstmcli,
            [
                "pyfcstm",
                "visualize",
                "-i",
                str(source_file),
                "-o",
                "out/diagram",
                "-t",
                "svg",
                "--renderer",
                "local",
                "--no-open",
            ],
        )

        assert result.exitcode == 0
        assert pathlib.Path("out/diagram.svg").exists()
        assert captured
        assert captured[0][2] == "svg"
