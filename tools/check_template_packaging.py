"""
Validate repository-source built-in template packaging contracts.

This maintenance command checks the packaging behavior that is intentionally
outside the pytest unit-test boundary. It exercises :mod:`tools.package_templates`
against repository-source template directories and verifies that the generated
zip assets are self-contained, metadata-rich, and suitable for packaged runtime
extraction.

The command contains the following checks:
* packaged index metadata and archive root layout
* C++ template reuse payload resolution for symlinks and Windows text stubs
* rejection of unexpected C++ reuse text stubs
* package/distribution metadata declarations for packaged template assets

Example::

    $ python tools/check_template_packaging.py
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, Iterable, List, Optional, Tuple


def _bootstrap_repo_imports() -> Path:
    """
    Add the repository root to ``sys.path`` for direct script execution.

    :return: Repository root path.
    :rtype: pathlib.Path
    """
    import sys

    root = Path(__file__).resolve().parents[1]
    root_text = str(root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)
    return root


_REPO_ROOT = _bootstrap_repo_imports()

from tools.package_templates import package_templates, _resolve_archive_source  # noqa: E402


CURRENT_TEMPLATE_NAMES = ("c", "c_poll", "cpp", "cpp_poll", "python")
REQUIRED_TEMPLATE_FILES = {
    "c": {
        "README.md",
        "README_zh.md",
        "README.md.j2",
        "README_zh.md.j2",
        "config.yaml",
        "template.json",
        "machine.h.j2",
        "machine.c.j2",
    },
    "c_poll": {
        "README.md",
        "README_zh.md",
        "README.md.j2",
        "README_zh.md.j2",
        "config.yaml",
        "template.json",
        "machine.h.j2",
        "machine.c.j2",
    },
    "cpp": {
        "README.md",
        "README_zh.md",
        "README.md.j2",
        "README_zh.md.j2",
        "config.yaml",
        "template.json",
        "machine.h.j2",
        "machine.c.j2",
        "machine.hpp.j2",
        "machine.cpp.j2",
    },
    "cpp_poll": {
        "README.md",
        "README_zh.md",
        "README.md.j2",
        "README_zh.md.j2",
        "config.yaml",
        "template.json",
        "machine.h.j2",
        "machine.c.j2",
        "machine.hpp.j2",
        "machine.cpp.j2",
    },
    "python": {
        "README.md",
        "README_zh.md",
        "README.md.j2",
        "README_zh.md.j2",
        "config.yaml",
        "template.json",
        "machine.py.j2",
    },
}


def repository_root() -> Path:
    """
    Return the repository root for this maintenance command.

    :return: Repository root path.
    :rtype: pathlib.Path

    Example::

        >>> repository_root().name  # doctest: +SKIP
        'pyfcstm'
    """
    return _REPO_ROOT


def read_json(path: Path) -> Dict[str, object]:
    """
    Load a UTF-8 JSON object from ``path``.

    :param path: JSON file path.
    :type path: pathlib.Path
    :return: Decoded JSON object.
    :rtype: Dict[str, object]
    :raises json.JSONDecodeError: If the file is not valid JSON.
    :raises OSError: If the file cannot be read.

    Example::

        >>> isinstance(read_json(repository_root() / 'pyfcstm' / 'template' / 'index.json'), dict)
        True
    """
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def read_text(path: Path) -> str:
    """
    Read a UTF-8 text file.

    :param path: Text file path.
    :type path: pathlib.Path
    :return: File text.
    :rtype: str
    :raises OSError: If the file cannot be read.

    Example::

        >>> 'pyfcstm' in read_text(repository_root() / 'setup.py')
        True
    """
    return path.read_text(encoding="utf-8")


def repository_template_names(templates_dir: Path) -> Tuple[str, ...]:
    """
    Return sorted repository-source built-in template names.

    :param templates_dir: Repository-root ``templates`` directory.
    :type templates_dir: pathlib.Path
    :return: Template directory names.
    :rtype: Tuple[str, ...]

    Example::

        >>> 'python' in repository_template_names(repository_root() / 'templates')
        True
    """
    return tuple(
        item.name
        for item in sorted(templates_dir.iterdir())
        if item.is_dir() and not item.name.startswith(".")
    )


def load_template_metadata(templates_dir: Path, name: str) -> Dict[str, object]:
    """
    Load one repository-source template metadata file.

    :param templates_dir: Repository-root ``templates`` directory.
    :type templates_dir: pathlib.Path
    :param name: Template name.
    :type name: str
    :return: Template metadata object.
    :rtype: Dict[str, object]
    :raises OSError: If the metadata file cannot be read.
    :raises json.JSONDecodeError: If the metadata file is not valid JSON.

    Example::

        >>> load_template_metadata(repository_root() / 'templates', 'python')['name']
        'python'
    """
    return read_json(templates_dir / name / "template.json")


def zip_payload(
    output_dir: Path, template_name: str, rel_path: str
) -> Tuple[zipfile.ZipInfo, bytes]:
    """
    Return metadata and bytes for one packaged template member.

    :param output_dir: Directory containing template zip archives.
    :type output_dir: pathlib.Path
    :param template_name: Packaged template name.
    :type template_name: str
    :param rel_path: Template-relative member path.
    :type rel_path: str
    :return: Zip member metadata and payload bytes.
    :rtype: Tuple[zipfile.ZipInfo, bytes]
    :raises KeyError: If the member does not exist in the archive.
    :raises zipfile.BadZipFile: If the archive is invalid.

    Example::

        >>> with TemporaryDirectory() as td:  # doctest: +SKIP
        ...     zip_payload(Path(td), 'python', 'config.yaml')
    """
    with zipfile.ZipFile(
        str(output_dir / "{name}.zip".format(name=template_name)), "r"
    ) as zf:
        info = zf.getinfo("{name}/{rel}".format(name=template_name, rel=rel_path))
        payload = zf.read(info)
    return info, payload


def package_to_tempdir(templates_dir: Path) -> Tuple[TemporaryDirectory, Path]:
    """
    Package repository templates into a temporary output directory.

    The returned :class:`tempfile.TemporaryDirectory` must be kept alive by the
    caller while the output path is used.

    :param templates_dir: Repository-root ``templates`` directory.
    :type templates_dir: pathlib.Path
    :return: Temporary directory manager and output path.
    :rtype: Tuple[tempfile.TemporaryDirectory, pathlib.Path]

    Example::

        >>> manager, output = package_to_tempdir(repository_root() / 'templates')  # doctest: +SKIP
        >>> manager.cleanup()  # doctest: +SKIP
    """
    manager = TemporaryDirectory()
    output_dir = Path(manager.name)
    package_templates(str(templates_dir), str(output_dir), verbose=False)
    return manager, output_dir


def assert_packaging_output_preserves_metadata_and_archive_roots(
    templates_dir: Path,
) -> None:
    """
    Verify packaged template metadata, roots, required files, and stale cleanup.

    :param templates_dir: Repository-root ``templates`` directory.
    :type templates_dir: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If a packaging contract is violated.

    Example::

        >>> assert_packaging_output_preserves_metadata_and_archive_roots(repository_root() / 'templates')
    """
    with TemporaryDirectory() as td:
        output_dir = Path(td)
        stale_zip = output_dir / "stale.zip"
        stale_zip.write_bytes(b"stale")

        package_templates(str(templates_dir), str(output_dir), verbose=False)

        assert not stale_zip.exists()
        index = read_json(output_dir / "index.json")
        assert [item["name"] for item in index["templates"]] == list(
            repository_template_names(templates_dir)
        )

        for item in index["templates"]:
            name = item["name"]
            repo_metadata = load_template_metadata(templates_dir, name)
            assert item["archive"] == "{name}.zip".format(name=name)
            assert item["root_dir"] == name
            for key in ["title", "description", "language", "experimental"]:
                assert item[key] == repo_metadata[key]

            archive_path = output_dir / item["archive"]
            assert archive_path.is_file()
            with zipfile.ZipFile(str(archive_path), "r") as zf:
                names = zf.namelist()
            assert names
            assert all(path.startswith(name + "/") for path in names)
            archived_rel_paths = {path[len(name) + 1 :] for path in names}
            assert REQUIRED_TEMPLATE_FILES[name] <= archived_rel_paths
            assert not any("__pycache__" in path for path in names)


def assert_distribution_metadata_keeps_template_assets_declared(
    repo_root: Path,
) -> None:
    """
    Verify source distribution metadata declares packaged template assets.

    :param repo_root: Repository root path.
    :type repo_root: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If package metadata no longer declares assets.

    Example::

        >>> assert_distribution_metadata_keeps_template_assets_declared(repository_root())
    """
    setup_text = read_text(repo_root / "setup.py")
    manifest_text = read_text(repo_root / "MANIFEST.in")

    assert "from tools.package_templates import package_templates" in setup_text
    assert "package_templates(" in setup_text
    assert "package_data" in setup_text
    assert "*.zip" in setup_text
    assert "*.json" in setup_text
    assert "recursive-include pyfcstm/template *.zip *.json" in manifest_text


def assert_cpp_templates_reuse_c_core_as_packaged_file_payloads(
    templates_dir: Path,
) -> None:
    """
    Verify C++ packaged core files contain C payload bytes, not symlinks/stubs.

    :param templates_dir: Repository-root ``templates`` directory.
    :type templates_dir: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If a C++ package stores a symlink or stub payload.

    Example::

        >>> assert_cpp_templates_reuse_c_core_as_packaged_file_payloads(repository_root() / 'templates')
    """
    manager, output_dir = package_to_tempdir(templates_dir)
    try:
        for template_name, source_template in [("cpp", "c"), ("cpp_poll", "c_poll")]:
            for rel_path in ["machine.c.j2", "machine.h.j2"]:
                info, payload = zip_payload(output_dir, template_name, rel_path)
                assert stat.S_IFMT(info.external_attr >> 16) != stat.S_IFLNK
                assert (
                    payload == (templates_dir / source_template / rel_path).read_bytes()
                )
                assert payload.strip() != (
                    "../{source}/{rel}".format(source=source_template, rel=rel_path)
                ).encode("utf-8")
    finally:
        manager.cleanup()


def assert_cpp_template_packaging_accepts_symlink_when_realpath_does_not_resolve(
    templates_dir: Path,
) -> None:
    """
    Verify explicit symlink text is accepted when ``realpath`` is unreliable.

    :param templates_dir: Repository-root ``templates`` directory.
    :type templates_dir: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If symlink target text does not resolve correctly.

    Example::

        >>> assert_cpp_template_packaging_accepts_symlink_when_realpath_does_not_resolve(repository_root() / 'templates')
    """
    src_file = templates_dir / "cpp" / "machine.c.j2"
    target_file = templates_dir / "c" / "machine.c.j2"
    realpath = os.path.realpath

    def unresolved_realpath(path: str) -> str:
        """
        Simulate a checkout mode where ``realpath`` cannot resolve one symlink.

        :param path: Path passed to :func:`os.path.realpath`.
        :type path: str
        :return: Simulated real path.
        :rtype: str
        """
        if os.path.abspath(path) == os.path.abspath(str(src_file)):
            return os.path.abspath(path)
        return realpath(path)

    try:
        os.path.realpath = unresolved_realpath
        assert _resolve_archive_source(
            str(templates_dir / "cpp"),
            str(src_file),
            "cpp",
            "machine.c.j2",
        ) == str(target_file)
    finally:
        os.path.realpath = realpath


def copy_templates_with_windows_symlink_text_stubs(
    templates_dir: Path,
    source_root: Path,
    template_names: Iterable[str],
) -> None:
    """
    Copy templates while replacing symlinks with Windows checkout text stubs.

    :param templates_dir: Repository-root ``templates`` directory.
    :type templates_dir: pathlib.Path
    :param source_root: Temporary template source root to create.
    :type source_root: pathlib.Path
    :param template_names: Template names to copy.
    :type template_names: Iterable[str]
    :return: ``None``.
    :rtype: None
    :raises OSError: If a file cannot be copied or written.

    Example::

        >>> with TemporaryDirectory() as td:  # doctest: +SKIP
        ...     copy_templates_with_windows_symlink_text_stubs(repository_root() / 'templates', Path(td), ['c'])
    """
    for name in template_names:
        src_dir = templates_dir / name
        dst_dir = source_root / name
        dst_dir.mkdir(parents=True)
        for item in src_dir.iterdir():
            if item.is_file() or item.is_symlink():
                if item.is_symlink():
                    target = Path(os.readlink(str(item))).as_posix()
                    (dst_dir / item.name).write_text(target + "\n", encoding="utf-8")
                else:
                    (dst_dir / item.name).write_bytes(item.read_bytes())


def assert_cpp_template_packaging_resolves_windows_symlink_text_stubs(
    templates_dir: Path,
) -> None:
    """
    Verify expected Windows text stubs are packaged as target payloads.

    :param templates_dir: Repository-root ``templates`` directory.
    :type templates_dir: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If a text stub is not resolved to target bytes.

    Example::

        >>> assert_cpp_template_packaging_resolves_windows_symlink_text_stubs(repository_root() / 'templates')
    """
    with TemporaryDirectory() as source_td, TemporaryDirectory() as output_td:
        source_root = Path(source_td) / "templates"
        output_dir = Path(output_td)
        copy_templates_with_windows_symlink_text_stubs(
            templates_dir,
            source_root,
            ["c", "c_poll", "cpp", "cpp_poll"],
        )

        package_templates(str(source_root), str(output_dir), verbose=False)

        _, cpp_c_payload = zip_payload(output_dir, "cpp", "machine.c.j2")
        _, cpp_h_payload = zip_payload(output_dir, "cpp", "machine.h.j2")
        _, cpp_poll_c_payload = zip_payload(output_dir, "cpp_poll", "machine.c.j2")
        _, cpp_poll_h_payload = zip_payload(output_dir, "cpp_poll", "machine.h.j2")
        assert cpp_c_payload == (source_root / "c" / "machine.c.j2").read_bytes()
        assert cpp_h_payload == (source_root / "c" / "machine.h.j2").read_bytes()
        assert (
            cpp_poll_c_payload == (source_root / "c_poll" / "machine.c.j2").read_bytes()
        )
        assert (
            cpp_poll_h_payload == (source_root / "c_poll" / "machine.h.j2").read_bytes()
        )


def assert_cpp_template_packaging_rejects_unexpected_windows_symlink_text_stub(
    templates_dir: Path,
) -> None:
    """
    Verify unexpected Windows text stubs fail packaging.

    :param templates_dir: Repository-root ``templates`` directory.
    :type templates_dir: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If the unexpected text stub is not rejected.

    Example::

        >>> assert_cpp_template_packaging_rejects_unexpected_windows_symlink_text_stub(repository_root() / 'templates')
    """
    with TemporaryDirectory() as source_td, TemporaryDirectory() as output_td:
        source_root = Path(source_td) / "templates"
        output_dir = Path(output_td)
        copy_templates_with_windows_symlink_text_stubs(
            templates_dir,
            source_root,
            ["c", "c_poll", "cpp", "cpp_poll"],
        )
        (source_root / "cpp" / "machine.c.j2").write_text(
            "../c_poll/machine.c.j2", encoding="utf-8"
        )

        try:
            package_templates(str(source_root), str(output_dir), verbose=False)
        except ValueError as err:
            # ValueError: tools.package_templates rejects unexpected checkout stub text.
            assert "expected checkout stub" in str(err)
        else:
            raise AssertionError("Unexpected C++ reuse text stub was accepted.")


def run_checks(repo_root: Path) -> None:
    """
    Run all template packaging maintenance checks.

    :param repo_root: Repository root path.
    :type repo_root: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If any maintenance contract fails.
    :raises OSError: If required repository files cannot be read.

    Example::

        >>> run_checks(repository_root())
    """
    templates_dir = repo_root / "templates"
    assert set(CURRENT_TEMPLATE_NAMES) <= set(repository_template_names(templates_dir))
    assert_packaging_output_preserves_metadata_and_archive_roots(templates_dir)
    assert_distribution_metadata_keeps_template_assets_declared(repo_root)
    assert_cpp_templates_reuse_c_core_as_packaged_file_payloads(templates_dir)
    assert_cpp_template_packaging_accepts_symlink_when_realpath_does_not_resolve(
        templates_dir
    )
    assert_cpp_template_packaging_resolves_windows_symlink_text_stubs(templates_dir)
    assert_cpp_template_packaging_rejects_unexpected_windows_symlink_text_stub(
        templates_dir
    )


def main(argv: Optional[List[str]] = None) -> None:
    """
    Run the command-line template packaging maintenance check.

    :param argv: Optional command-line argument list, defaults to ``None``.
    :type argv: List[str], optional
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If a maintenance contract fails.

    Example::

        >>> main([])  # doctest: +SKIP
    """
    parser = argparse.ArgumentParser(
        description="Validate repository-source built-in template packaging contracts."
    )
    parser.add_argument(
        "--repo-root",
        default=str(repository_root()),
        help="Repository root to check. Defaults to the parent of this tools directory.",
    )
    args = parser.parse_args(argv)
    run_checks(Path(args.repo_root).resolve())
    print("template packaging checks passed")


if __name__ == "__main__":
    main()
