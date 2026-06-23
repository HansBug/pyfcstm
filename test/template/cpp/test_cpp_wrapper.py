import re
import textwrap

import pytest

from ._utils import (
    available_compiler_pair,
    compile_and_run_cpp_wrapper_harness,
    compile_with_msvc_like_tool,
    render_cpp_artifacts,
)


_WRAPPER_DSL = """
def int counter = 0;
def int ready = 0;
state Root {
    enter abstract Boot;
    state Idle;
    state Active {
        enter abstract ActiveEnter;
    }
    state Done;
    [*] -> Idle;
    Idle -> Active :: Start effect { ready = 1; counter = counter + 10; };
    Active -> Done :: Stop effect { counter = counter + 20; };
}
"""


_RESERVED_ROOT_DSL = """
state _Root {
    state Idle;
    [*] -> Idle;
}
"""


_README_MULTI_EVENT_DSL = """
state Root {
    state Idle;
    state Active;
    state Done;
    [*] -> Idle;
    Idle -> Active :: Start;
    Active -> Done :: Stop;
}
"""


def _read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _strip_comments(source):
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.S)
    return re.sub(r"//.*", "", source)


def _assert_wrapper_source_contract(artifacts):
    header = _read(artifacts["machine_hpp_file"])
    source = _read(artifacts["machine_cpp_file"])
    generated = header + "\n" + source
    generated_code = _strip_comments(generated)

    assert "class MachineWrapper" in header
    assert "#include <stddef.h>" in header
    assert "typedef RootMachine Machine;" in header
    assert "typedef RootMachineVars Vars;" in header
    assert "typedef RootMachineEventId EventId;" in header
    assert "int cycle(const EventId *event_ids, size_t event_count);" in header
    assert "int cycle(EventId event_id);" in header
    assert "RootMachine_cycle(&machine_, event_ids, event_count)" in source
    assert "RootMachine_cycle(&machine_, &event_id, 1u)" in source
    assert "RootMachine_create" not in source
    assert "RootMachine_create_uninitialized" not in source

    for forbidden in (
        "throw",
        "try",
        "catch",
        "typeid",
        "dynamic_cast",
        "std::",
        "std::function",
        "lambda",
        "= delete",
        "machine_.stack",
        "machine_.vars",
        "machine_.hooks",
        "machine_.event_checks",
    ):
        assert forbidden not in generated_code
    assert not re.search(r"\bnew\b", generated_code)
    assert not re.search(r"\bdelete\b", generated_code)
    assert re.search(r"private:\s+MachineWrapper\(const MachineWrapper &\);", header)


def _harness_source():
    return textwrap.dedent(
        r"""
        #include "machine.hpp"
        #include <stddef.h>
        #include <string.h>

        typedef pyfcstm_generated::RootMachine_cpp::MachineWrapper Wrapper;

        typedef struct HookLog {
            int boot_calls;
            int active_calls;
            RootMachineInt boot_counter;
            RootMachineInt active_counter;
        } HookLog;

        static void boot_hook(
            RootMachine *machine,
            const RootMachineExecutionContext *ctx,
            void *user_data
        )
        {
            HookLog *log = (HookLog *)user_data;
            (void)machine;
            if (
                ctx->action_id == ROOT_MACHINE_ACTION_P4_ROOT_P4_BOOT &&
                ctx->state_id == ROOT_MACHINE_STATE_ROOT &&
                ctx->action_stage_id == ROOT_MACHINE_STAGE_ENTER
            ) {
                log->boot_calls += 1;
                log->boot_counter = ctx->vars->counter;
            }
        }

        static void active_hook(
            RootMachine *machine,
            const RootMachineExecutionContext *ctx,
            void *user_data
        )
        {
            HookLog *log = (HookLog *)user_data;
            (void)machine;
            if (
                ctx->action_id == ROOT_MACHINE_ACTION_P4_ROOT_P6_ACTIVE_P11_ACTIVEENTER &&
                ctx->state_id == ROOT_MACHINE_STATE_P4_ROOT_P6_ACTIVE &&
                ctx->action_stage_id == ROOT_MACHINE_STAGE_ENTER
            ) {
                log->active_calls += 1;
                log->active_counter = ctx->vars->counter;
            }
        }

        static int check_active_state(const Wrapper &wrapper)
        {
            if (wrapper.current_state_id() != ROOT_MACHINE_STATE_P4_ROOT_P6_ACTIVE) {
                return 1;
            }
            if (strcmp(wrapper.current_state_path(), "Root.Active") != 0) {
                return 2;
            }
            return 0;
        }

        int main()
        {
            Wrapper wrapper;
            RootMachineHooks hooks = ROOTMACHINE_HOOKS_INIT;
            HookLog log = {0, 0, 0, 0};
            static const RootMachineEventId start_and_stop_events[] = {
                ROOT_MACHINE_EVENT_P4_ROOT_P4_IDLE_P5_START,
                ROOT_MACHINE_EVENT_P4_ROOT_P6_ACTIVE_P4_STOP
            };

            if (wrapper.native_handle() == NULL) {
                return 10;
            }
            if (wrapper.vars() == NULL) {
                return 11;
            }
            if (wrapper.last_error() == NULL) {
                return 12;
            }

            hooks.on_p4_Root_p4_Boot = boot_hook;
            hooks.on_p4_Root_p6_Active_p11_ActiveEnter = active_hook;
            wrapper.set_hooks(&hooks, &log);

            if (!wrapper.cycle()) {
                return 20;
            }
            if (wrapper.current_state_id() != ROOT_MACHINE_STATE_P4_ROOT_P4_IDLE) {
                return 21;
            }
            if (strcmp(wrapper.current_state_path(), "Root.Idle") != 0) {
                return 22;
            }
            if (log.boot_calls != 1 || log.boot_counter != 0) {
                return 23;
            }

            if (!wrapper.cycle(start_and_stop_events, 2u)) {
                return 30;
            }
            if (check_active_state(wrapper) != 0) {
                return 31;
            }
            if (wrapper.vars()->counter != (RootMachineInt)10 || wrapper.vars()->ready != (RootMachineInt)1) {
                return 32;
            }
            if (log.active_calls != 1 || log.active_counter != (RootMachineInt)10) {
                return 33;
            }

            if (!wrapper.cycle((RootMachineEventId)ROOT_MACHINE_EVENT_P4_ROOT_P6_ACTIVE_P4_STOP)) {
                return 40;
            }
            if (wrapper.current_state_id() != ROOT_MACHINE_STATE_P4_ROOT_P4_DONE) {
                return 41;
            }
            if (wrapper.vars()->counter != (RootMachineInt)30) {
                return 42;
            }

            {
                RootMachineVars initial_vars = *wrapper.vars();
                initial_vars.counter = (RootMachineInt)7;
                initial_vars.ready = (RootMachineInt)1;
                if (!wrapper.hot_start(ROOT_MACHINE_STATE_P4_ROOT_P6_ACTIVE, initial_vars)) {
                    return 50;
                }
            }
            if (check_active_state(wrapper) != 0) {
                return 51;
            }
            if (wrapper.vars()->counter != (RootMachineInt)7) {
                return 52;
            }

            if (!wrapper.init()) {
                return 60;
            }
            if (!wrapper.cycle()) {
                return 61;
            }
            if (wrapper.current_state_id() != ROOT_MACHINE_STATE_P4_ROOT_P4_IDLE) {
                return 62;
            }

            return 0;
        }
        """
    )


def _extract_cpp_code_block(markdown, heading):
    pattern = r"## {heading}\n\n```cpp\n(.*?)\n```".format(heading=re.escape(heading))
    match = re.search(pattern, markdown, re.S)
    assert match is not None, "Cannot find C++ code block under {!r}.".format(heading)
    return match.group(1)


def _compile_probe_source():
    return textwrap.dedent(
        r"""
        #include "machine.hpp"
        #include <stddef.h>

        typedef pyfcstm_generated::RootMachine_cpp::MachineWrapper Wrapper;

        int main()
        {
            Wrapper wrapper;
            RootMachineVars vars = *wrapper.vars();
            RootMachineEventId event_id = ROOT_MACHINE_EVENT_P4_ROOT_P4_IDLE_P5_START;
            RootMachineEventId event_ids[] = { event_id };
            wrapper.set_hooks((const RootMachineHooks *)0, (void *)0);
            wrapper.hot_start(ROOT_MACHINE_STATE_P4_ROOT_P4_IDLE, &vars);
            wrapper.hot_start(ROOT_MACHINE_STATE_P4_ROOT_P4_IDLE, vars);
            wrapper.cycle();
            wrapper.cycle(event_id);
            wrapper.cycle(event_ids, 1u);
            return wrapper.native_handle() == 0;
        }
        """
    )


@pytest.mark.unittest
class TestCppWrapperTemplate:
    def test_wrapper_api_compiles_and_runs_with_cmake(self):
        with render_cpp_artifacts(_WRAPPER_DSL) as artifacts:
            _assert_wrapper_source_contract(artifacts)
            result = compile_and_run_cpp_wrapper_harness(
                artifacts,
                "cpp_wrapper_api",
                _harness_source(),
            )
        assert result.returncode == 0, result.stderr

    def test_wrapper_generated_english_readme_quick_start_runs(self):
        with render_cpp_artifacts(_README_MULTI_EVENT_DSL) as artifacts:
            readme = _read(artifacts["readme_file"])
            source = _extract_cpp_code_block(readme, "C++ Wrapper Quick Start")
            result = compile_and_run_cpp_wrapper_harness(
                artifacts,
                "cpp_readme_quick_start_en",
                source,
            )
        assert result.returncode == 0, result.stderr

    def test_wrapper_generated_chinese_readme_quick_start_runs(self):
        with render_cpp_artifacts(_README_MULTI_EVENT_DSL) as artifacts:
            readme = _read(artifacts["readme_zh_file"])
            source = _extract_cpp_code_block(readme, "C++ Wrapper 快速开始")
            result = compile_and_run_cpp_wrapper_harness(
                artifacts,
                "cpp_readme_quick_start_zh",
                source,
            )
        assert result.returncode == 0, result.stderr

    def test_wrapper_no_heap_profile_compiles_and_runs(self):
        with render_cpp_artifacts(_WRAPPER_DSL) as artifacts:
            result = compile_and_run_cpp_wrapper_harness(
                artifacts,
                "cpp_wrapper_no_heap",
                _harness_source(),
                compile_definitions=["PYFCSTM_GENERATED_NO_HEAP"],
            )
        assert result.returncode == 0, result.stderr

    def test_wrapper_compiles_with_gnu_no_exception_rtti_flags_when_available(self):
        c_compiler, cxx_compiler = available_compiler_pair("gcc", "g++")
        with render_cpp_artifacts(_WRAPPER_DSL) as artifacts:
            result = compile_and_run_cpp_wrapper_harness(
                artifacts,
                "cpp_wrapper_gnu_no_exception_rtti",
                _harness_source(),
                c_compiler=c_compiler,
                cxx_compiler=cxx_compiler,
                cxx_compile_options=["-fno-exceptions", "-fno-rtti"],
            )
        assert result.returncode == 0, result.stderr

    def test_wrapper_compiles_with_clang_when_available(self):
        c_compiler, cxx_compiler = available_compiler_pair("clang", "clang++")
        with render_cpp_artifacts(_WRAPPER_DSL) as artifacts:
            result = compile_and_run_cpp_wrapper_harness(
                artifacts,
                "cpp_wrapper_clang",
                _harness_source(),
                c_compiler=c_compiler,
                cxx_compiler=cxx_compiler,
                cxx_compile_options=["-fno-exceptions", "-fno-rtti"],
            )
        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize("tool_name", ["cl", "clang-cl"])
    def test_wrapper_has_minimal_msvc_like_compile_gate_when_available(self, tool_name):
        with render_cpp_artifacts(_WRAPPER_DSL) as artifacts:
            compile_with_msvc_like_tool(
                artifacts,
                "cpp_wrapper_" + tool_name.replace("-", "_"),
                _compile_probe_source(),
                tool_name,
            )

    def test_wrapper_reserved_public_names_stay_safe(self):
        with render_cpp_artifacts(_RESERVED_ROOT_DSL) as artifacts:
            header = _read(artifacts["machine_hpp_file"])
            source = _read(artifacts["machine_cpp_file"])

        assert "namespace p_p5_z00005FRootMachine_cpp" in header
        assert "PYFCSTM_GENERATED_P_P5_Z00005FROOT_MACHINE_CPP_HPP" in header
        public_names = re.findall(r"\b[A-Za-z_]\w*\b", header + "\n" + source)
        assert not [name for name in public_names if "__" in name]
