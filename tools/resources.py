import os.path
import sys

if sys.version_info >= (3, 8):
    from importlib import metadata as importlib_metadata
else:  # pragma: no cover - exercised by the Python 3.7 build matrix.
    import importlib_metadata
from hbutils.reflection import quick_import_object


class ResourceCollectionError(RuntimeError):
    """Raised when a required build resource cannot be enumerated."""


def _collection_error(stage, path, error):
    """Create a resource error carrying the failing stage and path."""
    location = " at {!s}".format(path) if path is not None else ""
    return ResourceCollectionError(
        "resource collection failed during {}{}: {}: {}".format(
            stage, location, type(error).__name__, error
        )
    )


def get_resources_from_package(package):
    try:
        path, _, _ = quick_import_object(f'{package}.__file__')
    except (ImportError, OSError, ValueError) as err:
        # ImportError means no importable resource root; OSError/ValueError
        # represent filesystem/path failures from the reflection helper.
        raise _collection_error('package import', package, err) from err

    if os.path.splitext(os.path.basename(path))[0] != '__init__':  # single file package
        return
    root_dir = os.path.dirname(path)

    try:
        for root, _, files in os.walk(root_dir):
            for file in files:
                src_file = os.path.abspath(os.path.join(root, file))
                _, ext = os.path.splitext(os.path.basename(src_file))
                if not ext.startswith('.py'):
                    yield src_file, os.path.relpath(os.path.dirname(src_file), os.path.dirname(os.path.abspath(root_dir)))
    except (OSError, ValueError) as err:
        # OSError covers inaccessible/disappearing package files; ValueError
        # covers malformed paths returned by a platform filesystem adapter.
        raise _collection_error('package walk', root_dir, err) from err


def list_installed_packages():
    installed_packages = importlib_metadata.distributions()
    for dist in installed_packages:
        yield dist.metadata['Name']


def list_resources():
    proj_dir = None
    try:
        from pyfcstm import __file__ as _mine_file

        proj_dir = os.path.abspath(os.path.normpath(os.path.join(_mine_file, '..')))
        for root, _, files in os.walk(proj_dir):
            if '__pycache__' in root:
                continue

            for file in files:
                _, ext = os.path.splitext(file)
                if ext != '.py':
                    rfile = os.path.abspath(os.path.join(root, file))
                    yield rfile
    except (ImportError, OSError, ValueError) as err:
        # ImportError means the first-party package is unavailable; OSError
        # covers inaccessible/disappearing files; ValueError covers malformed
        # paths returned by a platform filesystem adapter.
        raise _collection_error('project walk', proj_dir, err) from err


def get_resources_from_mine():
    workdir = os.path.abspath('.')
    try:
        for rfile in list_resources():
            dst_file = os.path.dirname(os.path.relpath(rfile, workdir))
            yield rfile, dst_file
    except (OSError, ValueError) as err:
        # ValueError/OSError may originate from relative-path calculations or
        # the underlying resource iterator and must fail the build closed.
        raise _collection_error('destination mapping', workdir, err) from err


def get_resource_files():
    # Collect project's own resource files and z3 library resources
    yield from get_resources_from_mine()
    # Include z3 library resources for constraint solving
    yield from get_resources_from_package('z3')
    # for pack_name in list_installed_packages():
    #     yield from get_resource_files_from_package(pack_name)


def print_resource_mappings():
    for rfile, dst_file in get_resource_files():
        t = f'{rfile}{os.pathsep}{dst_file}'
        print(f'--add-data {t!r}')


if __name__ == '__main__':
    # print(list_installed_packages())
    print_resource_mappings()
