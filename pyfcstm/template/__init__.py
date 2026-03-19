"""
Built-in template asset management for :mod:`pyfcstm`.

This module provides the runtime-facing API for packaged built-in templates.
The repository keeps editable template sources under the top-level
``templates/`` directory, while packaged distributions ship zipped template
assets under :mod:`pyfcstm.template` together with an ``index.json`` metadata
file.

The functions in this module intentionally do only three things:

* list the built-in template names available in the installed package
* return metadata for one packaged template
* extract one packaged template into a normal directory so the existing
  :class:`pyfcstm.render.StateMachineCodeRenderer` can consume it

This separation keeps built-in template distribution independent from the
renderer itself. The module does not parse DSL code, does not render output
files directly, and does not implement any template-specific business logic.

The module contains the following public components:

* :func:`list_templates` - Return the names of packaged built-in templates
* :func:`has_template` - Check whether one built-in template is available
* :func:`get_template_info` - Return metadata for one packaged template
* :func:`extract_template` - Extract one packaged template into a directory

Example::

    >>> from pyfcstm.template import list_templates, extract_template
    >>> isinstance(list_templates(), list)
    True

.. note::
   The packaged template assets are generated from repository-root template
   sources during the template packaging step. This module only reads the
   packaged results already present inside :mod:`pyfcstm`.
"""

from __future__ import annotations

import json
import os
import shutil
import zipfile
from typing import Dict, List

__all__ = [
    'list_templates',
    'has_template',
    'get_template_info',
    'extract_template',
]


def _module_dir() -> str:
    """
    Return the absolute directory path of this module.

    :return: Absolute directory path containing packaged template assets.
    :rtype: str
    """
    return os.path.dirname(os.path.abspath(__file__))


def _index_path() -> str:
    """
    Return the absolute path to the packaged template index file.

    :return: Absolute path of ``index.json`` inside this module directory.
    :rtype: str
    """
    return os.path.join(_module_dir(), 'index.json')


def _load_index() -> Dict[str, List[Dict[str, object]]]:
    """
    Load the packaged template index metadata from disk.

    :return: Decoded JSON object from ``index.json``.
    :rtype: Dict[str, List[Dict[str, object]]]
    :raises FileNotFoundError: If the packaged template index is missing.
    :raises json.JSONDecodeError: If the packaged template index is invalid JSON.
    """
    with open(_index_path(), 'r', encoding='utf-8') as f:
        return json.load(f)


def _repo_template_source_dir(name: str) -> str:
    """
    Return the editable repository template source directory for ``name``.

    This helper is used as a development-checkout fallback when packaged zip
    assets are not present next to :mod:`pyfcstm.template`.

    :param name: Built-in template name.
    :type name: str
    :return: Absolute path to the repository template source directory.
    :rtype: str
    """
    repo_root = os.path.abspath(os.path.join(_module_dir(), '..', '..'))
    return os.path.join(repo_root, 'templates', name)


def list_templates() -> List[str]:
    """
    Return the names of packaged built-in templates.

    The names are read from the packaged ``index.json`` file and returned in
    the stored order. The result is suitable for CLI validation, documentation
    display, or built-in template discovery.

    :return: Built-in template names available in the installed package.
    :rtype: List[str]
    :raises FileNotFoundError: If the packaged template index is missing.
    :raises json.JSONDecodeError: If the packaged template index is invalid JSON.

    Example::

        >>> from pyfcstm.template import list_templates
        >>> templates = list_templates()
        >>> isinstance(templates, list)
        True
    """
    return [item['name'] for item in _load_index().get('templates', [])]


def has_template(name: str) -> bool:
    """
    Check whether a packaged built-in template exists.

    :param name: Built-in template name to check.
    :type name: str
    :return: ``True`` if the template exists, ``False`` otherwise.
    :rtype: bool
    :raises FileNotFoundError: If the packaged template index is missing.
    :raises json.JSONDecodeError: If the packaged template index is invalid JSON.

    Example::

        >>> from pyfcstm.template import has_template
        >>> has_template('python') in (True, False)
        True
    """
    return any(item == name for item in list_templates())


def get_template_info(name: str) -> Dict[str, object]:
    """
    Return metadata for one packaged built-in template.

    The returned dictionary is a shallow copy of the metadata entry stored in
    ``index.json``. Callers may modify the returned mapping without affecting
    the packaged metadata loaded by subsequent calls.

    :param name: Built-in template name.
    :type name: str
    :return: Metadata dictionary for the requested built-in template.
    :rtype: Dict[str, object]
    :raises LookupError: If the named template does not exist.
    :raises FileNotFoundError: If the packaged template index is missing.
    :raises json.JSONDecodeError: If the packaged template index is invalid JSON.

    Example::

        >>> from pyfcstm.template import get_template_info
        >>> info = get_template_info('python')  # doctest: +SKIP
        >>> info['name']  # doctest: +SKIP
        'python'
    """
    for item in _load_index().get('templates', []):
        if item['name'] == name:
            return dict(item)
    raise LookupError('Built-in template {name!r} not found.'.format(name=name))


def extract_template(name: str, output_dir: str) -> str:
    """
    Extract a packaged built-in template into ``output_dir``.

    This function normally unpacks the zip archive referenced by the template
    metadata entry and returns the extracted template directory path. In a
    development repository checkout, the packaged zip asset may be absent
    while the editable source template still exists under the repository-root
    ``templates/`` directory. In that case, the source template directory is
    copied into ``output_dir`` instead.

    The extracted or copied directory is intended to be passed directly to
    :class:`pyfcstm.render.StateMachineCodeRenderer`.

    :param name: Built-in template name.
    :type name: str
    :param output_dir: Target directory for extraction.
    :type output_dir: str
    :return: Extracted template directory path.
    :rtype: str
    :raises LookupError: If the template does not exist.
    :raises FileNotFoundError: If neither the packaged archive nor a
        development source template directory can be found, or if the
        extracted root directory is not present after unpacking.
    :raises zipfile.BadZipFile: If the packaged archive is not a valid zip file.

    Example::

        >>> from tempfile import TemporaryDirectory
        >>> from pyfcstm.template import extract_template
        >>> with TemporaryDirectory() as td:
        ...     path = extract_template('python', td)  # doctest: +SKIP
        ...     isinstance(path, str)  # doctest: +SKIP
        True
    """
    info = get_template_info(name)
    archive_path = os.path.join(_module_dir(), info['archive'])
    os.makedirs(output_dir, exist_ok=True)
    template_dir = os.path.join(output_dir, info.get('root_dir', name))
    if os.path.isfile(archive_path):
        with zipfile.ZipFile(archive_path, 'r') as zf:
            zf.extractall(output_dir)
    else:
        source_template_dir = _repo_template_source_dir(name)
        if not os.path.isdir(source_template_dir):
            raise FileNotFoundError(
                'Built-in template archive {archive!r} not found and source template directory '
                '{source!r} is also missing for {name!r}.'.format(
                    archive=archive_path,
                    source=source_template_dir,
                    name=name,
                )
            )
        shutil.copytree(source_template_dir, template_dir)

    if not os.path.isdir(template_dir):
        raise FileNotFoundError(
            'Extracted template directory {path!r} not found after unpacking {name!r}.'.format(
                path=template_dir,
                name=name,
            )
        )
    return os.path.abspath(template_dir)
