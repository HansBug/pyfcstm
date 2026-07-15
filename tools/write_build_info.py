"""Generate package build identity and resource manifest data."""

import argparse
from pathlib import Path

from pyfcstm.config._build_identity import ensure_build_identity
from pyfcstm.config._resource_manifest import (
    ARTIFACT_KINDS,
    ResourceManifestError,
    write_build_info_json,
    write_resource_manifest,
)


def generate_build_artifacts(
    output_root=".",
    artifact_kind="wheel",
    output=None,
    require_manifest=False,
    require_commit=False,
    require_clean=False,
):
    """Generate all build metadata from one identity snapshot.

    :param output_root: Project root containing the ``pyfcstm`` package.
    :type output_root: str or os.PathLike
    :param artifact_kind: Current package or frozen-artifact kind.
    :type artifact_kind: str
    :param output: Optional generated ``build_info.py`` path.
    :type output: str or os.PathLike, optional
    :param require_manifest: Require a non-empty resource manifest.
    :type require_manifest: bool
    :param require_commit: Require a resolved Git/CI commit.
    :type require_commit: bool
    :param require_clean: Require a clean Git checkout.
    :type require_clean: bool
    :return: Paths and payloads for the generated metadata files.
    :rtype: dict
    :raises ResourceManifestError: If the package root or resources are invalid.

    Example::

        >>> result = generate_build_artifacts('.', 'wheel')
        >>> result['artifact_kind']
        'wheel'
    """
    if artifact_kind not in ARTIFACT_KINDS:
        raise ResourceManifestError("invalid artifact kind {!r}".format(artifact_kind))
    root = Path(output_root).absolute()
    package_root = root / "pyfcstm"
    if not package_root.is_dir() and root.name == "pyfcstm":
        package_root = root
        root = root.parent
    if output is None:
        identity_path = package_root / "config" / "build_info.py"
    else:
        identity_path = Path(output)
        if not identity_path.is_absolute():
            identity_path = root / identity_path
    identity = ensure_build_identity(
        identity_path,
        cwd=root,
        require_commit=require_commit,
        require_clean=require_clean,
    )
    manifest_path, manifest = write_resource_manifest(root, artifact_kind)
    if require_manifest and not manifest.get("resources"):
        raise ResourceManifestError("generated resource manifest is empty")
    build_info_path, build_info = write_build_info_json(
        root,
        identity,
        artifact_kind,
        manifest_path=manifest_path,
    )
    return {
        "artifact_kind": artifact_kind,
        "identity": identity,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "build_info_path": build_info_path,
        "build_info": build_info,
    }


def main() -> None:
    """Generate or validate build identity and package resource manifests.

    :return: ``None``.
    :rtype: None
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=None)
    parser.add_argument(
        "--output-root",
        default=".",
        help="project root containing the pyfcstm package (default: current directory)",
    )
    parser.add_argument(
        "--artifact-kind",
        choices=sorted(ARTIFACT_KINDS),
        default="wheel",
        help="artifact being prepared (default: wheel)",
    )
    parser.add_argument(
        "--require-manifest",
        action="store_true",
        help="fail if a non-empty resource manifest cannot be generated",
    )
    parser.add_argument("--require-commit", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    arguments = parser.parse_args()
    result = generate_build_artifacts(
        output_root=arguments.output_root,
        artifact_kind=arguments.artifact_kind,
        output=arguments.output or None,
        require_manifest=arguments.require_manifest,
        require_commit=arguments.require_commit,
        require_clean=arguments.require_clean,
    )
    identity = result["identity"]
    print(
        "{} manifest={} build_info={}".format(
            identity.revision or "unknown",
            result["manifest_path"],
            result["build_info_path"],
        )
    )


if __name__ == "__main__":
    main()
