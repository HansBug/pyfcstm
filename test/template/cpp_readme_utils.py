"""Validate generated C++ README command snippets.

This module contains small pytest helpers used by the ``cpp`` and
``cpp_poll`` template tests. The helpers execute direct shell command blocks
from generated README files against the generated artifacts, so documentation
examples stay aligned with the actual wrapper build surface.

The module contains:

* :func:`run_readme_command_block` - Execute one generated README direct-build
  command block and run the produced test program.

Example::

    >>> callable(run_readme_command_block)
    True
"""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest


def run_readme_command_block(artifacts, stem, source_code, command_block):
    """Compile and run a generated C++ README direct-build command block.

    :param artifacts: Rendered template artifact mapping.
    :type artifacts: dict
    :param stem: Unique test stem used for diagnostics.
    :type stem: str
    :param source_code: C++ consumer source to save as ``app.cpp``.
    :type source_code: str
    :param command_block: Newline-separated README shell commands.
    :type command_block: str
    :return: Completed process from executing the built ``app`` program.
    :rtype: subprocess.CompletedProcess

    Example::

        >>> run_readme_command_block
        <function run_readme_command_block at ...>
    """
    if os.name == "nt":
        pytest.skip("README direct gcc/clang command snippets are POSIX-style.")

    output_dir = Path(artifacts["output_dir"])
    (output_dir / "app.cpp").write_text(source_code, encoding="utf-8")
    for name in ["machine.o", "machine_cpp.o", "app.o", "app"]:
        path = output_dir / name
        if path.exists():
            path.unlink()

    commands = [
        shlex.split(line) for line in command_block.strip().splitlines() if line.strip()
    ]
    for command in commands:
        executable = command[0]
        if shutil.which(executable) is None:
            pytest.skip(
                "{executable} is required for {stem} README direct command validation.".format(
                    executable=executable,
                    stem=stem,
                )
            )
        result = subprocess.run(
            command,
            cwd=str(output_dir),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(
                "README direct command failed for {stem}.\n"
                "command: {command}\n"
                "stdout:\n{stdout}\n"
                "stderr:\n{stderr}".format(
                    stem=stem,
                    command=" ".join(command),
                    stdout=result.stdout,
                    stderr=result.stderr,
                )
            )

    app_path = output_dir / "app"
    assert app_path.is_file(), "README commands for {stem} did not create app.".format(
        stem=stem,
    )
    return subprocess.run(
        [str(app_path)],
        cwd=str(output_dir),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
