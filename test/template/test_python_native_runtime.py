import importlib.util
import os.path
import textwrap
from contextlib import contextmanager
from tempfile import TemporaryDirectory

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.template import extract_template


@contextmanager
def _render_python_native_module(dsl_code, module_name='generated_python_native'):
    ast_node = parse_with_grammar_entry(
        textwrap.dedent(dsl_code).strip(),
        entry_name='state_machine_dsl',
    )
    model = parse_dsl_node_to_state_machine(ast_node)

    with TemporaryDirectory() as td:
        template_dir = extract_template('python_native', td)
        output_dir = os.path.join(td, 'out')
        StateMachineCodeRenderer(template_dir).render(model=model, output_dir=output_dir)

        spec = importlib.util.spec_from_file_location(
            module_name,
            os.path.join(output_dir, 'machine.py'),
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module


@pytest.mark.unittest
class TestPythonNativeBuiltinTemplate:
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

        with _render_python_native_module(dsl_code) as module:
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

    def test_generated_machine_supports_hot_start_and_abstract_handlers(self):
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

        with _render_python_native_module(dsl_code) as module:
            calls = []

            hot_machine = module.RootMachine(
                initial_state='Root.System',
                initial_vars={'counter': 10},
            )
            hot_machine.register_abstract_handler(
                'Root.System.A.AEnter',
                lambda ctx: calls.append(
                    ('hot', ctx.get_full_state_path(), ctx.action_stage, ctx.get_var('counter'))
                ),
            )

            assert hot_machine.current_state_path == ('Root', 'System')
            hot_machine.cycle()
            assert hot_machine.current_state_path == ('Root', 'System', 'A')
            assert hot_machine.vars == {'counter': 11}
            assert calls == [('hot', 'Root.System.A', 'enter', 10)]

            cold_machine = module.RootMachine()
            cold_machine.register_abstract_handler(
                'Root.RootInit',
                lambda ctx: calls.append(
                    ('cold', ctx.get_full_state_path(), ctx.action_stage, ctx.get_var('counter'))
                ),
            )

            cold_machine.cycle()
            assert cold_machine.current_state_path == ('Root', 'System', 'A')
            assert cold_machine.vars == {'counter': 1}
            assert calls[-1] == ('cold', 'Root', 'enter', 0)

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

        with _render_python_native_module(dsl_code) as module:
            class DerivedMachine(module.RootMachine):
                def __init__(self):
                    self.hook_calls = []
                    super().__init__()

                def _abstract_Root_RootInit(self, ctx):
                    self.hook_calls.append(
                        ('root', ctx.get_full_state_path(), ctx.action_stage, ctx.get_var('counter'))
                    )
                    self._vars['counter'] = self._vars['counter'] + 10

                def _abstract_Root_System_A_AEnter(self, ctx):
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
                'Root.RootInit': '_abstract_Root_RootInit',
                'Root.System.A.AEnter': '_abstract_Root_System_A_AEnter',
            }
            assert 'Original DSL Source' in module.__doc__
            assert 'Root-level hook used for runtime customization.' in module.RootMachine._abstract_Root_RootInit.__doc__
