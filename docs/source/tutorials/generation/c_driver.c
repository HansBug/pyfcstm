#include "machine.h"

#include <stdio.h>

static int print_state(const char *label, const SimpleMachineMachine *machine) {
    const SimpleMachineMachineVars *vars = SimpleMachineMachine_vars(machine);
    const char *path = SimpleMachineMachine_current_state_path(machine);
    if (vars == 0 || path == 0) {
        return 0;
    }
    printf("c %s: %s counter=%lld\n", label, path, (long long)vars->counter);
    return 1;
}

static int run_cycle(
    SimpleMachineMachine *machine,
    const SimpleMachineMachineEventId *events,
    size_t event_count) {
    if (!SimpleMachineMachine_cycle(machine, events, event_count)) {
        fprintf(stderr, "cycle failed: %s\n", SimpleMachineMachine_last_error(machine));
        return 0;
    }
    return 1;
}

int main(void) {
    SimpleMachineMachine machine;
    static const SimpleMachineMachineEventId start_events[] = {
        SIMPLEMACHINE_MACHINE_EVENT_SIMPLEMACHINE_IDLE_START};
    static const SimpleMachineMachineEventId stop_events[] = {
        SIMPLEMACHINE_MACHINE_EVENT_SIMPLEMACHINE_RUNNING_STOP};
    static const SimpleMachineMachineEventId reset_events[] = {
        SIMPLEMACHINE_MACHINE_EVENT_SIMPLEMACHINE_STOPPED_RESET};

    if (!SimpleMachineMachine_init(&machine)) {
        return 1;
    }
    if (!run_cycle(&machine, 0, 0u) || !print_state("initial", &machine)) {
        return 2;
    }
    if (!run_cycle(&machine, start_events, 1u) ||
        !print_state("after Start", &machine)) {
        return 3;
    }
    if (!run_cycle(&machine, stop_events, 1u) || !print_state("after Stop", &machine)) {
        return 4;
    }
    if (!run_cycle(&machine, reset_events, 1u) ||
        !print_state("after Reset", &machine)) {
        return 5;
    }
    return 0;
}
