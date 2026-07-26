"""Check deterministic DiagramData across the three ways a model is built.

The umbrella contract requires parsed, imported and programmatic models with
the same semantics to expose the same portable data, because the browser and
any later headless host key off those IDs and that ordering.
"""

import json
import tempfile
import weakref
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyfcstm.dsl.node import INIT_STATE  # noqa: E402
from pyfcstm.model import (  # noqa: E402
    Event,
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
    """Assemble the COMPACT_SOURCE machine through the model API, not the DSL."""
    # ``:: Go`` is a local event reference rather than a declared ``event Go;``,
    # so the programmatic model has to reproduce that origin exactly.
    go = Event(
        name="Go", state_path=("Root", "Idle"), declared=False, origins=["local"]
    )
    idle = State(
        name="Idle",
        path=("Root", "Idle"),
        substates={},
        events={"Go": go},
    )
    root = State(
        name="Root",
        path=("Root",),
        substates={
            "Idle": idle,
            "Running": State(name="Running", path=("Root", "Running"), substates={}),
        },
        transitions=[
            # Both transitions are declared inside ``state Root { ... }``, so the
            # composite owns them; the child states carry none of their own.
            Transition(
                from_state=INIT_STATE,
                to_state="Idle",
                event=None,
                guard=None,
                effects=[],
            ),
            Transition(
                from_state="Idle",
                to_state="Running",
                event=go,
                guard=None,
                effects=[],
                event_scope="local",
            ),
        ],
    )
    # Only the real root has no parent; without these links every state would
    # report itself as the root and the comparison would drift for that reason
    # alone rather than for a genuine data difference.
    for child in root.substates.values():
        child.parent_ref = weakref.ref(root)
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
    _require_equal(
        compact.diagram().to_json(),
        programmatic.diagram().to_json(),
        "programmatic and parsed models produced different DiagramData",
    )
    print("diagram data parity: parsed, imported and programmatic models passed")


if __name__ == "__main__":
    main()
