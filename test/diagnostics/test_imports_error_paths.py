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


@pytest.mark.unittest
class TestAssembleStateMachineImportsCornerCases:
    """Corner cases for ``assemble_state_machine_imports`` itself."""

    def test_top_level_program_with_no_root_state_emits_diagnostic(self, tmp_path):
        # ``_assemble_program`` emits E_IMPORT_NOT_FOUND.reason='no_root_state'
        # when the program-under-assembly itself has no root state.
        # The grammar disallows this in normal parsing, so we use the
        # internal AST constructor.
        from pyfcstm.dsl import node as dsl_nodes
        program = dsl_nodes.StateMachineDSLProgram(
            definitions=[],
            root_state=None,
        )
        sink = DiagnosticSink(collect=True)
        assemble_state_machine_imports(program, collect_into=sink)
        codes = [d.code for d in sink.diagnostics]
        assert 'E_IMPORT_NOT_FOUND' in codes
        reasons = [
            d.refs.get('reason') for d in sink.diagnostics
            if d.code == 'E_IMPORT_NOT_FOUND'
        ]
        assert 'no_root_state' in reasons


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


@pytest.mark.unittest
class TestInternalHelpersDirectInvocation:
    """Direct invocation of internal helpers to cover defensive
    branches the grammar never produces in normal parsing.

    PR #117 coverage closeout: ``pyfcstm/model/imports.py`` has six
    emit-and-return sentinel branches whose preconditions are
    syntactically rejected upstream. We call the helpers directly
    with constructed AST stubs to hit those branches.
    """

    def test_resolve_import_event_target_path_absolute_empty_sentinel(self):
        # Lines 632-635 region: absolute target path with len 0.
        from pyfcstm.model.imports import _resolve_import_event_target_path
        from pyfcstm.diagnostics import DiagnosticSink
        from pyfcstm.dsl import node as dsl_nodes
        target = dsl_nodes.ChainID(path=[], is_absolute=True)
        sink = DiagnosticSink(collect=True)
        result = _resolve_import_event_target_path(
            target_event=target,
            owner_state_path=('Host',),
            alias='W',
            sink=sink,
        )
        # Emits E_IMPORT_MAPPING_INVALID + returns sentinel ((), '', ()).
        assert result == ((), '', ())
        assert any(d.code == 'E_IMPORT_MAPPING_INVALID' for d in sink.diagnostics)

    def test_resolve_import_event_target_path_relative_empty_sentinel(self):
        # Lines 650-653 region: relative target path with len 0.
        from pyfcstm.model.imports import _resolve_import_event_target_path
        from pyfcstm.diagnostics import DiagnosticSink
        from pyfcstm.dsl import node as dsl_nodes
        target = dsl_nodes.ChainID(path=[], is_absolute=False)
        sink = DiagnosticSink(collect=True)
        result = _resolve_import_event_target_path(
            target_event=target,
            owner_state_path=('Host',),
            alias='W',
            sink=sink,
        )
        assert result == ((), '', ())
        assert any(d.code == 'E_IMPORT_MAPPING_INVALID' for d in sink.diagnostics)

    def test_ensure_state_path_exists_empty_path_sentinel(self):
        # Lines 917-930 region: state_path empty → emit + return root.
        from pyfcstm.model.imports import _ensure_state_path_exists
        from pyfcstm.diagnostics import DiagnosticSink
        from pyfcstm.dsl import node as dsl_nodes
        # Minimal root stub. Use StateDefinition AST node.
        from pyfcstm.dsl.parse import parse_state_machine_dsl
        prog = parse_state_machine_dsl('state Root { state A; [*] -> A; }')
        sink = DiagnosticSink(collect=True)
        result = _ensure_state_path_exists(
            root=prog.root_state,
            state_path=(),
            alias='W',
            owner_state_path=('Host',),
            sink=sink,
        )
        # On empty path the helper returns the root anchor as a no-op.
        assert result is prog.root_state
        assert any(d.code == 'E_IMPORT_MAPPING_INVALID' for d in sink.diagnostics)

    def test_collect_mode_forwards_straggler_model_validation_error(self, tmp_path):
        # Lines 356-358 region: a mapping helper raises
        # ModelValidationError even though it should have routed to
        # sink. Belt-and-braces forward branch in _assemble_state.
        # Force the situation by monkey-patching
        # ``_apply_import_def_mappings`` to raise.
        from pyfcstm.model import imports as imports_mod
        from pyfcstm.utils.validate import (
            ModelDiagnostic, ModelValidationError,
        )
        worker = tmp_path / 'worker.fcstm'
        worker.write_text('state Worker;\n', encoding='utf-8')
        host = tmp_path / 'host.fcstm'
        host.write_text(
            '\n'.join([
                'state Root {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./worker.fcstm" as W;',
                '}',
            ]),
            encoding='utf-8',
        )
        original = imports_mod._apply_import_def_mappings

        def raising(*args, **kwargs):
            raise ModelValidationError(diagnostics=[
                ModelDiagnostic(
                    code='E_IMPORT_DUPLICATE_MAPPING',
                    severity='error',
                    message='synthetic straggler',
                    refs={
                        'alias': 'W',
                        'mapping_kind': 'variable',
                        'duplicated_name': 'x',
                        'direction': 'source_duplicated',
                        'host_state_path': 'Root',
                    },
                )
            ])

        try:
            imports_mod._apply_import_def_mappings = raising
            with open(host, 'r', encoding='utf-8') as f:
                ast = _parse(f.read())
            _, diagnostics = parse_dsl_node_to_state_machine(
                ast, path=str(host), collect=True,
            )
        finally:
            imports_mod._apply_import_def_mappings = original
        # The straggler diagnostic was forwarded into the outer sink.
        assert any(d.message == 'synthetic straggler' for d in diagnostics)

    def test_load_imported_program_no_root_state(self, tmp_path):
        # Line 474 region: parsed program has root_state=None.
        # Build a DSL file whose grammar parses but has no state. The
        # grammar requires at least one state, so we cannot easily
        # produce this from real DSL — instead, monkey-patch
        # parse_state_machine_dsl to return a program with root_state=None.
        from pyfcstm.model import imports as imports_mod
        from pyfcstm.diagnostics import DiagnosticSink
        from pyfcstm.dsl import node as dsl_nodes

        original = imports_mod.parse_state_machine_dsl

        def fake_parse(text):
            return dsl_nodes.StateMachineDSLProgram(definitions=[], root_state=None)

        target = tmp_path / 'shadow.fcstm'
        target.write_text('state Worker;\n', encoding='utf-8')

        # Construct a minimal ImportStatement stub
        import_item = dsl_nodes.ImportStatement(
            source_path='./shadow.fcstm',
            alias='W',
            extra_name=None,
            mappings=[],
        )
        sink = DiagnosticSink(collect=True)
        try:
            imports_mod.parse_state_machine_dsl = fake_parse
            result = imports_mod._load_imported_program(
                file_path=str(target),
                import_item=import_item,
                owner_state_path=('Host',),
                sink=sink,
            )
        finally:
            imports_mod.parse_state_machine_dsl = original

        # Helper emits no_root_state + returns None.
        assert result is None
        reasons = [
            d.refs.get('reason') for d in sink.diagnostics
            if d.code == 'E_IMPORT_NOT_FOUND'
        ]
        assert 'no_root_state' in reasons

    def _legacy_dup(self):
        return None  # placeholder

    def __test_collect_mode_continues_past_unloadable_import_unused(self, tmp_path):
        # First import has a parse error; second import is valid. In
        # collect mode the second should still be merged.
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
        # The good import is merged into the host state tree.
        substate_names = list(model.root_state.substates.keys())
        assert 'Good' in substate_names