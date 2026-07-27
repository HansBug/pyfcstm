"""Check the public Diagram snapshot and serialization contract."""

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from diagram_contract_support import sample_diagram  # noqa: E402


def _keys_anywhere(value: object) -> set:
    """
    Collect every mapping key reachable from a portable value.

    :param value: A portable diagram value.
    :type value: object
    :return: Every key name that appears at any depth.
    :rtype: set
    """
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            found.add(key)
            found |= _keys_anywhere(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            found |= _keys_anywhere(item)
    return found


def _json_from_subprocess(seed: str) -> str:
    """
    Serialize the sample diagram in a fresh interpreter.

    Calling ``to_json()`` twice on one frozen snapshot in one process compares a
    pure function of an immutable value against itself and cannot fail. The
    property worth holding is that two independent runs, with different hash
    seeds, produce the same bytes.

    :param seed: Value for ``PYTHONHASHSEED`` in the child process.
    :type seed: str
    :return: The child's serialized diagram.
    :rtype: str
    """
    environment = dict(os.environ, PYTHONHASHSEED=seed)
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, %r); sys.path.insert(0, %r)\n"
            "from diagram_contract_support import sample_diagram\n"
            "sys.stdout.write(sample_diagram().to_json())"
            % (str(ROOT / "tools"), str(ROOT)),
        ],
        capture_output=True,
        text=True,
        check=True,
        env=environment,
        cwd=str(ROOT),
    )
    return completed.stdout


def main() -> None:
    diagram = sample_diagram()
    if diagram.to_json() != _json_from_subprocess("0"):
        raise SystemExit("Diagram JSON differs from a fresh interpreter")
    if _json_from_subprocess("0") != _json_from_subprocess("12345"):
        raise SystemExit("Diagram JSON depends on the interpreter hash seed")
    # Key names, not a repr substring scan: a state named "Range" or a display
    # name containing "range" used to trip this check for no reason, and a key
    # nested inside a list of dicts could equally have slipped past a shallow
    # membership test.
    editor_only = {"filePath", "range", "sourcePath", "sourceRange"} & _keys_anywhere(
        json.loads(diagram.to_json())
    )
    if editor_only:
        raise SystemExit(
            "public DiagramData contains editor-only metadata: %s"
            % ", ".join(sorted(editor_only))
        )

    model = diagram.model
    model.root_state.name = "Changed"
    if diagram.to_dict()["rootState"]["name"] != "Root":
        raise SystemExit("Diagram snapshot changed after model mutation")
    if diagram.with_options(mode="dark").to_dict()["rootState"]["name"] != "Root":
        raise SystemExit("derived Diagram snapshot reread the mutable model")
    print("diagram contract: snapshot and portable data passed")


if __name__ == "__main__":
    main()
