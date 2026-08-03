"""TDD contracts for BMC source provenance and tracked relation groups."""

from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent
from typing import Tuple

import hashlib

import pytest
import z3

import pyfcstm.bmc.provenance as provenance_module
from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.bmc import (
    BmcEngine,
    BmcPreparedContext,
    build_bmc_core_formula,
    compile_bmc_property,
    solve_bmc_property,
)
from pyfcstm.bmc.errors import BmcBuildError, InvalidBmcQuery
from pyfcstm.bmc.parse import parse_bmc_query
from pyfcstm.bmc.provenance import (
    BmcSourceRef,
    BmcTrackedConstraint,
    SourceDocumentRegistry,
)
from pyfcstm.bmc.relation import _append_tracked_group
from pyfcstm.model import (
    load_state_machine_from_file,
    load_state_machine_from_text,
    parse_dsl_node_to_state_machine,
)
from pyfcstm.utils.validate import Span

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize(
    ("kwargs", "exception", "message"),
    [
        pytest.param(
            {"kind": "unknown", "path": None, "span": None},
            ValueError,
            "source kind",
            id="source-kind",
        ),
        pytest.param(
            {"kind": "fcstm", "path": "", "span": None},
            ValueError,
            "source path",
            id="empty-path",
        ),
        pytest.param(
            {"kind": "fcstm", "path": None, "span": object()},
            TypeError,
            "source span",
            id="invalid-span-type",
        ),
        pytest.param(
            {"kind": "generated", "path": "query.fbmcq", "span": None},
            ValueError,
            "generated.*path or span",
            id="generated-path",
        ),
        pytest.param(
            {"kind": "generated", "path": None, "span": Span(1, 1, 1, 2)},
            ValueError,
            "generated.*path or span",
            id="generated-span",
        ),
        # A caller can pass the wrong type to a documented constructor, so the
        # kind and path gates are checked with a plain non-string value.
        pytest.param(
            {"kind": 123, "path": None, "span": None},
            ValueError,
            "source kind",
            id="kind-not-a-string",
        ),
        pytest.param(
            {"kind": "fcstm", "path": 123, "span": None},
            ValueError,
            "source path",
            id="path-not-a-string",
        ),
    ],
)
def test_source_reference_rejects_malformed_values(kwargs, exception, message) -> None:
    """Source references reject invalid kind, path, and span values."""
    with pytest.raises(exception, match=message):
        BmcSourceRef(**kwargs)


@pytest.mark.parametrize(
    ("reader", "value", "message"),
    [
        pytest.param("exact_str", 123, "must be a string", id="str-from-int"),
        pytest.param("exact_str", None, "must be a string", id="str-from-none"),
        pytest.param("exact_int", "3", "must be an integer", id="int-from-str"),
        pytest.param("exact_int", 1.5, "must be an integer", id="int-from-float"),
        pytest.param("exact_float", "1.5", "must be a number", id="float-from-str"),
        pytest.param("exact_float", None, "must be a number", id="float-from-none"),
        pytest.param("exact_index", "0", "must be an integer", id="index-from-str"),
        # A coordinate is a number, and ``True`` is not one a caller means.
        pytest.param("exact_index", True, "must be an integer", id="index-from-bool"),
        pytest.param(
            "exact_optional_index", "0", "must be an integer", id="optional-from-str"
        ),
    ],
)
def test_the_exact_readers_refuse_a_wrong_type(reader, value, message) -> None:
    """The exported readers are what a caller reaches for to normalize a value.

    They are in ``provenance.__all__``, so passing one the wrong type is an
    ordinary caller mistake rather than an exotic construction -- and the error
    has to name the field, since the reader is used from many call sites.
    """
    from pyfcstm.bmc import provenance

    with pytest.raises(TypeError, match=message):
        getattr(provenance, reader)(value, "field")


def test_the_exact_readers_return_the_value_a_caller_gave() -> None:
    """A well-formed value passes through unchanged, as an exact builtin.

    ``exact_index`` is deliberately typed rather than bounded: an out-of-range
    coordinate already degrades to an absent excerpt downstream, so it is checked
    for being an integer and nothing more.
    """
    from pyfcstm.bmc import provenance

    assert provenance.exact_str("kernel", "stage") == "kernel"
    assert provenance.exact_int(7, "count") == 7
    assert provenance.exact_float(1.5, "seconds") == 1.5
    assert provenance.exact_index(1, "line") == 1
    assert provenance.exact_optional_index(None, "end_line") is None
    # Documented as typed, not bounded.
    assert provenance.exact_index(-1, "line") == -1


def test_source_reference_canonicalizes_a_complete_span() -> None:
    """Canonical source references preserve all half-open span coordinates."""
    reference = BmcSourceRef("fcstm", "machine.fcstm", Span(2, 3, 4, 5))

    assert reference.to_canonical() == {
        "kind": "fcstm",
        "path": "machine.fcstm",
        "span": {"line": 2, "column": 3, "end_line": 4, "end_column": 5},
    }
    assert BmcSourceRef("generated", None, None).to_canonical() == {
        "kind": "generated",
        "path": None,
        "span": None,
    }


@pytest.mark.parametrize(
    ("field", "value", "exception", "message"),
    [
        pytest.param("stable_id", "", ValueError, "stable_id", id="stable-id"),
        pytest.param("stage", "", ValueError, "stage", id="stage"),
        pytest.param("category", "", ValueError, "category", id="category"),
        pytest.param("expressions", (), ValueError, "expressions", id="expressions"),
        pytest.param("source_ref", object(), TypeError, "source_ref", id="source-ref"),
        # The identity fields reject a plain non-string as well as an empty one:
        # a wrong type is what a caller passes, an impossible one is not.
        pytest.param("stable_id", 123, ValueError, "stable_id", id="stable-id-type"),
        pytest.param("stage", 123, ValueError, "stage", id="stage-type"),
        pytest.param("category", 123, ValueError, "category", id="category-type"),
    ],
)
def test_tracked_constraint_rejects_malformed_values(
    field, value, exception, message
) -> None:
    """Tracked constraints reject malformed identity and payload fields."""
    values = {
        "stable_id": "group",
        "stage": "kernel",
        # A pairing the builder really registers: the constructor now refuses a
        # stage and category combination it never emits, so a made-up pairing
        # would be rejected before the field under test is reached.
        "category": "domain.frame_state",
        "expressions": (z3.BoolVal(True),),
        "source_ref": BmcSourceRef("generated", None, None),
    }
    values[field] = value

    with pytest.raises(exception, match=message):
        BmcTrackedConstraint(**values)


@pytest.mark.parametrize(
    ("expressions", "message"),
    [
        pytest.param((), "non-empty", id="empty"),
        pytest.param((z3.IntVal(1),), "Boolean", id="non-boolean"),
    ],
)
def test_tracked_group_registration_rejects_invalid_expressions(
    expressions, message
) -> None:
    """The relation-side registration guard rejects malformed Z3 inputs."""
    groups = []

    with pytest.raises(BmcBuildError, match=message):
        _append_tracked_group(
            groups,
            stable_id="invalid",
            stage="kernel",
            category="domain",
            expressions=expressions,
            source_ref=BmcSourceRef("generated", None, None),
        )


@pytest.mark.parametrize(
    ("kwargs", "exception", "message"),
    [
        pytest.param(
            {"documents": {1: "text"}},
            ValueError,
            "document paths",
            id="document-path",
        ),
        pytest.param(
            {"documents": {"machine.fcstm": object()}},
            TypeError,
            "document text",
            id="document-text",
        ),
        pytest.param(
            {"documents": {}, "query_documents": {"": "query"}},
            ValueError,
            "query document paths",
            id="query-path",
        ),
        pytest.param(
            {"documents": {}, "query_documents": {"query.fbmcq": object()}},
            TypeError,
            "query document text",
            id="query-text",
        ),
    ],
)
def test_source_registry_rejects_malformed_documents(
    kwargs, exception, message
) -> None:
    """Document snapshots require non-empty paths and string contents."""
    with pytest.raises(exception, match=message):
        SourceDocumentRegistry(**kwargs)


@pytest.mark.parametrize(
    "span",
    [
        pytest.param(Span(1, 1), id="anchor-only"),
        pytest.param(Span(0, 1, 1, 2), id="invalid-start-line"),
        pytest.param(Span(1, 1, 2, 1), id="invalid-end-line"),
        pytest.param(Span(1, 3, 1, 2), id="end-before-start"),
        pytest.param(Span(1, 1, 1, 5), id="end-after-document"),
    ],
)
def test_source_registry_returns_none_for_unusable_spans(span) -> None:
    """Invalid and anchor-only spans never produce misleading excerpts."""
    registry = SourceDocumentRegistry({"machine.fcstm": "abc"})
    reference = BmcSourceRef("fcstm", "machine.fcstm", span)

    assert registry.excerpt(reference) is None


@pytest.mark.parametrize(
    "span",
    [
        pytest.param(Span(1, 5, 1, 6), id="start-column-past-line"),
        pytest.param(Span(2, 5, 2, 6), id="end-column-past-line"),
        pytest.param(Span(1, 1, 2, 5), id="cross-line-end-column-past-line"),
    ],
)
def test_source_registry_rejects_columns_outside_their_line(
    span: Span,
) -> None:
    """A column cannot borrow characters from an adjacent source line."""
    registry = SourceDocumentRegistry({"machine.fcstm": "abc\ndef"})

    reference = registry.reference("fcstm", "machine.fcstm", span)

    assert reference.span is None
    assert registry.excerpt(reference) is None


def test_source_registry_handles_aliases_and_unknown_namespaces(tmp_path: Path) -> None:
    """Document lookup resolves display aliases without crossing namespaces."""
    source_path = tmp_path / "nested" / "machine.fcstm"
    registry = SourceDocumentRegistry(
        {str(source_path): "state Root;"}, display_root=str(tmp_path)
    )

    display_path = os.path.relpath(str(source_path), str(tmp_path))
    assert registry.document(display_path) == "state Root;"
    assert registry.document(None) is None
    assert registry.document("nested/machine.fcstm", kind="unknown") is None


def test_source_registry_preserves_path_when_relative_path_is_unavailable(
    tmp_path: Path, monkeypatch
) -> None:
    """Unrelativizable paths retain the caller path, as on different Windows drives."""
    registry = SourceDocumentRegistry(
        {str(tmp_path / "machine.fcstm"): "state Root;"},
        display_root=str(tmp_path),
    )

    def fail_relpath(path, start):
        raise ValueError("paths use different drives")

    monkeypatch.setattr(provenance_module.os.path, "relpath", fail_relpath)

    path = str(tmp_path / "machine.fcstm")
    assert registry.display_path(path) == path


def test_source_registry_returns_none_for_missing_excerpt_document() -> None:
    """A direct reference cannot produce an excerpt without a source snapshot."""
    registry = SourceDocumentRegistry({"machine.fcstm": "state Root;"})
    reference = BmcSourceRef("fcstm", "missing.fcstm", Span(1, 1, 1, 5))

    assert registry.excerpt(reference) is None


def test_source_registry_clears_known_document_spans_that_cannot_be_sliced() -> None:
    """Known documents do not advertise an invalid source span as precise."""
    registry = SourceDocumentRegistry({"machine.fcstm": "state Root;"})

    reference = registry.reference("fcstm", "machine.fcstm", Span(99, 1, 99, 2))

    assert reference.span is None
    assert registry.excerpt(reference) is None


def test_source_registry_slices_multiline_span_exactly() -> None:
    """A source excerpt must be the exact half-open span slice."""
    source = "line one\n第二行内容\nline three"
    registry = SourceDocumentRegistry({"machine.fcstm": source})
    reference = BmcSourceRef(
        kind="fcstm",
        path="machine.fcstm",
        span=Span(line=1, column=6, end_line=2, end_column=4),
    )

    assert registry.excerpt(reference) == "one\n第二行"


def test_source_registry_handles_crlf_line_boundaries() -> None:
    """CRLF separators do not become part of a same-line excerpt."""
    registry = SourceDocumentRegistry({"machine.fcstm": "abc\r\ndef"})
    reference = registry.reference("fcstm", "machine.fcstm", Span(1, 1, 1, 4))

    assert registry.excerpt(reference) == "abc"


def test_query_source_metadata_keeps_source_text_canonical_clean() -> None:
    """Query spans are available privately without changing canonical JSON."""
    text = 'init cold;\nassume at 0: var("x") == 1;\ncheck reach <= 1: true;'
    query = parse_bmc_query(text, source_path="query.fbmcq")

    assert query._source_path == "query.fbmcq"
    assert query._source_spans
    assert query.to_canonical() == {
        "node": "bmc_query",
        "initial": query.initial.to_canonical(),
        "assumptions": [item.to_canonical() for item in query.assumptions],
        "property": query.property.to_canonical(),
    }


def test_query_source_metadata_keeps_root_query_span_after_replace() -> None:
    """The returned immutable query root retains its own source span."""
    text = 'check reach <= 1: active("Root");'
    query = parse_bmc_query(text, source_path="query.fbmcq")
    registry = SourceDocumentRegistry({}, query_documents={"query.fbmcq": text})

    reference = registry.query_reference(query, query)

    assert reference.span is not None
    assert registry.excerpt(reference) == text


def test_query_source_path_rejects_empty_public_path() -> None:
    """The parser reports an unusable explicit source path."""
    with pytest.raises(InvalidBmcQuery, match="_source_path"):
        parse_bmc_query('check reach <= 1: active("Root");', source_path="")


def test_pathless_source_references_drop_unresolvable_spans() -> None:
    """Pathless FCSTM and FBMCQ metadata cannot retain misleading spans."""
    model = load_state_machine_from_text("def int x = 3;\nstate Root;")
    context = BmcEngine(model).prepare(
        'assume at 0: true;\ncheck reach <= 1: active("Root");',
        query_source_path=None,
    )
    core = build_bmc_core_formula(context)

    variable = next(
        group
        for group in core._tracked_groups
        if group.stable_id == "initial.variable.x"
    )
    assumption = next(
        group
        for group in core._tracked_groups
        if group.stable_id == "assumption.0000.frame.0000"
    )

    assert variable.source_ref.kind == "fcstm"
    assert variable.source_ref.path is None
    assert variable.source_ref.span is None
    assert context._source_registry.excerpt(variable.source_ref) is None
    assert assumption.source_ref.kind == "fbmcq"
    assert assumption.source_ref.path is None
    assert assumption.source_ref.span is None
    assert context._source_registry.excerpt(assumption.source_ref) is None
    assert variable.stable_id == "initial.variable.x"
    assert assumption.category == "assumption.frame"


def test_source_reference_drops_span_without_document_snapshot() -> None:
    """A path without a registered snapshot cannot support an exact span."""
    registry = SourceDocumentRegistry({})
    reference = registry.reference("fcstm", "missing.fcstm", Span(1, 1, 1, 8))

    assert reference.path == "missing.fcstm"
    assert reference.span is None
    assert registry.excerpt(reference) is None


def test_file_and_import_source_paths_are_not_collapsed(
    tmp_path: Path, text_aligner
) -> None:
    """Imported model spans must retain the imported document path."""
    imported = tmp_path / "worker.fcstm"
    imported.write_text("state Worker;", encoding="utf-8")
    main = tmp_path / "main.fcstm"
    main.write_text(
        'state Root { import "./worker.fcstm" as Worker; [*] -> Worker; }',
        encoding="utf-8",
    )

    model = load_state_machine_from_file(main)
    worker = model.root_state.substates["Worker"]

    assert worker._source_path == str(imported.resolve())
    # Through the aligner rather than ``==``: the loader keeps a file's own line
    # endings, while ``read_text`` applies universal newlines and turns CRLF into
    # LF.  On Linux both readings agree and a byte comparison passes; on Windows
    # they never agree, and the failure would be about newline handling rather
    # than about which document a path maps to, which is what this test is for.
    text_aligner.assert_equal(
        main.read_text(encoding="utf-8"),
        model._source_documents[str(main.resolve())],
    )
    text_aligner.assert_equal(
        imported.read_text(encoding="utf-8"),
        model._source_documents[str(imported.resolve())],
    )


def test_imported_lifecycle_operations_keep_source_paths_and_excerpts(
    tmp_path: Path,
) -> None:
    """Lifecycle operations and nested branches retain imported provenance."""
    imported = tmp_path / "worker.fcstm"
    imported.write_text(
        """def int x = 0;
state Worker {
    event Tick;
    enter { if [x > 0] { x = x + 1; } else { x = x + 2; } }
    during before Tick { x = x + 3; }
    exit { x = x + 4; }
    >> during after Monitor { x = x + 5; }
    state Idle;
    [*] -> Idle;
}
""",
        encoding="utf-8",
    )
    main = tmp_path / "main.fcstm"
    main.write_text(
        'state Root { import "./worker.fcstm" as Worker; [*] -> Worker; }\n',
        encoding="utf-8",
    )

    model = load_state_machine_from_file(main)
    worker = model.root_state.substates["Worker"]
    registry = SourceDocumentRegistry(
        model._source_documents, display_root=model._source_root
    )

    actions = (
        worker.on_enters[0],
        worker.on_durings[0],
        worker.on_exits[0],
        worker.on_during_aspects[0],
    )
    for action in actions:
        assert action._source_path == str(imported.resolve())
        operation = action.operations[0]
        assert operation._source_path == str(imported.resolve())
        assert registry.model_reference(operation).path == "worker.fcstm"

    enter_if = worker.on_enters[0].operations[0]
    assert enter_if._source_path == str(imported.resolve())
    assert [
        registry.excerpt(registry.model_reference(branch.statements[0]))
        for branch in enter_if.branches
    ] == ["x = x + 1;", "x = x + 2;"]

    assert [
        registry.excerpt(registry.model_reference(action.operations[0]))
        for action in actions[1:]
    ] == ["x = x + 3;", "x = x + 4;", "x = x + 5;"]


def test_imported_top_level_definition_keeps_bmc_source_ownership(
    tmp_path: Path,
) -> None:
    """Imported definitions retain their source file in compiled BMC groups."""
    imported = tmp_path / "child.fcstm"
    imported.write_text("def int x = 5;\nstate Worker;\n", encoding="utf-8")
    main = tmp_path / "main.fcstm"
    main.write_text(
        'state Root { import "./child.fcstm" as Child; [*] -> Child; }\n',
        encoding="utf-8",
    )

    model = load_state_machine_from_file(main)
    context = BmcEngine(model).prepare("check reach <= 1: true;")
    core = build_bmc_core_formula(context)
    group = next(
        item
        for item in core._tracked_groups
        if item.stable_id == "initial.variable.Child_x"
    )

    assert group.source_ref.kind == "fcstm"
    assert group.source_ref.path == "child.fcstm"
    assert context._source_registry.excerpt(group.source_ref) == "def int x = 5;"


def test_transition_effect_provenance_keeps_model_source_ownership(
    tmp_path: Path,
) -> None:
    """Transition and effect metadata retain exact FCSTM source excerpts."""
    source_path = tmp_path / "machine.fcstm"
    source = """def int x = 0;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B effect {
        x = x + 1;
    }
}
"""
    source_path.write_bytes(source.encode("utf-8"))

    model = load_state_machine_from_file(source_path)
    transition = next(
        item for item in model.root_state.transitions if item.from_state == "A"
    )
    effect = transition.effects[0]
    registry = SourceDocumentRegistry(
        model._source_documents, display_root=model._source_root
    )

    assert transition._source_path == str(source_path.resolve())
    assert effect._source_path == str(source_path.resolve())
    expected_transition = "\n".join(("A -> B effect {", "        x = x + 1;", "    }"))
    assert registry.excerpt(registry.model_reference(transition)) == expected_transition
    assert registry.excerpt(registry.model_reference(effect)) == "x = x + 1;"


def test_transition_case_group_keeps_exact_public_transition_excerpt(
    tmp_path: Path,
) -> None:
    """A lowered transition case points back to its authored transition."""
    source_path = tmp_path / "machine.fcstm"
    source = """def int x = 0;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B : if [x == 0] effect { x = x + 1; }
}
"""
    source_path.write_text(source, encoding="utf-8")

    model = load_state_machine_from_file(source_path)
    context = BmcEngine(model).prepare(
        'init state("Root.A"); check reach <= 1: active("Root.B");',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    group = next(
        item
        for item in core._tracked_case_groups
        if item.category == "transition.case" and item.refs["transition_labels"]
    )

    assert group.source_ref.kind == "fcstm"
    assert group.source_ref.path == "machine.fcstm"
    assert context._source_registry.excerpt(group.source_ref) == (
        "A -> B : if [x == 0] effect { x = x + 1; }"
    )
    assert group.refs["case_label"].startswith("Root.A::transition::")
    assert isinstance(group.refs["transition_labels"], tuple)
    with pytest.raises(AttributeError):
        getattr(group.refs["transition_labels"], "append")("forged")


def test_event_only_transition_case_uses_unique_event_source_excerpt(
    tmp_path: Path,
) -> None:
    """A uniquely matched event-only case keeps its FCSTM ownership."""
    source_path = tmp_path / "machine.fcstm"
    source = """state Root {
    event Go;
    state A;
    state B;
    [*] -> A;
    A -> B :: Go;
}
"""
    source_path.write_text(source, encoding="utf-8")

    model = load_state_machine_from_file(source_path)
    context = BmcEngine(model).prepare(
        'init state("Root.A"); check reach <= 1: active("Root.B");',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    group = next(
        item
        for item in core._tracked_case_groups
        if item.category == "transition.case"
        and item.refs.get("source_inference") == "unique_event"
    )

    assert group.source_ref.kind == "fcstm"
    assert group.source_ref.path == "machine.fcstm"
    assert context._source_registry.excerpt(group.source_ref) == "A -> B :: Go;"


def test_plain_transition_case_uses_unique_model_transition_excerpt(
    tmp_path: Path,
) -> None:
    """A plain transition without guard/effect remains source-locatable."""
    source_path = tmp_path / "machine.fcstm"
    source = """state Root {
    state A;
    state B;
    [*] -> A;
    A -> B;
}
"""
    source_path.write_bytes(source.encode("utf-8"))

    model = load_state_machine_from_file(source_path)
    context = BmcEngine(model).prepare(
        'init state("Root.A"); check reach <= 1: active("Root.B");',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    group = next(
        item
        for item in core._tracked_case_groups
        if item.refs.get("source_inference") == "unique_transition"
    )

    assert context._source_registry.excerpt(group.source_ref) == "A -> B;"


def test_nested_composite_transition_cases_keep_authored_source_excerpts(
    tmp_path: Path,
) -> None:
    """Plain, event, and combo edges to a composite retain FCSTM ownership."""
    source_path = tmp_path / "machine.fcstm"
    source = """state Root {
    event Go;
    event E1;
    event E2;
    state A;
    state B {
        state Deep;
        [*] -> Deep;
    }
    [*] -> A;
    A -> B;
    A -> B :: Go;
    A -> B :: E1 + E2;
}
"""
    source_path.write_text(source, encoding="utf-8")

    model = load_state_machine_from_file(source_path)
    context = BmcEngine(model).prepare(
        'init state("Root.A"); check reach <= 2: active("Root.B.Deep");',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)

    excerpts_by_inference = {
        item.refs["source_inference"]: context._source_registry.excerpt(item.source_ref)
        for item in core._tracked_case_groups
        if item.refs.get("source_inference") is not None
    }

    assert excerpts_by_inference == {
        "unique_transition": "A -> B;",
        "unique_event": "A -> B :: Go;",
        "unique_combo": "A -> B :: E1 + E2;",
    }


def test_parent_event_only_case_uses_unique_parent_transition_excerpt(
    tmp_path: Path,
) -> None:
    """An event-only parent continuation searches its owner prefixes."""
    source_path = tmp_path / "machine.fcstm"
    source = """state Root {
    event Go;
    state Outer {
        state A;
        [*] -> A;
        A -> [*];
    }
    state Sink;
    [*] -> Outer;
    Outer -> Sink :: Go;
}
"""
    source_path.write_bytes(source.encode("utf-8"))

    model = load_state_machine_from_file(source_path)
    context = BmcEngine(model).prepare(
        'check reach <= 3: active("Root.Sink");',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    groups = [
        item
        for item in core._tracked_case_groups
        if item.refs.get("source_inference") == "unique_event"
    ]

    assert groups
    assert {context._source_registry.excerpt(item.source_ref) for item in groups} == {
        "Outer -> Sink :: Go;"
    }


def test_plain_initial_case_uses_unique_initial_transition_excerpt(
    tmp_path: Path,
) -> None:
    """A single direct initial transition remains source-locatable."""
    source_path = tmp_path / "machine.fcstm"
    source = """state Root {
    state A;
    [*] -> A;
}
"""
    source_path.write_bytes(source.encode("utf-8"))

    model = load_state_machine_from_file(source_path)
    context = BmcEngine(model).prepare(
        'check reach <= 1: active("Root.A");',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    group = next(
        item
        for item in core._tracked_case_groups
        if item.refs.get("source_inference") == "unique_initial"
    )

    assert context._source_registry.excerpt(group.source_ref) == "[*] -> A;"


def test_combo_transition_case_uses_unique_original_source_excerpt(
    tmp_path: Path,
) -> None:
    """A unique combo chain points back to its authored transition span."""
    source_path = tmp_path / "machine.fcstm"
    source = """state Root {
    event E1;
    event E2;
    state A;
    state B;
    [*] -> A;
    A -> B :: E1 + E2;
}
"""
    source_path.write_bytes(source.encode("utf-8"))

    model = load_state_machine_from_file(source_path)
    context = BmcEngine(model).prepare(
        'init state("Root.A"); '
        'assume event("Root.E1", 0) == true; '
        'assume event("Root.E2", 1) == true; '
        'check reach <= 2: active("Root.B");',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    groups = [
        item
        for item in core._tracked_case_groups
        if item.refs.get("case_label") == "Root.A::transition::Root.B::0"
        and item.refs.get("source_inference") == "unique_combo"
    ]

    assert groups
    assert {context._source_registry.excerpt(item.source_ref) for item in groups} == {
        "A -> B :: E1 + E2;"
    }


def test_imported_combo_case_uses_original_source_excerpt(tmp_path: Path) -> None:
    """An imported combo chain keeps its child-file source ownership."""
    imported = tmp_path / "worker.fcstm"
    imported.write_text(
        """def int w = 1;
state WorkerRoot {
    state Outer {
        state Idle;
        state Done;
        [*] -> Idle;
        Idle -> Done :: Start + [w == 1] + Finish effect {
            w = w + 1;
        }
    }
    [*] -> Outer;
}
""",
        encoding="utf-8",
    )
    main = tmp_path / "main.fcstm"
    main.write_text(
        """state Root {
    state Host {
        import "./worker.fcstm" as Worker { def w -> w; };
        [*] -> Worker;
    }
    [*] -> Host;
}
""",
        encoding="utf-8",
    )

    model = load_state_machine_from_file(main)
    context = BmcEngine(model).prepare(
        'init state("Root.Host.Worker.Outer.Idle") where w == 1; '
        'assume event("Root.Host.Worker.Outer.Idle.Start", 0) == true; '
        'assume event("Root.Host.Worker.Outer.Idle.Finish", 1) == true; '
        'check reach <= 3: active("Root.Host.Worker.Outer.Done");',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    groups = [
        item
        for item in core._tracked_case_groups
        if item.refs.get("case_label")
        == "Root.Host.Worker.Outer.Idle::transition::Root.Host.Worker.Outer.Done::0"
        and item.refs.get("source_inference") == "unique_combo"
    ]

    assert groups
    assert {item.source_ref.path for item in groups} == {"worker.fcstm"}
    assert {context._source_registry.excerpt(item.source_ref) for item in groups} == {
        "Idle -> Done :: Start + [w == 1] + Finish effect {\n"
        "            w = w + 1;\n"
        "        }"
    }


def test_imported_combo_event_mapping_controls_bmc_witness(tmp_path: Path) -> None:
    """Mapped combo events must control normal BMC reachability semantics."""
    imported = tmp_path / "worker.fcstm"
    imported.write_text(
        """state WorkerRoot {
    event Start;
    event Finish;
    state Idle;
    state Done;
    [*] -> Idle;
    Idle -> Done : Start + Finish;
}
""",
        encoding="utf-8",
    )
    main = tmp_path / "main.fcstm"
    main.write_text(
        """state Root {
    event HostStart;
    event HostFinish;
    import "./worker.fcstm" as Worker {
        event /Start -> HostStart;
        event /Finish -> HostFinish;
    };
    [*] -> Worker;
}
""",
        encoding="utf-8",
    )

    model = load_state_machine_from_file(main)
    context = BmcEngine(model).prepare(
        'init state("Root.Worker.Idle"); '
        'assume event("Root.HostStart", 0) == true; '
        'assume event("Root.HostFinish", 0..1) == false; '
        'check reach <= 2: active("Root.Worker.Done");',
        query_source_path="query.fbmcq",
    )
    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        timeout_ms=None,
    )

    assert result.status == "unsat"
    assert result.outcome == "no_witness"
    assert result.property_satisfied is False
    assert result.witness_found is False


def test_guarded_combo_transition_case_uses_authored_source_excerpt(
    tmp_path: Path,
) -> None:
    """Generated guard edges retain the authored combo transition source."""
    source_path = tmp_path / "guarded_combo.fcstm"
    source = """def int ready = 1;
state Root {
    event E1;
    event E2;
    state A;
    state B;
    [*] -> A;
    A -> B :: E1 + [ready > 0] + E2;
}
"""
    source_path.write_bytes(source.encode("utf-8"))

    model = load_state_machine_from_file(source_path)
    context = BmcEngine(model).prepare(
        'init state("Root.A") where ready == 1; '
        'assume event("Root.A.E1", 0) == true; '
        'assume event("Root.A.E2", 2) == true; '
        'check reach <= 3: active("Root.B");',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    groups = [
        item
        for item in core._tracked_case_groups
        if item.refs.get("case_kind") == "transition"
    ]

    assert groups
    assert {item.source_ref.kind for item in groups} == {"fcstm"}
    assert {context._source_registry.excerpt(item.source_ref) for item in groups} == {
        "A -> B :: E1 + [ready > 0] + E2;"
    }


def test_programmatic_combo_does_not_claim_source_inference() -> None:
    """A source-less model keeps generated provenance without false inference."""
    model = load_state_machine_from_text(
        """state Root {
    event E1;
    event E2;
    state A;
    state B;
    [*] -> A;
    A -> B :: E1 + E2;
}
"""
    )
    context = BmcEngine(model).prepare(
        'init state("Root.A"); '
        'assume event("Root.A.E1", 0) == true; '
        'assume event("Root.A.E2", 1) == true; '
        'check reach <= 2: active("Root.B");'
    )
    core = build_bmc_core_formula(context)

    assert all(
        item.refs.get("source_inference") is None
        for item in core._tracked_case_groups
        if item.source_ref.kind == "generated"
    )


def test_parent_continuation_transition_uses_normal_transition_index(
    tmp_path: Path,
) -> None:
    """A parent continuation index must not select an initial transition."""
    source_path = tmp_path / "machine.fcstm"
    source = """def int x = 0;
state Root {
    state Outer {
        state A;
        [*] -> A;
        A -> [*];
    }
    state Sink;
    [*] -> Outer;
    Outer -> Sink : if [x == 0];
}
"""
    source_path.write_text(source, encoding="utf-8")

    model = load_state_machine_from_file(source_path)
    context = BmcEngine(model).prepare(
        'check reach <= 3: active("Root.Sink");',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    groups = [
        item
        for item in core._tracked_case_groups
        if dict(item.refs).get("transition_labels") == ("Root.Outer::0::Outer->Sink",)
    ]

    assert groups
    assert {context._source_registry.excerpt(item.source_ref) for item in groups} == {
        "Outer -> Sink : if [x == 0];"
    }


def test_forced_transition_expansions_share_source_provenance(tmp_path: Path) -> None:
    """Every model transition expanded from one forced source remains locatable."""
    source_path = tmp_path / "machine.fcstm"
    source = """state Root {
    state A;
    state B;
    state C;
    [*] -> A;
    !* -> C :: Go;
}
"""
    source_path.write_text(source, encoding="utf-8")

    model = load_state_machine_from_file(source_path)
    forced = [
        transition
        for transition in model.root_state.transitions
        if transition.is_forced
    ]
    registry = SourceDocumentRegistry(
        model._source_documents, display_root=model._source_root
    )

    assert len(forced) == 3
    assert {transition._source_path for transition in forced} == {
        str(source_path.resolve())
    }
    assert {
        registry.excerpt(registry.model_reference(transition)) for transition in forced
    } == {"!* -> C :: Go;"}


def test_direct_prepared_context_preserves_query_source_in_groups() -> None:
    """Direct public context construction keeps path and excerpt metadata aligned."""
    query_text = 'init state("Root") where true;\ncheck reach <= 1: active("Root");'
    model = load_state_machine_from_text("state Root;")
    parsed = parse_bmc_query(query_text, source_path="old.fbmcq")
    prepared = BmcEngine(model).prepare(parsed)

    context = BmcPreparedContext(
        model=prepared.model,
        query=prepared.query,
        bound_query=prepared.bound_query,
        domain=prepared.domain,
        options=prepared.options,
        source_text=query_text,
        query_source_path="new.fbmcq",
    )
    core = build_bmc_core_formula(context)
    target = next(
        group for group in core._tracked_groups if group.stable_id == "initial.target"
    )

    assert context.query_source_path == "new.fbmcq"
    assert context.query._source_path == "new.fbmcq"
    assert target.source_ref.path == "new.fbmcq"
    assert context._source_registry.excerpt(target.source_ref) == (
        'init state("Root") where true;'
    )


def test_public_model_loading_preserves_event_scope_origins() -> None:
    """Public model loading keeps local, chain, and absolute event origins."""
    model = load_state_machine_from_text(
        dedent(
            """
            state Root {
                event Global;
                state System {
                    event Parent;
                    state A {
                        event Local;
                    }
                    state B;
                    [*] -> A;
                    A -> B :: Local;
                    A -> B : Parent;
                    A -> B : /Global;
                }
                [*] -> System;
            }
            """
        )
    )

    system = model.root_state.substates["System"]
    transitions = {
        transition.event.name: transition
        for transition in system.transitions
        if transition.event is not None
    }

    assert transitions["Local"].event_scope == "local"
    assert transitions["Parent"].event_scope == "chain"
    assert transitions["Global"].event_scope == "absolute"


def test_programmatic_event_metadata_fallback_infers_scope_origins() -> None:
    """Public AST inputs without explicit event scopes use structural inference."""
    program = parse_with_grammar_entry(
        dedent(
            """
            state Root {
                event Global;
                state System {
                    event Parent;
                    state A {
                        event Local;
                    }
                    state B;
                    [*] -> A;
                    A -> B :: Local;
                    A -> B : Parent;
                    A -> B : /Global;
                }
                [*] -> System;
            }
            """
        ),
        entry_name="state_machine_dsl",
    )
    ast_system = program.root_state.substates[0]
    ast_transitions = {
        item.event_id.path[-1]: item
        for item in ast_system.transitions
        if item.event_id is not None
    }
    for transition in ast_transitions.values():
        transition.event_scope = None

    model = parse_dsl_node_to_state_machine(program)
    system = model.root_state.substates["System"]
    transitions = {
        transition.event.name: transition
        for transition in system.transitions
        if transition.event is not None
    }

    assert {name: item.event_scope for name, item in transitions.items()} == {
        "Local": "local",
        "Parent": "chain",
        "Global": "absolute",
    }


def test_initializer_definedness_provenance_uses_definition_source(
    tmp_path: Path,
) -> None:
    """Initializer definedness groups point to the defining FCSTM statement."""
    source_path = tmp_path / "machine.fcstm"
    source = "def int x = 1 / 0;\nstate Root;\n"
    source_path.write_text(source, encoding="utf-8")

    model = load_state_machine_from_file(source_path)
    context = BmcEngine(model).prepare(
        'check reach <= 1: active("Root");', query_source_path="query.fbmcq"
    )
    core = build_bmc_core_formula(context)
    group = next(
        item
        for item in core._tracked_groups
        if item.stable_id == "initial.variable.x.definedness.0000"
    )

    assert group.source_ref.kind == "fcstm"
    assert group.source_ref.path == "machine.fcstm"
    assert context._source_registry.excerpt(group.source_ref) == "def int x = 1 / 0;"


def test_environment_group_provenance_covers_frame_event_and_cardinality() -> None:
    """Environment groups retain exact FBMCQ excerpts for each assumption kind."""
    model = load_state_machine_from_text(
        """
        def int x = 1;
        state Root {
            event Tick;
        }
        """
    )
    query_text = (
        "assume always: x / 0 > 0;\n"
        'assume event("Root.Tick", 0) == true;\n'
        'assume events cardinality at_most_one { "Root.Tick" };\n'
        'check reach <= 1: active("Root");'
    )
    context = BmcEngine(model).prepare(query_text, query_source_path="query.fbmcq")
    core = build_bmc_core_formula(context)

    excerpts_by_category = {}
    for group in core._tracked_groups:
        if group.stage == "assumptions":
            excerpts_by_category.setdefault(group.category, set()).add(
                context._source_registry.excerpt(group.source_ref)
            )

    assert excerpts_by_category["definedness"] == {"assume always: x / 0 > 0;"}
    assert excerpts_by_category["assumption.frame"] == {"assume always: x / 0 > 0;"}
    assert excerpts_by_category["assumption.event"] == {
        'assume event("Root.Tick", 0) == true;'
    }
    assert excerpts_by_category["assumption.cardinality"] == {
        'assume events cardinality at_most_one { "Root.Tick" };'
    }


@pytest.mark.parametrize(
    "assumption_text",
    [
        "assume always: x / 0 > 0;",
        "assume at 0: x / 0 > 0;",
    ],
)
def test_frame_assumption_provenance_keeps_exact_query_excerpt(
    assumption_text: str,
) -> None:
    """Both frame-assumption forms use the complete source statement."""
    model = load_state_machine_from_text("def int x = 1;\nstate Root;")
    query_text = assumption_text + '\ncheck reach <= 1: active("Root");'
    context = BmcEngine(model).prepare(query_text, query_source_path="query.fbmcq")
    core = build_bmc_core_formula(context)

    frame_groups = [
        item for item in core._tracked_groups if item.category == "assumption.frame"
    ]

    assert frame_groups
    assert {
        context._source_registry.excerpt(item.source_ref) for item in frame_groups
    } == {assumption_text}


def test_programmatic_ast_without_spans_fails_closed_for_operation_metadata() -> None:
    """Programmatic AST input does not receive fabricated operation paths."""
    program = dsl_nodes.StateMachineDSLProgram(
        definitions=[dsl_nodes.DefAssignment("x", "int", dsl_nodes.Integer("0"))],
        root_state=dsl_nodes.StateDefinition(
            "Root",
            enters=[
                dsl_nodes.EnterOperations(
                    [dsl_nodes.OperationAssignment("x", dsl_nodes.Integer("1"))]
                )
            ],
        ),
    )

    model = parse_dsl_node_to_state_machine(program)

    operation = model.root_state.on_enters[0].operations[0]
    assert getattr(operation, "_source_path", None) is None


def test_text_loader_records_snapshot_when_path_is_an_existing_file(
    tmp_path: Path,
) -> None:
    """Text loading records a snapshot when its path names a real file."""
    source_path = tmp_path / "machine.fcstm"
    source = "state Root;"
    source_path.write_text(source, encoding="utf-8")

    model = load_state_machine_from_text(source, path=source_path)

    assert model._source_documents[str(source_path.resolve())] == source


def test_text_loader_records_snapshot_for_virtual_file_path(tmp_path: Path) -> None:
    """Text loading keeps provenance when the file path is not on disk."""
    source_path = tmp_path / "virtual.fcstm"
    source = "def int x = 7;\nstate Root;\n"

    model = load_state_machine_from_text(source, path=source_path)
    context = BmcEngine(model).prepare(
        'check reach <= 1: active("Root") and x == 7;',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    group = next(
        item for item in core._tracked_groups if item.stable_id == "initial.variable.x"
    )

    assert source_path.exists() is False
    assert model._source_documents[str(source_path.resolve())] == source
    assert context._source_registry.excerpt(group.source_ref) == "def int x = 7;"


def _conjoin(expressions):
    values = tuple(expressions)
    if not values:
        return z3.BoolVal(True)
    if len(values) == 1:
        return values[0]
    return z3.And(*values)


def test_tracked_groups_rebuild_each_aggregate_in_registration_order() -> None:
    """Tracked groups preserve every aggregate formula's old expression shape."""
    model = load_state_machine_from_text("state Root { state A; [*] -> A; }")
    context = BmcEngine(model).prepare(
        'assume always: cycle <= 2; check reach <= 2: active("Root.A");'
    )
    core = build_bmc_core_formula(context)
    groups = core._tracked_groups

    assert len({item.stable_id for item in groups}) == len(groups)
    assert all(item.expressions for item in groups)
    assert all(
        z3.is_bool(expression) for item in groups for expression in item.expressions
    )

    assert str(
        _conjoin(
            expression
            for item in groups
            if item.category == "domain.frame_state"
            for expression in item.expressions
        )
    ) == str(core.domain_formula)
    assert str(
        _conjoin(
            expression
            for item in groups
            if item.stage == "initialization"
            for expression in item.expressions
        )
    ) == str(core.initial_formula)
    assert str(
        _conjoin(
            expression
            for item in groups
            if item.category == "transition.step"
            for expression in item.expressions
        )
    ) == str(core.transition_formula)
    assert str(
        _conjoin(
            expression
            for item in groups
            if item.stage == "assumptions"
            for expression in item.expressions
        )
    ) == str(core.environment_formula)


def test_initial_where_definedness_is_tracked_with_the_source_predicate() -> None:
    """Initial predicate definedness constraints retain their source group."""
    model = load_state_machine_from_text("def int x = 1; def int y = 0; state Root;")
    query_text = 'init cold where x / y > 0;\ncheck reach <= 1: active("Root");'
    context = BmcEngine(model).prepare(query_text, query_source_path="query.fbmcq")
    core = build_bmc_core_formula(context)

    definedness = next(
        group
        for group in core._tracked_groups
        if group.stable_id == "initial.where.definedness.0000"
    )

    assert definedness.category == "definedness"
    assert definedness.source_ref.kind == "fbmcq"
    assert context._source_registry.excerpt(definedness.source_ref) == ("x / y > 0")
    assert len(definedness.expressions) == 1
    assert "F_0_y" in str(definedness.expressions[0])


def test_core_formula_validates_all_generated_group_owners() -> None:
    """Real FCSTM/FBMCQ inputs exercise every ordinary ledger owner kind."""
    model = load_state_machine_from_text(
        """def int x = 1 / 0;
def int y = 1;
state Root {
    event Go;
    state A;
    [*] -> A;
}
"""
    )
    query = """init cold where x / y > 0;
assume always: x / 0 > 0;
assume at 1: x / 0 > 0;
assume event("Root.Go", 0..1) == true;
assume events cardinality at_most_one {"Root.Go"};
check reach <= 2: active("Root.A");
"""

    core = build_bmc_core_formula(BmcEngine(model).prepare(query))
    categories = {group.category for group in core._tracked_groups}

    assert {
        "domain.frame_state",
        "initial.target",
        "initial.variable",
        "initial.where",
        "definedness",
        "transition.step",
        "assumption.frame",
        "assumption.event",
        "assumption.cardinality",
    } <= categories
    assert all("source_ref" in group for group in core.to_canonical()["tracked_groups"])


def test_basic_core_formulas_match_pre_tracking_sexpression_golden() -> None:
    """Source tracking must not change the existing canonical formula text."""
    model = load_state_machine_from_text("state Root;")
    core = build_bmc_core_formula(
        BmcEngine(model).prepare('check reach <= 1: active("Root");')
    )

    assert core.to_canonical()["formulas"] == {
        "D_N": dedent(
            """\
            And(Or(-3 == F_0_state, -1 == F_0_state, 0 == F_0_state),
                Or(-3 == F_1_state, -1 == F_1_state, 0 == F_1_state))"""
        ),
        "I_0": "-3 == F_0_state",
        "T_N": dedent(
            """\
            And(And(C_0_init___initial_Root_0_bda95de0da12e219a664812b5d8e9bf3e8c93d79 ==
                    And(-3 == F_0_state, True),
                    Implies(And(-3 == F_0_state, True), 0 == F_1_state)),
                And(C_0_init___delta___init___0_f7d616c3c15719463a33d4f46a98beedacea5870 ==
                    And(-3 == F_0_state,
                        Not(And(-3 == F_0_state, True))),
                    Implies(And(-3 == F_0_state,
                                Not(And(-3 == F_0_state, True))),
                            -3 == F_1_state)),
                Delta_0 ==
                And(-3 == F_0_state, Not(And(-3 == F_0_state, True))),
                Gamma_0 == False,
                Not(And(Delta_0, Gamma_0)))"""
        ),
        "ENV_N": "True",
        "Core_N": dedent(
            """\
            And(And(Or(-3 == F_0_state, -1 == F_0_state, 0 == F_0_state),
                    Or(-3 == F_1_state, -1 == F_1_state, 0 == F_1_state)),
                -3 == F_0_state,
                And(And(C_0_init___initial_Root_0_bda95de0da12e219a664812b5d8e9bf3e8c93d79 ==
                        And(-3 == F_0_state, True),
                        Implies(And(-3 == F_0_state, True),
                                0 == F_1_state)),
                    And(C_0_init___delta___init___0_f7d616c3c15719463a33d4f46a98beedacea5870 ==
                        And(-3 == F_0_state,
                            Not(And(-3 == F_0_state, True))),
                        Implies(And(-3 == F_0_state,
                                    Not(And(-3 == F_0_state, True))),
                                -3 == F_1_state)),
                    Delta_0 ==
                    And(-3 == F_0_state,
                        Not(And(-3 == F_0_state, True))),
                    Gamma_0 == False,
                    Not(And(Delta_0, Gamma_0))),
                True)"""
        ),
    }
    canonical = core.to_canonical()
    assert canonical["tracked_groups"]
    assert canonical["tracked_case_groups"]
    assert canonical["tracked_groups"][0]["source_ref"]["kind"] == "generated"
    assert canonical["tracked_case_groups"][0]["category"] == "transition.case"


def test_event_assumption_environment_formula_matches_golden() -> None:
    """Tracked event assumptions preserve the old environment expression."""
    model = load_state_machine_from_text("state Root { event go; }")
    core = build_bmc_core_formula(
        BmcEngine(model).prepare(
            'assume event("Root.go", 0) == false;\ncheck reach <= 1: active("Root");'
        )
    )

    assert core.to_canonical()["formulas"]["ENV_N"] == (
        "Not(E_0_event_0_Root_go_06775bfa102402247e16c156f692744c724aacbb)"
    )


def test_duplicate_assumption_occurrences_keep_distinct_stable_groups() -> None:
    """Equivalent source occurrences must not be merged by provenance."""
    model = load_state_machine_from_text("state Root;")
    context = BmcEngine(model).prepare(
        'assume at 0: active("Root"); '
        'assume at 0: active("Root"); '
        'check reach <= 1: active("Root");'
    )
    core = build_bmc_core_formula(context)

    assumption_ids = [
        item.stable_id
        for item in core._tracked_groups
        if item.category == "assumption.frame"
    ]
    assert assumption_ids == [
        "assumption.0000.frame.0000",
        "assumption.0001.frame.0000",
    ]


def test_query_group_excerpt_uses_exact_fbmcq_span() -> None:
    """Real query groups retain an exact source snapshot and half-open span."""
    model = load_state_machine_from_text("state Root;")
    query_text = 'init state("Root") where true;\ncheck reach <= 1: active("Root");'
    context = BmcEngine(model).prepare(query_text, query_source_path="query.fbmcq")
    core = build_bmc_core_formula(context)

    target = next(
        item for item in core._tracked_groups if item.stable_id == "initial.target"
    )
    assert target.source_ref.path == "query.fbmcq"
    assert (
        context._source_registry.excerpt(target.source_ref)
        == 'init state("Root") where true;'
    )


def test_public_query_parser_keeps_same_line_spans_non_empty() -> None:
    """Normal query parsing preserves non-empty half-open source spans."""
    query = parse_bmc_query(
        'init state("Root") where true;\ncheck reach <= 1: active("Root");',
        source_path="query.fbmcq",
    )

    assert query._source_spans
    for _, span in query._source_spans:
        if span.line == span.end_line:
            assert span.end_column > span.column


def test_fcstm_and_fbmcq_document_namespaces_are_isolated(tmp_path: Path) -> None:
    """A colliding display path must not cross-contaminate excerpts."""
    machine_path = tmp_path / "machine.fcstm"
    machine_path.write_text("def int x = 7;\nstate Root;\n", encoding="utf-8")
    model = load_state_machine_from_file(machine_path)
    query_text = 'init state("Root") where true;\ncheck reach <= 1: active("Root");'

    context = BmcEngine(model).prepare(query_text, query_source_path="machine.fcstm")
    core = build_bmc_core_formula(context)

    variable = next(
        item for item in core._tracked_groups if item.stable_id == "initial.variable.x"
    )
    target = next(
        item for item in core._tracked_groups if item.stable_id == "initial.target"
    )

    assert variable.source_ref.kind == "fcstm"
    assert variable.source_ref.path == "machine.fcstm"
    assert context._source_registry.excerpt(variable.source_ref) == "def int x = 7;"
    assert target.source_ref.kind == "fbmcq"
    assert target.source_ref.path == "machine.fcstm"
    assert (
        context._source_registry.excerpt(target.source_ref)
        == 'init state("Root") where true;'
    )


def test_case_provenance_is_not_part_of_formula_group_ledger() -> None:
    """Case provenance cannot be mistaken for a canonical formula conjunct."""
    model = load_state_machine_from_text("state Root;")
    core = build_bmc_core_formula(
        BmcEngine(model).prepare('check reach <= 1: active("Root");')
    )

    assert core._tracked_case_groups
    assert all(
        group.category == "transition.case" for group in core._tracked_case_groups
    )
    assert all(group.category != "transition.case" for group in core._tracked_groups)


def test_overlapping_combo_prefix_refuses_source_attribution(tmp_path: Path) -> None:
    """Combos sharing a first event stay unattributed instead of guessing a span.

    Two authored combo transitions leave the same state through the same first
    event, so the generated first edge belongs to both authored combos.  A macro
    case built on that shared edge has no unambiguous authored owner, and
    provenance must keep the generated reference rather than claim either span.
    """
    source_path = tmp_path / "shared_prefix.fcstm"
    source_path.write_text(
        """state Root {
    state S1;
    state S2;
    state S3;
    [*] -> S1;
    S1 -> S2 :: E1 + E2;
    S1 -> S3 :: E1 + E3;
}
""",
        encoding="utf-8",
    )

    model = load_state_machine_from_file(source_path)
    context = BmcEngine(model).prepare(
        'init state("Root.S1"); check reach <= 4: active("Root.S2");',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    combo_cases = [
        item
        for item in core._tracked_case_groups
        if item.refs.get("case_label")
        in {
            "Root.S1::transition::Root.S2::0",
            "Root.S1::transition::Root.S3::1",
        }
    ]

    assert combo_cases
    assert all(item.refs.get("source_inference") is None for item in combo_cases)
    assert all(item.source_ref.path is None for item in combo_cases)
    assert all(item.source_ref.span is None for item in combo_cases)
    assert all(
        context._source_registry.excerpt(item.source_ref) is None
        for item in combo_cases
    )


def test_reversed_event_combos_keep_distinct_source_spans(tmp_path: Path) -> None:
    """Combos over the same events in a different order keep their own spans.

    ``E1 + [x > 0] + E2`` and ``E2 + E1`` leave one state through disjoint first
    events, so each generated chain still resolves to exactly one authored
    combo.  Each case must excerpt its own authored line, never the other one.
    """
    source_path = tmp_path / "reversed_combo.fcstm"
    source_path.write_text(
        """def int x = 1;
state Root {
    state S1;
    state S2;
    state S3;
    [*] -> S1;
    S1 -> S2 :: E1 + [x > 0] + E2;
    S1 -> S3 :: E2 + E1;
}
""",
        encoding="utf-8",
    )

    model = load_state_machine_from_file(source_path)
    context = BmcEngine(model).prepare(
        'init state("Root.S1") where x == 1; check reach <= 5: active("Root.S2");',
        query_source_path="query.fbmcq",
    )
    core = build_bmc_core_formula(context)
    excerpts = {}
    inferences = {}
    for item in core._tracked_case_groups:
        label = item.refs.get("case_label")
        if label not in {
            "Root.S1::transition::Root.S2::0",
            "Root.S1::transition::Root.S3::1",
        }:
            continue
        excerpts.setdefault(label, set()).add(
            context._source_registry.excerpt(item.source_ref)
        )
        inferences.setdefault(label, set()).add(item.refs.get("source_inference"))

    assert excerpts == {
        "Root.S1::transition::Root.S2::0": {"S1 -> S2 :: E1 + [x > 0] + E2;"},
        "Root.S1::transition::Root.S3::1": {"S1 -> S3 :: E2 + E1;"},
    }
    assert inferences["Root.S1::transition::Root.S3::1"] == {"unique_combo"}


@pytest.mark.parametrize(
    "separators",
    [("\n",), ("\r\n",), ("\r",), ("\r", "\n", "\r\n")],
    ids=["lf", "crlf", "cr", "mixed"],
)
def test_line_ending_styles_keep_exact_source_excerpts(
    tmp_path: Path, separators: Tuple[str, ...]
) -> None:
    """Every line-ending style keeps exact spans for model, import, and query.

    The FCSTM and FBMCQ lexers only advance line numbers on ``LF``, so a
    snapshot may rewrite ``CRLF`` but must leave a lone ``CR`` alone.  A
    snapshot that turned lone ``CR`` into ``LF`` used to disagree with the
    lexer's line model, and every span after the first ``CR`` silently lost its
    excerpt: the main file, the imported module, and the query were all
    affected.  The ``mixed`` case cycles through separators so a file can change
    style mid-way, which shifts only part of the line numbering.

    Every excerpt is compared against its exact authored text, including the
    query ones.  Asserting only that a query excerpt is present would let a
    non-empty but wrongly attributed excerpt through, which is a worse failure
    than losing it.
    """

    def _join(lines: Tuple[str, ...]) -> str:
        parts = []
        for index, line in enumerate(lines):
            parts.append(line)
            if index != len(lines) - 1:
                parts.append(separators[index % len(separators)])
        return "".join(parts)

    worker = tmp_path / "worker.fcstm"
    worker.write_bytes(
        _join(
            (
                "def int y = 1;",
                "def int x = 5;",
                "state Worker;",
            )
        ).encode("utf-8")
    )
    main = tmp_path / "main.fcstm"
    main.write_bytes(
        _join(
            (
                "def int host = 0;",
                "state Root {",
                '    import "./worker.fcstm" as Child;',
                "    [*] -> Child;",
                "}",
            )
        ).encode("utf-8")
    )
    query_text = _join(
        (
            "init cold where true;",
            'assume at 0: var("Child_x") == 5;',
            'check reach <= 1: active("Root.Child");',
        )
    )

    model = load_state_machine_from_file(main)
    context = BmcEngine(model).prepare(
        query_text, query_source_path=str(tmp_path / "query.fbmcq")
    )
    core = build_bmc_core_formula(context)
    registry = context._source_registry
    excerpts = {
        group.stable_id: registry.excerpt(group.source_ref)
        for group in core._tracked_groups
        if group.source_ref.kind != "generated"
    }

    assert excerpts["initial.variable.host"] == "def int host = 0;"
    assert excerpts["initial.variable.Child_y"] == "def int y = 1;"
    assert excerpts["initial.variable.Child_x"] == "def int x = 5;"
    assert excerpts["initial.target"] == "init cold where true;"
    assert excerpts["initial.where"] == "true"
    assert excerpts["assumption.0000.frame.0000"] == (
        'assume at 0: var("Child_x") == 5;'
    )
    assert all(value is not None for value in excerpts.values())
    assert {
        group.source_ref.path
        for group in core._tracked_groups
        if group.source_ref.kind == "fcstm"
    } == {"main.fcstm", "worker.fcstm"}


@pytest.mark.unittest
@pytest.mark.parametrize("stable_id", ["冲突", "assumé", "a\tb", "a\x00b"])
def test_tracked_constraint_stable_ids_must_be_printable_ascii(stable_id) -> None:
    """The internal boundary keeps the same ASCII rule as the public one.

    A non-ASCII id reaching the relation layer would become a solver literal
    name, so the check belongs here as well as on the published reference.
    """
    with pytest.raises(ValueError, match="must be printable ASCII"):
        BmcTrackedConstraint(
            stable_id,
            "assumptions",
            "assumption.frame",
            (True,),
            BmcSourceRef("generated", None, None),
        )


def test_tracked_refs_get_the_same_validation_as_published_metadata() -> None:
    """The builder's own mapping is not a third door with looser rules.

    A shallow copy here still passes every published check downstream, because
    ``build_core_item`` revalidates at the public boundary -- which is precisely
    why no published-output test can tell the two apart.  What differs is where
    the failure surfaces: unvalidated builder metadata carries a caller's nested
    aliases and values that only fail once something serializes them.
    """
    from types import MappingProxyType

    from pyfcstm.bmc.provenance import BmcSourceRef, BmcTrackedConstraint

    source = BmcSourceRef("generated", None, None)

    def tracked(refs):
        return BmcTrackedConstraint(
            "assumption.0000.frame.0000",
            "assumptions",
            "assumption.frame",
            (z3.BoolVal(True),),
            source,
            refs=refs,
        )

    with pytest.raises(TypeError, match="not JSON-compatible"):
        tracked({"bad": object()})
    with pytest.raises(TypeError, match="keys must be strings"):
        tracked({"nested": {1: "a"}})
    with pytest.raises(ValueError, match="finite"):
        tracked({"nested": {"x": float("nan")}})

    # A nested mapping the caller keeps writing to must not reach the group.
    alias = {}
    group = tracked({"nested": alias})
    alias["late"] = object()
    assert "late" not in group.refs["nested"]
    assert isinstance(group.refs["nested"], MappingProxyType)


def test_reference_metadata_is_json_ready_or_refused() -> None:
    """Metadata reaches ``json.dumps`` unchanged, so it is checked on the way in.

    A caller builds ``refs`` from whatever they have to hand.  Anything that could
    not be rendered as JSON is refused where the group is built, because the
    alternative is a serialization failure at the point of publishing a report.
    """
    import json

    from pyfcstm.bmc.provenance import BmcSourceRef, BmcTrackedConstraint

    source = BmcSourceRef("generated", None, None)

    def tracked(refs):
        return BmcTrackedConstraint(
            "assumption.0000.frame.0000",
            "assumptions",
            "assumption.frame",
            (z3.BoolVal(True),),
            source,
            refs=refs,
        )

    # A well-formed nested mapping survives a round-trip through JSON.
    group = tracked({"nested": {"ok": 1}})
    assert json.loads(
        json.dumps({name: dict(value) for name, value in group.refs.items()})
    ) == {"nested": {"ok": 1}}

    # Values JSON cannot render are refused here rather than at publishing time.
    with pytest.raises(TypeError, match="is not JSON-compatible"):
        tracked({"x": {1, 2}})
    with pytest.raises(TypeError, match="is not JSON-compatible"):
        tracked({"x": b"ab"})

    # ``json.dumps`` would happily emit these, but no JSON reader accepts them.
    for not_finite in (float("nan"), float("inf")):
        with pytest.raises(ValueError, match="must be a finite number"):
            tracked({"x": not_finite})

    # A JSON object's keys are strings, so a non-string key cannot be published.
    with pytest.raises(TypeError, match="keys must be strings"):
        tracked({1: "a"})


def test_a_tracked_identifier_stays_printable_ascii() -> None:
    """A group's id is read by an ASCII scan, a dict lookup and a sort.

    The id becomes a solver literal name and a JSON key downstream, so a control
    character in it is refused where the group is built rather than at whichever
    reader trips over it first.
    """
    from pyfcstm.bmc.provenance import BmcSourceRef, BmcTrackedConstraint

    group = BmcTrackedConstraint(
        "assumption.0000.frame.0000",
        "assumptions",
        "assumption.frame",
        (z3.BoolVal(True),),
        BmcSourceRef("generated", None, None),
    )
    assert group.stable_id == "assumption.0000.frame.0000"

    for bad_id in ("a\x00b", "tab\there", "new\nline", "caf\xe9"):
        with pytest.raises(ValueError, match="printable ASCII"):
            BmcTrackedConstraint(
                bad_id,
                "assumptions",
                "assumption.frame",
                (z3.BoolVal(True),),
                BmcSourceRef("generated", None, None),
            )


def test_span_coordinates_are_typed_where_they_are_published() -> None:
    """The constructor must not be looser than the schema it publishes to.

    The asymmetry ledger records cases where the schema accepts what the
    constructor refuses, which is harmless because the constructor is the
    stricter side.  This is the mirror image: a constructor looser than the
    schema lets the tool emit output that fails its own published contract.
    ``Span`` is a shared utility and imposes no types of its own, so the check
    belongs at the boundary that publishes it.
    """
    import json

    from pyfcstm.bmc.provenance import BmcSourceRef

    for bad in (Span("oops", 1), Span(1.5, 1), Span(True, 1), Span(1, None)):
        with pytest.raises(TypeError, match="must be an integer"):
            BmcSourceRef("fcstm", "a.fcstm", bad)
    for bad in (Span(1, 1, "x", None), Span(1, 1, 1, 2.5)):
        with pytest.raises(TypeError, match="must be an integer"):
            BmcSourceRef("fcstm", "a.fcstm", bad)

    # Coordinates are typed, not bounded: a span that cannot be sliced already
    # degrades to an absent excerpt, and the schema states no bound either.
    published = BmcSourceRef("fcstm", "a.fcstm", Span(0, -1, None, None))
    payload = json.dumps(published.to_canonical()["span"])
    assert json.loads(payload) == {
        "line": 0,
        "column": -1,
        "end_line": None,
        "end_column": None,
    }


def test_the_digit_bound_falls_back_when_no_interpreter_limit_applies() -> None:
    """Two configurations mean "no interpreter limit", and both use the floor.

    Before Python 3.11 the setting does not exist at all, and from 3.11 on a
    value of zero disables it.  In both cases the published bound stands on its
    own, so the same payload is accepted everywhere.
    """
    import sys

    from pyfcstm.bmc import provenance

    saved = getattr(sys, "get_int_max_str_digits", None)
    try:
        if saved is not None:
            del sys.get_int_max_str_digits
        assert (
            provenance._effective_int_digit_limit()
            == provenance.MAX_METADATA_INT_DIGITS
        )
        sys.get_int_max_str_digits = lambda: 0
        assert (
            provenance._effective_int_digit_limit()
            == provenance.MAX_METADATA_INT_DIGITS
        )
        sys.get_int_max_str_digits = lambda: 640
        assert provenance._effective_int_digit_limit() == 640
    finally:
        if saved is None:
            sys.__dict__.pop("get_int_max_str_digits", None)
        else:
            sys.get_int_max_str_digits = saved


def test_the_digit_bound_follows_a_lowered_interpreter_limit() -> None:
    """Whatever this boundary accepts must be encodable in this process.

    A deployment may lower the interpreter's own integer-rendering limit for
    safety, down to 640.  A fixed published bound would then accept a value that
    still dies inside ``json.dumps`` -- the failure the boundary exists to
    prevent, just with a different threshold.  The check runs in a fresh process
    because the setting is global and changing it here would leak into every
    other test.
    """
    import subprocess
    import sys

    if not hasattr(sys, "set_int_max_str_digits"):
        pytest.skip("no interpreter integer limit before Python 3.11")

    probe = (
        "import json, sys\n"
        "from pyfcstm.bmc.explanation import BmcConstraintRef\n"
        "from pyfcstm.bmc.provenance import BmcSourceRef\n"
        "src = BmcSourceRef('generated', None, None)\n"
        "def build(value):\n"
        "    return BmcConstraintRef('g', 'assumptions', 'assumption.frame', src,\n"
        "                            's', refs={'n': value})\n"
        "print('limit', sys.get_int_max_str_digits())\n"
        "try:\n"
        "    build(10**700)\n"
        "    print('over accepted')\n"
        "except ValueError:\n"
        "    print('over refused')\n"
        "json.dumps(build(10**600).to_canonical(), allow_nan=False)\n"
        "print('under encoded')\n"
    )
    env = dict(os.environ, PYTHONINTMAXSTRDIGITS="640")
    completed = subprocess.run(
        [sys.executable, "-c", probe],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )

    assert "limit 640" in completed.stdout
    assert "over refused" in completed.stdout
    assert "under encoded" in completed.stdout


def test_an_excerpt_quotes_exactly_the_stored_text() -> None:
    """An excerpt is sliced from the document the registry holds, unchanged.

    Quoting anything other than the stored characters is the one failure a
    provenance registry exists to rule out, so a span is checked against the text
    it names on a multi-line document rather than only on a single word.
    """
    from pyfcstm.bmc.provenance import BmcSourceRef, SourceDocumentRegistry

    registry = SourceDocumentRegistry({"m.fcstm": "state A;\nstate B;\n"})

    assert registry.document("m.fcstm") == "state A;\nstate B;\n"
    assert registry.excerpt(BmcSourceRef("fcstm", "m.fcstm", Span(1, 1, 1, 9))) == (
        "state A;"
    )
    assert registry.excerpt(BmcSourceRef("fcstm", "m.fcstm", Span(2, 7, 2, 9))) == "B;"
    # A span naming a line the document does not have yields no excerpt at all
    # rather than the nearest text.
    assert registry.excerpt(BmcSourceRef("fcstm", "m.fcstm", Span(9, 1, 9, 2))) is None


@pytest.mark.unittest
def test_registry_refuses_a_path_that_names_no_document() -> None:
    """An empty path cannot identify a document, so the registry refuses it.

    A path is what a later report quotes provenance against.  Accepting one that
    names nothing would let a span be attributed to a document no one can look
    up.
    """
    from pyfcstm.bmc.provenance import SourceDocumentRegistry

    with pytest.raises(ValueError, match="paths must be non-empty strings"):
        SourceDocumentRegistry({"": "state A;"})

    # A well-formed registry resolves the path it was given and nothing else.
    registry = SourceDocumentRegistry({"real.fcstm": "REAL"})
    assert registry.document("real.fcstm") == "REAL"
    assert registry.document("anything-else") is None


@pytest.mark.unittest
def test_excerpts_drop_a_residual_carriage_return() -> None:
    """A ``CR`` the normalizer cannot remove must stay out of the excerpt.

    :func:`_normalize_line_separators` rewrites line breaks in one
    left-to-right pass, so ``"\r\r\n"`` collapses to ``"\r\n"`` and leaves a
    residual ``CR`` at the end of that line rather than inventing a second line
    break for it.  Locating line ends therefore has to trim that ``CR``, or a
    whole-line span would slice it into the excerpt and put a bare carriage
    return inside a report whose lines are otherwise exact.
    """
    residual = "def int x = 0;\r\r\nstate Root { }\r\n"
    stored = provenance_module._normalize_line_separators(residual)
    # The precondition this test exercises: normalization really does leave a
    # CR behind, so the trim below is not guarding an impossible input.
    assert stored == "def int x = 0;\r\nstate Root { }\n"

    registry = SourceDocumentRegistry({"m.fcstm": residual})
    whole_first_line = BmcSourceRef("fcstm", "m.fcstm", Span(1, 1, 1, 15))
    assert registry.excerpt(whole_first_line) == "def int x = 0;"

    # One column further is past the line's own width and is refused rather
    # than reaching into the residual CR or the line break after it.
    over_run = BmcSourceRef("fcstm", "m.fcstm", Span(1, 1, 1, 16))
    assert registry.excerpt(over_run) is None

    # The line after the residual is unaffected: its own break was normalized,
    # so its offsets shift by exactly the one retained CR.
    second_line = BmcSourceRef("fcstm", "m.fcstm", Span(2, 1, 2, 15))
    assert registry.excerpt(second_line) == "state Root { }"


@pytest.mark.unittest
def test_excerpts_are_identical_for_crlf_and_lf_checkouts() -> None:
    """A Windows checkout must yield the same excerpts as a Unix one.

    Spans arrive as 1-based line/column pairs with an exclusive end column, so
    the byte offsets they resolve to differ between ``\\r\\n`` and ``\\n``
    sources even though the visible text is the same.  A whole-line span is the
    case that exposes it: the trailing ``CR`` sits inside the span's column
    range and has to be trimmed, or every excerpt on a Windows checkout would
    carry a stray carriage return into the report.
    """
    unix = "def int x = 0;\nstate Root { }\n"
    windows = "def int x = 0;\r\nstate Root { }\r\n"

    unix_registry = SourceDocumentRegistry({"m.fcstm": unix})
    windows_registry = SourceDocumentRegistry({"m.fcstm": windows})

    for line, expected in ((1, "def int x = 0;"), (2, "state Root { }")):
        # Column 15 is one past the last character of a 14-character line, the
        # exclusive end that selects the whole line.
        span = Span(line, 1, line, 15)
        reference = BmcSourceRef("fcstm", "m.fcstm", span)
        assert unix_registry.excerpt(reference) == expected
        assert windows_registry.excerpt(reference) == expected

    # The equivalence comes from storage: the Windows text is held as LF, so
    # both registries resolve the same offsets rather than compensating later.
    assert windows_registry.document("m.fcstm", kind="fcstm") == unix
    assert provenance_module._span_offsets(unix, Span(2, 1, 2, 15)) == (15, 29)

    # A column past the line's own width is refused rather than silently
    # reaching into the terminator or the next line.
    over_run = BmcSourceRef("fcstm", "m.fcstm", Span(1, 1, 1, 16))
    assert unix_registry.excerpt(over_run) is None
    assert windows_registry.excerpt(over_run) is None


@pytest.mark.unittest
def test_synthetic_state_paths_yield_no_owner_prefixes() -> None:
    """A synthetic case must not search authored states for its provenance.

    Owner prefixes are how an event-only continuation finds the authored
    transition that explains it.  Encoder-internal state paths -- the empty path
    and the ``__``-prefixed synthetic ones -- name no authored state, so they
    must produce no prefixes at all.  Returning prefixes for them would let a
    synthetic case match an authored transition and claim a source span the user
    never wrote.
    """
    from pyfcstm.bmc import relation as relation_module

    assert relation_module._state_path_prefixes("") == ()
    assert relation_module._state_path_prefixes("__synthetic") == ()
    assert relation_module._state_path_prefixes("__synthetic.Child") == ()
    # An authored path still yields nearest-owner-first prefixes.
    assert relation_module._state_path_prefixes("Root.Outer.A") == (
        "Root.Outer.A",
        "Root.Outer",
        "Root",
    )


#: Queries whose builds between them register every stage and category pairing
#: the relation builder produces, so the naming rationale below rests on groups a
#: real build emitted rather than on a hand-written list of them.
_PAIRING_CORPUS = (
    (
        "def int x = 1;\ndef int y = 0;\n"
        "state Root { event Go; state A; state B; [*] -> A; A -> B :: Go; A -> B; }",
        'init state("Root.A") where x / y > 0; '
        'assume at 0: var("x") / var("y") > 0; '
        'check reach <= 2: active("Root.B");',
    ),
    (
        "def int x = 1;\n"
        "state Root { event Go; state A; state B; [*] -> A; A -> B :: Go; }",
        'init state("Root.A"); '
        'assume event("Root.Go", 0) == true; '
        'assume events cardinality at_most_one {"Root.Go"}; '
        'check reach <= 2: active("Root.B");',
    ),
)


def _constructed_pairings():
    """Return every stage and category pairing a corpus of real builds constructs.

    Read back from ``to_canonical()`` on the core the public builder returns,
    which publishes both group collections and gives each group's stage and
    category, so nothing here reaches past the published surface.

    :return: The pairings the corpus constructs.
    :rtype: Set[Tuple[str, str]]
    """
    from pyfcstm.bmc import BmcEngine, build_bmc_core_formula

    observed = set()
    for source, query in _PAIRING_CORPUS:
        context = BmcEngine(load_state_machine_from_text(source)).prepare(query)
        canonical = build_bmc_core_formula(context).to_canonical()
        # Case groups are published in their own key; reading only the first
        # would lose the whole transition.case family.
        for key in ("tracked_groups", "tracked_case_groups"):
            for group in canonical[key]:
                observed.add((group["stage"], group["category"]))
    return observed


@pytest.mark.unittest
def test_a_tracked_group_and_its_aggregate_agree_on_which_pairings_exist() -> None:
    """Two public surfaces must not disagree about which groups can exist.

    :class:`~pyfcstm.bmc.provenance.BmcTrackedConstraint` is exported and
    documented, so a caller can build a group directly rather than through a
    build.  :func:`~pyfcstm.bmc.explanation.constraint_aggregate` is equally
    public and answers which aggregate a group belongs to.  Were the constructor
    to accept a pairing the aggregate cannot classify, a caller following the
    documentation could hold an object no other published function can read.
    """
    import z3

    from pyfcstm.bmc.explanation import constraint_aggregate
    from pyfcstm.bmc.provenance import TRACKED_GROUP_PAIRINGS

    def build(stage, category):
        return BmcTrackedConstraint(
            "group.0000",
            stage,
            category,
            (z3.BoolVal(True),),
            BmcSourceRef("generated", None, None),
        )

    # Every pairing the constructor accepts can be classified.
    for stage, category in sorted(TRACKED_GROUP_PAIRINGS):
        group = build(stage, category)
        assert constraint_aggregate(group.stage, group.category)

    # A pairing it does not accept is refused at construction.  Both halves are
    # individually valid here -- "kernel" is a real stage and "definedness" a
    # real category -- which is why the pair is what gets checked.
    assert ("kernel", "definedness") not in TRACKED_GROUP_PAIRINGS
    with pytest.raises(ValueError, match="is not one the builder registers"):
        build("kernel", "definedness")

    # And what real builds emit is exactly what the constructor accepts, so the
    # table cannot drift from the registrations in either direction.
    observed = _constructed_pairings()
    assert observed == set(TRACKED_GROUP_PAIRINGS), (
        set(TRACKED_GROUP_PAIRINGS) - observed,
        observed - set(TRACKED_GROUP_PAIRINGS),
    )


@pytest.mark.unittest
def test_the_group_noun_reads_the_category_because_the_aggregate_cannot() -> None:
    """Pin the facts that decide how a source group is named to the reader.

    A rendered group is named from its category's leading segment rather than
    from its aggregate.  That choice is only correct because of the pairings real
    builds actually emit, so the deciding facts are asserted here against those
    builds instead of being asserted in prose in the reference documentation.
    """
    from pyfcstm.bmc.explanation import constraint_aggregate

    observed = _constructed_pairings()
    stages_by_noun = {}
    for stage, category in observed:
        stages_by_noun.setdefault(category.split(".")[0], set()).add(stage)

    # The rationale for naming a group by its category segment rests on there
    # being five nouns while the aggregate vocabulary offers four words, so both
    # sets are asserted rather than merely computed.
    assert set(stages_by_noun) == {
        "assumption",
        "definedness",
        "domain",
        "initial",
        "transition",
    }
    assert {constraint_aggregate(stage, category) for stage, category in observed} == {
        "domain",
        "environment",
        "initial",
        "transition",
    }

    # A transition group is always a kernel-stage group, so its aggregate is
    # "transition" and the rendered noun happens to agree with it.
    assert stages_by_noun["transition"] == {"kernel"}
    assert constraint_aggregate("kernel", "transition.step") == "transition"

    # A definedness group never comes from the kernel stage, and comes from both
    # of the others with a different aggregate in each -- which is why the
    # rendered noun reads the category instead of the aggregate.
    assert stages_by_noun["definedness"] == {"initialization", "assumptions"}
    assert {
        stage: constraint_aggregate(stage, "definedness")
        for stage in stages_by_noun["definedness"]
    } == {"initialization": "initial", "assumptions": "environment"}

    # An assumption group's aggregate is a word no reader sees elsewhere.
    assert stages_by_noun["assumption"] == {"assumptions"}
    assert constraint_aggregate("assumptions", "assumption.frame") == "environment"


_FACT_MODEL = """def int x = 0;
def int y = 3;
state Root {
    event Go;
    state A;
    state B;
    [*] -> A;
    A -> B :: Go;
}"""


def _fact_groups(query: str, machine: str = None):
    """Return the tracked groups a real build produces, keyed by category.

    ``machine`` overrides the default integer model so a test can exercise the
    other persistent variable type without duplicating the whole helper.
    """
    from pyfcstm.bmc import BmcEngine, build_bmc_core_formula

    core = build_bmc_core_formula(
        BmcEngine(
            load_state_machine_from_text(_FACT_MODEL if machine is None else machine)
        ).prepare(query)
    )
    groups = {}
    for group in list(core._tracked_groups) + list(core._tracked_case_groups):
        groups.setdefault(group.category, group)
    return groups


@pytest.mark.unittest
def test_a_variable_comparison_reads_as_a_domain_fact_not_a_structural_one() -> None:
    """An assumption pinning a variable publishes the variable, frame and value.

    A machine reader dispatching on ``kind`` needs the operator and the operand,
    not a restatement of the group's identity.  Without this an LLM or IDE can
    only echo the source line back.
    """
    from pyfcstm.bmc.provenance import normalized_fact_for

    groups = _fact_groups(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; '
        'check reach <= 2: active("Root.B");'
    )
    fact = normalized_fact_for(groups["assumption.frame"])

    assert fact["kind"] == "variable_comparison"
    assert fact["variable"] == "x"
    assert fact["frame"] == 0
    assert fact["operator"] == "eq"
    assert fact["value"] == 1


@pytest.mark.unittest
def test_an_initial_variable_reads_as_an_initializer_fact() -> None:
    """The declared initial value is published as a value, not as an expression."""
    from pyfcstm.bmc.provenance import normalized_fact_for

    groups = _fact_groups(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; '
        'check reach <= 2: active("Root.B");'
    )
    fact = normalized_fact_for(groups["initial.variable"])

    assert fact["kind"] == "variable_comparison"
    assert fact["variable"] == "x"
    assert fact["frame"] == 0
    assert fact["operator"] == "eq"
    assert fact["value"] == 0


@pytest.mark.unittest
def test_a_frame_state_domain_reads_as_the_set_of_legal_states() -> None:
    """A domain rule says which states a frame may hold, as plain integers."""
    from pyfcstm.bmc.provenance import normalized_fact_for

    groups = _fact_groups(
        'init state("Root.A") where x == 0; check reach <= 2: active("Root.B");'
    )
    fact = normalized_fact_for(groups["domain.frame_state"])

    assert fact["kind"] == "state_domain"
    assert fact["frame"] == 0
    assert isinstance(fact["states"], list)
    assert fact["states"] and all(isinstance(v, int) for v in fact["states"])


@pytest.mark.unittest
def test_a_definedness_rule_reads_as_the_operation_it_guards() -> None:
    """Definedness says which operation would otherwise be undefined."""
    from pyfcstm.bmc.provenance import normalized_fact_for

    groups = _fact_groups(
        'init state("Root.A") where x == 0; '
        'assume at 1: var("y") / var("x") > 0; '
        'check reach <= 2: active("Root.B");'
    )
    fact = normalized_fact_for(groups["definedness"])

    assert fact["kind"] == "definedness_condition"
    assert fact["operation"] == "division"
    assert fact["frame"] == 1


@pytest.mark.unittest
def test_an_unreduced_group_says_so_instead_of_guessing() -> None:
    """A shape with no recognizer degrades honestly, keeping its identity."""
    from pyfcstm.bmc.provenance import normalized_fact_for

    groups = _fact_groups(
        'init state("Root.A") where x == 0; check reach <= 2: active("Root.B");'
    )
    fact = normalized_fact_for(groups["transition.step"])

    assert fact["kind"] == "structural_constraint"
    assert fact["category"] == "transition.step"


@pytest.mark.unittest
def test_a_recognized_fact_is_not_echoed_back_as_its_own_identifier() -> None:
    """``normalized_fact`` publishes the fact, and ``constraint`` the metadata.

    The frozen result prototype puts ``frames``, ``steps`` and ``refs`` inside
    ``constraint``; repeating them inside the fact makes a reader carry two
    copies of the same values and obscures which keys are the fact itself.
    """
    from pyfcstm.bmc.infeasibility import build_core_item

    groups = _fact_groups(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; '
        'check reach <= 2: active("Root.B");'
    )
    item = build_core_item(groups["assumption.frame"])

    assert set(item.normalized_fact) == {
        "kind",
        "variable",
        "frame",
        "operator",
        "value",
    }
    # The metadata is still published, one level up.
    assert item.constraint.frames == (0,)
    assert item.constraint.refs["frame"] == 0


@pytest.mark.unittest
def test_a_float_variable_gets_the_same_domain_reading_as_an_integer_one() -> None:
    """``float`` is one of the two persistent variable types, not a special case.

    A reader who declares ``def float x`` and writes contradictory bounds
    deserves the same account as one who wrote ``def int x``.  Reading only
    integer numerals would leave every float model stuck at the structural
    fallback, so the recognizer reads the rational literals z3 builds for the
    real sort too.
    """
    from pyfcstm.bmc.provenance import normalized_fact_for

    groups = _fact_groups(
        'init state("Root.A") where x == 0.0; '
        'assume at 0: var("x") > 0.5; '
        'check reach <= 2: active("Root.B");',
        machine=(
            "def float x = 0.0;\n"
            "state Root { event Go; state A; state B; [*] -> A; A -> B :: Go; }"
        ),
    )
    fact = normalized_fact_for(groups["assumption.frame"])

    assert fact["kind"] == "variable_comparison"
    assert fact["variable"] == "x"
    assert fact["frame"] == 0
    # z3 normalizes ``x > 0.5`` to ``0.5 < x``, so the mirrored operand order is
    # the one that actually occurs for the real sort.
    assert fact["operator"] == "gt"
    assert fact["value"] == 0.5
    # A real bound is published as a float even when its value is whole, which is
    # what keeps integer-only reasoning off the real domain downstream.
    assert isinstance(fact["value"], float)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "declarations, assumption",
    [
        ("def int x = 0;\ndef int y = 0;", 'var("x") > var("y")'),
        ("def int x = 0;", 'var("x") > 0 && var("x") < 5'),
    ],
    ids=["comparison-between-two-variables", "two-bounds-in-one-assumption"],
)
def test_a_shape_outside_the_reading_keeps_its_identity(
    declarations, assumption
) -> None:
    """Two ordinary assumptions the value reading does not cover.

    A comparison between two variables has no single value to publish, and a
    conjunction of two bounds is not one comparison, so neither fits the
    single-relation fact shape.  Both are things a reader writes without thinking
    twice, so the fallback they take is a normal path, not an edge case -- and
    taking it means saying so, rather than publishing half a fact.
    """
    from pyfcstm.bmc.provenance import normalized_fact_for

    groups = _fact_groups(
        'init state("Root.A") where x == 0; '
        "assume at 0: %s; "
        'check reach <= 2: active("Root.B");' % assumption,
        machine=(
            "%s\nstate Root { event Go; state A; state B; [*] -> A; A -> B :: Go; }"
            % declarations
        ),
    )
    fact = normalized_fact_for(groups["assumption.frame"])

    assert fact["kind"] == "structural_constraint"
    assert fact["category"] == "assumption.frame"
    # The identity is preserved so a reader can still find the line.
    assert fact["stable_id"] == groups["assumption.frame"].stable_id


@pytest.mark.unittest
@pytest.mark.parametrize(
    "declaration, assumption, operation",
    [
        ("def int x = 0;", 'var("x") / 0 > 0', "division"),
        ("def float x = 0.0;", "sqrt(-1.0) >= 0.0", "sqrt"),
    ],
    ids=["division-by-zero", "square-root-of-a-negative"],
)
def test_a_definedness_fact_names_the_operation_it_actually_guards(
    declaration, assumption, operation
) -> None:
    """The published operation must be the one the source line performs.

    A definedness group carries only its domain condition, and two different
    operations can produce conditions of the same shape, so the operation cannot
    be inferred from the expression.  Naming it anyway produced a fact and a
    sentence that contradicted the source: ``sqrt(-1.0)`` was reported as a
    division that must stay defined.
    """
    from pyfcstm.bmc.provenance import normalized_fact_for

    groups = _fact_groups(
        'assume at 0: %s; check reach <= 1: active("Root");' % assumption,
        machine="%s state Root;" % declaration,
    )
    fact = normalized_fact_for(groups["definedness"])

    assert fact["kind"] == "definedness_condition"
    assert fact["operation"] == operation


@pytest.mark.unittest
@pytest.mark.parametrize(
    "symbol, frame, is_slot",
    [
        ("F_0_state", 0, True),
        ("F_0_state", 1, False),
        ("F_10_state", 1, False),
        ("F_1_state", 10, False),
        ("F_0_state_%s" % ("9" * 40), 0, False),
    ],
    ids=[
        "the-slot-of-its-own-frame",
        "the-slot-of-another-frame",
        "a-longer-frame-index-is-not-a-prefix-match",
        "a-shorter-frame-index-is-not-a-prefix-match",
        "a-model-variable-that-happens-to-be-called-state",
    ],
)
def test_the_state_slot_is_told_apart_from_everything_that_looks_like_it(
    symbol, frame, is_slot
) -> None:
    """The state reader must not claim a symbol that merely resembles the slot.

    Frame indices are decimal, so ``F_1_state`` and ``F_10_state`` share a prefix,
    and a model variable may legitimately be named ``state``.  Reading either as
    the frame's state slot would publish a state fact about something that is not
    a state, which the narrative would then build a conflict on.
    """
    import z3

    from pyfcstm.bmc.provenance import _frame_state_slot

    assert _frame_state_slot(z3.Int(symbol), frame) is is_slot


@pytest.mark.unittest
def test_the_two_operand_readers_never_claim_the_same_symbol() -> None:
    """A slot is not a variable and a variable is not a slot.

    The two readers run against the same operands, so an overlap would let one
    group publish two contradictory facts depending on dispatch order.  The case
    that makes this concrete is a model variable actually named ``state``.
    """
    import z3

    from pyfcstm.bmc.provenance import _frame_state_slot, _frame_variable_name

    for name in (
        "F_0_state",
        "F_0_x_%s" % ("a" * 40),
        "F_0_state_%s" % ("b" * 40),
    ):
        symbol = z3.Int(name)
        slot = _frame_state_slot(symbol, 0)
        variable = _frame_variable_name(symbol)
        assert not (slot and variable is not None), name

    # And each reader does claim the operand it is for.
    assert _frame_state_slot(z3.Int("F_0_state"), 0) is True
    assert _frame_variable_name(z3.Int("F_0_state_%s" % ("b" * 40))) == "state"


@pytest.mark.unittest
def test_a_long_variable_name_is_published_as_the_name_that_was_declared() -> None:
    """The published variable must be one the reader can find in their source.

    The encoding truncates a long name when it builds its symbol, so recovering
    the name from the symbol recovers the truncation, not the declaration.  A
    fact naming a variable that does not exist is the same defect as naming the
    wrong operation: the key is right and the value is a guess.
    """
    from pyfcstm.bmc.provenance import normalized_fact_for

    name = "v" * 81
    groups = _fact_groups(
        'assume at 0: var("%s") == 1; check reach <= 1: active("Root.A");' % name,
        machine=("def int %s = 0;\nstate Root { state A; state B; [*] -> A; }" % name),
    )
    fact = normalized_fact_for(groups["assumption.frame"], (name,))

    assert fact["kind"] == "variable_comparison"
    assert fact["variable"] == name

    # Without the declared names there is nothing to resolve against, so the
    # reader falls back to the body it can see rather than inventing one.
    fallback = normalized_fact_for(groups["assumption.frame"])
    assert fallback["variable"] == name[:80]


@pytest.mark.unittest
@pytest.mark.parametrize(
    "name, declared, resolved",
    [
        ("x", ("x", "y"), "x"),
        ("v" * 81, ("v" * 81,), "v" * 81),
        ("v" * 80 + "a", ("v" * 80 + "a", "v" * 80 + "b"), "v" * 80 + "a"),
        ("a.b", ("a.b", "a_b"), "a.b"),
        ("a_b", ("a.b", "a_b"), "a_b"),
        ("ghost", ("x", "y"), None),
    ],
    ids=[
        "an-ordinary-name",
        "a-name-longer-than-the-symbol-body",
        "two-names-sharing-their-first-eighty-characters",
        "a-name-whose-dot-becomes-an-underscore",
        "the-underscore-name-it-collides-with",
        "a-symbol-belonging-to-no-declared-variable",
    ],
)
def test_a_symbol_resolves_to_the_declared_name_it_was_built_from(
    name, declared, resolved
) -> None:
    """Resolution goes through the digest, which the whole name produced.

    The symbol body is the name with unsafe characters replaced and then
    truncated, so it is lossy twice over: ``a.b`` and ``a_b`` produce the same
    body, and any name past eighty characters loses its tail.  Reading the body
    back therefore has to be wrong for at least one of a colliding pair.  The
    digest does not collide, so matching declared names through it answers
    exactly, and a symbol that belongs to no declared variable answers nothing
    rather than a plausible-looking prefix.
    """
    import hashlib
    import re

    import z3

    from pyfcstm.bmc.provenance import _frame_variable_name

    # Built the way the encoder builds it, so the test exercises the real shape
    # rather than a hand-written string that happens to look like one.
    body = re.sub(r"[^0-9A-Za-z_]+", "_", name).strip("_") or "item"
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()
    symbol = z3.Int("F_0_%s_%s" % (body[:80], digest))

    assert _frame_variable_name(symbol, declared) == resolved


@pytest.mark.unittest
@pytest.mark.parametrize(
    "declaration, initial, literal",
    [
        ("def float x = 0.0;", "x == 0.0", "1"),
        ("def float x = 0.0;", "x == 0.0", "1.0"),
        ("def int x = 0;", "x == 0", "1"),
    ],
    ids=[
        "float-variable-integer-literal",
        "float-variable-decimal-literal",
        "integer-variable-integer-literal",
    ],
)
def test_a_comparison_is_read_whichever_way_the_sorts_were_written(
    declaration, initial, literal
) -> None:
    """Writing ``1`` where the variable is real must read the same as ``1.0``.

    Mixing sorts makes z3 insert a ``to_real`` coercion, around the literal when
    the variable is real and around the variable when the literal is.  Neither
    changes what the author wrote, so neither may change whether the fact is
    readable -- otherwise the same query degrades or not depending on a decimal
    point.
    """
    from pyfcstm.bmc.provenance import normalized_fact_for

    groups = _fact_groups(
        'init state("Root.A") where %s; '
        'assume at 1: var("x") == %s; '
        'check reach <= 2: active("Root.B");' % (initial, literal),
        machine=(
            "%s\nstate Root { event Go; state A; state B; [*] -> A; A -> B :: Go; }"
            % declaration
        ),
    )
    fact = normalized_fact_for(groups["assumption.frame"], ("x",))

    assert fact["kind"] == "variable_comparison"
    assert fact["variable"] == "x"
    assert fact["operator"] == "eq"
    assert fact["value"] == 1


@pytest.mark.unittest
def test_two_variables_never_share_one_symbol() -> None:
    """Distinct declarations must encode to distinct symbols.

    The symbol is the variable's identity inside the relation, so two variables
    collapsing onto one makes the encoder state something the model does not:
    here each assumption constrains its own havoc'd variable, which is plainly
    satisfiable, yet the scenario is reported infeasible.  A truncated digest is
    what allows the collapse -- these two names share their first eighty
    characters and, at forty bits, their digest too.
    """
    from pyfcstm.bmc.relation import _safe_symbol_fragment

    prefix = "v" * 80
    first, second = prefix + "498982", prefix + "626752"
    # The pair is only interesting because a short digest does collide on it.
    assert (
        hashlib.sha1(first.encode("utf-8")).hexdigest()[:10]
        == hashlib.sha1(second.encode("utf-8")).hexdigest()[:10]
    )

    assert _safe_symbol_fragment(first) != _safe_symbol_fragment(second)


@pytest.mark.unittest
def test_a_colliding_scenario_keeps_its_satisfiable_verdict() -> None:
    """The verdict must not depend on how long the author's names are.

    Two independent havoc'd variables required to hold different values is
    satisfiable, and stays satisfiable when the names get long.
    """
    from pyfcstm.bmc import (
        BmcEngine,
        build_bmc_core_formula,
        compile_bmc_property,
        solve_bmc_property,
    )
    from pyfcstm.model import load_state_machine_from_text

    prefix = "v" * 80
    first, second = prefix + "498982", prefix + "626752"
    machine = load_state_machine_from_text(
        "def int %s = 0;\ndef int %s = 0;\nstate Root;\n" % (first, second)
    )
    context = BmcEngine(machine).prepare(
        'init state("Root") havoc *; '
        'assume at 0: var("%s") == 1; '
        'assume at 0: var("%s") == 2; '
        'check reach <= 1: active("Root");' % (first, second)
    )

    result = solve_bmc_property(compile_bmc_property(build_bmc_core_formula(context)))

    assert result.feasibility.infeasible_stage is None


@pytest.mark.unittest
def test_a_sum_is_not_read_as_one_of_its_operands() -> None:
    """Only a leaf symbol names a variable; a compound term names none.

    ``x + y`` renders as ``F_0_x_... + F_0_y_...``, which starts like a frame
    symbol and ends with y's digest, so a reader working on the text alone calls
    it ``y``.  The narrative then states that y equals a value the query never
    required of it -- a fabricated equality, which is the one thing the contract
    says a controlled narrative must never produce.
    """
    from pyfcstm.bmc.provenance import normalized_fact_for

    groups = _fact_groups(
        'init state("Root") havoc *; '
        'assume at 0: var("x") + var("y") == 1.0; '
        'check reach <= 1: active("Root");',
        machine="def int x = 0;\ndef int y = 0;\nstate Root;",
    )
    fact = normalized_fact_for(groups["assumption.frame"], ("x", "y"))

    assert fact["kind"] == "structural_constraint"


@pytest.mark.unittest
def test_a_definedness_guard_over_a_sum_names_no_single_variable() -> None:
    """A divisor that is a sum is not a variable, and must not be named as one.

    ``10 / (x + y)`` requires ``x + y`` to be non-zero; ``y`` alone may be zero.
    Publishing ``variable: y`` states a requirement the query never made, which
    is the operand-level form of naming the wrong operation.
    """
    from pyfcstm.bmc.provenance import normalized_fact_for

    groups = _fact_groups(
        'init state("Root.A") havoc *; '
        'assume at 0: (10 / (var("x") + var("y"))) == 1; '
        'check reach <= 1: active("Root.A");',
        machine=("def int x = 0;\ndef int y = 0;\nstate Root { state A; [*] -> A; }"),
    )
    fact = normalized_fact_for(groups["definedness"], ("x", "y"))

    assert fact["kind"] == "definedness_condition"
    assert "variable" not in fact


@pytest.mark.unittest
@pytest.mark.parametrize(
    "declaration, literal, integral",
    [
        ("def int x = 0;", "1", True),
        ("def float x = 0.0;", "1", False),
        ("def float x = 0.0;", "1.0", False),
    ],
    ids=[
        "integer-variable",
        "real-variable-integer-literal",
        "real-variable-decimal-literal",
    ],
)
def test_the_domain_marker_follows_the_variable_not_the_literal(
    declaration, literal, integral
) -> None:
    """Which domain a bound lives in is decided by the variable, not the value.

    Downstream interval reasoning tightens a strict bound by one over the
    integers and must not over the reals, and it reads the domain off the
    published fact.  Unwrapping the sort coercion made ``x > 1`` on a real
    variable publish an integer, so the marker said "integer domain" for a
    variable that admits every value between consecutive ones.
    """
    from pyfcstm.bmc.provenance import normalized_fact_for

    groups = _fact_groups(
        'init state("Root.A") havoc *; '
        'assume at 0: var("x") > %s; '
        'check reach <= 1: active("Root.A");' % literal,
        machine="%s\nstate Root { state A; [*] -> A; }" % declaration,
    )
    fact = normalized_fact_for(groups["assumption.frame"], ("x",))

    assert fact["kind"] == "variable_comparison"
    assert isinstance(fact["value"], int) is integral


@pytest.mark.unittest
@pytest.mark.parametrize(
    "kind, machine, query",
    [
        (
            "variable_comparison",
            "def int x = 0;\n"
            "state Root { event Go; state A; state B; [*] -> A; A -> B :: Go; }",
            'init state("Root.A") where x == 0; assume at 0: var("x") == 1; '
            'check reach <= 2: active("Root.B");',
        ),
        (
            "state_membership",
            "state Root { state A; state B; [*] -> A; A -> B; }",
            'init state("Root.A"); assume at 0: active("Root.B"); '
            'check reach <= 1: active("Root.A");',
        ),
        (
            "state_domain",
            "state Root { state A; state B; [*] -> A; A -> B; }",
            'init state("Root.A"); check reach <= 1: active("Root.B");',
        ),
        (
            "definedness_condition",
            "def int x = 0; state Root;",
            'assume at 0: var("x") / 0 > 0; check reach <= 1: active("Root");',
        ),
    ],
)
def test_a_recognizer_publishes_every_key_its_tag_requires(
    kind, machine, query
) -> None:
    """The required-key table gates reading, so it must match what is produced.

    Members are filtered on that table before anything indexes them, which makes a
    table demanding one key too many degrade silently: the fact is complete, the
    narrative declines it, and nothing says why.  Comparing the table against what
    each recognizer really emits is the only way that stays true as either side
    changes.
    """
    from pyfcstm.bmc.explanation import _FACT_REQUIRED_KEYS
    from pyfcstm.bmc.provenance import normalized_fact_for

    groups = _fact_groups(query, machine=machine)
    declared = tuple(
        name
        for name in ("x", "y")
        if "def int %s" % name in machine or "def float %s" % name in machine
    )
    published = [normalized_fact_for(group, declared) for group in groups.values()]
    facts = [fact for fact in published if fact.get("kind") == kind]

    assert facts, "this corpus no longer produces a %s fact" % kind
    for fact in facts:
        missing = set(_FACT_REQUIRED_KEYS[kind]) - set(fact)
        assert missing == set(), "%s omits %s" % (kind, sorted(missing))


def test_two_modules_declaring_at_the_same_coordinates_keep_their_own_excerpts(
    tmp_path: Path,
) -> None:
    """A published define names the file it was written in, not a namesake's.

    Two imported modules that declare a variable at the same line and column are
    ordinary: ``def int x = 1;`` on line 1 is what a small module looks like.  A
    span key is (line, column, end_line, end_column) with no document in it, so
    pairing a define with its source by span alone lets the first file walked
    answer for both, and the published ``source_excerpt`` becomes a different
    variable from a different file.  That is worse than publishing nothing: a
    reader following the reference lands on a line that has no bearing on the
    conflict.
    """
    left = tmp_path / "left.fcstm"
    left.write_text("def int x = 1;\nstate LeftModule;\n", encoding="utf-8")
    right = tmp_path / "right.fcstm"
    right.write_text("def int y = 2;\nstate RightModule;\n", encoding="utf-8")
    main = tmp_path / "main.fcstm"
    main.write_text(
        "state Root {\n"
        '    import "./left.fcstm" as Left;\n'
        '    import "./right.fcstm" as Right;\n'
        "    [*] -> Left;\n"
        "}\n",
        encoding="utf-8",
    )

    machine = load_state_machine_from_file(main)
    context = BmcEngine(machine).prepare(
        'init state("Root.Left") where Right_y == 999; check reach <= 1: true;'
    )
    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="formal",
    )
    published = {
        item.constraint.stable_id: item
        for item in result.feasibility.explanation.core.items
    }

    define = published["initial.variable.Right_y"]
    assert Path(define.constraint.source.path).name == "right.fcstm"
    assert define.source_excerpt == "def int y = 2;"


def test_a_forced_expansion_names_the_file_it_was_written_in(tmp_path: Path) -> None:
    """An expanded transition points at its declaration, not at its host state.

    ``!* -> M1 :: Panic;`` expands onto every descendant, and a descendant can
    come from an imported module.  The expanded transition keeps the span of the
    line that declared it, so pairing it with the host state's file yields a
    reference whose document cannot contain that span: here the declaration sits
    on line 10 of the host and the imported module is five lines long, and a
    reader following the reference lands nowhere.  The whole-program span table
    knows which file the line belongs to, and it has to be consulted before the
    host state is used as a fallback.
    """
    imported = tmp_path / "worker.fcstm"
    imported.write_text(
        "state Worker {\n    state W1;\n    [*] -> W1;\n}\n", encoding="utf-8"
    )
    main = tmp_path / "main.fcstm"
    main.write_text(
        "// padding so the declaration sits past the imported file's last line\n"
        "// padding\n"
        "// padding\n"
        "// padding\n"
        "state Root {\n"
        '    import "./worker.fcstm" as Worker;\n'
        "    event Panic;\n"
        "    state M1;\n"
        "    [*] -> M1;\n"
        "    !* -> M1 :: Panic;\n"
        "}\n",
        encoding="utf-8",
    )

    machine = load_state_machine_from_file(main)
    worker = machine.root_state.substates["Worker"]
    expanded = [
        transition
        for transition in worker.transitions
        if getattr(transition, "is_forced", False)
    ]

    assert expanded, "the forced declaration should reach the imported state"
    for transition in expanded:
        assert transition._source_path == str(main.resolve())
        document = machine._source_documents[transition._source_path]
        line = document.split("\n")[transition._span.line - 1]
        assert "!* -> M1 :: Panic;" in line


def test_an_ambiguous_span_key_publishes_nothing_rather_than_a_wrong_file(
    tmp_path: Path,
) -> None:
    """When two files share a span key, an expansion claims neither of them.

    A key is (line, column, end_line, end_column) with no document in it, so two
    files that put a statement of the same length at the same place share one.
    An expansion has to be resolved through that table -- it lives in a state it
    was not written beside -- and the table cannot say which file the key belongs
    to.  Answering anyway sends a reader to a line somebody else wrote: here
    ``!* -> M1 :: Ev;`` at line 5 of the root and ``D1 -> D2 :: Ev;`` at line 5 of
    the middle module are both fifteen characters at column 5, and the expansion
    that reaches the innermost state used to be published as the middle module,
    whose line 5 is an unrelated transition.

    Falling back to the host state is no better: the host is by construction not
    where an expansion was written, and its line at that span is whatever happens
    to be there -- a closing brace, in this fixture.  So an ambiguous key resolves
    to nothing, and the member is published without a reference.

    A reader losing a link is a smaller harm than a reader following one into the
    wrong file, and it is the harm they can see.
    """
    (tmp_path / "deep.fcstm").write_text(
        "state Deep {\n    state X1;\n    state X2;\n    [*] -> X1;\n}\n",
        encoding="utf-8",
    )
    (tmp_path / "mid.fcstm").write_text(
        "state Mid {\n"
        '    import "./deep.fcstm" as Deep;\n'
        "    state D1;\n"
        "    state D2;\n"
        "    D1 -> D2 :: Ev;\n"
        "    [*] -> D1;\n"
        "}\n",
        encoding="utf-8",
    )
    main = tmp_path / "main.fcstm"
    main.write_text(
        "state Root {\n"
        '    import "./mid.fcstm" as Mid;\n'
        "    event Ev;\n"
        "    state M1;\n"
        "    !* -> M1 :: Ev;\n"
        "    [*] -> M1;\n"
        "}\n",
        encoding="utf-8",
    )

    machine = load_state_machine_from_file(main)
    documents = machine._source_documents
    deep = machine.root_state.substates["Mid"].substates["Deep"]
    expansions = [
        transition
        for transition in deep.transitions
        if getattr(transition, "_span", None) is not None
        and (transition._span.line, transition._span.column) == (5, 5)
        and transition._span.end_column == 20
    ]

    assert expansions, "the forced declaration should reach the innermost state"
    for transition in expansions:
        path = getattr(transition, "_source_path", None)
        if path is None:
            continue
        # If a path is published at all it has to be the file that wrote the line.
        assert "!* -> M1 :: Ev;" in documents[path].split("\n")[4]
    assert any(
        getattr(transition, "_source_path", None) is None for transition in expansions
    ), "an ambiguous key must not resolve to some file"


def test_a_branch_inside_a_branch_still_has_an_excerpt(tmp_path: Path) -> None:
    """The descent into conditional arms reaches the bottom, not one level down.

    A conditional operation holds its arms in ``branches`` and each arm holds
    statements that may be conditional in turn, so the walk that gives model
    objects their file has to recurse.  Stopping one level down leaves every
    statement inside a nested arm without a source, and ``model_reference`` then
    answers with no path and no excerpt for a line the author wrote.  The same
    descent has to reach transition effects, which are conditional as often as
    lifecycle actions are.

    A flattened walk is exactly what a merge produced here once, and it passed
    every test in the suite, so the shape is pinned rather than trusted.
    """
    source = tmp_path / "machine.fcstm"
    source.write_text(
        "def int x = 0;\n"
        "state Root {\n"
        "    event Go;\n"
        "    state A {\n"
        "        enter {\n"
        "            if [x > 0] {\n"
        "                if [x > 5] { x = x + 1; } else { x = x + 2; }\n"
        "            } else { x = x + 3; }\n"
        "        }\n"
        "    }\n"
        "    state B;\n"
        "    [*] -> A;\n"
        "    A -> B :: Go effect {\n"
        "        if [x > 0] {\n"
        "            if [x > 3] { x = x * 2; } else { x = x * 3; }\n"
        "        }\n"
        "    };\n"
        "}\n",
        encoding="utf-8",
    )

    model = load_state_machine_from_file(source)
    registry = SourceDocumentRegistry(
        model._source_documents, display_root=model._source_root
    )

    def excerpts(operation):
        """Every statement reachable under a conditional, read the public way."""
        found = []
        for branch in getattr(operation, "branches", ()):
            for statement in getattr(branch, "statements", ()):
                found.append(registry.excerpt(registry.model_reference(statement)))
                found.extend(excerpts(statement))
        return found

    root = model.root_state
    enter_if = root.substates["A"].on_enters[0].operations[0]
    assert excerpts(enter_if) == [
        "if [x > 5] { x = x + 1; } else { x = x + 2; }",
        "x = x + 1;",
        "x = x + 2;",
        "x = x + 3;",
    ]

    effect_if = [transition for transition in root.transitions if transition.effects][
        0
    ].effects[0]
    assert excerpts(effect_if) == [
        "if [x > 3] { x = x * 2; } else { x = x * 3; }",
        "x = x * 2;",
        "x = x * 3;",
    ]
