import glob
import os
import os.path
import pathlib
from typing import Iterator, Optional

from pyfcstm.utils import is_binary_file


def walk_files(directory: str, pattern: Optional[str] = None, ) -> Iterator[str]:
    """
    Recursively walk through a directory and yield relative paths of all files.

    This function takes a directory path and a pattern to search for files. It uses the `glob`
    module to find all files that match the specified pattern within the directory and its
    subdirectories. The yielded paths are relative to the specified directory.

    :param directory: The root directory to start walking.
    :type directory: str
    :param pattern: The pattern to match files against, defaults to ``**/*`` which matches all files.
    :type pattern: str

    :return: An iterator that yields relative paths of all files in the directory.
    :rtype: Iterator[str]

    :example:

    >>> for file in walk_files('/path/to/directory'):
    ...     print(file)
    """
    for path in glob.glob(os.path.abspath(os.path.join(directory, pattern or os.path.join('**', '*'))), recursive=True):
        if os.path.isfile(path):
            yield os.path.relpath(path, start=os.path.abspath(directory))


def file_compare(file1, file2):
    file1_type = 'binary' if is_binary_file(file1) else 'text'
    file2_type = 'binary' if is_binary_file(file2) else 'text'
    if file1_type != file2_type:
        assert False, f'{file1!r} is {file1_type}, but {file2!r} is {file2_type}.'

    if file1_type == 'text':
        assert pathlib.Path(file1).read_text(encoding='utf-8').splitlines(keepends=False) == \
               pathlib.Path(file2).read_text(encoding='utf-8').splitlines(keepends=False)
    else:
        assert pathlib.Path(file1).read_bytes() == pathlib.Path(file2).read_bytes()


def dir_compare(dir1, dir2):
    files1 = sorted(walk_files(dir1))
    files2 = sorted(walk_files(dir2))
    assert files1 == files2, f'File list of {dir1!r}:\n{files1!r}\n\nFile list of {dir2!r}:\n{files2}'

    for file in files1:
        file_compare(os.path.join(dir1, file), os.path.join(dir2, file))
