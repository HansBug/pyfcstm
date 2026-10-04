"""Role-aware public runtime sampling and commit contracts."""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.simulate.inputs import SequenceInput, SimulationRuntimeInputSourceError

pytestmark = pytest.mark.unittest


def machine(source):
    return parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(source, "state_machine_dsl")
    )


SOURCE = """
input float pressure;
param float gain = 2.0;
control int count = 0;
output float reading = 0.0;
state Root {
    enter { reading = pressure * gain; }
    state Running { during { count = count + 1; reading = pressure * gain; } }
    [*] -> Running;
}
"""


class Spy:
    def __init__(self, values=(10.0, 20.0, 30.0)):
        self.values = values
        self.index = 0
        self.reads = []
        self.advances = []

    def get(self):
        self.reads.append(self.index)
        return self.values[self.index]

    def cycle(self):
        self.advances.append(self.index)
        self.index += 1


def test_runtime_parameters_persistent_partition_and_overrides():
    source = Spy()
    runtime = SimulationRuntime(
        machine(SOURCE), parameters={"gain": 3.0}, input_source={"pressure": source}
    )
    assert dict(runtime.vars) == {"count": 0, "reading": 0.0}
    assert dict(runtime.parameters) == {"gain": 3.0}
    assert runtime.last_inputs is None
    assert source.reads == source.advances == []
    first = runtime.cycle(trace=True)
    assert dict(first.inputs) == {"pressure": 10.0}
    assert runtime.vars["reading"] == 30.0
    second = runtime.cycle(inputs={"pressure": 7.0}, trace=True)
    assert dict(second.inputs) == {"pressure": 7.0}
    assert runtime.vars["reading"] == 21.0
    assert runtime.history[-1]["inputs"] == {"pressure": 7.0}
    assert runtime.last_inputs == second.inputs
    assert runtime.outputs == {"reading": 21.0}
    assert runtime.control_variables == {"count": runtime.vars["count"]}
    assert all(entry.inputs == second.inputs for entry in second.trace)
    runtime.cycle()
    assert runtime.vars["reading"] == 90.0
    assert source.reads == source.advances == [0, 1, 2]
    for mapping in (
        runtime.parameters,
        runtime.outputs,
        runtime.control_variables,
        first.inputs,
        runtime.last_inputs,
    ):
        with pytest.raises(TypeError):
            mapping["anything"] = 0


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"input_source": {}},
        {"input_source": {"pressure": 1, "unknown": 2}},
        {"input_source": {"pressure": object()}},
        {"input_source": {"pressure": 1}, "parameters": {"count": 2}},
        {"input_source": {"pressure": 1}, "initial_vars": {"gain": 2}},
        {"input_source": {"pressure": 1}, "initial_vars": {"pressure": 2}},
    ],
)
def test_invalid_construction(kwargs):
    with pytest.raises(ValueError):
        SimulationRuntime(machine(SOURCE), **kwargs)


@pytest.mark.parametrize(
    "override", [{"unknown": 1}, {"pressure": True}, {"pressure": float("nan")}, []]
)
def test_bad_override_rejected_before_sampling(override):
    source = Spy()
    runtime = SimulationRuntime(machine(SOURCE), input_source={"pressure": source})
    with pytest.raises(SimulationRuntimeInputSourceError):
        runtime.cycle(inputs=override)
    assert source.reads == source.advances == []
    assert runtime.cycle_count == 0
    assert runtime.history == []
    assert runtime.last_inputs is None


def test_bad_event_rejected_before_sampling():
    source = Spy()
    runtime = SimulationRuntime(machine(SOURCE), input_source={"pressure": source})
    with pytest.raises(ValueError):
        runtime.cycle(object())
    assert source.reads == source.advances == []


def test_source_read_error_does_not_commit():
    runtime = SimulationRuntime(
        machine(SOURCE), input_source={"pressure": SequenceInput([10.0])}
    )
    runtime.cycle()
    before = dict(runtime.vars), list(runtime.history), runtime.last_inputs
    with pytest.raises(SimulationRuntimeInputSourceError) as caught:
        runtime.cycle()
    assert caught.value.code == "E_INPUT_SOURCE_READ"
    assert isinstance(caught.value.__cause__, StopIteration)
    assert (dict(runtime.vars), runtime.history, runtime.last_inputs) == before
    assert runtime.cycle_count == 1
    assert not runtime.is_error_state


def test_advance_failure_poison_prevents_all_further_calls(caplog):
    caplog.set_level("INFO", logger="pyfcstm.simulate")

    class Broken(Spy):
        def cycle(self):
            raise OSError("advance failed")

    source = Broken()
    runtime = SimulationRuntime(machine(SOURCE), input_source={"pressure": source})
    with pytest.raises(SimulationRuntimeInputSourceError) as caught:
        runtime.cycle()
    assert caught.value.code == "E_INPUT_SOURCE_CONTRACT"
    assert runtime.is_error_state
    assert runtime.input_source_error is caught.value
    assert runtime.cycle_count == 0
    assert runtime.vars == {"count": 0, "reading": 0.0}
    assert runtime.history == []
    assert runtime.last_inputs is None
    runtime.cycle()
    assert source.reads == [0]
    assert "completed successfully" not in caplog.text


def test_hot_start_requires_complete_parameters_and_persistent_values():
    sm = machine(SOURCE)
    with pytest.raises(ValueError):
        SimulationRuntime(
            sm,
            initial_state="Root.Running",
            initial_vars={"count": 4, "reading": 5.0},
            input_source={"pressure": 1},
        )
    source = Spy()
    runtime = SimulationRuntime(
        sm,
        initial_state="Root.Running",
        initial_vars={"count": 4, "reading": 5.0},
        parameters={"gain": 3},
        input_source={"pressure": source},
    )
    assert runtime.vars == {"count": 4, "reading": 5.0}
    assert source.reads == []
    runtime.cycle()
    assert runtime.vars == {"count": 5, "reading": 30.0}


@pytest.mark.parametrize("history_size", [-1, True, 0.5, "3"])
def test_history_prerequisites_checked_during_construction(history_size):
    source = Spy()
    with pytest.raises(ValueError):
        SimulationRuntime(
            machine(SOURCE),
            input_source={"pressure": source},
            history_size=history_size,
        )
    assert source.reads == source.advances == []


def test_delta_consumes_input_but_rolls_back_machine_state():
    sm = machine("""input int permit; output int result = 0;
    state Root {
        enter { result = permit; }
        state Ready;
        [*] -> Ready : if [permit > 0];
    }""")
    source = Spy((0, 1))
    runtime = SimulationRuntime(sm, input_source={"permit": source})
    first = runtime.cycle(trace=True)
    assert first.delta
    assert first.inputs == {"permit": 0}
    assert first.trace == ()
    assert runtime.vars == {"result": 0}
    second = runtime.cycle(trace=True)
    assert not second.delta
    assert runtime.vars == {"result": 1}
    assert source.reads == source.advances == [0, 1]
    assert runtime.cycle_count == len(runtime.history) == 2


def test_termination_and_ended_noop():
    sm = machine("""input int stop; output int result = 0;
    state Root {
        state Ready { exit { result = stop; } }
        [*] -> Ready;
        Ready -> [*] : if [stop > 0];
    }""")
    source = Spy((0, 1))
    runtime = SimulationRuntime(sm, input_source={"stop": source})
    runtime.cycle()
    result = runtime.cycle(trace=True)
    assert runtime.is_ended
    assert runtime.vars == {"result": 1}
    assert result.inputs == {"stop": 1}
    assert runtime.history[-1]["state"] == "(terminated)"
    assert runtime.cycle(inputs={"wrong": True}).inputs == {}
    assert runtime.last_inputs == {"stop": 1}
    assert source.reads == source.advances == [0, 1]


@pytest.mark.parametrize("mode", ["raise", "log"])
def test_handler_context_and_failure_contract(mode):
    sm = machine("""input int sensor; param int gain = 2; output int result = 0;
    state Root {
        state Ready { during abstract Observe; during { result = sensor * gain; } }
        [*] -> Ready;
    }""")
    source = Spy((3, 4, 5))
    runtime = SimulationRuntime(
        sm, input_source={"sensor": source}, abstract_error_mode=mode
    )
    contexts = []

    def handler(context):
        contexts.append(context)
        raise OSError("handler unavailable")

    runtime.cycle()
    runtime.register_abstract_handler("Root.Ready.Observe", handler)
    if mode == "raise":
        with pytest.raises(OSError, match="handler unavailable"):
            runtime.cycle()
        assert runtime.cycle_count == 1
        assert runtime.vars == {"result": 6}
        assert runtime.last_inputs == {"sensor": 3}
        assert runtime.is_error_state
        runtime.cycle()
        assert source.reads == [0, 1]
        assert source.advances == [0]
    else:
        runtime.cycle()
        assert runtime.cycle_count == 2
        assert runtime.vars == {"result": 8}
        assert len(runtime.abstract_handler_errors) == 1
        assert source.reads == source.advances == [0, 1]
    assert len(contexts) == 1
    assert contexts[0].inputs == {"sensor": 4}
    assert contexts[0].parameters == {"gain": 2}
    assert set(contexts[0].vars) == {"result"}
    for mapping in (contexts[0].inputs, contexts[0].parameters):
        with pytest.raises(TypeError):
            mapping["sensor"] = 0


def test_expression_error_retries_same_input_frame():
    sm = machine("""input int divisor; output int result = 0;
    state Root { enter { result = 8 / divisor; } state Ready; [*] -> Ready; }""")
    source = Spy((0, 2))
    runtime = SimulationRuntime(sm, input_source={"divisor": source})
    with pytest.raises(ArithmeticError):
        runtime.cycle()
    assert runtime.vars == {"result": 0}
    assert runtime.history == []
    assert runtime.last_inputs is None
    assert source.advances == []
    runtime.cycle(inputs={"divisor": 2})
    assert runtime.vars == {"result": 4}
    assert source.reads == [0, 0]
    assert source.advances == [0]


def test_hot_composite_delays_initial_transition_and_reads_current_inputs():
    sm = machine("""input int permit; param int gain = 2; output int result = 0;
    state Root {
        state Group {
            enter { result = 999; }
            during before { result = 888; }
            state Ready { enter { result = permit * gain; } }
            [*] -> Ready : if [permit > 0];
        }
        [*] -> Group;
    }""")
    source = Spy((0, 3))
    runtime = SimulationRuntime(
        sm,
        initial_state="Root.Group",
        initial_vars={"result": 7},
        parameters={"gain": 4},
        input_source={"permit": source},
    )
    assert source.reads == []
    assert runtime.cycle().delta
    assert runtime.vars == {"result": 7}
    assert not runtime.cycle().delta
    assert runtime.vars == {"result": 12}
    assert source.reads == source.advances == [0, 1]


@pytest.mark.parametrize("size", [None, 0, 1, 2])
def test_history_retention_and_detached_trace(size):
    runtime = SimulationRuntime(
        machine(SOURCE), input_source={"pressure": 1.0}, history_size=size
    )
    result = runtime.cycle(trace=True)
    runtime.cycle()
    runtime.cycle()
    assert len(runtime.history) == (3 if size is None else size)
    assert result.trace
    serialized = result.trace[0].to_dict()
    assert serialized["inputs"] == {"pressure": 1.0}
    assert serialized["parameters"] == {"gain": 2.0}
    serialized["inputs"]["pressure"] = 100
    assert result.trace[0].inputs == {"pressure": 1.0}
    with pytest.raises(ValueError):
        runtime.history_size = -1
    assert runtime.history_size == size


def test_source_instances_must_not_be_bound_twice():
    sm = machine("input int first; input int second; state Root;")
    source = Spy((1,))
    with pytest.raises(SimulationRuntimeInputSourceError, match="multiple inputs"):
        SimulationRuntime(sm, input_source={"first": source, "second": source})
    assert source.reads == source.advances == []


class Vector:
    input_names = ("first", "second")

    def __init__(self, values=None):
        self.values = {"second": 2, "first": 1} if values is None else values
        self.reads = 0
        self.advances = 0

    def get(self):
        self.reads += 1
        return self.values

    def cycle(self):
        self.advances += 1


def test_third_party_integrated_source_normalizes_order_and_overrides():
    sm = machine("input int first; input float second; state Root;")
    source = Vector()
    runtime = SimulationRuntime(sm, input_source=source)
    assert source.reads == 0
    result = runtime.cycle(inputs={"first": 3})
    assert result.inputs == {"first": 3, "second": 2.0}
    assert tuple(result.inputs) == ("first", "second")
    assert type(result.inputs["second"]) is float
    assert source.reads == source.advances == 1
    source.values["second"] = 99
    assert result.inputs["second"] == 2.0


@pytest.mark.parametrize(
    "names", [("second", "first"), ("first",), ("first", "first"), ["first", "second"]]
)
def test_integrated_static_contract_rejected_before_reads(names):
    sm = machine("input int first; input int second; state Root;")
    source = Vector()
    source.input_names = names
    with pytest.raises(SimulationRuntimeInputSourceError):
        SimulationRuntime(sm, input_source=source)
    assert source.reads == source.advances == 0


@pytest.mark.parametrize(
    "values",
    [
        [],
        {"first": 1},
        {"first": 1, "second": 2, "third": 3},
        {"first": 1.5, "second": 2},
    ],
)
def test_integrated_bad_read_does_not_advance(values):
    sm = machine("input int first; input int second; state Root;")
    source = Vector(values)
    runtime = SimulationRuntime(sm, input_source=source)
    with pytest.raises(SimulationRuntimeInputSourceError):
        runtime.cycle()
    assert source.reads == 1
    assert source.advances == runtime.cycle_count == 0
    assert runtime.last_inputs is None
    source.values = {"first": 1, "second": 2}
    runtime.cycle()
    assert source.advances == runtime.cycle_count == 1


@pytest.mark.parametrize("command", ["clear", "init Root.Running count=3 reading=4"])
def test_repl_rebuild_refuses_to_reuse_dynamic_source(command):
    from pyfcstm.entry.simulate.commands import CommandProcessor

    source = Spy()
    runtime = SimulationRuntime(machine(SOURCE), input_source={"pressure": source})
    processor = CommandProcessor(
        runtime, state_machine=runtime.state_machine, use_color=False
    )
    result = processor.process(command)
    assert "fresh input_source" in result.output
    assert processor.runtime is runtime
    assert source.reads == source.advances == []


@pytest.mark.parametrize("command", ["clear", "init Root.Ready result=7"])
def test_repl_rebuild_keeps_fixed_parameters(command):
    from pyfcstm.entry.simulate.commands import CommandProcessor

    sm = machine(
        "param int gain = 2; output int result = 0; state Root { state Ready; [*] -> Ready; }"
    )
    runtime = SimulationRuntime(sm, parameters={"gain": 9})
    processor = CommandProcessor(runtime, state_machine=sm, use_color=False)
    processor.process(command)
    assert processor.runtime is not runtime
    assert processor.runtime.parameters == {"gain": 9}


def test_cli_missing_cycle_vector_is_a_readable_error(tmp_path):
    from click.testing import CliRunner
    from pyfcstm.entry.cli import cli

    path = tmp_path / "external.fcstm"
    path.write_text("input int sensor; state Root;")
    result = CliRunner().invoke(cli, ["simulate", "-i", str(path), "-e", "cycle"])
    assert result.exit_code != 0
    assert "Each cycle requires exactly these inputs" in result.output
    assert "E_INPUT_SOURCE_CONTRACT" in result.output


def test_guard_effect_branches_aspects_and_refs_share_one_input_frame():
    sm = machine("""input int sensor; param int gain = 2;
    output int result = 0; control int ticks = 0;
    state Root {
        >> during before { ticks = ticks + sensor; }
        enter { result = sensor; }
        state A {
            exit { result = result + sensor; }
            during Read { if [sensor > 0] { result = sensor * gain; } else { result = 0; } }
        }
        state B {
            enter { result = result + sensor; }
            during ref /A.Read;
        }
        [*] -> A;
        A -> B : if [sensor > 1] effect { result = result + sensor; };
    }""")
    source = Spy((1, 2, 3))
    runtime = SimulationRuntime(sm, input_source={"sensor": source})
    runtime.cycle()
    assert runtime.vars == {"result": 2, "ticks": 1}
    second = runtime.cycle(trace=True)
    assert runtime.current_state.path == ("Root", "B")
    assert all(entry.inputs == {"sensor": 2} for entry in second.trace)
    assert any(entry.kind == "transition" for entry in second.trace)
    runtime.cycle()
    assert runtime.vars["result"] == 6
    assert source.reads == source.advances == [0, 1, 2]


def test_dfs_failure_leaves_sources_at_current_frame():
    from pyfcstm.simulate import SimulationRuntimeDfsError

    sm = machine("""input int sensor; control int count = 0;
    state Root {
        pseudo state Again { enter { count = count + sensor; } }
        [*] -> Again;
        Again -> Again;
    }""")
    source = Spy((1,))
    runtime = SimulationRuntime(sm, input_source={"sensor": source})
    with pytest.raises(SimulationRuntimeDfsError):
        runtime.cycle()
    assert runtime.vars == {"count": 0}
    assert runtime.cycle_count == 0
    assert runtime.last_inputs is None
    assert runtime.history == []
    assert source.reads == [0]
    assert source.advances == []


def test_partial_advancement_violation_quarantines_every_source():
    class Broken(Spy):
        def cycle(self):
            raise RuntimeError("provider bug")

    sm = machine("input int first; input int second; state Root;")
    first, second = Spy((1,)), Broken((2,))
    runtime = SimulationRuntime(sm, input_source={"second": second, "first": first})
    with pytest.raises(SimulationRuntimeInputSourceError):
        runtime.cycle()
    assert first.advances == [0]
    assert second.advances == []
    assert runtime.cycle_count == 0
    assert runtime.history == []
    runtime.cycle()
    assert first.reads == second.reads == [0]
    assert first.advances == [0]


def test_parameter_and_persistent_overrides_skip_failing_defaults():
    sm = machine("""param int gain = 1 / 0; output int result = 1 / 0;
    state Root { state Ready; [*] -> Ready; }""")
    runtime = SimulationRuntime(sm, parameters={"gain": 2}, initial_vars={"result": 7})
    assert runtime.parameters == {"gain": 2}
    assert runtime.vars == {"result": 7}
    runtime.cycle()
    runtime.cycle()
    assert runtime.outputs == {"result": 7}
