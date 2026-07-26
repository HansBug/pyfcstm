"""Check the public Diagram snapshot and serialization contract."""

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from diagram_contract_support import sample_diagram  # noqa: E402


def main() -> None:
    diagram = sample_diagram()
    first = diagram.to_json()
    second = diagram.to_json()
    if first != second:
        raise SystemExit("Diagram JSON is not deterministic")
    value = diagram.data.value
    if "filePath" in value or "range" in repr(value):
        raise SystemExit("public DiagramData contains editor-only metadata")

    model = diagram.model
    model.root_state.name = "Changed"
    if diagram.to_dict()["rootState"]["name"] != "Root":
        raise SystemExit("Diagram snapshot changed after model mutation")
    if diagram.with_options(mode="dark").to_dict()["rootState"]["name"] != "Root":
        raise SystemExit("derived Diagram snapshot reread the mutable model")
    print("diagram contract: snapshot and portable data passed")


if __name__ == "__main__":
    main()
