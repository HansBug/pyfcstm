Simulator diagnostic fixtures
=============================

This directory stores FCSTM sources for simulator-only pytest coverage.
They are not part of the shared semantic fixture corpus and must not be
consumed by template alignment runners.

Use these sources only for diagnostics that need Python simulator internals or
Python-only observations such as warning rollback, log emission, or error-state
metadata.
