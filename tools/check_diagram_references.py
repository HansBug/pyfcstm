"""Check that the diagram package's cross-references point at documented objects.

A reST role whose target is not registered renders as plain text rather than a
link, and Sphinx says nothing about it unless the build is run with ``-n``. The
diagram package accumulated thirty of them: exception classes referenced under
``pyfcstm.diagram.api`` while ``api_doc`` documents them under
``pyfcstm.diagram.engine``, the state machine referenced as
``pyfcstm.model.StateMachine`` while it is documented as
``pyfcstm.model.model.StateMachine``, and every entry of the package's own two
summary tables written as a bare class name under a module that documents
nothing. One of those names is not even importable, so a reader who followed
``Diagram.show``'s ``:raises:`` list got an ``AttributeError``.

The existing docstring gate does not catch any of this: it imports what the
``Example::`` blocks execute, which says nothing about whether a ``:class:``
target has an anchor. This one reads the ``api_doc`` tree for what autodoc
registers and compares the diagram package's references against it, without a
Sphinx build.

Only fully-qualified ``pyfcstm.*`` targets are checked, which is the shape that
went wrong here. Standard-library names are left alone: they never resolve in
this repository because intersphinx is not configured, and ``optional`` in a type
field is the convention CLAUDE.md sets out -- both are repository-wide and not
this package's to answer for.

A name written without its module is left alone too, and that is a real limit
rather than an oversight. Sphinx resolves those with more context than this can
reproduce: measured against a built page, ``:meth:`to_dict``` inside the
``Diagram`` docstring resolves through the class it sits in, and
``:raises DiagramUnavailableError:`` resolves to ``pyfcstm.diagram.engine`` --
a different module from the one being documented. But the same bare spelling in
a *module* docstring, which is what the package's two summary tables used, does
not resolve at all. Guessing at that from the outside would report references
that are in fact links, and a gate that cries wolf is worse than one with a
stated boundary. Those tables now name their modules, so they are covered by the
rule above.

Run ``make diagram_reference_targets_check``. Pass ``--check`` for the
self-check, which proves the scanner reports a reference it should.
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Iterable, List, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]

# The tree whose references are checked, and the documentation that registers
# the targets. Widening the first to all of `pyfcstm` means answering for the
# nineteen `pyfcstm.model.StateMachine` references elsewhere in it first.
SOURCES = ("pyfcstm/diagram", "pyfcstm/entry/diagram.py")
API_DOC = "docs/source/api_doc"

ROLE = re.compile(r":(?:class|exc|meth|func|data|mod|attr|obj):`~?([A-Za-z_][\w.]*)`")
RAISES = re.compile(r":raises\s+~?([A-Za-z_][\w.]*)\s*:")

CURRENTMODULE = re.compile(r"^\.\.\s+currentmodule::\s*([\w.]+)\s*$", re.M)
AUTOMODULE = re.compile(r"^\.\.\s+automodule::\s*([\w.]+)\s*$", re.M)
AUTOOBJECT = re.compile(
    r"^\.\.\s+auto(?:class|exception|function|data|method|attribute)::\s*([\w.]+)\s*$",
    re.M,
)
MEMBERS = re.compile(r"^\s+:members:\s*(.*)$", re.M)


def documented_names(api_doc: Path) -> Set[str]:
    """
    Collect every Python object path the API documentation registers.

    Each file sets a ``currentmodule`` and then documents names under it, so a
    class written ``.. autoclass:: Diagram`` in a file whose current module is
    ``pyfcstm.diagram.api`` is registered as ``pyfcstm.diagram.api.Diagram`` and
    at no other path -- which is the whole point of this check.

    :param api_doc: The ``api_doc`` directory.
    :type api_doc: pathlib.Path
    :return: Registered dotted paths.
    :rtype: set[str]
    """
    names = set()
    for page in sorted(api_doc.rglob("*.rst")):
        text = page.read_text(encoding="utf-8")
        current = CURRENTMODULE.search(text)
        module = current.group(1) if current else None
        for match in AUTOMODULE.finditer(text):
            names.add(match.group(1))
            module = module or match.group(1)
        if module is None:
            continue
        for match in AUTOOBJECT.finditer(text):
            name = match.group(1)
            qualified = name if "." in name else "%s.%s" % (module, name)
            names.add(qualified)
            # `:members:` follows the directive it belongs to, so the nearest
            # one after this position is this object's.
            rest = text[match.end() :]
            members = MEMBERS.search(rest)
            if members is None:
                continue
            head = rest[: members.start()]
            if head.strip() and not head.strip().startswith(":"):
                continue
            for member in members.group(1).split(","):
                member = member.strip()
                if member:
                    names.add("%s.%s" % (qualified, member))
    return names


def referenced_targets(path: Path) -> List[Tuple[int, str]]:
    """
    Find every target the docstrings of one module refer to.

    Bare names are returned as written; :func:`dead_references` is what decides
    whether one of them is ours, because that needs the registry.

    :param path: A Python file.
    :type path: pathlib.Path
    :return: Pairs of line number and dotted target.
    :rtype: list[tuple[int, str]]
    """
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    found = []
    holders = [tree] + [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    ]
    for holder in holders:
        doc = ast.get_docstring(holder, clean=False)
        if not doc:
            continue
        # The docstring's own first line, so a report points near the reference
        # rather than at the top of the file.
        base = holder.body[0].lineno
        for pattern in (ROLE, RAISES):
            for match in pattern.finditer(doc):
                line = base + doc[: match.start()].count("\n")
                found.append((line, match.group(1)))
    return found


def dead_references(root: Path) -> List[Tuple[Path, int, str]]:
    """
    Report references whose target the documentation does not register.

    :param root: The repository root.
    :type root: pathlib.Path
    :return: File, line and target for each dead reference.
    :rtype: list[tuple[pathlib.Path, int, str]]
    """
    names = documented_names(root / API_DOC)
    if not names:
        raise SystemExit("no documented names found under %s" % API_DOC)
    dead = []
    for entry in SOURCES:
        location = root / entry
        files = sorted(location.rglob("*.py")) if location.is_dir() else [location]
        for path in files:
            for line, target in referenced_targets(path):
                if not target.startswith("pyfcstm."):
                    continue
                if target not in names:
                    dead.append((path.relative_to(root), line, target))
    return dead


def _self_check() -> None:
    """
    Prove the scanner reports what it is for, on inputs written for it.

    :return: ``None``.
    :rtype: None
    """
    import tempfile

    with tempfile.TemporaryDirectory() as raw:
        fake = Path(raw)
        doc = fake / API_DOC
        doc.mkdir(parents=True)
        (doc / "api.rst").write_text(
            ".. currentmodule:: pyfcstm.diagram.api\n\n"
            ".. automodule:: pyfcstm.diagram.api\n\n"
            ".. autoclass:: Diagram\n    :members: show,save\n",
            encoding="utf-8",
        )
        package = fake / "pyfcstm" / "diagram"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text(
            '"""\n'
            "Live: :class:`pyfcstm.diagram.api.Diagram`.\n"
            "Live member: :meth:`pyfcstm.diagram.api.Diagram.show`.\n"
            "Live short form: :class:`~pyfcstm.diagram.api.Diagram`.\n"
            "Dead module: :class:`pyfcstm.diagram.Diagram`.\n"
            "Dead member: :meth:`pyfcstm.diagram.api.Diagram.to_pdf`.\n"
            "Not judged: :class:`Diagram` and :exc:`ValueError`, both bare.\n"
            "Outside: :class:`os.PathLike`.\n"
            '\n:raises pyfcstm.diagram.api.DiagramAssetError: dead in a field.\n"""\n',
            encoding="utf-8",
        )
        (fake / "pyfcstm" / "entry").mkdir(parents=True)
        (fake / "pyfcstm" / "entry" / "diagram.py").write_text("", encoding="utf-8")

        names = documented_names(doc)
        expected = {
            "pyfcstm.diagram.api",
            "pyfcstm.diagram.api.Diagram",
            "pyfcstm.diagram.api.Diagram.show",
            "pyfcstm.diagram.api.Diagram.save",
        }
        if names != expected:
            raise SystemExit("registered names wrong: %s" % sorted(names))

        found = sorted(target for _, _, target in dead_references(fake))
        wanted = [
            "pyfcstm.diagram.Diagram",
            "pyfcstm.diagram.api.Diagram.to_pdf",
            "pyfcstm.diagram.api.DiagramAssetError",
        ]
        if found != wanted:
            raise SystemExit("dead references wrong: %s" % found)
        # The three live spellings, `~` included, are not reported, or the gate
        # would be noise; neither are the two bare names, which it does not judge.
    print("diagram reference targets: self-check passed")


def main(argv: Iterable[str]) -> int:
    """
    Report dead references, or run the self-check.

    :param argv: Command-line arguments without the program name.
    :type argv: collections.abc.Iterable[str]
    :return: Process exit status.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--check",
        action="store_true",
        help="run the scanner's own self-check and exit",
    )
    arguments = parser.parse_args(list(argv))
    if arguments.check:
        _self_check()
        return 0
    dead = dead_references(ROOT)
    if dead:
        for path, line, target in dead:
            sys.stderr.write(
                "%s:%d: %s is not registered by any api_doc page\n"
                % (path, line, target)
            )
        sys.stderr.write(
            "%d reference(s) render as plain text. Point them at the module whose "
            "api_doc page documents the object.\n" % len(dead)
        )
        return 1
    judged = sum(
        1
        for entry in SOURCES
        for path in (
            sorted((ROOT / entry).rglob("*.py"))
            if (ROOT / entry).is_dir()
            else [ROOT / entry]
        )
        for _, target in referenced_targets(path)
        if target.startswith("pyfcstm.")
    )
    print(
        "diagram reference targets: %d qualified pyfcstm reference(s) all registered"
        % judged
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
