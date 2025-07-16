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
    return data.decode(encoding)


def auto_decode(data: Union[bytes, bytearray]) -> str:
    _elist = list(filter(bool, unique([
        chardet.detect(data)['encoding'],
        *windows_chinese_encodings,
        sys.getdefaultencoding(),
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
