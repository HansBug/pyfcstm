"""
Binary file detection utilities.

This module provides functionality to determine whether a given file is a binary
file or a text file by reading the first 1024 bytes of the file and checking for
the presence of non-text characters.

The module contains the following main components:

* :func:`is_binary_file` - Determine whether a file is binary based on byte content.

.. note::
    Inspired from https://stackoverflow.com/a/7392391/6995899

Example::

    >>> import os, pathlib, tempfile
    >>> from pyfcstm.utils.binary import is_binary_file
    >>> directory = tempfile.mkdtemp()
    >>> text_file = os.path.join(directory, 'example.txt')
    >>> _ = pathlib.Path(text_file).write_text('plain text\\n')
    >>> binary_file = os.path.join(directory, 'example.bin')
    >>> _ = pathlib.Path(binary_file).write_bytes(b'\\x00\\x01\\x02')
    >>> is_binary_file(text_file)
    False
    >>> is_binary_file(binary_file)
    True
"""

from __future__ import annotations

_TEXT_CHARS = bytearray({7, 8, 9, 10, 12, 13, 27} | set(range(0x20, 0x100)) - {0x7f})


def is_binary_file(file: str) -> bool:
    """
    Check if a given file is binary.

    This function reads the first 1024 bytes of the file and checks whether it
    contains any non-text (binary) characters. It uses a predefined set of
    text characters to determine the nature of the file.

    :param file: The path to the file to be checked.
    :type file: str
    :return: ``True`` if the file is binary, ``False`` if it is a text file.
    :rtype: bool
    :raises FileNotFoundError: If the specified file does not exist.
    :raises OSError: If there is an error reading the file.

    Example::

        >>> import os, pathlib, tempfile
        >>> directory = tempfile.mkdtemp()
        >>> text_file = os.path.join(directory, 'example.txt')
        >>> _ = pathlib.Path(text_file).write_text('plain text\\n')
        >>> binary_file = os.path.join(directory, 'example.bin')
        >>> _ = pathlib.Path(binary_file).write_bytes(b'\\x00\\x01\\x02')
        >>> is_binary_file(text_file)
        False
        >>> is_binary_file(binary_file)
        True
    """
    with open(file, 'rb') as f:
        prefix = f.read(1024)
        return bool(prefix.translate(None, _TEXT_CHARS))
