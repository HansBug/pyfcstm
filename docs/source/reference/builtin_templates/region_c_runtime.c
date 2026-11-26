#include "machine.h"
#include <stdio.h>
#include <string.h>

static void show(const char *label, const ControllerMachine *machine)
{
    ControllerMachineConfiguration configuration;
    char text[256];
    if (!ControllerMachine_get_configuration(machine, &configuration)) {
        printf("%s: no configuration\n", label);
        return;
    }
    ControllerMachine_configuration_format(&configuration, text, sizeof(text));
    printf("%s: %s | at=%d regions=[%d, %d] | motor=%g\n", label, text,
           (int)configuration.at, (int)configuration.regions[0],
           (int)configuration.regions[1],
           (double)ControllerMachine_vars(machine)->motor);
}

int main(void)
{
    ControllerMachine machine;
    ControllerMachineInputs inputs;
    ControllerMachineEventId start = CONTROLLER_MACHINE_EVENT_p10_Controller_p5_Start;
    ControllerMachineConfiguration configuration;
    ControllerMachineConfigurationError error;
    ControllerMachineStateId leaves[4];
    size_t count;
    char text[256];

    memset(&inputs, 0, sizeof(inputs));
    inputs.requested = 1;
    if (!ControllerMachine_init(&machine)) {
        return 1;
    }
    ControllerMachine_cycle_with_inputs(&machine, NULL, 0u, &inputs);
    show("cycle 1", &machine);
    ControllerMachine_cycle_with_inputs(&machine, &start, 1u, &inputs);
    show("cycle 2 (/Start)", &machine);
    ControllerMachine_cycle_with_inputs(&machine, NULL, 0u, &inputs);
    show("cycle 3", &machine);

    ControllerMachine_get_configuration(&machine, &configuration);
    printf("REGION_COUNT = %d\n", CONTROLLER_MACHINE_REGION_COUNT);
    printf("Safety status = %d (LIVE is %d)\n",
           (int)ControllerMachine_configuration_region_status(
               &configuration,
               CONTROLLER_MACHINE_REGION_p10_Controller_p7_Running_p6_Safety),
           (int)CONTROLLER_MACHINE_REGION_STATUS_LIVE);
    printf("Running active = %d, Idle active = %d\n",
           ControllerMachine_configuration_is_active(
               &configuration, CONTROLLER_MACHINE_STATE_CONTROLLER_RUNNING),
           ControllerMachine_configuration_is_active(
               &configuration, CONTROLLER_MACHINE_STATE_CONTROLLER_IDLE));
    count = ControllerMachine_configuration_leaves(&configuration, NULL, 0u);
    printf("leaf count = %lu\n", (unsigned long)count);
    count = ControllerMachine_configuration_leaves(&configuration, leaves, 4u);
    printf("leaf ids = %d, %d\n", (int)leaves[0], (int)leaves[1]);

    /* The text form is the simulator's; regions left out are pending. */
    if (ControllerMachine_configuration_parse(
            "Controller.Running{Motion: On}", &configuration, &error)) {
        ControllerMachine_configuration_format(&configuration, text, sizeof(text));
        printf("parsed: %s\n", text);
    }
    if (!ControllerMachine_configuration_parse(
            "Controller.Running.Motion.On", &configuration, &error)) {
        printf("refused: kind=%d position=%lu message=%s\n", error.kind,
               (unsigned long)error.position, error.message);
    }
    if (!ControllerMachine_configuration_parse(
            "Controller.Running{Speed: On}", &configuration, &error)) {
        printf("refused: kind=%d position=%lu message=%s\n", error.kind,
               (unsigned long)error.position, error.message);
    }
    if (!ControllerMachine_configuration_parse(
            "Controller.Running{Motion: On, Motion: Off}", &configuration, &error)) {
        printf("refused: kind=%d position=%lu message=%s\n", error.kind,
               (unsigned long)error.position, error.message);
    }

    /* Hot start from a saved position; every variable is supplied. */
    {
        ControllerMachineVars vars;
        memset(&vars, 0, sizeof(vars));
        ControllerMachine_configuration_parse(
            "Controller.Running{Safety: Watching, Motion: On}", &configuration, &error);
        vars.motor = 1;
        vars.permit = 1;
        if (!ControllerMachine_hot_start_at(&machine, &configuration, &vars)) {
            printf("hot start failed: %s\n", ControllerMachine_last_error(&machine));
            return 2;
        }
        show("after hot start", &machine);
        ControllerMachine_cycle_with_inputs(&machine, NULL, 0u, &inputs);
        show("cycle after hot start", &machine);
    }
    printf("ARENA_CAPACITY = %d, TRAIL_CAPACITY = %d, STORAGE_BYTES = %d\n",
           CONTROLLER_MACHINE_ARENA_CAPACITY, CONTROLLER_MACHINE_TRAIL_CAPACITY,
           (int)CONTROLLER_MACHINE_STORAGE_BYTES);
    printf("sizeof(machine) >= STORAGE_BYTES: %d\n",
           sizeof(machine) >= CONTROLLER_MACHINE_STORAGE_BYTES);
    return 0;
}
