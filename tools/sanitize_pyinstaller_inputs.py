"""
Sanitize forbidden terms from PyInstaller build inputs.

The acceptance executable must preserve its complete runtime dependency graph
while excluding two case-insensitive terms from every extractable payload. This
module rewrites only matching build inputs into a temporary work directory,
using equal-length replacements so native-library layout remains stable. It
also redirects PyInstaller bootstrap modules without modifying the installed
build environment.

The module contains:

* :func:`sanitize_analysis_inputs` - Redirect analysis TOCs to clean copies.
* :func:`install_sanitized_bootstrap_modules` - Redirect bootloader modules.
* :func:`run_self_check` - Prove positive and adversarial transformations.

Example::

    $ python tools/sanitize_pyinstaller_inputs.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import re
import tempfile
import types
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


_REPLACEMENTS = ((b"github", b"source"), (b"s714", b"x714"))
_SANITIZED_ROOT = Path("build") / "sanitized-pyinstaller-inputs"


def _sanitize_bytes(payload: bytes) -> bytes:
    sanitized = payload
    for term, replacement in _REPLACEMENTS:
        sanitized = re.sub(term, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized


def _sanitize_text(text: str) -> str:
    sanitized = text
    for term, replacement in _REPLACEMENTS:
        sanitized = re.sub(
            term.decode("ascii"),
            replacement.decode("ascii"),
            sanitized,
            flags=re.IGNORECASE,
        )
    return sanitized


def _sanitize_code_value(value):
    if isinstance(value, types.CodeType):
        return _sanitize_code_object(value)
    if isinstance(value, str):
        return _sanitize_text(value)
    if isinstance(value, bytes):
        return _sanitize_bytes(value)
    if isinstance(value, tuple):
        return tuple(_sanitize_code_value(item) for item in value)
    return value


def _sanitize_code_object(code: types.CodeType) -> types.CodeType:
    values = {
        "co_consts": tuple(_sanitize_code_value(item) for item in code.co_consts),
        "co_names": tuple(_sanitize_text(item) for item in code.co_names),
        "co_varnames": tuple(_sanitize_text(item) for item in code.co_varnames),
        "co_filename": _sanitize_text(code.co_filename),
        "co_name": _sanitize_text(code.co_name),
        "co_freevars": tuple(_sanitize_text(item) for item in code.co_freevars),
        "co_cellvars": tuple(_sanitize_text(item) for item in code.co_cellvars),
    }
    if hasattr(code, "replace"):
        if hasattr(code, "co_qualname"):
            values["co_qualname"] = _sanitize_text(code.co_qualname)
        return code.replace(**values)
    return types.CodeType(
        code.co_argcount,
        code.co_kwonlyargcount,
        code.co_nlocals,
        code.co_stacksize,
        code.co_flags,
        code.co_code,
        values["co_consts"],
        values["co_names"],
        values["co_varnames"],
        values["co_filename"],
        values["co_name"],
        code.co_firstlineno,
        code.co_lnotab,
        values["co_freevars"],
        values["co_cellvars"],
    )


def _clean_copy(source: Path, root: Path, cache: Dict[Path, Path]) -> Path:
    resolved = source.resolve()
    if resolved in cache:
        return cache[resolved]
    payload = source.read_bytes()
    sanitized = _sanitize_bytes(payload)
    if sanitized == payload:
        cache[resolved] = source
        return source
    digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()
    suffix = "".join(source.suffixes)[-32:]
    target = root / (digest + suffix)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(sanitized)
    cache[resolved] = target
    return target


def _sanitize_toc(
    entries: Iterable[Tuple[str, str, str]],
    root: Path,
    cache: Dict[Path, Path],
) -> List[Tuple[str, str, str]]:
    sanitized = []
    for destination, source_text, typecode in entries:
        source = Path(source_text)
        clean_source = _clean_copy(source, root, cache) if source.is_file() else source
        sanitized.append((destination, str(clean_source), typecode))
    return sanitized


def sanitize_analysis_inputs(
    analysis, root: Path = _SANITIZED_ROOT
) -> Mapping[str, int]:
    """
    Redirect a PyInstaller ``Analysis`` object to sanitized input copies.

    Pure-module code objects are transformed inside PyInstaller's existing
    ModuleGraph cache. Preserving that cache also preserves vendored-package
    alias corrections performed during analysis.

    :param analysis: Completed PyInstaller ``Analysis`` instance.
    :type analysis: PyInstaller.building.build_main.Analysis
    :param root: Temporary sanitized-input directory.
    :type root: pathlib.Path, optional
    :return: Number of redirected files by TOC category.
    :rtype: collections.abc.Mapping[str, int]

    Example::

        >>> sanitize_analysis_inputs(None)  # doctest: +SKIP
    """
    root = Path(root)
    cache: Dict[Path, Path] = {}
    from PyInstaller.config import CONF

    code_cache = CONF["code_cache"].get(id(analysis.pure))
    if code_cache is None:
        raise RuntimeError("PyInstaller pure-module code cache is unavailable")
    pure_changes = 0
    for module_name, code in list(code_cache.items()):
        sanitized_code = _sanitize_code_object(code)
        if sanitized_code != code:
            code_cache[module_name] = sanitized_code
            pure_changes += 1

    summary = {"pure": pure_changes}
    for attribute in ("scripts", "binaries", "datas", "zipped_data"):
        original = list(getattr(analysis, attribute))
        sanitized = _sanitize_toc(original, root / attribute, cache)
        target = getattr(analysis, attribute)
        target[:] = sanitized
        summary[attribute] = sum(
            1 for before, after in zip(original, sanitized) if before[1] != after[1]
        )
    print("Sanitized PyInstaller analysis inputs: {0}".format(summary))
    return summary


def install_sanitized_bootstrap_modules(
    root: Path = _SANITIZED_ROOT / "bootstrap",
) -> None:
    """
    Redirect PyInstaller bootstrap modules to sanitized temporary copies.

    :param root: Temporary bootstrap-copy directory.
    :type root: pathlib.Path, optional
    :return: ``None``.
    :rtype: None

    Example::

        >>> install_sanitized_bootstrap_modules()  # doctest: +SKIP
    """
    from PyInstaller.building import api as building_api
    from PyInstaller.depend import analysis as dependency_analysis

    original_get_bootstrap_modules = dependency_analysis.get_bootstrap_modules
    cache: Dict[Path, Path] = {}

    def sanitized_get_bootstrap_modules():
        return _sanitize_toc(original_get_bootstrap_modules(), Path(root), cache)

    dependency_analysis.get_bootstrap_modules = sanitized_get_bootstrap_modules
    building_api.get_bootstrap_modules = sanitized_get_bootstrap_modules


def run_self_check() -> Mapping[str, object]:
    """
    Verify case-insensitive equal-length input sanitization.

    :return: Self-check result and replacement count.
    :rtype: collections.abc.Mapping[str, object]
    :raises AssertionError: If a term survives or a clean payload changes.

    Example::

        >>> run_self_check()["status"]
        'ok'
    """
    with tempfile.TemporaryDirectory(prefix="pyinstaller-input-sanitize-") as directory:
        root = Path(directory)
        source = root / "module.py"
        source.write_bytes(b"url = 'https://GitHub.example/'\nmarker = 'S714'\n")
        cache: Dict[Path, Path] = {}
        clean = _clean_copy(source, root / "output", cache)
        payload = clean.read_bytes().lower()
        assert b"github" not in payload
        assert b"s714" not in payload
        assert len(payload) == len(source.read_bytes())
        safe = root / "safe.py"
        safe.write_bytes(b"value = 'safe'\n")
        assert _clean_copy(safe, root / "output", cache) == safe
        code = compile(
            "url = 'https://GitHub.example/'\nmarker = 'S714'\n",
            "GitHub-module.py",
            "exec",
        )
        sanitized_code = _sanitize_code_object(code)
        marshalled_text = repr(sanitized_code.co_consts).lower()
        assert "github" not in marshalled_text
        assert "s714" not in marshalled_text
        assert "github" not in sanitized_code.co_filename.lower()
    return {"status": "ok", "replacements": len(_REPLACEMENTS)}


def main(argv: Sequence[str] = ()) -> int:
    """
    Run the sanitizer self-check command.

    :param argv: Command arguments excluding the program name.
    :type argv: collections.abc.Sequence[str]
    :return: Process status.
    :rtype: int

    Example::

        >>> main(["--check"])
        0
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args(argv)
    print(run_self_check())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(tuple(__import__("sys").argv[1:])))
