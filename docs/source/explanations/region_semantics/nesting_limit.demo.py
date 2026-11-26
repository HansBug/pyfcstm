from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeDfsError


def nested_model(depth):
    """A chain of ``depth`` owners, each inside a region of the previous one."""
    body = "region R { [*] -> Leaf; state Leaf; }"
    for index in reversed(range(depth)):
        body = "region R { [*] -> O%d; state O%d { %s } }" % (index, index, body)
    return "state Root { [*] -> P; state P { %s } }" % body


def first_cycle(depth):
    runtime = SimulationRuntime(load_state_machine_from_text(nested_model(depth)))
    runtime.cycle([])
    return runtime


depth = 1
while True:
    try:
        first_cycle(depth + 1)
    except SimulationRuntimeDfsError as error:
        message = str(error)
        break
    depth += 1
print("deepest chain that starts in one cycle: %d owners (P and %d inside it)" % (depth + 1, depth))
print("one more:", message)
