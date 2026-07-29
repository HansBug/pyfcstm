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

import math
import os
import sys
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional, Tuple

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
            return entry
        if isinstance(entry, bool):
            # Only an object claiming to be a bool reaches here.
            raise TypeError("%s is not JSON-compatible, got %r." % (where, entry))
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
                if plain_key in normalized:
                    # Two distinct keys that coexist in the caller's mapping can
                    # canonicalize to one.  Overwriting would drop a piece of
                    # provenance with nothing recorded, so this fails closed.
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
        # Membership uses __eq__ and __hash__, both overridable, so the check
        # runs on the exact text and the field is replaced by it.
        if not isinstance(self.kind, str):
            raise ValueError("Unsupported BMC source kind: %r." % self.kind)
        try:
            plain_kind = exact_str(self.kind, "BMC source kind")
        except TypeError:
            # exact_str raises for anything that is not a str.
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
            if not isinstance(self.path, str):
                raise ValueError("BMC source path must be None or a non-empty string.")
            try:
                plain_path = exact_str(self.path, "BMC source path")
            except TypeError:
                # exact_str raises for anything that is not a str.
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
        # The exact text replaces the field before anything reads it: iterating
        # the value, measuring it or comparing it all go through methods the
        # value itself provides, so a subclass could pass the check below and
        # then publish characters the check would have refused.
        if not isinstance(self.stable_id, str):
            raise ValueError("tracked constraint stable_id must be non-empty.")
        try:
            plain_id = exact_str(self.stable_id, "tracked constraint stable_id")
        except TypeError:
            # exact_str raises for anything that is not a str.
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
            if plain_path in snapshot:
                # Two distinct keys can hold the same text; silently keeping one
                # would drop a document with nothing recorded.
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
