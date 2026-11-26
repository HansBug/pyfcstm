from pyfcstm.model import load_state_machine_from_text
from pyfcstm.dsl.error import GrammarParseError
from pyfcstm.utils.validate import ModelValidationError


def load(path):
    with open(path, encoding="utf-8") as stream:
        return load_state_machine_from_text(stream.read())


model = load("region_namespace.fcstm")
print("states (walk_states):")
for state in model.walk_states():
    print("  " + ".".join(state.path))
print("events:")
for state in model.walk_states():
    for event in state.events.values():
        print("  " + event.path_name)
for region_state in model.walk_states():
    for name, region in region_state.regions.items():
        print("region %s of %s has %d transitions" % (name, ".".join(region_state.path), len(region.transitions)))

print()
print("history on an owner whose subtree has regions")
try:
    load_state_machine_from_text(
        "state Root { [*] -> H; state H { [*] -> A; [H] -> A; state A { region R { [*] -> X; state X; } } state B; A -> B :: Go; }"
        " state Out; H -> Out :: Leave; Out -> H.[H] :: Back; }"
    )
except ModelValidationError as error:
    print("ModelValidationError:", str(error).splitlines()[0])
