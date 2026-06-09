"""Compatibility shim for SMT-local verification helpers.

The implementation has moved under :mod:`pyfcstm.verify.encoding._core` and
the public algorithm entry points are registered from
``pyfcstm.verify.algorithms``.  This module remains as a compatibility alias
for existing tests and callers that import private helper names from
``pyfcstm.verify.smt_local``.
"""

from __future__ import annotations

import sys

from .encoding import _core

sys.modules[__name__] = _core
