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
import zipfile


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


def _package_one_template(source_dir, output_file, root_name):
    archived_files = []
    with zipfile.ZipFile(output_file, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [item for item in dirs if item != "__pycache__"]
            for file in sorted(files):
                src_file = os.path.join(root, file)
                rel_file = os.path.relpath(src_file, source_dir)
                arcname = os.path.join(root_name, rel_file)
                zf.write(src_file, arcname)
                archived_files.append((src_file, arcname))
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
