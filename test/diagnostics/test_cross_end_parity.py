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

from ._schema_check import assert_all_diags_match_schema


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
    return codes, model, diagnostics


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
    # I-h: mirror jsfcstm fixture 11-temporary-read-before-assign.
    # ``tracker`` and ``compute_me`` are not declared at file top, so
    # the first read of ``compute_me`` (on the right-hand side of the
    # first assignment) fires E_UNDEFINED_VAR with ``is_temporary=True``
    # — the schema flag distinguishing read-before-assign of a
    # would-be block-local temp from a read of a genuinely undefined
    # identifier.
    (
        'temporary-read-before-assign',
        '\n'.join([
            'state Root {',
            '    state Idle {',
            '        enter {',
            '            tracker = compute_me + 1;',
            '            compute_me = tracker * 2;',
            '        }',
            '    }',
            '    [*] -> Idle;',
            '}',
        ]),
        ['E_UNDEFINED_VAR'],
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
    codes, _, diagnostics = _collect_codes_from_dsl(dsl)
    tally = {}
    for code in codes:
        tally[code] = tally.get(code, 0) + 1
    for expected in must_fire:
        assert tally.get(expected, 0) > 0, (
            f'{name}: expected {expected} to fire, got {codes}'
        )
        tally[expected] -= 1
    # I-e mechanical safeguard: every emitted diagnostic's refs
    # payload must conform to ``codes.yaml`` (required fields present,
    # enum values in range, runtime types match). This is the parity
    # test that would have caught C-A/B/C/D before merge.
    assert_all_diags_match_schema(diagnostics, context=name)


@pytest.mark.unittest
@pytest.mark.parametrize('name,files,entry,must_fire', MULTI_FILE_FIXTURES, ids=[
    item[0] for item in MULTI_FILE_FIXTURES
])
def test_multi_file_fixture_emits_expected_codes(name, files, entry, must_fire, tmp_path):
    for relative, body in files.items():
        path = tmp_path / relative
        path.write_text(body, encoding='utf-8')

    entry_path = str(tmp_path / entry)
    codes, _, diagnostics = _collect_codes_from_file(entry_path)
    for expected in must_fire:
        assert expected in codes, (
            f'{name}: expected {expected} to fire, got {codes}'
        )
    assert_all_diags_match_schema(diagnostics, context=name)


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


@pytest.mark.unittest
def test_undefined_var_emits_per_identifier():
    """``E_UNDEFINED_VAR`` must emit one diagnostic per undefined
    identifier, and ``refs['var_name']`` must be a ``str`` — not a list.

    The schema (``pyfcstm/diagnostics/codes.yaml``) declares
    ``var_name: type: str, required: true``. Bundling multiple unknown
    names into a list violates the schema type contract and diverges
    from jsfcstm, which emits one diagnostic per identifier so VSCode
    can highlight each one independently.

    This fixture has three undefined identifiers inside a *single*
    guard expression — the only way to surface the difference between
    list-emit and per-identifier-emit behaviour.
    """
    dsl = '\n'.join([
        'def int counter = 0;',
        'state Root {',
        '    state A;',
        '    state B;',
        '    [*] -> A;',
        '    A -> B : if [foo > 0 && bar < 10 && baz == 0];',
        '}',
    ])
    codes, _, _ = _collect_codes_from_dsl(dsl)
    assert codes.count('E_UNDEFINED_VAR') == 3, (
        f'expected one E_UNDEFINED_VAR per undefined identifier '
        f'(foo/bar/baz), got {codes}'
    )

    ast = parse_with_grammar_entry(dsl, 'state_machine_dsl')
    _, diagnostics = parse_dsl_node_to_state_machine(ast, collect=True)
    undef_diags = [d for d in diagnostics if d.code == 'E_UNDEFINED_VAR']
    var_names = sorted(d.refs['var_name'] for d in undef_diags)
    assert var_names == ['bar', 'baz', 'foo'], (
        f'expected per-identifier var_name values, got {var_names}'
    )
    for d in undef_diags:
        assert isinstance(d.refs['var_name'], str), (
            f'refs.var_name must be str per schema, got '
            f'{type(d.refs["var_name"]).__name__}={d.refs["var_name"]!r}'
        )


@pytest.mark.unittest
def test_import_mapping_collect_mode_accumulates_multiple_errors(tmp_path):
    """C-E from PR #115 R2.C4 / R1.C2: in collect mode, multiple
    mapping errors inside a *single* import statement must accumulate
    on the sink, not get truncated to the first one.

    Before the fix, ``imports.py`` wrapped the four mapping helpers in
    a single ``try/except ModelValidationError`` which forwarded only
    the FIRST raised diagnostic per import. The mapping pipeline was
    effectively fail-fast inside an import, contradicting the
    docstring promise that ``execution continues — the import pipeline
    is expected to ``continue`` past the offending step``.
    """
    worker = tmp_path / 'worker.fcstm'
    worker.write_text(
        '\n'.join([
            'def int sensor_a = 0;',
            'def int sensor_b = 0;',
            'def int sensor_c = 0;',
            'state Worker;',
        ]),
        encoding='utf-8',
    )
    host = tmp_path / 'host.fcstm'
    # Three independent duplicate-mapping errors in one import block.
    host.write_text(
        '\n'.join([
            'state Root {',
            '    state Idle;',
            '    [*] -> Idle;',
            '    import "./worker.fcstm" as W {',
            '        def sensor_a -> io_x;',
            '        def sensor_a -> io_x;',
            '        def sensor_b -> io_y;',
            '        def sensor_b -> io_y;',
            '        def sensor_c -> io_z;',
            '        def sensor_c -> io_z;',
            '    }',
            '}',
        ]),
        encoding='utf-8',
    )
    with open(host, 'r', encoding='utf-8') as f:
        ast = parse_with_grammar_entry(f.read(), 'state_machine_dsl')
    _, diagnostics = parse_dsl_node_to_state_machine(
        ast, path=str(host), collect=True,
    )
    dup_codes = [d.code for d in diagnostics if d.code == 'E_IMPORT_DUPLICATE_MAPPING']
    assert len(dup_codes) >= 2, (
        f'expected at least 2 E_IMPORT_DUPLICATE_MAPPING diagnostics in collect mode, '
        f'got codes={[d.code for d in diagnostics]}'
    )


@pytest.mark.unittest
def test_undefined_var_carries_is_temporary_flag():
    """I-i from PR #115 review: a read-before-assign of a name that
    has no file-top ``def`` is semantically a would-be block-local
    temporary that was never written. ``refs.is_temporary=True``
    distinguishes this case from a read of a genuinely undefined
    identifier so downstream LLM consumers can branch on the flag.
    """
    dsl = '\n'.join([
        'state Root {',
        '    state Idle {',
        '        enter {',
        '            tracker = compute_me + 1;',
        '            compute_me = tracker * 2;',
        '        }',
        '    }',
        '    [*] -> Idle;',
        '}',
    ])
    _, _, diagnostics = _collect_codes_from_dsl(dsl)
    undef_diags = [d for d in diagnostics if d.code == 'E_UNDEFINED_VAR']
    assert undef_diags, f'expected E_UNDEFINED_VAR to fire, got {[d.code for d in diagnostics]}'
    for d in undef_diags:
        assert d.refs.get('is_temporary') is True, (
            f'expected is_temporary=True (var has no file-top def), '
            f'got refs={d.refs}'
        )


@pytest.mark.unittest
def test_undefined_var_is_temporary_false_when_no_later_assignment():
    """The complementary half of I-i: a read of a name that is neither
    a file-top ``def`` nor assigned anywhere later in the same block is
    a "real" undefined identifier, NOT a would-be temp. The flag must
    be ``False`` (or absent) so the LLM can give different fix advice
    (declare a def vs. assign before read).
    """
    dsl = '\n'.join([
        'state Root {',
        '    state Idle {',
        '        enter {',
        '            tracker = nowhere_else + 1;',
        '        }',
        '    }',
        '    [*] -> Idle;',
        '}',
    ])
    _, _, diagnostics = _collect_codes_from_dsl(dsl)
    undef_diags = [d for d in diagnostics if d.code == 'E_UNDEFINED_VAR']
    assert undef_diags
    # ``nowhere_else`` is the unknown identifier; it has no file-top
    # def and is not assigned later in this block.
    nowhere_diags = [d for d in undef_diags if d.refs.get('var_name') == 'nowhere_else']
    assert nowhere_diags, f'expected diag for "nowhere_else", got {[d.refs for d in undef_diags]}'
    for d in nowhere_diags:
        assert d.refs.get('is_temporary') is False, (
            f'real undefined (no later assignment) should have is_temporary=False; '
            f'refs={d.refs}'
        )


@pytest.mark.unittest
def test_is_temporary_flattens_across_if_branches():
    """I5 lockdown (PR #116 re-review): a name assigned in one
    ``if`` branch but read in another is reported with
    ``is_temporary=True`` — the heuristic is intentionally flattened
    across branches, matching jsfcstm's
    ``analyzeOperationStatements`` behaviour. A future tightening to
    per-path precision would diverge the two ends, so this test pins
    the current contract."""
    dsl = '\n'.join([
        'state Root {',
        '    state Idle {',
        '        enter {',
        '            if [1 > 0] { x = 1; }',
        '            else { y = x + 1; }',
        '        }',
        '    }',
        '    [*] -> Idle;',
        '}',
    ])
    _, _, diagnostics = _collect_codes_from_dsl(dsl)
    x_reads = [
        d for d in diagnostics
        if d.code == 'E_UNDEFINED_VAR' and d.refs.get('var_name') == 'x'
    ]
    assert x_reads, (
        f'expected E_UNDEFINED_VAR for "x" in else branch, '
        f'got {[d.refs for d in diagnostics]}'
    )
    for d in x_reads:
        assert d.refs.get('is_temporary') is True, (
            f'x is assigned in the if-branch sibling; the flag should '
            f'flatten across branches per docstring; refs={d.refs}'
        )


@pytest.mark.unittest
def test_lookup_api_codes_never_fire_in_static_pipeline():
    """I-b from PR #115 review: E_EVENT_REF_INVALID / E_EVENT_NOT_FOUND
    are marked ``emit_tier: lookup_api`` because they only fire when a
    caller invokes ``State.resolve_event`` / ``StateMachine.resolve_event``
    explicitly. The static pipeline (``parse_dsl_node_to_state_machine``)
    must never produce them. This test pins that contract: even when
    we exercise every single-file showcase fixture in collect mode,
    none of the lookup_api codes appear.
    """
    from pyfcstm.diagnostics import CODE_REGISTRY

    lookup_api_codes = {
        code
        for code, spec in CODE_REGISTRY.items()
        if spec.emit_tier == 'lookup_api'
    }
    assert lookup_api_codes, 'expected at least one lookup_api code in registry'

    for name, dsl, _ in SINGLE_FILE_FIXTURES:
        codes, _, _ = _collect_codes_from_dsl(dsl)
        bad = [c for c in codes if c in lookup_api_codes]
        assert not bad, (
            f'fixture {name}: static pipeline emitted lookup_api code(s) {bad}; '
            f'these codes must only surface through ``resolve_event`` API calls.'
        )


@pytest.mark.unittest
def test_partial_static_pipeline_codes_dont_fire_on_pyfcstm():
    """I-b sibling: E_TYPE_MISMATCH is currently ``emit_tier:
    partial_static_pipeline`` — jsfcstm has an analyzer that emits it
    on type-confused expressions, pyfcstm has no such analyzer. This
    test pins the "pyfcstm doesn't fire it" half so downstream
    consumers know not to expect it from the Python side.
    """
    from pyfcstm.diagnostics import CODE_REGISTRY

    partial_codes = {
        code
        for code, spec in CODE_REGISTRY.items()
        if spec.emit_tier == 'partial_static_pipeline'
    }
    if not partial_codes:
        pytest.skip('no partial_static_pipeline codes declared')

    for name, dsl, _ in SINGLE_FILE_FIXTURES:
        codes, _, _ = _collect_codes_from_dsl(dsl)
        leaked = [c for c in codes if c in partial_codes]
        assert not leaked, (
            f'fixture {name}: pyfcstm emitted partial_static_pipeline code(s) {leaked}; '
            f'these are currently implemented only on jsfcstm.'
        )
