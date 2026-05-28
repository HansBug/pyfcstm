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
    # M2 from PR-112 review: enforce required-field presence. Without
    # this, a regression that drops a ``required: true`` field (e.g.
    # ``event_ref`` on E_EVENT_REF_INVALID) slips through silently.
    for name, field_spec in spec.refs_schema.items():
        if field_spec.required:
            assert name in actual, (
                f"{diag.code} refs missing required field {name!r}"
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

    def test_sink_in_strict_mode_raises_typed_subclass(self, machine):
        # Post-review fix: a strict-mode sink (collect=False) must raise
        # the typed subclass (ModelValueError / ModelLookupError), not
        # plain ModelValidationError — preserving the back-compat catch
        # surface for ``except ValueError:`` / ``except LookupError:``.
        # Full MRO matrix is exercised in
        # TestStrictSinkTypedExceptionMatrix.
        sink = DiagnosticSink(collect=False)
        with pytest.raises(ModelValueError) as info:
            machine.root_state.resolve_event('', collect_into=sink)
        assert isinstance(info.value, ValueError)
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
class TestStrictSinkTypedExceptionMatrix:
    """
    Post-review fix (PR-110/PR-112 review I1 + M5): passing a strict-mode
    ``DiagnosticSink`` (``collect=False``) to ``resolve_event`` must still
    raise the typed subclass (``ModelValueError`` / ``ModelLookupError``)
    so the legacy ``except ValueError:`` / ``except LookupError:`` catch
    surface keeps working. The earlier implementation routed through
    ``sink.emit()`` which raised plain ``ModelValidationError``, breaking
    the back-compat promise.

    These tests pin the full MRO matrix across both resolver methods, both
    diagnostic codes (E_EVENT_REF_INVALID / E_EVENT_NOT_FOUND), and all
    four catch handlers (ValueError / LookupError / SyntaxError /
    ModelValidationError).
    """

    @pytest.mark.parametrize('event_ref', ['', '/', '/foo..bar', 'foo..bar'])
    def test_state_resolve_event_strict_sink_keeps_value_error(
            self, machine, event_ref):
        sink = DiagnosticSink(collect=False)
        with pytest.raises(ValueError) as info:
            machine.root_state.resolve_event(event_ref, collect_into=sink)
        # All four catch handlers must succeed.
        assert isinstance(info.value, ModelValueError)
        assert isinstance(info.value, ValueError)
        assert isinstance(info.value, SyntaxError)
        assert isinstance(info.value, ModelValidationError)
        assert info.value.diagnostics[0].code == 'E_EVENT_REF_INVALID'

    @pytest.mark.parametrize('event_ref', [
        '/NoSuch.Go',
        '/Inner.NoEvent',
        'NoSuch.Go',
    ])
    def test_state_resolve_event_strict_sink_keeps_lookup_error(
            self, machine, event_ref):
        sink = DiagnosticSink(collect=False)
        with pytest.raises(LookupError) as info:
            machine.root_state.resolve_event(event_ref, collect_into=sink)
        assert isinstance(info.value, ModelLookupError)
        assert isinstance(info.value, LookupError)
        assert isinstance(info.value, SyntaxError)
        assert isinstance(info.value, ModelValidationError)
        assert info.value.diagnostics[0].code == 'E_EVENT_NOT_FOUND'

    @pytest.mark.parametrize('event_path', ['', 'Root..Go', 'Go'])
    def test_state_machine_resolve_event_strict_sink_keeps_value_error(
            self, machine, event_path):
        sink = DiagnosticSink(collect=False)
        with pytest.raises(ValueError) as info:
            machine.resolve_event(event_path, collect_into=sink)
        assert isinstance(info.value, ModelValueError)
        assert isinstance(info.value, ValueError)
        assert isinstance(info.value, SyntaxError)

    @pytest.mark.parametrize('event_path', [
        'NotRoot.Go',
        'Root.NoSuch.Go',
        'Root.Inner.NoEvent',
    ])
    def test_state_machine_resolve_event_strict_sink_keeps_lookup_error(
            self, machine, event_path):
        sink = DiagnosticSink(collect=False)
        with pytest.raises(LookupError) as info:
            machine.resolve_event(event_path, collect_into=sink)
        assert isinstance(info.value, ModelLookupError)
        assert isinstance(info.value, LookupError)
        assert isinstance(info.value, SyntaxError)


@pytest.mark.unittest
class TestParentRelativeReasonDepthIndependence:
    """
    Post-review fix (PR-112 review I2): a malformed parent-relative
    reference like ``.foo..bar`` should report ``reason='invalid_relative'``
    regardless of the calling state's depth in the hierarchy. The original
    implementation walked up the hierarchy BEFORE syntax-validating the
    remaining dotted path, so the same input reported ``beyond_root``
    when called from a shallow state but ``invalid_relative`` from a
    deeper one — a contract violation where ``reason`` (a schema-backed
    enum field) silently changes based on geometry rather than syntax.
    """

    def test_dotdot_foodotdotbar_from_root_is_invalid_relative(
            self, machine):
        # Was previously beyond_root because walk-up exhausts hierarchy
        # before the syntax check fires. After the fix the syntax check
        # runs first.
        with pytest.raises(ModelValueError) as info:
            machine.root_state.resolve_event('.foo..bar')
        assert info.value.diagnostics[0].refs['reason'] == 'invalid_relative'

    def test_dotdot_foodotdotbar_from_inner_is_invalid_relative(
            self, machine):
        # From Inner (depth 2) the walk-up succeeds, so this already
        # reported invalid_relative pre-fix. Pin that behavior so the
        # fix doesn't regress it.
        inner = machine.root_state.substates['Inner']
        with pytest.raises(ModelValueError) as info:
            inner.resolve_event('.foo..bar')
        assert info.value.diagnostics[0].refs['reason'] == 'invalid_relative'

    def test_dot_foo_from_root_still_beyond_root(self, machine):
        # Sanity: syntactically valid parent-relative refs that overflow
        # the root must still report beyond_root.
        with pytest.raises(ModelValueError) as info:
            machine.root_state.resolve_event('.foo')
        assert info.value.diagnostics[0].refs['reason'] == 'beyond_root'


@pytest.mark.unittest
class TestSearchedFromCallerState:
    """
    Post-review fix (PR-112 review M3): codes.yaml describes
    ``E_EVENT_NOT_FOUND.refs.searched_from`` as the originating state
    path, but the previous tests never asserted the actual value. Pin the
    contract: ``searched_from`` is the CALLER's state path (not the
    effective search root, which would always be ``Root`` for absolute
    refs).
    """

    def test_local_scope_searched_from_is_caller_state_path(self, machine):
        inner = machine.root_state.substates['Inner']
        with pytest.raises(ModelLookupError) as info:
            inner.resolve_event('NoSuch.Go')
        diag = info.value.diagnostics[0]
        assert diag.refs['scope'] == 'local'
        assert diag.refs['searched_from'] == 'Root.Inner'

    def test_chain_scope_searched_from_is_caller_state_path(self, machine):
        inner = machine.root_state.substates['Inner']
        with pytest.raises(ModelLookupError) as info:
            inner.resolve_event('.NoSuch.Go')
        diag = info.value.diagnostics[0]
        assert diag.refs['scope'] == 'chain'
        assert diag.refs['searched_from'] == 'Root.Inner'

    def test_absolute_scope_searched_from_is_caller_state_path(self, machine):
        # For absolute refs, the search physically starts at Root, but
        # the contract says ``searched_from`` carries the caller's state
        # path so downstream tooling can highlight where the bad ref
        # textually lives.
        inner = machine.root_state.substates['Inner']
        with pytest.raises(ModelLookupError) as info:
            inner.resolve_event('/NoSuch.Go')
        diag = info.value.diagnostics[0]
        assert diag.refs['scope'] == 'absolute'
        assert diag.refs['searched_from'] == 'Root.Inner'

    def test_state_machine_resolve_event_searched_from_for_root_mismatch(
            self, machine):
        # StateMachine.resolve_event isn't tied to a single State, so
        # ``searched_from`` describes the search root token at the point
        # of failure. Pin that as ``Root`` (the model's root state name).
        with pytest.raises(ModelLookupError) as info:
            machine.resolve_event('NotRoot.Go')
        diag = info.value.diagnostics[0]
        assert diag.refs['searched_from'] == 'Root'


@pytest.mark.unittest
class TestAssertRefsMatchSchemaRequiredField:
    """
    Post-review fix (PR-112 review M2): the test helper used across this
    file must enforce required-field presence, not just extra-key absence
    and enum membership. Without this, a regression that drops a
    ``required: true`` field (like ``event_ref`` on E_EVENT_REF_INVALID)
    slips through silently.
    """

    def test_helper_rejects_missing_required_field(self):
        # Build a hand-crafted diagnostic that violates the required
        # contract of E_EVENT_REF_INVALID — missing ``event_ref``.
        bad_diag = ModelDiagnostic(
            code='E_EVENT_REF_INVALID',
            severity='error',
            message='m',
            refs={'reason': 'empty'},  # missing event_ref
        )
        with pytest.raises(AssertionError, match='missing required field'):
            _assert_refs_match_schema(bad_diag)

    def test_helper_accepts_all_required_fields_present(self):
        # Sanity: a well-formed diagnostic must pass.
        ok_diag = ModelDiagnostic(
            code='E_EVENT_REF_INVALID',
            severity='error',
            message='m',
            refs={'event_ref': 'x', 'reason': 'empty'},
        )
        _assert_refs_match_schema(ok_diag)


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
