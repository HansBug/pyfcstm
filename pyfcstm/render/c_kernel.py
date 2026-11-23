"""
Execution kernel of the built-in C runtime templates, emitted for one model.

The C runtime of a model is made of three things: the public types and
functions of ``machine.h``, the engine that decides what a cycle does
(:mod:`pyfcstm.render.c_kernel_engine`, which does not depend on the model) and
everything that does depend on the model. This module emits the last one and
glues the engine to it:

* the tables of states, regions and transitions, with every number they need
  derived from the model, so each machine only carries what it can use
* one function per lifecycle stage of every state, and per aspect of every
  state and region, that runs its concrete actions and calls the hook of its
  abstract ones
* the private structure of a machine and the capacities of its search arena
* the conversion between a running machine and a configuration value, used to
  read the position and to hot start from one

The machine is a union of an alignment member and a byte array in the public
header, so its members cannot be named from outside; the generated source casts
that storage to the private structure defined here. The byte size is computed
from the same field list that defines the structure, and the generated source
asserts at compile time that the structure fits.

The module contains:

* :func:`iter_action_items` - Every lifecycle action of a model in a fixed order
* :func:`event_paths` - The event id space of a model
* :func:`action_rows` - The action id space of a model
* :func:`hook_rows` - The abstract actions of a model, one row per hook
* :func:`private_storage_bytes` - Upper bound of the private structure's size
* :func:`render_c_kernel_types` - Engine types and the private structure
* :func:`render_c_kernel_code` - Tables, action functions, engine and glue

Example::

    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('''
    ... state Root {
    ...     event Go;
    ...     [*] -> A;
    ...     state A;
    ...     state B;
    ...     A -> B :: Go;
    ... }
    ... ''')
    >>> event_paths(model)
    ['Root.Go', 'Root.A.Go']
    >>> [row['func_name'] for row in hook_rows(model)]
    []
"""

from dataclasses import dataclass
from typing import Dict, Iterator, List, Optional, Tuple

from ..dsl import node as dsl_nodes
from ..model.region import Region, walk_namespaces
from ..utils import to_c_identifier, to_c_path_identifier
from .c_kernel_engine import ENGINE_CODE, ENGINE_TYPES
from .c_runtime import render_c_action_body, render_c_condition_body

__all__ = [
    "iter_action_items",
    "event_paths",
    "action_rows",
    "hook_rows",
    "private_storage_bytes",
    "render_c_kernel_types",
    "render_c_kernel_code",
]

# Stage names in the order the public ``..._STAGE_*`` macros number them.
_STAGE_IDS = {"enter": 0, "during": 1, "exit": 2}
_SENTINEL_NAME_LIMIT = 64


def iter_action_items(model) -> Iterator[Tuple[object, str, object]]:
    """
    Yield every lifecycle action of a model in the order ids are assigned.

    States are visited together with regions in tree order. A state contributes
    its ``enter``, plain ``during``, ``exit``, ``during before``, ``during
    after`` and the aspect actions ``>> during before`` and ``>> during after``;
    a region contributes only its aspect actions. The order is part of the
    contract of the generated runtime: action ids, hook ids and the generated
    hook table all follow it.

    :param model: State machine to scan.
    :type model: pyfcstm.model.model.StateMachine
    :return: Triples of the owning state or region, the group name and the
        action item itself (not resolved through ``ref``).
    :rtype: Iterator[Tuple[object, str, object]]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     enter abstract Boot;
        ...     [*] -> A;
        ...     state A;
        ... }
        ... ''')
        >>> [(group, item.func_name) for _, group, item in iter_action_items(model)]
        [('enter', 'Root.Boot')]
    """
    for scope in walk_namespaces(model.root_state):
        if isinstance(scope, Region):
            groups = [
                ("aspect_before", scope.list_on_during_aspects(aspect="before", with_ids=True)),
                ("aspect_after", scope.list_on_during_aspects(aspect="after", with_ids=True)),
            ]
        else:
            groups = [
                ("enter", scope.list_on_enters(with_ids=True)),
                ("during", scope.list_on_durings(aspect=None, with_ids=True)),
                ("exit", scope.list_on_exits(with_ids=True)),
                ("during_before", scope.list_on_durings(aspect="before", with_ids=True)),
                ("during_after", scope.list_on_durings(aspect="after", with_ids=True)),
                ("aspect_before", scope.list_on_during_aspects(aspect="before", with_ids=True)),
                ("aspect_after", scope.list_on_during_aspects(aspect="after", with_ids=True)),
            ]
        for group_name, items in groups:
            for _, item in items:
                yield scope, group_name, item


def event_paths(model) -> List[str]:
    """
    List the events of a model in the order their ids are assigned.

    Events declared on a state and on a region both count; they are visited in
    tree order, a state before its regions and a region before its states.

    :param model: State machine to scan.
    :type model: pyfcstm.model.model.StateMachine
    :return: Dotted event paths; the position in the list is the event id.
    :rtype: List[str]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     event Go;
        ...     [*] -> A;
        ...     state A;
        ... }
        ... ''')
        >>> event_paths(model)
        ['Root.Go']
    """
    return [
        event.path_name
        for scope in walk_namespaces(model.root_state)
        for event in scope.events.values()
    ]


def _resolve(item):
    """Follow ``ref`` links from an action item to the action that does the work."""
    hops = 0
    while item.ref is not None and hops < _SENTINEL_NAME_LIMIT * _SENTINEL_NAME_LIMIT:
        item = item.ref
        hops += 1
    return item


def action_rows(model) -> List[Dict[str, str]]:
    """
    List the distinct actions of a model in the order their ids are assigned.

    :param model: State machine to scan.
    :type model: pyfcstm.model.model.StateMachine
    :return: One ``{'func_name': ...}`` row per distinct action name, in first
        seen order; the position is the action id.
    :rtype: List[Dict[str, str]]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... def int x = 0;
        ... state Root {
        ...     enter { x = 1; }
        ...     [*] -> A;
        ...     state A;
        ... }
        ... ''')
        >>> action_rows(model)
        [{'func_name': 'Root.None'}]
    """
    rows: List[Dict[str, str]] = []
    seen = set()
    for _, _, item in iter_action_items(model):
        if item.func_name not in seen:
            seen.add(item.func_name)
            rows.append({"func_name": item.func_name})
    return rows


def hook_rows(model) -> List[Dict[str, str]]:
    """
    List the abstract actions of a model, one row per generated hook.

    Actions that reach the same abstract definition through ``ref`` share a
    hook, so the rows are keyed by the resolved action's name.

    :param model: State machine to scan.
    :type model: pyfcstm.model.model.StateMachine
    :return: Rows with ``func_name`` (dotted action path), ``hook_field`` (the
        field of the hook table), ``owner_path`` (dotted path of the state or
        region that declares it), ``stage``, ``aspect`` (``None`` or the aspect
        keyword) and ``dsl_fragment`` (the declaration as DSL text).
    :rtype: List[Dict[str, str]]

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     enter abstract Boot;
        ...     [*] -> A;
        ...     state A;
        ... }
        ... ''')
        >>> [(row['func_name'], row['hook_field'], row['stage']) for row in hook_rows(model)]
        [('Root.Boot', 'on_p4_Root_p4_Boot', 'enter')]
    """
    rows: List[Dict[str, str]] = []
    seen = set()
    for _, _, item in iter_action_items(model):
        resolved = _resolve(item)
        if not resolved.is_abstract or resolved.func_name in seen:
            continue
        seen.add(resolved.func_name)
        rows.append(
            {
                "func_name": resolved.func_name,
                "hook_field": "on_" + to_c_path_identifier(resolved.func_name.split(".")),
                "owner_path": ".".join(resolved.parent.path),
                "stage": resolved.stage,
                "aspect": resolved.aspect,
                "dsl_fragment": str(resolved.to_ast_node()),
            }
        )
    return rows


def _round_up(value: int, align: int) -> int:
    """Round ``value`` up to a multiple of ``align``."""
    return (value + align - 1) // align * align


@dataclass
class _Field:
    """One member of a C structure: its declaration, size and alignment."""

    declaration: str
    size: int
    align: int


def _layout(fields: List[_Field]) -> int:
    """Return the size of a structure made of ``fields`` under natural alignment."""
    offset = 0
    biggest = 1
    for field in fields:
        offset = _round_up(offset, field.align) + field.size
        biggest = max(biggest, field.align)
    return _round_up(offset, biggest)


class _Plan:
    """
    Everything the generated kernel needs to know about one model.

    The constructor walks the model once: it numbers states, regions, events,
    actions and transitions, derives the capacities and records the table rows.
    The render functions only format what the plan holds.

    :param model: State machine to plan for.
    :type model: pyfcstm.model.model.StateMachine
    """

    def __init__(self, model) -> None:
        self.model = model
        self.states = list(model.walk_states())
        # Region ids follow the configuration type: owner by owner in state order,
        # and in declaration order inside one owner.
        self.regions = [region for state in self.states for region in state.regions.values()]
        self.state_index = {state.path: index for index, state in enumerate(self.states)}
        self.region_index = {region.path: index for index, region in enumerate(self.regions)}
        self.events = event_paths(model)
        self.actions = [row["func_name"] for row in action_rows(model)]
        self.hooks = [row["func_name"] for row in hook_rows(model)]
        self.var_names = list(model.persistent_variables)
        self.transitions: List[Dict[str, object]] = []
        self._transition_ids: Dict[Tuple[int, Tuple[str, ...]], int] = {}
        self.functions: List[str] = []
        self._plan_stacks()
        self._plan_capacity()

    # -- capacities -----------------------------------------------------

    def _plan_stacks(self) -> None:
        """Derive the depth of the main stack and of every region stack."""

        def chain_depth(state) -> int:
            if state.regions or not state.substates:
                return 1
            return 1 + max(chain_depth(child) for child in state.substates.values())

        self.main_depth = chain_depth(self.model.root_state)
        self.region_depth = max(
            [max(chain_depth(child) for child in region.substates.values()) for region in self.regions]
            or [1]
        )

    def _plan_capacity(self) -> None:
        """Choose how many configurations and nested checks a machine can hold."""
        scopes = len(self.states) + len(self.regions)
        simple = (
            not self.regions
            and not any(state.is_pseudo for state in self.states)
            and all(state.is_leaf_state or state.parent is None for state in self.states)
        )
        self.arena_capacity = 8 if simple else max(24, 12 * scopes)
        self.trail_capacity = 4 if simple else 16 + 4 * scopes

    # -- sizes ----------------------------------------------------------

    def variable_struct_size(self, count: int) -> int:
        """Size of a structure of ``count`` 8-byte numbers (or a 4-byte placeholder)."""
        return count * 8 if count else 4

    def context_size(self) -> int:
        """Size of one configuration tree, matching the generated ``Ctx``."""
        scopes = len(self.states) + len(self.regions)
        regions = max(1, len(self.regions))
        fields = [
            _Field("vars", self.variable_struct_size(len(self.var_names)), 8 if self.var_names else 4),
            _Field("main", _round_up(self.main_depth * 4 + 4, 4), 4),
            _Field("regions", regions * _round_up(self.region_depth * 4 + 4 + 2, 4), 4),
            _Field("ended", 1, 1),
            _Field("before_done", scopes, 1),
            _Field("after_pending", scopes, 1),
        ]
        return _layout(fields)

    def node_size(self) -> int:
        """Size of one search arena node."""
        return _layout(
            [_Field("ctx", self.context_size(), 8), _Field("hash", 8, 8), _Field("parent", 4, 4), _Field("flags", 4, 2)]
        )

    # -- ids ------------------------------------------------------------

    def event_id(self, event) -> int:
        """Return the id of ``event``, or ``-1`` for a transition without one."""
        if event is None:
            return -1
        return self.events.index(event.path_name)

    def action_id(self, func_name: str) -> int:
        """Return the action id of a dotted action name."""
        return self.actions.index(func_name)

    def hook_id(self, func_name: str) -> int:
        """Return the hook id of a dotted abstract action name."""
        return self.hooks.index(func_name)

    def scope_index(self, scope) -> int:
        """Return the scope number of a state (its id) or a region (states + its id)."""
        if isinstance(scope, Region):
            return len(self.states) + self.region_index[scope.path]
        return self.state_index[scope.path]


def _identifier_list(values: List[int]) -> str:
    """Format a non-empty C initializer list; an empty table gets one zero."""
    return ", ".join(str(value) for value in (values or [0]))


def private_storage_bytes(model, extra_bytes: int = 0) -> int:
    """
    Compute the byte size reserved for the private structure of a machine.

    The public header declares a machine as an alignment member plus this many
    bytes. The value is computed on an LP64 layout, which is never smaller than
    a 32-bit one, and the generated source asserts at compile time that the
    private structure fits, so an error here fails the build instead of
    corrupting memory.

    :param model: State machine the runtime is generated for.
    :type model: pyfcstm.model.model.StateMachine
    :param extra_bytes: Size of the members a template adds on top of the shared
        ones (for example its event bookkeeping), defaults to ``0``.
    :type extra_bytes: int, optional
    :return: Number of bytes to reserve.
    :rtype: int

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     [*] -> A;
        ...     state A;
        ... }
        ... ''')
        >>> private_storage_bytes(model) % 8
        0
    """
    plan = _Plan(model)
    ctx = plan.context_size()
    parameters = plan.variable_struct_size(len(model.parameters))
    inputs = plan.variable_struct_size(len(model.inputs))
    provider = len(model.inputs) * 8 if model.inputs else 4
    fields = [
        _Field("ctx", ctx, 8),
        _Field("snapshot", ctx, 8),
        _Field("parameters", parameters, 8),
        _Field("last_inputs", inputs, 8),
        _Field("provider", provider, 8),
        _Field("pointers", 8 * 8, 8),
        _Field("ints", 16 * 4, 4),
        _Field("last_error", 512, 1),
        _Field("arena", plan.arena_capacity * plan.node_size(), 8),
        _Field("work", plan.arena_capacity * 4, 4),
        _Field("trail", plan.trail_capacity * 32, 8),
        _Field("extra", extra_bytes, 8),
    ]
    return _round_up(_layout(fields) + 64, 16)


def render_c_kernel_types(
    model,
    machine_class_name: str,
    machine_macro_name: str,
    private_members: str = "",
) -> str:
    """
    Emit the engine types and the private structure of a machine.

    :param model: State machine the runtime is generated for.
    :type model: pyfcstm.model.model.StateMachine
    :param machine_class_name: Public class prefix, for example ``RootMachine``.
    :type machine_class_name: str
    :param machine_macro_name: Public macro prefix, for example ``ROOT_MACHINE``.
    :type machine_macro_name: str
    :param private_members: Extra members a template appends to the private
        structure, one declaration per line, defaults to ``''``.
    :type private_members: str, optional
    :return: C source of the types, the private structure and the accessors
        between the public and the private view of a machine.
    :rtype: str

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     [*] -> A;
        ...     state A;
        ... }
        ... ''')
        >>> text = render_c_kernel_types(model, 'RootMachine', 'ROOT_MACHINE')
        >>> 'typedef struct _RootMachinePriv' in text
        True
    """
    plan = _Plan(model)
    values = _fill_values(plan, machine_class_name, machine_macro_name)
    body = ENGINE_TYPES + _PRIVATE_STRUCT.replace("@PRIVATE_MEMBERS@", private_members)
    return _fill(body, values)


def _fill_values(plan: _Plan, machine_class_name: str, machine_macro_name: str) -> Dict[str, str]:
    """Collect the placeholder values shared by every emitted block."""
    return {
        "M": machine_class_name,
        "MM": machine_macro_name,
        "P": "_%s_" % machine_class_name,
        "T": "_%s" % machine_class_name,
        "NS": str(len(plan.states)),
        "NR": str(len(plan.regions)),
        "NRX": str(max(1, len(plan.regions))),
        "NSR": str(len(plan.states) + len(plan.regions)),
        "MAXD_MAIN": str(plan.main_depth),
        "MAXD_REG": str(plan.region_depth),
        "ARENA_CAP": str(plan.arena_capacity),
        "TRAIL_CAP": str(plan.trail_capacity),
        "ROOT_ID": str(plan.state_index[plan.model.root_state.path]),
        "HAS_HOOKS": "1" if plan.hooks else "0",
        "STORAGE": str(private_storage_bytes(plan.model)),
    }


def _fill(text: str, values: Dict[str, str]) -> str:
    """
    Substitute ``@NAME@`` placeholders and fail if one is left unfilled.

    :param text: Text with placeholders.
    :type text: str
    :param values: Replacement for each placeholder name.
    :type values: Dict[str, str]
    :return: The filled text.
    :rtype: str
    :raises ValueError: If a placeholder has no value.
    """
    for name, value in values.items():
        text = text.replace("@%s@" % name, value)
    start = text.find("@")
    while start >= 0:
        end = text.find("@", start + 1)
        candidate = text[start + 1 : end] if end > 0 else ""
        if candidate and candidate.replace("_", "").isalnum() and candidate.upper() == candidate:
            raise ValueError("unfilled placeholder @%s@" % candidate)
        start = text.find("@", start + 1)
    return text


_PRIVATE_STRUCT = r'''
/* The private state of a machine. Nothing outside this file names these members. */
typedef struct @T@Priv {
    @T@Ctx ctx;                       /* the committed configuration; the executing one during a cycle */
    @T@Ctx snapshot;                  /* the configuration a cycle started from */
    @M@Parameters parameters;
    @M@Inputs last_inputs;
    const @M@Inputs *active_inputs;
    @M@InputProvider input_provider;
    void *input_user_data;
    const @M@Hooks *hooks;
    void *hook_user_data;
    @M@Vars *active_vars;
    const @T@Outer *outer;
    int has_last_inputs;
    int started;
    int initialized;
    int delta;
    int error_kind;
    int init_depth;
    int speculation;
    int hooks_live;
    int arena_top;
    int work_size;
    int trail_size;
    char last_error[512];
    @T@Node arena[@ARENA_CAP@];
    int work[@ARENA_CAP@];
    @T@TrailEntry trail[@TRAIL_CAP@];
@PRIVATE_MEMBERS@
} @T@Priv;

/* The storage reserved in the public header must hold the private structure. */
typedef char @T@PrivFits[(sizeof(@T@Priv) <= @MM@_STORAGE_BYTES) ? 1 : -1];

static @T@Priv *@P@priv(@M@ *machine)
{
    return (@T@Priv *)(void *)machine->_private;
}

static PYFCSTM_GENERATED_UNUSED const @T@Priv *@P@priv_const(const @M@ *machine)
{
    return (const @T@Priv *)(const void *)machine->_private;
}

static @M@ *@P@pub(@T@Priv *p)
{
    return (@M@ *)(void *)((char *)(void *)p - offsetof(@M@, _private));
}
'''


_TABLE_TYPES = r'''
/* One transition: its target state id (-1 for a state, -2 for the exit of the enclosing scope), the event
 * id it needs (-1 for none), its guard and its effect. */
typedef struct @T@Transition {
    int to;
    int event;
    @T@GuardFn guard;
    @T@ActionFn effect;
} @T@Transition;

/* What the engine knows about one state. kind: 0 leaf, 1 composite, 2 owner of regions. */
typedef struct @T@StateInfo {
    int kind;
    @T@ActionFn enter;
    @T@ActionFn during;
    @T@ActionFn exit;
    const int *initial;
    int initial_count;
    const int *outgoing;
    int outgoing_count;
    const int *regions;
    int region_count;
} @T@StateInfo;

typedef struct @T@RegionInfo {
    int owner;
    const int *initial;
    int initial_count;
} @T@RegionInfo;

static PYFCSTM_GENERATED_UNUSED int @P@hook(
    @T@Priv *m,
    int hook_id,
    int action_id,
    int stage_id,
    int target_id,
    int ref_id,
    int state,
    int aspect_scope);
'''

_HOOK_AND_GLUE = r'''
/* Deepest state common to everything an aspect of `scope` wraps (_wrapped_state_path). */
static PYFCSTM_GENERATED_UNUSED int @P@wrapped_scope(@T@Priv *m, int scope)
{
    @T@Stack st;
    int index = -1, i;
    if (scope >= @NS@) {
        st = @P@stack_of(&m->ctx, scope - @NS@);
    } else {
        st = @P@stack_of(&m->ctx, @P@enclosing_region[scope]);
        for (i = 0; i < *st.size; ++i) {
            if (st.frames[i].state == scope) {
                index = i;
            }
        }
        if (index < 0) {
            return scope;
        }
    }
    for (;;) {
        if (index >= 0 && @P@states[st.frames[index].state].kind == 2) {
            int owner = st.frames[index].state;
            if (@P@states[owner].region_count != 1) {
                break;
            }
            st = @P@stack_of(&m->ctx, @P@states[owner].regions[0]);
            index = -1;
        }
        if (index + 1 < *st.size) {
            ++index;
        } else {
            break;
        }
    }
    return index >= 0 ? st.frames[index].state : @P@regions_info[st.stack].owner;
}

static PYFCSTM_GENERATED_UNUSED int @P@hook(
    @T@Priv *m,
    int hook_id,
    int action_id,
    int stage_id,
    int target_id,
    int ref_id,
    int state,
    int aspect_scope)
{
    @M@ExecutionContext ctx;
    @M@Vars *saved;
    int where;
    if (!m->hooks_live || m->speculation > 0 || m->hooks == NULL) {
        return @MM@_SUCCESS;
    }
    where = aspect_scope >= 0 ? @P@wrapped_scope(m, aspect_scope) : state;
    saved = m->active_vars;
    m->active_vars = &m->ctx.vars;
    ctx.state_id = (@M@StateId)where;
    ctx.vars = &m->ctx.vars;
    ctx.action_id = (@M@ActionId)action_id;
    ctx.action_stage_id = (@M@StageId)stage_id;
    ctx.active_leaf_state_id = (@M@StateId)where;
    ctx.call_stage_id = (@M@StageId)stage_id;
    ctx.abstract_target_id = (@M@ActionId)target_id;
    ctx.named_ref_id = (@M@ActionId)ref_id;
    (void)ctx;
    switch (hook_id) {
@HOOK_CASES@
    default:
        break;
    }
    m->active_vars = saved;
    return @MM@_SUCCESS;
}

/* ---- the configuration value of a running machine ---- */

static void @P@collect_branch(const @T@Ctx *c, int stack, @M@Configuration *out)
{
    const @T@Frame *frames = stack < 0 ? c->main.frames : c->regions[stack].frames;
    int size = stack < 0 ? c->main.size : c->regions[stack].size;
    int state, k;
    if (size == 0) {
        return;
    }
    state = frames[size - 1].state;
    if (stack < 0) {
        out->at = (@M@StateId)state;
    } else {
        out->regions[stack] = (@M@StateId)state;
    }
    if (@P@states[state].kind == 2) {
        for (k = 0; k < @P@states[state].region_count; ++k) {
            int region = @P@states[state].regions[k];
            if (@P@region_done(c, region)) {
                out->regions[region] = @MM@_REGION_SLOT_DONE;
            } else if (!@P@region_pending(c, region)) {
                @P@collect_branch(c, region, out);
            }
        }
    }
}

/* Fill `out` from a context; 0 when the machine has ended and has no position. */
static int @P@ctx_to_configuration(const @T@Ctx *c, @M@Configuration *out)
{
    memset(out, 0, sizeof(*out));
    if (c->main.size == 0) {
        return 0;
    }
    @P@collect_branch(c, -1, out);
    return 1;
}

static void @P@place_chain(@T@Frame *frames, int *size, int state)
{
    int chain[@NS@ + 1], n = 0, i;
    while (state >= 0 && state < @NS@) {
        chain[n++] = state;
        state = @P@scope_parent[state];
    }
    for (i = n - 1; i >= 0; --i) {
        frames[*size].state = (short)chain[i];
        frames[*size].mode = @MM@_K_ACTIVE;
        frames[*size].plain_before_pending = 0;
        ++*size;
    }
}

/* The context of a machine that has not run: the root waits for its entry. */
static void @P@reset_ctx(@T@Ctx *c)
{
    int r;
    c->main.size = 1;
    c->main.frames[0].state = (short)@ROOT_ID@;
    c->main.frames[0].mode = @MM@_K_INIT_WAIT;
    c->main.frames[0].plain_before_pending = 0;
    for (r = 0; r < @NRX@; ++r) {
        c->regions[r].size = 0;
        c->regions[r].region_mode = @MM@_K_RM_NONE;
        c->regions[r].plain_before_pending = 0;
    }
    c->ended = 0;
    memset(c->before_done, 0, sizeof(c->before_done));
    memset(c->after_pending, 0, sizeof(c->after_pending));
}

static int @P@set_top_modes(@T@Priv *m, @T@Ctx *c, int stack)
{
    @T@Stack st = @P@stack_of(c, stack);
    int state, k, done = 0, pending = 0;
    if (*st.size == 0) {
        return 0;
    }
    state = st.frames[*st.size - 1].state;
    if (@P@states[state].kind == 1) {
        st.frames[*st.size - 1].mode = @MM@_K_INIT_WAIT;
    } else if (@P@states[state].kind == 2) {
        for (k = 0; k < @P@states[state].region_count; ++k) {
            int region = @P@states[state].regions[k];
            if (@P@region_done(c, region)) {
                ++done;
            } else if (@P@region_pending(c, region)) {
                ++pending;
            }
        }
        if (done == @P@states[state].region_count) {
            @P@set_error(
                @P@pub(m),
                "All regions are Done at '%s'; a finished owner cannot be hot-started.",
                @P@state_paths[state]);
            return -1;
        }
        st.frames[*st.size - 1].mode =
            pending == @P@states[state].region_count ? @MM@_K_INIT_WAIT : @MM@_K_ACTIVE;
    }
    return 0;
}

/*
 * Put a configuration in place without running any action: the frames of every
 * written branch are active, a plain composite or an owner whose regions all
 * wait is waiting for its initial transition, and a done region stays done.
 */
static int @P@configuration_to_ctx(@T@Priv *m, const @M@Configuration *configuration, @T@Ctx *c)
{
    @M@ConfigurationError error;
    int region;
    if (!@M@_configuration_validate(configuration, &error)) {
        if (error.message[0] != '\0') {
            @P@set_error(@P@pub(m), "Invalid configuration: %s", error.message);
        } else {
            @P@set_error(@P@pub(m), "Invalid configuration (kind %d).", error.kind);
        }
        return -1;
    }
    @P@reset_ctx(c);
    c->main.size = 0;
    @P@place_chain(c->main.frames, &c->main.size, configuration->at);
    if (c->main.size > @MM@_K_DEPTH_LIMIT) {
        @P@set_error(
            @P@pub(m),
            "Hot start target exceeds the structural stack-depth safety limit (64) before execution; "
            "choose a shallower target state or simplify the state hierarchy.");
        return -1;
    }
    for (region = 0; region < @NR@; ++region) {
        if (configuration->regions[region] == @MM@_REGION_SLOT_DONE) {
            c->regions[region].region_mode = @MM@_K_POST_CHILD_EXIT;
        } else if (configuration->regions[region] != @MM@_REGION_SLOT_PENDING) {
            c->regions[region].region_mode = @MM@_K_ACTIVE;
            @P@place_chain(c->regions[region].frames, &c->regions[region].size, configuration->regions[region]);
        }
    }
    if (@P@set_top_modes(m, c, -1) != 0) {
        return -1;
    }
    for (region = 0; region < @NR@; ++region) {
        if (@P@set_top_modes(m, c, region) != 0) {
            return -1;
        }
    }
    return 0;
}

/* The configuration that holds one state and lets every other region wait. */
static void @P@configuration_of_state(int state, @M@Configuration *out)
{
    memset(out, 0, sizeof(*out));
    for (;;) {
        int region = @P@enclosing_region[state];
        if (region < 0) {
            out->at = (@M@StateId)state;
            return;
        }
        out->regions[region] = (@M@StateId)state;
        state = @P@regions_info[region].owner;
    }
}
'''


class _Emitter:
    """
    Emit the model-dependent part of the kernel from a :class:`_Plan`.

    :param plan: Planned model.
    :type plan: _Plan
    :param machine_class_name: Public class prefix.
    :type machine_class_name: str
    :param machine_macro_name: Public macro prefix.
    :type machine_macro_name: str
    """

    def __init__(self, plan: _Plan, machine_class_name: str, machine_macro_name: str) -> None:
        self.plan = plan
        self.model = plan.model
        self.cls = machine_class_name
        self.macro = machine_macro_name
        self.lines: List[str] = []
        self.constant_lists: List[str] = []

    def write(self, text: str) -> None:
        """Append one block of C source."""
        self.lines.append(text)

    # -- actions --------------------------------------------------------

    def _action_function(self, name: str, operations) -> str:
        """Emit one concrete action and return its name."""
        body = render_c_action_body(operations, self.model.defines, self.cls, self.macro)
        self.write("static int %s(%s *machine, %sVars *scope)\n{\n%s\n}\n" % (name, self.cls, self.cls, body))
        return name

    def _stage_function(self, name: str, items, state: int, aspect_scope: int) -> str:
        """
        Emit the function that runs a list of actions of one stage.

        :param name: Name of the function to emit.
        :type name: str
        :param items: Action items to run, in order.
        :type items: Iterable
        :param state: State id reported to the hooks of a plain action, or ``-1``.
        :type state: int
        :param aspect_scope: Scope number of the aspect owner, or ``-1`` for a plain action.
        :type aspect_scope: int
        :return: The emitted function's name, or ``NULL`` if there is nothing to run.
        :rtype: str
        """
        calls: List[str] = []
        for index, item in enumerate(items):
            resolved = _resolve(item)
            if resolved.is_abstract:
                ref_id = (
                    self.plan.action_id(item.func_name)
                    if item.name is not None and item.ref is not None
                    else -1
                )
                calls.append(
                    "%s_hook(%s_priv(machine), %d, %d, %d, %d, %d, %d, %d)"
                    % (
                        "_" + self.cls,
                        "_" + self.cls,
                        self.plan.hook_id(resolved.func_name),
                        self.plan.action_id(resolved.func_name),
                        _STAGE_IDS[item.stage],
                        self.plan.action_id(resolved.func_name),
                        ref_id,
                        state,
                        aspect_scope,
                    )
                )
            elif resolved.operations:
                part = self._action_function("%s_%d" % (name, index), resolved.operations)
                calls.append("%s(machine, scope)" % part)
        if not calls:
            return "NULL"
        body = "".join("    if (%s != %s_SUCCESS) {\n        return %s_FAILURE;\n    }\n" % (call, self.macro, self.macro) for call in calls)
        self.write(
            "static int %s(%s *machine, %sVars *scope)\n{\n    (void)scope;\n%s    return %s_SUCCESS;\n}\n"
            % (name, self.cls, self.cls, body, self.macro)
        )
        return name

    # -- transitions ----------------------------------------------------

    def _transition_row(self, transition, owner_path: Tuple[str, ...]) -> int:
        """
        Register one transition and emit its guard and effect.

        :param transition: Transition to register.
        :type transition: pyfcstm.model.model.Transition
        :param owner_path: Path of the state or region whose substates its target names.
        :type owner_path: Tuple[str, ...]
        :return: Index of its row in the transition table.
        :rtype: int
        """
        key = (id(transition), owner_path)
        if key in self.plan._transition_ids:
            return self.plan._transition_ids[key]
        tid = len(self.plan.transitions)
        self.plan._transition_ids[key] = tid
        guard = "NULL"
        if transition.guard is not None:
            name = "_%s_guard_%d" % (self.cls, tid)
            body = render_c_condition_body(
                transition.guard.to_ast_node(), self.model.defines, self.cls, self.macro, "transition guard"
            )
            self.write(
                "static int %s(%s *machine, const %sVars *scope, int *result)\n{\n%s\n}\n"
                % (name, self.cls, self.cls, body)
            )
            guard = name
        effect = "NULL"
        if transition.effects:
            effect = self._action_function("_%s_effect_%d" % (self.cls, tid), transition.effects)
        if transition.to_state is dsl_nodes.EXIT_STATE:
            target = -2
        else:
            target = self.plan.state_index[owner_path + (transition.to_state,)]
        event = self.plan.event_id(transition.event)
        self.plan.transitions.append({"to": target, "event": event, "guard": guard, "effect": effect})
        return tid

    def _constant_list(self, name: str, values: List[int]) -> str:
        """Emit a constant int array and return its name."""
        self.write("static const int %s[%d] = {%s};\n" % (name, max(1, len(values)), _identifier_list(values)))
        return name

    # -- whole kernel ---------------------------------------------------

    def render(self) -> str:
        """
        Emit action functions, transition and state tables.

        :return: C source of everything the model contributes to the kernel.
        :rtype: str
        """
        plan = self.plan
        cls = self.cls
        prefix = "_%s_" % cls
        states, regions = plan.states, plan.regions
        scopes = len(states) + len(regions)

        enter, during, exit_ = [], [], []
        plain_before, plain_after = [], []
        aspect_before: List[str] = [""] * scopes
        aspect_after: List[str] = [""] * scopes
        for index, state in enumerate(states):
            tag = "%sstage_%d_" % (prefix, index)
            enter.append(self._stage_function(tag + "enter", [item for _, item in state.list_on_enters(with_ids=True)], index, -1))
            during.append(self._stage_function(tag + "during", [item for _, item in state.list_on_durings(aspect=None, with_ids=True)], index, -1))
            exit_.append(self._stage_function(tag + "exit", [item for _, item in state.list_on_exits(with_ids=True)], index, -1))
            plain_before.append(self._stage_function(tag + "pbefore", [item for _, item in state.list_on_durings(aspect="before", with_ids=True)], index, -1))
            plain_after.append(self._stage_function(tag + "pafter", [item for _, item in state.list_on_durings(aspect="after", with_ids=True)], index, -1))
        for scope in list(states) + list(regions):
            number = plan.scope_index(scope)
            tag = "%sstage_%d_" % (prefix, number)
            aspect_before[number] = self._stage_function(
                tag + "abefore", [item for _, item in scope.list_on_during_aspects(aspect="before", with_ids=True)], -1, number
            )
            aspect_after[number] = self._stage_function(
                tag + "aafter", [item for _, item in scope.list_on_during_aspects(aspect="after", with_ids=True)], -1, number
            )

        state_initial: List[List[int]] = []
        state_outgoing: List[List[int]] = []
        for state in states:
            owner = state.parent.path if state.parent is not None else ()
            state_initial.append(
                [self._transition_row(t, state.path) for t in state.init_transitions]
            )
            state_outgoing.append(
                [self._transition_row(t, owner) for t in state.transitions_from]
            )
        region_initial = [
            [self._transition_row(t, region.path) for t in region.init_transitions] for region in regions
        ]

        self.write("static const %sTransition %stransitions[%d] = {\n" % ("_" + cls, prefix, len(plan.transitions)))
        for row in plan.transitions:
            self.write("    {%d, %d, %s, %s},\n" % (row["to"], row["event"], row["guard"], row["effect"]))
        self.write("};\n")

        for index, state in enumerate(states):
            self._constant_list("%sinitial_%d" % (prefix, index), state_initial[index])
            self._constant_list("%soutgoing_%d" % (prefix, index), state_outgoing[index])
            self._constant_list(
                "%sregion_list_%d" % (prefix, index), [plan.region_index[r.path] for r in state.regions.values()]
            )
        for index, region in enumerate(regions):
            self._constant_list("%sregion_initial_%d" % (prefix, index), region_initial[index])

        self.write("static const %sStateInfo %sstates[%d] = {\n" % ("_" + cls, prefix, len(states)))
        for index, state in enumerate(states):
            kind = 2 if state.regions else (1 if state.substates else 0)
            self.write(
                "    {%d, %s, %s, %s, %sinitial_%d, %d, %soutgoing_%d, %d, %sregion_list_%d, %d},\n"
                % (
                    kind,
                    enter[index],
                    during[index],
                    exit_[index],
                    prefix,
                    index,
                    len(state_initial[index]),
                    prefix,
                    index,
                    len(state_outgoing[index]),
                    prefix,
                    index,
                    len(state.regions),
                )
            )
        self.write("};\n")
        self.write("static const %sRegionInfo %sregions_info[%d] = {\n" % ("_" + cls, prefix, max(1, len(regions))))
        for index, region in enumerate(regions):
            self.write(
                "    {%d, %sregion_initial_%d, %d},\n"
                % (plan.state_index[region.parent.path], prefix, index, len(region_initial[index]))
            )
        if not regions:
            self.write("    {0, NULL, 0},\n")
        self.write("};\n")

        self.write("static const int %sis_pseudo[%d] = {%s};\n" % (prefix, len(states), _identifier_list([1 if s.is_pseudo else 0 for s in states])))
        parents: List[int] = []
        paths: List[Tuple[str, ...]] = []
        for state in states:
            parent = state.parent
            if parent is None:
                parents.append(-1)
            elif isinstance(parent, Region):
                parents.append(len(states) + plan.region_index[parent.path])
            else:
                parents.append(plan.state_index[parent.path])
            paths.append(state.path)
        for region in regions:
            parents.append(plan.state_index[region.parent.path])
            paths.append(region.path)
        self._constant_list(prefix + "scope_parent", parents)
        order = sorted(range(scopes), key=lambda number: (-len(paths[number]), paths[number]))
        self._constant_list(prefix + "flush_order", order)
        enclosing: List[int] = []
        for state in states:
            scope = state.parent
            while scope is not None and not isinstance(scope, Region):
                scope = scope.parent
            enclosing.append(plan.region_index[scope.path] if scope is not None else -1)
        self._constant_list(prefix + "enclosing_region", enclosing)
        for name, table, size in (
            ("plain_before", plain_before, len(states)),
            ("plain_after", plain_after, len(states)),
            ("aspect_before", aspect_before, scopes),
            ("aspect_after", aspect_after, scopes),
        ):
            self.write("static const %sActionFn %s%s[%d] = {%s};\n" % ("_" + cls, prefix, name, size, ", ".join(table)))
        self.write(
            "static const char *const %sstate_paths[%d] = {%s};\n"
            % (prefix, len(states), ", ".join('"%s"' % ".".join(s.path) for s in states))
        )
        self.write(
            "static PYFCSTM_GENERATED_UNUSED const char *const %sstate_names[%d] = {%s};\n"
            % (prefix, len(states), ", ".join('"%s"' % s.name for s in states))
        )
        self._emit_vars(plan)
        return "".join(self.lines)

    def _emit_vars(self, plan: _Plan) -> None:
        """Emit the hash and the equality of the persistent variables."""
        names = plan.var_names
        defines = self.model.defines
        hashing = ["    unsigned long long h = 1469598103934665603ULL, x;", "    double d;", "    (void)d;", "    (void)x;", "    (void)v;"]
        for name in names:
            field = to_c_identifier(name)
            if defines[name].type == "int":
                hashing.append("    x = (unsigned long long)v->%s;\n    h = (h ^ x) * 1099511628211ULL;\n    h ^= h >> 29;" % field)
            else:
                hashing.append(
                    "    d = v->%s;\n    if (d == 0.0) {\n        d = 0.0;\n    }\n    memcpy(&x, &d, sizeof(x));\n"
                    "    h = (h ^ x) * 1099511628211ULL;\n    h ^= h >> 29;" % field
                )
        self.write(
            "static unsigned long long _%s_vars_hash(const %sVars *v)\n{\n%s\n    return h;\n}\n"
            % (self.cls, self.cls, "\n".join(hashing))
        )
        compares = "".join(
            "    if (a->%s != b->%s) {\n        return 0;\n    }\n" % (to_c_identifier(n), to_c_identifier(n))
            for n in names
        )
        self.write(
            "static int _%s_vars_equal(const %sVars *a, const %sVars *b)\n{\n    (void)a;\n    (void)b;\n%s    return 1;\n}\n"
            % (self.cls, self.cls, self.cls, compares)
        )


def render_c_kernel_code(model, machine_class_name: str, machine_macro_name: str) -> str:
    """
    Emit the tables, action functions, engine and glue of a machine.

    The block expects what a template defines before it: the public header, the
    private structure from :func:`render_c_kernel_types`, ``_<Class>GuardFn`` and
    ``_<Class>ActionFn``, ``_<Class>_set_error(machine, fmt, ...)`` and
    ``_<Class>_event_active(priv, event_id)``.

    :param model: State machine the runtime is generated for.
    :type model: pyfcstm.model.model.StateMachine
    :param machine_class_name: Public class prefix, for example ``RootMachine``.
    :type machine_class_name: str
    :param machine_macro_name: Public macro prefix, for example ``ROOT_MACHINE``.
    :type machine_macro_name: str
    :return: C source to place after the helpers and before the public API.
    :rtype: str

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     [*] -> A;
        ...     state A;
        ... }
        ... ''')
        >>> text = render_c_kernel_code(model, 'RootMachine', 'ROOT_MACHINE')
        >>> 'static int _RootMachine_search(' in text
        True
    """
    plan = _Plan(model)
    values = _fill_values(plan, machine_class_name, machine_macro_name)
    emitter = _Emitter(plan, machine_class_name, machine_macro_name)
    tables = emitter.render()
    hook_cases = []
    for row in hook_rows(model):
        field = row["hook_field"]
        hook_cases.append(
            "    case %d:\n        if (m->hooks->%s != NULL) {\n"
            "            m->hooks->%s(_%s_pub(m), &ctx, m->hook_user_data);\n        }\n        break;"
            % (plan.hook_id(row["func_name"]), field, field, machine_class_name)
        )
    glue = _HOOK_AND_GLUE.replace("@HOOK_CASES@", "\n".join(hook_cases))
    return _fill(_TABLE_TYPES, values) + tables + _fill(ENGINE_CODE, values) + _fill(glue, values)
