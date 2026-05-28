"""
Fixture-driven tests that verify
:func:`pyfcstm.model.parse_dsl_node_to_state_machine` emits the right
structured :class:`pyfcstm.utils.validate.ModelDiagnostic` for each of the
14 ``E_*`` codes registered in ``pyfcstm/diagnostics/codes.yaml``.

PR-2 of the Layer 1 structured-diagnostic refactor (see issue #103)
guarantees:

1. Every legacy ``raise SyntaxError`` site in ``model.py`` is replaced by
   ``sink.emit(ModelDiagnostic(code=..., severity='error', message=...,
   refs=...))``.
2. Strict-mode callers (the default, ``collect=False``) still get
   :class:`pyfcstm.utils.validate.ModelValidationError`, which multi-
   inherits from :class:`SyntaxError` for backwards compatibility. The
   PR-0 baseline (``test/model/test_error_baseline.py``) checks the
   substring contract.
3. ``collect=True`` returns ``(model_or_None, diagnostics)`` so callers
   that want every error in one pass (IDE, LLM agent loop) can have them.

Each test below pairs a minimal DSL snippet with assertions on
``diag.code`` / ``diag.refs`` keys to lock the structured payload contract
that downstream consumers (``research_ideas`` ``SemanticFeedback``
schema) read.
"""

import pytest

from pyfcstm.diagnostics import CODE_REGISTRY
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.utils import ModelDiagnostic, ModelValidationError, Span


def _collect(dsl_text: str):
    ast = parse_with_grammar_entry(dsl_text, entry_name='state_machine_dsl')
    return parse_dsl_node_to_state_machine(ast, collect=True)


def _strict_diag(dsl_text: str) -> ModelDiagnostic:
    """Run in strict mode, expect raise, return the first diagnostic."""
    ast = parse_with_grammar_entry(dsl_text, entry_name='state_machine_dsl')
    with pytest.raises(ModelValidationError) as info:
        parse_dsl_node_to_state_machine(ast)
    assert info.value.diagnostics, "expected at least one diagnostic"
    return info.value.diagnostics[0]


def _assert_refs_match_schema(diag: ModelDiagnostic) -> None:
    """The diagnostic's ``refs`` must only carry keys declared in the
    ``codes.yaml`` schema, and every required key must be present."""
    spec = CODE_REGISTRY.get(diag.code)
    assert spec is not None, f"unknown code {diag.code!r}"
    declared = set(spec.refs_schema.keys())
    actual = set(diag.refs.keys())
    extra = actual - declared
    assert not extra, (
        f"{diag.code} refs has extra keys {extra} not in codes.yaml schema"
    )
    required = set(spec.required_fields())
    missing = required - actual
    assert not missing, (
        f"{diag.code} refs missing required keys {missing}"
    )


@pytest.mark.unittest
class TestEUndefinedVar:
    def test_undefined_in_guard(self):
        diag = _strict_diag("""
def int x = 0;
state Root {
    state A; state B;
    A -> B : if [unknown > 0];
}
""")
        assert diag.code == 'E_UNDEFINED_VAR'
        assert diag.refs['var_name'] == ['unknown']
        assert diag.refs['referenced_in'] == 'guard'
        _assert_refs_match_schema(diag)

    def test_undefined_in_force_transition_guard(self):
        diag = _strict_diag("""
def int x = 0;
state Root {
    state A; state B;
    !A -> B : if [unknown > 0];
}
""")
        assert diag.code == 'E_UNDEFINED_VAR'
        assert diag.refs['referenced_in'] == 'guard'

    def test_undefined_in_effect(self):
        # ``x = unknown + 1`` references ``unknown`` on the RHS, which must
        # already exist. ``x = 1`` style is *not* used because the DSL
        # treats LHS-only undeclared names as block-local temporaries.
        diag = _strict_diag("""
def int x = 0;
state Root {
    state A; state B;
    [*] -> A;
    A -> B effect { x = unknown + 1; };
}
""")
        assert diag.code == 'E_UNDEFINED_VAR'
        assert diag.refs['referenced_in'] == 'effect'

    def test_undefined_in_enter(self):
        diag = _strict_diag("""
def int x = 0;
state Root {
    state A {
        enter { x = unknown + 1; }
    }
    [*] -> A;
}
""")
        assert diag.code == 'E_UNDEFINED_VAR'
        assert diag.refs['referenced_in'] == 'enter'

    def test_undefined_in_exit(self):
        diag = _strict_diag("""
def int x = 0;
state Root {
    state A {
        exit { x = unknown + 1; }
    }
    [*] -> A;
}
""")
        assert diag.code == 'E_UNDEFINED_VAR'
        assert diag.refs['referenced_in'] == 'exit'

    def test_undefined_in_during_leaf(self):
        diag = _strict_diag("""
def int x = 0;
state Root {
    state A {
        during { x = unknown + 1; }
    }
    [*] -> A;
}
""")
        assert diag.code == 'E_UNDEFINED_VAR'
        assert diag.refs['referenced_in'] == 'during'


@pytest.mark.unittest
class TestEDuplicateVar:
    def test_two_defs_same_name(self):
        diag = _strict_diag("""
def int x = 0;
def int x = 1;
state Root { state A; }
""")
        assert diag.code == 'E_DUPLICATE_VAR'
        assert diag.refs['var_name'] == 'x'
        # previous_span should anchor at the first declaration
        assert diag.refs['previous_span'] is not None
        prev = diag.refs['previous_span']
        assert isinstance(prev, Span)
        # Diagnostic span anchors at the duplicate, prev_span at line above.
        assert diag.span is not None
        assert prev.line < diag.span.line
        _assert_refs_match_schema(diag)


@pytest.mark.unittest
class TestEMissingState:
    def test_event_path_state_unresolved(self):
        # Targets a chain-id event referencing a non-existent state.
        diag = _strict_diag("""
state Root {
    state A; state B;
    A -> B : /NoSuch.GoEvent;
}
""")
        assert diag.code == 'E_MISSING_STATE'
        assert 'state_path' in diag.refs
        assert diag.refs['reason'] == 'event_path_not_found'
        _assert_refs_match_schema(diag)


@pytest.mark.unittest
class TestEDuplicateState:
    def test_two_states_same_name(self):
        diag = _strict_diag("""
state Root {
    state A;
    state A;
}
""")
        assert diag.code == 'E_DUPLICATE_STATE'
        assert diag.refs['state_name'] == 'A'
        assert diag.refs['parent_path'].endswith('Root')
        _assert_refs_match_schema(diag)


@pytest.mark.unittest
class TestEDanglingTransition:
    def test_unknown_to_state(self):
        diag = _strict_diag("""
state Root {
    state A;
    A -> NoSuch;
}
""")
        assert diag.code == 'E_DANGLING_TRANSITION'
        assert diag.refs['tgt'] == 'NoSuch'
        assert diag.refs['reason'] == 'tgt_not_found'
        _assert_refs_match_schema(diag)


@pytest.mark.unittest
class TestEPseudoNotLeaf:
    def test_pseudo_with_substates(self):
        # ``pseudo state X { state Y; ... }`` — pseudo states must be leaves.
        diag = _strict_diag("""
state Root {
    pseudo state Outer {
        state Inner;
        [*] -> Inner;
    }
    [*] -> Outer;
}
""")
        assert diag.code == 'E_PSEUDO_NOT_LEAF'
        assert 'state_path' in diag.refs
        _assert_refs_match_schema(diag)


@pytest.mark.unittest
class TestEDuringAspectInvalid:
    def test_leaf_state_with_aspect(self):
        # Leaf state must NOT carry a during aspect.
        diag = _strict_diag("""
state Root {
    state A {
        during before { }
    }
}
""")
        assert diag.code == 'E_DURING_ASPECT_INVALID'
        assert diag.refs['state_kind'] == 'leaf'
        assert diag.refs['aspect'] == 'before'
        _assert_refs_match_schema(diag)

    def test_composite_without_aspect(self):
        # Composite state must carry an aspect when it has `during`.
        diag = _strict_diag("""
state Root {
    state Outer {
        during { }
        state Inner;
        [*] -> Inner;
    }
    [*] -> Outer;
}
""")
        assert diag.code == 'E_DURING_ASPECT_INVALID'
        assert diag.refs['state_kind'] == 'composite'
        assert diag.refs['aspect'] is None


@pytest.mark.unittest
class TestEDuplicateFunctionName:
    def test_duplicate_enter_name(self):
        diag = _strict_diag("""
state Root {
    state A {
        enter F1 { }
        enter F1 { }
    }
}
""")
        assert diag.code == 'E_DUPLICATE_FUNCTION_NAME'
        assert diag.refs['function_name'] == 'F1'
        assert diag.refs['stage'] == 'enter'
        _assert_refs_match_schema(diag)


@pytest.mark.unittest
class TestEInitialTransitionInvalid:
    def test_composite_missing_entry(self):
        diag = _strict_diag("""
state Root {
    state Outer {
        state Inner;
    }
}
""")
        assert diag.code == 'E_INITIAL_TRANSITION_INVALID'
        assert diag.refs['reason'] == 'missing_entry'
        _assert_refs_match_schema(diag)


@pytest.mark.unittest
class TestEForcedTransitionExpansion:
    def test_force_unknown_from_state(self):
        diag = _strict_diag("""
state Root {
    state A;
    !NoSuch -> A;
}
""")
        assert diag.code == 'E_FORCED_TRANSITION_EXPANSION'
        assert diag.refs['reason'] == 'src_not_found'
        _assert_refs_match_schema(diag)


@pytest.mark.unittest
class TestENamedFunctionRefNotFound:
    def test_named_ref_state_not_found(self):
        diag = _strict_diag("""
state Root {
    state A {
        enter ref NoSuch.NoSuch;
    }
}
""")
        assert diag.code == 'E_NAMED_FUNCTION_REF_NOT_FOUND'
        assert diag.refs['reason'] == 'state_not_found'
        _assert_refs_match_schema(diag)


@pytest.mark.unittest
class TestCollectMode:
    def test_collect_returns_tuple(self):
        machine, diags = _collect("""
state Root {
    state A;
    state A;
}
""")
        # `machine` may or may not be None depending on how far parsing got;
        # diagnostics list must carry the duplicate-state error.
        codes = [d.code for d in diags]
        assert 'E_DUPLICATE_STATE' in codes

    def test_collect_gathers_multiple_distinct_errors(self):
        # Two completely independent errors in one DSL — collect mode must
        # surface both, strict mode raises on the first.
        machine, diags = _collect("""
def int x = 0;
def int x = 1;
state Root {
    state A;
    state A;
}
""")
        codes = [d.code for d in diags]
        assert 'E_DUPLICATE_VAR' in codes
        assert 'E_DUPLICATE_STATE' in codes

    def test_strict_mode_raises_on_first(self):
        # Same DSL as above, strict mode aborts at the first issue. The
        # raised exception still carries the first diagnostic in its
        # `diagnostics` list.
        ast = parse_with_grammar_entry("""
def int x = 0;
def int x = 1;
state Root {
    state A;
    state A;
}
""", entry_name='state_machine_dsl')
        with pytest.raises(ModelValidationError) as info:
            parse_dsl_node_to_state_machine(ast)
        assert len(info.value.diagnostics) == 1
        assert info.value.diagnostics[0].code == 'E_DUPLICATE_VAR'

    def test_strict_caught_via_syntax_error(self):
        # Backwards-compat: `ModelValidationError` multi-inherits
        # `SyntaxError`, so downstream code catching the plain
        # `SyntaxError` keeps working after PR-2.
        ast = parse_with_grammar_entry("""
def int x = 0;
def int x = 1;
state Root { state A; }
""", entry_name='state_machine_dsl')
        with pytest.raises(SyntaxError) as info:
            parse_dsl_node_to_state_machine(ast)
        assert info.value.diagnostics[0].code == 'E_DUPLICATE_VAR'


@pytest.mark.unittest
class TestI1FirstWinsNamedFunction:
    """
    I1 from PR-110 review: in strict mode the duplicate-named-function
    raise prevents the subsequent overwrite of ``named_functions[name]``;
    in collect mode the overwrite still happens, so "last wins" silently
    flips. Pin "first wins" as the canonical tiebreaker across both modes.
    """

    def test_collect_mode_named_function_first_wins_enter(self):
        machine, diags = _collect("""
state Root {
    state A {
        enter F1 { }
        enter F1 { }
    }
    [*] -> A;
}
""")
        # Both stages emit the duplicate-function diagnostic.
        dup = [d for d in diags if d.code == 'E_DUPLICATE_FUNCTION_NAME']
        assert len(dup) >= 1

        # The named_functions map under state A must point at the FIRST
        # declaration (first wins), so a `ref F1` resolves consistently
        # with strict mode's "abort on duplicate before overwrite".
        a = machine.root_state.substates['A']
        first_decl = a.on_enters[0]
        assert a.named_functions['F1'] is first_decl

    def test_collect_mode_named_function_first_wins_during(self):
        machine, diags = _collect("""
state Root {
    state Outer {
        during before { }
        state Inner {
            during D1 { }
            during D1 { }
        }
        [*] -> Inner;
    }
    [*] -> Outer;
}
""")
        inner = machine.root_state.substates['Outer'].substates['Inner']
        first_decl = inner.on_durings[0]
        assert inner.named_functions['D1'] is first_decl


@pytest.mark.unittest
class TestI2DanglingTransitionBothNotFound:
    """
    I2 from PR-110 review: when both ``from_state`` and ``to_state`` of a
    transition are unresolved, codes.yaml declares ``reason='both_not_found'``
    but the emit logic produces two separate diagnostics (one
    ``src_not_found`` + one ``tgt_not_found``). Collapse to a single
    diagnostic carrying ``reason='both_not_found'`` so downstream
    consumers don't double-count one broken transition.
    """

    def test_both_sides_unknown_emits_single_both_not_found(self):
        machine, diags = _collect("""
state Root {
    state A;
    NoSrc -> NoTgt;
}
""")
        dangling = [d for d in diags if d.code == 'E_DANGLING_TRANSITION']
        assert len(dangling) == 1, (
            f"expected 1 E_DANGLING_TRANSITION, got {len(dangling)}: "
            f"{[d.refs for d in dangling]}"
        )
        d = dangling[0]
        assert d.refs['reason'] == 'both_not_found'
        assert d.refs['src'] == 'NoSrc'
        assert d.refs['tgt'] == 'NoTgt'

    def test_only_src_unknown_still_emits_src_not_found(self):
        diag = _strict_diag("""
state Root {
    state Target;
    NoSrc -> Target;
}
""")
        assert diag.code == 'E_DANGLING_TRANSITION'
        assert diag.refs['reason'] == 'src_not_found'

    def test_only_tgt_unknown_still_emits_tgt_not_found(self):
        diag = _strict_diag("""
state Root {
    state Source;
    Source -> NoTgt;
}
""")
        assert diag.code == 'E_DANGLING_TRANSITION'
        assert diag.refs['reason'] == 'tgt_not_found'


@pytest.mark.unittest
class TestI3ForceTransitionFailureContinues:
    """
    I3 from PR-110 review: failed src/tgt resolution still appends the
    broken tuple to ``force_transition_tuples_to_inherit``. The bad
    string later mismatches ``ALL`` and any real substate name, so the
    inheritance phase silently drops the transition — on top of the
    diagnostic — but the bad string also lingers in the tuple list and
    risks downstream defensive-validation logic getting confused.

    After the fix, a failed force-transition must not appear in any form
    in the partial model (apart from the diagnostic itself).
    """

    def _walk_states(self, machine):
        if machine is None:
            return
        def _go(s):
            yield s
            for c in s.substates.values():
                yield from _go(c)
        yield from _go(machine.root_state)

    def test_force_transition_with_bad_src_does_not_pollute_transitions(self):
        machine, diags = _collect("""
state Root {
    state A;
    state B;
    !NoSrc -> A;
    [*] -> A;
}
""")
        ftd = [d for d in diags if d.code == 'E_FORCED_TRANSITION_EXPANSION']
        assert ftd, "missing E_FORCED_TRANSITION_EXPANSION"
        # No state in the machine should carry a transition whose
        # from_state matches the bad source.
        for state in self._walk_states(machine):
            for trans in state.transitions:
                assert getattr(trans, 'from_state', None) != 'NoSrc', (
                    f"phantom transition with from_state='NoSrc' leaked "
                    f"into state {'.'.join(state.path)!r}"
                )

    def test_force_transition_with_bad_tgt_does_not_pollute_transitions(self):
        machine, diags = _collect("""
state Root {
    state A;
    state B;
    !A -> NoTgt;
    [*] -> A;
}
""")
        ftd = [d for d in diags if d.code == 'E_FORCED_TRANSITION_EXPANSION']
        assert ftd, "missing E_FORCED_TRANSITION_EXPANSION"
        # Bad to_state must not propagate as a real Transition in any
        # state's transitions list.
        for state in self._walk_states(machine):
            for trans in state.transitions:
                assert trans.to_state != 'NoTgt', (
                    f"phantom transition with to_state='NoTgt' leaked "
                    f"into state {'.'.join(state.path)!r}"
                )


@pytest.mark.unittest
class TestI4UndefinedVarStatePath:
    """
    I4 from PR-110 review: E_UNDEFINED_VAR.refs.state_path is the
    downstream-required field that tells LLM repair agents "which state
    owns this block". For block-bound contexts (enter/during/exit/
    during_aspect), the parser has ``current_path`` available locally
    and must populate it.

    Guard sites on transitions stay None since the offending block is
    not state-owned per se.
    """

    def test_undefined_in_enter_block_carries_state_path(self):
        diag = _strict_diag("""
def int x = 0;
state Root {
    state A {
        enter { x = unknown + 1; }
    }
    [*] -> A;
}
""")
        assert diag.code == 'E_UNDEFINED_VAR'
        assert diag.refs.get('state_path') == 'Root.A'

    def test_undefined_in_during_block_carries_state_path(self):
        diag = _strict_diag("""
def int x = 0;
state Root {
    state A {
        during { x = unknown + 1; }
    }
    [*] -> A;
}
""")
        assert diag.code == 'E_UNDEFINED_VAR'
        assert diag.refs.get('state_path') == 'Root.A'

    def test_undefined_in_exit_block_carries_state_path(self):
        diag = _strict_diag("""
def int x = 0;
state Root {
    state A {
        exit { x = unknown + 1; }
    }
    [*] -> A;
}
""")
        assert diag.code == 'E_UNDEFINED_VAR'
        assert diag.refs.get('state_path') == 'Root.A'

    def test_undefined_in_during_aspect_block_carries_state_path(self):
        diag = _strict_diag("""
def int x = 0;
state Root {
    state Outer {
        during before { x = unknown + 1; }
        state Inner;
        [*] -> Inner;
    }
    [*] -> Outer;
}
""")
        assert diag.code == 'E_UNDEFINED_VAR'
        assert diag.refs.get('state_path') == 'Root.Outer'


@pytest.mark.unittest
class TestI5EmitHelperPreservesContext:
    """
    I5 from PR-110 review: ``_emit(None, ...)`` raises with
    ``diagnostics=[diagnostic]`` only, losing any previously accumulated
    warnings or earlier diagnostics. The semantically equivalent
    ``DiagnosticSink.emit`` (in strict mode) raises with the full
    accumulated list. Callers shouldn't have to track which path is
    "context-preserving".

    The fix is to make ``_emit`` accept an optional ``prior`` list (or
    drop the helper entirely as unused). This test pins the API:
    ``_emit`` either preserves a prior list passed alongside, or
    ``None``-sink raise carries the single diagnostic but documents the
    asymmetry by accepting a ``prior_diagnostics`` kwarg.
    """

    def test_emit_with_none_sink_accepts_prior_diagnostics(self):
        from pyfcstm.diagnostics.sink import _emit
        from pyfcstm.utils import ModelDiagnostic
        prior = [
            ModelDiagnostic(code='W_X', severity='warning', message='early'),
        ]
        with pytest.raises(ModelValidationError) as info:
            _emit(None, ModelDiagnostic(
                code='E_X', severity='error', message='boom',
            ), prior_diagnostics=prior)
        codes = [d.code for d in info.value.diagnostics]
        assert codes == ['W_X', 'E_X']

    def test_emit_with_none_sink_default_no_prior(self):
        # Backwards-compat: existing callers that don't pass prior just
        # raise with the single diagnostic.
        from pyfcstm.diagnostics.sink import _emit
        from pyfcstm.utils import ModelDiagnostic
        with pytest.raises(ModelValidationError) as info:
            _emit(None, ModelDiagnostic(
                code='E_X', severity='error', message='boom',
            ))
        codes = [d.code for d in info.value.diagnostics]
        assert codes == ['E_X']


@pytest.mark.unittest
class TestEmitMatchesEnum:
    """
    C2 from PR-110 review: every ``refs[field]`` value emitted from a real
    DSL fixture must be a member of the ``enum`` declared for that field
    in codes.yaml. Schema documentation is documentation-only; the only
    way to keep emitters honest is to drive them through fixtures and
    assert membership.

    These tests would catch the original drift where ``E_MISSING_STATE``
    was emitting ``reason='event_path_not_found'`` against an enum that
    only allowed ``'not_found' | 'parent_missing' | 'ambiguous'``.
    """

    # (fixture_dsl, expected_code, refs_assertions)
    # refs_assertions is a list of (field_name, expected_value_or_None)
    # where None means "just assert the field is present".
    ENUM_FIXTURES = [
        # E_MISSING_STATE — normal transition through bad event path
        (
            """
state Root {
    state A; state B;
    [*] -> A;
    A -> B : /NoSuch.GhostEvt;
}
""",
            'E_MISSING_STATE',
            [('reason', None)],  # whatever reason it emits must be in enum
        ),
        # E_DANGLING_TRANSITION — unknown to-state
        (
            """
state Root {
    state A;
    A -> NoSuch;
}
""",
            'E_DANGLING_TRANSITION',
            [('reason', None)],
        ),
        # E_FORCED_TRANSITION_EXPANSION — unknown src
        (
            """
state Root {
    state A;
    !NoSuch -> A;
}
""",
            'E_FORCED_TRANSITION_EXPANSION',
            [('reason', None)],
        ),
        # E_INITIAL_TRANSITION_INVALID — composite missing entry
        (
            """
state Root {
    state Outer {
        state Inner;
    }
}
""",
            'E_INITIAL_TRANSITION_INVALID',
            [('reason', None)],
        ),
        # E_NAMED_FUNCTION_REF_NOT_FOUND — bare-name unresolved
        (
            """
state Root {
    state A {
        enter ref MissingFunc;
    }
    [*] -> A;
}
""",
            'E_NAMED_FUNCTION_REF_NOT_FOUND',
            [('reason', None)],
        ),
        # E_DURING_ASPECT_INVALID — leaf state with aspect
        (
            """
state Root {
    state A {
        during before { }
    }
}
""",
            'E_DURING_ASPECT_INVALID',
            [('state_kind', None)],
        ),
        # E_UNDEFINED_VAR — referenced_in tag
        (
            """
def int x = 0;
state Root {
    state A; state B;
    [*] -> A;
    A -> B : if [unknown > 0];
}
""",
            'E_UNDEFINED_VAR',
            [('referenced_in', None)],
        ),
        # E_DUPLICATE_FUNCTION_NAME — stage tag
        (
            """
state Root {
    state A {
        enter F1 { }
        enter F1 { }
    }
    [*] -> A;
}
""",
            'E_DUPLICATE_FUNCTION_NAME',
            [('stage', None)],
        ),
    ]

    @pytest.mark.parametrize(
        'dsl,expected_code,refs_assertions',
        ENUM_FIXTURES,
        ids=[f[1] + '_' + str(i) for i, f in enumerate(ENUM_FIXTURES)],
    )
    def test_emitted_refs_values_are_in_declared_enum(
            self, dsl, expected_code, refs_assertions):
        """For every enumerated field the emitter populates, the value
        must be a member of the schema's declared enum (if any)."""
        diag = _strict_diag(dsl)
        assert diag.code == expected_code
        spec = CODE_REGISTRY[diag.code]
        for field_name, _ in refs_assertions:
            field_spec = spec.refs_schema[field_name]
            declared_enum = field_spec.enum
            if declared_enum is None:
                continue  # no enum constraint for this field
            actual = diag.refs.get(field_name)
            assert actual in declared_enum, (
                f"code {diag.code} field {field_name!r}: emitted value "
                f"{actual!r} is not in declared enum {declared_enum}"
            )


@pytest.mark.unittest
class TestCollectModeNoPhantomMutation:
    """
    C1 from PR-110 review: in collect mode, ``sink.emit(E_MISSING_STATE)``
    no longer raises — but the code immediately below the segment-walk
    falls through and inserts a fabricated ``Event`` into whatever state
    the walk got stuck on (usually root or the last good parent).

    The "best-effort partial model" returned by collect mode must not be
    silently polluted with events the user never wrote. These tests assert
    no phantom events appear in any state's ``events`` dict after a bad
    event-id path triggers ``E_MISSING_STATE``.
    """

    def _walk_states(self, machine):
        # Recursive walker that yields every State in the model.
        def _go(s):
            yield s
            for child in s.substates.values():
                yield from _go(child)
        if machine is None:
            return
        yield from _go(machine.root_state)

    def test_normal_transition_bad_event_path_no_phantom_event(self):
        machine, diags = _collect("""
state Root {
    state A; state B;
    [*] -> A;
    A -> B : /NoSuch.GhostEvent;
}
""")
        codes = [d.code for d in diags]
        assert 'E_MISSING_STATE' in codes
        # No state in the partial model should carry a phantom 'GhostEvent'.
        for state in self._walk_states(machine):
            assert 'GhostEvent' not in state.events, (
                f"phantom event 'GhostEvent' leaked into state "
                f"{'.'.join(state.path)!r} after E_MISSING_STATE in collect mode"
            )

    def test_force_transition_bad_event_path_no_phantom_event(self):
        machine, diags = _collect("""
state Root {
    state A; state B;
    [*] -> A;
    !A -> B : /NoSuch.GhostEvent;
}
""")
        codes = [d.code for d in diags]
        assert 'E_MISSING_STATE' in codes
        for state in self._walk_states(machine):
            assert 'GhostEvent' not in state.events, (
                f"phantom event 'GhostEvent' leaked into state "
                f"{'.'.join(state.path)!r} after E_MISSING_STATE in force "
                f"transition collect mode"
            )

    def test_phantom_does_not_create_follow_on_diagnostics(self):
        """A phantom event under the wrong parent would let downstream
        transitions in the same pass match it and skip further error
        reporting — assert the diagnostic list stays minimal."""
        machine, diags = _collect("""
state Root {
    state A; state B;
    [*] -> A;
    A -> B : /NoSuch.GhostEvent;
    A -> B : /AlsoNoSuch.OtherEvent;
}
""")
        # Both bad transitions must each surface their own diagnostic; if
        # the first one polluted state.events, the second's resolution
        # logic might find a phantom and silently succeed.
        missing_diags = [d for d in diags if d.code == 'E_MISSING_STATE']
        assert len(missing_diags) >= 2, (
            f"expected 2 distinct E_MISSING_STATE, got "
            f"{[d.refs.get('state_path') for d in missing_diags]}"
        )


@pytest.mark.unittest
class TestSpanPropagation:
    def test_duplicate_var_carries_span(self):
        diag = _strict_diag("""
def int x = 0;
def int x = 1;
state Root { state A; }
""")
        assert diag.span is not None
        # The duplicate is on line 3 of the DSL (after the leading blank).
        assert diag.span.line == 3

    def test_duplicate_state_carries_span(self):
        diag = _strict_diag("""
state Root {
    state A;
    state A;
}
""")
        assert diag.span is not None
        # The duplicate state line is the 4th line.
        assert diag.span.line == 4

    def test_collect_mode_continues_past_event_path_failure(self):
        # In collect mode, the sink doesn't raise — the loop hits ``break``
        # to skip the rest of the bad event chain and keep walking the
        # rest of the model. Exercises the safety ``break`` after the
        # ``E_MISSING_STATE`` emit in the transition event-id walk.
        machine, diags = _collect("""
def int x = 0;
state Root {
    state A; state B;
    [*] -> A;
    A -> B : /NoSuch.Event;
    A -> B : if [unknown > 0];
}
""")
        codes = {d.code for d in diags}
        assert 'E_MISSING_STATE' in codes
        # The guard's E_UNDEFINED_VAR must still surface, proving the
        # event-id failure didn't short-circuit the whole pass.
        assert 'E_UNDEFINED_VAR' in codes

    def test_collect_mode_continues_past_force_transition_event_path_failure(self):
        machine, diags = _collect("""
def int x = 0;
state Root {
    state A; state B;
    [*] -> A;
    !A -> B : /NoSuch.Evt;
    A -> B : if [unknown > 0];
}
""")
        codes = {d.code for d in diags}
        assert 'E_MISSING_STATE' in codes
        assert 'E_UNDEFINED_VAR' in codes

    def test_collect_mode_continues_past_named_ref_state_not_found(self):
        # ``walk_failed = True; break; if walk_failed: continue`` — exercise
        # the named-function ref walk that needs to skip a broken ref
        # without crashing the whole pass.
        machine, diags = _collect("""
state Root {
    state A {
        enter ref NoSuch.Other.Foo;
    }
    state B {
        enter ref MoreMissing.Bar;
    }
    [*] -> A;
}
""")
        codes = [d.code for d in diags]
        # Both refs are unresolved — collect mode must surface both.
        assert codes.count('E_NAMED_FUNCTION_REF_NOT_FOUND') >= 2

    def test_collect_mode_named_function_not_found_continues(self):
        # The terminal ``continue`` after ``E_NAMED_FUNCTION_REF_NOT_FOUND``
        # with reason 'named_function_not_found' — ref walks past the state
        # tree successfully but the leaf name isn't a named action. A
        # bare-name relative ref resolves through the state tree and only
        # fails on the leaf segment.
        machine, diags = _collect("""
state Root {
    state A {
        enter ref Missing1;
    }
    state B {
        enter ref Missing2;
    }
    [*] -> A;
}
""")
        nf_diags = [d for d in diags if d.code == 'E_NAMED_FUNCTION_REF_NOT_FOUND']
        assert len(nf_diags) >= 2
        for d in nf_diags:
            assert d.refs['reason'] == 'named_function_not_found'

    def test_e_lineno_via_syntax_error_interface(self):
        # The SyntaxError 4-tuple maps (line, column) from the first
        # diagnostic with a span. Downstream `except SyntaxError as e:
        # e.lineno` keeps working.
        ast = parse_with_grammar_entry("""
def int x = 0;
def int x = 1;
state Root { state A; }
""", entry_name='state_machine_dsl')
        with pytest.raises(SyntaxError) as info:
            parse_dsl_node_to_state_machine(ast)
        assert info.value.lineno == 3
