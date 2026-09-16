"""Cycle-indexed numeric input sources for simulation.

Implement :class:`ScalarInputPattern` or :class:`IntegratedInputPattern` to
adapt an existing provider. Subclass :class:`BaseScalarInputPattern` or
:class:`BaseIntegratedInputPattern` to inherit per-cycle caching and implement
only ``_sample(step)``. Sampling may fail; advancing a supported provider must
not fail or perform I/O. Each runtime owns the advancement of its providers.

Example::

    >>> source = SequenceInput([10, 20], end='hold')
    >>> source.get(), source.get()
    (10, 10)
    >>> source.cycle()
    >>> source.get()
    20
"""

import math
import random
import sys
from abc import ABC, abstractmethod
from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, Callable, Mapping as TypingMapping, Optional, Tuple, Union

if sys.version_info >= (3, 8):
    from typing import Protocol, runtime_checkable
else:
    from typing_extensions import Protocol, runtime_checkable

Number = Union[int, float]


class SimulationRuntimeInputSourceError(ValueError):
    """Invalid input binding, snapshot, or provider advancement.

    :param code: Stable diagnostic code identifying the failure category.
    :param message: Explanation including the offending input when available.
    """

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__("{}: {}".format(code, message))


@runtime_checkable
class ScalarInputPattern(Protocol):
    """Structural interface for one numeric input.

    ``get`` returns the same value until ``cycle`` advances the source.
    ``cycle`` must return normally and must not read the next value. Callers
    must not independently advance a source while it belongs to a runtime.
    """

    def get(self) -> Number:
        """Read the current numeric sample without advancing."""
        ...

    def cycle(self) -> None:
        """Advance one cycle without sampling or raising an exception."""
        ...


@runtime_checkable
class IntegratedInputPattern(Protocol):
    """Structural interface for a complete, correlated numeric input vector."""

    @property
    def input_names(self) -> Tuple[str, ...]:
        """Static, immutable names in model declaration order."""
        ...

    def get(self) -> Mapping:
        """Read the complete current vector without advancing."""
        ...

    def cycle(self) -> None:
        """Advance one cycle without sampling or raising an exception."""
        ...


InputSourceSpec = Union[
    TypingMapping[str, Union[int, float, ScalarInputPattern]],
    IntegratedInputPattern,
]


def _number(value: Any, type_name: Optional[str] = None) -> Number:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SimulationRuntimeInputSourceError(
            "E_INPUT_SOURCE_TYPE", "Expected a numeric value, got {!r}.".format(value)
        )
    if type_name == "int" and not isinstance(value, int):
        raise SimulationRuntimeInputSourceError(
            "E_INPUT_SOURCE_TYPE", "Expected an integer, got {!r}.".format(value)
        )
    if type_name == "float":
        try:
            value = float(value)
        except OverflowError as err:
            # float(large_int) cannot represent a finite floating-point value.
            raise SimulationRuntimeInputSourceError(
                "E_INPUT_SOURCE_TYPE", "Value exceeds finite float range."
            ) from err
    if isinstance(value, float) and not math.isfinite(value):
        raise SimulationRuntimeInputSourceError(
            "E_INPUT_SOURCE_TYPE", "Input values must be finite."
        )
    return value


def _names(names) -> Tuple[str, ...]:
    if not isinstance(names, tuple) or any(
        not isinstance(name, str) or not name for name in names
    ):
        raise SimulationRuntimeInputSourceError(
            "E_INPUT_SOURCE_CONTRACT",
            "input_names must be a tuple of nonempty strings.",
        )
    if len(set(names)) != len(names):
        raise SimulationRuntimeInputSourceError(
            "E_INPUT_SOURCE_CONTRACT", "input_names must not contain duplicates."
        )
    return names


def _snapshot(value, names: Tuple[str, ...]) -> Mapping:
    if not isinstance(value, Mapping):
        raise SimulationRuntimeInputSourceError(
            "E_INPUT_SOURCE_CONTRACT", "Input snapshot must be a mapping."
        )
    missing = set(names) - set(value)
    unknown = set(value) - set(names)
    if missing:
        raise SimulationRuntimeInputSourceError(
            "E_INPUT_SOURCE_MISSING", "Missing inputs: {!r}.".format(sorted(missing))
        )
    if unknown:
        raise SimulationRuntimeInputSourceError(
            "E_INPUT_SOURCE_UNKNOWN", "Unknown inputs: {!r}.".format(list(unknown))
        )
    return MappingProxyType({name: _number(value[name]) for name in names})


class _CachedInput(ABC):
    """Shared cache implementation; subclasses supply sampling and validation."""

    def __init__(self):
        self._step = 0
        self._cached = False
        self._value = None

    @abstractmethod
    def _sample(self, step: int):
        """Compute the current sample; failures leave this step retryable."""
        ...

    @abstractmethod
    def _freeze(self, value):
        """Validate and detach a value before making it observable."""
        ...

    def get(self):
        """Return the cached sample, sampling only on the first successful read."""
        if not self._cached:
            self._value = self._freeze(self._sample(self._step))
            self._cached = True
        return self._value

    def cycle(self) -> None:
        """Advance the logical step and invalidate its cache, without sampling."""
        self._step += 1
        self._cached = False
        self._value = None


class BaseScalarInputPattern(_CachedInput):
    """Base for custom scalar sources implementing ``_sample(step)``.

    The zero-based step is supplied to the extension hook. Values must be
    finite integers or floats, excluding booleans. Successful samples are
    cached until :meth:`cycle`; a failed sample may be retried at the same step.
    """

    def _freeze(self, value):
        return _number(value)


class BaseIntegratedInputPattern(_CachedInput):
    """Base for custom correlated sources implementing ``_sample(step)``.

    :param input_names: Immutable tuple of names in model declaration order.
        Returned mappings must have exactly these keys. Cached snapshots are
        copied and frozen, so later mutation of a provider dictionary is safe.
    """

    def __init__(self, input_names: Tuple[str, ...]):
        super().__init__()
        self._input_names = _names(input_names)

    @property
    def input_names(self) -> Tuple[str, ...]:
        """Return the immutable declared input names."""
        return self._input_names

    def _freeze(self, value):
        return _snapshot(value, self.input_names)


class ConstantIntInput(BaseScalarInputPattern):
    """Constant integer source.

    :param value: Integer value; booleans and floats are rejected.
    """

    def __init__(self, value: int):
        super().__init__()
        self.value = _number(value, "int")

    def _sample(self, step):
        return self.value


class ConstantFloatInput(BaseScalarInputPattern):
    """Constant finite float source.

    :param value: Numeric value, normalized to float.
    """

    def __init__(self, value: Number):
        super().__init__()
        self.value = _number(value, "float")

    def _sample(self, step):
        return self.value


def _sequence_index(step, length, end):
    if step < length:
        return step
    if end == "error":
        raise StopIteration("Input sequence exhausted at step {}.".format(step))
    if end == "hold":
        return length - 1
    return step % length


def _end_policy(length, end):
    if end not in ("error", "hold", "loop"):
        raise ValueError("end must be error, hold, or loop")
    if not length and end != "error":
        raise ValueError('An empty sequence requires end="error"')


class SequenceInput(BaseScalarInputPattern):
    """Finite scalar sequence with an explicit exhaustion policy.

    :param values: Finite iterable copied and validated at construction.
    :param end: ``error`` (default), ``hold``, or ``loop``. Exhaustion is
        reported by ``get()``, never by ``cycle()``.
    """

    def __init__(self, values, *, end="error"):
        super().__init__()
        self._values = tuple(_number(value) for value in values)
        _end_policy(len(self._values), end)
        self._end = end

    def _sample(self, step):
        return self._values[_sequence_index(step, len(self._values), self._end)]


class UniformIntInput(BaseScalarInputPattern):
    """Independent seeded uniform integer source with inclusive bounds.

    :param low: Minimum integer.
    :param high: Maximum integer, at least ``low``.
    :param seed: Seed accepted by :class:`random.Random`.
    """

    def __init__(self, low: int, high: int, *, seed=None):
        super().__init__()
        self._low, self._high = _number(low, "int"), _number(high, "int")
        if self._low > self._high:
            raise ValueError("low must not exceed high")
        self._random = random.Random(seed)

    def _sample(self, step):
        return self._random.randint(self._low, self._high)


class UniformFloatInput(BaseScalarInputPattern):
    """Independent seeded uniform float source.

    :param low: Finite lower bound.
    :param high: Finite upper bound, at least ``low``.
    :param seed: Seed accepted by :class:`random.Random`.
    """

    def __init__(self, low: Number, high: Number, *, seed=None):
        super().__init__()
        self._low, self._high = _number(low, "float"), _number(high, "float")
        if self._low > self._high:
            raise ValueError("low must not exceed high")
        self._random = random.Random(seed)

    def _sample(self, step):
        # Weighted endpoints avoid overflowing high - low for finite extremes.
        weight = self._random.random()
        return self._low * (1.0 - weight) + self._high * weight


class NormalFloatInput(BaseScalarInputPattern):
    """Independent seeded normal float source.

    :param mean: Finite distribution mean.
    :param stddev: Finite, nonnegative standard deviation.
    :param seed: Seed accepted by :class:`random.Random`.
    """

    def __init__(self, mean: Number, stddev: Number, *, seed=None):
        super().__init__()
        self._mean, self._stddev = _number(mean, "float"), _number(stddev, "float")
        if self._stddev < 0:
            raise ValueError("stddev must be nonnegative")
        self._random = random.Random(seed)

    def _sample(self, step):
        return self._random.gauss(self._mean, self._stddev)


class NormalIntInput(NormalFloatInput):
    """Normal source with explicitly selected integer rounding.

    :param mean: Finite mean.
    :param stddev: Nonnegative finite standard deviation.
    :param seed: Independent random seed.
    :param rounding: Required choice of ``round`` (ties to even), ``floor``,
        ``ceil``, or ``trunc``.
    """

    def __init__(self, mean: Number, stddev: Number, *, rounding: str, seed=None):
        super().__init__(mean, stddev, seed=seed)
        rounding_functions = {
            "round": round,
            "floor": math.floor,
            "ceil": math.ceil,
            "trunc": math.trunc,
        }
        if rounding not in rounding_functions:
            raise ValueError("rounding must be round, floor, ceil, or trunc")
        self._round = rounding_functions[rounding]

    def _sample(self, step):
        return self._round(super()._sample(step))


class CallableInput(BaseScalarInputPattern):
    """Cached custom scalar sampler.

    :param sample: Callable receiving a zero-based logical step. It must not
        consume an external stream irreversibly; failed cycles may be retried.
    """

    def __init__(self, sample: Callable[[int], Number]):
        super().__init__()
        if not callable(sample):
            raise ValueError("sample must be callable")
        self._sampler = sample

    def _sample(self, step):
        return self._sampler(step)


class IntegratedCallableInput(BaseIntegratedInputPattern):
    """Cached custom input-vector sampler.

    :param sample: Callable receiving the logical step and returning a mapping.
    :param input_names: Explicit static name tuple; the callable is not probed.
    """

    def __init__(
        self, sample: Callable[[int], Mapping], *, input_names: Tuple[str, ...]
    ):
        super().__init__(input_names)
        if not callable(sample):
            raise ValueError("sample must be callable")
        self._sampler = sample

    def _sample(self, step):
        return self._sampler(step)


class IntegratedSequenceInput(BaseIntegratedInputPattern):
    """Copied sequence of correlated input vectors.

    :param values: Finite iterable of complete mappings.
    :param input_names: Static tuple, or omitted to use the first mapping's
        insertion order. Empty sequences require explicit names.
    :param end: ``error``, ``hold``, or ``loop`` exhaustion policy.
    """

    def __init__(self, values, *, input_names=None, end="error"):
        values = tuple(values)
        if input_names is None:
            if not values or not isinstance(values[0], Mapping):
                raise ValueError(
                    "Name inference requires a nonempty sequence of mappings"
                )
            input_names = tuple(values[0])
        super().__init__(input_names)
        self._values = tuple(_snapshot(value, self.input_names) for value in values)
        _end_policy(len(self._values), end)
        self._end = end

    def _sample(self, step):
        return self._values[_sequence_index(step, len(self._values), self._end)]


class ReplayInputPattern(IntegratedSequenceInput):
    """Deterministic finite replay source with explicit model input names.

    :param snapshots: Complete per-cycle input mappings, copied on construction.
    :param input_names: Model input names in declaration order.
    """

    def __init__(self, snapshots, *, input_names: Tuple[str, ...]):
        super().__init__(snapshots, input_names=input_names, end="error")


class _InputSources:
    """Bind providers once and enforce snapshot and advancement boundaries."""

    def __init__(self, defines, source):
        self.defines = defines
        self.names = tuple(defines)
        self.error = None
        self.integrated = None
        self.scalars = {}
        if source is None:
            source = {}
        if isinstance(source, Mapping):
            if set(source) != set(self.names):
                _snapshot(source, self.names)
            identities = set()
            for name in self.names:
                pattern = source[name]
                if isinstance(pattern, (int, float)):
                    pattern = (
                        ConstantFloatInput(pattern)
                        if isinstance(pattern, float)
                        else ConstantIntInput(pattern)
                    )
                self._check_pattern(pattern)
                if id(pattern) in identities:
                    raise SimulationRuntimeInputSourceError(
                        "E_INPUT_SOURCE_CONTRACT",
                        "A scalar source instance cannot be bound to multiple inputs.",
                    )
                identities.add(id(pattern))
                self.scalars[name] = pattern
        else:
            self._check_pattern(source)
            names = _names(getattr(source, "input_names", None))
            if names != self.names:
                raise SimulationRuntimeInputSourceError(
                    "E_INPUT_SOURCE_CONTRACT",
                    "Integrated input_names must equal model declaration order.",
                )
            self.integrated = source

    @staticmethod
    def _check_pattern(pattern):
        if not callable(getattr(pattern, "get", None)) or not callable(
            getattr(pattern, "cycle", None)
        ):
            raise SimulationRuntimeInputSourceError(
                "E_INPUT_SOURCE_CONTRACT",
                "An input pattern requires callable get() and cycle().",
            )

    def overrides(self, values):
        if values is None:
            return {}
        if not isinstance(values, Mapping):
            raise SimulationRuntimeInputSourceError(
                "E_INPUT_SOURCE_CONTRACT", "inputs must be a mapping."
            )
        result = {}
        for name, value in values.items():
            if name not in self.defines:
                raise SimulationRuntimeInputSourceError(
                    "E_INPUT_SOURCE_UNKNOWN", "Unknown input {!r}.".format(name)
                )
            result[name] = _number(value, self.defines[name].type)
        return result

    @staticmethod
    def _read(pattern):
        try:
            return pattern.get()
        except SimulationRuntimeInputSourceError:
            # Built-in get() validates cached values and supplies a typed diagnostic.
            raise
        except Exception as err:
            # get() is explicitly user-defined provider code: any Exception
            # subclass is a documented read failure. Preserve its cause; do
            # not include runtime execution or validation in this boundary.
            raise SimulationRuntimeInputSourceError(
                "E_INPUT_SOURCE_READ",
                "Input source read failed: {}.".format(type(err).__name__),
            ) from err

    def read(self, overrides):
        if self.integrated is not None:
            values = _snapshot(self._read(self.integrated), self.names)
        else:
            values = {}
            for name, pattern in self.scalars.items():
                values[name] = _number(self._read(pattern), self.defines[name].type)
        normalized = {
            name: _number(values[name], self.defines[name].type) for name in self.names
        }
        normalized.update(overrides)
        return MappingProxyType(normalized)

    def advance(self):
        patterns = (
            (self.integrated,) if self.integrated is not None else self.scalars.values()
        )
        for pattern in patterns:
            try:
                pattern.cycle()
            except Exception as err:
                # cycle() is user provider code. Any Exception violates its
                # total-advancement contract; poison permanently because an
                # earlier provider may already have advanced. Preserve cause.
                self.error = SimulationRuntimeInputSourceError(
                    "E_INPUT_SOURCE_CONTRACT",
                    "Input source advancement failed; create a new runtime with fresh sources.",
                )
                raise self.error from err
