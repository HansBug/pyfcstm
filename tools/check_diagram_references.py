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
Sphinx renders through ``bodyrolename='class'`` and are therefore references like
any other. Standard-library names are left alone: they never resolve in this
repository because intersphinx is not configured, and ``optional`` in a type field
is the convention CLAUDE.md sets out -- both are repository-wide and not this
package's to answer for.

A name written without its module is judged where the candidates Sphinx tries are
reproducible from the outside, which is two places:

* An inline role in a *module's own* docstring: there is no class to search and no
  ``refspecific`` flag, so ``modname + "." + name`` is the only candidate. Both
  directions are measured against built pages -- the bare ``:class:`DiagramAssetEngine```
  in ``pyfcstm/diagram/engine.py`` is a live link because that module documents it, and
  the same spelling in the package's own summary tables was not, because
  ``pyfcstm.diagram`` documents nothing.
* A ``:meth:`` or ``:attr:`` in a *class's* docstring, which the AST names: Sphinx tries
  the enclosing class and then the module, so it is dead only when neither has the
  name. Misspelling a member is the case this catches -- ``:meth:`to_dictt``` in the
  ``Diagram`` docstring renders as plain text and nothing else here would notice.

Those two roles are judged without asking whether the registry already knows the name,
because a bare member of a documented class means that class's member and a misspelling
is exactly what should be reported. Every other role is judged only when the registry
knows the name under some module, or ``:class:`ValueError``` would be read as ours.

What is still not judged is an information field: ``:raises DiagramUnavailableError:``
carries ``refspecific``, so Sphinx matches the whole registry by suffix and can resolve
it under a different module entirely -- that one lands in ``pyfcstm.diagram.engine``.
Nor is a bare name inside a *method*, where the enclosing class is tried first and the
AST here does not carry which class a method belongs to.

A first version guessed at the class case with the module's name and reported sixteen
references that are in fact links. A gate that cries wolf is worse than one with a
stated boundary.

The registry over-approximates in one way worth knowing: every name listed in a
``:members:`` option counts as registered, while autodoc emits no anchor for a member
that has no docstring -- a bare dataclass field, for instance. Checked against a built
``objects.inv``, 1876 of the names collected here do not exist as anchors, 93 of them
in this package's own modules; the reverse, a real object the registry does not know
about, is zero. So the error only ever costs a report, never invents one, and no live
reference is masked by it today.

Run ``make diagram_reference_targets_check``. Pass ``--check`` for the
self-check, which proves the scanner reports a reference it should.
"""

import argparse
import ast
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[1]

# The tree whose references are checked, and the documentation that registers
# the targets. Widening the first to all of `pyfcstm` means answering for the
# nineteen `pyfcstm.model.StateMachine` references elsewhere in it first.
SOURCES = ("pyfcstm/diagram", "pyfcstm/entry/diagram.py")
API_DOC = "docs/source/api_doc"

ROLE = re.compile(r":(class|exc|meth|func|data|mod|attr|obj):`~?([A-Za-z_][\w.]*)`")
# A name written without its module after one of these means a member of whatever it
# sits in, so a misspelling is a dead reference rather than a foreign name. The others
# routinely name things outside this package -- `ValueError`, `Path` -- which is why
# they are only judged when the registry knows the name under some module.
MEMBER_ROLES = frozenset(("meth", "attr"))
RAISES = re.compile(r":raises\s+~?([A-Za-z_][\w.]*)\s*:")
# `:rtype:`, `:type:` and `:vartype:` bodies are cross-references too: Sphinx renders
# them through `bodyrolename='class'`, so `:rtype: pyfcstm.diagram.api.Diagram` is a
# link in the built page and the same line pointed at a module that does not document
# the class is plain text. Leaving these out meant the one `:rtype:` this gate arrived
# with could regress in silence.
FIELD = re.compile(r":(?:rtype|type|vartype)\s*[\w.]*:\s*([^\n]*)")
QUALIFIED = re.compile(r"\bpyfcstm\.[A-Za-z_][\w.]*")

CURRENTMODULE = re.compile(r"^\.\.\s+currentmodule::\s*([\w.]+)\s*$", re.M)
AUTOMODULE = re.compile(r"^\.\.\s+automodule::\s*([\w.]+)\s*$", re.M)
AUTOOBJECT = re.compile(
    r"^\.\.\s+auto(?:class|exception|function|data|method|attribute)::\s*([\w.]+)\s*$",
    re.M,
)
MEMBERS = re.compile(r"^\s+:members:\s*(.*)$", re.M)

# Stands for "the module this file is", so `referenced_targets` can say which prefix
# applies without being told the repository root.
MODULE = object()


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


def referenced_targets(path: Path) -> List[Tuple[int, str, Optional[str], str]]:
    """
    Find every target the docstrings of one module refer to.

    :param path: A Python file.
    :type path: pathlib.Path
    :return: Line, target, the prefix a name written without its module would resolve
        against -- the module for the module's own docstring, the class for a class's,
        and ``None`` where Sphinx uses context this cannot reproduce -- and the role
        it was written with.
    :rtype: list[tuple[int, str, str or None, str]]
    """
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    found = []
    classes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes[node] = node.name
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
        # What a bare name resolves against here, or nothing when Sphinx has more
        # context than this can reproduce -- inside a method, the enclosing class is
        # tried first and this does not know which class the method belongs to.
        if holder is tree:
            prefix = MODULE
        elif holder in classes:
            prefix = classes[holder]
        else:
            prefix = None
        for match in ROLE.finditer(doc):
            line = base + doc[: match.start()].count("\n")
            found.append((line, match.group(2), prefix, match.group(1)))
        for match in RAISES.finditer(doc):
            line = base + doc[: match.start()].count("\n")
            # Never judged bare: an information field carries `refspecific`, so
            # Sphinx matches the whole registry by suffix and can resolve it under
            # a module other than this one.
            found.append((line, match.group(1), None, "exc"))
        for match in FIELD.finditer(doc):
            line = base + doc[: match.start()].count("\n")
            for target in QUALIFIED.findall(match.group(1)):
                # A type field can name several -- `str or pyfcstm.model.model.State`
                # -- and only ours are judged.
                found.append((line, target, None, "class"))
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
    # Which last components are ours at all, so a name written without its module
    # can be told from `ValueError`: ours appears in the registry under some module,
    # a builtin appears nowhere in it.
    ours = {name.rsplit(".", 1)[-1] for name in names if "." in name}
    dead = []
    for entry in SOURCES:
        location = root / entry
        files = sorted(location.rglob("*.py")) if location.is_dir() else [location]
        for path in files:
            module = module_of(path, root)
            for line, target, prefix, role in referenced_targets(path):
                if "." not in target:
                    if prefix is None:
                        continue
                    if role not in MEMBER_ROLES and target not in ours:
                        continue
                    if role in MEMBER_ROLES and prefix is not MODULE:
                        # A member of the class it sits in, or a function of the
                        # module -- Sphinx tries the class first and the module next,
                        # so it is dead only when neither has it.
                        candidates = (
                            "%s.%s.%s" % (module, prefix, target),
                            "%s.%s" % (module, target),
                        )
                        if not any(name in names for name in candidates):
                            dead.append((path.relative_to(root), line, candidates[0]))
                        continue
                    if prefix is MODULE:
                        # An inline role in a module's own docstring has no class to
                        # search and no `refspecific` flag, so `modname + "." + name`
                        # is the only candidate Sphinx has.
                        target = "%s.%s" % (module, target)
                    else:
                        # In a class's docstring the enclosing class is tried first,
                        # and the AST says which class that is.
                        target = "%s.%s.%s" % (module, prefix, target)
                elif not target.startswith("pyfcstm."):
                    continue
                if target not in names:
                    dead.append((path.relative_to(root), line, target))
    return dead


def _self_check() -> None:
    """
    Prove the scanner reports what it is for, and only that, on inputs written for it.

    Every rule gets a live case and a dead one: a qualified target, a member, the
    ``~`` short form, a field body, and a name written without its module in a module
    docstring -- which is judged, and is the shape the package's own summary tables
    had.  The bare name in a module that *does* document it must stay unreported, or
    the gate would report links as dead.

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
            "Dead bare, this module documenting nothing: :class:`Diagram`.\n"
            "Not ours and bare, so not judged: :exc:`ValueError`.\n"
            "Bare member of no class here, and no module function: :meth:`nowhere`.\n"
            "Outside: :class:`os.PathLike`.\n"
            "\n:raises DiagramAssetError: bare in a field, never judged.\n"
            ":raises pyfcstm.diagram.api.DiagramAssetError: dead, and judged.\n"
            ":rtype: pyfcstm.diagram.api.Diagram\n"
            ':type thing: str or pyfcstm.diagram.Diagram\n"""\n',
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
            "pyfcstm.diagram.api",
            "pyfcstm.diagram.api.Diagram",
            "pyfcstm.diagram.api.Diagram.show",
            "pyfcstm.diagram.api.Diagram.save",
        }
        if names != expected:
            raise SystemExit("registered names wrong: %s" % sorted(names))

        found = sorted(target for _, _, target in dead_references(fake))
        wanted = [
            "pyfcstm.diagram.Diagram",  # the dead module-qualified role
            "pyfcstm.diagram.Diagram",  # the dead bare name, resolved to this module
            "pyfcstm.diagram.Diagram",  # and the same in a type field
            "pyfcstm.diagram.api.Diagram.shoe",  # the misspelled bare member
            "pyfcstm.diagram.api.Diagram.to_pdf",
            "pyfcstm.diagram.api.DiagramAssetError",
            "pyfcstm.diagram.nowhere",  # a bare member with neither class nor module
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
        for _, target, prefix, _role in referenced_targets(path)
        if target.startswith("pyfcstm.") or (prefix is not None and "." not in target)
    )
    print("diagram reference targets: %d judged reference(s) all registered" % judged)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
