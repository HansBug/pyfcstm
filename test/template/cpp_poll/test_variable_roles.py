"""Polled C++ wrappers expose the same instance and cycle value APIs."""

import pytest

from ..cpp.test_variable_roles import (
    _check_cpp_role_integration, _check_integer_conversion,
    _check_role_api_failure_boundaries,
)


pytestmark = pytest.mark.unittest


def test_cpp_poll_role_integration():
    _check_cpp_role_integration(True)


@pytest.mark.parametrize("numeric_profile", ["integers", "float_input", "float_values"])
def test_native_role_api_failure_boundaries(numeric_profile):
    _check_role_api_failure_boundaries(True, numeric_profile)


@pytest.mark.parametrize("initializer", [True, False], ids=["parameter", "input-writeback"])
@pytest.mark.parametrize("value, error", [
    ("1.0e100", "outside signed 64-bit range"),
    ("-1.0e100", "outside signed 64-bit range"),
    ("9223372036854775808.0", "outside signed 64-bit range"),
    ("1.5", "non-integer float"),
    ("2.0", None),
    ("-9223372036854775808.0", None),
])
def test_native_integer_conversion_checks_range_and_integrality(initializer, value, error):
    _check_integer_conversion(True, initializer, value, error)


@pytest.mark.parametrize("role", ["param", "output"])
@pytest.mark.parametrize("value", ["1.5", "1.0e100", "-1.0e100", "2.0", "1 / 0"])
def test_explicit_configuration_bypasses_invalid_default(role, value):
    from ..cpp.test_variable_roles import _check_configuration_failures
    _check_configuration_failures(True, role, value)


def test_deep_hot_start_preserves_configuration():
    from ..cpp.test_variable_roles import _check_deep_hot_start
    _check_deep_hot_start(True)


def test_input_snapshot_requires_event_checks():
    from ..cpp.test_variable_roles import _check_poll_input_event_mount
    _check_poll_input_event_mount()


@pytest.mark.parametrize("wrapper", [False, True], ids=["c", "cpp"])
@pytest.mark.parametrize("language", ["en", "zh"])
@pytest.mark.parametrize("section", ["quick", "snapshot", "initial", "hot"])
def test_role_readme_example_runs(wrapper, language, section):
    from ..cpp.test_variable_roles import _check_role_readme_example
    _check_role_readme_example(True, wrapper, language, section)


def test_role_identifiers_remain_distinct():
    from ..cpp.test_variable_roles import _check_role_identifier_spelling
    _check_role_identifier_spelling(True)
