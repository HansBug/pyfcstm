"""
Instantiate the lowered relation of one step for the other steps of a trace.

Every step after the first one starts from the same sources, so lowering it
again produces the relation of the previous step over the symbols of other
frames.  This module keeps the lowered objects of one such step as a template
and produces the objects of any other step by renaming those symbols, which is
one solver-side substitution instead of a second pass through the lowering code.

Z3 shares structurally equal terms, so an instantiated term is the very term
the lowering code would have built; nothing downstream can tell the two apart.

The module contains:

* :class:`StepTemplate` - Lowered objects of one step, ready to be renamed.
* :class:`StepTemplateUnsupported` - Raised when objects cannot be a template.
* :func:`register_rebuilt` - Declare a dataclass whose instances hold terms.
* :func:`register_shared` - Declare a dataclass whose instances hold no terms.
* :func:`step_instantiation_mode` - Read how instantiation is configured.
* :func:`must_check_step` - Tell which instantiated steps are always checked.
* :func:`first_difference` - Compare two lowered object graphs term by term.

.. note::
   A template is only taken from objects whose every free symbol is known to
   belong to the step, or to be shared by all steps.  Anything else raises
   :class:`StepTemplateUnsupported`, and the caller lowers each step as before.

Example::

    >>> import z3
    >>> from pyfcstm.bmc.step_template import StepTemplate
    >>> x1, x2, x5, x6 = z3.Ints("x1 x2 x5 x6")
    >>> template = StepTemplate({"next": x2 == x1 + 1, "step": 1}, 1, (x1, x2), ())
    >>> template.instantiate(5, (x5, x6))["next"]
    x6 == x5 + 1
"""

import dataclasses
import os
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

import z3
from z3 import z3core

__all__ = [
    "StepTemplate",
    "StepTemplateUnsupported",
    "register_rebuilt",
    "register_shared",
    "step_instantiation_mode",
    "must_check_step",
    "first_difference",
]

#: Environment variable selecting how later steps are produced: ``on`` (the
#: default) instantiates them from a template and checks the first and the last
#: instantiated step against a direct lowering, ``off`` lowers every step, and
#: ``verify`` instantiates and lowers every step and requires the results to be
#: the same terms.  It is an internal switch for the repository's own checks,
#: not a documented option.
MODE_VARIABLE = "PYFCSTM_BMC_STEP_INSTANTIATION"

_BUNDLE_NAME = "pyfcstm!step_bundle"

# Dataclasses that are rebuilt for another step, with the names of the fields
# that hold the index of the step.
_REBUILT: Dict[type, Tuple[str, ...]] = {}
# Dataclasses whose instances hold neither terms nor a step index; they are
# shared by every step.
_SHARED: Set[type] = set()

_CONST = 0
_LEAF = 1
_STEP = 2
_TUPLE = 3
_LIST = 4
_DICT = 5
_DATA = 6

_ATOMS = (str, int, float, bool, bytes, type(None))


class StepTemplateUnsupported(Exception):
    """Raised when lowered objects cannot serve as a template.

    :param reason: What the template builder met that it does not cover.
    :type reason: str

    Example::

        >>> StepTemplateUnsupported("free symbol x").reason
        'free symbol x'
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def _declare_fields(cls: type, fields: Sequence[str]) -> None:
    """Require that a registration names exactly the fields of the dataclass.

    A field added to a registered dataclass later would otherwise be rebuilt
    or shared by whatever rule happens to fit its first value, so the module
    refuses to import until the registration has been revisited.

    :param cls: Dataclass being registered.
    :type cls: type
    :param fields: Every field name the registration was written for.
    :type fields: Sequence[str]
    :raises TypeError: If ``cls`` is not a dataclass.
    :raises ValueError: If ``fields`` is not exactly the set of its fields.
    """
    if not dataclasses.is_dataclass(cls):
        raise TypeError("%r is not a dataclass." % (cls,))
    actual = {item.name for item in dataclasses.fields(cls)}
    if set(fields) != actual:
        raise ValueError(
            "%s registers %s but has the fields %s."
            % (cls.__name__, sorted(set(fields)), sorted(actual))
        )


def register_rebuilt(
    cls: type, fields: Sequence[str], step_fields: Sequence[str] = ()
) -> None:
    """Declare a dataclass whose instances are rebuilt for another step.

    :param cls: Dataclass that can hold solver terms.
    :type cls: type
    :param fields: Every field of ``cls``; the declaration is refused when it
        differs from the fields the dataclass has.
    :type fields: Sequence[str]
    :param step_fields: Names of the fields holding the index of the step,
        defaults to ``()``.
    :type step_fields: Sequence[str], optional
    :return: ``None``.
    :rtype: None
    :raises TypeError: If ``cls`` is not a dataclass.
    :raises ValueError: If ``fields`` is not exactly the set of its fields, or
        ``step_fields`` names a field it does not have.

    Example::

        >>> import dataclasses
        >>> @dataclasses.dataclass(frozen=True)
        ... class Pair:
        ...     step: int
        ...     term: object
        >>> register_rebuilt(Pair, ("step", "term"), ("step",))
    """
    _declare_fields(cls, fields)
    if not set(step_fields) <= set(fields):
        raise ValueError("%s: step_fields must be fields." % cls.__name__)
    _REBUILT[cls] = tuple(step_fields)


def register_shared(cls: type, fields: Sequence[str]) -> None:
    """Declare a dataclass whose instances every step shares by reference.

    :param cls: Dataclass holding neither solver terms nor a step index.
    :type cls: type
    :param fields: Every field of ``cls``; the declaration is refused when it
        differs from the fields the dataclass has.
    :type fields: Sequence[str]
    :return: ``None``.
    :rtype: None
    :raises TypeError: If ``cls`` is not a dataclass.
    :raises ValueError: If ``fields`` is not exactly the set of its fields.

    Example::

        >>> import dataclasses
        >>> @dataclasses.dataclass(frozen=True)
        ... class Label:
        ...     text: str
        >>> register_shared(Label, ("text",))
    """
    _declare_fields(cls, fields)
    _SHARED.add(cls)


def step_instantiation_mode() -> str:
    """Return how the steps after the first recurrence step are produced.

    :return: ``"on"``, ``"off"`` or ``"verify"``; an unknown setting reads as
        ``"on"``.
    :rtype: str

    Example::

        >>> step_instantiation_mode() in ("on", "off", "verify")
        True
    """
    value = os.environ.get(MODE_VARIABLE, "on").strip().lower()
    if value in ("0", "off", "false", "no"):
        return "off"
    if value == "verify":
        return "verify"
    return "on"


def must_check_step(mode: str, step_index: int, first: int, last: int) -> bool:
    """Tell whether an instantiated step is compared with a direct lowering.

    Every step is in ``verify`` mode.  Otherwise the first and the last
    instantiated step are: a template is taken from one step and renamed for
    the rest, so a step that differs from it shows up at the start of the
    repetition, and a last step is the likeliest place for a special case.

    :param mode: Value of :func:`step_instantiation_mode`.
    :type mode: str
    :param step_index: Index of the instantiated step.
    :type step_index: int
    :param first: Index of the first instantiated step.
    :type first: int
    :param last: Index of the last step of the trace.
    :type last: int
    :return: Whether to lower the step directly and compare.
    :rtype: bool

    Example::

        >>> [must_check_step("on", index, 2, 5) for index in range(2, 6)]
        [True, False, False, True]
        >>> must_check_step("verify", 3, 2, 5)
        True
    """
    return mode == "verify" or step_index == first or step_index == last


def _compile(
    obj: Any,
    step: int,
    leaves: List[z3.ExprRef],
    leaf_index: Dict[int, int],
    memo: Dict[int, tuple],
) -> tuple:
    """Turn an object graph into a plan that rebuilds it for another step."""
    if isinstance(obj, z3.ExprRef):
        index = leaf_index.get(id(obj))
        if index is None:
            index = len(leaves)
            leaves.append(obj)
            leaf_index[id(obj)] = index
        return (_LEAF, index)
    kind = type(obj)
    if kind in _ATOMS or kind in _SHARED:
        return (_CONST, obj)
    key = id(obj)
    if key in memo:
        return memo[key]
    if kind is tuple or kind is list:
        parts = [_compile(item, step, leaves, leaf_index, memo) for item in obj]
        if all(part[0] == _CONST for part in parts):
            node = (_CONST, obj)
        else:
            node = (_TUPLE if kind is tuple else _LIST, parts)
    elif kind is dict:
        for name in obj:
            if type(name) not in _ATOMS:
                raise StepTemplateUnsupported(
                    "mapping key of type %s" % type(name).__name__
                )
        parts = [
            _compile(item, step, leaves, leaf_index, memo) for item in obj.values()
        ]
        if all(part[0] == _CONST for part in parts):
            node = (_CONST, obj)
        else:
            node = (_DICT, tuple(obj), parts)
    elif kind in _REBUILT:
        step_fields = _REBUILT[kind]
        names = []
        parts = []
        for item in dataclasses.fields(kind):
            if not item.init:
                raise StepTemplateUnsupported(
                    "field %s.%s is not a constructor argument"
                    % (kind.__name__, item.name)
                )
            value = getattr(obj, item.name)
            names.append(item.name)
            if item.name in step_fields:
                if value != step or type(value) is not int:
                    raise StepTemplateUnsupported(
                        "%s.%s is %r in the template of step %d"
                        % (kind.__name__, item.name, value, step)
                    )
                parts.append((_STEP,))
            else:
                parts.append(_compile(value, step, leaves, leaf_index, memo))
        if all(part[0] == _CONST for part in parts):
            node = (_CONST, obj)
        else:
            node = (_DATA, kind, tuple(names), parts)
    else:
        raise StepTemplateUnsupported("object of type %s" % kind.__name__)
    memo[key] = node
    return node


def _build(
    node: tuple, leaves: List[z3.ExprRef], step: int, memo: Dict[int, Any]
) -> Any:
    """Rebuild the object a plan node stands for, over the terms of a step."""
    tag = node[0]
    if tag == _CONST:
        return node[1]
    if tag == _LEAF:
        return leaves[node[1]]
    if tag == _STEP:
        return step
    key = id(node)
    if key in memo:
        return memo[key]
    if tag == _TUPLE:
        value = tuple([_build(part, leaves, step, memo) for part in node[1]])
    elif tag == _DICT:
        value = {
            name: _build(part, leaves, step, memo)
            for name, part in zip(node[1], node[2])
        }
    elif tag == _DATA:
        value = node[1](
            **{
                name: _build(part, leaves, step, memo)
                for name, part in zip(node[2], node[3])
            }
        )
    else:
        value = [_build(part, leaves, step, memo) for part in node[1]]
    memo[key] = value
    return value


_get_ast_id = z3core.Z3_get_ast_id
_get_ast_kind = z3core.Z3_get_ast_kind
_get_app_num_args = z3core.Z3_get_app_num_args
_get_app_arg = z3core.Z3_get_app_arg


def _foreign_symbol(ctx: z3.Context, root: Any, known: Set[int]) -> Optional[str]:
    """Return a free symbol of ``root`` that is not in ``known``, if there is one.

    Anything that is neither an application nor a numeral is reported as well:
    the terms a step lowers to hold neither bound variables nor quantifiers, so
    meeting one means the template does not understand what it was given.
    """
    ref = ctx.ref()
    get_id = _get_ast_id
    get_kind = _get_ast_kind
    count_args = _get_app_num_args
    get_arg = _get_app_arg
    seen: Set[int] = set()
    pending = [root]
    while pending:
        term = pending.pop()
        ident = get_id(ref, term)
        if ident in seen:
            continue
        seen.add(ident)
        kind = get_kind(ref, term)
        if kind == z3.Z3_NUMERAL_AST:
            continue
        if kind != z3.Z3_APP_AST:
            return "a term that is not an application"
        count = count_args(ref, term)
        if count:
            for index in range(count):
                pending.append(get_arg(ref, term, index))
            continue
        if ident in known:
            continue
        decl = z3.Z3_get_app_decl(ref, term)
        if z3.Z3_get_decl_kind(ref, decl) == z3.Z3_OP_UNINTERPRETED:
            return z3.Z3_ast_to_string(ref, term)
    return None


class StepTemplate:
    """Lowered objects of one step that can be renamed into another step.

    ``payload`` may be any nesting of tuples, lists and dicts over solver
    terms, plain values, registered dataclasses and registered shared objects.
    Building the template checks that every free symbol of every term is one
    of ``symbols`` or ``invariants``.

    :param payload: Lowered objects of the template step.
    :type payload: object
    :param step_index: Index of the step ``payload`` was lowered for.
    :type step_index: int
    :param symbols: Every symbol that belongs to the template step.
    :type symbols: Sequence[z3.ExprRef]
    :param invariants: Symbols every step shares, such as parameters.
    :type invariants: Iterable[z3.ExprRef]
    :raises StepTemplateUnsupported: If the payload holds an object of an
        unregistered class, or a term mentions a symbol that is neither a
        symbol of the step nor an invariant.

    Example::

        >>> import z3
        >>> a1, a7, p = z3.Ints("a1 a7 p")
        >>> template = StepTemplate((a1 > p, "kept"), 1, (a1,), (p,))
        >>> template.instantiate(7, (a7,))
        (a7 > p, 'kept')
        >>> StepTemplate((a1 > p,), 1, (a1,), ())
        Traceback (most recent call last):
          ...
        pyfcstm.bmc.step_template.StepTemplateUnsupported: symbol p belongs to no step
    """

    def __init__(
        self,
        payload: Any,
        step_index: int,
        symbols: Sequence[z3.ExprRef],
        invariants: Iterable[z3.ExprRef],
    ) -> None:
        self.step_index = step_index
        self._leaves: List[z3.ExprRef] = []
        self._plan = _compile(payload, step_index, self._leaves, {}, {})
        self._symbols = tuple(symbols)
        self._bundle = None
        self._ctx = None
        if not self._leaves:
            return
        ctx = self._leaves[0].ctx
        ref = ctx.ref()
        self._ctx = ctx
        count = len(self._leaves)
        bool_sort = z3.BoolSort(ctx)
        sorts = [
            bool_sort if isinstance(leaf, z3.BoolRef) else leaf.sort()
            for leaf in self._leaves
        ]
        # One application over every term: renaming it renames them all in a
        # single pass that visits each shared subterm once.
        self._decl = z3.FuncDeclRef(
            z3.Z3_mk_func_decl(
                ref,
                z3.to_symbol(_BUNDLE_NAME, ctx),
                count,
                (z3.Sort * count)(*[item.ast for item in sorts]),
                bool_sort.ast,
            ),
            ctx,
        )
        self._bundle = z3.ExprRef(
            z3.Z3_mk_app(
                ref,
                self._decl.ast,
                count,
                (z3.Ast * count)(*[leaf.as_ast() for leaf in self._leaves]),
            ),
            ctx,
        )
        self._classes = [type(leaf) for leaf in self._leaves]
        self._sources = (z3.Ast * len(self._symbols))(
            *[item.as_ast() for item in self._symbols]
        )
        known = {item.get_id() for item in self._symbols}
        known.update(item.get_id() for item in invariants)
        foreign = _foreign_symbol(ctx, self._bundle.as_ast(), known)
        if foreign is not None:
            raise StepTemplateUnsupported("symbol %s belongs to no step" % foreign)

    def instantiate(self, step_index: int, symbols: Sequence[z3.ExprRef]) -> Any:
        """Return the payload as it reads in another step.

        :param step_index: Index of the step to produce.
        :type step_index: int
        :param symbols: The symbols of that step, in the order the template
            was given the symbols of its own step.
        :type symbols: Sequence[z3.ExprRef]
        :return: Objects equal to what lowering that step would have built.
        :rtype: object
        :raises ValueError: If ``symbols`` does not match the template.

        Example::

            >>> import z3
            >>> a1, a4 = z3.Ints("a1 a4")
            >>> StepTemplate([a1 + 1], 1, (a1,), ()).instantiate(4, (a4,))
            [a4 + 1]
        """
        if len(symbols) != len(self._symbols):
            raise ValueError(
                "a step has %d symbols, got %d." % (len(self._symbols), len(symbols))
            )
        leaves: List[z3.ExprRef] = []
        if self._bundle is not None:
            ctx = self._ctx
            ref = ctx.ref()
            count = len(symbols)
            renamed = z3.ExprRef(
                z3.Z3_substitute(
                    ref,
                    self._bundle.as_ast(),
                    count,
                    self._sources,
                    (z3.Ast * count)(*[item.as_ast() for item in symbols]),
                ),
                ctx,
            )
            term = renamed.as_ast()
            get_arg = _get_app_arg
            # Renaming a symbol into a symbol of its sort keeps the sort and the
            # shape of every term, so each term keeps the class it had.
            leaves = [
                cls(get_arg(ref, term, index), ctx)
                for index, cls in enumerate(self._classes)
            ]
        return _build(self._plan, leaves, step_index, {})


def first_difference(left: Any, right: Any, where: str = "") -> Optional[str]:
    """Return where two lowered object graphs differ, or ``None`` if nowhere.

    Solver terms are the same only when they are the same term of the same
    wrapper class; everything else is compared by type and value.

    :param left: One object graph.
    :type left: object
    :param right: The other object graph.
    :type right: object
    :param where: Path of the objects inside what is compared, defaults to
        ``""``.
    :type where: str, optional
    :return: Path and description of the first difference found.
    :rtype: Optional[str]

    Example::

        >>> import z3
        >>> x = z3.Int("x")
        >>> first_difference((x + 1, "a"), (x + 1, "a")) is None
        True
        >>> first_difference((x + 1,), (x + 2,))
        '[0]: terms differ: x + 1 / x + 2'
    """
    if type(left) is not type(right):
        return "%s: %s / %s" % (where, type(left).__name__, type(right).__name__)
    if isinstance(left, z3.ExprRef):
        if left.eq(right):
            return None
        return "%s: terms differ: %s / %s" % (
            where,
            str(left)[:200],
            str(right)[:200],
        )
    if isinstance(left, (tuple, list)):
        if len(left) != len(right):
            return "%s: lengths %d / %d" % (where, len(left), len(right))
        for index, (one, other) in enumerate(zip(left, right)):
            found = first_difference(one, other, "%s[%d]" % (where, index))
            if found is not None:
                return found
        return None
    if isinstance(left, dict):
        if list(left) != list(right):
            return "%s: keys %r / %r" % (where, list(left)[:8], list(right)[:8])
        for name in left:
            found = first_difference(left[name], right[name], "%s[%r]" % (where, name))
            if found is not None:
                return found
        return None
    if type(left) in _REBUILT:
        for item in dataclasses.fields(left):
            found = first_difference(
                getattr(left, item.name),
                getattr(right, item.name),
                "%s.%s" % (where, item.name),
            )
            if found is not None:
                return found
        return None
    if left is right or left == right:
        return None
    return "%s: %r / %r" % (where, left, right)
