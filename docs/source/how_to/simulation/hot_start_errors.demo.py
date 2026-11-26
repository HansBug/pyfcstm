from pyfcstm.model import load_state_machine_from_file
from pyfcstm.simulate import SequenceInput, SimulationRuntime

model = load_state_machine_from_file("hot_controller.fcstm")
full = {"permit": 1, "motor": 1, "__forced_0": 0}
cases = [
    ("hidden variable left out", "Controller.Running{Safety: Watching, Motion: On}",
     {"permit": 1, "motor": 1}),
    ("every region done", "Controller.Running{Safety: [done], Motion: [done]}", full),
    ("unknown state", "Controller.Running{Safety: Nope, Motion: On}", full),
]
for label, initial_state, variables in cases:
    try:
        SimulationRuntime(
            model,
            initial_state=initial_state,
            initial_vars=variables,
            input_source={"fault": SequenceInput([0]), "requested": SequenceInput([1])},
        )
    except ValueError as error:
        # ValueError: the start position or the variable set is refused at construction.
        print(f"{label}: ValueError: {error}")
