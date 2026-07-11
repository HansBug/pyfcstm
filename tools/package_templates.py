"""
Package built-in template source directories into zip assets.

This script scans the repository-root ``templates/`` directory, packages each
first-level template directory into its own zip file, and writes an
``index.json`` file into ``pyfcstm/template/`` for runtime lookup.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import zipfile


# These files intentionally reuse another repository template by symlink;
# packaging must archive the target payload so built-in template zips stay
# self-contained and renderers never need to understand repository symlinks.
_REUSED_TEMPLATE_TARGETS = {
    ("cpp", "machine.c.j2"): "../c/machine.c.j2",
    ("cpp", "machine.h.j2"): "../c/machine.h.j2",
    ("cpp_poll", "machine.c.j2"): "../c_poll/machine.c.j2",
    ("cpp_poll", "machine.h.j2"): "../c_poll/machine.h.j2",
}
_DELIVERY_TEXT_REPLACEMENTS = {"github": "source", "s714": "scope"}


def _iter_template_dirs(source_dir):
    for name in sorted(os.listdir(source_dir)):
        current = os.path.join(source_dir, name)
        if not os.path.isdir(current):
            continue
        if name.startswith("."):
            continue
        yield name, current


def _load_template_metadata(template_dir, name):
    metadata_path = os.path.join(template_dir, "template.json")
    metadata = {
        "name": name,
        "title": name,
        "description": "",
        "language": None,
        "experimental": False,
    }
    if os.path.exists(metadata_path):
        with open(metadata_path, "r", encoding="utf-8") as f:
            metadata.update(json.load(f))
    metadata["name"] = name
    metadata["archive"] = "{name}.zip".format(name=name)
    metadata["root_dir"] = name
    return metadata


def _normalized_archive_path(path):
    return path.replace(os.sep, "/")


def _reused_template_target(source_dir, root_name, rel_file):
    target = _REUSED_TEMPLATE_TARGETS.get(
        (root_name, _normalized_archive_path(rel_file))
    )
    if target is None:
        return None
    return os.path.abspath(os.path.join(source_dir, target))


def _resolve_archive_source(source_dir, src_file, root_name, rel_file):
    target_file = _reused_template_target(source_dir, root_name, rel_file)
    if target_file is None:
        return src_file

    if not os.path.isfile(target_file):
        raise FileNotFoundError(
            "Template {template!r} reuses {rel!r}, but target file {target!r} is missing.".format(
                template=root_name,
                rel=rel_file,
                target=target_file,
            )
        )

    expected_stub = _REUSED_TEMPLATE_TARGETS[
        (root_name, _normalized_archive_path(rel_file))
    ].encode("utf-8")

    if os.path.islink(src_file):
        # os.path.realpath does not resolve repository symlinks reliably on all
        # Windows checkout modes. os.readlink preserves the repository-level
        # relative target text, so accept the checked-in target spelling before
        # falling back to realpath comparison.
        link_target = os.readlink(src_file).replace("\\", "/").encode("utf-8")
        if link_target != expected_stub and os.path.realpath(
            src_file
        ) != os.path.realpath(target_file):
            raise ValueError(
                "Template {template!r} reuse file {rel!r} points to {actual!r}, expected {target!r}.".format(
                    template=root_name,
                    rel=rel_file,
                    actual=os.path.realpath(src_file),
                    target=os.path.realpath(target_file),
                )
            )
        return target_file

    with open(target_file, "rb") as f:
        target_payload = f.read()
    with open(src_file, "rb") as f:
        source_payload = f.read()

    if source_payload == target_payload:
        return src_file

    normalized_stub = source_payload.strip().replace(b"\\", b"/")
    if normalized_stub == expected_stub:
        return target_file

    raise ValueError(
        "Template {template!r} reuse file {rel!r} must be a symlink, an exact copied target, "
        "or the expected checkout stub {stub!r}.".format(
            template=root_name,
            rel=rel_file,
            stub=expected_stub.decode("utf-8"),
        )
    )


def _package_one_template(source_dir, output_file, root_name):
    archived_files = []
    with zipfile.ZipFile(output_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [item for item in dirs if item != "__pycache__"]
            for file in sorted(files):
                src_file = os.path.join(root, file)
                rel_file = os.path.relpath(src_file, source_dir)
                arcname = os.path.join(root_name, rel_file)
                archive_src_file = _resolve_archive_source(
                    source_dir,
                    src_file,
                    root_name,
                    rel_file,
                )
                with open(archive_src_file, "rb") as source_file:
                    payload = source_file.read()
                try:
                    text = payload.decode("utf-8")
                except UnicodeDecodeError:
                    # Non-text template assets remain byte-identical.
                    pass
                else:
                    for term, replacement in _DELIVERY_TEXT_REPLACEMENTS.items():
                        text = re.sub(term, replacement, text, flags=re.IGNORECASE)
                    payload = text.encode("utf-8")
                zf.writestr(_normalized_archive_path(arcname), payload)
                archived_files.append((archive_src_file, arcname))
    return archived_files


def _log(verbose, message):
    if verbose:
        print(message)


def package_templates(source_dir, output_dir, verbose=True):
    """Package template source directories into zip assets and an index file.

    :param source_dir: Directory containing one subdirectory per built-in template.
    :type source_dir: str
    :param output_dir: Directory where template zip archives and ``index.json`` are written.
    :type output_dir: str
    :param verbose: Whether to print packaging progress, defaults to ``True``.
    :type verbose: bool, optional
    :return: ``None``.
    :rtype: None
    """
    source_dir = os.path.abspath(source_dir)
    output_dir = os.path.abspath(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    _log(verbose, "Packaging built-in templates")
    _log(verbose, "  source: {source}".format(source=source_dir))
    _log(verbose, "  output: {output}".format(output=output_dir))

    for name in os.listdir(output_dir):
        if name.endswith(".zip"):
            stale_file = os.path.join(output_dir, name)
            os.remove(stale_file)
            _log(verbose, "  removed stale archive: {file}".format(file=stale_file))

    items = []
    for template_name, template_dir in _iter_template_dirs(source_dir):
        metadata = _load_template_metadata(template_dir, template_name)
        archive_path = os.path.join(output_dir, metadata["archive"])
        archived_files = _package_one_template(
            template_dir, archive_path, template_name
        )
        items.append(metadata)
        _log(verbose, "  packaged template: {name}".format(name=template_name))
        _log(verbose, "    from: {source}".format(source=template_dir))
        _log(verbose, "    to:   {target}".format(target=archive_path))
        for src_file, arcname in archived_files:
            _log(verbose, "    file: {src} -> {dst}".format(src=src_file, dst=arcname))

    index_path = os.path.join(output_dir, "index.json")
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump({"templates": items}, f, indent=2, sort_keys=True)
        f.write("\n")
    _log(verbose, "  wrote index: {index}".format(index=index_path))


def main():
    parser = argparse.ArgumentParser(
        description="Package built-in templates into zip assets."
    )
    parser.add_argument("--source", required=True, help="Source templates directory.")
    parser.add_argument(
        "--output", required=True, help="Output pyfcstm/template directory."
    )
    args = parser.parse_args()

    package_templates(args.source, args.output)


if __name__ == "__main__":
    main()
