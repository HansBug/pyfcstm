"""
Run native C-family semantic alignment reports.

This command is a thin wrapper around
:mod:`test.testings.native_semantic_alignment`. It gives maintainers a stable
entry point for generating the formal C / C poll shared fixture report for
native generated-runtime parity work.

Example::

    $ python tools/native_semantic_alignment_report.py --runner generated_c_alignment --case-id design_basic_simple_transition
"""

import importlib
import os
import sys


_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def _load_main():
    return importlib.import_module("test.testings.native_semantic_alignment").main


if __name__ == "__main__":
    raise SystemExit(_load_main()())
