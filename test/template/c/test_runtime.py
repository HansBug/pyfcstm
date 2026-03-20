import os.path
import shutil
import subprocess

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
            assert '| DSL action path | Hook field | Owner state | Stage |' in readme
            assert 'read-only extension points' in readme
            assert 'do not mutate persistent' in readme
            assert 'RootMachine_vars_mut(&machine)->name' in readme
            assert '可注册的 Abstract Hook 清单' in readme_zh
            assert 'on_Root_RootInit' in readme_zh
            assert 'on_Root_System_A_AEnter' in readme_zh
            assert '只读扩展点' in readme_zh
            assert '不应在回调内部修改状态机持久变量' in readme_zh
            assert 'RootMachine_vars_mut(&machine)->name' in readme_zh

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

            if artifacts['compiler'] is not None and os.name != 'nt':
                subprocess.run(
                    [
                        artifacts['compiler'],
                        '-std=c99',
                        '-Wall',
                        '-Wextra',
                        '-pedantic',
                        '-c',
                        artifacts['machine_c_file'],
                        '-o',
                        os.path.join(artifacts['output_dir'], 'machine.o'),
                    ],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )

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
