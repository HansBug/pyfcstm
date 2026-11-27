"""
C text of the execution engine shared by the built-in C runtime templates.

The engine is the part of a generated C runtime that decides what one cycle does
for a model with states, pseudo states, composite states and ordered regions. It
follows the simulator's structure method by method (see
:class:`pyfcstm.simulate.runtime.SimulationRuntime`): an *execution level* walks
one path through the configuration tree and never backs out, and at every choice
point a *judgement level* asks on copies whether a candidate has a stable
continuation, takes the first candidate that does, and runs it for real. The
copies live in a fixed arena inside the machine, so the engine uses no heap.

The text here does not depend on the model. Everything that does (state and
region tables, the action functions, the capacities, the names) is produced by
:mod:`pyfcstm.render.c_kernel`, which also fills the ``@...@`` placeholders of
the text below:

* ``@M@`` / ``@MM@`` - the machine class and macro names
* ``@P@`` / ``@T@`` - the prefixes of the internal functions and types
* ``@NS@``, ``@NR@``, ``@NSR@``, ``@MAXD_MAIN@``, ``@MAXD_REG@``, ``@ARENA_CAP@``,
  ``@TRAIL_CAP@``, ``@ROOT_ID@`` ... - numbers derived from the model

The module contains:

* :data:`ENGINE_TYPES` - Type and capacity declarations of the engine
* :data:`ENGINE_CODE` - The functions of the engine

Example::

    >>> from pyfcstm.render.c_kernel_engine import ENGINE_CODE
    >>> '@P@search' in ENGINE_CODE
    True
"""

#: C type declarations of the search engine, with ``@NAME@`` placeholders that
#: :mod:`pyfcstm.render.c_kernel` fills per model.
#:
#: :meta hide-value:
ENGINE_TYPES = r'''
/* Frame modes. RM_NONE only marks a region branch that holds no frame at all. */
enum {
    @MM@_K_ACTIVE = 0,
    @MM@_K_AFTER_ENTRY = 1,
    @MM@_K_INIT_WAIT = 2,
    @MM@_K_POST_CHILD_EXIT = 3,
    @MM@_K_RM_NONE = 4
};
/* Outcomes of the execution level (the simulator's _STABLE, _ENDED, ...). */
enum {
    @MM@_K_O_STABLE = 0,
    @MM@_K_O_ENDED = 1,
    @MM@_K_O_REGION_DONE = 2,
    @MM@_K_O_FAILED = 3,
    @MM@_K_O_CONTINUE = 4,
    @MM@_K_O_LOOP = 5,
    @MM@_K_O_ERR = -1
};
/* Answers of the judgement level. B_LOOP is the simulator's livelock error. */
enum { @MM@_K_B_FALSE = 0, @MM@_K_B_TRUE = 1, @MM@_K_B_LOOP = 2, @MM@_K_B_ERR = -1 };
/* Results of a candidate selection besides a transition id. */
enum { @MM@_K_SEL_NONE = -1, @MM@_K_SEL_LOOP = -2, @MM@_K_SEL_ERR = -3 };
/* What kind of failure ended a cycle; only informs the message. */
enum {
    @MM@_K_E_NONE = 0,
    @MM@_K_E_LOOP = 1,
    @MM@_K_E_STEP = 2,
    @MM@_K_E_DEPTH = 3,
    @MM@_K_E_CAPACITY = 4,
    @MM@_K_E_OTHER = 5
};
enum { @MM@_K_V_NONE = 0, @MM@_K_V_TRANSITION = 1, @MM@_K_V_INITIAL = 2 };
enum { @MM@_K_ORIGIN = 1, @MM@_K_CONT = 2 };

/* 64-bit FNV constants written without a long long literal, so the file also builds as C++98. */
#define @MM@_K_FNV_PRIME ((((PYFCSTM_GENERATED_UINT64)0x100u) << 32) | (PYFCSTM_GENERATED_UINT64)0x000001B3u)
#define @MM@_K_FNV_BASIS ((((PYFCSTM_GENERATED_UINT64)0xCBF29CE4u) << 32) | (PYFCSTM_GENERATED_UINT64)0x84222325u)

/* Search budgets. A search stops with an error after @MM@_K_STEP_LIMIT steps. The capacities of the
 * arena and of the trail are public macros of machine.h, because the size of a machine depends on them. */
#define @MM@_K_STEP_LIMIT 1000
#define @MM@_K_GROUP_DEPTH_LIMIT 64
#define @MM@_K_DEPTH_LIMIT 64

typedef struct @T@Frame {
    short state;
    unsigned char mode;
    unsigned char plain_before_pending;
} @T@Frame;

typedef struct @T@MainStack {
    @T@Frame frames[@MAXD_MAIN@];
    int size;
} @T@MainStack;

/* The stack of one region branch; the region frame itself is `region_mode`. */
typedef struct @T@RegionStack {
    @T@Frame frames[@MAXD_REG@];
    int size;
    unsigned char region_mode;
    unsigned char plain_before_pending;
} @T@RegionStack;

/* Everything one execution of a cycle reads and writes: the whole configuration tree. */
typedef struct @T@Ctx {
    @M@Vars vars;
    @T@MainStack main;
    @T@RegionStack regions[@NRX@];
    unsigned char ended;
    unsigned char before_done[@NSR@];
    unsigned char after_pending[@NSR@];
} @T@Ctx;

/* Link from a branch stack to the stack whose top frame owns it. stack -1 is the main stack. */
typedef struct @T@Outer {
    int stack;
    int index;
    const struct @T@Outer *parent;
} @T@Outer;

/* A copy of a context: a search worklist item or an entry of the seen set of a run. */
typedef struct @T@Node {
    @T@Ctx ctx;
    PYFCSTM_GENERATED_UINT64 hash;
    int parent;
    short stack;
    unsigned char visited;
    unsigned char ended;
    unsigned char hashed;
} @T@Node;

/* An entry of the continuation trail: a check that is under way. */
typedef struct @T@TrailEntry {
    int kind;
    const @T@Ctx *ctx;
    int stack;
    const @T@Outer *chain;
} @T@TrailEntry;

typedef struct @T@Run {
    int base;
    int steps;
} @T@Run;

typedef struct @T@Stack {
    @T@Frame *frames;
    int *size;
    int capacity;
    int stack;
} @T@Stack;
'''

#: C code of the search engine, with ``@NAME@`` placeholders that
#: :mod:`pyfcstm.render.c_kernel` fills per model.
#:
#: :meta hide-value:
ENGINE_CODE = r'''
/* ---------------------------------------------------------------------------
 * Execution engine. Each function names the simulator method it follows.
 * ------------------------------------------------------------------------- */

#define @MM@_K_MIX(h, v) ((h) = (((h) ^ (PYFCSTM_GENERATED_UINT64)(v)) * @MM@_K_FNV_PRIME) ^ ((h) >> 31))

static @T@Stack @P@stack_of(@T@Ctx *c, int stack)
{
    @T@Stack s;
    if (stack < 0) {
        s.frames = c->main.frames;
        s.size = &c->main.size;
        s.capacity = @MAXD_MAIN@;
    } else {
        s.frames = c->regions[stack].frames;
        s.size = &c->regions[stack].size;
        s.capacity = @MAXD_REG@;
    }
    s.stack = stack;
    return s;
}

static int @P@is_stoppable(int state)
{
    return @P@states[state].kind == 0 && !@P@is_pseudo[state];
}

static int @P@no_outgoing_pseudo(int state)
{
    return @P@is_pseudo[state] && @P@states[state].outgoing_count == 0;
}

static int @P@region_done(const @T@Ctx *c, int region)
{
    return c->regions[region].size == 0 && c->regions[region].region_mode == @MM@_K_POST_CHILD_EXIT;
}

static int @P@region_pending(const @T@Ctx *c, int region)
{
    return c->regions[region].size == 0 && c->regions[region].region_mode != @MM@_K_POST_CHILD_EXIT;
}

/* Run an action of the model: 0 on success or when there is none, -1 when it failed. */
static int @P@run_action(@T@Priv *m, @T@Ctx *c, @T@ActionFn fn)
{
    return fn == NULL || fn(@P@pub(m), &c->vars) == @MM@_SUCCESS ? 0 : -1;
}

static void @P@fail(@T@Priv *m, int kind, const char *text)
{
    m->error_kind = kind;
    @P@set_error(@P@pub(m), "%s", text);
}

/* _check_structural_limit: a stack that nests deeper than the safety limit is an unbounded chain. */
static int @P@check_depth(@T@Priv *m, const @T@Ctx *c, int stack)
{
    int depth = stack < 0 ? c->main.size : c->regions[stack].size + 1;
    if (depth > @MM@_K_DEPTH_LIMIT) {
        @P@fail(
            m,
            @MM@_K_E_DEPTH,
            "Speculative DFS exceeded the structural stack-depth safety limit (64) without reaching a stoppable state "
            "or pruning; the state machine likely contains an invalid unbounded nesting chain.");
        return -1;
    }
    return 0;
}

/* ---- arena: copies of contexts, used last in first out ---- */

static int @P@arena_alloc(@T@Priv *m, const @T@Ctx *src, int stack)
{
    int k;
    if (m->arena_top >= @MM@_ARENA_CAPACITY) {
        @P@set_error(
            @P@pub(m),
            "Speculative search exceeded the capacity safety limit (%d configurations); "
            "define @MM@_ARENA_CAPACITY to a larger value to allow a longer search.",
            (int)@MM@_ARENA_CAPACITY);
        m->error_kind = @MM@_K_E_CAPACITY;
        return -1;
    }
    k = m->arena_top++;
    m->arena[k].ctx = *src;
    m->arena[k].stack = (short)stack;
    m->arena[k].parent = -1;
    m->arena[k].visited = 0;
    m->arena[k].ended = 0;
    m->arena[k].hash = 0;
    m->arena[k].hashed = 0;
    return k;
}

/* ---- signatures (_stack_shape, _create_execution_signature, _enclosing_shapes) ---- */

static int @P@region_equal(const @T@Ctx *a, const @T@Ctx *b, int region);

static int @P@frames_equal(const @T@Ctx *a, const @T@Ctx *b, const @T@Frame *fa, const @T@Frame *fb, int n, int skip)
{
    int i, k;
    for (i = 0; i < n; ++i) {
        if (fa[i].state != fb[i].state || fa[i].mode != fb[i].mode
            || fa[i].plain_before_pending != fb[i].plain_before_pending) {
            return 0;
        }
        if (@P@states[fa[i].state].kind == 2) {
            for (k = 0; k < @P@states[fa[i].state].region_count; ++k) {
                if (i == n - 1 && k == skip) {
                    continue;
                }
                if (!@P@region_equal(a, b, @P@states[fa[i].state].regions[k])) {
                    return 0;
                }
            }
        }
    }
    return 1;
}

static int @P@region_equal(const @T@Ctx *a, const @T@Ctx *b, int region)
{
    const @T@RegionStack *x = &a->regions[region];
    const @T@RegionStack *y = &b->regions[region];
    if (x->region_mode != y->region_mode) {
        return 0;
    }
    if (x->region_mode == @MM@_K_RM_NONE) {
        return 1;
    }
    if (x->plain_before_pending != y->plain_before_pending || x->size != y->size) {
        return 0;
    }
    return @P@frames_equal(a, b, x->frames, y->frames, x->size, -1);
}

static int @P@stack_equal(const @T@Ctx *a, const @T@Ctx *b, int stack, int skip)
{
    if (stack < 0) {
        if (a->main.size != b->main.size) {
            return 0;
        }
        return @P@frames_equal(a, b, a->main.frames, b->main.frames, a->main.size, skip);
    }
    {
        const @T@RegionStack *x = &a->regions[stack];
        const @T@RegionStack *y = &b->regions[stack];
        if (x->region_mode != y->region_mode) {
            return 0;
        }
        if (x->region_mode == @MM@_K_RM_NONE) {
            return 1;
        }
        if (x->plain_before_pending != y->plain_before_pending || x->size != y->size) {
            return 0;
        }
        return @P@frames_equal(a, b, x->frames, y->frames, x->size, skip);
    }
}

static PYFCSTM_GENERATED_UINT64 @P@frames_hash(const @T@Ctx *c, const @T@Frame *f, int n, PYFCSTM_GENERATED_UINT64 h);

static PYFCSTM_GENERATED_UINT64 @P@region_hash(const @T@Ctx *c, int region, PYFCSTM_GENERATED_UINT64 h)
{
    const @T@RegionStack *x = &c->regions[region];
    @MM@_K_MIX(h, 0x100 + x->region_mode);
    if (x->region_mode == @MM@_K_RM_NONE) {
        return h;
    }
    @MM@_K_MIX(h, x->plain_before_pending);
    @MM@_K_MIX(h, x->size);
    return @P@frames_hash(c, x->frames, x->size, h);
}

static PYFCSTM_GENERATED_UINT64 @P@frames_hash(const @T@Ctx *c, const @T@Frame *f, int n, PYFCSTM_GENERATED_UINT64 h)
{
    int i, k;
    for (i = 0; i < n; ++i) {
        @MM@_K_MIX(h, f[i].state);
        @MM@_K_MIX(h, f[i].mode);
        @MM@_K_MIX(h, f[i].plain_before_pending);
        if (@P@states[f[i].state].kind == 2) {
            for (k = 0; k < @P@states[f[i].state].region_count; ++k) {
                h = @P@region_hash(c, @P@states[f[i].state].regions[k], h);
            }
        }
    }
    return h;
}

static PYFCSTM_GENERATED_UINT64 @P@signature_hash(const @T@Ctx *c, int stack)
{
    PYFCSTM_GENERATED_UINT64 h = @P@vars_hash(&c->vars);
    @MM@_K_MIX(h, stack + 7);
    if (stack < 0) {
        @MM@_K_MIX(h, c->main.size);
        return @P@frames_hash(c, c->main.frames, c->main.size, h);
    }
    return @P@region_hash(c, stack, h);
}

static int @P@signature_equal(const @T@Ctx *a, const @T@Ctx *b, int stack)
{
    return @P@vars_equal(&a->vars, &b->vars) && @P@stack_equal(a, b, stack, -1);
}

/*
 * The hash of a node only filters candidates for the exact comparison above, so it is computed when a
 * search or a run has grown past SMALL_SET nodes and compared directly before that. Either way the
 * answer is decided by signature_equal.
 */
#define @MM@_K_SMALL_SET 8

static PYFCSTM_GENERATED_UINT64 @P@node_hash(@T@Priv *m, int k)
{
    if (!m->arena[k].hashed) {
        m->arena[k].hash = @P@signature_hash(&m->arena[k].ctx, m->arena[k].stack);
        m->arena[k].hashed = 1;
    }
    return m->arena[k].hash;
}

static int @P@chain_equal(const @T@Ctx *a, const @T@Outer *oa, const @T@Ctx *b, const @T@Outer *ob)
{
    while (oa != NULL && ob != NULL) {
        if (oa->stack != ob->stack || oa->index != ob->index) {
            return 0;
        }
        if (!@P@stack_equal(a, b, oa->stack, oa->index)) {
            return 0;
        }
        oa = oa->parent;
        ob = ob->parent;
    }
    return oa == NULL && ob == NULL;
}

static int @P@ledger_equal(const @T@Ctx *a, const @T@Ctx *b)
{
    return memcmp(a->before_done, b->before_done, sizeof(a->before_done)) == 0
        && memcmp(a->after_pending, b->after_pending, sizeof(a->after_pending)) == 0;
}

static int @P@on_trail(const @T@Priv *m, int kind, const @T@Ctx *c, int stack, const @T@Outer *chain)
{
    int i;
    for (i = 0; i < m->trail_size; ++i) {
        const @T@TrailEntry *e = &m->trail[i];
        if (e->kind != kind || e->stack != stack) {
            continue;
        }
        if (!@P@signature_equal(e->ctx, c, stack)) {
            continue;
        }
        if (!@P@chain_equal(e->ctx, e->chain, c, chain)) {
            continue;
        }
        if (kind == @MM@_K_ORIGIN && !@P@ledger_equal(e->ctx, c)) {
            continue;
        }
        return 1;
    }
    return 0;
}

static int @P@trail_push(@T@Priv *m, int kind, const @T@Ctx *c, int stack, const @T@Outer *chain)
{
    if (m->trail_size >= @MM@_TRAIL_CAPACITY) {
        @P@set_error(
            @P@pub(m),
            "Speculative search exceeded the capacity safety limit (%d nested checks); "
            "define @MM@_TRAIL_CAPACITY to a larger value to allow deeper nesting.",
            (int)@MM@_TRAIL_CAPACITY);
        m->error_kind = @MM@_K_E_CAPACITY;
        return -1;
    }
    m->trail[m->trail_size].kind = kind;
    m->trail[m->trail_size].ctx = c;
    m->trail[m->trail_size].stack = stack;
    m->trail[m->trail_size].chain = chain;
    ++m->trail_size;
    return 0;
}

/* ---- aspects (_run_scoped_during, _flush_after_aspects) ---- */

static int @P@run_leaf_during(@T@Priv *m, @T@Ctx *c, int state)
{
    int chain[@NSR@ + 1], n = 0, scope, i;
    for (scope = @P@scope_parent[state]; scope >= 0; scope = @P@scope_parent[scope]) {
        chain[n++] = scope;
    }
    if (!@P@is_pseudo[state]) {
        for (i = n - 1; i >= 0; --i) {
            scope = chain[i];
            if (!c->before_done[scope]) {
                c->before_done[scope] = 1;
                if (@P@run_action(m, c, @P@aspect_before[scope]) != 0) {
                    return -1;
                }
            }
        }
    }
    if (@P@run_action(m, c, @P@states[state].during) != 0) {
        return -1;
    }
    if (!@P@is_pseudo[state]) {
        for (i = 0; i < n; ++i) {
            c->after_pending[chain[i]] = 1;
        }
    }
    return 0;
}

static int @P@under_scope(int scope, int ancestor)
{
    while (scope >= 0) {
        if (scope == ancestor) {
            return 1;
        }
        scope = @P@scope_parent[scope];
    }
    return 0;
}

static int @P@flush_after(@T@Priv *m, @T@Ctx *c, int prefix_scope)
{
    int k;
    for (k = 0; k < @NSR@; ++k) {
        int scope = @P@flush_order[k];
        if (!c->after_pending[scope]) {
            continue;
        }
        if (prefix_scope >= 0 && !@P@under_scope(scope, prefix_scope)) {
            continue;
        }
        c->after_pending[scope] = 0;
        if (@P@run_action(m, c, @P@aspect_after[scope]) != 0) {
            return -1;
        }
    }
    return 0;
}

/* ---- structural steps (_enter_state, _execute_*_on_context) ---- */

static int @P@enter_state(@T@Priv *m, @T@Ctx *c, int stack, int state)
{
    @T@Stack st = @P@stack_of(c, stack);
    int index, k;
    if (*st.size >= st.capacity) {
        @P@fail(m, @MM@_K_E_OTHER, "Runtime stack overflow.");
        return -1;
    }
    index = (*st.size)++;
    st.frames[index].state = (short)state;
    st.frames[index].mode = @MM@_K_ACTIVE;
    st.frames[index].plain_before_pending = 0;
    if (@P@no_outgoing_pseudo(state)) {
        return 0;
    }
    if (@P@run_action(m, c, @P@states[state].enter) != 0) {
        return -1;
    }
    if (@P@states[state].kind == 0) {
        if (@P@run_leaf_during(m, c, state) != 0) {
            return -1;
        }
        st.frames[index].mode = @MM@_K_AFTER_ENTRY;
    } else {
        st.frames[index].mode = @MM@_K_INIT_WAIT;
        st.frames[index].plain_before_pending = 1;
        for (k = 0; k < @P@states[state].region_count; ++k) {
            @T@RegionStack *rs = &c->regions[@P@states[state].regions[k]];
            rs->size = 0;
            rs->region_mode = @MM@_K_RM_NONE;
            rs->plain_before_pending = 0;
        }
    }
    return 0;
}

/* The top is a waiting composite or a region frame. */
static int @P@execute_initial(@T@Priv *m, @T@Ctx *c, int stack, int tid)
{
    const @T@Transition *t = &@P@transitions[tid];
    @T@Stack st = @P@stack_of(c, stack);
    int index = *st.size - 1;
    if (@P@run_action(m, c, t->effect) != 0) {
        return -1;
    }
    if (!@P@is_pseudo[t->to]) {
        if (index >= 0) {
            if (st.frames[index].plain_before_pending) {
                if (@P@run_action(m, c, @P@plain_before[st.frames[index].state]) != 0) {
                    return -1;
                }
                st.frames[index].plain_before_pending = 0;
            }
        } else if (c->regions[stack].plain_before_pending) {
            if (@P@run_action(m, c, @P@plain_before[@P@regions_info[stack].owner]) != 0) {
                return -1;
            }
            c->regions[stack].plain_before_pending = 0;
        }
    }
    if (@P@enter_state(m, c, stack, t->to) != 0) {
        return -1;
    }
    if (index >= 0) {
        st.frames[index].mode = @MM@_K_ACTIVE;
    } else {
        c->regions[stack].region_mode = @MM@_K_ACTIVE;
    }
    return 0;
}

/* 1 when the machine ended, 0 otherwise, -1 on error. */
static int @P@execute_transition(@T@Priv *m, @T@Ctx *c, int stack, int tid)
{
    const @T@Transition *t = &@P@transitions[tid];
    @T@Stack st = @P@stack_of(c, stack);
    int source = st.frames[*st.size - 1].state;
    if (@P@run_action(m, c, @P@states[source].exit) != 0) {
        return -1;
    }
    if (@P@run_action(m, c, t->effect) != 0) {
        return -1;
    }
    --*st.size;
    if (t->to == -2) {
        int parent;
        if (@P@is_pseudo[source] && *st.size > 0 && st.frames[*st.size - 1].state == @P@scope_parent[source]
            && st.frames[*st.size - 1].plain_before_pending) {
            st.frames[*st.size - 1].plain_before_pending = 0;
        }
        if (*st.size == 0) {
            if (stack >= 0) {
                c->regions[stack].region_mode = @MM@_K_POST_CHILD_EXIT;
                return 0;
            }
            c->ended = 1;
            return 1;
        }
        parent = st.frames[*st.size - 1].state;
        if (@P@run_action(m, c, @P@plain_after[parent]) != 0) {
            return -1;
        }
        if (stack < 0 && *st.size == 1) {
            if (@P@run_action(m, c, @P@states[parent].exit) != 0) {
                return -1;
            }
            *st.size = 0;
            c->ended = 1;
            return 1;
        }
        st.frames[*st.size - 1].mode = @MM@_K_POST_CHILD_EXIT;
        return 0;
    }
    if (@P@is_pseudo[source] && !@P@is_pseudo[t->to]) {
        if (*st.size > 0) {
            @T@Frame *p = &st.frames[*st.size - 1];
            if (p->plain_before_pending) {
                if (@P@run_action(m, c, @P@plain_before[p->state]) != 0) {
                    return -1;
                }
                p->plain_before_pending = 0;
            }
        } else if (c->regions[stack].plain_before_pending) {
            if (@P@run_action(m, c, @P@plain_before[@P@regions_info[stack].owner]) != 0) {
                return -1;
            }
            c->regions[stack].plain_before_pending = 0;
        }
    }
    return @P@enter_state(m, c, stack, t->to) != 0 ? -1 : 0;
}

/* The candidates of the top of a stack: its outgoing transitions or its initial transitions. */
static void @P@candidates(const @T@Ctx *c, int stack, int initial, const int **ids, int *count)
{
    const @T@Frame *f = stack < 0 ? c->main.frames : c->regions[stack].frames;
    int depth = stack < 0 ? c->main.size : c->regions[stack].size;
    if (initial) {
        if (depth > 0) {
            *ids = @P@states[f[depth - 1].state].initial;
            *count = @P@states[f[depth - 1].state].initial_count;
        } else {
            *ids = @P@regions_info[stack].initial;
            *count = @P@regions_info[stack].initial_count;
        }
        return;
    }
    *ids = @P@states[f[depth - 1].state].outgoing;
    *count = @P@states[f[depth - 1].state].outgoing_count;
}

static int @P@search(@T@Priv *m, const @T@Ctx *start, int stack, const @T@Outer *outer, const @T@Ctx *trail0);
static int @P@init_group(@T@Priv *m, @T@Ctx *c, int stack, const @T@Outer *outer);
static int @P@advance_stack(@T@Priv *m, @T@Ctx *c, int stack, @T@Run *run);

/* _validate_transition */
static int @P@validate_transition(@T@Priv *m, const @T@Ctx *c, int stack, int tid)
{
    int mark = m->arena_top, k, e, r;
    k = @P@arena_alloc(m, c, stack);
    if (k < 0) {
        return @MM@_K_B_ERR;
    }
    e = @P@execute_transition(m, &m->arena[k].ctx, stack, tid);
    if (e < 0) {
        m->arena_top = mark;
        return @MM@_K_B_ERR;
    }
    if (e == 1) {
        m->arena_top = mark;
        return @MM@_K_B_TRUE;
    }
    r = @P@search(m, &m->arena[k].ctx, stack, m->outer, c);
    m->arena_top = mark;
    return r;
}

/* _validate_initial_transition */
static int @P@validate_initial(@T@Priv *m, const @T@Ctx *c, int stack, int tid)
{
    int mark = m->arena_top, k, r;
    k = @P@arena_alloc(m, c, stack);
    if (k < 0) {
        return @MM@_K_B_ERR;
    }
    if (@P@execute_initial(m, &m->arena[k].ctx, stack, tid) != 0) {
        m->arena_top = mark;
        return @MM@_K_B_ERR;
    }
    r = @P@search(m, &m->arena[k].ctx, stack, m->outer, c);
    m->arena_top = mark;
    return r;
}

/* _check_candidate */
static int @P@check_candidate(@T@Priv *m, const @T@Ctx *c, int stack, int tid, int validator)
{
    const @T@Transition *t = &@P@transitions[tid];
    int ok = 1, r;
    if (t->event >= 0 && !@P@event_active(m, c, t->event)) {
        return @MM@_K_B_FALSE;
    }
    if (t->guard != NULL && t->guard(@P@pub(m), &c->vars, &ok) != @MM@_SUCCESS) {
        return @MM@_K_B_ERR;
    }
    if (!ok) {
        return @MM@_K_B_FALSE;
    }
    if (validator == @MM@_K_V_NONE) {
        return @MM@_K_B_TRUE;
    }
    /* A check under way owns the point it started from; coming back to it further in is a loop. */
    if (@P@on_trail(m, @MM@_K_ORIGIN, c, stack, m->outer)) {
        return @MM@_K_B_LOOP;
    }
    if (@P@trail_push(m, @MM@_K_ORIGIN, c, stack, m->outer) != 0) {
        return @MM@_K_B_ERR;
    }
    ++m->speculation;
    r = validator == @MM@_K_V_INITIAL ? @P@validate_initial(m, c, stack, tid) : @P@validate_transition(m, c, stack, tid);
    --m->speculation;
    --m->trail_size;
    return r;
}

/* _select_valid_candidate */
static int @P@select_valid(@T@Priv *m, const @T@Ctx *c, int stack, int initial)
{
    const int *ids;
    int count, i, loop = 0;
    @P@candidates(c, stack, initial, &ids, &count);
    for (i = 0; i < count; ++i) {
        int r = @P@check_candidate(m, c, stack, ids[i], initial ? @MM@_K_V_INITIAL : @MM@_K_V_TRANSITION);
        if (r == @MM@_K_B_ERR) {
            return @MM@_K_SEL_ERR;
        }
        if (r == @MM@_K_B_LOOP) {
            loop = 1;
            continue;
        }
        if (r == @MM@_K_B_TRUE) {
            return ids[i];
        }
    }
    return loop ? @MM@_K_SEL_LOOP : @MM@_K_SEL_NONE;
}

/* _owner_can_continue */
static int @P@owner_can_continue(@T@Priv *m, const @T@Ctx *c, int stack, const @T@Outer *outer)
{
    int r;
    if (@P@on_trail(m, @MM@_K_CONT, c, stack, outer)) {
        return @MM@_K_B_LOOP;
    }
    if (@P@trail_push(m, @MM@_K_CONT, c, stack, outer) != 0) {
        return @MM@_K_B_ERR;
    }
    r = @P@search(m, c, stack, outer, NULL);
    --m->trail_size;
    return r;
}

/* _continuation_viable: the region on top of its branch is finished in `c`. */
static int @P@continuation_viable(@T@Priv *m, const @T@Ctx *c, const @T@Outer *outer)
{
    int owner, k, mark = m->arena_top, r;
    @T@Stack os = @P@stack_of((@T@Ctx *)c, outer->stack);
    owner = os.frames[*os.size - 1].state;
    for (k = 0; k < @P@states[owner].region_count; ++k) {
        if (!@P@region_done(c, @P@states[owner].regions[k])) {
            return @MM@_K_B_TRUE;
        }
    }
    k = @P@arena_alloc(m, c, outer->stack);
    if (k < 0) {
        return @MM@_K_B_ERR;
    }
    if (@P@run_action(m, &m->arena[k].ctx, @P@plain_after[owner]) != 0) {
        m->arena_top = mark;
        return @MM@_K_B_ERR;
    }
    os = @P@stack_of(&m->arena[k].ctx, outer->stack);
    os.frames[*os.size - 1].mode = @MM@_K_POST_CHILD_EXIT;
    r = @P@owner_can_continue(m, &m->arena[k].ctx, outer->stack, outer->parent);
    m->arena_top = mark;
    return r;
}

static int @P@on_search_path(@T@Priv *m, int node, int hashed, int stack, const @T@Ctx *trail0)
{
    int p;
    PYFCSTM_GENERATED_UINT64 h = hashed ? @P@node_hash(m, node) : 0;
    for (p = m->arena[node].parent; p >= 0; p = m->arena[p].parent) {
        if ((!hashed || @P@node_hash(m, p) == h) && @P@signature_equal(&m->arena[p].ctx, &m->arena[node].ctx, stack)) {
            return 1;
        }
    }
    return trail0 != NULL && @P@signature_equal(trail0, &m->arena[node].ctx, stack);
}

static int @P@push_work(@T@Priv *m, int k)
{
    if (m->work_size >= @MM@_ARENA_CAPACITY) {
        @P@set_error(
            @P@pub(m),
            "Speculative search exceeded the capacity safety limit (%d work items); "
            "define @MM@_ARENA_CAPACITY to a larger value to allow a longer search.",
            (int)@MM@_ARENA_CAPACITY);
        m->error_kind = @MM@_K_E_CAPACITY;
        return -1;
    }
    m->work[m->work_size++] = k;
    return 0;
}

/* _search_stable_continuation */
static int @P@search(@T@Priv *m, const @T@Ctx *start, int stack, const @T@Outer *outer, const @T@Ctx *trail0)
{
    int mark = m->arena_top, wmark = m->work_size, root, loop = 0, result = @MM@_K_B_FALSE;
    long steps = 0;
    root = @P@arena_alloc(m, start, stack);
    if (root < 0) {
        return @MM@_K_B_ERR;
    }
    if (@P@push_work(m, root) != 0) {
        result = @MM@_K_B_ERR;
        goto out;
    }
    while (m->work_size > wmark) {
        int k = m->work[--m->work_size], j, i, count, index, s, mode;
        int hashed;
        const int *ids;
        @T@Ctx *cur;
        @T@Stack st;
        if (m->arena[k].ended) {
            result = @MM@_K_B_TRUE;
            goto out;
        }
        if (@P@check_depth(m, &m->arena[k].ctx, stack) != 0) {
            result = @MM@_K_B_ERR;
            goto out;
        }
        hashed = m->arena_top - mark > @MM@_K_SMALL_SET;
        if (@P@on_search_path(m, k, hashed, stack, trail0)) {
            loop = 1;
            continue;
        }
        for (j = mark; j < m->arena_top; ++j) {
            if (m->arena[j].visited && (!hashed || @P@node_hash(m, j) == @P@node_hash(m, k))
                && @P@signature_equal(&m->arena[j].ctx, &m->arena[k].ctx, stack)) {
                break;
            }
        }
        if (j < m->arena_top) {
            continue;
        }
        m->arena[k].visited = 1;
        if (steps >= @MM@_K_STEP_LIMIT) {
            @P@fail(
                m,
                @MM@_K_E_STEP,
                "Speculative DFS exceeded the step safety limit (1000) without reaching a stoppable state or pruning; "
                "the state machine likely contains an invalid unbounded pseudo-state or transition chain.");
            result = @MM@_K_B_ERR;
            goto out;
        }
        ++steps;
        cur = &m->arena[k].ctx;
        st = @P@stack_of(cur, stack);
        if (*st.size == 0) {
            int r = @P@continuation_viable(m, cur, outer);
            if (r == @MM@_K_B_ERR) {
                result = @MM@_K_B_ERR;
                goto out;
            }
            if (r == @MM@_K_B_LOOP) {
                loop = 1;
                continue;
            }
            if (r == @MM@_K_B_TRUE) {
                result = @MM@_K_B_TRUE;
                goto out;
            }
            continue;
        }
        index = *st.size - 1;
        s = st.frames[index].state;
        mode = st.frames[index].mode;
        if (@P@states[s].kind == 2 && mode == @MM@_K_INIT_WAIT) {
            int ck = @P@arena_alloc(m, cur, stack), r;
            if (ck < 0) {
                result = @MM@_K_B_ERR;
                goto out;
            }
            m->arena[ck].parent = k;
            r = @P@init_group(m, &m->arena[ck].ctx, stack, outer);
            if (r == @MM@_K_B_ERR) {
                result = @MM@_K_B_ERR;
                goto out;
            }
            if (r == @MM@_K_B_TRUE) {
                if (@P@push_work(m, ck) != 0) {
                    result = @MM@_K_B_ERR;
                    goto out;
                }
            } else {
                m->arena_top = ck;
                if (r == @MM@_K_B_LOOP) {
                    loop = 1;
                }
            }
            continue;
        }
        if (@P@states[s].kind == 2 && (mode == @MM@_K_ACTIVE || mode == @MM@_K_AFTER_ENTRY)) {
            result = @MM@_K_B_TRUE;
            goto out;
        }
        if (@P@states[s].kind == 0 && mode == @MM@_K_AFTER_ENTRY) {
            int ck;
            if (@P@is_stoppable(s)) {
                result = @MM@_K_B_TRUE;
                goto out;
            }
            ck = @P@arena_alloc(m, cur, stack);
            if (ck < 0) {
                result = @MM@_K_B_ERR;
                goto out;
            }
            m->arena[ck].parent = k;
            @P@stack_of(&m->arena[ck].ctx, stack).frames[index].mode = @MM@_K_ACTIVE;
            if (@P@push_work(m, ck) != 0) {
                result = @MM@_K_B_ERR;
                goto out;
            }
            continue;
        }
        {
            int initial = @P@states[s].kind != 0 && mode == @MM@_K_INIT_WAIT;
            @P@candidates(cur, stack, initial, &ids, &count);
            for (i = count - 1; i >= 0; --i) {
                int r, ck, e;
                r = @P@check_candidate(m, cur, stack, ids[i], @MM@_K_V_NONE);
                if (r == @MM@_K_B_ERR) {
                    result = @MM@_K_B_ERR;
                    goto out;
                }
                if (r != @MM@_K_B_TRUE) {
                    continue;
                }
                ck = @P@arena_alloc(m, cur, stack);
                if (ck < 0) {
                    result = @MM@_K_B_ERR;
                    goto out;
                }
                m->arena[ck].parent = k;
                if (initial) {
                    e = @P@execute_initial(m, &m->arena[ck].ctx, stack, ids[i]);
                } else {
                    e = @P@execute_transition(m, &m->arena[ck].ctx, stack, ids[i]);
                }
                if (e < 0) {
                    result = @MM@_K_B_ERR;
                    goto out;
                }
                m->arena[ck].ended = (unsigned char)(e == 1);
                if (@P@push_work(m, ck) != 0) {
                    result = @MM@_K_B_ERR;
                    goto out;
                }
            }
        }
    }
    result = loop ? @MM@_K_B_LOOP : @MM@_K_B_FALSE;
out:
    m->arena_top = mark;
    m->work_size = wmark;
    return result;
}

/* _finish_group_advance */
static int @P@finish_group_advance(@T@Priv *m, @T@Ctx *c, int stack, int entered)
{
    @T@Stack st = @P@stack_of(c, stack);
    @T@Frame *f = &st.frames[*st.size - 1];
    int k, all = 1;
    for (k = 0; k < @P@states[f->state].region_count; ++k) {
        if (!@P@region_done(c, @P@states[f->state].regions[k])) {
            all = 0;
        }
    }
    if (all) {
        if (@P@run_action(m, c, @P@plain_after[f->state]) != 0) {
            return -1;
        }
        f->mode = @MM@_K_POST_CHILD_EXIT;
    } else {
        f->mode = entered ? @MM@_K_AFTER_ENTRY : @MM@_K_ACTIVE;
    }
    return 0;
}

/* _init_group: B_TRUE initialized, B_FALSE a region could not reach a stable position. */
static int @P@init_group(@T@Priv *m, @T@Ctx *c, int stack, const @T@Outer *outer)
{
    @T@Stack st = @P@stack_of(c, stack);
    int index = *st.size - 1, owner = st.frames[index].state, pending = st.frames[index].plain_before_pending;
    int i, result = @MM@_K_B_TRUE;
    if (++m->init_depth > @MM@_K_GROUP_DEPTH_LIMIT) {
        @P@fail(
            m,
            @MM@_K_E_DEPTH,
            "Group initialization nested deeper than the structural safety limit (64) within one cycle; "
            "the state machine either enters more than 64 groups inside one another or one after another "
            "in the same cycle, or re-enters a group without bound.");
        --m->init_depth;
        return @MM@_K_B_ERR;
    }
    for (i = 0; i < @P@states[owner].region_count; ++i) {
        int region = @P@states[owner].regions[i], outcome;
        @T@Run run;
        @T@Outer here;
        const @T@Outer *saved = m->outer;
        c->regions[region].size = 0;
        c->regions[region].region_mode = @MM@_K_INIT_WAIT;
        c->regions[region].plain_before_pending = (unsigned char)pending;
        run.base = m->arena_top;
        run.steps = 0;
        here.stack = stack;
        here.index = i;
        here.parent = outer;
        m->outer = &here;
        outcome = @P@advance_stack(m, c, region, &run);
        m->outer = saved;
        m->arena_top = run.base;
        if (outcome == @MM@_K_O_ERR) {
            result = @MM@_K_B_ERR;
            goto out;
        }
        if (outcome == @MM@_K_O_LOOP) {
            result = @MM@_K_B_LOOP;
            goto out;
        }
        if (outcome != @MM@_K_O_STABLE && outcome != @MM@_K_O_REGION_DONE) {
            result = @MM@_K_B_FALSE;
            goto out;
        }
        if (@P@flush_after(m, c, @NS@ + region) != 0) {
            result = @MM@_K_B_ERR;
            goto out;
        }
        pending = c->regions[region].plain_before_pending;
    }
    st.frames[index].plain_before_pending = 0;
    if (@P@finish_group_advance(m, c, stack, 1) != 0) {
        result = @MM@_K_B_ERR;
    }
out:
    --m->init_depth;
    return result;
}

/* _advance_owner */
static int @P@advance_owner(@T@Priv *m, @T@Ctx *c, int stack, @T@Run *run)
{
    @T@Stack st = @P@stack_of(c, stack);
    int index = *st.size - 1, owner = st.frames[index].state, i;
    if (st.frames[index].mode == @MM@_K_INIT_WAIT) {
        int r = @P@init_group(m, c, stack, m->outer);
        if (r == @MM@_K_B_ERR) {
            return @MM@_K_O_ERR;
        }
        if (r == @MM@_K_B_LOOP) {
            return @MM@_K_O_LOOP;
        }
        return r == @MM@_K_B_TRUE ? @MM@_K_O_CONTINUE : @MM@_K_O_FAILED;
    }
    for (i = 0; i < @P@states[owner].region_count; ++i) {
        int region = @P@states[owner].regions[i], outcome;
        @T@Outer here;
        const @T@Outer *saved = m->outer;
        if (@P@region_done(c, region)) {
            continue;
        }
        if (@P@region_pending(c, region)) {
            c->regions[region].size = 0;
            c->regions[region].region_mode = @MM@_K_INIT_WAIT;
            c->regions[region].plain_before_pending = 0;
        }
        here.stack = stack;
        here.index = i;
        here.parent = saved;
        m->outer = &here;
        outcome = @P@advance_stack(m, c, region, run);
        m->outer = saved;
        if (outcome == @MM@_K_O_ERR || outcome == @MM@_K_O_LOOP) {
            return outcome;
        }
        if (outcome != @MM@_K_O_STABLE && outcome != @MM@_K_O_REGION_DONE) {
            return @MM@_K_O_FAILED;
        }
        if (@P@flush_after(m, c, @NS@ + region) != 0) {
            return @MM@_K_O_ERR;
        }
    }
    if (@P@finish_group_advance(m, c, stack, 0) != 0) {
        return @MM@_K_O_ERR;
    }
    return st.frames[index].mode == @MM@_K_POST_CHILD_EXIT ? @MM@_K_O_CONTINUE : @MM@_K_O_STABLE;
}

/* The seen set of a _Run: 1 when this stack and these values were met before in this run. */
static int @P@run_seen(@T@Priv *m, @T@Run *run, const @T@Ctx *c, int stack)
{
    int hashed = m->arena_top - run->base > @MM@_K_SMALL_SET;
    PYFCSTM_GENERATED_UINT64 h = hashed ? @P@signature_hash(c, stack) : 0;
    int j, k;
    for (j = run->base; j < m->arena_top; ++j) {
        if (m->arena[j].stack == stack && (!hashed || @P@node_hash(m, j) == h)
            && @P@signature_equal(&m->arena[j].ctx, c, stack)) {
            return 1;
        }
    }
    k = @P@arena_alloc(m, c, stack);
    if (k < 0) {
        return -1;
    }
    if (hashed) {
        m->arena[k].hash = h;
        m->arena[k].hashed = 1;
    }
    return 0;
}

static int @P@attempt_init(@T@Priv *m, @T@Ctx *c, int stack)
{
    int t = @P@select_valid(m, c, stack, 1);
    if (t == @MM@_K_SEL_ERR) {
        return @MM@_K_O_ERR;
    }
    if (t == @MM@_K_SEL_LOOP) {
        return @MM@_K_O_LOOP;
    }
    if (t == @MM@_K_SEL_NONE) {
        return @MM@_K_O_FAILED;
    }
    return @P@execute_initial(m, c, stack, t) != 0 ? @MM@_K_O_ERR : @MM@_K_O_CONTINUE;
}

static void @P@note_steps(@T@Run *run)
{
    ++run->steps;
}

/* _advance_stack */
static int @P@advance_stack(@T@Priv *m, @T@Ctx *c, int stack, @T@Run *run)
{
    for (;;) {
        @T@Stack st = @P@stack_of(c, stack);
        int seen = @P@run_seen(m, run, c, stack), index, s, r, t;
        @T@Frame *top;
        if (seen < 0) {
            return @MM@_K_O_ERR;
        }
        if (seen) {
            return @MM@_K_O_FAILED;
        }
        if (@P@check_depth(m, c, stack) != 0) {
            return @MM@_K_O_ERR;
        }
        if (run->steps >= @MM@_K_STEP_LIMIT) {
            @P@fail(
                m,
                @MM@_K_E_STEP,
                "Speculative DFS exceeded the step safety limit (1000) without reaching a stoppable state or pruning; "
                "the state machine likely contains an invalid unbounded pseudo-state or transition chain.");
            return @MM@_K_O_ERR;
        }
        if (*st.size == 0) {
            if (c->regions[stack].region_mode == @MM@_K_POST_CHILD_EXIT) {
                return @MM@_K_O_REGION_DONE;
            }
            r = @P@attempt_init(m, c, stack);
            @P@note_steps(run);
            if (r != @MM@_K_O_CONTINUE) {
                return r;
            }
            continue;
        }
        index = *st.size - 1;
        top = &st.frames[index];
        s = top->state;
        if (@P@no_outgoing_pseudo(s)) {
            return @MM@_K_O_FAILED;
        }
        if (@P@states[s].kind == 2 && top->mode == @MM@_K_AFTER_ENTRY) {
            top->mode = @MM@_K_ACTIVE;
            return @MM@_K_O_STABLE;
        }
        if (@P@states[s].kind == 2 && top->mode != @MM@_K_POST_CHILD_EXIT) {
            r = @P@advance_owner(m, c, stack, run);
            @P@note_steps(run);
            if (r == @MM@_K_O_CONTINUE) {
                continue;
            }
            return r;
        }
        if (@P@states[s].kind == 0) {
            if (top->mode == @MM@_K_AFTER_ENTRY) {
                top->mode = @MM@_K_ACTIVE;
                if (@P@is_stoppable(s)) {
                    return @MM@_K_O_STABLE;
                }
                @P@note_steps(run);
                continue;
            }
            t = @P@select_valid(m, c, stack, 0);
            if (t == @MM@_K_SEL_ERR) {
                return @MM@_K_O_ERR;
            }
            if (t == @MM@_K_SEL_LOOP) {
                return @MM@_K_O_LOOP;
            }
            if (t >= 0) {
                int e = @P@execute_transition(m, c, stack, t);
                if (e < 0) {
                    return @MM@_K_O_ERR;
                }
                @P@note_steps(run);
                if (e == 1) {
                    return @MM@_K_O_ENDED;
                }
                continue;
            }
            if (@P@run_leaf_during(m, c, s) != 0) {
                return @MM@_K_O_ERR;
            }
            st.frames[index].mode = @MM@_K_AFTER_ENTRY;
            @P@note_steps(run);
            continue;
        }
        if (top->mode == @MM@_K_POST_CHILD_EXIT) {
            int e;
            t = @P@select_valid(m, c, stack, 0);
            if (t == @MM@_K_SEL_ERR) {
                return @MM@_K_O_ERR;
            }
            if (t == @MM@_K_SEL_LOOP) {
                return @MM@_K_O_LOOP;
            }
            if (t == @MM@_K_SEL_NONE) {
                @P@fail(m, @MM@_K_E_OTHER, "No continuation exists for a composite state whose child exited.");
                return @MM@_K_O_ERR;
            }
            e = @P@execute_transition(m, c, stack, t);
            if (e < 0) {
                return @MM@_K_O_ERR;
            }
            @P@note_steps(run);
            if (e == 1) {
                return @MM@_K_O_ENDED;
            }
            continue;
        }
        r = @P@attempt_init(m, c, stack);
        @P@note_steps(run);
        if (r != @MM@_K_O_CONTINUE) {
            return r;
        }
    }
}

/* _run_cycle_on_context, with _initialize_context on a cold start. */
static int @P@one_pass(@T@Priv *m, int hooks)
{
    @T@Run run;
    int r;
    m->arena_top = 0;
    m->work_size = 0;
    m->trail_size = 0;
    m->init_depth = 0;
    m->outer = NULL;
    m->speculation = 0;
    m->hooks_live = hooks;
    memset(m->ctx.before_done, 0, sizeof(m->ctx.before_done));
    memset(m->ctx.after_pending, 0, sizeof(m->ctx.after_pending));
    if (!m->started) {
        m->ctx.main.size = 0;
        if (@P@enter_state(m, &m->ctx, -1, @ROOT_ID@) != 0) {
            return @MM@_K_O_ERR;
        }
    }
    run.base = 0;
    run.steps = 0;
    r = @P@advance_stack(m, &m->ctx, -1, &run);
    m->arena_top = 0;
    if (r == @MM@_K_O_STABLE) {
        if (@P@flush_after(m, &m->ctx, -1) != 0) {
            return @MM@_K_O_ERR;
        }
        return @MM@_K_O_STABLE;
    }
    if (r == @MM@_K_O_ENDED) {
        m->ctx.ended = 1;
        m->ctx.main.size = 0;
        return @MM@_K_O_ENDED;
    }
    return r;
}

/*
 * One cycle: a silent pass decides the whole cycle; if the model has abstract
 * actions and the cycle is accepted, the cycle runs again from the same start
 * with the hooks live. Returns 1 for success (a Delta cycle is a success that
 * keeps the position), 0 for failure with the error recorded.
 */
static int @P@run_cycle(@T@Priv *m)
{
    int r;
    m->snapshot = m->ctx;
    m->delta = 0;
    r = @P@one_pass(m, 0);
    if (r == @MM@_K_O_ERR || r == @MM@_K_O_LOOP || r == @MM@_K_O_FAILED) {
        m->ctx = m->snapshot;
        if (r == @MM@_K_O_ERR) {
            return 0;
        }
        if (r == @MM@_K_O_LOOP) {
            @P@fail(
                m,
                @MM@_K_E_LOOP,
                "Cannot reach a stoppable state in the same cycle; suspected loop. "
                "Add an exit to a stoppable leaf, a terminating guard, or separate the events driving exit and re-entry.");
            return 0;
        }
        m->delta = 1;
        return 1;
    }
#if @HAS_HOOKS@
    m->ctx = m->snapshot;
    r = @P@one_pass(m, 1);
    m->hooks_live = 0;
    if (r != @MM@_K_O_STABLE && r != @MM@_K_O_ENDED) {
        m->ctx = m->snapshot;
        @P@fail(m, @MM@_K_E_OTHER, "The executing pass of a cycle diverged from the deciding pass.");
        return 0;
    }
#endif
    m->started = 1;
    return 1;
}
'''
