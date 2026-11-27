#include "machine.h"
#include <stdio.h>
#include <string.h>

typedef struct App {
    int start_calls;
    int stop_calls;
} App;

static int check_start(ControllerMachine *machine,
                       const ControllerMachineEventContext *ctx, void *user_data)
{
    App *app = (App *)user_data;
    (void)machine;
    (void)ctx;
    app->start_calls += 1;
    return app->start_calls == 2;
}

static int check_stop(ControllerMachine *machine,
                      const ControllerMachineEventContext *ctx, void *user_data)
{
    App *app = (App *)user_data;
    (void)machine;
    (void)ctx;
    app->stop_calls += 1;
    return 0;
}

int main(void)
{
    ControllerMachine machine;
    ControllerMachineEventChecks checks = CONTROLLERMACHINE_EVENT_CHECKS_INIT;
    ControllerMachineInputs inputs;
    ControllerMachineConfiguration configuration;
    char text[256];
    App app;
    int cycle;

    memset(&app, 0, sizeof(app));
    memset(&inputs, 0, sizeof(inputs));
    inputs.requested = 1;
    checks.check_p10_Controller_p5_Start = check_start;
    checks.check_p10_Controller_p4_Stop = check_stop;
    ControllerMachine_init(&machine);
    ControllerMachine_set_event_checks(&machine, &checks, &app);
    for (cycle = 1; cycle <= 3; cycle++) {
        ControllerMachine_cycle_with_inputs(&machine, &inputs);
        ControllerMachine_get_configuration(&machine, &configuration);
        ControllerMachine_configuration_format(&configuration, text, sizeof(text));
        printf("cycle %d: %s | start checks so far=%d stop checks so far=%d\n", cycle,
               text, app.start_calls, app.stop_calls);
    }
    return 0;
}
