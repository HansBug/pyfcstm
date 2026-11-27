#include "machine.h"
#include <stdio.h>
#include <string.h>

static void report(const char *name, LineMachine *machine,
                   const LineMachineExecutionContext *ctx, void *user_data)
{
    LineMachineConfiguration configuration;
    char text[128];
    (void)user_data;
    LineMachine_get_configuration(machine, &configuration);
    LineMachine_configuration_format(&configuration, text, sizeof(text));
    printf("%s: state_id=%d active_leaf_state_id=%d configuration=%s\n",
           name, (int)ctx->state_id, (int)ctx->active_leaf_state_id, text);
}

static void on_boot(LineMachine *m, const LineMachineExecutionContext *c, void *u)
{
    report("Boot", m, c, u);
}

static void on_tick(LineMachine *m, const LineMachineExecutionContext *c, void *u)
{
    report("Tick", m, c, u);
}

static int read_fault(void *user_data, LineMachineInt *value)
{
    (void)user_data;
    *value = 0;
    return 1;
}

int main(void)
{
    LineMachine machine;
    LineMachineHooks hooks;
    LineMachineInputProvider provider;
    memset(&hooks, 0, sizeof(hooks));
    memset(&provider, 0, sizeof(provider));
    hooks.on_p4_Line_p4_Boot = on_boot;
    hooks.on_p4_Line_p4_Work_p4_Left_p1_L_p4_Tick = on_tick;
    provider.read_fault = read_fault;
    LineMachine_init(&machine);
    LineMachine_set_hooks(&machine, &hooks, NULL);
    LineMachine_set_input_provider(&machine, &provider, NULL);
    LineMachine_cycle(&machine, NULL, 0u);
    printf("state ids: Line=%d Work=%d Left.L=%d Right.R=%d\n",
           (int)LINE_MACHINE_STATE_LINE, (int)LINE_MACHINE_STATE_LINE_WORK,
           (int)LINE_MACHINE_STATE_LINE_WORK_LEFT_L,
           (int)LINE_MACHINE_STATE_LINE_WORK_RIGHT_R);
    return 0;
}
