"""
Validate pytest boundary rules for repository tests.

This maintenance command scans Python files under :mod:`test` and reports
patterns that would make pytest depend on repository maintenance tooling or
repository-source built-in templates. The command is intentionally outside the
pytest unit-test suite so the guard can protect the test boundary without
becoming another unit test that imports the private tooling it audits.

The command contains the following checks:
* direct imports or dynamic imports of ``tools.*`` from pytest files
* subprocess or shell command strings that execute repository ``tools`` scripts
* repo-root-tainted paths that access the source ``templates`` directory
* source-install smoke-test markers that belong in maintenance commands

Example::

    $ python tools/check_test_boundary.py
"""

from __future__ import annotations

import argparse
import ast
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Set


AST_CONSTANT_TYPE = getattr(ast, "Constant", None)
AST_STR_TYPE = getattr(ast, "Str", None) if sys.version_info < (3, 8) else None


TOOLS_IMPORT_RULE = "tools-import"
TOOLS_DYNAMIC_RULE = "tools-dynamic-import"
TOOLS_CALL_RULE = "tools-call"
TOOLS_EXEC_RULE = "tools-exec"
SOURCE_TEMPLATE_RULE = "repo-source-templates"
SOURCE_INSTALL_RULE = "source-install-smoke"
PACKAGE_TEMPLATES_RULE = "package-templates-call"

_SUBPROCESS_METHODS = {
    "run",
    "call",
    "check_call",
    "check_output",
    "Popen",
}
_OS_COMMAND_METHODS = {
    "system",
    "popen",
    "spawnl",
    "spawnle",
    "spawnlp",
    "spawnlpe",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
}
_SOURCE_INSTALL_MARKERS = (
    "--target",
    "source install",
    "source-install",
    "install_dir",
)
_REPO_ROOT_NAME_FRAGMENTS = (
    "repo_root",
    "repository_root",
)


@dataclass(frozen=True)
class BoundaryFinding:
    """
    Describe one test-boundary violation.

    :param path: Python file containing the finding.
    :type path: pathlib.Path
    :param line: One-based source line number.
    :type line: int
    :param column: One-based source column number.
    :type column: int
    :param rule: Stable rule identifier.
    :type rule: str
    :param message: Human-readable diagnostic message.
    :type message: str
    :param source: Source line text, if available.
    :type source: str

    Example::

        >>> finding = BoundaryFinding(Path('test/example.py'), 1, 1, 'rule', 'message', 'text')
        >>> finding.location
        'test/example.py:1:1'
    """

    path: Path
    line: int
    column: int
    rule: str
    message: str
    source: str

    @property
    def location(self) -> str:
        """
        Return the compact source location for this finding.

        :return: Location formatted as ``path:line:column``.
        :rtype: str

        Example::

            >>> BoundaryFinding(Path('x.py'), 2, 3, 'r', 'm', '').location
            'x.py:2:3'
        """
        return "{path}:{line}:{column}".format(
            path=self.path.as_posix(),
            line=self.line,
            column=self.column,
        )


def repository_root() -> Path:
    """
    Return the repository root for direct script execution.

    :return: Repository root path.
    :rtype: pathlib.Path

    Example::

        >>> repository_root().name  # doctest: +SKIP
        'pyfcstm'
    """
    return Path(__file__).resolve().parents[1]


def iter_python_files(test_root: Path) -> Iterable[Path]:
    """
    Yield Python test files in deterministic order.

    :param test_root: Root directory to scan.
    :type test_root: pathlib.Path
    :return: Iterator over Python source paths.
    :rtype: typing.Iterable[pathlib.Path]

    Example::

        >>> next(iter_python_files(repository_root() / 'test')).suffix
        '.py'
    """
    for path in sorted(test_root.rglob("*.py")):
        parts = set(path.parts)
        if "__pycache__" not in parts:
            yield path


def read_source(path: Path) -> str:
    """
    Read a UTF-8 Python source file.

    :param path: Python file path.
    :type path: pathlib.Path
    :return: Source text.
    :rtype: str
    :raises OSError: If the source file cannot be read.

    Example::

        >>> 'Validate pytest boundary' in read_source(repository_root() / 'tools' / 'check_test_boundary.py')
        True
    """
    return path.read_text(encoding="utf-8")


def dotted_name(node: ast.AST) -> Optional[str]:
    """
    Return a dotted expression name when ``node`` is name-like.

    :param node: AST node to inspect.
    :type node: ast.AST
    :return: Dotted name, or ``None`` when the node is not name-like.
    :rtype: str, optional

    Example::

        >>> dotted_name(ast.parse('subprocess.run()').body[0].value.func)
        'subprocess.run'
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = dotted_name(node.value)
        if parent is not None:
            return "{parent}.{attr}".format(parent=parent, attr=node.attr)
    return None


def literal_string(node: ast.AST) -> Optional[str]:
    """
    Return a string literal value from an AST node.

    :param node: AST node to inspect.
    :type node: ast.AST
    :return: String literal value, or ``None`` when the node is not a string.
    :rtype: str, optional

    Example::

        >>> literal_string(ast.parse('"x"').body[0].value)
        'x'
    """
    if AST_STR_TYPE is not None and isinstance(node, AST_STR_TYPE):
        return getattr(node, "s")
    if AST_CONSTANT_TYPE is not None and isinstance(node, AST_CONSTANT_TYPE):
        if isinstance(node.value, str):
            return node.value
    return None


def collect_string_literals(node: ast.AST) -> List[str]:
    """
    Collect string literals inside ``node``.

    :param node: AST node to scan.
    :type node: ast.AST
    :return: String literal values in traversal order.
    :rtype: List[str]

    Example::

        >>> collect_string_literals(ast.parse('["a", "b"]').body[0].value)
        ['a', 'b']
    """
    values = []
    for child in ast.walk(node):
        value = literal_string(child)
        if value is not None:
            values.append(value)
    return values


def collect_defined_names(tree: ast.AST) -> Set[str]:
    """
    Collect names defined by functions, classes, and assignments.

    :param tree: Parsed Python AST.
    :type tree: ast.AST
    :return: Defined names.
    :rtype: Set[str]

    Example::

        >>> tree = ast.parse('def f(): pass')
        >>> collect_defined_names(tree)
        {'f'}
        >>> tree = ast.parse('package_templates = lambda: None')
        >>> 'package_templates' in collect_defined_names(tree)
        True
    """
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                names.update(assigned_target_names(target))
        elif isinstance(node, ast.AnnAssign):
            names.update(assigned_target_names(node.target))
    return names


def assigned_target_names(node: ast.AST) -> Set[str]:
    """
    Return simple names assigned by an assignment target.

    :param node: Assignment target node.
    :type node: ast.AST
    :return: Assigned identifier names.
    :rtype: Set[str]

    Example::

        >>> assigned_target_names(ast.parse('a = 1').body[0].targets[0])
        {'a'}
    """
    if isinstance(node, ast.Name):
        return {node.id}
    names = set()
    if isinstance(node, (ast.Tuple, ast.List)):
        for item in node.elts:
            names.update(assigned_target_names(item))
    return names


def is_tools_module_name(name: str) -> bool:
    """
    Return whether ``name`` denotes the repository ``tools`` package.

    :param name: Dotted import or module name.
    :type name: str
    :return: ``True`` when the name is ``tools`` or a ``tools.*`` module.
    :rtype: bool

    Example::

        >>> is_tools_module_name('tools.package_templates')
        True
    """
    return name == "tools" or name.startswith("tools.")


def is_repo_root_name(name: str) -> bool:
    """
    Return whether an identifier conventionally denotes the repository root.

    :param name: Identifier to inspect.
    :type name: str
    :return: ``True`` when the name is a repo-root-style identifier.
    :rtype: bool

    Example::

        >>> is_repo_root_name('_REPO_ROOT')
        True
    """
    lower = name.lower()
    return any(fragment in lower for fragment in _REPO_ROOT_NAME_FRAGMENTS)


def node_contains_name(node: ast.AST, name: str) -> bool:
    """
    Return whether ``node`` contains a :class:`ast.Name` with ``name``.

    :param node: AST node to inspect.
    :type node: ast.AST
    :param name: Identifier to search for.
    :type name: str
    :return: ``True`` when the identifier appears in ``node``.
    :rtype: bool

    Example::

        >>> node_contains_name(ast.parse('Path(__file__)').body[0].value, '__file__')
        True
    """
    return any(
        isinstance(child, ast.Name) and child.id == name for child in ast.walk(node)
    )


def is_file_parents_expr(node: ast.AST) -> bool:
    """
    Return whether ``node`` climbs from ``__file__`` toward parent paths.

    :param node: AST node to inspect.
    :type node: ast.AST
    :return: ``True`` for path expressions rooted at ``__file__`` parents.
    :rtype: bool

    Example::

        >>> expr = ast.parse('Path(__file__).resolve().parents[2]').body[0].value
        >>> is_file_parents_expr(expr)
        True
        >>> expr = ast.parse('Path(__file__).resolve().parent.parent').body[0].value
        >>> is_file_parents_expr(expr)
        True
        >>> expr = ast.parse('Path(__file__).resolve().parent').body[0].value
        >>> is_file_parents_expr(expr)
        False
    """
    for child in ast.walk(node):
        if isinstance(child, ast.Subscript):
            value = child.value
            if isinstance(value, ast.Attribute) and value.attr == "parents":
                if node_contains_name(value.value, "__file__"):
                    return True
        if parent_chain_depth(child) >= 2:
            return True
    return False


def parent_chain_depth(node: ast.AST) -> int:
    """
    Return the number of consecutive ``.parent`` hops from a ``__file__`` path.

    :param node: AST node to inspect.
    :type node: ast.AST
    :return: Number of consecutive ``.parent`` attributes rooted at ``__file__``.
    :rtype: int

    Example::

        >>> expr = ast.parse('Path(__file__).resolve().parent.parent').body[0].value
        >>> parent_chain_depth(expr)
        2
    """
    depth = 0
    current = node
    while isinstance(current, ast.Attribute) and current.attr == "parent":
        depth += 1
        current = current.value
    if depth and node_contains_name(current, "__file__"):
        return depth
    return 0


def is_exact_segment(node: ast.AST, segment: str) -> bool:
    """
    Return whether ``node`` is exactly a string path segment.

    :param node: AST node to inspect.
    :type node: ast.AST
    :param segment: Expected path segment.
    :type segment: str
    :return: ``True`` when ``node`` is exactly that string literal.
    :rtype: bool

    Example::

        >>> is_exact_segment(ast.parse('"templates"').body[0].value, 'templates')
        True
    """
    value = literal_string(node)
    return value == segment


def command_text_runs_tools_script(text: str) -> bool:
    """
    Return whether a command string executes repository tools.

    :param text: Command string or command argument.
    :type text: str
    :return: ``True`` for ``tools/*.py`` or ``python -m tools.*`` patterns.
    :rtype: bool

    Example::

        >>> command_text_runs_tools_script('python -m tools.package_templates')
        True
    """
    normalized = text.replace("\\", "/")
    if "tools/" in normalized and ".py" in normalized:
        return True
    return "-m tools." in normalized or normalized.strip().startswith("tools.")


def command_sequence_runs_tools_script(values: Sequence[str]) -> bool:
    """
    Return whether a command argument sequence executes repository tools.

    :param values: Command argument literals.
    :type values: Sequence[str]
    :return: ``True`` when the sequence targets a repository tools module/script.
    :rtype: bool

    Example::

        >>> command_sequence_runs_tools_script(['python', '-m', 'tools.package_templates'])
        True
    """
    for index, value in enumerate(values):
        if command_text_runs_tools_script(value):
            return True
        if value == "-m" and index + 1 < len(values):
            if values[index + 1] == "tools" or values[index + 1].startswith("tools."):
                return True
    return False


def expression_runs_tools_script(node: ast.AST) -> bool:
    """
    Return whether a command expression executes repository tools.

    :param node: AST node for a subprocess or shell command argument.
    :type node: ast.AST
    :return: ``True`` when the command contains a tools script/module target.
    :rtype: bool

    Example::

        >>> expression_runs_tools_script(ast.parse('["python", "-m", "tools.x"]').body[0].value)
        True
        >>> expression_runs_tools_script(ast.parse('Path("tools") / "x.py"').body[0].value)
        True
    """
    if isinstance(node, ast.Name):
        return False
    values = collect_string_literals(node)
    if isinstance(node, (ast.List, ast.Tuple)):
        return command_sequence_runs_tools_script(
            values
        ) or command_literals_form_tools_script_path(values)
    if command_sequence_runs_tools_script(values):
        return True
    if command_literals_form_tools_script_path(values):
        return True
    return any(command_text_runs_tools_script(value) for value in values)


def command_literals_form_tools_script_path(values: Sequence[str]) -> bool:
    """
    Return whether string literals combine into a ``tools/*.py`` path.

    :param values: String literal values from a command expression.
    :type values: Sequence[str]
    :return: ``True`` when literals contain a ``tools`` segment and a Python file.
    :rtype: bool

    Example::

        >>> command_literals_form_tools_script_path(['tools', 'x.py'])
        True
    """
    normalized_values = [value.replace("\\", "/") for value in values]
    has_tools_segment = any(
        value == "tools" or "/tools/" in "/{value}/".format(value=value.strip("/"))
        for value in normalized_values
    )
    has_python_file = any(value.endswith(".py") for value in normalized_values)
    return has_tools_segment and has_python_file


def string_contains_source_install_marker(value: str) -> bool:
    """
    Return whether a string literal describes a source-install smoke path.

    :param value: String literal value to inspect.
    :type value: str
    :return: ``True`` when the literal looks like a source-install smoke command.
    :rtype: bool

    Example::

        >>> string_contains_source_install_marker('pip install pytest')
        False
        >>> string_contains_source_install_marker('python -m pip install .')
        True
    """
    lowered = value.lower()
    if any(marker in lowered for marker in _SOURCE_INSTALL_MARKERS):
        return True
    normalized = lowered.replace("\\", "/")
    tokens = normalized.split()
    for index in range(len(tokens) - 1):
        if tokens[index] != "pip" or tokens[index + 1] != "install":
            continue
        install_args = tokens[index + 2 :]
        for arg in install_args:
            if arg in {"-e", "--editable", ".", "./", "..", "../"}:
                return True
            if arg.startswith("./") or arg.startswith("../"):
                return True
    return False


class TestBoundaryVisitor(ast.NodeVisitor):
    """
    Visit a test module AST and collect boundary violations.

    :param path: Source path relative to the repository root.
    :type path: pathlib.Path
    :param source: Source text for diagnostics.
    :type source: str
    :param defined_names: Names defined by functions and classes in the module.
    :type defined_names: Set[str]
    :param docstring_node_ids: String literal nodes that are docstrings,
        defaults to ``None``.
    :type docstring_node_ids: Set[int], optional

    Example::

        >>> source = 'import tools.package_templates'
        >>> tree = ast.parse(source)
        >>> visitor = TestBoundaryVisitor(Path('test/example.py'), source, set())
        >>> visitor.visit(tree)
        >>> visitor.findings[0].rule
        'tools-import'
    """

    def __init__(
        self,
        path: Path,
        source: str,
        defined_names: Set[str],
        docstring_node_ids: Optional[Set[int]] = None,
    ) -> None:
        self.path = path
        self.source_lines = source.splitlines()
        self.defined_names = defined_names
        self.docstring_node_ids = docstring_node_ids or set()
        self.findings = []  # type: List[BoundaryFinding]
        self.tools_aliases = set()  # type: Set[str]
        self.dynamic_tools_aliases = set()  # type: Set[str]
        self.importlib_aliases = {"importlib"}  # type: Set[str]
        self.subprocess_aliases = {"subprocess"}  # type: Set[str]
        self.subprocess_function_aliases = set()  # type: Set[str]
        self.os_aliases = {"os"}  # type: Set[str]
        self.os_function_aliases = set()  # type: Set[str]
        self.os_path_join_aliases = set()  # type: Set[str]
        self.os_path_dirname_aliases = set()  # type: Set[str]
        self.os_path_abspath_aliases = set()  # type: Set[str]
        self.repo_root_aliases = set()  # type: Set[str]
        self.tools_command_aliases = set()  # type: Set[str]
        self.package_templates_aliases = set()  # type: Set[str]

    def add_finding(self, node: ast.AST, rule: str, message: str) -> None:
        """
        Append one finding for ``node``.

        :param node: AST node that triggered the finding.
        :type node: ast.AST
        :param rule: Stable rule identifier.
        :type rule: str
        :param message: Human-readable diagnostic message.
        :type message: str
        :return: ``None``.
        :rtype: None

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), 'bad', set())
            >>> visitor.add_finding(ast.parse('bad').body[0], 'r', 'm')
            >>> visitor.findings[0].line
            1
        """
        line = getattr(node, "lineno", 1)
        column = getattr(node, "col_offset", 0) + 1
        if 1 <= line <= len(self.source_lines):
            source = self.source_lines[line - 1].strip()
        else:
            source = ""
        self.findings.append(
            BoundaryFinding(
                path=self.path,
                line=line,
                column=column,
                rule=rule,
                message=message,
                source=source,
            )
        )

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        """
        Visit an ``import`` statement.

        :param node: Import statement node.
        :type node: ast.Import
        :return: ``None``.
        :rtype: None

        Example::

            >>> tree = ast.parse('import importlib as imp')
            >>> visitor = TestBoundaryVisitor(Path('x.py'), 'import importlib as imp', set())
            >>> visitor.visit(tree)
            >>> 'imp' in visitor.importlib_aliases
            True
        """
        for alias in node.names:
            local_name = alias.asname or alias.name.split(".")[0]
            if is_tools_module_name(alias.name):
                self.tools_aliases.add(local_name)
                self.add_finding(
                    node,
                    TOOLS_IMPORT_RULE,
                    "pytest files must not import repository tools modules directly",
                )
            elif alias.name == "importlib":
                self.importlib_aliases.add(local_name)
            elif alias.name == "subprocess":
                self.subprocess_aliases.add(local_name)
            elif alias.name == "os":
                self.os_aliases.add(local_name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        """
        Visit a ``from ... import ...`` statement.

        :param node: Import-from statement node.
        :type node: ast.ImportFrom
        :return: ``None``.
        :rtype: None

        Example::

            >>> tree = ast.parse('from subprocess import run as sprun')
            >>> visitor = TestBoundaryVisitor(Path('x.py'), 'from subprocess import run as sprun', set())
            >>> visitor.visit(tree)
            >>> 'sprun' in visitor.subprocess_function_aliases
            True
        """
        module = node.module or ""
        if is_tools_module_name(module):
            for alias in node.names:
                local_name = alias.asname or alias.name
                if (
                    alias.name == "package_templates"
                    or module == "tools.package_templates"
                ):
                    self.package_templates_aliases.add(local_name)
            self.add_finding(
                node,
                TOOLS_IMPORT_RULE,
                "pytest files must not import repository tools modules directly",
            )
        elif module == "importlib":
            for alias in node.names:
                if alias.name == "import_module":
                    self.importlib_aliases.add(alias.asname or alias.name)
        elif module == "subprocess":
            for alias in node.names:
                if alias.name in _SUBPROCESS_METHODS:
                    self.subprocess_function_aliases.add(alias.asname or alias.name)
        elif module == "os":
            for alias in node.names:
                if alias.name in _OS_COMMAND_METHODS:
                    self.os_function_aliases.add(alias.asname or alias.name)
        elif module == "os.path":
            for alias in node.names:
                if alias.name == "join":
                    self.os_path_join_aliases.add(alias.asname or alias.name)
                elif alias.name == "dirname":
                    self.os_path_dirname_aliases.add(alias.asname or alias.name)
                elif alias.name == "abspath":
                    self.os_path_abspath_aliases.add(alias.asname or alias.name)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        """
        Visit an assignment and track tainted aliases.

        :param node: Assignment node.
        :type node: ast.Assign
        :return: ``None``.
        :rtype: None

        Example::

            >>> tree = ast.parse('x = __import__("tools.x")')
            >>> visitor = TestBoundaryVisitor(Path('x.py'), 'x = __import__("tools.x")', set())
            >>> visitor.visit(tree)
            >>> 'x' in visitor.dynamic_tools_aliases
            True
        """
        self._visit_assignment_targets(node.targets, node.value)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        """
        Visit an annotated assignment and track tainted aliases.

        :param node: Annotated assignment node.
        :type node: ast.AnnAssign
        :return: ``None``.
        :rtype: None

        Example::

            >>> tree = ast.parse('x: object = __import__("tools.x")')
            >>> visitor = TestBoundaryVisitor(Path('x.py'), 'x: object = __import__("tools.x")', set())
            >>> visitor.visit(tree)
            >>> 'x' in visitor.dynamic_tools_aliases
            True
        """
        if node.value is not None:
            self._visit_assignment_targets([node.target], node.value)
        self.generic_visit(node)

    def _visit_assignment_targets(
        self, targets: Sequence[ast.AST], value: ast.AST
    ) -> None:
        """
        Track aliases introduced by assignment targets.

        :param targets: Assignment targets.
        :type targets: Sequence[ast.AST]
        :param value: Assigned value expression.
        :type value: ast.AST
        :return: ``None``.
        :rtype: None

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor._visit_assignment_targets([ast.Name(id='repo_root')], ast.parse('Path(__file__).parents[1]').body[0].value)
            >>> 'repo_root' in visitor.repo_root_aliases
            True
        """
        for target in targets:
            for name in self._target_names(target):
                if self.is_repo_root_tainted(value) or is_repo_root_name(name):
                    self.repo_root_aliases.add(name)
                if self.is_dynamic_tools_import_call(value):
                    self.dynamic_tools_aliases.add(name)
                if expression_runs_tools_script(value):
                    self.tools_command_aliases.add(name)

    def _target_names(self, node: ast.AST) -> List[str]:
        """
        Return names assigned by a target node.

        :param node: Assignment target node.
        :type node: ast.AST
        :return: Assigned identifier names.
        :rtype: List[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set())._target_names(ast.Name(id='x'))
            ['x']
        """
        if isinstance(node, ast.Name):
            return [node.id]
        names = []
        if isinstance(node, (ast.Tuple, ast.List)):
            for item in node.elts:
                names.extend(self._target_names(item))
        return names

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        """
        Visit a call expression and report forbidden tool/template patterns.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``None``.
        :rtype: None

        Example::

            >>> tree = ast.parse('__import__("tools.x")')
            >>> visitor = TestBoundaryVisitor(Path('x.py'), '__import__("tools.x")', set())
            >>> visitor.visit(tree)
            >>> visitor.findings[0].rule
            'tools-dynamic-import'
        """
        if self.is_dynamic_tools_import_call(node):
            self.add_finding(
                node,
                TOOLS_DYNAMIC_RULE,
                "pytest files must not dynamically import repository tools modules",
            )
        if self.is_tools_attribute_call(node):
            self.add_finding(
                node,
                TOOLS_CALL_RULE,
                "pytest files must not call repository tools module attributes directly",
            )
        if self.is_getattr_tools_call(node):
            self.add_finding(
                node,
                TOOLS_CALL_RULE,
                "pytest files must not use getattr to call repository tools modules",
            )
        if self.is_package_templates_call(node):
            self.add_finding(
                node,
                PACKAGE_TEMPLATES_RULE,
                "pytest files must not call tools.package_templates from unit tests",
            )
        if self.is_command_call_running_tools(node):
            self.add_finding(
                node,
                TOOLS_EXEC_RULE,
                "pytest files must not execute repository tools scripts from subprocess or shell commands",
            )
        if self.is_repo_source_template_access(node):
            self.add_finding(
                node,
                SOURCE_TEMPLATE_RULE,
                "pytest files must not access the repository-source templates directory directly",
            )
        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:  # noqa: N802
        """
        Visit binary path joins and report repo-source template access.

        :param node: Binary operation node.
        :type node: ast.BinOp
        :return: ``None``.
        :rtype: None

        Example::

            >>> tree = ast.parse('_REPO_ROOT / "templates"')
            >>> visitor = TestBoundaryVisitor(Path('x.py'), '_REPO_ROOT / "templates"', set())
            >>> visitor.visit(tree)
            >>> visitor.findings[0].rule
            'repo-source-templates'
        """
        if self.is_repo_source_template_access(node):
            self.add_finding(
                node,
                SOURCE_TEMPLATE_RULE,
                "pytest files must not access the repository-source templates directory directly",
            )
        self.generic_visit(node)

    def visit_Constant(self, node: ast.Constant) -> None:  # noqa: N802
        """
        Visit Python 3.8+ literal constants for source-install markers.

        :param node: Constant node.
        :type node: ast.Constant
        :return: ``None``.
        :rtype: None

        Example::

            >>> tree = ast.parse('"pip install ."')
            >>> visitor = TestBoundaryVisitor(Path('x.py'), '"pip install ."', set())
            >>> visitor.visit(tree)
            >>> visitor.findings[0].rule
            'source-install-smoke'
        """
        self._visit_string_marker(node)
        self.generic_visit(node)

    def visit_Str(self, node: ast.AST) -> None:  # noqa: N802
        """
        Visit Python 3.7 string literals for source-install markers.

        :param node: String node.
        :type node: ast.AST
        :return: ``None``.
        :rtype: None

        Example::

            >>> tree = ast.parse('"--target"')
            >>> visitor = TestBoundaryVisitor(Path('x.py'), '"--target"', set())
            >>> visitor.visit(tree)
            >>> visitor.findings[0].rule
            'source-install-smoke'
        """
        self._visit_string_marker(node)
        self.generic_visit(node)

    def _visit_string_marker(self, node: ast.AST) -> None:
        """
        Report source-install smoke markers in runtime string literals.

        :param node: Literal node.
        :type node: ast.AST
        :return: ``None``.
        :rtype: None

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '"install_dir"', set())
            >>> visitor._visit_string_marker(ast.parse('"install_dir"').body[0].value)
            >>> visitor.findings[0].rule
            'source-install-smoke'
        """
        if id(node) in self.docstring_node_ids:
            return
        value = literal_string(node)
        if value is None:
            return
        if string_contains_source_install_marker(value):
            self.add_finding(
                node,
                SOURCE_INSTALL_RULE,
                "pytest files must not contain source-install smoke-test markers",
            )
            return

    def is_dynamic_tools_import_call(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` dynamically imports ``tools``.

        :param node: AST node to inspect.
        :type node: ast.AST
        :return: ``True`` for ``importlib.import_module('tools...')`` or ``__import__``.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_dynamic_tools_import_call(ast.parse('__import__("tools.x")').body[0].value)
            True
        """
        if not isinstance(node, ast.Call):
            return False
        func_name = dotted_name(node.func)
        if func_name == "__import__":
            return bool(
                node.args and is_tools_module_name(literal_string(node.args[0]) or "")
            )
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "import_module" and isinstance(
                node.func.value, ast.Name
            ):
                if node.func.value.id in self.importlib_aliases:
                    return bool(
                        node.args
                        and is_tools_module_name(literal_string(node.args[0]) or "")
                    )
        if isinstance(node.func, ast.Name) and node.func.id in self.importlib_aliases:
            return bool(
                node.args and is_tools_module_name(literal_string(node.args[0]) or "")
            )
        return False

    def is_tools_attribute_call(self, node: ast.Call) -> bool:
        """
        Return whether a call targets a known tools module alias.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when the callee is under a tools alias.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.tools_aliases.add('tools')
            >>> visitor.is_tools_attribute_call(ast.parse('tools.x()').body[0].value)
            True
        """
        if not isinstance(node.func, ast.Attribute):
            return False
        root = self._attribute_root_name(node.func)
        return root in self.tools_aliases or root in self.dynamic_tools_aliases

    def is_getattr_tools_call(self, node: ast.Call) -> bool:
        """
        Return whether a call uses ``getattr`` on a tools-like object.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when ``getattr`` targets a tools alias or tools-like name.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_getattr_tools_call(ast.parse('getattr(tools_module, "x")').body[0].value)
            True
        """
        if dotted_name(node.func) != "getattr" or not node.args:
            return False
        target = node.args[0]
        if isinstance(target, ast.Name):
            name = target.id
            if name in self.tools_aliases or name in self.dynamic_tools_aliases:
                return True
            return (
                name == "tools" or name == "tools_module" or name.startswith("tools_")
            )
        return False

    def _attribute_root_name(self, node: ast.AST) -> Optional[str]:
        """
        Return the root name of an attribute chain.

        :param node: Attribute or name node.
        :type node: ast.AST
        :return: Root identifier, or ``None``.
        :rtype: str, optional

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set())._attribute_root_name(ast.parse('a.b.c').body[0].value)
            'a'
        """
        current = node
        while isinstance(current, ast.Attribute):
            current = current.value
        if isinstance(current, ast.Name):
            return current.id
        return None

    def is_package_templates_call(self, node: ast.Call) -> bool:
        """
        Return whether a call invokes template-packaging helper code.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` for direct or unresolved ``package_templates`` calls.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_package_templates_call(ast.parse('package_templates()').body[0].value)
            True
        """
        name = dotted_name(node.func)
        if name is None:
            return False
        if name in self.package_templates_aliases:
            return True
        if name.endswith(".package_templates"):
            root = name.split(".", 1)[0]
            if root in self.tools_aliases or root in self.dynamic_tools_aliases:
                return True
        return name == "package_templates" and name not in self.defined_names

    def is_command_call_running_tools(self, node: ast.Call) -> bool:
        """
        Return whether a subprocess or shell call executes repository tools.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` for command calls that target ``tools`` scripts/modules.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_command_call_running_tools(ast.parse('subprocess.run(["python", "-m", "tools.x"])').body[0].value)
            True
            >>> visitor.is_command_call_running_tools(ast.parse('subprocess.run(args=["python", "tools/x.py"])').body[0].value)
            True
            >>> visitor.is_command_call_running_tools(ast.parse('os.spawnl(os.P_WAIT, "python", "python", "tools/x.py")').body[0].value)
            True
        """
        if self.is_subprocess_command_call(node):
            return any(
                self.expression_or_alias_runs_tools_script(command)
                for command in self.subprocess_command_arguments(node)
            )
        os_method = self.os_command_method_name(node)
        if os_method is not None:
            command_args = (
                node.args[1:] if os_method.startswith("spawn") else node.args[:1]
            )
            return any(
                self.expression_or_alias_runs_tools_script(command)
                for command in command_args
            )
        return False

    def subprocess_command_arguments(self, node: ast.Call) -> List[ast.AST]:
        """
        Return command argument expressions for a subprocess call.

        :param node: Subprocess call expression.
        :type node: ast.Call
        :return: Candidate command argument expressions.
        :rtype: List[ast.AST]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> call = ast.parse('subprocess.run(args=["python"])').body[0].value
            >>> len(visitor.subprocess_command_arguments(call))
            1
        """
        if node.args:
            return [node.args[0]]
        for keyword in node.keywords:
            if keyword.arg == "args":
                return [keyword.value]
        return []

    def expression_or_alias_runs_tools_script(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` is a tools command literal or known alias.

        :param node: Command expression node.
        :type node: ast.AST
        :return: ``True`` when the expression targets repository tools.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.tools_command_aliases.add('cmd')
            >>> visitor.expression_or_alias_runs_tools_script(ast.Name(id='cmd'))
            True
            >>> expr = ast.parse('str(cmd)').body[0].value
            >>> visitor.expression_or_alias_runs_tools_script(expr)
            True
        """
        if any(
            isinstance(child, ast.Name) and child.id in self.tools_command_aliases
            for child in ast.walk(node)
        ):
            return True
        return expression_runs_tools_script(node)

    def is_subprocess_command_call(self, node: ast.Call) -> bool:
        """
        Return whether a call is a subprocess command invocation.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when the callee is subprocess-like.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_subprocess_command_call(ast.parse('subprocess.run([])').body[0].value)
            True
        """
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in _SUBPROCESS_METHODS and isinstance(
                node.func.value, ast.Name
            ):
                return node.func.value.id in self.subprocess_aliases
        if isinstance(node.func, ast.Name):
            return node.func.id in self.subprocess_function_aliases
        return False

    def is_os_command_call(self, node: ast.Call) -> bool:
        """
        Return whether a call is an OS shell command invocation.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when the callee is OS-command-like.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_os_command_call(ast.parse('os.system("true")').body[0].value)
            True
        """
        return self.os_command_method_name(node) is not None

    def os_command_method_name(self, node: ast.Call) -> Optional[str]:
        """
        Return the :mod:`os` command helper name called by ``node``.

        :param node: Call expression node.
        :type node: ast.Call
        :return: OS command helper name, or ``None``.
        :rtype: str, optional

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.os_command_method_name(ast.parse('os.system("true")').body[0].value)
            'system'
        """
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in _OS_COMMAND_METHODS and isinstance(
                node.func.value, ast.Name
            ):
                if node.func.value.id in self.os_aliases:
                    return node.func.attr
        if isinstance(node.func, ast.Name):
            if node.func.id in self.os_function_aliases:
                return node.func.id
        return None

    def is_repo_root_tainted(self, node: ast.AST) -> bool:
        """
        Return whether an expression is rooted at the repository directory.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` for repo-root-like expressions or aliases.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_repo_root_tainted(ast.parse('Path(__file__).parents[2]').body[0].value)
            True
        """
        if isinstance(node, ast.Name):
            return node.id in self.repo_root_aliases or is_repo_root_name(node.id)
        if is_file_parents_expr(node):
            return True
        if isinstance(node, ast.Call):
            if self.os_path_dirname_depth(node) >= 2:
                return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self.is_repo_root_tainted(node.left) or self.is_repo_root_tainted(
                node.right
            )
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in {"resolve", "absolute", "joinpath"}:
                    return self.is_repo_root_tainted(node.func.value)
            if dotted_name(node.func) in {"Path", "pathlib.Path"} and node.args:
                if self.is_repo_root_tainted(node.args[0]):
                    return True
                return any(is_exact_segment(arg, "templates") for arg in node.args[1:])
            if self.is_os_path_abspath_call(node) and node.args:
                return node_contains_name(
                    node.args[0], "__file__"
                ) or self.is_repo_root_tainted(node.args[0])
            if self.is_os_path_join_call(node) and node.args:
                return self.is_repo_root_tainted(node.args[0])
        return False

    def is_os_path_join_call(self, node: ast.Call) -> bool:
        """
        Return whether a call targets ``os.path.join``.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when the callee is ``os.path.join`` or an alias.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_os_path_join_call(ast.parse('os.path.join("a", "b")').body[0].value)
            True
        """
        if dotted_name(node.func) == "os.path.join":
            return True
        return (
            isinstance(node.func, ast.Name)
            and node.func.id in self.os_path_join_aliases
        )

    def is_os_path_dirname_call(self, node: ast.Call) -> bool:
        """
        Return whether a call targets ``os.path.dirname``.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when the callee is ``os.path.dirname`` or an alias.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_os_path_dirname_call(ast.parse('os.path.dirname(__file__)').body[0].value)
            True
        """
        if dotted_name(node.func) == "os.path.dirname":
            return True
        return (
            isinstance(node.func, ast.Name)
            and node.func.id in self.os_path_dirname_aliases
        )

    def is_os_path_abspath_call(self, node: ast.Call) -> bool:
        """
        Return whether a call targets ``os.path.abspath``.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when the callee is ``os.path.abspath`` or an alias.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_os_path_abspath_call(ast.parse('os.path.abspath(__file__)').body[0].value)
            True
        """
        if dotted_name(node.func) == "os.path.abspath":
            return True
        return (
            isinstance(node.func, ast.Name)
            and node.func.id in self.os_path_abspath_aliases
        )

    def os_path_dirname_depth(self, node: ast.AST) -> int:
        """
        Return nested ``os.path.dirname`` depth from a ``__file__`` path.

        :param node: AST node to inspect.
        :type node: ast.AST
        :return: Number of nested dirname calls rooted at ``__file__``.
        :rtype: int

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> expr = ast.parse('os.path.dirname(os.path.dirname(os.path.abspath(__file__)))').body[0].value
            >>> visitor.os_path_dirname_depth(expr)
            2
        """
        depth = 0
        current = node
        while isinstance(current, ast.Call):
            if self.is_os_path_abspath_call(current) and current.args:
                current = current.args[0]
                continue
            if self.is_os_path_dirname_call(current) and current.args:
                depth += 1
                current = current.args[0]
                continue
            break
        if depth and node_contains_name(current, "__file__"):
            return depth
        return 0

    def is_repo_source_template_access(self, node: ast.AST) -> bool:
        """
        Return whether an expression accesses repo-root ``templates``.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` when repo-root taint combines with exact ``templates``.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_repo_source_template_access(ast.parse('_REPO_ROOT / "templates"').body[0].value)
            True
        """
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return (
                self.is_repo_root_tainted(node.left)
                and self.expression_has_exact_segment(node.right, "templates")
            ) or (
                self.is_repo_root_tainted(node.right)
                and self.expression_has_exact_segment(node.left, "templates")
            )
        if isinstance(node, ast.Call):
            if dotted_name(node.func) in {"Path", "pathlib.Path"} and node.args:
                if self.is_repo_root_tainted(node.args[0]):
                    return any(
                        is_exact_segment(arg, "templates") for arg in node.args[1:]
                    )
            if isinstance(node.func, ast.Attribute) and node.func.attr == "joinpath":
                if self.is_repo_root_tainted(node.func.value):
                    return any(is_exact_segment(arg, "templates") for arg in node.args)
            if self.is_os_path_join_call(node) and node.args:
                if self.is_repo_root_tainted(node.args[0]):
                    return any(
                        is_exact_segment(arg, "templates") for arg in node.args[1:]
                    )
        return False

    def expression_has_exact_segment(self, node: ast.AST, segment: str) -> bool:
        """
        Return whether an expression contains an exact string segment.

        :param node: AST expression node.
        :type node: ast.AST
        :param segment: String segment to search for.
        :type segment: str
        :return: ``True`` when the exact segment appears.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.expression_has_exact_segment(ast.parse('"templates"').body[0].value, 'templates')
            True
        """
        if is_exact_segment(node, segment):
            return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self.expression_has_exact_segment(
                node.left, segment
            ) or self.expression_has_exact_segment(node.right, segment)
        if isinstance(node, ast.Call):
            return any(is_exact_segment(arg, segment) for arg in node.args)
        return False


def collect_docstring_node_ids(tree: ast.AST) -> Set[int]:
    """
    Collect AST node identifiers for module, class, and function docstrings.

    :param tree: Parsed Python AST.
    :type tree: ast.AST
    :return: ``id()`` values for string literal nodes used as docstrings.
    :rtype: Set[int]

    Example::

        >>> source = "'''source install note'''" + chr(10) + "x = 'source install'"
        >>> tree = ast.parse(source)
        >>> len(collect_docstring_node_ids(tree))
        1
    """
    docstring_node_ids = set()
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and literal_string(first.value) is not None:
            docstring_node_ids.add(id(first.value))
    return docstring_node_ids


def scan_source(path: Path, relative_path: Path, source: str) -> List[BoundaryFinding]:
    """
    Scan one Python test source file.

    :param path: Absolute source path, used for parser diagnostics.
    :type path: pathlib.Path
    :param relative_path: Path to report in findings.
    :type relative_path: pathlib.Path
    :param source: Python source text.
    :type source: str
    :return: Boundary findings for the file.
    :rtype: List[BoundaryFinding]
    :raises SyntaxError: If the source cannot be parsed as Python.

    Example::

        >>> scan_source(Path('x.py'), Path('x.py'), 'import os')
        []
        >>> scan_source(Path('x.py'), Path('x.py'), "'''source install note'''")
        []
    """
    tree = ast.parse(source, filename=str(path))
    visitor = TestBoundaryVisitor(
        relative_path,
        source,
        collect_defined_names(tree),
        collect_docstring_node_ids(tree),
    )
    visitor.visit(tree)
    return visitor.findings


def scan_tests(repo_root: Path) -> List[BoundaryFinding]:
    """
    Scan all Python files under ``test``.

    :param repo_root: Repository root directory.
    :type repo_root: pathlib.Path
    :return: Sorted boundary findings.
    :rtype: List[BoundaryFinding]
    :raises OSError: If a test file cannot be read.
    :raises SyntaxError: If a test file cannot be parsed.

    Example::

        >>> isinstance(scan_tests(repository_root()), list)
        True
    """
    test_root = repo_root / "test"
    findings = []
    for path in iter_python_files(test_root):
        relative_path = path.relative_to(repo_root)
        findings.extend(scan_source(path, relative_path, read_source(path)))
    return sorted(
        findings,
        key=lambda item: (item.path.as_posix(), item.line, item.column, item.rule),
    )


def format_findings(findings: Sequence[BoundaryFinding]) -> str:
    """
    Format findings for command-line output.

    :param findings: Boundary findings to format.
    :type findings: Sequence[BoundaryFinding]
    :return: Multi-line diagnostic text.
    :rtype: str

    Example::

        >>> format_findings([])
        'test boundary check passed: no violations found'
    """
    if not findings:
        return "test boundary check passed: no violations found"
    lines = [
        "test boundary check failed: {count} violation(s) found".format(
            count=len(findings)
        )
    ]
    for finding in findings:
        lines.append(
            "{location}: {rule}: {message}".format(
                location=finding.location,
                rule=finding.rule,
                message=finding.message,
            )
        )
        if finding.source:
            lines.append("    {source}".format(source=finding.source))
    return os.linesep.join(lines)


def run_check(repo_root: Path) -> int:
    """
    Run the test-boundary check.

    :param repo_root: Repository root directory.
    :type repo_root: pathlib.Path
    :return: Process-style exit code, ``0`` when no findings exist.
    :rtype: int

    Example::

        >>> run_check(repository_root()) in (0, 1)  # doctest: +ELLIPSIS
        test boundary check ...
        True
    """
    findings = scan_tests(repo_root)
    print(format_findings(findings))
    return 1 if findings else 0


def main(argv: Optional[List[str]] = None) -> int:
    """
    Run the command-line test-boundary check.

    :param argv: Optional command-line arguments, defaults to ``None``.
    :type argv: List[str], optional
    :return: Process exit code.
    :rtype: int

    Example::

        >>> main(['--repo-root', str(repository_root())]) in (0, 1)  # doctest: +ELLIPSIS
        test boundary check ...
        True
    """
    parser = argparse.ArgumentParser(
        description="Validate pytest boundary rules for repository tests."
    )
    parser.add_argument(
        "--repo-root",
        default=str(repository_root()),
        help="Repository root to scan. Defaults to the parent of this tools directory.",
    )
    args = parser.parse_args(argv)
    return run_check(Path(args.repo_root).resolve())


if __name__ == "__main__":
    raise SystemExit(main())
