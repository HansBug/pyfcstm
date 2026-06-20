import os.path
import re
import shutil
import subprocess
import textwrap

import pytest

from ._utils import render_c_artifacts, render_c_runtime


_CLANG_FORMAT_STYLE = "{BasedOnStyle: LLVM, IndentWidth: 4, ContinuationIndentWidth: 4}"


def _format_c_text(text, filename):
    clang_format = shutil.which("clang-format")
    if clang_format is None:
        pytest.skip("clang-format is required for C formatter convergence tests.")

    return subprocess.run(
        [
            clang_format,
            "-style=" + _CLANG_FORMAT_STYLE,
            "--assume-filename=" + filename,
        ],
        input=text,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    ).stdout


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


def _public_generated_names(header):
    macro_names = re.findall(r'^#define\s+(\w+)', header, flags=re.M)
    hook_fields = re.findall(r'^\s+(on_\w+);', header, flags=re.M)
    return macro_names + hook_fields


def _reserved_cxx_public_names(header):
    return [
        name
        for name in _public_generated_names(header)
        if '__' in name or re.search(r'(?:^|_)_[A-Z]', name)
    ]


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
class TestCBuiltinTemplate:
    def test_generated_machine_source_banners_document_file_contract(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            state Idle {
                during { counter = counter + 1; }
            }
            state Running;
            [*] -> Idle;
            Idle -> Running :: Start;
        }
        """

        with render_c_artifacts(dsl_code) as artifacts:
            with open(artifacts['machine_h_file'], 'r', encoding='utf-8') as f:
                header = f.read()
            with open(artifacts['machine_c_file'], 'r', encoding='utf-8') as f:
                source = f.read()

            _assert_generated_c_banner(
                header,
                template_name='c',
                root_name='Root',
                extra_terms=['public integration header'],
            )
            _assert_generated_c_banner(
                source,
                template_name='c',
                root_name='Root',
                extra_terms=['implementation'],
            )
            assert source.index('/*') < source.index('#include "machine.h"')


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

    def test_generated_root_public_identifiers_avoid_reserved_shapes(self):
        cases = [
            {
                "root_name": "_Root",
                "class_name": "p_p5_z00005FRootMachine",
                "macro_name": "P_P5_Z00005FROOT_MACHINE",
                "state_slug": "p5_z00005FRoot_p4_Idle",
            },
            {
                "root_name": "class",
                "class_name": "class_Machine",
                "macro_name": "P_P5_CLASS_MACHINE",
                "state_slug": "p5_class_p4_Idle",
            },
        ]

        for case in cases:
            dsl_code = """
            state {root_name} {{
                state Idle;
                [*] -> Idle;
            }}
            """.format(root_name=case["root_name"])

            with render_c_artifacts(dsl_code) as artifacts:
                with open(artifacts["machine_h_file"], "r", encoding="utf-8") as f:
                    header = f.read()

                class_name = case["class_name"]
                macro_name = case["macro_name"]
                run = _compile_and_run_cpp_harness(
                    artifacts,
                    "root_reserved_safe_public_identifiers_" + case["root_name"].replace("_", "u"),
                    textwrap.dedent(
                        """
                        #include "machine.h"

                        int main()
                        {{
                            {class_name} machine;

                            if (!{class_name}_init(&machine)) {{
                                return 10;
                            }}
                            if (!{class_name}_cycle(&machine, 0, 0u)) {{
                                return 11;
                            }}
                            if ({class_name}_current_state_id(&machine) != {macro_name}_STATE_{state_slug}) {{
                                return 12;
                            }}
                            if ({macro_name}_SUCCESS != 1) {{
                                return 13;
                            }}
                            return 0;
                        }}
                        """.format(
                            class_name=class_name,
                            macro_name=macro_name,
                            state_slug=case["state_slug"],
                        )
                    ),
                )

            assert "_ROOT_MACHINE" not in header
            assert "CLASS__MACHINE" not in header
            assert "#ifndef PYFCSTM_GENERATED_{macro_name}_H".format(
                macro_name=case["macro_name"],
            ) in header
            assert "#define {macro_name}_API".format(
                macro_name=case["macro_name"],
            ) in header
            assert _reserved_cxx_public_names(header) == []
            assert run.returncode == 0, run.stderr

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

                    int main(void)
                    {
                        RootMachine machine;
                        RootMachineHooks hooks = ROOTMACHINE_HOOKS_INIT;
                        static const RootMachineEventId swap_events[] = {
                            ROOT_MACHINE_EVENT_P4_ROOT_P3_AZ00005FB_P4_SWAP
                        };
                        (void)hooks.on_p4_Root_p1_A_p1_B_p6_Shared;
                        (void)hooks.on_p4_Root_p3_Az00005FB_p6_Shared;

                        if (ROOT_MACHINE_STATE_P4_ROOT_P1_A_P1_B == ROOT_MACHINE_STATE_P4_ROOT_P3_AZ00005FB) {
                            return 10;
                        }
                        if (ROOT_MACHINE_EVENT_P4_ROOT_P1_A_P1_B_P2_GO == ROOT_MACHINE_EVENT_P4_ROOT_P3_AZ00005FB_P2_GO) {
                            return 11;
                        }
                        if (ROOT_MACHINE_ACTION_P4_ROOT_P1_A_P1_B_P6_SHARED == ROOT_MACHINE_ACTION_P4_ROOT_P3_AZ00005FB_P6_SHARED) {
                            return 12;
                        }
                        if (!RootMachine_init(&machine)) {
                            return 13;
                        }
                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 14;
                        }
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_P4_ROOT_P3_AZ00005FB) {
                            return 15;
                        }
                        if (!RootMachine_cycle(&machine, swap_events, 1u)) {
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
        assert _reserved_cxx_public_names(header) == []
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
        assert _reserved_cxx_public_names(header) == []
        assert run.returncode == 0, run.stderr

    def test_generated_public_metadata_identifiers_preserve_case_and_underscores(self):
        dsl_code = """
        def int trace = 0;
        state Count {
            event Internal;
            enter abstract Count;
            state Internal {
                event Count;
                enter abstract InvalidActionId;
                during abstract Shared;
            }
            state Internal_ {
                event Count;
                enter abstract Shared;
            }
            state A {
                enter abstract Shared;
            }
            state a {
                enter abstract Shared;
            }
            state A_B {
                enter abstract Shared;
            }
            state A__B {
                enter abstract Shared;
            }
            [*] -> Internal;
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
                "case_and_underscore_safe_public_metadata",
                textwrap.dedent(
                    r"""
                    #include "machine.h"

                    int main(void)
                    {
                        CountMachineHooks hooks = COUNTMACHINE_HOOKS_INIT;
                        (void)hooks.on_p5_Count_p8_Internal_p15_InvalidActionId;
                        (void)hooks.on_p5_Count_p8_Internal_p6_Shared;
                        (void)hooks.on_p5_Count_p9_Internalz00005F_p6_Shared;
                        (void)hooks.on_p5_Count_p1_A_p6_Shared;
                        (void)hooks.on_p5_Count_p1_a_p6_Shared;
                        (void)hooks.on_p5_Count_p3_Az00005FB_p6_Shared;
                        (void)hooks.on_p5_Count_p4_Az00005Fz00005FB_p6_Shared;

                        if (COUNT_MACHINE_STATE_p5_Count_p8_Internal == COUNT_MACHINE_STATE_p5_Count_p9_Internalz00005F) {
                            return 10;
                        }
                        if (COUNT_MACHINE_STATE_p5_Count_p1_A == COUNT_MACHINE_STATE_p5_Count_p1_a) {
                            return 11;
                        }
                        if (COUNT_MACHINE_STATE_p5_Count_p3_Az00005FB == COUNT_MACHINE_STATE_p5_Count_p4_Az00005Fz00005FB) {
                            return 12;
                        }
                        if (COUNT_MACHINE_EVENT_p5_Count_p8_Internal_p5_Count == COUNT_MACHINE_EVENT_p5_Count_p9_Internalz00005F_p5_Count) {
                            return 13;
                        }
                        if (COUNT_MACHINE_ACTION_p5_Count_p8_Internal_p6_Shared == COUNT_MACHINE_ACTION_p5_Count_p9_Internalz00005F_p6_Shared) {
                            return 14;
                        }
                        if (COUNT_MACHINE_ACTION_p5_Count_p1_A_p6_Shared == COUNT_MACHINE_ACTION_p5_Count_p1_a_p6_Shared) {
                            return 15;
                        }
                        if (COUNT_MACHINE_ACTION_p5_Count_p3_Az00005FB_p6_Shared == COUNT_MACHINE_ACTION_p5_Count_p4_Az00005Fz00005FB_p6_Shared) {
                            return 16;
                        }
                        return 0;
                    }
                    """
                ),
            )

        assert "#define COUNT_MACHINE_STATE_P5_COUNT_P1_A " not in header
        assert "#define COUNT_MACHINE_ACTION_P5_COUNT_P1_A_P6_SHARED " not in header
        assert "#define COUNT_MACHINE_STATE_COUNT_A_B " not in header
        assert duplicate_names == []
        assert _reserved_cxx_public_names(header) == []
        assert run.returncode == 0, run.stderr

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
                        if (RootMachine_cycle(machine, NULL, 0u)) {
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
                'on_p4_Root_p8_RootInit': root_hook,
                'on_p4_Root_p6_System_p1_A_p6_AEnter': a_enter_hook,
            })
            runtime.cycle()

            assert runtime.current_state_path == ('Root', 'System', 'A')
            assert runtime.vars == {'counter': 2}
            assert calls == [
                ('root', 'Root', 'enter', 0),
                ('a_enter', 'Root.System.A', 'enter', 0),
            ]
            assert runtime.get_abstract_hook_map() == {
                'Root.RootInit': 'on_p4_Root_p8_RootInit',
                'Root.System.A.AEnter': 'on_p4_Root_p6_System_p1_A_p6_AEnter',
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
                            ctx->action_id == ROOT_MACHINE_ACTION_P4_ROOT_P8_ROOTINIT &&
                            ctx->state_id == ROOT_MACHINE_STATE_ROOT &&
                            ctx->action_stage_id == ROOT_MACHINE_STAGE_ENTER
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
                            ctx->action_id == ROOT_MACHINE_ACTION_P4_ROOT_P6_SYSTEM_P1_A_P6_AENTER &&
                            ctx->state_id == ROOT_MACHINE_STATE_P4_ROOT_P6_SYSTEM_P1_A &&
                            ctx->action_stage_id == ROOT_MACHINE_STAGE_ENTER
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

                        hooks.on_p4_Root_p8_RootInit = root_hook;
                        hooks.on_p4_Root_p6_System_p1_A_p6_AEnter = a_enter_hook;
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
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_P4_ROOT_P6_SYSTEM_P1_A) {
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

                    typedef struct HookLog {
                        int total_calls;
                        int root_calls;
                        int a_calls;
                        int b_calls;
                    } HookLog;

                    static void platform_hook(
                        RootMachine *machine,
                        const RootMachineExecutionContext *ctx,
                        void *user_data
                    )
                    {
                        HookLog *log = (HookLog *)user_data;
                        (void)machine;

                        if (ctx->action_id != ROOT_MACHINE_ACTION_P4_ROOT_P12_PLATFORMINIT) {
                            log->total_calls = -100;
                            return;
                        }
                        if (ctx->abstract_target_id != ROOT_MACHINE_ACTION_P4_ROOT_P12_PLATFORMINIT) {
                            log->total_calls = -101;
                            return;
                        }
                        if (ctx->call_stage_id != ROOT_MACHINE_STAGE_ENTER) {
                            log->total_calls = -102;
                            return;
                        }

                        log->total_calls += 1;
                        if (ctx->state_id == ROOT_MACHINE_STATE_ROOT) {
                            log->root_calls += 1;
                        }
                        if (ctx->state_id == ROOT_MACHINE_STATE_P4_ROOT_P1_A) {
                            log->a_calls += 1;
                        }
                        if (ctx->state_id == ROOT_MACHINE_STATE_P4_ROOT_P1_B) {
                            log->b_calls += 1;
                        }
                    }

                    int main(void)
                    {
                        RootMachine machine;
                        RootMachineHooks hooks = ROOTMACHINE_HOOKS_INIT;
                        HookLog log = {0};
                        static const RootMachineEventId go_events[] = {
                            ROOT_MACHINE_EVENT_P4_ROOT_P1_A_P2_GO
                        };

                        if (!RootMachine_init(&machine)) {
                            return 20;
                        }

                        hooks.on_p4_Root_p12_PlatformInit = platform_hook;
                        RootMachine_set_hooks(&machine, &hooks, &log);

                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 21;
                        }
                        if (log.total_calls != 2 || log.root_calls != 1 || log.a_calls != 1 || log.b_calls != 0) {
                            return 22;
                        }
                        if (RootMachine_vars(&machine)->trace != 1) {
                            return 23;
                        }

                        if (!RootMachine_cycle(&machine, go_events, 1u)) {
                            return 24;
                        }
                        if (log.total_calls != 3 || log.root_calls != 1 || log.a_calls != 1 || log.b_calls != 1) {
                            return 25;
                        }
                        if (RootMachine_vars(&machine)->trace != 11) {
                            return 26;
                        }
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_P4_ROOT_P1_B) {
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

            runtime.install_hooks({'on_p4_Root_p12_PlatformInit': platform_init})
            runtime.cycle()
            assert runtime.current_state_path == ('Root', 'A')
            assert runtime.vars == {'trace': 1}

            runtime.cycle(['Root.A.Go'])
            assert runtime.current_state_path == ('Root', 'B')
            assert runtime.vars == {'trace': 11}

            assert runtime.get_abstract_hook_map() == {
                'Root.PlatformInit': 'on_p4_Root_p12_PlatformInit',
            }
            assert calls == [
                ('Root.PlatformInit', 'enter', 'Root'),
                ('Root.PlatformInit', 'enter', 'Root.A'),
                ('Root.PlatformInit', 'enter', 'Root.B'),
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
            assert 'on_p4_Root_p8_RootInit' in readme
            assert 'on_p4_Root_p6_System_p1_A_p6_AEnter' in readme
            assert '| Hook field | DSL action path | Owner state | Stage |' in readme
            assert '## Public Header Reference' in readme
            assert '## Function Reference' in readme
            assert '## Performance Advice' in readme
            assert 'C++98' in readme
            assert 'RootMachineInt' in readme
            assert 'g++ -x c++ -std=c++98' in readme
            assert '### Deployment Profiles' in readme
            assert 'Caller-owned object' in readme
            assert 'PYFCSTM_GENERATED_NO_HEAP' in readme
            assert 'target_compile_definitions(machine PUBLIC PYFCSTM_GENERATED_NO_HEAP)' in readme
            assert 'default hosted profile only' in readme
            assert 'omitted when `PYFCSTM_GENERATED_NO_HEAP` is defined' in readme
            assert 'if(NOT WIN32)' in readme
            assert 'gcc -std=c99' in readme
            assert 'clang -std=c99' in readme
            assert 'strict freestanding guarantee' in readme
            assert 'read-only extension points' in readme
            assert 'should not mutate persistent machine variables' in readme
            assert 'RootMachine_vars(&machine)' in readme
            assert '| Hook 字段 | DSL 动作路径 | 所属状态 | 阶段 |' in readme_zh
            assert 'on_p4_Root_p8_RootInit' in readme_zh
            assert 'on_p4_Root_p6_System_p1_A_p6_AEnter' in readme_zh
            assert '## 公开头文件参考' in readme_zh
            assert '## 函数参考' in readme_zh
            assert '## 性能建议' in readme_zh
            assert 'C++98' in readme_zh
            assert 'RootMachineInt' in readme_zh
            assert 'g++ -x c++ -std=c++98' in readme_zh
            assert '### 部署剖面' in readme_zh
            assert '调用方拥有对象' in readme_zh
            assert 'PYFCSTM_GENERATED_NO_HEAP' in readme_zh
            assert 'target_compile_definitions(machine PUBLIC PYFCSTM_GENERATED_NO_HEAP)' in readme_zh
            assert '仅默认宿主剖面可用' in readme_zh
            assert '定义 `PYFCSTM_GENERATED_NO_HEAP` 时省略' in readme_zh
            assert 'if(NOT WIN32)' in readme_zh
            assert 'gcc -std=c99' in readme_zh
            assert 'clang -std=c99' in readme_zh
            assert '不等于严格 freestanding 保证' in readme_zh
            assert '只读扩展点' in readme_zh
            assert '不适合修改状态机持久变量' in readme_zh
            assert 'RootMachine_vars(&machine)' in readme_zh

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

    def test_generated_machine_source_is_c99_and_build_files_work(self):
        with render_c_artifacts(_representative_gate_dsl()) as artifacts:
            with open(artifacts["machine_h_file"], "r", encoding="utf-8") as f:
                header = f.read()
            with open(artifacts["machine_c_file"], "r", encoding="utf-8") as f:
                source = f.read()

            assert "#include <stddef.h>" in header
            assert "#include <math.h>" in source
            assert "windows.h" not in source
            assert "pthread.h" not in source
            assert "fork(" not in source

            assert os.path.isfile(artifacts["shared_lib"])
            assert os.path.isfile(artifacts["build_files"]["cmakelists"])

            make_executable = shutil.which("make")
            if make_executable is not None and os.name != "nt":
                subprocess.run(
                    [make_executable],
                    cwd=artifacts["output_dir"],
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                assert os.path.isfile(
                    os.path.join(artifacts["output_dir"], "libmachine.a")
                )
                assert os.path.isfile(artifacts["build_files"]["makefile"])

            if artifacts["cmake"] is not None:
                built_entries = set(os.listdir(artifacts["build_dir"]))
                assert "CMakeCache.txt" in built_entries

    def test_generated_machine_no_heap_profile_uses_caller_owned_objects(self):
        with render_c_artifacts(_representative_gate_dsl()) as artifacts:
            with open(artifacts["machine_h_file"], "r", encoding="utf-8") as f:
                header = f.read()
            with open(artifacts["machine_c_file"], "r", encoding="utf-8") as f:
                source = f.read()

            assert "#if !defined(PYFCSTM_GENERATED_NO_HEAP)" in header
            assert "#if !defined(PYFCSTM_GENERATED_NO_HEAP)" in source
            assert re.search(
                r"#if !defined\(PYFCSTM_GENERATED_NO_HEAP\)\n"
                r"#include <stdlib\.h>\n"
                r"#endif",
                source,
            )

            run = _compile_and_run_c_harness(
                artifacts,
                "no_heap_caller_owned_object",
                textwrap.dedent(
                    r"""
                    #include "machine.h"

                    #if !defined(PYFCSTM_GENERATED_NO_HEAP)
                    #error "The no-heap profile must be visible to consumers."
                    #endif

                    typedef struct HookLog {
                        int boot_calls;
                        int active_calls;
                    } HookLog;

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
                        static ControlMachine static_machine;
                        ControlMachine stack_machine;
                        ControlMachineHooks hooks = CONTROLMACHINE_HOOKS_INIT;
                        ControlMachineVars vars = {0};
                        HookLog log = {0, 0};
                        ControlMachineEventId start_event = CONTROL_MACHINE_EVENT_P7_CONTROL_P4_IDLE_P5_START;

                        if (!ControlMachine_init(&static_machine)) {
                            return 10;
                        }

                        if (!ControlMachine_init(&stack_machine)) {
                            return 12;
                        }
                        hooks.on_p7_Control_p4_Boot = boot_hook;
                        hooks.on_p7_Control_p6_Active_p11_ActiveEnter = active_hook;
                        ControlMachine_set_hooks(&stack_machine, &hooks, &log);

                        if (!ControlMachine_cycle(&stack_machine, NULL, 0u)) {
                            return 13;
                        }
                        if (
                            ControlMachine_current_state_id(&stack_machine) != CONTROL_MACHINE_STATE_P7_CONTROL_P4_IDLE ||
                            ControlMachine_vars(&stack_machine)->counter != (ControlMachineInt)1 ||
                            log.boot_calls != 1 ||
                            log.active_calls != 0
                        ) {
                            return 14;
                        }

                        if (!ControlMachine_cycle(&stack_machine, &start_event, 1u)) {
                            return 15;
                        }
                        if (
                            ControlMachine_current_state_id(&stack_machine) != CONTROL_MACHINE_STATE_P7_CONTROL_P6_ACTIVE_P4_WORK ||
                            ControlMachine_vars(&stack_machine)->ready != (ControlMachineInt)1 ||
                            ControlMachine_vars(&stack_machine)->counter != (ControlMachineInt)16 ||
                            log.active_calls != 1
                        ) {
                            return 16;
                        }

                        vars.counter = 7;
                        vars.ready = 1;
                        vars.gain = 3.0;
                        if (!ControlMachine_hot_start(
                                &stack_machine,
                                CONTROL_MACHINE_STATE_P7_CONTROL_P6_ACTIVE_P4_WORK,
                                &vars)) {
                            return 17;
                        }
                        if (
                            ControlMachine_current_state_id(&stack_machine) != CONTROL_MACHINE_STATE_P7_CONTROL_P6_ACTIVE_P4_WORK ||
                            ControlMachine_vars(&stack_machine)->counter != (ControlMachineInt)7 ||
                            log.boot_calls != 1 ||
                            log.active_calls != 1
                        ) {
                            return 18;
                        }

                        return 0;
                    }
                    """
                ),
                compile_definitions=[
                    "PYFCSTM_GENERATED_NO_HEAP",
                    "calloc=PYFCSTM_FORBIDDEN_CALLOC",
                    "free=PYFCSTM_FORBIDDEN_FREE",
                ],
            )
            assert run.returncode == 0, run.stderr

    def test_generated_machine_no_heap_profile_propagates_through_public_cmake_library(self):
        with render_c_artifacts(_representative_gate_dsl()) as artifacts:
            run = _compile_and_run_c_library_consumer(
                artifacts,
                "no_heap_public_cmake_library",
                textwrap.dedent(
                    r"""
                    #include "machine.h"

                    #if !defined(PYFCSTM_GENERATED_NO_HEAP)
                    #error "The no-heap profile must propagate to library consumers."
                    #endif

                    int main(void)
                    {
                        ControlMachine machine;
                        if (!ControlMachine_init(&machine)) {
                            return 10;
                        }
                        return 0;
                    }
                    """
                ),
                compile_definitions=["PYFCSTM_GENERATED_NO_HEAP"],
            )
            assert run.returncode == 0, run.stderr

    def test_generated_machine_no_heap_profile_removes_heap_api(self):
        with render_c_artifacts(_representative_gate_dsl()) as artifacts:
            run = _compile_and_run_c_harness(
                artifacts,
                "no_heap_forbidden_heap_api",
                textwrap.dedent(
                    r"""
                    #include "machine.h"

                    int main(void)
                    {
                        ControlMachine *machine = ControlMachine_create();
                        ControlMachine_destroy(machine);
                        return 0;
                    }
                    """
                ),
                compile_definitions=["PYFCSTM_GENERATED_NO_HEAP=1"],
                expect_build_success=False,
            )
            combined_output = run.stdout + run.stderr
            assert run.returncode != 0
            assert (
                "ControlMachine_create" in combined_output
                or "ControlMachine_destroy" in combined_output
            )

    def test_generated_hot_start_checks_stack_depth_before_path_write(self):
        with render_c_artifacts(_representative_gate_dsl()) as artifacts:
            with open(artifacts["machine_c_file"], "r", encoding="utf-8") as f:
                source = f.read()

            hot_start = source.index("int ControlMachine_hot_start(")
            path_loop = source.index("path_count = 0u;", hot_start)
            guard = source.index("if (path_count >=", path_loop)
            write = source.index("path_ids[path_count++]", path_loop)

            assert guard < write

    def test_generated_machine_c99_gate_runs_representative_model(self):
        with render_c_artifacts(_representative_gate_dsl()) as artifacts:
            run = _compile_and_run_c_harness(
                artifacts,
                "representative_c99_gate",
                textwrap.dedent(
                    r"""
                    #include "machine.h"

                    typedef struct HookLog {
                        int boot_calls;
                        int active_calls;
                    } HookLog;

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
                        if (
                            ctx->action_id == CONTROL_MACHINE_ACTION_P7_CONTROL_P6_ACTIVE_P11_ACTIVEENTER &&
                            ctx->state_id == CONTROL_MACHINE_STATE_P7_CONTROL_P6_ACTIVE
                        ) {
                            log->active_calls += 1;
                        }
                    }

                    int main(void)
                    {
                        ControlMachine machine;
                        ControlMachineHooks hooks = CONTROLMACHINE_HOOKS_INIT;
                        HookLog log = {0, 0};
                        static const ControlMachineEventId start_events[] = {
                            CONTROL_MACHINE_EVENT_P7_CONTROL_P4_IDLE_P5_START
                        };

                        if (!ControlMachine_init(&machine)) {
                            return 10;
                        }
                        hooks.on_p7_Control_p4_Boot = boot_hook;
                        hooks.on_p7_Control_p6_Active_p11_ActiveEnter = active_hook;
                        ControlMachine_set_hooks(&machine, &hooks, &log);

                        if (!ControlMachine_cycle(&machine, NULL, 0u)) {
                            return 11;
                        }
                        if (ControlMachine_current_state_id(&machine) != CONTROL_MACHINE_STATE_P7_CONTROL_P4_IDLE) {
                            return 12;
                        }
                        if (ControlMachine_vars(&machine)->counter != (ControlMachineInt)1) {
                            return 13;
                        }
                        if (log.boot_calls != 1 || log.active_calls != 0) {
                            return 14;
                        }

                        if (!ControlMachine_cycle(&machine, start_events, 1u)) {
                            return 15;
                        }
                        if (ControlMachine_current_state_id(&machine) != CONTROL_MACHINE_STATE_P7_CONTROL_P6_ACTIVE_P4_WORK) {
                            return 16;
                        }
                        if (
                            ControlMachine_vars(&machine)->ready != (ControlMachineInt)1 ||
                            ControlMachine_vars(&machine)->counter != (ControlMachineInt)16 ||
                            ControlMachine_vars(&machine)->gain != 2.0
                        ) {
                            return 17;
                        }
                        if (log.boot_calls != 1 || log.active_calls != 1) {
                            return 18;
                        }

                        return 0;
                    }
                    """
                ),
            )
            assert run.returncode == 0, run.stderr

    def test_generated_machine_cpp98_gate_runs_representative_model(self):
        with render_c_artifacts(_representative_gate_dsl()) as artifacts:
            run = _compile_and_run_cpp_harness(
                artifacts,
                "representative_cpp98_gate",
                textwrap.dedent(
                    r"""
                    #include "machine.h"

                    struct HookLog {
                        int boot_calls;
                        int active_calls;
                    };

                    static void boot_hook(
                        ControlMachine *machine,
                        const ControlMachineExecutionContext *ctx,
                        void *user_data
                    )
                    {
                        HookLog *log = static_cast<HookLog *>(user_data);
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
                        HookLog *log = static_cast<HookLog *>(user_data);
                        (void)machine;
                        if (
                            ctx->action_id == CONTROL_MACHINE_ACTION_P7_CONTROL_P6_ACTIVE_P11_ACTIVEENTER &&
                            ctx->state_id == CONTROL_MACHINE_STATE_P7_CONTROL_P6_ACTIVE
                        ) {
                            log->active_calls += 1;
                        }
                    }

                    int main()
                    {
                        ControlMachine machine;
                        ControlMachineHooks hooks = CONTROLMACHINE_HOOKS_INIT;
                        HookLog log = {0, 0};
                        static const ControlMachineEventId start_events[] = {
                            CONTROL_MACHINE_EVENT_P7_CONTROL_P4_IDLE_P5_START
                        };

                        if (!ControlMachine_init(&machine)) {
                            return 30;
                        }
                        hooks.on_p7_Control_p4_Boot = boot_hook;
                        hooks.on_p7_Control_p6_Active_p11_ActiveEnter = active_hook;
                        ControlMachine_set_hooks(&machine, &hooks, &log);

                        if (!ControlMachine_cycle(&machine, 0, 0u)) {
                            return 31;
                        }
                        if (ControlMachine_current_state_id(&machine) != CONTROL_MACHINE_STATE_P7_CONTROL_P4_IDLE) {
                            return 32;
                        }
                        if (!ControlMachine_cycle(&machine, start_events, 1u)) {
                            return 33;
                        }
                        if (ControlMachine_current_state_id(&machine) != CONTROL_MACHINE_STATE_P7_CONTROL_P6_ACTIVE_P4_WORK) {
                            return 34;
                        }
                        if (
                            ControlMachine_vars(&machine)->ready != (ControlMachineInt)1 ||
                            ControlMachine_vars(&machine)->counter != (ControlMachineInt)16 ||
                            ControlMachine_vars(&machine)->gain != 2.0
                        ) {
                            return 35;
                        }
                        if (log.boot_calls != 1 || log.active_calls != 1) {
                            return 36;
                        }

                        return 0;
                    }
                    """
                ),
            )
            assert run.returncode == 0, run.stderr


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
                'on_p4_Root_p1_B_p2_B1_p7_B1Enter': lambda ctx: calls.append(
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

                    int main(void)
                    {
                        RootMachine machine;
                        static const RootMachineEventId start_events[] = {
                            ROOT_MACHINE_EVENT_P4_ROOT_P4_IDLE_P5_START
                        };

                        if (!RootMachine_init(&machine)) {
                            return 10;
                        }
                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 11;
                        }
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_P4_ROOT_P4_IDLE) {
                            return 12;
                        }
                        if (RootMachine_vars(&machine)->counter != (RootMachineInt)1) {
                            return 13;
                        }

                        if (!RootMachine_cycle(&machine, start_events, 1u)) {
                            return 14;
                        }
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_P4_ROOT_P7_RUNNING) {
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
                            ROOT_MACHINE_STATE_P4_ROOT_P7_SERVICE,
                            &initial_vars
                        )) {
                            return 21;
                        }
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_P4_ROOT_P7_SERVICE) {
                            return 22;
                        }

                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 23;
                        }
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_P4_ROOT_P7_SERVICE_P5_READY) {
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
                            ctx->action_id == ROOT_MACHINE_ACTION_P4_ROOT_P8_ROOTINIT &&
                            ctx->state_id == ROOT_MACHINE_STATE_ROOT &&
                            ctx->action_stage_id == ROOT_MACHINE_STAGE_ENTER
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
                            ctx->action_id == ROOT_MACHINE_ACTION_P4_ROOT_P6_SYSTEM_P1_A_P6_AENTER &&
                            ctx->state_id == ROOT_MACHINE_STATE_P4_ROOT_P6_SYSTEM_P1_A &&
                            ctx->action_stage_id == ROOT_MACHINE_STAGE_ENTER
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

                        hooks.on_p4_Root_p8_RootInit = root_hook;
                        hooks.on_p4_Root_p6_System_p1_A_p6_AEnter = a_enter_hook;
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

                    typedef struct HookLog {
                        int total_calls;
                        int root_calls;
                        int a_calls;
                        int b_calls;
                    } HookLog;

                    static void platform_hook(
                        RootMachine *machine,
                        const RootMachineExecutionContext *ctx,
                        void *user_data
                    )
                    {
                        HookLog *log = (HookLog *)user_data;
                        (void)machine;

                        if (ctx->action_id != ROOT_MACHINE_ACTION_P4_ROOT_P12_PLATFORMINIT) {
                            log->total_calls = -100;
                            return;
                        }
                        if (ctx->abstract_target_id != ROOT_MACHINE_ACTION_P4_ROOT_P12_PLATFORMINIT) {
                            log->total_calls = -101;
                            return;
                        }
                        if (ctx->call_stage_id != ROOT_MACHINE_STAGE_ENTER) {
                            log->total_calls = -102;
                            return;
                        }

                        log->total_calls += 1;
                        if (ctx->state_id == ROOT_MACHINE_STATE_ROOT) {
                            log->root_calls += 1;
                        }
                        if (ctx->state_id == ROOT_MACHINE_STATE_P4_ROOT_P1_A) {
                            log->a_calls += 1;
                        }
                        if (ctx->state_id == ROOT_MACHINE_STATE_P4_ROOT_P1_B) {
                            log->b_calls += 1;
                        }
                    }

                    int main(void)
                    {
                        RootMachine machine;
                        RootMachineHooks hooks = ROOTMACHINE_HOOKS_INIT;
                        HookLog log = {0, 0, 0, 0};
                        static const RootMachineEventId go_events[] = {
                            ROOT_MACHINE_EVENT_P4_ROOT_P1_A_P2_GO
                        };

                        if (!RootMachine_init(&machine)) {
                            return 40;
                        }

                        hooks.on_p4_Root_p12_PlatformInit = platform_hook;
                        RootMachine_set_hooks(&machine, &hooks, &log);

                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 41;
                        }
                        if (log.total_calls != 2 || log.root_calls != 1 || log.a_calls != 1 || log.b_calls != 0) {
                            return 42;
                        }
                        if (RootMachine_vars(&machine)->trace != (RootMachineInt)1) {
                            return 43;
                        }

                        if (!RootMachine_cycle(&machine, go_events, 1u)) {
                            return 44;
                        }
                        if (log.total_calls != 3 || log.root_calls != 1 || log.a_calls != 1 || log.b_calls != 1) {
                            return 45;
                        }
                        if (RootMachine_vars(&machine)->trace != (RootMachineInt)11) {
                            return 46;
                        }
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_P4_ROOT_P1_B) {
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
                            ctx->action_id == ROOT_MACHINE_ACTION_P4_ROOT_P1_B_P2_B1_P7_B1ENTER &&
                            ctx->state_id == ROOT_MACHINE_STATE_P4_ROOT_P1_B_P2_B1
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
                            ROOT_MACHINE_EVENT_P4_ROOT_P1_A_P2_GO
                        };

                        if (!RootMachine_init(&machine)) {
                            return 50;
                        }

                        hooks.on_p4_Root_p1_B_p2_B1_p7_B1Enter = b1_enter_hook;
                        RootMachine_set_hooks(&machine, &hooks, &log);

                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 51;
                        }
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_P4_ROOT_P1_A) {
                            return 52;
                        }
                        if (RootMachine_vars(&machine)->counter != (RootMachineInt)1) {
                            return 53;
                        }

                        if (!RootMachine_cycle(&machine, go_events, 1u)) {
                            return 54;
                        }
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_P4_ROOT_P1_A) {
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

                    int main(void)
                    {
                        RootMachine machine;

                        if (!RootMachine_init(&machine)) {
                            return 60;
                        }
                        if (!RootMachine_cycle(&machine, NULL, 0u)) {
                            return 61;
                        }
                        if (RootMachine_current_state_id(&machine) != ROOT_MACHINE_STATE_p4_Root_p10_namespacez00005F) {
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


def _compile_and_run_harness_with_cmake(
    artifacts,
    stem,
    source_code,
    *,
    language,
    standard,
    compile_definitions=None,
    expect_build_success=True,
):
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
        ])
        if compile_definitions:
            cmake_lines.extend([
                'target_compile_definitions(',
                '    {target_name}'.format(target_name=stem),
                '    PRIVATE',
            ])
            cmake_lines.extend(
                '    {definition}'.format(definition=definition)
                for definition in compile_definitions
            )
            cmake_lines.extend([
                ')',
                '',
            ])
        cmake_lines.extend([
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
    build_result = subprocess.run(
        [cmake_executable, '--build', '.', '--config', 'Release'],
        cwd=build_dir,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if not expect_build_success:
        return build_result
    build_result.check_returncode()

    return subprocess.run(
        [_find_built_executable(build_dir, stem)],
        cwd=build_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _compile_and_run_c_harness(
    artifacts,
    stem,
    source_code,
    *,
    compile_definitions=None,
    expect_build_success=True,
):
    return _compile_and_run_harness_with_cmake(
        artifacts,
        stem,
        source_code,
        language='C',
        standard=None,
        compile_definitions=compile_definitions,
        expect_build_success=expect_build_success,
    )


def _compile_and_run_c_library_consumer(
    artifacts,
    stem,
    source_code,
    *,
    compile_definitions=None,
):
    cmake_executable = artifacts['cmake']
    if cmake_executable is None:
        pytest.skip('cmake is required for generated C template harness tests.')

    project_dir = os.path.join(artifacts['output_dir'], stem + '_cmake_project')
    build_dir = os.path.join(project_dir, 'build')
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(build_dir, exist_ok=True)

    source_file = os.path.join(project_dir, stem + '.c')
    cmakelists = os.path.join(project_dir, 'CMakeLists.txt')
    with open(source_file, 'w', encoding='utf-8') as f:
        f.write(source_code)
    with open(cmakelists, 'w', encoding='utf-8') as f:
        cmake_lines = [
            'cmake_minimum_required(VERSION 3.5)',
            'project({project_name} C)'.format(project_name=stem + '_project'),
            '',
            'add_library(machine STATIC "{machine_c_file}")'.format(
                machine_c_file=artifacts['machine_c_file'].replace('\\', '/')
            ),
            'target_include_directories(',
            '    machine',
            '    PUBLIC',
            '    "{machine_dir}"'.format(
                machine_dir=artifacts['output_dir'].replace('\\', '/')
            ),
            ')',
            'set_target_properties(',
            '    machine',
            '    PROPERTIES',
            '    C_STANDARD 99',
            '    C_STANDARD_REQUIRED YES',
            '    C_EXTENSIONS NO',
            ')',
            '',
        ]
        if compile_definitions:
            cmake_lines.extend([
                'target_compile_definitions(',
                '    machine',
                '    PUBLIC',
            ])
            cmake_lines.extend(
                '    {definition}'.format(definition=definition)
                for definition in compile_definitions
            )
            cmake_lines.extend([
                ')',
                '',
            ])
        cmake_lines.extend([
            'if (NOT WIN32)',
            '    target_link_libraries(machine PUBLIC m)',
            'endif()',
            '',
            'add_executable({target_name} "{source_file}")'.format(
                target_name=stem,
                source_file=source_file.replace('\\', '/'),
            ),
            'target_link_libraries({target_name} PRIVATE machine)'.format(
                target_name=stem
            ),
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


def _compile_and_run_cpp_harness(artifacts, stem, source_code, std='c++98'):
    return _compile_and_run_harness_with_cmake(
        artifacts,
        stem,
        source_code,
        language='CXX',
        standard=std,
    )
