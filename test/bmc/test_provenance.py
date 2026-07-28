"""TDD contracts for BMC source provenance and tracked relation groups."""

from __future__ import annotations

import os
from pathlib import Path
from textwrap import dedent
from typing import Tuple

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


def test_metadata_scalars_and_keys_become_exact_builtins() -> None:
    """A value must not be the one answering questions about itself.

    ``__str__``, ``__int__``, ``__eq__`` and ``__hash__`` are all overridable, and
    ``__class__`` can be faked so that ``isinstance`` agrees.  Storing whatever
    passed the check lets a subclass carry state that changes its hash later, or
    lets an impostor reach the JSON encoder and fail there instead of here.
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

    class MutableHashStr(str):
        def __new__(cls, value):
            obj = str.__new__(cls, value)
            obj.broken = False
            return obj

        def __hash__(self):
            if self.broken:
                raise RuntimeError("the caller changed this key's hash")
            return str.__hash__(self)

    class PretendInt:
        @property
        def __class__(self):
            return int

    # A key is rebuilt, so breaking the original afterwards cannot reach it.
    key = MutableHashStr("nested")
    group = tracked({key: {"ok": 1}})
    key.broken = True
    assert [type(name) for name in group.refs] == [str]
    json.dumps({name: dict(value) for name, value in group.refs.items()})

    # Values are rebuilt too, and an impostor is refused here rather than later.
    with pytest.raises(TypeError, match="must be an integer"):
        tracked({"x": PretendInt()})

    class Shouty(str):
        def __str__(self):
            return "LIE"

    stored = tracked({"note": Shouty("real")})
    assert stored.refs["note"] == "real"
    assert type(stored.refs["note"]) is str


def test_exact_readers_refuse_an_impostor_of_every_primitive() -> None:
    """Each reader refuses an object that only claims to be its type.

    ``isinstance`` consults ``__class__``, so a plain object can satisfy it.  The
    base type's own descriptor cannot be fooled, and refusing here is what keeps
    the failure attributable instead of surfacing much later in a serializer.
    """
    from pyfcstm.bmc.provenance import exact_float, exact_int, exact_str

    def impostor_of(cls):
        return type("Impostor", (object,), {"__class__": property(lambda self: cls)})()

    with pytest.raises(TypeError, match="must be a string"):
        exact_str(impostor_of(str), "note")
    with pytest.raises(TypeError, match="must be an integer"):
        exact_int(impostor_of(int), "frames")
    with pytest.raises(TypeError, match="must be a number"):
        exact_float(impostor_of(float), "threshold")


def test_a_bool_impostor_is_not_json_compatible() -> None:
    """Only the two real singletons count as a JSON boolean.

    ``bool`` cannot be subclassed, so anything that merely claims to be one is an
    impostor with no JSON counterpart.
    """
    from pyfcstm.bmc.provenance import BmcSourceRef, BmcTrackedConstraint

    fake_bool = type(
        "FakeBool", (object,), {"__class__": property(lambda self: bool)}
    )()

    with pytest.raises(TypeError, match="not JSON-compatible"):
        BmcTrackedConstraint(
            "assumption.0000.frame.0000",
            "assumptions",
            "assumption.frame",
            (z3.BoolVal(True),),
            BmcSourceRef("generated", None, None),
            refs={"flag": fake_bool},
        )


def test_tracked_identifiers_are_stored_as_exact_text() -> None:
    """The builder container replaces its own identifiers too.

    ``build_core_item`` revalidates at the public boundary, so a subclass stored
    here still cannot reach a published document -- which is exactly why no
    published-output test can see this.  What it can reach is anything that reads
    the group directly: the ASCII scan, a dict lookup, a sort.
    """
    from pyfcstm.bmc.provenance import BmcSourceRef, BmcTrackedConstraint

    class Shouty(str):
        def __str__(self):
            return "LIE"

    class AsciiLie(str):
        def __iter__(self):
            return iter("ok")

    group = BmcTrackedConstraint(
        Shouty("assumption.0000.frame.0000"),
        Shouty("assumptions"),
        Shouty("assumption.frame"),
        (z3.BoolVal(True),),
        BmcSourceRef("generated", None, None),
    )

    assert type(group.stable_id) is str
    assert type(group.stage) is str
    assert type(group.category) is str
    assert group.stable_id == "assumption.0000.frame.0000"

    # A subclass hiding a control character behind __iter__ is still refused.
    with pytest.raises(ValueError, match="printable ASCII"):
        BmcTrackedConstraint(
            AsciiLie("a\x00b"),
            "assumptions",
            "assumption.frame",
            (z3.BoolVal(True),),
            BmcSourceRef("generated", None, None),
        )


def test_tracked_identifier_gates_refuse_impostors() -> None:
    """The builder container refuses an object that only claims to be text."""
    from pyfcstm.bmc.provenance import BmcSourceRef, BmcTrackedConstraint

    impostor = type("Impostor", (object,), {"__class__": property(lambda self: str)})()

    with pytest.raises(ValueError, match="stable_id must be non-empty"):
        BmcTrackedConstraint(
            123,
            "assumptions",
            "assumption.frame",
            (z3.BoolVal(True),),
            BmcSourceRef("generated", None, None),
        )
    with pytest.raises(ValueError, match="stable_id must be non-empty"):
        BmcTrackedConstraint(
            impostor,
            "assumptions",
            "assumption.frame",
            (z3.BoolVal(True),),
            BmcSourceRef("generated", None, None),
        )
    with pytest.raises(ValueError, match="category must be a string"):
        BmcTrackedConstraint(
            "assumption.0000.frame.0000",
            "assumptions",
            123,
            (z3.BoolVal(True),),
            BmcSourceRef("generated", None, None),
        )
    with pytest.raises(ValueError, match="stage must be a string"):
        BmcTrackedConstraint(
            "assumption.0000.frame.0000",
            impostor,
            "assumption.frame",
            (z3.BoolVal(True),),
            BmcSourceRef("generated", None, None),
        )


def test_a_source_kind_cannot_talk_its_way_past_the_vocabulary() -> None:
    """``in`` uses ``__eq__`` and ``__hash__``, so membership reads the text."""
    from pyfcstm.bmc.provenance import BmcSourceRef

    class InvalidKind(str):
        def __hash__(self):
            return hash("generated")

        def __eq__(self, other):
            return True

    with pytest.raises(ValueError, match="Unsupported BMC source kind"):
        BmcSourceRef(InvalidKind("nonsense"), None, None)

    impostor = type("Impostor", (object,), {"__class__": property(lambda self: str)})()
    with pytest.raises(ValueError, match="Unsupported BMC source kind"):
        BmcSourceRef(impostor, None, None)
    with pytest.raises(ValueError, match="Unsupported BMC source kind"):
        BmcSourceRef(123, None, None)
    with pytest.raises(ValueError, match="source path must be None"):
        BmcSourceRef("fcstm", impostor, None)
    with pytest.raises(ValueError, match="source path must be None"):
        BmcSourceRef("fcstm", 123, None)
    with pytest.raises(ValueError, match="source path must be None"):
        BmcSourceRef("fcstm", "", None)


def test_two_keys_canonicalizing_to_one_fail_closed() -> None:
    """Folding two distinct keys into one would drop provenance silently.

    Both keys coexist in the caller's mapping because their ``__eq__`` says they
    differ, but they hold the same text.  Overwriting the first would lose a
    recorded fact with nothing to show for it.
    """
    from pyfcstm.bmc.provenance import _require_json_mapping

    class DuplicateKey(str):
        def __new__(cls, text, salt):
            obj = str.__new__(cls, text)
            obj.salt = salt
            return obj

        def __hash__(self):
            return hash((str.__str__(self), self.salt))

        def __eq__(self, other):
            return self is other

    source = {DuplicateKey("same", 1): "first", DuplicateKey("same", 2): "second"}
    assert len(source) == 2

    with pytest.raises(ValueError, match="both canonicalize to"):
        _require_json_mapping(source, "refs")


def test_a_span_stand_in_is_refused() -> None:
    """``isinstance`` accepts a faked ``__class__``; the real type decides.

    Every later reader treats this field as a Span and reads ``line`` and
    friends from it, so a stand-in would fail somewhere far from here.
    """
    from pyfcstm.bmc.provenance import BmcSourceRef

    fake_span = type(
        "FakeSpan", (object,), {"__class__": property(lambda self: Span)}
    )()

    with pytest.raises(TypeError, match="span must be Span or None"):
        BmcSourceRef("fcstm", "a.fcstm", fake_span)


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


def test_a_document_cannot_publish_text_the_registry_never_held() -> None:
    """Excerpts are sliced from the stored text, so that text must be exact.

    ``replace`` is an instance method.  A ``str`` subclass overriding it makes the
    registry store, and every excerpt quote, characters the caller never supplied
    -- the one thing a provenance registry exists to rule out.
    """
    from pyfcstm.bmc.provenance import BmcSourceRef, SourceDocumentRegistry

    class EvilText(str):
        def replace(self, old, new, *args):
            return "EVIL"

    registry = SourceDocumentRegistry({"m.fcstm": EvilText("SAFE")})

    assert registry.document("m.fcstm") == "SAFE"
    assert type(registry.document("m.fcstm")) is str
    assert (
        registry.excerpt(BmcSourceRef("fcstm", "m.fcstm", Span(1, 1, 1, 5))) == "SAFE"
    )


def test_container_subclasses_cannot_rewrite_published_metadata() -> None:
    """A real ``dict`` or ``list`` subclass must not choose what gets published.

    ``items`` and ``__iter__`` are overridable, so a subclass of the concrete
    type can pass every check and then hand the walk different contents than it
    holds.  Reading through the base type closes that; a ``Mapping`` by protocol
    only still goes through its own ``items``, since that is the sole way in.
    """
    from collections import UserDict

    from pyfcstm.bmc.provenance import _require_json_mapping

    class LyingDict(dict):
        def items(self):
            return iter([("forged", 2)])

    class LyingList(list):
        def __iter__(self):
            return iter([999])

    published = _require_json_mapping({"a": LyingDict({"real": 1})}, "refs")
    assert dict(published["a"]) == {"real": 1}

    published = _require_json_mapping({"a": LyingList([1])}, "refs")
    assert list(published["a"]) == [1]

    # A well-behaved Mapping that is not a dict is still accepted by protocol.
    published = _require_json_mapping({"a": UserDict({"ok": 1})}, "refs")
    assert dict(published["a"]) == {"ok": 1}


def test_registry_paths_are_stored_as_exact_text() -> None:
    """One document's text must never be quoted as another's provenance.

    A ``str`` subclass overriding ``__eq__``/``__hash__`` makes every lookup hit
    the same entry, so any path would resolve to that document -- exactly the
    misattribution a provenance registry exists to prevent.
    """
    from pyfcstm.bmc.provenance import SourceDocumentRegistry

    class AliasPath(str):
        def __eq__(self, other):
            return True

        def __hash__(self):
            return hash("alias")

    registry = SourceDocumentRegistry({AliasPath("real.fcstm"): "REAL"})

    assert [type(path) for path in registry.documents] == [str]
    assert registry.document("real.fcstm") == "REAL"
    assert registry.document("anything-else") is None

    # Two distinct keys holding the same text would silently drop one document.
    # A dict literal cannot express that -- equal keys collapse before the
    # registry sees them -- so the pair has to differ by identity.
    class DistinctPath(str):
        def __new__(cls, text, salt):
            obj = str.__new__(cls, text)
            obj.salt = salt
            return obj

        def __eq__(self, other):
            return self is other

        def __hash__(self):
            return hash((str.__str__(self), self.salt))

    # An object that only claims to be a str is refused, on both mappings.
    impostor = type("Impostor", (object,), {"__class__": property(lambda self: str)})()
    for mapping_kwargs in (
        {"documents": {impostor: "x"}},
        {"documents": {}, "query_documents": {impostor: "x"}},
    ):
        with pytest.raises(ValueError, match="paths must be non-empty strings"):
            SourceDocumentRegistry(**mapping_kwargs)
    with pytest.raises(ValueError, match="paths must be non-empty strings"):
        SourceDocumentRegistry({"": "x"})

    colliding = {DistinctPath("same.fcstm", 1): "A", DistinctPath("same.fcstm", 2): "B"}
    assert len(colliding) == 2
    with pytest.raises(ValueError, match="two entries for"):
        SourceDocumentRegistry(colliding)


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
@pytest.mark.parametrize(
    ("reason", "labels"),
    [
        ("too few separators", ("Root::0",)),
        ("index is not a number", ("Root::x::A->B",)),
        ("index is negative", ("Root::-1::A->B",)),
        ("owner path names no state", ("NoSuchState::0::A->B",)),
        ("edge has no arrow", ("Root::0::AB",)),
        ("edge endpoint is blank", ("Root::0:: ->B",)),
        ("index is past the owner's transitions", ("Root::99::A->B",)),
        ("endpoints do not match the indexed transition", ("Root::0::B->A",)),
        ("more than one transition contributed", ("Root::0::A->B", "Root::1::A->B")),
    ],
)
def test_unparsable_transition_labels_fall_back_to_the_generated_reference(
    tmp_path: Path, reason: str, labels: Tuple[str, ...]
) -> None:
    """A label the resolver cannot verify must degrade, not crash or guess.

    Case provenance is inferred by parsing the expander's own transition label
    back into an owner state, a transition index, and an edge, then checking
    that the indexed transition really has those endpoints.  Every step can fail
    if the label shape ever drifts from what the expander emits.  Failing there
    has to yield the generated reference with no inference recorded: raising
    would abort a BMC run over a provenance detail, and returning a span anyway
    would attribute a composite or unrelated formula to one authored line.

    :param reason: Which verification step the label is built to fail.
    :type reason: str
    :param labels: Transition labels attached to the case under test.
    :type labels: Tuple[str, ...]
    """
    import dataclasses

    from pyfcstm.bmc import relation as relation_module
    from pyfcstm.bmc.macro import ActionBlock

    source_path = tmp_path / "machine.fcstm"
    source_path.write_text(
        """state Root {
    event Go;
    state A;
    state B;
    [*] -> A;
    A -> B;
    A -> B :: Go;
}
""",
        encoding="utf-8",
    )
    model = load_state_machine_from_file(source_path)
    context = BmcEngine(model).prepare(
        'init state("Root.A"); check reach <= 2: active("Root.B");',
        query_source_path="query.fbmcq",
    )

    # Take a real case and its real generated reference out of a real build, so
    # only the labels under test are synthetic.
    captured = []
    original = relation_module._case_source_reference

    def record(ctx, case, generated_ref):
        captured.append((ctx, case, generated_ref))
        return original(ctx, case, generated_ref)

    relation_module._case_source_reference = record
    try:
        build_bmc_core_formula(context)
    finally:
        relation_module._case_source_reference = original

    build_context, case, generated_ref = next(
        entry for entry in captured if entry[1].kind == "transition"
    )

    blocks = tuple(
        ActionBlock(
            "transition_effect",
            "transition_effect",
            case.source_state_id,
            case.source_state_path,
            (),
            transition_label=label,
        )
        for label in labels
    )
    mutant = dataclasses.replace(case, action_blocks=blocks, guard_requirements=())

    reference, resolved_labels, inference = relation_module._case_source_reference(
        build_context, mutant, generated_ref
    )
    assert reference is generated_ref, reason
    assert inference is None, reason
    # The labels are still reported, so a reader can see what could not be
    # resolved rather than being told the case had no labels at all.
    assert resolved_labels == tuple(sorted(labels))


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


@pytest.mark.unittest
def test_registry_fields_are_all_hardened_against_hostile_input() -> None:
    """Hold the registry's own field list to its hardening tests.

    The impostor sweep in test/bmc/test_explanation.py skips this class: it is a
    path-keyed registry rather than a published core field, so it has no
    per-field JSON contract for that sweep to check.  That skip is only safe
    while every field it does have is hardened here.  This test names the fields
    it knows about, so a field added later fails until someone decides how a
    hostile value for it must be refused.
    """
    import dataclasses

    known = {
        # Every value is normalized and every key stored as exact text; a key
        # that collides after canonicalization is refused.
        "documents",
        # Sliced to a display path; a path the registry never held cannot be
        # published.
        "display_root",
        # Same treatment as ``documents``, on the query side.
        "query_documents",
    }
    actual = {field.name for field in dataclasses.fields(SourceDocumentRegistry)}
    assert actual == known, (
        "SourceDocumentRegistry gained or lost a field; decide how a hostile "
        "value for it is refused, add a test, then update this list"
    )

    well_formed = {"a.fcstm": "state A;"}

    # Both document maps refuse a non-string body and a non-string path key, and
    # each says which map it was: a shared message would let a query-side bug be
    # read as a machine-side one.
    with pytest.raises(TypeError, match="source document text must be strings"):
        SourceDocumentRegistry({"a.fcstm": 1})
    with pytest.raises(ValueError, match="source document paths must be"):
        SourceDocumentRegistry({1: "state A;"})
    with pytest.raises(TypeError, match="query document text must be strings"):
        SourceDocumentRegistry(well_formed, query_documents={"q.fbmcq": 1})
    with pytest.raises(ValueError, match="query document paths must be"):
        SourceDocumentRegistry(well_formed, query_documents={1: "x"})

    # ``display_root`` is refused too, but by os.fspath rather than by a message
    # of the registry's own. That is recorded rather than asserted as good: the
    # rejection holds, and pinning the wording here would pin CPython's.
    with pytest.raises(TypeError):
        SourceDocumentRegistry(well_formed, display_root=5)


@pytest.mark.unittest
def test_stage_and_category_pairings_the_builder_emits() -> None:
    """Enumerate which stage and category pairings actually occur.

    Reasoning about a group by resolving its aggregate for some stage and
    category is only sound for pairings the builder emits.  Twice a rationale was
    written about a pairing that never occurs -- a transition group arriving
    through the assumptions stage, and a definedness group arriving through the
    kernel one -- because the aggregate function answers for any input, whether or
    not the builder produces it.

    This pins the pairings themselves, so a rationale can be checked against a
    list rather than against an assumption, and so a builder change that adds or
    drops one is visible here.
    """
    from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
    from pyfcstm.bmc.explanation import constraint_aggregate

    # A query that reaches every stage: an initializer, a where clause needing
    # definedness, a frame assumption, and a transition to reach.
    machine = load_state_machine_from_text(
        "def int x = 1;\ndef int y = 0;\n"
        "state Root { event Go; state A; state B; [*] -> A; A -> B :: Go; A -> B; }"
    )
    context = BmcEngine(machine).prepare(
        # The where clause and the assumption both divide, so definedness groups
        # are emitted from initialization and from assumptions -- the two places
        # the rationale compares.  Without the dividing assumption only one of
        # them appears and the comparison below would pass while checking half of
        # what it claims.
        'init state("Root.A") where x / y > 0; '
        'assume at 0: var("x") / var("y") > 0; '
        'check reach <= 2: active("Root.B");'
    )
    core = build_bmc_core_formula(context)
    # Every tracked group, not only the case groups: the assumption and
    # definedness groups live in the wider collection.
    pairings = sorted({(g.stage, g.category) for g in core._tracked_groups})

    stages_by_prefix = {}
    for stage, category in pairings:
        stages_by_prefix.setdefault(category.split(".")[0], set()).add(stage)

    # A transition group is always a kernel-stage group, so its aggregate is
    # "transition" and the rendered noun and the aggregate happen to agree.
    assert stages_by_prefix["transition"] == {"kernel"}
    assert constraint_aggregate("kernel", "transition.step") == "transition"

    # A definedness group never comes from the kernel stage, and it does come
    # from both of the others.  Asserting the set rather than testing for
    # membership keeps this from passing when the query stops reaching one of
    # them: the rationale compares the two aggregates, so both have to be here.
    assert stages_by_prefix["definedness"] == {"initialization", "assumptions"}
    assert {
        stage: constraint_aggregate(stage, "definedness")
        for stage in stages_by_prefix["definedness"]
    } == {"initialization": "initial", "assumptions": "environment"}

    # An assumption group's aggregate is a word no reader sees elsewhere.
    assert stages_by_prefix["assumption"] == {"assumptions"}
    assert constraint_aggregate("assumptions", "assumption.frame") == "environment"
