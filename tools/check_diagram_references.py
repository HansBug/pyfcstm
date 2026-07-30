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

Fully-qualified ``pyfcstm.*`` targets are checked wherever they appear -- inline
roles, ``:raises:`` and the body of ``:rtype:`` / ``:type:`` / ``:vartype:``, which
Sphinx renders through ``bodyrolename='class'`` and are therefore references like any
other. Field bodies include their continuation lines, because a type wrapped after
``or`` is ordinary reST and reading one line let the second target through.

Names written *without* their module are not judged, and that boundary is the result
of trying. Judging them needs to know which candidates Sphinx will try, which depends
on the enclosing class, on the ``refspecific`` flag that information fields carry,
and -- for a bare member -- on whether an intersphinx inventory could resolve it
elsewhere. Attempts at that reported live links as dead, and the guard meant to
protect the last of them leaked four times: a whole-file substring matched a comment
saying intersphinx was *not* configured, then any string constant did, then a
statement's own inline comment did, and on Python 3.7 the node class it looked for is
not the one a string literal produces. Each iteration was a new way to be wrong about
something this checker does not need to know, so the bare rules are gone and the
assumption and the guard went with them.

What catches a misspelled bare member instead is Sphinx itself: a build with ``-n``
reports every unresolved reference, bare ones included. This checker exists for the
class that build does *not* make obvious while ``-n`` is off -- a fully-qualified
target pointed at the wrong module, which renders as plain text without a word of
complaint, and which is what thirty references in this package were doing.

The registry over-approximates in one way worth knowing: every name listed in a
``:members:`` option counts as registered, while autodoc emits no anchor for a member
that has no docstring -- a bare dataclass field, for instance. Checked against a built
``objects.inv``, 1876 of the names collected here do not exist as anchors, 14 of them
in this package's own modules -- all dataclass fields and ``__post_init__`` -- and the
reverse, a real object the registry does not know about, is zero. So the error only ever costs a report, never invents one, and no live
reference is masked by it today.

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
# `:rtype:`, `:type:` and `:vartype:` bodies are cross-references too: Sphinx renders
# them through `bodyrolename='class'`, so `:rtype: pyfcstm.diagram.api.Diagram` is a
# link in the built page and the same line pointed at a module that does not document
# the class is plain text. Leaving these out meant the one `:rtype:` this gate arrived
# with could regress in silence.
# The name after `:type` may carry escaped stars -- `:type \*args:` and
# `:type \*\*kwargs:` are ordinary reST for a variadic signature -- and a name
# pattern that stopped at `[\w.]` skipped the whole field, continuation lines and all.
FIELD = re.compile(r"^(\s*):(?:rtype|type|vartype)\s*(?:\\?\*)*[\w.]*:")
QUALIFIED = re.compile(r"\bpyfcstm\.[A-Za-z_][\w.]*")

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


def module_of(path: Path, root: Path) -> str:
    """
    Return the dotted module a source file is imported as.

    :param path: A Python file inside the repository.
    :type path: pathlib.Path
    :param root: The repository root.
    :type root: pathlib.Path
    :return: The dotted module path.
    :rtype: str
    """
    parts = list(path.relative_to(root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _field_bodies(doc: str) -> List[Tuple[int, str]]:
    """
    Return one entry per line of each type field's body.

    A reST field body runs on for as long as the following lines are indented past
    the field marker, so ``:rtype: A or\n    B`` names two things.  Reading only the
    marker's own line judged ``A`` and let ``B`` through, which is the same
    line-anchored mistake that has bitten this branch twice before.

    :param doc: A docstring.
    :type doc: str
    :return: Pairs of line offset within the docstring and that line's body text, one
        entry per line of the body, so a target on a continuation line is reported
        against the line it is on.
    :rtype: list[tuple[int, str]]
    """
    lines = doc.split("\n")
    bodies = []
    index = 0
    while index < len(lines):
        match = FIELD.match(lines[index])
        if match is None:
            index += 1
            continue
        indent = len(match.group(1))
        start = index
        collected = [lines[index][match.end() :]]
        index += 1
        offsets = [start]
        while index < len(lines):
            following = lines[index]
            if not following.strip():
                # A blank line does not end a field body; what ends it is the next
                # line that is not indented past the marker. `docutils` keeps a
                # second paragraph inside the same `field_body`.
                ahead = index + 1
                while ahead < len(lines) and not lines[ahead].strip():
                    ahead += 1
                if ahead >= len(lines):
                    break
                deeper = len(lines[ahead]) - len(lines[ahead].lstrip()) > indent
                if not deeper:
                    break
                index = ahead
                continue
            if len(following) - len(following.lstrip()) <= indent:
                break
            collected.append(following)
            offsets.append(index)
            index += 1
        for offset, text in zip(offsets, collected):
            bodies.append((offset, text))
    return bodies


def _docstring_first_line(lines: List[str], holder: ast.AST) -> int:
    """
    Return the 1-based line the docstring of one holder opens on.

    :param lines: The file's lines.
    :type lines: list[str]
    :param holder: A module, class or function whose first statement is a string.
    :type holder: ast.AST
    :return: The line the opening quotes are on.
    :rtype: int
    """
    if isinstance(holder, ast.Module):
        start = 0
    else:
        start = holder.lineno - 1
    for index in range(start, len(lines)):
        stripped = lines[index].lstrip().lstrip("rRbBuU")
        if stripped.startswith(('"""', "'''")):
            return index + 1
    # No quotes found means the caller had no docstring to ask about.
    return start + 1


def referenced_targets(path: Path) -> List[Tuple[int, str]]:
    """
    Find every target the docstrings of one module refer to.

    :param path: A Python file.
    :type path: pathlib.Path
    :return: Pairs of line number and target, as written.
    :rtype: list[tuple[int, str]]
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
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
        # The docstring's own first line, found by looking for the quotes rather than
        # by asking the node: before Python 3.8 a multi-line string's `lineno` is its
        # *last* line, which put every report twenty lines off on 3.7. Searching the
        # value in the source would break on an escaped docstring instead.
        base = _docstring_first_line(lines, holder)
        for pattern in (ROLE, RAISES):
            for match in pattern.finditer(doc):
                line = base + doc[: match.start()].count("\n")
                found.append((line, match.group(1)))
        for offset, body in _field_bodies(doc):
            for target in QUALIFIED.findall(body):
                # A type field can name several -- `str or pyfcstm.model.model.State`
                # -- and only ours are judged.
                found.append((base + offset, target))
    return found


def dead_references(root: Path) -> List[Tuple[Path, int, str]]:
    """
    Report references whose target the documentation does not register.

    :param root: The repository root.
    :type root: pathlib.Path
    :return: File, line and target for each dead reference.
    :rtype: list[tuple[pathlib.Path, int, str]]
    :raises SystemExit: If the documentation tree registers no names at all, which
        means the tree moved rather than that every reference is live.
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
                # A trailing dot comes from a dotted path broken across lines, or from
                # a sentence that ends on one. Judging the name without it keeps a
                # full stop in prose from being reported; a genuinely broken path then
                # resolves to the module and is left to a `-n` build, which sees the
                # whole field body rather than one line of it.
                target = target.rstrip(".")
                if target and target not in names:
                    dead.append((path.relative_to(root), line, target))
    return dead


def _self_check() -> None:
    """
    Prove the scanner reports what it is for, and only that, on inputs written for it.

    Every rule gets a live case and a dead one, and the expectation carries the line
    each target sits on: a qualified target, a member, the ``~`` short form, a field
    body and its continuation, a body that continues past a blank line, a variadic
    field name, and a name ending on a full stop, which must not be read as a broken
    path.  Names written without their module appear too, and must stay unreported.

    Line numbers are compared because three of these rules are about *where* a target
    is, and comparing only the names left them invisible to this check.

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
        # So that a full stop after `pyfcstm.diagram` resolves once the dot is
        # stripped, which is what keeps prose from being reported.
        (doc / "index.rst").write_text(
            ".. automodule:: pyfcstm.diagram\n", encoding="utf-8"
        )
        package = fake / "pyfcstm" / "diagram"
        package.mkdir(parents=True)
        (package / "__init__.py").write_text(
            # A raw docstring, because the fixture carries `\\*args`: a plain one makes
            # the generated file raise a SyntaxWarning when this parses it back.
            'r"""\n'
            "Live: :class:`pyfcstm.diagram.api.Diagram`.\n"
            "Live member: :meth:`pyfcstm.diagram.api.Diagram.show`.\n"
            "Live short form: :class:`~pyfcstm.diagram.api.Diagram`.\n"
            "Dead module: :class:`pyfcstm.diagram.Diagram`.\n"
            "Dead member: :meth:`pyfcstm.diagram.api.Diagram.to_pdf`.\n"
            "Outside: :class:`os.PathLike`.\n"
            "\n:raises DiagramAssetError: bare in a field, never judged.\n"
            ":raises pyfcstm.diagram.api.DiagramAssetError: dead, and judged.\n"
            ":rtype: pyfcstm.diagram.api.Diagram\n"
            ":type thing: str or pyfcstm.diagram.Diagram\n"
            ":vartype wrapped: pyfcstm.diagram.api.Diagram or\n"
            "    pyfcstm.diagram.Wrapped\n"
            r":type \*args: pathlib.Path or"
            "\n"
            "    pyfcstm.diagram.Starred\n"
            ":vartype spaced: pyfcstm.diagram.api.Diagram\n"
            "\n"
            "    pyfcstm.diagram.PastBlank\n"
            ":rtype: a value described in pyfcstm.diagram.\n"
            '"""\n',
            encoding="utf-8",
        )
        (package / "api.py").write_text(
            '"""Bare in a module that documents it: :class:`Diagram`."""\n'
            "\n\n"
            "class Diagram:\n"
            '    """\n'
            "    Live member of the class it sits in: :meth:`show`.\n"
            "    Dead member, misspelled: :meth:`shoe`.\n"
            "    Not a member role, and not ours, so not judged: :class:`Mapping`.\n"
            '    """\n',
            encoding="utf-8",
        )
        (fake / "pyfcstm" / "entry").mkdir(parents=True)
        (fake / "pyfcstm" / "entry" / "diagram.py").write_text("", encoding="utf-8")

        names = documented_names(doc)
        expected = {
            "pyfcstm.diagram",
            "pyfcstm.diagram.api",
            "pyfcstm.diagram.api.Diagram",
            "pyfcstm.diagram.api.Diagram.show",
            "pyfcstm.diagram.api.Diagram.save",
        }
        if names != expected:
            raise SystemExit("registered names wrong: %s" % sorted(names))

        found = sorted((target, line) for _, line, target in dead_references(fake))
        wanted = [
            # (target, line within `__init__.py`)
            ("pyfcstm.diagram.Diagram", 5),  # the dead module-qualified role
            ("pyfcstm.diagram.Diagram", 12),  # and the same in a type field
            ("pyfcstm.diagram.PastBlank", 19),  # a body continuing past a blank line
            ("pyfcstm.diagram.Starred", 16),  # a variadic field name, escaped star
            ("pyfcstm.diagram.Wrapped", 14),  # on a field's continuation line
            ("pyfcstm.diagram.api.Diagram.to_pdf", 6),
            ("pyfcstm.diagram.api.DiagramAssetError", 10),
        ]
        if found != wanted:
            raise SystemExit("dead references wrong: %s" % found)
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
            if target.endswith("."):
                # A dotted path broken across lines. Reporting it as a missing target
                # would name something no reader can act on, and dropping the dot
                # would resolve to the module and hide a docstring Sphinx cannot read
                # either.
                sys.stderr.write(
                    "%s:%d: %s ends on a dot -- a dotted path broken across lines, "
                    "which Sphinx cannot resolve either\n" % (path, line, target)
                )
                continue
            sys.stderr.write(
                "%s:%d: %s is not registered by any api_doc page\n"
                % (path, line, target)
            )
        sys.stderr.write(
            "%d reference(s) render as plain text. If the object is ours, point the "
            "reference at the module whose api_doc page documents it; if it is not "
            "ours -- a standard-library name reached through a bare member role -- "
            "nothing here can resolve it, so say what it is in prose instead.\n"
            % len(dead)
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
    print("diagram reference targets: %d judged reference(s) all registered" % judged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
