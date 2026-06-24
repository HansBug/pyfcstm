"""
Shared C++ wrapper semantic-fixture alignment helpers.

This module renders the built-in ``cpp`` and ``cpp_poll`` templates for one
schema-v2 semantic fixture, generates a C++98 harness that drives only the
public ``machine.hpp`` wrapper API, builds the generated C core plus C++
wrapper with CMake, and compares emitted public observations with the existing
shared fixture expectations. The generated harness intentionally includes only
``machine.hpp`` directly and calls wrapper methods rather than the underlying
``machine.h`` C entry points.

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

import json
import os
import re
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

_INCLUDE_DIRECTIVE_RE = re.compile(r"^\s*#\s*include\s*(?P<target>[^\n]+)", re.M)
_INCLUDE_LITERAL_RE = re.compile(r'(?:(?:"([^"\n]+)")|(?:<([^>\n]+)>))')
_LINE_CONTINUATION_RE = re.compile(r"\\\r?\n")
_NATIVE_HANDLE_CALL_RE = re.compile(r"\bnative_handle\s*\(")
_TOKEN_PASTE_RE = re.compile(r"##")
_DIRECT_C_TYPE_RE = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*Machine"
    r"(Vars|StateId|EventId|Int|Hooks|EventChecks|ExecutionContext|EventContext)?\b"
)
_DIRECT_C_API_RE = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*Machine_"
    r"(create_uninitialized|create|destroy|init|hot_start|set_hooks|"
    r"set_event_checks|cycle|vars|is_ended|current_state_id|"
    r"current_state_path|current_state_name|last_error|dsl_source)\b"
)
_WRAPPER_HEADER_BASENAME = "machine.hpp"
_CONTEXT_TEMPLATE_MAP = {"cpp": "c", "cpp_poll": "c_poll"}

# Harness sections: wrapper aliases, hook/event recording helpers, JSON writers,
# initialization or hot-start code, then shared fixture step execution.
_CPP_TEMPLATE = r"""
#include "machine.hpp"

#include <stdio.h>
#include <string.h>

typedef pyfcstm_generated::{{ context.machine_class_name }}_cpp::MachineWrapper Wrapper;

static Wrapper::Hooks hooks = {{ context.machine_class_name.upper() }}_HOOKS_INIT;
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
{% for variable in context.variables %}    Wrapper::Int {{ variable.field }}_is_int;
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

static void write_machine_int(FILE *out, Wrapper::Int value)
{
    char digits[64];
    size_t count = 0u;
    Wrapper::Int quotient = value;

    if (quotient == 0) {
        fputc('0', out);
        return;
    }
    if (quotient < 0) {
        fputc('-', out);
        while (quotient != 0) {
            Wrapper::Int next = quotient / 10;
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

static void write_vars(FILE *out, const Wrapper::Vars *vars)
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
static void record_hook(Wrapper::Machine *machine_ptr, const Wrapper::ExecutionContext *ctx, void *user_data)
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

static int run_cycle(Wrapper *wrapper, const Wrapper::EventId *events, size_t event_count)
{
    return wrapper->cycle(events, event_count);
}

static void write_observation(FILE *out, Wrapper *wrapper, int step_index, int cycle_index, const char **event_names, size_t event_count, const char *last_error)
{
    size_t i;
    const char *state_path = wrapper->current_state_path();
    const Wrapper::Vars *vars = wrapper->vars();
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
        Wrapper::Vars initial_vars;
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
{% else %}{% if step.events %}        Wrapper::EventId event_ids[] = {
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

# The poll harness mirrors ``_CPP_TEMPLATE`` but routes events through
# ``set_event_checks()`` before invoking the zero-argument wrapper cycle.
_CPP_POLL_TEMPLATE = r"""
#include "machine.hpp"

#include <stdio.h>
#include <string.h>

typedef pyfcstm_generated::{{ context.machine_class_name }}_cpp_poll::MachineWrapper Wrapper;

static Wrapper::Hooks hooks = {{ context.machine_class_name.upper() }}_HOOKS_INIT;
static Wrapper::EventId active_events[64];
static size_t active_event_count = 0u;
static Wrapper::EventChecks event_checks = {{ context.machine_class_name.upper() }}_EVENT_CHECKS_INIT;

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
{% for variable in context.variables %}    Wrapper::Int {{ variable.field }}_is_int;
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

static void write_machine_int(FILE *out, Wrapper::Int value)
{
    char digits[64];
    size_t count = 0u;
    Wrapper::Int quotient = value;

    if (quotient == 0) {
        fputc('0', out);
        return;
    }
    if (quotient < 0) {
        fputc('-', out);
        while (quotient != 0) {
            Wrapper::Int next = quotient / 10;
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

static void write_vars(FILE *out, const Wrapper::Vars *vars)
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
static void record_hook(Wrapper::Machine *machine_ptr, const Wrapper::ExecutionContext *ctx, void *user_data)
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
static int check_event(Wrapper::Machine *machine_ptr, const Wrapper::EventContext *ctx, void *user_data)
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

static int run_cycle(Wrapper *wrapper, const Wrapper::EventId *events, size_t event_count)
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
    const Wrapper::Vars *vars = wrapper->vars();
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
        Wrapper::Vars initial_vars;
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
{% else %}{% if step.events %}        Wrapper::EventId event_ids[] = {
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

_TEMPLATE_TEXT_MAP = {"cpp": _CPP_TEMPLATE, "cpp_poll": _CPP_POLL_TEMPLATE}

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
    """
    Validate that a C++ alignment helper received a supported template name.

    :param template_name: Candidate template name.
    :type template_name: str
    :return: ``None``.
    :rtype: None
    :raises ValueError: If ``template_name`` is not ``"cpp"`` or
        ``"cpp_poll"``.

    Example::

        >>> _validate_template_name("cpp")
    """
    if template_name not in _CONTEXT_TEMPLATE_MAP:
        raise ValueError("unsupported C++ alignment template: %r" % template_name)


def _cmake_generator_args() -> List[str]:
    """
    Return platform-specific CMake generator arguments for fixture builds.

    Windows CI uses MinGW for these generated wrapper harness tests, while
    POSIX platforms can use CMake's default generator.

    :return: Extra arguments for the CMake configure command.
    :rtype: list[str]

    Example::

        >>> isinstance(_cmake_generator_args(), list)
        True
    """
    if os.name == "nt":
        return ["-G", "MinGW Makefiles"]
    return []


def _find_cmake() -> str:
    """
    Locate the CMake executable required by generated C++ harness tests.

    :return: Path to the ``cmake`` executable.
    :rtype: str
    :raises pytest.skip.Exception: If CMake is unavailable in the current
        environment.

    Example::

        >>> bool(_find_cmake())  # doctest: +SKIP
        True
    """
    cmake = shutil.which("cmake")
    if cmake is None:
        pytest.skip("cmake is required for generated C++ alignment tests.")
    return cmake


def _environment() -> Environment:
    """
    Create the strict Jinja2 environment used for harness source templates.

    :return: Jinja2 environment with the ``tojson`` filter registered.
    :rtype: jinja2.Environment

    Example::

        >>> env = _environment()
        >>> env.from_string('{{ value | tojson }}').render(value='x')
        '"x"'
    """
    env = Environment(
        undefined=StrictUndefined,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["tojson"] = json.dumps
    return env


def _render_generated_template(
    template_name: str, case: SemanticCase, generated_dir: str
) -> None:
    """
    Render a built-in C++ wrapper template for one semantic fixture case.

    :param template_name: Template under test, either ``"cpp"`` or
        ``"cpp_poll"``.
    :type template_name: str
    :param case: Shared semantic fixture case used to build the state machine.
    :type case: test.testings.simulate_semantics.SemanticCase
    :param generated_dir: Directory where generated template files are written.
    :type generated_dir: str
    :return: ``None``.
    :rtype: None

    Example::

        >>> from test.testings.simulate_semantics import load_semantic_case
        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> case.id
        'design_basic_simple_transition'
    """
    model = simulate_semantics.build_state_machine_from_case(case)
    template_root = os.path.join(os.path.dirname(generated_dir), "template-src")
    template_dir = extract_template(template_name, template_root)
    StateMachineCodeRenderer(template_dir).render(model=model, output_dir=generated_dir)


def _render_harness(template_name: str, case: SemanticCase, harness_path: str) -> None:
    """
    Render the C++98 fixture harness for one generated wrapper template.

    The C++ wrapper templates reuse the existing C-family harness context, but
    the mapping is explicit so new template variants cannot silently fall back
    to the plain C context.

    :param template_name: Template under test, either ``"cpp"`` or
        ``"cpp_poll"``.
    :type template_name: str
    :param case: Shared semantic fixture case.
    :type case: test.testings.simulate_semantics.SemanticCase
    :param harness_path: Path where ``harness.cpp`` is written.
    :type harness_path: str
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If the rendered harness bypasses the C++ wrapper
        entrypoint.
    :raises ValueError: If ``template_name`` is unsupported.

    Example::

        >>> from test.testings.simulate_semantics import load_semantic_case
        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> case.id
        'design_basic_simple_transition'
    """
    _validate_template_name(template_name)
    context_template_name = _CONTEXT_TEMPLATE_MAP[template_name]
    base_context = build_harness_context(context_template_name, case)
    context = replace(base_context, template_name=template_name)
    template_text = _TEMPLATE_TEXT_MAP[template_name]
    rendered = _environment().from_string(template_text).render(context=context)
    _assert_wrapper_only_harness(rendered)
    os.makedirs(os.path.dirname(harness_path), exist_ok=True)
    with open(harness_path, "w", encoding="utf-8") as f:
        f.write(rendered)


def _splice_cpp_line_continuations(source: str) -> str:
    """
    Remove C/C++ backslash-newline continuations before source checks.

    The C preprocessor performs this splice before it recognizes comments or
    directives. The wrapper-only guard mirrors that phase so split forms with
    a trailing backslash before a newline cannot hide a direct ``machine.h``
    include.

    :param source: C++ source text to inspect.
    :type source: str
    :return: Source text after line-continuation splicing.
    :rtype: str

    Example::

        >>> _splice_cpp_line_continuations('#\\\ninclude "machine.hpp"\n')
        '#include "machine.hpp"\n'
    """
    return _LINE_CONTINUATION_RE.sub("", source)


def _mask_cpp_comments_and_literals(source: str, mask_literals: bool) -> str:
    """
    Replace C++ comments and optionally literals with whitespace.

    Newlines are preserved so preprocessor directive checks still operate on
    the same logical lines after block comments are removed. Include checks keep
    literals intact because header names live in ``#include "..."`` tokens;
    symbol checks mask literals so diagnostic strings cannot satisfy or trip
    wrapper-only guard patterns.

    :param source: C++ source text to inspect.
    :type source: str
    :param mask_literals: Whether string and character literals should also be
        replaced by whitespace.
    :type mask_literals: bool
    :return: Source text with comments, and optionally literals, masked.
    :rtype: str

    Example::

        >>> _mask_cpp_comments_and_literals('// #include "machine.hpp"\n', False)
        '\n'
        >>> _mask_cpp_comments_and_literals('"RootMachine_cycle"', True)
        '                   '
    """
    source = _splice_cpp_line_continuations(source)
    output = []
    index = 0
    length = len(source)
    while index < length:
        char = source[index]
        next_char = source[index + 1] if index + 1 < length else ""

        if char == "/" and next_char == "/":
            index += 2
            while index < length and source[index] != "\n":
                index += 1
            if index < length:
                output.append("\n")
                index += 1
        elif char == "/" and next_char == "*":
            output.append(" ")
            output.append(" ")
            index += 2
            while index < length:
                current = source[index]
                following = source[index + 1] if index + 1 < length else ""
                if current == "*" and following == "/":
                    output.append(" ")
                    output.append(" ")
                    index += 2
                    break
                output.append("\n" if current == "\n" else " ")
                index += 1
        elif mask_literals and char in {'"', "'"}:
            quote = char
            output.append(" ")
            index += 1
            while index < length:
                current = source[index]
                output.append("\n" if current == "\n" else " ")
                index += 1
                if current == "\\" and index < length:
                    escaped = source[index]
                    output.append("\n" if escaped == "\n" else " ")
                    index += 1
                elif current == quote:
                    break
        else:
            output.append(char)
            index += 1
    return "".join(output)


def _iter_include_targets(source: str) -> List[str]:
    """
    Return literal include targets from comment-masked C++ source.

    Macro include directives are represented by an empty string so callers can
    reject them conservatively without implementing a preprocessor.

    :param source: C++ source text to inspect.
    :type source: str
    :return: Include targets; ``""`` means a non-literal include directive.
    :rtype: list[str]

    Example::

        >>> _iter_include_targets('#include "machine.hpp"\n')
        ['machine.hpp']
        >>> _iter_include_targets('#include HEADER\n')
        ['']
    """
    directive_source = _mask_cpp_comments_and_literals(source, mask_literals=False)
    targets = []
    for match in _INCLUDE_DIRECTIVE_RE.finditer(directive_source):
        raw_target = match.group("target").strip()
        literal_match = _INCLUDE_LITERAL_RE.fullmatch(raw_target)
        if literal_match:
            targets.append(literal_match.group(1) or literal_match.group(2))
        else:
            targets.append("")
    return targets


def _has_wrapper_header_include(source: str) -> bool:
    """
    Return whether a harness directly includes the C++ wrapper header.

    The check uses preprocessor include directives rather than substring
    matching, so comments and string literals cannot satisfy the wrapper-entry
    contract accidentally.

    :param source: Rendered C++ harness source.
    :type source: str
    :return: Whether the source includes ``machine.hpp`` through a directive.
    :rtype: bool

    Example::

        >>> _has_wrapper_header_include('#include "machine.hpp"\n')
        True
        >>> _has_wrapper_header_include('// #include "machine.hpp"\n')
        False
    """
    for target in _iter_include_targets(source):
        normalized_target = target.replace("\\", "/")
        if os.path.basename(normalized_target).lower() == _WRAPPER_HEADER_BASENAME:
            return True
    return False


def _has_direct_machine_header_include(source: str) -> bool:
    """
    Return whether a harness directly includes the generated C header.

    Direct harness entry must go through ``machine.hpp``. This helper rejects
    quote, angle-bracket, and relative include spellings whose normalized
    basename is ``machine.h`` while leaving ordinary standard-library includes
    untouched.

    :param source: Rendered C++ harness source.
    :type source: str
    :return: Whether the source directly includes ``machine.h``.
    :rtype: bool

    Example::

        >>> _has_direct_machine_header_include('#include "machine.h"\n')
        True
        >>> _has_direct_machine_header_include('#include "machine.hpp"\n')
        False
    """
    for target in _iter_include_targets(source):
        normalized_target = target.replace("\\", "/")
        if os.path.basename(normalized_target).lower() == "machine.h":
            return True
    return False


def _assert_wrapper_only_harness(source: str) -> None:
    """
    Assert that generated fixture harnesses enter through the C++ wrapper.

    Fixture-alignment harnesses are allowed to include only ``machine.hpp``
    directly. They may observe state through ``Wrapper::...`` aliases and
    wrapper methods, but they must not directly include ``machine.h``, use macro
    includes, use token-paste macros, bind C runtime typedef names, or call
    generated ``...Machine_*`` C functions.

    .. note::
       This is a conservative source-level gate, not a complete C++ parser or
       preprocessor. It masks comments and string literals before symbol checks,
       rejects every non-literal ``#include`` directive, and rejects token-paste
       macros because fixture harnesses do not need those constructs.

    :param source: Rendered C++ harness source.
    :type source: str
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If the harness bypasses the C++ wrapper entrypoint.

    Example::

        >>> _assert_wrapper_only_harness('#include "machine.hpp"\\n')
    """
    include_targets = _iter_include_targets(source)
    symbol_source = _mask_cpp_comments_and_literals(source, mask_literals=True)
    assert include_targets and all(include_targets)
    assert _has_wrapper_header_include(source)
    assert not _has_direct_machine_header_include(source)
    assert not _TOKEN_PASTE_RE.search(symbol_source)
    assert not _NATIVE_HANDLE_CALL_RE.search(symbol_source)
    assert not _DIRECT_C_TYPE_RE.search(symbol_source)
    assert not _DIRECT_C_API_RE.search(symbol_source)


def _render_cmake(artifacts: CppAlignmentArtifacts, harness_path: str) -> None:
    """
    Render the CMake project that compiles a generated wrapper harness.

    The project always builds the generated C core, generated C++ wrapper, and
    synthetic fixture harness together so fixture execution validates the same
    wrapper entrypoint that downstream users compile.

    :param artifacts: Artifact paths for this fixture run.
    :type artifacts: CppAlignmentArtifacts
    :param harness_path: Path to the rendered ``harness.cpp`` source file.
    :type harness_path: str
    :return: ``None``.
    :rtype: None

    Example::

        >>> artifacts = CppAlignmentArtifacts("cpp", "demo", "/tmp/a", "/tmp/a/g", "/tmp/a/h", "/tmp/a/b", "/tmp/a/o.jsonl")
        >>> artifacts.harness_dir
        '/tmp/a/h'
    """
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
    """
    Create generated sources, harness files, and build directories for a case.

    :param template_name: Template under test, either ``"cpp"`` or
        ``"cpp_poll"``.
    :type template_name: str
    :param case: Shared semantic fixture case.
    :type case: test.testings.simulate_semantics.SemanticCase
    :param artifact_root: Root directory for all run artifacts.
    :type artifact_root: str
    :return: Paths for generated sources, harness files, build output, and
        observations.
    :rtype: CppAlignmentArtifacts
    :raises AssertionError: If the generated harness bypasses wrapper APIs.
    :raises ValueError: If ``template_name`` is unsupported.

    Example::

        >>> from test.testings.simulate_semantics import load_semantic_case
        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> case.id
        'design_basic_simple_transition'
    """
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
    """
    Run a command and persist command, stdout, and stderr logs.

    :param command: Command arguments to execute.
    :type command: collections.abc.Sequence[str]
    :param cwd: Working directory for the child process.
    :type cwd: str
    :param stdout_path: File path receiving captured standard output.
    :type stdout_path: str
    :param stderr_path: File path receiving captured standard error.
    :type stderr_path: str
    :return: Completed process object with captured output.
    :rtype: subprocess.CompletedProcess

    Example::

        >>> import tempfile
        >>> root = tempfile.mkdtemp()
        >>> result = _run_command(["python", "-c", "print('ok')"], root, os.path.join(root, "x.stdout.txt"), os.path.join(root, "x.stderr.txt"))
        >>> result.returncode
        0
    """
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
    """
    Return a bounded diagnostic tail for command output.

    :param output: Captured command output.
    :type output: str
    :param limit: Maximum number of trailing characters to keep, defaults to
        ``4000``.
    :type limit: int, optional
    :return: Full output when short enough, otherwise a truncation marker plus
        the trailing output segment.
    :rtype: str

    Example::

        >>> _command_output_tail("abcdef", limit=3)
        '...<truncated>\\ndef'
    """
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
    """
    Raise an assertion with persisted log paths and bounded output tails.

    :param stage: Human-readable stage name, such as ``"CMake build"``.
    :type stage: str
    :param command: Command arguments that failed.
    :type command: collections.abc.Sequence[str]
    :param completed: Completed process returned by :func:`_run_command`.
    :type completed: subprocess.CompletedProcess
    :param stdout_path: Path to the captured stdout log.
    :type stdout_path: str
    :param stderr_path: Path to the captured stderr log.
    :type stderr_path: str
    :return: ``None``.
    :rtype: None
    :raises AssertionError: Always, with command diagnostics.

    Example::

        >>> import subprocess
        >>> proc = subprocess.CompletedProcess(["false"], 1, "", "boom")
        >>> _fail_command("demo", ["false"], proc, "out", "err")
        Traceback (most recent call last):
        ...
        AssertionError: demo failed with return code 1.
        ...
    """
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
    """
    Locate the generated C++ harness executable under a CMake build tree.

    :param build_dir: CMake build directory.
    :type build_dir: str
    :return: Path to the harness executable.
    :rtype: str
    :raises FileNotFoundError: If no platform-specific executable candidate
        exists.

    Example::

        >>> _find_executable("/path/that/does/not/exist")
        Traceback (most recent call last):
        ...
        FileNotFoundError: Cannot find C++ shared fixture harness executable under '/path/that/does/not/exist'.
    """
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
    """
    Configure, build, and execute a generated C++ fixture harness.

    :param artifacts: Paths produced by :func:`_prepare_artifacts`.
    :type artifacts: CppAlignmentArtifacts
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If CMake configure, CMake build, or harness
        execution exits with a non-zero status.
    :raises FileNotFoundError: If the harness executable cannot be located
        after a successful build.
    :raises pytest.skip.Exception: If CMake is unavailable.

    Example::

        >>> artifacts = CppAlignmentArtifacts("cpp", "demo", "/tmp/a", "/tmp/a/g", "/tmp/a/h", "/tmp/a/b", "/tmp/a/o.jsonl")
        >>> artifacts.template_name
        'cpp'
    """
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

        >>> from test.testings.simulate_semantics import load_semantic_case
        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> case.id
        'design_basic_simple_transition'
    """
    _validate_template_name(template_name)
    artifacts = _prepare_artifacts(template_name, case, artifact_root)
    _build_and_run(artifacts)
    observations = read_observations_jsonl(artifacts.observations_path)
    assert_observations_match_case(template_name, case, observations)
    return artifacts
