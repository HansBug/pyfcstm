"""C++98 wrappers expose role APIs without owning a second execution engine."""

import pytest

from ._utils import render_cpp_artifacts, compile_and_run_cpp_wrapper_harness
from ..cpp_poll._utils import render_cpp_poll_artifacts as render_poll_artifacts
from ..cpp_poll._utils import (
    compile_and_run_cpp_poll_wrapper_harness as compile_poll_harness,
)
from ..c.test_variable_roles import ROLE_MODEL, IDENTIFIER_MODEL


pytestmark = pytest.mark.unittest


def _check_cpp_role_integration(polled):
    render = render_poll_artifacts if polled else render_cpp_artifacts
    compile_harness = (
        compile_poll_harness if polled else compile_and_run_cpp_wrapper_harness
    )
    namespace = "RootMachine_cpp_poll" if polled else "RootMachine_cpp"
    source = r"""
#include "machine.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
typedef pyfcstm_generated::NAMESPACE::MachineWrapper Wrapper;
static void observe(RootMachine *native, const RootMachineExecutionContext *context, void *data) {
    (void)native;
    (void)context;
    Wrapper *machine = static_cast<Wrapper *>(data);
    assert(machine->get_input_signal() > 0);
    assert(machine->get_input_unused() > 0);
    assert(machine->get_param_gain() > 0);
}
static int read_signal(void *data, RootMachineInt *value) {
    int *reads = static_cast<int *>(data);
    ++*reads;
    *value = 5;
    return 1;
}
static int fail_unused(void *data, RootMachineInt *value) {
    (void)data;
    (void)value;
    return 0;
}
int main() {
    Wrapper::InitOptions options;
    memset(&options, 0, sizeof(options));
    options.parameters.gain = 3;
    options.parameters_present.gain = 1;
    options.vars.count = 7;
    options.vars_present.count = 1;
    Wrapper machine(options);
    Wrapper::Hooks hooks;
    memset(&hooks, 0, sizeof(hooks));
    hooks.on_p4_Root_p5_Ready_p7_Observe = observe;
    machine.set_hooks(&hooks, &machine);
    options.parameters.gain = 99;
    assert(machine.get_param_gain() == 3);
    Wrapper::Inputs inputs;
    inputs.signal = 4;
    inputs.unused = 9;
    assert(machine.cycle_with_inputs(inputs) == 1);
    assert(machine.vars()->count == 8);
    assert(machine.vars()->result == 12);
    assert(machine.last_inputs()->signal == 4);
    Wrapper::InputProvider provider;
    memset(&provider, 0, sizeof(provider));
    provider.read_signal = read_signal;
    int reads = 0;
    machine.set_input_provider(&provider, &reads);
    assert(machine.cycle() == 0);
    assert(reads == 1);
    assert(machine.vars()->count == 8);
    assert(machine.last_inputs()->unused == 9);
    provider.read_unused = fail_unused;
    machine.set_input_provider(&provider, &reads);
    assert(machine.cycle() == 0);
    assert(reads == 2);
    assert(machine.vars()->result == 12);
    assert(machine.last_inputs()->unused == 9);
    provider.read_unused = read_signal;
    reads = 0;
    machine.set_input_provider(&provider, &reads);
    assert(machine.cycle() == 1);
    assert(reads == 2);
    assert(machine.vars()->result == 15);
    Wrapper::Parameters parameters;
    parameters.gain = 4;
    Wrapper::Vars initial = *machine.vars();
    initial.count = 50;
    assert(machine.hot_start(machine.current_state_id(), initial, parameters) == 1);
    assert(machine.cycle_with_inputs(inputs) == 1);
    assert(machine.vars()->count == 51);
    assert(machine.vars()->result == 16);
    assert(machine.cycle() == 1);
    assert(reads == 4);
    assert(machine.vars()->count == 52);
    assert(machine.vars()->result == 20);
    assert(machine.init(options) == 1);
    assert(machine.get_param_gain() == 99);
    return 0;
}
""".replace("NAMESPACE", namespace)
    dsl = ROLE_MODEL.replace("input int signal;", "input int signal; input int unused;")
    dsl = dsl.replace("state Ready {", "state Ready { during abstract Observe;")
    with render(dsl) as artifacts:
        result = compile_harness(artifacts, "role_integration", source)
        assert result.returncode == 0, result.stderr


def test_cpp_role_integration():
    _check_cpp_role_integration(False)


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
    _check_integer_conversion(False, initializer, value, error)


def _check_integer_conversion(polled, initializer, value, error):
    source = (
        "param int gain = %s; state Root;" % value
        if initializer else
        "input float signal; output int result = 0; state Root { during { result = signal; } }"
    )
    status = 0 if error else 1
    if initializer:
        body = "assert(machine.init() == %d);" % status
        if error is None:
            body += " assert(machine.get_param_gain() == %s);" % value
    else:
        body = "Wrapper::Inputs inputs; inputs.signal = %s; " % value
        body += "assert(machine.cycle_with_inputs(inputs) == %d); " % status
        body += "assert(machine.vars()->result == %s);" % ("0" if error else value)
    if error:
        body += ' assert(strstr(machine.last_error(), "%s") != NULL);' % error
    harness = r"""
#include "machine.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
typedef pyfcstm_generated::RootMachine_cpp::MachineWrapper Wrapper;
int main() {
    Wrapper machine;
    BODY
    return 0;
}
""".replace("BODY", body)
    render = render_poll_artifacts if polled else render_cpp_artifacts
    compile_harness = compile_poll_harness if polled else compile_and_run_cpp_wrapper_harness
    if polled:
        harness = harness.replace("RootMachine_cpp::", "RootMachine_cpp_poll::")
    with render(source) as artifacts:
        result = compile_harness(artifacts, "integer_range", harness)
        assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("numeric_profile", ["integers", "float_input", "float_values"])
def test_native_role_api_failure_boundaries(numeric_profile):
    _check_role_api_failure_boundaries(False, numeric_profile)


def _check_role_api_failure_boundaries(polled, numeric_profile):
    """Check C core failure contracts, including calls without an instance."""
    render = render_poll_artifacts if polled else render_cpp_artifacts
    compile_harness = compile_poll_harness if polled else compile_and_run_cpp_wrapper_harness
    dsl = ROLE_MODEL.replace("[*] -> Ready;", "[*] -> Ready; Ready -> [*] : if [signal < 0];")
    dsl = dsl.replace("result = signal * gain;", "result = signal * gain + 0 / signal;")
    if numeric_profile != "integers":
        dsl = dsl.replace("input int signal;", "input float signal;")
    if numeric_profile == "float_values":
        dsl = dsl.replace("param int gain = 2;", "param float gain = 2.0;")
        dsl = dsl.replace("output int result = 0;", "output float result = 0.0;")
    else:
        dsl = dsl.replace("param int gain = 2;", "param int gain = 2.0;")
    harness = r'''
#include "machine.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
#include <limits>
static int snapshot(RootMachine *machine, const RootMachineInputs *inputs) {
    return SNAPSHOT_CALL;
}
static int acquire(RootMachine *machine) {
    return PROVIDER_CALL;
}
static int read_signal(void *data, RootMachineInt *value) {
    ++*static_cast<int *>(data);
    *value = 7;
    return 1;
}
static int fail_signal(void *data, RootMachineInt *value) {
    (void)data;
    *value = 99;
    return 0;
}
int main() {
    RootMachine machine;
    RootMachineInitOptions options;
    RootMachineInputs inputs;
    RootMachineInputProvider provider;
    RootMachineVars initial;
    RootMachineParameters parameters;
    int reads = 0;
    memset(&machine, 0, sizeof(machine));
    memset(&options, 0, sizeof(options));
    memset(&provider, 0, sizeof(provider));
    inputs.signal = 2;
    assert(RootMachine_init_with_options(NULL, NULL) == 0);
    assert(snapshot(NULL, &inputs) == 0);
    assert(snapshot(&machine, &inputs) == 0);
    assert(RootMachine_last_inputs(NULL) == NULL);
    RootMachine_set_input_provider(NULL, NULL, NULL);
    assert(RootMachine_init_with_options(&machine, NULL) == 1);
    assert(RootMachine_get_param_gain(&machine) == 2);
    assert(RootMachine_last_inputs(&machine) == NULL);
    {
        RootMachineInitOptions configured = options;
        configured.parameters.gain = 3;
        configured.parameters_present.gain = 1;
        assert(RootMachine_init_with_options(&machine, &configured) == 1);
        configured.parameters.gain = 99;
        assert(RootMachine_get_param_gain(&machine) == 3);
    }
    options.vars.result = 9;
    options.vars_present.result = 1;
    assert(RootMachine_init_with_options(&machine, &options) == 1);
    assert(RootMachine_vars(&machine)->count == 0);
    assert(RootMachine_vars(&machine)->result == 9);
    FINITE_CONFIGURATION_CHECKS
    assert(acquire(&machine) == 0);
    assert(snapshot(&machine, &inputs) == 1);
    assert(RootMachine_last_inputs(&machine)->signal == 2);
    {
        RootMachineInputs zero;
        zero.signal = 0;
        assert(snapshot(&machine, &zero) == 0);
        assert(RootMachine_last_inputs(&machine)->signal == 2);
        assert(RootMachine_vars(&machine)->count == 1);
        assert(RootMachine_vars(&machine)->result == 4);
    }
    FINITE_INPUT_CHECKS
    INVALID_EVENTS
    initial.count = 50;
    initial.result = 60;
    parameters.gain = 4;
    assert(RootMachine_hot_start_with_parameters(NULL, 1, &initial, &parameters) == 0);
    assert(RootMachine_hot_start_with_parameters(&machine, 1, NULL, &parameters) == 0);
    assert(RootMachine_hot_start(&machine, 1, &initial) == 0);
    assert(RootMachine_hot_start_with_parameters(&machine, 999, &initial, &parameters) == 0);
    assert(RootMachine_get_param_gain(&machine) == 2);
    assert(RootMachine_hot_start_with_parameters(&machine, 0, &initial, &parameters) == 1);
    assert(RootMachine_current_state_id(&machine) == 0);
    assert(RootMachine_hot_start_with_parameters(&machine, 1, &initial, &parameters) == 1);
    parameters.gain = 99;
    assert(RootMachine_get_param_gain(&machine) == 4);
    FINITE_HOT_CHECKS
    assert(RootMachine_last_inputs(&machine) == NULL);
    provider.read_signal = fail_signal;
    RootMachine_set_input_provider(&machine, &provider, NULL);
    assert(acquire(&machine) == 0);
    assert(RootMachine_vars(&machine)->count == 50);
    assert(RootMachine_vars(&machine)->result == 60);
    assert(RootMachine_last_inputs(&machine) == NULL);
    provider.read_signal = read_signal;
    RootMachine_set_input_provider(&machine, &provider, &reads);
    provider.read_signal = NULL;
    assert(acquire(&machine) == 1);
    assert(reads == 1);
    assert(RootMachine_vars(&machine)->result == 28);
    assert(RootMachine_last_inputs(&machine)->signal == 7);
    RootMachine_set_input_provider(&machine, NULL, NULL);
    assert(acquire(&machine) == 0);
    assert(RootMachine_last_inputs(&machine)->signal == 7);
    inputs.signal = -1;
    assert(snapshot(&machine, &inputs) == 1);
    assert(RootMachine_is_ended(&machine));
    assert(acquire(&machine) == 1);
    assert(reads == 1);
    assert(RootMachine_last_inputs(&machine)->signal == -1);
    return 0;
}
'''
    invalid_values = "double invalid_values[] = {std::numeric_limits<double>::quiet_NaN(), std::numeric_limits<double>::infinity(), -std::numeric_limits<double>::infinity()};"
    if numeric_profile != "integers":
        harness = harness.replace("RootMachineInt *value", "double *value")
        input_checks = """{
            INVALID_VALUES
            for (int i = 0; i < 3; ++i) {
                RootMachineInputs invalid_inputs;
                invalid_inputs.signal = invalid_values[i];
                assert(snapshot(&machine, &invalid_inputs) == 0);
                assert(RootMachine_last_inputs(&machine)->signal == 2);
                assert(RootMachine_vars(&machine)->result == 4);
            }
        }""".replace("INVALID_VALUES", invalid_values)
    else:
        input_checks = ""
    if numeric_profile == "float_values":
        configuration_checks = """{
            INVALID_VALUES
            for (int i = 0; i < 3; ++i) {
                RootMachineInitOptions invalid_options = options;
                invalid_options.parameters.gain = invalid_values[i];
                invalid_options.parameters_present.gain = 1;
                assert(RootMachine_init_with_options(&machine, &invalid_options) == 0);
                invalid_options = options;
                invalid_options.vars.result = invalid_values[i];
                invalid_options.vars_present.result = 1;
                assert(RootMachine_init_with_options(&machine, &invalid_options) == 0);
            }
            assert(RootMachine_init_with_options(&machine, &options) == 1);
        }""".replace("INVALID_VALUES", invalid_values)
        hot_checks = """{
            INVALID_VALUES
            for (int i = 0; i < 3; ++i) {
                RootMachineParameters invalid_parameters = parameters;
                invalid_parameters.gain = invalid_values[i];
                assert(RootMachine_hot_start_with_parameters(&machine, 1, &initial, &invalid_parameters) == 0);
                RootMachineVars invalid_vars = initial;
                invalid_vars.result = invalid_values[i];
                assert(RootMachine_hot_start_with_parameters(&machine, 1, &invalid_vars, &parameters) == 0);
                assert(RootMachine_get_param_gain(&machine) == 4);
                assert(RootMachine_vars(&machine)->count == 50);
                assert(RootMachine_vars(&machine)->result == 60);
            }
        }""".replace("INVALID_VALUES", invalid_values)
    else:
        configuration_checks = ""
        hot_checks = ""
    harness = harness.replace("FINITE_INPUT_CHECKS", input_checks)
    harness = harness.replace("FINITE_CONFIGURATION_CHECKS", configuration_checks)
    harness = harness.replace("FINITE_HOT_CHECKS", hot_checks)
    harness = harness.replace("SNAPSHOT_CALL", "RootMachine_cycle_with_inputs(machine, inputs)" if polled else "RootMachine_cycle_with_inputs(machine, NULL, 0u, inputs)")
    harness = harness.replace("PROVIDER_CALL", "RootMachine_cycle(machine)" if polled else "RootMachine_cycle(machine, NULL, 0u)")
    harness = harness.replace("INVALID_EVENTS", "" if polled else "RootMachineEventId invalid_event = -99; assert(RootMachine_cycle(&machine, &invalid_event, 1u) == 0);")
    with render(dsl) as artifacts:
        result = compile_harness(artifacts, "role_api_boundaries", harness)
        assert result.returncode == 0, result.stderr


def _check_configuration_failures(polled, role, value):
    """An explicit cold value bypasses an invalid DSL default initializer."""
    render = render_poll_artifacts if polled else render_cpp_artifacts
    compile_harness = compile_poll_harness if polled else compile_and_run_cpp_wrapper_harness
    dsl = "%s int gain = %s; state Root;" % (role, value)
    storage = "parameters" if role == "param" else "vars"
    harness = r'''
#include "machine.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
int main() {
    RootMachine machine;
    RootMachineInitOptions options;
    memset(&machine, 0, sizeof(machine));
    memset(&options, 0, sizeof(options));
    assert(RootMachine_init_with_options(&machine, NULL) == DEFAULT_STATUS);
    assert(RootMachine_init_with_options(&machine, &options) == DEFAULT_STATUS);
    options.STORAGE.gain = 3;
    options.STORAGE_present.gain = 1;
    assert(RootMachine_init_with_options(&machine, &options) == 1);
    assert(GET_VALUE == 3);
    return 0;
}
'''.replace("DEFAULT_STATUS", "1" if value == "2.0" else "0").replace("STORAGE", storage).replace(
        "GET_VALUE", "RootMachine_get_param_gain(&machine)" if role == "param"
        else "RootMachine_vars(&machine)->gain")
    with render(dsl) as artifacts:
        result = compile_harness(artifacts, "invalid_default", harness)
        assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("role", ["param", "output"])
@pytest.mark.parametrize("value", ["1.5", "1.0e100", "-1.0e100", "2.0", "1 / 0"])
def test_explicit_configuration_bypasses_invalid_default(role, value):
    _check_configuration_failures(False, role, value)


def _check_deep_hot_start(polled):
    render = render_poll_artifacts if polled else render_cpp_artifacts
    compile_harness = compile_poll_harness if polled else compile_and_run_cpp_wrapper_harness
    dsl = "param int gain = 2; output int result = 0; state Root { "
    dsl += " ".join("state S%d {" % i for i in range(65))
    dsl += "state Leaf; [*] -> Leaf; }"
    dsl += " ".join("[*] -> S%d; }" % i for i in reversed(range(65)))
    harness = r'''
#include "machine.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
int main() {
    RootMachine machine;
    RootMachineVars vars;
    RootMachineParameters parameters;
    memset(&machine, 0, sizeof(machine));
    vars.result = 9;
    parameters.gain = 4;
    assert(RootMachine_init(&machine) == 1);
    assert(RootMachine_hot_start_with_parameters(&machine, 66, &vars, &parameters) == 0);
    assert(strstr(RootMachine_last_error(&machine), "stack-depth safety limit") != NULL);
    assert(RootMachine_get_param_gain(&machine) == 2);
    assert(RootMachine_vars(&machine)->result == 0);
    assert(RootMachine_current_state_id(&machine) == 0);
    return 0;
}
'''
    with render(dsl) as artifacts:
        result = compile_harness(artifacts, "deep_hot_configuration", harness)
        assert result.returncode == 0, result.stderr


def test_deep_hot_start_preserves_configuration():
    _check_deep_hot_start(False)


def _check_poll_input_event_mount():
    dsl = ROLE_MODEL.replace("[*] -> Ready;", "[*] -> Ready; Ready -> Ready :: Tick;")
    harness = r'''
#include "machine.h"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
static int check_tick(RootMachine *machine, const RootMachineEventContext *context, void *data) {
    (void)context;
    (void)data;
    assert(RootMachine_get_input_signal(machine) == 3);
    return 0;
}
int main() {
    RootMachine machine;
    RootMachineInputs inputs;
    RootMachineEventChecks checks;
    memset(&checks, 0, sizeof(checks));
    inputs.signal = 3;
    assert(RootMachine_init(&machine) == 1);
    assert(RootMachine_cycle_with_inputs(&machine, &inputs) == 0);
    assert(RootMachine_last_inputs(&machine) == NULL);
    checks.check_p4_Root_p5_Ready_p4_Tick = check_tick;
    RootMachine_set_event_checks(&machine, &checks, NULL);
    assert(RootMachine_cycle_with_inputs(&machine, &inputs) == 1);
    assert(RootMachine_cycle_with_inputs(&machine, &inputs) == 1);
    assert(RootMachine_last_inputs(&machine)->signal == 3);
    return 0;
}
'''
    with render_poll_artifacts(dsl) as artifacts:
        result = compile_poll_harness(artifacts, "input_event_mount", harness)
        assert result.returncode == 0, result.stderr


def _check_role_readme_example(polled, wrapper, language):
    from pathlib import Path
    import re

    render = render_poll_artifacts if polled else render_cpp_artifacts
    compile_harness = compile_poll_harness if polled else compile_and_run_cpp_wrapper_harness
    with render(ROLE_MODEL) as artifacts:
        if not wrapper:
            from pyfcstm.render import StateMachineCodeRenderer
            from pyfcstm.template import extract_template
            from tempfile import TemporaryDirectory
            with TemporaryDirectory() as directory:
                template = extract_template("c_poll" if polled else "c", directory)
                StateMachineCodeRenderer(template).render(
                    model=artifacts["model"], output_dir=artifacts["output_dir"])
        filename = "README.md" if language == "en" else "README_zh.md"
        readme = (Path(artifacts["output_dir"]) / filename).read_text(encoding="utf-8")
        source = re.findall(r"```(?:c|cpp)\n(.*?)```", readme, re.DOTALL)[-1]
        # The wrapper source is still linked when checking the byte-identical C core.
        result = compile_harness(artifacts, "role_readme", source)
        assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("wrapper", [False, True], ids=["c", "cpp"])
@pytest.mark.parametrize("language", ["en", "zh"])
def test_role_readme_example_runs(wrapper, language):
    _check_role_readme_example(False, wrapper, language)


def _check_role_identifier_spelling(polled):
    render = render_poll_artifacts if polled else render_cpp_artifacts
    compile_harness = compile_poll_harness if polled else compile_and_run_cpp_wrapper_harness
    harness = r'''
#include "machine.hpp"
#ifdef NDEBUG
#undef NDEBUG
#endif
#include <assert.h>
#include <string.h>
typedef pyfcstm_generated::NAMESPACE::MachineWrapper Wrapper;
int main() {
    Wrapper machine;
    assert(machine.get_param_gain() == 4);
    assert(machine.get_param_v_p5_gainz00005F() == 5);
    assert(machine.get_param_v_p5_class() == 2.5);
    Wrapper::Inputs inputs;
    memset(&inputs, 0, sizeof(inputs));
    inputs.a_b = 1;
    inputs.v_p4_az00005Fz00005Fb = 2;
    inputs.v_p4_az00005Fbz00005F = 3;
    inputs.v_p10_vz00005Fp5z00005Fclass = 7;
    assert(machine.cycle_with_inputs(inputs) == 1);
    assert(machine.vars()->result == 304321.0);
    assert(machine.last_inputs()->v_p10_vz00005Fp5z00005Fclass == 7);
    Wrapper::InitOptions options;
    memset(&options, 0, sizeof(options));
    options.parameters.v_p5_gainz00005F = 6;
    options.parameters_present.v_p5_gainz00005F = 1;
    assert(machine.init(options) == 1);
    assert(machine.get_param_v_p5_gainz00005F() == 6);
    return 0;
}
'''.replace("NAMESPACE", "RootMachine_cpp_poll" if polled else "RootMachine_cpp")
    with render(IDENTIFIER_MODEL) as artifacts:
        result = compile_harness(artifacts, "role_identifiers", harness)
        assert result.returncode == 0, result.stderr


def test_role_identifiers_remain_distinct():
    _check_role_identifier_spelling(False)
