#include "machine.hpp"

#include <iostream>

using pyfcstm_generated::SimpleMachineMachine_cpp::MachineWrapper;

static bool print_state(const char *label, const MachineWrapper &machine) {
    const MachineWrapper::Vars *vars = machine.vars();
    const char *path = machine.current_state_path();
    if (vars == 0 || path == 0) {
        return false;
    }
    std::cout << "cpp " << label << ": " << path << " counter=" << vars->counter << "\n";
    return true;
}

int main() {
    MachineWrapper machine;
    if (!machine.init()) {
        return 1;
    }
    if (!machine.cycle() || !print_state("initial", machine)) {
        return 2;
    }
    if (!machine.cycle(SIMPLEMACHINE_MACHINE_EVENT_SIMPLEMACHINE_IDLE_START) ||
        !print_state("after Start", machine)) {
        return 3;
    }
    if (!machine.cycle(SIMPLEMACHINE_MACHINE_EVENT_SIMPLEMACHINE_RUNNING_STOP) ||
        !print_state("after Stop", machine)) {
        return 4;
    }
    if (!machine.cycle(SIMPLEMACHINE_MACHINE_EVENT_SIMPLEMACHINE_STOPPED_RESET) ||
        !print_state("after Reset", machine)) {
        return 5;
    }
    return 0;
}
