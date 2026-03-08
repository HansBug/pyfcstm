"""
Tests for abstract handler decorator functionality.

This module tests the decorator-based handler registration system that allows
users to organize handlers in classes.
"""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime, ReadOnlyExecutionContext, abstract_handler


@pytest.mark.unittest
class TestAbstractHandlerDecorator:
    """Test decorator-based handler registration."""

    def test_basic_decorator_registration(self):
        """Test basic decorator usage with single handler."""
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

        # Define handler class
        class MyHandlers:
            def __init__(self):
                self.calls = []

            @abstract_handler('System.Idle.InitHardware')
            def handle_init(self, ctx: ReadOnlyExecutionContext):
                self.calls.append(ctx.action_name)

        # Register handlers from object
        handlers = MyHandlers()
        count = runtime.register_handlers_from_object(handlers)

        assert count == 1

        # Execute
        runtime.cycle()

        # Verify handler was called
        assert len(handlers.calls) == 1
        assert handlers.calls[0] == 'System.Idle.InitHardware'

    def test_multiple_handlers_in_class(self):
        """Test class with multiple decorated handlers."""
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

        # Define handler class with multiple handlers
        class SystemHandlers:
            def __init__(self):
                self.init_called = False
                self.monitor_called = False
                self.cleanup_called = False

            @abstract_handler('System.Active.Init')
            def handle_init(self, ctx: ReadOnlyExecutionContext):
                self.init_called = True

            @abstract_handler('System.Active.Monitor')
            def handle_monitor(self, ctx: ReadOnlyExecutionContext):
                self.monitor_called = True

            @abstract_handler('System.Active.Cleanup')
            def handle_cleanup(self, ctx: ReadOnlyExecutionContext):
                self.cleanup_called = True

            def helper_method(self):
                # Not decorated, should not be registered
                pass

        # Register handlers
        handlers = SystemHandlers()
        count = runtime.register_handlers_from_object(handlers)

        assert count == 3

        # First cycle - init and monitor
        runtime.cycle()
        assert handlers.init_called is True
        assert handlers.monitor_called is True
        assert handlers.cleanup_called is False

        # Second cycle - cleanup
        runtime.cycle(['System.Active.Stop'])
        assert handlers.cleanup_called is True

    def test_handler_with_state(self):
        """Test handler class maintaining state across calls."""
        dsl_code = '''
        def int counter = 0;

        state System {
            state Active {
                during {
                    counter = counter + 1;
                }
                during abstract Monitor;
            }

            [*] -> Active;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Handler class with state
        class StatefulHandler:
            def __init__(self):
                self.call_count = 0
                self.counter_values = []

            @abstract_handler('System.Active.Monitor')
            def monitor(self, ctx: ReadOnlyExecutionContext):
                self.call_count += 1
                self.counter_values.append(ctx.get_var('counter'))

        # Register and execute multiple cycles
        handler = StatefulHandler()
        runtime.register_handlers_from_object(handler)

        for i in range(5):
            runtime.cycle()

        # Verify state was maintained
        assert handler.call_count == 5
        assert handler.counter_values == [1, 2, 3, 4, 5]

    def test_multiple_objects_registration(self):
        """Test registering handlers from multiple objects."""
        dsl_code = '''
        def int counter = 0;

        state System {
            state Active {
                enter abstract Init;
                during abstract Monitor;
            }

            [*] -> Active;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # First handler class
        class InitHandlers:
            def __init__(self):
                self.init_calls = []

            @abstract_handler('System.Active.Init')
            def handle_init(self, ctx: ReadOnlyExecutionContext):
                self.init_calls.append('init1')

        # Second handler class
        class MonitorHandlers:
            def __init__(self):
                self.monitor_calls = []

            @abstract_handler('System.Active.Monitor')
            def handle_monitor(self, ctx: ReadOnlyExecutionContext):
                self.monitor_calls.append('monitor1')

        # Register both
        init_handlers = InitHandlers()
        monitor_handlers = MonitorHandlers()

        count1 = runtime.register_handlers_from_object(init_handlers)
        count2 = runtime.register_handlers_from_object(monitor_handlers)

        assert count1 == 1
        assert count2 == 1

        # Execute
        runtime.cycle()

        # Verify both were called
        assert len(init_handlers.init_calls) == 1
        assert len(monitor_handlers.monitor_calls) == 1

    def test_same_action_multiple_handlers_from_different_objects(self):
        """Test multiple objects registering handlers for the same action."""
        dsl_code = '''
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

        # Two classes with handlers for the same action
        class Handler1:
            def __init__(self):
                self.calls = []

            @abstract_handler('System.Active.Init')
            def handle(self, ctx: ReadOnlyExecutionContext):
                self.calls.append('handler1')

        class Handler2:
            def __init__(self):
                self.calls = []

            @abstract_handler('System.Active.Init')
            def handle(self, ctx: ReadOnlyExecutionContext):
                self.calls.append('handler2')

        # Register both
        h1 = Handler1()
        h2 = Handler2()

        runtime.register_handlers_from_object(h1)
        runtime.register_handlers_from_object(h2)

        # Execute
        runtime.cycle()

        # Both handlers should be called in registration order
        assert len(h1.calls) == 1
        assert len(h2.calls) == 1

    def test_complex_handler_logic(self):
        """Test handler with complex logic and multiple variables."""
        dsl_code = '''
        def int counter = 0;
        def float temperature = 20.0;
        def int error_count = 0;

        state System {
            state Active {
                during {
                    counter = counter + 1;
                    temperature = temperature + 0.5;
                }
                during abstract Monitor;
            }

            [*] -> Active;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Complex handler with validation logic
        class ComplexHandler:
            def __init__(self):
                self.anomalies = []
                self.stats = {
                    'total_cycles': 0,
                    'high_temp_count': 0,
                    'counter_sum': 0
                }

            @abstract_handler('System.Active.Monitor')
            def monitor(self, ctx: ReadOnlyExecutionContext):
                counter = ctx.get_var('counter')
                temp = ctx.get_var('temperature')

                self.stats['total_cycles'] += 1
                self.stats['counter_sum'] += counter

                # Detect anomalies
                if temp > 22.0:
                    self.stats['high_temp_count'] += 1
                    self.anomalies.append(f'High temp at cycle {counter}: {temp}')

                if counter > 5:
                    self.anomalies.append(f'Counter threshold exceeded: {counter}')

        # Register and run
        handler = ComplexHandler()
        runtime.register_handlers_from_object(handler)

        for i in range(7):
            runtime.cycle()

        # Verify complex logic
        assert handler.stats['total_cycles'] == 7
        assert handler.stats['counter_sum'] == 1 + 2 + 3 + 4 + 5 + 6 + 7
        assert handler.stats['high_temp_count'] > 0
        assert len(handler.anomalies) > 0

    def test_empty_object_registration(self):
        """Test registering object with no decorated methods."""
        dsl_code = '''
        state System {
            state Idle;
            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Object with no decorated methods
        class EmptyHandler:
            def regular_method(self):
                pass

        handler = EmptyHandler()
        count = runtime.register_handlers_from_object(handler)

        assert count == 0

    def test_decorator_with_invalid_action_path(self):
        """Test that decorator raises error for empty action path."""
        with pytest.raises(ValueError, match='action_path cannot be empty'):
            @abstract_handler('')
            def invalid_handler(ctx):
                pass

    def test_aspect_handlers_with_decorator(self):
        """Test decorator with aspect actions."""
        dsl_code = '''
        def int counter = 0;

        state System {
            >> during before abstract PreProcess;
            >> during after abstract PostProcess;

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

        # Handler for aspect actions
        class AspectHandlers:
            def __init__(self):
                self.pre_calls = []
                self.post_calls = []

            @abstract_handler('System.PreProcess')
            def pre_process(self, ctx: ReadOnlyExecutionContext):
                self.pre_calls.append(ctx.get_var('counter'))

            @abstract_handler('System.PostProcess')
            def post_process(self, ctx: ReadOnlyExecutionContext):
                self.post_calls.append(ctx.get_var('counter'))

        # Register and execute
        handlers = AspectHandlers()
        runtime.register_handlers_from_object(handlers)

        runtime.cycle()
        runtime.cycle()
        runtime.cycle()

        # Verify aspect handlers were called
        assert len(handlers.pre_calls) == 3
        assert len(handlers.post_calls) == 3
        # Pre should see counter before increment, post after
        assert handlers.pre_calls == [0, 1, 2]
        assert handlers.post_calls == [1, 2, 3]
