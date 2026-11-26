"""Print compact, deterministic cycle traces for the region explanation page.

The helper only wraps the public simulator: it builds a ``SimulationRuntime``
from a ``.fcstm`` file, drives it with the given cycles and prints what
``CycleResult.trace`` and ``runtime.configuration`` report.  Paths are printed
without the name of the root state to keep the lines short.
"""

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

_COLLECTIONS = {
    "on_enters": "enter action",
    "on_durings": "during",
    "on_exits": "exit action",
    "on_during_aspects": "aspect",
}


def load(path):
    """Load a model from a text file next to the script."""
    with open(path, encoding="utf-8") as stream:
        return load_state_machine_from_text(stream.read())


def _short(path):
    return ".".join(path[1:]) if len(path) > 1 else path[0]


def _show_vars(values, names=None):
    names = sorted(values) if names is None else names
    return " ".join("%s=%s" % (name, values[name]) for name in names)


def _show_inputs(inputs):
    return " ".join("%s=%s" % item for item in sorted(inputs.items())) or "-"


def _aspect_kinds(model):
    """Map ``scope path`` to the ``before`` / ``after`` kind of each aspect."""
    kinds = {}
    for state in model.walk_states():
        kinds[".".join(state.path)] = [a.aspect for a in state.on_during_aspects]
        kinds[".".join(state.path) + "#during"] = [a.aspect for a in state.on_durings]
        for region in state.regions.values():
            kinds[".".join(region.path)] = [a.aspect for a in region.on_during_aspects]
    return kinds


def _entry_line(entry, kinds):
    if entry.kind == "state_enter":
        return "enter  " + _short(entry.state_path)
    if entry.kind == "state_exit":
        return "exit   " + _short(entry.state_path)
    if entry.kind == "transition":
        label = entry.transition_label.split("::")[-1].replace("INIT_STATE", "[*]")
        return "take   %s  %s" % (_short(entry.state_path), label)
    scope, kind, index = entry.action_path.split("::")
    if kind == "on_during_aspects":
        return "aspect %s  %s" % (_short(tuple(scope.split("."))), kinds[scope][int(index)])
    label = _COLLECTIONS.get(kind, kind)
    if kind == "on_durings" and kinds[scope + "#during"][int(index)]:
        label += " " + kinds[scope + "#during"][int(index)]
    return "do     %s  %s" % (_short(entry.state_path), label)


def make_runtime(path, **kwargs):
    """Build a runtime whose omitted inputs read as 0 unless a cycle gives them."""
    model = load(path)
    zero = {name: 0 for name in model.inputs}
    return SimulationRuntime(model, input_source=zero, **kwargs)


def play(runtime, steps, trace=False, show=None, header=None):
    """Run ``steps`` and print one block per cycle.

    ``steps`` is a list of ``(events, inputs)`` pairs.  With ``trace`` the
    committed observations are listed in execution order; a variable that
    changes between two observations is printed after the line that changed it.
    ``show`` restricts the printed variables.
    """
    kinds = _aspect_kinds(runtime.state_machine)
    if header:
        print(header)
    for events, inputs in steps:
        before = dict(runtime.vars)
        result = runtime.cycle(events, inputs=inputs, trace=trace)
        label = "cycle %d" % runtime.cycle_count
        label += "  events: %s" % (", ".join(result.input_events) or "-")
        label += "  inputs: %s" % _show_inputs(inputs)
        if result.delta:
            label += "  (Delta)"
        print(label)
        if trace:
            seen = before
            for entry in result.trace:
                line = "  " + _entry_line(entry, kinds)
                changed = [
                    "%s %s->%s" % (name, seen[name], entry.vars[name])
                    for name in sorted(entry.vars)
                    if seen.get(name) != entry.vars[name]
                    and (show is None or name in show)
                ]
                if changed:
                    line += "   [" + ", ".join(changed) + "]"
                seen = dict(entry.vars)
                print(line)
        print("  => %s   %s" % (runtime.configuration, _show_vars(runtime.vars, show)))


def table(runtime, steps, show=None, delta_mark=True):
    """Run ``steps`` and print one aligned row per cycle.

    The columns are the cycle number, the events, the inputs, the resting
    configuration and the variables (restricted by ``show``).  A cycle that
    ended as a Delta is marked ``Delta`` in the last column.
    """
    rows = [("cycle", "events", "inputs", "configuration", "variables")]
    for events, inputs in steps:
        result = runtime.cycle(events, inputs=inputs)
        variables = _show_vars(runtime.vars, show)
        if result.delta and delta_mark:
            variables += "   (Delta)"
        rows.append(
            (
                str(runtime.cycle_count),
                ", ".join(e.split(".", 1)[1] for e in result.input_events) or "-",
                _show_inputs(inputs),
                str(runtime.configuration),
                variables,
            )
        )
    widths = [max(len(row[i]) for row in rows) for i in range(len(rows[0]) - 1)]
    for row in rows:
        cells = [row[i].ljust(widths[i]) for i in range(len(widths))]
        print("  ".join(cells + [row[-1]]).rstrip())
