"""Source metadata and tracked-constraint primitives for BMC explanations.

This module owns source-document snapshots, source references, exact source
excerpts, and the generic tracked-group container used by the relation layer.
It deliberately does not import Z3, model construction, witness solving, or
CLI presentation.  Keeping these values independent from solver objects makes
it possible for preparation and parser code to preserve provenance without
loading the solver stack.

The word ``source`` here means a FCSTM/FBMCQ/generated document location.  It
is distinct from :class:`pyfcstm.bmc.source.MacroStepSource`, which describes
the runtime origin profile of a macro-step.

The model integration contract is intentionally private and metadata-only:
``pyfcstm.model`` loaders may attach ``_source_documents`` as a mapping from
absolute source paths to immutable text snapshots, ``_source_root`` as the
display root, and ``_source_path`` to source-bearing model objects.  The BMC
registry reads these names without changing model equality, canonical output,
or programmatic-model behavior.  Changes to those private names or their
types must update this module and the model loader together; missing metadata
is reported as an unavailable path or excerpt rather than guessed.

Example::

    >>> from pyfcstm.bmc.provenance import BmcSourceRef, SourceDocumentRegistry
    >>> from pyfcstm.utils.validate import Span
    >>> registry = SourceDocumentRegistry({"machine.fcstm": "state Root;"})
    >>> ref = BmcSourceRef("fcstm", "machine.fcstm", Span(1, 1, 1, 12))
    >>> registry.excerpt(ref)
    'state Root;'
"""

from __future__ import annotations

import hashlib
import math
import os
import sys
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, List, Mapping, Optional, Tuple

from pyfcstm.utils.validate import Span

_SOURCE_KINDS = {"fcstm", "fbmcq", "generated"}


def _normalize_line_separators(text: str) -> str:
    """Align a source snapshot with the line model used by the DSL lexers.

    The FCSTM and FBMCQ ANTLR lexers advance token line numbers on ``LF`` only:
    they treat a ``CRLF`` pair as one line break but consume a lone ``CR`` as
    ordinary whitespace inside the current line.  A snapshot therefore only
    rewrites ``CRLF`` to ``LF``, which drops a trailing character that no token
    column depends on.  Rewriting a lone ``CR`` to ``LF`` as well would insert
    line breaks the lexers never saw, so every span after the first ``CR``
    would fall outside its recomputed line and lose its excerpt.

    The rewrite is a single left-to-right pass, so a ``CR`` immediately before a
    ``CRLF`` leaves a residual ``CR`` at the end of a line: ``"a\\r\\r\\nb"``
    becomes ``"a\\r\\nb"``.  Keeping that residual out of a same-line excerpt is
    :func:`_span_offsets`' job, which trims one trailing ``CR`` after the ``LF``.

    :param text: Raw source text as read from disk or supplied by a caller.
    :type text: str
    :return: Text whose line breaks match the lexer's own line numbering.
    :rtype: str

    Example::

        >>> _normalize_line_separators("a\\r\\nb")
        'a\\nb'
        >>> _normalize_line_separators("a\\rb")
        'a\\rb'
    """
    # This text is what every published excerpt is sliced from, so the exact
    # characters are read before any rewriting.
    return exact_str(text, "source document text").replace("\r\n", "\n")


def _span_offsets(text: str, span: Span) -> Optional[Tuple[int, int]]:
    """Return character offsets for a complete one-based half-open span.

    ``text`` must already be normalized by :func:`_normalize_line_separators`,
    so that the line numbering here is the same one the lexer used when it
    produced ``span``.  Line ends are located by scanning ``LF`` and then
    trimming a trailing ``CR``, which keeps a residual ``CR`` out of a
    same-line excerpt without inventing a line break for it.

    :param text: Source document text with lexer-aligned line separators.
    :type text: str
    :param span: One-based source span with optional end coordinates.
    :type span: pyfcstm.utils.validate.Span
    :return: Start and end character offsets, or ``None`` for an anchor-only
        span, or when the span cannot be sliced from ``text``.
    :rtype: Optional[Tuple[int, int]]

    Example::

        >>> _span_offsets("abc", Span(1, 1, 1, 3))
        (0, 2)
    """
    if span.end_line is None or span.end_column is None:
        return None
    starts = [0]
    for index, char in enumerate(text):
        if char == "\n":
            starts.append(index + 1)
    if not (1 <= span.line <= len(starts)):
        return None
    if not (1 <= span.end_line <= len(starts)):
        return None
    line_ends = []
    for index, line_start in enumerate(starts):
        line_end = starts[index + 1] if index + 1 < len(starts) else len(text)
        if line_end > line_start and text[line_end - 1] == "\n":
            line_end -= 1
            if line_end > line_start and text[line_end - 1] == "\r":
                line_end -= 1
        line_ends.append(line_end)
    if not (1 <= span.column <= line_ends[span.line - 1] - starts[span.line - 1] + 1):
        return None
    if not (
        1
        <= span.end_column
        <= line_ends[span.end_line - 1] - starts[span.end_line - 1] + 1
    ):
        return None
    start = starts[span.line - 1] + span.column - 1
    end = starts[span.end_line - 1] + span.end_column - 1
    if start < 0 or end < start or end > len(text):
        return None
    return start, end


def exact_str(value: Any, where: str) -> str:
    """Return the plain ``str`` a value actually is.

    Published text becomes a JSON value and a solver literal name downstream, so
    it is stored as an exact ``str`` rather than as whatever was passed in.
    Reading the characters through the base type's own method keeps the stored
    text independent of anything a subclass overrides.

    :param value: Candidate string.
    :type value: object
    :param where: Field or path name used in the error message.
    :type where: str
    :return: The same text as an exact ``str``.
    :rtype: str
    :raises TypeError: If the value is not a ``str``.

    Example::

        >>> exact_str("kernel", "stage")
        'kernel'
        >>> exact_str(123, "stage")
        Traceback (most recent call last):
          ...
        TypeError: stage must be a string, got 123.
    """
    try:
        return str.__str__(value)
    except TypeError as err:
        # str.__str__ is a descriptor bound to str, so it refuses anything whose
        # real type is not str.
        raise TypeError("%s must be a string, got %r." % (where, value)) from err


def exact_int(value: Any, where: str) -> int:
    """Return the plain ``int`` a value actually is.

    :param value: Candidate integer.
    :type value: object
    :param where: Field or path name used in the error message.
    :type where: str
    :return: The same number as an exact ``int``.
    :rtype: int
    :raises TypeError: If the value is not really an ``int``.
    :raises ValueError: If the number needs more decimal digits than
        the smaller of :data:`MAX_METADATA_INT_DIGITS` and this interpreter's
        own limit, since past that point ``json.dumps`` cannot render it.

    Example::

        >>> import enum
        >>> class Frame(enum.IntEnum):
        ...     SECOND = 1
        >>> exact_int(Frame.SECOND, "frames")
        1
    """
    try:
        plain = int.__int__(value)
    except TypeError as err:
        # Same reasoning as exact_str: the descriptor refuses a non-int.
        raise TypeError("%s must be an integer, got %r." % (where, value)) from err
    limit = _effective_int_digit_limit()
    if not -(10**limit) < plain < 10**limit:
        raise ValueError(
            "%s exceeds the %d decimal digits this interpreter can render."
            % (where, limit)
        )
    return plain


def exact_float(value: Any, where: str) -> float:
    """Return the plain ``float`` a value actually is.

    :param value: Candidate number.
    :type value: object
    :param where: Field or path name used in the error message.
    :type where: str
    :return: The same number as an exact ``float``.
    :rtype: float
    :raises TypeError: If the value is not really a ``float``.

    Example::

        >>> exact_float(1.5, "threshold")
        1.5
    """
    try:
        return float.__float__(value)
    except TypeError as err:
        # Same reasoning as exact_str.
        raise TypeError("%s must be a number, got %r." % (where, value)) from err


def exact_index(value: Any, where: str) -> int:
    """Return a source coordinate as an exact ``int``.

    :param value: Candidate coordinate.
    :type value: object
    :param where: Field name used in the error message.
    :type where: str
    :return: The coordinate as an exact ``int``.
    :rtype: int
    :raises TypeError: If the value is not really an ``int``.

    Example::

        >>> exact_index(1, "line")
        1
    """
    # The value is typed, not bounded.  A span that cannot be sliced degrades to
    # an absent excerpt by an existing contract, so an out-of-range coordinate is
    # already handled downstream; the published schema only requires an integer.
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("%s must be an integer, got %r." % (where, value))
    return exact_int(value, where)


def exact_optional_index(value: Any, where: str) -> Optional[int]:
    """Return an optional source coordinate, or ``None``.

    :param value: Candidate coordinate, or ``None``.
    :type value: object
    :param where: Field name used in the error message.
    :type where: str
    :return: The coordinate as an exact ``int``, or ``None``.
    :rtype: Optional[int]
    :raises TypeError: If the value is neither ``None`` nor an ``int``.

    Example::

        >>> exact_optional_index(None, "end_line") is None
        True
    """
    if value is None:
        return None
    return exact_index(value, where)


#: How many decimal digits a published integer may have.
#:
#: This is the *floor*, not the whole rule.  CPython refuses to render an integer
#: longer than its own configured limit into text, and a longer one would pass
#: every type check here only to fail inside ``json.dumps`` with an error naming
#: neither the field nor the object.  The effective bound is therefore the
#: smaller of this value and the live interpreter setting -- see
#: :func:`_effective_int_digit_limit`.  Stating a floor keeps the same payload
#: accepted on every supported version, including those with no limit at all,
#: while following the live setting keeps the promise that whatever is accepted
#: here can actually be encoded in this process.
MAX_METADATA_INT_DIGITS = 4300


def _effective_int_digit_limit() -> int:
    """Return how many decimal digits this interpreter will actually render.

    The published bound is a floor, not the whole answer.  A deployment may
    lower the interpreter's own limit (``PYTHONINTMAXSTRDIGITS``, minimum 640)
    for safety, and then a value this module accepted still dies inside
    ``json.dumps``.  Reading the live setting keeps the promise the boundary
    actually makes: whatever is accepted here can be encoded in this process.

    Before Python 3.11 there is no limit at all, so the published bound stands
    on its own and the same payload is accepted everywhere.

    :return: The digit budget to enforce.
    :rtype: int

    Example::

        >>> _effective_int_digit_limit() >= 640
        True
    """
    live = getattr(sys, "get_int_max_str_digits", None)
    if live is None:
        # No interpreter limit exists before 3.11.
        return MAX_METADATA_INT_DIGITS
    configured = live()
    if configured == 0:
        # Zero disables the interpreter limit entirely.
        return MAX_METADATA_INT_DIGITS
    return min(MAX_METADATA_INT_DIGITS, configured)


#: How deeply published metadata may nest.
#:
#: The recursive walk that validates and rebuilds this metadata is bounded by
#: the interpreter's own stack, and so is the JSON encoder that later serializes
#: it.  Left implicit, a legal but very deep mapping passes validation and then
#: fails during serialization with a bare ``RecursionError`` naming neither the
#: field nor the object -- exactly the failure this boundary exists to prevent.
#: The limit is far above any shape the relation builder produces, whose
#: metadata is one level of scalars.
MAX_METADATA_DEPTH = 64


def _require_json_mapping(value: Any, label: str) -> Dict[str, Any]:
    """Reject metadata that could not survive a round trip through JSON.

    These mappings are free-form by design, which is exactly why they need a
    boundary: an unserializable value placed here would not fail until the
    whole result is dumped, and the error would name neither the field nor the
    object it came from.

    :param value: Candidate mapping.
    :type value: object
    :param label: Field name used in the error message.
    :type label: str
    :return: The validated mapping as a plain dict.
    :rtype: Dict[str, object]
    :raises TypeError: If a key is not a string, or a value is outside the
        JSON data model.
    :raises ValueError: If a float is not finite, or the mapping nests deeper
        than :data:`MAX_METADATA_DEPTH`.

    Example::

        >>> _require_json_mapping({"frame": 0}, "refs")
        {'frame': 0}
    """

    def _normalize(entry: Any, where: str, depth: int) -> Any:
        """Return one value in its canonical, detached, immutable form.

        The walk both validates and rebuilds.  Checking alone is not enough: a
        nested mapping the caller still holds a reference to can be written to
        after this frozen object is built, so the value that finally reaches
        JSON is not the one that was validated.  A nested mapping that is not a
        ``dict`` has the same problem in reverse -- it passes a ``Mapping``
        check and then fails to serialize.

        Sequences become tuples and mappings become read-only views, so nothing
        published here can be reached through the caller's own reference.

        The two container tests are deliberately at different levels: mappings
        are matched on the ``Mapping`` protocol, sequences on ``list``/``tuple``
        specifically.  Widening the sequence test to ``Sequence`` would pull in
        ``str``, which is a sequence of one-character strings and would be taken
        apart rather than published.  The asymmetry is safe in the direction it
        leans -- ``json.dumps`` refuses ``UserList`` and ``UserDict`` alike, so
        refusing the former is the strict side -- but it is easy to mistake for
        an oversight and "fix".

        :param entry: Candidate value somewhere inside the mapping.
        :type entry: object
        :param where: Dotted path used in the error message.
        :type where: str
        :return: The canonical form of ``entry``.
        :rtype: object
        :raises TypeError: If a mapping key is not a string, or the value is of
            a type with no JSON counterpart.
        :raises ValueError: If a float is not finite.
        """
        if depth > MAX_METADATA_DEPTH:
            raise ValueError(
                "%s nests deeper than the published limit of %d levels."
                % (where, MAX_METADATA_DEPTH)
            )
        if entry is None:
            return entry
        # ``bool`` cannot be subclassed and both values are singletons, so
        # identity is the exact test.  It comes first because a bool is also an
        # int.
        if entry is True or entry is False:
            # ``bool`` cannot be subclassed and both values are singletons, so
            # identity is exact and no further bool check is needed.
            return entry
        if isinstance(entry, int):
            return exact_int(entry, where)
        if isinstance(entry, float):
            # NaN and Infinity are not JSON numbers.  json.dumps emits them by
            # default and refuses them under allow_nan=False, so either way the
            # payload stops being interchangeable.
            plain = exact_float(entry, where)
            if not math.isfinite(plain):
                raise ValueError("%s must be a finite number, got %r." % (where, entry))
            return plain
        if isinstance(entry, str):
            return exact_str(entry, where)
        if isinstance(entry, (list, tuple)):
            # A list or tuple subclass may override __iter__, so the items are
            # read through the base type.  Iterating the instance would let the
            # value choose what gets published, which is the whole point of
            # rebuilding rather than merely checking.
            base = list if isinstance(entry, list) else tuple
            items = base.__iter__(entry)
            return tuple(
                _normalize(item, "%s[%d]" % (where, index), depth + 1)
                for index, item in enumerate(items)
            )
        if isinstance(entry, Mapping):
            normalized = {}
            # A dict subclass may override items(); anything else is a Mapping by
            # protocol only, and its items() is the sole way in.  Reading a real
            # dict through the base type keeps the two consistent where it can.
            pairs = dict.items(entry) if isinstance(entry, dict) else entry.items()
            for key, item in pairs:
                if not isinstance(key, str):
                    raise TypeError("%s keys must be strings, got %r." % (where, key))
                # The key is rebuilt too.  A str subclass can carry state that
                # changes its hash later, and then the published mapping breaks
                # when something merely looks a key up.
                plain_key = exact_str(key, "%s key" % where)
                if plain_key in normalized:  # pragma: no cover - see below.
                    # Unreachable today: exact_str reads characters and does not
                    # normalize, so two distinct plain keys never collide, and a
                    # mapping literal collapses equal ones before this sees them.
                    # Kept because it fails closed rather than silently dropping a
                    # recorded fact if a future reader ever does normalize text.
                    raise ValueError(
                        "%s has two keys that both canonicalize to %r."
                        % (where, plain_key)
                    )
                normalized[plain_key] = _normalize(
                    item, "%s[%r]" % (where, key), depth + 1
                )
            return MappingProxyType(normalized)
        raise TypeError("%s is not JSON-compatible, got %r." % (where, entry))

    if not isinstance(value, Mapping):
        # A sequence would be silently normalized into an empty mapping by
        # dict(), which loses the caller's data and disagrees with the JSON
        # contract that names this field an object.
        raise TypeError("%s must be a mapping, got %r." % (label, value))
    # The top level stays a plain dict because the caller wraps it; every level
    # below it is already detached and read-only.
    return {
        key: value_
        for key, value_ in dict(_normalize(value, label, 0)).items()  # type: ignore[arg-type]
    }


#: Category prefixes whose groups carry a single variable comparison.
#:
#: These are the groups whose expression is one relational atom over one frame
#: variable, which is what makes an ``equality`` or ``range`` fact readable
#: without walking an arbitrary formula.
#: Every category whose group can hold one comparison between a frame
#: variable and a value.  The relation builder produces this shape from three
#: places -- a frame assumption, a declared initializer and an ``init ... where``
#: predicate -- and leaving one out publishes the same mathematical conflict a
#: grade lower depending on where the author wrote it.
_VALUE_FACT_CATEGORIES = (
    "assumption.frame",
    "initial.variable",
    "initial.where",
)


def _relational_operators(z3: Any) -> Dict[int, str]:
    """Return the Z3 declaration kinds this module reduces to an operator.

    Built on demand rather than at import time: this module deliberately keeps
    ``z3`` out of the import graph so preparation and parser code can preserve
    provenance without loading the solver stack, and a published gate asserts
    that ``import pyfcstm.bmc`` does not pull it in.

    :param z3: The already-imported ``z3`` module.
    :type z3: module
    :return: Declaration kind to published operator.
    :rtype: Dict[int, str]

    Example::

        >>> import z3 as z3_module
        >>> _relational_operators(z3_module)[z3_module.Z3_OP_EQ]
        'eq'
    """
    return {
        z3.Z3_OP_EQ: "eq",
        z3.Z3_OP_DISTINCT: "ne",
        z3.Z3_OP_LE: "le",
        z3.Z3_OP_LT: "lt",
        z3.Z3_OP_GE: "ge",
        z3.Z3_OP_GT: "gt",
    }


def _without_coercion(expression: Any) -> Any:
    """Strip the sort coercion z3 inserts around a mixed-sort operand.

    Comparing a real variable with an integer literal -- or the reverse -- makes
    z3 wrap one side in ``to_real``.  The wrapper records nothing the author
    wrote, so a reader that stops at it would make the same query readable or not
    depending on whether a decimal point was typed.

    :param expression: The operand as it appears in the constraint.
    :type expression: object
    :return: The operand with any coercion removed.
    :rtype: object

    Example::

        >>> import z3
        >>> str(_without_coercion(z3.ToReal(z3.Int("x"))))
        'x'
        >>> str(_without_coercion(z3.Int("x")))
        'x'
    """
    import z3

    while (
        z3.is_app(expression)
        and expression.decl().kind() == z3.Z3_OP_TO_REAL
        and expression.num_args() == 1
    ):
        expression = expression.arg(0)
    return expression


def _frame_variable_name(
    expression: Any, declared: Optional[Any] = None
) -> Optional[str]:
    """Return the model variable a frame symbol stands for.

    The encoding builds a symbol as ``F_<frame>_<body>_<digest>``, where the body
    is the variable name with unsafe characters replaced and then **truncated**,
    and the digest is a hash of the whole name.  Reading the body back therefore
    recovers the truncation rather than the declaration, and publishing it names a
    variable the reader cannot find in their source.

    Passing ``declared`` -- the model's variable names -- resolves that: each name
    is hashed the same way the encoder hashes it and compared against the symbol,
    so the answer is the declared name or nothing.  Without it the reader falls
    back to the body, which is correct for every name short enough to survive
    truncation intact.

    :param expression: The candidate operand.
    :type expression: object
    :param declared: Model variable names to resolve against, defaults to
        ``None``.
    :type declared: Optional[Iterable[str]], optional
    :return: The declared variable name, or ``None`` when the operand is not a
        frame variable.
    :rtype: Optional[str]

    Example::

        >>> import z3
        >>> _frame_variable_name(z3.Int("F_0_x_11f6ad8ec5"))
        'x'
        >>> _frame_variable_name(z3.Int("F_0_state")) is None
        True
    """
    import z3

    expression = _without_coercion(expression)
    if not z3.is_const(expression):
        # Only a leaf symbol names a variable.  ``x + y`` renders as
        # ``F_0_x_... + F_0_y_...``, which begins like a frame symbol and ends
        # with the second operand's digest, so a reader working on the text alone
        # calls the sum ``y`` and the narrative then states an equality the query
        # never required.  The state-slot reader has always checked this; the
        # omission here was the asymmetry.
        return None
    text = str(expression)
    if not text.startswith("F_"):
        return None
    parts = text.split("_")
    if len(parts) < 4:
        # "F_0_state" and friends name a frame slot, not a model variable.
        return None
    if declared:
        digest = parts[-1]
        matches = [
            name
            for name in declared
            if hashlib.sha1(name.encode("utf-8")).hexdigest() == digest
        ]
        if len(matches) == 1:
            return matches[0]
        # No match means the symbol is not this model's variable; more than one
        # would mean the digest failed to distinguish them, and picking either
        # would name the wrong declaration.  Saying nothing beats a guess.
        return None
    return "_".join(parts[2:-1]) or None


def _numeric_value(expression: Any) -> Optional[Any]:
    """Read a z3 numeral as the plain Python number a consumer can use.

    An integer numeral becomes ``int`` and a rational one becomes ``float``,
    including when its value is whole.  That distinction is load-bearing: a real
    variable admits values between consecutive integers, so a reader of the
    published fact must be able to tell the two domains apart without a separate
    key, and downstream interval reasoning must not tighten a real bound the way
    it may tighten an integer one.

    :param expression: The candidate operand.
    :type expression: object
    :return: The numeral's value, or ``None`` when it is not a numeral.
    :rtype: Optional[Any]

    Example::

        >>> import z3
        >>> _numeric_value(z3.IntVal(7))
        7
        >>> _numeric_value(z3.RealVal("1/2"))
        0.5
        >>> _numeric_value(z3.Int("x")) is None
        True
    """
    import z3

    expression = _without_coercion(expression)
    if isinstance(expression, z3.IntNumRef):
        return expression.as_long()
    if isinstance(expression, z3.RatNumRef):
        # as_fraction keeps the exact value z3 holds; float() is the published
        # form.  A rational past the float range is a legal thing to write, and
        # converting it raises rather than losing precision, so the fact declines
        # instead -- an explanation that cannot represent a value degrades, it
        # does not take the mandatory verdict down with it.
        try:
            return float(expression.as_fraction())
        except OverflowError:
            # OverflowError: the exact rational does not fit a Python float.
            return None
    return None


# Each recognizer below opens with shape preconditions -- one expression, an
# integer frame, an Or of equalities -- that today's encoder always satisfies for
# the categories they are called on.  They are kept anyway, and deliberately left
# without tests: their job is to make a recognizer degrade to
# "structural_constraint" if the encoder's shape ever changes, and deleting them
# would turn that degradation into an AttributeError, which is the opposite of
# what a component whose contract is "read this shape or say you cannot" should
# do.  Reaching them from a test would mean hand-building a tracked group the
# builder cannot produce, which the repository's test boundary forbids.  The
# preconditions that authored queries *do* reach -- a comparison between two
# variables, an assertion about the active state -- are covered as normal paths.
def _value_comparison_fact(
    group: Any, declared: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """Read a one-variable comparison group as a variable-comparison fact.

    :param group: The tracked group to read.
    :type group: BmcTrackedConstraint
    :return: The fact mapping, or ``None`` when the shape is not a single
        comparison between one frame variable and one numeral.
    :rtype: Optional[Dict[str, Any]]
    """
    import z3

    if len(group.expressions) != 1:
        return None
    expression = group.expressions[0]
    if not z3.is_app(expression):
        return None
    operator = _relational_operators(z3).get(expression.decl().kind())
    if operator is None or expression.num_args() != 2:
        return None
    left, right = expression.arg(0), expression.arg(1)
    name = _frame_variable_name(left, declared)
    value = _numeric_value(right)
    if name is None or value is None:
        # Operand order is not fixed, so the mirrored shape is read too.
        name = _frame_variable_name(right, declared)
        value = _numeric_value(left)
        operator = {"lt": "gt", "gt": "lt", "le": "ge", "ge": "le"}.get(
            operator, operator
        )
    if name is None or value is None:
        return None
    frame = group.refs.get("frame")
    if not isinstance(frame, int):
        return None
    # The domain marker follows the *variable*, not the literal.  Unwrapping the
    # sort coercion means a real variable compared with ``1`` yields a Python
    # int, and downstream interval reasoning reads the published type to decide
    # whether it may tighten a strict bound by one -- which it must not do over
    # the reals.  Publishing whole real values as floats is what keeps the two
    # domains distinguishable without a separate key.
    slot = left if _frame_variable_name(left, None) == name else right
    if z3.is_int(_without_coercion(slot)):
        # An integer variable compared with ``3.0``: the literal is a real, but
        # the domain is not.  Narrowing is only sound when the value is whole --
        # a fractional bound on an integer variable is not an integer bound, and
        # rounding it would move it.
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        elif isinstance(value, float):
            return None
    else:
        try:
            value = float(value)
        except OverflowError:
            # OverflowError: an integer literal too large for a float, compared
            # against a real variable.  Same choice as above: decline the fact.
            return None
    # One tag with an operator field, not one tag per relation: a consumer that
    # wants only equalities filters on the operator, while one that wants any
    # bound on a variable does not have to enumerate tags to find them.
    return {
        "kind": "variable_comparison",
        "variable": name,
        "frame": frame,
        "operator": operator,
        "value": value,
    }


def _state_domain_fact(group: Any) -> Optional[Dict[str, Any]]:
    """Read a frame-state domain group as the set of states the frame may hold.

    :param group: The tracked group to read.
    :type group: BmcTrackedConstraint
    :return: The fact mapping, or ``None`` when the disjunction is not a plain
        list of state equalities.
    :rtype: Optional[Dict[str, Any]]
    """
    import z3

    frame = group.refs.get("frame")
    if not isinstance(frame, int) or len(group.expressions) != 1:
        return None
    expression = group.expressions[0]
    if not z3.is_app(expression) or expression.decl().kind() != z3.Z3_OP_OR:
        return None
    states = []
    for index in range(expression.num_args()):
        atom = expression.arg(index)
        if not z3.is_app(atom) or atom.decl().kind() != z3.Z3_OP_EQ:
            return None
        left, right = atom.arg(0), atom.arg(1)
        # Which side is this frame's state slot, read the way the membership
        # recognizer beside this one reads it.  The point is the agreement rather
        # than a defence: both answer "is the compared symbol the slot I am about",
        # and two recognizers giving that question different answers is a thing the
        # next reader has to stop and work out.
        #
        # There is no test because there is nothing to reach: the builder emits
        # single-frame disjunctions, so a cross-frame one has no source, and
        # constructing one would mean standing in for the group this reads.
        value = None
        for slot, code in ((left, right), (right, left)):
            if _frame_state_slot(slot, frame):
                value = _numeric_value(code)
                break
        if value is None:
            return None
        states.append(value)
    return {"kind": "state_domain", "frame": frame, "states": sorted(states)}


def _definedness_fact(
    group: Any, declared: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """Read a definedness group as the operation it keeps well defined.

    The operation is taken from the builder's own metadata, never inferred from
    the condition: a divisor check and a non-negativity check both compare one
    operand against zero, so the shape cannot distinguish ``x / 0`` from
    ``sqrt(-1.0)``.  A group whose builder recorded no operation returns ``None``
    so the caller degrades honestly instead of publishing a guess -- an earlier
    version named every definedness group a division, which reported
    ``sqrt(-1.0) >= 0.0`` as a division that must stay defined.

    :param group: The tracked group to read.
    :type group: BmcTrackedConstraint
    :return: The fact mapping, or ``None`` when the frame or the operation is
        unknown.
    :rtype: Optional[Dict[str, Any]]
    """
    import z3

    frame = group.refs.get("frame")
    operation = group.refs.get("operation")
    if not isinstance(frame, int) or not isinstance(operation, str):
        return None
    fact = {
        "kind": "definedness_condition",
        "frame": frame,
        "operation": operation,
    }
    if len(group.expressions) == 1:
        expression = group.expressions[0]
        if z3.is_app(expression) and expression.decl().kind() == z3.Z3_OP_DISTINCT:
            name = _frame_variable_name(
                expression.arg(0), declared
            ) or _frame_variable_name(expression.arg(1), declared)
            if name is not None:
                fact["variable"] = name
    return fact


def _state_membership_fact(group: Any) -> Optional[Dict[str, Any]]:
    """Read a group that pins one frame's state as a state-membership fact.

    Both an initial target and an ``active(...)`` assumption lower to a single
    equality between a state code and the frame's state slot, so one reader
    covers both.  The code is published as the plain integer the encoding uses --
    the model's own name for it is not carried on the group, and the item's source
    excerpt quotes the line that names it.

    :param group: The tracked group to read.
    :type group: BmcTrackedConstraint
    :return: The fact mapping, or ``None`` when the shape is not one state
        equality on a known frame.
    :rtype: Optional[Dict[str, Any]]
    """
    import z3

    frame = group.refs.get("frame")
    if not isinstance(frame, int) or len(group.expressions) != 1:
        return None
    expression = group.expressions[0]
    if not z3.is_app(expression):
        return None
    # "not active(S)" lowers to Not(code == slot), which excludes one state
    # rather than requiring it.  Both readings publish the same tag with an
    # ``excluded`` flag, so a consumer sees one shape for one concept.
    excluded = expression.decl().kind() == z3.Z3_OP_NOT
    if excluded:
        if expression.num_args() != 1:
            return None
        expression = expression.arg(0)
        if not z3.is_app(expression):
            return None
    if expression.decl().kind() != z3.Z3_OP_EQ:
        return None
    left, right = expression.arg(0), expression.arg(1)
    for slot, code in ((left, right), (right, left)):
        if _frame_state_slot(slot, frame):
            value = _numeric_value(code)
            if value is not None:
                return {
                    "kind": "state_membership",
                    "frame": frame,
                    "state": value,
                    "excluded": excluded,
                }
    return None


def _frame_state_slot(expression: Any, frame: int) -> bool:
    """Report whether an expression is the state slot of one frame.

    The slot is named ``F_<frame>_state`` by the encoding, which is exactly the
    shape :func:`_frame_variable_name` rejects for model variables, so the two
    readers stay disjoint rather than competing for the same operand.

    :param expression: The candidate operand.
    :type expression: object
    :param frame: The frame the slot must belong to.
    :type frame: int
    :return: ``True`` when the operand is that frame's state slot.
    :rtype: bool

    Example::

        >>> import z3
        >>> _frame_state_slot(z3.Int("F_0_state"), 0)
        True
        >>> _frame_state_slot(z3.Int("F_0_state"), 1)
        False
    """
    import z3

    if not z3.is_const(expression):
        return False
    return str(expression) == "F_%d_state" % frame


def _event_path_of_symbol(expression: Any, event_paths: Optional[Any] = None):
    """Return the event a proposition symbol stands for, and the step it names.

    The encoder builds the symbol as ``E_<step>_event_<id>_<body>_<digest>``, where
    the body is the event path with its dots replaced and the digest is a hash of
    the path itself.  Reading the body back recovers the replacement rather than the
    path, so two events whose names differ only in a dot would share it.  Hashing the
    known paths and comparing instead answers with the path the author wrote, or with
    nothing.

    Without ``event_paths`` the body is the fallback, which is correct for every path
    whose characters survive the replacement intact -- the same trade
    :func:`_frame_variable_name` makes for a variable name.

    :param expression: The candidate symbol.
    :type expression: object
    :param event_paths: Event paths to resolve against, defaults to ``None``.
    :type event_paths: Optional[Iterable[str]], optional
    :return: ``(path, step)``, or ``None`` when the operand is not one.
    :rtype: Optional[Tuple[str, int]]
    """
    import z3

    if not z3.is_const(expression):
        return None
    text = str(expression)
    parts = text.split("_")
    if len(parts) < 5 or parts[0] != "E" or not parts[1].isdigit():
        return None
    if parts[2] != "event":
        return None
    step = int(parts[1])
    digest = parts[-1]
    if event_paths:
        matches = [
            path
            for path in event_paths
            if hashlib.sha1(path.encode("utf-8")).hexdigest() == digest
        ]
        if len(matches) != 1:
            # No match means the symbol is not this model's event; more than one
            # would mean the digest failed to tell them apart, and either answer
            # would name the wrong declaration.
            return None
        return matches[0], step
    body = "_".join(parts[4:-1])
    return (body, step) if body else None


def _proposition_fact(
    group: Any, event_paths: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """Read an event assumption as the proposition it requires.

    An event assertion is one requirement about one event at one step, and the
    encoding says so directly: a single boolean symbol, negated when the query wrote
    ``== false``.  The published fact keeps that shape -- one identity, one polarity
    -- so the rule that closes a core holding both a proposition and its complement
    can compare them without knowing how either was spelled.

    The step is part of the identity.  Leaving it out would make "this event at step
    0" and "the same event at step 1" one subject, and the rule would then report a
    contradiction the query never stated.

    :param group: The tracked group to read.
    :type group: BmcTrackedConstraint
    :param event_paths: Event paths to resolve the symbol against, defaults to
        ``None``.
    :type event_paths: Optional[Iterable[str]], optional
    :return: The fact mapping, or ``None`` when the shape is not one event symbol.
    :rtype: Optional[Dict[str, Any]]
    """
    import z3

    if len(group.expressions) != 1:
        return None
    expression = group.expressions[0]
    holds = True
    if z3.is_app(expression) and expression.decl().kind() == z3.Z3_OP_NOT:
        if expression.num_args() != 1:
            return None
        expression, holds = expression.arg(0), False
    resolved = _event_path_of_symbol(expression, event_paths)
    if resolved is None:
        return None
    path, step = resolved
    return {
        "kind": "proposition",
        # One string rather than two fields: the rule compares subjects for equality
        # and nothing else, so a single opaque identity is what it needs, while a
        # reader gets the path and the step it was built from.
        "identity": "%s@%d" % (path, step),
        "holds": holds,
    }


def conjunctive_units(expression: Any) -> Tuple[Any, ...]:
    """Split one constraint into the independent requirements it makes.

    Two rewrites, applied until neither changes anything:

    * a conjunction contributes its members rather than itself, recursively, so a
      nested ``And`` is flattened rather than counted as one requirement;
    * an implication whose consequent is a conjunction contributes one implication
      per member, because "under P, both a and b hold" says the same as "under P,
      a holds" beside "under P, b holds".

    The order is the traversal's own -- depth first, left to right, with a
    distributed implication taking the position of the consequent member it came
    from.  It is part of the contract rather than an accident: a published fact
    identifies which requirement it stands for by index, so the same model and
    query have to decompose the same way every time.

    An implication whose consequent is a further implication is left alone.  The
    rewrite is about conjunctive consequents; collapsing nested antecedents would
    be a second transformation with its own soundness argument, and this reading is
    not the place to make it.

    :param expression: The constraint to split.
    :type expression: z3.BoolRef
    :return: The requirements, in traversal order.
    :rtype: Tuple[z3.BoolRef, ...]

    Example::

        >>> import z3
        >>> a, b, p = z3.Bool("a"), z3.Bool("b"), z3.Bool("p")
        >>> [str(unit) for unit in conjunctive_units(z3.And(a, z3.And(b, p)))]
        ['a', 'b', 'p']
        >>> [str(unit) for unit in conjunctive_units(z3.Implies(p, z3.And(a, b)))]
        ['Implies(p, a)', 'Implies(p, b)']
    """
    import z3

    def flatten(node: Any) -> List[Any]:
        if z3.is_and(node):
            return [unit for child in node.children() for unit in flatten(child)]
        return [node]

    units = flatten(expression)
    changed = True
    while changed:
        changed = False
        rewritten: List[Any] = []
        for unit in units:
            if z3.is_implies(unit):
                consequents = flatten(unit.arg(1))
                if len(consequents) > 1:
                    rewritten.extend(
                        z3.Implies(unit.arg(0), part) for part in consequents
                    )
                    changed = True
                    continue
            rewritten.append(unit)
        units = rewritten
    return tuple(units)


def _frame_of_symbol(expression: Any) -> Optional[int]:
    """Return the frame index a frame symbol belongs to.

    :param expression: The candidate symbol.
    :type expression: object
    :return: The frame index, or ``None`` when the operand is not a frame symbol.
    :rtype: Optional[int]
    """
    text = str(_without_coercion(expression))
    if not text.startswith("F_"):
        return None
    parts = text.split("_")
    if len(parts) < 3 or not parts[1].isdigit():
        return None
    return int(parts[1])


#: How a z3 arithmetic application names the operation a published fact reports.
#:
#: Keyed by ``decl().kind()`` so the reading does not depend on how z3 renders the
#: operator.  Only the four the evaluation rule can apply appear here: an operation
#: outside this set has no published name, so the case it belongs to degrades
#: rather than arriving under a name no rule evaluates.
def _arithmetic_operations(z3: Any) -> Dict[int, str]:
    """Return the operation name for each arithmetic declaration kind.

    :param z3: The imported ``z3`` module.
    :type z3: module
    :return: Declaration kind mapped to the published operation name.
    :rtype: Dict[int, str]
    """
    return {
        z3.Z3_OP_ADD: "add",
        z3.Z3_OP_SUB: "sub",
        z3.Z3_OP_MUL: "mul",
        z3.Z3_OP_IDIV: "div",
        z3.Z3_OP_DIV: "div",
    }


def _condition_facts(
    expression: Any, declared: Optional[Any] = None
) -> Optional[Tuple[Dict[str, Any], ...]]:
    """Read the condition that selects one case as the facts it requires.

    The condition is published as facts rather than as the encoder's own text.  A
    reader is owed the model's terms -- a frame, a state, a variable -- and the
    encoder's rendering carries neither: ``And(1 == F_0_state, True)`` names a slot
    and a digest, so a consumer could not match it against anything and a sentence
    quoting it would put the encoding in front of the reader.

    Order is the conjunction's own, so the same model and query publish the same
    list every time.  A conjunct that is trivially true carries no requirement and
    is dropped; one that no existing fact category reads makes the whole condition
    unreadable, and the case then keeps its structural identity rather than
    publishing a condition weaker than the one the encoding holds.

    :param expression: The case's selection condition.
    :type expression: z3.BoolRef
    :param declared: Model variable names to resolve symbols against, defaults to
        ``None``.
    :type declared: Optional[Iterable[str]], optional
    :return: The facts the condition requires, in conjunction order, or ``None``
        when any conjunct has no reading.
    :rtype: Optional[Tuple[Dict[str, Any], ...]]
    """
    import z3

    facts: List[Dict[str, Any]] = []
    for conjunct in conjunctive_units(expression):
        if z3.is_true(conjunct):
            # The guard slot of a transition that carries no guard.  It requires
            # nothing, so publishing it would add a member standing for nothing.
            continue
        fact = _state_equality_fact(conjunct, declared)
        if fact is None:
            fact = _variable_comparison_in(conjunct, declared)
        if fact is None:
            # An event-triggered transition names its event in the condition, and the
            # reading for that was already here -- one function away, used by the
            # proposition publisher -- while this list knew two readings and not the
            # third.  A condition mentioning an event was therefore unreadable, and
            # the case kept its structural identity, which is what kept the whole
            # arithmetic chain from starting on any event-triggered model.
            fact = _event_proposition_in(conjunct)
        if fact is None:
            return None
        facts.append(fact)
    return tuple(facts)


def _condition_can_hold(expression: Any) -> bool:
    """Report whether a case's condition is satisfiable at all.

    A case whose condition cannot hold never fires, so it states nothing about the
    step and must not be counted among the step's assignments.  The shape this exists
    for is the fallback case of a state whose every outgoing transition is
    unconditional: "no transition applies" reduces to ``s == state and not s ==
    state``.

    The solve is over one small condition with no budget attached, which is
    deliberate: a step relation has a handful of cases and each condition is a short
    conjunction, and an unknown answer is treated as "may hold" so an undecided solve
    can only make the reading more conservative, never less.

    :param expression: The case's selection condition.
    :type expression: z3.BoolRef
    :return: ``False`` only when the condition is refuted outright.
    :rtype: bool

    Example::

        >>> import z3
        >>> _condition_can_hold(z3.BoolVal(True))
        True
        >>> _condition_can_hold(z3.BoolVal(False))
        False
    """
    import z3

    solver = z3.Solver()
    solver.add(expression)
    return solver.check() != z3.unsat


def _event_proposition_in(expression: Any) -> Optional[Dict[str, Any]]:
    """Read a condition conjunct that requires an event, as a ``proposition`` fact.

    The same reading the proposition publisher performs, applied where a case's
    condition names the event that triggers its transition.  No event-path table is
    needed: the encoder puts the path and the step into the symbol's own name, so the
    fact is recoverable from the symbol alone.

    :param expression: One conjunct of a case's selection condition.
    :type expression: z3.BoolRef
    :return: A ``proposition`` fact, or ``None`` when the conjunct names no event.
    :rtype: Optional[Dict[str, object]]

    Example::

        >>> _event_proposition_in(None) is None
        True
    """
    import z3

    if expression is None:
        return None
    holds = True
    if z3.is_app(expression) and expression.decl().kind() == z3.Z3_OP_NOT:
        if expression.num_args() != 1:
            return None
        holds = False
        expression = expression.arg(0)
    resolved = _event_path_of_symbol(expression)
    if resolved is None:
        return None
    path, step = resolved
    # The shape is copied from :func:`_proposition_fact`, field for field.  Writing it
    # from understanding instead produced ``event`` and ``step`` here against its
    # ``identity``, which every consumer compares for equality -- two spellings of one
    # fact is how a rule comes to refuse a premise that says what it asked for.
    return {
        "kind": "proposition",
        "identity": "%s@%d" % (path, step),
        "holds": holds,
    }


def _state_equality_fact(
    expression: Any, declared: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """Read one equality between a state code and some frame's state slot.

    Unlike :func:`_state_membership_fact` the frame is not known in advance here:
    a condition names the frame it speaks about rather than inheriting it from a
    group's refs, so the slot's own name supplies it.

    :param expression: The candidate conjunct.
    :type expression: z3.BoolRef
    :param declared: Unused; present so both condition readers share one shape.
    :type declared: Optional[Iterable[str]], optional
    :return: A ``state_membership`` fact, or ``None``.
    :rtype: Optional[Dict[str, Any]]
    """
    import z3

    del declared
    if not z3.is_app(expression) or expression.decl().kind() != z3.Z3_OP_EQ:
        return None
    if expression.num_args() != 2:
        return None
    for slot, code in (
        (expression.arg(0), expression.arg(1)),
        (expression.arg(1), expression.arg(0)),
    ):
        frame = _frame_of_symbol(slot)
        if frame is None or not _frame_state_slot(slot, frame):
            continue
        value = _numeric_value(code)
        if value is not None:
            return {
                "kind": "state_membership",
                "frame": frame,
                "state": value,
                "excluded": False,
            }
    return None


def _variable_comparison_in(
    expression: Any, declared: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """Read one comparison between a frame variable and a numeral.

    The group-level reader takes its frame from ``refs``; a guard inside a
    condition names its own, so this one reads the frame off the symbol.

    :param expression: The candidate conjunct.
    :type expression: z3.BoolRef
    :param declared: Model variable names to resolve symbols against, defaults to
        ``None``.
    :type declared: Optional[Iterable[str]], optional
    :return: A ``variable_comparison`` fact, or ``None``.
    :rtype: Optional[Dict[str, Any]]
    """
    import z3

    if not z3.is_app(expression):
        return None
    operator = _relational_operators(z3).get(expression.decl().kind())
    if operator is None or expression.num_args() != 2:
        return None
    left, right = expression.arg(0), expression.arg(1)
    name, value = _frame_variable_name(left, declared), _numeric_value(right)
    slot = left
    if name is None or value is None:
        name, value = _frame_variable_name(right, declared), _numeric_value(left)
        slot = right
        operator = {"lt": "gt", "gt": "lt", "le": "ge", "ge": "le"}.get(
            operator, operator
        )
    if name is None or value is None:
        return None
    frame = _frame_of_symbol(slot)
    if frame is None:
        return None
    return {
        "kind": "variable_comparison",
        "variable": name,
        "frame": frame,
        "operator": operator,
        "value": value,
    }


def _assignment_in_unit(
    unit: Any, step: int, declared: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """Read one decomposed requirement as an assignment a transition makes.

    The shape read is ``Implies(condition, next == <arithmetic over this frame>)``:
    an implication whose consequent equates a variable at the following frame with
    an expression over the same variable at this one.  A requirement that only
    carries a value forward unchanged is not an assignment the model wrote, so it
    is declined -- reporting it would put "x becomes x" in a proof as though the
    transition had said something.

    :param unit: One requirement from :func:`conjunctive_units`.
    :type unit: z3.BoolRef
    :param step: The macro-step the requirement belongs to.
    :type step: int
    :param declared: Model variable names to resolve symbols against, defaults to
        ``None``.
    :type declared: Optional[Iterable[str]], optional
    :return: The variable, operation and operand, or ``None`` when the requirement
        is not an assignment.
    :rtype: Optional[Dict[str, Any]]
    """
    import z3

    if not z3.is_implies(unit):
        return None
    consequent = unit.arg(1)
    if not z3.is_eq(consequent) or consequent.num_args() != 2:
        return None
    # Operand order is not fixed.  An arithmetic update encodes as
    # ``F_next_x == F_step_x + 1`` and a constant assignment as ``1 == F_next_x``, so
    # reading position 0 as the target alone finds one shape and misses the other --
    # which is how a plain ``x = 1`` went unpublished.  The mirrored reading is what
    # the value-comparison recognizer has always done, and the omission here was the
    # asymmetry.
    target, source = consequent.arg(0), consequent.arg(1)
    variable = _frame_variable_name(target, declared)
    if variable is None or _frame_of_symbol(target) != step + 1:
        target, source = consequent.arg(1), consequent.arg(0)
        variable = _frame_variable_name(target, declared)
    if variable is None or _frame_of_symbol(target) != step + 1:
        return None
    if not z3.is_app(source):
        return None
    value = _numeric_value(source)
    if value is not None:
        # ``x = 1``: the next frame's value does not depend on this one, so the
        # published operation is a replacement rather than an arithmetic update.  The
        # rules read ``set`` and decline it -- "x becomes 1" is not a step a value can
        # be carried across -- but the reader is still owed what the transition wrote.
        return {
            "variable": variable,
            "operation": "set",
            "operand": value,
            "condition_expression": unit.arg(0),
        }
    operation = _arithmetic_operations(z3).get(source.decl().kind())
    if operation is None or source.num_args() != 2:
        return None
    left, right = source.arg(0), source.arg(1)
    if (
        _frame_variable_name(left, declared) != variable
        or _frame_of_symbol(left) != step
    ):
        # The rule that evaluates this reads the left operand as the variable's own
        # value at this frame.  A different subject there is a statement about two
        # variables, which the published shape has no field for.
        return None
    reading = {
        "variable": variable,
        "operation": operation,
        "condition_expression": unit.arg(0),
    }
    operand = _numeric_value(right)
    if operand is not None:
        reading["operand"] = operand
        return reading
    operand_variable = _frame_variable_name(right, declared)
    if operand_variable is None or _frame_of_symbol(right) != step:
        return None
    # A symbolic operand is named rather than resolved: the substitution rule needs
    # to see which variable is still standing before the evaluation rule can run.
    reading["operand_variable"] = operand_variable
    return reading


def _transition_case_fact(
    group: Any, declared: Optional[Any] = None
) -> Optional[Dict[str, Any]]:
    """Read a step relation as the assignment its one assigning case makes.

    A step relation holds every case the step could take -- initial entry, delta,
    absorb, fallback, each authored transition -- so it is a conjunction of many
    requirements rather than one statement.  What a reader is owed from it is the
    assignment the model wrote, and that is recoverable when exactly one decomposed
    requirement reads as an assignment: the fact then names it and carries the
    condition under which it applies, which is what lets a checker agree that the
    fact and the requirement say the same thing.

    Two or more assigning requirements are declined rather than picked between.
    The group would then need one fact per assignment, and publishing one of them
    as though it were the group's reading would hide the rest.

    A requirement whose condition cannot hold is not one of them.  A step's fallback
    case requires that no transition applies, and where every transition out of the
    state is unconditional that requirement reduces to ``s == state and not
    s == state`` -- unsatisfiable, so the case never fires and says nothing about the
    step.  Counting it as a second assignment is what made a ``during`` action on such
    a state unreadable: two readings, one of them empty, and the group declined a
    reading it could have given.

    :param group: The tracked group to read.
    :type group: BmcTrackedConstraint
    :param declared: Model variable names to resolve symbols against, defaults to
        ``None``.
    :type declared: Optional[Iterable[str]], optional
    :return: The fact mapping, or ``None`` when the step makes no single
        recoverable assignment.
    :rtype: Optional[Dict[str, Any]]
    """
    if len(group.expressions) != 1:
        return None
    step = group.refs.get("step")
    if not isinstance(step, int):
        return None
    # Which requirement of the group this reads is a property of the *binding*, not
    # of the fact, so the position is used to decide uniqueness and then dropped.
    # The binding check recomputes the decomposition; publishing the index here as
    # well would give a reader two answers that could disagree.
    readings = [
        reading
        for reading in (
            _assignment_in_unit(unit, step, declared)
            for unit in conjunctive_units(group.expressions[0])
        )
        if reading is not None and _condition_can_hold(reading["condition_expression"])
    ]
    if len(readings) != 1:
        return None
    reading = readings[0]
    fact = {
        "kind": "transition_case",
        "variable": reading["variable"],
        "frame": step,
        "target_frame": step + 1,
        "operation": reading["operation"],
    }
    if "operand" in reading:
        fact["operand"] = reading["operand"]
    else:
        fact["operand_variable"] = reading["operand_variable"]
    # The condition travels as facts rather than as the encoder's text, and a
    # condition with no reading takes the whole case down with it: publishing an
    # assignment whose condition is weaker than the encoding's would state something
    # the group does not require, which the binding check refuses in one direction
    # and a reader has no way to notice.
    condition = _condition_facts(reading["condition_expression"], declared)
    if not condition:
        return None
    fact["condition"] = list(condition)
    return fact


def normalized_fact_for(
    group: Any,
    declared: Optional[Any] = None,
    event_paths: Optional[Any] = None,
) -> Dict[str, Any]:
    """Return the published domain fact for one tracked source group.

    The reading is deterministic and carries no Z3 object: a machine consumer
    dispatches on ``kind`` and reads plain values.  A group whose shape has no
    recognizer keeps its identity under ``structural_constraint`` rather than
    inviting a reader to guess a domain meaning that was never derived.

    :param group: The tracked group whose fact is published.
    :type group: BmcTrackedConstraint
    :param declared: The model's variable names.  A published fact names the
        variable that was declared rather than the encoder's rendering of it;
        without this the reader falls back to the symbol body, which is correct
        for every name short enough to survive truncation intact.  Defaults to
        ``None``.
    :type declared: Optional[Iterable[str]], optional
    :param event_paths: The model's event paths, resolved the same way and for the
        same reason: the symbol body replaces the path's dots, so two events whose
        names differ only there would share it.  Defaults to ``None``.
    :type event_paths: Optional[Iterable[str]], optional
    :return: A tagged mapping of plain JSON-compatible values.
    :rtype: Dict[str, Any]

    Example::

        >>> import z3
        >>> from pyfcstm.bmc.provenance import BmcSourceRef, BmcTrackedConstraint
        >>> group = BmcTrackedConstraint(
        ...     "assumption.0000.frame.0000", "assumptions", "assumption.frame",
        ...     (z3.Int("F_0_x_deadbeef11") == 1,),
        ...     BmcSourceRef("generated", None, None),
        ...     refs={"frame": 0, "assumption": 0},
        ... )
        >>> fact = normalized_fact_for(group)
        >>> fact["kind"], fact["variable"], fact["operator"], fact["value"]
        ('variable_comparison', 'x', 'eq', 1)
    """
    if group.category in _VALUE_FACT_CATEGORIES:
        fact = _value_comparison_fact(group, declared)
        if fact is not None:
            return fact
        # An assumption may pin the active state rather than a variable, and both
        # arrive in the same category, so the state reader gets its turn before
        # the group falls back.
        fact = _state_membership_fact(group)
        if fact is not None:
            return fact
    elif group.category == "initial.target":
        fact = _state_membership_fact(group)
        if fact is not None:
            return fact
    elif group.category == "domain.frame_state":
        fact = _state_domain_fact(group)
        if fact is not None:
            return fact
    elif group.category == "definedness":
        fact = _definedness_fact(group, declared)
        if fact is not None:
            return fact
    elif group.category == "transition.step":
        fact = _transition_case_fact(group, declared)
        if fact is not None:
            return fact
    elif group.category == "assumption.event":
        fact = _proposition_fact(group, event_paths)
        if fact is not None:
            return fact
    return {
        "kind": "structural_constraint",
        "stable_id": group.stable_id,
        "stage": group.stage,
        "category": group.category,
    }


def json_canonical(value: Any) -> Any:
    """Convert a normalized metadata graph back to plain JSON containers.

    :func:`_require_json_mapping` stores nested mappings as read-only views and
    nested sequences as tuples so that a published value cannot be mutated
    through the caller's reference.  Those types have no JSON counterpart, so
    this restores ``dict`` and ``list`` on the way out.

    :param value: Normalized metadata value.
    :type value: object
    :return: The same data using only JSON containers.
    :rtype: object
    :raises ValueError: If the value nests deeper than
        :data:`MAX_METADATA_DEPTH`, which the validator also refuses.

    Example::

        >>> from types import MappingProxyType
        >>> json_canonical({"a": MappingProxyType({"b": (1, 2)})})
        {'a': {'b': [1, 2]}}
    """
    return _json_canonical(value, 0)


def _json_canonical(value: Any, depth: int) -> Any:
    """Recursive worker for :func:`json_canonical`, bounded by depth.

    The public entry point is bounded for the same reason the validator is: the
    JSON encoder that consumes this output shares the interpreter stack, so an
    unbounded walk turns a depth problem into a bare ``RecursionError`` with no
    field name.  A value built through the validator cannot exceed the limit, but
    this function is public and can be handed data that never went through it.

    :param value: Normalized metadata value.
    :type value: object
    :param depth: Current nesting depth.
    :type depth: int
    :return: The same data using only JSON containers.
    :rtype: object
    :raises ValueError: If the value nests deeper than
        :data:`MAX_METADATA_DEPTH`.

    Example::

        >>> _json_canonical({"a": (1,)}, 0)
        {'a': [1]}
    """
    if depth > MAX_METADATA_DEPTH:
        raise ValueError(
            "value nests deeper than the published limit of %d levels."
            % MAX_METADATA_DEPTH
        )
    if isinstance(value, Mapping):
        return {key: _json_canonical(item, depth + 1) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_canonical(item, depth + 1) for item in value]
    return value


@dataclass(frozen=True)
class BmcSourceRef:
    """Stable reference to a FCSTM, FBMCQ, or generated source location.

    :param kind: Source kind: ``fcstm``, ``fbmcq``, or ``generated``.
    :type kind: str
    :param path: Display path, or ``None`` when no reliable path is available.
    :type path: Optional[str]
    :param span: One-based, end-exclusive source span, or ``None``.
    :type span: Optional[pyfcstm.utils.validate.Span]
    :raises ValueError: If the source kind is unsupported, a ``generated``
        reference carries a path or span, or the path is neither ``None`` nor a
        non-empty string.
    :raises TypeError: If ``span`` is neither ``None`` nor a
        :class:`pyfcstm.utils.validate.Span`.

    Example::

        >>> BmcSourceRef("generated", None, None).kind
        'generated'
    """

    kind: str
    path: Optional[str]
    span: Optional[Span]

    def __post_init__(self) -> None:
        # The kind is checked against the vocabulary as exact text, and the
        # field is replaced by it so every later reader sees the same value.
        try:
            plain_kind = exact_str(self.kind, "BMC source kind")
        except TypeError:
            # exact_str raises for anything that is not a str, which is how a wrong
            # type passed to this constructor arrives here.
            raise ValueError("Unsupported BMC source kind: %r." % self.kind) from None
        if plain_kind not in _SOURCE_KINDS:
            raise ValueError("Unsupported BMC source kind: %r." % self.kind)
        object.__setattr__(self, "kind", plain_kind)
        if self.kind == "generated" and (
            self.path is not None or self.span is not None
        ):
            raise ValueError(
                "generated BMC source references cannot carry path or span."
            )
        if self.path is not None:
            try:
                plain_path = exact_str(self.path, "BMC source path")
            except TypeError:
                # exact_str raises for anything that is not a str, which is how a
                # wrong type passed to this constructor arrives here.
                raise ValueError(
                    "BMC source path must be None or a non-empty string."
                ) from None
            if not plain_path:
                raise ValueError("BMC source path must be None or a non-empty string.")
            object.__setattr__(self, "path", plain_path)
        # A span is read field by field downstream, so anything that is not a
        # Span is refused here rather than at the first reader of ``span.line``.
        if self.span is not None:
            if type(self.span) is not Span:
                raise TypeError("BMC source span must be Span or None.")
            # Span itself imposes no bounds, being a shared utility, so the
            # coordinates are checked where they are published.  The schema types
            # them as integers, and this is the one direction the asymmetry
            # ledger does not cover: a constructor looser than the schema emits
            # output that fails the contract it publishes.
            object.__setattr__(
                self,
                "span",
                Span(
                    exact_index(self.span.line, "BMC source span line"),
                    exact_index(self.span.column, "BMC source span column"),
                    exact_optional_index(
                        self.span.end_line, "BMC source span end_line"
                    ),
                    exact_optional_index(
                        self.span.end_column, "BMC source span end_column"
                    ),
                ),
            )

    def to_canonical(self) -> Dict[str, Any]:
        """Return a JSON-compatible source reference.

        :return: Canonical source reference dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> BmcSourceRef("generated", None, None).to_canonical()
            {'kind': 'generated', 'path': None, 'span': None}
        """
        span = None
        if self.span is not None:
            span = {
                "line": self.span.line,
                "column": self.span.column,
                "end_line": self.span.end_line,
                "end_column": self.span.end_column,
            }
        return {"kind": self.kind, "path": self.path, "span": span}


#: Every stage and category pairing a tracked group may carry.
#:
#: The pair is checked, not each field separately: a stage and a category can
#: each be individually valid and still describe a group no build emits.  This
#: class is exported and documented, so a caller can construct such a group
#: directly -- and then :func:`pyfcstm.bmc.explanation.constraint_aggregate`,
#: which is equally public, cannot say which aggregate it belongs to.  Refusing
#: the pair here keeps those two public surfaces from disagreeing.
#:
#: Adding a pairing is a deliberate act that belongs in the same change as the
#: registration that needs it.
TRACKED_GROUP_PAIRINGS = frozenset(
    {
        ("assumptions", "assumption.cardinality"),
        ("assumptions", "assumption.event"),
        ("assumptions", "assumption.frame"),
        ("assumptions", "definedness"),
        ("initialization", "definedness"),
        ("initialization", "initial.target"),
        ("initialization", "initial.variable"),
        ("initialization", "initial.where"),
        ("kernel", "domain.frame_state"),
        ("kernel", "transition.case"),
        ("kernel", "transition.step"),
    }
)


@dataclass(frozen=True)
class BmcTrackedConstraint:
    """One source-group occurrence and its generated Boolean expressions.

    The expressions are intentionally typed as ``Any`` here so this module
    remains solver-independent.  The Z3 relation builder validates that every
    expression is a Boolean expression in one context before accepting a group.

    :param stable_id: Deterministic non-empty group identifier.
    :type stable_id: str
    :param stage: Formula stage such as ``kernel`` or ``assumptions``.
    :type stage: str
    :param category: Domain-specific group category.
    :type category: str
    :param expressions: Non-empty generated Boolean-expression sequence.
    :type expressions: Tuple[object, ...]
    :param source_ref: Source document reference for the group.
    :type source_ref: BmcSourceRef
    :param refs: Stable frame/step/case metadata, defaults to ``{}``.
    :type refs: Mapping[str, object], optional
    :raises ValueError: If the stable id is not a non-empty printable-ASCII
        string, the stage or category is not a string, the expression sequence is
        empty, or the stage and category pair is not one of
        :data:`TRACKED_GROUP_PAIRINGS` -- which is also how an empty stage or
        category is refused, since no listed pair contains one.
    :raises TypeError: If ``source_ref`` is not a :class:`BmcSourceRef`.

    Example::

        >>> group = BmcTrackedConstraint(
        ...     "initial.target", "initialization", "initial.target", (True,),
        ...     BmcSourceRef("generated", None, None),
        ... )
        >>> group.stable_id
        'initial.target'
    """

    stable_id: str
    stage: str
    category: str
    expressions: Tuple[Any, ...]
    source_ref: BmcSourceRef
    refs: Mapping[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # The exact text replaces the field before the emptiness check and every
        # later reader, so all of them see the same characters.
        try:
            plain_id = exact_str(self.stable_id, "tracked constraint stable_id")
        except TypeError:
            # exact_str raises for anything that is not a str, which is how a
            # wrong type passed to this constructor arrives here.
            raise ValueError(
                "tracked constraint stable_id must be non-empty."
            ) from None
        if not plain_id:
            raise ValueError("tracked constraint stable_id must be non-empty.")
        object.__setattr__(self, "stable_id", plain_id)
        for name in ("stage", "category"):
            value = getattr(self, name)
            try:
                object.__setattr__(
                    self, name, exact_str(value, "tracked constraint %s" % name)
                )
            except TypeError:
                # exact_str raises for anything that is not a str.
                # Storing it would leave the group carrying a value that has no
                # text for anything downstream to read.
                raise ValueError(
                    "tracked constraint %s must be a string." % name
                ) from None
        if (self.stage, self.category) not in TRACKED_GROUP_PAIRINGS:
            raise ValueError(
                "tracked constraint stage/category pairing %r is not one the "
                "builder registers; add it to TRACKED_GROUP_PAIRINGS in the same "
                "change as the registration that needs it."
                % ((self.stage, self.category),)
            )
        if not all("\x20" <= char <= "\x7e" for char in self.stable_id):
            # The id becomes a solver literal name and a JSON key downstream, so
            # the frozen contract keeps it printable ASCII.  ``str.isascii`` is
            # the wrong test here: it also admits control characters, which the
            # published pattern rejects, so the two boundaries would disagree.
            raise ValueError(
                "tracked constraint stable_id must be printable ASCII, got %r."
                % self.stable_id
            )
        expressions = tuple(self.expressions)
        if not expressions:
            raise ValueError("tracked constraint expressions must be non-empty.")
        if type(self.source_ref) is not BmcSourceRef:
            raise TypeError("tracked constraint source_ref must be BmcSourceRef.")
        object.__setattr__(self, "expressions", expressions)
        # The same validation the published metadata gets.  A shallow copy here
        # would make this a third door with its own rules: the builder's mapping
        # would keep a caller's nested aliases and could hold values that only
        # fail once the whole result is serialized.
        object.__setattr__(
            self, "refs", MappingProxyType(_require_json_mapping(self.refs, "refs"))
        )


@dataclass(frozen=True)
class SourceDocumentRegistry:
    """Immutable source-text snapshot used for exact provenance excerpts.

    :param documents: Mapping from internal source paths to complete UTF-8
        source text snapshots.
    :type documents: Mapping[str, str]
    :param display_root: Optional directory used to produce stable relative
        display paths, defaults to ``None``.
    :type display_root: Optional[str], optional
    :param query_documents: FBMCQ-only source snapshots kept separate from
        FCSTM documents, defaults to ``{}``.
    :type query_documents: Mapping[str, str], optional
    :raises ValueError: If any FCSTM or FBMCQ document path is not a non-empty
        string.
    :raises TypeError: If any FCSTM or FBMCQ document text is not a string.

    .. note::
        Stored snapshots are passed through :func:`_normalize_line_separators`
        so that excerpt slicing uses the same line model as the lexer that
        produced the spans.

    Example::

        >>> SourceDocumentRegistry({"a.fcstm": "state A;"}).document("a.fcstm")
        'state A;'
    """

    documents: Mapping[str, str]
    display_root: Optional[str] = None
    query_documents: Mapping[str, str] = field(
        default_factory=dict, repr=False, compare=False
    )

    @staticmethod
    def _snapshot(documents: Any, label: str) -> Dict[str, str]:
        """Return an exact-keyed, line-normalized copy of one document mapping.

        :param documents: Mapping from source paths to complete document text.
        :type documents: Mapping[str, str]
        :param label: Field name used in the error messages.
        :type label: str
        :return: The same documents keyed by exact text.
        :rtype: Dict[str, str]
        :raises ValueError: If a path is not a non-empty string.
        :raises TypeError: If a document text is not a string.

        Example::

            >>> SourceDocumentRegistry._snapshot({"a.fcstm": "x"}, "source document")
            {'a.fcstm': 'x'}
        """
        snapshot = {}
        pairs = (
            dict.items(documents)
            if isinstance(documents, dict)
            else dict(documents).items()
        )
        for path, text in pairs:
            try:
                plain_path = exact_str(path, "%s path" % label)
            except TypeError:
                # exact_str raises for anything that is not a str.
                raise ValueError(
                    "%s paths must be non-empty strings." % label
                ) from None
            if not plain_path:
                raise ValueError("%s paths must be non-empty strings." % label)
            if plain_path in snapshot:  # pragma: no cover - see the refs key note.
                # Same shape as the refs key collision above, and unreachable for
                # the same reason: silently keeping one entry would drop a document
                # with nothing recorded, so it fails closed instead.
                raise ValueError(
                    "%s paths contain two entries for %r." % (label, plain_path)
                )
            if not isinstance(text, str):
                raise TypeError("%s text must be strings." % label)
            snapshot[plain_path] = _normalize_line_separators(text)
        return snapshot

    def __post_init__(self) -> None:
        # Keys are rebuilt as exact text, not stored as given.  A str subclass
        # overriding __eq__/__hash__ would otherwise make every lookup hit the
        # same document, so one file's text would be quoted as another's
        # provenance -- the one thing this registry exists to rule out.
        object.__setattr__(
            self,
            "documents",
            MappingProxyType(self._snapshot(self.documents, "source document")),
        )
        object.__setattr__(
            self,
            "query_documents",
            MappingProxyType(self._snapshot(self.query_documents, "query document")),
        )
        if self.display_root is not None:
            object.__setattr__(self, "display_root", os.path.abspath(self.display_root))

    def display_path(self, path: Optional[str]) -> Optional[str]:
        """Return a stable display path for an internal source path.

        :param path: Internal source path, or ``None``.
        :type path: Optional[str]
        :return: Relative display path when possible, otherwise original path.
        :rtype: Optional[str]

        Example::

            >>> SourceDocumentRegistry({"machine.fcstm": ""}).display_path("machine.fcstm")
            'machine.fcstm'
        """
        if path is None:
            return None
        if self.display_root is None or not os.path.isabs(path):
            return path
        try:
            return os.path.relpath(path, self.display_root)
        except ValueError:
            # ValueError: Windows drives can be unrelated, so retain the
            # caller-provided path rather than inventing a relative location.
            return path

    def document(self, path: Optional[str], kind: str = "fcstm") -> Optional[str]:
        """Return a snapshotted document by internal or display path.

        :param path: Internal or display path.
        :type path: Optional[str]
        :param kind: Source kind namespace, defaults to ``'fcstm'``.
        :type kind: str, optional
        :return: Source text, or ``None`` when no document is available.
        :rtype: Optional[str]

        Example::

            >>> SourceDocumentRegistry({"a.fcstm": "state A;"}).document("a.fcstm")
            'state A;'
        """
        if path is None:
            return None
        if kind == "fcstm":
            documents = self.documents
        elif kind == "fbmcq":
            documents = self.query_documents
        else:
            return None
        if path in documents:
            return documents[path]
        for internal_path, text in documents.items():
            if self.display_path(internal_path) == path:
                return text
        return None

    def reference(
        self, kind: str, path: Optional[str], span: Optional[Span]
    ) -> BmcSourceRef:
        """Create a source reference with the registry's display-path policy.

        :param kind: Source kind.
        :type kind: str
        :param path: Internal path, or ``None``.
        :type path: Optional[str]
        :param span: Optional source span.
        :type span: Optional[pyfcstm.utils.validate.Span]
        :return: Display-normalized source reference.
        :rtype: BmcSourceRef

        Example::

            >>> registry = SourceDocumentRegistry({"a.fcstm": ""})
            >>> registry.reference("fcstm", "a.fcstm", None).path
            'a.fcstm'
        """
        display_path = self.display_path(path)
        if display_path is None:
            return BmcSourceRef(kind, None, None)
        if span is not None:
            document = self.document(path, kind=kind)
            if document is None or _span_offsets(document, span) is None:
                return BmcSourceRef(kind, display_path, None)
        return BmcSourceRef(kind, display_path, span)

    def excerpt(self, reference: BmcSourceRef) -> Optional[str]:
        """Return the exact source slice described by a reference.

        :param reference: Source reference to resolve.
        :type reference: BmcSourceRef
        :return: Exact half-open source slice, or ``None`` when unavailable or
            when the span is anchor-only/invalid.
        :rtype: Optional[str]

        Example::

            >>> registry = SourceDocumentRegistry({"a.fcstm": "state A;"})
            >>> registry.excerpt(BmcSourceRef("fcstm", "a.fcstm", Span(1, 1, 1, 9)))
            'state A;'
        """
        if reference.span is None:
            return None
        text = self.document(reference.path, kind=reference.kind)
        if text is None:
            return None
        offsets = _span_offsets(text, reference.span)
        if offsets is None:
            return None
        start, end = offsets
        return text[start:end]

    def model_reference(self, obj: object) -> BmcSourceRef:
        """Build a FCSTM reference from private model metadata.

        :param obj: Model object carrying optional ``_source_path`` and
            ``_span`` attributes.
        :type obj: object
        :return: FCSTM source reference, possibly without path/span.
        :rtype: BmcSourceRef

        Example::

            >>> SourceDocumentRegistry({}).model_reference(object()).kind
            'fcstm'
        """
        path = getattr(obj, "_source_path", None)
        span = getattr(obj, "_span", None)
        return self.reference("fcstm", path, span)

    def query_reference(self, query: object, obj: object) -> BmcSourceRef:
        """Build an FBMCQ reference from root-query private metadata.

        :param query: Root query carrying ``_source_path`` and ``_source_spans``.
        :type query: object
        :param obj: Query node whose identity is being resolved.
        :type obj: object
        :return: FBMCQ source reference, possibly without path/span.
        :rtype: BmcSourceRef

        Example::

            >>> SourceDocumentRegistry({}).query_reference(object(), object()).kind
            'fbmcq'
        """
        spans = dict(getattr(query, "_source_spans", ()) or ())
        return self.reference(
            "fbmcq", getattr(query, "_source_path", None), spans.get(id(obj))
        )


__all__ = [
    "MAX_METADATA_DEPTH",
    "normalized_fact_for",
    "TRACKED_GROUP_PAIRINGS",
    "BmcSourceRef",
    "BmcTrackedConstraint",
    "SourceDocumentRegistry",
    "exact_float",
    "exact_index",
    "exact_int",
    "exact_optional_index",
    "exact_str",
    "json_canonical",
]
