"""
Shared C++ wrapper semantic-fixture alignment helpers.

This module renders the built-in ``cpp`` and ``cpp_poll`` templates for one
schema-v2 semantic fixture, generates a C++98 harness that drives only the
public ``machine.hpp`` wrapper API, builds the generated C core plus C++ wrapper
with CMake, and compares emitted public observations with the existing shared
fixture expectations.

The module contains:

* :class:`CppAlignmentArtifacts` - Paths produced while building one fixture
  harness.
* :func:`run_cpp_alignment_case` - Execute a fixture against ``cpp`` or
  ``cpp_poll`` generated wrapper artifacts.

Example::

    >>> from test.testings.simulate_semantics import load_semantic_case
    >>> case = load_semantic_case("design_basic_simple_transition")
    >>> case.id
    'design_basic_simple_transition'
"""

import os
import shutil
import subprocess
from dataclasses import dataclass, replace
from typing import List, Sequence

import pytest
from jinja2 import Environment, StrictUndefined

from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.template import extract_template
from test.testings import simulate_semantics
from test.testings.native_toolchain_alignment.harness import build_harness_context
from test.testings.native_toolchain_alignment.report import read_observations_jsonl
from test.testings.native_toolchain_alignment.runner import (
    assert_observations_match_case,
)
from test.testings.simulate_semantics import SemanticCase

_CPP_TEMPLATE = r"""
#include "machine.hpp"

#include <stdio.h>
#include <string.h>

typedef pyfcstm_generated::{{ context.machine_class_name }}_cpp::MachineWrapper Wrapper;

static {{ context.machine_class_name }}Hooks hooks = {{ context.machine_class_name.upper() }}_HOOKS_INIT;
static const char *state_paths[] = {
{% for state in context.states %}    {{ state.path | tojson }},
{% endfor %}};
{% if context.actions %}static const char *action_paths[] = {
{% for action in context.actions %}    {{ action.path | tojson }},
{% endfor %}};
{% else %}static const char **action_paths = NULL;
{% endif %}static const char *stage_names[] = {"enter", "during", "exit"};

struct HandlerCall {
    int action_id;
    int state_id;
    int stage_id;
    int active_leaf_id;
    int call_stage_id;
    int abstract_target_id;
    int named_ref_id;
{% for variable in context.variables %}    {{ context.machine_class_name }}Int {{ variable.field }}_is_int;
    double {{ variable.field }}_is_float;
{% endfor %}};

static struct HandlerCall handler_calls[512];
static size_t handler_call_count = 0u;

static const char *lookup_string(const char **items, size_t count, int id)
{
    if (id < 0 || (size_t)id >= count) {
        return NULL;
    }
    return items[id];
}

static void json_string(FILE *out, const char *value)
{
    const unsigned char *cursor;
    if (value == NULL) {
        fputs("null", out);
        return;
    }
    fputc('"', out);
    for (cursor = (const unsigned char *)value; *cursor != '\0'; ++cursor) {
        if (*cursor == '"' || *cursor == '\\') {
            fputc('\\', out);
            fputc((int)*cursor, out);
        } else if (*cursor == '\n') {
            fputs("\\n", out);
        } else if (*cursor == '\r') {
            fputs("\\r", out);
        } else if (*cursor == '\t') {
            fputs("\\t", out);
        } else {
            fputc((int)*cursor, out);
        }
    }
    fputc('"', out);
}

static void write_machine_int(FILE *out, {{ context.machine_class_name }}Int value)
{
    char digits[64];
    size_t count = 0u;
    {{ context.machine_class_name }}Int quotient = value;

    if (quotient == 0) {
        fputc('0', out);
        return;
    }
    if (quotient < 0) {
        fputc('-', out);
        while (quotient != 0) {
            {{ context.machine_class_name }}Int next = quotient / 10;
            digits[count++] = (char)('0' + (int)(next * 10 - quotient));
            quotient = next;
        }
    } else {
        while (quotient != 0) {
            digits[count++] = (char)('0' + (int)(quotient % 10));
            quotient = quotient / 10;
        }
    }
    while (count > 0u) {
        fputc((int)digits[--count], out);
    }
}

static void write_vars(FILE *out, const {{ context.machine_class_name }}Vars *vars)
{
    fputc('{', out);
{% for variable in context.variables %}    if ({{ loop.index0 }} > 0) {
        fputc(',', out);
    }
    json_string(out, {{ variable.name | tojson }});
    fputc(':', out);
{% if variable.type == 'int' %}    write_machine_int(out, vars->{{ variable.field }});
{% else %}    fprintf(out, "%.17g", vars->{{ variable.field }});
{% endif %}{% endfor %}    fputc('}', out);
}

static void write_handler_calls(FILE *out)
{
    size_t i;
    fputc('[', out);
    for (i = 0u; i < handler_call_count; ++i) {
        const struct HandlerCall *call = &handler_calls[i];
        if (i > 0u) {
            fputc(',', out);
        }
        fputc('{', out);
        fputs("\"action\":", out);
        json_string(out, lookup_string(action_paths, {{ context.actions | length }}u, call->action_id));
        fputs(",\"state\":", out);
        json_string(out, lookup_string(state_paths, sizeof(state_paths) / sizeof(state_paths[0]), call->state_id));
        fputs(",\"stage\":", out);
        json_string(out, lookup_string(stage_names, sizeof(stage_names) / sizeof(stage_names[0]), call->stage_id));
        fputs(",\"vars\":{", out);
{% for variable in context.variables %}        if ({{ loop.index0 }} > 0) {
            fputc(',', out);
        }
        json_string(out, {{ variable.name | tojson }});
        fputc(':', out);
{% if variable.type == 'int' %}        write_machine_int(out, call->{{ variable.field }}_is_int);
{% else %}        fprintf(out, "%.17g", call->{{ variable.field }}_is_float);
{% endif %}{% endfor %}        fputs("}", out);
        fputs(",\"active_leaf\":", out);
        json_string(out, lookup_string(state_paths, sizeof(state_paths) / sizeof(state_paths[0]), call->active_leaf_id));
        fputs(",\"call_stage\":", out);
        json_string(out, lookup_string(stage_names, sizeof(stage_names) / sizeof(stage_names[0]), call->call_stage_id));
        fputs(",\"abstract_target\":", out);
        json_string(out, lookup_string(action_paths, {{ context.actions | length }}u, call->abstract_target_id));
        fputs(",\"named_ref\":", out);
        json_string(out, lookup_string(action_paths, {{ context.actions | length }}u, call->named_ref_id));
        fputc('}', out);
    }
    fputc(']', out);
}

{% if context.hooks %}extern "C" {
static void record_hook({{ context.machine_class_name }} *machine_ptr, const {{ context.machine_class_name }}ExecutionContext *ctx, void *user_data)
{
    struct HandlerCall *call;
    (void)machine_ptr;
    (void)user_data;
    if (handler_call_count >= sizeof(handler_calls) / sizeof(handler_calls[0])) {
        return;
    }
    call = &handler_calls[handler_call_count++];
    call->action_id = ctx->action_id;
    call->state_id = ctx->state_id;
    call->stage_id = ctx->action_stage_id;
    call->active_leaf_id = ctx->active_leaf_state_id;
    call->call_stage_id = ctx->call_stage_id;
    call->abstract_target_id = ctx->abstract_target_id;
    call->named_ref_id = ctx->named_ref_id;
{% for variable in context.variables %}{% if variable.type == 'int' %}    call->{{ variable.field }}_is_int = ctx->vars->{{ variable.field }};
{% else %}    call->{{ variable.field }}_is_float = ctx->vars->{{ variable.field }};
{% endif %}{% endfor %}}
}
{% endif %}
static void install_hooks(Wrapper *wrapper)
{
{% for hook in context.hooks %}    hooks.{{ hook.field }} = record_hook;
{% endfor %}    wrapper->set_hooks(&hooks, NULL);
}

static int run_cycle(Wrapper *wrapper, const {{ context.machine_class_name }}EventId *events, size_t event_count)
{
    return wrapper->cycle(events, event_count);
}

static void write_observation(FILE *out, Wrapper *wrapper, int step_index, int cycle_index, const char **event_names, size_t event_count, const char *last_error)
{
    size_t i;
    const char *state_path = wrapper->current_state_path();
    const {{ context.machine_class_name }}Vars *vars = wrapper->vars();
    fputc('{', out);
    fputs("\"schema_version\":\"1\"", out);
    fputs(",\"case_id\":", out);
    json_string(out, {{ context.case_id | tojson }});
    fputs(",\"template_name\":", out);
    json_string(out, {{ context.template_name | tojson }});
    fputs(",\"phase\":\"step\"", out);
    fprintf(out, ",\"step_index\":%d,\"cycle_index\":%d", step_index, cycle_index);
    fputs(",\"events\":[", out);
    for (i = 0u; i < event_count; ++i) {
        if (i > 0u) {
            fputc(',', out);
        }
        json_string(out, event_names[i]);
    }
    fputs("]", out);
    fputs(",\"current_state\":", out);
    json_string(out, state_path);
    fputs(",\"is_ended\":", out);
    fputs(wrapper->is_ended() ? "true" : "false", out);
    fputs(",\"vars\":", out);
    write_vars(out, vars);
    fputs(",\"handler_calls\":", out);
    write_handler_calls(out);
    fputs(",\"last_error\":", out);
    json_string(out, last_error);
    fputs(",\"api_return\":null", out);
    fputs("}\n", out);
}

static void write_initial_error(FILE *out, const char *last_error)
{
    fputc('{', out);
    fputs("\"schema_version\":\"1\"", out);
    fputs(",\"case_id\":", out);
    json_string(out, {{ context.case_id | tojson }});
    fputs(",\"template_name\":", out);
    json_string(out, {{ context.template_name | tojson }});
    fputs(",\"phase\":\"init\"", out);
    fputs(",\"step_index\":null,\"cycle_index\":null", out);
    fputs(",\"events\":[]", out);
    fputs(",\"current_state\":null", out);
    fputs(",\"is_ended\":false", out);
    fputs(",\"vars\":{}", out);
    fputs(",\"handler_calls\":[]", out);
    fputs(",\"last_error\":", out);
    json_string(out, last_error);
    fputs(",\"api_return\":null", out);
    fputs("}\n", out);
}

int main(int argc, char **argv)
{
    FILE *out;
    Wrapper wrapper;
    int api_return;
    size_t cycle_iter;
    const char *last_error;
    if (argc < 2) {
        return 2;
    }
    out = fopen(argv[1], "w");
    if (out == NULL) {
        return 2;
    }
{% if not context.initial %}    if (!wrapper.init()) {
{% if context.initial_expect %}        write_initial_error(out, wrapper.last_error());
        fclose(out);
        return 0;
{% else %}        fclose(out);
        return 3;
{% endif %}    }
{% endif %}    install_hooks(&wrapper);
{% if context.initial %}{% if context.initial.synthetic_error %}{% if context.initial_expect %}    write_initial_error(out, {{ context.initial.error_message | tojson }});
    fclose(out);
    return 0;
{% else %}    fclose(out);
    return 4;
{% endif %}{% else %}    {
        {{ context.machine_class_name }}Vars initial_vars;
        memset(&initial_vars, 0, sizeof(initial_vars));
{% for assignment in context.initial.assignments %}        initial_vars.{{ assignment.field }} = {{ assignment.value }};
{% endfor %}        if (!wrapper.hot_start({{ context.machine_macro_name }}_{{ context.initial.state_macro }}, &initial_vars)) {
{% if context.initial_expect %}            write_initial_error(out, wrapper.last_error());
            fclose(out);
            return 0;
{% else %}            fclose(out);
            return 5;
{% endif %}        }
{% if context.initial_expect %}        write_initial_error(out, "Expected initial failure but hot start succeeded");
        fclose(out);
        return 0;
{% endif %}    }
{% endif %}{% elif context.initial_expect %}    if (wrapper.last_error() != NULL && wrapper.last_error()[0] != '\0') {
        write_initial_error(out, wrapper.last_error());
        fclose(out);
        return 0;
    }
    write_initial_error(out, "Expected initial failure but initialization succeeded");
    fclose(out);
    return 0;
{% endif %}
{% for step in context.steps %}    {
{% if step.events %}        const char *event_names[] = {
{% for event in step.events %}            {{ event.path | tojson }},
{% endfor %}        };
{% else %}        const char **event_names = NULL;
{% endif %}{% if step.pre_error_message %}        api_return = 0;
        last_error = {{ step.pre_error_message | tojson }};
{% elif step.cycle_count == 0 %}        api_return = 1;
        last_error = NULL;
{% else %}{% if step.events %}        {{ context.machine_class_name }}EventId event_ids[] = {
{% for event in step.events %}            {{ context.machine_macro_name }}_{{ event.macro }},
{% endfor %}        };
{% endif %}        api_return = 1;
        last_error = NULL;
        for (cycle_iter = 0u; cycle_iter < {{ step.cycle_count }}u; ++cycle_iter) {
{% if step.events %}            api_return = run_cycle(&wrapper, event_ids, {{ step.events | length }}u);
{% else %}            api_return = run_cycle(&wrapper, NULL, 0u);
{% endif %}            if (!api_return) {
                last_error = wrapper.last_error();
                if (last_error == NULL || last_error[0] == '\0') {
                    last_error = "Generated C++ wrapper cycle returned failure without diagnostic";
                }
                break;
            }
        }
{% endif %}        write_observation(out, &wrapper, {{ step.index }}, 0, event_names, {{ step.events | length }}u, last_error);
    }
{% endfor %}    fclose(out);
    return 0;
}
"""

_CPP_POLL_TEMPLATE = r"""
#include "machine.hpp"

#include <stdio.h>
#include <string.h>

typedef pyfcstm_generated::{{ context.machine_class_name }}_cpp_poll::MachineWrapper Wrapper;

static {{ context.machine_class_name }}Hooks hooks = {{ context.machine_class_name.upper() }}_HOOKS_INIT;
static {{ context.machine_class_name }}EventId active_events[64];
static size_t active_event_count = 0u;
static {{ context.machine_class_name }}EventChecks event_checks = {{ context.machine_class_name.upper() }}_EVENT_CHECKS_INIT;

static const char *state_paths[] = {
{% for state in context.states %}    {{ state.path | tojson }},
{% endfor %}};
{% if context.actions %}static const char *action_paths[] = {
{% for action in context.actions %}    {{ action.path | tojson }},
{% endfor %}};
{% else %}static const char **action_paths = NULL;
{% endif %}static const char *stage_names[] = {"enter", "during", "exit"};

struct HandlerCall {
    int action_id;
    int state_id;
    int stage_id;
    int active_leaf_id;
    int call_stage_id;
    int abstract_target_id;
    int named_ref_id;
{% for variable in context.variables %}    {{ context.machine_class_name }}Int {{ variable.field }}_is_int;
    double {{ variable.field }}_is_float;
{% endfor %}};

static struct HandlerCall handler_calls[512];
static size_t handler_call_count = 0u;

static const char *lookup_string(const char **items, size_t count, int id)
{
    if (id < 0 || (size_t)id >= count) {
        return NULL;
    }
    return items[id];
}

static void json_string(FILE *out, const char *value)
{
    const unsigned char *cursor;
    if (value == NULL) {
        fputs("null", out);
        return;
    }
    fputc('"', out);
    for (cursor = (const unsigned char *)value; *cursor != '\0'; ++cursor) {
        if (*cursor == '"' || *cursor == '\\') {
            fputc('\\', out);
            fputc((int)*cursor, out);
        } else if (*cursor == '\n') {
            fputs("\\n", out);
        } else if (*cursor == '\r') {
            fputs("\\r", out);
        } else if (*cursor == '\t') {
            fputs("\\t", out);
        } else {
            fputc((int)*cursor, out);
        }
    }
    fputc('"', out);
}

static void write_machine_int(FILE *out, {{ context.machine_class_name }}Int value)
{
    char digits[64];
    size_t count = 0u;
    {{ context.machine_class_name }}Int quotient = value;

    if (quotient == 0) {
        fputc('0', out);
        return;
    }
    if (quotient < 0) {
        fputc('-', out);
        while (quotient != 0) {
            {{ context.machine_class_name }}Int next = quotient / 10;
            digits[count++] = (char)('0' + (int)(next * 10 - quotient));
            quotient = next;
        }
    } else {
        while (quotient != 0) {
            digits[count++] = (char)('0' + (int)(quotient % 10));
            quotient = quotient / 10;
        }
    }
    while (count > 0u) {
        fputc((int)digits[--count], out);
    }
}

static void write_vars(FILE *out, const {{ context.machine_class_name }}Vars *vars)
{
    fputc('{', out);
{% for variable in context.variables %}    if ({{ loop.index0 }} > 0) {
        fputc(',', out);
    }
    json_string(out, {{ variable.name | tojson }});
    fputc(':', out);
{% if variable.type == 'int' %}    write_machine_int(out, vars->{{ variable.field }});
{% else %}    fprintf(out, "%.17g", vars->{{ variable.field }});
{% endif %}{% endfor %}    fputc('}', out);
}

static void write_handler_calls(FILE *out)
{
    size_t i;
    fputc('[', out);
    for (i = 0u; i < handler_call_count; ++i) {
        const struct HandlerCall *call = &handler_calls[i];
        if (i > 0u) {
            fputc(',', out);
        }
        fputc('{', out);
        fputs("\"action\":", out);
        json_string(out, lookup_string(action_paths, {{ context.actions | length }}u, call->action_id));
        fputs(",\"state\":", out);
        json_string(out, lookup_string(state_paths, sizeof(state_paths) / sizeof(state_paths[0]), call->state_id));
        fputs(",\"stage\":", out);
        json_string(out, lookup_string(stage_names, sizeof(stage_names) / sizeof(stage_names[0]), call->stage_id));
        fputs(",\"vars\":{", out);
{% for variable in context.variables %}        if ({{ loop.index0 }} > 0) {
            fputc(',', out);
        }
        json_string(out, {{ variable.name | tojson }});
        fputc(':', out);
{% if variable.type == 'int' %}        write_machine_int(out, call->{{ variable.field }}_is_int);
{% else %}        fprintf(out, "%.17g", call->{{ variable.field }}_is_float);
{% endif %}{% endfor %}        fputs("}", out);
        fputs(",\"active_leaf\":", out);
        json_string(out, lookup_string(state_paths, sizeof(state_paths) / sizeof(state_paths[0]), call->active_leaf_id));
        fputs(",\"call_stage\":", out);
        json_string(out, lookup_string(stage_names, sizeof(stage_names) / sizeof(stage_names[0]), call->call_stage_id));
        fputs(",\"abstract_target\":", out);
        json_string(out, lookup_string(action_paths, {{ context.actions | length }}u, call->abstract_target_id));
        fputs(",\"named_ref\":", out);
        json_string(out, lookup_string(action_paths, {{ context.actions | length }}u, call->named_ref_id));
        fputc('}', out);
    }
    fputc(']', out);
}

{% if context.hooks %}extern "C" {
static void record_hook({{ context.machine_class_name }} *machine_ptr, const {{ context.machine_class_name }}ExecutionContext *ctx, void *user_data)
{
    struct HandlerCall *call;
    (void)machine_ptr;
    (void)user_data;
    if (handler_call_count >= sizeof(handler_calls) / sizeof(handler_calls[0])) {
        return;
    }
    call = &handler_calls[handler_call_count++];
    call->action_id = ctx->action_id;
    call->state_id = ctx->state_id;
    call->stage_id = ctx->action_stage_id;
    call->active_leaf_id = ctx->active_leaf_state_id;
    call->call_stage_id = ctx->call_stage_id;
    call->abstract_target_id = ctx->abstract_target_id;
    call->named_ref_id = ctx->named_ref_id;
{% for variable in context.variables %}{% if variable.type == 'int' %}    call->{{ variable.field }}_is_int = ctx->vars->{{ variable.field }};
{% else %}    call->{{ variable.field }}_is_float = ctx->vars->{{ variable.field }};
{% endif %}{% endfor %}}
}
{% endif %}
static void install_hooks(Wrapper *wrapper)
{
{% for hook in context.hooks %}    hooks.{{ hook.field }} = record_hook;
{% endfor %}    wrapper->set_hooks(&hooks, NULL);
}

extern "C" {
static int check_event({{ context.machine_class_name }} *machine_ptr, const {{ context.machine_class_name }}EventContext *ctx, void *user_data)
{
    size_t i;
    (void)machine_ptr;
    (void)user_data;
    for (i = 0u; i < active_event_count; ++i) {
        if (active_events[i] == ctx->event_id) {
            return 1;
        }
    }
    return 0;
}
}

static void install_event_checks(Wrapper *wrapper)
{
{% for event in context.events %}    event_checks.{{ event.field }} = check_event;
{% endfor %}    wrapper->set_event_checks(&event_checks, NULL);
}

static int run_cycle(Wrapper *wrapper, const {{ context.machine_class_name }}EventId *events, size_t event_count)
{
    size_t i;
    if (event_count > sizeof(active_events) / sizeof(active_events[0])) {
        return 0;
    }
    active_event_count = event_count;
    for (i = 0u; i < event_count; ++i) {
        active_events[i] = events[i];
    }
    return wrapper->cycle();
}

static void write_observation(FILE *out, Wrapper *wrapper, int step_index, int cycle_index, const char **event_names, size_t event_count, const char *last_error)
{
    size_t i;
    const char *state_path = wrapper->current_state_path();
    const {{ context.machine_class_name }}Vars *vars = wrapper->vars();
    fputc('{', out);
    fputs("\"schema_version\":\"1\"", out);
    fputs(",\"case_id\":", out);
    json_string(out, {{ context.case_id | tojson }});
    fputs(",\"template_name\":", out);
    json_string(out, {{ context.template_name | tojson }});
    fputs(",\"phase\":\"step\"", out);
    fprintf(out, ",\"step_index\":%d,\"cycle_index\":%d", step_index, cycle_index);
    fputs(",\"events\":[", out);
    for (i = 0u; i < event_count; ++i) {
        if (i > 0u) {
            fputc(',', out);
        }
        json_string(out, event_names[i]);
    }
    fputs("]", out);
    fputs(",\"current_state\":", out);
    json_string(out, state_path);
    fputs(",\"is_ended\":", out);
    fputs(wrapper->is_ended() ? "true" : "false", out);
    fputs(",\"vars\":", out);
    write_vars(out, vars);
    fputs(",\"handler_calls\":", out);
    write_handler_calls(out);
    fputs(",\"last_error\":", out);
    json_string(out, last_error);
    fputs(",\"api_return\":null", out);
    fputs("}\n", out);
}

static void write_initial_error(FILE *out, const char *last_error)
{
    fputc('{', out);
    fputs("\"schema_version\":\"1\"", out);
    fputs(",\"case_id\":", out);
    json_string(out, {{ context.case_id | tojson }});
    fputs(",\"template_name\":", out);
    json_string(out, {{ context.template_name | tojson }});
    fputs(",\"phase\":\"init\"", out);
    fputs(",\"step_index\":null,\"cycle_index\":null", out);
    fputs(",\"events\":[]", out);
    fputs(",\"current_state\":null", out);
    fputs(",\"is_ended\":false", out);
    fputs(",\"vars\":{}", out);
    fputs(",\"handler_calls\":[]", out);
    fputs(",\"last_error\":", out);
    json_string(out, last_error);
    fputs(",\"api_return\":null", out);
    fputs("}\n", out);
}

int main(int argc, char **argv)
{
    FILE *out;
    Wrapper wrapper;
    int api_return;
    size_t cycle_iter;
    const char *last_error;
    if (argc < 2) {
        return 2;
    }
    out = fopen(argv[1], "w");
    if (out == NULL) {
        return 2;
    }
{% if not context.initial %}    if (!wrapper.init()) {
{% if context.initial_expect %}        write_initial_error(out, wrapper.last_error());
        fclose(out);
        return 0;
{% else %}        fclose(out);
        return 3;
{% endif %}    }
{% endif %}    install_hooks(&wrapper);
    install_event_checks(&wrapper);
{% if context.initial %}{% if context.initial.synthetic_error %}{% if context.initial_expect %}    write_initial_error(out, {{ context.initial.error_message | tojson }});
    fclose(out);
    return 0;
{% else %}    fclose(out);
    return 4;
{% endif %}{% else %}    {
        {{ context.machine_class_name }}Vars initial_vars;
        memset(&initial_vars, 0, sizeof(initial_vars));
{% for assignment in context.initial.assignments %}        initial_vars.{{ assignment.field }} = {{ assignment.value }};
{% endfor %}        if (!wrapper.hot_start({{ context.machine_macro_name }}_{{ context.initial.state_macro }}, &initial_vars)) {
{% if context.initial_expect %}            write_initial_error(out, wrapper.last_error());
            fclose(out);
            return 0;
{% else %}            fclose(out);
            return 5;
{% endif %}        }
{% if context.initial_expect %}        write_initial_error(out, "Expected initial failure but hot start succeeded");
        fclose(out);
        return 0;
{% endif %}    }
{% endif %}{% elif context.initial_expect %}    if (wrapper.last_error() != NULL && wrapper.last_error()[0] != '\0') {
        write_initial_error(out, wrapper.last_error());
        fclose(out);
        return 0;
    }
    write_initial_error(out, "Expected initial failure but initialization succeeded");
    fclose(out);
    return 0;
{% endif %}
{% for step in context.steps %}    {
{% if step.events %}        const char *event_names[] = {
{% for event in step.events %}            {{ event.path | tojson }},
{% endfor %}        };
{% else %}        const char **event_names = NULL;
{% endif %}{% if step.pre_error_message %}        api_return = 0;
        last_error = {{ step.pre_error_message | tojson }};
{% elif step.cycle_count == 0 %}        api_return = 1;
        last_error = NULL;
{% else %}{% if step.events %}        {{ context.machine_class_name }}EventId event_ids[] = {
{% for event in step.events %}            {{ context.machine_macro_name }}_{{ event.macro }},
{% endfor %}        };
{% endif %}        api_return = 1;
        last_error = NULL;
        for (cycle_iter = 0u; cycle_iter < {{ step.cycle_count }}u; ++cycle_iter) {
{% if step.events %}            api_return = run_cycle(&wrapper, event_ids, {{ step.events | length }}u);
{% else %}            api_return = run_cycle(&wrapper, NULL, 0u);
{% endif %}            if (!api_return) {
                last_error = wrapper.last_error();
                if (last_error == NULL || last_error[0] == '\0') {
                    last_error = "Generated C++ wrapper cycle returned failure without diagnostic";
                }
                break;
            }
        }
{% endif %}        write_observation(out, &wrapper, {{ step.index }}, 0, event_names, {{ step.events | length }}u, last_error);
    }
{% endfor %}    fclose(out);
    return 0;
}
"""

_CMAKE_TEMPLATE = r"""
cmake_minimum_required(VERSION 3.5)
project(pyfcstm_cpp_shared_fixture_harness C CXX)

set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)
set(CMAKE_C_EXTENSIONS OFF)
set(CMAKE_CXX_STANDARD 98)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

include_directories("{{ source_dir }}")

add_executable(cpp_shared_fixture_harness
    "{{ machine_c }}"
    "{{ machine_cpp }}"
    "{{ harness_cpp }}"
)

if(NOT WIN32)
    target_link_libraries(cpp_shared_fixture_harness m)
endif()
"""


@dataclass(frozen=True)
class CppAlignmentArtifacts:
    """
    Paths produced by one C++ shared-fixture harness run.

    :param template_name: Template under test, either ``"cpp"`` or
        ``"cpp_poll"``.
    :type template_name: str
    :param case_id: Semantic fixture case id.
    :type case_id: str
    :param root_dir: Root artifact directory for this fixture run.
    :type root_dir: str
    :param generated_dir: Rendered generated-source directory.
    :type generated_dir: str
    :param harness_dir: Directory containing ``harness.cpp`` and
        ``CMakeLists.txt``.
    :type harness_dir: str
    :param build_dir: CMake build directory.
    :type build_dir: str
    :param observations_path: JSON Lines observation file emitted by the
        harness executable.
    :type observations_path: str

    Example::

        >>> artifacts = CppAlignmentArtifacts("cpp", "demo", "/tmp/a", "/tmp/a/g", "/tmp/a/h", "/tmp/a/b", "/tmp/a/o.jsonl")
        >>> artifacts.template_name
        'cpp'
    """

    template_name: str
    case_id: str
    root_dir: str
    generated_dir: str
    harness_dir: str
    build_dir: str
    observations_path: str


def _validate_template_name(template_name: str) -> None:
    if template_name not in ("cpp", "cpp_poll"):
        raise ValueError("unsupported C++ alignment template: %r" % template_name)


def _cmake_generator_args() -> List[str]:
    if os.name == "nt":
        return ["-G", "MinGW Makefiles"]
    return []


def _find_cmake() -> str:
    cmake = shutil.which("cmake")
    if cmake is None:
        pytest.skip("cmake is required for generated C++ alignment tests.")
    return cmake


def _environment() -> Environment:
    env = Environment(
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


def _render_generated_template(
    template_name: str, case: SemanticCase, generated_dir: str
) -> None:
    model = simulate_semantics.build_state_machine_from_case(case)
    template_root = os.path.join(os.path.dirname(generated_dir), "template-src")
    template_dir = extract_template(template_name, template_root)
    StateMachineCodeRenderer(template_dir).render(model=model, output_dir=generated_dir)


def _render_harness(template_name: str, case: SemanticCase, harness_path: str) -> None:
    base_context = build_harness_context(
        "c_poll" if template_name == "cpp_poll" else "c", case
    )
    context = replace(base_context, template_name=template_name)
    template_text = _CPP_POLL_TEMPLATE if template_name == "cpp_poll" else _CPP_TEMPLATE
    rendered = _environment().from_string(template_text).render(context=context)
    os.makedirs(os.path.dirname(harness_path), exist_ok=True)
    with open(harness_path, "w", encoding="utf-8") as f:
        f.write(rendered)


def _render_cmake(artifacts: CppAlignmentArtifacts, harness_path: str) -> None:
    text = (
        _environment()
        .from_string(_CMAKE_TEMPLATE)
        .render(
            source_dir=artifacts.generated_dir.replace("\\", "/"),
            machine_c=os.path.join(artifacts.generated_dir, "machine.c").replace(
                "\\", "/"
            ),
            machine_cpp=os.path.join(artifacts.generated_dir, "machine.cpp").replace(
                "\\", "/"
            ),
            harness_cpp=harness_path.replace("\\", "/"),
        )
    )
    with open(
        os.path.join(artifacts.harness_dir, "CMakeLists.txt"), "w", encoding="utf-8"
    ) as f:
        f.write(text)


def _prepare_artifacts(
    template_name: str, case: SemanticCase, artifact_root: str
) -> CppAlignmentArtifacts:
    generated_dir = os.path.join(artifact_root, "generated")
    harness_dir = os.path.join(artifact_root, "harness")
    build_dir = os.path.join(artifact_root, "build")
    observations_path = os.path.join(artifact_root, "observations.jsonl")
    os.makedirs(generated_dir, exist_ok=True)
    os.makedirs(harness_dir, exist_ok=True)
    os.makedirs(build_dir, exist_ok=True)
    _render_generated_template(template_name, case, generated_dir)
    artifacts = CppAlignmentArtifacts(
        template_name,
        case.id,
        artifact_root,
        generated_dir,
        harness_dir,
        build_dir,
        observations_path,
    )
    harness_path = os.path.join(harness_dir, "harness.cpp")
    _render_harness(template_name, case, harness_path)
    _render_cmake(artifacts, harness_path)
    return artifacts


def _run_command(
    command: Sequence[str], cwd: str, stdout_path: str, stderr_path: str
) -> subprocess.CompletedProcess:
    command_path = stdout_path.replace(".stdout.txt", ".command.txt")
    with open(command_path, "w", encoding="utf-8") as f:
        f.write(" ".join(command) + "\n")
    completed = subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    with open(stdout_path, "w", encoding="utf-8") as f:
        f.write(completed.stdout or "")
    with open(stderr_path, "w", encoding="utf-8") as f:
        f.write(completed.stderr or "")
    return completed


def _command_output_tail(output: str, limit: int = 4000) -> str:
    if len(output) <= limit:
        return output
    return "...<truncated>\n" + output[-limit:]


def _fail_command(
    stage: str,
    command: Sequence[str],
    completed: subprocess.CompletedProcess,
    stdout_path: str,
    stderr_path: str,
) -> None:
    raise AssertionError(
        "{stage} failed with return code {returncode}.\n"
        "command: {command}\n"
        "stdout: {stdout}\n"
        "stderr: {stderr}\n"
        "stdout tail:\n{stdout_tail}\n"
        "stderr tail:\n{stderr_tail}".format(
            stage=stage,
            returncode=completed.returncode,
            command=" ".join(command),
            stdout=stdout_path,
            stderr=stderr_path,
            stdout_tail=_command_output_tail(completed.stdout or ""),
            stderr_tail=_command_output_tail(completed.stderr or ""),
        )
    )


def _find_executable(build_dir: str) -> str:
    candidates = [
        os.path.join(build_dir, "cpp_shared_fixture_harness"),
        os.path.join(build_dir, "cpp_shared_fixture_harness.exe"),
        os.path.join(build_dir, "Release", "cpp_shared_fixture_harness.exe"),
        os.path.join(build_dir, "Debug", "cpp_shared_fixture_harness.exe"),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    raise FileNotFoundError(
        "Cannot find C++ shared fixture harness executable under %r." % build_dir
    )


def _build_and_run(artifacts: CppAlignmentArtifacts) -> None:
    cmake = _find_cmake()
    logs_dir = os.path.join(artifacts.root_dir, "logs")
    os.makedirs(logs_dir, exist_ok=True)
    configure_command = (
        [cmake]
        + _cmake_generator_args()
        + [
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            os.path.abspath(artifacts.harness_dir),
        ]
    )
    configure_stdout = os.path.join(logs_dir, "configure.stdout.txt")
    configure_stderr = os.path.join(logs_dir, "configure.stderr.txt")
    configure_result = _run_command(
        configure_command, artifacts.build_dir, configure_stdout, configure_stderr
    )
    if configure_result.returncode != 0:
        _fail_command(
            "CMake configure",
            configure_command,
            configure_result,
            configure_stdout,
            configure_stderr,
        )

    build_command = [cmake, "--build", ".", "--config", "Release"]
    build_stdout = os.path.join(logs_dir, "build.stdout.txt")
    build_stderr = os.path.join(logs_dir, "build.stderr.txt")
    build_result = _run_command(
        build_command, artifacts.build_dir, build_stdout, build_stderr
    )
    if build_result.returncode != 0:
        _fail_command(
            "CMake build", build_command, build_result, build_stdout, build_stderr
        )

    run_command = [_find_executable(artifacts.build_dir), artifacts.observations_path]
    run_stdout = os.path.join(logs_dir, "run.stdout.txt")
    run_stderr = os.path.join(logs_dir, "run.stderr.txt")
    run_result = _run_command(run_command, artifacts.build_dir, run_stdout, run_stderr)
    if run_result.returncode != 0:
        _fail_command(
            "C++ harness run", run_command, run_result, run_stdout, run_stderr
        )


def run_cpp_alignment_case(
    template_name: str, case: SemanticCase, artifact_root: str
) -> CppAlignmentArtifacts:
    """
    Execute one semantic fixture against a generated C++ wrapper template.

    The generated harness includes only ``machine.hpp`` directly and drives the
    state machine through wrapper methods such as ``init()``, ``hot_start()``,
    ``cycle()``, ``vars()``, ``is_ended()``, and ``current_state_path()``. It
    writes JSON Lines observations that are compared with the existing shared
    semantic fixture expectations.

    :param template_name: Template under test, either ``"cpp"`` or
        ``"cpp_poll"``.
    :type template_name: str
    :param case: Shared semantic fixture case.
    :type case: test.testings.simulate_semantics.SemanticCase
    :param artifact_root: Directory where generated sources, harness files,
        build logs, and observations are written.
    :type artifact_root: str
    :return: Artifact paths for the completed run.
    :rtype: CppAlignmentArtifacts
    :raises AssertionError: If configure, build, run, or observation alignment
        fails.
    :raises ValueError: If ``template_name`` is unsupported.

    Example::

        >>> case = simulate_semantics.load_semantic_case("design_basic_simple_transition")
        >>> case.id
        'design_basic_simple_transition'
    """
    _validate_template_name(template_name)
    artifacts = _prepare_artifacts(template_name, case, artifact_root)
    _build_and_run(artifacts)
    observations = read_observations_jsonl(artifacts.observations_path)
    assert_observations_match_case(template_name, case, observations)
    return artifacts
