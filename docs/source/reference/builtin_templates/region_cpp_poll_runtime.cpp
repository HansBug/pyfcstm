#include "machine.hpp"
#include <stdio.h>
#include <string.h>

typedef pyfcstm_generated::ControllerMachine_cpp_poll::MachineWrapper Wrapper;

static int check_start(ControllerMachine *machine, const Wrapper::EventContext *ctx,
                       void *user_data)
{
    int *calls = (int *)user_data;
    (void)machine;
    (void)ctx;
    *calls += 1;
    return *calls == 2;
}

static int check_stop(ControllerMachine *machine, const Wrapper::EventContext *ctx,
                      void *user_data)
{
    (void)machine;
    (void)ctx;
    (void)user_data;
    return 0;
}

int main()
{
    Wrapper machine;
    Wrapper::EventChecks checks = CONTROLLERMACHINE_EVENT_CHECKS_INIT;
    Wrapper::Inputs inputs;
    Wrapper::Configuration configuration;
    char text[256];
    int calls = 0;
    int cycle;

    memset(&inputs, 0, sizeof(inputs));
    inputs.requested = 1;
    checks.check_p10_Controller_p5_Start = check_start;
    checks.check_p10_Controller_p4_Stop = check_stop;
    machine.set_event_checks(&checks, &calls);
    for (cycle = 1; cycle <= 3; cycle++) {
        machine.cycle_with_inputs(inputs);
        machine.get_configuration(&configuration);
        Wrapper::format_configuration(configuration, text, sizeof(text));
        printf("cycle %d: %s | start checks so far=%d\n", cycle, text, calls);
    }
    return 0;
}
