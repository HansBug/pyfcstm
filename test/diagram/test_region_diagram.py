"""Diagram snapshots and exports of models with ordered regions."""

import json
import pathlib
import re

import pytest
from hbutils.testing import simulate_entry

from pyfcstm.diagram import DiagramOptions
from pyfcstm.entry import pyfcstmcli
from pyfcstm.model import load_state_machine_from_file, load_state_machine_from_text

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


def _region_boxes(svg):
    """Bounding boxes ``(x0, y0, x1, y1)`` of the dashed, filled region sections.

    The exported SVG carries only paths. A region is the one filled shape with
    the dashed region border; transitions that are dashed (forced ones) have no
    fill. The boxes come in drawing order, which is the pre-order of the tree.
    """
    boxes = []
    for tag in re.findall(r"<path [^>]*>", svg):
        if 'stroke-dasharray="6 3"' not in tag or 'fill="none"' in tag:
            continue
        numbers = [
            float(item)
            for item in re.findall(
                r"-?\d+(?:\.\d+)?", re.search(r' d="([^"]*)"', tag).group(1)
            )
        ]
        xs, ys = numbers[0::2], numbers[1::2]
        boxes.append((min(xs), min(ys), max(xs), max(ys)))
    return boxes


def _boxes_by_region(machine, svg):
    boxes = _region_boxes(svg)
    regions = [".".join(region.path) for region in machine.walk_regions()]
    assert len(boxes) == len(regions)
    return dict(zip(regions, boxes))


def _overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def test_svg_draws_one_dashed_section_per_region_and_no_generated_flags():
    machine = _model("controller")
    svg = machine.diagram().to_svg()
    assert sorted(_boxes_by_region(machine, svg)) == [
        "Controller.Running.Motion",
        "Controller.Running.Safety",
    ]
    assert "__active_" not in svg


@pytest.mark.parametrize("direction", ["TB", "LR"])
@pytest.mark.parametrize(
    "name,owner",
    [
        ("controller", "Controller.Running"),
        ("job", "Workflow.Job"),
        ("nested", "Workflow.Job"),
        ("nested", "Workflow.Job.A.Q"),
        ("elevator", "Elevator.Serving"),
        ("wide", "Plant.Run"),
    ],
)
def test_regions_are_drawn_in_declaration_order_without_overlap(name, owner, direction):
    machine = _model(name)
    diagram = machine.diagram(options=DiagramOptions(direction=direction))
    boxes = _boxes_by_region(machine, diagram.to_svg())
    owner_state = _find(diagram.to_dict()["rootState"], owner.split(".")[1:])
    ordered = [
        child["qualifiedName"]
        for child in owner_state["children"]
        if child.get("region")
    ]
    assert len(ordered) >= 2
    axis = 0 if direction == "TB" else 1  # same row in TB, same column in LR
    positions = [boxes[item][axis] for item in ordered]
    assert positions == sorted(positions) and len(set(positions)) == len(positions)
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            assert not _overlap(boxes[left], boxes[right])


def test_regions_of_one_owner_start_on_the_same_line():
    machine = _model("nested")
    boxes = _boxes_by_region(machine, machine.diagram().to_svg())
    assert len({boxes["Workflow.Job.%s" % name][1] for name in ("A", "B", "C")}) == 1
    machine = _model("elevator")
    boxes = _boxes_by_region(machine, machine.diagram().to_svg())
    assert len({box[1] for box in boxes.values()}) == 1


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
