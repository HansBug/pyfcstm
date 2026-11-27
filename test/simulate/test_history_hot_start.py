"""Hot start of machines whose history was lowered into hidden variables."""

import pytest

from pyfcstm.entry.simulate.commands import CommandProcessor
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

from test.model.test_history_lowering import EVENTS, WASHER

USER_VARS = {
    "program_entries": 0,
    "fill_entries": 0,
    "agitate_entries": 0,
    "wash_initials": 0,
    # The hidden variable of the forced ``!Program -> Paused`` of the model: an
    # ordinary variable, so a hot start supplies it like the others.
    "__forced_0": 0,
}


def _hot_start(machine, **history):
    return SimulationRuntime(
        machine,
        initial_state="Washer.Paused",
        initial_vars={**USER_VARS, **machine.history_variables(), **history},
    )


@pytest.mark.unittest
class TestHistoryHotStart:
    @pytest.mark.parametrize("leaf", ["Idle", "Wash.Fill", "Wash.Agitate"])
    def test_every_recordable_leaf_can_be_restored(self, leaf):
        machine = load_state_machine_from_text(WASHER)
        values = machine.history_variables({"Washer.Program": leaf})
        runtime = _hot_start(machine, **values)
        runtime.cycle()
        runtime.cycle([EVENTS["Deep"]])
        assert ".".join(runtime.current_state.path) == "Washer.Program." + leaf

    @pytest.mark.parametrize(
        "name,value",
        [
            ("__hist_goto", 5),
            ("__hist_Program", -1),
            ("__hist_Program", 1),
            ("__hist_Program", 2),
            ("__hist_Program", 99),
        ],
    )
    def test_a_value_no_execution_holds_is_taken_like_any_other(self, name, value):
        """The hidden variables are ordinary variables: nothing is refused, and the
        machine does exactly what the model loaded from its exported text does."""
        machine = load_state_machine_from_text(WASHER)
        expansion = load_state_machine_from_text(str(machine.to_ast_node()))
        given = {**USER_VARS, **machine.history_variables(), name: value}
        outcomes = []
        for model in (machine, expansion):
            runtime = SimulationRuntime(
                model, initial_state="Washer.Paused", initial_vars=dict(given)
            )
            rows = []
            for events in ([], [EVENTS["Deep"]], [], []):
                runtime.cycle(events)
                rows.append((runtime.current_state.path, sorted(runtime.vars.items())))
            outcomes.append(rows)
        assert outcomes[0] == outcomes[1]

    def test_the_history_variables_of_a_model_without_history_are_plain_variables(self):
        machine = load_state_machine_from_text(
            "def int __hist_goto = 3; state R { state A; [*] -> A; }"
        )
        runtime = SimulationRuntime(machine, initial_state="R.A", initial_vars={"__hist_goto": 7})
        assert runtime.vars["__hist_goto"] == 7


@pytest.mark.unittest
class TestHistoryInitCommand:
    def _processor(self):
        machine = load_state_machine_from_text(WASHER)
        runtime = SimulationRuntime(machine)
        return machine, CommandProcessor(runtime, state_machine=machine, use_color=False)

    def test_init_accepts_history_variables_and_resumes(self):
        machine, processor = self._processor()
        record = machine.history_owners[0].record_value(("Wash", "Agitate"))
        user = " ".join("%s=0" % name for name in USER_VARS)
        result = processor.process(
            "init Washer.Paused %s __hist_goto=0 __hist_Program=%d" % (user, record)
        )
        assert "Error" not in result.output, result.output
        processor.process("cycle")
        processor.process("cycle %s" % EVENTS["Deep"])
        assert processor.runtime.current_state.path == ("Washer", "Program", "Wash", "Agitate")

    def test_init_takes_any_value_of_a_history_variable(self):
        _, processor = self._processor()
        user = " ".join("%s=0" % name for name in USER_VARS)
        result = processor.process("init Washer.Paused %s __hist_goto=0 __hist_Program=2" % user)
        assert result.exit_code == 0, result.output
        assert processor.runtime.vars["__hist_Program"] == 2
