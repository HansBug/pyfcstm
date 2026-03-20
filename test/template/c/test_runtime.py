import os.path
import shutil
import subprocess
import textwrap

import pytest

from ._utils import render_c_artifacts, render_c_runtime


@pytest.mark.unittest
class TestCBuiltinTemplate:
    def test_generated_machine_runs_cycle_and_event_transition(self):
        dsl_code = """
        def int counter = 0;
        state System {
            state Idle {
                during { counter = counter + 1; }
            }
            state Running {
                during { counter = counter + 100; }
            }
            [*] -> Idle;
            Idle -> Running :: Start effect { counter = counter + 10; };
        }
        """

        with render_c_runtime(dsl_code) as (runtime, _):
            assert runtime.current_state_path == ('System',)
            assert runtime.vars == {'counter': 0}

            runtime.cycle()
            assert runtime.current_state_path == ('System', 'Idle')
            assert runtime.vars == {'counter': 1}

            runtime.cycle(['Start'])
            assert runtime.current_state_path == ('System', 'Running')
            assert runtime.vars == {'counter': 111}

    def test_generated_machine_supports_hot_start_and_hook_registration(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            enter abstract RootInit;
            state System {
                state A {
                    enter abstract AEnter;
                    during { counter = counter + 1; }
                }
                [*] -> A;
            }
            [*] -> System;
        }
        """

        with render_c_runtime(dsl_code) as (runtime, _):
            hot_calls = []

            runtime.install_hooks({
                'on_Root_System_A_AEnter': lambda ctx: hot_calls.append(
                    ('hot', ctx.get_full_state_path(), ctx.action_stage, ctx.get_var('counter'))
                ),
            })
            runtime.hot_start('Root.System', {'counter': 10})
            assert runtime.current_state_path == ('Root', 'System')

            runtime.cycle()
            assert runtime.current_state_path == ('Root', 'System', 'A')
            assert runtime.vars == {'counter': 11}
            assert hot_calls == [('hot', 'Root.System.A', 'enter', 10)]

        with render_c_runtime(dsl_code) as (runtime, _):
            cold_calls = []

            runtime.install_hooks({
                'on_Root_RootInit': lambda ctx: cold_calls.append(
                    ('cold', ctx.get_full_state_path(), ctx.action_stage, ctx.get_var('counter'))
                ),
            })
            runtime.cycle()

            assert runtime.current_state_path == ('Root', 'System', 'A')
            assert runtime.vars == {'counter': 1}
            assert cold_calls == [('cold', 'Root', 'enter', 0)]

    def test_generated_machine_exposes_read_only_hook_context(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            enter abstract RootInit;
            state System {
                state A {
                    enter abstract AEnter;
                    during { counter = counter + 2; }
                }
                [*] -> A;
            }
            [*] -> System;
        }
        """

        with render_c_runtime(dsl_code) as (runtime, _):
            calls = []

            def root_hook(ctx):
                calls.append(('root', ctx.get_full_state_path(), ctx.action_stage, ctx.get_var('counter')))

            def a_enter_hook(ctx):
                calls.append(('a_enter', ctx.get_full_state_path(), ctx.action_stage, ctx.get_var('counter')))

            runtime.install_hooks({
                'on_Root_RootInit': root_hook,
                'on_Root_System_A_AEnter': a_enter_hook,
            })
            runtime.cycle()

            assert runtime.current_state_path == ('Root', 'System', 'A')
            assert runtime.vars == {'counter': 2}
            assert calls == [
                ('root', 'Root', 'enter', 0),
                ('a_enter', 'Root.System.A', 'enter', 0),
            ]
            assert runtime.get_abstract_hook_map() == {
                'Root.RootInit': 'on_Root_RootInit',
                'Root.System.A.AEnter': 'on_Root_System_A_AEnter',
            }

    def test_generated_machine_c_hooks_install_and_fire_with_user_data(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            enter abstract RootInit;
            state System {
                state A {
                    enter abstract AEnter;
                    during { counter = counter + 2; }
                }
                [*] -> A;
            }
            [*] -> System;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            run = _compile_and_run_c_harness(
                artifacts,
                'hook_mount_test',
                textwrap.dedent(
                    r'''
                    #include "machine.h"
                    #include <stdio.h>
                    #include <string.h>

                    typedef struct HookLog {
                        int count;
                        int root_seen;
                        int a_seen;
                        long long root_counter;
                        long long a_counter;
                    } HookLog;

                    static void root_hook(
                        RootMachine *machine,
                        const RootMachineExecutionContext *ctx,
                        void *user_data
                    )
                    {
                        HookLog *log = (HookLog *)user_data;
                        (void)machine;
                        log->count += 1;
                        if (
                            strcmp(ctx->action_name, "Root.RootInit") == 0 &&
                            strcmp(ctx->state_path, "Root") == 0 &&
                            strcmp(ctx->action_stage, "enter") == 0
                        ) {
                            log->root_seen = 1;
                            log->root_counter = ctx->vars->counter;
                        }
                    }

                    static void a_enter_hook(
                        RootMachine *machine,
                        const RootMachineExecutionContext *ctx,
                        void *user_data
                    )
                    {
                        HookLog *log = (HookLog *)user_data;
                        (void)machine;
                        log->count += 1;
                        if (
                            strcmp(ctx->action_name, "Root.System.A.AEnter") == 0 &&
                            strcmp(ctx->state_path, "Root.System.A") == 0 &&
                            strcmp(ctx->action_stage, "enter") == 0
                        ) {
                            log->a_seen = 1;
                            log->a_counter = ctx->vars->counter;
                        }
                    }

                    int main(void)
                    {
                        RootMachine machine;
                        RootMachineHooks hooks = ROOTMACHINE_HOOKS_INIT;
                        HookLog log = {0};

                        if (!RootMachine_init(&machine)) {
                            return 10;
                        }

                        hooks.on_Root_RootInit = root_hook;
                        hooks.on_Root_System_A_AEnter = a_enter_hook;
                        RootMachine_set_hooks(&machine, &hooks, &log);

                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 11;
                        }
                        if (log.count != 2 || !log.root_seen || !log.a_seen) {
                            return 12;
                        }
                        if (log.root_counter != 0 || log.a_counter != 0) {
                            return 13;
                        }
                        if (strcmp(RootMachine_current_state_path(&machine), "Root.System.A") != 0) {
                            return 14;
                        }
                        if (RootMachine_vars(&machine)->counter != 2) {
                            return 15;
                        }

                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 16;
                        }
                        if (log.count != 2) {
                            return 17;
                        }
                        if (RootMachine_vars(&machine)->counter != 4) {
                            return 18;
                        }

                        return 0;
                    }
                    '''
                ),
            )
            assert run.returncode == 0, run.stderr

    def test_generated_machine_c_hooks_follow_ref_reuse_behavior(self):
        dsl_code = """
        def int trace = 0;
        state Root {
            enter abstract PlatformInit;

            state A {
                enter ref /PlatformInit;
                during { trace = trace + 1; }
            }

            state B {
                enter ref /PlatformInit;
                during { trace = trace + 10; }
            }

            [*] -> A;
            A -> B :: Go;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            run = _compile_and_run_c_harness(
                artifacts,
                'hook_ref_reuse_test',
                textwrap.dedent(
                    r'''
                    #include "machine.h"
                    #include <stdio.h>
                    #include <string.h>

                    typedef struct HookLog {
                        int total_calls;
                        int root_calls;
                    } HookLog;

                    static void platform_hook(
                        RootMachine *machine,
                        const RootMachineExecutionContext *ctx,
                        void *user_data
                    )
                    {
                        HookLog *log = (HookLog *)user_data;
                        (void)machine;

                        if (strcmp(ctx->action_name, "Root.PlatformInit") != 0) {
                            log->total_calls = -100;
                            return;
                        }

                        log->total_calls += 1;
                        if (strcmp(ctx->state_path, "Root") == 0) {
                            log->root_calls += 1;
                        }
                    }

                    int main(void)
                    {
                        RootMachine machine;
                        RootMachineHooks hooks = ROOTMACHINE_HOOKS_INIT;
                        HookLog log = {0};
                        static const RootMachineEventId go_events[] = {
                            ROOT_MACHINE_EVENT_ROOT_A_GO
                        };

                        if (!RootMachine_init(&machine)) {
                            return 20;
                        }

                        hooks.on_Root_PlatformInit = platform_hook;
                        RootMachine_set_hooks(&machine, &hooks, &log);

                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 21;
                        }
                        if (log.total_calls != 2 || log.root_calls != 2) {
                            return 22;
                        }
                        if (RootMachine_vars(&machine)->trace != 1) {
                            return 23;
                        }

                        if (!RootMachine_cycle(&machine, go_events, 1u)) {
                            return 24;
                        }
                        if (log.total_calls != 3 || log.root_calls != 3) {
                            return 25;
                        }
                        if (RootMachine_vars(&machine)->trace != 11) {
                            return 26;
                        }
                        if (strcmp(RootMachine_current_state_path(&machine), "Root.B") != 0) {
                            return 27;
                        }

                        return 0;
                    }
                    '''
                ),
            )
            assert run.returncode == 0, run.stderr

    def test_generated_machine_reuses_same_hook_for_abstract_refs(self):
        dsl_code = """
        def int trace = 0;
        state Root {
            enter abstract PlatformInit;

            state A {
                enter ref /PlatformInit;
                during { trace = trace + 1; }
            }

            state B {
                enter ref /PlatformInit;
                during { trace = trace + 10; }
            }

            [*] -> A;
            A -> B :: Go;
        }
        """

        with render_c_runtime(dsl_code) as (runtime, _):
            calls = []

            def platform_init(ctx):
                calls.append((ctx.action_name, ctx.action_stage, ctx.get_full_state_path()))

            runtime.install_hooks({'on_Root_PlatformInit': platform_init})
            runtime.cycle()
            assert runtime.current_state_path == ('Root', 'A')
            assert runtime.vars == {'trace': 1}

            runtime.cycle(['Root.A.Go'])
            assert runtime.current_state_path == ('Root', 'B')
            assert runtime.vars == {'trace': 11}

            assert runtime.get_abstract_hook_map() == {
                'Root.PlatformInit': 'on_Root_PlatformInit',
            }
            assert calls == [
                ('Root.PlatformInit', 'enter', 'Root'),
                ('Root.PlatformInit', 'enter', 'Root'),
                ('Root.PlatformInit', 'enter', 'Root'),
            ]

    def test_generated_readme_documents_usage_and_abstract_hooks(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            enter abstract RootInit;
            state System {
                state A {
                    enter abstract AEnter;
                    during { counter = counter + 1; }
                }
                [*] -> A;
            }
            [*] -> System;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            with open(artifacts['readme_file'], 'r', encoding='utf-8') as f:
                readme = f.read()
            with open(artifacts['readme_zh_file'], 'r', encoding='utf-8') as f:
                readme_zh = f.read()

            assert os.path.isfile(artifacts['readme_file'])
            assert os.path.isfile(artifacts['readme_zh_file'])
            assert '# RootMachine' in readme
            assert 'RootMachineHooks' in readme
            assert 'on_Root_RootInit' in readme
            assert 'on_Root_System_A_AEnter' in readme
            assert '| Hook field | DSL action path | Owner state | Stage |' in readme
            assert '## Public Header Reference' in readme
            assert '## Function Reference' in readme
            assert '## Performance Advice' in readme
            assert 'C++98' in readme
            assert 'RootMachineInt' in readme
            assert 'g++ -x c++ -std=c++98' in readme
            assert 'read-only extension points' in readme
            assert 'should not mutate persistent machine variables' in readme
            assert 'RootMachine_vars(&machine)' in readme
            assert '| Hook 字段 | DSL 动作路径 | 所属状态 | 阶段 |' in readme_zh
            assert 'on_Root_RootInit' in readme_zh
            assert 'on_Root_System_A_AEnter' in readme_zh
            assert '## 公开头文件参考' in readme_zh
            assert '## 函数参考' in readme_zh
            assert '## 性能建议' in readme_zh
            assert 'C++98' in readme_zh
            assert 'RootMachineInt' in readme_zh
            assert 'g++ -x c++ -std=c++98' in readme_zh
            assert '只读扩展点' in readme_zh
            assert '不适合修改状态机持久变量' in readme_zh
            assert 'RootMachine_vars(&machine)' in readme_zh

    def test_generated_machine_source_is_c99_and_build_files_work(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            state Idle {
                during { counter = counter + 1; }
            }
            [*] -> Idle;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            with open(artifacts['machine_h_file'], 'r', encoding='utf-8') as f:
                header = f.read()
            with open(artifacts['machine_c_file'], 'r', encoding='utf-8') as f:
                source = f.read()

            assert '#include <stddef.h>' in header
            assert '#include <math.h>' in source
            assert 'windows.h' not in source
            assert 'pthread.h' not in source
            assert 'fork(' not in source

            assert os.path.isfile(artifacts['shared_lib'])
            assert os.path.isfile(artifacts['build_files']['cmakelists'])

            make_executable = shutil.which('make')
            if make_executable is not None and os.name != 'nt':
                subprocess.run(
                    [make_executable],
                    cwd=artifacts['output_dir'],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                assert os.path.isfile(os.path.join(artifacts['output_dir'], 'libmachine.a'))
                assert os.path.isfile(artifacts['build_files']['makefile'])

            if artifacts['cmake'] is not None:
                built_entries = set(os.listdir(artifacts['build_dir']))
                assert 'CMakeCache.txt' in built_entries

    def test_generated_machine_rolls_back_transition_effects_on_validation_failure(self):
        dsl_code = """
        def int counter = 0;
        def int ready = 0;
        state Root {
            state A {
                during { counter = counter + 1; }
            }

            state B {
                state B1 {
                    during { counter = counter + 100; }
                }
                [*] -> B1 : if [ready == 1];
            }

            [*] -> A;
            A -> B :: Go effect { counter = counter + 1000; };
        }
        """

        with render_c_runtime(dsl_code) as (runtime, _):
            runtime.cycle()
            assert runtime.current_state_path == ('Root', 'A')
            assert runtime.vars == {'counter': 1, 'ready': 0}

            runtime.cycle(['Root.A.Go'])
            assert runtime.current_state_path == ('Root', 'A')
            assert runtime.vars == {'counter': 2, 'ready': 0}

    def test_generated_machine_does_not_fire_hooks_for_rejected_transition(self):
        dsl_code = """
        def int counter = 0;
        def int ready = 0;
        state Root {
            state A {
                during { counter = counter + 1; }
            }

            state B {
                state B1 {
                    enter abstract B1Enter;
                    during { counter = counter + 100; }
                }
                [*] -> B1 : if [ready == 1];
            }

            [*] -> A;
            A -> B :: Go effect { counter = counter + 1000; };
        }
        """

        with render_c_runtime(dsl_code) as (runtime, _):
            calls = []
            runtime.install_hooks({
                'on_Root_B_B1_B1Enter': lambda ctx: calls.append(
                    (ctx.get_full_state_path(), ctx.action_stage, ctx.get_var('counter'))
                ),
            })

            runtime.cycle()
            assert runtime.current_state_path == ('Root', 'A')
            assert runtime.vars == {'counter': 1, 'ready': 0}

            runtime.cycle(['Root.A.Go'])
            assert runtime.current_state_path == ('Root', 'A')
            assert runtime.vars == {'counter': 2, 'ready': 0}
            assert calls == []

    def test_generated_machine_cpp98_runs_basic_cycle_and_transition(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            state Idle {
                during { counter = counter + 1; }
            }
            state Running {
                during { counter = counter + 100; }
            }
            [*] -> Idle;
            Idle -> Running :: Start effect { counter = counter + 10; };
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            run = _compile_and_run_cpp_harness(
                artifacts,
                'cpp98_basic_cycle',
                textwrap.dedent(
                    r'''
                    #include "machine.h"
                    #include <string.h>

                    int main(void)
                    {
                        RootMachine machine;
                        static const RootMachineEventId start_events[] = {
                            ROOT_MACHINE_EVENT_ROOT_IDLE_START
                        };

                        if (!RootMachine_init(&machine)) {
                            return 10;
                        }
                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 11;
                        }
                        if (strcmp(RootMachine_current_state_path(&machine), "Root.Idle") != 0) {
                            return 12;
                        }
                        if (RootMachine_vars(&machine)->counter != (RootMachineInt)1) {
                            return 13;
                        }

                        if (!RootMachine_cycle(&machine, start_events, 1u)) {
                            return 14;
                        }
                        if (strcmp(RootMachine_current_state_path(&machine), "Root.Running") != 0) {
                            return 15;
                        }
                        if (RootMachine_vars(&machine)->counter != (RootMachineInt)111) {
                            return 16;
                        }

                        return 0;
                    }
                    '''
                ),
            )
            assert run.returncode == 0, run.stderr

    def test_generated_machine_cpp98_supports_hot_start(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            state Service {
                state Ready {
                    during { counter = counter + 3; }
                }
                [*] -> Ready;
            }
            [*] -> Service;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            run = _compile_and_run_cpp_harness(
                artifacts,
                'cpp98_hot_start',
                textwrap.dedent(
                    r'''
                    #include "machine.h"
                    #include <string.h>

                    int main(void)
                    {
                        RootMachine machine;
                        RootMachineVars initial_vars;

                        if (!RootMachine_init(&machine)) {
                            return 20;
                        }

                        initial_vars.counter = (RootMachineInt)40;
                        if (!RootMachine_hot_start(
                            &machine,
                            ROOT_MACHINE_STATE_ROOT_SERVICE,
                            &initial_vars
                        )) {
                            return 21;
                        }
                        if (strcmp(RootMachine_current_state_path(&machine), "Root.Service") != 0) {
                            return 22;
                        }

                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 23;
                        }
                        if (strcmp(RootMachine_current_state_path(&machine), "Root.Service.Ready") != 0) {
                            return 24;
                        }
                        if (RootMachine_vars(&machine)->counter != (RootMachineInt)43) {
                            return 25;
                        }

                        return 0;
                    }
                    '''
                ),
            )
            assert run.returncode == 0, run.stderr

    def test_generated_machine_cpp98_hooks_install_and_fire_with_user_data(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            enter abstract RootInit;
            state System {
                state A {
                    enter abstract AEnter;
                    during { counter = counter + 2; }
                }
                [*] -> A;
            }
            [*] -> System;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            run = _compile_and_run_cpp_harness(
                artifacts,
                'cpp98_hook_mount',
                textwrap.dedent(
                    r'''
                    #include "machine.h"
                    #include <string.h>

                    typedef struct HookLog {
                        int count;
                        int root_seen;
                        int a_seen;
                        RootMachineInt root_counter;
                        RootMachineInt a_counter;
                    } HookLog;

                    static void root_hook(
                        RootMachine *machine,
                        const RootMachineExecutionContext *ctx,
                        void *user_data
                    )
                    {
                        HookLog *log = (HookLog *)user_data;
                        (void)machine;
                        log->count += 1;
                        if (
                            strcmp(ctx->action_name, "Root.RootInit") == 0 &&
                            strcmp(ctx->state_path, "Root") == 0 &&
                            strcmp(ctx->action_stage, "enter") == 0
                        ) {
                            log->root_seen = 1;
                            log->root_counter = ctx->vars->counter;
                        }
                    }

                    static void a_enter_hook(
                        RootMachine *machine,
                        const RootMachineExecutionContext *ctx,
                        void *user_data
                    )
                    {
                        HookLog *log = (HookLog *)user_data;
                        (void)machine;
                        log->count += 1;
                        if (
                            strcmp(ctx->action_name, "Root.System.A.AEnter") == 0 &&
                            strcmp(ctx->state_path, "Root.System.A") == 0 &&
                            strcmp(ctx->action_stage, "enter") == 0
                        ) {
                            log->a_seen = 1;
                            log->a_counter = ctx->vars->counter;
                        }
                    }

                    int main(void)
                    {
                        RootMachine machine;
                        RootMachineHooks hooks = ROOTMACHINE_HOOKS_INIT;
                        HookLog log = {0, 0, 0, 0, 0};

                        if (!RootMachine_init(&machine)) {
                            return 30;
                        }

                        hooks.on_Root_RootInit = root_hook;
                        hooks.on_Root_System_A_AEnter = a_enter_hook;
                        RootMachine_set_hooks(&machine, &hooks, &log);

                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 31;
                        }
                        if (log.count != 2 || !log.root_seen || !log.a_seen) {
                            return 32;
                        }
                        if (log.root_counter != 0 || log.a_counter != 0) {
                            return 33;
                        }
                        if (RootMachine_vars(&machine)->counter != (RootMachineInt)2) {
                            return 34;
                        }

                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 35;
                        }
                        if (log.count != 2) {
                            return 36;
                        }

                        return 0;
                    }
                    '''
                ),
            )
            assert run.returncode == 0, run.stderr

    def test_generated_machine_cpp98_hooks_follow_ref_reuse_behavior(self):
        dsl_code = """
        def int trace = 0;
        state Root {
            enter abstract PlatformInit;

            state A {
                enter ref /PlatformInit;
                during { trace = trace + 1; }
            }

            state B {
                enter ref /PlatformInit;
                during { trace = trace + 10; }
            }

            [*] -> A;
            A -> B :: Go;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            run = _compile_and_run_cpp_harness(
                artifacts,
                'cpp98_hook_ref_reuse',
                textwrap.dedent(
                    r'''
                    #include "machine.h"
                    #include <string.h>

                    typedef struct HookLog {
                        int total_calls;
                        int root_calls;
                    } HookLog;

                    static void platform_hook(
                        RootMachine *machine,
                        const RootMachineExecutionContext *ctx,
                        void *user_data
                    )
                    {
                        HookLog *log = (HookLog *)user_data;
                        (void)machine;

                        if (strcmp(ctx->action_name, "Root.PlatformInit") != 0) {
                            log->total_calls = -100;
                            return;
                        }

                        log->total_calls += 1;
                        if (strcmp(ctx->state_path, "Root") == 0) {
                            log->root_calls += 1;
                        }
                    }

                    int main(void)
                    {
                        RootMachine machine;
                        RootMachineHooks hooks = ROOTMACHINE_HOOKS_INIT;
                        HookLog log = {0, 0};
                        static const RootMachineEventId go_events[] = {
                            ROOT_MACHINE_EVENT_ROOT_A_GO
                        };

                        if (!RootMachine_init(&machine)) {
                            return 40;
                        }

                        hooks.on_Root_PlatformInit = platform_hook;
                        RootMachine_set_hooks(&machine, &hooks, &log);

                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 41;
                        }
                        if (log.total_calls != 2 || log.root_calls != 2) {
                            return 42;
                        }
                        if (RootMachine_vars(&machine)->trace != (RootMachineInt)1) {
                            return 43;
                        }

                        if (!RootMachine_cycle(&machine, go_events, 1u)) {
                            return 44;
                        }
                        if (log.total_calls != 3 || log.root_calls != 3) {
                            return 45;
                        }
                        if (RootMachine_vars(&machine)->trace != (RootMachineInt)11) {
                            return 46;
                        }
                        if (strcmp(RootMachine_current_state_path(&machine), "Root.B") != 0) {
                            return 47;
                        }

                        return 0;
                    }
                    '''
                ),
            )
            assert run.returncode == 0, run.stderr

    def test_generated_machine_cpp98_rolls_back_transition_effects(self):
        dsl_code = """
        def int counter = 0;
        def int ready = 0;
        state Root {
            state A {
                during { counter = counter + 1; }
            }

            state B {
                state B1 {
                    enter abstract B1Enter;
                    during { counter = counter + 100; }
                }
                [*] -> B1 : if [ready == 1];
            }

            [*] -> A;
            A -> B :: Go effect { counter = counter + 1000; };
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            run = _compile_and_run_cpp_harness(
                artifacts,
                'cpp98_validation_rollback',
                textwrap.dedent(
                    r'''
                    #include "machine.h"
                    #include <string.h>

                    typedef struct HookLog {
                        int b1_enter_count;
                    } HookLog;

                    static void b1_enter_hook(
                        RootMachine *machine,
                        const RootMachineExecutionContext *ctx,
                        void *user_data
                    )
                    {
                        HookLog *log = (HookLog *)user_data;
                        (void)machine;
                        if (
                            strcmp(ctx->action_name, "Root.B.B1.B1Enter") == 0 &&
                            strcmp(ctx->state_path, "Root.B.B1") == 0
                        ) {
                            log->b1_enter_count += 1;
                        }
                    }

                    int main(void)
                    {
                        RootMachine machine;
                        RootMachineHooks hooks = ROOTMACHINE_HOOKS_INIT;
                        HookLog log = {0};
                        static const RootMachineEventId go_events[] = {
                            ROOT_MACHINE_EVENT_ROOT_A_GO
                        };

                        if (!RootMachine_init(&machine)) {
                            return 50;
                        }

                        hooks.on_Root_B_B1_B1Enter = b1_enter_hook;
                        RootMachine_set_hooks(&machine, &hooks, &log);

                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 51;
                        }
                        if (strcmp(RootMachine_current_state_path(&machine), "Root.A") != 0) {
                            return 52;
                        }
                        if (RootMachine_vars(&machine)->counter != (RootMachineInt)1) {
                            return 53;
                        }

                        if (!RootMachine_cycle(&machine, go_events, 1u)) {
                            return 54;
                        }
                        if (strcmp(RootMachine_current_state_path(&machine), "Root.A") != 0) {
                            return 55;
                        }
                        if (RootMachine_vars(&machine)->counter != (RootMachineInt)2) {
                            return 56;
                        }
                        if (log.b1_enter_count != 0) {
                            return 57;
                        }

                        return 0;
                    }
                    '''
                ),
            )
            assert run.returncode == 0, run.stderr

    def test_generated_machine_cpp98_supports_cxx_keyword_safe_identifiers(self):
        dsl_code = """
        def int class = 0;
        def int template = 0;
        state Root {
            state namespace_ {
                during {
                    class = class + 1;
                    template = template + 2;
                }
            }
            [*] -> namespace_;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            run = _compile_and_run_cpp_harness(
                artifacts,
                'cpp98_keyword_safe_identifiers',
                textwrap.dedent(
                    r'''
                    #include "machine.h"
                    #include <string.h>

                    int main(void)
                    {
                        RootMachine machine;

                        if (!RootMachine_init(&machine)) {
                            return 60;
                        }
                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 61;
                        }
                        if (strcmp(RootMachine_current_state_path(&machine), "Root.namespace_") != 0) {
                            return 62;
                        }
                        if (RootMachine_vars(&machine)->class_ != (RootMachineInt)1) {
                            return 63;
                        }
                        if (RootMachine_vars(&machine)->template_ != (RootMachineInt)2) {
                            return 64;
                        }

                        return 0;
                    }
                    '''
                ),
            )
            assert run.returncode == 0, run.stderr


def _assert_runtime_state(runtime, current_path=None, vars=None, is_ended=False):
    assert runtime.is_ended is is_ended
    if current_path is None:
        assert runtime.current_state_path is None
    else:
        assert runtime.current_state_path == current_path
    if vars is not None:
        assert runtime.vars == vars


def _run_cycle_and_assert(runtime, events=None, *, current_path=None, vars=None, is_ended=False):
    runtime.cycle(events)
    _assert_runtime_state(runtime, current_path=current_path, vars=vars, is_ended=is_ended)


def _cmake_generator_args():
    if os.name == 'nt':
        return ['-G', 'MinGW Makefiles']
    return []


def _find_built_executable(build_dir, stem):
    candidate_names = [stem + '.exe', stem]
    search_dirs = [
        build_dir,
        os.path.join(build_dir, 'Release'),
        os.path.join(build_dir, 'RelWithDebInfo'),
        os.path.join(build_dir, 'Debug'),
        os.path.join(build_dir, 'MinSizeRel'),
    ]

    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        for filename in candidate_names:
            path = os.path.join(directory, filename)
            if os.path.isfile(path):
                return path

    for root, _, files in os.walk(build_dir):
        for filename in files:
            if filename in candidate_names:
                return os.path.join(root, filename)

    raise FileNotFoundError(
        'Cannot find built executable {!r} under {!r}.'.format(stem, build_dir)
    )


def _compile_and_run_harness_with_cmake(artifacts, stem, source_code, *, language, standard):
    cmake_executable = artifacts['cmake']
    if cmake_executable is None:
        pytest.skip('cmake is required for generated C template harness tests.')

    source_ext = '.cpp' if language == 'CXX' else '.c'
    project_dir = os.path.join(artifacts['output_dir'], stem + '_cmake_project')
    build_dir = os.path.join(project_dir, 'build')
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(build_dir, exist_ok=True)

    source_file = os.path.join(project_dir, stem + source_ext)
    cmakelists = os.path.join(project_dir, 'CMakeLists.txt')
    with open(source_file, 'w', encoding='utf-8') as f:
        f.write(source_code)
    with open(cmakelists, 'w', encoding='utf-8') as f:
        cmake_lines = [
            'cmake_minimum_required(VERSION 3.5)',
            'project({project_name} {project_languages})'.format(
                project_name=stem + '_project',
                project_languages='C CXX' if language == 'CXX' else 'C',
            ),
            '',
            'include_directories("{machine_dir}")'.format(
                machine_dir=artifacts['output_dir'].replace('\\', '/')
            ),
            '',
            'add_executable({target_name}'.format(target_name=stem),
            '    "{machine_c_file}"'.format(
                machine_c_file=artifacts['machine_c_file'].replace('\\', '/')
            ),
            '    "{source_file}"'.format(source_file=source_file.replace('\\', '/')),
            ')',
            '',
            'set_target_properties(',
            '    {target_name}'.format(target_name=stem),
            '    PROPERTIES',
            '    C_STANDARD 99',
            '    C_STANDARD_REQUIRED YES',
            '    C_EXTENSIONS NO',
        ]
        if language == 'CXX':
            cmake_lines.extend([
                '    CXX_STANDARD {cxx_standard}'.format(
                    cxx_standard=standard.replace('c++', '')
                ),
                '    CXX_STANDARD_REQUIRED YES',
                '    CXX_EXTENSIONS NO',
            ])
        cmake_lines.extend([
            ')',
            '',
            'if (NOT WIN32)',
            '    target_link_libraries({target_name} m)'.format(target_name=stem),
            'endif()',
            '',
        ])
        f.write('\n'.join(cmake_lines))

    subprocess.run(
        [cmake_executable]
        + _cmake_generator_args()
        + [
            '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
            os.path.abspath(project_dir),
        ],
        cwd=build_dir,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    subprocess.run(
        [cmake_executable, '--build', '.', '--config', 'Release'],
        cwd=build_dir,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    return subprocess.run(
        [_find_built_executable(build_dir, stem)],
        cwd=build_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _compile_and_run_c_harness(artifacts, stem, source_code):
    return _compile_and_run_harness_with_cmake(
        artifacts,
        stem,
        source_code,
        language='C',
        standard='c++98',
    )


def _compile_and_run_cpp_harness(artifacts, stem, source_code, std='c++98'):
    return _compile_and_run_harness_with_cmake(
        artifacts,
        stem,
        source_code,
        language='CXX',
        standard=std,
    )
