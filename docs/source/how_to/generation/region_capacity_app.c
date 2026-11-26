#include "machine.h"

#include <stdio.h>
#include <string.h>

typedef struct AppData {
    ControllerMachineInt fault;
    ControllerMachineInt requested;
} AppData;

static int read_fault(void *user_data, ControllerMachineInt *value)
{
    *value = ((AppData *)user_data)->fault;
    return 1;
}

static int read_requested(void *user_data, ControllerMachineInt *value)
{
    *value = ((AppData *)user_data)->requested;
    return 1;
}

int main(void)
{
    static ControllerMachine machine;
    ControllerMachineInitOptions options;
    ControllerMachineInputProvider provider;
    ControllerMachineConfiguration configuration;
    ControllerMachineEventId start = CONTROLLER_MACHINE_EVENT_p10_Controller_p5_Start;
    AppData data = {0, 1};
    char text[128];
    int step;

    memset(&options, 0, sizeof(options));
    memset(&provider, 0, sizeof(provider));
    provider.read_fault = read_fault;
    provider.read_requested = read_requested;
    if (!ControllerMachine_init_with_options(&machine, &options)) {
        fprintf(stderr, "%s\n", ControllerMachine_last_error(&machine));
        return 1;
    }
    ControllerMachine_set_input_provider(&machine, &provider, &data);
    printf("storage bytes: %zu\n", (size_t)CONTROLLER_MACHINE_STORAGE_BYTES);
    for (step = 0; step < 3; step++) {
        if (!ControllerMachine_cycle(&machine, step == 1 ? &start : NULL, step == 1 ? 1u : 0u)) {
            printf("cycle %d failed: %s\n", step + 1, ControllerMachine_last_error(&machine));
            return 2;
        }
        ControllerMachine_get_configuration(&machine, &configuration);
        ControllerMachine_configuration_format(&configuration, text, sizeof(text));
        printf("cycle %d: %s motor=%g\n", step + 1, text,
               (double)ControllerMachine_vars(&machine)->motor);
    }
    return 0;
}
