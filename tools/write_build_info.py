"""Generate the package build identity data file."""

import argparse
from pathlib import Path

from pyfcstm.config._build_identity import ensure_build_identity


_DEFAULT_OUTPUT = Path("pyfcstm") / "config" / "build_info.py"


def main() -> None:
    """Generate or validate build identity for packaging commands.

    :return: ``None``.
    :rtype: None
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(_DEFAULT_OUTPUT))
    parser.add_argument("--require-commit", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    arguments = parser.parse_args()
    identity = ensure_build_identity(
        arguments.output,
        require_commit=arguments.require_commit,
        require_clean=arguments.require_clean,
    )
    print(identity.revision or "unknown")


if __name__ == "__main__":
    main()
