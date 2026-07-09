#include "machine.h"

#include <stdio.h>

typedef struct EventInputs {
    int start;
    int stop;
    int reset;
} EventInputs;

static int check_start(
    SimpleMachineMachine *machine,
    const SimpleMachineMachineEventContext *ctx,
    void *user_data) {
    EventInputs *inputs = (EventInputs *)user_data;
    (void)machine;
    (void)ctx;
    return inputs->start;
}

static int check_stop(
    SimpleMachineMachine *machine,
    const SimpleMachineMachineEventContext *ctx,
    void *user_data) {
    EventInputs *inputs = (EventInputs *)user_data;
    (void)machine;
    (void)ctx;
    return inputs->stop;
}

static int check_reset(
    SimpleMachineMachine *machine,
    const SimpleMachineMachineEventContext *ctx,
    void *user_data) {
    EventInputs *inputs = (EventInputs *)user_data;
    (void)machine;
    (void)ctx;
    return inputs->reset;
}

static int print_state(const char *label, const SimpleMachineMachine *machine) {
    const SimpleMachineMachineVars *vars = SimpleMachineMachine_vars(machine);
    const char *path = SimpleMachineMachine_current_state_path(machine);
    if (vars == 0 || path == 0) {
        return 0;
    }
    printf("c_poll %s: %s counter=%lld\n", label, path, (long long)vars->counter);
    return 1;
}

static int run_cycle(SimpleMachineMachine *machine) {
    if (!SimpleMachineMachine_cycle(machine)) {
        fprintf(stderr, "cycle failed: %s\n", SimpleMachineMachine_last_error(machine));
        return 0;
    }
    return 1;
}

int main(void) {
    SimpleMachineMachine machine;
    SimpleMachineMachineEventChecks checks = SIMPLEMACHINEMACHINE_EVENT_CHECKS_INIT;
    EventInputs inputs = {0, 0, 0};

    checks.check_p13_SimpleMachine_p4_Idle_p5_Start = check_start;
    checks.check_p13_SimpleMachine_p7_Running_p4_Stop = check_stop;
    checks.check_p13_SimpleMachine_p7_Stopped_p5_Reset = check_reset;

    if (!SimpleMachineMachine_init(&machine)) {
        return 1;
    }
    SimpleMachineMachine_set_event_checks(&machine, &checks, &inputs);

    if (!run_cycle(&machine) || !print_state("initial", &machine)) {
        return 2;
    }
    inputs.start = 1;
    if (!run_cycle(&machine) || !print_state("after Start", &machine)) {
        return 3;
    }
    inputs.start = 0;
    inputs.stop = 1;
    if (!run_cycle(&machine) || !print_state("after Stop", &machine)) {
        return 4;
    }
    inputs.stop = 0;
    inputs.reset = 1;
    if (!run_cycle(&machine) || !print_state("after Reset", &machine)) {
        return 5;
    }
    return 0;
}
