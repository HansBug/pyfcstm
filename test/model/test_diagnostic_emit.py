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
