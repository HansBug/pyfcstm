"""
Expression rendering module for converting DSL nodes to different language formats.

This module provides functionality to render expression nodes in various language styles
including DSL, C/C++, and Python. It uses Jinja2 templating to transform abstract syntax
tree nodes into string representations according to the specified language style.

The module contains predefined templates for different node types and operators,
and allows for custom template extensions.
"""

from functools import partial
from typing import Optional, Dict, Union, Any

import jinja2

from .env import create_env
from ..dsl import node as dsl_nodes
from ..model import Integer, Float, Boolean

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

_PY_STYLE = {
    **_DSL_STYLE,
    'UFunc': 'math.{{ node.func }}({{ node.expr | expr_render }})',
    'UnaryOp(!)': 'not {{ node.expr | expr_render }}',
    'BinaryOp(&&)': '{{ node.expr1 | expr_render }} and {{ node.expr2 | expr_render }}',
    'BinaryOp(||)': '{{ node.expr1 | expr_render }} or {{ node.expr2 | expr_render }}',
    'ConditionalOp': '{{ node.value_true | expr_render }} if {{ node.cond | expr_render }} else {{ node.value_false | expr_render }}',
}

_KNOWN_STYLES = {
    'dsl': _DSL_STYLE,
    'c': _C_STYLE,
    'cpp': _C_STYLE,
    'python': _PY_STYLE,
}


def fn_expr_render(node: Union[float, int, dict, dsl_nodes.Expr, Any], templates: Dict[str, str],
                   env: jinja2.Environment):
    """
    Render an expression node using the provided templates and Jinja2 environment.

    This function handles different types of expression nodes and selects the appropriate
    template for rendering based on the node type and available templates.

    :param node: The expression node to render, can be a DSL node or a primitive value
    :type node: Union[float, int, dict, dsl_nodes.Expr, Any]

    :param templates: Dictionary mapping node types to Jinja2 template strings
    :type templates: Dict[str, str]

    :param env: Jinja2 environment for template rendering
    :type env: jinja2.Environment

    :return: The rendered string representation of the expression node
    :rtype: str

    Example::

        >>> env = create_env()
        >>> templates = _DSL_STYLE
        >>> fn_expr_render(Integer(42).to_ast_node(), templates, env)
        '42'
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


def create_expr_render_template(lang_style: str = 'dsl', ext_configs: Optional[Dict[str, str]] = None):
    """
    Create a template dictionary for expression rendering based on the specified language style.

    This function combines the predefined templates for the specified language style with
    any additional custom templates provided in ext_configs.

    :param lang_style: The language style to use ('dsl', 'c', 'cpp', 'python')
    :type lang_style: str

    :param ext_configs: Optional additional template configurations to extend or override defaults
    :type ext_configs: Optional[Dict[str, str]]

    :return: A dictionary of templates for the specified language style
    :rtype: Dict[str, str]

    Example::

        >>> templates = create_expr_render_template('python', {'CustomNode': '{{ node.custom_value }}'})
        >>> 'UFunc' in templates and 'CustomNode' in templates
        True
    """
    return {**_KNOWN_STYLES[lang_style], **(ext_configs or {})}


def render_expr_node(expr: Union[float, int, dict, dsl_nodes.Expr, Any],
                     lang_style: str = 'dsl', ext_configs: Optional[Dict[str, str]] = None,
                     env: Optional[jinja2.Environment] = None):
    """
    Render an expression node to a string representation in the specified language style.

    This is a high-level function that sets up the environment and renders the expression
    in one step. It's a convenient wrapper around add_expr_render_to_env and fn_expr_render.

    :param expr: The expression to render
    :type expr: Union[float, int, dict, dsl_nodes.Expr, Any]

    :param lang_style: The language style to use ('dsl', 'c', 'cpp', 'python')
    :type lang_style: str

    :param ext_configs: Optional additional template configurations
    :type ext_configs: Optional[Dict[str, str]]

    :param env: Optional pre-configured Jinja2 environment
    :type env: Optional[jinja2.Environment]

    :return: The rendered string representation of the expression
    :rtype: str

    Example::

        >>> from pyfcstm.dsl import Integer
        >>> render_expr_node(Integer('42'), lang_style='python')
        '42'
        >>> render_expr_node(Integer('42'), lang_style='c')
        '42'
    """
    env = env or create_env()
    templates = create_expr_render_template(lang_style, ext_configs)
    _fn_expr_render = partial(fn_expr_render, templates=templates, env=env)
    env.globals['expr_render'] = _fn_expr_render
    env.filters['expr_render'] = _fn_expr_render
    return _fn_expr_render(node=expr)
