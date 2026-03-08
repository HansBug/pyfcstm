#!/usr/bin/env python3
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime, abstract_handler

dsl_code = """
def int counter = 0;

state System {
    [*] -> Active;

    state Active {
        enter abstract Init;
        during abstract Monitor;
        exit abstract Cleanup;

        during {
            counter = counter + 1;
        }
    }

    state Done;

    Active -> Done : if [counter >= 5];
}
"""

# Define handler class
class MyHandlers:
    def __init__(self):
        self.init_called = False
        self.monitor_count = 0

    @abstract_handler('System.Active.Init')
    def handle_init(self, ctx):
        self.init_called = True
        print(f"[Init] State: {ctx.get_full_state_path()}")
        print(f"[Init] Counter: {ctx.get_var('counter')}")

    @abstract_handler('System.Active.Monitor')
    def handle_monitor(self, ctx):
        self.monitor_count += 1
        print(f"[Monitor #{self.monitor_count}] Counter: {ctx.get_var('counter')}")

    @abstract_handler('System.Active.Cleanup')
    def handle_cleanup(self, ctx):
        print(f"[Cleanup] Final counter: {ctx.get_var('counter')}")
        print(f"[Cleanup] Monitor was called {self.monitor_count} times")

# Parse and create state machine
ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
sm = parse_dsl_node_to_state_machine(ast)

# Create runtime and register handlers
runtime = SimulationRuntime(sm)
handlers = MyHandlers()
runtime.register_handlers_from_object(handlers)

# Execute cycles
print("=== Starting simulation ===\n")
for i in range(1, 7):
    runtime.cycle()
    print(f"\nCycle {i} complete - State: {runtime.current_state}\n")

print(f"\n=== Simulation complete ===")
print(f"Init was called: {handlers.init_called}")
print(f"Monitor was called: {handlers.monitor_count} times")
