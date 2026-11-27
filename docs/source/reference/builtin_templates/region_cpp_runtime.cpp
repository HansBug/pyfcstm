#include "machine.hpp"
#include <stdio.h>
#include <string.h>

typedef pyfcstm_generated::ControllerMachine_cpp::MachineWrapper Wrapper;

static void show(const char *label, const Wrapper &machine)
{
    Wrapper::Configuration configuration;
    char text[256];
    if (!machine.get_configuration(&configuration)) {
        printf("%s: no configuration\n", label);
        return;
    }
    Wrapper::format_configuration(configuration, text, sizeof(text));
    printf("%s: %s | motor=%g\n", label, text, (double)machine.vars()->motor);
}

int main()
{
    Wrapper machine;
    Wrapper::Inputs inputs;
    Wrapper::EventId start = CONTROLLER_MACHINE_EVENT_p10_Controller_p5_Start;
    Wrapper::Configuration saved;
    Wrapper::Configuration other;
    Wrapper::ConfigurationError error;
    Wrapper::Vars vars;

    memset(&inputs, 0, sizeof(inputs));
    inputs.requested = 1;
    machine.cycle_with_inputs(inputs);
    machine.cycle_with_inputs(inputs, &start, 1u);
    machine.cycle_with_inputs(inputs);
    show("after three cycles", machine);

    machine.get_configuration(&saved);
    printf("Safety status = %d\n",
           (int)Wrapper::region_status(
               saved, CONTROLLER_MACHINE_REGION_p10_Controller_p7_Running_p6_Safety));
    printf("valid = %d\n", Wrapper::validate_configuration(saved));
    Wrapper::parse_configuration("Controller.Running{Safety: Watching, Motion: Off}",
                                 &other, &error);
    printf("saved == parsed: %d\n", saved == other);
    printf("saved != parsed: %d\n", saved != other);
    if (!Wrapper::parse_configuration("Controller.Running{Safety: Idle}", &other,
                                      &error)) {
        printf("refused: kind=%d message=%s\n", error.kind, error.message);
    }

    memset(&vars, 0, sizeof(vars));
    vars.motor = 1;
    vars.permit = 1;
    if (!machine.hot_start_at(saved, vars)) {
        printf("hot start failed: %s\n", machine.last_error());
        return 2;
    }
    show("after hot start", machine);
    return 0;
}
