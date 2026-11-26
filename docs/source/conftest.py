"""
Check the examples written in documentation pages against real runs.

A page shows an example exactly as the reader sees it, and this file makes
pytest run it and compare the real output with the output written in the page:

* ``.. code-block:: console`` is a terminal record. Each line that starts with
  ``$`` is a command, and the lines after it are what the command prints. All
  commands of one block run in one shell, so ``cd`` and ``$?`` behave as they do
  in a terminal.
* ``.. testcode::`` is a Python script, and the ``.. testoutput::`` after it is
  what the script prints.

``...`` in an output stands for text that is left out. A command that ends with
a non-zero exit status must be followed by ``$ echo $?``, so a page cannot show
a failing command as if it had succeeded. Every example of a page runs in one
throwaway copy of the page directory, so an example may use a file that an
earlier example of the same page wrote, and nothing is written into the
checkout.

Models that several pages use live in ``docs/source/_models``. Their files are
copied into the throwaway directory before the page's own files, so a page can
run ``pyfcstm simulate -i controller.fcstm`` whether the model is in its own
directory or in ``_models``. Commands find the ``pyfcstm`` of this checkout
through ``docs/source/_shims``, so nothing has to be installed first.

Run it with ``make docs_doctest``, or with ``pytest`` and the path of one page
directory, for example ``pytest docs/source/tutorials/regions``.
"""

import doctest
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest
from sybil import Sybil
from sybil.parsers.rest import CodeBlockParser
from sybil.parsers.rest.lexers import DirectiveLexer

_SOURCE = pathlib.Path(__file__).resolve().parent
_MARK = "@@end-of-documented-command@@"
_SCRIPT_OUTPUT = "output of the script that has no output block yet"


def _compare(what, expected, got):
    """
    Fail unless the real output matches the output written in the page.

    :param what: The command or script the output belongs to, for the message.
    :type what: str
    :param expected: The output written in the page; ``...`` matches any text.
    :type expected: str
    :param got: The output of the real run.
    :type got: str
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If the two outputs differ.
    """
    want = expected.rstrip() + "\n"
    got = "\n".join(line.rstrip() for line in got.splitlines()).rstrip() + "\n"
    if not doctest.OutputChecker().check_output(want, got, doctest.ELLIPSIS):
        raise AssertionError("%s\nThe page says:\n%s\nThe real output is:\n%s" % (what, want, got))


def _run_console_block(example):
    """
    Run the commands of one console block and compare what each one prints.

    :param example: The console block; ``example.parsed`` is its text.
    :type example: sybil.Example
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If an output differs, or a command fails and the
        page does not show its exit status.
    """
    commands = []  # pairs of [command, lines of its expected output]
    for line in example.parsed.splitlines():
        if commands and commands[-1][0].endswith("\\"):
            # A trailing backslash continues the command on the next line;
            # the shell joins the lines, exactly as it does for the reader.
            commands[-1][0] += "\n" + line
        elif line.startswith("$ "):
            commands.append([line[2:], []])
        elif commands:
            commands[-1][1].append(line)
    # After each command print a marker carrying its exit status, then restore
    # that status so that a following ``echo $?`` reports it.
    script = "".join(
        "%s\n__status=$?; printf '\\n%s %%s\\n' \"$__status\"; (exit \"$__status\")\n" % (command, _MARK)
        for command, _ in commands
    )
    done = subprocess.run(
        ["sh", "-c", script],
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    parts = re.split(r"\n%s (\d+)\n" % re.escape(_MARK), done.stdout)
    for index, (command, expected) in enumerate(commands):
        _compare("$ " + command, "\n".join(expected), parts[2 * index])
        status = int(parts[2 * index + 1])
        following = commands[index + 1][0] if index + 1 < len(commands) else None
        if status != 0 and following != "echo $?":
            raise AssertionError(
                "$ %s\nends with exit status %d; show it with '$ echo $?' on the next line." % (command, status)
            )


def _run_script(example):
    """
    Run one Python script of a page in its own interpreter and keep its output.

    :param example: The ``testcode`` block; ``example.parsed`` is the script.
    :type example: sybil.Example
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If the script before this one prints something that
        no output block checks, or if this script fails.
    """
    _require_no_pending_output(example.namespace)
    done = subprocess.run(
        [sys.executable, "-c", example.parsed],
        universal_newlines=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if done.returncode != 0:
        raise AssertionError(
            "The script ends with exit status %d. Its output:\n%s" % (done.returncode, done.stdout)
        )
    if done.stdout.strip():
        example.namespace[_SCRIPT_OUTPUT] = done.stdout


def _check_script_output(example):
    """
    Compare one output block with what the script before it printed.

    :param example: The ``testoutput`` block; ``example.parsed`` is its text.
    :type example: sybil.Example
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If the outputs differ, or no script precedes it.
    """
    if _SCRIPT_OUTPUT not in example.namespace:
        raise AssertionError("This output block has no script before it.")
    _compare("the script above this output block", example.parsed, example.namespace.pop(_SCRIPT_OUTPUT))


def _require_no_pending_output(namespace):
    """
    Fail when a script of the page was run and nothing compared its output.

    :param namespace: The values shared by the examples of one page.
    :type namespace: dict
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If a script has no output block after it.
    """
    if _SCRIPT_OUTPUT in namespace:
        raise AssertionError("A script has no output block after it, so nothing checks what it prints.")


def _scripts_and_outputs(document):
    """
    Find the scripts and the output blocks of one page.

    :param document: The page being checked.
    :type document: sybil.Document
    :return: The ``testcode`` and ``testoutput`` blocks, each with its check.
    :rtype: Iterable[sybil.Region]
    """
    for directive, evaluator in (("testcode", _run_script), ("testoutput", _check_script_output)):
        for region in DirectiveLexer(directive=directive)(document):
            region.parsed = region.lexemes["source"]
            region.evaluator = evaluator
            yield region


@pytest.fixture(scope="module")
def page_directory(request, tmp_path_factory):
    """
    Run all examples of one page inside a throwaway copy of its directory.

    The copy holds the shared models of ``_models`` and then the files of the
    page directory itself. While the page runs, the ``pyfcstm`` command and the
    ``pyfcstm`` package of this checkout are the ones that commands find.

    :param request: The pytest request; its path is the page being checked.
    :type request: pytest.FixtureRequest
    :param tmp_path_factory: The pytest factory of temporary directories.
    :type tmp_path_factory: pytest.TempPathFactory
    :return: The copy, which is the working directory while the page runs.
    :rtype: pathlib.Path
    """
    work = tmp_path_factory.mktemp("page") / "work"
    shutil.copytree(str(_SOURCE / "_models"), str(work))
    shutil.copytree(str(request.path.parent), str(work), dirs_exist_ok=True)
    patch = pytest.MonkeyPatch()
    patch.setenv("PATH", str(_SOURCE / "_shims") + os.pathsep + os.environ.get("PATH", ""))
    patch.setenv("PYTHONPATH", str(_SOURCE.parent.parent) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    patch.chdir(work)
    yield work
    patch.undo()


def pytest_configure(config):
    """
    Keep pytest's own doctest plugin away from the pages.

    That plugin treats any text file named on the command line as a doctest
    file and would run the ``>>>`` lines that a terminal record prints.

    :param config: The pytest configuration.
    :type config: pytest.Config
    :return: ``None``.
    :rtype: None
    """
    config.pluginmanager.set_blocked("doctest")


pytest_collect_file = Sybil(
    parsers=[
        _scripts_and_outputs,
        CodeBlockParser(language="console", evaluator=_run_console_block),
    ],
    patterns=["*.rst"],
    fixtures=["page_directory"],
    teardown=_require_no_pending_output,
).pytest()
