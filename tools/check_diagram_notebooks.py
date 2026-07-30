"""
Check the notebook representation survives execution and a save/reopen cycle.

``Diagram._repr_svg_`` is called by the front end while a cell renders, so its
contract has two halves that unit tests cannot both reach: the value has to be
stored in the notebook document, and it has to still be there after the document
is written and read back.  A notebook whose image lives only in the running
kernel looks perfect until someone reopens the file.

What this checks, in the order the failures matter:

* **The output is stored at all.** A repr hook that raises produces a traceback
  output instead, and a hook returning ``None`` produces a plain text repr.  Both
  leave a notebook that executed without error and shows no diagram.
* **It survives the round trip.** ``nbformat`` writes and reads the document, so
  an output that cannot be serialised is caught here rather than by a user.
* **It is self-contained.** No ``<script``, no remote URL, and no absolute path
  from the machine that produced it -- a notebook is shared, and a path from
  someone else's home directory is both broken and a disclosure.

The front-end rendering itself is out of scope: that needs a browser driving
JupyterLab or the classic notebook, which belongs with the installed-artifact
matrix rather than here.  This command covers the document, which is what gets
committed and shared.

Run it directly, or through ``make diagram_notebooks_check``::

    $ python tools/check_diagram_notebooks.py
    diagram notebooks: representation stored, round-tripped and self-contained
"""

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any, List

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CELL_SOURCE = "\n".join(
    (
        "from pyfcstm.model import load_state_machine_from_text",
        "model = load_state_machine_from_text(",
        "    'state Root { state A; state B; [*] -> A; A -> B :: Go; }'",
        ")",
        "model.diagram()",
    )
)


def build_notebook() -> Any:
    """
    Build a one-cell notebook that displays a diagram.

    :return: An unexecuted notebook document.
    :rtype: nbformat.NotebookNode
    """
    import nbformat

    notebook = nbformat.v4.new_notebook()
    notebook.cells = [nbformat.v4.new_code_cell(CELL_SOURCE)]
    return notebook


def execute(notebook: Any, timeout: int) -> Any:
    """
    Run the notebook in a real kernel.

    :param notebook: Notebook document to execute.
    :type notebook: nbformat.NotebookNode
    :param timeout: Per-cell timeout in seconds.
    :type timeout: int
    :return: The executed notebook.
    :rtype: nbformat.NotebookNode
    :raises SystemExit: If the notebook tooling is not installed.
    """
    try:
        from nbclient import NotebookClient
    except ImportError:
        raise SystemExit(
            "nbclient is not installed, so the notebook representation cannot be "
            "checked here; install it or run this where the notebook tooling is"
        )
    client = NotebookClient(
        notebook, timeout=timeout, kernel_name="python3", resources={}
    )
    client.execute(cwd=str(ROOT))
    return notebook


def collect_svg(notebook: Any) -> List[str]:
    """
    Collect every stored SVG representation, reporting other outcomes.

    :param notebook: Executed notebook document.
    :type notebook: nbformat.NotebookNode
    :return: The stored SVG payloads.
    :rtype: list[str]
    :raises SystemExit: If a cell errored, or stored no SVG.
    """
    found = []
    for cell in notebook.cells:
        for output in cell.get("outputs", []):
            kind = output.get("output_type")
            if kind == "error":
                raise SystemExit(
                    "the notebook cell raised %s: %s"
                    % (output.get("ename"), output.get("evalue"))
                )
            data = output.get("data") or {}
            if "image/svg+xml" in data:
                payload = data["image/svg+xml"]
                found.append(
                    "".join(payload) if isinstance(payload, list) else str(payload)
                )
    if not found:
        raise SystemExit(
            "the notebook stored no SVG representation; a repr hook that returns "
            "None or raises leaves a notebook that executed cleanly and shows no "
            "diagram"
        )
    return found


def check_payload(svg: str) -> None:
    """
    Require one stored representation to be a self-contained SVG.

    :param svg: Stored SVG payload.
    :type svg: str
    :return: ``None``.
    :rtype: None
    :raises SystemExit: If the payload is empty, not SVG, or not self-contained.
    """
    problems = []
    if not svg.strip():
        problems.append("the stored representation is empty")
    if "<svg" not in svg:
        problems.append("the stored representation is not an SVG document")
    if "<script" in svg:
        problems.append("the stored representation carries a script element")
    for scheme in ("http://", "https://"):
        # An `xmlns` value is a namespace name, not something a viewer fetches.
        for candidate in ('href="%s' % scheme, 'src="%s' % scheme, "url(%s" % scheme):
            if candidate in svg:
                problems.append("the stored representation references %s" % scheme)
                break
    if "<text" in svg or "font-family" in svg:
        problems.append(
            "the stored representation depends on fonts, so it renders differently "
            "wherever the notebook is opened"
        )
    for marker in (str(ROOT), str(Path.home())):
        if marker and marker in svg:
            problems.append(
                "the stored representation embeds an absolute path from the "
                "machine that produced it"
            )
            break
    if problems:
        raise SystemExit("notebook representation problems:\n  " + "\n  ".join(problems))


def round_trip(notebook: Any) -> Any:
    """
    Write the notebook out and read it back, as saving and reopening does.

    :param notebook: Executed notebook document.
    :type notebook: nbformat.NotebookNode
    :return: The notebook as read back from disk.
    :rtype: nbformat.NotebookNode
    """
    import nbformat

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "diagram.ipynb"
        nbformat.write(notebook, str(path))
        return nbformat.read(str(path), as_version=4)


def _self_check() -> None:
    """
    Prove the payload check rejects each shape it exists to catch.

    :return: ``None``.
    :rtype: None
    :raises SystemExit: If any bad payload is accepted, or a good one rejected.
    """
    check_payload('<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0"/></svg>')
    bad = {
        "empty": "",
        "not svg": "<html></html>",
        "script": '<svg><script>x</script></svg>',
        "remote reference": '<svg><image href="https://example.invalid/a.png"/></svg>',
        "font dependency": '<svg><text font-family="X">a</text></svg>',
        "absolute path": '<svg><desc>%s/machine.fcstm</desc></svg>' % ROOT,
    }
    for label, payload in bad.items():
        try:
            check_payload(payload)
        except SystemExit:
            continue
        raise SystemExit("the payload check accepted %s" % label)
    print("diagram notebooks: self-check passed")


def main(argv=None) -> int:
    """
    Execute the notebook check, or run this command's own self-check.

    :param argv: Command-line arguments, defaults to ``sys.argv[1:]``.
    :type argv: collections.abc.Sequence[str], optional
    :return: Process exit status.
    :rtype: int
    :raises SystemExit: If the representation is missing or not self-contained.
    """
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        "--check", action="store_true", help="run this command's own self-check"
    )
    parser.add_argument("--timeout", type=int, default=300)
    arguments = parser.parse_args(argv)
    if arguments.check:
        _self_check()
        return 0

    notebook = execute(build_notebook(), arguments.timeout)
    stored = collect_svg(notebook)
    for svg in stored:
        check_payload(svg)
    reopened = round_trip(notebook)
    reopened_stored = collect_svg(reopened)
    if reopened_stored != stored:
        raise SystemExit(
            "the stored representation changed across a save and reopen cycle"
        )
    for svg in reopened_stored:
        check_payload(svg)
    print(
        json.dumps(
            {
                "representations": len(stored),
                "bytes": [len(svg) for svg in stored],
                "roundTripped": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
