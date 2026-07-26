"""Check deterministic DiagramData for equivalent source formatting."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pyfcstm.model import load_state_machine_from_text  # noqa: E402


def main() -> None:
    compact = load_state_machine_from_text(
        "state Root { state Idle; state Running; [*] -> Idle; Idle -> Running :: Go; }"
    )
    expanded = load_state_machine_from_text(
        """state Root {
            state Idle;
            state Running;
            [*] -> Idle;
            Idle -> Running :: Go;
        }"""
    )
    if compact.diagram().to_json() != expanded.diagram().to_json():
        raise SystemExit("equivalent models produced different DiagramData")
    print("diagram data parity: equivalent models passed")


if __name__ == "__main__":
    main()
