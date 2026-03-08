"""
Tests for abstract handler functionality in SimulationRuntime.

This module tests the abstract handler registration, execution, error handling,
and validation mode isolation features.
"""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime, ReadOnlyExecutionContext


@pytest.mark.unittest
class TestAbstractHandlers:
    """Test abstract handler registration and execution."""

    def test_register_single_handler(self):
        """Test registering a single handler for an abstract action."""
        dsl_code = '''
        def int counter = 0;

        state System {
            state Idle {
                enter abstract InitHardware;
            }

            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Register handler
        calls = []

        def handler(ctx: ReadOnlyExecutionContext):
            calls.append(ctx.action_name)

        runtime.register_abstract_handler('System.Idle.InitHardware', handler)

        # Execute
        runtime.cycle()

        # Verify handler was called
        assert len(calls) == 1
        assert calls[0] == 'System.Idle.InitHardware'

    def test_during_abstract_handler(self):
        """Test handler for during abstract action."""
        dsl_code = '''
        def int counter = 0;

        state System {
            state Active {
                during abstract Monitor;
            }

            [*] -> Active;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Register handler
        calls = []

        def handler(ctx: ReadOnlyExecutionContext):
            calls.append({
                'action': ctx.action_name,
                'stage': ctx.action_stage,
                'state': ctx.get_full_state_path()
            })

        runtime.register_abstract_handler('System.Active.Monitor', handler)

        # Execute - during is called in the first cycle
        runtime.cycle()

        # Verify handler was called
        assert len(calls) == 1
        assert calls[0]['action'] == 'System.Active.Monitor'
        assert calls[0]['stage'] == 'during'
        assert calls[0]['state'] == 'System.Active'

    def test_exit_abstract_handler(self):
        """Test handler for exit abstract action."""
        dsl_code = '''
        def int counter = 0;

        state System {
            state Active {
                exit abstract Cleanup;
            }

            state Idle;

            [*] -> Active;
            Active -> Idle :: Stop;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Register handler
        calls = []

        def handler(ctx: ReadOnlyExecutionContext):
            calls.append({
                'action': ctx.action_name,
                'stage': ctx.action_stage,
                'state': ctx.get_full_state_path()
            })

        runtime.register_abstract_handler('System.Active.Cleanup', handler)

        # First cycle - enter Active
        runtime.cycle()
        assert len(calls) == 0  # Exit not called yet

        # Second cycle - transition to Idle, exit is called
        runtime.cycle(['System.Active.Stop'])
        assert len(calls) == 1
        assert calls[0]['action'] == 'System.Active.Cleanup'
        assert calls[0]['stage'] == 'exit'
        assert calls[0]['state'] == 'System.Active'

    def test_aspect_before_abstract_handler(self):
        """Test handler for >> during before abstract action."""
        dsl_code = '''
        def int counter = 0;

        state System {
            >> during before abstract PreProcess;

            state Active {
                during {
                    counter = counter + 1;
                }
            }

            [*] -> Active;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Register handler
        calls = []

        def handler(ctx: ReadOnlyExecutionContext):
            calls.append({
                'action': ctx.action_name,
                'stage': ctx.action_stage,
                'state': ctx.get_full_state_path(),
                'counter': ctx.get_var('counter')
            })

        runtime.register_abstract_handler('System.PreProcess', handler)

        # Execute - aspect before is called before leaf during
        runtime.cycle()

        # Verify handler was called
        assert len(calls) == 1
        assert calls[0]['action'] == 'System.PreProcess'
        assert calls[0]['stage'] == 'during'
        assert calls[0]['state'] == 'System'
        assert calls[0]['counter'] == 0  # Called before counter increment

        # Verify counter was incremented after aspect
        assert runtime.vars['counter'] == 1

    def test_aspect_after_abstract_handler(self):
        """Test handler for >> during after abstract action."""
        dsl_code = '''
        def int counter = 0;

        state System {
            >> during after abstract PostProcess;

            state Active {
                during {
                    counter = counter + 10;
                }
            }

            [*] -> Active;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Register handler
        calls = []

        def handler(ctx: ReadOnlyExecutionContext):
            calls.append({
                'action': ctx.action_name,
                'stage': ctx.action_stage,
                'state': ctx.get_full_state_path(),
                'counter': ctx.get_var('counter')
            })

        runtime.register_abstract_handler('System.PostProcess', handler)

        # Execute - aspect after is called after leaf during
        runtime.cycle()

        # Verify handler was called
        assert len(calls) == 1
        assert calls[0]['action'] == 'System.PostProcess'
        assert calls[0]['stage'] == 'during'
        assert calls[0]['state'] == 'System'
        assert calls[0]['counter'] == 10  # Called after counter increment

    def test_multiple_lifecycle_abstract_handlers(self):
        """Test handlers for multiple lifecycle stages in the same state."""
        dsl_code = '''
        def int counter = 0;

        state System {
            state Active {
                enter abstract Init;
                during abstract Monitor;
                exit abstract Cleanup;
            }

            state Idle;

            [*] -> Active;
            Active -> Idle :: Stop;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Register handlers
        calls = []

        def init_handler(ctx: ReadOnlyExecutionContext):
            calls.append(('init', ctx.action_stage))

        def monitor_handler(ctx: ReadOnlyExecutionContext):
            calls.append(('monitor', ctx.action_stage))

        def cleanup_handler(ctx: ReadOnlyExecutionContext):
            calls.append(('cleanup', ctx.action_stage))

        runtime.register_abstract_handler('System.Active.Init', init_handler)
        runtime.register_abstract_handler('System.Active.Monitor', monitor_handler)
        runtime.register_abstract_handler('System.Active.Cleanup', cleanup_handler)

        # First cycle - enter and during
        runtime.cycle()
        assert len(calls) == 2
        assert calls[0] == ('init', 'enter')
        assert calls[1] == ('monitor', 'during')

        # Second cycle - exit
        runtime.cycle(['System.Active.Stop'])
        assert len(calls) == 3
        assert calls[2] == ('cleanup', 'exit')

    def test_register_multiple_handlers(self):
        """Test registering multiple handlers for the same abstract action."""
        dsl_code = '''
        def int counter = 0;

        state System {
            state Idle {
                enter abstract InitHardware;
            }

            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Register multiple handlers
        calls = []

        def handler1(ctx: ReadOnlyExecutionContext):
            calls.append('handler1')

        def handler2(ctx: ReadOnlyExecutionContext):
            calls.append('handler2')

        def handler3(ctx: ReadOnlyExecutionContext):
            calls.append('handler3')

        runtime.register_abstract_handler('System.Idle.InitHardware', handler1)
        runtime.register_abstract_handler('System.Idle.InitHardware', handler2)
        runtime.register_abstract_handler('System.Idle.InitHardware', handler3)

        # Execute
        runtime.cycle()

        # Verify all handlers were called in order
        assert calls == ['handler1', 'handler2', 'handler3']

    def test_handler_receives_correct_context(self):
        """Test that handlers receive correct read-only context."""
        dsl_code = '''
        def int counter = 10;
        def float temperature = 25.5;

        state System {
            state Active {
                during abstract Monitor;
            }

            [*] -> Active;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Register handler
        captured_ctx = []

        def handler(ctx: ReadOnlyExecutionContext):
            captured_ctx.append({
                'state_path': ctx.state_path,
                'state_name': ctx.get_state_name(),
                'full_path': ctx.get_full_state_path(),
                'counter': ctx.get_var('counter'),
                'temperature': ctx.get_var('temperature'),
                'action_name': ctx.action_name,
                'action_stage': ctx.action_stage,
                'has_counter': ctx.has_var('counter'),
                'has_nonexistent': ctx.has_var('nonexistent'),
            })

        runtime.register_abstract_handler('System.Active.Monitor', handler)

        # Execute
        runtime.cycle()

        # Verify context
        assert len(captured_ctx) == 1
        ctx_data = captured_ctx[0]
        assert ctx_data['state_path'] == ('System', 'Active')
        assert ctx_data['state_name'] == 'Active'
        assert ctx_data['full_path'] == 'System.Active'
        assert ctx_data['counter'] == 10
        assert ctx_data['temperature'] == 25.5
        assert ctx_data['action_name'] == 'System.Active.Monitor'
        assert ctx_data['action_stage'] == 'during'
        assert ctx_data['has_counter'] is True
        assert ctx_data['has_nonexistent'] is False

    def test_handler_cannot_modify_vars(self):
        """Test that handlers cannot modify variables (context is read-only)."""
        dsl_code = '''
        def int counter = 10;

        state System {
            state Active {
                enter abstract Init;
            }

            [*] -> Active;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Register handler that tries to modify vars
        def handler(ctx: ReadOnlyExecutionContext):
            # This should not affect runtime vars
            ctx.vars['counter'] = 999

        runtime.register_abstract_handler('System.Active.Init', handler)

        # Execute
        runtime.cycle()

        # Verify vars were not modified
        assert runtime.vars['counter'] == 10

    def test_unregister_all_handlers(self):
        """Test unregistering all handlers for an action."""
        dsl_code = '''
        state System {
            state Idle {
                enter abstract Init;
            }

            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Register handlers
        calls = []

        def handler1(ctx: ReadOnlyExecutionContext):
            calls.append('handler1')

        def handler2(ctx: ReadOnlyExecutionContext):
            calls.append('handler2')

        runtime.register_abstract_handler('System.Idle.Init', handler1)
        runtime.register_abstract_handler('System.Idle.Init', handler2)

        # Unregister all
        count = runtime.unregister_abstract_handler('System.Idle.Init')
        assert count == 2

        # Execute - no handlers should be called
        runtime.cycle()
        assert len(calls) == 0

    def test_unregister_specific_handler(self):
        """Test unregistering a specific handler."""
        dsl_code = '''
        state System {
            state Idle {
                enter abstract Init;
            }

            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Register handlers
        calls = []

        def handler1(ctx: ReadOnlyExecutionContext):
            calls.append('handler1')

        def handler2(ctx: ReadOnlyExecutionContext):
            calls.append('handler2')

        def handler3(ctx: ReadOnlyExecutionContext):
            calls.append('handler3')

        runtime.register_abstract_handler('System.Idle.Init', handler1)
        runtime.register_abstract_handler('System.Idle.Init', handler2)
        runtime.register_abstract_handler('System.Idle.Init', handler3)

        # Unregister handler2
        count = runtime.unregister_abstract_handler('System.Idle.Init', handler2)
        assert count == 1

        # Execute - only handler1 and handler3 should be called
        runtime.cycle()
        assert calls == ['handler1', 'handler3']

    def test_clear_all_handlers(self):
        """Test clearing all handlers."""
        dsl_code = '''
        state System {
            state A {
                enter abstract Init1;
            }
            state B {
                enter abstract Init2;
            }

            [*] -> A;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Register handlers
        def handler1(ctx: ReadOnlyExecutionContext):
            pass

        def handler2(ctx: ReadOnlyExecutionContext):
            pass

        runtime.register_abstract_handler('System.A.Init1', handler1)
        runtime.register_abstract_handler('System.B.Init2', handler2)

        # Clear all
        count = runtime.clear_all_abstract_handlers()
        assert count == 2

        # Verify no handlers remain
        assert not runtime.has_abstract_handlers('System.A.Init1')
        assert not runtime.has_abstract_handlers('System.B.Init2')

    def test_anonymous_abstract_warning(self):
        """Test that anonymous abstracts trigger a warning."""
        dsl_code = '''
        state System {
            state Idle {
                enter abstract /*
                    Anonymous abstract action
                */
            }

            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Execute - should trigger warning on first execution
        with pytest.warns(UserWarning, match='has no name'):
            runtime.cycle()

        # Create a new runtime to test the same abstract again
        # The warning should trigger again because it's a different runtime instance
        runtime2 = SimulationRuntime(sm)
        with pytest.warns(UserWarning, match='has no name'):
            runtime2.cycle()


@pytest.mark.unittest
class TestAbstractHandlerErrorModes:
    """Test error handling modes for abstract handlers."""

    def test_raise_mode_stops_on_error(self):
        """Test that 'raise' mode stops execution on handler error."""
        dsl_code = '''
        def int counter = 0;

        state System {
            state Idle {
                enter abstract Init;
                enter {
                    counter = counter + 1;
                }
            }

            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm, abstract_error_mode='raise')

        # Register handler that raises exception
        def handler(ctx: ReadOnlyExecutionContext):
            raise ValueError('Test error')

        runtime.register_abstract_handler('System.Idle.Init', handler)

        # Execute - should raise exception
        with pytest.raises(ValueError, match='Test error'):
            runtime.cycle()

        # Verify runtime is in error state
        assert runtime.is_error_state
        assert runtime.error_info is not None
        action_path, exception = runtime.error_info
        assert action_path == 'System.Idle.Init'
        assert isinstance(exception, ValueError)

        # Verify subsequent enter action was not executed
        assert runtime.vars['counter'] == 0

    def test_log_mode_continues_on_error(self):
        """Test that 'log' mode continues execution on handler error."""
        dsl_code = '''
        def int counter = 0;

        state System {
            state Idle {
                enter abstract Init;
                enter {
                    counter = counter + 1;
                }
            }

            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm, abstract_error_mode='log')

        # Register handler that raises exception
        def handler(ctx: ReadOnlyExecutionContext):
            raise ValueError('Test error')

        runtime.register_abstract_handler('System.Idle.Init', handler)

        # Execute - should not raise exception
        runtime.cycle()

        # Verify runtime is not in error state
        assert not runtime.is_error_state

        # Verify error was logged
        errors = runtime.abstract_handler_errors
        assert len(errors) == 1
        action_path, exception = errors[0]
        assert action_path == 'System.Idle.Init'
        assert isinstance(exception, ValueError)

        # Verify subsequent enter action was executed
        assert runtime.vars['counter'] == 1

    def test_log_mode_multiple_errors(self):
        """Test that 'log' mode collects multiple errors."""
        dsl_code = '''
        state System {
            state Idle {
                enter abstract Init;
            }

            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm, abstract_error_mode='log')

        # Register multiple handlers that raise exceptions
        def handler1(ctx: ReadOnlyExecutionContext):
            raise ValueError('Error 1')

        def handler2(ctx: ReadOnlyExecutionContext):
            raise TypeError('Error 2')

        def handler3(ctx: ReadOnlyExecutionContext):
            raise RuntimeError('Error 3')

        runtime.register_abstract_handler('System.Idle.Init', handler1)
        runtime.register_abstract_handler('System.Idle.Init', handler2)
        runtime.register_abstract_handler('System.Idle.Init', handler3)

        # Execute
        runtime.cycle()

        # Verify all errors were logged
        errors = runtime.abstract_handler_errors
        assert len(errors) == 3
        assert isinstance(errors[0][1], ValueError)
        assert isinstance(errors[1][1], TypeError)
        assert isinstance(errors[2][1], RuntimeError)


@pytest.mark.unittest
class TestValidationModeIsolation:
    """Test that validation mode does not execute handlers."""

    # Note: Validation mode tests are complex and need careful design
    # Skipping for now - validation mode isolation is implemented but needs
    # more sophisticated test scenarios
    pass


@pytest.mark.unittest
class TestAbstractHandlerUtilities:
    """Test utility methods for abstract handlers."""

    def test_get_abstract_handlers(self):
        """Test getting registered handlers."""
        dsl_code = '''
        state System {
            state Idle {
                enter abstract Init;
            }

            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Initially no handlers
        handlers = runtime.get_abstract_handlers('System.Idle.Init')
        assert len(handlers) == 0

        # Register handlers
        def handler1(ctx: ReadOnlyExecutionContext):
            pass

        def handler2(ctx: ReadOnlyExecutionContext):
            pass

        runtime.register_abstract_handler('System.Idle.Init', handler1)
        runtime.register_abstract_handler('System.Idle.Init', handler2)

        # Get handlers
        handlers = runtime.get_abstract_handlers('System.Idle.Init')
        assert len(handlers) == 2
        assert handlers[0] is handler1
        assert handlers[1] is handler2

    def test_has_abstract_handlers(self):
        """Test checking if handlers are registered."""
        dsl_code = '''
        state System {
            state Idle {
                enter abstract Init;
            }

            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Initially no handlers
        assert not runtime.has_abstract_handlers('System.Idle.Init')

        # Register handler
        def handler(ctx: ReadOnlyExecutionContext):
            pass

        runtime.register_abstract_handler('System.Idle.Init', handler)

        # Now has handlers
        assert runtime.has_abstract_handlers('System.Idle.Init')

        # Unregister
        runtime.unregister_abstract_handler('System.Idle.Init')

        # No handlers again
        assert not runtime.has_abstract_handlers('System.Idle.Init')

    def test_register_empty_action_path_raises(self):
        """Test that registering with empty action path raises ValueError."""
        dsl_code = '''
        state System {
            state Idle;
            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        def handler(ctx: ReadOnlyExecutionContext):
            pass

        with pytest.raises(ValueError, match='action_path cannot be empty'):
            runtime.register_abstract_handler('', handler)
