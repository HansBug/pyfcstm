"""
Built-in template asset management for :mod:`pyfcstm`.

This module exposes packaged built-in template metadata and extraction helpers.
Packaged templates are stored as zip files alongside an ``index.json`` file.
The module intentionally stays small and only handles listing metadata and
extracting template assets to a directory for use by the existing renderer.
"""

from __future__ import annotations

import json
import os
import zipfile
from typing import Dict, List

__all__ = [
    'list_templates',
    'has_template',
    'get_template_info',
    'extract_template',
]


def _module_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _index_path() -> str:
    return os.path.join(_module_dir(), 'index.json')


def _load_index() -> Dict[str, List[Dict[str, object]]]:
    with open(_index_path(), 'r', encoding='utf-8') as f:
        return json.load(f)


def list_templates() -> List[str]:
    """
    List packaged built-in template names.
    """
    return [item['name'] for item in _load_index().get('templates', [])]


def has_template(name: str) -> bool:
    """
    Check whether a packaged built-in template exists.
    """
    return any(item == name for item in list_templates())


def get_template_info(name: str) -> Dict[str, object]:
    """
    Return metadata for one packaged built-in template.
    """
    for item in _load_index().get('templates', []):
        if item['name'] == name:
            return dict(item)
    raise LookupError('Built-in template {name!r} not found.'.format(name=name))


def extract_template(name: str, output_dir: str) -> str:
    """
    Extract a packaged built-in template into ``output_dir``.

    :param name: Built-in template name.
    :type name: str
    :param output_dir: Target directory for extraction.
    :type output_dir: str
    :return: Extracted template directory path.
    :rtype: str
    :raises LookupError: If the template does not exist.
    """
    info = get_template_info(name)
    archive_path = os.path.join(_module_dir(), info['archive'])
    os.makedirs(output_dir, exist_ok=True)
    with zipfile.ZipFile(archive_path, 'r') as zf:
        zf.extractall(output_dir)

    template_dir = os.path.join(output_dir, info.get('root_dir', name))
    if not os.path.isdir(template_dir):
        raise FileNotFoundError(
            'Extracted template directory {path!r} not found after unpacking {name!r}.'.format(
                path=template_dir,
                name=name,
            )
        )
    return os.path.abspath(template_dir)
