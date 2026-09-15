"""Exercise role boundaries on one generated runtime with both numeric types."""

import importlib.util
from pathlib import Path

import pytest

from .test_runtime import _render_python_artifacts


pytestmark = pytest.mark.unittest

ROLE_BOUNDARIES = """
input int divisor;
input float pressure;
param int scale = 2.0;
param float gain = 3.0;
control int samples = 0;
output float reading = 0.0;
state Root {
    state Ready {
        during {
            samples = samples + 1;
            reading = pressure * gain * scale / divisor;
        }
    }
    [*] -> Ready;
    Ready -> [*] :: Stop;
}
"""


@pytest.fixture(scope="module")
def role_module(tmp_path_factory):
    # Keep generated source available after teardown for coverage JSON reports.
    source_path = tmp_path_factory.mktemp("role_runtime") / "machine.py"
    with _render_python_artifacts(ROLE_BOUNDARIES) as artifacts:
        source_path.write_bytes(Path(artifacts["machine_file"]).read_bytes())
    spec = importlib.util.spec_from_file_location(
        "generated_role_boundaries", str(source_path)
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_defaults_snapshot_rollback_and_ended_noop(role_module):
    machine = role_module.RootMachine()
    assert machine.parameters == {"scale": 2, "gain": 3.0}
    assert machine.get_param_scale() == 2
    assert machine.get_param_gain() == 3.0
    assert machine.last_inputs is None
    values = {"divisor": 2, "pressure": 4.0}
    machine.cycle(inputs=values)
    values["pressure"] = 999.0
    assert machine.vars == {"samples": 1, "reading": 12.0}
    assert machine.last_inputs == {"divisor": 2, "pressure": 4.0}
    with pytest.raises(ValueError):
        machine.cycle(inputs={"divisor": 0, "pressure": 5.0})
    assert machine.vars == {"samples": 1, "reading": 12.0}
    assert machine.last_inputs == {"divisor": 2, "pressure": 4.0}
    machine.cycle(inputs={"divisor": 1, "pressure": 1.0})
    machine.cycle("Root.Ready.Stop", inputs={"divisor": 1, "pressure": 1.0})
    assert machine.is_ended
    last_inputs = machine.last_inputs
    machine.cycle(inputs={"unknown": object()})
    assert machine.last_inputs is last_inputs


def test_providers_and_partial_snapshots_freeze_every_input(role_module):
    reads = []

    class Device(role_module.RootMachine):
        def read_divisor(self):
            reads.append("divisor")
            return 2

        def read_pressure(self):
            reads.append("pressure")
            return 4.0

    parameters = {"scale": 4, "gain": 5.0}
    machine = Device(parameters=parameters)
    parameters["gain"] = 999.0
    assert reads == []
    machine.cycle()
    assert reads == ["divisor", "pressure"]
    assert machine.vars["reading"] == 40.0
    machine.cycle(inputs={"divisor": 4})
    assert reads == ["divisor", "pressure", "pressure"]
    assert machine.vars["reading"] == 20.0
    machine.cycle(inputs={"pressure": 1.0})
    assert reads == ["divisor", "pressure", "pressure", "divisor"]
    assert machine.vars["reading"] == 10.0


@pytest.mark.parametrize("parameters", [{}, {"scale": 1}])
def test_hot_start_requires_each_parameter(role_module, parameters):
    with pytest.raises(ValueError, match="Hot start requires parameter"):
        role_module.RootMachine(
            initial_state="Root.Ready",
            initial_vars={"samples": 7, "reading": 8.0},
            parameters=parameters,
        )


def test_hot_start_uses_complete_owned_configuration(role_module):
    machine = role_module.RootMachine(
        initial_state="Root.Ready",
        initial_vars={"samples": 7, "reading": 8.0},
        parameters={"scale": 4, "gain": 5.0},
    )
    assert machine.vars == {"samples": 7, "reading": 8.0}
    machine.cycle(inputs={"divisor": 2, "pressure": 1.0})
    assert machine.vars == {"samples": 8, "reading": 10.0}
    with pytest.raises(TypeError):
        machine.parameters["scale"] = 7
    with pytest.raises(TypeError):
        machine.last_inputs["pressure"] = 7


@pytest.mark.parametrize("inputs", [{}, {"divisor": 1}])
def test_missing_external_implementations_fail_without_commit(role_module, inputs):
    machine = role_module.RootMachine()
    with pytest.raises(NotImplementedError):
        machine.cycle(inputs=inputs)
    assert machine.last_inputs is None
    assert machine.vars == {"samples": 0, "reading": 0.0}


@pytest.mark.parametrize("name", ["divisor", "pressure"])
def test_input_getters_reject_reads_outside_a_cycle(role_module, name):
    machine = role_module.RootMachine()
    with pytest.raises(ValueError, match="only available during a cycle"):
        getattr(machine, "get_input_" + name)()


def test_unknown_names_and_wrong_integer_type_are_rejected(role_module):
    with pytest.raises(ValueError, match="Unknown parameters"):
        role_module.RootMachine(parameters={"unknown": 1})
    machine = role_module.RootMachine()
    # Pin the shared normalizer guard as well as public name validation.
    with pytest.raises(ValueError, match="not defined"):
        machine._normalize_persistent_value("unknown", 1, "input")
    with pytest.raises(ValueError, match="Unknown inputs"):
        machine.cycle(inputs={"unknown": 1})
    with pytest.raises(ValueError, match="must be int"):
        machine.cycle(inputs={"divisor": 1.0, "pressure": 2.0})
    assert machine.last_inputs is None


def test_direct_context_copies_optional_role_mappings(role_module):
    parameters = {"gain": 2.0}
    inputs = {"pressure": 3.0}
    ctx = role_module.ReadOnlyExecutionContext(
        ("Root",), {}, "Observe", "during", parameters=parameters, inputs=inputs
    )
    parameters["gain"] = 8.0
    inputs["pressure"] = 9.0
    assert ctx.parameters == {"gain": 2.0}
    assert ctx.inputs == {"pressure": 3.0}
    old_style = role_module.ReadOnlyExecutionContext(("Root",), {}, "Observe", "during")
    assert old_style.parameters == {}
    assert old_style.inputs == {}
