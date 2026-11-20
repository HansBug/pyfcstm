"""Diagram snapshots and exports of models with ordered regions."""

import json
import pathlib
import re

import pytest
from hbutils.testing import simulate_entry

from pyfcstm.diagram import DiagramOptions
from pyfcstm.entry import pyfcstmcli
from pyfcstm.model import (
    State,
    StateMachine,
    Transition,
    load_state_machine_from_file,
    load_state_machine_from_text,
)

pytestmark = pytest.mark.unittest

FIXTURES = pathlib.Path(__file__).parent.parent / "testfile" / "region_diagram"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _model(name):
    return load_state_machine_from_file(str(FIXTURES / ("%s.fcstm" % name)))


def _find(state, path):
    """Walk a snapshot state tree by qualified-name segments below the root."""
    for segment in path:
        state = next(child for child in state["children"] if child["name"] == segment)
    return state


def _walk(state):
    yield state
    for child in state["children"]:
        yield from _walk(child)


def test_regions_become_ordered_flagged_children_of_their_owner():
    data = _model("controller").diagram().to_dict()
    running = _find(data["rootState"], ["Running"])
    assert [
        (c["name"], c.get("region"), c.get("ordinal")) for c in running["children"]
    ] == [("Safety", True, 1), ("Motion", True, 2)]
    assert running["leaf"] is False
    safety, motion = running["children"]
    assert safety["qualifiedName"] == "Controller.Running.Safety"
    assert [child["name"] for child in safety["children"]] == ["Normal", "Tripped"]
    assert [child["name"] for child in motion["children"]] == ["Off", "On"]
    assert [t["label"] for t in safety["transitions"]] == [
        "[*] -> Normal",
        "Normal -> Tripped if [fault != 0]",
    ]
    assert safety["actions"][0]["aspect"] == "before"
    assert motion["events"][0]["name"] == "Kick"


def test_region_ordinals_follow_the_declaration_order_and_restart_when_nested():
    swapped = load_state_machine_from_text(
        "state Root { region B { state Y; [*] -> Y; } region A { state X; [*] -> X; } }"
    )
    root = swapped.diagram().to_dict()["rootState"]
    assert [(c["name"], c["ordinal"]) for c in root["children"]] == [("B", 1), ("A", 2)]

    data = _model("nested").diagram().to_dict()
    job = _find(data["rootState"], ["Job"])
    assert [(c["name"], c["ordinal"]) for c in job["children"]] == [
        ("A", 1),
        ("B", 2),
        ("C", 3),
    ]
    inner = _find(job, ["A", "Q"])
    assert [(c["name"], c["ordinal"]) for c in inner["children"]] == [
        ("A1", 1),
        ("A2", 2),
    ]


def test_active_queries_keep_their_written_form_and_hide_generated_flags():
    machine = _model("controller")
    data = machine.diagram().to_dict()
    text = json.dumps(data, ensure_ascii=False)
    assert "__active_" not in text
    assert [item["name"] for item in data["variables"]] == [
        "fault",
        "requested",
        "permit",
        "motor",
    ]
    tripped = _find(data["rootState"], ["Running", "Safety", "Tripped"])
    assert tripped["actions"] == []
    motion = _find(data["rootState"], ["Running", "Motion"])
    guards = [t["guardLabel"] for t in motion["transitions"] if t["guardLabel"]]
    assert guards == [
        "permit != 0 && requested != 0",
        'active("Controller.Running.Safety.Tripped")',
    ]
    on = _find(motion, ["On"])
    assert [action["label"] for action in on["actions"]] == ["during {1 op}"]


def test_summary_and_event_legend_count_region_content():
    machine = _model("job")
    data = machine.diagram().to_dict()
    # states: Workflow, Job, AwaitPermission, Ready, Idle and the two Working states
    assert data["summary"]["states"] == 7
    assert data["summary"]["events"] == 3
    both = (
        load_state_machine_from_text("""state Root {
        event Go;
        state P {
            region A { state X; state Y; [*] -> X; X -> Y : /Go; Y -> X : /Go; }
            region B { state U; [*] -> U; U -> [*] : /Go; }
        }
        [*] -> P;
    }""")
        .diagram()
        .to_dict()
    )
    assert both["summary"]["transitions"] == 6
    assert [
        (e["qualifiedName"], e["transitionCount"]) for e in both["eventLegend"]
    ] == [("Root.Go", 3)]


def test_models_without_regions_gain_no_region_fields():
    data = (
        load_state_machine_from_text(
            'state Root { state A; state B; [*] -> A; A -> B : if [active("Root.B")]; }'
        )
        .diagram()
        .to_dict()
    )
    assert "__active_" not in json.dumps(data)
    for state in _walk(data["rootState"]):
        assert "region" not in state and "ordinal" not in state
    assert [
        t["guardLabel"] for t in data["rootState"]["transitions"] if t["guardLabel"]
    ] == ['active("Root.B")']


def test_summary_counts_only_what_the_diagram_shows_for_active_queries():
    data = (
        load_state_machine_from_text(
            "def int x = 0; state Root { [*] -> A; state A; state B;"
            ' A -> B : if [active("/B") && x > 0]; B -> A : if [active("Root")]; }'
        )
        .diagram()
        .to_dict()
    )
    assert [item["name"] for item in data["variables"]] == ["x"]
    assert data["summary"]["variables"] == 1
    assert data["summary"]["actions"] == 0
    assert data["summary"]["states"] == 3


def test_active_queries_in_effects_keep_their_written_form():
    machine = load_state_machine_from_text("""def int x = 0;
    state Root {
        state A { state P; [*] -> P; }
        state B;
        [*] -> A;
        A -> B effect {
            if [active("Root.A.P")] { x = 1; }
            else if [!active("Root.B")] { x = (active("Root.A.P")) ? 2 : 3; }
            else { x = 4; }
        }
    }""")
    data = machine.diagram().to_dict()
    assert "__active_" not in json.dumps(data)
    effect = [t for t in data["rootState"]["transitions"] if t["effectLines"]][0][
        "effectLines"
    ]
    assert effect == [
        "effect {",
        '    if [active("Root.A.P")] {',
        "        x = 1;",
        "    }",
        '    else if [!active("Root.B")] {',
        '        x = (active("Root.A.P")) ? 2 : 3;',
        "    }",
        "    else {",
        "        x = 4;",
        "    }",
        "}",
    ]


def test_effect_with_an_empty_branch_is_shown_with_a_placeholder():
    machine = load_state_machine_from_text(
        "def int x = 0; state Root { state A; state B; [*] -> A;"
        " A -> B effect { if [x > 0] { } else { x = 1; } } }"
    )
    effect = [
        t
        for t in machine.diagram().to_dict()["rootState"]["transitions"]
        if t["effectLines"]
    ][0]["effectLines"]
    assert effect == [
        "effect {",
        "    if [x > 0] {",
        "        ...",
        "    }",
        "    else {",
        "        x = 1;",
        "    }",
        "}",
    ]


def test_transition_without_a_source_range_still_gets_a_diagram():
    root = State(
        name="Root",
        path=("Root",),
        substates={
            "A": State(name="A", path=("Root", "A"), substates={}),
            "B": State(name="B", path=("Root", "B"), substates={}),
        },
        transitions=[
            Transition(from_state="A", to_state="B", event=None, guard=None, effects=[])
        ],
    )
    data = StateMachine(defines={}, root_state=root).diagram().to_dict()
    assert [t["label"] for t in data["rootState"]["transitions"]] == ["A -> B"]


def test_active_queries_of_an_imported_module_show_the_instance_path(tmp_path):
    (tmp_path / "module.fcstm").write_text("""def int y = 0;
    state Sub {
        region A { [*] -> X; state X; state Y; X -> Y : if [active("/A.X")]; Y -> X effect { y = 1; } }
        region B { [*] -> Z; state Z; Z -> Z : if [active("Sub.A.Y")]; }
    }""")
    (tmp_path / "host.fcstm").write_text(
        'def int y = 0;\nstate Host { import "module.fcstm" as Mod; [*] -> Mod; }'
    )
    data = (
        load_state_machine_from_file(str(tmp_path / "host.fcstm")).diagram().to_dict()
    )
    text = json.dumps(data)
    assert "__active_" not in text
    guards = sorted(
        t["guardLabel"]
        for state in _walk(data["rootState"])
        for t in state["transitions"]
        if t["guardLabel"]
    )
    assert guards == ['active("Host.Mod.A.X")', 'active("Host.Mod.A.Y")']


DIVIDER_DASH = 'stroke-dasharray="6 3"'


def _path_points(tag):
    numbers = [
        float(item)
        for item in re.findall(
            r"-?\d+(?:\.\d+)?", re.search(r' d="([^"]*)"', tag).group(1)
        )
    ]
    return list(zip(numbers[0::2], numbers[1::2]))


def _dividers(svg):
    """The region dividers ``(x0, y0, x1, y1)``, in drawing order.

    The exported SVG carries only paths. A divider is the one dashed stroke
    with the ``6 3`` pattern that is a single straight segment; the dashed
    transitions (forced ones) use another pattern and have several segments.
    """
    lines = []
    for tag in re.findall(r"<path [^>]*>", svg):
        if DIVIDER_DASH not in tag or 'fill="none"' not in tag:
            continue
        (x0, y0), (x1, y1) = _path_points(tag)
        lines.append((x0, y0, x1, y1))
    return lines


def _leaf_boxes(svg):
    """Bounding boxes of the leaf states: the large white rounded rectangles."""
    boxes = []
    for tag in re.findall(r"<path [^>]*>", svg):
        if 'fill="#ffffff"' not in tag:
            continue
        points = _path_points(tag)
        xs, ys = [p[0] for p in points], [p[1] for p in points]
        box = (min(xs), min(ys), max(xs), max(ys))
        if box[2] - box[0] >= 100 and box[3] - box[1] >= 40:
            boxes.append(box)
    return boxes


def _crosses(line, box):
    x0, y0, x1, y1 = line
    if x0 == x1:
        return box[0] < x0 < box[2] and y0 < box[3] and box[1] < y1
    return box[1] < y0 < box[3] and x0 < box[2] and box[0] < x1


def _leaves_per_tile(svg, direction):
    """For every owner with regions, how many leaf states lie in each tile.

    The dividers of one owner share one extent across the direction of the
    diagram and split it along that direction, so the tiles come out in
    layout order. The result holds one list per owner, in drawing order.
    """
    vertical = direction == "TB"
    groups = {}
    for x0, y0, x1, y1 in _dividers(svg):
        if vertical:
            assert x0 == x1
            groups.setdefault((y0, y1), []).append(x0)
        else:
            assert y0 == y1
            groups.setdefault((x0, x1), []).append(y0)
    leaves = _leaf_boxes(svg)
    result = []
    for (low, high), positions in groups.items():
        positions.sort()
        counts = [0] * (len(positions) + 1)
        for box in leaves:
            across = (box[1] + box[3]) / 2 if vertical else (box[0] + box[2]) / 2
            along = (box[0] + box[2]) / 2 if vertical else (box[1] + box[3]) / 2
            if low <= across <= high:
                counts[sum(along > position for position in positions)] += 1
        result.append(counts)
    return result


@pytest.mark.parametrize("direction", ["TB", "LR"])
@pytest.mark.parametrize("name", ["controller", "job", "nested", "elevator", "wide"])
def test_svg_separates_the_regions_of_an_owner_with_dashed_dividers(name, direction):
    machine = _model(name)
    svg = machine.diagram(options=DiagramOptions(direction=direction)).to_svg()
    expected = sum(
        len(state.regions) - 1 for state in machine.walk_states() if state.regions
    )
    dividers = _dividers(svg)
    assert len(dividers) == expected > 0
    for x0, y0, x1, y1 in dividers:
        # Vertical lines between side-by-side sections (TB), horizontal ones
        # between stacked sections (LR).
        assert (x0 == x1) if direction == "TB" else (y0 == y1)
    # A region has no border of its own: nothing filled is dashed with the divider pattern.
    filled_dashed = [
        tag
        for tag in re.findall(r"<path [^>]*>", svg)
        if DIVIDER_DASH in tag and 'fill="none"' not in tag
    ]
    assert filled_dashed == []
    assert "__active_" not in svg


@pytest.mark.parametrize("direction", ["TB", "LR"])
@pytest.mark.parametrize("name", ["controller", "job", "nested", "elevator", "wide"])
def test_dividers_never_cross_a_state(name, direction):
    machine = _model(name)
    svg = machine.diagram(options=DiagramOptions(direction=direction)).to_svg()
    leaves = _leaf_boxes(svg)
    assert leaves
    for line in _dividers(svg):
        assert [box for box in leaves if _crosses(line, box)] == []


@pytest.mark.parametrize("direction", ["TB", "LR"])
@pytest.mark.parametrize(
    "name,leaves_per_region",
    [
        ("controller", [2, 2]),  # Safety: Normal, Tripped; Motion: Off, On
        ("wide", [2, 1, 3, 2, 1, 4]),  # R1 to R6
    ],
)
def test_regions_follow_the_declaration_order_along_the_diagram(
    name, leaves_per_region, direction
):
    machine = _model(name)
    svg = machine.diagram(options=DiagramOptions(direction=direction)).to_svg()
    assert _leaves_per_tile(svg, direction) == [leaves_per_region]


@pytest.mark.parametrize("direction", ["TB", "LR"])
def test_nested_regions_are_tiled_in_declaration_order(direction):
    machine = _model("nested")
    svg = machine.diagram(options=DiagramOptions(direction=direction)).to_svg()
    # Job owns regions A (Q with two regions, and Packing: three leaves), B and C.
    tiles = _leaves_per_tile(svg, direction)
    assert [3, 1, 1] in tiles
    assert len(tiles) == 2


def test_exports_cover_every_format_for_region_models():
    diagram = _model("elevator").diagram()
    assert diagram.to_svg().lstrip().startswith("<svg")
    assert diagram.to_png().startswith(PNG_SIGNATURE)
    assert diagram.to_pdf().startswith(b"%PDF")
    html = diagram.to_html()
    assert (
        "<html" in html.lower()
        and "__active_" not in html
        and "&quot;ordinal&quot;" in html.replace('"', "&quot;")
    )


@pytest.mark.parametrize("suffix", ["json", "html", "svg", "png", "pdf"])
def test_diagram_command_exports_region_models(tmp_path, suffix):
    target = tmp_path / ("machine." + suffix)
    result = simulate_entry(
        pyfcstmcli,
        [
            "pyfcstm",
            "diagram",
            "-i",
            str(FIXTURES / "controller.fcstm"),
            "-o",
            str(target),
        ],
    )
    assert result.exitcode == 0, result.stdout + result.stderr
    content = target.read_bytes()
    assert content
    if suffix == "json":
        assert "region 1" not in content.decode("utf-8")
        data = json.loads(content)
        assert _find(data["rootState"], ["Running"])["children"][0]["ordinal"] == 1
    elif suffix == "png":
        assert content.startswith(PNG_SIGNATURE)
    elif suffix == "pdf":
        assert content.startswith(b"%PDF")


def test_diagram_command_still_reports_model_errors_for_region_documents(tmp_path):
    path = tmp_path / "broken.fcstm"
    path.write_text("state Root { region Worker { state A; } }", encoding="utf-8")
    result = simulate_entry(pyfcstmcli, ["pyfcstm", "diagram", "-i", str(path)])
    assert result.exitcode != 0
    assert "Traceback" not in result.stdout + result.stderr
    assert re.search(r"initial|Worker", result.stdout + result.stderr)
