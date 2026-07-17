"""
Private standard-library self-check implementation.

This package is an internal execution boundary for ``python -m pyfcstm
--self-check``. It is intentionally not re-exported from :mod:`pyfcstm` and
does not provide a third-party check plug-in API.

Self-check is a post-release deployment diagnostic, not a substitute for the
unit-test suite, the full CI gates, or the CLI build. Those pre-release gates
establish implementation correctness before a wheel or standalone CLI is
published. Once an artifact is installed or unpacked by a user, self-check
inspects that deployment's imports, packaged resources, runtime dependencies,
platform compatibility, and optional visualization services. A failure should
therefore be read as evidence about the current installation or environment,
not as a second implementation-correctness test. Reports preserve the
relevant environment metadata and failure detail so a deployment problem can
be diagnosed without reproducing the original machine.

The package contains:

.. list-table::
   :header-rows: 1

   * - Module
     - Responsibility
   * - :mod:`pyfcstm._selfcheck.arguments`
     - Parse supervisor and hidden-worker options.
   * - :mod:`pyfcstm._selfcheck.model`
     - Store typed results and the ordered single-writer ledger.
   * - :mod:`pyfcstm._selfcheck.protocol`
     - Encode and validate worker frames.
   * - :mod:`pyfcstm._selfcheck.registry`
     - Map stable worker keys to built-in checks.
   * - :mod:`pyfcstm._selfcheck.supervisor`
     - Run checks serially and coordinate reporting and exit status.
   * - :mod:`pyfcstm._selfcheck.environment`
     - Collect redacted runtime and package environment metadata.
   * - :mod:`pyfcstm._selfcheck.process`
     - Run one worker, drain bounded pipes, and clean up its process tree.
   * - :mod:`pyfcstm._selfcheck.report`
     - Render human/JSON reports and emergency diagnostics.
   * - :mod:`pyfcstm._selfcheck.worker`
     - Run one static check and emit one validated result envelope.
   * - :mod:`pyfcstm._selfcheck._win32`
     - Provide Windows Job Object and console compatibility helpers.

The implementation must remain compatible with Python 3.7 and must not import
Click or other optional CLI dependencies during bootstrap.
"""

__all__ = []
