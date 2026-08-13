"""
Coverage for every model-build error code under the collecting inspect path.

Strict model building raises on the first error, so an inspect report can never
carry more than one ``E_*``. The collecting path accumulates all of them. These
tests pin down, for each error code that the model builder can emit, that the
code survives into :class:`pyfcstm.diagnostics.ModelInspect` and that building
the report over the resulting -- possibly inconsistent -- model does not raise,
with and without verify enabled.

One code is intentionally absent, and the reason is recorded in
:data:`UNCOVERED_BUILD_ERROR_CODES` rather than left implicit.
"""

import os
import tempfile

import pytest

from pyfcstm.diagnostics import inspect_model
from pyfcstm.diagnostics.codes import CODE_REGISTRY
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import load_state_machine_from_file, parse_dsl_node_to_state_machine


# Single-file DSL snippets, one per model-build error code.
SINGLE_FILE_CASES = {
    'E_UNDEFINED_VAR': 'state Root { state A; state B; A -> B : if [zzz > 0]; }',
    'E_DUPLICATE_VAR': 'def int x = 0;\ndef int x = 1;\nstate Root { state A; }',
    'E_MISSING_STATE': (
        'state Root { state A; state B; [*] -> A; A -> B : /NoSuch.GoEvent; }'
    ),
    'E_DUPLICATE_STATE': 'state Root { state A; state A; }',
    'E_DANGLING_TRANSITION': 'state Root { state A; NoSuch -> A; }',
    'E_FORCED_TRANSITION_EXPANSION': 'state Root { state A; !NoSuch -> A; }',
    'E_INITIAL_TRANSITION_INVALID': 'state Root { state Outer { state Inner; } }',
    'E_DUPLICATE_FUNCTION_NAME': (
        'state Root { state A { enter f {} enter f {} } [*] -> A; }'
    ),
    'E_DURING_ASPECT_INVALID': 'state Root { state A { during before { } } }',
    'E_PSEUDO_NOT_LEAF': (
        'state Root { pseudo state Outer { state Inner; [*] -> Inner; } }'
    ),
    'E_NAMED_FUNCTION_REF_CYCLE': (
        'def int x = 0;\n'
        'state Root { enter A ref A; state Idle { during { x = x + 1; } } '
        '[*] -> Idle; }'
    ),
    'E_NAMED_FUNCTION_REF_NOT_FOUND': (
        'state Root { enter A ref Missing; state Idle; [*] -> Idle; }'
    ),
}

# Import errors need a real file tree, so each case is a {filename: content} map
# rooted at ``root.fcstm``.
IMPORT_CASES = {
    'E_IMPORT_NOT_FOUND': {
        'root.fcstm': 'state Host { import "./missing.fcstm" as M; [*] -> M; }',
    },
    'E_IMPORT_CIRCULAR': {
        'root.fcstm': 'state Host { import "./a.fcstm" as A; [*] -> A; }',
        'a.fcstm': 'state A { import "./root.fcstm" as R; [*] -> R; }',
    },
    'E_IMPORT_ALIAS_CONFLICT': {
        'root.fcstm': (
            'state Host { import "./w.fcstm" as W; import "./w.fcstm" as W; '
            '[*] -> W; }'
        ),
        'w.fcstm': 'state W { state Idle; [*] -> Idle; }',
    },
    'E_IMPORT_MAPPING_INVALID': {
        'root.fcstm': (
            'state Host { import "./w.fcstm" as W '
            '{ def sensor_* -> left_${x}; } [*] -> W; }'
        ),
        'w.fcstm': 'def int sensor_input = 0;\nstate W { state Idle; [*] -> Idle; }',
    },
    'E_IMPORT_DUPLICATE_MAPPING': {
        'root.fcstm': (
            'state Host { import "./w.fcstm" as W '
            '{ def sensor_input -> a; def sensor_input -> b; } [*] -> W; }'
        ),
        'w.fcstm': 'def int sensor_input = 0;\nstate W { state Idle; [*] -> Idle; }',
    },
}

# Codes the model builder can emit that these tests deliberately do not cover,
# each with the reason. Keep this exhaustive: the inventory test below fails if a
# build error code is neither covered nor listed here.
UNCOVERED_BUILD_ERROR_CODES = {
    'E_COMBO_PSEUDO_NAME_COLLISION': (
        'Reaching it requires occupying every generated pseudo-state name for a '
        'combo trigger, which the existing coverage does by patching the name '
        'generator. Driving production internals to manufacture the state is out '
        'of bounds for this suite, so the collecting path is not pinned for it.'
    ),
}


# Error codes that exist in the catalog but that the Python model builder never
# emits, so the collecting path cannot surface them.
NON_MODEL_BUILD_ERROR_CODES = {
    # Emitted only by the lookup API (State.resolve_event / StateMachine
    # .resolve_event), which model construction does not call.
    'E_EVENT_REF_INVALID',
    'E_EVENT_NOT_FOUND',
    # No Python emission point at all: E_TYPE_MISMATCH is raised by the
    # TypeScript editor side, and E_COMBO_TRIGGER_NOT_EXPANDED is a catalog-only
    # cross-version compatibility entry that the inspect exit filters out.
    'E_TYPE_MISMATCH',
    'E_COMBO_TRIGGER_NOT_EXPANDED',
}


def _build_error_codes():
    """Return the error codes the Python model builder can emit."""
    catalog_errors = {
        code for code, spec in CODE_REGISTRY.items() if spec.severity == 'error'
    }
    return catalog_errors - NON_MODEL_BUILD_ERROR_CODES


def _collect_from_text(source):
    ast = parse_with_grammar_entry(source, 'state_machine_dsl')
    return parse_dsl_node_to_state_machine(ast, collect=True)


def _assert_code_survives_into_report(code, machine, diagnostics):
    assert code in {d.code for d in diagnostics}, (
        f'{code} was not emitted by the model builder'
    )
    for verify_enabled in (False, True):
        report = inspect_model(
            machine,
            model_diagnostics=diagnostics,
            enable_verify=verify_enabled,
        )
        assert code in {d.code for d in report.diagnostics}, (
            f'{code} was dropped from the report '
            f'(enable_verify={verify_enabled})'
        )


@pytest.mark.unittest
class TestEveryBuildErrorSurvivesCollection:
    @pytest.mark.parametrize(('code', 'source'), sorted(SINGLE_FILE_CASES.items()))
    def test_single_file_error_reaches_the_report(self, code, source):
        machine, diagnostics = _collect_from_text(source)

        assert machine is not None
        _assert_code_survives_into_report(code, machine, diagnostics)

    @pytest.mark.parametrize(('code', 'files'), sorted(IMPORT_CASES.items()))
    def test_import_error_reaches_the_report(self, code, files):
        with tempfile.TemporaryDirectory() as td:
            for name, content in files.items():
                with open(os.path.join(td, name), 'w', encoding='utf-8') as f:
                    f.write(content)
            machine, diagnostics = load_state_machine_from_file(
                os.path.join(td, 'root.fcstm'), collect=True
            )

        assert machine is not None
        _assert_code_survives_into_report(code, machine, diagnostics)

    def test_every_model_build_error_code_is_covered_or_recorded(self):
        """No build error code may be silently left out of this suite."""
        covered = set(SINGLE_FILE_CASES) | set(IMPORT_CASES)
        expected = _build_error_codes()

        assert covered <= expected, covered - expected
        assert set(UNCOVERED_BUILD_ERROR_CODES) <= expected
        assert expected - covered == set(UNCOVERED_BUILD_ERROR_CODES)

    def test_every_collected_error_carries_a_span(self):
        """Spanless diagnostics are dropped by the report builder."""
        for code, source in sorted(SINGLE_FILE_CASES.items()):
            _, diagnostics = _collect_from_text(source)
            for diagnostic in diagnostics:
                assert diagnostic.span is not None, f'{code}: {diagnostic.code}'


@pytest.mark.unittest
class TestCollectionStaysScopedToInspect:
    """Only inspect gains the collecting path.

    ``diagram`` and ``bmc`` cannot do anything useful with an inconsistent
    model, so they keep failing on the first model error.
    """

    _MULTI_ERROR = 'state Root { state A; state A; NoSuch -> A; [*] -> A; }'

    def _write(self, directory):
        path = os.path.join(directory, 'multi.fcstm')
        with open(path, 'w', encoding='utf-8') as f:
            f.write(self._MULTI_ERROR)
        return path

    def test_loaders_still_default_to_strict(self):
        from pyfcstm.utils.validate import ModelValidationError

        with tempfile.TemporaryDirectory() as td:
            path = self._write(td)

            with pytest.raises(ModelValidationError):
                load_state_machine_from_file(path)

    @pytest.mark.parametrize('command', ['diagram', 'bmc'])
    def test_other_commands_still_fail_on_the_first_error(self, command):
        from hbutils.testing import simulate_entry

        from pyfcstm.entry import pyfcstmcli

        with tempfile.TemporaryDirectory() as td:
            path = self._write(td)
            args = ['pyfcstm', command, '-i', path]
            if command == 'bmc':
                query_path = os.path.join(td, 'q.fbmcq')
                with open(query_path, 'w', encoding='utf-8') as f:
                    f.write('check reachable state Root.A within 3;')
                args += ['-q', query_path]

            result = simulate_entry(pyfcstmcli, args)

        assert result.exitcode != 0
        output = result.stderr or result.stdout
        # The strict single-error shape is preserved: the run stops at the first
        # error and never reaches the report that would list the others.
        assert 'Duplicate state name' in output
        assert 'E_DANGLING_TRANSITION' not in output
