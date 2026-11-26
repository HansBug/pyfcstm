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
from test.testings.native_semantic_alignment import (
    GENERATED_C_ALIGNMENT,
    GENERATED_C_POLL_ALIGNMENT,
    run_native_alignment_case_subprocess,
)
from test.testings.simulate_semantics import (
    load_semantic_case,
    run_generated_python_alignment_case,
    run_simulation_case,
)

pytestmark = pytest.mark.unittest

MODEL_CASES = (
    "region_controller_interlock_prototype_trace",
    "region_done_region_waits_and_last_completion_continues_same_cycle",
    "region_group_exit_takes_a_nested_group_out_before_its_owner",
    "region_group_preemption_wins_over_child_completion_in_same_cycle",
    "region_active_query_follows_enter_exit_effect_and_same_cycle_order",
)


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


@pytest.mark.parametrize("runner", [GENERATED_C_ALIGNMENT, GENERATED_C_POLL_ALIGNMENT])
def test_generated_c_runtimes_follow_the_simulator(case, runner):
    """The generated C and C poll runtimes agree with the simulator after every cycle."""
    result = run_native_alignment_case_subprocess(runner, case.id)
    assert result.status == "passed", result.message


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


def test_plantuml_draws_every_region_in_written_order(case, model_path):
    """The PlantUML text names the regions in written order, separated by ``--``."""
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
    assert len(separators) == sum(len(names) - 1 for names in _regions_by_owner(case).values())
    # The drawing shows the model as written, not the hidden variables of its expansion.
    assert "__forced_" not in result.output
    assert "__active_" not in result.output


def test_diagram_snapshot_and_command_give_the_same_regions(case, model_path):
    """``StateMachine.diagram()`` and ``pyfcstm diagram`` agree on the regions."""
    result = _invoke("diagram", "-i", model_path)
    assert result.exit_code == 0, result.output
    from_command = json.loads(result.output)
    model = load_state_machine_from_text(case.dsl_code)
    from_api = model.diagram().to_dict()
    assert from_api == from_command
    assert sorted(_region_nodes(from_api["rootState"])) == sorted(
        _regions_in_written_order(case)
    )


def test_exported_and_reloaded_model_behaves_the_same(case):
    """The model written out and read back meets the same scenario, in simulation and in Python."""
    exported = str(load_state_machine_from_text(case.dsl_code).to_ast_node())
    reloaded = replace(case, dsl_code=exported)
    run_simulation_case(reloaded)
    run_generated_python_alignment_case(reloaded)


def _richest_configuration(case):
    """The configuration of the scenario that shows the most regions at once."""
    configurations = [
        step["expect"]["configuration"]
        for step in case.data["steps"]
        if step.get("expect", {}).get("configuration")
    ]
    return max(configurations, key=len)


def test_bmc_finds_a_witness_that_the_simulator_replays(case, model_path, tmp_path):
    """``pyfcstm bmc`` reaches the richest configuration of the scenario, and the replay agrees."""
    target = _richest_configuration(case)
    steps = len(case.data["steps"])
    query = tmp_path / "reach.fbmcq"
    query.write_text('check reach <= %d: active("%s");\n' % (steps, target), encoding="utf-8")
    result = _invoke("bmc", "-i", model_path, "-q", query, "--json")
    assert result.exit_code == 0, result.output
    report = json.loads(result.output)
    assert report["replay"]["ok"] is True
    assert report["replay"]["mismatches"] == []
    frames = report["replay"]["runtime_trace"]["frames"]
    assert target in [frame["configuration"] for frame in frames]


@pytest.mark.parametrize("template", ["python", "c", "c_poll", "cpp", "cpp_poll"])
def test_generate_command_writes_every_built_in_runtime(case, model_path, tmp_path, template):
    """``pyfcstm generate`` renders the model with every built-in template."""
    output = tmp_path / ("out_" + template)
    result = _invoke("generate", "-i", model_path, "--template", template, "-o", output)
    assert result.exit_code == 0, result.output
    assert [path for path in output.rglob("*") if path.is_file()]
