"""
Utilities for converting configuration items into callable objects.

This module provides a single public function, :func:`process_item_to_object`,
which transforms dictionary-based configuration items into callable render
functions, imported objects, or extracted values. It is designed to integrate
with Jinja2 templates and dynamic imports, enabling flexible runtime behavior
from declarative configurations.

The module contains the following main component:

* :func:`process_item_to_object` - Convert configuration items into objects

.. note::
   This module mutates dictionary inputs by popping configuration keys such as
   ``type``, ``template``, ``params``, ``from``, and ``value``. If the original
   dictionary should be preserved, pass a copy.

Example::

    >>> import jinja2
    >>> env = jinja2.Environment()
    >>> template_config = {
    ...     'type': 'template',
    ...     'template': 'Hello {{ name }}',
    ...     'params': ['name'],
    ... }
    >>> renderer = process_item_to_object(template_config, env)
    >>> renderer('World')
    'Hello World'

    >>> import_config = {'type': 'import', 'from': 'math.sqrt'}
    >>> sqrt_fn = process_item_to_object(import_config, env)
    >>> sqrt_fn(16)
    4.0
"""

from typing import Any, Dict

import jinja2
from hbutils.reflection import quick_import_object


def process_item_to_object(f: Any, env: jinja2.Environment) -> Any:
    """
    Process a configuration item into an object based on its type.

    This function converts dictionary configurations into different types of
    objects:

    - ``'template'``: Creates a callable Jinja2 template renderer function
    - ``'import'``: Imports an object from a specified module
    - ``'value'``: Extracts and returns a value from the configuration
    - Any other type or non-dictionary input is returned unchanged

    When the configuration is a dictionary, the function mutates it by
    removing the keys it consumes (such as ``type``, ``template``, ``params``,
    ``from``, or ``value``).

    :param f: Configuration item to process; typically a dictionary with a
        ``type`` key, or any other object to return unchanged.
    :type f: Any
    :param env: Jinja2 environment used for template rendering.
    :type env: jinja2.Environment
    :return: The processed object (callable, imported object, extracted value,
        or the original input).
    :rtype: Any
    :raises ImportError: If ``type`` is ``'import'`` and the target cannot be imported.

    Example::

        >>> import jinja2
        >>> env = jinja2.Environment()
        >>> template_config = {
        ...     'type': 'template',
        ...     'template': 'Hello {{ name }}',
        ...     'params': ['name'],
        ... }
        >>> renderer = process_item_to_object(template_config, env)
        >>> renderer('World')
        'Hello World'

        >>> import_config = {'type': 'import', 'from': 'math.sqrt'}
        >>> sqrt_fn = process_item_to_object(import_config, env)
        >>> sqrt_fn(16)
        4.0
    """
    if isinstance(f, dict):
        type_ = f.pop('type', None)
        if type_ == 'template':
            params = f.pop('params', None)
            template = f.pop('template')
            if params is not None:  # with params order
                obj_template = env.from_string(template)

                def _fn_render(*args: Any, **kwargs: Any) -> str:
                    render_args = dict(zip(params, args))
                    return obj_template.render(**render_args, **kwargs)

                return _fn_render

            else:  # no params order
                return env.from_string(template).render

        elif type_ == 'import':
            from_ = f.pop('from')
            obj, _, _ = quick_import_object(from_)
            return obj

        elif type_ == 'value':
            value = f.pop('value')
            return value

        else:
            return f
    else:
        return f
