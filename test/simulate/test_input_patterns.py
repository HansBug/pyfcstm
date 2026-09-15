"""Public input patterns retain one value per logical simulation cycle."""

import math

import pytest

from pyfcstm.simulate.inputs import (
    BaseIntegratedInputPattern,
    BaseScalarInputPattern,
    CallableInput,
    ConstantFloatInput,
    ConstantIntInput,
    IntegratedCallableInput,
    IntegratedInputPattern,
    IntegratedSequenceInput,
    NormalFloatInput,
    NormalIntInput,
    ReplayInputPattern,
    ScalarInputPattern,
    SequenceInput,
    SimulationRuntimeInputSourceError,
    UniformFloatInput,
    UniformIntInput,
)

pytestmark = pytest.mark.unittest


class Ramp(BaseScalarInputPattern):
    def __init__(self):
        super().__init__()
        self.samples = []

    def _sample(self, step):
        self.samples.append(step)
        return 10 + step


def test_scalar_base_caches_and_advances_without_sampling():
    source = Ramp()
    assert isinstance(source, ScalarInputPattern)
    assert source.samples == []
    assert source.get() == source.get() == 10
    assert source.samples == [0]
    source.cycle()
    assert source.samples == [0]
    assert source.get() == 11
    assert source.samples == [0, 1]


def test_callable_failure_retries_current_step():
    calls = []

    def read(step):
        calls.append(step)
        if len(calls) == 1:
            raise OSError("sensor unavailable")
        return 3

    source = CallableInput(read)
    with pytest.raises(OSError, match="sensor unavailable"):
        source.get()
    assert source.get() == source.get() == 3
    assert calls == [0, 0]


@pytest.mark.parametrize(
    "cls,value,expected",
    [
        (ConstantIntInput, 2, 2),
        (ConstantFloatInput, 2, 2.0),
        (ConstantFloatInput, 2.5, 2.5),
    ],
)
def test_constants(cls, value, expected):
    source = cls(value)
    for _ in range(3):
        assert source.get() == expected
        assert type(source.get()) is type(expected)
        source.cycle()


@pytest.mark.parametrize(
    "value", [True, None, "2", float("nan"), float("inf"), float("-inf")]
)
def test_non_numeric_and_nonfinite_values_rejected(value):
    with pytest.raises(SimulationRuntimeInputSourceError):
        ConstantFloatInput(value)
    with pytest.raises(SimulationRuntimeInputSourceError):
        CallableInput(lambda step: value).get()


def test_integer_constant_rejects_float():
    with pytest.raises(SimulationRuntimeInputSourceError):
        ConstantIntInput(1.0)


@pytest.mark.parametrize(
    "end,expected", [("hold", [1, 2, 2, 2]), ("loop", [1, 2, 1, 2])]
)
def test_sequence_end_policies(end, expected):
    source = SequenceInput([1, 2], end=end)
    actual = []
    for value in expected:
        actual.append(source.get())
        assert source.get() == value
        source.cycle()
    assert actual == expected


def test_sequence_exhaustion_is_read_failure_not_advance_failure():
    source = SequenceInput([1])
    assert source.get() == 1
    source.cycle()
    with pytest.raises(StopIteration):
        source.get()
    source.cycle()
    with pytest.raises(StopIteration):
        source.get()


@pytest.mark.parametrize("end", ["hold", "loop", "unknown"])
def test_invalid_empty_sequence_policy(end):
    with pytest.raises(ValueError):
        SequenceInput([], end=end)


def test_empty_error_sequence():
    with pytest.raises(StopIteration):
        SequenceInput([]).get()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: UniformIntInput(-2, 5, seed=42),
        lambda: UniformFloatInput(-2, 5, seed=42),
        lambda: NormalFloatInput(2, 3, seed=42),
        lambda: NormalIntInput(2, 3, seed=42, rounding="round"),
        lambda: NormalIntInput(2, 3, seed=42, rounding="floor"),
        lambda: NormalIntInput(2, 3, seed=42, rounding="ceil"),
        lambda: NormalIntInput(2, 3, seed=42, rounding="trunc"),
    ],
)
def test_random_sources_are_repeatable_and_independent(factory):
    first, second = factory(), factory()
    unrelated = UniformFloatInput(0, 1, seed=4)
    for _ in range(8):
        value = first.get()
        assert math.isfinite(value)
        assert first.get() == value
        unrelated.get()
        unrelated.cycle()
        assert second.get() == value
        first.cycle()
        second.cycle()


@pytest.mark.parametrize(
    "factory",
    [
        lambda: UniformIntInput(2, 1),
        lambda: UniformIntInput(0.5, 2),
        lambda: UniformFloatInput(2, 1),
        lambda: NormalFloatInput(0, -1),
        lambda: NormalIntInput(0, 1, rounding="bad"),
        lambda: CallableInput(42),
    ],
)
def test_invalid_pattern_options(factory):
    with pytest.raises(ValueError):
        factory()


class Correlated(BaseIntegratedInputPattern):
    def __init__(self):
        super().__init__(("pressure", "alarm"))
        self.values = {"alarm": 0, "pressure": 70.0}

    def _sample(self, step):
        return self.values


def test_integrated_base_freezes_names_and_copies_snapshot():
    source = Correlated()
    assert isinstance(source, IntegratedInputPattern)
    assert source.input_names == ("pressure", "alarm")
    snapshot = source.get()
    assert tuple(snapshot) == source.input_names
    source.values["pressure"] = 90.0
    assert snapshot["pressure"] == 70.0
    assert source.get() is snapshot
    with pytest.raises(TypeError):
        snapshot["pressure"] = 0
    with pytest.raises(AttributeError):
        source.input_names = ("other",)
    source.cycle()
    assert source.get()["pressure"] == 90.0


@pytest.mark.parametrize("names", [("x", "x"), (1,), "x"])
def test_invalid_integrated_names(names):
    with pytest.raises(ValueError):
        IntegratedCallableInput(lambda step: {}, input_names=names)


@pytest.mark.parametrize(
    "value", [None, {"x": 1}, {"x": 1, "y": 2, "z": 3}, {"x": 1, "y": True}]
)
def test_integrated_snapshot_contract(value):
    source = IntegratedCallableInput(lambda step: value, input_names=("x", "y"))
    with pytest.raises(SimulationRuntimeInputSourceError):
        source.get()


def test_integrated_sequence_and_replay():
    values = [{"y": 2, "x": 1}, {"x": 3, "y": 4}]
    for source in (
        IntegratedSequenceInput(values, input_names=("x", "y")),
        ReplayInputPattern(values, input_names=("x", "y")),
    ):
        values[0]["x"] = 99
        assert dict(source.get()) == {"x": 1, "y": 2}
        assert tuple(source.get()) == ("x", "y")
        source.cycle()
        assert dict(source.get()) == {"x": 3, "y": 4}
        source.cycle()
        with pytest.raises(StopIteration):
            source.get()


def test_integrated_sequence_infers_names_and_validates_all_frames():
    assert IntegratedSequenceInput([{"b": 1, "a": 2}]).input_names == ("b", "a")
    with pytest.raises(ValueError):
        IntegratedSequenceInput([])
    with pytest.raises(ValueError):
        IntegratedSequenceInput([{"x": 1}, {"y": 2}])
    with pytest.raises(StopIteration):
        IntegratedSequenceInput([], input_names=("x",)).get()


def test_float_overflow_and_invalid_integrated_callable():
    with pytest.raises(SimulationRuntimeInputSourceError, match="float range"):
        ConstantFloatInput(10**400)
    with pytest.raises(ValueError, match="callable"):
        IntegratedCallableInput(None, input_names=())


def test_builtin_invalid_read_keeps_typed_diagnostic():
    from pyfcstm.dsl import parse_with_grammar_entry
    from pyfcstm.model import parse_dsl_node_to_state_machine
    from pyfcstm.simulate import SimulationRuntime

    model = parse_dsl_node_to_state_machine(
        parse_with_grammar_entry("input int sensor; state Root;", "state_machine_dsl")
    )
    runtime = SimulationRuntime(
        model, input_source={"sensor": CallableInput(lambda step: True)}
    )
    with pytest.raises(SimulationRuntimeInputSourceError) as caught:
        runtime.cycle()
    assert caught.value.code == "E_INPUT_SOURCE_TYPE"
    assert runtime.cycle_count == 0
