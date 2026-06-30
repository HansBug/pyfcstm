"""
Validate source-install access to packaged built-in templates.

This maintenance command checks the source-install smoke path that is
intentionally outside the pytest unit-test boundary. It installs the current
checkout into a temporary target directory without dependencies, runs a probe
outside the checkout, and verifies that :func:`pyfcstm.template.extract_template`
can still extract a packaged built-in template.

Example::

    $ python tools/check_template_source_install.py
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Optional


def repository_root() -> Path:
    """
    Return the repository root for this maintenance command.

    :return: Repository root path.
    :rtype: pathlib.Path

    Example::

        >>> repository_root().name  # doctest: +SKIP
        'pyfcstm'
    """
    return Path(__file__).resolve().parents[1]


def install_checkout(repo_root: Path, install_dir: Path) -> None:
    """
    Install the checkout into ``install_dir`` without dependencies.

    :param repo_root: Repository root path.
    :type repo_root: pathlib.Path
    :param install_dir: Target directory for ``pip install --target``.
    :type install_dir: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises subprocess.CalledProcessError: If pip installation fails.

    Example::

        >>> with TemporaryDirectory() as td:  # doctest: +SKIP
        ...     install_checkout(repository_root(), Path(td) / 'install')
    """
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--quiet",
        "--no-deps",
        "--target",
        str(install_dir),
        ".",
    ]
    subprocess.run(command, cwd=str(repo_root), check=True)


def probe_environment(install_dir: Path) -> Dict[str, str]:
    """
    Build the environment for the installed-template probe.

    :param install_dir: Directory containing the installed checkout package.
    :type install_dir: pathlib.Path
    :return: Environment mapping for :func:`subprocess.run`.
    :rtype: Dict[str, str]

    Example::

        >>> 'PYTHONPATH' in probe_environment(Path('/tmp/install'))
        True
    """
    return {
        **os.environ,
        "PYTHONPATH": str(install_dir),
    }


def run_extract_probe(build_root: Path, install_dir: Path) -> None:
    """
    Run the installed-package built-in template extraction probe.

    :param build_root: Temporary working directory outside the checkout.
    :type build_root: pathlib.Path
    :param install_dir: Directory containing the installed checkout package.
    :type install_dir: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises subprocess.CalledProcessError: If the probe fails.
    :raises AssertionError: If the probe output is not ``ok``.

    Example::

        >>> with TemporaryDirectory() as td:  # doctest: +SKIP
        ...     run_extract_probe(Path(td), Path(td) / 'install')
    """
    probe_code = (
        "import os\n"
        "from tempfile import TemporaryDirectory\n"
        "from pyfcstm.template import extract_template\n"
        "with TemporaryDirectory() as td:\n"
        "    path = extract_template('python', td)\n"
        "    assert os.path.basename(path) == 'python', path\n"
        "    assert os.path.isfile(os.path.join(path, 'config.yaml')), path\n"
        "    assert os.path.isfile(os.path.join(path, 'machine.py.j2')), path\n"
        "    print('ok')\n"
    )
    probe = subprocess.run(
        [sys.executable, "-c", probe_code],
        cwd=str(build_root),
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=probe_environment(install_dir),
    )
    assert probe.stdout.strip() == "ok"


def run_check(repo_root: Path) -> None:
    """
    Run the source-install built-in template extraction smoke check.

    :param repo_root: Repository root path.
    :type repo_root: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises subprocess.CalledProcessError: If installation or probing fails.
    :raises AssertionError: If the probe output is unexpected.

    Example::

        >>> run_check(repository_root())  # doctest: +SKIP
    """
    with TemporaryDirectory() as build_td:
        build_root = Path(build_td)
        install_dir = build_root / "install"
        install_checkout(repo_root, install_dir)
        run_extract_probe(build_root, install_dir)


def main(argv: Optional[List[str]] = None) -> None:
    """
    Run the command-line source-install template extraction check.

    :param argv: Optional command-line argument list, defaults to ``None``.
    :type argv: List[str], optional
    :return: ``None``.
    :rtype: None
    :raises subprocess.CalledProcessError: If installation or probing fails.

    Example::

        >>> main([])  # doctest: +SKIP
    """
    parser = argparse.ArgumentParser(
        description="Validate source-install built-in template extraction."
    )
    parser.add_argument(
        "--repo-root",
        default=str(repository_root()),
        help="Repository root to install. Defaults to the parent of this tools directory.",
    )
    args = parser.parse_args(argv)
    run_check(Path(args.repo_root).resolve())
    print("template source-install check passed")


if __name__ == "__main__":
    main()
