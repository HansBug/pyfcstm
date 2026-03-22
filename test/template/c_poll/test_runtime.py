import os.path
import re
import shutil
import subprocess
import textwrap

import pytest

from ._utils import render_c_artifacts, render_c_runtime

_CLANG_FORMAT_STYLE = '{BasedOnStyle: LLVM, IndentWidth: 4, ContinuationIndentWidth: 4}'


def _format_c_text(text, filename):
    clang_format = shutil.which('clang-format')
    if clang_format is None:
        pytest.skip('clang-format is required for c_poll formatter convergence tests.')

    return subprocess.run(
        [
            clang_format,
            '-style=' + _CLANG_FORMAT_STYLE,
            '--assume-filename=' + filename,
        ],
        input=text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    ).stdout


@pytest.mark.unittest
class TestCPollBuiltinTemplate:
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

    def test_generated_machine_requires_event_checks_before_cycle(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            state A {
                during { counter = counter + 1; }
            }
            state B;
            [*] -> A;
            A -> B :: Go;
        }
        """

        with render_c_runtime(dsl_code, auto_install_event_checks=False) as (runtime, _):
            with pytest.raises(RuntimeError, match='Event checks are not mounted'):
                runtime.cycle()

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

    def test_generated_machine_exposes_read_only_event_check_context(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            state A {
                during { counter = counter + 1; }
            }
            state B;
            [*] -> A;
            A -> B :: Go;
        }
        """

        with render_c_runtime(dsl_code, auto_install_event_checks=False) as (runtime, _):
            calls = []

            runtime.install_event_checks({
                'check_Root_A_Go': lambda ctx: calls.append(
                    (ctx.event_path, ctx.get_full_state_path(), ctx.get_var('counter'))
                ) or True,
            })

            runtime.cycle()
            assert runtime.current_state_path == ('Root', 'A')
            assert runtime.vars == {'counter': 1}
            assert calls == []

            runtime.cycle(['Root.A.Go'])
            assert runtime.current_state_path == ('Root', 'B')
            assert runtime.vars == {'counter': 1}
            assert calls == [('Root.A.Go', 'Root.A', 1)]

    def test_generated_machine_event_checks_and_hooks_coexist(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            enter abstract RootInit;
            state A {
                during { counter = counter + 1; }
            }
            state B {
                enter abstract BEnter;
            }
            [*] -> A;
            A -> B :: Go;
        }
        """

        with render_c_runtime(dsl_code, auto_install_event_checks=False) as (runtime, _):
            trace = []

            runtime.install_hooks({
                'on_Root_RootInit': lambda ctx: trace.append(('hook', ctx.action_name, ctx.get_var('counter'))),
                'on_Root_B_BEnter': lambda ctx: trace.append(('hook', ctx.action_name, ctx.get_var('counter'))),
            })
            runtime.install_event_checks({
                'check_Root_A_Go': lambda ctx: trace.append(('event', ctx.event_path, ctx.get_var('counter'))) or True,
            })

            runtime.cycle()
            assert runtime.current_state_path == ('Root', 'A')
            assert runtime.vars == {'counter': 1}

            runtime.cycle(['Root.A.Go'])
            assert runtime.current_state_path == ('Root', 'B')
            assert runtime.vars == {'counter': 1}
            assert trace == [
                ('hook', 'Root.RootInit', 0),
                ('event', 'Root.A.Go', 1),
                ('hook', 'Root.B.BEnter', 1),
            ]

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

    def test_generated_readme_documents_poll_event_checks(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            enter abstract RootInit;
            state A {
                during { counter = counter + 1; }
            }
            state B;
            [*] -> A;
            A -> B :: Go;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            with open(artifacts['readme_file'], 'r', encoding='utf-8') as f:
                readme = f.read()
            with open(artifacts['readme_zh_file'], 'r', encoding='utf-8') as f:
                readme_zh = f.read()

            assert 'EventChecks' in readme
            assert 'EventCheckFn' in readme
            assert '_set_event_checks(' in readme
            assert '_cycle(&machine)' in readme
            assert 'cycle(machine, event_ids, event_count)' not in readme
            assert 'fails fast' in readme
            assert 'check_Root_A_Go' in readme
            assert 'return non-zero' in readme
            assert 'return `0`' in readme

            assert 'EventChecks' in readme_zh
            assert 'EventCheckFn' in readme_zh
            assert '_set_event_checks(' in readme_zh
            assert '_cycle(&machine)' in readme_zh
            assert 'cycle(machine, event_ids, event_count)' not in readme_zh
            assert '直接失败' in readme_zh
            assert 'check_Root_A_Go' in readme_zh
            assert '返回非零' in readme_zh
            assert '返回 `0`' in readme_zh

    def test_generated_machine_clang_format_converges_under_four_space_style(self):
        dsl_code = """
        def int counter = 0;
        def int ready = 0;
        state Root {
            enter abstract RootInit;
            state A {
                during { counter = counter + 1; }
            }
            state B {
                enter abstract BEnter;
                state B1 {
                    during { counter = counter + 10; }
                }
                [*] -> B1 : if [ready == 1];
            }
            [*] -> A;
            A -> B :: Go effect { counter = counter + 100; };
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            for key in ['machine_h_file', 'machine_c_file']:
                path = artifacts[key]
                with open(path, 'r', encoding='utf-8') as f:
                    original = f.read()

                formatted_once = _format_c_text(original, os.path.basename(path))
                formatted_twice = _format_c_text(formatted_once, os.path.basename(path))

                assert formatted_once == formatted_twice
                assert '\t' not in formatted_once

    def test_generated_readme_code_blocks_are_formatter_friendly(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            state A {
                during { counter = counter + 1; }
            }
            state B;
            [*] -> A;
            A -> B :: Go;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            with open(artifacts['readme_file'], 'r', encoding='utf-8') as f:
                readme = f.read()
            with open(artifacts['readme_zh_file'], 'r', encoding='utf-8') as f:
                readme_zh = f.read()

            for content in [readme, readme_zh]:
                blocks = re.findall(r'```(?:c|cpp|bash)\n(.*?)```', content, flags=re.S)
                assert blocks
                for block in blocks:
                    assert '\t' not in block

            assert 'clang-format' in readme
            assert 'clang-format' in readme_zh

    def test_generated_machine_c_event_checks_install_and_drive_cycle(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            state A {
                during { counter = counter + 1; }
            }
            state B {
                during { counter = counter + 10; }
            }
            [*] -> A;
            A -> B :: Go;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            run = _compile_and_run_c_harness(
                artifacts,
                'event_check_mount_test',
                textwrap.dedent(
                    r'''
                    #include "machine.h"
                    #include <string.h>

                    typedef struct EventLog {
                        int allow_go;
                        int seen;
                    } EventLog;

                    static int check_go(
                        RootMachine *machine,
                        const RootMachineEventContext *ctx,
                        void *user_data
                    )
                    {
                        EventLog *log = (EventLog *)user_data;
                        (void)machine;
                        if (
                            strcmp(ctx->event_path, "Root.A.Go") == 0 &&
                            strcmp(ctx->current_state_path, "Root.A") == 0
                        ) {
                            log->seen += 1;
                        }
                        return log->allow_go;
                    }

                    int main(void)
                    {
                        RootMachine machine;
                        RootMachineEventChecks event_checks = ROOTMACHINE_EVENT_CHECKS_INIT;
                        EventLog log = {0};

                        if (!RootMachine_init(&machine)) {
                            return 10;
                        }
                        if (RootMachine_cycle(&machine)) {
                            return 11;
                        }

                        event_checks.check_Root_A_Go = check_go;
                        RootMachine_set_event_checks(&machine, &event_checks, &log);

                        if (!RootMachine_cycle(&machine)) {
                            return 12;
                        }
                        if (strcmp(RootMachine_current_state_path(&machine), "Root.A") != 0) {
                            return 13;
                        }
                        if (RootMachine_vars(&machine)->counter != 1) {
                            return 14;
                        }

                        log.allow_go = 1;
                        if (!RootMachine_cycle(&machine)) {
                            return 15;
                        }
                        if (strcmp(RootMachine_current_state_path(&machine), "Root.B") != 0) {
                            return 16;
                        }
                        if (RootMachine_vars(&machine)->counter != 11) {
                            return 17;
                        }
                        if (log.seen != 1) {
                            return 18;
                        }

                        return 0;
                    }
                    '''
                ),
            )
            assert run.returncode == 0, run.stderr

    def test_generated_machine_cpp98_event_checks_install_and_drive_cycle(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            state A {
                during { counter = counter + 1; }
            }
            state B {
                during { counter = counter + 10; }
            }
            [*] -> A;
            A -> B :: Go;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            run = _compile_and_run_cpp_harness(
                artifacts,
                'cpp98_event_check_mount',
                textwrap.dedent(
                    r'''
                    #include "machine.h"
                    #include <cstring>

                    struct EventLog {
                        int allow_go;
                        int seen;
                    };

                    static int check_go(
                        RootMachine *machine,
                        const RootMachineEventContext *ctx,
                        void *user_data
                    )
                    {
                        EventLog *log = static_cast<EventLog *>(user_data);
                        (void)machine;
                        if (
                            std::strcmp(ctx->event_path, "Root.A.Go") == 0 &&
                            std::strcmp(ctx->current_state_path, "Root.A") == 0
                        ) {
                            log->seen += 1;
                        }
                        return log->allow_go;
                    }

                    int main()
                    {
                        RootMachine machine;
                        RootMachineEventChecks event_checks = ROOTMACHINE_EVENT_CHECKS_INIT;
                        EventLog log = {0, 0};

                        if (!RootMachine_init(&machine)) {
                            return 20;
                        }
                        event_checks.check_Root_A_Go = check_go;
                        RootMachine_set_event_checks(&machine, &event_checks, &log);

                        if (!RootMachine_cycle(&machine)) {
                            return 21;
                        }
                        if (std::strcmp(RootMachine_current_state_path(&machine), "Root.A") != 0) {
                            return 22;
                        }
                        log.allow_go = 1;
                        if (!RootMachine_cycle(&machine)) {
                            return 23;
                        }
                        if (std::strcmp(RootMachine_current_state_path(&machine), "Root.B") != 0) {
                            return 24;
                        }
                        if (RootMachine_vars(&machine)->counter != 11) {
                            return 25;
                        }
                        if (log.seen != 1) {
                            return 26;
                        }
                        return 0;
                    }
                    '''
                ),
            )
            assert run.returncode == 0, run.stderr

    def test_generated_machine_cpp98_supports_cxx_keyword_safe_identifiers(self):
        dsl_code = """
        def int class = 1;
        state Root {
            state template {
                during { class = class + 1; }
            }
            [*] -> template;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            run = _compile_and_run_cpp_harness(
                artifacts,
                'cpp98_keyword_safe_identifiers',
                textwrap.dedent(
                    r'''
                    #include "machine.h"
                    #include <cstring>

                    int main()
                    {
                        RootMachine machine;
                        if (!RootMachine_init(&machine)) {
                            return 30;
                        }
                        if (!RootMachine_cycle(&machine)) {
                            return 31;
                        }
                        if (std::strcmp(RootMachine_current_state_path(&machine), "Root.template") != 0) {
                            return 32;
                        }
                        return 0;
                    }
                    '''
                ),
            )
            assert run.returncode == 0, run.stderr


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
