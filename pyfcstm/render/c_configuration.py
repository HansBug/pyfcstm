"""
C configuration type and text functions for the built-in C runtime template.

A configuration answers "where is the machine?" for a model that declares
regions, and :class:`pyfcstm.model.configuration.Configuration` is its
simulator form. This module emits the matching C code for one model: a flat
value type, queries over it and, unless the target leaves them out, a text
formatter and parser that agree byte for byte with the simulator's text form.

The emitted C type stores the deepest active state outside every region in
``at`` and one slot per region in ``regions``. A slot holds the deepest active
state of that region's branch, a *pending* marker (zero, the region waits for
its initial transition) or a *done* marker (the region has completed). The slot
of a region whose owner is not active is always pending, so a valid
configuration has exactly one representation and two configurations can be
compared with ``memcmp``. Regions are numbered owner by owner in
:meth:`pyfcstm.model.model.StateMachine.walk_states` order and, inside one
owner, in declaration order; states use the ids the C template already
assigns, which follow the same walk.

The emitted functions are C99, use neither the heap nor any libc function
outside ``<string.h>``, and the header part also compiles as C++98. Everything
that needs names (``..._format``, ``..._parse`` and the name tables) sits
inside ``#ifndef PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT`` so that a small
target can drop it and keep the type, the validator and the queries.

The functions that connect a configuration to a running machine are not
emitted here; the machine runtime fills a configuration from its own state
(``..._get_configuration``) and starts from a validated one
(``..._hot_start_at``) using the type and validator emitted by this module.

The module contains:

* :func:`render_c_configuration_header` - Types, macros and declarations
* :func:`render_c_configuration_source` - Tables and function definitions

Example::

    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('''
    ... state Root {
    ...     [*] -> Run;
    ...     state Run {
    ...         region Motion { [*] -> Stop; state Stop; state Move; Stop -> Move :: Go; }
    ...         region Guard { [*] -> Watch; state Watch; }
    ...     }
    ... }
    ... ''')
    >>> header = render_c_configuration_header(model, 'RootMachine', 'ROOT_MACHINE')
    >>> print([line for line in header.splitlines() if line.startswith('#define ROOT_MACHINE_REGION_p')])
    ['#define ROOT_MACHINE_REGION_p4_Root_p3_Run_p6_Motion ((RootMachineRegionId)0)', '#define ROOT_MACHINE_REGION_p4_Root_p3_Run_p5_Guard ((RootMachineRegionId)1)']
"""

import re
from dataclasses import dataclass
from string import Template
from typing import List, Tuple

from ..utils import to_c_path_identifier

__all__ = [
    "render_c_configuration_header",
    "render_c_configuration_source",
]

_C_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


@dataclass(frozen=True)
class _StateRow:
    """
    Structural facts about one state, in C state id order.

    :param path: Full state path from the root state.
    :type path: Tuple[str, ...]
    :param parent: Index of the containing state, ``-1`` for the root state.
        A state directly inside a region is contained by the region's owner.
    :type parent: int
    :param scope: Index of the nearest region enclosing the state, ``-1`` for
        a state outside every region.
    :type scope: int
    :param first_region: Index of the first region the state owns, ``-1`` when
        it owns none.
    :type first_region: int
    :param region_count: Number of regions the state owns.
    :type region_count: int
    :param is_leaf: Whether the state has neither child states nor regions.
    :type is_leaf: bool
    :param depth: Number of regions between the root state and this state.
    :type depth: int
    """

    path: Tuple[str, ...]
    parent: int
    scope: int
    first_region: int
    region_count: int
    is_leaf: bool
    depth: int


@dataclass(frozen=True)
class _RegionRow:
    """
    Structural facts about one region, in C region id order.

    :param path: Full region path, the owner path plus the region name.
    :type path: Tuple[str, ...]
    :param owner: Index of the state that owns the region.
    :type owner: int
    """

    path: Tuple[str, ...]
    owner: int


def _layout(model) -> Tuple[List[_StateRow], List[_RegionRow]]:
    """
    Number the states and regions of a model the way the C runtime does.

    States are numbered in :meth:`~pyfcstm.model.model.StateMachine.walk_states`
    order, which is the order of the C template's ``..._STATE_*`` ids. Regions
    are numbered owner by owner in that same order and, inside one owner, in
    declaration order, so the regions of one owner have consecutive ids.

    :param model: State machine to number.
    :type model: pyfcstm.model.model.StateMachine
    :return: State rows and region rows, each in id order.
    :rtype: Tuple[List[_StateRow], List[_RegionRow]]
    """
    states = list(model.walk_states())
    state_index = {tuple(state.path): index for index, state in enumerate(states)}
    region_index = {}
    regions = []
    for index, state in enumerate(states):
        for region in state.regions.values():
            region_index[tuple(region.path)] = len(regions)
            regions.append(_RegionRow(path=tuple(region.path), owner=index))
    rows = []
    for state in states:
        container = tuple(state.path[:-1])
        if container in region_index:
            # Directly inside a region: contained by the region's owner.
            parent = state_index[container[:-1]]
            scope = region_index[container]
            depth = rows[parent].depth + 1
        elif container:
            parent = state_index[container]
            scope = rows[parent].scope
            depth = rows[parent].depth
        else:
            parent, scope, depth = -1, -1, 0
        owned = [region_index[tuple(region.path)] for region in state.regions.values()]
        rows.append(
            _StateRow(
                path=tuple(state.path),
                parent=parent,
                scope=scope,
                first_region=owned[0] if owned else -1,
                region_count=len(owned),
                is_leaf=bool(state.is_leaf_state),
                depth=depth,
            )
        )
    return rows, regions


def _check_names(machine_class_name: str, machine_macro_name: str) -> None:
    """
    Refuse machine names that cannot be pasted into C source.

    :param machine_class_name: Type and function prefix, such as
        ``'RootMachine'``.
    :type machine_class_name: str
    :param machine_macro_name: Macro prefix, such as ``'ROOT_MACHINE'``.
    :type machine_macro_name: str
    :return: ``None``.
    :rtype: None
    :raises ValueError: If either name is not a C identifier.
    """
    for label, value in (
        ("machine_class_name", machine_class_name),
        ("machine_macro_name", machine_macro_name),
    ):
        if not isinstance(value, str) or _C_IDENTIFIER.fullmatch(value) is None:
            raise ValueError("%s must be a C identifier, got %r." % (label, value))


def _state_macro(macro: str, path) -> str:
    """
    Spell the case-preserving C state id macro of a state path.

    :param macro: Machine macro prefix.
    :type macro: str
    :param path: Full state path.
    :type path: Tuple[str, ...]
    :return: For example ``'ROOT_MACHINE_STATE_p4_Root_p3_Run'``.
    :rtype: str
    """
    return "%s_STATE_%s" % (macro, to_c_path_identifier(path))


def _region_macro(macro: str, path) -> str:
    """
    Spell the C region id macro of a region path.

    :param macro: Machine macro prefix.
    :type macro: str
    :param path: Full region path.
    :type path: Tuple[str, ...]
    :return: For example ``'ROOT_MACHINE_REGION_p4_Root_p3_Run_p6_Motion'``.
    :rtype: str
    """
    return "%s_REGION_%s" % (macro, to_c_path_identifier(path))


_HEADER = Template("""\
/*
 * Configuration: where the machine is, as a value.
 *
 * `at` is the deepest active state outside every region. `regions[r]` belongs
 * to region `r` (see the `${MM}_REGION_*` ids): the deepest active state
 * of that region's branch, `${MM}_REGION_SLOT_DONE` once the region has
 * completed, or `${MM}_REGION_SLOT_PENDING` while it waits for its
 * initial transition. The slot of a region whose owner is not active is always
 * `${MM}_REGION_SLOT_PENDING`, so a valid configuration has exactly one
 * representation and two configurations compare with `memcmp`. A zeroed
 * configuration is the root state before its own initialization.
 *
 * Configurations are plain values: copy them freely. Queries expect a
 * configuration that `${M}_configuration_validate` accepts; on any other
 * value they return without reading outside the generated tables, but the
 * answer has no meaning.
 *
 * The text form is the pyfcstm simulator's, for example
 * `Root.Run{Motion: Move, Guard: [done]}`. Define
 * `PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT` to leave out `..._format`,
 * `..._parse` and the name tables they need.
 */
typedef int ${M}RegionId;
typedef int ${M}RegionStatus;
#define ${MM}_REGION_COUNT ${region_count}
${region_macros}#define ${MM}_REGION_SLOT_PENDING ((${M}StateId)0)
#define ${MM}_REGION_SLOT_DONE ((${M}StateId) - 1)
#define ${MM}_REGION_STATUS_INACTIVE ((${M}RegionStatus)0)
#define ${MM}_REGION_STATUS_PENDING ((${M}RegionStatus)1)
#define ${MM}_REGION_STATUS_LIVE ((${M}RegionStatus)2)
#define ${MM}_REGION_STATUS_DONE ((${M}RegionStatus)3)

typedef struct ${M}Configuration {
    ${M}StateId at; /* deepest active state outside every region */
    ${M}StateId regions[${slot_count}]; /* one slot per region${padding_note} */
} ${M}Configuration;

/* `kind` values of `${M}ConfigurationError`; one cause, one kind. */
#define ${MM}_CONFIGURATION_ERROR_NONE 0
#define ${MM}_CONFIGURATION_ERROR_ARGUMENT 1 /* a required pointer is NULL */
#define ${MM}_CONFIGURATION_ERROR_SYNTAX 2 /* text is not a well-formed configuration */
#define ${MM}_CONFIGURATION_ERROR_UNKNOWN_PATH 3 /* a path names no state or region */
#define ${MM}_CONFIGURATION_ERROR_REGION_PATH 4 /* a path ends at a region, not a state */
#define ${MM}_CONFIGURATION_ERROR_MISSING_REGION_BLOCK 5 /* a path passes through a region owner */
#define ${MM}_CONFIGURATION_ERROR_UNKNOWN_REGION 6 /* a region block names a region the state lacks */
#define ${MM}_CONFIGURATION_ERROR_DUPLICATE_REGION 7 /* a region block names a region twice */
#define ${MM}_CONFIGURATION_ERROR_TOO_DEEP 8 /* region blocks nest deeper than the model */
#define ${MM}_CONFIGURATION_ERROR_INVALID_STATE 9 /* `at` is not a state outside every region */
#define ${MM}_CONFIGURATION_ERROR_STATE_NOT_IN_REGION 10 /* a slot holds a state of another region */
#define ${MM}_CONFIGURATION_ERROR_INACTIVE_REGION 11 /* a slot no active region uses is not pending */
#define ${MM}_CONFIGURATION_ERROR_MESSAGE_SIZE 160

/*
 * Why a configuration or its text was refused. `position` is the byte offset
 * in the text (0 for `${M}_configuration_validate`). `message` is empty
 * when `PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT` is defined.
 */
typedef struct ${M}ConfigurationError {
    size_t position;
    int kind;
    char message[${MM}_CONFIGURATION_ERROR_MESSAGE_SIZE];
} ${M}ConfigurationError;

#ifdef __cplusplus
extern "C" {
#endif

/* LIVE, DONE, PENDING (owner active, not initialized) or INACTIVE (owner not active). */
${MM}_API ${M}RegionStatus ${M}_configuration_region_status(
    const ${M}Configuration *configuration,
    ${M}RegionId region);
/* Non-zero when `state` or one of its descendants is active. */
${MM}_API int ${M}_configuration_is_active(
    const ${M}Configuration *configuration,
    ${M}StateId state);
/* Write up to `capacity` active leaf ids in region order; return how many there are. */
${MM}_API size_t ${M}_configuration_leaves(
    const ${M}Configuration *configuration,
    ${M}StateId *leaves,
    size_t capacity);
/* Return SUCCESS for a well-formed configuration, else FAILURE and fill `error` (may be NULL). */
${MM}_API int ${M}_configuration_validate(
    const ${M}Configuration *configuration,
    ${M}ConfigurationError *error);

#ifndef PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT
/*
 * Write the text form and a terminating NUL into `buffer`, truncating to
 * `size`; return the full text length. An invalid configuration writes "" and
 * returns 0. `buffer` may be NULL when `size` is 0.
 */
${MM}_API size_t ${M}_configuration_format(
    const ${M}Configuration *configuration,
    char *buffer,
    size_t size);
/*
 * Parse text into `configuration` and return SUCCESS, or return FAILURE, fill
 * `error` (may be NULL) and leave `configuration` unchanged. Accepts every
 * snapshot the simulator accepts in transient mode; omitted regions are pending.
 */
${MM}_API int ${M}_configuration_parse(
    const char *text,
    ${M}Configuration *configuration,
    ${M}ConfigurationError *error);
#endif

#ifdef __cplusplus
}
#endif
""")

_SOURCE = Template("""\
#include <string.h>

/* Configuration tables: one row per state id, then one owner per region id. */
typedef struct ${M}ConfigurationStateInfo {
    int parent; /* containing state; a state directly in a region is contained by its owner */
    int scope; /* nearest enclosing region, -1 outside every region */
    int first_region; /* first owned region */
    int region_count; /* number of owned regions */
    int is_leaf; /* no child states and no regions */
} ${M}ConfigurationStateInfo;

static const ${M}ConfigurationStateInfo ${M}_configuration_states[${MM}_STATE_COUNT] = {
${state_rows}};

static const int ${M}_configuration_region_owners[${slot_count}] = {
${region_owner_rows}};

static int ${M}_configuration_slot_holds_state(${M}StateId value)
{
    return value > 0 && value < ${MM}_STATE_COUNT;
}

/* Non-zero when `state` ends a live branch: it is `at`, or the value of a live region. */
static int ${M}_configuration_heads_branch(const ${M}Configuration *configuration, ${M}StateId state)
{
    int region;
    for (;;) {
        region = ${M}_configuration_states[state].scope;
        if (region < 0) {
            return state == configuration->at;
        }
        if (configuration->regions[region] != state) {
            return 0;
        }
        state = ${M}_configuration_region_owners[region];
    }
}

static int ${M}_configuration_is_within(${M}StateId state, ${M}StateId ancestor)
{
    while (state >= 0) {
        if (state == ancestor) {
            return 1;
        }
        state = ${M}_configuration_states[state].parent;
    }
    return 0;
}

static void ${M}_configuration_collect_leaves(
    const ${M}Configuration *configuration,
    ${M}StateId state,
    ${M}StateId *leaves,
    size_t capacity,
    size_t *count)
{
    const ${M}ConfigurationStateInfo *info = &${M}_configuration_states[state];
    int region;
    ${M}StateId value;
    if (info->is_leaf) {
        if (*count < capacity) {
            leaves[*count] = state;
        }
        ++*count;
    }
    for (region = info->first_region; region < info->first_region + info->region_count; ++region) {
        value = configuration->regions[region];
        /* The scope test keeps an invalid value from walking back up the tree. */
        if (${M}_configuration_slot_holds_state(value) && ${M}_configuration_states[value].scope == region) {
            ${M}_configuration_collect_leaves(configuration, value, leaves, capacity, count);
        }
    }
}

${MM}_API ${M}RegionStatus ${M}_configuration_region_status(
    const ${M}Configuration *configuration,
    ${M}RegionId region)
{
    ${M}StateId value;
    if (configuration == NULL || region < 0 || region >= ${MM}_REGION_COUNT
        || configuration->at < 0 || configuration->at >= ${MM}_STATE_COUNT) {
        return ${MM}_REGION_STATUS_INACTIVE;
    }
    value = configuration->regions[region];
    if (value == ${MM}_REGION_SLOT_DONE) {
        return ${MM}_REGION_STATUS_DONE;
    }
    if (value != ${MM}_REGION_SLOT_PENDING) {
        return ${MM}_REGION_STATUS_LIVE;
    }
    if (${M}_configuration_heads_branch(configuration, ${M}_configuration_region_owners[region])) {
        return ${MM}_REGION_STATUS_PENDING;
    }
    return ${MM}_REGION_STATUS_INACTIVE;
}

${MM}_API int ${M}_configuration_is_active(
    const ${M}Configuration *configuration,
    ${M}StateId state)
{
    int region;
    if (configuration == NULL || state < 0 || state >= ${MM}_STATE_COUNT
        || configuration->at < 0 || configuration->at >= ${MM}_STATE_COUNT) {
        return 0;
    }
    if (${M}_configuration_is_within(configuration->at, state)) {
        return 1;
    }
    for (region = 0; region < ${MM}_REGION_COUNT; ++region) {
        if (${M}_configuration_slot_holds_state(configuration->regions[region])
            && ${M}_configuration_is_within(configuration->regions[region], state)) {
            return 1;
        }
    }
    return 0;
}

${MM}_API size_t ${M}_configuration_leaves(
    const ${M}Configuration *configuration,
    ${M}StateId *leaves,
    size_t capacity)
{
    size_t count = 0;
    if (configuration == NULL || configuration->at < 0 || configuration->at >= ${MM}_STATE_COUNT) {
        return 0;
    }
    if (leaves == NULL) {
        capacity = 0;
    }
    ${M}_configuration_collect_leaves(configuration, configuration->at, leaves, capacity, &count);
    return count;
}

#ifndef PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT
static const char *const ${M}_configuration_state_names[${MM}_STATE_COUNT] = {
${state_name_rows}};

static const char *const ${M}_configuration_region_names[${slot_count}] = {
${region_name_rows}};

/* Bounded text sink: counts every byte, stores what fits before the NUL. */
typedef struct ${M}ConfigurationWriter {
    char *buffer;
    size_t size;
    size_t length;
} ${M}ConfigurationWriter;

static void ${M}_configuration_put(${M}ConfigurationWriter *writer, const char *text, size_t length)
{
    size_t index;
    for (index = 0; index < length; ++index) {
        if (writer->length + 1 < writer->size) {
            writer->buffer[writer->length] = text[index];
        }
        ++writer->length;
    }
}

static void ${M}_configuration_put_text(${M}ConfigurationWriter *writer, const char *text)
{
    ${M}_configuration_put(writer, text, strlen(text));
}

static void ${M}_configuration_finish(${M}ConfigurationWriter *writer)
{
    if (writer->size > 0) {
        writer->buffer[writer->length < writer->size ? writer->length : writer->size - 1] = '\\0';
    }
}

static void ${M}_configuration_put_number(${M}ConfigurationWriter *writer, size_t value, int negative)
{
    char digits[24];
    size_t used = 0;
    if (negative) {
        ${M}_configuration_put(writer, "-", 1);
    }
    do {
        digits[sizeof(digits) - 1 - used] = (char)('0' + (int)(value % 10));
        ++used;
        value /= 10;
    } while (value > 0);
    ${M}_configuration_put(writer, digits + sizeof(digits) - used, used);
}

/* Dotted path of `state`, relative to `region`, or from the root when `region` is -1. */
static void ${M}_configuration_put_path(${M}ConfigurationWriter *writer, ${M}StateId state, int region)
{
    const ${M}ConfigurationStateInfo *info = &${M}_configuration_states[state];
    int container = info->scope >= 0 && info->parent == ${M}_configuration_region_owners[info->scope]
        ? info->scope
        : -1;
    if (container < 0 ? info->parent >= 0 : container != region) {
        ${M}_configuration_put_path(writer, info->parent, region);
        ${M}_configuration_put(writer, ".", 1);
        if (container >= 0) {
            ${M}_configuration_put_text(writer, ${M}_configuration_region_names[container]);
            ${M}_configuration_put(writer, ".", 1);
        }
    }
    ${M}_configuration_put_text(writer, ${M}_configuration_state_names[state]);
}

static void ${M}_configuration_put_region_path(${M}ConfigurationWriter *writer, int region)
{
    ${M}_configuration_put_path(writer, ${M}_configuration_region_owners[region], -1);
    ${M}_configuration_put(writer, ".", 1);
    ${M}_configuration_put_text(writer, ${M}_configuration_region_names[region]);
}

static void ${M}_configuration_put_block(
    ${M}ConfigurationWriter *writer,
    const ${M}Configuration *configuration,
    ${M}StateId state)
{
    const ${M}ConfigurationStateInfo *info = &${M}_configuration_states[state];
    int region;
    ${M}StateId value;
    if (info->region_count == 0) {
        return;
    }
    ${M}_configuration_put(writer, "{", 1);
    for (region = info->first_region; region < info->first_region + info->region_count; ++region) {
        if (region > info->first_region) {
            ${M}_configuration_put(writer, ", ", 2);
        }
        ${M}_configuration_put_text(writer, ${M}_configuration_region_names[region]);
        ${M}_configuration_put(writer, ": ", 2);
        value = configuration->regions[region];
        if (value == ${MM}_REGION_SLOT_DONE) {
            ${M}_configuration_put(writer, "[done]", 6);
        } else if (value == ${MM}_REGION_SLOT_PENDING) {
            ${M}_configuration_put(writer, "[init]", 6);
        } else {
            ${M}_configuration_put_path(writer, value, region);
            ${M}_configuration_put_block(writer, configuration, value);
        }
    }
    ${M}_configuration_put(writer, "}", 1);
}

/* Start an error report; the returned writer appends to `error->message`. */
static ${M}ConfigurationWriter ${M}_configuration_report(
    ${M}ConfigurationError *error,
    int kind,
    size_t position)
{
    ${M}ConfigurationWriter writer;
    writer.buffer = NULL;
    writer.size = 0;
    writer.length = 0;
    if (error != NULL) {
        memset(error, 0, sizeof(*error));
        error->kind = kind;
        error->position = position;
        writer.buffer = error->message;
        writer.size = sizeof(error->message);
    }
    return writer;
}
#endif

static int ${M}_configuration_structure_error(
    ${M}ConfigurationError *error,
    int kind,
    int region,
    ${M}StateId value)
{
#ifndef PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT
    ${M}ConfigurationWriter writer = ${M}_configuration_report(error, kind, 0);
    if (kind == ${MM}_CONFIGURATION_ERROR_ARGUMENT) {
        ${M}_configuration_put_text(&writer, "Configuration pointer is NULL.");
    } else if (kind == ${MM}_CONFIGURATION_ERROR_INVALID_STATE) {
        ${M}_configuration_put_text(&writer, "Configuration at = ");
        ${M}_configuration_put_number(&writer, value < 0 ? (size_t)(-(value + 1)) + 1 : (size_t)value, value < 0);
        ${M}_configuration_put_text(&writer, " is not a state outside every region.");
    } else if (region < 0) {
        ${M}_configuration_put_text(&writer, "Unused region slot must be pending.");
    } else {
        ${M}_configuration_put_text(&writer, "Region ");
        ${M}_configuration_put_region_path(&writer, region);
        if (kind == ${MM}_CONFIGURATION_ERROR_STATE_NOT_IN_REGION) {
            ${M}_configuration_put_text(&writer, " holds ");
            ${M}_configuration_put_number(&writer, value < 0 ? (size_t)(-(value + 1)) + 1 : (size_t)value, value < 0);
            ${M}_configuration_put_text(&writer, ", which is not a state of that region.");
        } else {
            ${M}_configuration_put_text(&writer, " is not active, so its slot must be pending.");
        }
    }
    ${M}_configuration_finish(&writer);
#else
    (void)region;
    (void)value;
    if (error != NULL) {
        memset(error, 0, sizeof(*error));
        error->kind = kind;
    }
#endif
    return ${MM}_FAILURE;
}

${MM}_API int ${M}_configuration_validate(
    const ${M}Configuration *configuration,
    ${M}ConfigurationError *error)
{
    int region;
    ${M}StateId value;
    if (configuration == NULL) {
        return ${M}_configuration_structure_error(error, ${MM}_CONFIGURATION_ERROR_ARGUMENT, -1, 0);
    }
    if (configuration->at < 0 || configuration->at >= ${MM}_STATE_COUNT
        || ${M}_configuration_states[configuration->at].scope >= 0) {
        return ${M}_configuration_structure_error(
            error, ${MM}_CONFIGURATION_ERROR_INVALID_STATE, -1, configuration->at);
    }
    /* Outer regions have smaller ids, so every slot an owner test reads is already checked. */
    for (region = 0; region < ${MM}_REGION_COUNT; ++region) {
        value = configuration->regions[region];
        if (value == ${MM}_REGION_SLOT_PENDING) {
            continue;
        }
        if (value != ${MM}_REGION_SLOT_DONE
            && !(${M}_configuration_slot_holds_state(value) && ${M}_configuration_states[value].scope == region)) {
            return ${M}_configuration_structure_error(
                error, ${MM}_CONFIGURATION_ERROR_STATE_NOT_IN_REGION, region, value);
        }
        if (!${M}_configuration_heads_branch(configuration, ${M}_configuration_region_owners[region])) {
            return ${M}_configuration_structure_error(
                error, ${MM}_CONFIGURATION_ERROR_INACTIVE_REGION, region, value);
        }
    }
${padding_check}    return ${MM}_SUCCESS;
}

#ifndef PYFCSTM_GENERATED_NO_CONFIGURATION_TEXT
${MM}_API size_t ${M}_configuration_format(
    const ${M}Configuration *configuration,
    char *buffer,
    size_t size)
{
    ${M}ConfigurationWriter writer;
    writer.buffer = buffer;
    writer.size = buffer == NULL ? 0 : size;
    writer.length = 0;
    if (${M}_configuration_validate(configuration, NULL) != ${MM}_SUCCESS) {
        ${M}_configuration_finish(&writer);
        return 0;
    }
    ${M}_configuration_put_path(&writer, configuration->at, -1);
    ${M}_configuration_put_block(&writer, configuration, configuration->at);
    ${M}_configuration_finish(&writer);
    return writer.length;
}

#define ${MM}_CONFIGURATION_TOKEN_END 0
#define ${MM}_CONFIGURATION_TOKEN_NAME 1
#define ${MM}_CONFIGURATION_TOKEN_INIT 2
#define ${MM}_CONFIGURATION_TOKEN_DONE 3
#define ${MM}_CONFIGURATION_TOKEN_MARK 4

/*
 * Two passes over the text, as the simulator does: the first checks only the
 * syntax, the second resolves names against the model and fills `work`.
 */
typedef struct ${M}ConfigurationParser {
    const char *text;
    size_t position; /* byte offset of the current token */
    size_t length; /* byte length of the current token */
    int token;
    int resolve; /* 0: syntax pass, 1: model pass */
    ${M}Configuration *work;
    unsigned char *seen;
    ${M}ConfigurationError *error;
} ${M}ConfigurationParser;

/* Byte length of the whitespace character at `text`, 0 if there is none (Python str.isspace). */
static size_t ${M}_configuration_space(const unsigned char *text)
{
    if (text[0] == ' ' || (text[0] >= 0x09 && text[0] <= 0x0D) || (text[0] >= 0x1C && text[0] <= 0x1F)) {
        return 1;
    }
    if (text[0] == 0xC2 && (text[1] == 0x85 || text[1] == 0xA0)) {
        return 2;
    }
    if ((text[0] == 0xE1 && text[1] == 0x9A && text[2] == 0x80)
        || (text[0] == 0xE2 && text[1] == 0x80
            && ((text[2] >= 0x80 && text[2] <= 0x8A) || text[2] == 0xA8 || text[2] == 0xA9 || text[2] == 0xAF))
        || (text[0] == 0xE2 && text[1] == 0x81 && text[2] == 0x9F)
        || (text[0] == 0xE3 && text[1] == 0x80 && text[2] == 0x80)) {
        return 3;
    }
    return 0;
}

static int ${M}_configuration_name_start(char character)
{
    return (character >= 'A' && character <= 'Z') || (character >= 'a' && character <= 'z') || character == '_';
}

static void ${M}_configuration_scan(${M}ConfigurationParser *parser, size_t offset)
{
    const char *text = parser->text;
    size_t skip;
    while ((skip = ${M}_configuration_space((const unsigned char *)text + offset)) > 0) {
        offset += skip;
    }
    parser->position = offset;
    parser->length = 1;
    if (text[offset] == '\\0') {
        parser->token = ${MM}_CONFIGURATION_TOKEN_END;
        parser->length = 0;
    } else if (strncmp(text + offset, "[init]", 6) == 0) {
        parser->token = ${MM}_CONFIGURATION_TOKEN_INIT;
        parser->length = 6;
    } else if (strncmp(text + offset, "[done]", 6) == 0) {
        parser->token = ${MM}_CONFIGURATION_TOKEN_DONE;
        parser->length = 6;
    } else if (${M}_configuration_name_start(text[offset])) {
        parser->token = ${MM}_CONFIGURATION_TOKEN_NAME;
        while (${M}_configuration_name_start(text[offset + parser->length])
               || (text[offset + parser->length] >= '0' && text[offset + parser->length] <= '9')) {
            ++parser->length;
        }
    } else {
        /* One character; a UTF-8 sequence counts as one, as the simulator reads code points. */
        parser->token = ${MM}_CONFIGURATION_TOKEN_MARK;
        if ((unsigned char)text[offset] >= 0xC0) {
            while (((unsigned char)text[offset + parser->length] & 0xC0) == 0x80) {
                ++parser->length;
            }
        }
    }
}

static void ${M}_configuration_next(${M}ConfigurationParser *parser)
{
    ${M}_configuration_scan(parser, parser->position + parser->length);
}

static int ${M}_configuration_at_mark(const ${M}ConfigurationParser *parser, char mark)
{
    return parser->token == ${MM}_CONFIGURATION_TOKEN_MARK && parser->text[parser->position] == mark;
}

static int ${M}_configuration_token_is(const ${M}ConfigurationParser *parser, const char *name)
{
    return strlen(name) == parser->length && strncmp(parser->text + parser->position, name, parser->length) == 0;
}

static void ${M}_configuration_put_token(${M}ConfigurationWriter *writer, const ${M}ConfigurationParser *parser)
{
    ${M}_configuration_put(writer, "'", 1);
    if (parser->length > 40) {
        ${M}_configuration_put(writer, parser->text + parser->position, 37);
        ${M}_configuration_put(writer, "...", 3);
    } else {
        ${M}_configuration_put(writer, parser->text + parser->position, parser->length);
    }
    ${M}_configuration_put(writer, "'", 1);
}

static void ${M}_configuration_put_position(${M}ConfigurationWriter *writer, size_t position)
{
    ${M}_configuration_put_text(writer, " at byte ");
    ${M}_configuration_put_number(writer, position, 0);
}

static int ${M}_configuration_expected(${M}ConfigurationParser *parser, const char *expected)
{
    ${M}ConfigurationWriter writer = ${M}_configuration_report(
        parser->error, ${MM}_CONFIGURATION_ERROR_SYNTAX, parser->position);
    ${M}_configuration_put_text(&writer, "Expected ");
    ${M}_configuration_put_text(&writer, expected);
    ${M}_configuration_put_position(&writer, parser->position);
    ${M}_configuration_put_text(&writer, ", got ");
    if (parser->token == ${MM}_CONFIGURATION_TOKEN_END) {
        ${M}_configuration_put_text(&writer, "end of input");
    } else {
        ${M}_configuration_put_token(&writer, parser);
    }
    ${M}_configuration_put(&writer, ".", 1);
    ${M}_configuration_finish(&writer);
    return ${MM}_FAILURE;
}

/* A model error about the token at `parser`, or about the state `state` when it is not -1. */
static int ${M}_configuration_refuse(
    ${M}ConfigurationParser *parser,
    int kind,
    size_t position,
    const char *what,
    ${M}StateId state)
{
    ${M}ConfigurationWriter writer = ${M}_configuration_report(parser->error, kind, position);
    ${M}_configuration_put_text(&writer, what);
    ${M}_configuration_put(&writer, " ", 1);
    if (state >= 0) {
        ${M}_configuration_put(&writer, "'", 1);
        ${M}_configuration_put_path(&writer, state, -1);
        ${M}_configuration_put(&writer, "'", 1);
    } else {
        ${M}_configuration_put_token(&writer, parser);
    }
    ${M}_configuration_put_position(&writer, position);
    ${M}_configuration_put(&writer, ".", 1);
    ${M}_configuration_finish(&writer);
    return ${MM}_FAILURE;
}

/* Child state named by the current token, inside `region` when it is not -1, else inside `state`. */
static ${M}StateId ${M}_configuration_find_state(
    const ${M}ConfigurationParser *parser,
    ${M}StateId state,
    int region)
{
    ${M}StateId candidate;
    if (region >= 0) {
        state = ${M}_configuration_region_owners[region];
    }
    for (candidate = 0; candidate < ${MM}_STATE_COUNT; ++candidate) {
        if (${M}_configuration_states[candidate].parent == state
            && (region < 0 || ${M}_configuration_states[candidate].scope == region)
            && ${M}_configuration_token_is(parser, ${M}_configuration_state_names[candidate])) {
            return candidate;
        }
    }
    return -1;
}

/* Region of `state` named by the current token, or -1. */
static int ${M}_configuration_find_region(const ${M}ConfigurationParser *parser, ${M}StateId state)
{
    const ${M}ConfigurationStateInfo *info = &${M}_configuration_states[state];
    int region;
    for (region = info->first_region; region < info->first_region + info->region_count; ++region) {
        if (${M}_configuration_token_is(parser, ${M}_configuration_region_names[region])) {
            return region;
        }
    }
    return -1;
}

/*
 * One dotted path and its optional region block. `region` is the region the
 * path is relative to (-1 for the outermost path); `end` receives the state
 * the path names. Lookups run only in the model pass.
 */
static int ${M}_configuration_position(
    ${M}ConfigurationParser *parser,
    int region,
    int depth,
    ${M}StateId *end)
{
    size_t start = parser->position;
    ${M}StateId state = 0;
    ${M}StateId skipped_owner = -1;
    int in_region = region;
    int entry = -1;
    ${M}StateId child = 0;
    for (;;) {
        if (parser->token != ${MM}_CONFIGURATION_TOKEN_NAME) {
            return ${M}_configuration_expected(parser, "a configuration identifier");
        }
        if (parser->resolve) {
            if (parser->position == start && region < 0) {
                state = ${M}_configuration_token_is(parser, ${M}_configuration_state_names[0]) ? 0 : -1;
            } else if (in_region >= 0) {
                state = ${M}_configuration_find_state(parser, state, in_region);
                in_region = -1;
            } else if (${M}_configuration_states[state].region_count > 0) {
                in_region = ${M}_configuration_find_region(parser, state);
                if (skipped_owner < 0) {
                    skipped_owner = state;
                }
                if (in_region < 0) {
                    state = -1;
                }
            } else {
                state = ${M}_configuration_find_state(parser, state, -1);
            }
            if (state < 0) {
                return ${M}_configuration_refuse(
                    parser, ${MM}_CONFIGURATION_ERROR_UNKNOWN_PATH, parser->position, "Unknown name", -1);
            }
        }
        ${M}_configuration_next(parser);
        if (!${M}_configuration_at_mark(parser, '.')) {
            break;
        }
        ${M}_configuration_next(parser);
    }
    if (parser->resolve && in_region >= 0) {
        return ${M}_configuration_refuse(
            parser, ${MM}_CONFIGURATION_ERROR_REGION_PATH, start, "Path ends at a region of", state);
    }
    if (parser->resolve && skipped_owner >= 0) {
        return ${M}_configuration_refuse(
            parser, ${MM}_CONFIGURATION_ERROR_MISSING_REGION_BLOCK, start,
            "Path passes through the regions of", skipped_owner);
    }
    if (${M}_configuration_at_mark(parser, '{')) {
        ${M}_configuration_next(parser);
        for (;;) {
            if (parser->token != ${MM}_CONFIGURATION_TOKEN_NAME) {
                return ${M}_configuration_expected(parser, "a configuration identifier");
            }
            if (parser->resolve) {
                entry = ${M}_configuration_find_region(parser, state);
                if (entry < 0) {
                    return ${M}_configuration_refuse(
                        parser, ${MM}_CONFIGURATION_ERROR_UNKNOWN_REGION, parser->position, "Unknown region", -1);
                }
                if (parser->seen[entry]) {
                    return ${M}_configuration_refuse(
                        parser, ${MM}_CONFIGURATION_ERROR_DUPLICATE_REGION, parser->position,
                        "Duplicate region", -1);
                }
                parser->seen[entry] = 1;
            }
            ${M}_configuration_next(parser);
            if (!${M}_configuration_at_mark(parser, ':')) {
                return ${M}_configuration_expected(parser, "':'");
            }
            ${M}_configuration_next(parser);
            if (parser->token == ${MM}_CONFIGURATION_TOKEN_DONE || parser->token == ${MM}_CONFIGURATION_TOKEN_INIT) {
                child = parser->token == ${MM}_CONFIGURATION_TOKEN_DONE
                    ? ${MM}_REGION_SLOT_DONE
                    : ${MM}_REGION_SLOT_PENDING;
                ${M}_configuration_next(parser);
            } else if (parser->token == ${MM}_CONFIGURATION_TOKEN_NAME && depth >= ${depth_limit}) {
                return ${M}_configuration_refuse(
                    parser, ${MM}_CONFIGURATION_ERROR_TOO_DEEP, parser->position,
                    "Region blocks nest deeper than the model allows near", -1);
            } else if (!${M}_configuration_position(parser, entry, depth + 1, &child)) {
                return ${MM}_FAILURE;
            }
            if (parser->resolve) {
                parser->work->regions[entry] = child;
            }
            if (!${M}_configuration_at_mark(parser, ',')) {
                break;
            }
            ${M}_configuration_next(parser);
        }
        if (!${M}_configuration_at_mark(parser, '}')) {
            return ${M}_configuration_expected(parser, "'}'");
        }
        ${M}_configuration_next(parser);
    }
    *end = state;
    return ${MM}_SUCCESS;
}

${MM}_API int ${M}_configuration_parse(
    const char *text,
    ${M}Configuration *configuration,
    ${M}ConfigurationError *error)
{
    ${M}Configuration work;
    unsigned char seen[${slot_count}];
    ${M}ConfigurationParser parser;
    ${M}StateId at = 0;
    if (text == NULL || configuration == NULL) {
        ${M}ConfigurationWriter writer = ${M}_configuration_report(error, ${MM}_CONFIGURATION_ERROR_ARGUMENT, 0);
        ${M}_configuration_put_text(&writer, text == NULL ? "Text pointer is NULL." : "Configuration pointer is NULL.");
        ${M}_configuration_finish(&writer);
        return ${MM}_FAILURE;
    }
    memset(&work, 0, sizeof(work));
    memset(seen, 0, sizeof(seen));
    parser.text = text;
    parser.work = &work;
    parser.seen = seen;
    parser.error = error;
    for (parser.resolve = 0; parser.resolve < 2; ++parser.resolve) {
        ${M}_configuration_scan(&parser, 0);
        if (!${M}_configuration_position(&parser, -1, 0, &at)) {
            return ${MM}_FAILURE;
        }
        if (parser.token != ${MM}_CONFIGURATION_TOKEN_END) {
            return ${M}_configuration_expected(&parser, "end of input");
        }
    }
    work.at = at;
    *configuration = work;
    return ${MM}_SUCCESS;
}

#undef ${MM}_CONFIGURATION_TOKEN_END
#undef ${MM}_CONFIGURATION_TOKEN_NAME
#undef ${MM}_CONFIGURATION_TOKEN_INIT
#undef ${MM}_CONFIGURATION_TOKEN_DONE
#undef ${MM}_CONFIGURATION_TOKEN_MARK
#endif
""")


def render_c_configuration_header(
    model, machine_class_name: str, machine_macro_name: str
) -> str:
    """
    Render the configuration types, macros and declarations for one model.

    The result belongs in the generated ``machine.h`` after the ``..._API``
    macro, the ``..._SUCCESS`` / ``..._FAILURE`` codes, the ``...StateId``
    typedef and the ``..._STATE_*`` id macros, all of which it uses. It opens
    its own ``extern "C"`` block for the declarations, compiles as C99 and as
    C++98, and references only ``size_t`` from ``<stddef.h>``.

    Region ids are named ``<macro>_REGION_<path>`` with the same
    case-preserving path encoding the state ids use, and are numbered owner by
    owner in :meth:`~pyfcstm.model.model.StateMachine.walk_states` order, in
    declaration order inside one owner. A model without regions gets
    ``<macro>_REGION_COUNT 0`` and a one-slot ``regions`` array, so the type
    has the same shape for every model.

    :param model: State machine to emit the configuration type for.
    :type model: pyfcstm.model.model.StateMachine
    :param machine_class_name: Type and function prefix, the C template's
        ``machine_class_name(model)``.
    :type machine_class_name: str
    :param machine_macro_name: Macro prefix, the C template's
        ``machine_macro_name(model)``.
    :type machine_macro_name: str
    :return: C header text ending with a newline.
    :rtype: str
    :raises ValueError: If either name is not a C identifier.

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root { [*] -> Idle; state Idle; }')
        >>> header = render_c_configuration_header(model, 'RootMachine', 'ROOT_MACHINE')
        >>> '#define ROOT_MACHINE_REGION_COUNT 0' in header
        True
        >>> 'RootMachineStateId regions[1];' in header
        True
        >>> render_c_configuration_header(model, 'Root Machine', 'ROOT_MACHINE')
        Traceback (most recent call last):
        ...
        ValueError: machine_class_name must be a C identifier, got 'Root Machine'.
    """
    _check_names(machine_class_name, machine_macro_name)
    _, regions = _layout(model)
    region_macros = "".join(
        "/* DSL region path: `%s` */\n#define %s ((%sRegionId)%d)\n"
        % (
            ".".join(region.path),
            _region_macro(machine_macro_name, region.path),
            machine_class_name,
            index,
        )
        for index, region in enumerate(regions)
    )
    return _HEADER.substitute(
        M=machine_class_name,
        MM=machine_macro_name,
        region_count=len(regions),
        slot_count=max(1, len(regions)),
        region_macros=region_macros,
        padding_note="" if regions else "; this model has none, the slot stays pending",
    )


def render_c_configuration_source(
    model, machine_class_name: str, machine_macro_name: str
) -> str:
    """
    Render the configuration tables and function definitions for one model.

    The result belongs in the generated ``machine.c`` after ``machine.h`` (with
    the text of :func:`render_c_configuration_header`) has been included. It
    defines file-local tables keyed by the ``..._STATE_*`` and
    ``..._REGION_*`` macros, so a naming mismatch with the header is a compile
    error, and the exported functions declared by the header. Each state and
    region name is stored once and shared by the formatter and the parser.

    The text formatter writes exactly ``str(configuration)`` of the simulator,
    and the parser accepts exactly the texts that
    :meth:`pyfcstm.model.configuration.Configuration.parse` accepts in
    ``transient`` mode, reading whitespace as Python's ``str.isspace`` does.
    Parsing recurses at most one level deeper than the model nests regions, so
    hostile text cannot exhaust the stack.

    :param model: State machine to emit the configuration functions for.
    :type model: pyfcstm.model.model.StateMachine
    :param machine_class_name: Type and function prefix, the C template's
        ``machine_class_name(model)``.
    :type machine_class_name: str
    :param machine_macro_name: Macro prefix, the C template's
        ``machine_macro_name(model)``.
    :type machine_macro_name: str
    :return: C source text ending with a newline.
    :rtype: str
    :raises ValueError: If either name is not a C identifier.

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     [*] -> Run;
        ...     state Run {
        ...         region Motion { [*] -> Stop; state Stop; }
        ...     }
        ... }
        ... ''')
        >>> source = render_c_configuration_source(model, 'RootMachine', 'ROOT_MACHINE')
        >>> '"Motion", /* ROOT_MACHINE_REGION_p4_Root_p3_Run_p6_Motion */' in source
        True
        >>> 'ROOT_MACHINE_API int RootMachine_configuration_parse(' in source
        True
    """
    _check_names(machine_class_name, machine_macro_name)
    states, regions = _layout(model)
    macro = machine_macro_name

    def state_ref(index):
        """
        Spell a state index as its id macro.

        :param index: State index, or ``-1``.
        :type index: int
        :return: The macro name, or ``'-1'``.
        :rtype: str
        """
        return "-1" if index < 0 else _state_macro(macro, states[index].path)

    def region_ref(index):
        """
        Spell a region index as its id macro.

        :param index: Region index, or ``-1``.
        :type index: int
        :return: The macro name, or ``'-1'``.
        :rtype: str
        """
        return "-1" if index < 0 else _region_macro(macro, regions[index].path)

    state_rows = "".join(
        "    {%s, %s, %s, %d, %d}, /* %s */\n"
        % (
            state_ref(row.parent),
            region_ref(row.scope),
            region_ref(row.first_region) if row.region_count else "0",
            row.region_count,
            int(row.is_leaf),
            _state_macro(macro, row.path),
        )
        for row in states
    )
    state_name_rows = "".join(
        '    "%s", /* %s */\n' % (row.path[-1], _state_macro(macro, row.path))
        for row in states
    )
    if regions:
        region_owner_rows = "".join(
            "    %s, /* %s */\n"
            % (state_ref(region.owner), _region_macro(macro, region.path))
            for region in regions
        )
        region_name_rows = "".join(
            '    "%s", /* %s */\n'
            % (region.path[-1], _region_macro(macro, region.path))
            for region in regions
        )
        padding_check = ""
    else:
        region_owner_rows = "    -1, /* this model has no regions */\n"
        region_name_rows = '    "", /* this model has no regions */\n'
        padding_check = (
            "    if (configuration->regions[0] != %s_REGION_SLOT_PENDING) {\n"
            "        return %s_configuration_structure_error(\n"
            "            error, %s_CONFIGURATION_ERROR_INACTIVE_REGION, -1, configuration->regions[0]);\n"
            "    }\n" % (macro, machine_class_name, macro)
        )
    return _SOURCE.substitute(
        M=machine_class_name,
        MM=machine_macro_name,
        slot_count=max(1, len(regions)),
        state_rows=state_rows,
        state_name_rows=state_name_rows,
        region_owner_rows=region_owner_rows,
        region_name_rows=region_name_rows,
        padding_check=padding_check,
        depth_limit=max(row.depth for row in states) + 1,
    )
