"""Tests for the public Python diagram facade and browser contract."""

import json
import os
from pathlib import Path
import re
import stat
import sys
import warnings

import pytest

from pyfcstm.diagram import (
    DiagramAssetError,
    DiagramData,
    DiagramOptions,
    DiagramUnavailableError,
    DiagramViewState,
)
from pyfcstm.model import State, StateMachine, load_state_machine_from_text


def _model(source):
    return load_state_machine_from_text(source)


@pytest.mark.parametrize(
    ("resource", "payload", "message"),
    [
        ("viewer.js", b"\xff", "not valid UTF-8"),
        ("fonts/JetBrainsMono-Regular.ttf", b"bad-font", "OpenType"),
        ("resvg.wasm", b"\x00asm\x01\x00\x00\x00", "WebAssembly"),
    ],
)
def test_html_resource_failures_are_actionable(monkeypatch, resource, payload, message):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_get_data = engine_module.pkgutil.get_data

    def corrupted_resource(package, name):
        if name == resource:
            return payload
        return real_get_data(package, name)

    monkeypatch.setattr(engine_module.pkgutil, "get_data", corrupted_resource)
    with pytest.raises(DiagramAssetError, match=message):
        _model("state Root;").diagram().to_html()


def test_html_resource_failure_reports_issue_url_outside_checkout(monkeypatch):
    import importlib

    engine_module = importlib.import_module("pyfcstm.diagram.engine")
    real_get_data = engine_module.pkgutil.get_data

    def missing_viewer(package, resource):
        if resource == "viewer.js":
            return None
        return real_get_data(package, resource)

    monkeypatch.setattr(engine_module.pkgutil, "get_data", missing_viewer)
    monkeypatch.setattr(engine_module, "_is_development_checkout", lambda: False)
    with pytest.raises(
        DiagramAssetError,
        match="https://github.com/HansBug/pyfcstm/issues",
    ):
        _model("state Root;").diagram().to_html()


def test_portable_data_is_deterministic_and_has_no_editor_metadata():
    first = _model("state Root { state Idle; state Run; [*] -> Idle; Idle -> Run; }")
    second = _model(
        "\nstate Root {\n state Idle;\n state Run;\n [*] -> Idle;\n Idle -> Run;\n}\n"
    )

    first_json = first.diagram().to_json()
    second_json = second.diagram().to_json()
    assert json.loads(first_json) == json.loads(second_json)
    assert "range" not in first_json
    assert "source_path" not in first_json
    assert "filePath" not in first_json
    transition_ids = [
        item["id"] for item in first.diagram().to_dict()["rootState"]["transitions"]
    ]
    assert transition_ids == ["Root::transition::0", "Root::transition::1"]


def test_public_diagram_data_value_is_portable_and_immutable():
    diagram = _model("state Root;").diagram()
    value = diagram.data.value
    assert "filePath" not in value
    assert "range" not in json.dumps(diagram.to_dict(), ensure_ascii=False)
    with pytest.raises(TypeError):
        value["kind"] = "changed"


def test_diagram_derivations_keep_the_original_model_snapshot():
    model = _model("state Root;")
    diagram = model.diagram()
    model.root_state.name = "Changed"

    derived = diagram.with_options(mode="dark")
    assert diagram.to_dict()["rootState"]["name"] == "Root"
    assert derived.to_dict()["rootState"]["name"] == "Root"

    match = re.search(
        r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>",
        diagram.to_html(),
        re.DOTALL,
    )
    assert match is not None
    assert json.loads(match.group(1))["title"] == "Root"


def test_source_text_override_rejects_line_layout_changes():
    model = _model("state Root;")
    with pytest.raises(ValueError, match="does not match the source"):
        model.diagram(source_text="state Other;")


def test_state_ids_match_shared_renderer_qualified_paths():
    source = "state Root { state Slash; state Tilde; [*] -> Slash; }"
    model = _model(source)
    model.root_state.substates["Slash"].name = "a/b"
    model.root_state.substates["Slash"].path = ("Root", "a/b")
    model.root_state.substates["Tilde"].name = "a~b"
    model.root_state.substates["Tilde"].path = ("Root", "a~b")
    children = model.diagram().to_dict()["rootState"]["children"]
    assert {item["id"] for item in children} == {"Root.a/b", "Root.a~b"}


def test_mapping_view_state_rejects_boolean_numbers():
    with pytest.raises(ValueError, match="finite positive number"):
        _model("state Root;").diagram(view_state={"zoom": True})


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
    match = re.search(
        r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>", html, re.DOTALL
    )
    assert match is not None
    state = json.loads(match.group(1))
    assert state["palette"] == "nord"
    assert state["colorMode"] == "dark"


def test_html_language_is_the_interface_language():
    assert (
        '<html lang="en">' in _model("state Root;").diagram(cjk_locale="jp").to_html()
    )


def test_diagram_options_default_to_browser_preferences_and_allow_auto_mode():
    model = _model("state Root;")
    html = model.diagram().to_html()
    match = re.search(
        r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>", html, re.DOTALL
    )
    assert match is not None
    state = json.loads(match.group(1))
    assert "palette" not in state
    assert "colorMode" not in state
    assert DiagramOptions(mode="auto").mode == "auto"


def test_source_highlighting_preserves_multiline_token_state():
    from pyfcstm.diagram.api import _highlight_source

    rendered = _highlight_source("/* first line\nsecond line */\nstate Root;")
    assert rendered.count('class="fcstm-source-line"') == 3
    assert 'data-line-number="1"' in rendered
    assert 'data-line-number="3"' in rendered
    assert '</span>\n<span class="fcstm-source-line"' in rendered
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
    match = re.search(
        r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>", html, re.DOTALL
    )
    assert match is not None
    state = json.loads(match.group(1))
    transition_id = state["sourceLineMap"]["4"]
    assert transition_id == "Root::transition::1"
    assert state["sourceMap"][transition_id]["kind"] == "transition"


def test_model_show_returns_html_path_without_opening_window(tmp_path):
    model = _model("state Root;")
    output = model.show(
        tmp_path / "diagram.html",
        open_window=False,
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
        open_window=False,
        mode="dark",
        view_state={"mode": "fcstm"},
    )
    assert output.exists()
    assert '"standaloneMode":"fcstm"' in output.read_text(encoding="utf-8")


def test_show_launches_a_standalone_app_window(monkeypatch, tmp_path):
    import pyfcstm.diagram.api as diagram_api

    calls = []

    def fake_popen(command, **kwargs):
        calls.append((command, kwargs))
        return object()

    monkeypatch.setattr(diagram_api, "_browser_app_executable", lambda: "/opt/chrome")
    monkeypatch.setattr(diagram_api.subprocess, "Popen", fake_popen)
    output = _model("state Root;").show(
        tmp_path / "window.html", open_window=True, window_size=(960, 640)
    )
    assert output.exists()
    assert len(calls) == 1
    command, kwargs = calls[0]
    assert command[0] == "/opt/chrome"
    assert command[1].startswith("--app=file://")
    assert "--new-window" in command
    assert "--window-size=960,640" in command
    assert kwargs["stdin"] is diagram_api.subprocess.DEVNULL


def test_show_rejects_invalid_window_size(tmp_path):
    with pytest.raises(ValueError, match="window_size"):
        _model("state Root;").show(
            tmp_path / "window.html", open_window=False, window_size=(0, 640)
        )


def test_show_reports_missing_app_browser(monkeypatch, tmp_path):
    import pyfcstm.diagram.api as diagram_api

    monkeypatch.setattr(diagram_api, "_browser_app_executable", lambda: None)
    with pytest.raises(DiagramUnavailableError, match="Chromium-family browser"):
        _model("state Root;").show(tmp_path / "window.html", open_window=True)


def test_html_cache_and_save_replace_are_deterministic(tmp_path):
    diagram = _model("state Root;").diagram()
    first = diagram.to_html()
    second = diagram.to_html()
    assert first == second
    # Identity, not equality: the second call must reuse the memoised document
    # rather than spending another full build to produce an equal one.
    assert first is second
    output = tmp_path / "diagram.json"
    diagram.save(output)
    assert output.read_text(encoding="utf-8").endswith("\n")
    diagram.save(output)
    assert not list(tmp_path.glob(".diagram.json.*"))


def test_combo_relay_is_explicit_model_data():
    state = State(
        name="__combo_relay",
        path=("Root", "__combo_relay"),
        substates={},
        is_pseudo=True,
        is_combo_relay=True,
    )
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
    # The axis is named so a caller with two pan values knows which one failed.
    with pytest.raises(ValueError, match="pan_x offsets must be finite numbers"):
        DiagramViewState(pan_x=True)
    with pytest.raises(ValueError, match="pan_y offsets must be finite numbers"):
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
    state = load_state_machine_from_text(
        root.read_text(encoding="utf-8"), path=str(root)
    )
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
    model = load_state_machine_from_text(
        root.read_text(encoding="utf-8"), path=str(root)
    )
    html = model.diagram().to_html()
    match = re.search(
        r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>", html, re.DOTALL
    )
    assert match is not None
    state = json.loads(match.group(1))
    child_lines = [
        key for key in state["sourceLineMap"] if key.startswith("child.fcstm:")
    ]
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
    model = load_state_machine_from_text(
        root.read_text(encoding="utf-8"), path=str(root)
    )
    html = model.diagram().to_html()
    match = re.search(
        r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>", html, re.DOTALL
    )
    assert match is not None
    state = json.loads(match.group(1))
    documents = state["sourceDocuments"]
    assert "a/child.fcstm" in documents
    assert "b/child.fcstm" in documents
    assert documents["a/child.fcstm"]["html"] != documents["b/child.fcstm"]["html"]


def test_source_line_map_preserves_multiple_items_on_one_line():
    model = _model(
        "state Root { state A; state B; state C; [*] -> A; A -> B; A -> C; }"
    )
    html = model.diagram().to_html()
    match = re.search(
        r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>", html, re.DOTALL
    )
    assert match is not None
    state = json.loads(match.group(1))
    line_value = state["sourceLineMap"]["0"]
    assert isinstance(line_value, list)
    assert len(line_value) >= 3
    assert all(item in state["sourceMap"] for item in line_value)
    assert {state["sourceMap"][item]["kind"] for item in line_value} >= {
        "state",
        "transition",
    }
    assert "pyfcstm:0" not in state["sourceLineMap"]


def test_programmatic_model_exposes_source_unavailable_state():
    model = StateMachine(
        defines={}, root_state=State(name="Root", path=("Root",), substates={})
    )
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


def _wasm_section(section_id, body=b"\x00"):
    """Build one minimal WASM section with a single-byte LEB128 size."""
    assert len(body) < 0x80
    return bytes([section_id, len(body)]) + body


def _wasm_module(section_ids):
    """Build a WASM envelope carrying the requested sections in order."""
    payload = b"\x00asm\x01\x00\x00\x00"
    for section_id in section_ids:
        payload += _wasm_section(section_id)
    return payload


@pytest.mark.unittest
def test_wasm_envelope_accepts_the_specified_section_order():
    from pyfcstm.diagram.engine import _valid_wasm_envelope

    # Type, Function, Export and Code are the sections the viewer binding needs.
    assert _valid_wasm_envelope(_wasm_module([1, 3, 7, 10]))
    # DataCount is section id 12 but the binary format places it between
    # Element (9) and Code (10), so raw id ordering must not reject it.
    assert _valid_wasm_envelope(_wasm_module([1, 3, 7, 9, 12, 10, 11]))
    # Custom sections (id 0) may repeat anywhere in the stream.
    assert _valid_wasm_envelope(_wasm_module([0, 1, 3, 0, 7, 10, 0]))


@pytest.mark.unittest
def test_wasm_envelope_rejects_broken_binaries():
    from pyfcstm.diagram.engine import _valid_wasm_envelope

    assert not _valid_wasm_envelope(b"\x00asm\x01\x00\x00\x00")
    assert not _valid_wasm_envelope(b"\x00asm\x02\x00\x00\x00" + _wasm_section(1))
    # Out-of-order sections, duplicates and unknown ids stay rejected.
    assert not _valid_wasm_envelope(_wasm_module([3, 1, 7, 10]))
    assert not _valid_wasm_envelope(_wasm_module([1, 1, 3, 7, 10]))
    assert not _valid_wasm_envelope(_wasm_module([1, 3, 7, 10, 13]))
    # A truncated final section must not pass as a complete envelope.
    assert not _valid_wasm_envelope(_wasm_module([1, 3, 7, 10])[:-1])


@pytest.mark.unittest
def test_line_ending_equivalent_override_keeps_imported_documents(tmp_path):
    """A CRLF copy of the model source must not drop imported documents."""
    main_path = tmp_path / "main.fcstm"
    child_path = tmp_path / "child.fcstm"
    source = "state Root;\n"
    model = StateMachine(
        defines={},
        root_state=State(name="Root", path=("Root",), substates={}),
        source_text=source,
        source_path=str(main_path),
        _source_documents={str(main_path): source, str(child_path): "state Child;\n"},
    )
    baseline = model.diagram().to_html()
    override = model.diagram(source_text=source.replace("\n", "\r\n")).to_html()
    assert '"child.fcstm"' in baseline
    assert '"child.fcstm"' in override


@pytest.mark.unittest
def test_diagram_data_hash_is_stable_across_processes():
    """A persisted content key must not depend on PYTHONHASHSEED."""
    import subprocess

    script = (
        "from pyfcstm.model import load_state_machine_from_text as load;"
        "print(hash(load('state Root;').diagram().data))"
    )
    digests = set()
    for seed in ("0", "1", "12345"):
        environment = dict(os.environ, PYTHONHASHSEED=seed)
        result = subprocess.run(
            [sys.executable, "-c", script],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        digests.add(result.stdout.strip())
    assert len(digests) == 1


@pytest.mark.unittest
def test_derived_snapshots_can_still_render_html():
    """Derived views copy every field the HTML document consumes."""
    model = _model('state Root { state Idle named "空闲"; [*] -> Idle; }')
    original = model.diagram()
    derived = original.with_options(mode="dark").with_view_state(mode="diagram")
    document = derived.to_html()
    baseline = original.to_html()
    assert document.startswith("<!doctype html>")
    assert '"colorMode":"dark"' in document
    assert derived.data is original.data
    # The clone copies its fields one by one, so the source-link payload has to
    # be asserted explicitly; otherwise a dropped field only breaks at runtime.
    for field in ("sourceMap", "sourceLineMap", "sourceDocumentId", "sourceHtml"):
        marker = '"%s":' % field
        assert marker in document
        assert document.split(marker, 1)[1][:80] == baseline.split(marker, 1)[1][:80]
    assert derived.source_text == original.source_text


@pytest.mark.unittest
@pytest.mark.parametrize("locale", ["sc", "tc", "hk", "jp", "kr"])
def test_font_locale_never_changes_the_document_language(locale):
    """The interface is English, so no CJK font choice may relabel the document."""
    html = _model("state Root;").diagram(cjk_locale=locale).to_html()
    assert '<html lang="en">' in html
    for leaked in (
        'lang="zh-CN"',
        'lang="zh-TW"',
        'lang="zh-HK"',
        'lang="ja"',
        'lang="ko"',
    ):
        assert leaked not in html


@pytest.mark.unittest
def test_source_text_override_accepts_the_modelled_source():
    """An override equal to the model source stays a supported input."""
    source = 'state Root { state Idle named "空闲"; [*] -> Idle; }'
    model = _model(source)
    assert model.diagram(source_text=source).to_html()
    # Programmatic models keep accepting an override because they have no
    # ranges that the replacement text could invalidate.
    programmatic = StateMachine(
        defines={},
        root_state=State(name="Root", path=("Root",), substates={}),
    )
    assert programmatic.diagram(source_text="state Root;").to_html()


def _browser_view_state(html):
    match = re.search(
        r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>", html, re.DOTALL
    )
    assert match is not None
    return json.loads(match.group(1))["standaloneViewState"]


@pytest.mark.unittest
def test_absent_view_transform_stays_distinguishable_from_an_explicit_one():
    """The viewer must tell "no preference" from a literal 100% at the origin.

    Both were once spelled ``zoom=1.0, pan_x=0.0, pan_y=0.0``, so the viewer
    could only guess which one the caller meant, and one of the two intents was
    unreachable whichever way it guessed.
    """
    model = _model("state Root;")
    default = model.diagram()
    assert default.view_state.zoom is None
    assert default.view_state.pan_x is None
    assert default.view_state.pan_y is None
    assert _browser_view_state(default.to_html()) == {
        "zoom": None,
        "panX": None,
        "panY": None,
    }

    explicit = model.diagram().with_view_state(zoom=1.0, pan_x=0.0, pan_y=0.0)
    assert _browser_view_state(explicit.to_html()) == {
        "zoom": 1.0,
        "panX": 0.0,
        "panY": 0.0,
    }

    # Choosing a mode is not a framing request, so it must not silently pin the
    # transform and reintroduce the clipped first paint.
    mode_only = model.diagram().with_view_state(mode="fcstm")
    assert mode_only.view_state.mode == "fcstm"
    assert _browser_view_state(mode_only.to_html()) == {
        "zoom": None,
        "panX": None,
        "panY": None,
    }


@pytest.mark.unittest
@pytest.mark.parametrize("field", ["zoom", "pan_x", "pan_y"])
def test_view_transform_fields_still_reject_invalid_numbers(field):
    """Optional does not mean unchecked: only ``None`` is a new valid input."""
    invalid = [True, float("nan"), float("inf")]
    if field == "zoom":
        invalid += [0, -1]
    for value in invalid:
        with pytest.raises((ValueError, TypeError)):
            DiagramViewState(**{field: value})


@pytest.mark.unittest
def test_keyword_form_updates_only_the_named_fields():
    """``with_options`` reads like ``dataclasses.replace``, so it must behave so.

    Treating the keyword form as a whole-object replacement silently reset every
    field the caller did not repeat, which changed the rendering direction and
    the embedded font of a snapshot that only asked to switch colour mode.
    """
    model = _model("state Root;")
    base = model.diagram(direction="LR", cjk_locale="jp")
    updated = base.with_options(mode="dark")
    assert updated.options.mode == "dark"
    assert updated.options.direction == "LR"
    assert updated.options.cjk_locale == "jp"
    # camelCase spellings reach the same field.
    assert base.with_options(cjkLocale="kr").options.direction == "LR"
    # A positional value still replaces wholesale, which is what it documents.
    assert base.with_options({"direction": "TB"}).options.cjk_locale == "sc"

    view = model.diagram(view_state={"mode": "diagram", "zoom": 2.0})
    moved = view.with_view_state(pan_x=10)
    assert moved.view_state.pan_x == 10.0
    assert moved.view_state.mode == "diagram"
    assert moved.view_state.zoom == 2.0


@pytest.mark.unittest
def test_collapsed_state_ids_rejects_a_single_id_and_non_strings():
    """``str`` is iterable, so one mistyped ID became one ID per character."""
    with pytest.raises(TypeError):
        DiagramViewState(collapsed_state_ids="Root.Run")
    with pytest.raises(TypeError):
        DiagramViewState(collapsed_state_ids=5)
    with pytest.raises(TypeError):
        DiagramViewState(collapsed_state_ids=["Root.Run", None])
    assert DiagramViewState(collapsed_state_ids=["Root.Run"]).collapsed_state_ids == (
        "Root.Run",
    )


@pytest.mark.unittest
def test_source_linking_requires_ranges_not_just_text():
    """Source text without ranges is a pane where nothing responds."""
    programmatic = StateMachine(
        defines={},
        root_state=State(name="Root", path=("Root",), substates={}),
    )
    state = json.loads(
        re.search(
            r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>",
            programmatic.diagram(source_text="state Root;").to_html(),
            re.DOTALL,
        ).group(1)
    )
    assert state["sourceAvailable"] is False
    assert "no source ranges" in state["sourceUnavailableReason"]

    parsed = json.loads(
        re.search(
            r"window\.__FCSTM_INITIAL_STATE__ = (.*?);</script><script>",
            _model("state Root;").diagram().to_html(),
            re.DOTALL,
        ).group(1)
    )
    assert parsed["sourceAvailable"] is True
    assert parsed["sourceUnavailableReason"] == ""


@pytest.mark.unittest
def test_snapshots_reject_attribute_assignment():
    """The class documents an immutable snapshot, so the container must be one."""
    view = _model("state Root;").diagram()
    for name in ("options", "data", "model", "view_state"):
        with pytest.raises(AttributeError):
            setattr(view, name, None)
    # Deriving still works and does not alias the parent's source metadata.
    derived = view.with_options(mode="dark")
    assert derived.options.mode == "dark"
    assert derived._source_map is not view._source_map


@pytest.mark.unittest
def test_a_shown_viewer_does_not_accumulate():
    """Repeats must reuse one file, and the window's copy must outlive us.

    A cleanup hook once made ``pyfcstm diagram --open`` open a window onto a
    file that no longer existed, because the browser is launched detached and
    reads the document after the command has exited. Keeping every file instead
    traded that for ~30 MB per call, so the name is derived from the document.
    """
    from pyfcstm.diagram import api as diagram_api

    model = _model("state Root { state Idle; state Busy; [*] -> Idle; Idle -> Busy; }")
    document = model.diagram().to_html()
    first = diagram_api._temporary_viewer_path(document, for_window=True)
    assert diagram_api._temporary_viewer_path(document, for_window=True) == first
    other = diagram_api._temporary_viewer_path(
        _model("state Root;").diagram().to_html(), for_window=True
    )
    assert other != first, "different diagrams need different files"


@pytest.mark.unittest
def test_a_temporary_viewer_is_private_and_process_scoped():
    """The viewer embeds the model's own source into a world-readable directory.

    Deriving the name from the document made it predictable, and dropping the
    pre-created file removed the 0600 that had been protecting it by accident,
    so any local user could read another user's state machine. The mode is
    forced rather than preserved, which also stops a pre-created permissive file
    from lending its mode to fresh content.

    The name also has to say who owns the file. One shared content-derived name
    let an unrelated process rendering the same model delete, at its own exit,
    the document a live browser window was still reading.
    """
    import atexit as atexit_module

    from pyfcstm.diagram import api as diagram_api

    model = _model("state Root { state Secret; [*] -> Secret; }")
    document = model.diagram().to_html()
    windowed = diagram_api._temporary_viewer_path(document, for_window=True)
    scoped = diagram_api._temporary_viewer_path(document, for_window=False)
    assert windowed != scoped, "a window's document must not share a reapable name"
    assert str(os.getpid()) in scoped.name
    assert str(os.getpid()) not in windowed.name
    # Reusable across processes, which is what keeps repeats from accumulating.
    assert diagram_api._temporary_viewer_path(document, for_window=True) == windowed

    registered = []
    original = atexit_module.register
    diagram_api.atexit.register = lambda func, *args: registered.append((func, args))
    try:
        path = model.diagram().show(open_window=False)
    finally:
        diagram_api.atexit.register = original
    try:
        assert path == scoped
        # Windows cannot represent a POSIX mode, so it reports 0o666 here.
        if os.name != "nt":
            assert stat.S_IMODE(path.stat().st_mode) == 0o600
        assert "Secret" in path.read_text(encoding="utf-8")
        # The removal must be wired to interpreter exit, not merely callable.
        assert (diagram_api._remove_temporary_viewer, (path,)) in registered
        diagram_api._remove_temporary_viewer(path)
        assert not path.exists()
    finally:
        diagram_api._TEMPORARY_VIEWERS.discard(path)
        if path.exists():
            path.unlink()


@pytest.mark.unittest
def test_detail_level_reaches_the_renderer_preset():
    """A level that changes nothing is worse than no level at all.

    ``to_dict()`` used to spell out every key the preset governs, using what
    happened to be the ``normal`` values, and the renderer prefers an explicit
    value over its preset — so ``minimal`` and ``full`` rendered exactly like
    ``normal``. The preset-governed keys must be absent for the level to mean
    anything.
    """
    preset_governed = {
        "showVariableDefinitions",
        "showEvents",
        "showTransitionGuards",
        "showTransitionEffects",
        "transitionEffectMode",
        "eventVisualizationMode",
        "showStateEvents",
        "showStateActions",
    }
    for level in ("minimal", "normal", "full"):
        emitted = DiagramOptions(detail_level=level).to_dict()
        assert emitted["detailLevel"] == level
        assert preset_governed.isdisjoint(emitted), (
            "%s must leave the preset to the renderer" % level
        )
    # The keys no preset covers still have to be supplied.
    normal = DiagramOptions().to_dict()
    for name in ("direction", "cjkLocale", "eventNameFormat", "maxLabelLength"):
        assert name in normal


@pytest.mark.unittest
def test_diagram_data_equality_agrees_with_its_hash():
    """Equal objects must hash alike, and this value is identified by its bytes.

    The generated comparison used Python's numeric rules, where ``1`` equals
    ``1.0`` and ``True`` equals ``1``, while the hash came from the JSON text
    where those differ. Equal snapshots therefore missed each other in a dict
    and stacked up in a set.
    """
    root = {"kind": "diagram", "rootState": {"children": []}}
    for left, right in ((1, 1.0), (True, 1), (0, -0.0)):
        a = DiagramData(dict(root, probe=left))
        b = DiagramData(dict(root, probe=right))
        if a == b:
            assert hash(a) == hash(b), (left, right)
            assert len({a, b}) == 1, (left, right)
            assert {a: "x"}.get(b) == "x", (left, right)
        else:
            # Distinct JSON bytes are a distinct content key, which is the
            # contract this value advertises.
            assert len({a, b}) == 2, (left, right)
    same = DiagramData(dict(root, probe=1))
    assert same == DiagramData(dict(root, probe=1))
    assert hash(same) == hash(DiagramData(dict(root, probe=1)))
    assert same != root


@pytest.mark.unittest
def test_diagram_data_rejects_numbers_json_cannot_represent():
    """``to_json()`` promises JSON text, and no parser accepts NaN or infinity.

    Python writes them as bare ``NaN`` / ``Infinity`` tokens, so a document
    carrying them is rejected outright by the browser this data is built for.
    """
    root = {"kind": "diagram", "rootState": {"children": []}}
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="JSON numbers"):
            DiagramData(dict(root, probe=bad))
    # Ordinary numbers are unaffected, and the result really parses.
    ok = DiagramData(dict(root, probe=1.5))
    assert json.loads(ok.to_json())["probe"] == 1.5


def test_detail_level_is_recorded_and_leaves_the_diagram_data_alone():
    # The DiagramOptions docstring says the preset is stored rather than acted
    # on. Measured in Chrome across the three levels for a machine carrying a
    # state action and a transition effect: all render the same seven labels
    # ["Root", "A", "B", "\u25cf Go", "\u25b8 c = c + 1;", "c = c * 2;",
    # "\u25cf Back"], because the four settings the presets disagree on --
    # state event labels, state action labels, transition-effect placement and
    # event placement -- do not reach the standalone drawing path. What a unit
    # test can hold is the half that needs no browser: the value is carried
    # into the document, and the portable data does not vary with it.
    model = load_state_machine_from_text(
        "def int c = 0;\n"
        "state Root {\n"
        "    [*] -> A;\n"
        "    state A { enter { c = 1; } }\n"
        "    state B;\n"
        "    A -> B :: Go effect { c = c + 1; }\n"
        "}\n"
    )
    snapshots = set()
    for level in ("minimal", "normal", "full"):
        view = model.diagram(detail_level=level)
        assert view.options.to_dict()["detailLevel"] == level
        snapshots.add(view.to_json())
    assert len(snapshots) == 1, (
        "detail_level now changes the diagram data; the DiagramOptions "
        "docstring says it does not and has to be updated"
    )


def test_atomic_writes_remove_their_temporary_when_interrupted(tmp_path, monkeypatch):
    # Only OSError was cleaned up, so Ctrl-C part-way through a ~30 MB document
    # left the temporary sibling behind at full size. SIGKILL cannot be covered
    # from inside the process; an interrupt can.
    from pyfcstm.diagram import api

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(api, "_apply_target_mode", interrupt)
    for writer, payload, name in (
        (api._atomic_write_text, "x" * 4096, "page.html"),
        (api._atomic_write_bytes, b"x" * 4096, "image.png"),
    ):
        with pytest.raises(KeyboardInterrupt):
            writer(tmp_path / name, payload)
    assert sorted(item.name for item in tmp_path.iterdir()) == [], (
        "an interrupted atomic write must not leave its temporary sibling"
    )


def test_atomic_writes_still_report_a_failed_cleanup_with_both_causes(
    tmp_path, monkeypatch
):
    # The interrupt cleanup must not swallow the case where the write failed and
    # removing the temporary failed too: both reasons stay in the message.
    from pyfcstm.diagram import api

    def fail_mode(*_args, **_kwargs):
        raise OSError("mode could not be applied")

    def fail_unlink(self, *_args, **_kwargs):
        raise PermissionError("cannot unlink")

    monkeypatch.setattr(api, "_apply_target_mode", fail_mode)
    monkeypatch.setattr(Path, "unlink", fail_unlink)
    with pytest.raises(OSError) as caught:
        api._atomic_write_text(tmp_path / "page.html", "x")
    assert "mode could not be applied" in str(caught.value)
    assert "cannot unlink" in str(caught.value)


def test_atomic_writes_report_a_cleanup_they_could_not_perform(tmp_path, monkeypatch):
    # The cleanup cannot raise: doing so would replace the KeyboardInterrupt the
    # caller needs with a detail about a temporary file. Swallowing it silently
    # would leave a full-size file behind with nothing said, so it warns.
    from pyfcstm.diagram import api

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    def fail_unlink(self, *_args, **_kwargs):
        raise PermissionError("locked")

    monkeypatch.setattr(api, "_apply_target_mode", interrupt)
    monkeypatch.setattr(Path, "unlink", fail_unlink)
    with pytest.warns(RuntimeWarning, match="could not remove the temporary file"):
        with pytest.raises(KeyboardInterrupt):
            api._atomic_write_text(tmp_path / "page.html", "x")


def test_atomic_writes_stay_quiet_when_cleanup_works(tmp_path, monkeypatch):
    # The warning must not fire on the ordinary interrupted path, or every
    # cancelled write would look like a leak.
    from pyfcstm.diagram import api

    def interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(api, "_apply_target_mode", interrupt)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(KeyboardInterrupt):
            api._atomic_write_text(tmp_path / "page.html", "x")
    assert [str(item.message) for item in caught] == []
    assert list(tmp_path.iterdir()) == []

    # The other quiet path: an OSError write cleans up in its own branch, so the
    # `finally` finds nothing left. Without a FileNotFoundError arm that second
    # attempt reads as a cleanup failure and warns about a file it just removed.
    def fail_mode(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(api, "_apply_target_mode", fail_mode)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(OSError, match="disk full"):
            api._atomic_write_text(tmp_path / "other.html", "x")
    assert [str(item.message) for item in caught] == []
    assert list(tmp_path.iterdir()) == []


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
def test_umask_probe_failure_does_not_fail_the_write(tmp_path, monkeypatch):
    # The probe exists only to read a number. Removing it used to be able to
    # raise, and an indexer or scanner holding the handle -- routine on Windows
    # -- then turned a write that would otherwise have succeeded into a failure
    # with no file produced at all.
    from pyfcstm.diagram import api

    real_unlink = os.unlink

    def picky_unlink(path, *args, **kwargs):
        if ".pyfcstm-umask-" in str(path):
            raise PermissionError("in use by another process")
        return real_unlink(path, *args, **kwargs)

    monkeypatch.setattr(os, "unlink", picky_unlink)
    target = tmp_path / "doc.html"
    with pytest.warns(RuntimeWarning, match="could not remove the probe file"):
        api._atomic_write_text(target, "x" * 128)
    assert target.read_text(encoding="utf-8") == "x" * 128


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes")
def test_umask_probe_never_widens_the_process(tmp_path, monkeypatch):
    # Reading the umask by clearing it is a process-wide race. The mode a new
    # file lands with must still be right, and `os.umask` must not be called at
    # all to work it out.
    from pyfcstm.diagram import api

    calls = []
    real_umask = os.umask

    def counting_umask(value):
        calls.append(value)
        return real_umask(value)

    monkeypatch.setattr(os, "umask", counting_umask)
    previous = real_umask(0o027)
    try:
        target = tmp_path / "doc.html"
        api._atomic_write_text(target, "x")
        assert stat.S_IMODE(target.stat().st_mode) == 0o640
    finally:
        real_umask(previous)
    assert calls == [], "the umask must not be touched to read it"
