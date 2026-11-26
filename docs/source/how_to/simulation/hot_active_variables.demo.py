from pyfcstm.model import Configuration, load_state_machine_from_file
from pyfcstm.simulate import SequenceInput, SimulationRuntime

model = load_state_machine_from_file("hot_watch.fcstm")
config = Configuration.parse(
    model, "Plant{Earlier: Waiting, Trigger: Fired, Later: Saw}"
)
hidden = model.active_variables(config)
print("queries:", [(".".join(q.state_path), q.variable_name) for q in model.active_queries])
print("hidden variables for this position:", hidden)

runtime = SimulationRuntime(
    model,
    initial_state=config,
    initial_vars=hidden,
    input_source={"go": SequenceInput([1])},
)
runtime.cycle()
print("after one cycle:", runtime.configuration)
print("runtime.vars:", dict(runtime.vars))
