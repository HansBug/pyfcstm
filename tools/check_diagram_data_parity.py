"""Check deterministic DiagramData across the three ways a model is built.

The umbrella contract requires parsed, imported and programmatic models with
the same semantics to expose the same portable data, because the browser and
any later headless host key off those IDs and that ordering.
"""

import json
import tempfile
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyfcstm.model import (  # noqa: E402
    State,
    StateMachine,
    Transition,
    load_state_machine_from_file,
    load_state_machine_from_text,
)


COMPACT_SOURCE = (
    "state Root { state Idle; state Running; [*] -> Idle; Idle -> Running :: Go; }"
)
EXPANDED_SOURCE = """state Root {
    state Idle;
    state Running;
    [*] -> Idle;
    Idle -> Running :: Go;
}"""
MAIN_SOURCE = 'state Root { import "./child.fcstm" as Child; [*] -> Child; }'
CHILD_SOURCE = "state Child { state Waiting; [*] -> Waiting; }"
INLINE_SOURCE = (
    "state Root { state Child { state Waiting; [*] -> Waiting; } [*] -> Child; }"
)


def _imported_and_inline_data():
    """Build the same machine through an import and through inline nesting."""
    with tempfile.TemporaryDirectory(prefix="pyfcstm-diagram-parity-") as directory:
        base = Path(directory)
        (base / "child.fcstm").write_text(CHILD_SOURCE, encoding="utf-8")
        (base / "main.fcstm").write_text(MAIN_SOURCE, encoding="utf-8")
        imported = load_state_machine_from_file(base / "main.fcstm")
        imported_data = imported.diagram().to_dict()
    inline_data = load_state_machine_from_text(INLINE_SOURCE).diagram().to_dict()
    return imported_data, inline_data


def _programmatic_machine() -> StateMachine:
    """Assemble the compact machine through the model API instead of the DSL."""
    root = State(
        name="Root",
        path=("Root",),
        substates={
            "Idle": State(name="Idle", path=("Root", "Idle"), substates={}),
            "Running": State(name="Running", path=("Root", "Running"), substates={}),
        },
        transitions=[
            Transition(
                from_state="[*]", to_state="Idle", event=None, guard=None, effects=[]
            ),
            Transition(
                from_state="Idle",
                to_state="Running",
                event=None,
                guard=None,
                effects=[],
            ),
        ],
    )
    return StateMachine(defines={}, root_state=root)


def _require_equal(left, right, message: str) -> None:
    if left != right:
        raise SystemExit(message)


def main() -> None:
    compact = load_state_machine_from_text(COMPACT_SOURCE)
    expanded = load_state_machine_from_text(EXPANDED_SOURCE)
    _require_equal(
        compact.diagram().to_json(),
        expanded.diagram().to_json(),
        "equivalent parsed models produced different DiagramData",
    )

    imported_data, inline_data = _imported_and_inline_data()
    _require_equal(
        json.dumps(imported_data, sort_keys=True, ensure_ascii=False),
        json.dumps(inline_data, sort_keys=True, ensure_ascii=False),
        "imported and inline models produced different DiagramData",
    )

    programmatic = _programmatic_machine()
    parsed_states = _state_ids(compact.diagram().to_dict()["rootState"])
    programmatic_states = _state_ids(programmatic.diagram().to_dict()["rootState"])
    _require_equal(
        parsed_states,
        programmatic_states,
        "programmatic and parsed models produced different state IDs",
    )
    _require_equal(
        _transition_ids(compact.diagram().to_dict()["rootState"]),
        _transition_ids(programmatic.diagram().to_dict()["rootState"]),
        "programmatic and parsed models produced different transition IDs",
    )
    print("diagram data parity: parsed, imported and programmatic models passed")


def _state_ids(node):
    """Collect state IDs in document order."""
    collected = [node["id"]]
    for child in node["children"]:
        collected.extend(_state_ids(child))
    return collected


def _transition_ids(node):
    """Collect transition IDs in document order."""
    collected = [transition["id"] for transition in node["transitions"]]
    for child in node["children"]:
        collected.extend(_transition_ids(child))
    return collected


if __name__ == "__main__":
    main()
