import logging
import os.path

# ``importlib_metadata`` is the third-party backport; on Python 3.8+
# the stdlib ``importlib.metadata`` is equivalent. The build pipeline
# does not actually call ``list_installed_packages`` from get_resource_files
# (the call site is commented out below), but the top-level import used to
# be hard - if the backport was not installed, ``tools.resources`` failed
# to load entirely and ``generate_spec.collect_datas`` silently returned
# zero data files. That is exactly what made the PyInstaller exe ship
# without ``pyfcstm/template/*.zip`` and ``z3/lib/libz3.so``. Fall back
# to stdlib so the import chain is robust regardless of which environment
# the build runs in.
try:
    import importlib_metadata  # type: ignore
except ImportError:  # pragma: no cover - exercised on Python 3.8+ envs without the backport
    import importlib.metadata as importlib_metadata  # type: ignore
from hbutils.reflection import quick_import_object


def get_resources_from_package(package):
    try:
        path, _, _ = quick_import_object(f'{package}.__file__')
    except ImportError:
        logging.warning(f'Cannot check {package!r} directory, skipped.')
        return

    if os.path.splitext(os.path.basename(path))[0] != '__init__':  # single file package
        return
    root_dir = os.path.dirname(path)

    for root, _, files in os.walk(root_dir):
        for file in files:
            src_file = os.path.abspath(os.path.join(root, file))
            _, ext = os.path.splitext(os.path.basename(src_file))
            if not ext.startswith('.py'):
                yield src_file, os.path.relpath(os.path.dirname(src_file), os.path.dirname(os.path.abspath(root_dir)))


def list_installed_packages():
    installed_packages = importlib_metadata.distributions()
    for dist in installed_packages:
        yield dist.metadata['Name']


def list_resources():
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


def get_resources_from_mine():
    workdir = os.path.abspath('.')
    for rfile in list_resources():
        dst_file = os.path.dirname(os.path.relpath(rfile, workdir))
        yield rfile, dst_file


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
