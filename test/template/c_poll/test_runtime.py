import os.path
import re
import shutil
import subprocess
import textwrap

import pytest

from ._utils import render_c_artifacts, render_c_runtime

_CLANG_FORMAT_STYLE = '{BasedOnStyle: LLVM, IndentWidth: 4, ContinuationIndentWidth: 4}'


def _representative_gate_dsl():
    return """
    def int counter = 0;
    def int ready = 0;
    def float gain = 1.5;
    state Control {
        enter abstract Boot;
        state Idle {
            during { counter = counter + 1; }
        }
        state Active {
            enter abstract ActiveEnter;
            during before { gain = gain + 0.5; }
            state Work {
                enter { counter = counter + 2; }
                during { counter = counter + 3; }
            }
            [*] -> Work : if [ready == 1];
        }
        state Done;
        [*] -> Idle;
        Idle -> Active :: Start effect { ready = 1; counter = counter + 10; };
        Active -> Done : if [counter >= 20] effect { counter = counter + 1; };
    }
    """


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


def _workflow_metadata_labels():
    return [
        ''.join(('p', 'r', '-', '3')),
        ''.join(('issue', ' #', '209')),
        ''.join(('road', 'map')),
        ''.join(('review', ' ', 'round')),
    ]


def _duplicate_macro_define_names(header):
    seen_names = set()
    duplicates = []
    for name in re.findall(r'^#define\s+(\w+)', header, flags=re.M):
        if name in seen_names and name not in duplicates:
            duplicates.append(name)
        seen_names.add(name)
    return duplicates


def _normalized_lower_text(text):
    lines = []
    for line in text.lower().splitlines():
        lines.append(line.strip().lstrip('/*').lstrip('*').strip())
    return ' '.join(item for item in lines if item)


def _first_c_comment_block(source):
    start = source.find('/*')
    end = source.find('*/', start)
    assert start >= 0
    assert end > start
    return source[start:end + 2]


def _assert_generated_c_banner(source, *, template_name, root_name, extra_terms=None):
    banner = _first_c_comment_block(source)
    lower_banner = _normalized_lower_text(banner)
    assert 'generated' in lower_banner
    assert '`{name}` template'.format(name=template_name) in lower_banner
    assert root_name in banner
    assert 'do not edit generated source directly' in lower_banner
    assert 'change the fcstm dsl/model and regenerate' in lower_banner
    assert 'self-contained' in lower_banner
    assert (
        'does not depend on pyfcstm' in lower_banner
        or 'does not require pyfcstm' in lower_banner
    )
    assert 'third-party runtime packages' in lower_banner
    for term in extra_terms or []:
        assert term.lower() in lower_banner

    lower_source = source.lower()
    for label in _workflow_metadata_labels():
        assert label not in lower_source


@pytest.mark.unittest
class TestCPollBuiltinTemplate:

    def test_generated_context_metadata_uses_numeric_contract(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            enter abstract Boot;
            state Library {
                enter abstract Shared;
            }
            state A {
                enter FirstRef ref /Library.Shared;
                during abstract Touch;
            }
            state B;
            [*] -> A;
            A -> B :: Go;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            with open(artifacts["machine_h_file"], "r", encoding="utf-8") as f:
                header = f.read()
            with open(artifacts["machine_c_file"], "r", encoding="utf-8") as f:
                source = f.read()
            with open(artifacts["readme_file"], "r", encoding="utf-8") as f:
                readme = f.read()

        assert "typedef int RootMachineActionId;" in header
        assert "typedef int RootMachineStageId;" in header
        assert "ROOT_MACHINE_INVALID_ACTION_ID" in header
        assert "ROOT_MACHINE_STAGE_ENTER" in header
        assert "RootMachine_current_state_id" in header

        context_block = re.search(
            r"struct RootMachineExecutionContext \{(?P<body>.*?)\};",
            header,
            flags=re.S,
        ).group("body")
        for forbidden in (
            "const char *state_path",
            "const char *action_name",
            "const char *action_stage",
            "const char *active_leaf",
            "const char *call_stage",
            "const char *abstract_target",
            "const char *named_ref",
        ):
            assert forbidden not in context_block
        assert "RootMachineStateId state_id;" in context_block
        assert "RootMachineActionId action_id;" in context_block
        assert "RootMachineStageId action_stage_id;" in context_block
        assert "RootMachineStateId active_leaf_state_id;" in context_block
        assert "RootMachineStageId call_stage_id;" in context_block
        assert "RootMachineActionId abstract_target_id;" in context_block
        assert "RootMachineActionId named_ref_id;" in context_block

        assert "ctx->action_name" not in readme
        assert "ctx->state_path" not in readme
        assert "strcmp(ctx->" not in readme
        assert "strcmp(ctx->" not in source

        event_context_block = re.search(
            r"struct RootMachineEventContext \{(?P<body>.*?)\};",
            header,
            flags=re.S,
        ).group("body")
        assert "event_path" not in event_context_block
        assert "current_state_path" not in event_context_block
        assert "RootMachineEventId event_id;" in event_context_block
        assert "RootMachineStateId current_state_id;" in event_context_block

    def test_generated_public_metadata_identifiers_resist_path_collisions(self):
        dsl_code = """
        def int trace = 0;
        state Root {
            state A {
                state B {
                    event Go;
                    enter abstract Shared;
                }
                [*] -> B;
            }
            state A_B {
                event Go;
                enter abstract Shared;
            }
            [*] -> A_B;
            A_B -> A :: Swap;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            with open(artifacts["machine_h_file"], "r", encoding="utf-8") as f:
                header = f.read()

            run = _compile_and_run_c_harness(
                artifacts,
                "collision_safe_public_metadata",
                textwrap.dedent(
                    r"""
                    #include "machine.h"

                    static int inactive_event(
                        RootMachine *machine,
                        const RootMachineEventContext *ctx,
                        void *user_data
                    )
                    {
                        (void)machine;
                        (void)ctx;
                        (void)user_data;
                        return 0;
                    }

                    static int swap_event(
                        RootMachine *machine,
                        const RootMachineEventContext *ctx,
                        void *user_data
                    )
                    {
                        (void)machine;
                        (void)user_data;
                        return (
                            ctx->event_id == ROOT_MACHINE_EVENT_P4_ROOT_P3_A_B_P4_SWAP &&
                            ctx->current_state_id == ROOT_MACHINE_STATE_P4_ROOT_P3_A_B
                        );
                    }

                    int main(void)
                    {
                        RootMachine machine;
                        RootMachineHooks hooks = ROOTMACHINE_HOOKS_INIT;
                        RootMachineEventChecks event_checks = ROOTMACHINE_EVENT_CHECKS_INIT;
                        (void)hooks.on_p4_Root_p1_A_p1_B_p6_Shared;
                        (void)hooks.on_p4_Root_p3_A_B_p6_Shared;

                        if (ROOT_MACHINE_STATE_P4_ROOT_P1_A_P1_B == ROOT_MACHINE_STATE_P4_ROOT_P3_A_B) {
                            return 10;
                        }
                        if (ROOT_MACHINE_EVENT_P4_ROOT_P1_A_P1_B_P2_GO == ROOT_MACHINE_EVENT_P4_ROOT_P3_A_B_P2_GO) {
                            return 11;
                        }
                        if (ROOT_MACHINE_ACTION_P4_ROOT_P1_A_P1_B_P6_SHARED == ROOT_MACHINE_ACTION_P4_ROOT_P3_A_B_P6_SHARED) {
                            return 12;
                        }
                        if (!RootMachine_init(&machine)) {
                            return 13;
                        }
                        event_checks.check_p4_Root_p3_A_B_p4_Swap = swap_event;
                        event_checks.check_p4_Root_p1_A_p1_B_p2_Go = inactive_event;
                        event_checks.check_p4_Root_p3_A_B_p2_Go = inactive_event;
                        RootMachine_set_event_checks(&machine, &event_checks, NULL);
                        if (!RootMachine_cycle(&machine)) {
                            return 14;
                        }
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_P4_ROOT_P3_A_B) {
                            return 15;
                        }
                        if (!RootMachine_cycle(&machine)) {
                            return 16;
                        }
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_P4_ROOT_P1_A_P1_B) {
                            return 17;
                        }
                        return 0;
                    }
                    """
                ),
            )

        assert "#define ROOT_MACHINE_STATE_P4_ROOT_P1_A_B " not in header
        assert "#define ROOT_MACHINE_EVENT_ROOT_A_B_GO " not in header
        assert "#define ROOT_MACHINE_ACTION_ROOT_A_B_SHARED " not in header
        assert run.returncode == 0, run.stderr

    def test_generated_public_metadata_aliases_avoid_reserved_macros(self):
        dsl_code = """
        def int trace = 0;
        state Count {
            enter abstract Count;
            state InvalidStateId {
                enter abstract StageEnter;
                event Count;
                event InvalidEventId;
            }
            state ActionCount;
            [*] -> InvalidStateId;
            InvalidStateId -> ActionCount :: Count;
            ActionCount -> InvalidStateId :: InvalidEventId;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            with open(artifacts["machine_h_file"], "r", encoding="utf-8") as f:
                header = f.read()

            duplicate_names = [
                name
                for name in _duplicate_macro_define_names(header)
                if name != "COUNT_MACHINE_API"
            ]
            run = _compile_and_run_c_harness(
                artifacts,
                "reserved_public_metadata_aliases",
                textwrap.dedent(
                    r"""
                    #include "machine.h"

                    int main(void)
                    {
                        if (COUNT_MACHINE_STATE_COUNT != 3) {
                            return 10;
                        }
                        if (COUNT_MACHINE_EVENT_COUNT != 3) {
                            return 11;
                        }
                        if (COUNT_MACHINE_ACTION_COUNT != 2) {
                            return 12;
                        }
                        if (COUNT_MACHINE_STAGE_ENTER != 0) {
                            return 13;
                        }
                        if (COUNT_MACHINE_INVALID_STATE_ID >= 0) {
                            return 14;
                        }
                        if (COUNT_MACHINE_INVALID_EVENT_ID >= 0) {
                            return 15;
                        }
                        if (COUNT_MACHINE_STATE_P5_COUNT < 0) {
                            return 16;
                        }
                        if (COUNT_MACHINE_STATE_P5_COUNT_P14_INVALIDSTATEID < 0) {
                            return 17;
                        }
                        if (COUNT_MACHINE_EVENT_P5_COUNT_P14_INVALIDSTATEID_P5_COUNT < 0) {
                            return 18;
                        }
                        if (COUNT_MACHINE_ACTION_P5_COUNT_P5_COUNT < 0) {
                            return 19;
                        }
                        if (COUNT_MACHINE_ACTION_P5_COUNT_P14_INVALIDSTATEID_P10_STAGEENTER < 0) {
                            return 20;
                        }
                        return 0;
                    }
                    """
                ),
            )

        assert "#define COUNT_MACHINE_STATE_COUNT COUNT_MACHINE_STATE_" not in header
        assert "#define COUNT_MACHINE_ACTION_COUNT COUNT_MACHINE_ACTION_" not in header
        assert duplicate_names == []
        assert run.returncode == 0, run.stderr

    def test_generated_machine_source_banners_document_file_contract(self):
        with render_c_artifacts(_representative_gate_dsl()) as artifacts:
            with open(artifacts["machine_h_file"], "r", encoding="utf-8") as f:
                header = f.read()
            with open(artifacts["machine_c_file"], "r", encoding="utf-8") as f:
                source = f.read()

            _assert_generated_c_banner(
                header,
                template_name="c_poll",
                root_name="Control",
                extra_terms=["public integration header", "event-check polling"],
            )
            _assert_generated_c_banner(
                source,
                template_name="c_poll",
                root_name="Control",
                extra_terms=["implementation", "event-check polling"],
            )
            assert source.index("/*") < source.index('#include "machine.h"')


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

    def test_generated_machine_create_failure_cannot_be_cycled(self):
        dsl_code = """
        def int counter = 1.5;
        state Root {
            state A;
            [*] -> A;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            run = _compile_and_run_c_harness(
                artifacts,
                'create_failure_cycle_guard_test',
                textwrap.dedent(
                    r'''
                    #include "machine.h"
                    #include <string.h>

                    int main(void)
                    {
                        RootMachine *machine = RootMachine_create();
                        const char *message;

                        if (machine == NULL) {
                            return 10;
                        }
                        message = RootMachine_last_error(machine);
                        if (message == NULL || strstr(message, "non-integer float") == NULL) {
                            RootMachine_destroy(machine);
                            return 11;
                        }
                        if (RootMachine_current_state_path(machine) != NULL) {
                            RootMachine_destroy(machine);
                            return 12;
                        }
                        if (RootMachine_cycle(machine)) {
                            RootMachine_destroy(machine);
                            return 13;
                        }
                        message = RootMachine_last_error(machine);
                        if (message == NULL || strstr(message, "not initialized") == NULL) {
                            RootMachine_destroy(machine);
                            return 14;
                        }
                        if (RootMachine_current_state_path(machine) != NULL) {
                            RootMachine_destroy(machine);
                            return 15;
                        }

                        RootMachine_destroy(machine);
                        return 0;
                    }
                    '''
                ),
            )
            assert run.returncode == 0, run.stderr

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
                'on_p4_Root_p6_System_p1_A_p6_AEnter': lambda ctx: hot_calls.append(
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
                'on_p4_Root_p8_RootInit': lambda ctx: cold_calls.append(
                    ('cold', ctx.get_full_state_path(), ctx.action_stage, ctx.get_var('counter'))
                ),
            })
            runtime.cycle()

            assert runtime.current_state_path == ('Root', 'System', 'A')
            assert runtime.vars == {'counter': 1}
            assert cold_calls == [('cold', 'Root', 'enter', 0)]


    def test_failed_hot_start_preserves_public_runtime_snapshot(self):
        dsl_code = """
        def int trace = 0;
        state Root {
            state Idle { during { trace = trace + 1; } }
            state Composite {
                state Blocked;
                [*] -> Blocked : if [false];
            }
            [*] -> Idle;
        }
        """

        with render_c_runtime(dsl_code) as (runtime, _):
            runtime.cycle()
            before_state = runtime.current_state_path
            before_vars = dict(runtime.vars)
            before_ended = runtime.is_ended

            with pytest.raises(ValueError, match='cannot reach a stoppable state'):
                runtime.hot_start('Root.Composite', {'trace': 5})

            assert runtime.current_state_path == before_state
            assert runtime.vars == before_vars
            assert runtime.is_ended is before_ended

            runtime.cycle()
            assert runtime.current_state_path == before_state
            assert runtime.vars == {'trace': before_vars['trace'] + 1}
            assert runtime.is_ended is before_ended

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
                'check_p4_Root_p1_A_p2_Go': lambda ctx: calls.append(
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
                'on_p4_Root_p8_RootInit': lambda ctx: trace.append(('hook', ctx.action_name, ctx.get_var('counter'))),
                'on_p4_Root_p1_B_p6_BEnter': lambda ctx: trace.append(('hook', ctx.action_name, ctx.get_var('counter'))),
            })
            runtime.install_event_checks({
                'check_p4_Root_p1_A_p2_Go': lambda ctx: trace.append(('event', ctx.event_path, ctx.get_var('counter'))) or True,
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
            assert 'check_p4_Root_p1_A_p2_Go' in readme
            assert 'return non-zero' in readme
            assert 'return `0`' in readme

            assert 'EventChecks' in readme_zh
            assert 'EventCheckFn' in readme_zh
            assert '_set_event_checks(' in readme_zh
            assert '_cycle(&machine)' in readme_zh
            assert 'cycle(machine, event_ids, event_count)' not in readme_zh
            assert '直接失败' in readme_zh
            assert 'check_p4_Root_p1_A_p2_Go' in readme_zh
            assert '返回非零' in readme_zh
            assert '返回 `0`' in readme_zh

    def test_generated_machine_clang_format_converges_under_four_space_style(self):
        with render_c_artifacts(_representative_gate_dsl()) as artifacts:
            for key in ["machine_h_file", "machine_c_file"]:
                path = artifacts[key]
                with open(path, "r", encoding="utf-8") as f:
                    original = f.read()

                formatted_once = _format_c_text(original, os.path.basename(path))
                formatted_twice = _format_c_text(formatted_once, os.path.basename(path))

                assert formatted_once == formatted_twice
                assert "\t" not in formatted_once

    def test_generated_hot_start_checks_stack_depth_before_path_write(self):
        with render_c_artifacts(_representative_gate_dsl()) as artifacts:
            with open(artifacts["machine_c_file"], "r", encoding="utf-8") as f:
                source = f.read()

            hot_start = source.index("int ControlMachine_hot_start(")
            path_loop = source.index("path_count = 0u;", hot_start)
            guard = source.index("if (path_count >=", path_loop)
            write = source.index("path_ids[path_count++]", path_loop)

            assert guard < write

    def test_generated_readme_code_blocks_are_formatter_friendly(self):
        with render_c_artifacts(_representative_gate_dsl()) as artifacts:
            with open(artifacts["readme_file"], "r", encoding="utf-8") as f:
                readme = f.read()
            with open(artifacts["readme_zh_file"], "r", encoding="utf-8") as f:
                readme_zh = f.read()

            for content in [readme, readme_zh]:
                blocks = re.findall(r"```(?:c|cpp|bash)\n(.*?)```", content, flags=re.S)
                assert blocks
                for block in blocks:
                    assert "\t" not in block

            assert "clang-format" in readme
            assert "clang-format" in readme_zh


    def test_generated_machine_c_event_checks_install_and_drive_cycle(self):
        with render_c_artifacts(_representative_gate_dsl()) as artifacts:
            run = _compile_and_run_c_harness(
                artifacts,
                "event_check_mount_test",
                textwrap.dedent(
                    r"""
                    #include "machine.h"

                    typedef struct EventLog {
                        int allow_start;
                        int seen_start;
                    } EventLog;

                    typedef struct HookLog {
                        int boot_calls;
                        int active_calls;
                    } HookLog;

                    static int check_start(
                        ControlMachine *machine,
                        const ControlMachineEventContext *ctx,
                        void *user_data
                    )
                    {
                        EventLog *log = (EventLog *)user_data;
                        (void)machine;
                        if (
                            ctx->event_id == CONTROL_MACHINE_EVENT_P7_CONTROL_P4_IDLE_P5_START &&
                            ctx->current_state_id == CONTROL_MACHINE_STATE_P7_CONTROL_P4_IDLE
                        ) {
                            log->seen_start += 1;
                        }
                        return log->allow_start;
                    }

                    static void boot_hook(
                        ControlMachine *machine,
                        const ControlMachineExecutionContext *ctx,
                        void *user_data
                    )
                    {
                        HookLog *log = (HookLog *)user_data;
                        (void)machine;
                        if (ctx->action_id == CONTROL_MACHINE_ACTION_P7_CONTROL_P4_BOOT) {
                            log->boot_calls += 1;
                        }
                    }

                    static void active_hook(
                        ControlMachine *machine,
                        const ControlMachineExecutionContext *ctx,
                        void *user_data
                    )
                    {
                        HookLog *log = (HookLog *)user_data;
                        (void)machine;
                        if (ctx->action_id == CONTROL_MACHINE_ACTION_P7_CONTROL_P6_ACTIVE_P11_ACTIVEENTER) {
                            log->active_calls += 1;
                        }
                    }

                    int main(void)
                    {
                        ControlMachine machine;
                        ControlMachineHooks hooks = CONTROLMACHINE_HOOKS_INIT;
                        ControlMachineEventChecks event_checks = CONTROLMACHINE_EVENT_CHECKS_INIT;
                        EventLog log = {0};
                        HookLog hooks_log = {0};

                        if (!ControlMachine_init(&machine)) {
                            return 10;
                        }
                        if (ControlMachine_cycle(&machine)) {
                            return 11;
                        }

                        hooks.on_p7_Control_p4_Boot = boot_hook;
                        hooks.on_p7_Control_p6_Active_p11_ActiveEnter = active_hook;
                        ControlMachine_set_hooks(&machine, &hooks, &hooks_log);
                        event_checks.check_p7_Control_p4_Idle_p5_Start = check_start;
                        ControlMachine_set_event_checks(&machine, &event_checks, &log);

                        if (!ControlMachine_cycle(&machine)) {
                            return 12;
                        }
                        if (ControlMachine_current_state_id(&machine) != CONTROL_MACHINE_STATE_P7_CONTROL_P4_IDLE) {
                            return 13;
                        }
                        if (ControlMachine_vars(&machine)->counter != 1) {
                            return 14;
                        }
                        if (hooks_log.boot_calls != 1 || hooks_log.active_calls != 0) {
                            return 15;
                        }

                        log.allow_start = 1;
                        if (!ControlMachine_cycle(&machine)) {
                            return 16;
                        }
                        if (ControlMachine_current_state_id(&machine) != CONTROL_MACHINE_STATE_P7_CONTROL_P6_ACTIVE_P4_WORK) {
                            return 17;
                        }
                        if (
                            ControlMachine_vars(&machine)->ready != (ControlMachineInt)1 ||
                            ControlMachine_vars(&machine)->counter != (ControlMachineInt)16 ||
                            ControlMachine_vars(&machine)->gain != 2.0
                        ) {
                            return 18;
                        }
                        if (log.seen_start != 1) {
                            return 19;
                        }
                        if (hooks_log.boot_calls != 1 || hooks_log.active_calls != 1) {
                            return 20;
                        }

                        return 0;
                    }
                    """
                ),
            )
            assert run.returncode == 0, run.stderr


    def test_generated_machine_cpp98_event_checks_install_and_drive_cycle(self):
        with render_c_artifacts(_representative_gate_dsl()) as artifacts:
            run = _compile_and_run_cpp_harness(
                artifacts,
                "cpp98_event_check_mount",
                textwrap.dedent(
                    r"""
                    #include "machine.h"

                    struct EventLog {
                        int allow_start;
                        int seen_start;
                    };

                    static int check_start(
                        ControlMachine *machine,
                        const ControlMachineEventContext *ctx,
                        void *user_data
                    )
                    {
                        EventLog *log = static_cast<EventLog *>(user_data);
                        (void)machine;
                        if (
                            ctx->event_id == CONTROL_MACHINE_EVENT_P7_CONTROL_P4_IDLE_P5_START &&
                            ctx->current_state_id == CONTROL_MACHINE_STATE_P7_CONTROL_P4_IDLE
                        ) {
                            log->seen_start += 1;
                        }
                        return log->allow_start;
                    }

                    int main()
                    {
                        ControlMachine machine;
                        ControlMachineEventChecks event_checks = CONTROLMACHINE_EVENT_CHECKS_INIT;
                        EventLog log = {0, 0};

                        if (!ControlMachine_init(&machine)) {
                            return 20;
                        }
                        event_checks.check_p7_Control_p4_Idle_p5_Start = check_start;
                        ControlMachine_set_event_checks(&machine, &event_checks, &log);

                        if (!ControlMachine_cycle(&machine)) {
                            return 21;
                        }
                        if (ControlMachine_current_state_id(&machine) != CONTROL_MACHINE_STATE_P7_CONTROL_P4_IDLE) {
                            return 22;
                        }
                        log.allow_start = 1;
                        if (!ControlMachine_cycle(&machine)) {
                            return 23;
                        }
                        if (ControlMachine_current_state_id(&machine) != CONTROL_MACHINE_STATE_P7_CONTROL_P6_ACTIVE_P4_WORK) {
                            return 24;
                        }
                        if (
                            ControlMachine_vars(&machine)->ready != (ControlMachineInt)1 ||
                            ControlMachine_vars(&machine)->counter != (ControlMachineInt)16 ||
                            ControlMachine_vars(&machine)->gain != 2.0
                        ) {
                            return 25;
                        }
                        if (log.seen_start != 1) {
                            return 26;
                        }
                        return 0;
                    }
                    """
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

                    int main()
                    {
                        RootMachine machine;
                        if (!RootMachine_init(&machine)) {
                            return 30;
                        }
                        if (!RootMachine_cycle(&machine)) {
                            return 31;
                        }
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_P4_ROOT_P9_TEMPLATE_) {
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
