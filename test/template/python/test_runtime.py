import ast
import importlib.util
import os.path
import shutil
import subprocess
import sys
import textwrap
from contextlib import contextmanager
from tempfile import TemporaryDirectory

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.template import extract_template


@contextmanager
def _render_python_artifacts(dsl_code, module_name='generated_python'):
    ast_node = parse_with_grammar_entry(
        textwrap.dedent(dsl_code).strip(),
        entry_name='state_machine_dsl',
    )
    model = parse_dsl_node_to_state_machine(ast_node)

    with TemporaryDirectory() as td:
        template_dir = extract_template('python', td)
        output_dir = os.path.join(td, 'out')
        StateMachineCodeRenderer(template_dir).render(model=model, output_dir=output_dir)

        spec = importlib.util.spec_from_file_location(
            module_name,
            os.path.join(output_dir, 'machine.py'),
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield {
            'module': module,
            'output_dir': output_dir,
            'machine_file': os.path.join(output_dir, 'machine.py'),
            'readme_file': os.path.join(output_dir, 'README.md'),
            'readme_zh_file': os.path.join(output_dir, 'README_zh.md'),
        }


@contextmanager
def _render_python_module(dsl_code, module_name='generated_python'):
    with _render_python_artifacts(dsl_code, module_name=module_name) as artifacts:
        yield artifacts['module']


@pytest.mark.unittest
class TestPythonBuiltinTemplate:
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

        with _render_python_module(dsl_code) as module:
            machine = module.SystemMachine()

            assert machine.current_state_path == ('System',)
            assert machine.vars == {'counter': 0}

            machine.cycle()
            assert machine.current_state_path == ('System', 'Idle')
            assert machine.vars == {'counter': 1}

            machine.cycle(['Start'])
            assert machine.current_state_path == ('System', 'Running')
            assert machine.vars == {'counter': 111}
            assert module.SystemMachine.DSL_SOURCE.strip().startswith('def int counter = 0;')
            assert 'System.Idle' in module.SystemMachine.STATE_PATHS

    def test_generated_machine_supports_hot_start_and_subclass_hooks(self):
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

        with _render_python_module(dsl_code) as module:
            class HotMachine(module.RootMachine):
                def __init__(self):
                    self.calls = []
                    super().__init__(
                        initial_state='Root.System',
                        initial_vars={'counter': 10},
                    )

                def _abstract_hook_Root_System_A_AEnter(self, ctx):
                    self.calls.append(
                        ('hot', ctx.get_full_state_path(), ctx.action_stage, ctx.get_var('counter'))
                    )

            hot_machine = HotMachine()
            assert hot_machine.current_state_path == ('Root', 'System')
            hot_machine.cycle()
            assert hot_machine.current_state_path == ('Root', 'System', 'A')
            assert hot_machine.vars == {'counter': 11}
            assert hot_machine.calls == [('hot', 'Root.System.A', 'enter', 10)]

            class ColdMachine(module.RootMachine):
                def __init__(self):
                    self.calls = []
                    super().__init__()

                def _abstract_hook_Root_RootInit(self, ctx):
                    self.calls.append(
                        ('cold', ctx.get_full_state_path(), ctx.action_stage, ctx.get_var('counter'))
                    )

            cold_machine = ColdMachine()
            cold_machine.cycle()
            assert cold_machine.current_state_path == ('Root', 'System', 'A')
            assert cold_machine.vars == {'counter': 1}
            assert cold_machine.calls == [('cold', 'Root', 'enter', 0)]

    def test_generated_machine_supports_subclass_hook_override(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            enter abstract RootInit /*
                Root-level hook used for runtime customization.
            */
            state System {
                state A {
                    enter abstract AEnter /*
                        Enter hook for state A.
                    */
                    during { counter = counter + 2; }
                }
                [*] -> A;
            }
            [*] -> System;
        }
        """

        with _render_python_module(dsl_code) as module:
            class DerivedMachine(module.RootMachine):
                def __init__(self):
                    self.hook_calls = []
                    super().__init__()

                def _abstract_hook_Root_RootInit(self, ctx):
                    self.hook_calls.append(
                        ('root', ctx.get_full_state_path(), ctx.action_stage, ctx.get_var('counter'))
                    )
                    self._vars['counter'] = self._vars['counter'] + 10

                def _abstract_hook_Root_System_A_AEnter(self, ctx):
                    self.hook_calls.append(
                        ('a_enter', ctx.get_full_state_path(), ctx.action_stage, ctx.get_var('counter'))
                    )
                    self._vars['counter'] = self._vars['counter'] + 3

            machine = DerivedMachine()
            machine.cycle()

            assert machine.current_state_path == ('Root', 'System', 'A')
            assert machine.vars == {'counter': 15}
            assert machine.hook_calls == [
                ('root', 'Root', 'enter', 0),
                ('a_enter', 'Root.System.A', 'enter', 10),
            ]
            assert module.RootMachine.get_abstract_hook_map() == {
                'Root.RootInit': '_abstract_hook_Root_RootInit',
                'Root.System.A.AEnter': '_abstract_hook_Root_System_A_AEnter',
            }
            assert 'Original DSL Source' in module.__doc__
            assert (
                'Root-level hook used for runtime customization.'
                in module.RootMachine._abstract_hook_Root_RootInit.__doc__
            )

    def test_generated_machine_executes_protected_hooks_for_all_abstract_stages(self):
        dsl_code = """
        def int trace = 0;
        state Root {
            enter abstract RootEnter;
            >> during before abstract RootAspectBefore;
            >> during after abstract RootAspectAfter;

            state Parent {
                enter abstract ParentEnter;
                during before abstract ParentBefore;
                during after abstract ParentAfter;
                exit abstract ParentExit;

                state A {
                    enter abstract AEnter;
                    during abstract ADuring;
                    exit abstract AExit;
                }

                state B {
                    enter abstract BEnter;
                    during abstract BDuring;
                    exit abstract BExit;
                }

                [*] -> A;
                A -> B :: Next;
                B -> [*] :: Stop;
            }

            [*] -> Parent;
            Parent -> [*] :: Stop;
        }
        """

        with _render_python_module(dsl_code) as module:
            calls = []
            hook_map = module.RootMachine.get_abstract_hook_map()
            assert hook_map == {
                'Root.RootEnter': '_abstract_hook_Root_RootEnter',
                'Root.RootAspectBefore': '_abstract_hook_Root_RootAspectBefore',
                'Root.RootAspectAfter': '_abstract_hook_Root_RootAspectAfter',
                'Root.Parent.ParentEnter': '_abstract_hook_Root_Parent_ParentEnter',
                'Root.Parent.ParentBefore': '_abstract_hook_Root_Parent_ParentBefore',
                'Root.Parent.ParentAfter': '_abstract_hook_Root_Parent_ParentAfter',
                'Root.Parent.ParentExit': '_abstract_hook_Root_Parent_ParentExit',
                'Root.Parent.A.AEnter': '_abstract_hook_Root_Parent_A_AEnter',
                'Root.Parent.A.ADuring': '_abstract_hook_Root_Parent_A_ADuring',
                'Root.Parent.A.AExit': '_abstract_hook_Root_Parent_A_AExit',
                'Root.Parent.B.BEnter': '_abstract_hook_Root_Parent_B_BEnter',
                'Root.Parent.B.BDuring': '_abstract_hook_Root_Parent_B_BDuring',
                'Root.Parent.B.BExit': '_abstract_hook_Root_Parent_B_BExit',
            }

            class DerivedMachine(module.RootMachine):
                def _abstract_hook_Root_RootEnter(self, ctx):
                    calls.append(('root_enter', ctx.action_name, ctx.action_stage, ctx.get_full_state_path()))
                    self._vars['trace'] = self._vars['trace'] + 1

                def _abstract_hook_Root_RootAspectBefore(self, ctx):
                    calls.append(
                        ('root_aspect_before', ctx.action_name, ctx.action_stage, ctx.get_full_state_path())
                    )
                    self._vars['trace'] = self._vars['trace'] + 10

                def _abstract_hook_Root_RootAspectAfter(self, ctx):
                    calls.append(
                        ('root_aspect_after', ctx.action_name, ctx.action_stage, ctx.get_full_state_path())
                    )
                    self._vars['trace'] = self._vars['trace'] + 100

                def _abstract_hook_Root_Parent_ParentEnter(self, ctx):
                    calls.append(('parent_enter', ctx.action_name, ctx.action_stage, ctx.get_full_state_path()))
                    self._vars['trace'] = self._vars['trace'] + 1000

                def _abstract_hook_Root_Parent_ParentBefore(self, ctx):
                    calls.append(('parent_before', ctx.action_name, ctx.action_stage, ctx.get_full_state_path()))
                    self._vars['trace'] = self._vars['trace'] + 10000

                def _abstract_hook_Root_Parent_ParentAfter(self, ctx):
                    calls.append(('parent_after', ctx.action_name, ctx.action_stage, ctx.get_full_state_path()))
                    self._vars['trace'] = self._vars['trace'] + 100000

                def _abstract_hook_Root_Parent_ParentExit(self, ctx):
                    calls.append(('parent_exit', ctx.action_name, ctx.action_stage, ctx.get_full_state_path()))
                    self._vars['trace'] = self._vars['trace'] + 1000000

                def _abstract_hook_Root_Parent_A_AEnter(self, ctx):
                    calls.append(('a_enter', ctx.action_name, ctx.action_stage, ctx.get_full_state_path()))
                    self._vars['trace'] = self._vars['trace'] + 10000000

                def _abstract_hook_Root_Parent_A_ADuring(self, ctx):
                    calls.append(('a_during', ctx.action_name, ctx.action_stage, ctx.get_full_state_path()))
                    self._vars['trace'] = self._vars['trace'] + 100000000

                def _abstract_hook_Root_Parent_A_AExit(self, ctx):
                    calls.append(('a_exit', ctx.action_name, ctx.action_stage, ctx.get_full_state_path()))
                    self._vars['trace'] = self._vars['trace'] + 1000000000

                def _abstract_hook_Root_Parent_B_BEnter(self, ctx):
                    calls.append(('b_enter', ctx.action_name, ctx.action_stage, ctx.get_full_state_path()))
                    self._vars['trace'] = self._vars['trace'] + 2000000000

                def _abstract_hook_Root_Parent_B_BDuring(self, ctx):
                    calls.append(('b_during', ctx.action_name, ctx.action_stage, ctx.get_full_state_path()))
                    self._vars['trace'] = self._vars['trace'] + 3000000000

                def _abstract_hook_Root_Parent_B_BExit(self, ctx):
                    calls.append(('b_exit', ctx.action_name, ctx.action_stage, ctx.get_full_state_path()))
                    self._vars['trace'] = self._vars['trace'] + 4000000000

            machine = DerivedMachine()

            machine.cycle()
            assert machine.current_state_path == ('Root', 'Parent', 'A')
            assert machine.vars == {'trace': 110011111}

            machine.cycle(['Root.Parent.A.Next'])
            assert machine.current_state_path == ('Root', 'Parent', 'B')
            assert machine.vars == {'trace': 6110011221}

            machine.cycle(['Root.Parent.B.Stop', 'Root.Parent.Stop'])
            assert machine.is_ended is True
            assert machine.current_state_path is None
            assert machine.vars == {'trace': 10111111221}

            assert calls == [
                ('root_enter', 'Root.RootEnter', 'enter', 'Root'),
                ('parent_enter', 'Root.Parent.ParentEnter', 'enter', 'Root.Parent'),
                ('parent_before', 'Root.Parent.ParentBefore', 'during', 'Root.Parent'),
                ('a_enter', 'Root.Parent.A.AEnter', 'enter', 'Root.Parent.A'),
                ('root_aspect_before', 'Root.RootAspectBefore', 'during', 'Root'),
                ('a_during', 'Root.Parent.A.ADuring', 'during', 'Root.Parent.A'),
                ('root_aspect_after', 'Root.RootAspectAfter', 'during', 'Root'),
                ('a_exit', 'Root.Parent.A.AExit', 'exit', 'Root.Parent.A'),
                ('b_enter', 'Root.Parent.B.BEnter', 'enter', 'Root.Parent.B'),
                ('root_aspect_before', 'Root.RootAspectBefore', 'during', 'Root'),
                ('b_during', 'Root.Parent.B.BDuring', 'during', 'Root.Parent.B'),
                ('root_aspect_after', 'Root.RootAspectAfter', 'during', 'Root'),
                ('b_exit', 'Root.Parent.B.BExit', 'exit', 'Root.Parent.B'),
                ('parent_after', 'Root.Parent.ParentAfter', 'during', 'Root.Parent'),
                ('parent_exit', 'Root.Parent.ParentExit', 'exit', 'Root.Parent'),
            ]

    def test_generated_machine_reuses_same_protected_hook_for_abstract_refs(self):
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

        with _render_python_module(dsl_code) as module:
            calls = []
            hook_map = module.RootMachine.get_abstract_hook_map()

            class DerivedMachine(module.RootMachine):
                def _abstract_hook_Root_PlatformInit(self, ctx):
                    calls.append((ctx.action_name, ctx.action_stage, ctx.get_full_state_path()))
                    self._vars['trace'] = self._vars['trace'] + 100

            machine = DerivedMachine()

            machine.cycle()
            assert machine.current_state_path == ('Root', 'A')
            assert machine.vars == {'trace': 201}

            machine.cycle(['Root.A.Go'])
            assert machine.current_state_path == ('Root', 'B')
            assert machine.vars == {'trace': 311}

            assert hook_map == {'Root.PlatformInit': '_abstract_hook_Root_PlatformInit'}
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

        with _render_python_artifacts(dsl_code) as artifacts:
            with open(artifacts['readme_file'], 'r', encoding='utf-8') as f:
                readme = f.read()
            with open(artifacts['readme_zh_file'], 'r', encoding='utf-8') as f:
                readme_zh = f.read()

            assert os.path.isfile(artifacts['readme_file'])
            assert os.path.isfile(artifacts['readme_zh_file'])
            assert '# RootMachine' in readme
            assert 'class CustomMachine(RootMachine)' in readme
            assert '_abstract_hook_Root_RootInit' in readme
            assert '_abstract_hook_Root_System_A_AEnter' in readme
            assert '| DSL action path | Hook method | Owner state | Stage |' in readme
            assert 'Abstract hooks are read-only extension points' in readme
            assert 'do not mutate persistent' in readme
            assert '可覆写的 Abstract Hook 清单' in readme_zh
            assert '_abstract_hook_Root_RootInit' in readme_zh
            assert '_abstract_hook_Root_System_A_AEnter' in readme_zh
            assert 'abstract hook' in readme_zh
            assert '修改状态机持久变量' in readme_zh

    def test_generated_machine_source_stays_platform_neutral_and_python37_compatible(self):
        dsl_code = """
        def int counter = 0;
        state Root {
            state Idle {
                during { counter = counter + 1; }
            }
            [*] -> Idle;
        }
        """

        with _render_python_artifacts(dsl_code) as artifacts:
            with open(artifacts['machine_file'], 'r', encoding='utf-8') as f:
                source = f.read()

            if sys.version_info >= (3, 8):
                tree = ast.parse(source, feature_version=(3, 7))
            else:
                tree = ast.parse(source)
            imported_modules = set()
            for node in tree.body:
                if isinstance(node, ast.Import):
                    imported_modules.update(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom):
                    imported_modules.add(node.module)

            assert imported_modules <= {'__future__', 'math', 'dataclasses', 'typing'}
            assert 'msvcrt' not in source
            assert 'fcntl' not in source
            assert 'subprocess' not in source
            assert 'pathlib' not in source

            ruff_executable = shutil.which('ruff')
            if ruff_executable is None:
                pytest.skip('ruff is not installed in this test environment')

            subprocess.run(
                [ruff_executable, 'format', '--check', artifacts['machine_file']],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
