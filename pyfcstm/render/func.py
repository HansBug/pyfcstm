"""
Module for processing items to objects with Jinja2 templates and dynamic imports.

This module provides functionality to convert dictionary configurations into callable objects,
templates, or imported objects based on their specified type. It supports creating template
renderers, importing objects from modules, and extracting values from configuration dictionaries.
"""

import jinja2
from hbutils.reflection import quick_import_object


def process_item_to_object(f, env: jinja2.Environment):
    """
    Process a configuration item into an object based on its type.

    This function converts dictionary configurations into different types of objects:

    - 'template': Creates a callable template renderer function
    - 'import': Imports an object from a specified module
    - 'value': Extracts a value from the configuration
    - For other types or non-dictionary inputs, returns the input unchanged

    :param f: The configuration item to process, can be a dictionary or any other type
    :type f: dict or any

    :param env: The Jinja2 environment used for template rendering
    :type env: jinja2.Environment

    :return: The processed object (function, imported object, value, or unchanged input)
    :rtype: any

    Example::

        >>> env = jinja2.Environment()
        >>> # Create a template renderer
        >>> template_config = {'type': 'template', 'template': 'Hello {{ name }}', 'params': ['name']}
        >>> renderer = process_item_to_object(template_config, env)
        >>> renderer('World')
        'Hello World'

        >>> # Import an object
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

                def _fn_render(*args, **kwargs):
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
