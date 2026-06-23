"""
Formatting helpers for the built-in Python runtime template.

This module contains template-private utilities used by ``templates/python`` to
make generated runtime source converge under standard Python formatting tools.
Keeping these helpers in the template package lets the generic renderer stay
unaware of concrete built-in template file names while still allowing the
Python template to centralize its own source cleanup policy.

The module contains the following component:

* :func:`clean_python_runtime_source` - Normalize whitespace in generated
  Python runtime source text before it is written by the template.

Example::

    >>> from pyfcstm.template._python_format import clean_python_runtime_source
    >>> clean_python_runtime_source('VALUES = (\n\n    1,\n\n)\n\n\n')
    'VALUES = (\n    1,\n)\n'
"""

import re


def clean_python_runtime_source(source: str) -> str:
    """
    Normalize whitespace in generated Python runtime source text.

    The built-in Python runtime template uses Jinja2 control structures to emit
    large literal dictionaries, tuples, methods, and docstrings. This helper
    removes template-control blank lines that are semantically meaningless in
    Python source while preserving ordinary PEP 8 spacing between top-level
    classes, functions, and decorators.

    :param source: Generated Python source text rendered by the template.
    :type source: str
    :return: Cleaned Python source ending with exactly one newline.
    :rtype: str

    Example::

        >>> clean_python_runtime_source('DATA = {\n\n    "a": 1,\n\n}\n')
        'DATA = {\n    "a": 1,\n}\n'
    """
    source = re.sub(r"([\(\[\{]\n)\n+", r"\1", source)
    source = re.sub(r"\n{3,}", "\n\n", source)
    source = re.sub(r',\n\n([ \t]*["\]\}])', r",\n\1", source)
    source = re.sub(r"\n\n(?=(?:class|def|@))", "\n\n\n", source)
    source = re.sub(
        r"\n([ \t]*)\n(?=[ \t]*[\]\)\}](?:,)?\n)",
        r"\n\1",
        source,
    )
    return re.sub(r"\n+\Z", "\n", source)
