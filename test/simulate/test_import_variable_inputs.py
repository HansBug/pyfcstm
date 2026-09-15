"""Imported inputs use one host sample and one immutable parameter binding."""

import pytest

from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SimulationRuntime

pytestmark = pytest.mark.unittest


class CountingInput:
    def __init__(self):
        self.reads = 0
        self.advances = 0

    def get(self):
        self.reads += 1
        return 3

    def cycle(self):
        self.advances += 1


def test_shared_import_input_uses_final_name_and_one_sample(tmp_path):
    (tmp_path / "child.fcstm").write_text(
        """input int value;
param int gain = 2;
output int result = 0;
state Child { enter { result = value * gain; } }
""",
        encoding="utf-8",
    )
    host = tmp_path / "host.fcstm"
    host.write_text(
        """input int shared;
param int configured = 4;
state Host {
    import "./child.fcstm" as A {
        var value -> shared;
        var gain -> configured;
        var result -> a_result;
    }
    import "./child.fcstm" as B {
        var value -> shared;
        var gain -> configured;
        var result -> b_result;
    }
    [*] -> A;
    A -> B;
}
""",
        encoding="utf-8",
    )
    machine = load_state_machine_from_file(host)
    source = CountingInput()
    runtime = SimulationRuntime(
        machine, parameters={"configured": 5}, input_source={"shared": source}
    )
    first = runtime.cycle()
    assert first.inputs == {"shared": 3}
    assert source.reads == source.advances == 1
    assert runtime.outputs["a_result"] == 15
    runtime.cycle()
    assert source.reads == source.advances == 2
    assert runtime.outputs == {"a_result": 15, "b_result": 15}
    assert runtime.parameters == {"configured": 5}
