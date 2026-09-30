"""Public AST transition trigger construction and mutation contracts."""

import pytest
from pyfcstm.dsl import node
from pyfcstm.dsl import parse_with_grammar_entry


@pytest.mark.unittest
def test_trigger_terms_are_validated_and_canonical():
    event = node.EventTerm(node.ChainID(["Go"]), "chain")
    guard = node.GuardTerm(node.Name("ready"))
    trigger = node.TransitionTrigger(":", (event, guard))
    assert trigger.canonical_text == ": Go + [ready]"
    assert trigger.is_combo
    for terms in ((), [], [event], (None,), (node.TriggerTerm(),)):
        with pytest.raises((TypeError, ValueError)):
            node.TransitionTrigger(":", terms)
    for target, field, bad in (
        (event, "event_id", None),
        (event, "event_scope", "bad"),
        (guard, "condition_expr", None),
        (trigger, "terms", ()),
        (trigger, "scope_prefix", "!"),
    ):
        old = getattr(target, field)
        with pytest.raises((TypeError, ValueError, AttributeError)):
            setattr(target, field, bad)
        assert getattr(target, field) == old
    from dataclasses import replace

    trigger = replace(trigger, terms=(guard,))
    assert not trigger.is_combo
    transition = node.TransitionDefinition("A", "B", trigger, [])
    transition.trigger = None
    for field in ("event_id", "event_scope", "condition_expr", "combo_trigger"):
        with pytest.raises(AttributeError):
            setattr(transition, field, None)
    with pytest.raises(TypeError):
        transition.trigger = guard
    with pytest.raises(ValueError):
        node.ForceTransitionDefinition(
            "A", "B", node.TransitionTrigger(":", (event, guard))
        )


@pytest.mark.unittest
@pytest.mark.parametrize(
    "suffix",
    [
        "",
        " :: Go",
        " : A.Go",
        " : /Bus.Go",
        " : if [ready > 0]",
        " : [ready > 0]",
        " :: Go + [ready > 0]",
    ],
)
def test_parser_uses_one_trigger_and_round_trips(suffix):
    transition = parse_with_grammar_entry(
        "A -> B" + suffix + ";", "transition_definition"
    )
    assert not hasattr(transition, "event_id")
    assert not hasattr(transition, "condition_expr")
    assert not hasattr(transition, "combo_trigger")
    if suffix:
        assert isinstance(transition.trigger, node.TransitionTrigger)
        assert isinstance(transition.trigger.terms, tuple)
    else:
        assert transition.trigger is None
    canonical = suffix.replace(" : A.Go", " :: Go").replace(
        " : [ready > 0]", " : if [ready > 0]"
    )
    assert str(transition) == "A -> B" + canonical + ";"


@pytest.mark.unittest
def test_trigger_public_assignment_copy_and_provenance():
    from copy import deepcopy
    from dataclasses import replace
    from pyfcstm.utils.validate import Span

    event = node.EventTerm(node.ChainID(["Go"]), "chain")
    guard = node.GuardTerm(node.Integer("1"))
    trigger = node.TransitionTrigger(":", (event,))
    for name, value in [
        ("terms", [event]),
        ("terms", (object(),)),
        ("legacy_guard_syntax", 1),
        ("scope_prefix", None),
    ]:
        previous = getattr(trigger, name)
        with pytest.raises(AttributeError):
            setattr(trigger, name, value)
        assert getattr(trigger, name) == previous
    event.event_id = node.ChainID(["Run"])
    event.event_scope = "local"
    guard.condition_expr = node.Integer("2")
    trigger = replace(trigger, terms=(guard,), legacy_guard_syntax=True)
    assert trigger.canonical_text == ": if [2]"
    span = Span(line=1, column=1, end_line=1, end_column=4)
    trigger.trigger_span = span
    guard.term_span = span
    assert deepcopy(trigger) == trigger
    assert replace(trigger, terms=(event,)).terms == (event,)
    for transition in (
        node.TransitionDefinition("A", "B", None, []),
        node.ForceTransitionDefinition("A", "B", None),
    ):
        transition.trigger = trigger
        assert deepcopy(transition) == transition
        for name in ("event_id", "condition_expr", "event_scope", "combo_trigger"):
            with pytest.raises(AttributeError):
                setattr(transition, name, None)
        with pytest.raises(TypeError):
            transition.trigger = event
        assert transition.trigger is trigger
        transition.trigger = None
    forced = node.ForceTransitionDefinition("A", "B", trigger)
    with pytest.raises(ValueError):
        forced.trigger = node.TransitionTrigger(":", (event, guard))
    assert forced.trigger is trigger
    with pytest.raises(AttributeError):
        forced.trigger.terms = (event, guard)
    assert len(forced.trigger.terms) == 1


@pytest.mark.unittest
@pytest.mark.parametrize(
    "source, suffix, term_text",
    [
        ("! A -> B :: Go;", ":: Go", "Go"),
        ("! A -> [*] : /Bus.Stop;", ": /Bus.Stop", "/Bus.Stop"),
        ("! * -> B :: Start;", ":: Start", "Start"),
        ("! * -> [*] : if [x > 0];", ": if [x > 0]", "[x > 0]"),
    ],
)
def test_forced_trigger_provenance(source, suffix, term_text):
    transition = parse_with_grammar_entry(source, "transition_force_definition")
    trigger = transition.trigger
    assert len(trigger.terms) == 1
    term = trigger.terms[0]
    assert (
        source[trigger.trigger_span.column - 1 : trigger.trigger_span.end_column - 1]
        == suffix
    )
    assert (
        source[term.term_span.column - 1 : term.term_span.end_column - 1] == term_text
    )
    assert term.removal_span == term.term_span


@pytest.mark.unittest
@pytest.mark.parametrize(
    "kwargs, error",
    [
        (
            {"scope_prefix": "!", "terms": (node.GuardTerm(node.Integer("1")),)},
            ValueError,
        ),
        (
            {
                "scope_prefix": ":",
                "terms": (node.GuardTerm(node.Integer("1")),),
                "legacy_guard_syntax": 1,
            },
            TypeError,
        ),
    ],
)
def test_trigger_rejects_invalid_semantic_construction(kwargs, error):
    with pytest.raises(error):
        node.TransitionTrigger(**kwargs)


@pytest.mark.unittest
def test_trigger_semantic_fields_cannot_be_deleted():
    trigger = node.TransitionTrigger(":", (node.GuardTerm(node.Integer("1")),))
    for name in ("scope_prefix", "terms", "legacy_guard_syntax"):
        with pytest.raises(AttributeError):
            delattr(trigger, name)
    trigger.trigger_span = None
    del trigger.trigger_span
    assert trigger.terms


@pytest.mark.unittest
def test_trigger_terms_reject_opposite_condition_fields():
    event = node.EventTerm(node.ChainID(["Go"]), "chain")
    guard = node.GuardTerm(node.Integer("1"))
    for term, name, value in (
        (event, "condition_expr", node.Integer("0")),
        (guard, "event_id", node.ChainID(["Go"])),
        (guard, "event_scope", "chain"),
    ):
        with pytest.raises(AttributeError):
            setattr(term, name, value)
        assert not hasattr(term, name)
        with pytest.raises(AttributeError):
            delattr(term, name)
    event._source_path = "event.fcstm"
    guard._source_path = "guard.fcstm"
    assert event._source_path == "event.fcstm"
    assert guard._source_path == "guard.fcstm"
