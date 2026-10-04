"""Native integration of instance parameters and cycle input snapshots."""

import ctypes

import pytest

from ._utils import render_c_artifacts


pytestmark = pytest.mark.unittest

ROLE_MODEL = """
input int signal;
param int gain = 2;
control int count = 0;
output int result = 0;
state Root {
    state Ready { during { count = count + 1; result = signal * gain; } }
    [*] -> Ready;
}
"""


class Vars(ctypes.Structure):
    _fields_ = [("count", ctypes.c_int64), ("result", ctypes.c_int64)]


class VarsPresent(ctypes.Structure):
    _fields_ = [("count", ctypes.c_int), ("result", ctypes.c_int)]


class Parameters(ctypes.Structure):
    _fields_ = [("gain", ctypes.c_int64)]


class ParametersPresent(ctypes.Structure):
    _fields_ = [("gain", ctypes.c_int)]


class InitOptions(ctypes.Structure):
    _fields_ = [
        ("vars", Vars),
        ("vars_present", VarsPresent),
        ("parameters", Parameters),
        ("parameters_present", ParametersPresent),
    ]


class Inputs(ctypes.Structure):
    _fields_ = [("signal", ctypes.c_int64)]


ReadSignal = ctypes.CFUNCTYPE(
    ctypes.c_int, ctypes.c_void_p, ctypes.POINTER(ctypes.c_int64)
)


class InputProvider(ctypes.Structure):
    _fields_ = [("read_signal", ReadSignal)]


def test_native_role_snapshot_and_provider_share_fixed_parameters():
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
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(Inputs),
        ]
        lib.RootMachine_cycle.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
        ]
        lib.RootMachine_set_input_provider.argtypes = [
            ctypes.c_void_p,
            ctypes.POINTER(InputProvider),
            ctypes.c_void_p,
        ]
        lib.RootMachine_vars.argtypes = [ctypes.c_void_p]
        lib.RootMachine_vars.restype = ctypes.POINTER(Vars)
        lib.RootMachine_last_inputs.argtypes = [ctypes.c_void_p]
        lib.RootMachine_last_inputs.restype = ctypes.POINTER(Inputs)
        lib.RootMachine_get_param_gain.argtypes = [ctypes.c_void_p]
        lib.RootMachine_get_param_gain.restype = ctypes.c_int64
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
            assert not lib.RootMachine_last_inputs(machine)
            assert lib.RootMachine_cycle(machine, None, 0) == 0
            assert lib.RootMachine_vars(machine).contents.count == 7
            options.parameters.gain = 99
            assert lib.RootMachine_get_param_gain(machine) == 3
            assert (
                lib.RootMachine_cycle_with_inputs(
                    machine, None, 0, ctypes.byref(Inputs(4))
                )
                == 1
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
            assert lib.RootMachine_cycle(machine, None, 0) == 1
            assert len(reads) == 1
            assert lib.RootMachine_vars(machine).contents.count == 9
            assert lib.RootMachine_vars(machine).contents.result == 15
            assert lib.RootMachine_last_inputs(machine).contents.signal == 5
            invalid_event = ctypes.c_int(-99)
            assert lib.RootMachine_cycle(machine, ctypes.byref(invalid_event), 1) == 0
            assert len(reads) == 1

            @ReadSignal
            def failed_read(user_data, value):
                value[0] = 999
                return 0

            failed_provider = InputProvider(failed_read)
            lib.RootMachine_set_input_provider(
                machine, ctypes.byref(failed_provider), None
            )
            assert lib.RootMachine_cycle(machine, None, 0) == 0
            assert lib.RootMachine_vars(machine).contents.count == 9
            assert lib.RootMachine_vars(machine).contents.result == 15
            assert lib.RootMachine_last_inputs(machine).contents.signal == 5
            assert (
                lib.RootMachine_cycle_with_inputs(
                    machine, None, 0, ctypes.byref(Inputs(6))
                )
                == 1
            )
            assert lib.RootMachine_vars(machine).contents.result == 18
            lib.RootMachine_set_input_provider(machine, None, None)
            assert lib.RootMachine_cycle(machine, None, 0) == 0
        finally:
            if machine:
                lib.RootMachine_destroy(machine)


def test_native_hot_start_requires_complete_parameters():
    with render_c_artifacts(ROLE_MODEL) as artifacts:
        lib = ctypes.CDLL(artifacts["shared_lib"])
        lib.RootMachine_create_uninitialized.restype = ctypes.c_void_p
        lib.RootMachine_destroy.argtypes = [ctypes.c_void_p]
        lib.RootMachine_hot_start_with_parameters.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.POINTER(Vars),
            ctypes.POINTER(Parameters),
        ]
        lib.RootMachine_cycle_with_inputs.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_size_t,
            ctypes.POINTER(Inputs),
        ]
        lib.RootMachine_vars.argtypes = [ctypes.c_void_p]
        lib.RootMachine_vars.restype = ctypes.POINTER(Vars)
        lib.RootMachine_get_param_gain.argtypes = [ctypes.c_void_p]
        lib.RootMachine_get_param_gain.restype = ctypes.c_int64
        machine = None
        try:
            machine = lib.RootMachine_create_uninitialized()
            assert machine
            initial_vars = Vars(50, 60)
            assert (
                lib.RootMachine_hot_start_with_parameters(
                    machine, 1, ctypes.byref(initial_vars), None
                )
                == 0
            )
            parameters = Parameters(4)
            assert (
                lib.RootMachine_hot_start_with_parameters(
                    machine, 1, ctypes.byref(initial_vars), ctypes.byref(parameters)
                )
                == 1
            )
            parameters.gain = 99
            assert lib.RootMachine_get_param_gain(machine) == 4
            assert lib.RootMachine_vars(machine).contents.count == 50
            assert (
                lib.RootMachine_cycle_with_inputs(
                    machine, None, 0, ctypes.byref(Inputs(3))
                )
                == 1
            )
            assert lib.RootMachine_vars(machine).contents.count == 51
            assert lib.RootMachine_vars(machine).contents.result == 12
        finally:
            if machine:
                lib.RootMachine_destroy(machine)


IDENTIFIER_MODEL = """
input int a_b; input int a__b; input int a_b_; input int v_p5_class;
param int gain = 4; param int gain_ = 5; param float class = 2.5;
output float result = 0.0;
state Root { state Ready { during {
    result = a_b + 10 * a__b + 100 * a_b_ + 1000 * gain + 10000 * gain_ + 100000 * class;
} } [*] -> Ready; }
"""


def _check_native_identifier_layout(build_runtime):
    runtime = build_runtime(
        IDENTIFIER_MODEL, parameters={"gain_": 6}, initial_vars={"result": 99.0}
    )
    try:
        assert runtime.parameters == {"gain": 4, "gain_": 6, "class": 2.5}
        inputs = {"a_b": 1, "a__b": 2, "a_b_": 3, "v_p5_class": 7}
        runtime.cycle(inputs=inputs)
        assert runtime.outputs == {"result": 314321.0}
        assert runtime.last_inputs == inputs
        runtime.hot_start("Root.Ready", {"result": 1.0}, {"gain": 4, "gain_": 5, "class": 2.5})
        runtime.cycle(inputs=inputs)
        assert runtime.outputs == {"result": 304321.0}
    finally:
        runtime.close()


def test_native_identifier_fields_match_generated_abi():
    from ._utils import build_c_runtime
    _check_native_identifier_layout(build_c_runtime)
