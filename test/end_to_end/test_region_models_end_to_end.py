"""
Models with regions, taken through every stage of the toolchain.

Each model comes from the shared semantic fixture corpus, which supplies the model
text and a scenario with the expected outcome of every cycle. The tests run the
same model through the simulator, the generated Python and C runtimes, ``inspect``,
PlantUML, ``pyfcstm diagram``, an export and reload, ``pyfcstm bmc`` with a replayed
witness, and ``pyfcstm generate``. They only use public entry points.

The models are the ones the first release is judged on: a controller interlock, a
job with a completing region, a nested group, a group preemption and a
collaboration through ``active()``.
"""

import json
import re
from dataclasses import replace

import pytest
from click.testing import CliRunner

from pyfcstm.entry import pyfcstmcli
from pyfcstm.model import load_state_machine_from_text
from test.end_to_end import MODEL_CASES
from test.testings.simulate_semantics import (
    load_semantic_case,
    run_generated_python_alignment_case,
    run_simulation_case,
)

pytestmark = pytest.mark.unittest


@pytest.fixture(params=MODEL_CASES)
def case(request):
    """One shared semantic fixture: the model text and its expected scenario."""
    return load_semantic_case(request.param)


@pytest.fixture
def model_path(case, tmp_path):
    """The model of the case written to a file the commands can read."""
    path = tmp_path / "model.fcstm"
    path.write_text(case.dsl_code, encoding="utf-8")
    return path


def _invoke(*arguments):
    """Run ``pyfcstm`` with the arguments and return the finished result."""
    result = CliRunner().invoke(pyfcstmcli, [str(item) for item in arguments])
    return result


def _regions_by_owner(case):
    """The regions of every owner of the model, as written, keyed by the owner path."""
    model = load_state_machine_from_text(case.dsl_code)
    return {
        ".".join(state.path): list(state.regions)
        for state in model.walk_states()
        if state.regions
    }


def _regions_in_written_order(case):
    """The dotted path of every region of the model, in the order it is written."""
    return [
        "%s.%s" % (owner, name)
        for owner, names in _regions_by_owner(case).items()
        for name in names
    ]


def _region_nodes(node):
    """The dotted names of the region nodes of a diagram snapshot, in written order."""
    found = [node["qualifiedName"]] if node.get("region") else []
    for child in node["children"]:
        found.extend(_region_nodes(child))
    return found


def test_every_model_declares_regions(case):
    """The models of the loop all carry regions, so every stage has something to do."""
    assert _regions_in_written_order(case)


def test_simulator_follows_the_expectations_of_the_scenario(case):
    """The simulator, the judge of the other runtimes, meets the written expectations."""
    run_simulation_case(case)


def test_generated_python_runtime_follows_the_simulator(case):
    """The generated Python runtime agrees with the simulator after every cycle."""
    run_generated_python_alignment_case(case)


def test_inspect_lists_every_region_in_written_order(case, model_path):
    """``pyfcstm inspect`` finishes and reports each region at its written position."""
    result = _invoke("inspect", "-i", model_path, "--format", "json")
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    reported = {}
    for region in sorted(report["regions"], key=lambda item: item["index"]):
        reported.setdefault(region["owner_path"], []).append(region["name"])
    assert reported == _regions_by_owner(case)
    assert not [d for d in report["diagnostics"] if d.get("severity") == "error"]


def test_plantuml_draws_every_region_at_its_written_position(case, model_path):
    """The PlantUML text numbers each region by its written position, with ``--`` between them."""
    result = _invoke("plantuml", "-i", model_path)
    assert result.exit_code == 0, result.output
    notes = re.findall(r"\*\*region (\d+): ([^*]+)\*\*", result.output)
    expected = [
        (str(index), name)
        for names in _regions_by_owner(case).values()
        for index, name in enumerate(names, 1)
    ]
    assert sorted(notes) == sorted(expected)
    separators = [line for line in result.output.splitlines() if line.strip() == "--"]
    assert len(separators) == sum(
        len(names) - 1 for names in _regions_by_owner(case).values()
    )
    # The drawing shows the model as written, not the hidden variables of its expansion.
    assert "__forced_" not in result.output
    assert "__active_" not in result.output


def test_diagram_snapshot_and_command_give_the_same_regions(case, model_path):
    """``StateMachine.diagram()`` and ``pyfcstm diagram`` give one snapshot, with a node for every region."""
    result = _invoke("diagram", "-i", model_path)
    assert result.exit_code == 0, result.output
    from_command = json.loads(result.output)
    model = load_state_machine_from_text(case.dsl_code)
    from_api = model.diagram().to_dict()
    assert from_api == from_command
    assert sorted(_region_nodes(from_api["rootState"])) == sorted(
        _regions_in_written_order(case)
    )


def test_diagram_viewer_page_names_every_region(case, model_path, tmp_path):
    """``pyfcstm diagram -o`` writes the viewer page, and the regions are in it."""
    page = tmp_path / "viewer.html"
    result = _invoke("diagram", "-i", model_path, "-o", page)
    assert result.exit_code == 0, result.output
    text = page.read_text(encoding="utf-8")
    for names in _regions_by_owner(case).values():
        for name in names:
            assert name in text


def test_exported_and_reloaded_model_behaves_the_same(case):
    """The model written out and read back meets the same scenario, in simulation and in Python."""
    exported = str(load_state_machine_from_text(case.dsl_code).to_ast_node())
    reloaded = replace(case, dsl_code=exported)
    run_simulation_case(reloaded)
    run_generated_python_alignment_case(reloaded)


# What each model is about, as a bounded reachability query: the position and the values that only
# the behaviour of the model can produce, the earliest frame it can appear in, and a variant with a
# wrong value that nothing can reach. The earliest frame is the number of steps of the shortest
# witness (the smallest bound for which the query is satisfiable), not a guess: the solver may return
# a longer witness on one machine and the shortest one on another, so a larger number would be flaky.
BMC_PROBES = {
    "region_controller_interlock_prototype_trace": (
        'active("Controller.Running{Safety: Watching, Motion: On}") && var("motor") == 1',
        3,
        'active("Controller.Running{Safety: Watching, Motion: On}") && var("permit") == 0',
    ),
    "region_done_region_waits_and_last_completion_continues_same_cycle": (
        'active("Workflow.AwaitPermission") && var("aexit") == 1 && var("w") == 1',
        2,
        'active("Workflow.AwaitPermission") && var("aexit") == 0 && var("w") == 1',
    ),
    "region_group_exit_takes_a_nested_group_out_before_its_owner": (
        'active("Root.Off") && var("seq") == 123459',
        2,
        'active("Root.Off") && var("seq") == 543219',
    ),
    "region_group_preemption_wins_over_child_completion_in_same_cycle": (
        'active("Workflow.Idle") && var("order") == 123',
        2,
        'active("Workflow.Idle") && var("order") == 321',
    ),
    "region_active_query_follows_enter_exit_effect_and_same_cycle_order": (
        'active("Root.P{Safety: Tripped, Motion: Stop}") && var("x1") == 1 && var("x2") == 2'
        ' && var("y1") == 2 && var("y2") == 2 && var("z1") == 1 && var("z2") == 2',
        2,
        'active("Root.P{Safety: Tripped, Motion: Stop}") && var("x1") == 1 && var("x2") == 1',
    ),
}


def _bmc(model_path, tmp_path, goal):
    """Run ``pyfcstm bmc`` on a bounded reachability query and return the result and its JSON."""
    query = tmp_path / "query.fbmcq"
    query.write_text("check reach <= 6: %s;\n" % goal, encoding="utf-8")
    result = _invoke("bmc", "-i", model_path, "-q", query, "--json")
    return result, json.loads(result.output)


def test_bmc_reaches_what_only_the_model_can_do_and_the_simulator_replays_it(
    case, model_path, tmp_path
):
    """``pyfcstm bmc`` reaches the position and values of the model, and the replay agrees with it."""
    goal, earliest, _ = BMC_PROBES[case.id]
    result, report = _bmc(model_path, tmp_path, goal)
    assert result.exit_code == 0, result.output
    assert report["result"]["witness_found"] is True
    assert report["replay"]["ok"] is True
    assert report["replay"]["mismatches"] == []
    frames = report["replay"]["runtime_trace"]["frames"]
    target = re.search(r'active\("([^"]+)"\)', goal).group(1)
    reached = [
        index for index, frame in enumerate(frames) if frame["configuration"] == target
    ]
    assert reached and reached[0] >= earliest, (reached, earliest)


def test_bmc_finds_nothing_with_a_wrong_value(case, model_path, tmp_path):
    """The same position with a value the model cannot produce has no witness."""
    _, _, wrong = BMC_PROBES[case.id]
    result, report = _bmc(model_path, tmp_path, wrong)
    assert result.exit_code == 1, result.output
    assert report["result"]["witness_found"] is False


def test_bmc_guarantees_that_the_interlock_never_runs_the_motor_without_permission(
    tmp_path,
):
    """The interlock model satisfies ``motor on implies permission`` at every step of the bound."""
    case = load_semantic_case("region_controller_interlock_prototype_trace")
    path = tmp_path / "model.fcstm"
    path.write_text(case.dsl_code, encoding="utf-8")
    query = tmp_path / "query.fbmcq"
    query.write_text(
        'check forbid <= 6: var("motor") == 1 && var("permit") == 0;\n',
        encoding="utf-8",
    )
    result = _invoke("bmc", "-i", path, "-q", query, "--json")
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)["result"]
    assert report["property_satisfied"] is True
    assert report["counterexample_found"] is False


def test_simulate_command_follows_the_scenario(case, model_path):
    """``pyfcstm simulate`` run in batch mode prints the configuration the scenario expects."""
    commands = []
    expected = []
    for step in case.data["steps"]:
        events = step.get("cycle") or []
        events = [events] if isinstance(events, str) else events
        inputs = step.get("inputs") or {}
        commands.append(
            " ".join(
                ["cycle"]
                + list(events)
                + ["--input %s=%s" % item for item in inputs.items()]
            )
        )
        expected.append(step.get("expect", {}).get("configuration"))
    result = _invoke(
        "simulate", "-i", model_path, "-e", "; ".join(commands), "--no-color"
    )
    assert result.exit_code == 0, result.output
    printed = re.findall(r"^Current State: (.+)$", result.output, re.M)
    assert printed == [item for item in expected if item is not None]


@pytest.mark.parametrize("template", ["python", "c", "c_poll", "cpp", "cpp_poll"])
def test_generate_command_writes_every_built_in_runtime(
    case, model_path, tmp_path, template
):
    """``pyfcstm generate`` renders the model with every built-in template."""
    output = tmp_path / ("out_" + template)
    result = _invoke("generate", "-i", model_path, "--template", template, "-o", output)
    assert result.exit_code == 0, result.output
    sources = [
        path.name
        for path in output.rglob("*")
        if path.is_file() and path.name.startswith("machine.")
    ]
    assert sources, [path.name for path in output.rglob("*")]
