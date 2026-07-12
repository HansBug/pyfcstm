"""
Build identity generation and validation helpers.

This module owns the standard-library-only contract for the generated
``build_info.py`` data file. The generated file is deliberately parsed as a
strict Python-literal data format instead of imported, so a damaged artifact
cannot execute code while :mod:`pyfcstm.config` is imported.

The public package namespace exposes the parsed values through
:mod:`pyfcstm.config`; this private module is shared by the build hook and the
``tools.write_build_info`` maintenance command.
"""

import ast
import codecs
import errno
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Sequence


BUILD_INFO_FIELDS = (
    "BUILD_COMMIT",
    "BUILD_COMMIT_ALGORITHM",
    "BUILD_COMMIT_SHORT",
    "BUILD_DIRTY",
    "BUILD_REVISION",
    "BUILD_REVISION_SHORT",
    "BUILD_REF",
    "BUILD_TIME_UTC",
    "BUILD_SOURCE",
)
BUILD_SOURCES = frozenset(("git", "ci-override", "sdist-carried", "unknown"))
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_TIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_GIT_TIMEOUT_SECONDS = 30


class BuildInfoDataError(ValueError):
    """Raised when generated build identity data violates its schema."""


@dataclass(frozen=True)
class BuildIdentity:
    """Validated build identity values stored in ``build_info.py``."""

    commit: Optional[str]
    algorithm: Optional[str]
    commit_short: Optional[str]
    dirty: Optional[bool]
    revision: Optional[str]
    revision_short: Optional[str]
    ref: Optional[str]
    time_utc: Optional[str]
    source: Optional[str]

    @classmethod
    def unknown(cls) -> "BuildIdentity":
        """Return the explicit no-identity development state."""
        return cls(None, None, None, None, None, None, None, None, "unknown")

    def with_source(self, source: str) -> "BuildIdentity":
        """Return this identity with a validated build-time source label."""
        return BuildIdentity(
            self.commit,
            self.algorithm,
            self.commit_short,
            self.dirty,
            self.revision,
            self.revision_short,
            self.ref,
            self.time_utc,
            source,
        )

    def values(self) -> Dict[str, object]:
        """Return generated-module field names mapped to literal values."""
        return {
            "BUILD_COMMIT": self.commit,
            "BUILD_COMMIT_ALGORITHM": self.algorithm,
            "BUILD_COMMIT_SHORT": self.commit_short,
            "BUILD_DIRTY": self.dirty,
            "BUILD_REVISION": self.revision,
            "BUILD_REVISION_SHORT": self.revision_short,
            "BUILD_REF": self.ref,
            "BUILD_TIME_UTC": self.time_utc,
            "BUILD_SOURCE": self.source,
        }


def _require_string_or_none(name: str, value: object) -> Optional[str]:
    if value is None or type(value) is str:
        return value  # type: ignore[return-value]
    raise BuildInfoDataError("{} must be str or None".format(name))


def _require_bool_or_none(name: str, value: object) -> Optional[bool]:
    if value is None or type(value) is bool:
        return value  # type: ignore[return-value]
    raise BuildInfoDataError("{} must be bool or None".format(name))


def _validate_commit(commit: Optional[str], algorithm: Optional[str]) -> None:
    if commit is None:
        if algorithm is not None:
            raise BuildInfoDataError("BUILD_COMMIT_ALGORITHM requires BUILD_COMMIT")
        return
    if not _COMMIT_PATTERN.fullmatch(commit):
        raise BuildInfoDataError(
            "BUILD_COMMIT must be a 40 or 64 character lowercase hex object ID"
        )
    expected_algorithm = "sha1" if len(commit) == 40 else "sha256"
    if algorithm != expected_algorithm:
        raise BuildInfoDataError(
            "BUILD_COMMIT_ALGORITHM must be {} for this BUILD_COMMIT".format(
                expected_algorithm
            )
        )


def _validate_identity_values(values: Dict[str, object]) -> BuildIdentity:
    if set(values) != set(BUILD_INFO_FIELDS):
        missing = sorted(set(BUILD_INFO_FIELDS) - set(values))
        extra = sorted(set(values) - set(BUILD_INFO_FIELDS))
        raise BuildInfoDataError(
            "build info schema mismatch: missing={!r}, extra={!r}".format(
                missing, extra
            )
        )

    commit = _require_string_or_none("BUILD_COMMIT", values["BUILD_COMMIT"])
    algorithm = _require_string_or_none(
        "BUILD_COMMIT_ALGORITHM", values["BUILD_COMMIT_ALGORITHM"]
    )
    commit_short = _require_string_or_none(
        "BUILD_COMMIT_SHORT", values["BUILD_COMMIT_SHORT"]
    )
    dirty = _require_bool_or_none("BUILD_DIRTY", values["BUILD_DIRTY"])
    revision = _require_string_or_none("BUILD_REVISION", values["BUILD_REVISION"])
    revision_short = _require_string_or_none(
        "BUILD_REVISION_SHORT", values["BUILD_REVISION_SHORT"]
    )
    ref = _require_string_or_none("BUILD_REF", values["BUILD_REF"])
    time_utc = _require_string_or_none("BUILD_TIME_UTC", values["BUILD_TIME_UTC"])
    source = _require_string_or_none("BUILD_SOURCE", values["BUILD_SOURCE"])

    if algorithm not in (None, "sha1", "sha256"):
        raise BuildInfoDataError("BUILD_COMMIT_ALGORITHM must be sha1, sha256, or None")
    if source not in BUILD_SOURCES and source is not None:
        raise BuildInfoDataError("BUILD_SOURCE is not a recognized build-time source")
    _validate_commit(commit, algorithm)

    if commit is None:
        derived_values = (commit_short, dirty, revision, revision_short, ref, time_utc)
        if any(value is not None for value in derived_values):
            raise BuildInfoDataError(
                "BUILD_COMMIT is required when identity fields are populated"
            )
        if source not in (None, "unknown"):
            raise BuildInfoDataError(
                "BUILD_SOURCE requires BUILD_COMMIT unless it is unknown"
            )
        return BuildIdentity(None, None, None, None, None, None, None, None, source)

    if dirty is None:
        raise BuildInfoDataError("BUILD_DIRTY is required with BUILD_COMMIT")
    if source not in ("git", "ci-override", "sdist-carried"):
        raise BuildInfoDataError("BUILD_SOURCE must identify a known commit source")
    if commit_short != commit[:12]:
        raise BuildInfoDataError(
            "BUILD_COMMIT_SHORT must be the first 12 commit characters"
        )
    expected_revision = commit + ("-dirty" if dirty else "")
    expected_revision_short = commit[:12] + ("-dirty" if dirty else "")
    if revision != expected_revision:
        raise BuildInfoDataError(
            "BUILD_REVISION does not match BUILD_COMMIT and BUILD_DIRTY"
        )
    if revision_short != expected_revision_short:
        raise BuildInfoDataError(
            "BUILD_REVISION_SHORT does not match BUILD_COMMIT and BUILD_DIRTY"
        )
    if time_utc is None or not _TIME_PATTERN.fullmatch(time_utc):
        raise BuildInfoDataError("BUILD_TIME_UTC must be a UTC timestamp ending in Z")
    try:
        datetime.strptime(time_utc, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as err:
        raise BuildInfoDataError("BUILD_TIME_UTC is not a valid UTC timestamp") from err
    if ref is not None and ("\n" in ref or "\r" in ref):
        raise BuildInfoDataError("BUILD_REF must not contain line breaks")
    return BuildIdentity(
        commit,
        algorithm,
        commit_short,
        dirty,
        revision,
        revision_short,
        ref,
        time_utc,
        source,
    )


def load_build_identity_file(path: os.PathLike) -> BuildIdentity:
    """Load strict literal identity data without importing the generated module."""
    raw = Path(path).read_bytes()
    if raw.startswith(codecs.BOM_UTF8):
        raise BuildInfoDataError("build info must not start with a UTF-8 BOM")
    if b"\x00" in raw:
        raise BuildInfoDataError("build info must not contain NUL bytes")
    try:
        source = raw.decode("utf-8")
    except UnicodeDecodeError as err:
        raise BuildInfoDataError(
            "build info is not valid UTF-8: {}".format(err)
        ) from err
    try:
        tree = ast.parse(source, filename=str(path), mode="exec")
    except SyntaxError as err:
        raise BuildInfoDataError("build info syntax error: {}".format(err)) from err

    values = {}  # type: Dict[str, object]
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            raise BuildInfoDataError("build info permits only single-name assignments")
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in BUILD_INFO_FIELDS:
            raise BuildInfoDataError("build info contains an unknown field")
        if target.id in values:
            raise BuildInfoDataError("build info contains a duplicate field")
        try:
            values[target.id] = ast.literal_eval(node.value)
        except (ValueError, TypeError) as err:
            raise BuildInfoDataError(
                "build info field {} is not a literal".format(target.id)
            ) from err
    return _validate_identity_values(values)


def _run_git(args: Sequence[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + list(args),
        cwd=str(cwd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        encoding="utf-8",
        errors="replace",
        timeout=_GIT_TIMEOUT_SECONDS,
        check=False,
    )


def _git_value(
    args: Sequence[str], cwd: Path, allow_failure: bool = False
) -> Optional[str]:
    result = _run_git(args, cwd)
    if result.returncode:
        if allow_failure:
            return None
        raise BuildInfoDataError(
            "git {} failed ({}): {}".format(
                " ".join(args), result.returncode, result.stderr.strip()
            )
        )
    return result.stdout.strip()


def _read_live_git_identity(cwd: Path, now: datetime) -> Optional[BuildIdentity]:
    if not _has_git_metadata(cwd):
        return None
    try:
        result = _run_git(("rev-parse", "--verify", "HEAD^{commit}"), cwd)
    except OSError as err:
        # FileNotFoundError: the Git executable is unavailable in a source
        # checkout that may still legitimately carry an identity file.
        if err.errno == errno.ENOENT:
            return None
        raise
    if result.returncode:
        return None
    commit = result.stdout.strip()
    commit = commit.lower()
    if not _COMMIT_PATTERN.fullmatch(commit):
        raise BuildInfoDataError("git returned an invalid commit object ID")
    algorithm = "sha1" if len(commit) == 40 else "sha256"
    reported_algorithm = _git_value(
        ("rev-parse", "--show-object-format"), cwd, allow_failure=True
    )
    if reported_algorithm in ("sha1", "sha256") and reported_algorithm != algorithm:
        raise BuildInfoDataError(
            "git object format does not match commit object ID length"
        )
    dirty = bool(_git_value(("status", "--porcelain", "--untracked-files=normal"), cwd))
    ref = _git_value(
        ("symbolic-ref", "--quiet", "--short", "HEAD"), cwd, allow_failure=True
    )
    timestamp = (
        now.astimezone(timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    return BuildIdentity(
        commit,
        algorithm,
        commit[:12],
        dirty,
        commit + ("-dirty" if dirty else ""),
        commit[:12] + ("-dirty" if dirty else ""),
        ref or None,
        timestamp,
        "git",
    )


def _parse_ci_dirty(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in ("1", "true"):
        return True
    if normalized in ("0", "false"):
        return False
    raise BuildInfoDataError("PYFCSTM_BUILD_DIRTY must be one of 0, 1, false, or true")


def _resolve_timestamp(
    environment: Dict[str, str], now: Optional[datetime]
) -> datetime:
    epoch = environment.get("SOURCE_DATE_EPOCH")
    if epoch is None:
        return now or datetime.now(timezone.utc)
    try:
        seconds = int(epoch)
    except ValueError as err:
        raise BuildInfoDataError("SOURCE_DATE_EPOCH must be an integer") from err
    if seconds < 0:
        raise BuildInfoDataError("SOURCE_DATE_EPOCH must not be negative")
    try:
        return datetime.fromtimestamp(seconds, timezone.utc)
    except (OverflowError, OSError, ValueError) as err:
        raise BuildInfoDataError(
            "SOURCE_DATE_EPOCH is outside the supported UTC range"
        ) from err


def _identity_from_commit(
    commit: str,
    dirty: bool,
    ref: Optional[str],
    now: datetime,
    source: str,
) -> BuildIdentity:
    commit = commit.lower()
    if not _COMMIT_PATTERN.fullmatch(commit):
        raise BuildInfoDataError(
            "build commit must be a 40 or 64 character lowercase hex object ID"
        )
    algorithm = "sha1" if len(commit) == 40 else "sha256"
    timestamp = (
        now.astimezone(timezone.utc)
        .replace(microsecond=0)
        .strftime("%Y-%m-%dT%H:%M:%SZ")
    )
    return BuildIdentity(
        commit,
        algorithm,
        commit[:12],
        dirty,
        commit + ("-dirty" if dirty else ""),
        commit[:12] + ("-dirty" if dirty else ""),
        ref,
        timestamp,
        source,
    )


def ensure_build_identity(
    output_path: os.PathLike,
    cwd: Optional[os.PathLike] = None,
    environment: Optional[Dict[str, str]] = None,
    require_commit: bool = False,
    require_clean: bool = False,
    now: Optional[datetime] = None,
) -> BuildIdentity:
    """Resolve and atomically write build identity for a build lifecycle step."""
    output = Path(output_path)
    build_cwd = Path(cwd) if cwd is not None else Path.cwd()
    env = dict(os.environ if environment is None else environment)
    resolved_now = _resolve_timestamp(env, now)

    live_identity = _read_live_git_identity(build_cwd, resolved_now)
    ci_commit = env.get("PYFCSTM_BUILD_COMMIT")
    if ci_commit is not None:
        ci_dirty = _parse_ci_dirty(env.get("PYFCSTM_BUILD_DIRTY", "false"))
        ci_identity = _identity_from_commit(
            ci_commit,
            ci_dirty,
            env.get("PYFCSTM_BUILD_REF") or None,
            resolved_now,
            "ci-override",
        )
        if live_identity is not None and ci_identity.commit != live_identity.commit:
            raise BuildInfoDataError(
                "PYFCSTM_BUILD_COMMIT does not match live Git HEAD"
            )
        if live_identity is not None and ci_identity.dirty != live_identity.dirty:
            raise BuildInfoDataError(
                "PYFCSTM_BUILD_DIRTY does not match live Git status"
            )
        identity = ci_identity
    elif live_identity is not None:
        identity = live_identity
    elif output.exists():
        identity = load_build_identity_file(output)
        if identity.commit is not None:
            identity = identity.with_source("sdist-carried")
    else:
        identity = BuildIdentity.unknown()

    if require_commit and identity.commit is None:
        raise BuildInfoDataError("a build commit is required but unavailable")
    if require_clean and identity.dirty is not False:
        raise BuildInfoDataError("a clean build is required")
    write_build_identity_file(output, identity)
    return identity


def write_build_identity_file(path: os.PathLike, identity: BuildIdentity) -> None:
    """Atomically write a strict generated build identity data file."""
    _validate_identity_values(identity.values())
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Generated by tools.write_build_info. Do not edit.", ""]
    for field in BUILD_INFO_FIELDS:
        lines.append("{} = {}".format(field, ascii(identity.values()[field])))
    payload = ("\n".join(lines) + "\n").encode("ascii")

    fd, temporary_name = tempfile.mkstemp(
        prefix=".build_info.", suffix=".tmp", dir=str(target.parent)
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(payload)
            file.flush()
            os.fsync(file.fileno())
        os.replace(str(temporary_path), str(target))
        if not _is_windows():
            directory_fd = os.open(str(target.parent), os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        try:
            temporary_path.unlink()
        except FileNotFoundError:
            # os.replace has already moved this temporary path on a successful
            # atomic replacement, so cleanup has no remaining file to remove.
            pass


def _is_windows() -> bool:
    """Return whether the writer runs on a Windows filesystem contract."""
    return os.name == "nt"


def _has_git_metadata(cwd: Path) -> bool:
    """Return whether ``cwd`` itself, rather than an ancestor, owns Git metadata."""
    return (cwd / ".git").exists()
