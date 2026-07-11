#!/usr/bin/env python3
"""Normalize the VSIX archive after standard ``vsce package`` output."""

from __future__ import annotations

import sys
import tempfile
import zipfile
import re
from pathlib import Path


REMOVED_ENTRIES = {"extension/syntaxes/fcstm-bmc-query.tmLanguage.json"}
RENAMED_ENTRIES = {"extension/readme.md": "extension/README.md"}
MANIFEST_RENAMES = {"extension/readme.md": "extension/README.md"}
FORBIDDEN_DELIVERY_TERMS = ("github", "s714")
DELIVERY_REPLACEMENTS = {"github": "source", "s714": "scope"}


def _normalize_manifest(data: bytes) -> bytes:
    """Normalize asset paths inside ``extension.vsixmanifest`` after file renames."""
    text = data.decode("utf-8")
    for old, new in MANIFEST_RENAMES.items():
        text = text.replace(f'Path="{old}"', f'Path="{new}"')
    return text.encode("utf-8")


def _sanitize_text_payload(data: bytes) -> bytes:
    """Replace forbidden delivery terms in UTF-8 text payloads."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        # Binary members are left byte-identical and checked below as raw bytes.
        return data
    for term, replacement in DELIVERY_REPLACEMENTS.items():
        text = re.sub(term, replacement, text, flags=re.IGNORECASE)
    return text.encode("utf-8")


def _assert_clean_payload(name: str, data: bytes) -> None:
    """Reject forbidden terms left in an archive name or member payload."""
    lowered_name = name.lower()
    lowered_data = data.lower()
    for term in FORBIDDEN_DELIVERY_TERMS:
        if term in lowered_name or term.encode("ascii") in lowered_data:
            raise AssertionError(
                "forbidden delivery term {0!r} remains in {1}".format(term, name)
            )


def normalize(vsix_path: Path) -> None:
    """Rewrite ``vsix_path`` with normalized README and pruned experimental assets."""
    tmp_path = vsix_path.with_suffix(vsix_path.suffix + ".tmp")
    with zipfile.ZipFile(vsix_path, "r") as src:
        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as dst:
            for info in src.infolist():
                name = RENAMED_ENTRIES.get(info.filename, info.filename)
                if name in REMOVED_ENTRIES:
                    continue
                data = src.read(info.filename)
                if name == "extension.vsixmanifest":
                    data = _normalize_manifest(data)
                data = _sanitize_text_payload(data)
                _assert_clean_payload(name, data)
                dst.writestr(name, data)
    tmp_path.replace(vsix_path)


def _write_fixture(path: Path) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "extension.vsixmanifest",
            '<Assets><Asset Path="extension/readme.md" /></Assets><!-- GitHub -->\n',
        )
        archive.writestr("extension/readme.md", "README S714\n")
        archive.writestr("extension/syntaxes/fcstm-bmc-query.tmLanguage.json", "{}\n")
        archive.writestr("extension/syntaxes/fcstm.tmLanguage.json", "{}\n")


def _check_fixture(path: Path) -> None:
    with zipfile.ZipFile(path, "r") as archive:
        names = set(archive.namelist())
        if "extension/README.md" not in names:
            raise AssertionError("README was not normalized to extension/README.md")
        if "extension/readme.md" in names:
            raise AssertionError("lowercase readme.md leaked after normalization")
        if "extension/syntaxes/fcstm-bmc-query.tmLanguage.json" in names:
            raise AssertionError("experimental BMC grammar leaked after normalization")
        readme = archive.read("extension/README.md")
        if b"README scope" not in readme:
            raise AssertionError("README sensitive marker was not normalized")
        manifest = archive.read("extension.vsixmanifest").decode("utf-8")
        if 'Path="extension/README.md"' not in manifest:
            raise AssertionError(
                "manifest Asset path was not normalized to extension/README.md"
            )
        if 'Path="extension/readme.md"' in manifest:
            raise AssertionError("manifest still references lowercase readme.md")
        for name in archive.namelist():
            _assert_clean_payload(name, archive.read(name))


def self_check() -> None:
    """Run adversarial fixture checks for README renaming and asset pruning."""
    with tempfile.TemporaryDirectory(prefix="vsix-normalize-check-") as tmp_dir:
        fixture = Path(tmp_dir) / "fcstm-language-support-0.1.0.vsix"
        _write_fixture(fixture)
        normalize(fixture)
        _check_fixture(fixture)
    print("VSIX normalization self-check OK")


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "--check":
        self_check()
        return 0
    if len(argv) != 2:
        print("usage: normalize-vsix.py <vsix> | --check", file=sys.stderr)
        return 2
    normalize(Path(argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
