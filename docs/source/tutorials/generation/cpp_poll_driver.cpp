#include "machine.hpp"

#include <iostream>

using pyfcstm_generated::SimpleMachineMachine_cpp_poll::MachineWrapper;

struct EventInputs {
    int start;
    int stop;
    int reset;
};

static int check_start(
    MachineWrapper::Machine *machine,
    const MachineWrapper::EventContext *ctx,
    void *user_data) {
    EventInputs *inputs = static_cast<EventInputs *>(user_data);
    (void)machine;
    (void)ctx;
    return inputs->start;
}

static int check_stop(
    MachineWrapper::Machine *machine,
    const MachineWrapper::EventContext *ctx,
    void *user_data) {
    EventInputs *inputs = static_cast<EventInputs *>(user_data);
    (void)machine;
    (void)ctx;
    return inputs->stop;
}

static int check_reset(
    MachineWrapper::Machine *machine,
    const MachineWrapper::EventContext *ctx,
    void *user_data) {
    EventInputs *inputs = static_cast<EventInputs *>(user_data);
    (void)machine;
    (void)ctx;
    return inputs->reset;
}

static bool print_state(const char *label, const MachineWrapper &machine) {
    const MachineWrapper::Vars *vars = machine.vars();
    const char *path = machine.current_state_path();
    if (vars == 0 || path == 0) {
        return false;
    }
    std::cout << "cpp_poll " << label << ": " << path << " counter=" << vars->counter << "\n";
    return true;
}

int main() {
    MachineWrapper machine;
    MachineWrapper::EventChecks checks = SIMPLEMACHINEMACHINE_EVENT_CHECKS_INIT;
    EventInputs inputs = {0, 0, 0};

    checks.check_p13_SimpleMachine_p4_Idle_p5_Start = check_start;
    checks.check_p13_SimpleMachine_p7_Running_p4_Stop = check_stop;
    checks.check_p13_SimpleMachine_p7_Stopped_p5_Reset = check_reset;

    if (!machine.init()) {
        return 1;
    }
    machine.set_event_checks(&checks, &inputs);

    if (!machine.cycle() || !print_state("initial", machine)) {
        return 2;
    }
    inputs.start = 1;
    if (!machine.cycle() || !print_state("after Start", machine)) {
        return 3;
    }
    inputs.start = 0;
    inputs.stop = 1;
    if (!machine.cycle() || !print_state("after Stop", machine)) {
        return 4;
    }
    inputs.stop = 0;
    inputs.reset = 1;
    if (!machine.cycle() || !print_state("after Reset", machine)) {
        return 5;
    }
    return 0;
}
