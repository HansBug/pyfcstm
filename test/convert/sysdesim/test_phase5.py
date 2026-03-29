"""Unit tests for the SysDeSim phase5 parallel-split pipeline."""

from pathlib import Path
from textwrap import dedent

import pytest

from pyfcstm.convert.sysdesim import (
    convert_sysdesim_xml_to_ast,
    convert_sysdesim_xml_to_asts,
    convert_sysdesim_xml_to_dsl,
    convert_sysdesim_xml_to_dsls,
    prepare_sysdesim_output_machines,
)
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.model import StateMachine, parse_dsl_node_to_state_machine

pytestmark = pytest.mark.unittest


def _write_xml(tmp_path: Path, content: str) -> Path:
    """Write a temporary SysDeSim XML file for one test case."""
    xml_file = tmp_path / "sample.sysdesim.xml"
    xml_file.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return xml_file


def _normalize_newlines(text: str) -> str:
    """Normalize text line endings to ``\\n`` for cross-platform assertions."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _assert_dsl_code_loads_to_state_machine(dsl_code: str) -> StateMachine:
    """Assert that DSL text can be parsed and loaded into the public StateMachine model."""
    parsed_program = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
    model = parse_dsl_node_to_state_machine(parsed_program)
    assert isinstance(model, StateMachine)
    return model


def test_phase5_parallel_owner_splits_into_stable_multi_output_programs(tmp_path: Path):
    """Parallel owners should keep one main machine plus one stable FCSTM output per region."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Parallel Split" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Parallel Split">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_controller"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_controller" name="Controller">
                    <region xmi:type="uml:Region" xmi:id="region_left" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_left_init" source="init_left" target="state_left_idle"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_left_go" source="state_left_idle" target="state_left_run"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_left"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_left_idle" name="LeftIdle"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_left_run" name="LeftRun"/>
                    </region>
                    <region xmi:type="uml:Region" xmi:id="region_right" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_right_init" source="init_right" target="state_right_idle"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_right_go" source="state_right_idle" target="state_right_run"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_right"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_right_idle" name="RightIdle"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_right_run" name="RightRun"/>
                    </region>
                  </subvertex>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    prepared_outputs = prepare_sysdesim_output_machines(str(xml_file))
    ast_outputs = convert_sysdesim_xml_to_asts(str(xml_file))
    dsl_outputs = {
        name: _normalize_newlines(code)
        for name, code in convert_sysdesim_xml_to_dsls(str(xml_file)).items()
    }

    expected_outputs = {
        "ParallelSplit": dedent(
            """\
            state ParallelSplit named 'Parallel Split' {
                state Controller;
                [*] -> Controller;
            }"""
        ),
        "ParallelSplit__Controller_region1": dedent(
            """\
            state ParallelSplit named 'Parallel Split' {
                state Controller {
                    state LeftIdle;
                    state LeftRun;
                    [*] -> LeftIdle;
                    LeftIdle -> LeftRun;
                }
                [*] -> Controller;
            }"""
        ),
        "ParallelSplit__Controller_region2": dedent(
            """\
            state ParallelSplit named 'Parallel Split' {
                state Controller {
                    state RightIdle;
                    state RightRun;
                    [*] -> RightIdle;
                    RightIdle -> RightRun;
                }
                [*] -> Controller;
            }"""
        ),
    }

    assert [item.output_name for item in prepared_outputs] == list(
        expected_outputs.keys()
    )
    assert list(ast_outputs.keys()) == list(expected_outputs.keys())
    assert dsl_outputs == expected_outputs
    assert {
        name: _normalize_newlines(str(program)) for name, program in ast_outputs.items()
    } == expected_outputs

    for prepared in prepared_outputs:
        assert prepared.semantic_note is not None
        assert prepared.machine.diagnostics[-1].code in {
            "parallel_main_machine_semantic_downgrade",
            "parallel_split_semantic_downgrade",
        }
        assert "semantic downgrade" in prepared.machine.diagnostics[-1].message

    for output_name, dsl_code in dsl_outputs.items():
        model = _assert_dsl_code_loads_to_state_machine(dsl_code)
        assert model.root_state.name == "ParallelSplit"
        if output_name == "ParallelSplit":
            assert tuple(model.root_state.substates) == ("Controller",)
            assert not model.root_state.substates["Controller"].substates
        elif output_name.endswith("region1"):
            assert tuple(model.root_state.substates["Controller"].substates) == (
                "LeftIdle",
                "LeftRun",
            )
        else:
            assert tuple(model.root_state.substates["Controller"].substates) == (
                "RightIdle",
                "RightRun",
            )


def test_phase5_nested_parallel_owner_preserves_outer_machine_structure(tmp_path: Path):
    """Splitting a deep nested parallel owner should keep the surrounding machine topology intact."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Nested Main Split" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Nested Main Split">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_root_init" source="init_root" target="state_top"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_finish" source="state_top" target="state_done">
                    <trigger xmi:type="uml:Trigger" xmi:id="trigger_finish" event="signal_evt_finish"/>
                  </transition>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_top" name="Top">
                    <region xmi:type="uml:Region" xmi:id="region_top" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_top_init" source="init_top" target="state_before"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_before_to_parallel" source="state_before" target="state_parallel"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_parallel_to_after" source="state_parallel" target="state_after"/>
                      <transition xmi:type="uml:Transition" xmi:id="tx_after_reset" source="state_after" target="state_before"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_top"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_before" name="Before"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_parallel" name="Parallel">
                        <region xmi:type="uml:Region" xmi:id="region_left" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_left_init" source="init_left" target="state_left_idle"/>
                          <transition xmi:type="uml:Transition" xmi:id="tx_left_go" source="state_left_idle" target="state_left_run"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_left"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_left_idle" name="LeftIdle"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_left_run" name="LeftRun"/>
                        </region>
                        <region xmi:type="uml:Region" xmi:id="region_right" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_right_init" source="init_right" target="state_right_idle"/>
                          <transition xmi:type="uml:Transition" xmi:id="tx_right_go" source="state_right_idle" target="state_right_run"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_right"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_right_idle" name="RightIdle"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_right_run" name="RightRun"/>
                        </region>
                      </subvertex>
                      <subvertex xmi:type="uml:State" xmi:id="state_after" name="After"/>
                    </region>
                  </subvertex>
                  <subvertex xmi:type="uml:State" xmi:id="state_done" name="Done"/>
                </region>
              </ownedBehavior>
              <ownedAttribute xmi:type="uml:Property" xmi:id="var_count" name="count">
                <type xmi:type="uml:PrimitiveType" href="pathmap://UML_LIBRARIES/UMLPrimitiveTypes.library.uml#Integer"/>
                <defaultValue xmi:type="uml:LiteralInteger" xmi:id="var_count_default" value="0"/>
              </ownedAttribute>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_finish" name="Finish"/>
            <packagedElement xmi:type="uml:SignalEvent" xmi:id="signal_evt_finish" name="" signal="signal_finish"/>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    ast_outputs = convert_sysdesim_xml_to_asts(str(xml_file))
    dsl_outputs = {
        name: _normalize_newlines(code)
        for name, code in convert_sysdesim_xml_to_dsls(str(xml_file)).items()
    }

    expected_outputs = {
        "NestedMainSplit": dedent(
            """\
            state NestedMainSplit named 'Nested Main Split' {
                state Top {
                    state Before;
                    state Parallel;
                    state After;
                    [*] -> Before;
                    Before -> Parallel;
                    Parallel -> After;
                    After -> Before;
                }
                state Done;
                event FINISH named 'Finish';
                [*] -> Top;
                Top -> Done : /FINISH;
            }"""
        ),
        "NestedMainSplit__Top__Parallel_region1": dedent(
            """\
            state NestedMainSplit named 'Nested Main Split' {
                state Top {
                    state Before;
                    state Parallel {
                        state LeftIdle;
                        state LeftRun;
                        [*] -> LeftIdle;
                        LeftIdle -> LeftRun;
                    }
                    state After;
                    [*] -> Before;
                    Before -> Parallel;
                    Parallel -> After;
                    After -> Before;
                }
                state Done;
                event FINISH named 'Finish';
                [*] -> Top;
                Top -> Done : /FINISH;
            }"""
        ),
        "NestedMainSplit__Top__Parallel_region2": dedent(
            """\
            state NestedMainSplit named 'Nested Main Split' {
                state Top {
                    state Before;
                    state Parallel {
                        state RightIdle;
                        state RightRun;
                        [*] -> RightIdle;
                        RightIdle -> RightRun;
                    }
                    state After;
                    [*] -> Before;
                    Before -> Parallel;
                    Parallel -> After;
                    After -> Before;
                }
                state Done;
                event FINISH named 'Finish';
                [*] -> Top;
                Top -> Done : /FINISH;
            }"""
        ),
    }

    assert list(ast_outputs.keys()) == list(expected_outputs.keys())
    assert dsl_outputs == expected_outputs
    assert {
        name: _normalize_newlines(str(program)) for name, program in ast_outputs.items()
    } == expected_outputs
    for output_name, dsl_code in dsl_outputs.items():
        model = _assert_dsl_code_loads_to_state_machine(dsl_code)
        assert tuple(model.root_state.substates) == ("Top", "Done")
        assert tuple(model.root_state.events) == ("FINISH",)
        assert tuple(model.root_state.substates["Top"].substates) == (
            "Before",
            "Parallel",
            "After",
        )
        if output_name == "NestedMainSplit":
            assert not model.root_state.substates["Top"].substates["Parallel"].substates
        else:
            assert tuple(
                model.root_state.substates["Top"].substates["Parallel"].substates
            ) in {
                ("LeftIdle", "LeftRun"),
                ("RightIdle", "RightRun"),
            }
        assert [
            transition.to_state
            for transition in model.root_state.substates["Top"].transitions
        ] == [
            "Before",
            "Parallel",
            "After",
            "Before",
        ]


def test_phase5_single_output_apis_require_plural_conversion_for_split_machines(
    tmp_path: Path,
):
    """Singular conversion APIs should reject machines that expand into multiple split outputs."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Parallel Split" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Parallel Split">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_controller"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_controller" name="Controller">
                    <region xmi:type="uml:Region" xmi:id="region_left" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_left_init" source="init_left" target="state_left_idle"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_left"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_left_idle" name="LeftIdle"/>
                    </region>
                    <region xmi:type="uml:Region" xmi:id="region_right" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_right_init" source="init_right" target="state_right_idle"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_right"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_right_idle" name="RightIdle"/>
                    </region>
                  </subvertex>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    with pytest.raises(ValueError, match="expands to 3 outputs due to parallel split"):
        convert_sysdesim_xml_to_ast(str(xml_file))
    with pytest.raises(ValueError, match="expands to 3 outputs due to parallel split"):
        convert_sysdesim_xml_to_dsl(str(xml_file))


def test_phase5_rejects_cross_region_transition_under_parallel_owner(tmp_path: Path):
    """Cross-region transitions under one parallel owner should be rejected explicitly."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Cross Region Split" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Cross Region Split">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_controller"/>
                  <transition xmi:type="uml:Transition" xmi:id="tx_cross_region" source="state_left_idle" target="state_right_idle"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_controller" name="Controller">
                    <region xmi:type="uml:Region" xmi:id="region_left" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_left_init" source="init_left" target="state_left_idle"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_left"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_left_idle" name="LeftIdle"/>
                    </region>
                    <region xmi:type="uml:Region" xmi:id="region_right" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_right_init" source="init_right" target="state_right_idle"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_right"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_right_idle" name="RightIdle"/>
                    </region>
                  </subvertex>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    with pytest.raises(
        NotImplementedError, match="cross-region transitions under parallel owner"
    ):
        prepare_sysdesim_output_machines(str(xml_file))


def test_phase5_nested_parallel_owners_append_stable_split_prefixes(tmp_path: Path):
    """Nested parallel owners should append region suffixes onto the outer split output name."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Nested Split" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Nested Split">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_controller"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_controller" name="Controller">
                    <region xmi:type="uml:Region" xmi:id="region_outer_left" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_outer_left_init" source="init_outer_left" target="state_worker"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_outer_left"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_worker" name="Worker">
                        <region xmi:type="uml:Region" xmi:id="region_worker_a" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_worker_a_init" source="init_worker_a" target="state_a_idle"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_worker_a"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_a_idle" name="AIdle"/>
                        </region>
                        <region xmi:type="uml:Region" xmi:id="region_worker_b" name="">
                          <transition xmi:type="uml:Transition" xmi:id="tx_worker_b_init" source="init_worker_b" target="state_b_idle"/>
                          <subvertex xmi:type="uml:Pseudostate" xmi:id="init_worker_b"/>
                          <subvertex xmi:type="uml:State" xmi:id="state_b_idle" name="BIdle"/>
                        </region>
                      </subvertex>
                    </region>
                    <region xmi:type="uml:Region" xmi:id="region_outer_right" name="">
                      <transition xmi:type="uml:Transition" xmi:id="tx_outer_right_init" source="init_outer_right" target="state_side"/>
                      <subvertex xmi:type="uml:Pseudostate" xmi:id="init_outer_right"/>
                      <subvertex xmi:type="uml:State" xmi:id="state_side" name="Side"/>
                    </region>
                  </subvertex>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    ast_outputs = convert_sysdesim_xml_to_asts(str(xml_file))
    dsl_outputs = {
        name: _normalize_newlines(code)
        for name, code in convert_sysdesim_xml_to_dsls(str(xml_file)).items()
    }

    expected_outputs = {
        "NestedSplit": dedent(
            """\
            state NestedSplit named 'Nested Split' {
                state Controller;
                [*] -> Controller;
            }"""
        ),
        "NestedSplit__Controller_region1": dedent(
            """\
            state NestedSplit named 'Nested Split' {
                state Controller {
                    state Worker;
                    [*] -> Worker;
                }
                [*] -> Controller;
            }"""
        ),
        "NestedSplit__Controller_region1__Worker_region1": dedent(
            """\
            state NestedSplit named 'Nested Split' {
                state Controller {
                    state Worker {
                        state AIdle;
                        [*] -> AIdle;
                    }
                    [*] -> Worker;
                }
                [*] -> Controller;
            }"""
        ),
        "NestedSplit__Controller_region1__Worker_region2": dedent(
            """\
            state NestedSplit named 'Nested Split' {
                state Controller {
                    state Worker {
                        state BIdle;
                        [*] -> BIdle;
                    }
                    [*] -> Worker;
                }
                [*] -> Controller;
            }"""
        ),
        "NestedSplit__Controller_region2": dedent(
            """\
            state NestedSplit named 'Nested Split' {
                state Controller {
                    state Side;
                    [*] -> Side;
                }
                [*] -> Controller;
            }"""
        ),
    }

    assert list(ast_outputs.keys()) == list(expected_outputs.keys())
    assert dsl_outputs == expected_outputs
    assert {
        name: _normalize_newlines(str(program)) for name, program in ast_outputs.items()
    } == expected_outputs
    for output_name, dsl_code in dsl_outputs.items():
        model = _assert_dsl_code_loads_to_state_machine(dsl_code)
        assert tuple(model.root_state.substates) == ("Controller",)
        if output_name == "NestedSplit":
            assert not model.root_state.substates["Controller"].substates
        elif output_name == "NestedSplit__Controller_region1":
            assert tuple(model.root_state.substates["Controller"].substates) == (
                "Worker",
            )
            assert (
                not model.root_state.substates["Controller"]
                .substates["Worker"]
                .substates
            )
        elif output_name == "NestedSplit__Controller_region2":
            assert tuple(model.root_state.substates["Controller"].substates) == (
                "Side",
            )
        else:
            assert tuple(model.root_state.substates["Controller"].substates) == (
                "Worker",
            )
            worker = model.root_state.substates["Controller"].substates["Worker"]
            if output_name.endswith("region1"):
                assert tuple(worker.substates) == ("AIdle",)
            else:
                assert tuple(worker.substates) == ("BIdle",)


def test_phase5_prepare_outputs_preserves_non_split_diagnostics_without_semantic_note(
    tmp_path: Path,
):
    """Prepared outputs should keep unrelated diagnostics without fabricating a split semantic note."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Root Regions" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Root Regions">
                <region xmi:type="uml:Region" xmi:id="region_left" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init_left" source="init_left" target="state_ready"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_left"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_ready" name="Ready"/>
                </region>
                <region xmi:type="uml:Region" xmi:id="region_right" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init_right" source="init_right" target="state_unused"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_right"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_unused" name="Unused"/>
                </region>
              </ownedBehavior>
            </packagedElement>
          </uml:Model>
        </xmi:XMI>
        """,
    )

    prepared_outputs = prepare_sysdesim_output_machines(str(xml_file))

    assert len(prepared_outputs) == 1
    assert prepared_outputs[0].output_name == "RootRegions"
    assert prepared_outputs[0].semantic_note is None
    assert prepared_outputs[0].machine.diagnostics[0].code == "multiple_root_regions"
