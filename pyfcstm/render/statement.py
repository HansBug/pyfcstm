"""
Statement rendering utilities for operation blocks.

This module renders operation-block statements from either DSL AST nodes or
model-layer nodes into target-language text. It is the statement-level
counterpart to :mod:`pyfcstm.render.expr`: expression rendering handles single
expressions, while this module handles executable assignment and ``if`` block
structures.

Built-in styles are provided for the main target-language set used by the
project:

* ``dsl`` - Render statements back into DSL text
* ``c`` / ``cpp`` - Render statements with brace blocks and explicit temporary
  declarations
* ``python`` - Render statements into Python code suitable for generated
  runtime methods
* ``java`` / ``js`` / ``ts`` / ``rust`` / ``go`` - Render statements into
  directly usable code for those language families

For Python rendering, callers may pass ``state_vars`` so the renderer can
distinguish persistent state variables from block-local temporary variables.
State variables are emitted as ``scope['name']`` accesses, while temporaries
are emitted as local Python names. Temporary variable visibility follows the
same branch-local semantics as :class:`pyfcstm.simulate.runtime.SimulationRuntime`:
names created inside one ``if`` branch do not leak to the outer scope.

For future static-language backends, the renderer also exposes a minimal
temporary-declaration extension interface:

* ``declare_temp`` - Optional template used when a temporary variable first appears
* ``temp_type_aliases`` - Optional mapping from inferred DSL types to target-language types
* ``temp_type_fallback`` - Optional fallback type when inference cannot decide

The built-in defaults follow a convention-over-configuration approach: when a
caller selects one of the built-in language names without extra overrides, the
renderer should emit broadly usable code for that language in most ordinary
toolchains. Custom configuration remains available on top of these defaults.

The module exposes the following public functions:

* :func:`create_stmt_render_template` - Build a statement-style configuration
* :func:`fn_stmt_render` - Render one operation statement with a prepared style
* :func:`fn_stmts_render` - Render a statement sequence with a prepared style
* :func:`render_stmt_node` - High-level convenience wrapper for one statement
* :func:`render_stmt_nodes` - High-level convenience wrapper for a statement sequence
"""

from __future__ import annotations

from functools import partial
from typing import Any, Dict, Iterable, Mapping, Optional, Set, Tuple, Union

import jinja2

from .expr import create_expr_render_template, fn_expr_render
from ..dsl import node as dsl_nodes
from ..model import OperationStatement
from ..utils import add_settings_for_env

_DSL_STYLE = {
    'base_lang': 'dsl',
    'expr_lang': 'dsl',
    'expr_templates': {},
    'state_var_target': '{{ name }}',
    'temp_var_target': '{{ name }}',
    'assign': '{{ target }} = {{ expr }};',
    'declare_temp': None,
    'temp_type_aliases': {},
    'temp_type_fallback': None,
    'if': 'if [{{ condition }}] {',
    'elif': '} else if [{{ condition }}] {',
    'else': '} else {',
    'block_end': '}',
    'pass': '',
}

_PYTHON_STYLE = {
    'base_lang': 'python',
    'expr_lang': 'python',
    'expr_templates': {},
    'state_var_target': 'scope[{{ name | tojson }}]',
    'temp_var_target': '{{ name }}',
    'assign': '{{ target }} = {{ expr }}',
    'declare_temp': None,
    'temp_type_aliases': {},
    'temp_type_fallback': None,
    'if': 'if {{ condition }}:',
    'elif': 'elif {{ condition }}:',
    'else': 'else:',
    'block_end': None,
    'pass': 'pass',
}

_C_STYLE = {
    'base_lang': 'c',
    'expr_lang': 'c',
    'expr_templates': {},
    'state_var_target': 'scope->{{ name }}',
    'temp_var_target': '{{ name }}',
    'assign': '{{ target }} = {{ expr }};',
    'declare_temp': '{{ temp_type }} {{ name }};',
    'temp_type_aliases': {'int': 'int', 'float': 'double'},
    'temp_type_fallback': 'double',
    'if': 'if ({{ condition }}) {',
    'elif': '} else if ({{ condition }}) {',
    'else': '} else {',
    'block_end': '}',
    'pass': '/* no-op */',
}

_CPP_STYLE = {
    'base_lang': 'cpp',
    'expr_lang': 'cpp',
    'expr_templates': {},
    'state_var_target': 'scope->{{ name }}',
    'temp_var_target': '{{ name }}',
    'assign': '{{ target }} = {{ expr }};',
    'declare_temp': '{{ temp_type }} {{ name }};',
    'temp_type_aliases': {'int': 'int', 'float': 'double'},
    'temp_type_fallback': 'double',
    'if': 'if ({{ condition }}) {',
    'elif': '} else if ({{ condition }}) {',
    'else': '} else {',
    'block_end': '}',
    'pass': '/* no-op */',
}

_JAVA_STYLE = {
    'base_lang': 'java',
    'expr_lang': 'java',
    'expr_templates': {},
    'state_var_target': 'scope.{{ name }}',
    'temp_var_target': '{{ name }}',
    'assign': '{{ target }} = {{ expr }};',
    'declare_temp': '{{ temp_type }} {{ name }};',
    'temp_type_aliases': {'int': 'int', 'float': 'double'},
    'temp_type_fallback': 'double',
    'if': 'if ({{ condition }}) {',
    'elif': '} else if ({{ condition }}) {',
    'else': '} else {',
    'block_end': '}',
    'pass': '// no-op',
}

_JS_STYLE = {
    'base_lang': 'js',
    'expr_lang': 'js',
    'expr_templates': {},
    'state_var_target': 'scope.{{ name }}',
    'temp_var_target': '{{ name }}',
    'assign': '{{ target }} = {{ expr }};',
    'declare_temp': 'let {{ name }};',
    'temp_type_aliases': {},
    'temp_type_fallback': None,
    'if': 'if ({{ condition }}) {',
    'elif': '} else if ({{ condition }}) {',
    'else': '} else {',
    'block_end': '}',
    'pass': '// no-op',
}

_TS_STYLE = {
    'base_lang': 'ts',
    'expr_lang': 'ts',
    'expr_templates': {},
    'state_var_target': 'scope.{{ name }}',
    'temp_var_target': '{{ name }}',
    'assign': '{{ target }} = {{ expr }};',
    'declare_temp': 'let {{ name }}: {{ temp_type }};',
    'temp_type_aliases': {'int': 'number', 'float': 'number'},
    'temp_type_fallback': 'number',
    'if': 'if ({{ condition }}) {',
    'elif': '} else if ({{ condition }}) {',
    'else': '} else {',
    'block_end': '}',
    'pass': '// no-op',
}

_RUST_STYLE = {
    'base_lang': 'rust',
    'expr_lang': 'rust',
    'expr_templates': {},
    'state_var_target': 'scope.{{ name }}',
    'temp_var_target': '{{ name }}',
    'assign': '{{ target }} = {{ expr }};',
    'declare_temp': 'let mut {{ name }}: {{ temp_type }};',
    'temp_type_aliases': {'int': 'i64', 'float': 'f64'},
    'temp_type_fallback': 'f64',
    'if': 'if {{ condition }} {',
    'elif': '} else if {{ condition }} {',
    'else': '} else {',
    'block_end': '}',
    'pass': '// no-op',
}

_GO_STYLE = {
    'base_lang': 'go',
    'expr_lang': 'go',
    'expr_templates': {},
    'state_var_target': 'scope.{{ name }}',
    'temp_var_target': '{{ name }}',
    'assign': '{{ target }} = {{ expr }}',
    'declare_temp': 'var {{ name }} {{ temp_type }}',
    'temp_type_aliases': {'int': 'int', 'float': 'float64'},
    'temp_type_fallback': 'float64',
    'if': 'if {{ condition }} {',
    'elif': '} else if {{ condition }} {',
    'else': '} else {',
    'block_end': '}',
    'pass': '// no-op',
}

_KNOWN_STMT_STYLES = {
    'dsl': _DSL_STYLE,
    'c': _C_STYLE,
    'cpp': _CPP_STYLE,
    'java': _JAVA_STYLE,
    'js': _JS_STYLE,
    'ts': _TS_STYLE,
    'rust': _RUST_STYLE,
    'go': _GO_STYLE,
    'python': _PYTHON_STYLE,
}

_STMT_STYLE_ALIASES = {
    'py': 'python',
    'python3': 'python',
    'c++': 'cpp',
    'cxx': 'cpp',
    'cc': 'cpp',
    'javascript': 'js',
    'node': 'js',
    'nodejs': 'js',
    'typescript': 'ts',
    'rustlang': 'rust',
    'rs': 'rust',
    'golang': 'go',
}


def _normalize_stmt_style(lang_style: str) -> str:
    """
    Normalize a statement-style name to its canonical built-in key.

    :param lang_style: Requested style name.
    :type lang_style: str
    :return: Canonical style name.
    :rtype: str
    """
    return _STMT_STYLE_ALIASES.get(lang_style, lang_style)


def _create_base_env(env: Optional[jinja2.Environment] = None) -> jinja2.Environment:
    """
    Create a minimally configured Jinja2 environment for statement rendering.

    :param env: Optional pre-existing environment.
    :type env: Optional[jinja2.Environment]
    :return: Configured environment.
    :rtype: jinja2.Environment
    """
    if env is not None:
        return env
    return add_settings_for_env(jinja2.Environment())


def _coerce_statement_node(node: Union[OperationStatement, dsl_nodes.OperationalStatement]) -> dsl_nodes.OperationalStatement:
    """
    Convert one model-layer or AST-layer statement into an AST-layer node.

    :param node: Operation statement node.
    :type node: Union[OperationStatement, dsl_nodes.OperationalStatement]
    :return: AST-layer operation statement.
    :rtype: dsl_nodes.OperationalStatement
    :raises TypeError: If the node type is unsupported.
    """
    if isinstance(node, dsl_nodes.OperationalStatement):
        return node
    if isinstance(node, OperationStatement):
        return node.to_ast_node()
    raise TypeError(f'Unsupported operation statement type: {type(node)!r}')


def _normalize_name_set(names: Optional[Iterable[str]]) -> Set[str]:
    """
    Normalize an optional name iterable into a set.

    :param names: Optional name iterable.
    :type names: Optional[Iterable[str]]
    :return: Name set.
    :rtype: Set[str]
    """
    return set(names or [])


def _normalize_var_types(var_types: Optional[Mapping[str, Any]]) -> Dict[str, str]:
    """
    Normalize variable type metadata into a plain ``name -> type`` mapping.

    :param var_types: Optional variable type mapping.
    :type var_types: Optional[Mapping[str, Any]]
    :return: Normalized variable type mapping.
    :rtype: Dict[str, str]
    """
    result = {}
    for name, value in (var_types or {}).items():
        if isinstance(value, str):
            result[name] = value
        elif hasattr(value, 'type'):
            result[name] = str(value.type)
        else:
            result[name] = str(value)
    return result


def _render_template_string(
        template_str: str,
        env: jinja2.Environment,
        **kwargs: Any,
) -> str:
    """
    Render a one-off Jinja2 template string.

    :param template_str: Template source.
    :type template_str: str
    :param env: Jinja2 environment.
    :type env: jinja2.Environment
    :return: Rendered text.
    :rtype: str
    """
    return env.from_string(template_str).render(**kwargs)


def _merge_numeric_types(type_a: Optional[str], type_b: Optional[str]) -> Optional[str]:
    """
    Merge two inferred numeric types conservatively.

    :param type_a: Left type.
    :type type_a: Optional[str]
    :param type_b: Right type.
    :type type_b: Optional[str]
    :return: Merged type.
    :rtype: Optional[str]
    """
    known = {type_a, type_b} - {None}
    if not known:
        return None
    if 'float' in known:
        return 'float'
    if known == {'int'}:
        return 'int'
    return next(iter(known))


def _infer_expr_type(node: dsl_nodes.Expr, known_types: Mapping[str, str]) -> Optional[str]:
    """
    Infer a coarse DSL numeric type for one expression node.

    :param node: Expression node.
    :type node: dsl_nodes.Expr
    :param known_types: Known variable type mapping.
    :type known_types: Mapping[str, str]
    :return: Inferred type name such as ``'int'`` or ``'float'``.
    :rtype: Optional[str]
    """
    if isinstance(node, (dsl_nodes.Integer, dsl_nodes.HexInt, dsl_nodes.Boolean)):
        return 'int'
    if isinstance(node, dsl_nodes.Float):
        return 'float'
    if isinstance(node, dsl_nodes.Constant):
        if str(node.value) in {'pi', 'e'}:
            return 'float'
        return None
    if isinstance(node, dsl_nodes.Name):
        return known_types.get(node.name)
    if isinstance(node, dsl_nodes.Paren):
        return _infer_expr_type(node.expr, known_types)
    if isinstance(node, dsl_nodes.UnaryOp):
        if node.op == '!':
            return 'int'
        return _infer_expr_type(node.expr, known_types)
    if isinstance(node, dsl_nodes.UFunc):
        if node.func in {'floor', 'ceil', 'round', 'int'}:
            return 'int'
        if node.func == 'abs':
            return _infer_expr_type(node.expr, known_types)
        return 'float'
    if isinstance(node, dsl_nodes.BinaryOp):
        if node.op in {'<<', '>>', '&', '^', '|'}:
            return 'int'
        if node.op in {'&&', '||', '==', '!=', '<', '<=', '>', '>='}:
            return 'int'
        left = _infer_expr_type(node.expr1, known_types)
        right = _infer_expr_type(node.expr2, known_types)
        if node.op == '/':
            return 'float'
        return _merge_numeric_types(left, right)
    if isinstance(node, dsl_nodes.ConditionalOp):
        return _merge_numeric_types(
            _infer_expr_type(node.value_true, known_types),
            _infer_expr_type(node.value_false, known_types),
        )
    return None


def _create_scoped_expr_render(
        env: jinja2.Environment,
        lang_style: str,
        expr_templates: Dict[str, str],
        state_vars: Set[str],
        visible_names: Set[str],
        state_var_target_template: str,
        temp_var_target_template: str,
):
    """
    Create a scoped expression renderer for statement rendering.

    :param env: Jinja2 environment.
    :type env: jinja2.Environment
    :param expr_templates: Extra expression templates.
    :type expr_templates: Dict[str, str]
    :param state_vars: Persistent state variable names.
    :type state_vars: Set[str]
    :param visible_names: Currently visible temporary variable names.
    :type visible_names: Set[str]
    :param lang_style: Expression language style.
    :type lang_style: str
    :return: Expression rendering callable and previous environment hooks.
    :rtype: tuple
    """
    templates = create_expr_render_template(
        lang_style,
        {
            **expr_templates,
            'Name': '{{ stmt_resolve_name(node.name) }}',
        },
    )

    def _resolve_name(name: str) -> str:
        if name in state_vars:
            return _render_template_string(state_var_target_template, env, name=name)
        if name in visible_names:
            return _render_template_string(temp_var_target_template, env, name=name)
        return name

    expr_renderer = partial(fn_expr_render, templates=templates, env=env)
    previous_global = env.globals.get('expr_render')
    previous_filter = env.filters.get('expr_render')
    previous_resolver = env.globals.get('stmt_resolve_name')
    env.globals['expr_render'] = expr_renderer
    env.filters['expr_render'] = expr_renderer
    env.globals['stmt_resolve_name'] = _resolve_name
    return expr_renderer, previous_global, previous_filter, previous_resolver


def _restore_scoped_expr_render(
        env: jinja2.Environment,
        previous_global: Any,
        previous_filter: Any,
        previous_resolver: Any,
) -> None:
    """
    Restore temporary expression-rendering hooks used during statement rendering.

    :param env: Jinja2 environment.
    :type env: jinja2.Environment
    :param previous_global: Previously registered ``expr_render`` global.
    :type previous_global: Any
    :param previous_filter: Previously registered ``expr_render`` filter.
    :type previous_filter: Any
    :param previous_resolver: Previously registered name-resolution helper.
    :type previous_resolver: Any
    :return: ``None``.
    :rtype: None
    """
    if previous_global is None:
        env.globals.pop('expr_render', None)
    else:
        env.globals['expr_render'] = previous_global
    if previous_filter is None:
        env.filters.pop('expr_render', None)
    else:
        env.filters['expr_render'] = previous_filter
    if previous_resolver is None:
        env.globals.pop('stmt_resolve_name', None)
    else:
        env.globals['stmt_resolve_name'] = previous_resolver


def _make_known_types(
        state_var_types: Mapping[str, str],
        visible_var_types: Mapping[str, str],
) -> Dict[str, str]:
    """
    Merge state and visible temporary type mappings.

    :param state_var_types: Persistent state variable types.
    :type state_var_types: Mapping[str, str]
    :param visible_var_types: Visible temporary variable types.
    :type visible_var_types: Mapping[str, str]
    :return: Merged type mapping.
    :rtype: Dict[str, str]
    """
    return {**state_var_types, **visible_var_types}


def _render_temp_declaration(
        templates: Dict[str, Any],
        env: jinja2.Environment,
        name: str,
        inferred_type: Optional[str],
) -> Optional[str]:
    """
    Render one optional temporary declaration line.

    :param templates: Prepared statement-style configuration.
    :type templates: Dict[str, Any]
    :param env: Jinja2 environment.
    :type env: jinja2.Environment
    :param name: Temporary variable name.
    :type name: str
    :param inferred_type: Inferred DSL type.
    :type inferred_type: Optional[str]
    :return: Rendered declaration line, or ``None`` when declaration is disabled.
    :rtype: Optional[str]
    """
    declare_temp = templates.get('declare_temp')
    if not declare_temp:
        return None
    temp_type = (templates.get('temp_type_aliases') or {}).get(inferred_type, inferred_type)
    if temp_type is None:
        temp_type = templates.get('temp_type_fallback')
    if temp_type is None:
        return None
    return _render_template_string(declare_temp, env, name=name, temp_type=temp_type)


def create_stmt_render_template(lang_style: str = 'dsl',
                                ext_configs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a statement-style configuration dictionary.

    :param lang_style: Base language style, one of ``'dsl'``, ``'c'``, ``'cpp'``,
        ``'python'``, ``'java'``, ``'js'``, ``'ts'``, ``'rust'``, or ``'go'``.
    :type lang_style: str
    :param ext_configs: Optional overrides for the built-in style configuration.
    :type ext_configs: Optional[Dict[str, Any]]
    :return: Statement-style configuration dictionary.
    :rtype: Dict[str, Any]
    :raises KeyError: If ``lang_style`` is not recognized.

    Example::

        >>> style = create_stmt_render_template('python')
        >>> style['base_lang']
        'python'
    """
    lang_style = _normalize_stmt_style(lang_style)
    return {**_KNOWN_STMT_STYLES[lang_style], **(ext_configs or {})}


def _render_statement_impl(
        node: Union[OperationStatement, dsl_nodes.OperationalStatement],
        templates: Dict[str, Any],
        env: jinja2.Environment,
        state_vars: Set[str],
        state_var_types: Dict[str, str],
        visible_names: Set[str],
        visible_var_types: Dict[str, str],
        indent: str,
        level: int,
) -> Tuple[str, Set[str], Dict[str, str]]:
    """
    Render one statement and return the updated visible temporary names.

    :param node: Statement node.
    :type node: Union[OperationStatement, dsl_nodes.OperationalStatement]
    :param templates: Prepared statement-style configuration.
    :type templates: Dict[str, Any]
    :param env: Jinja2 environment.
    :type env: jinja2.Environment
    :param state_vars: Persistent state variable names.
    :type state_vars: Set[str]
    :param state_var_types: Persistent state variable types.
    :type state_var_types: Dict[str, str]
    :param visible_names: Visible temporary variable names before this statement.
    :type visible_names: Set[str]
    :param visible_var_types: Visible temporary variable types before this statement.
    :type visible_var_types: Dict[str, str]
    :param indent: Indentation unit string.
    :type indent: str
    :param level: Current indentation level.
    :type level: int
    :return: Tuple of rendered text, updated visible temporary names, and updated visible temporary types.
    :rtype: Tuple[str, Set[str], Dict[str, str]]
    :raises TypeError: If the statement type is unsupported.
    """
    style = templates['base_lang']
    expr_lang = templates.get('expr_lang') or style
    expr_templates = dict(templates.get('expr_templates') or {})
    node = _coerce_statement_node(node)

    if style in {'dsl', 'c', 'cpp', 'java', 'js', 'ts', 'rust', 'go'}:
        if isinstance(node, dsl_nodes.OperationAssignment):
            expr_renderer, previous_global, previous_filter, previous_resolver = _create_scoped_expr_render(
                env=env,
                lang_style=expr_lang,
                expr_templates=expr_templates,
                state_vars=state_vars,
                visible_names=visible_names,
                state_var_target_template=templates['state_var_target'],
                temp_var_target_template=templates['temp_var_target'],
            )
            try:
                expr = expr_renderer(node=node.expr)
            finally:
                _restore_scoped_expr_render(env, previous_global, previous_filter, previous_resolver)
            target = _render_template_string(
                templates['state_var_target'] if node.name in state_vars else templates['temp_var_target'],
                env,
                name=node.name,
            )
            text = _render_template_string(templates['assign'], env, target=target, expr=expr)
            new_visible = set(visible_names)
            new_visible_types = dict(visible_var_types)
            lines = []
            if node.name not in state_vars:
                new_visible.add(node.name)
                inferred_type = _infer_expr_type(
                    node.expr,
                    _make_known_types(state_var_types, visible_var_types),
                )
                if node.name not in visible_names:
                    declaration = _render_temp_declaration(
                        templates=templates,
                        env=env,
                        name=node.name,
                        inferred_type=inferred_type,
                    )
                    if declaration:
                        lines.append('{indent}{text}'.format(indent=indent * level, text=declaration))
                if inferred_type is not None:
                    new_visible_types[node.name] = inferred_type
            lines.append('{indent}{text}'.format(indent=indent * level, text=text))
            return '\n'.join(lines), new_visible, new_visible_types

        if isinstance(node, dsl_nodes.OperationIf):
            lines = []
            for index, branch in enumerate(node.branches):
                if index == 0:
                    expr_renderer, previous_global, previous_filter, previous_resolver = _create_scoped_expr_render(
                        env=env,
                        lang_style=expr_lang,
                        expr_templates=expr_templates,
                        state_vars=state_vars,
                        visible_names=visible_names,
                        state_var_target_template=templates['state_var_target'],
                        temp_var_target_template=templates['temp_var_target'],
                    )
                    try:
                        condition = expr_renderer(node=branch.condition)
                    finally:
                        _restore_scoped_expr_render(env, previous_global, previous_filter, previous_resolver)
                    header = _render_template_string(templates['if'], env, condition=condition)
                elif branch.condition is None:
                    header = _render_template_string(templates['else'], env)
                else:
                    expr_renderer, previous_global, previous_filter, previous_resolver = _create_scoped_expr_render(
                        env=env,
                        lang_style=expr_lang,
                        expr_templates=expr_templates,
                        state_vars=state_vars,
                        visible_names=visible_names,
                        state_var_target_template=templates['state_var_target'],
                        temp_var_target_template=templates['temp_var_target'],
                    )
                    try:
                        condition = expr_renderer(node=branch.condition)
                    finally:
                        _restore_scoped_expr_render(env, previous_global, previous_filter, previous_resolver)
                    header = _render_template_string(templates['elif'], env, condition=condition)

                lines.append('{indent}{header}'.format(indent=indent * level, header=header))
                body, _, _ = _render_statements_impl(
                    nodes=branch.statements,
                    templates=templates,
                    env=env,
                    state_vars=state_vars,
                    state_var_types=state_var_types,
                    visible_names=set(visible_names),
                    visible_var_types=dict(visible_var_types),
                    indent=indent,
                    level=level + 1,
                )
                if body:
                    lines.extend(body.splitlines())
            lines.append('{indent}{footer}'.format(indent=indent * level, footer=templates['block_end']))
            return '\n'.join(lines), set(visible_names), dict(visible_var_types)

        raise TypeError(f'Unsupported operation statement type: {type(node)!r}')

    if style == 'python':
        if isinstance(node, dsl_nodes.OperationAssignment):
            expr_renderer, previous_global, previous_filter, previous_resolver = _create_scoped_expr_render(
                env=env,
                lang_style=expr_lang,
                expr_templates=expr_templates,
                state_vars=state_vars,
                visible_names=visible_names,
                state_var_target_template=templates['state_var_target'],
                temp_var_target_template=templates['temp_var_target'],
            )
            try:
                expr = expr_renderer(node=node.expr)
            finally:
                _restore_scoped_expr_render(env, previous_global, previous_filter, previous_resolver)

            target = _render_template_string(
                templates['state_var_target'] if node.name in state_vars else templates['temp_var_target'],
                env,
                name=node.name,
            )
            text = _render_template_string(templates['assign'], env, target=target, expr=expr)
            new_visible = set(visible_names)
            new_visible_types = dict(visible_var_types)
            lines = []
            if node.name not in state_vars:
                inferred_type = _infer_expr_type(
                    node.expr,
                    _make_known_types(state_var_types, visible_var_types),
                )
                if node.name not in visible_names:
                    declaration = _render_temp_declaration(
                        templates=templates,
                        env=env,
                        name=node.name,
                        inferred_type=inferred_type,
                    )
                    if declaration:
                        lines.append('{indent}{text}'.format(indent=indent * level, text=declaration))
                new_visible.add(node.name)
                if inferred_type is not None:
                    new_visible_types[node.name] = inferred_type
            lines.append('{indent}{text}'.format(indent=indent * level, text=text))
            return '\n'.join(lines), new_visible, new_visible_types

        if isinstance(node, dsl_nodes.OperationIf):
            lines = []
            for index, branch in enumerate(node.branches):
                branch_visible = set(visible_names)
                if branch.condition is None:
                    header = _render_template_string(templates['else'], env)
                else:
                    expr_renderer, previous_global, previous_filter, previous_resolver = _create_scoped_expr_render(
                        env=env,
                        lang_style=expr_lang,
                        expr_templates=expr_templates,
                        state_vars=state_vars,
                        visible_names=branch_visible,
                        state_var_target_template=templates['state_var_target'],
                        temp_var_target_template=templates['temp_var_target'],
                    )
                    try:
                        condition = expr_renderer(node=branch.condition)
                    finally:
                        _restore_scoped_expr_render(env, previous_global, previous_filter, previous_resolver)
                    if index == 0:
                        header = _render_template_string(templates['if'], env, condition=condition)
                    else:
                        header = _render_template_string(templates['elif'], env, condition=condition)

                lines.append('{indent}{header}'.format(indent=indent * level, header=header))
                body, _, _ = _render_statements_impl(
                    nodes=branch.statements,
                    templates=templates,
                    env=env,
                    state_vars=state_vars,
                    state_var_types=state_var_types,
                    visible_names=branch_visible,
                    visible_var_types=dict(visible_var_types),
                    indent=indent,
                    level=level + 1,
                )
                if body:
                    lines.extend(body.splitlines())
                else:
                    lines.append('{indent}{text}'.format(
                        indent=indent * (level + 1),
                        text=templates['pass'],
                    ))
            return '\n'.join(lines), set(visible_names), dict(visible_var_types)

        raise TypeError(f'Unsupported operation statement type: {type(node)!r}')

    raise KeyError(f'Unsupported statement rendering style: {style!r}')


def _render_statements_impl(
        nodes: Iterable[Union[OperationStatement, dsl_nodes.OperationalStatement]],
        templates: Dict[str, Any],
        env: jinja2.Environment,
        state_vars: Set[str],
        state_var_types: Dict[str, str],
        visible_names: Set[str],
        visible_var_types: Dict[str, str],
        indent: str,
        level: int,
        sep: str = '\n',
) -> Tuple[str, Set[str], Dict[str, str]]:
    """
    Render a statement sequence and return the updated visible temporaries.

    :param nodes: Statement sequence.
    :type nodes: Iterable[Union[OperationStatement, dsl_nodes.OperationalStatement]]
    :param templates: Prepared statement-style configuration.
    :type templates: Dict[str, Any]
    :param env: Jinja2 environment.
    :type env: jinja2.Environment
    :param state_vars: Persistent state variable names.
    :type state_vars: Set[str]
    :param state_var_types: Persistent state variable types.
    :type state_var_types: Dict[str, str]
    :param visible_names: Visible temporary variable names before this sequence.
    :type visible_names: Set[str]
    :param visible_var_types: Visible temporary variable types before this sequence.
    :type visible_var_types: Dict[str, str]
    :param indent: Indentation unit string.
    :type indent: str
    :param level: Current indentation level.
    :type level: int
    :param sep: Separator for top-level rendered statements.
    :type sep: str
    :return: Tuple of rendered text, updated visible temporary names, and updated visible temporary types.
    :rtype: Tuple[str, Set[str], Dict[str, str]]
    """
    rendered_items = []
    current_visible = set(visible_names)
    current_visible_types = dict(visible_var_types)
    for node in nodes:
        rendered, current_visible, current_visible_types = _render_statement_impl(
            node=node,
            templates=templates,
            env=env,
            state_vars=state_vars,
            state_var_types=state_var_types,
            visible_names=current_visible,
            visible_var_types=current_visible_types,
            indent=indent,
            level=level,
        )
        rendered_items.append(rendered)
    return sep.join(rendered_items), current_visible, current_visible_types


def fn_stmt_render(node: Union[OperationStatement, dsl_nodes.OperationalStatement],
                   templates: Dict[str, Any],
                   env: jinja2.Environment,
                   state_vars: Optional[Iterable[str]] = None,
                   var_types: Optional[Mapping[str, Any]] = None,
                   visible_names: Optional[Iterable[str]] = None,
                   visible_var_types: Optional[Mapping[str, Any]] = None,
                   indent: str = '    ',
                   level: int = 0) -> str:
    """
    Render one operation statement with a prepared statement style.

    :param node: Statement node to render.
    :type node: Union[OperationStatement, dsl_nodes.OperationalStatement]
    :param templates: Prepared statement-style configuration.
    :type templates: Dict[str, Any]
    :param env: Jinja2 environment.
    :type env: jinja2.Environment
    :param state_vars: Persistent state variable names.
    :type state_vars: Optional[Iterable[str]]
    :param var_types: Optional variable type mapping used for static-language extensions.
    :type var_types: Optional[Mapping[str, Any]]
    :param visible_names: Visible temporary names before this statement.
    :type visible_names: Optional[Iterable[str]]
    :param visible_var_types: Visible temporary type mapping before this statement.
    :type visible_var_types: Optional[Mapping[str, Any]]
    :param indent: Indentation unit string, defaults to ``'    '``.
    :type indent: str, optional
    :param level: Initial indentation level, defaults to ``0``.
    :type level: int, optional
    :return: Rendered statement text.
    :rtype: str
    """
    rendered, _, _ = _render_statement_impl(
        node=node,
        templates=templates,
        env=env,
        state_vars=_normalize_name_set(state_vars),
        state_var_types=_normalize_var_types(var_types),
        visible_names=_normalize_name_set(visible_names),
        visible_var_types=_normalize_var_types(visible_var_types),
        indent=indent,
        level=level,
    )
    return rendered


def fn_stmts_render(nodes: Iterable[Union[OperationStatement, dsl_nodes.OperationalStatement]],
                    templates: Dict[str, Any],
                    env: jinja2.Environment,
                    state_vars: Optional[Iterable[str]] = None,
                    var_types: Optional[Mapping[str, Any]] = None,
                    visible_names: Optional[Iterable[str]] = None,
                    visible_var_types: Optional[Mapping[str, Any]] = None,
                    indent: str = '    ',
                    level: int = 0,
                    sep: str = '\n') -> str:
    """
    Render a sequence of operation statements with a prepared statement style.

    :param nodes: Statement sequence to render.
    :type nodes: Iterable[Union[OperationStatement, dsl_nodes.OperationalStatement]]
    :param templates: Prepared statement-style configuration.
    :type templates: Dict[str, Any]
    :param env: Jinja2 environment.
    :type env: jinja2.Environment
    :param state_vars: Persistent state variable names.
    :type state_vars: Optional[Iterable[str]]
    :param var_types: Optional variable type mapping used for static-language extensions.
    :type var_types: Optional[Mapping[str, Any]]
    :param visible_names: Visible temporary names before this sequence.
    :type visible_names: Optional[Iterable[str]]
    :param visible_var_types: Visible temporary type mapping before this sequence.
    :type visible_var_types: Optional[Mapping[str, Any]]
    :param indent: Indentation unit string, defaults to ``'    '``.
    :type indent: str, optional
    :param level: Initial indentation level, defaults to ``0``.
    :type level: int, optional
    :param sep: Separator between top-level rendered statements, defaults to newline.
    :type sep: str, optional
    :return: Rendered statement sequence.
    :rtype: str
    """
    rendered, _, _ = _render_statements_impl(
        nodes=nodes,
        templates=templates,
        env=env,
        state_vars=_normalize_name_set(state_vars),
        state_var_types=_normalize_var_types(var_types),
        visible_names=_normalize_name_set(visible_names),
        visible_var_types=_normalize_var_types(visible_var_types),
        indent=indent,
        level=level,
        sep=sep,
    )
    return rendered


def render_stmt_node(stmt: Union[OperationStatement, dsl_nodes.OperationalStatement],
                     lang_style: str = 'dsl',
                     ext_configs: Optional[Dict[str, Any]] = None,
                     env: Optional[jinja2.Environment] = None,
                     state_vars: Optional[Iterable[str]] = None,
                     var_types: Optional[Mapping[str, Any]] = None,
                     visible_names: Optional[Iterable[str]] = None,
                     visible_var_types: Optional[Mapping[str, Any]] = None,
                     indent: str = '    ',
                     level: int = 0) -> str:
    """
    Render one statement with a built-in or extended language style.

    :param stmt: Statement node.
    :type stmt: Union[OperationStatement, dsl_nodes.OperationalStatement]
    :param lang_style: Base language style, defaults to ``'dsl'``.
    :type lang_style: str, optional
    :param ext_configs: Optional style overrides.
    :type ext_configs: Optional[Dict[str, Any]]
    :param env: Optional Jinja2 environment.
    :type env: Optional[jinja2.Environment]
    :param state_vars: Persistent state variable names.
    :type state_vars: Optional[Iterable[str]]
    :param var_types: Optional variable type mapping used for static-language extensions.
    :type var_types: Optional[Mapping[str, Any]]
    :param visible_names: Visible temporary names before this statement.
    :type visible_names: Optional[Iterable[str]]
    :param visible_var_types: Visible temporary type mapping before this statement.
    :type visible_var_types: Optional[Mapping[str, Any]]
    :param indent: Indentation unit string.
    :type indent: str, optional
    :param level: Initial indentation level.
    :type level: int, optional
    :return: Rendered statement text.
    :rtype: str
    """
    env = _create_base_env(env)
    templates = create_stmt_render_template(lang_style, ext_configs)
    return fn_stmt_render(
        node=stmt,
        templates=templates,
        env=env,
        state_vars=state_vars,
        var_types=var_types,
        visible_names=visible_names,
        visible_var_types=visible_var_types,
        indent=indent,
        level=level,
    )


def render_stmt_nodes(stmts: Iterable[Union[OperationStatement, dsl_nodes.OperationalStatement]],
                      lang_style: str = 'dsl',
                      ext_configs: Optional[Dict[str, Any]] = None,
                      env: Optional[jinja2.Environment] = None,
                      state_vars: Optional[Iterable[str]] = None,
                      var_types: Optional[Mapping[str, Any]] = None,
                      visible_names: Optional[Iterable[str]] = None,
                      visible_var_types: Optional[Mapping[str, Any]] = None,
                      indent: str = '    ',
                      level: int = 0,
                      sep: str = '\n') -> str:
    """
    Render a sequence of statements with a built-in or extended language style.

    :param stmts: Statement sequence.
    :type stmts: Iterable[Union[OperationStatement, dsl_nodes.OperationalStatement]]
    :param lang_style: Base language style, defaults to ``'dsl'``.
    :type lang_style: str, optional
    :param ext_configs: Optional style overrides.
    :type ext_configs: Optional[Dict[str, Any]]
    :param env: Optional Jinja2 environment.
    :type env: Optional[jinja2.Environment]
    :param state_vars: Persistent state variable names.
    :type state_vars: Optional[Iterable[str]]
    :param var_types: Optional variable type mapping used for static-language extensions.
    :type var_types: Optional[Mapping[str, Any]]
    :param visible_names: Visible temporary names before this statement sequence.
    :type visible_names: Optional[Iterable[str]]
    :param visible_var_types: Visible temporary type mapping before this statement sequence.
    :type visible_var_types: Optional[Mapping[str, Any]]
    :param indent: Indentation unit string.
    :type indent: str, optional
    :param level: Initial indentation level.
    :type level: int, optional
    :param sep: Separator between top-level rendered statements.
    :type sep: str, optional
    :return: Rendered statement sequence.
    :rtype: str
    """
    env = _create_base_env(env)
    templates = create_stmt_render_template(lang_style, ext_configs)
    return fn_stmts_render(
        nodes=stmts,
        templates=templates,
        env=env,
        state_vars=state_vars,
        var_types=var_types,
        visible_names=visible_names,
        visible_var_types=visible_var_types,
        indent=indent,
        level=level,
        sep=sep,
    )
