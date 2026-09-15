"""Generated runtimes freeze external reads and own immutable configuration."""

import pytest

from .test_runtime import _render_python_module


pytestmark = pytest.mark.unittest


ROLE_MODEL = """
input float pressure;
param float gain = 2.0;
control int samples = 0;
output float reading = 0.0;
state Root {
    state Ready {
        during {
            if [pressure > 0.0] {
                samples = samples + 1;
                reading = pressure * gain;
            }
        }
    }
    [*] -> Ready;
}
"""


def test_input_hook_is_sampled_once_across_validation_and_execution():
    with _render_python_module(ROLE_MODEL) as module:

        class Device(module.RootMachine):
            reads = 0

            def read_pressure(self):
                self.reads += 1
                return float(self.reads)

        parameters = {"gain": 3.0}
        machine = Device(parameters=parameters)
        parameters["gain"] = 99.0
        assert machine.reads == 0
        assert machine.last_inputs is None
        assert machine.parameters == {"gain": 3.0}
        assert machine.vars == {"samples": 0, "reading": 0.0}
        machine.cycle()
        assert machine.reads == 1
        assert machine.vars == {"samples": 1, "reading": 3.0}
        assert machine.last_inputs == {"pressure": 1.0}
        machine.cycle()
        assert machine.reads == 2
        assert machine.vars == {"samples": 2, "reading": 6.0}
        with pytest.raises(TypeError):
            machine.parameters["gain"] = 8.0
        with pytest.raises(TypeError):
            machine.last_inputs["pressure"] = 8.0


def test_snapshot_input_keeps_unwritten_control_and_output():
    with _render_python_module(ROLE_MODEL) as module:
        machine = module.RootMachine()
        machine.cycle(inputs={"pressure": 5.0})
        machine.cycle(inputs={"pressure": -2.0})
        assert machine.vars == {"samples": 1, "reading": 10.0}
        assert machine.last_inputs == {"pressure": -2.0}
        assert machine.parameters == {"gain": 2.0}


def test_failed_cycle_preserves_committed_input_and_persistent_values():
    source = """
    input int divisor;
    param int numerator = 8;
    control int attempts = 0;
    output int result = 0;
    state Root { state Ready { during {
        attempts = attempts + 1;
        result = numerator / divisor;
    } } [*] -> Ready; }
    """
    with _render_python_module(source) as module:
        machine = module.RootMachine()
        machine.cycle(inputs={"divisor": 2})
        with pytest.raises(ValueError):
            machine.cycle(inputs={"divisor": 0})
        assert machine.vars == {"attempts": 1, "result": 4}
        assert machine.cycle_count == 1
        assert machine.last_inputs == {"divisor": 2}
        machine.cycle(inputs={"divisor": 4})
        assert machine.vars == {"attempts": 2, "result": 2}


def test_hot_start_uses_complete_configuration_without_entry_actions():
    source = ROLE_MODEL.replace("state Root {", "state Root { enter { samples = 99; }")
    with _render_python_module(source) as module:
        machine = module.RootMachine(
            initial_state="Root.Ready",
            initial_vars={"samples": 7, "reading": 11.0},
            parameters={"gain": 3.0},
        )
        assert machine.vars == {"samples": 7, "reading": 11.0}
        machine.cycle(inputs={"pressure": 5.0})
        assert machine.vars == {"samples": 8, "reading": 15.0}


def test_abstract_context_keeps_parameter_and_input_snapshots():
    source = ROLE_MODEL.replace(
        "state Ready {", "state Ready { during abstract Observe;"
    )
    with _render_python_module(source) as module:
        snapshots = []

        class Device(module.RootMachine):
            def _abstract_hook_Root_Ready_Observe(self, ctx):
                snapshots.append(ctx)
                assert ctx.inputs["pressure"] == self.get_input_pressure()
                assert ctx.parameters["gain"] == self.get_param_gain()

        machine = Device(parameters={"gain": 3.0})
        machine.cycle(inputs={"pressure": 2.0})
        machine.cycle(inputs={"pressure": 4.0})
        assert [ctx.inputs for ctx in snapshots] == [
            {"pressure": 2.0},
            {"pressure": 4.0},
        ]
        assert [ctx.parameters for ctx in snapshots] == [{"gain": 3.0}, {"gain": 3.0}]
        for ctx in snapshots:
            with pytest.raises(TypeError):
                ctx.inputs["pressure"] = 99.0
            with pytest.raises(TypeError):
                ctx.parameters["gain"] = 99.0




@pytest.mark.parametrize("value", [True, "2", float("nan"), float("inf"), 10**1000])
def test_parameter_values_are_validated_before_execution(value):
    with _render_python_module(ROLE_MODEL) as module:
        with pytest.raises(ValueError):
            module.RootMachine(parameters={"gain": value})


def test_unknown_or_missing_parameters_are_rejected():
    with _render_python_module(ROLE_MODEL) as module:
        with pytest.raises(ValueError, match="Unknown parameters"):
            module.RootMachine(parameters={"pressure": 1.0})
        with pytest.raises(ValueError, match="Hot start requires parameter gain"):
            module.RootMachine(
                initial_state="Root.Ready", initial_vars={"samples": 0, "reading": 0.0}
            )


def test_missing_input_hook_and_unknown_input_do_not_advance_machine():
    with _render_python_module(ROLE_MODEL) as module:
        machine = module.RootMachine()
        with pytest.raises(NotImplementedError, match="read_pressure"):
            machine.cycle()
        with pytest.raises(ValueError, match="Unknown inputs"):
            machine.cycle(inputs={"gain": 1.0})
        assert machine.cycle_count == 0
        assert machine.last_inputs is None
        assert machine.vars == {"samples": 0, "reading": 0.0}
        with pytest.raises(ValueError, match="only available during a cycle"):
            machine.get_input_pressure()
        machine.cycle(inputs={"pressure": 2.0})
        with pytest.raises(ValueError, match="only available during a cycle"):
            machine.get_input_pressure()


@pytest.mark.parametrize("value", [True, 1.0, "1", None])
def test_integer_input_requires_an_integer_snapshot(value):
    source = "input int signal; output int result = 0; state Root { state Ready { during { result = signal; } } [*] -> Ready; }"
    with _render_python_module(source) as module:
        machine = module.RootMachine()
        with pytest.raises(ValueError, match="Input signal must be int"):
            machine.cycle(inputs={"signal": value})
        assert machine.last_inputs is None
        assert machine.vars == {"result": 0}


def test_failed_external_read_preserves_previous_committed_snapshot():
    with _render_python_module(ROLE_MODEL) as module:

        class Device(module.RootMachine):
            def read_pressure(self):
                raise OSError("sensor unavailable")

        machine = Device()
        machine.cycle(inputs={"pressure": 2.0})
        with pytest.raises(OSError, match="sensor unavailable"):
            machine.cycle()
        assert machine.last_inputs == {"pressure": 2.0}
        assert machine.vars == {"samples": 1, "reading": 4.0}
        assert machine.cycle_count == 1
        machine.cycle(inputs={"pressure": 3.0})
        assert machine.vars == {"samples": 2, "reading": 6.0}


@pytest.mark.parametrize("language", ["en", "zh"])
@pytest.mark.parametrize("section", ["quick", "snapshot", "initial", "hot"])
def test_role_readme_examples_use_inputs_and_separate_parameters(
    language, section, monkeypatch
):
    import sys
    from pathlib import Path
    from .test_runtime import _render_python_artifacts

    dsl = ROLE_MODEL.replace("input float pressure;", "input float pressure; input int unused;")
    dsl = dsl.replace("state Ready {", "state Ready { during abstract Observe;")
    dsl = dsl.replace("[*] -> Ready;", "[*] -> Ready; Ready -> Ready :: Tick;")
    with _render_python_artifacts(dsl) as artifacts:
        monkeypatch.setitem(sys.modules, "machine", artifacts["module"])
        key = "readme_file" if language == "en" else "readme_zh_file"
        markdown = Path(artifacts[key]).read_text(encoding="utf-8")
        from test.template.readme_examples import example_code
        namespace = {}
        exec(example_code(markdown, "quick-start"), namespace)
        machine = namespace["machine"]
        assert machine.last_inputs == {"pressure": 1.0, "unused": 1}
        assert machine.parameters == {"gain": 1.0}
        assert machine.vars == {"samples": 1, "reading": 1.0}
        assert machine.hook_calls == [("Root.Ready.Observe", "during")]
        assert type(machine).read_pressure is not artifacts["module"].RootMachine.read_pressure
        if section == "snapshot":
            # Missing device data proves that the complete snapshot bypasses all readers.
            namespace["sensor_values"].clear()
            exec(example_code(markdown, "input-snapshot"), namespace)
            assert machine.vars == {"samples": 2, "reading": 1.0}
            assert len(machine.hook_calls) == 2
            return
        if section == "initial":
            exec(example_code(markdown, "initial-values"), namespace)
            machine = namespace["machine"]
            assert machine.vars == {"samples": 1, "reading": 1.0}
            assert machine.last_inputs is None
            assert machine.hook_calls == []
        if section == "hot":
            exec(example_code(markdown, "hot-start"), namespace)
            machine = namespace["machine"]
            assert machine.vars == {"samples": 1, "reading": 1.0}
            assert machine.parameters == {"gain": 1.0}
            assert machine.hook_calls == []
        namespace["sensor_values"]["pressure"] = 3.0
        machine.cycle()
        assert machine.vars == {"samples": 2, "reading": 3.0}
        assert machine.parameters == {"gain": 1.0}
        committed = dict(machine.last_inputs)
        del namespace["sensor_values"]["unused"]
        with pytest.raises(KeyError, match="unused"):
            machine.cycle()
        assert machine.vars == {"samples": 2, "reading": 3.0}
        assert machine.last_inputs == committed
        namespace["sensor_values"].update(pressure=-2.0, unused=7)
        machine.cycle()
        assert machine.last_inputs == {"pressure": -2.0, "unused": 7}
        assert machine.vars == {"samples": 2, "reading": 3.0}
        assert machine.hook_calls[-1] == ("Root.Ready.Observe", "during")


def test_unused_input_is_sampled_each_cycle_without_implicit_hold():
    source = "input int signal; input int unused; output int result = 0; state Root { state Ready { during { result = signal; } } [*] -> Ready; }"
    with _render_python_module(source) as module:
        reads = []

        class Device(module.RootMachine):
            def read_signal(self):
                reads.append("signal")
                return len(reads)

            def read_unused(self):
                reads.append("unused")
                return len(reads)

        machine = Device()
        assert machine.parameters == {}
        machine.cycle()
        assert reads == ["signal", "unused"]
        assert machine.last_inputs == {"signal": 1, "unused": 2}
        machine.cycle()
        assert reads == ["signal", "unused", "signal", "unused"]
        assert machine.last_inputs == {"signal": 3, "unused": 4}
        assert machine.vars == {"result": 3}


def test_role_getters_preserve_significant_underscores():
    source = """
    input int a_b; input int a__b; input int a_b_;
    param int gain = 4; param int gain_ = 5;
    output int result = 0;
    state Root { state Ready { during {
        result = a_b + 10 * a__b + 100 * a_b_ + 1000 * gain + 10000 * gain_;
    } } [*] -> Ready; }
    """
    with _render_python_module(source) as module:
        machine = module.RootMachine()
        assert machine.parameters == {"gain": 4, "gain_": 5}
        assert machine.get_param_gain_() == 5
        machine.cycle(inputs={"a_b": 1, "a__b": 2, "a_b_": 3})
        assert machine.vars == {"result": 54321}
        assert machine.last_inputs == {"a_b": 1, "a__b": 2, "a_b_": 3}
