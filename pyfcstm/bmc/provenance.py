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

Examples::

    >>> from pyfcstm.bmc.provenance import BmcSourceRef, SourceDocumentRegistry
    >>> from pyfcstm.utils.validate import Span
    >>> registry = SourceDocumentRegistry({"machine.fcstm": "state Root;"})
    >>> ref = BmcSourceRef("fcstm", "machine.fcstm", Span(1, 1, 1, 13))
    >>> registry.excerpt(ref)
    'state Root;'
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Dict, Mapping, Optional, Tuple

from pyfcstm.utils.validate import Span

_SOURCE_KINDS = {"fcstm", "fbmcq", "generated"}


def _span_offsets(text: str, span: Span) -> Optional[Tuple[int, int]]:
    """Return character offsets for a complete one-based half-open span.

    :param text: Source document text.
    :type text: str
    :param span: One-based source span with optional end coordinates.
    :type span: pyfcstm.utils.validate.Span
    :return: Start and end character offsets, or ``None`` for an anchor-only
        span.
    :rtype: Optional[Tuple[int, int]]

    Examples::

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
    start = starts[span.line - 1] + span.column - 1
    end = starts[span.end_line - 1] + span.end_column - 1
    if start < 0 or end < start or end > len(text):
        return None
    return start, end


@dataclass(frozen=True)
class BmcSourceRef:
    """Stable reference to a FCSTM, FBMCQ, or generated source location.

    :param kind: Source kind: ``fcstm``, ``fbmcq``, or ``generated``.
    :type kind: str
    :param path: Display path, or ``None`` when no reliable path is available.
    :type path: Optional[str]
    :param span: One-based, end-exclusive source span, or ``None``.
    :type span: Optional[pyfcstm.utils.validate.Span]
    :raises ValueError: If the source kind or path is malformed.

    Examples::

        >>> BmcSourceRef("generated", None, None).kind
        'generated'
    """

    kind: str
    path: Optional[str]
    span: Optional[Span]

    def __post_init__(self) -> None:
        if self.kind not in _SOURCE_KINDS:
            raise ValueError("Unsupported BMC source kind: %r." % self.kind)
        if self.path is not None and (not isinstance(self.path, str) or not self.path):
            raise ValueError("BMC source path must be None or a non-empty string.")
        if self.span is not None and not isinstance(self.span, Span):
            raise TypeError("BMC source span must be Span or None.")

    def to_canonical(self) -> Dict[str, Any]:
        """Return a JSON-compatible source reference.

        :return: Canonical source reference dictionary.
        :rtype: Dict[str, object]

        Examples::

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
    :raises ValueError: If the identity or group is malformed.

    Examples::

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
        if not isinstance(self.stable_id, str) or not self.stable_id:
            raise ValueError("tracked constraint stable_id must be non-empty.")
        if not isinstance(self.stage, str) or not self.stage:
            raise ValueError("tracked constraint stage must be non-empty.")
        if not isinstance(self.category, str) or not self.category:
            raise ValueError("tracked constraint category must be non-empty.")
        expressions = tuple(self.expressions)
        if not expressions:
            raise ValueError("tracked constraint expressions must be non-empty.")
        if not isinstance(self.source_ref, BmcSourceRef):
            raise TypeError("tracked constraint source_ref must be BmcSourceRef.")
        object.__setattr__(self, "expressions", expressions)
        object.__setattr__(self, "refs", MappingProxyType(dict(self.refs)))


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

    Examples::

        >>> SourceDocumentRegistry({"a.fcstm": "state A;"}).document("a.fcstm")
        'state A;'
    """

    documents: Mapping[str, str]
    display_root: Optional[str] = None
    query_documents: Mapping[str, str] = field(
        default_factory=dict, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        copied = {}
        for path, text in dict(self.documents).items():
            if not isinstance(path, str) or not path:
                raise ValueError("source document paths must be non-empty strings.")
            if not isinstance(text, str):
                raise TypeError("source document text must be strings.")
            copied[path] = text
        object.__setattr__(self, "documents", MappingProxyType(copied))
        copied_queries = {}
        for path, text in dict(self.query_documents).items():
            if not isinstance(path, str) or not path:
                raise ValueError("query document paths must be non-empty strings.")
            if not isinstance(text, str):
                raise TypeError("query document text must be strings.")
            copied_queries[path] = text
        object.__setattr__(self, "query_documents", MappingProxyType(copied_queries))
        if self.display_root is not None:
            object.__setattr__(self, "display_root", os.path.abspath(self.display_root))

    def display_path(self, path: Optional[str]) -> Optional[str]:
        """Return a stable display path for an internal source path.

        :param path: Internal source path, or ``None``.
        :type path: Optional[str]
        :return: Relative display path when possible, otherwise original path.
        :rtype: Optional[str]

        Examples::

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

        Examples::

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

        Examples::

            >>> registry = SourceDocumentRegistry({"a.fcstm": ""})
            >>> registry.reference("fcstm", "a.fcstm", None).path
            'a.fcstm'
        """
        return BmcSourceRef(kind, self.display_path(path), span)

    def excerpt(self, reference: BmcSourceRef) -> Optional[str]:
        """Return the exact source slice described by a reference.

        :param reference: Source reference to resolve.
        :type reference: BmcSourceRef
        :return: Exact half-open source slice, or ``None`` when unavailable or
            when the span is anchor-only/invalid.
        :rtype: Optional[str]

        Examples::

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

        Examples::

            >>> SourceDocumentRegistry({}).model_reference(object()).kind
            'fcstm'
        """
        return self.reference(
            "fcstm",
            getattr(obj, "_source_path", None),
            getattr(obj, "_span", None),
        )

    def query_reference(self, query: object, obj: object) -> BmcSourceRef:
        """Build an FBMCQ reference from root-query private metadata.

        :param query: Root query carrying ``_source_path`` and ``_source_spans``.
        :type query: object
        :param obj: Query node whose identity is being resolved.
        :type obj: object
        :return: FBMCQ source reference, possibly without path/span.
        :rtype: BmcSourceRef

        Examples::

            >>> SourceDocumentRegistry({}).query_reference(object(), object()).kind
            'fbmcq'
        """
        spans = dict(getattr(query, "_source_spans", ()))
        return self.reference(
            "fbmcq", getattr(query, "_source_path", None), spans.get(id(obj))
        )


__all__ = [
    "BmcSourceRef",
    "BmcTrackedConstraint",
    "SourceDocumentRegistry",
]
