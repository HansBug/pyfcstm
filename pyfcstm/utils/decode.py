"""
Automatic text decoding utilities with a focus on Chinese encodings.

This module provides helpers for decoding byte sequences by trying a series of
likely encodings. It is designed to work well with Windows-centric Chinese
encodings while still supporting Unicode variants. The decoding strategy
attempts multiple encodings in a defined order and returns the first successful
result.

The module contains the following public components:

* :data:`windows_chinese_encodings` - Ordered list of common Chinese encodings
* :func:`auto_decode` - Robust decoding function with auto-detection

.. note::
   This module relies on :mod:`chardet` for probabilistic encoding detection.

Example::

    >>> from pyfcstm.utils.decode import auto_decode
    >>> text_bytes = b'\\xc4\\xe3\\xba\\xc3'  # "你好" in GBK encoding
    >>> auto_decode(text_bytes)
    '你好'
"""

import sys
from typing import Union

import chardet
from hbutils.collection import unique

windows_chinese_encodings = [
    'utf-8',  # UTF-8 encoding, Unicode standard
    'gbk',  # Most common default encoding for Chinese Windows
    'gb2312',  # Common encoding for Simplified Chinese, subset of GBK
    'gb18030',  # Chinese national standard encoding, includes all Chinese characters
    'big5',  # Common encoding for Traditional Chinese (Taiwan, Hong Kong)
    'cp936',  # Windows code page for Simplified Chinese, essentially an alias for GBK
    'cp950',  # Windows code page for Traditional Chinese, approximately equivalent to Big5
    'hz',  # Early Chinese character encoding
    # 'iso-2022-cn',  # ISO standard encoding for Chinese
    'euc-cn',  # Extended Unix Code for Chinese
    'utf-16',  # Default Unicode encoding used by Windows Notepad
    'utf-16-le',  # Little-endian UTF-16 encoding, commonly used in Windows
    'utf-16-be',  # Big-endian UTF-16 encoding
    'utf-32',  # 32-bit Unicode encoding
    'utf-32-le',  # Little-endian UTF-32 encoding
    'utf-32-be'  # Big-endian UTF-32 encoding
]


def _decode(data: bytes, encoding: str) -> str:
    """
    Decode bytes data using the specified encoding.

    :param data: Bytes to decode.
    :type data: bytes
    :param encoding: Text encoding to use for decoding.
    :type encoding: str
    :return: Decoded text.
    :rtype: str
    :raises UnicodeDecodeError: If the bytes cannot be decoded using ``encoding``.
    """
    return data.decode(encoding)


def auto_decode(data: Union[bytes, bytearray]) -> str:
    """
    Automatically decode bytes by trying multiple encodings.

    The decoding order depends on the input length:

    * For inputs with length >= 30, the order is:
      1) encoding detected by :mod:`chardet`
      2) entries in :data:`windows_chinese_encodings`
      3) system default encoding
    * For shorter inputs, the order is:
      1) entries in :data:`windows_chinese_encodings`
      2) system default encoding
      3) encoding detected by :mod:`chardet`

    The function tries each encoding until one succeeds. If all attempts fail,
    it raises the :class:`UnicodeDecodeError` that progressed furthest (i.e.,
    the error with the highest ``start`` position).

    :param data: The bytes data to decode.
    :type data: Union[bytes, bytearray]
    :return: The decoded string.
    :rtype: str
    :raises UnicodeDecodeError: If decoding fails for all attempted encodings.

    Example::

        >>> text_bytes = b'\\xc4\\xe3\\xba\\xc3'  # "你好" in GBK encoding
        >>> auto_decode(text_bytes)
        '你好'
    """
    if len(data) >= 30:
        _elist = list(filter(bool, unique([
            chardet.detect(data)['encoding'],
            *windows_chinese_encodings,
            sys.getdefaultencoding(),
        ])))
    else:
        _elist = list(filter(bool, unique([
            *windows_chinese_encodings,
            sys.getdefaultencoding(),
            chardet.detect(data)['encoding'],
        ])))

    last_err = None
    for enc in _elist:
        try:
            text = _decode(data, enc)
        except UnicodeDecodeError as err:
            if last_err is None or err.start > last_err.start:
                last_err = err
        else:
            return text

    raise last_err
