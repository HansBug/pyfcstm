"""TDD contracts for BMC source provenance and tracked relation groups."""

from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
from textwrap import dedent
from types import SimpleNamespace

import pytest
import z3

import pyfcstm.bmc.provenance as provenance_module
from pyfcstm.dsl import node as dsl_nodes
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.bmc import BmcEngine, BmcPreparedContext, build_bmc_core_formula
from pyfcstm.bmc.errors import BmcBuildError, InvalidBmcQuery
from pyfcstm.bmc.parse import parse_bmc_query
from pyfcstm.bmc.provenance import (
    BmcSourceRef,
    BmcTrackedConstraint,
    SourceDocumentRegistry,
)
from pyfcstm.bmc.relation import BmcCoreFormula, _append_tracked_group
from pyfcstm.model import (
    load_state_machine_from_file,
    load_state_machine_from_text,
    parse_dsl_node_to_state_machine,
)
from pyfcstm.model.expr import Integer
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
    ],
)
def test_source_reference_rejects_malformed_values(kwargs, exception, message) -> None:
    """Source references reject invalid kind, path, and span values."""
    with pytest.raises(exception, match=message):
        BmcSourceRef(**kwargs)


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
    ],
)
def test_tracked_constraint_rejects_malformed_values(
    field, value, exception, message
) -> None:
    """Tracked constraints reject malformed identity and payload fields."""
    values = {
        "stable_id": "group",
        "stage": "kernel",
        "category": "domain",
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


def test_query_source_metadata_rejects_invalid_public_metadata() -> None:
    """Parser and query dataclass reject malformed source metadata."""
    query_text = 'check reach <= 1: active("Root");'

    with pytest.raises(InvalidBmcQuery, match="_source_path"):
        parse_bmc_query(query_text, source_path="")

    query = parse_bmc_query(query_text)
    with pytest.raises(InvalidBmcQuery, match="_source_spans"):
        replace(query, _source_spans=(("not-an-id", Span(1, 1)),))


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


def test_file_and_import_source_paths_are_not_collapsed(tmp_path: Path) -> None:
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
    assert model._source_documents[str(main.resolve())] == main.read_text(
        encoding="utf-8"
    )
    assert model._source_documents[str(imported.resolve())] == imported.read_text(
        encoding="utf-8"
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
        if dict(item.refs).get("transition_labels") == ["Root.Outer::0::Outer->Sink"]
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


def test_public_model_mutation_drops_stale_model_source_span(tmp_path: Path) -> None:
    """A changed public model cannot retain an obsolete exact source span."""
    source_path = tmp_path / "machine.fcstm"
    source_path.write_text("def int x = 1;\nstate Root;\n", encoding="utf-8")
    model = load_state_machine_from_file(source_path)

    model.defines["x"].init = Integer("2")
    context = BmcEngine(model).prepare(
        'check reach <= 1: active("Root");', query_source_path="query.fbmcq"
    )
    core = build_bmc_core_formula(context)
    group = next(
        item for item in core._tracked_groups if item.stable_id == "initial.variable.x"
    )

    assert group.source_ref.path == "machine.fcstm"
    assert group.source_ref.span is None
    assert context._source_registry.excerpt(group.source_ref) is None


def test_public_model_mutation_that_breaks_export_fails_closed(tmp_path: Path) -> None:
    """An unexportable mutated model object cannot retain a source span."""
    source_path = tmp_path / "machine.fcstm"
    source_path.write_text("def int x = 1;\nstate Root;\n", encoding="utf-8")
    model = load_state_machine_from_file(source_path)
    model.defines["x"].init = None
    registry = SourceDocumentRegistry(
        model._source_documents, display_root=model._source_root
    )

    reference = registry.model_reference(model.defines["x"])

    assert reference.path == "machine.fcstm"
    assert reference.span is None
    assert registry.excerpt(reference) is None


def test_model_reference_without_exporter_drops_stale_span() -> None:
    """Metadata-only objects cannot claim an exact model source span."""
    registry = SourceDocumentRegistry({"machine.fcstm": "state Root;"})
    metadata_only = SimpleNamespace(
        _source_path="machine.fcstm",
        _span=Span(1, 1, 1, 12),
        _source_fingerprint="stale",
    )

    reference = registry.model_reference(metadata_only)

    assert reference.path == "machine.fcstm"
    assert reference.span is None
    assert registry.excerpt(reference) is None


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
            And(And(C_0_init___initial_Root_0_bda95de0da ==
                    And(-3 == F_0_state, True),
                    Implies(And(-3 == F_0_state, True), 0 == F_1_state)),
                And(C_0_init___delta___init___0_f7d616c3c1 ==
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
                And(And(C_0_init___initial_Root_0_bda95de0da ==
                        And(-3 == F_0_state, True),
                        Implies(And(-3 == F_0_state, True),
                                0 == F_1_state)),
                    And(C_0_init___delta___init___0_f7d616c3c1 ==
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
    assert "tracked_groups" not in core.to_canonical()


def test_event_assumption_environment_formula_matches_golden() -> None:
    """Tracked event assumptions preserve the old environment expression."""
    model = load_state_machine_from_text("state Root { event go; }")
    core = build_bmc_core_formula(
        BmcEngine(model).prepare(
            'assume event("Root.go", 0) == false;\ncheck reach <= 1: active("Root");'
        )
    )

    assert core.to_canonical()["formulas"]["ENV_N"] == (
        "Not(E_0_event_0_Root_go_06775bfa10)"
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


def test_tracked_group_rejects_expression_from_another_z3_context() -> None:
    """The core bundle rejects groups that cannot be checked by its solver."""
    model = load_state_machine_from_text("state Root;")
    context = BmcEngine(model).prepare('check reach <= 1: active("Root");')
    core = build_bmc_core_formula(context)
    other_context = z3.Context()
    foreign = BmcTrackedConstraint(
        "foreign",
        "kernel",
        "domain",
        (z3.Bool("foreign", ctx=other_context),),
        BmcSourceRef("generated", None, None),
    )

    with pytest.raises(BmcBuildError, match="core Z3 context"):
        BmcCoreFormula(
            context=core.context,
            symbols=core.symbols,
            domain_formula=core.domain_formula,
            initial_formula=core.initial_formula,
            transition_formula=core.transition_formula,
            environment_formula=core.environment_formula,
            core=core.core,
            steps=core.steps,
            _tracked_groups=(foreign,),
        )


def test_core_formula_rejects_malformed_tracked_group_payloads() -> None:
    """Core formulas reject invalid, duplicate, and non-Boolean groups."""
    model = load_state_machine_from_text("state Root;")
    core = build_bmc_core_formula(
        BmcEngine(model).prepare('check reach <= 1: active("Root");')
    )

    with pytest.raises(BmcBuildError, match="tracked groups must contain"):
        replace(core, _tracked_groups=(object(),))

    group = core._tracked_groups[0]
    with pytest.raises(BmcBuildError, match="unique stable ids"):
        replace(core, _tracked_groups=(group, group))

    non_boolean = replace(group, expressions=(z3.Int("not_boolean"),))
    with pytest.raises(BmcBuildError, match="Z3 Boolean expressions"):
        replace(core, _tracked_groups=(non_boolean,))

    with pytest.raises(BmcBuildError, match="reconstruct D_N"):
        replace(core, domain_formula=z3.BoolVal(True))

    orphan = replace(core._tracked_groups[0], category="orphan")
    formula_groups = list(core._tracked_groups)
    formula_groups[0] = orphan
    with pytest.raises(BmcBuildError, match="does not belong"):
        replace(core, _tracked_groups=tuple(formula_groups))

    case_group = core._tracked_case_groups[0]
    with pytest.raises(BmcBuildError, match="missing lowered cases"):
        replace(core, _tracked_case_groups=())

    unknown_case_refs = dict(case_group.refs)
    unknown_case_refs["case_index"] = 99
    with pytest.raises(BmcBuildError, match="does not identify a lowered case"):
        replace(
            core,
            _tracked_case_groups=(
                replace(case_group, refs=unknown_case_refs),
                core._tracked_case_groups[1],
            ),
        )

    duplicate_case_refs = dict(core._tracked_case_groups[1].refs)
    duplicate_case_refs["step"] = case_group.refs["step"]
    duplicate_case_refs["case_index"] = case_group.refs["case_index"]
    with pytest.raises(BmcBuildError, match="identify each lowered case once"):
        replace(
            core,
            _tracked_case_groups=(
                case_group,
                replace(core._tracked_case_groups[1], refs=duplicate_case_refs),
            ),
        )

    mismatched_label_refs = dict(case_group.refs)
    mismatched_label_refs["case_label"] = "not-the-lowered-label"
    with pytest.raises(BmcBuildError, match="label does not match"):
        replace(
            core,
            _tracked_case_groups=(
                replace(case_group, refs=mismatched_label_refs),
                core._tracked_case_groups[1],
            ),
        )

    mismatched_kind_refs = dict(case_group.refs)
    mismatched_kind_refs["case_kind"] = "not-the-lowered-kind"
    with pytest.raises(BmcBuildError, match="kind does not match"):
        replace(
            core,
            _tracked_case_groups=(
                replace(case_group, refs=mismatched_kind_refs),
                core._tracked_case_groups[1],
            ),
        )

    mismatched_transition_refs = dict(case_group.refs)
    mismatched_transition_refs["transition_labels"] = ["not-a-real-transition"]
    with pytest.raises(BmcBuildError, match="transition labels do not match"):
        replace(
            core,
            _tracked_case_groups=(
                replace(case_group, refs=mismatched_transition_refs),
                core._tracked_case_groups[1],
            ),
        )

    with pytest.raises(BmcBuildError, match="transition.case category"):
        replace(
            core,
            _tracked_case_groups=(replace(case_group, category="domain.frame_state"),),
        )

    with pytest.raises(BmcBuildError, match="tracked case groups must contain"):
        replace(core, _tracked_case_groups=(object(),))

    with pytest.raises(BmcBuildError, match="tracked case groups must have unique"):
        replace(core, _tracked_case_groups=(case_group, case_group))

    case_non_boolean = replace(case_group, expressions=(z3.Int("case_not_boolean"),))
    with pytest.raises(BmcBuildError, match="tracked case group expressions"):
        replace(core, _tracked_case_groups=(case_non_boolean,))

    other_context = z3.Context()
    case_foreign = replace(
        case_group,
        expressions=(z3.Bool("case_foreign", ctx=other_context),),
    )
    with pytest.raises(BmcBuildError, match="tracked case group expressions"):
        replace(core, _tracked_case_groups=(case_foreign,))

    with pytest.raises(BmcBuildError, match="all tracked groups must have"):
        replace(
            core,
            _tracked_case_groups=(
                replace(case_group, stable_id=core._tracked_groups[0].stable_id),
            ),
        )

    with pytest.raises(BmcBuildError, match="cover every lowered case"):
        replace(core, _tracked_case_groups=core._tracked_case_groups[:-1])

    case_formula_groups = list(core._tracked_case_groups)
    case_formula_groups[0] = replace(
        case_formula_groups[0],
        expressions=(z3.Not(case_formula_groups[0].expressions[0]),),
    )
    with pytest.raises(BmcBuildError, match="formula does not match case"):
        replace(core, _tracked_case_groups=tuple(case_formula_groups))


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
