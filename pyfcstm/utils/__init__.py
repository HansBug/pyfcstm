"""
Utility helpers package for :mod:`pyfcstm`.

This package provides a consolidated import location for frequently used utility
functions, interfaces, and exceptions within :mod:`pyfcstm`. The exported
symbols cover binary detection, decoding utilities, documentation formatting,
Jinja2 environment configuration, JSON/YAML serialization interfaces, safe
string handling, text normalization, value parsing, and validation helpers.

The package exposes the following main components:

* :func:`is_binary_file` - Detect whether a file is binary by inspecting its bytes
* :func:`auto_decode` - Decode bytes by trying multiple encodings
* :func:`format_multiline_comment` - Normalize multiline comments from parsers
* :func:`add_builtins_to_env` - Register Python built-ins in a Jinja2 environment
* :func:`add_settings_for_env` - Apply common filters and globals to Jinja2
* :class:`IJsonOp` - Interface for JSON/YAML serialization
* :func:`sequence_safe` - Build a safe underscore-separated identifier
* :func:`normalize` - Normalize text to identifier-friendly form
* :func:`to_identifier` - Convert text to a valid identifier format
* :func:`to_c_identifier` - Convert text to a C/C++-safe identifier
* :func:`parse_value` - Parse string values to appropriate Python types
* :func:`parse_key_value_pairs` - Parse multiple key=value pairs into a dictionary
* :class:`ValidationError` - Base validation error exception
* :class:`ModelValidationError` - Aggregated validation error exception
* :class:`IValidatable` - Interface for objects with validation rules

.. note::
   This package re-exports utilities from internal modules to provide a unified
   import path. The implementations reside in submodules such as
   :mod:`pyfcstm.utils.text` and :mod:`pyfcstm.utils.validate`.

Example::

    >>> from pyfcstm.utils import normalize, IJsonOp, parse_value
    >>> normalize("Hello World!")
    'Hello_World'
    >>> parse_value('42')
    42
"""

from .binary import is_binary_file
from .decode import auto_decode
from .doc import format_multiline_comment
from .fixed import Int8, Int16, Int32, Int64, UInt8, UInt16, UInt32, UInt64
from .jinja2 import add_builtins_to_env, add_settings_for_env
from .json import IJsonOp
from .logging import get_logger
from .parse import parse_value, parse_key_value_pairs
from .safe import sequence_safe
from .text import normalize, to_identifier, to_c_identifier
from .validate import ValidationError, ModelValidationError, IValidatable
