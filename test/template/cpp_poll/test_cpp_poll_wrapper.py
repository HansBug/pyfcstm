import re
import textwrap

import pytest

from test.template.cpp_readme_utils import run_readme_command_block
from ._utils import (
    available_compiler_pair,
    compile_and_run_cpp_poll_wrapper_harness,
    compile_with_msvc_like_tool,
    render_cpp_poll_artifacts,
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
    assert "typedef RootMachineEventChecks EventChecks;" in header
    assert (
        "void set_event_checks(const EventChecks *event_checks, void *user_data);"
        in header
    )
    assert "int cycle();" in header
    assert "bool last_cycle_was_delta() const;" in header
    assert "RootMachine_set_event_checks(" in source
    assert "&machine_," in source
    assert "event_checks," in source
    assert "user_data)" in source
    assert "RootMachine_cycle(&machine_)" in source
    assert "RootMachine_last_cycle_was_delta(&machine_)" in source
    assert "RootMachine_create" not in source
    assert "RootMachine_create_uninitialized" not in source
    assert "cycle(const EventId *event_ids" not in header
    assert "cycle(EventId event_id)" not in header

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

        typedef pyfcstm_generated::RootMachine_cpp_poll::MachineWrapper Wrapper;

        typedef struct Log {
            int boot_calls;
            int active_calls;
            int start_active;
            int stop_active;
            RootMachineInt boot_counter;
            RootMachineInt active_counter;
        } Log;

        static void boot_hook(
            RootMachine *machine,
            const RootMachineExecutionContext *ctx,
            void *user_data
        )
        {
            Log *log = (Log *)user_data;
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
            Log *log = (Log *)user_data;
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

        static int check_start(
            RootMachine *machine,
            const RootMachineEventContext *ctx,
            void *user_data
        )
        {
            Log *log = (Log *)user_data;
            (void)machine;
            if (ctx->event_id != ROOT_MACHINE_EVENT_P4_ROOT_P4_IDLE_P5_START) {
                return 0;
            }
            return log->start_active;
        }

        static int check_stop(
            RootMachine *machine,
            const RootMachineEventContext *ctx,
            void *user_data
        )
        {
            Log *log = (Log *)user_data;
            (void)machine;
            if (ctx->event_id != ROOT_MACHINE_EVENT_P4_ROOT_P6_ACTIVE_P4_STOP) {
                return 0;
            }
            return log->stop_active;
        }

        int main()
        {
            Wrapper wrapper;
            RootMachineHooks hooks = ROOTMACHINE_HOOKS_INIT;
            RootMachineEventChecks event_checks = ROOTMACHINE_EVENT_CHECKS_INIT;
            Log log = {0, 0, 0, 0, 0, 0};

            if (wrapper.native_handle() == NULL) {
                return 10;
            }
            if (wrapper.vars() == NULL) {
                return 11;
            }
            if (wrapper.last_error() == NULL) {
                return 12;
            }
            if (wrapper.last_cycle_was_delta()) {
                return 13;
            }

            hooks.on_p4_Root_p4_Boot = boot_hook;
            hooks.on_p4_Root_p6_Active_p11_ActiveEnter = active_hook;
            wrapper.set_hooks(&hooks, &log);
            event_checks.check_p4_Root_p4_Idle_p5_Start = check_start;
            event_checks.check_p4_Root_p6_Active_p4_Stop = check_stop;
            wrapper.set_event_checks(&event_checks, &log);

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

            log.start_active = 1;
            if (!wrapper.cycle()) {
                return 30;
            }
            if (wrapper.current_state_id() != ROOT_MACHINE_STATE_P4_ROOT_P6_ACTIVE) {
                return 31;
            }
            if (wrapper.vars()->counter != (RootMachineInt)10 || wrapper.vars()->ready != (RootMachineInt)1) {
                return 32;
            }
            if (log.active_calls != 1 || log.active_counter != (RootMachineInt)10) {
                return 33;
            }

            log.stop_active = 1;
            if (!wrapper.cycle()) {
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
                if (!wrapper.hot_start(ROOT_MACHINE_STATE_P4_ROOT_P6_ACTIVE, &initial_vars)) {
                    return 50;
                }
            }
            if (wrapper.current_state_id() != ROOT_MACHINE_STATE_P4_ROOT_P6_ACTIVE) {
                return 51;
            }
            if (wrapper.vars()->counter != (RootMachineInt)7) {
                return 52;
            }

            if (!wrapper.init()) {
                return 60;
            }
            wrapper.set_hooks(&hooks, &log);
            wrapper.set_event_checks(&event_checks, &log);
            log.start_active = 0;
            log.stop_active = 0;
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


def _compile_probe_source():
    return textwrap.dedent(
        r"""
        #include "machine.hpp"
        #include <stddef.h>

        typedef pyfcstm_generated::RootMachine_cpp_poll::MachineWrapper Wrapper;

        int main()
        {
            Wrapper wrapper;
            RootMachineVars vars = *wrapper.vars();
            RootMachineEventChecks event_checks = ROOTMACHINE_EVENT_CHECKS_INIT;
            wrapper.set_hooks((const RootMachineHooks *)0, (void *)0);
            wrapper.set_event_checks(&event_checks, (void *)0);
            wrapper.hot_start(ROOT_MACHINE_STATE_P4_ROOT_P4_IDLE, &vars);
            wrapper.hot_start(ROOT_MACHINE_STATE_P4_ROOT_P4_IDLE, vars);
            wrapper.cycle();
            return wrapper.native_handle() == 0;
        }
        """
    )


def _extract_cpp_code_block(markdown, heading):
    pattern = r"## {heading}\n\n```cpp\n(.*?)\n```".format(heading=re.escape(heading))
    match = re.search(pattern, markdown, re.S)
    assert match is not None, "Cannot find C++ code block under {!r}.".format(heading)
    return match.group(1)


def _extract_named_bash_block(markdown, marker):
    pattern = r"{marker}.*?```bash\n(.*?)\n```".format(marker=re.escape(marker))
    match = re.search(pattern, markdown, re.S)
    assert match is not None, "Cannot find bash command block after {!r}.".format(
        marker
    )
    return match.group(1)


@pytest.mark.unittest
class TestCppPollWrapperTemplate:
    def test_poll_wrapper_api_compiles_and_runs_with_cmake(self):
        with render_cpp_poll_artifacts(_WRAPPER_DSL) as artifacts:
            _assert_wrapper_source_contract(artifacts)
            result = compile_and_run_cpp_poll_wrapper_harness(
                artifacts,
                "cpp_poll_wrapper_api",
                _harness_source(),
            )
        assert result.returncode == 0, result.stderr

    def test_poll_wrapper_generated_english_readme_quick_start_runs(self):
        with render_cpp_poll_artifacts(_README_MULTI_EVENT_DSL) as artifacts:
            readme = _read(artifacts["readme_file"])
            source = _extract_cpp_code_block(readme, "C++ Poll Wrapper Quick Start")
            result = compile_and_run_cpp_poll_wrapper_harness(
                artifacts,
                "cpp_poll_readme_quick_start_en",
                source,
            )
        assert result.returncode == 0, result.stderr

    def test_poll_wrapper_generated_chinese_readme_quick_start_runs(self):
        with render_cpp_poll_artifacts(_README_MULTI_EVENT_DSL) as artifacts:
            readme = _read(artifacts["readme_zh_file"])
            source = _extract_cpp_code_block(readme, "C++ Poll Wrapper 快速开始")
            result = compile_and_run_cpp_poll_wrapper_harness(
                artifacts,
                "cpp_poll_readme_quick_start_zh",
                source,
            )
        assert result.returncode == 0, result.stderr

    def test_poll_wrapper_generated_english_readme_gcc_direct_commands_run(self):
        with render_cpp_poll_artifacts(_README_MULTI_EVENT_DSL) as artifacts:
            readme = _read(artifacts["readme_file"])
            source = _extract_cpp_code_block(readme, "C++ Poll Wrapper Quick Start")
            commands = _extract_named_bash_block(
                readme,
                "Compile the C poll core as C99",
            )
            result = run_readme_command_block(
                artifacts,
                "cpp_poll_readme_gcc_direct_en",
                source,
                commands,
            )
        assert result.returncode == 0, result.stderr

    def test_poll_wrapper_generated_chinese_readme_gcc_direct_commands_run(self):
        with render_cpp_poll_artifacts(_README_MULTI_EVENT_DSL) as artifacts:
            readme = _read(artifacts["readme_zh_file"])
            source = _extract_cpp_code_block(readme, "C++ Poll Wrapper 快速开始")
            commands = _extract_named_bash_block(
                readme,
                "先把 C poll core 按 C99 编译",
            )
            result = run_readme_command_block(
                artifacts,
                "cpp_poll_readme_gcc_direct_zh",
                source,
                commands,
            )
        assert result.returncode == 0, result.stderr

    def test_poll_wrapper_generated_english_readme_clang_direct_commands_run(self):
        with render_cpp_poll_artifacts(_README_MULTI_EVENT_DSL) as artifacts:
            readme = _read(artifacts["readme_file"])
            source = _extract_cpp_code_block(readme, "C++ Poll Wrapper Quick Start")
            commands = _extract_named_bash_block(
                readme,
                "The equivalent Clang / Clang++ form is:",
            )
            result = run_readme_command_block(
                artifacts,
                "cpp_poll_readme_clang_direct_en",
                source,
                commands,
            )
        assert result.returncode == 0, result.stderr

    def test_poll_wrapper_generated_chinese_readme_clang_direct_commands_run(self):
        with render_cpp_poll_artifacts(_README_MULTI_EVENT_DSL) as artifacts:
            readme = _read(artifacts["readme_zh_file"])
            source = _extract_cpp_code_block(readme, "C++ Poll Wrapper 快速开始")
            commands = _extract_named_bash_block(
                readme,
                "等价的 Clang / Clang++ 写法是：",
            )
            result = run_readme_command_block(
                artifacts,
                "cpp_poll_readme_clang_direct_zh",
                source,
                commands,
            )
        assert result.returncode == 0, result.stderr

    def test_poll_wrapper_no_heap_profile_compiles_and_runs(self):
        with render_cpp_poll_artifacts(_WRAPPER_DSL) as artifacts:
            result = compile_and_run_cpp_poll_wrapper_harness(
                artifacts,
                "cpp_poll_wrapper_no_heap",
                _harness_source(),
                compile_definitions=["PYFCSTM_GENERATED_NO_HEAP"],
            )
        assert result.returncode == 0, result.stderr

    def test_poll_wrapper_compiles_with_gnu_no_exception_rtti_flags_when_available(
        self,
    ):
        c_compiler, cxx_compiler = available_compiler_pair("gcc", "g++")
        with render_cpp_poll_artifacts(_WRAPPER_DSL) as artifacts:
            result = compile_and_run_cpp_poll_wrapper_harness(
                artifacts,
                "cpp_poll_wrapper_gnu_no_exception_rtti",
                _harness_source(),
                c_compiler=c_compiler,
                cxx_compiler=cxx_compiler,
                cxx_compile_options=["-fno-exceptions", "-fno-rtti"],
            )
        assert result.returncode == 0, result.stderr

    def test_poll_wrapper_compiles_with_clang_when_available(self):
        c_compiler, cxx_compiler = available_compiler_pair("clang", "clang++")
        with render_cpp_poll_artifacts(_WRAPPER_DSL) as artifacts:
            result = compile_and_run_cpp_poll_wrapper_harness(
                artifacts,
                "cpp_poll_wrapper_clang",
                _harness_source(),
                c_compiler=c_compiler,
                cxx_compiler=cxx_compiler,
                cxx_compile_options=["-fno-exceptions", "-fno-rtti"],
            )
        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize("tool_name", ["cl", "clang-cl"])
    def test_poll_wrapper_has_minimal_msvc_like_compile_gate_when_available(
        self, tool_name
    ):
        with render_cpp_poll_artifacts(_WRAPPER_DSL) as artifacts:
            compile_with_msvc_like_tool(
                artifacts,
                "cpp_poll_wrapper_" + tool_name.replace("-", "_"),
                _compile_probe_source(),
                tool_name,
            )
