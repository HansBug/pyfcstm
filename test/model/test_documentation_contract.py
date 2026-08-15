"""Regression tests for the issue-392 documentation boundaries."""

from dataclasses import fields

import pytest

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
from pyfcstm.bmc.witness import (
    decode_bmc_witness,
    replay_bmc_witness,
    solve_bmc_property,
)
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import load_state_machine_from_text, parse_dsl_node_to_state_machine
from pyfcstm.model.model import State
from pyfcstm.model.plantuml import PlantUMLOptions


pytestmark = pytest.mark.unittest


def _parse(text):
    return parse_with_grammar_entry(text, entry_name="state_machine_dsl")


def test_recursive_doc_free_ast_is_non_mutating_and_matches_no_doc_source():
    documented = _parse(
        """/* Root docs */
state Root {
    /* event docs */
    event Start;
    /* state docs */
    state Idle;
    /* transition docs */
    [*] -> Idle;
}
"""
    )
    plain = _parse(
        """state Root {
    event Start;
    state Idle;
    [*] -> Idle;
}
"""
    )

    inclusive_before = str(documented)
    free = documented.without_docs()
    inclusive_after = str(documented)

    assert "Root docs" in inclusive_before
    assert "Root docs" not in str(free)
    assert str(free) == str(plain)
    assert free is not documented
    assert inclusive_after == inclusive_before
    assert documented.root_state.doc == "Root docs"
    assert documented.root_state.events[0].doc == "event docs"


def test_without_docs_supports_shallow_copy_on_write_and_metadata():
    documented = _parse(
        """/* root docs */
state Root {
    /* child docs */
    state Child;
}
"""
    )
    root = documented.root_state
    root._source_path = "memory.fcstm"
    root._source_text = str(documented)

    shallow = root.without_docs(recursive=False)
    assert shallow is not root
    assert shallow.doc is None
    assert shallow.substates[0] is root.substates[0]
    assert shallow.substates[0].doc == "child docs"
    assert shallow._source_path == root._source_path
    assert shallow._source_text == root._source_text
    assert root.doc == "root docs"


def test_without_docs_returns_self_when_tree_has_no_documentation():
    plain = _parse("state Root { state Child; }")
    assert plain.without_docs() is plain


def test_without_docs_clears_empty_documentation_without_mutating_source():
    documented = _parse("/* */ state Root;")
    stripped = documented.without_docs()
    assert stripped is not documented
    assert stripped.root_state.doc is None
    assert documented.root_state.doc == ""


def test_plantuml_output_is_identical_for_documented_and_plain_models():
    documented = load_state_machine_from_text(
        """/* Root docs */
state Root {
    /* action docs */
    enter abstract Setup;
    /* state docs */
    state Idle;
    /* transition docs */
    [*] -> Idle;
}
"""
    )
    plain = load_state_machine_from_text(
        """state Root {
    enter abstract Setup;
    state Idle;
    [*] -> Idle;
}
"""
    )
    options = PlantUMLOptions(show_lifecycle_actions=True)

    documented_output = documented.to_plantuml(options)
    plain_output = plain.to_plantuml(options)
    assert documented_output == plain_output
    assert "Root docs" not in documented_output
    assert "action docs" not in documented_output


def test_structured_diagram_data_is_doc_free():
    documented = load_state_machine_from_text(
        "/* Root docs */\nstate Root { /* child docs */ state Child; [*] -> Child; }\n"
    )
    plain = load_state_machine_from_text(
        "state Root { state Child; [*] -> Child; }\n"
    )

    documented_data = documented.diagram().to_dict()
    plain_data = plain.diagram().to_dict()
    assert documented_data == plain_data
    assert "doc" not in str(documented_data)


def test_diagnostics_do_not_embed_owner_documentation():
    documented = _parse(
        """/* first */ def int x = 0;
/* duplicate */ def int x = 1;
state Root;
"""
    )
    plain = _parse(
        """def int x = 0;
def int x = 1;
state Root;
"""
    )
    _, documented_diagnostics = parse_dsl_node_to_state_machine(
        documented, collect=True
    )
    _, plain_diagnostics = parse_dsl_node_to_state_machine(plain, collect=True)

    assert [item.message for item in documented_diagnostics] == [
        item.message for item in plain_diagnostics
    ]
    assert all("first" not in item.message for item in documented_diagnostics)
    assert all("duplicate" not in item.message for item in documented_diagnostics)


def test_named_function_diagnostic_is_doc_free_recursively():
    documented = _parse(
        """state Root {
    /* child owner docs */
    state Child {
        /* existing action docs */
        enter abstract Existing;
    }
    state Caller {
        enter ref Child.Missing;
    }
    [*] -> Caller;
}
"""
    )
    _, diagnostics = parse_dsl_node_to_state_machine(
        documented, collect=True
    )
    named = [
        item for item in diagnostics if item.code == "E_NAMED_FUNCTION_REF_NOT_FOUND"
    ]
    assert named
    assert all("child owner docs" not in item.message for item in named)
    assert all("existing action docs" not in item.message for item in named)


def test_concrete_lifecycle_owner_documentation_survives_model_round_trip():
    machine = load_state_machine_from_text(
        """state Root {
    /* concrete enter docs */
    enter { }
    state Child;
    [*] -> Child;
}
"""
    )

    action = machine.root_state.on_enters[0]
    assert action.doc == "concrete enter docs"
    assert action.to_ast_node().doc == "concrete enter docs"


def test_state_doc_is_public_before_private_span_without_positional_drift():
    field_names = [field.name for field in fields(State)]
    assert field_names.index("doc") < field_names.index("_span")
    state = State(
        "Root",
        ("Root",),
        {},
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        False,
        "legacy-span",
        True,
        "docs",
    )
    assert state._span == "legacy-span"
    assert state.is_combo_relay is True
    assert state.doc == "docs"


def test_bmc_result_witness_and_replay_ignore_documentation():
    """Documentation must not alter BMC semantics or its public witness."""
    documented = """/* root docs */
state Root {
    /* active state docs */
    state Active;
    /* initial transition docs */
    [*] -> Active;
}
"""
    plain = """state Root {
    state Active;
    [*] -> Active;
}
"""
    query = 'check reach <= 1: active("Root.Active");'

    def run(source):
        machine = load_state_machine_from_text(source)
        context = BmcEngine(machine).prepare(query)
        formula = compile_bmc_property(build_bmc_core_formula(context))
        result = solve_bmc_property(formula)
        assert result.status == "sat"
        witness = decode_bmc_witness(formula, result.model)
        replay = replay_bmc_witness(machine, witness)
        assert replay.ok
        return result.to_canonical(), witness.to_canonical(), replay.to_canonical()

    documented_result, documented_witness, documented_replay = run(documented)
    plain_result, plain_witness, plain_replay = run(plain)

    # Solver wall-clock measurements are intentionally non-semantic.
    for result in (documented_result, plain_result):
        result["elapsed_ms"] = None
        result["total_elapsed_ms"] = None
    assert documented_result == plain_result
    assert documented_witness == plain_witness
    assert documented_replay == plain_replay
