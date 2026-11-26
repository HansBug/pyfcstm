from pyfcstm.model import Configuration, load_state_machine_from_file
from pyfcstm.simulate import SequenceInput, SimulationRuntime

model = load_state_machine_from_file("hot_controller.fcstm")
variables = {"permit": 1, "motor": 1, "__forced_0": 0}
motion_on = model.root_state.substates["Running"].regions["Motion"].substates["On"]
forms = {
    "configuration text": "Controller.Running{Safety: Watching, Motion: On}",
    "Configuration object": Configuration.parse(
        model, "Controller.Running{Safety: Watching, Motion: On}"
    ),
    "dotted path": "Controller.Running.Motion.On",
    "tuple path": ("Controller", "Running", "Motion", "On"),
    "State object": motion_on,
    "owner only": "Controller.Running",
}
for label, initial_state in forms.items():
    runtime = SimulationRuntime(
        model,
        initial_state=initial_state,
        initial_vars=variables,
        input_source={"fault": SequenceInput([0]), "requested": SequenceInput([1])},
    )
    before = runtime.configuration
    runtime.cycle()
    print(f"{label}:")
    print(f"  at start     {before}")
    print(f"  after cycle  {runtime.configuration}")
