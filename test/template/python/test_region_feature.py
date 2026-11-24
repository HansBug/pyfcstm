"""Built-in template ``python`` and models that declare regions."""

import importlib.util

import pytest
from hbutils.testing import simulate_entry

from pyfcstm.entry import pyfcstmcli
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.template import extract_template
from test.testings.simulate_semantics import iter_semantic_cases

pytestmark = pytest.mark.unittest

REGION_SOURCE = """
def int n = 0;
state Root {
    [*] -> Run;
    state Run {
        region Worker { [*] -> Idle; state Idle { during { n = n + 1; } } }
        region Watch { [*] -> Idle; state Idle; }
    }
}
"""


def test_the_template_declares_the_region_feature(tmp_path):
    renderer = StateMachineCodeRenderer(extract_template("python", str(tmp_path)))
    assert renderer.features == frozenset({"region"})


def test_generate_renders_a_runnable_runtime_for_a_region_model(tmp_path):
    source = tmp_path / "regions.fcstm"
    source.write_text(REGION_SOURCE, encoding="utf-8")
    output = tmp_path / "generated"
    result = simulate_entry(
        pyfcstmcli,
        ["pyfcstm", "generate", "-i", str(source), "--template", "python", "-o", str(output)],
    )
    assert result.exitcode == 0, result.stdout + result.stderr
    assert sorted(item.name for item in output.iterdir()) == [
        "README.md",
        "README_zh.md",
        "machine.py",
    ]
    spec = importlib.util.spec_from_file_location("generated_region_machine", output / "machine.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    machine = module.RootMachine()
    machine.cycle()
    assert machine.configuration == "Root.Run{Worker: Idle, Watch: Idle}"
    assert machine.vars == {"n": 1}


def test_every_region_case_runs_on_the_generated_python_runner():
    region_ids = {case.id for case in iter_semantic_cases(categories=["regions"])}
    python_ids = {case.id for case in iter_semantic_cases(runners=["generated_python_alignment"])}
    assert region_ids
    assert region_ids <= python_ids
