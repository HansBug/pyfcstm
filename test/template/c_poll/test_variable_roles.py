"""Polled native runtimes share the numeric input and parameter contract."""

import ctypes

import pytest

from ._utils import render_c_artifacts
from ..c.test_variable_roles import (
    Inputs,
    Parameters,
    InitOptions,
    InputProvider,
    ReadSignal,
    Vars,
    VarsPresent,
    ParametersPresent,
    ROLE_MODEL,
)


pytestmark = pytest.mark.unittest


def test_polled_runtime_freezes_numeric_inputs_and_owns_parameters():
    with render_c_artifacts(ROLE_MODEL) as artifacts:
        lib = ctypes.CDLL(artifacts["shared_lib"])
        lib.RootMachine_create_uninitialized.restype = ctypes.c_void_p
        lib.RootMachine_destroy.argtypes = [ctypes.c_void_p]
        lib.RootMachine_init_with_options.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(InitOptions),
        ]
        lib.RootMachine_cycle_with_inputs.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(Inputs),
        ]
        lib.RootMachine_cycle.argtypes = [ctypes.c_void_p]
        lib.RootMachine_set_input_provider.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(InputProvider),
            ctypes.c_void_p,
        ]
        lib.RootMachine_vars.argtypes = [ctypes.c_void_p]
        lib.RootMachine_vars.restype = ctypes.POINTER(Vars)
        machine = None
        try:
            machine = lib.RootMachine_create_uninitialized()
            assert machine
            options = InitOptions(
                Vars(7, 0), VarsPresent(1, 0), Parameters(3), ParametersPresent(1)
            )
            assert (
                lib.RootMachine_init_with_options(machine, ctypes.byref(options)) == 1
            )
            options.parameters.gain = 99
            assert (
                lib.RootMachine_cycle_with_inputs(machine, ctypes.byref(Inputs(4))) == 1
            )
            assert lib.RootMachine_vars(machine).contents.count == 8
            assert lib.RootMachine_vars(machine).contents.result == 12
            reads = []

            @ReadSignal
            def read_signal(user_data, value):
                reads.append(user_data)
                value[0] = 5
                return 1

            provider = InputProvider(read_signal)
            lib.RootMachine_set_input_provider(machine, ctypes.byref(provider), None)
            assert lib.RootMachine_cycle(machine) == 1
            assert len(reads) == 1
            assert lib.RootMachine_vars(machine).contents.count == 9
            assert lib.RootMachine_vars(machine).contents.result == 15
        finally:
            if machine:
                lib.RootMachine_destroy(machine)


def test_native_identifier_fields_match_generated_abi():
    from ._utils import build_c_runtime
    from ..c.test_variable_roles import _check_native_identifier_layout
    _check_native_identifier_layout(build_c_runtime)
