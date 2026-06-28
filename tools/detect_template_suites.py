"""
Command-line wrapper for template suite detection.

This script delegates to :func:`tools.template_suites.main` so the selection
semantics live in importable, self-checked repository tooling while maintainer
commands still have a short executable path. It is intentionally not part of
the public :mod:`pyfcstm` runtime package.

Example::

    $ python tools/detect_template_suites.py --help
"""

import os
import sys

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from tools.template_suites import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
