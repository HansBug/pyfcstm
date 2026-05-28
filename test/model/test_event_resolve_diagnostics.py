"""
PR-3 (issue #103) tests: ``State.resolve_event`` / ``StateMachine.resolve_event``
now raise structured :class:`pyfcstm.utils.validate.ModelValueError` /
:class:`pyfcstm.utils.validate.ModelLookupError` carrying
:class:`pyfcstm.utils.validate.ModelDiagnostic` objects, and accept an
optional ``collect_into=`` :class:`pyfcstm.diagnostics.DiagnosticSink`
parameter for accumulator-style resolution.

These tests pin down:

1. Both new exception classes multi-inherit ``ValueError`` / ``LookupError``
   AND ``SyntaxError`` (via ``ModelValidationError``), preserving the
   pre-PR-3 catch surface for every existing
   ``except ValueError:`` / ``except LookupError:`` / ``except SyntaxError:``
   handler.
2. The structured diagnostic on every failure path uses the correct
   ``code`` (``E_EVENT_REF_INVALID`` or ``E_EVENT_NOT_FOUND``) and a
   ``refs`` payload that conforms to the codes.yaml enum for ``reason``
   (E_EVENT_REF_INVALID) or ``scope`` (E_EVENT_NOT_FOUND).
3. The ``collect_into`` sink injection accumulates failures and returns
   ``None`` instead of raising — letting downstream IDE / agent-loop
   integrations harvest every diagnostic in one pass.
"""

import pytest

from pyfcstm.diagnostics import CODE_REGISTRY, DiagnosticSink
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.utils.validate import (
    ModelDiagnostic,
    ModelLookupError,
    ModelValidationError,
    ModelValueError,
)


@pytest.fixture()
def machine():
    src = """
def int x = 0;
state Root {
    state Inner {
        state Leaf;
        [*] -> Leaf;
        event Done;
    }
    state Other;
    event Go;
    [*] -> Inner;
}
"""
    ast = parse_with_grammar_entry(src, entry_name='state_machine_dsl')
    return parse_dsl_node_to_state_machine(ast)


def _assert_refs_match_schema(diag: ModelDiagnostic) -> None:
    spec = CODE_REGISTRY[diag.code]
    declared = set(spec.refs_schema.keys())
    actual = set(diag.refs.keys())
    extra = actual - declared
    assert not extra, (
        f"{diag.code} refs has extra keys {extra} not in codes.yaml schema"
    )
    for name, value in diag.refs.items():
        field_spec = spec.refs_schema[name]
        if field_spec.enum is None or value is None:
            continue
        assert value in field_spec.enum, (
            f"{diag.code}.refs[{name}!r] = {value!r} not in enum {field_spec.enum}"
        )


@pytest.mark.unittest
class TestExceptionHierarchy:
    """The new typed exceptions must preserve every existing catch."""

    def test_model_value_error_is_value_error(self):
        e = ModelValueError(diagnostics=[ModelDiagnostic(
            code='E_EVENT_REF_INVALID', severity='error', message='m',
            refs={'event_ref': 'x', 'reason': 'empty'},
        )])
        assert isinstance(e, ValueError)
        assert isinstance(e, ModelValidationError)
        assert isinstance(e, SyntaxError)  # via ModelValidationError -> SyntaxError

    def test_model_lookup_error_is_lookup_error(self):
        e = ModelLookupError(diagnostics=[ModelDiagnostic(
            code='E_EVENT_NOT_FOUND', severity='error', message='m',
            refs={'event_ref': 'x', 'scope': 'absolute'},
        )])
        assert isinstance(e, LookupError)
        assert isinstance(e, ModelValidationError)
        assert isinstance(e, SyntaxError)

    def test_caught_via_legacy_value_error_handler(self, machine):
        # Pre-PR-3 code: ``except ValueError as e: ...`` — must still catch.
        with pytest.raises(ValueError) as info:
            machine.root_state.resolve_event('')
        assert isinstance(info.value, ModelValueError)
        assert info.value.diagnostics[0].code == 'E_EVENT_REF_INVALID'

    def test_caught_via_legacy_lookup_error_handler(self, machine):
        with pytest.raises(LookupError) as info:
            machine.root_state.resolve_event('NoSuch.NoEvt')
        assert isinstance(info.value, ModelLookupError)
        assert info.value.diagnostics[0].code == 'E_EVENT_NOT_FOUND'

    def test_caught_via_syntax_error_handler(self, machine):
        # PR-2 multi-inheritance contract: ``except SyntaxError:`` must catch.
        with pytest.raises(SyntaxError) as info:
            machine.root_state.resolve_event('')
        assert isinstance(info.value, ModelValueError)


@pytest.mark.unittest
class TestStateResolveEventRefInvalid:
    """Each ``reason`` enum value of E_EVENT_REF_INVALID has a fixture."""

    @pytest.mark.parametrize('event_ref,reason', [
        ('', 'empty'),
        ('/', 'bare_slash'),
        ('/foo..bar', 'invalid_absolute'),
        ('.', 'trailing_dots'),
        ('foo..bar', 'invalid_relative'),
    ])
    def test_invalid_reason_dispatch_from_root(self, machine, event_ref, reason):
        with pytest.raises(ModelValueError) as info:
            machine.root_state.resolve_event(event_ref)
        diag = info.value.diagnostics[0]
        assert diag.code == 'E_EVENT_REF_INVALID'
        assert diag.refs['reason'] == reason
        assert diag.refs['event_ref'] == event_ref
        _assert_refs_match_schema(diag)

    def test_invalid_relative_via_parent_form(self, machine):
        # The parent-relative form (``.foo..bar``) only reaches the
        # ``invalid_relative`` branch when ``dot_count`` doesn't exhaust
        # the root chain. From ``Root.Inner`` one leading dot consumes
        # the level up to ``Root`` and the remaining ``foo..bar`` splits
        # to ['foo', '', 'bar'], failing the ``all(parts)`` check.
        inner = machine.root_state.substates['Inner']
        with pytest.raises(ModelValueError) as info:
            inner.resolve_event('.foo..bar')
        diag = info.value.diagnostics[0]
        assert diag.code == 'E_EVENT_REF_INVALID'
        assert diag.refs['reason'] == 'invalid_relative'
        _assert_refs_match_schema(diag)

    def test_beyond_root_at_state_inner(self, machine):
        # Inner is at depth 2 (Root.Inner). Going up 5 levels exceeds root.
        inner = machine.root_state.substates['Inner']
        with pytest.raises(ModelValueError) as info:
            inner.resolve_event('.....Foo')
        diag = info.value.diagnostics[0]
        assert diag.code == 'E_EVENT_REF_INVALID'
        assert diag.refs['reason'] == 'beyond_root'
        _assert_refs_match_schema(diag)


@pytest.mark.unittest
class TestStateResolveEventNotFound:
    """Each ``scope`` enum value of E_EVENT_NOT_FOUND has a fixture."""

    def test_absolute_scope_state_missing(self, machine):
        with pytest.raises(ModelLookupError) as info:
            machine.root_state.resolve_event('/NoSuch.Go')
        diag = info.value.diagnostics[0]
        assert diag.code == 'E_EVENT_NOT_FOUND'
        assert diag.refs['scope'] == 'absolute'
        _assert_refs_match_schema(diag)

    def test_absolute_scope_event_missing(self, machine):
        # The state path resolves but the event name doesn't exist.
        with pytest.raises(ModelLookupError) as info:
            machine.root_state.resolve_event('/Inner.NoSuchEvent')
        diag = info.value.diagnostics[0]
        assert diag.code == 'E_EVENT_NOT_FOUND'
        assert diag.refs['scope'] == 'absolute'

    def test_chain_scope_state_missing(self, machine):
        # ``.`` form (one dot) — chain scope, walks up by 1.
        inner = machine.root_state.substates['Inner']
        with pytest.raises(ModelLookupError) as info:
            inner.resolve_event('.NoSuch.Go')
        diag = info.value.diagnostics[0]
        assert diag.code == 'E_EVENT_NOT_FOUND'
        assert diag.refs['scope'] == 'chain'

    def test_local_scope_state_missing(self, machine):
        # Bare relative — local scope.
        with pytest.raises(ModelLookupError) as info:
            machine.root_state.resolve_event('NoSuch.Go')
        diag = info.value.diagnostics[0]
        assert diag.code == 'E_EVENT_NOT_FOUND'
        assert diag.refs['scope'] == 'local'


@pytest.mark.unittest
class TestStateMachineResolveEventPath:
    def test_empty_path(self, machine):
        with pytest.raises(ModelValueError) as info:
            machine.resolve_event('')
        diag = info.value.diagnostics[0]
        assert diag.code == 'E_EVENT_REF_INVALID'
        assert diag.refs['reason'] == 'empty'

    def test_path_with_empty_parts(self, machine):
        with pytest.raises(ModelValueError) as info:
            machine.resolve_event('Root..Go')
        diag = info.value.diagnostics[0]
        assert diag.code == 'E_EVENT_REF_INVALID'
        assert diag.refs['reason'] == 'invalid_absolute'

    def test_path_with_only_one_part(self, machine):
        with pytest.raises(ModelValueError) as info:
            machine.resolve_event('Go')
        diag = info.value.diagnostics[0]
        assert diag.code == 'E_EVENT_REF_INVALID'
        assert diag.refs['reason'] == 'invalid_absolute'

    def test_root_mismatch(self, machine):
        with pytest.raises(ModelLookupError) as info:
            machine.resolve_event('NotRoot.Go')
        diag = info.value.diagnostics[0]
        assert diag.code == 'E_EVENT_NOT_FOUND'
        assert diag.refs['scope'] == 'absolute'

    def test_middle_state_missing(self, machine):
        with pytest.raises(ModelLookupError) as info:
            machine.resolve_event('Root.NoSuch.Go')
        diag = info.value.diagnostics[0]
        assert diag.code == 'E_EVENT_NOT_FOUND'

    def test_leaf_event_missing(self, machine):
        with pytest.raises(ModelLookupError) as info:
            machine.resolve_event('Root.Inner.NoEvent')
        diag = info.value.diagnostics[0]
        assert diag.code == 'E_EVENT_NOT_FOUND'

    def test_success_path(self, machine):
        # Sanity: happy path still returns the event.
        ev = machine.resolve_event('Root.Inner.Done')
        assert ev.name == 'Done'


@pytest.mark.unittest
class TestSinkInjection:
    """``collect_into`` accumulates failures and returns ``None``."""

    def test_state_resolve_event_with_sink_returns_none_and_emits(self, machine):
        sink = DiagnosticSink(collect=True)
        result = machine.root_state.resolve_event('', collect_into=sink)
        assert result is None
        assert len(sink.diagnostics) == 1
        assert sink.diagnostics[0].code == 'E_EVENT_REF_INVALID'

    def test_state_machine_resolve_event_with_sink_returns_none_and_emits(self, machine):
        sink = DiagnosticSink(collect=True)
        result = machine.resolve_event('Root.NoSuch.Go', collect_into=sink)
        assert result is None
        assert len(sink.diagnostics) == 1
        assert sink.diagnostics[0].code == 'E_EVENT_NOT_FOUND'

    def test_sink_accumulates_multiple_failures(self, machine):
        sink = DiagnosticSink(collect=True)
        machine.root_state.resolve_event('', collect_into=sink)
        machine.root_state.resolve_event('/', collect_into=sink)
        machine.root_state.resolve_event('NoSuch.Go', collect_into=sink)
        codes = [d.code for d in sink.diagnostics]
        assert codes == [
            'E_EVENT_REF_INVALID',
            'E_EVENT_REF_INVALID',
            'E_EVENT_NOT_FOUND',
        ]

    def test_sink_does_not_raise(self, machine):
        sink = DiagnosticSink(collect=True)
        # Without sink this would raise — with sink, no raise.
        machine.root_state.resolve_event('', collect_into=sink)
        machine.resolve_event('Root.NoSuch.Go', collect_into=sink)

    def test_sink_in_strict_mode_still_raises(self, machine):
        # A strict-mode sink (collect=False) should still let resolve_event
        # raise — because sink.emit raises on error. This pins the design
        # contract: collect_into is "give me a sink"; if the sink is strict,
        # behavior matches no-sink (raise).
        sink = DiagnosticSink(collect=False)
        with pytest.raises(ModelValidationError) as info:
            machine.root_state.resolve_event('', collect_into=sink)
        # The strict sink raises plain ModelValidationError (its baseline
        # raise type), not ModelValueError — because the sink doesn't know
        # the subclass. Callers that want the typed exception must NOT pass
        # a strict sink; they either omit collect_into entirely or use a
        # collect=True sink.
        assert info.value.diagnostics[0].code == 'E_EVENT_REF_INVALID'

    def test_sink_preserves_happy_path(self, machine):
        sink = DiagnosticSink(collect=True)
        ev = machine.resolve_event('Root.Inner.Done', collect_into=sink)
        assert ev is not None
        assert ev.name == 'Done'
        assert sink.diagnostics == []

    # The following parametrize sets cover every ``return None`` branch in
    # the sink-mode path of both resolve_event methods. Without them the
    # coverage of model.py lingers around 98% because every error-path is
    # only exercised by the raise variant.

    @pytest.mark.parametrize('event_ref,expected_code,expected_reason_or_scope', [
        ('', 'E_EVENT_REF_INVALID', 'empty'),
        ('/', 'E_EVENT_REF_INVALID', 'bare_slash'),
        ('/foo..bar', 'E_EVENT_REF_INVALID', 'invalid_absolute'),
        ('.', 'E_EVENT_REF_INVALID', 'trailing_dots'),
        ('foo..bar', 'E_EVENT_REF_INVALID', 'invalid_relative'),
        ('/NoSuch.Go', 'E_EVENT_NOT_FOUND', 'absolute'),
        ('/Inner.NoEvent', 'E_EVENT_NOT_FOUND', 'absolute'),
        ('NoSuch.Go', 'E_EVENT_NOT_FOUND', 'local'),
    ])
    def test_state_resolve_event_all_failure_branches_via_sink(
            self, machine, event_ref, expected_code, expected_reason_or_scope):
        sink = DiagnosticSink(collect=True)
        result = machine.root_state.resolve_event(event_ref, collect_into=sink)
        assert result is None
        assert sink.diagnostics, f"no diagnostic for ref {event_ref!r}"
        diag = sink.diagnostics[0]
        assert diag.code == expected_code
        key = 'reason' if expected_code == 'E_EVENT_REF_INVALID' else 'scope'
        assert diag.refs[key] == expected_reason_or_scope

    @pytest.mark.parametrize('inner_ref,expected_reason', [
        ('.....TooDeep', 'beyond_root'),
        ('.foo..bar', 'invalid_relative'),
    ])
    def test_state_resolve_event_parent_relative_via_sink(
            self, machine, inner_ref, expected_reason):
        # Drive the parent-relative branches from ``Inner`` so neither of
        # them collapses into ``beyond_root`` prematurely.
        sink = DiagnosticSink(collect=True)
        inner = machine.root_state.substates['Inner']
        result = inner.resolve_event(inner_ref, collect_into=sink)
        assert result is None
        assert sink.diagnostics
        assert sink.diagnostics[0].refs['reason'] == expected_reason

    @pytest.mark.parametrize('event_path,expected_code,expected_reason_or_scope', [
        ('', 'E_EVENT_REF_INVALID', 'empty'),
        ('Root..Go', 'E_EVENT_REF_INVALID', 'invalid_absolute'),
        ('Go', 'E_EVENT_REF_INVALID', 'invalid_absolute'),
        ('NotRoot.Go', 'E_EVENT_NOT_FOUND', 'absolute'),
        ('Root.NoSuch.Go', 'E_EVENT_NOT_FOUND', 'absolute'),
        ('Root.Inner.NoEvent', 'E_EVENT_NOT_FOUND', 'absolute'),
    ])
    def test_state_machine_resolve_event_all_failure_branches_via_sink(
            self, machine, event_path, expected_code, expected_reason_or_scope):
        sink = DiagnosticSink(collect=True)
        result = machine.resolve_event(event_path, collect_into=sink)
        assert result is None
        assert sink.diagnostics
        diag = sink.diagnostics[0]
        assert diag.code == expected_code
        key = 'reason' if expected_code == 'E_EVENT_REF_INVALID' else 'scope'
        assert diag.refs[key] == expected_reason_or_scope


@pytest.mark.unittest
class TestBackwardsCompatMessage:
    """The original error messages stay intact so existing
    ``pytest.raises(ValueError, match=...)`` test fixtures continue to
    work without modification."""

    @pytest.mark.parametrize('event_ref,expected_substring', [
        ('', 'Event reference cannot be empty'),
        ('/', "cannot be just '/'"),
        ('/foo..bar', 'Invalid absolute event reference'),
        ('.', 'cannot end with dots'),
        ('foo..bar', 'Invalid relative event reference'),
    ])
    def test_state_resolve_event_message_preserved(
            self, machine, event_ref, expected_substring):
        with pytest.raises(ValueError) as info:
            machine.root_state.resolve_event(event_ref)
        assert expected_substring in str(info.value)

    def test_state_machine_resolve_event_message_preserved(self, machine):
        with pytest.raises(ValueError) as info:
            machine.resolve_event('')
        assert 'Event path cannot be empty' in str(info.value)

        with pytest.raises(LookupError) as info:
            machine.resolve_event('NotRoot.Go')
        assert 'does not match' in str(info.value)
