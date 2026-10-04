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

    def test_a_pending_restore_is_rejected(self):
        machine = load_state_machine_from_text(WASHER)
        with pytest.raises(ValueError, match=r"__hist_goto.*must be 0"):
            _hot_start(machine, __hist_goto=5)

    @pytest.mark.parametrize("value", [-1, 1, 2, 99])
    def test_a_record_that_names_no_stoppable_leaf_is_rejected(self, value):
        machine = load_state_machine_from_text(WASHER)
        (owner,) = machine.history_owners
        assert owner.decode(value) is None
        with pytest.raises(ValueError) as info:
            _hot_start(machine, __hist_Program=value)
        message = str(info.value)
        assert "__hist_Program" in message and "Washer.Program" in message
        for leaf in ("Idle", "Wash.Fill", "Wash.Agitate"):
            assert leaf in message
        assert "history_variables" in message

    def test_initial_values_without_a_hot_start_are_checked_too(self):
        machine = load_state_machine_from_text(WASHER)
        with pytest.raises(ValueError, match="__hist_goto"):
            SimulationRuntime(machine, initial_vars={"__hist_goto": 3})

    def test_models_without_history_ignore_the_check(self):
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

    def test_init_reports_an_invalid_record_readably(self):
        _, processor = self._processor()
        user = " ".join("%s=0" % name for name in USER_VARS)
        before = processor.runtime
        result = processor.process("init Washer.Paused %s __hist_goto=0 __hist_Program=2" % user)
        assert result.exit_code == 1
        assert result.output.startswith("Initialization failed:")
        assert "7 (Wash.Agitate)" in result.output
        assert processor.runtime is before
