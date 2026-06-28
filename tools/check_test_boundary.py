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
from typing import Dict, Iterable, List, Optional, Sequence, Set


AST_CONSTANT_TYPE = getattr(ast, "Constant", None)
AST_INDEX_TYPE = getattr(ast, "Index", None)
AST_NUM_TYPE = getattr(ast, "Num", None)
AST_STR_TYPE = getattr(ast, "Str", None) if sys.version_info < (3, 8) else None


_STATIC_STRING_METHODS = {
    "casefold",
    "lower",
    "upper",
}
_PATH_CONSTRUCTOR_NAMES = {
    "Path",
    "PurePath",
    "PurePosixPath",
    "PureWindowsPath",
    "PosixPath",
    "WindowsPath",
}
_OS_PATH_PASSTHROUGH_HELPERS = {
    "abspath",
    "normpath",
    "realpath",
}
_OS_PATH_HELPERS = {
    "abspath",
    "dirname",
    "join",
    "normpath",
    "realpath",
    "split",
}
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
    "execl",
    "execle",
    "execlp",
    "execlpe",
    "execv",
    "execve",
    "execvp",
    "execvpe",
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
_REPO_ROOT_NAME_FRAGMENTS = (
    "repo_root",
    "repository_root",
)


@dataclass
class NameScope:
    """
    Track bindings and tainted aliases visible inside one lexical scope.

    :param defined_names: Names bound by ordinary statements in the scope.
    :type defined_names: Set[str]
    :param shadowing_names: Non-import bindings that shadow same-scope import
        aliases and outer-scope names.
    :type shadowing_names: Set[str]
    :param tools_aliases: Names known to refer to repository ``tools`` modules.
    :type tools_aliases: Set[str]
    :param dynamic_tools_aliases: Names assigned from dynamic ``tools`` imports.
    :type dynamic_tools_aliases: Set[str]
    :param importlib_aliases: Names that expose ``importlib.import_module``.
    :type importlib_aliases: Set[str]
    :param importlib_util_aliases: Names that expose the :mod:`importlib.util`
        module.
    :type importlib_util_aliases: Set[str]
    :param importlib_util_spec_aliases: Names imported from
        :func:`importlib.util.spec_from_file_location`.
    :type importlib_util_spec_aliases: Set[str]
    :param builtins_aliases: Names that expose the :mod:`builtins` module.
    :type builtins_aliases: Set[str]
    :param pathlib_aliases: Names that expose the :mod:`pathlib` module.
    :type pathlib_aliases: Set[str]
    :param path_class_aliases: Names that expose :class:`pathlib.Path` or
        compatible :mod:`pathlib` path constructors.
    :type path_class_aliases: Set[str]
    :param pytest_aliases: Names that expose the :mod:`pytest` module.
    :type pytest_aliases: Set[str]
    :param pytest_importorskip_aliases: Names imported from
        :func:`pytest.importorskip`.
    :type pytest_importorskip_aliases: Set[str]
    :param runpy_aliases: Names that expose the :mod:`runpy` module.
    :type runpy_aliases: Set[str]
    :param runpy_run_module_aliases: Names imported from
        :func:`runpy.run_module`.
    :type runpy_run_module_aliases: Set[str]
    :param runpy_run_path_aliases: Names imported from :func:`runpy.run_path`.
    :type runpy_run_path_aliases: Set[str]
    :param sys_aliases: Names that expose the :mod:`sys` module.
    :type sys_aliases: Set[str]
    :param sys_modules_aliases: Names imported from :data:`sys.modules`.
    :type sys_modules_aliases: Set[str]
    :param sys_modules_getitem_aliases: Names that expose
        ``sys.modules.__getitem__``.
    :type sys_modules_getitem_aliases: Set[str]
    :param sys_modules_get_aliases: Names that expose ``sys.modules.get``.
    :type sys_modules_get_aliases: Set[str]
    :param subprocess_aliases: Names that expose the :mod:`subprocess` module.
    :type subprocess_aliases: Set[str]
    :param subprocess_function_aliases: Names imported from subprocess command helpers.
    :type subprocess_function_aliases: Set[str]
    :param os_aliases: Names that expose the :mod:`os` module.
    :type os_aliases: Set[str]
    :param os_function_aliases: Names imported from OS command helpers.
    :type os_function_aliases: Set[str]
    :param os_function_alias_methods: Original OS command helper names by local
        alias.
    :type os_function_alias_methods: Dict[str, str]
    :param os_path_aliases: Names that expose the :mod:`os.path` module.
    :type os_path_aliases: Set[str]
    :param os_path_join_aliases: Names imported from ``os.path.join``.
    :type os_path_join_aliases: Set[str]
    :param os_path_dirname_aliases: Names imported from ``os.path.dirname``.
    :type os_path_dirname_aliases: Set[str]
    :param os_path_abspath_aliases: Names imported from path-preserving
        :mod:`os.path` helpers such as ``abspath``, ``normpath``, or
        ``realpath``.
    :type os_path_abspath_aliases: Set[str]
    :param os_path_split_aliases: Names imported from ``os.path.split``.
    :type os_path_split_aliases: Set[str]
    :param os_getcwd_aliases: Names imported from ``os.getcwd``.
    :type os_getcwd_aliases: Set[str]
    :param repo_root_aliases: Names assigned from repository-root expressions.
    :type repo_root_aliases: Set[str]
    :param path_parent_hop_aliases: Parent-hop counts for path expressions rooted at
        ``__file__`` but not necessarily at repo root yet.
    :type path_parent_hop_aliases: Dict[str, int]
    :param file_parents_aliases: Names assigned from ``Path(__file__).parents``
        sequence expressions.
    :type file_parents_aliases: Set[str]
    :param string_aliases: Statically known string values by local name.
    :type string_aliases: Dict[str, str]
    :param dynamic_code_alias_rules: Boundary rules found in compiled dynamic
        code by local name.
    :type dynamic_code_alias_rules: Dict[str, str]
    :param template_segment_aliases: Names assigned from the exact path segment
        ``"templates"``.
    :type template_segment_aliases: Set[str]
    :param tools_module_name_aliases: Names assigned from ``tools`` module-name
        strings.
    :type tools_module_name_aliases: Set[str]
    :param tools_command_aliases: Names assigned from commands that execute tools scripts.
    :type tools_command_aliases: Set[str]
    :param source_install_command_aliases: Names assigned from source-install commands.
    :type source_install_command_aliases: Set[str]
    :param package_templates_aliases: Names imported from ``tools.package_templates``.
    :type package_templates_aliases: Set[str]
    :param is_class_body: Whether this scope models a class namespace.
    :type is_class_body: bool

    Example::

        >>> scope = NameScope.create(defined_names={'tools'})
        >>> 'tools' in scope.defined_names
        True
    """

    defined_names: Set[str]
    shadowing_names: Set[str]
    tools_aliases: Set[str]
    dynamic_tools_aliases: Set[str]
    importlib_aliases: Set[str]
    importlib_util_aliases: Set[str]
    importlib_util_spec_aliases: Set[str]
    builtins_aliases: Set[str]
    pathlib_aliases: Set[str]
    path_class_aliases: Set[str]
    pytest_aliases: Set[str]
    pytest_importorskip_aliases: Set[str]
    runpy_aliases: Set[str]
    runpy_run_module_aliases: Set[str]
    runpy_run_path_aliases: Set[str]
    sys_aliases: Set[str]
    sys_modules_aliases: Set[str]
    sys_modules_getitem_aliases: Set[str]
    sys_modules_get_aliases: Set[str]
    subprocess_aliases: Set[str]
    subprocess_function_aliases: Set[str]
    os_aliases: Set[str]
    os_function_aliases: Set[str]
    os_function_alias_methods: Dict[str, str]
    os_path_aliases: Set[str]
    os_path_join_aliases: Set[str]
    os_path_dirname_aliases: Set[str]
    os_path_abspath_aliases: Set[str]
    os_path_split_aliases: Set[str]
    os_getcwd_aliases: Set[str]
    repo_root_aliases: Set[str]
    path_parent_hop_aliases: Dict[str, int]
    file_parents_aliases: Set[str]
    string_aliases: Dict[str, str]
    dynamic_code_alias_rules: Dict[str, str]
    template_segment_aliases: Set[str]
    tools_module_name_aliases: Set[str]
    tools_command_aliases: Set[str]
    source_install_command_aliases: Set[str]
    package_templates_aliases: Set[str]
    is_class_body: bool = False

    @classmethod
    def create(
        cls,
        defined_names: Optional[Set[str]] = None,
        shadowing_names: Optional[Set[str]] = None,
        importlib_aliases: Optional[Set[str]] = None,
        builtins_aliases: Optional[Set[str]] = None,
        pathlib_aliases: Optional[Set[str]] = None,
        path_class_aliases: Optional[Set[str]] = None,
        pytest_aliases: Optional[Set[str]] = None,
        runpy_aliases: Optional[Set[str]] = None,
        sys_aliases: Optional[Set[str]] = None,
        subprocess_aliases: Optional[Set[str]] = None,
        os_aliases: Optional[Set[str]] = None,
        is_class_body: bool = False,
    ) -> "NameScope":
        """
        Create a scope with optional predefined bindings.

        :param defined_names: Ordinary names bound in this scope, defaults to ``None``.
        :type defined_names: Set[str], optional
        :param shadowing_names: Non-import bindings that shadow aliases, defaults
            to ``None``.
        :type shadowing_names: Set[str], optional
        :param importlib_aliases: Predefined importlib aliases, defaults to ``None``.
        :type importlib_aliases: Set[str], optional
        :param builtins_aliases: Predefined builtins aliases, defaults to ``None``.
        :type builtins_aliases: Set[str], optional
        :param pathlib_aliases: Predefined pathlib aliases, defaults to ``None``.
        :type pathlib_aliases: Set[str], optional
        :param path_class_aliases: Predefined Path class aliases, defaults to
            ``None``.
        :type path_class_aliases: Set[str], optional
        :param pytest_aliases: Predefined pytest aliases, defaults to ``None``.
        :type pytest_aliases: Set[str], optional
        :param runpy_aliases: Predefined runpy aliases, defaults to ``None``.
        :type runpy_aliases: Set[str], optional
        :param sys_aliases: Predefined sys aliases, defaults to ``None``.
        :type sys_aliases: Set[str], optional
        :param subprocess_aliases: Predefined subprocess aliases, defaults to ``None``.
        :type subprocess_aliases: Set[str], optional
        :param os_aliases: Predefined os aliases, defaults to ``None``.
        :type os_aliases: Set[str], optional
        :param is_class_body: Whether the scope is a class namespace, defaults to ``False``.
        :type is_class_body: bool, optional
        :return: New lexical scope state.
        :rtype: NameScope

        Example::

            >>> scope = NameScope.create(importlib_aliases={'importlib'})
            >>> 'importlib' in scope.importlib_aliases
            True
        """
        return cls(
            defined_names=set(defined_names or set()),
            shadowing_names=set(shadowing_names or set()),
            tools_aliases=set(),
            dynamic_tools_aliases=set(),
            importlib_aliases=set(importlib_aliases or set()),
            importlib_util_aliases=set(),
            importlib_util_spec_aliases=set(),
            builtins_aliases=set(builtins_aliases or set()),
            pathlib_aliases=set(pathlib_aliases or set()),
            path_class_aliases=set(path_class_aliases or set()),
            pytest_aliases=set(pytest_aliases or set()),
            pytest_importorskip_aliases=set(),
            runpy_aliases=set(runpy_aliases or set()),
            runpy_run_module_aliases=set(),
            runpy_run_path_aliases=set(),
            sys_aliases=set(sys_aliases or set()),
            sys_modules_aliases=set(),
            sys_modules_getitem_aliases=set(),
            sys_modules_get_aliases=set(),
            subprocess_aliases=set(subprocess_aliases or set()),
            subprocess_function_aliases=set(),
            os_aliases=set(os_aliases or set()),
            os_function_aliases=set(),
            os_function_alias_methods={},
            os_path_aliases=set(),
            os_path_join_aliases=set(),
            os_path_dirname_aliases=set(),
            os_path_abspath_aliases=set(),
            os_path_split_aliases=set(),
            os_getcwd_aliases=set(),
            repo_root_aliases=set(),
            path_parent_hop_aliases={},
            file_parents_aliases=set(),
            string_aliases={},
            dynamic_code_alias_rules={},
            template_segment_aliases=set(),
            tools_module_name_aliases=set(),
            tools_command_aliases=set(),
            source_install_command_aliases=set(),
            package_templates_aliases=set(),
            is_class_body=is_class_body,
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
    Return a statically known string value from an AST node.

    :param node: AST node to inspect.
    :type node: ast.AST
    :return: String literal value, or ``None`` when the node is not a string.
    :rtype: str, optional

    Example::

        >>> literal_string(ast.parse('"x"').body[0].value)
        'x'
        >>> literal_string(ast.parse('"tem" + "plates"').body[0].value)
        'templates'
        >>> literal_string(ast.parse('f"tools.package_templates"').body[0].value)
        'tools.package_templates'
        >>> literal_string(ast.parse('chr(116) + "ools"').body[0].value)
        'tools'
        >>> literal_string(ast.parse('"TEMPLATES".lower()').body[0].value)
        'templates'
        >>> literal_string(ast.parse('b"templates".decode()').body[0].value)
        'templates'
    """
    if AST_STR_TYPE is not None and isinstance(node, AST_STR_TYPE):
        return getattr(node, "s")
    if AST_CONSTANT_TYPE is not None and isinstance(node, AST_CONSTANT_TYPE):
        if isinstance(node.value, str):
            return node.value
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.FormattedValue):
                if value.format_spec is not None:
                    return None
                part = literal_string(value.value)
            else:
                part = literal_string(value)
            if part is None:
                return None
            parts.append(part)
        return "".join(parts)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = literal_string(node.left)
        right = literal_string(node.right)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.Call):
        if (
            dotted_name(node.func) == "chr"
            and len(node.args) == 1
            and not node.keywords
        ):
            codepoint = literal_integer(node.args[0])
            if codepoint is not None and 0 <= codepoint <= 0x10FFFF:
                return chr(codepoint)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in _STATIC_STRING_METHODS:
                if node.args or node.keywords:
                    return None
                value = literal_string(node.func.value)
                if value is None:
                    return None
                if node.func.attr == "lower":
                    return value.lower()
                if node.func.attr == "upper":
                    return value.upper()
                return value.casefold()
            if node.func.attr == "decode":
                return literal_decode_call_string(node)
    return None


def literal_decode_call_string(node: ast.Call) -> Optional[str]:
    """
    Return the static string produced by a bytes ``decode`` call.

    :param node: Call expression to inspect.
    :type node: ast.Call
    :return: Decoded string, or ``None`` when the call is not static.
    :rtype: str, optional

    Example::

        >>> literal_decode_call_string(ast.parse('b"tools".decode("ascii")').body[0].value)
        'tools'
    """
    if not isinstance(node.func, ast.Attribute) or node.func.attr != "decode":
        return None
    if len(node.args) > 1 or node.keywords:
        return None
    value = literal_bytes(node.func.value)
    if value is None:
        return None
    encoding = "utf-8"
    if node.args:
        static_encoding = literal_string(node.args[0])
        if static_encoding is None:
            return None
        encoding = static_encoding
    try:
        return value.decode(encoding)
    except (LookupError, UnicodeDecodeError):
        # LookupError: static encoding literal is not a known codec.
        # UnicodeDecodeError: static bytes cannot be decoded with that codec.
        return None


def literal_bytes(node: ast.AST) -> Optional[bytes]:
    """
    Return a static bytes literal value.

    :param node: AST node to inspect.
    :type node: ast.AST
    :return: Bytes value, or ``None`` when the node is not a bytes literal.
    :rtype: bytes, optional

    Example::

        >>> literal_bytes(ast.parse('b"x"').body[0].value)
        b'x'
    """
    if AST_CONSTANT_TYPE is not None and isinstance(node, AST_CONSTANT_TYPE):
        if isinstance(node.value, bytes):
            return node.value
    return None


def literal_integer(node: ast.AST) -> Optional[int]:
    """
    Return a static integer literal value.

    :param node: AST node to inspect.
    :type node: ast.AST
    :return: Integer value, or ``None`` when the node is not an integer literal.
    :rtype: int, optional

    Example::

        >>> literal_integer(ast.parse('116').body[0].value)
        116
    """
    if isinstance(node, int):
        return node
    if AST_CONSTANT_TYPE is not None and isinstance(node, AST_CONSTANT_TYPE):
        if isinstance(node.value, int) and not isinstance(node.value, bool):
            return node.value
    if AST_NUM_TYPE is not None and isinstance(node, AST_NUM_TYPE):
        number = getattr(node, "n", None)
        if isinstance(number, int) and not isinstance(number, bool):
            return number
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
    Collect module-scope names that make bare names look locally defined.

    :param tree: Parsed Python AST.
    :type tree: ast.AST
    :return: Module-scope defined names.
    :rtype: Set[str]

    Example::

        >>> tree = ast.parse('def f(): pass')
        >>> collect_defined_names(tree)
        {'f'}
        >>> tree = ast.parse('package_templates = lambda: None')
        >>> 'package_templates' in collect_defined_names(tree)
        True
        >>> tree = ast.parse('def f():\\n    tools = object()')
        >>> 'tools' in collect_defined_names(tree)
        False
    """
    return collect_scope_defined_names(getattr(tree, "body", []), include_imports=True)


def collect_scope_defined_names(
    statements: Sequence[ast.AST], include_imports: bool = True
) -> Set[str]:
    """
    Collect names bound directly in a lexical statement scope.

    Nested function and class bodies are intentionally not traversed because
    their local bindings must not shadow sibling functions in the containing
    module.

    :param statements: Statements that make up one lexical scope body.
    :type statements: Sequence[ast.AST]
    :param include_imports: Whether import statements count as ordinary
        definitions, defaults to ``True``.
    :type include_imports: bool, optional
    :return: Names bound in that scope.
    :rtype: Set[str]

    Example::

        >>> tree = ast.parse('def f():\\n    tools = object()\\ndef g(): pass')
        >>> sorted(collect_scope_defined_names(tree.body))
        ['f', 'g']
        >>> func = tree.body[0]
        >>> 'tools' in collect_scope_defined_names(func.body)
        True
    """
    names = set()
    for statement in statements:
        names.update(
            statement_defined_names(statement, include_imports=include_imports)
        )
    return names


def statement_defined_names(
    statement: ast.AST, include_imports: bool = True
) -> Set[str]:
    """
    Collect names bound by one statement in its current lexical scope.

    :param statement: Statement node to inspect.
    :type statement: ast.AST
    :param include_imports: Whether import statements count as definitions,
        defaults to ``True``.
    :type include_imports: bool, optional
    :return: Names bound by the statement or nested same-scope branches.
    :rtype: Set[str]

    Example::

        >>> statement_defined_names(ast.parse('for tools in items:\\n    pass').body[0])
        {'tools'}
    """
    names = set()
    if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return {statement.name}
    if isinstance(statement, ast.Import) and include_imports:
        for alias in statement.names:
            names.add(alias.asname or alias.name.split(".")[0])
    elif isinstance(statement, ast.ImportFrom) and include_imports:
        for alias in statement.names:
            names.add(alias.asname or alias.name)
    elif isinstance(statement, ast.Assign):
        for target in statement.targets:
            names.update(assigned_target_names(target))
    elif isinstance(statement, ast.AnnAssign):
        names.update(assigned_target_names(statement.target))
    elif isinstance(statement, ast.AugAssign):
        names.update(assigned_target_names(statement.target))
    elif isinstance(statement, (ast.For, ast.AsyncFor)):
        names.update(assigned_target_names(statement.target))
        names.update(
            collect_scope_defined_names(statement.body, include_imports=include_imports)
        )
        names.update(
            collect_scope_defined_names(
                statement.orelse, include_imports=include_imports
            )
        )
    elif isinstance(statement, (ast.With, ast.AsyncWith)):
        for item in statement.items:
            if item.optional_vars is not None:
                names.update(assigned_target_names(item.optional_vars))
        names.update(
            collect_scope_defined_names(statement.body, include_imports=include_imports)
        )
    elif isinstance(statement, ast.If):
        names.update(
            collect_scope_defined_names(statement.body, include_imports=include_imports)
        )
        names.update(
            collect_scope_defined_names(
                statement.orelse, include_imports=include_imports
            )
        )
    elif isinstance(statement, ast.While):
        names.update(
            collect_scope_defined_names(statement.body, include_imports=include_imports)
        )
        names.update(
            collect_scope_defined_names(
                statement.orelse, include_imports=include_imports
            )
        )
    elif isinstance(statement, ast.Try):
        names.update(
            collect_scope_defined_names(statement.body, include_imports=include_imports)
        )
        names.update(
            collect_scope_defined_names(
                statement.orelse, include_imports=include_imports
            )
        )
        names.update(
            collect_scope_defined_names(
                statement.finalbody, include_imports=include_imports
            )
        )
        for handler in statement.handlers:
            if handler.name:
                names.add(handler.name)
            names.update(
                collect_scope_defined_names(
                    handler.body, include_imports=include_imports
                )
            )
    return names


def collect_shadowing_names(statements: Sequence[ast.AST]) -> Set[str]:
    """
    Collect non-import names that shadow aliases in one scope.

    :param statements: Statements that make up one lexical scope body.
    :type statements: Sequence[ast.AST]
    :return: Names introduced by non-import bindings.
    :rtype: Set[str]

    Example::

        >>> tree = ast.parse('import tools\\ndef tools(): pass')
        >>> collect_shadowing_names(tree.body)
        {'tools'}
    """
    return collect_scope_defined_names(statements, include_imports=False)


def function_argument_names(arguments: ast.arguments) -> Set[str]:
    """
    Collect names bound by a function or lambda argument list.

    :param arguments: Function argument node.
    :type arguments: ast.arguments
    :return: Argument names bound in the function scope.
    :rtype: Set[str]

    Example::

        >>> func = ast.parse('def f(pos, /, x, *args, y, **kwargs): pass').body[0]
        >>> sorted(function_argument_names(func.args))
        ['args', 'kwargs', 'pos', 'x', 'y']
    """
    names = set()
    for argument in list(getattr(arguments, "posonlyargs", [])) + list(arguments.args):
        names.add(argument.arg)
    for argument in arguments.kwonlyargs:
        names.add(argument.arg)
    if arguments.vararg is not None:
        names.add(arguments.vararg.arg)
    if arguments.kwarg is not None:
        names.add(arguments.kwarg.arg)
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


def is_pip_command_token(token: str) -> bool:
    """
    Return whether ``token`` is a direct pip executable name.

    :param token: Command token to inspect.
    :type token: str
    :return: ``True`` for ``pip`` and versioned ``pip`` executable names.
    :rtype: bool

    Example::

        >>> is_pip_command_token('pip')
        True
        >>> is_pip_command_token('pip3.10')
        True
        >>> is_pip_command_token('pip-tools')
        False
    """
    if token == "pip":
        return True
    if not token.startswith("pip"):
        return False
    suffix = token[3:]
    if not suffix:
        return True
    parts = suffix.split(".")
    return all(part.isdigit() for part in parts)


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


def subscript_integer(node: ast.Subscript) -> Optional[int]:
    """
    Return an integer literal subscript index when available.

    Python 3.7 parses ``x[2]`` as ``ast.Index(ast.Num(2))``, while newer
    versions expose the literal directly as :class:`ast.Constant`. This helper
    normalizes both layouts before reading the integer.

    :param node: Subscript node to inspect.
    :type node: ast.Subscript
    :return: Integer index, or ``None`` when not statically literal.
    :rtype: int, optional

    Example::

        >>> subscript_integer(ast.parse('x[2]').body[0].value)
        2
    """
    value = node.slice
    if AST_INDEX_TYPE is not None and isinstance(value, AST_INDEX_TYPE):
        value = value.value
    if isinstance(value, int):
        return value
    if AST_CONSTANT_TYPE is not None and isinstance(value, AST_CONSTANT_TYPE):
        if isinstance(value.value, int):
            return value.value
    if AST_NUM_TYPE is not None and isinstance(value, AST_NUM_TYPE):
        number = getattr(value, "n", None)
        if isinstance(number, int):
            return number
    return None


def is_exact_segment(node: ast.AST, segment: str) -> bool:
    """
    Return whether ``node`` contains an exact path segment.

    :param node: AST node to inspect.
    :type node: ast.AST
    :param segment: Expected path segment.
    :type segment: str
    :return: ``True`` when ``node`` contains that exact path segment.
    :rtype: bool

    Example::

        >>> is_exact_segment(ast.parse('"templates"').body[0].value, 'templates')
        True
        >>> is_exact_segment(ast.parse('"/repo/templates"').body[0].value, 'templates')
        True
        >>> is_exact_segment(ast.parse('"harness_templates"').body[0].value, 'templates')
        False
    """
    value = literal_string(node)
    if value is None:
        return False
    return segment in path_segments(value)


def path_segments(value: str) -> List[str]:
    """
    Split a path-like literal into non-empty slash-delimited segments.

    Both POSIX and Windows separators are normalized so exact segment checks can
    recognize ``templates`` without treating ``harness_templates`` as a match.

    :param value: String literal value to split.
    :type value: str
    :return: Non-empty path segments.
    :rtype: List[str]

    Example::

        >>> path_segments('/repo/templates')
        ['repo', 'templates']
        >>> path_segments('harness_templates')
        ['harness_templates']
    """
    return [segment for segment in value.replace("\\", "/").split("/") if segment]


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


def expression_runs_source_install_command(node: ast.AST) -> bool:
    """
    Return whether a command expression performs a source install.

    :param node: AST node for a subprocess or shell command argument.
    :type node: ast.AST
    :return: ``True`` when string literals form ``pip install`` of local source.
    :rtype: bool

    Example::

        >>> expression_runs_source_install_command(ast.parse('["python", "-m", "pip", "install", "."]').body[0].value)
        True
        >>> expression_runs_source_install_command(ast.parse('["pip", "install", "pytest"]').body[0].value)
        False
    """
    if isinstance(node, ast.Name):
        return False
    values = collect_string_literals(node)
    return any(
        string_contains_source_install_marker(value) for value in values
    ) or string_contains_source_install_marker(" ".join(values))


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

    The check intentionally requires a ``pip install`` command shape before
    treating local paths or ``--target`` as source-install smoke evidence. This
    avoids blocking ordinary test configuration keys such as ``install_dir`` or
    native compiler flags such as ``--target``.

    :param value: String literal value to inspect.
    :type value: str
    :return: ``True`` when the literal looks like a source-install smoke command.
    :rtype: bool

    Example::

        >>> string_contains_source_install_marker('pip install pytest')
        False
        >>> string_contains_source_install_marker('python -m pip install .')
        True
        >>> string_contains_source_install_marker('pip3 install .')
        True
        >>> string_contains_source_install_marker('pip3.10 install --target /tmp/x .')
        True
        >>> string_contains_source_install_marker('python setup.py install')
        True
        >>> string_contains_source_install_marker('python setup.py develop')
        True
        >>> string_contains_source_install_marker('pip-tools install .')
        False
        >>> string_contains_source_install_marker('clang --target x86_64-linux-gnu')
        False
    """
    normalized = value.lower().replace("\\", "/")
    tokens = normalized.split()
    for index in range(len(tokens) - 1):
        if tokens[index].endswith("setup.py") and tokens[index + 1] in {
            "install",
            "develop",
        }:
            return True
    for index in range(len(tokens) - 1):
        if not is_pip_command_token(tokens[index]) or tokens[index + 1] != "install":
            continue
        install_args = tokens[index + 2 :]
        for arg in install_args:
            if arg in {"-e", "--editable", ".", "./", "..", "../", "--target"}:
                return True
            if arg.startswith("--target="):
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
        shadowing_names: Optional[Set[str]] = None,
    ) -> None:
        self.path = path
        self.source_lines = source.splitlines()
        self.docstring_node_ids = docstring_node_ids or set()
        self.findings = []  # type: List[BoundaryFinding]
        self.scope_stack = [
            NameScope.create(
                defined_names=defined_names,
                shadowing_names=shadowing_names,
                importlib_aliases={"importlib"},
                builtins_aliases={"builtins"},
                pathlib_aliases={"pathlib"},
                path_class_aliases=set(_PATH_CONSTRUCTOR_NAMES),
                pytest_aliases={"pytest"},
                runpy_aliases={"runpy"},
                sys_aliases={"sys"},
                subprocess_aliases={"subprocess"},
                os_aliases={"os"},
            )
        ]  # type: List[NameScope]

    @property
    def current_scope(self) -> NameScope:
        """
        Return the innermost lexical scope currently being visited.

        :return: Current lexical scope state.
        :rtype: NameScope

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.defined_names
            set()
        """
        return self.scope_stack[-1]

    def visible_names(self, attribute: str) -> Set[str]:
        """
        Return one scope attribute with lexical shadowing applied.

        Ordinary ``defined_names`` are returned as the visible union because
        they model names that are already declared in the reachable lexical
        scopes and suppress unresolved bare ``tools`` call diagnostics. Tainted
        aliases use Python's lexical shadowing rule, so a local variable named
        ``subprocess`` or ``importlib`` blocks the module-level alias of the
        same name.

        :param attribute: :class:`NameScope` set attribute name.
        :type attribute: str
        :return: Names visible from outer scopes through the current scope.
        :rtype: Set[str]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', {'tools'})
            >>> 'tools' in visitor.visible_names('defined_names')
            True
            >>> visitor.current_scope.importlib_aliases.add('importlib')
            >>> visitor.push_scope({'importlib'})
            >>> 'importlib' in visitor.visible_names('importlib_aliases')
            False
        """
        if attribute == "defined_names":
            names = set()
            for scope in self.scope_stack:
                names.update(scope.defined_names)
            return names
        names = set()
        shadowed = set()
        for scope in reversed(self.scope_stack):
            names.update(
                name for name in getattr(scope, attribute) if name not in shadowed
            )
            shadowed.update(scope.shadowing_names)
            shadowed.update(scope.defined_names)
        return names

    @property
    def defined_names(self) -> Set[str]:
        """
        Return ordinary names visible in the current lexical scope.

        :return: Visible ordinary bindings.
        :rtype: Set[str]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', {'tools'})
            >>> visitor.defined_names
            {'tools'}
        """
        return self.visible_names("defined_names")

    @property
    def tools_aliases(self) -> Set[str]:
        """
        Return visible aliases for repository ``tools`` modules.

        :return: Visible tools aliases.
        :rtype: Set[str]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.tools_aliases
            set()
        """
        return self.visible_names("tools_aliases")

    @property
    def dynamic_tools_aliases(self) -> Set[str]:
        """
        Return visible aliases produced by dynamic ``tools`` imports.

        :return: Visible dynamic tools aliases.
        :rtype: Set[str]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.dynamic_tools_aliases.add('mod')
            >>> 'mod' in visitor.dynamic_tools_aliases
            True
        """
        return self.visible_names("dynamic_tools_aliases")

    @property
    def importlib_aliases(self) -> Set[str]:
        """
        Return visible aliases for :mod:`importlib` helpers.

        :return: Visible importlib aliases.
        :rtype: Set[str]

        Example::

            >>> 'importlib' in TestBoundaryVisitor(Path('x.py'), '', set()).importlib_aliases
            True
        """
        return self.visible_names("importlib_aliases")

    @property
    def importlib_util_aliases(self) -> Set[str]:
        """
        Return visible aliases for :mod:`importlib.util`.

        :return: Visible importlib utility aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).importlib_util_aliases
            set()
        """
        return self.visible_names("importlib_util_aliases")

    @property
    def importlib_util_spec_aliases(self) -> Set[str]:
        """
        Return visible aliases for ``spec_from_file_location``.

        :return: Visible importlib spec helper aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).importlib_util_spec_aliases
            set()
        """
        return self.visible_names("importlib_util_spec_aliases")

    @property
    def builtins_aliases(self) -> Set[str]:
        """
        Return visible aliases for the :mod:`builtins` module.

        :return: Visible builtins aliases.
        :rtype: Set[str]

        Example::

            >>> 'builtins' in TestBoundaryVisitor(Path('x.py'), '', set()).builtins_aliases
            True
        """
        return self.visible_names("builtins_aliases")

    @property
    def pathlib_aliases(self) -> Set[str]:
        """
        Return visible aliases for the :mod:`pathlib` module.

        :return: Visible pathlib aliases.
        :rtype: Set[str]

        Example::

            >>> 'pathlib' in TestBoundaryVisitor(Path('x.py'), '', set()).pathlib_aliases
            True
        """
        return self.visible_names("pathlib_aliases")

    @property
    def path_class_aliases(self) -> Set[str]:
        """
        Return visible aliases for :mod:`pathlib` path constructors.

        :return: Visible path-constructor aliases.
        :rtype: Set[str]

        Example::

            >>> 'Path' in TestBoundaryVisitor(Path('x.py'), '', set()).path_class_aliases
            True
        """
        return self.visible_names("path_class_aliases")

    @property
    def pytest_aliases(self) -> Set[str]:
        """
        Return visible aliases for the :mod:`pytest` module.

        :return: Visible pytest aliases.
        :rtype: Set[str]

        Example::

            >>> 'pytest' in TestBoundaryVisitor(Path('x.py'), '', set()).pytest_aliases
            True
        """
        return self.visible_names("pytest_aliases")

    @property
    def pytest_importorskip_aliases(self) -> Set[str]:
        """
        Return visible aliases for :func:`pytest.importorskip`.

        :return: Visible ``importorskip`` aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).pytest_importorskip_aliases
            set()
        """
        return self.visible_names("pytest_importorskip_aliases")

    @property
    def runpy_aliases(self) -> Set[str]:
        """
        Return visible aliases for the :mod:`runpy` module.

        :return: Visible runpy aliases.
        :rtype: Set[str]

        Example::

            >>> 'runpy' in TestBoundaryVisitor(Path('x.py'), '', set()).runpy_aliases
            True
        """
        return self.visible_names("runpy_aliases")

    @property
    def runpy_run_module_aliases(self) -> Set[str]:
        """
        Return visible aliases for :func:`runpy.run_module`.

        :return: Visible ``run_module`` aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).runpy_run_module_aliases
            set()
        """
        return self.visible_names("runpy_run_module_aliases")

    @property
    def runpy_run_path_aliases(self) -> Set[str]:
        """
        Return visible aliases for :func:`runpy.run_path`.

        :return: Visible ``run_path`` aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).runpy_run_path_aliases
            set()
        """
        return self.visible_names("runpy_run_path_aliases")

    @property
    def sys_aliases(self) -> Set[str]:
        """
        Return visible aliases for the :mod:`sys` module.

        :return: Visible sys aliases.
        :rtype: Set[str]

        Example::

            >>> 'sys' in TestBoundaryVisitor(Path('x.py'), '', set()).sys_aliases
            True
        """
        return self.visible_names("sys_aliases")

    @property
    def sys_modules_aliases(self) -> Set[str]:
        """
        Return visible aliases for :data:`sys.modules`.

        :return: Visible ``sys.modules`` aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).sys_modules_aliases
            set()
        """
        return self.visible_names("sys_modules_aliases")

    @property
    def sys_modules_getitem_aliases(self) -> Set[str]:
        """
        Return visible aliases for ``sys.modules.__getitem__``.

        :return: Visible ``sys.modules`` getitem aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).sys_modules_getitem_aliases
            set()
        """
        return self.visible_names("sys_modules_getitem_aliases")

    @property
    def sys_modules_get_aliases(self) -> Set[str]:
        """
        Return visible aliases for ``sys.modules.get``.

        :return: Visible ``sys.modules.get`` aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).sys_modules_get_aliases
            set()
        """
        return self.visible_names("sys_modules_get_aliases")

    @property
    def subprocess_aliases(self) -> Set[str]:
        """
        Return visible aliases for the :mod:`subprocess` module.

        :return: Visible subprocess aliases.
        :rtype: Set[str]

        Example::

            >>> 'subprocess' in TestBoundaryVisitor(Path('x.py'), '', set()).subprocess_aliases
            True
        """
        return self.visible_names("subprocess_aliases")

    @property
    def subprocess_function_aliases(self) -> Set[str]:
        """
        Return visible aliases for subprocess command functions.

        :return: Visible subprocess function aliases.
        :rtype: Set[str]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.subprocess_function_aliases.add('run')
            >>> 'run' in visitor.subprocess_function_aliases
            True
        """
        return self.visible_names("subprocess_function_aliases")

    @property
    def os_aliases(self) -> Set[str]:
        """
        Return visible aliases for the :mod:`os` module.

        :return: Visible OS aliases.
        :rtype: Set[str]

        Example::

            >>> 'os' in TestBoundaryVisitor(Path('x.py'), '', set()).os_aliases
            True
        """
        return self.visible_names("os_aliases")

    @property
    def os_function_aliases(self) -> Set[str]:
        """
        Return visible aliases for OS command helpers.

        :return: Visible OS command aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).os_function_aliases
            set()
        """
        return self.visible_names("os_function_aliases")

    @property
    def os_function_alias_methods(self) -> Dict[str, str]:
        """
        Return visible original helper names for OS command aliases.

        :return: Mapping from local alias to original :mod:`os` helper name.
        :rtype: Dict[str, str]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.os_function_alias_methods['run_exec'] = 'execvp'
            >>> visitor.os_function_alias_methods['run_exec']
            'execvp'
        """
        visible = {}
        shadowed = set()
        for scope in reversed(self.scope_stack):
            for name, method_name in scope.os_function_alias_methods.items():
                if name not in shadowed:
                    visible[name] = method_name
            shadowed.update(scope.shadowing_names)
            shadowed.update(scope.defined_names)
        return visible

    @property
    def os_path_join_aliases(self) -> Set[str]:
        """
        Return visible aliases for ``os.path.join``.

        :return: Visible join aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).os_path_join_aliases
            set()
        """
        return self.visible_names("os_path_join_aliases")

    @property
    def os_path_aliases(self) -> Set[str]:
        """
        Return visible aliases for the :mod:`os.path` module.

        :return: Visible ``os.path`` aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).os_path_aliases
            set()
        """
        return self.visible_names("os_path_aliases")

    @property
    def os_path_dirname_aliases(self) -> Set[str]:
        """
        Return visible aliases for ``os.path.dirname``.

        :return: Visible dirname aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).os_path_dirname_aliases
            set()
        """
        return self.visible_names("os_path_dirname_aliases")

    @property
    def os_path_abspath_aliases(self) -> Set[str]:
        """
        Return visible aliases for path-preserving :mod:`os.path` wrappers.

        :return: Visible path-preserving wrapper aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).os_path_abspath_aliases
            set()
        """
        return self.visible_names("os_path_abspath_aliases")

    @property
    def os_path_split_aliases(self) -> Set[str]:
        """
        Return visible aliases for ``os.path.split``.

        :return: Visible split aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).os_path_split_aliases
            set()
        """
        return self.visible_names("os_path_split_aliases")

    @property
    def os_getcwd_aliases(self) -> Set[str]:
        """
        Return visible aliases for :func:`os.getcwd`.

        :return: Visible ``getcwd`` aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).os_getcwd_aliases
            set()
        """
        return self.visible_names("os_getcwd_aliases")

    @property
    def repo_root_aliases(self) -> Set[str]:
        """
        Return visible repository-root aliases.

        :return: Visible repository-root aliases.
        :rtype: Set[str]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.repo_root_aliases.add('repo_root')
            >>> 'repo_root' in visitor.repo_root_aliases
            True
        """
        return self.visible_names("repo_root_aliases")

    @property
    def path_parent_hop_aliases(self) -> Dict[str, int]:
        """
        Return visible parent-hop aliases rooted at ``__file__``.

        :return: Mapping from visible local names to parent-hop counts.
        :rtype: Dict[str, int]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('test/x.py'), '', set())
            >>> visitor.current_scope.path_parent_hop_aliases['base'] = 1
            >>> visitor.path_parent_hop_aliases['base']
            1
        """
        visible = {}
        shadowed = set()
        for scope in reversed(self.scope_stack):
            for name, hops in scope.path_parent_hop_aliases.items():
                if name not in shadowed:
                    visible[name] = hops
            shadowed.update(scope.shadowing_names)
            shadowed.update(scope.defined_names)
        return visible

    @property
    def file_parents_aliases(self) -> Set[str]:
        """
        Return aliases for ``Path(__file__).parents`` sequence expressions.

        :return: Visible ``parents`` sequence aliases.
        :rtype: Set[str]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.file_parents_aliases.add('parents')
            >>> 'parents' in visitor.file_parents_aliases
            True
        """
        return self.visible_names("file_parents_aliases")

    @property
    def string_aliases(self) -> Dict[str, str]:
        """
        Return visible statically known string aliases.

        :return: Mapping from visible local names to string values.
        :rtype: Dict[str, str]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.string_aliases['name'] = 'tools'
            >>> visitor.string_aliases['name']
            'tools'
        """
        visible = {}
        shadowed = set()
        for scope in reversed(self.scope_stack):
            for name, value in scope.string_aliases.items():
                if name not in shadowed:
                    visible[name] = value
            shadowed.update(scope.shadowing_names)
            shadowed.update(scope.defined_names)
        return visible

    @property
    def dynamic_code_alias_rules(self) -> Dict[str, str]:
        """
        Return visible compiled dynamic-code findings by alias name.

        :return: Mapping from aliases to nested boundary rule names.
        :rtype: Dict[str, str]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.dynamic_code_alias_rules['code'] = 'tools-import'
            >>> visitor.dynamic_code_alias_rules['code']
            'tools-import'
        """
        visible = {}
        shadowed = set()
        for scope in reversed(self.scope_stack):
            for name, rule in scope.dynamic_code_alias_rules.items():
                if name not in shadowed:
                    visible[name] = rule
            shadowed.update(scope.shadowing_names)
            shadowed.update(scope.defined_names)
        return visible

    @property
    def template_segment_aliases(self) -> Set[str]:
        """
        Return aliases for the exact ``templates`` path segment.

        :return: Visible template-segment aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).template_segment_aliases
            set()
        """
        return self.visible_names("template_segment_aliases")

    @property
    def tools_module_name_aliases(self) -> Set[str]:
        """
        Return aliases for ``tools`` module-name strings.

        :return: Visible tools-module-name aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).tools_module_name_aliases
            set()
        """
        return self.visible_names("tools_module_name_aliases")

    @property
    def tools_command_aliases(self) -> Set[str]:
        """
        Return visible command aliases that execute repository tools scripts.

        :return: Visible tools command aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).tools_command_aliases
            set()
        """
        return self.visible_names("tools_command_aliases")

    @property
    def source_install_command_aliases(self) -> Set[str]:
        """
        Return visible command aliases that perform source installs.

        :return: Visible source-install command aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).source_install_command_aliases
            set()
        """
        return self.visible_names("source_install_command_aliases")

    @property
    def package_templates_aliases(self) -> Set[str]:
        """
        Return visible aliases for ``tools.package_templates`` helpers.

        :return: Visible package-template helper aliases.
        :rtype: Set[str]

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).package_templates_aliases
            set()
        """
        return self.visible_names("package_templates_aliases")

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

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        """
        Visit a function body with its own lexical bindings.

        :param node: Function definition node.
        :type node: ast.FunctionDef
        :return: ``None``.
        :rtype: None

        Example::

            >>> source = 'def f():' + chr(10) + '    tools = object()' + chr(10) + '    tools.x()'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> visitor.findings
            []
        """
        self.visit_function_like(node, node.args, node.body)
        self.clear_scope_aliases(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        """
        Visit an async function body with its own lexical bindings.

        :param node: Async function definition node.
        :type node: ast.AsyncFunctionDef
        :return: ``None``.
        :rtype: None

        Example::

            >>> source = 'async def f():' + chr(10) + '    tools = object()' + chr(10) + '    tools.x()'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> visitor.findings
            []
        """
        self.visit_function_like(node, node.args, node.body)
        self.clear_scope_aliases(node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:  # noqa: N802
        """
        Visit a lambda expression with argument bindings in scope.

        :param node: Lambda node.
        :type node: ast.Lambda
        :return: ``None``.
        :rtype: None

        Example::

            >>> source = 'fn = lambda tools: tools.x()'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> visitor.findings
            []
        """
        self.visit_argument_expressions(node.args)
        self.visit_callable_body(function_argument_names(node.args), [node.body])

    def visit_function_like(
        self, node: ast.AST, arguments: ast.arguments, body: Sequence[ast.AST]
    ) -> None:
        """
        Visit decorators, defaults, and a function body with proper scope.

        :param node: Function-like node.
        :type node: ast.AST
        :param arguments: Function argument list.
        :type arguments: ast.arguments
        :param body: Function body statements.
        :type body: Sequence[ast.AST]
        :return: ``None``.
        :rtype: None

        Example::

            >>> source = 'def f(tools):' + chr(10) + '    tools.x()'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> visitor.findings
            []
        """
        for decorator in getattr(node, "decorator_list", []):
            self.visit(decorator)
        returns = getattr(node, "returns", None)
        if returns is not None:
            self.visit(returns)
        self.visit_argument_expressions(arguments)
        argument_names = function_argument_names(arguments)
        bound_names = argument_names | collect_scope_defined_names(body)
        shadowing_names = argument_names | collect_shadowing_names(body)
        self.visit_callable_body(bound_names, body, shadowing_names=shadowing_names)

    def visit_argument_expressions(self, arguments: ast.arguments) -> None:
        """
        Visit default values and annotations outside the callee local scope.

        :param arguments: Function or lambda argument list.
        :type arguments: ast.arguments
        :return: ``None``.
        :rtype: None

        Example::

            >>> source = 'fn = lambda x=__import__("tools.x"): x'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> [finding.rule for finding in visitor.findings]
            ['tools-dynamic-import']
        """
        all_arguments = (
            list(getattr(arguments, "posonlyargs", []))
            + list(arguments.args)
            + list(arguments.kwonlyargs)
        )
        for argument in all_arguments:
            annotation = getattr(argument, "annotation", None)
            if annotation is not None:
                self.visit(annotation)
        for argument in (arguments.vararg, arguments.kwarg):
            if argument is not None and argument.annotation is not None:
                self.visit(argument.annotation)
        for default in list(arguments.defaults) + list(arguments.kw_defaults):
            if default is not None:
                self.visit(default)

    def visit_callable_body(
        self,
        defined_names: Set[str],
        body: Sequence[ast.AST],
        shadowing_names: Optional[Set[str]] = None,
    ) -> None:
        """
        Visit a function-like body while excluding class namespaces.

        Python function and lambda bodies close over surrounding function scopes,
        but class-body names are not lexical locals for methods. Excluding class
        scopes here prevents class attributes such as ``tools`` or
        ``subprocess`` from hiding forbidden module-level calls inside methods.

        :param defined_names: Names bound by arguments and local statements.
        :type defined_names: Set[str]
        :param body: Function or lambda body nodes to visit.
        :type body: Sequence[ast.AST]
        :param shadowing_names: Non-import names that shadow aliases, defaults
            to ``None``.
        :type shadowing_names: Set[str], optional
        :return: ``None``.
        :rtype: None

        Example::

            >>> source = 'class C:' + chr(10) + '    tools = object()' + chr(10) + '    def m(self):' + chr(10) + '        tools.x()'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> [finding.rule for finding in visitor.findings]
            ['tools-call']
            >>> source = 'def f():' + chr(10) + '    import subprocess' + chr(10) + '    subprocess.run(["python", "tools/x.py"])'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> [finding.rule for finding in visitor.findings]
            ['tools-exec']
        """
        parent_stack = self.scope_stack
        callable_scope = NameScope.create(
            defined_names=defined_names,
            shadowing_names=shadowing_names,
        )
        # Class namespaces are intentionally filtered here because Python
        # method bodies do not close over class-body assignments.
        self.scope_stack = [
            scope for scope in parent_stack if not scope.is_class_body
        ] + [callable_scope]
        try:
            for node in body:
                self.visit(node)
        finally:
            self.scope_stack = parent_stack

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        """
        Visit a class body with class-local bindings.

        :param node: Class definition node.
        :type node: ast.ClassDef
        :return: ``None``.
        :rtype: None

        Example::

            >>> source = 'class C:' + chr(10) + '    tools = object()' + chr(10) + '    tools.x()'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> visitor.findings
            []
        """
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        self.push_scope(
            collect_scope_defined_names(node.body),
            shadowing_names=collect_shadowing_names(node.body),
            is_class_body=True,
        )
        try:
            for statement in node.body:
                self.visit(statement)
        finally:
            self.scope_stack.pop()
        self.clear_scope_aliases(node.name)

    def push_scope(
        self,
        defined_names: Set[str],
        shadowing_names: Optional[Set[str]] = None,
        is_class_body: bool = False,
    ) -> None:
        """
        Push a lexical scope with ordinary bindings but no inherited taint.

        :param defined_names: Names bound by the new scope.
        :type defined_names: Set[str]
        :param shadowing_names: Non-import names that shadow aliases, defaults
            to ``None``.
        :type shadowing_names: Set[str], optional
        :param is_class_body: Whether the scope models a class namespace, defaults to ``False``.
        :type is_class_body: bool, optional
        :return: ``None``.
        :rtype: None

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.push_scope({'tools'})
            >>> 'tools' in visitor.defined_names
            True
        """
        self.scope_stack.append(
            NameScope.create(
                defined_names=defined_names,
                shadowing_names=shadowing_names,
                is_class_body=is_class_body,
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
                self.current_scope.tools_aliases.add(local_name)
                self.add_finding(
                    node,
                    TOOLS_IMPORT_RULE,
                    "pytest files must not import repository tools modules directly",
                )
            elif alias.name == "importlib":
                self.current_scope.importlib_aliases.add(local_name)
            elif alias.name == "importlib.util":
                if alias.asname is None:
                    self.current_scope.importlib_aliases.add(local_name)
                else:
                    self.current_scope.importlib_util_aliases.add(local_name)
            elif alias.name == "builtins":
                self.current_scope.builtins_aliases.add(local_name)
            elif alias.name == "pathlib":
                self.current_scope.pathlib_aliases.add(local_name)
            elif alias.name == "pytest":
                self.current_scope.pytest_aliases.add(local_name)
            elif alias.name == "runpy":
                self.current_scope.runpy_aliases.add(local_name)
            elif alias.name == "sys":
                self.current_scope.sys_aliases.add(local_name)
            elif alias.name == "subprocess":
                self.current_scope.subprocess_aliases.add(local_name)
            elif alias.name == "os":
                self.current_scope.os_aliases.add(local_name)
            elif alias.name == "os.path" and alias.asname is not None:
                self.current_scope.os_path_aliases.add(local_name)
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
                    self.current_scope.package_templates_aliases.add(local_name)
            self.add_finding(
                node,
                TOOLS_IMPORT_RULE,
                "pytest files must not import repository tools modules directly",
            )
        elif module == "importlib":
            for alias in node.names:
                if alias.name == "import_module":
                    self.current_scope.importlib_aliases.add(alias.asname or alias.name)
                elif alias.name == "util":
                    self.current_scope.importlib_util_aliases.add(
                        alias.asname or alias.name
                    )
        elif module == "importlib.util":
            for alias in node.names:
                if alias.name == "spec_from_file_location":
                    self.current_scope.importlib_util_spec_aliases.add(
                        alias.asname or alias.name
                    )
        elif module == "builtins":
            for alias in node.names:
                if alias.name == "__import__":
                    self.current_scope.importlib_aliases.add(alias.asname or alias.name)
        elif module == "pathlib":
            for alias in node.names:
                if alias.name == "*":
                    self.current_scope.path_class_aliases.update(
                        _PATH_CONSTRUCTOR_NAMES
                    )
                elif alias.name in _PATH_CONSTRUCTOR_NAMES:
                    self.current_scope.path_class_aliases.add(
                        alias.asname or alias.name
                    )
        elif module == "pytest":
            for alias in node.names:
                if alias.name == "importorskip":
                    self.current_scope.pytest_importorskip_aliases.add(
                        alias.asname or alias.name
                    )
        elif module == "runpy":
            for alias in node.names:
                if alias.name == "run_module":
                    self.current_scope.runpy_run_module_aliases.add(
                        alias.asname or alias.name
                    )
                elif alias.name == "run_path":
                    self.current_scope.runpy_run_path_aliases.add(
                        alias.asname or alias.name
                    )
        elif module == "sys":
            for alias in node.names:
                if alias.name == "modules":
                    self.current_scope.sys_modules_aliases.add(
                        alias.asname or alias.name
                    )
        elif module == "subprocess":
            for alias in node.names:
                if alias.name in _SUBPROCESS_METHODS:
                    self.current_scope.subprocess_function_aliases.add(
                        alias.asname or alias.name
                    )
        elif module == "os":
            for alias in node.names:
                if alias.name in _OS_COMMAND_METHODS:
                    local_name = alias.asname or alias.name
                    self.current_scope.os_function_aliases.add(local_name)
                    self.current_scope.os_function_alias_methods[local_name] = (
                        alias.name
                    )
                elif alias.name == "getcwd":
                    self.current_scope.os_getcwd_aliases.add(alias.asname or alias.name)
                elif alias.name == "path":
                    self.current_scope.os_path_aliases.add(alias.asname or alias.name)
                elif alias.name == "pardir":
                    self.current_scope.string_aliases[alias.asname or alias.name] = ".."
        elif module == "os.path":
            for alias in node.names:
                if alias.name == "*":
                    self.current_scope.os_path_join_aliases.add("join")
                    self.current_scope.os_path_dirname_aliases.add("dirname")
                    self.current_scope.os_path_abspath_aliases.update(
                        _OS_PATH_PASSTHROUGH_HELPERS
                    )
                    self.current_scope.os_path_split_aliases.add("split")
                    self.current_scope.string_aliases["pardir"] = ".."
                elif alias.name == "join":
                    self.current_scope.os_path_join_aliases.add(
                        alias.asname or alias.name
                    )
                elif alias.name == "dirname":
                    self.current_scope.os_path_dirname_aliases.add(
                        alias.asname or alias.name
                    )
                elif alias.name == "abspath":
                    self.current_scope.os_path_abspath_aliases.add(
                        alias.asname or alias.name
                    )
                elif alias.name in {"normpath", "realpath"}:
                    self.current_scope.os_path_abspath_aliases.add(
                        alias.asname or alias.name
                    )
                elif alias.name == "split":
                    self.current_scope.os_path_split_aliases.add(
                        alias.asname or alias.name
                    )
                elif alias.name == "pardir":
                    self.current_scope.string_aliases[alias.asname or alias.name] = ".."
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

    def visit_AugAssign(self, node: ast.AugAssign) -> None:  # noqa: N802
        """
        Visit an augmented assignment and refresh static alias taint.

        String-building updates such as ``cmd += "tools/x.py"`` can turn a
        previously harmless command alias into a boundary violation. The visitor
        models ``+=`` as a static binary addition before rebinding the target so
        command, module-name, and path-segment aliases stay conservative.

        :param node: Augmented assignment node.
        :type node: ast.AugAssign
        :return: ``None``.
        :rtype: None

        Example::

            >>> source = 'import subprocess' + chr(10) + 'cmd = "python "' + chr(10) + 'cmd += "tools/x.py"' + chr(10) + 'subprocess.run(cmd, shell=True)'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> [finding.rule for finding in visitor.findings]
            ['tools-exec']
        """
        if isinstance(node.op, ast.Add):
            value = ast.BinOp(left=node.target, op=ast.Add(), right=node.value)
            ast.copy_location(value, node)
            self._visit_assignment_targets([node.target], value)
        else:
            for name in self._target_names(node.target):
                self.clear_scope_aliases(name)
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:  # noqa: N802
        """
        Visit a ``for`` loop and conservatively propagate static iterable aliases.

        :param node: For-loop node.
        :type node: ast.For
        :return: ``None``.
        :rtype: None

        Example::

            >>> source = 'import subprocess' + chr(10) + 'for cmd in [["python", "tools/x.py"]]:' + chr(10) + '    subprocess.run(cmd)'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> [finding.rule for finding in visitor.findings]
            ['tools-exec']
        """
        if self.iterable_has_tools_command(node.iter):
            self.mark_target_names(node.target, "tools_command_aliases")
        if self.iterable_has_source_install_command(node.iter):
            self.mark_target_names(node.target, "source_install_command_aliases")
        self.generic_visit(node)

    def mark_target_names(self, target: ast.AST, attribute: str) -> None:
        """
        Mark every simple name in an assignment target with an alias set.

        :param target: Assignment target node.
        :type target: ast.AST
        :param attribute: Alias set attribute on the current scope.
        :type attribute: str
        :return: ``None``.
        :rtype: None

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.mark_target_names(ast.Name(id='cmd'), 'tools_command_aliases')
            >>> 'cmd' in visitor.tools_command_aliases
            True
        """
        for name in self._target_names(target):
            self.clear_scope_aliases(name)
            getattr(self.current_scope, attribute).add(name)

    def iterable_has_tools_command(self, node: ast.AST) -> bool:
        """
        Return whether a static iterable can yield a tools command.

        :param node: Iterable expression node.
        :type node: ast.AST
        :return: ``True`` when any yielded element executes repository tools.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> expr = ast.parse('[["python", "tools/x.py"]]').body[0].value
            >>> visitor.iterable_has_tools_command(expr)
            True
        """
        return any(
            self.expression_or_alias_runs_tools_script(element)
            for element in self.static_iterable_elements(node)
        )

    def iterable_has_tools_module_name(self, node: ast.AST) -> bool:
        """
        Return whether a static iterable contains a ``tools`` module name.

        :param node: Iterable expression node.
        :type node: ast.AST
        :return: ``True`` when any yielded element names a ``tools`` module.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> expr = ast.parse('("tools.package_templates",)').body[0].value
            >>> visitor.iterable_has_tools_module_name(expr)
            True
        """
        return any(
            self.expression_denotes_tools_module(element)
            for element in self.static_iterable_elements(node)
        )

    def iterable_has_source_install_command(self, node: ast.AST) -> bool:
        """
        Return whether a static iterable can yield a source-install command.

        :param node: Iterable expression node.
        :type node: ast.AST
        :return: ``True`` when any yielded element performs a source install.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> expr = ast.parse('[["python", "-m", "pip", "install", "."]]').body[0].value
            >>> visitor.iterable_has_source_install_command(expr)
            True
        """
        return any(
            self.expression_or_alias_runs_source_install_command(element)
            for element in self.static_iterable_elements(node)
        )

    def static_iterable_elements(self, node: ast.AST) -> List[ast.AST]:
        """
        Return statically visible elements yielded by a simple iterable.

        :param node: Iterable expression node.
        :type node: ast.AST
        :return: Element expressions, or an empty list for dynamic iterables.
        :rtype: List[ast.AST]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> len(visitor.static_iterable_elements(ast.parse('(["x"],)').body[0].value))
            1
        """
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return list(node.elts)
        return []

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
        if self._visit_static_unpack(targets, value):
            return
        if self._visit_path_split_unpack(targets, value):
            return
        repo_root_tainted = self.is_repo_root_tainted(value)
        path_parent_hops = self.path_argument_parent_hops(value)
        file_parents_sequence = self.expression_denotes_file_parents_sequence(value)
        dynamic_tools_import = self.is_dynamic_tools_import_call(value)
        tools_command = self.expression_or_alias_runs_tools_script(value)
        source_install_command = self.expression_or_alias_runs_source_install_command(
            value
        )
        template_segment = self.expression_has_exact_segment(value, "templates")
        tools_module_name = self.expression_denotes_tools_module(value)
        tools_module_sequence = self.iterable_has_tools_module_name(value)
        static_string = self.static_string(value)
        dynamic_code_rule = self.compiled_dynamic_code_boundary_rule(value)
        for target in targets:
            for name in self._target_names(target):
                self.clear_scope_aliases(name)
                if static_string is not None:
                    self.current_scope.string_aliases[name] = static_string
                if repo_root_tainted:
                    self.current_scope.repo_root_aliases.add(name)
                if path_parent_hops is not None:
                    self.current_scope.path_parent_hop_aliases[name] = path_parent_hops
                if file_parents_sequence:
                    self.current_scope.file_parents_aliases.add(name)
                if dynamic_tools_import:
                    self.current_scope.dynamic_tools_aliases.add(name)
                if dynamic_code_rule is not None:
                    self.current_scope.dynamic_code_alias_rules[name] = (
                        dynamic_code_rule
                    )
                if template_segment:
                    self.current_scope.template_segment_aliases.add(name)
                if tools_module_name or tools_module_sequence:
                    self.current_scope.tools_module_name_aliases.add(name)
                if self.expression_denotes_importlib_module(value):
                    self.current_scope.importlib_aliases.add(name)
                if self.expression_denotes_importlib_import_module(value):
                    self.current_scope.importlib_aliases.add(name)
                if self.expression_denotes_importlib_util_module(value):
                    self.current_scope.importlib_util_aliases.add(name)
                if self.expression_denotes_importlib_util_spec_helper(value):
                    self.current_scope.importlib_util_spec_aliases.add(name)
                if self.expression_denotes_subprocess_command_helper(value):
                    self.current_scope.subprocess_function_aliases.add(name)
                os_helper = self.expression_denotes_os_command_helper(value)
                if os_helper is not None:
                    self.current_scope.os_function_aliases.add(name)
                    self.current_scope.os_function_alias_methods[name] = os_helper
                os_path_helper = self.expression_denotes_os_path_helper(value)
                if os_path_helper == "join":
                    self.current_scope.os_path_join_aliases.add(name)
                elif os_path_helper == "dirname":
                    self.current_scope.os_path_dirname_aliases.add(name)
                elif os_path_helper == "abspath":
                    self.current_scope.os_path_abspath_aliases.add(name)
                elif os_path_helper == "split":
                    self.current_scope.os_path_split_aliases.add(name)
                sys_modules_method = self.sys_modules_method_name(value)
                if sys_modules_method == "__getitem__":
                    self.current_scope.sys_modules_getitem_aliases.add(name)
                elif sys_modules_method == "get":
                    self.current_scope.sys_modules_get_aliases.add(name)
                if tools_command:
                    self.current_scope.tools_command_aliases.add(name)
                if source_install_command:
                    self.current_scope.source_install_command_aliases.add(name)

    def _visit_static_unpack(self, targets: Sequence[ast.AST], value: ast.AST) -> bool:
        """
        Track aliases introduced by static tuple or list unpacking.

        :param targets: Assignment targets.
        :type targets: Sequence[ast.AST]
        :param value: Assigned iterable expression.
        :type value: ast.AST
        :return: ``True`` when static unpacking was handled.
        :rtype: bool

        Example::

            >>> source = 'import importlib' + chr(10) + 'importer, _ = (importlib.import_module, None)' + chr(10) + 'importer("tools.package_templates")'
            >>> visitor = TestBoundaryVisitor(Path('test/x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> visitor.findings[0].rule
            'tools-dynamic-import'
        """
        if len(targets) != 1 or not isinstance(targets[0], (ast.Tuple, ast.List)):
            return False
        elements = self.static_iterable_elements(value)
        unpack_target = targets[0]
        if not elements or len(elements) != len(unpack_target.elts):
            return False
        for target, element in zip(unpack_target.elts, elements):
            self._visit_assignment_targets([target], element)
        return True

    def _visit_path_split_unpack(
        self, targets: Sequence[ast.AST], value: ast.AST
    ) -> bool:
        """
        Track parent hops from ``os.path.split`` tuple unpacking.

        :param targets: Assignment targets.
        :type targets: Sequence[ast.AST]
        :param value: Assigned value expression.
        :type value: ast.AST
        :return: ``True`` when the assignment was handled as path splitting.
        :rtype: bool

        Example::

            >>> source = 'import os' + chr(10) + 'base, _ = os.path.split(__file__)' + chr(10) + 'os.path.join(base, "..", "templates")'
            >>> visitor = TestBoundaryVisitor(Path('test/x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> visitor.findings[0].rule
            'repo-source-templates'
        """
        if len(targets) != 1 or not isinstance(targets[0], (ast.Tuple, ast.List)):
            return False
        if not isinstance(value, ast.Call) or not value.args:
            return False
        if not self.is_os_path_split_call(value):
            return False
        base_hops = self.path_argument_parent_hops(value.args[0])
        if base_hops is None:
            return False
        unpack_target = targets[0]
        for name in self._target_names(unpack_target):
            self.clear_scope_aliases(name)
        if unpack_target.elts:
            for name in self._target_names(unpack_target.elts[0]):
                self.current_scope.path_parent_hop_aliases[name] = base_hops + 1
        return True

    def clear_scope_aliases(self, name: str) -> None:
        """
        Clear tainted aliases overwritten by an ordinary binding.

        :param name: Name rebound in the current scope.
        :type name: str
        :return: ``None``.
        :rtype: None

        Example::

            >>> source = 'def f():' + chr(10) + '    import subprocess' + chr(10) + '    subprocess.run(["python", "tools/x.py"])' + chr(10) + '    subprocess = object()' + chr(10) + '    subprocess.run(["python", "tools/y.py"])'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> [(finding.rule, finding.line) for finding in visitor.findings]
            [('tools-exec', 3)]
        """
        self.current_scope.tools_aliases.discard(name)
        self.current_scope.dynamic_tools_aliases.discard(name)
        self.current_scope.importlib_aliases.discard(name)
        self.current_scope.importlib_util_aliases.discard(name)
        self.current_scope.importlib_util_spec_aliases.discard(name)
        self.current_scope.builtins_aliases.discard(name)
        self.current_scope.pathlib_aliases.discard(name)
        self.current_scope.path_class_aliases.discard(name)
        self.current_scope.pytest_aliases.discard(name)
        self.current_scope.pytest_importorskip_aliases.discard(name)
        self.current_scope.runpy_aliases.discard(name)
        self.current_scope.runpy_run_module_aliases.discard(name)
        self.current_scope.runpy_run_path_aliases.discard(name)
        self.current_scope.sys_aliases.discard(name)
        self.current_scope.sys_modules_aliases.discard(name)
        self.current_scope.sys_modules_getitem_aliases.discard(name)
        self.current_scope.sys_modules_get_aliases.discard(name)
        self.current_scope.subprocess_aliases.discard(name)
        self.current_scope.subprocess_function_aliases.discard(name)
        self.current_scope.os_aliases.discard(name)
        self.current_scope.os_function_aliases.discard(name)
        self.current_scope.os_function_alias_methods.pop(name, None)
        self.current_scope.os_path_aliases.discard(name)
        self.current_scope.os_path_join_aliases.discard(name)
        self.current_scope.os_path_dirname_aliases.discard(name)
        self.current_scope.os_path_abspath_aliases.discard(name)
        self.current_scope.os_path_split_aliases.discard(name)
        self.current_scope.os_getcwd_aliases.discard(name)
        self.current_scope.repo_root_aliases.discard(name)
        self.current_scope.path_parent_hop_aliases.pop(name, None)
        self.current_scope.file_parents_aliases.discard(name)
        self.current_scope.string_aliases.pop(name, None)
        self.current_scope.dynamic_code_alias_rules.pop(name, None)
        self.current_scope.template_segment_aliases.discard(name)
        self.current_scope.tools_module_name_aliases.discard(name)
        self.current_scope.tools_command_aliases.discard(name)
        self.current_scope.source_install_command_aliases.discard(name)
        self.current_scope.package_templates_aliases.discard(name)

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

    def static_string(self, node: ast.AST) -> Optional[str]:
        """
        Return a statically known string value with local aliases expanded.

        :param node: AST expression node.
        :type node: ast.AST
        :return: String value, or ``None`` when it is not statically known.
        :rtype: str, optional

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.string_aliases['suffix'] = 'package_templates'
            >>> visitor.static_string(ast.parse('f"tools.{suffix}"').body[0].value)
            'tools.package_templates'
        """
        value = literal_string(node)
        if value is not None:
            return value
        if isinstance(node, ast.Name):
            return self.string_aliases.get(node.id)
        if isinstance(node, ast.Attribute) and node.attr == "pardir":
            if isinstance(node.value, ast.Name) and node.value.id in self.os_aliases:
                return ".."
            if self.expression_denotes_os_path_module(node.value):
                return ".."
            if dotted_name(node) in {"os.pardir", "os.path.pardir"}:
                return ".."
        if isinstance(node, ast.JoinedStr):
            parts = []
            for value_node in node.values:
                if isinstance(value_node, ast.FormattedValue):
                    if value_node.format_spec is not None:
                        return None
                    part = self.static_string(value_node.value)
                else:
                    part = self.static_string(value_node)
                if part is None:
                    return None
                parts.append(part)
            return "".join(parts)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self.static_string(node.left)
            right = self.static_string(node.right)
            if left is not None and right is not None:
                return left + right
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr in _STATIC_STRING_METHODS:
                if node.args or node.keywords:
                    return None
                value = self.static_string(node.func.value)
                if value is None:
                    return None
                if node.func.attr == "lower":
                    return value.lower()
                if node.func.attr == "upper":
                    return value.upper()
                return value.casefold()
        return None

    def expression_denotes_importlib_module(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` denotes the :mod:`importlib` module.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` for visible importlib module aliases.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.expression_denotes_importlib_module(ast.Name(id='importlib'))
            True
            >>> expr = ast.parse('__import__("importlib")').body[0].value
            >>> visitor.expression_denotes_importlib_module(expr)
            True
        """
        if isinstance(node, ast.Name):
            return node.id in self.importlib_aliases
        if isinstance(node, ast.Call) and self.is_module_import_call(node):
            name = self.dynamic_import_target_module_name(node)
            return name is not None and (
                name == "importlib" or name.startswith("importlib.")
            )
        return False

    def expression_denotes_importlib_import_module(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` denotes :func:`importlib.import_module`.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` for visible ``import_module`` helpers.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> expr = ast.parse('importlib.import_module').body[0].value
            >>> visitor.expression_denotes_importlib_import_module(expr)
            True
            >>> expr = ast.parse('getattr(importlib, "import_module")').body[0].value
            >>> visitor.expression_denotes_importlib_import_module(expr)
            True
        """
        if isinstance(node, ast.Attribute) and node.attr == "import_module":
            return self.expression_denotes_importlib_module(node.value)
        if isinstance(node, ast.Call) and dotted_name(node.func) == "getattr":
            if len(node.args) < 2:
                return False
            return (
                self.expression_denotes_importlib_module(node.args[0])
                and self.static_string(node.args[1]) == "import_module"
            )
        return False

    def expression_denotes_importlib_util_module(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` denotes :mod:`importlib.util`.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` for visible importlib utility module aliases.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.expression_denotes_importlib_util_module(ast.parse('importlib.util').body[0].value)
            True
        """
        if isinstance(node, ast.Name):
            return node.id in self.importlib_util_aliases
        if isinstance(node, ast.Attribute) and node.attr == "util":
            return (
                isinstance(node.value, ast.Name)
                and node.value.id in self.importlib_aliases
            )
        return False

    def expression_denotes_importlib_util_spec_helper(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` denotes ``spec_from_file_location``.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` for visible importlib utility spec helpers.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> expr = ast.parse('importlib.util.spec_from_file_location').body[0].value
            >>> visitor.expression_denotes_importlib_util_spec_helper(expr)
            True
        """
        if isinstance(node, ast.Name):
            return node.id in self.importlib_util_spec_aliases
        if isinstance(node, ast.Attribute) and node.attr == "spec_from_file_location":
            return self.expression_denotes_importlib_util_module(node.value)
        if isinstance(node, ast.Call) and dotted_name(node.func) == "getattr":
            if len(node.args) < 2:
                return False
            return (
                self.expression_denotes_importlib_util_module(node.args[0])
                and self.static_string(node.args[1]) == "spec_from_file_location"
            )
        return False

    def expression_denotes_subprocess_command_helper(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` denotes a subprocess command helper.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` for visible subprocess helper attributes.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> expr = ast.parse('getattr(subprocess, "run")').body[0].value
            >>> visitor.expression_denotes_subprocess_command_helper(expr)
            True
        """
        if isinstance(node, ast.Attribute) and node.attr in _SUBPROCESS_METHODS:
            return (
                isinstance(node.value, ast.Name)
                and node.value.id in self.subprocess_aliases
            )
        if isinstance(node, ast.Call) and dotted_name(node.func) == "getattr":
            if len(node.args) < 2:
                return False
            method = self.static_string(node.args[1])
            return (
                method in _SUBPROCESS_METHODS
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id in self.subprocess_aliases
            )
        return False

    def expression_denotes_os_command_helper(self, node: ast.AST) -> Optional[str]:
        """
        Return the original :mod:`os` command helper denoted by ``node``.

        :param node: AST expression node.
        :type node: ast.AST
        :return: OS helper name, or ``None``.
        :rtype: str, optional

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> expr = ast.parse('getattr(os, "system")').body[0].value
            >>> visitor.expression_denotes_os_command_helper(expr)
            'system'
        """
        if isinstance(node, ast.Name):
            return self.os_function_alias_methods.get(node.id)
        if isinstance(node, ast.Attribute) and node.attr in _OS_COMMAND_METHODS:
            if isinstance(node.value, ast.Name) and node.value.id in self.os_aliases:
                return node.attr
        if isinstance(node, ast.Call) and dotted_name(node.func) == "getattr":
            if len(node.args) < 2:
                return None
            method = self.static_string(node.args[1])
            if method in _OS_COMMAND_METHODS:
                if (
                    isinstance(node.args[0], ast.Name)
                    and node.args[0].id in self.os_aliases
                ):
                    return method
        return None

    def expression_denotes_os_path_helper(self, node: ast.AST) -> Optional[str]:
        """
        Return the :mod:`os.path` helper denoted by ``node``.

        :param node: AST expression node.
        :type node: ast.AST
        :return: Helper name such as ``"join"``, or ``None``.
        :rtype: str, optional

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.expression_denotes_os_path_helper(ast.parse('getattr(os.path, "join")').body[0].value)
            'join'
        """
        if isinstance(node, ast.Name):
            if node.id in self.os_path_join_aliases:
                return "join"
            if node.id in self.os_path_dirname_aliases:
                return "dirname"
            if node.id in self.os_path_abspath_aliases:
                return "abspath"
            if node.id in self.os_path_split_aliases:
                return "split"
        if isinstance(node, ast.Attribute) and node.attr in _OS_PATH_HELPERS:
            if self.expression_denotes_os_path_module(node.value):
                return node.attr
        if isinstance(node, ast.Call) and dotted_name(node.func) == "getattr":
            if len(node.args) < 2:
                return None
            helper = self.static_string(node.args[1])
            if helper in _OS_PATH_HELPERS:
                if self.expression_denotes_os_path_module(node.args[0]):
                    return helper
        return None

    def expression_denotes_os_path_module(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` denotes the :mod:`os.path` module.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` for visible ``os.path`` module aliases.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.expression_denotes_os_path_module(ast.parse('os.path').body[0].value)
            True
        """
        if isinstance(node, ast.Name):
            return node.id in self.os_path_aliases
        if isinstance(node, ast.Attribute) and node.attr == "path":
            return isinstance(node.value, ast.Name) and node.value.id in self.os_aliases
        return False

    def sys_modules_method_name(self, node: ast.AST) -> Optional[str]:
        """
        Return the ``sys.modules`` method denoted by ``node``.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``"__getitem__"`` or ``"get"``, or ``None``.
        :rtype: str, optional

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> expr = ast.parse('getattr(sys.modules, "__getitem__")').body[0].value
            >>> visitor.sys_modules_method_name(expr)
            '__getitem__'
        """
        if isinstance(node, ast.Attribute) and node.attr in {"__getitem__", "get"}:
            if self.is_sys_modules_expr(node.value):
                return node.attr
        if isinstance(node, ast.Call) and dotted_name(node.func) == "getattr":
            if len(node.args) < 2:
                return None
            if self.is_sys_modules_expr(node.args[0]):
                method = self.static_string(node.args[1])
                if method in {"__getitem__", "get"}:
                    return method
        return None

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
        dynamic_code_rule = self.dynamic_code_boundary_rule(node)
        if dynamic_code_rule is not None:
            self.add_finding(
                node,
                dynamic_code_rule,
                "pytest files must not execute dynamic code that violates test-boundary rules",
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
        if self.is_sys_modules_tools_get_call(node):
            self.add_finding(
                node,
                TOOLS_DYNAMIC_RULE,
                "pytest files must not load repository tools modules from sys.modules",
            )
        if self.is_sys_modules_tools_getitem_call(node):
            self.add_finding(
                node,
                TOOLS_DYNAMIC_RULE,
                "pytest files must not load repository tools modules from sys.modules",
            )
        if self.is_command_call_running_tools(node):
            self.add_finding(
                node,
                TOOLS_EXEC_RULE,
                "pytest files must not execute repository tools scripts from subprocess or shell commands",
            )
        if self.is_command_call_running_source_install(node):
            self.add_finding(
                node,
                SOURCE_INSTALL_RULE,
                "pytest files must not run source-install smoke commands",
            )
        if self.is_repo_source_template_access(node):
            self.add_finding(
                node,
                SOURCE_TEMPLATE_RULE,
                "pytest files must not access the repository-source templates directory directly",
            )
        self.update_mutated_static_collection_aliases(node)
        self.generic_visit(node)

    def update_mutated_static_collection_aliases(self, node: ast.Call) -> None:
        """
        Propagate static taint through simple list mutation calls.

        The boundary guard treats starred path arguments as a compact way to
        hide repo-root and ``templates`` segments. Static list mutations such
        as ``segments.append("templates")`` or ``segments.extend([...])`` need
        the same conservative alias propagation as ``segments += [...]``.

        :param node: Call expression node to inspect.
        :type node: ast.Call
        :return: ``None``.
        :rtype: None

        Example::

            >>> source = 'segments = []' + chr(10) + 'segments.append("templates")'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> 'segments' in visitor.template_segment_aliases
            True
        """
        if not isinstance(node.func, ast.Attribute):
            return
        if not isinstance(node.func.value, ast.Name):
            return
        name = node.func.value.id
        elements = self.static_collection_mutation_elements(node)
        if not elements:
            return
        if any(self.is_repo_root_tainted(element) for element in elements):
            self.current_scope.repo_root_aliases.add(name)
        if any(
            self.expression_has_exact_segment(element, "templates")
            for element in elements
        ):
            self.current_scope.template_segment_aliases.add(name)
        if any(
            self.expression_or_alias_runs_tools_script(element) for element in elements
        ):
            self.current_scope.tools_command_aliases.add(name)
        if any(
            self.expression_or_alias_runs_source_install_command(element)
            for element in elements
        ):
            self.current_scope.source_install_command_aliases.add(name)

    def static_collection_mutation_elements(self, node: ast.Call) -> List[ast.AST]:
        """
        Return static elements added by a list-like mutation call.

        :param node: Mutation call expression.
        :type node: ast.Call
        :return: Added element expressions, or an empty list for unsupported
            calls.
        :rtype: List[ast.AST]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> call = ast.parse('segments.extend(["templates"])').body[0].value
            >>> [literal_string(item) for item in visitor.static_collection_mutation_elements(call)]
            ['templates']
        """
        if not isinstance(node.func, ast.Attribute):
            return []
        if node.func.attr == "append" and len(node.args) == 1:
            return [node.args[0]]
        if node.func.attr == "extend" and len(node.args) == 1:
            elements = self.static_iterable_elements(node.args[0])
            return elements or [node.args[0]]
        if node.func.attr == "insert" and len(node.args) >= 2:
            return [node.args[1]]
        return []

    def visit_Subscript(self, node: ast.Subscript) -> None:  # noqa: N802
        """
        Visit subscript expressions and report ``sys.modules`` tool lookups.

        :param node: Subscript expression node.
        :type node: ast.Subscript
        :return: ``None``.
        :rtype: None

        Example::

            >>> source = 'sys.modules["tools.package_templates"]'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
            >>> visitor.findings[0].rule
            'tools-dynamic-import'
        """
        if self.is_sys_modules_tools_subscript(node):
            self.add_finding(
                node,
                TOOLS_DYNAMIC_RULE,
                "pytest files must not load repository tools modules from sys.modules",
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

            >>> source = '_REPO_ROOT = Path(__file__).resolve().parents[1]' + chr(10) + '_REPO_ROOT / "templates"'
            >>> tree = ast.parse(source)
            >>> visitor = TestBoundaryVisitor(Path('test/x.py'), source, set())
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

    def visit_JoinedStr(self, node: ast.JoinedStr) -> None:  # noqa: N802
        """
        Visit f-strings and report repo-source template access.

        :param node: Joined string node.
        :type node: ast.JoinedStr
        :return: ``None``.
        :rtype: None

        Example::

            >>> source = 'repo_root = Path(__file__).resolve().parents[1]' + chr(10) + 'f"{repo_root}/templates"'
            >>> visitor = TestBoundaryVisitor(Path('test/x.py'), source, set())
            >>> visitor.visit(ast.parse(source))
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

            >>> tree = ast.parse('"python -m pip install --target ./vendor ."')
            >>> visitor = TestBoundaryVisitor(Path('x.py'), '"python -m pip install --target ./vendor ."', set())
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

            >>> source = '"python -m pip install --target ./vendor ."'
            >>> visitor = TestBoundaryVisitor(Path('x.py'), source, set())
            >>> visitor._visit_string_marker(ast.parse(source).body[0].value)
            >>> visitor.findings[0].rule
            'source-install-smoke'
        """
        if id(node) in self.docstring_node_ids:
            return
        value = self.static_string(node)
        if value is None:
            return
        if string_contains_source_install_marker(value):
            self.add_finding(
                node,
                SOURCE_INSTALL_RULE,
                "pytest files must not contain source-install smoke-test markers",
            )
            return

    def dynamic_code_boundary_rule(self, node: ast.Call) -> Optional[str]:
        """
        Return the first boundary rule found inside literal ``exec``/``eval`` code.

        :param node: Call expression node.
        :type node: ast.Call
        :return: First nested boundary rule, or ``None``.
        :rtype: str, optional

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.dynamic_code_boundary_rule(ast.parse('exec("import tools")').body[0].value)
            'tools-import'
            >>> visitor.dynamic_code_boundary_rule(ast.parse('eval("tools.x()")').body[0].value)
            'tools-call'
        """
        if dotted_name(node.func) not in {"exec", "eval"} or not node.args:
            return None
        if isinstance(node.args[0], ast.Name):
            alias_rule = self.dynamic_code_alias_rules.get(node.args[0].id)
            if alias_rule is not None:
                return alias_rule
        compiled_rule = self.compiled_dynamic_code_boundary_rule(node.args[0])
        if compiled_rule is not None:
            return compiled_rule
        source = self.static_string(node.args[0])
        if source is None:
            return None
        return self.boundary_rule_in_dynamic_source(source)

    def compiled_dynamic_code_boundary_rule(self, node: ast.AST) -> Optional[str]:
        """
        Return the boundary rule found in a ``compile(...)`` source argument.

        :param node: AST expression node.
        :type node: ast.AST
        :return: Nested boundary rule, or ``None``.
        :rtype: str, optional

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> call = ast.parse('compile("import tools.x", "<string>", "exec")').body[0].value
            >>> visitor.compiled_dynamic_code_boundary_rule(call)
            'tools-import'
        """
        if not isinstance(node, ast.Call):
            return None
        if dotted_name(node.func) != "compile" or not node.args:
            return None
        source = self.static_string(node.args[0])
        if source is None:
            return None
        return self.boundary_rule_in_dynamic_source(source)

    def boundary_rule_in_dynamic_source(self, source: str) -> Optional[str]:
        """
        Return the first boundary rule found in nested Python source.

        :param source: Python source string.
        :type source: str
        :return: First nested boundary rule, or ``None``.
        :rtype: str, optional

        Example::

            >>> TestBoundaryVisitor(Path('x.py'), '', set()).boundary_rule_in_dynamic_source('import tools.x')
            'tools-import'
        """
        try:
            tree = ast.parse(source)
        except SyntaxError:
            # SyntaxError: exec/eval literal is not parseable Python source, so the
            # static boundary guard cannot inspect it as nested code.
            return None
        visitor = TestBoundaryVisitor(
            self.path,
            source,
            collect_defined_names(tree),
            collect_docstring_node_ids(tree),
        )
        visitor.visit(tree)
        if visitor.findings:
            return visitor.findings[0].rule
        return None

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
            >>> visitor.is_dynamic_tools_import_call(ast.parse('__import__(name="tools.x")').body[0].value)
            True
            >>> visitor.is_dynamic_tools_import_call(ast.parse('builtins.__import__("tools.x")').body[0].value)
            True
            >>> visitor.current_scope.builtins_aliases.add('bi')
            >>> visitor.is_dynamic_tools_import_call(ast.parse('bi.__import__("tools.x")').body[0].value)
            True
            >>> visitor.current_scope.importlib_aliases.add('import_module')
            >>> visitor.is_dynamic_tools_import_call(ast.parse('import_module(".x", package="tools")').body[0].value)
            True
            >>> visitor.is_dynamic_tools_import_call(ast.parse('import_module(".x", "tools")').body[0].value)
            True
            >>> visitor.is_dynamic_tools_import_call(ast.parse('pytest.importorskip("tools.package_templates")').body[0].value)
            True
            >>> visitor.is_dynamic_tools_import_call(ast.parse('runpy.run_module("tools.package_templates")').body[0].value)
            True
        """
        if not isinstance(node, ast.Call):
            return False
        func_name = dotted_name(node.func)
        if func_name == "__import__" or self.expression_denotes_builtin_import(
            node.func
        ):
            return self.dynamic_import_target_is_tools(node)
        if self.is_pytest_importorskip_call(node):
            return self.dynamic_import_target_is_tools(node)
        if self.is_runpy_run_module_call(node):
            return self.dynamic_import_target_is_tools(node)
        if self.is_runpy_run_path_call(node) and node.args:
            return self.expression_or_alias_runs_tools_script(node.args[0])
        if self.is_importlib_util_spec_from_file_location_call(node):
            return self.importlib_util_spec_location_runs_tools_script(node)
        if self.expression_denotes_importlib_import_module(node.func):
            return self.dynamic_import_target_is_tools(node)
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "__import__" and isinstance(node.func.value, ast.Name):
                if node.func.value.id in self.builtins_aliases:
                    return self.dynamic_import_target_is_tools(node)
            if node.func.attr == "import_module" and isinstance(
                node.func.value, ast.Name
            ):
                if node.func.value.id in self.importlib_aliases:
                    return self.dynamic_import_target_is_tools(node)
        if isinstance(node.func, ast.Name) and node.func.id in self.importlib_aliases:
            return self.dynamic_import_target_is_tools(node)
        return False

    def is_module_import_call(self, node: ast.Call) -> bool:
        """
        Return whether ``node`` calls a visible module import helper.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` for ``__import__`` and ``importlib.import_module`` forms.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_module_import_call(ast.parse('__import__("x")').body[0].value)
            True
            >>> visitor.is_module_import_call(ast.parse('importlib.import_module("x")').body[0].value)
            True
        """
        func_name = dotted_name(node.func)
        if func_name == "__import__" or self.expression_denotes_builtin_import(
            node.func
        ):
            return True
        if self.expression_denotes_importlib_import_module(node.func):
            return True
        return (
            isinstance(node.func, ast.Name) and node.func.id in self.importlib_aliases
        )

    def dynamic_import_target_module_name(self, node: ast.Call) -> Optional[str]:
        """
        Return the statically visible target name of a dynamic import call.

        :param node: Dynamic import call expression.
        :type node: ast.Call
        :return: Imported module name, or ``None`` when dynamic.
        :rtype: str, optional

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.dynamic_import_target_module_name(ast.parse('__import__("importlib")').body[0].value)
            'importlib'
        """
        args = self.static_call_arguments(node)
        name = self.static_module_name(args[0]) if args else None
        for keyword in node.keywords:
            if keyword.arg == "name":
                name = self.static_module_name(keyword.value)
        return name

    def expression_denotes_builtin_import(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` denotes the built-in ``__import__`` helper.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` when the expression resolves to ``__import__``.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> expr = ast.parse('getattr(builtins, "__import__")').body[0].value
            >>> visitor.expression_denotes_builtin_import(expr)
            True
            >>> expr = ast.parse('getattr(__builtins__, "__import__")').body[0].value
            >>> visitor.expression_denotes_builtin_import(expr)
            True
        """
        if isinstance(node, ast.Attribute) and node.attr == "__import__":
            if isinstance(node.value, ast.Name):
                return node.value.id in self.builtins_aliases or node.value.id == (
                    "__builtins__"
                )
        if isinstance(node, ast.Call) and dotted_name(node.func) == "getattr":
            if len(node.args) < 2:
                return False
            if self.static_string(node.args[1]) != "__import__":
                return False
            target = node.args[0]
            return isinstance(target, ast.Name) and (
                target.id in self.builtins_aliases or target.id == "__builtins__"
            )
        return False

    def is_importlib_util_spec_from_file_location_call(self, node: ast.Call) -> bool:
        """
        Return whether ``node`` calls ``spec_from_file_location``.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` for visible importlib utility spec helpers.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> call = ast.parse('importlib.util.spec_from_file_location("x", "tools/x.py")').body[0].value
            >>> visitor.is_importlib_util_spec_from_file_location_call(call)
            True
        """
        return self.expression_denotes_importlib_util_spec_helper(node.func)

    def importlib_util_spec_location_runs_tools_script(self, node: ast.Call) -> bool:
        """
        Return whether a spec helper location points at repository tools.

        :param node: ``spec_from_file_location`` call expression.
        :type node: ast.Call
        :return: ``True`` when the location argument targets ``tools/*.py``.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> call = ast.parse('importlib.util.spec_from_file_location("x", "tools/x.py")').body[0].value
            >>> visitor.importlib_util_spec_location_runs_tools_script(call)
            True
        """
        if len(node.args) > 1:
            return self.expression_or_alias_runs_tools_script(node.args[1])
        for keyword in node.keywords:
            if keyword.arg == "location":
                return self.expression_or_alias_runs_tools_script(keyword.value)
        return False

    def is_pytest_importorskip_call(self, node: ast.Call) -> bool:
        """
        Return whether ``node`` calls :func:`pytest.importorskip`.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when the callee is a visible ``importorskip`` helper.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_pytest_importorskip_call(ast.parse('pytest.importorskip("x")').body[0].value)
            True
        """
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "importorskip" and isinstance(
                node.func.value, ast.Name
            ):
                return node.func.value.id in self.pytest_aliases
        return (
            isinstance(node.func, ast.Name)
            and node.func.id in self.pytest_importorskip_aliases
        )

    def is_runpy_run_module_call(self, node: ast.Call) -> bool:
        """
        Return whether ``node`` calls :func:`runpy.run_module`.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when the callee is a visible ``run_module`` helper.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_runpy_run_module_call(ast.parse('runpy.run_module("x")').body[0].value)
            True
        """
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "run_module" and isinstance(node.func.value, ast.Name):
                return node.func.value.id in self.runpy_aliases
        return (
            isinstance(node.func, ast.Name)
            and node.func.id in self.runpy_run_module_aliases
        )

    def is_runpy_run_path_call(self, node: ast.Call) -> bool:
        """
        Return whether ``node`` calls :func:`runpy.run_path`.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when the callee is a visible ``run_path`` helper.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_runpy_run_path_call(ast.parse('runpy.run_path("x.py")').body[0].value)
            True
        """
        if isinstance(node.func, ast.Attribute):
            if node.func.attr == "run_path" and isinstance(node.func.value, ast.Name):
                return node.func.value.id in self.runpy_aliases
        return (
            isinstance(node.func, ast.Name)
            and node.func.id in self.runpy_run_path_aliases
        )

    def dynamic_import_target_is_tools(self, node: ast.Call) -> bool:
        """
        Return whether a dynamic import call targets ``tools``.

        :param node: Dynamic import call expression.
        :type node: ast.Call
        :return: ``True`` when positional or keyword import arguments resolve to ``tools``.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> call = ast.parse('import_module(name="tools.x")').body[0].value
            >>> visitor.dynamic_import_target_is_tools(call)
            True
            >>> visitor.current_scope.tools_module_name_aliases.add('module_name')
            >>> call = ast.parse('import_module(module_name)').body[0].value
            >>> visitor.dynamic_import_target_is_tools(call)
            True
            >>> call = ast.parse('import_module(*("tools.x",))').body[0].value
            >>> visitor.dynamic_import_target_is_tools(call)
            True
            >>> call = ast.parse('import_module(*(".x", "tools"))').body[0].value
            >>> visitor.dynamic_import_target_is_tools(call)
            True
        """
        args = self.static_call_arguments(node)
        name = None
        package = None
        if args:
            name = self.static_module_name(args[0])
        if len(args) > 1:
            package = self.static_module_name(args[1])
        for keyword in node.keywords:
            if keyword.arg == "name":
                name = self.static_module_name(keyword.value)
            elif keyword.arg == "package":
                package = self.static_module_name(keyword.value)
        if name is None:
            return False
        if is_tools_module_name(name):
            return True
        if name.startswith(".") and package is not None:
            return is_tools_module_name(package)
        return False

    def static_module_name(self, node: ast.AST) -> Optional[str]:
        """
        Return a statically known module-name string.

        :param node: AST expression node.
        :type node: ast.AST
        :return: Module name, ``"tools"`` for tools-name aliases, or ``None``.
        :rtype: str, optional

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.tools_module_name_aliases.add('name')
            >>> visitor.static_module_name(ast.Name(id='name'))
            'tools'
        """
        if isinstance(node, ast.Starred):
            elements = self.static_iterable_elements(node.value)
            if elements:
                return self.static_module_name(elements[0])
            return self.static_module_name(node.value)
        value = self.static_string(node)
        if value is not None:
            return value
        if isinstance(node, ast.Name) and node.id in self.tools_module_name_aliases:
            return "tools"
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self.static_module_name(node.left)
            right = self.static_module_name(node.right)
            if left is not None and right is not None:
                return left + right
        return None

    def static_call_arguments(self, node: ast.Call) -> List[ast.AST]:
        """
        Return positional call arguments with static star-unpacking expanded.

        :param node: Call expression to inspect.
        :type node: ast.Call
        :return: Positional argument expressions.
        :rtype: List[ast.AST]

        Example::

            >>> call = ast.parse('f(*("tools.x",))').body[0].value
            >>> len(TestBoundaryVisitor(Path('x.py'), '', set()).static_call_arguments(call))
            1
        """
        arguments = []
        for argument in node.args:
            if isinstance(argument, ast.Starred):
                elements = self.static_iterable_elements(argument.value)
                if elements:
                    arguments.extend(elements)
                else:
                    arguments.append(argument)
            else:
                arguments.append(argument)
        return arguments

    def expression_denotes_tools_module(self, node: ast.AST) -> bool:
        """
        Return whether an expression denotes a ``tools`` module-name string.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` for tools-module literals or known aliases.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.expression_denotes_tools_module(ast.parse('"tools" + ".x"').body[0].value)
            True
        """
        value = self.static_module_name(node)
        return value is not None and is_tools_module_name(value)

    def is_tools_attribute_call(self, node: ast.Call) -> bool:
        """
        Return whether a call targets a known tools module alias.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when the callee is under a tools alias.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_tools_attribute_call(ast.parse('tools.x()').body[0].value)
            True
            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', {'tools'})
            >>> visitor.is_tools_attribute_call(ast.parse('tools.x()').body[0].value)
            False
            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.tools_aliases.add('tools')
            >>> visitor.is_tools_attribute_call(ast.parse('tools.x()').body[0].value)
            True
        """
        if not isinstance(node.func, ast.Attribute):
            return False
        root = self._attribute_root_name(node.func)
        if root == "tools" and root not in self.defined_names:
            return True
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
            >>> visitor.current_scope.dynamic_tools_aliases.add('tools_module')
            >>> visitor.is_getattr_tools_call(ast.parse('getattr(tools_module, "x")').body[0].value)
            True
            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_getattr_tools_call(ast.parse('getattr(tools, "x")').body[0].value)
            False
        """
        if dotted_name(node.func) != "getattr" or not node.args:
            return False
        target = node.args[0]
        if isinstance(target, ast.Name):
            name = target.id
            return name in self.tools_aliases or name in self.dynamic_tools_aliases
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

    def is_sys_modules_expr(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` denotes :data:`sys.modules`.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` for ``sys.modules`` or imported ``modules`` aliases.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_sys_modules_expr(ast.parse('sys.modules').body[0].value)
            True
        """
        if isinstance(node, ast.Name):
            return node.id in self.sys_modules_aliases
        if isinstance(node, ast.Attribute) and node.attr == "modules":
            return (
                isinstance(node.value, ast.Name) and node.value.id in self.sys_aliases
            )
        return False

    def is_sys_modules_tools_subscript(self, node: ast.Subscript) -> bool:
        """
        Return whether ``node`` reads a ``tools`` module from ``sys.modules``.

        :param node: Subscript expression node.
        :type node: ast.Subscript
        :return: ``True`` when the lookup key names a ``tools`` module.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> expr = ast.parse('sys.modules["tools.package_templates"]').body[0].value
            >>> visitor.is_sys_modules_tools_subscript(expr)
            True
        """
        if not self.is_sys_modules_expr(node.value):
            return False
        key = node.slice
        if AST_INDEX_TYPE is not None and isinstance(key, AST_INDEX_TYPE):
            key = key.value
        return self.expression_denotes_tools_module(key)

    def is_sys_modules_tools_get_call(self, node: ast.Call) -> bool:
        """
        Return whether ``node`` calls ``sys.modules.get`` for ``tools``.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when ``get`` receives a ``tools`` module name.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> call = ast.parse('sys.modules.get("tools.package_templates")').body[0].value
            >>> visitor.is_sys_modules_tools_get_call(call)
            True
        """
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "get":
            return False
        if not self.is_sys_modules_expr(node.func.value):
            return False
        return bool(node.args) and self.expression_denotes_tools_module(node.args[0])

    def is_sys_modules_tools_getitem_call(self, node: ast.Call) -> bool:
        """
        Return whether ``node`` calls a ``sys.modules`` getitem alias.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when the call reads a ``tools`` module.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> source = 'getattr(sys.modules, "__getitem__")("tools.x")'
            >>> visitor.is_sys_modules_tools_getitem_call(ast.parse(source).body[0].value)
            True
        """
        if isinstance(node.func, ast.Name):
            if node.func.id in self.sys_modules_getitem_aliases:
                return bool(node.args) and self.expression_denotes_tools_module(
                    node.args[0]
                )
            if node.func.id in self.sys_modules_get_aliases:
                return bool(node.args) and self.expression_denotes_tools_module(
                    node.args[0]
                )
        method = self.sys_modules_method_name(node.func)
        if method in {"__getitem__", "get"}:
            return bool(node.args) and self.expression_denotes_tools_module(
                node.args[0]
            )
        return False

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
            >>> visitor.is_command_call_running_tools(ast.parse('os.execlp("python", "python", "tools/x.py")').body[0].value)
            True
            >>> visitor.is_command_call_running_tools(ast.parse('os.execvp("python", ["python", "tools/x.py"])').body[0].value)
            True
        """
        if self.expression_denotes_subprocess_command_helper(node.func):
            return any(
                self.expression_or_alias_runs_tools_script(command)
                for command in self.subprocess_command_arguments(node)
            )
        os_helper = self.expression_denotes_os_command_helper(node.func)
        if os_helper is not None:
            return any(
                self.expression_or_alias_runs_tools_script(command)
                for command in self.os_command_arguments(node, os_helper)
            )
        if self.is_subprocess_command_call(node):
            return any(
                self.expression_or_alias_runs_tools_script(command)
                for command in self.subprocess_command_arguments(node)
            )
        os_method = self.os_command_method_name(node)
        if os_method is not None:
            return any(
                self.expression_or_alias_runs_tools_script(command)
                for command in self.os_command_arguments(node, os_method)
            )
        return False

    def is_command_call_running_source_install(self, node: ast.Call) -> bool:
        """
        Return whether a subprocess or shell call performs a source install.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` for command calls such as ``pip install .``.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_command_call_running_source_install(ast.parse('subprocess.run(["python", "-m", "pip", "install", "."])').body[0].value)
            True
        """
        if self.expression_denotes_subprocess_command_helper(node.func):
            return any(
                self.expression_or_alias_runs_source_install_command(command)
                for command in self.subprocess_command_arguments(node)
            )
        os_helper = self.expression_denotes_os_command_helper(node.func)
        if os_helper is not None:
            return any(
                self.expression_or_alias_runs_source_install_command(command)
                for command in self.os_command_arguments(node, os_helper)
            )
        if self.is_subprocess_command_call(node):
            return any(
                self.expression_or_alias_runs_source_install_command(command)
                for command in self.subprocess_command_arguments(node)
            )
        os_method = self.os_command_method_name(node)
        if os_method is not None:
            return any(
                self.expression_or_alias_runs_source_install_command(command)
                for command in self.os_command_arguments(node, os_method)
            )
        return False

    def os_command_arguments(self, node: ast.Call, method_name: str) -> List[ast.AST]:
        """
        Return command-bearing arguments for an :mod:`os` command helper call.

        :param node: OS command call expression.
        :type node: ast.Call
        :param method_name: OS command helper name.
        :type method_name: str
        :return: Candidate command argument expressions.
        :rtype: List[ast.AST]

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> call = ast.parse('os.system("python tools/x.py")').body[0].value
            >>> len(visitor.os_command_arguments(call, 'system'))
            1
            >>> call = ast.parse('os.execv("python", ["python", "tools/x.py"])').body[0].value
            >>> len(visitor.os_command_arguments(call, 'execv'))
            2
            >>> call = ast.parse('os.spawnve(os.P_WAIT, "python", ["python"], {"PYTHONPATH": "tools/x.py"})').body[0].value
            >>> len(visitor.os_command_arguments(call, 'spawnve'))
            2
        """
        if method_name.startswith("spawn"):
            if method_name in {"spawnle", "spawnlpe"} and len(node.args) > 3:
                return node.args[1:-1]
            if method_name in {"spawnve", "spawnvpe"}:
                return node.args[1:3]
            return node.args[1:]
        if method_name.startswith("exec"):
            if method_name in {"execle", "execlpe"} and len(node.args) > 2:
                return node.args[:-1]
            if method_name in {"execve", "execvpe"}:
                return node.args[:2]
            return node.args
        return node.args[:1]

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
            >>> call = ast.parse('subprocess.run(cmd=["python"])').body[0].value
            >>> len(visitor.subprocess_command_arguments(call))
            1
        """
        if node.args:
            return [node.args[0]]
        for keyword in node.keywords:
            if keyword.arg in {"args", "argv", "cmd"}:
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
            >>> visitor.current_scope.tools_command_aliases.add('cmd')
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
        value = self.static_string(node)
        if value is not None and command_text_runs_tools_script(value):
            return True
        return expression_runs_tools_script(node)

    def expression_or_alias_runs_source_install_command(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` is a source-install command or known alias.

        :param node: Command expression node.
        :type node: ast.AST
        :return: ``True`` when the expression performs a source install.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.source_install_command_aliases.add('cmd')
            >>> visitor.expression_or_alias_runs_source_install_command(ast.Name(id='cmd'))
            True
        """
        if any(
            isinstance(child, ast.Name)
            and child.id in self.source_install_command_aliases
            for child in ast.walk(node)
        ):
            return True
        value = self.static_string(node)
        if value is not None and string_contains_source_install_marker(value):
            return True
        return expression_runs_source_install_command(node)

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
            >>> source = 'from os import execvp as run_exec'
            >>> visitor.visit(ast.parse(source))
            >>> visitor.os_command_method_name(ast.parse('run_exec("python", ["python"])').body[0].value)
            'execvp'
        """
        if isinstance(node.func, ast.Attribute):
            if node.func.attr in _OS_COMMAND_METHODS and isinstance(
                node.func.value, ast.Name
            ):
                if node.func.value.id in self.os_aliases:
                    return node.func.attr
        if isinstance(node.func, ast.Name):
            if node.func.id in self.os_function_aliases:
                return self.os_function_alias_methods.get(node.func.id, node.func.id)
        return None

    @property
    def repo_root_parent_index(self) -> int:
        """
        Return the ``Path(__file__).parents`` index that reaches repo root.

        :return: Parent index for this file's repository root.
        :rtype: int

        Example::

            >>> TestBoundaryVisitor(Path('test/x.py'), '', set()).repo_root_parent_index
            1
        """
        return len(self.path.parent.parts)

    @property
    def repo_root_dirname_depth(self) -> int:
        """
        Return nested ``dirname`` depth needed to reach repo root.

        :return: Number of ``dirname`` hops from ``__file__`` to repo root.
        :rtype: int

        Example::

            >>> TestBoundaryVisitor(Path('test/x.py'), '', set()).repo_root_dirname_depth
            2
        """
        return self.repo_root_parent_index + 1

    def expression_denotes_file_parents_sequence(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` denotes ``Path(__file__).parents``.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` for a visible ``parents`` sequence rooted at ``__file__``.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.expression_denotes_file_parents_sequence(ast.parse('Path(__file__).resolve().parents').body[0].value)
            True
        """
        return (
            isinstance(node, ast.Attribute)
            and node.attr == "parents"
            and node_contains_name(node.value, "__file__")
        )

    def file_parents_expr_reaches_repo_root(self, node: ast.AST) -> bool:
        """
        Return whether a ``__file__`` parent expression reaches repo root.

        :param node: AST node to inspect.
        :type node: ast.AST
        :return: ``True`` when the parent expression reaches this file's repo root.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('test/x.py'), '', set())
            >>> visitor.file_parents_expr_reaches_repo_root(ast.parse('Path(__file__).parents[1]').body[0].value)
            True
            >>> visitor.file_parents_expr_reaches_repo_root(ast.parse('Path(__file__).resolve().parent / ".."').body[0].value)
            True
            >>> visitor = TestBoundaryVisitor(Path('test/sub/x.py'), '', set())
            >>> visitor.file_parents_expr_reaches_repo_root(ast.parse('Path(__file__).parents[0]').body[0].value)
            False
            >>> visitor.file_parents_expr_reaches_repo_root(ast.parse('Path(__file__).parents[1]').body[0].value)
            False
            >>> visitor.file_parents_expr_reaches_repo_root(ast.parse('Path(__file__).parents[2]').body[0].value)
            True
        """
        for child in ast.walk(node):
            if isinstance(child, ast.Subscript):
                value = child.value
                if isinstance(value, ast.Attribute) and value.attr == "parents":
                    if node_contains_name(value.value, "__file__"):
                        index = subscript_integer(child)
                        if index is not None and index >= self.repo_root_parent_index:
                            return True
            if parent_chain_depth(child) >= self.repo_root_dirname_depth:
                return True
        if self.file_path_hops_reach_repo_root(node):
            return True
        return False

    def file_path_hops_reach_repo_root(self, node: ast.AST) -> bool:
        """
        Return whether a simple ``__file__`` path expression climbs to repo root.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` when ``.parent`` and ``".."`` hops reach repo root.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('test/x.py'), '', set())
            >>> visitor.file_path_hops_reach_repo_root(ast.parse('Path(__file__).resolve().parent / ".."').body[0].value)
            True
        """
        hops = self.file_path_parent_hops(node)
        return hops is not None and hops >= self.repo_root_dirname_depth

    def file_path_parent_hops(self, node: ast.AST) -> Optional[int]:
        """
        Return parent-hop count for a simple ``__file__`` path expression.

        :param node: AST expression node.
        :type node: ast.AST
        :return: Parent-hop count, or ``None`` when the expression is dynamic.
        :rtype: int, optional

        Example::

            >>> visitor = TestBoundaryVisitor(Path('test/x.py'), '', set())
            >>> visitor.file_path_parent_hops(ast.parse('Path(__file__).resolve().parent / ".."').body[0].value)
            2
            >>> visitor.file_path_parent_hops(ast.parse('Path(__file__).resolve().parents[0] / ".."').body[0].value)
            2
        """
        if isinstance(node, ast.Name):
            return self.path_parent_hop_aliases.get(node.id)
        if node_contains_name(node, "__file__") and not isinstance(
            node, (ast.BinOp, ast.Call, ast.Attribute, ast.Subscript)
        ):
            return 0
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            left = self.file_path_parent_hops(node.left)
            if left is None:
                return None
            segment = self.static_string(node.right)
            if segment == "..":
                return left + 1
            if segment is not None:
                return left
            return None
        if isinstance(node, ast.Attribute) and node.attr == "parent":
            base = self.file_path_parent_hops(node.value)
            if base is not None:
                return base + 1
        if isinstance(node, ast.Subscript):
            value = node.value
            if isinstance(value, ast.Name) and value.id in self.file_parents_aliases:
                index = subscript_integer(node)
                if index is not None:
                    return index + 1
            if isinstance(value, ast.Attribute) and value.attr == "parents":
                if node_contains_name(value.value, "__file__"):
                    index = subscript_integer(node)
                    if index is not None:
                        return index + 1
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in {"resolve", "absolute"}:
                    return self.file_path_parent_hops(node.func.value)
            if self.is_path_constructor_call(node) and node.args:
                if node_contains_name(node.args[0], "__file__"):
                    return 0
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
            >>> visitor.current_scope.repo_root_aliases.add('repo_root')
            >>> visitor.is_repo_root_tainted(ast.parse('str(repo_root)').body[0].value)
            True
            >>> visitor.current_scope.template_segment_aliases.add('segments')
            >>> visitor.current_scope.repo_root_aliases.add('segments')
            >>> visitor.is_repo_root_tainted(ast.parse('*segments').body[0].value)
            True
        """
        if isinstance(node, ast.Name):
            return node.id in self.repo_root_aliases
        if isinstance(node, ast.Starred):
            return self.is_repo_root_tainted(node.value)
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            if any(self.is_repo_root_tainted(element) for element in node.elts):
                return True
            hops = self.path_argument_sequence_parent_hops(node.elts)
            return hops is not None and hops >= self.repo_root_dirname_depth
        if isinstance(node, ast.JoinedStr):
            return any(self.is_repo_root_tainted(value) for value in node.values)
        if isinstance(node, ast.FormattedValue):
            return self.is_repo_root_tainted(node.value)
        if self.file_parents_expr_reaches_repo_root(node):
            return True
        if isinstance(node, ast.Call):
            if self.os_path_dirname_depth(node) >= self.repo_root_dirname_depth:
                return True
            if self.is_path_cwd_call(node) or self.is_os_getcwd_call(node):
                return True
            if self.is_workspace_environment_call(node):
                return True
        if self.is_workspace_environment_subscript(node):
            return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self.is_repo_root_tainted(node.left) or self.is_repo_root_tainted(
                node.right
            )
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return self.is_repo_root_tainted(node.left) or self.is_repo_root_tainted(
                node.right
            )
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in {"resolve", "absolute", "joinpath"}:
                    return self.is_repo_root_tainted(node.func.value)
                if node.func.attr == "format":
                    return self.is_repo_root_tainted_format_call(node)
            if dotted_name(node.func) in {"str", "repr", "bytes", "os.fspath"}:
                return any(self.is_repo_root_tainted(arg) for arg in node.args)
            if dotted_name(node.func) in {"format", "builtins.format"}:
                return any(self.is_repo_root_tainted(arg) for arg in node.args)
            if self.is_path_constructor_call(node) and node.args:
                if self.is_repo_root_tainted(node.args[0]):
                    return True
                return any(is_exact_segment(arg, "templates") for arg in node.args[1:])
            if self.is_os_path_passthrough_call(node) and node.args:
                return node_contains_name(
                    node.args[0], "__file__"
                ) or self.is_repo_root_tainted(node.args[0])
            if self.is_os_path_join_call(node) and node.args:
                if self.os_path_join_reaches_repo_root(node):
                    return True
                return self.is_repo_root_tainted(node.args[0])
        return False

    def path_argument_sequence_parent_hops(
        self, arguments: Sequence[ast.AST]
    ) -> Optional[int]:
        """
        Return parent-hop count for path helper argument sequences.

        This helper models simple path-building calls such as
        ``os.path.join(os.path.dirname(__file__), "..")`` where a base path and
        static ``".."`` segments collectively climb to the repository root.

        :param arguments: Path-building argument expressions.
        :type arguments: Sequence[ast.AST]
        :return: Parent-hop count, or ``None`` when the sequence is dynamic.
        :rtype: int, optional

        Example::

            >>> visitor = TestBoundaryVisitor(Path('test/x.py'), '', set())
            >>> expr = ast.parse('os.path.dirname(__file__)').body[0].value
            >>> visitor.path_argument_sequence_parent_hops([expr, ast.Constant(value='..')])
            2
        """
        if not arguments:
            return None
        hops = self.path_argument_parent_hops(arguments[0])
        if hops is None:
            return None
        for argument in arguments[1:]:
            segment = self.static_string(argument)
            if segment == "..":
                hops += 1
            elif segment is not None:
                continue
            else:
                return None
        return hops

    def path_argument_parent_hops(self, node: ast.AST) -> Optional[int]:
        """
        Return parent-hop count for one path-building argument.

        :param node: Path argument expression.
        :type node: ast.AST
        :return: Parent-hop count, or ``None`` when unknown.
        :rtype: int, optional

        Example::

            >>> visitor = TestBoundaryVisitor(Path('test/x.py'), '', set())
            >>> visitor.path_argument_parent_hops(ast.parse('os.path.dirname(__file__)').body[0].value)
            1
            >>> visitor.path_argument_parent_hops(ast.parse('__file__').body[0].value)
            0
        """
        if isinstance(node, ast.Name) and node.id == "__file__":
            return 0
        if isinstance(node, ast.Name):
            parent_hops = self.path_parent_hop_aliases.get(node.id)
            if parent_hops is not None:
                return parent_hops
            if node.id in self.repo_root_aliases:
                return self.repo_root_dirname_depth
        if isinstance(node, ast.Starred):
            if self.is_repo_root_tainted(node.value):
                return self.repo_root_dirname_depth
            return None
        dirname_depth = self.os_path_dirname_depth(node)
        if dirname_depth:
            return dirname_depth
        file_hops = self.file_path_parent_hops(node)
        if file_hops is not None:
            return file_hops
        if isinstance(node, ast.Call):
            if self.is_os_path_passthrough_call(node) and node.args:
                return self.path_argument_parent_hops(node.args[0])
            if self.is_os_path_join_call(node):
                return self.path_argument_sequence_parent_hops(node.args)
        return None

    def os_path_join_reaches_repo_root(self, node: ast.Call) -> bool:
        """
        Return whether ``os.path.join`` arguments climb to repo root.

        :param node: ``os.path.join`` call expression.
        :type node: ast.Call
        :return: ``True`` when the static path sequence reaches repo root.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('test/x.py'), '', set())
            >>> call = ast.parse('os.path.join(os.path.dirname(__file__), "..", "templates")').body[0].value
            >>> visitor.os_path_join_reaches_repo_root(call)
            True
        """
        if not self.is_os_path_join_call(node):
            return False
        hops = self.path_argument_sequence_parent_hops(node.args)
        return hops is not None and hops >= self.repo_root_dirname_depth

    def is_path_constructor_call(self, node: ast.Call) -> bool:
        """
        Return whether ``node`` constructs a :class:`pathlib.Path`.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when the callee is a visible ``Path`` constructor.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_path_constructor_call(ast.parse('Path("x")').body[0].value)
            True
        """
        if isinstance(node.func, ast.Name):
            return node.func.id in self.path_class_aliases
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in _PATH_CONSTRUCTOR_NAMES
        ):
            return (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id in self.pathlib_aliases
            )
        return False

    def is_path_cwd_call(self, node: ast.Call) -> bool:
        """
        Return whether ``node`` calls ``Path.cwd``.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` for visible ``Path.cwd`` helpers.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_path_cwd_call(ast.parse('Path.cwd()').body[0].value)
            True
        """
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "cwd":
            return False
        value = node.func.value
        if isinstance(value, ast.Name):
            return value.id in self.path_class_aliases
        if isinstance(value, ast.Attribute) and value.attr == "Path":
            return (
                isinstance(value.value, ast.Name)
                and value.value.id in self.pathlib_aliases
            )
        return False

    def is_os_getcwd_call(self, node: ast.Call) -> bool:
        """
        Return whether ``node`` calls :func:`os.getcwd`.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` for visible ``getcwd`` helpers.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_os_getcwd_call(ast.parse('os.getcwd()').body[0].value)
            True
        """
        if isinstance(node.func, ast.Attribute) and node.func.attr == "getcwd":
            return (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id in self.os_aliases
            )
        return (
            isinstance(node.func, ast.Name) and node.func.id in self.os_getcwd_aliases
        )

    def is_os_environ_expr(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` denotes :data:`os.environ`.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` for visible ``os.environ`` aliases.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_os_environ_expr(ast.parse('os.environ').body[0].value)
            True
        """
        return (
            isinstance(node, ast.Attribute)
            and node.attr == "environ"
            and isinstance(node.value, ast.Name)
            and node.value.id in self.os_aliases
        )

    def is_workspace_environment_subscript(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` reads a workspace-root environment variable.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` for ``os.environ["GITHUB_WORKSPACE"]``.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> expr = ast.parse('os.environ["GITHUB_WORKSPACE"]').body[0].value
            >>> visitor.is_workspace_environment_subscript(expr)
            True
        """
        if not isinstance(node, ast.Subscript):
            return False
        if not self.is_os_environ_expr(node.value):
            return False
        key = node.slice
        if AST_INDEX_TYPE is not None and isinstance(key, AST_INDEX_TYPE):
            key = key.value
        return literal_string(key) == "GITHUB_WORKSPACE"

    def is_workspace_environment_call(self, node: ast.Call) -> bool:
        """
        Return whether ``node`` calls ``os.environ.get`` for workspace root.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` for ``os.environ.get("GITHUB_WORKSPACE")``.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> call = ast.parse('os.environ.get("GITHUB_WORKSPACE")').body[0].value
            >>> visitor.is_workspace_environment_call(call)
            True
        """
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "get":
            return False
        if not self.is_os_environ_expr(node.func.value):
            return False
        return bool(node.args) and literal_string(node.args[0]) == "GITHUB_WORKSPACE"

    def is_repo_root_tainted_format_call(self, node: ast.Call) -> bool:
        """
        Return whether ``str.format`` interpolates a repo-root value.

        :param node: Call expression for a ``format`` method.
        :type node: ast.Call
        :return: ``True`` when any format argument is repo-root tainted.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.repo_root_aliases.add('repo_root')
            >>> visitor.is_repo_root_tainted_format_call(ast.parse('"{}".format(repo_root)').body[0].value)
            True
        """
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "format":
            return False
        values = list(node.args) + [keyword.value for keyword in node.keywords]
        return any(self.is_repo_root_tainted(value) for value in values)

    def format_call_has_exact_segment(self, node: ast.Call, segment: str) -> bool:
        """
        Return whether a ``str.format`` call can insert ``segment``.

        :param node: Call expression for a ``format`` method.
        :type node: ast.Call
        :param segment: String segment to search for.
        :type segment: str
        :return: ``True`` when the format string or replacement values contain
            the exact segment.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.template_segment_aliases.add('seg')
            >>> call = ast.parse('"{root}/{seg}".format(root=repo_root, seg=seg)').body[0].value
            >>> visitor.format_call_has_exact_segment(call, 'templates')
            True
        """
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "format":
            return False
        values = [node.func.value] + list(node.args)
        values.extend(keyword.value for keyword in node.keywords)
        return any(
            self.expression_has_exact_segment(value, segment) for value in values
        )

    def mod_format_value_is_repo_root_tainted(self, node: ast.AST) -> bool:
        """
        Return whether a ``%`` format value carries repo-root taint.

        :param node: Format value expression.
        :type node: ast.AST
        :return: ``True`` when any replacement value is repo-root tainted.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.repo_root_aliases.add('repo_root')
            >>> visitor.mod_format_value_is_repo_root_tainted(ast.parse('repo_root').body[0].value)
            True
            >>> visitor.mod_format_value_is_repo_root_tainted(ast.parse('(1, repo_root)').body[0].value)
            True
        """
        if isinstance(node, (ast.Tuple, ast.List)):
            return any(self.is_repo_root_tainted(item) for item in node.elts)
        if isinstance(node, ast.Dict):
            return any(self.is_repo_root_tainted(value) for value in node.values)
        return self.is_repo_root_tainted(node)

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
        if self.is_os_path_function_call(node, "join"):
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
        if self.is_os_path_function_call(node, "dirname"):
            return True
        return (
            isinstance(node.func, ast.Name)
            and node.func.id in self.os_path_dirname_aliases
        )

    def is_os_path_passthrough_call(self, node: ast.Call) -> bool:
        """
        Return whether a call preserves path parent-hop semantics.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` for wrappers such as ``abspath`` and ``normpath``.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_os_path_passthrough_call(ast.parse('os.path.normpath(__file__)').body[0].value)
            True
        """
        if self.is_os_path_abspath_call(node):
            return True
        return any(
            self.is_os_path_function_call(node, helper)
            for helper in _OS_PATH_PASSTHROUGH_HELPERS
            if helper != "abspath"
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
        if self.is_os_path_function_call(node, "abspath"):
            return True
        return (
            isinstance(node.func, ast.Name)
            and node.func.id in self.os_path_abspath_aliases
        )

    def is_os_path_split_call(self, node: ast.Call) -> bool:
        """
        Return whether a call targets ``os.path.split``.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when the callee is ``os.path.split`` or an alias.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.is_os_path_split_call(ast.parse('os.path.split(__file__)').body[0].value)
            True
        """
        if self.is_os_path_function_call(node, "split"):
            return True
        return (
            isinstance(node.func, ast.Name)
            and node.func.id in self.os_path_split_aliases
        )

    def is_os_path_function_call(self, node: ast.Call, function_name: str) -> bool:
        """
        Return whether ``node`` calls an ``os.path`` module helper.

        :param node: Call expression node.
        :type node: ast.Call
        :param function_name: Helper name such as ``"join"``.
        :type function_name: str
        :return: ``True`` when the callee is ``os.path.<function_name>`` or an
            ``os.path`` module alias.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.os_path_aliases.add('osp')
            >>> visitor.is_os_path_function_call(ast.parse('osp.join("a", "b")').body[0].value, 'join')
            True
        """
        if dotted_name(node.func) == "os.path.{name}".format(name=function_name):
            return True
        if not isinstance(node.func, ast.Attribute) or node.func.attr != function_name:
            return False
        return self.expression_denotes_os_path_module(node.func.value)

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
            >>> expr = ast.parse('os.path.split(os.path.abspath(__file__))[0]').body[0].value
            >>> visitor.os_path_dirname_depth(expr)
            1
        """
        depth = 0
        current = node
        while isinstance(current, (ast.Call, ast.Subscript)):
            split_arg = self.os_path_split_subscript_zero_arg(current)
            if split_arg is not None:
                depth += 1
                current = split_arg
                continue
            if not isinstance(current, ast.Call):
                break
            if self.is_os_path_passthrough_call(current) and current.args:
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

    def os_path_split_subscript_zero_arg(self, node: ast.AST) -> Optional[ast.AST]:
        """
        Return the argument from ``os.path.split(path)[0]`` expressions.

        :param node: AST expression node.
        :type node: ast.AST
        :return: Split path argument, or ``None`` for other expressions.
        :rtype: ast.AST, optional

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> expr = ast.parse('os.path.split(__file__)[0]').body[0].value
            >>> visitor.os_path_split_subscript_zero_arg(expr) is not None
            True
        """
        if not isinstance(node, ast.Subscript):
            return None
        if subscript_integer(node) != 0:
            return None
        if not isinstance(node.value, ast.Call) or not node.value.args:
            return None
        if not self.is_os_path_split_call(node.value):
            return None
        return node.value.args[0]

    def is_repo_source_template_access(self, node: ast.AST) -> bool:
        """
        Return whether an expression accesses repo-root ``templates``.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` when repo-root taint combines with exact ``templates``.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.repo_root_aliases.add('_REPO_ROOT')
            >>> visitor.is_repo_source_template_access(ast.parse('_REPO_ROOT / "templates"').body[0].value)
            True
            >>> source = 'os.path.join(str(_REPO_ROOT), "templates")'
            >>> visitor.is_repo_source_template_access(ast.parse(source).body[0].value)
            True
            >>> source = 'f"{_REPO_ROOT}/templates"'
            >>> visitor.is_repo_source_template_access(ast.parse(source).body[0].value)
            True
            >>> source = 'Path(*segments)'
            >>> visitor.current_scope.repo_root_aliases.add('segments')
            >>> visitor.current_scope.template_segment_aliases.add('segments')
            >>> visitor.is_repo_source_template_access(ast.parse(source).body[0].value)
            True
        """
        if isinstance(node, ast.JoinedStr):
            return self.is_repo_root_tainted(
                node
            ) and self.expression_has_exact_segment(node, "templates")
        if isinstance(node, ast.FormattedValue):
            return self.is_repo_source_template_access(node.value)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return (
                self.is_repo_root_tainted(node.left)
                and self.expression_has_exact_segment(node.right, "templates")
            ) or (
                self.is_repo_root_tainted(node.right)
                and self.expression_has_exact_segment(node.left, "templates")
            )
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return (
                self.is_repo_root_tainted(node.left)
                and self.expression_has_exact_segment(node.right, "templates")
            ) or (
                self.is_repo_root_tainted(node.right)
                and self.expression_has_exact_segment(node.left, "templates")
            )
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            return self.expression_has_exact_segment(
                node.left, "templates"
            ) and self.mod_format_value_is_repo_root_tainted(node.right)
        if isinstance(node, ast.Call):
            if self.path_separator_join_combines_repo_root_and_templates(node):
                return True
            if self.is_repo_root_tainted_format_call(node):
                return self.format_call_has_exact_segment(node, "templates")
            if self.is_path_constructor_call(node) and node.args:
                if self.expressions_combine_repo_root_and_template_segment(node.args):
                    return True
                if self.is_repo_root_tainted(node.args[0]):
                    return any(
                        self.expression_has_exact_segment(arg, "templates")
                        for arg in node.args[1:]
                    )
            if isinstance(node.func, ast.Attribute) and node.func.attr == "joinpath":
                joinpath_parts = [node.func.value] + list(node.args)
                if self.path_argument_sequence_reaches_repo_templates(joinpath_parts):
                    return True
                if self.expressions_combine_repo_root_and_template_segment(
                    joinpath_parts
                ):
                    return True
                if self.is_repo_root_tainted(node.func.value):
                    return any(
                        self.expression_has_exact_segment(arg, "templates")
                        for arg in node.args
                    )
            if self.is_os_path_join_call(node) and node.args:
                if self.os_path_join_reaches_repo_root(node) and any(
                    self.expression_has_exact_segment(arg, "templates")
                    for arg in node.args
                ):
                    return True
                if self.expressions_combine_repo_root_and_template_segment(node.args):
                    return True
                if self.is_repo_root_tainted(node.args[0]):
                    return any(
                        self.expression_has_exact_segment(arg, "templates")
                        for arg in node.args[1:]
                    )
                if any(self.is_repo_root_tainted(arg) for arg in node.args):
                    return any(
                        self.expression_has_exact_segment(arg, "templates")
                        for arg in node.args
                    )
        return False

    def path_separator_join_combines_repo_root_and_templates(
        self, node: ast.Call
    ) -> bool:
        """
        Return whether a string separator join builds repo-root ``templates``.

        :param node: Call expression node.
        :type node: ast.Call
        :return: ``True`` when ``os.sep.join`` or literal-separator ``join``
            combines repository-root taint with the ``templates`` segment.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('test/x.py'), '', set())
            >>> source = 'import os' + chr(10) + 'repo = Path(__file__).resolve().parents[1]' + chr(10) + 'os.sep.join([str(repo), "templates"])'
            >>> tree = ast.parse(source)
            >>> visitor.visit(tree)
            >>> visitor.findings[-1].rule
            'repo-source-templates'
        """
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "join":
            return False
        if len(node.args) != 1:
            return False
        if not self.expression_denotes_path_separator(node.func.value):
            return False
        elements = self.static_iterable_elements(node.args[0])
        return bool(
            elements
        ) and self.expressions_combine_repo_root_and_template_segment(elements)

    def expression_denotes_path_separator(self, node: ast.AST) -> bool:
        """
        Return whether ``node`` denotes a filesystem path separator string.

        :param node: AST expression node.
        :type node: ast.AST
        :return: ``True`` for ``os.sep`` or literal slash separators.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.expression_denotes_path_separator(ast.parse('os.sep').body[0].value)
            True
            >>> visitor.expression_denotes_path_separator(ast.parse('":"').body[0].value)
            False
        """
        value = self.static_string(node)
        if value in {"/", "\\"}:
            return True
        return dotted_name(node) in {"os.sep", "os.path.sep"}

    def path_argument_sequence_reaches_repo_templates(
        self, arguments: Sequence[ast.AST]
    ) -> bool:
        """
        Return whether path arguments climb to repo root then ``templates``.

        :param arguments: Path-building expressions in call order.
        :type arguments: Sequence[ast.AST]
        :return: ``True`` when static parent hops reach the repository root and
            the sequence contains an exact ``templates`` segment.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('test/x.py'), '', set())
            >>> expr = ast.parse('Path(__file__).resolve().parents[0].joinpath("..", "templates")').body[0].value
            >>> visitor.path_argument_sequence_reaches_repo_templates([expr.func.value] + list(expr.args))
            True
        """
        hops = self.path_argument_sequence_parent_hops(arguments)
        return (
            hops is not None
            and hops >= self.repo_root_dirname_depth
            and any(
                self.expression_has_exact_segment(argument, "templates")
                for argument in arguments
            )
        )

    def expressions_combine_repo_root_and_template_segment(
        self, expressions: Sequence[ast.AST]
    ) -> bool:
        """
        Return whether expressions jointly contain repo-root and ``templates``.

        :param expressions: Path-building expressions to inspect.
        :type expressions: Sequence[ast.AST]
        :return: ``True`` when the expressions combine repository root taint
            with an exact ``templates`` segment.
        :rtype: bool

        Example::

            >>> visitor = TestBoundaryVisitor(Path('x.py'), '', set())
            >>> visitor.current_scope.repo_root_aliases.add('segments')
            >>> visitor.current_scope.template_segment_aliases.add('segments')
            >>> visitor.expressions_combine_repo_root_and_template_segment([ast.parse('*segments').body[0].value])
            True
        """
        return any(self.is_repo_root_tainted(expr) for expr in expressions) and any(
            self.expression_has_exact_segment(expr, "templates") for expr in expressions
        )

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
            >>> visitor.current_scope.template_segment_aliases.add('segments')
            >>> visitor.expression_has_exact_segment(ast.parse('*segments').body[0].value, 'templates')
            True
            >>> expr = ast.parse('("templates", "python")').body[0].value
            >>> visitor.expression_has_exact_segment(expr, 'templates')
            True
        """
        value = self.static_string(node)
        if value is not None and segment in path_segments(value):
            return True
        if is_exact_segment(node, segment):
            return True
        if isinstance(node, ast.Name):
            if segment == "templates" and node.id in self.template_segment_aliases:
                return True
        if isinstance(node, ast.Starred):
            return self.expression_has_exact_segment(node.value, segment)
        if isinstance(node, ast.FormattedValue):
            return self.expression_has_exact_segment(node.value, segment)
        if isinstance(node, ast.IfExp):
            return self.expression_has_exact_segment(
                node.body, segment
            ) or self.expression_has_exact_segment(node.orelse, segment)
        if isinstance(node, ast.JoinedStr):
            return any(
                self.expression_has_exact_segment(value_node, segment)
                for value_node in node.values
            )
        if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
            return any(
                self.expression_has_exact_segment(element, segment)
                for element in node.elts
            )
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
            return self.expression_has_exact_segment(
                node.left, segment
            ) or self.expression_has_exact_segment(node.right, segment)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return self.expression_has_exact_segment(
                node.left, segment
            ) or self.expression_has_exact_segment(node.right, segment)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod):
            return self.expression_has_exact_segment(node.left, segment) or (
                self.expression_has_exact_segment(node.right, segment)
            )
        if isinstance(node, ast.Call):
            return any(
                self.expression_has_exact_segment(arg, segment) for arg in node.args
            )
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
        >>> source = 'import subprocess' + chr(10) + 'cmd = "python "' + chr(10) + 'cmd += "tools/check.py"' + chr(10) + 'subprocess.run(cmd, shell=True)'
        >>> [finding.rule for finding in scan_source(Path('x.py'), Path('x.py'), source)]
        ['tools-exec']
        >>> source = 'repo_root = Path(__file__).resolve().parents[1]' + chr(10) + 'segments = ("templates", "python")' + chr(10) + 'repo_root.joinpath(*segments)'
        >>> [finding.rule for finding in scan_source(Path('x.py'), Path('x.py'), source)]
        ['repo-source-templates']
        >>> source = 'from pathlib import Path' + chr(10) + 'repo_root = Path(__file__).resolve().parents[1]' + chr(10) + 'segments = (repo_root, "templates", "python")' + chr(10) + 'Path(*segments)'
        >>> [finding.rule for finding in scan_source(Path('x.py'), Path('test/x.py'), source)]
        ['repo-source-templates']
        >>> source = 'import os' + chr(10) + 'os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))'
        >>> [finding.rule for finding in scan_source(Path('x.py'), Path('test/x.py'), source)]
        ['repo-source-templates']
        >>> source = 'from pathlib import Path' + chr(10) + 'base = Path(__file__).resolve().parents[0]' + chr(10) + 'base.joinpath("..", "templates")'
        >>> [finding.rule for finding in scan_source(Path('x.py'), Path('test/x.py'), source)]
        ['repo-source-templates']
        >>> source = 'import os' + chr(10) + 'base = os.path.dirname(__file__)' + chr(10) + 'os.path.join(base, "..", "templates")'
        >>> [finding.rule for finding in scan_source(Path('x.py'), Path('test/x.py'), source)]
        ['repo-source-templates']
        >>> source = 'import pathlib' + chr(10) + 'from pathlib import Path' + chr(10) + 'repo = Path(__file__).resolve().parents[1]' + chr(10) + 'pathlib.PurePath(repo, "templates")'
        >>> [finding.rule for finding in scan_source(Path('x.py'), Path('test/x.py'), source)]
        ['repo-source-templates']
        >>> source = 'from pathlib import Path' + chr(10) + 'parents = Path(__file__).resolve().parents' + chr(10) + 'parents[1] / "templates"'
        >>> [finding.rule for finding in scan_source(Path('x.py'), Path('test/x.py'), source)]
        ['repo-source-templates']
        >>> source = 'from os.path import dirname, join, normpath' + chr(10) + 'join(normpath(join(dirname(__file__), "..")), "templates")'
        >>> [finding.rule for finding in scan_source(Path('x.py'), Path('test/x.py'), source)]
        ['repo-source-templates']
        >>> source = 'from os.path import *' + chr(10) + 'join(dirname(__file__), "..", "templates")'
        >>> [finding.rule for finding in scan_source(Path('x.py'), Path('test/x.py'), source)]
        ['repo-source-templates']
        >>> source = 'repo_root = tmp_path' + chr(10) + 'repo_root / "templates"'
        >>> scan_source(Path('x.py'), Path('test/x.py'), source)
        []
    """
    tree = ast.parse(source, filename=str(path))
    visitor = TestBoundaryVisitor(
        relative_path,
        source,
        collect_defined_names(tree),
        collect_docstring_node_ids(tree),
        collect_shadowing_names(getattr(tree, "body", [])),
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
