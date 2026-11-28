"""The step template renames lowered objects from one step into another."""

from __future__ import annotations

import dataclasses
from typing import Any, Tuple

import pytest
import z3

from pyfcstm.bmc.step_template import (
    MODE_VARIABLE,
    StepTemplate,
    StepTemplateUnsupported,
    first_difference,
    must_check_step,
    register_rebuilt,
    register_shared,
    step_instantiation_mode,
)

pytestmark = pytest.mark.unittest


@dataclasses.dataclass(frozen=True)
class _Relation:
    step: int
    condition: Any
    label: str


@dataclasses.dataclass(frozen=True)
class _Tag:
    name: str


@dataclasses.dataclass(frozen=True)
class _Holder:
    tag: _Tag
    relation: _Relation


@dataclasses.dataclass(frozen=True)
class _Unregistered:
    value: int


@dataclasses.dataclass(frozen=True)
class _Derived:
    value: Any
    cached: Any = dataclasses.field(default=None, init=False)


register_rebuilt(_Relation, ("step", "condition", "label"), ("step",))
register_rebuilt(_Holder, ("tag", "relation"))
register_shared(_Tag, ("name",))
register_rebuilt(_Derived, ("value", "cached"))


def _symbols(step: int) -> Tuple[z3.ArithRef, z3.ArithRef]:
    return z3.Int("a%d" % step), z3.Int("b%d" % step)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "on"),
        ("on", "on"),
        (" ON ", "on"),
        ("off", "off"),
        ("0", "off"),
        ("False", "off"),
        ("no", "off"),
        ("verify", "verify"),
        ("Verify", "verify"),
        ("anything else", "on"),
    ],
)
def test_the_mode_is_read_from_the_environment(monkeypatch, value, expected) -> None:
    if value is None:
        monkeypatch.delenv(MODE_VARIABLE, raising=False)
    else:
        monkeypatch.setenv(MODE_VARIABLE, value)

    assert step_instantiation_mode() == expected


@pytest.mark.parametrize(
    ("mode", "step", "checked"),
    [
        ("on", 2, True),
        ("on", 3, False),
        ("on", 4, False),
        ("on", 5, True),
        ("verify", 3, True),
        ("verify", 4, True),
        ("off", 3, False),
    ],
)
def test_the_first_and_last_instantiated_steps_are_always_checked(
    mode, step, checked
) -> None:
    assert must_check_step(mode, step, 2, 5) is checked


def test_instantiating_renames_terms_and_the_step_index() -> None:
    a1, b1 = _symbols(1)
    payload = (_Relation(1, a1 + b1 > 0, "case"), [b1], {"k": a1}, "text", 7)
    template = StepTemplate(payload, 1, (a1, b1), ())
    a4, b4 = _symbols(4)

    renamed = template.instantiate(4, (a4, b4))

    expected = (_Relation(4, a4 + b4 > 0, "case"), [b4], {"k": a4}, "text", 7)
    assert first_difference(renamed, expected) is None
    assert template.step_index == 1


def test_terms_keep_their_wrapper_class_and_shared_subterms_stay_shared() -> None:
    a1, b1 = _symbols(1)
    flag = z3.Bool("flag1")
    template = StepTemplate((flag, a1 + b1 > 0, a1), 1, (a1, b1, flag), ())
    a2, b2 = _symbols(2)
    renamed = template.instantiate(2, (a2, b2, z3.Bool("flag2")))

    assert [type(item) for item in renamed] == [z3.BoolRef, z3.BoolRef, z3.ArithRef]
    assert z3.eq(renamed[1], a2 + b2 > 0)


def test_the_same_object_met_twice_is_rebuilt_once() -> None:
    a1, b1 = _symbols(1)
    inner = _Relation(1, a1 > 0, "inner")
    template = StepTemplate((inner, inner, _Holder(_Tag("t"), inner)), 1, (a1, b1), ())
    a3, b3 = _symbols(3)
    first, second, holder = template.instantiate(3, (a3, b3))

    assert first is second
    assert holder.relation is first
    assert holder.tag is template.instantiate(3, (a3, b3))[2].tag
    assert first.step == 3


def test_a_payload_without_terms_is_returned_as_it_is() -> None:
    payload = ("plain", 3, (1, 2), [], {"x": 1}, _Tag("t"), None)
    template = StepTemplate(payload, 1, (), ())

    assert template.instantiate(5, ()) is not None
    assert first_difference(template.instantiate(5, ()), payload) is None


def test_terms_over_parameters_stay_untouched() -> None:
    a1, b1 = _symbols(1)
    parameter = z3.Int("p")
    template = StepTemplate((a1 > parameter,), 1, (a1, b1), (parameter,))
    a2, b2 = _symbols(2)

    assert z3.eq(template.instantiate(2, (a2, b2))[0], a2 > parameter)


def test_instantiating_with_the_wrong_number_of_symbols_is_rejected() -> None:
    a1, b1 = _symbols(1)
    template = StepTemplate((a1,), 1, (a1, b1), ())

    with pytest.raises(ValueError, match="symbols"):
        template.instantiate(2, (z3.Int("a2"),))


@pytest.mark.parametrize(
    ("payload", "reason"),
    [
        pytest.param(_Unregistered(1), "_Unregistered", id="unregistered-class"),
        pytest.param(object(), "object", id="plain-object"),
        pytest.param({(1, 2): 3}, "mapping key", id="structured-key"),
        pytest.param(_Relation(2, True, "x"), "template of step 1", id="wrong-step"),
        pytest.param(_Relation(True, True, "x"), "template of step 1", id="bool-step"),
        pytest.param(_Derived(1), "constructor argument", id="derived-field"),
    ],
)
def test_objects_the_template_does_not_cover_are_refused(payload, reason) -> None:
    a1, b1 = _symbols(1)

    with pytest.raises(StepTemplateUnsupported, match=reason) as caught:
        StepTemplate((a1, payload), 1, (a1, b1), ())

    assert reason in caught.value.reason


def test_a_symbol_that_belongs_to_no_step_is_refused() -> None:
    a1, b1 = _symbols(1)

    with pytest.raises(StepTemplateUnsupported, match="belongs to no step"):
        StepTemplate((a1 > z3.Int("stranger"),), 1, (a1, b1), ())


def test_a_term_that_is_not_an_application_is_refused() -> None:
    a1, b1 = _symbols(1)
    bound = z3.Int("bound")

    with pytest.raises(StepTemplateUnsupported, match="not an application"):
        StepTemplate((z3.ForAll([bound], bound > a1),), 1, (a1, b1), ())


def test_registration_must_name_exactly_the_fields_of_a_dataclass() -> None:
    class NotADataclass:
        pass

    with pytest.raises(TypeError, match="not a dataclass"):
        register_rebuilt(NotADataclass, ())
    with pytest.raises(TypeError, match="not a dataclass"):
        register_shared(NotADataclass, ())
    with pytest.raises(ValueError, match="_Tag registers"):
        register_shared(_Tag, ("name", "extra"))
    with pytest.raises(ValueError, match="_Tag registers"):
        register_shared(_Tag, ())
    with pytest.raises(ValueError, match="_Relation registers"):
        register_rebuilt(_Relation, ("step", "condition"), ("step",))
    with pytest.raises(ValueError, match="step_fields"):
        register_rebuilt(_Relation, ("step", "condition", "label"), ("missing",))


@pytest.mark.parametrize(
    ("left", "right", "where"),
    [
        (1, 1, None),
        ("a", "a", None),
        (1, "1", ": int / str"),
        (1, 2, ": 1 / 2"),
        ((1, 2), (1, 2), None),
        ((1, 2), (1, 2, 3), ": lengths 2 / 3"),
        ((1, 2), (1, 3), "[1]: 2 / 3"),
        ([1], (1,), ": list / tuple"),
        ({"a": 1}, {"a": 1}, None),
        ({"a": 1}, {"b": 1}, ": keys ['a'] / ['b']"),
        ({"a": 1}, {"a": 2}, "['a']: 1 / 2"),
        (_Tag("t"), _Tag("t"), None),
    ],
)
def test_comparing_object_graphs_reports_the_first_difference(
    left, right, where
) -> None:
    assert first_difference(left, right) == where


def test_comparing_terms_and_rebuilt_dataclasses() -> None:
    x = z3.Int("x")

    assert first_difference(x + 1, x + 1) is None
    assert first_difference((x + 1,), (x + 2,)) == "[0]: terms differ: x + 1 / x + 2"
    assert first_difference(_Relation(1, x > 0, "a"), _Relation(1, x > 0, "a")) is None
    assert (
        first_difference(_Relation(1, x > 0, "a"), _Relation(2, x > 0, "a"))
        == ".step: 1 / 2"
    )
    assert first_difference(x > 0, z3.Bool("b")).startswith(": terms differ")
    assert first_difference(z3.IntVal(1), z3.RealVal(1)).startswith(": IntNumRef")
