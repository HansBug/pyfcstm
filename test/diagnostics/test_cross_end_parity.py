"""
Cross-end E_* parity tests — confirm that a given DSL fixture triggers
the same ``E_*`` code set on both pyfcstm and jsfcstm.

The jsfcstm side has its own hermetic showcase (mocha test
``editors/jsfcstm/test/diagnostics-showcase-demos.test.ts``) that runs
``collectDocumentDiagnostics`` against the same DSL strings inlined
below. This pytest file pins down the **pyfcstm** half of the same
fixture set: each fixture runs through
:func:`pyfcstm.model.parse_dsl_node_to_state_machine` with
``collect=True`` and the resulting ``ModelDiagnostic`` list must contain
the expected ``E_*`` codes.

If a fixture here triggers ``E_*`` codes that the matching jsfcstm
showcase does not, or vice versa, the two ends have drifted and the
Layer 2 PR-A contract is violated. Keeping these two suites in lockstep
is the mechanical safeguard for "what pyfcstm CLI reports must equal
what VSCode shows".

The fixture catalogue mirrors
``editors/jsfcstm/test/diagnostics-showcase-demos.test.ts``: same names,
same DSL bodies, same ``mustFire`` codes (the jsfcstm side has slightly
richer ``sideEffects`` and ``mustNotFire`` lists for the W_* layer that
pyfcstm has not implemented yet — see issue #104).
"""

import os
import tempfile

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.utils.validate import ModelDiagnostic


def _collect_codes_from_dsl(dsl: str, *, base_dir=None):
    """Parse a DSL string in collect mode and return the emitted code
    list. The optional ``base_dir`` is the directory where imports are
    resolved against — only used by multi-file fixtures."""
    try:
        ast = parse_with_grammar_entry(dsl, 'state_machine_dsl')
    except Exception as e:
        # Grammar parse errors don't carry ``E_*`` codes (they belong to
        # the parser layer); return them as a sentinel so the test can
        # see what went wrong.
        return ['<PARSE_ERROR>'], None
    result = parse_dsl_node_to_state_machine(
        ast, path=base_dir, collect=True,
    )
    model, diagnostics = result
    codes = [d.code for d in diagnostics]
    return codes, model


def _collect_codes_from_file(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        dsl = f.read()
    return _collect_codes_from_dsl(dsl, base_dir=path)


# ---------------------------------------------------------------------------
# Single-file fixtures (mirror jsfcstm/test/diagnostics-showcase-demos.test.ts)
# ---------------------------------------------------------------------------

SINGLE_FILE_FIXTURES = [
    (
        'undefined-variable',
        '\n'.join([
            'def int counter = 0;',
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active : if [unknown_var > 0];',
            '    Active -> Idle : if [counter > 5] effect { counter = counter + mystery_input; };',
            '}',
        ]),
        ['E_UNDEFINED_VAR', 'E_UNDEFINED_VAR'],
    ),
    (
        'duplicate-variable',
        '\n'.join([
            'def int counter = 0;',
            'def float temp = 25.0;',
            'def int unrelated = 42;',
            'def int counter = 1;',
            'def float temp = 30.0;',
            '',
            'state Root {',
            '    state Idle;',
            '    [*] -> Idle;',
            '}',
        ]),
        ['E_DUPLICATE_VAR', 'E_DUPLICATE_VAR'],
    ),
    (
        'missing-state',
        '\n'.join([
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    GhostState -> Idle :: Wake;',
            '    Active -> NoSuchTarget :: Halt;',
            '}',
        ]),
        ['E_MISSING_STATE', 'E_DANGLING_TRANSITION'],
    ),
    (
        'duplicate-state',
        '\n'.join([
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    state Idle;',
            '    [*] -> Idle;',
            '    Active -> Idle :: Stop;',
            '}',
        ]),
        ['E_DUPLICATE_STATE'],
    ),
    (
        'duplicate-function-name',
        '\n'.join([
            'state Root {',
            '    state System {',
            '        enter Initialize {}',
            '        enter Initialize {}',
            '        state Idle;',
            '        [*] -> Idle;',
            '    }',
            '    [*] -> System;',
            '}',
        ]),
        ['E_DUPLICATE_FUNCTION_NAME'],
    ),
    (
        'pseudo-not-leaf',
        '\n'.join([
            'state Root {',
            '    pseudo state BadPseudo {',
            '        state Inner;',
            '        [*] -> Inner;',
            '    }',
            '    state Idle;',
            '    [*] -> Idle;',
            '}',
        ]),
        ['E_PSEUDO_NOT_LEAF'],
    ),
    (
        'during-aspect-invalid',
        '\n'.join([
            'def int counter = 0;',
            'state Root {',
            '    state Idle {',
            '        >> during before { counter = counter + 1; }',
            '    }',
            '    [*] -> Idle;',
            '}',
        ]),
        ['E_DURING_ASPECT_INVALID'],
    ),
    (
        'initial-transition-invalid',
        '\n'.join([
            'state Root {',
            '    state Outer {',
            '        state InnerScope {',
            '            state Leaf;',
            '        }',
            '        [*] -> InnerScope;',
            '    }',
            '    [*] -> Outer;',
            '}',
        ]),
        ['E_INITIAL_TRANSITION_INVALID'],
    ),
    (
        'named-function-ref-not-found',
        '\n'.join([
            'state Root {',
            '    state Idle {',
            '        enter ref NoSuch.Action;',
            '    }',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active :: Go;',
            '}',
        ]),
        ['E_NAMED_FUNCTION_REF_NOT_FOUND'],
    ),
    (
        'forced-transition-expansion',
        '\n'.join([
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    !Ghost -> Idle :: Panic;',
            '    Active -> Idle :: Stop;',
            '}',
        ]),
        ['E_FORCED_TRANSITION_EXPANSION'],
    ),
]


# ---------------------------------------------------------------------------
# Multi-file fixtures (E_IMPORT_*). pyfcstm needs the import targets to
# actually exist on disk, so each fixture materializes its files in a
# tmp directory.
# ---------------------------------------------------------------------------

MULTI_FILE_FIXTURES = [
    (
        'import-not-found',
        {
            'host.fcstm': '\n'.join([
                'state Root {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./absent.fcstm" as Worker;',
                '}',
            ]),
        },
        'host.fcstm',
        ['E_IMPORT_NOT_FOUND'],
    ),
    (
        'import-alias-conflict',
        {
            'host.fcstm': '\n'.join([
                'state Root {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./worker.fcstm" as Idle;',
                '}',
            ]),
            'worker.fcstm': 'state Worker;\n',
        },
        'host.fcstm',
        ['E_IMPORT_ALIAS_CONFLICT'],
    ),
    (
        'import-duplicate-mapping',
        {
            # Same exact mapping line repeated — jsfcstm's analyzer
            # detects byte-equal mapping AST nodes; pyfcstm's analyzer
            # detects same-source exact selector reused. Both fire on
            # this fixture. The worker file must actually declare the
            # ``sensor`` variable so the def-mapping pipeline runs
            # (an empty imported module short-circuits the resolver).
            'host.fcstm': '\n'.join([
                'state Root {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./worker.fcstm" as Worker {',
                '        def sensor -> io_a;',
                '        def sensor -> io_a;',
                '    }',
                '}',
            ]),
            'worker.fcstm': 'def int sensor = 0;\nstate Worker;\n',
        },
        'host.fcstm',
        ['E_IMPORT_DUPLICATE_MAPPING'],
    ),
    (
        'import-circular',
        {
            'a.fcstm': '\n'.join([
                'state A {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./b.fcstm" as B;',
                '}',
            ]),
            'b.fcstm': '\n'.join([
                'state B {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./a.fcstm" as A;',
                '}',
            ]),
        },
        'a.fcstm',
        ['E_IMPORT_CIRCULAR'],
    ),
]


@pytest.mark.unittest
@pytest.mark.parametrize('name,dsl,must_fire', SINGLE_FILE_FIXTURES, ids=[
    item[0] for item in SINGLE_FILE_FIXTURES
])
def test_single_file_fixture_emits_expected_codes(name, dsl, must_fire):
    codes, _ = _collect_codes_from_dsl(dsl)
    tally = {}
    for code in codes:
        tally[code] = tally.get(code, 0) + 1
    for expected in must_fire:
        assert tally.get(expected, 0) > 0, (
            f'{name}: expected {expected} to fire, got {codes}'
        )
        tally[expected] -= 1


@pytest.mark.unittest
@pytest.mark.parametrize('name,files,entry,must_fire', MULTI_FILE_FIXTURES, ids=[
    item[0] for item in MULTI_FILE_FIXTURES
])
def test_multi_file_fixture_emits_expected_codes(name, files, entry, must_fire, tmp_path):
    for relative, body in files.items():
        path = tmp_path / relative
        path.write_text(body, encoding='utf-8')

    entry_path = str(tmp_path / entry)
    codes, _ = _collect_codes_from_file(entry_path)
    for expected in must_fire:
        assert expected in codes, (
            f'{name}: expected {expected} to fire, got {codes}'
        )


@pytest.mark.unittest
def test_strict_mode_raises_with_diagnostic_attribute():
    """In strict mode the first E_* still surfaces as a raised
    ModelValidationError carrying the diagnostic. Confirms the
    backward-compat path used by every existing ``except SyntaxError:``
    handler still sees a structured payload."""
    from pyfcstm.utils.validate import ModelValidationError
    dsl = '\n'.join([
        'state Root {',
        '    state Idle;',
        '    state Idle;',
        '    [*] -> Idle;',
        '}',
    ])
    ast = parse_with_grammar_entry(dsl, 'state_machine_dsl')
    with pytest.raises(ModelValidationError) as exc_info:
        parse_dsl_node_to_state_machine(ast)
    assert isinstance(exc_info.value, SyntaxError)
    assert any(d.code == 'E_DUPLICATE_STATE' for d in exc_info.value.diagnostics)


@pytest.mark.unittest
def test_import_strict_mode_raises_e_import_not_found(tmp_path):
    """The new ``E_IMPORT_*`` codes also raise in strict mode and
    inherit the SyntaxError backward-compat invariant."""
    from pyfcstm.utils.validate import ModelValidationError
    host = tmp_path / 'host.fcstm'
    host.write_text(
        '\n'.join([
            'state Root {',
            '    state Idle;',
            '    [*] -> Idle;',
            '    import "./absent.fcstm" as Worker;',
            '}',
        ]),
        encoding='utf-8',
    )
    with open(host, 'r', encoding='utf-8') as f:
        ast = parse_with_grammar_entry(f.read(), 'state_machine_dsl')
    with pytest.raises(ModelValidationError) as exc_info:
        parse_dsl_node_to_state_machine(ast, path=str(host))
    assert isinstance(exc_info.value, SyntaxError)
    assert any(d.code == 'E_IMPORT_NOT_FOUND' for d in exc_info.value.diagnostics)


@pytest.mark.unittest
def test_collect_mode_accumulates_import_and_model_errors(tmp_path):
    """The full alignment guarantee: in collect mode, both import-time
    diagnostics (from ``imports.py``) and model-time diagnostics (from
    ``model.py``) accumulate on the same sink."""
    host = tmp_path / 'host.fcstm'
    host.write_text(
        '\n'.join([
            'def int counter = 0;',
            'state Root {',
            '    state Idle;',
            '    [*] -> Idle;',
            '    Idle -> NoSuchState : if [counter > 0];',
            '    import "./absent.fcstm" as Worker;',
            '}',
        ]),
        encoding='utf-8',
    )
    with open(host, 'r', encoding='utf-8') as f:
        ast = parse_with_grammar_entry(f.read(), 'state_machine_dsl')
    _, diagnostics = parse_dsl_node_to_state_machine(
        ast, path=str(host), collect=True,
    )
    codes = [d.code for d in diagnostics]
    # Both an import error and a model error accumulated together —
    # neither aborted the other.
    assert 'E_IMPORT_NOT_FOUND' in codes
    assert 'E_DANGLING_TRANSITION' in codes
