"""Tests for the public Python diagram facade and browser contract."""

import json
import re

import pytest

from pyfcstm.diagram import (
    DiagramData,
    DiagramOptions,
    DiagramUnavailableError,
    DiagramViewState,
)
from pyfcstm.model import State, StateMachine, load_state_machine_from_text


def _model(source):
    return load_state_machine_from_text(source)


def test_portable_data_is_deterministic_and_has_no_editor_metadata():
    first = _model("state Root { state Idle; state Run; [*] -> Idle; Idle -> Run; }")
    second = _model("\nstate Root {\n state Idle;\n state Run;\n [*] -> Idle;\n Idle -> Run;\n}\n")

    first_json = first.diagram().to_json()
    second_json = second.diagram().to_json()
    assert json.loads(first_json) == json.loads(second_json)
    assert "range" not in first_json
    assert "source_path" not in first_json
    assert "filePath" not in first_json
    transition_ids = [item["id"] for item in first.diagram().to_dict()["rootState"]["transitions"]]
    assert transition_ids == ["Root::transition::0", "Root::transition::1"]


def test_source_sidecar_and_three_browser_modes_are_embedded():
    source = "state Root { state Idle; [*] -> Idle; }"
    model = _model(source)
    html = model.diagram(view_state=DiagramViewState(mode="compare")).to_html()
    assert "Content-Security-Policy" in html
    assert "fcstm-source-line" in html
    assert "standaloneMode" in html
    assert "standaloneViewState" in html
    assert "standaloneDiagram" in html
    assert "sourceMap" in html
    assert str(model.source_path) not in html


def test_diagram_options_reach_standalone_colour_preferences():
    model = _model("state Root;")
    html = model.diagram(options=DiagramOptions(palette="nord", mode="dark")).to_html()
    match = re.search(r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>", html, re.DOTALL)
    assert match is not None
    state = json.loads(match.group(1))
    assert state["palette"] == "nord"
    assert state["colorMode"] == "dark"


def test_diagram_options_default_to_browser_preferences_and_allow_auto_mode():
    model = _model("state Root;")
    html = model.diagram().to_html()
    match = re.search(r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>", html, re.DOTALL)
    assert match is not None
    state = json.loads(match.group(1))
    assert "palette" not in state
    assert "colorMode" not in state
    assert DiagramOptions(mode="auto").mode == "auto"


def test_source_highlighting_preserves_multiline_token_state():
    from pyfcstm.diagram.api import _highlight_source

    rendered = _highlight_source("/* first line\nsecond line */\nstate Root;")
    assert rendered.count('class="fcstm-source-line"') == 3
    assert "second line" in rendered
    assert "&lt;" not in rendered


def test_source_line_mapping_prefers_transition_ranges():
    source = """state Root {
    state Idle;
    state Run;
    [*] -> Idle;
    Idle -> Run;
}"""
    html = _model(source).diagram().to_html()
    match = re.search(r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>", html, re.DOTALL)
    assert match is not None
    state = json.loads(match.group(1))
    transition_id = state["sourceLineMap"]["4"]
    assert transition_id == "Root::transition::1"
    assert state["sourceMap"][transition_id]["kind"] == "transition"


def test_model_show_returns_html_path_without_opening_browser(tmp_path):
    model = _model("state Root;")
    output = model.show(
        tmp_path / "diagram.html",
        open_browser=False,
        options={"mode": "dark"},
        view_state={"mode": "fcstm"},
        source_text="state Root;",
    )
    assert output.exists()
    assert output.suffix == ".html"
    content = output.read_text(encoding="utf-8")
    assert "FCSTM" in content
    assert '"standaloneMode":"fcstm"' in content
    assert '"colorMode":"dark"' in content


def test_model_diagram_and_show_accept_option_keywords(tmp_path):
    model = _model("state Root;")
    diagram = model.diagram(mode="dark", palette="nord", cjk_locale="tc")
    assert diagram.options.mode == "dark"
    assert diagram.options.palette == "nord"
    assert diagram.options.cjk_locale == "tc"

    output = model.show(
        tmp_path / "keyword-options.html",
        open_browser=False,
        mode="dark",
        view_state={"mode": "fcstm"},
    )
    assert output.exists()
    assert '"standaloneMode":"fcstm"' in output.read_text(encoding="utf-8")


def test_html_cache_and_save_replace_are_deterministic(tmp_path):
    diagram = _model("state Root;").diagram()
    first = diagram.to_html()
    second = diagram.to_html()
    assert first == second
    assert len(diagram._html_cache) == 1
    output = tmp_path / "diagram.json"
    diagram.save(output)
    assert output.read_text(encoding="utf-8").endswith("\n")
    diagram.save(output)
    assert not list(tmp_path.glob(".diagram.json.*"))


def test_combo_relay_is_explicit_model_data():
    state = State(name="__combo_relay", path=("Root", "__combo_relay"), substates={}, is_pseudo=True, is_combo_relay=True)
    assert state.is_combo_relay is True


def test_diagram_value_objects_reject_unknown_values_and_copy_sequences():
    with pytest.raises(ValueError):
        DiagramOptions(palette="unknown")
    with pytest.raises(ValueError):
        DiagramViewState(mode="unknown")
    state = DiagramViewState(collapsed_state_ids=["Root.Child"])
    assert state.collapsed_state_ids == ("Root.Child",)
    assert DiagramOptions(cjk_locale="JP").to_dict()["cjkLocale"] == "jp"


def test_view_state_rejects_boolean_numeric_values():
    with pytest.raises(ValueError, match="zoom must be a finite positive number"):
        DiagramViewState(zoom=True)
    with pytest.raises(ValueError, match="pan offsets must be finite numbers"):
        DiagramViewState(pan_x=True)
    with pytest.raises(ValueError, match="pan offsets must be finite numbers"):
        DiagramViewState(pan_y=False)


def test_diagram_derivation_methods_return_independent_snapshots():
    model = _model("state Root;")
    original = model.diagram()
    changed_options = original.with_options({"mode": "dark"})
    changed_view = original.with_view_state({"mode": "fcstm", "zoom": 1.5})

    assert original.options.mode is None
    assert original.view_state.mode == "compare"
    assert changed_options.options.mode == "dark"
    assert changed_options.view_state == original.view_state
    assert changed_view.view_state.mode == "fcstm"
    assert changed_view.view_state.zoom == 1.5
    assert changed_view.options == original.options


def test_save_rejects_non_default_scale_for_non_png_formats(tmp_path):
    diagram = _model("state Root;").diagram()
    with pytest.raises(ValueError, match="scale is only supported for PNG"):
        diagram.save(tmp_path / "diagram.json", scale=2)
    with pytest.raises(ValueError, match="scale is only supported for PNG"):
        diagram.save(tmp_path / "diagram.html", scale=2)
    with pytest.raises(ValueError, match="scale is only supported for PNG"):
        diagram.save(tmp_path / "diagram.svg", scale=2)
    with pytest.raises(ValueError, match="scale is only supported for PNG"):
        diagram.save(tmp_path / "diagram.pdf", scale=2)


def test_diagram_mapping_inputs_fail_closed_on_unknown_or_ambiguous_fields():
    model = _model("state Root;")
    with pytest.raises(ValueError, match="unknown DiagramOptions field"):
        model.diagram(options={"palette": "default", "typo": True})
    with pytest.raises(ValueError, match="detail_level and detailLevel"):
        model.diagram(options={"detail_level": "normal", "detailLevel": "normal"})
    with pytest.raises(ValueError, match="unknown DiagramViewState field"):
        model.diagram(view_state={"mode": "compare", "typo": True})


def test_headless_exports_are_typed_unavailable_until_delivery_stage():
    diagram = _model("state Root;").diagram()
    with pytest.raises(DiagramUnavailableError, match="headless SVG"):
        diagram.to_svg()
    with pytest.raises(DiagramUnavailableError, match="headless PNG"):
        diagram.to_png()
    with pytest.raises(DiagramUnavailableError, match="headless PDF"):
        diagram.to_pdf()
    with pytest.raises(ValueError, match="finite positive"):
        diagram.to_png(scale=0)
    with pytest.raises(ValueError, match="finite positive"):
        diagram.to_png(scale=None)
    with pytest.raises(ValueError, match="finite positive"):
        diagram.to_png(scale=True)
    with pytest.raises(DiagramUnavailableError, match="headless PNG"):
        diagram.save("diagram.png", scale=2)


def test_diagram_data_rejects_non_mapping_snapshots():
    with pytest.raises(TypeError, match="must be a mapping"):
        DiagramData([("kind", "diagram")])


def test_diagram_data_snapshot_is_not_mutable():
    data = _model("state Root;").diagram().data
    with pytest.raises(TypeError):
        data.value["kind"] = "changed"


def test_diagram_data_hash_matches_equal_immutable_snapshots():
    first = _model("state Root;").diagram().data
    second = _model("state Root;").diagram().data
    assert first == second
    assert hash(first) == hash(second)


def test_imported_source_ranges_keep_document_identity(tmp_path):
    child = tmp_path / "child.fcstm"
    child.write_text("state ChildRoot { state Idle; [*] -> Idle; }", encoding="utf-8")
    root = tmp_path / "main.fcstm"
    root.write_text(
        'state Root { import "./child.fcstm" as Child; [*] -> Child; }',
        encoding="utf-8",
    )
    state = load_state_machine_from_text(root.read_text(encoding="utf-8"), path=str(root))
    html = state.diagram().to_html()
    assert '"sourceDocuments"' in html
    assert '"documentId":"child.fcstm"' in html
    assert '"documentId":"main.fcstm"' in html
    assert str(root) not in html
    assert str(child) not in html
    assert "_sourcePath" not in html


def test_imported_source_line_map_contains_child_document_lines(tmp_path):
    child = tmp_path / "child.fcstm"
    child.write_text("state ChildRoot { state Idle; [*] -> Idle; }", encoding="utf-8")
    root = tmp_path / "main.fcstm"
    root.write_text(
        'state Root { import "./child.fcstm" as Child; [*] -> Child; }',
        encoding="utf-8",
    )
    model = load_state_machine_from_text(root.read_text(encoding="utf-8"), path=str(root))
    html = model.diagram().to_html()
    match = re.search(r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>", html, re.DOTALL)
    assert match is not None
    state = json.loads(match.group(1))
    child_lines = [key for key in state["sourceLineMap"] if key.startswith("child.fcstm:")]
    assert child_lines
    assert all(state["sourceLineMap"][key] for key in child_lines)


def test_imported_documents_with_duplicate_basenames_keep_distinct_ids(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "a" / "child.fcstm").write_text(
        "state AChild { state Idle; [*] -> Idle; }", encoding="utf-8"
    )
    (tmp_path / "b" / "child.fcstm").write_text(
        "state BChild { state Idle; [*] -> Idle; }", encoding="utf-8"
    )
    root = tmp_path / "main.fcstm"
    root.write_text(
        'state Root { import "./a/child.fcstm" as A; '
        'import "./b/child.fcstm" as B; [*] -> A; }',
        encoding="utf-8",
    )
    model = load_state_machine_from_text(root.read_text(encoding="utf-8"), path=str(root))
    html = model.diagram().to_html()
    match = re.search(r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>", html, re.DOTALL)
    assert match is not None
    state = json.loads(match.group(1))
    documents = state["sourceDocuments"]
    assert "a/child.fcstm" in documents
    assert "b/child.fcstm" in documents
    assert documents["a/child.fcstm"]["html"] != documents["b/child.fcstm"]["html"]


def test_source_line_map_preserves_multiple_items_on_one_line():
    model = _model("state Root { state A; state B; state C; [*] -> A; A -> B; A -> C; }")
    html = model.diagram().to_html()
    match = re.search(r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>", html, re.DOTALL)
    assert match is not None
    state = json.loads(match.group(1))
    line_value = state["sourceLineMap"]["0"]
    assert isinstance(line_value, list)
    assert len(line_value) >= 3
    assert all(item in state["sourceMap"] for item in line_value)
    assert {state["sourceMap"][item]["kind"] for item in line_value} >= {"state", "transition"}
    assert "pyfcstm:0" not in state["sourceLineMap"]


def test_programmatic_model_exposes_source_unavailable_state():
    model = StateMachine(defines={}, root_state=State(name="Root", path=("Root",), substates={}))
    html = model.diagram().to_html()
    assert "sourceUnavailableReason" in html


def test_browser_sidecar_does_not_mutate_source_documents(tmp_path):
    main_path = tmp_path / "main.fcstm"
    child_path = tmp_path / "child.fcstm"
    model = StateMachine(
        defines={},
        root_state=State(name="Root", path=("Root",), substates={}),
        source_text="state Root;",
        source_path=str(main_path),
        _source_documents={str(child_path): "state Child;"},
    )
    before = dict(model._source_documents)
    model.diagram().to_html()
    assert model._source_documents == before


def test_html_escapes_hostile_source_before_bootstrap_script():
    model = _model('state Root named "</script><script>bad";')
    html = model.diagram().to_html()
    assert "</script><script>bad" not in html


def test_html_escapes_javascript_line_separators_before_bootstrap_script():
    model = _model('state Root named "test\u2028line\u2029break";')
    html = model.diagram().to_html()
    assert "\u2028" not in html.split("</script>", 1)[0]
    assert "\u2029" not in html.split("</script>", 1)[0]
    assert "\\u2028" in html
    assert "\\u2029" in html
