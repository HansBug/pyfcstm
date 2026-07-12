"""Validate build identity across direct and carried package artifacts.

This maintenance command exercises package lifecycle behavior that belongs
outside pytest: it builds a direct wheel from a clean clone, builds an sdist
and a wheel from its Git-free extraction, then verifies the installed version
bootstrap in fresh dependency-free virtual environments.
"""

import argparse
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from typing import Iterable, Sequence, Tuple


_REPO_ROOT = Path(__file__).resolve().parents[1]


def _run(command: Sequence[str], cwd: Path) -> subprocess.CompletedProcess:
    """Run one checker subprocess and raise with captured diagnostics on failure."""
    completed = subprocess.run(
        list(command),
        cwd=str(cwd),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(
            "command failed ({0}): {1}\nstdout:\n{2}\nstderr:\n{3}".format(
                completed.returncode,
                " ".join(command),
                completed.stdout,
                completed.stderr,
            )
        )
    return completed


def _require(condition: bool, message: str) -> None:
    """Raise a stable checker failure without relying on optimized assertions."""
    if not condition:
        raise RuntimeError(message)


def _single_path(paths: Iterable[Path], description: str) -> Path:
    """Return exactly one generated artifact path."""
    matches = list(paths)
    _require(
        len(matches) == 1, "expected one {0}, found {1!r}".format(description, matches)
    )
    return matches[0]


def _venv_paths(venv_dir: Path) -> Tuple[Path, Path]:
    """Return Python and console-script paths for the current host platform."""
    if os.name == "nt":
        scripts_dir = venv_dir / "Scripts"
        return scripts_dir / "python.exe", scripts_dir / "pyfcstm.exe"
    bin_dir = venv_dir / "bin"
    return bin_dir / "python", bin_dir / "pyfcstm"


def _make_venv(venv_dir: Path) -> Tuple[Path, Path]:
    """Create a fresh virtual environment without project dependencies."""
    _run((sys.executable, "-m", "venv", str(venv_dir)), venv_dir.parent)
    python, console = _venv_paths(venv_dir)
    _require(python.is_file(), "fresh virtual environment did not create Python")
    _require(
        console.parent.is_dir(), "fresh virtual environment has no scripts directory"
    )
    return python, console


def _install_and_verify(
    wheel: Path,
    venv_dir: Path,
    expected_commit: str,
    expected_source: str,
    working_dir: Path,
) -> None:
    """Install one wheel and verify the dependency-free version bootstrap."""
    python, console = _make_venv(venv_dir)
    _run(
        (
            str(python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--no-deps",
            str(wheel),
        ),
        working_dir,
    )
    no_click = subprocess.run(
        (str(python), "-I", "-c", "import click"),
        cwd=str(working_dir),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    _require(
        no_click.returncode != 0,
        "fresh version-bootstrap environment unexpectedly has click",
    )

    console_output = _run((str(console), "--version"), working_dir).stdout
    module_output = _run(
        (str(python), "-I", "-m", "pyfcstm", "--version"), working_dir
    ).stdout
    _require(
        console_output == module_output,
        "console and python -I -m version output differ\nconsole:\n{0}\nmodule:\n{1}".format(
            console_output, module_output
        ),
    )
    _require(
        "Commit: {0}".format(expected_commit) in console_output,
        "installed version output does not contain the expected full commit",
    )
    probe = _run(
        (
            str(python),
            "-I",
            "-c",
            "import pyfcstm; from pyfcstm.config import BUILD_SOURCE; "
            "print(pyfcstm.__file__); print(BUILD_SOURCE)",
        ),
        working_dir,
    ).stdout.splitlines()
    _require(len(probe) == 2, "installed identity probe returned unexpected output")
    package_file = Path(probe[0]).resolve()
    _require(
        venv_dir.resolve() in package_file.parents,
        "installed pyfcstm package did not resolve under the fresh virtual environment",
    )
    _require(
        probe[1] == expected_source,
        "installed identity source does not match expectation",
    )


def _build_wheel(source_dir: Path, output_dir: Path) -> Path:
    """Build one wheel through pip without resolving runtime dependencies."""
    output_dir.mkdir()
    _run(
        (
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--disable-pip-version-check",
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            str(output_dir),
            ".",
        ),
        source_dir,
    )
    return _single_path(output_dir.glob("pyfcstm-*.whl"), "wheel")


def _extract_sdist(sdist: Path, output_dir: Path) -> Path:
    """Extract one local sdist after rejecting unsafe archive member names."""
    with tarfile.open(str(sdist), "r:gz") as archive:
        members = archive.getmembers()
        _require(bool(members), "sdist archive is empty")
        for member in members:
            member_path = Path(member.name)
            _require(
                not member_path.is_absolute() and ".." not in member_path.parts,
                "sdist contains an unsafe member path: {0}".format(member.name),
            )
        root_name = Path(members[0].name).parts[0]
        archive.extractall(str(output_dir))
    extracted = output_dir / root_name
    _require(extracted.is_dir(), "sdist extraction root is missing")
    return extracted


def check_build_identity_packaging(repo_root: Path = _REPO_ROOT) -> None:
    """Validate direct-wheel and carried-sdist identity behavior from a clean clone."""
    resolved_root = repo_root.resolve()
    expected_commit = _run(
        ("git", "rev-parse", "--verify", "HEAD^{commit}"), resolved_root
    ).stdout.strip()
    _require(len(expected_commit) in (40, 64), "Git did not provide a full object ID")

    with tempfile.TemporaryDirectory(prefix="pyfcstm-build-identity-") as temporary:
        temporary_root = Path(temporary)
        clone_dir = temporary_root / "source"
        _run(
            ("git", "clone", "--no-local", str(resolved_root), str(clone_dir)),
            temporary_root,
        )

        direct_wheel = _build_wheel(clone_dir, temporary_root / "direct-wheel")
        _install_and_verify(
            direct_wheel,
            temporary_root / "direct-venv",
            expected_commit,
            "git",
            temporary_root,
        )

        sdist_dir = temporary_root / "sdist"
        sdist_dir.mkdir()
        _run(
            (sys.executable, "-m", "build", "--sdist", "--outdir", str(sdist_dir)),
            clone_dir,
        )
        sdist = _single_path(sdist_dir.glob("pyfcstm-*.tar.gz"), "sdist")
        extracted = _extract_sdist(sdist, temporary_root / "extracted")
        _require(
            not (extracted / ".git").exists(),
            "extracted sdist unexpectedly contains Git metadata",
        )
        carried_wheel = _build_wheel(extracted, temporary_root / "carried-wheel")
        _install_and_verify(
            carried_wheel,
            temporary_root / "carried-venv",
            expected_commit,
            "sdist-carried",
            temporary_root,
        )


def main(arguments: Sequence[str] = None) -> int:
    """Run the build-identity package lifecycle maintenance check."""
    parser = argparse.ArgumentParser(
        description="Validate direct-wheel and sdist-carried pyfcstm build identity."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run the complete build identity package lifecycle check.",
    )
    parser.add_argument(
        "--repo-root",
        default=str(_REPO_ROOT),
        help="Repository checkout to clone and validate.",
    )
    args = parser.parse_args(arguments)
    if not args.check:
        parser.error("--check is required")
    check_build_identity_packaging(Path(args.repo_root))
    print("build identity packaging check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
