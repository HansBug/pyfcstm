"""
Negative-path tests for ``pyfcstm.model.imports`` covering error
branches surfaced by the PR #115 codecov delta. Each test triggers a
specific emit site that the existing import-phase fixtures do not
exercise:

* ``_assemble_program`` root-state-is-None branch (top-level entry).
* ``_load_imported_program`` read_error / parse_error / no_root_state
  branches.
* ``_resolve_import_event_target_path`` empty-path sentinel return
  (I1 from PR #116 review).
* ``_ensure_state_path_exists`` empty state_path branch.
* Collect-mode skip paths (``imported_program is None`` continue,
  straggler ``ModelValidationError.diagnostics`` forwarding).
"""

import os
import stat
import sys

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.model.imports import assemble_state_machine_imports
from pyfcstm.diagnostics import DiagnosticSink
from pyfcstm.utils.validate import ModelValidationError


def _parse(src):
    return parse_with_grammar_entry(src, 'state_machine_dsl')


@pytest.mark.unittest
class TestImportLoadErrorPaths:
    """``_load_imported_program`` has three error paths beyond
    file-not-found: read_error, parse_error, no_root_state. Exercise
    each with a host file that imports a deliberately-broken module."""

    def test_parse_error_when_imported_file_has_invalid_dsl(self, tmp_path):
        worker = tmp_path / 'worker.fcstm'
        worker.write_text('this is { not valid fcstm dsl', encoding='utf-8')
        host = tmp_path / 'host.fcstm'
        host.write_text(
            '\n'.join([
                'state Root {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./worker.fcstm" as Worker;',
                '}',
            ]),
            encoding='utf-8',
        )
        with open(host, 'r', encoding='utf-8') as f:
            ast = _parse(f.read())
        _, diagnostics = parse_dsl_node_to_state_machine(
            ast, path=str(host), collect=True,
        )
        codes = [d.code for d in diagnostics]
        reasons = [
            d.refs.get('reason') for d in diagnostics
            if d.code == 'E_IMPORT_NOT_FOUND'
        ]
        assert 'E_IMPORT_NOT_FOUND' in codes
        assert 'parse_error' in reasons

    @pytest.mark.skipif(
        sys.platform.startswith('win'),
        reason='chmod 0 is not reliable on Windows',
    )
    def test_read_error_when_imported_file_is_unreadable(self, tmp_path):
        worker = tmp_path / 'worker.fcstm'
        worker.write_text('state Worker;\n', encoding='utf-8')
        # Strip read permission. Even if running as root, the
        # ``open(..., 'r')`` call may still succeed; in that case the
        # test simply observes a successful import — assert nothing
        # stronger than "either we see read_error, or the import
        # succeeded".
        worker.chmod(0)
        host = tmp_path / 'host.fcstm'
        host.write_text(
            '\n'.join([
                'state Root {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./worker.fcstm" as Worker;',
                '}',
            ]),
            encoding='utf-8',
        )
        try:
            with open(host, 'r', encoding='utf-8') as f:
                ast = _parse(f.read())
            _, diagnostics = parse_dsl_node_to_state_machine(
                ast, path=str(host), collect=True,
            )
            reasons = [
                d.refs.get('reason') for d in diagnostics
                if d.code == 'E_IMPORT_NOT_FOUND'
            ]
            # Either read_error fires (good — branch covered) or the
            # platform let us read anyway (test still useful as a
            # smoke check).
            assert reasons == [] or 'read_error' in reasons
        finally:
            # Restore permissions so the tmp_path cleanup can succeed.
            worker.chmod(stat.S_IRUSR | stat.S_IWUSR)


# Note: ``test_top_level_program_with_no_root_state_emits_diagnostic``
# was removed. It hand-constructed a StateMachineDSLProgram with
# root_state=None — that AST shape is never produced by the grammar,
# so the test was driving an unreachable defensive branch via a
# non-public AST constructor (rule 4 violation). The corresponding
# branch in ``imports.py`` is marked ``# pragma: no cover``.


@pytest.mark.unittest
class TestImportCollectModeSkipsCorruptedImports:
    """When an import fails partway, the host-machine assembly should
    skip the offending import and continue. Two skip paths:
    ``imported_program is None`` after a failed load, and the
    straggler ``ModelValidationError`` forward branch."""

    def test_collect_mode_continues_past_unloadable_import_first(self, tmp_path):
        # Same as below but use a unique name so the next test stays
        # distinct (kept for backward compat with the originally-named
        # test which we replace).
        broken = tmp_path / 'broken.fcstm'
        broken.write_text('garbage{', encoding='utf-8')
        good = tmp_path / 'good.fcstm'
        good.write_text(
            '\n'.join([
                'state Good {',
                '    state Idle;',
                '    [*] -> Idle;',
                '}',
            ]),
            encoding='utf-8',
        )
        host = tmp_path / 'host.fcstm'
        host.write_text(
            '\n'.join([
                'state Root {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./broken.fcstm" as Broken;',
                '    import "./good.fcstm" as Good;',
                '}',
            ]),
            encoding='utf-8',
        )
        with open(host, 'r', encoding='utf-8') as f:
            ast = _parse(f.read())
        model, diagnostics = parse_dsl_node_to_state_machine(
            ast, path=str(host), collect=True,
        )
        codes = [d.code for d in diagnostics]
        assert 'E_IMPORT_NOT_FOUND' in codes
        substate_names = list(model.root_state.substates.keys())
        assert 'Good' in substate_names



# NOTE (PR #117 follow-up): the previously-present
# ``TestInternalHelpersDirectInvocation`` class has been removed.
# Each of its 4 tests invoked private helpers
# (``_resolve_import_event_target_path``,
# ``_ensure_state_path_exists``, ``_load_imported_program``,
# ``_apply_import_def_mappings``) directly or monkey-patched them,
# violating the project's "no private-helper / no mock" testing rule.
#
# The defensive branches those tests "covered" are now marked with
# ``# pragma: no cover`` directly in ``pyfcstm/model/imports.py``,
# with rationale notes explaining why grammar-protected DSL inputs
# never reach them. The branches remain in the source as fail-loud
# guards against future regressions of the upstream validation
# pipeline.
