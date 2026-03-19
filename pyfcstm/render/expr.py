"""
Expression rendering utilities for converting DSL AST nodes into language-specific text.

This module provides functionality to render expression nodes from the DSL
abstract syntax tree into string representations for multiple language styles,
including DSL, C, C++, Python, Java, JavaScript, TypeScript, Rust, and Go.
Rendering is performed through Jinja2 templating with a small set of default
templates and an optional extension mechanism to override or extend the
template set.

The module exposes the following public functions:

* :func:`fn_expr_render` - Render a single expression node with a provided template set
* :func:`create_expr_render_template` - Build template mappings for a given language style
* :func:`render_expr_node` - High-level rendering convenience function

.. note::
   Templates must include a ``default`` key if you intend to render custom nodes
   that are not matched by the predefined entries.

Example::

    >>> from pyfcstm.dsl import Integer
    >>> from pyfcstm.render.expr import render_expr_node
    >>> render_expr_node(Integer("42"), lang_style='python')
    '42'
    >>> render_expr_node(Integer("42"), lang_style='c')
    '42'

"""

from functools import partial
from typing import Optional, Dict, Union, Any

import jinja2

from ..dsl import node as dsl_nodes
from ..model import Integer, Float, Boolean
from ..utils import add_settings_for_env

_DSL_STYLE = {
    'Float': '{{ node.value | repr }}',
    'Integer': '{{ node.value | repr }}',
    'Boolean': '{{ node.value | repr }}',
    'Constant': '{{ node.value | repr }}',
    'HexInt': '{{ node.value | hex }}',
    'Paren': '({{ node.expr | expr_render }})',
    'UFunc': '{{ node.func }}({{ node.expr | expr_render }})',
    'Name': '{{ node.name }}',
    'UnaryOp': '{{ node.op }}{{ node.expr | expr_render }}',
    'BinaryOp': '{{ node.expr1 | expr_render }} {{ node.op }} {{ node.expr2 | expr_render }}',
    'ConditionalOp': '({{ node.cond | expr_render }}) ? {{ node.value_true | expr_render }} : {{ node.value_false | expr_render }}',
}

_C_STYLE = {
    **_DSL_STYLE,
    'Boolean': '{{ (1 if node.value else 0) | hex }}',
    'BinaryOp(**)': 'pow({{ node.expr1 | expr_render }}, {{ node.expr2 | expr_render }})',
}

_CPP_STYLE = {
    **_DSL_STYLE,
    'Boolean': '{{ "true" if node.value else "false" }}',
    'UFunc': 'std::{{ node.func }}({{ node.expr | expr_render }})',
    'BinaryOp(**)': 'std::pow({{ node.expr1 | expr_render }}, {{ node.expr2 | expr_render }})',
}

_PY_STYLE = {
    **_DSL_STYLE,
    'UFunc(sin)': 'math.sin({{ node.expr | expr_render }})',
    'UFunc(cos)': 'math.cos({{ node.expr | expr_render }})',
    'UFunc(tan)': 'math.tan({{ node.expr | expr_render }})',
    'UFunc(asin)': 'math.asin({{ node.expr | expr_render }})',
    'UFunc(acos)': 'math.acos({{ node.expr | expr_render }})',
    'UFunc(atan)': 'math.atan({{ node.expr | expr_render }})',
    'UFunc(sinh)': 'math.sinh({{ node.expr | expr_render }})',
    'UFunc(cosh)': 'math.cosh({{ node.expr | expr_render }})',
    'UFunc(tanh)': 'math.tanh({{ node.expr | expr_render }})',
    'UFunc(asinh)': 'math.asinh({{ node.expr | expr_render }})',
    'UFunc(acosh)': 'math.acosh({{ node.expr | expr_render }})',
    'UFunc(atanh)': 'math.atanh({{ node.expr | expr_render }})',
    'UFunc(sqrt)': 'math.sqrt({{ node.expr | expr_render }})',
    'UFunc(cbrt)': 'math.copysign(abs({{ node.expr | expr_render }}) ** (1.0 / 3.0), {{ node.expr | expr_render }})',
    'UFunc(exp)': 'math.exp({{ node.expr | expr_render }})',
    'UFunc(log)': 'math.log({{ node.expr | expr_render }})',
    'UFunc(log10)': 'math.log10({{ node.expr | expr_render }})',
    'UFunc(log2)': 'math.log2({{ node.expr | expr_render }})',
    'UFunc(log1p)': 'math.log1p({{ node.expr | expr_render }})',
    'UFunc(abs)': 'abs({{ node.expr | expr_render }})',
    'UFunc(ceil)': 'math.ceil({{ node.expr | expr_render }})',
    'UFunc(floor)': 'math.floor({{ node.expr | expr_render }})',
    'UFunc(round)': 'round({{ node.expr | expr_render }})',
    'UFunc(trunc)': 'math.trunc({{ node.expr | expr_render }})',
    'UnaryOp(!)': 'not {{ node.expr | expr_render }}',
    'BinaryOp(&&)': '{{ node.expr1 | expr_render }} and {{ node.expr2 | expr_render }}',
    'BinaryOp(||)': '{{ node.expr1 | expr_render }} or {{ node.expr2 | expr_render }}',
    'ConditionalOp': '{{ node.value_true | expr_render }} if {{ node.cond | expr_render }} else {{ node.value_false | expr_render }}',
}

_JAVA_STYLE = {
    **_DSL_STYLE,
    'Boolean': '{{ "true" if node.value else "false" }}',
    'Constant': '{{ "Math.PI" if node.value == "pi" else ("Math.E" if node.value == "e" else ("(2.0 * Math.PI)" if node.value == "tau" else node.value | repr)) }}',
    'UFunc': 'Math.{{ node.func }}({{ node.expr | expr_render }})',
    'UFunc(trunc)': '({{ node.expr | expr_render }}) >= 0 ? Math.floor({{ node.expr | expr_render }}) : Math.ceil({{ node.expr | expr_render }})',
    'BinaryOp(**)': 'Math.pow({{ node.expr1 | expr_render }}, {{ node.expr2 | expr_render }})',
    'ConditionalOp': '{{ node.cond | expr_render }} ? {{ node.value_true | expr_render }} : {{ node.value_false | expr_render }}',
}

_JS_STYLE = {
    **_DSL_STYLE,
    'Boolean': '{{ "true" if node.value else "false" }}',
    'Constant': '{{ "Math.PI" if node.value == "pi" else ("Math.E" if node.value == "e" else ("(2 * Math.PI)" if node.value == "tau" else node.value | repr)) }}',
    'UFunc': 'Math.{{ node.func }}({{ node.expr | expr_render }})',
    'BinaryOp(**)': 'Math.pow({{ node.expr1 | expr_render }}, {{ node.expr2 | expr_render }})',
}

_TS_STYLE = {
    **_JS_STYLE,
}

_RUST_STYLE = {
    **_DSL_STYLE,
    'Boolean': '{{ "true" if node.value else "false" }}',
    'Constant': '{{ "std::f64::consts::PI" if node.value == "pi" else ("std::f64::consts::E" if node.value == "e" else ("std::f64::consts::TAU" if node.value == "tau" else node.value | repr)) }}',
    'UFunc(abs)': '({{ node.expr | expr_render }}).abs()',
    'UFunc(round)': '({{ node.expr | expr_render }} as f64).round() as i64',
    'UFunc(ceil)': '({{ node.expr | expr_render }} as f64).ceil() as i64',
    'UFunc(floor)': '({{ node.expr | expr_render }} as f64).floor() as i64',
    'UFunc(trunc)': '({{ node.expr | expr_render }} as f64).trunc() as i64',
    'UFunc(log)': '({{ node.expr | expr_render }} as f64).ln()',
    'UFunc(log10)': '({{ node.expr | expr_render }} as f64).log10()',
    'UFunc(log2)': '({{ node.expr | expr_render }} as f64).log2()',
    'UFunc(log1p)': '({{ node.expr | expr_render }} as f64).ln_1p()',
    'UFunc': '({{ node.expr | expr_render }} as f64).{{ node.func }}()',
    'BinaryOp(**)': '({{ node.expr1 | expr_render }} as f64).powf({{ node.expr2 | expr_render }} as f64)',
    'ConditionalOp': '(if {{ node.cond | expr_render }} { {{ node.value_true | expr_render }} } else { {{ node.value_false | expr_render }} })',
}

_GO_STYLE = {
    **_DSL_STYLE,
    'Boolean': '{{ "true" if node.value else "false" }}',
    'Constant': '{{ "math.Pi" if node.value == "pi" else ("math.E" if node.value == "e" else ("(2 * math.Pi)" if node.value == "tau" else node.value | repr)) }}',
    'UFunc(abs)': '{{ go_abs_expr(node.expr | expr_render, node.expr) }}',
    'UFunc(round)': 'int(math.Round(float64({{ node.expr | expr_render }})))',
    'UFunc(ceil)': 'int(math.Ceil(float64({{ node.expr | expr_render }})))',
    'UFunc(floor)': 'int(math.Floor(float64({{ node.expr | expr_render }})))',
    'UFunc(trunc)': 'int(math.Trunc(float64({{ node.expr | expr_render }})))',
    'UFunc': 'math.{{ node.func | capitalize }}(float64({{ node.expr | expr_render }}))',
    'BinaryOp(**)': 'math.Pow(float64({{ node.expr1 | expr_render }}), float64({{ node.expr2 | expr_render }}))',
    'ConditionalOp': 'func() {{ go_expr_type(node) }} { if {{ node.cond | expr_render }} { return {{ node.value_true | expr_render }} }; return {{ node.value_false | expr_render }} }()',
}

_KNOWN_STYLES = {
    'dsl': _DSL_STYLE,
    'c': _C_STYLE,
    'cpp': _CPP_STYLE,
    'java': _JAVA_STYLE,
    'js': _JS_STYLE,
    'ts': _TS_STYLE,
    'rust': _RUST_STYLE,
    'go': _GO_STYLE,
    'python': _PY_STYLE,
}


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


def _infer_expr_type(node: dsl_nodes.Expr) -> Optional[str]:
    """
    Infer a coarse DSL numeric type for one expression node.

    :param node: Expression node.
    :type node: dsl_nodes.Expr
    :return: Inferred type name such as ``'int'`` or ``'float'``.
    :rtype: Optional[str]
    """
    if isinstance(node, (dsl_nodes.Integer, dsl_nodes.HexInt, dsl_nodes.Boolean)):
        return 'int'
    if isinstance(node, dsl_nodes.Float):
        return 'float'
    if isinstance(node, dsl_nodes.Constant):
        if str(node.value) in {'pi', 'e', 'tau'}:
            return 'float'
        return None
    if isinstance(node, dsl_nodes.Name):
        return None
    if isinstance(node, dsl_nodes.Paren):
        return _infer_expr_type(node.expr)
    if isinstance(node, dsl_nodes.UnaryOp):
        if node.op == '!':
            return 'int'
        return _infer_expr_type(node.expr)
    if isinstance(node, dsl_nodes.UFunc):
        if node.func in {'floor', 'ceil', 'round', 'int', 'trunc'}:
            return 'int'
        if node.func == 'abs':
            return _infer_expr_type(node.expr)
        return 'float'
    if isinstance(node, dsl_nodes.BinaryOp):
        if node.op in {'<<', '>>', '&', '^', '|'}:
            return 'int'
        if node.op in {'&&', '||', '==', '!=', '<', '<=', '>', '>='}:
            return 'int'
        left = _infer_expr_type(node.expr1)
        right = _infer_expr_type(node.expr2)
        if node.op == '/':
            return 'float'
        return _merge_numeric_types(left, right)
    if isinstance(node, dsl_nodes.ConditionalOp):
        return _merge_numeric_types(
            _infer_expr_type(node.value_true),
            _infer_expr_type(node.value_false),
        )
    return None


def _create_base_env(env: Optional[jinja2.Environment] = None) -> jinja2.Environment:
    """
    Create a minimally configured Jinja2 environment for expression rendering.

    :param env: Optional pre-existing environment.
    :type env: Optional[jinja2.Environment]
    :return: Configured environment.
    :rtype: jinja2.Environment
    """
    if env is not None:
        env.globals.setdefault('expr_infer_type', _infer_expr_type)
        env.globals.setdefault('go_expr_type', lambda node: 'float64' if _infer_expr_type(node) == 'float' else 'int')
        env.globals.setdefault(
            'go_abs_expr',
            lambda expr_text, node: (
                f'int(math.Abs(float64({expr_text})))'
                if _infer_expr_type(node) == 'int' else f'math.Abs(float64({expr_text}))'
            ),
        )
        return env
    env = add_settings_for_env(jinja2.Environment())
    env.globals['expr_infer_type'] = _infer_expr_type
    env.globals['go_expr_type'] = lambda node: 'float64' if _infer_expr_type(node) == 'float' else 'int'
    env.globals['go_abs_expr'] = lambda expr_text, node: (
        f'int(math.Abs(float64({expr_text})))'
        if _infer_expr_type(node) == 'int' else f'math.Abs(float64({expr_text}))'
    )
    return env


def fn_expr_render(node: Union[float, int, dict, dsl_nodes.Expr, Any],
                   templates: Dict[str, str],
                   env: jinja2.Environment) -> str:
    """
    Render an expression node using the provided templates and Jinja2 environment.

    This function detects the node type and selects the most specific template
    available. For operator nodes, it tries operator-specific templates such as
    ``UnaryOp(!)`` or ``BinaryOp(**)`` before falling back to the generic template.
    If the node is not a DSL expression, primitive Python types are converted
    into their corresponding DSL literal nodes. Any other object is rendered via
    :func:`repr`.

    :param node: The expression node to render, which may be a DSL expression,
        a primitive value, or any Python object
    :type node: Union[float, int, dict, dsl_nodes.Expr, Any]
    :param templates: Dictionary mapping node types to Jinja2 template strings
    :type templates: Dict[str, str]
    :param env: Jinja2 environment for template rendering
    :type env: jinja2.Environment
    :return: The rendered string representation of the expression node
    :rtype: str
    :raises KeyError: If no matching template is found and ``default`` is absent

    Example::

        >>> env = create_env()
        >>> templates = _DSL_STYLE
        >>> fn_expr_render(Integer(42).to_ast_node(), templates, env)
        '42'
        >>> fn_expr_render(True, templates, env)
        'True'

    """
    if isinstance(node, dsl_nodes.Expr):
        if isinstance(node, (dsl_nodes.Float, dsl_nodes.Integer, dsl_nodes.Boolean, dsl_nodes.Constant,
                             dsl_nodes.HexInt, dsl_nodes.Paren, dsl_nodes.Name, dsl_nodes.ConditionalOp)) \
                and type(node).__name__ in templates:
            template_str = templates[type(node).__name__]
        elif isinstance(node, dsl_nodes.UFunc) and f'{type(node).__name__}({node.func})' in templates:
            template_str = templates[f'{type(node).__name__}({node.func})']
        elif isinstance(node, dsl_nodes.UFunc) and type(node).__name__ in templates:
            template_str = templates[type(node).__name__]
        elif isinstance(node, dsl_nodes.UnaryOp) and f'{type(node).__name__}({node.op})' in templates:
            template_str = templates[f'{type(node).__name__}({node.op})']
        elif isinstance(node, dsl_nodes.UnaryOp) and type(node).__name__ in templates:
            template_str = templates[type(node).__name__]
        elif isinstance(node, dsl_nodes.BinaryOp) and f'{type(node).__name__}({node.op})' in templates:
            template_str = templates[f'{type(node).__name__}({node.op})']
        elif isinstance(node, dsl_nodes.BinaryOp) and type(node).__name__ in templates:
            template_str = templates[type(node).__name__]
        else:
            template_str = templates['default']

        tp: jinja2.Template = env.from_string(template_str)
        return tp.render(node=node)

    elif isinstance(node, bool):
        return fn_expr_render(Boolean(node).to_ast_node(), templates=templates, env=env)
    elif isinstance(node, int):
        return fn_expr_render(Integer(node).to_ast_node(), templates=templates, env=env)
    elif isinstance(node, float):
        return fn_expr_render(Float(node).to_ast_node(), templates=templates, env=env)
    else:
        return repr(node)


def create_expr_render_template(lang_style: str = 'dsl',
                                ext_configs: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    Create a template dictionary for expression rendering based on the specified language style.

    This function merges predefined templates for the requested language style with
    optional custom template entries. Custom entries override defaults with the same key.

    :param lang_style: The language style to use (``'dsl'``, ``'c'``, ``'cpp'``, ``'python'``, ``'java'``, ``'js'``, ``'ts'``, ``'rust'``, ``'go'``)
    :type lang_style: str
    :param ext_configs: Optional additional template configurations to extend or override defaults
    :type ext_configs: Optional[Dict[str, str]]
    :return: A dictionary of templates for the specified language style
    :rtype: Dict[str, str]
    :raises KeyError: If ``lang_style`` is not recognized

    Example::

        >>> templates = create_expr_render_template('python', {'CustomNode': '{{ node.custom_value }}'})
        >>> 'UFunc' in templates and 'CustomNode' in templates
        True

    """
    ext_configs = dict(ext_configs or {})
    templates = dict(_KNOWN_STYLES[lang_style])

    for generic_key in ('UFunc', 'UnaryOp', 'BinaryOp'):
        if generic_key in ext_configs:
            prefix = generic_key + '('
            templates = {
                key: value
                for key, value in templates.items()
                if key != generic_key and not key.startswith(prefix)
            }

    return {**templates, **ext_configs}


def render_expr_node(expr: Union[float, int, dict, dsl_nodes.Expr, Any],
                     lang_style: str = 'dsl',
                     ext_configs: Optional[Dict[str, str]] = None,
                     env: Optional[jinja2.Environment] = None) -> str:
    """
    Render an expression node to a string representation in the specified language style.

    This is a high-level convenience wrapper that prepares a Jinja2 environment,
    registers the ``expr_render`` filter and global function, and renders the
    provided expression node.

    :param expr: The expression to render
    :type expr: Union[float, int, dict, dsl_nodes.Expr, Any]
    :param lang_style: The language style to use (``'dsl'``, ``'c'``, ``'cpp'``, ``'python'``, ``'java'``, ``'js'``, ``'ts'``, ``'rust'``, ``'go'``)
    :type lang_style: str
    :param ext_configs: Optional additional template configurations
    :type ext_configs: Optional[Dict[str, str]]
    :param env: Optional pre-configured Jinja2 environment
    :type env: Optional[jinja2.Environment]
    :return: The rendered string representation of the expression
    :rtype: str
    :raises KeyError: If ``lang_style`` is not recognized

    Example::

        >>> from pyfcstm.dsl import Integer
        >>> render_expr_node(Integer('42'), lang_style='python')
        '42'
        >>> render_expr_node(Integer('42'), lang_style='c')
        '42'

    """
    env = _create_base_env(env)
    templates = create_expr_render_template(lang_style, ext_configs)
    _fn_expr_render = partial(fn_expr_render, templates=templates, env=env)
    env.globals['expr_render'] = _fn_expr_render
    env.filters['expr_render'] = _fn_expr_render
    return _fn_expr_render(node=expr)
