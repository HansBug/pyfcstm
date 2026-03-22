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
        if name.startswith('.'):
            continue
        yield name, current


def _load_template_metadata(template_dir, name):
    metadata_path = os.path.join(template_dir, 'template.json')
    metadata = {
        'name': name,
        'title': name,
        'description': '',
        'language': None,
        'experimental': False,
    }
    if os.path.exists(metadata_path):
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata.update(json.load(f))
    metadata['name'] = name
    metadata['archive'] = '{name}.zip'.format(name=name)
    metadata['root_dir'] = name
    return metadata


def _package_one_template(source_dir, output_file, root_name):
    archived_files = []
    with zipfile.ZipFile(output_file, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [item for item in dirs if item != '__pycache__']
            for file in sorted(files):
                src_file = os.path.join(root, file)
                rel_file = os.path.relpath(src_file, source_dir)
                arcname = os.path.join(root_name, rel_file)
                zf.write(src_file, arcname)
                archived_files.append((src_file, arcname))
    return archived_files


def main():
    parser = argparse.ArgumentParser(description='Package built-in templates into zip assets.')
    parser.add_argument('--source', required=True, help='Source templates directory.')
    parser.add_argument('--output', required=True, help='Output pyfcstm/template directory.')
    args = parser.parse_args()

    source_dir = os.path.abspath(args.source)
    output_dir = os.path.abspath(args.output)
    os.makedirs(output_dir, exist_ok=True)

    print('Packaging built-in templates')
    print('  source: {source}'.format(source=source_dir))
    print('  output: {output}'.format(output=output_dir))

    for name in os.listdir(output_dir):
        if name.endswith('.zip'):
            stale_file = os.path.join(output_dir, name)
            os.remove(stale_file)
            print('  removed stale archive: {file}'.format(file=stale_file))

    items = []
    for template_name, template_dir in _iter_template_dirs(source_dir):
        metadata = _load_template_metadata(template_dir, template_name)
        archive_path = os.path.join(output_dir, metadata['archive'])
        archived_files = _package_one_template(template_dir, archive_path, template_name)
        items.append(metadata)
        print('  packaged template: {name}'.format(name=template_name))
        print('    from: {source}'.format(source=template_dir))
        print('    to:   {target}'.format(target=archive_path))
        for src_file, arcname in archived_files:
            print('    file: {src} -> {dst}'.format(src=src_file, dst=arcname))

    index_path = os.path.join(output_dir, 'index.json')
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump({'templates': items}, f, indent=2, sort_keys=True)
        f.write('\n')
    print('  wrote index: {index}'.format(index=index_path))


if __name__ == '__main__':
    main()
