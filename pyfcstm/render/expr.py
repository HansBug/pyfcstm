from functools import partial
from typing import Optional, Dict

import jinja2

from .env import create_env
from ..dsl import node as dsl_nodes

_DEFAULT = {
    'default': '{{ node }}',
}

_DSL_STYLE = {
    **_DEFAULT,
}

_C_STYLE = {
    **_DEFAULT,
    'Float': '{{ node.value | repr }}',
    'Integer': '{{ node.value | repr }}',
    'Boolean': '{{ (1 if node.value else 0) | hex }}',
    'Constant': '{{ node.value | repr }}',
    'HexInt': '{{ node.value | hex }}',
    'Paren': '({{ node.expr | expr_render }})',
    'UFunc': '{{ node.func }}({{ node.expr | expr_render }})',
    'Name': '{{ node.name }}',
    'UnaryOp': '{{ node.op }}{{ node.expr | expr_render }}',
    'BinaryOp': '{{ node.expr1 | expr_render}} {{ node.op }} {{ node.expr2 | expr_render}}',
    'BinaryOp(**)': 'pow({{ node.expr1 | expr_render}}, {{ node.expr2 | expr_render}})',
    'ConditionalOp': '({{ node.cond | expr_render }}) ? {{ node.value_true | expr_render }} : {{ node.value_false | expr_render }}',
}

_PY_STYLE = {
    **_DEFAULT,
    'Float': '{{ node.value | repr }}',
    'Integer': '{{ node.value | repr }}',
    'Boolean': '{{ node.value | repr }}',
    'Constant': '{{ node.value | repr }}',
    'HexInt': '{{ node.value | hex }}',
    'Paren': '({{ node.expr | expr_render }})',
    'UFunc': 'math.{{ node.func }}({{ node.expr | expr_render }})',
    'Name': '{{ node.name }}',
    'UnaryOp': '{{ node.op }}{{ node.expr | expr_render }}',
    'UnaryOp(!)': 'not {{ node.expr | expr_render }}',
    'BinaryOp': '{{ node.expr1 | expr_render}} {{ node.op }} {{ node.expr2 | expr_render}}',
    'BinaryOp(&&)': '{{ node.expr1 | expr_render}} and {{ node.expr2 | expr_render}}',
    'BinaryOp(||)': '{{ node.expr1 | expr_render}} or {{ node.expr2 | expr_render}}',
    'ConditionalOp': '{{ node.value_true | expr_render }} if {{ node.cond | expr_render }} else {{ node.value_false | expr_render }}',
}

_KNOWN_STYLES = {
    'default': _DEFAULT,
    'dsl': _DSL_STYLE,
    'c': _C_STYLE,
    'cpp': _C_STYLE,
    'python': _PY_STYLE,
}


def fn_expr_render(node: dsl_nodes.Expr, templates: Dict[str, str], env: jinja2.Environment):
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
    elif isinstance(node, dsl_nodes.ConditionalOp) and type(node).__name__ in templates:
        template_str = templates[type(node).__name__]
    else:
        template_str = templates['default']

    tp = env.from_string(template_str)
    return tp.render(node=node)


def add_expr_render_to_env(env: jinja2.Environment,
                           lang_style: str = 'dsl', ext_configs: Optional[Dict[str, str]] = None):
    templates = {**_KNOWN_STYLES[lang_style], **(ext_configs or {})}
    _fn_expr_render = partial(fn_expr_render, templates=templates, env=env)
    env.globals['expr_render'] = _fn_expr_render
    env.filters['expr_render'] = _fn_expr_render
    return env


def render_expr_node(expr: dsl_nodes.Expr, lang_style: str = 'dsl', ext_configs: Optional[Dict[str, str]] = None,
                     env: Optional[jinja2.Environment] = None):
    env = env or create_env()
    env = add_expr_render_to_env(env, lang_style=lang_style, ext_configs=ext_configs)
    _fn_expr_render = env.globals['expr_render']
    return _fn_expr_render(node=expr)
