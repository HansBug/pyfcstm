"""Unit tests for the raw SysDeSim XMI index layer."""

from pathlib import Path
from textwrap import dedent

import pytest

from pyfcstm.convert.sysdesim import load_sysdesim_raw_xmi, summarize_sysdesim_raw_xmi

pytestmark = pytest.mark.unittest


def _write_xml(tmp_path: Path, content: str) -> Path:
    """Write a temporary SysDeSim XML file for one test case."""
    xml_file = tmp_path / "sample.sysdesim.xml"
    xml_file.write_text(dedent(content).strip() + "\n", encoding="utf-8")
    return xml_file


def test_raw_xmi_index_builds_global_grouped_and_bypass_views(tmp_path: Path):
    """Raw XMI loading should expose reusable indexes for later timeline extraction."""
    xml_file = _write_xml(
        tmp_path,
        """
        <?xml version="1.0" encoding="UTF-8"?>
        <xmi:XMI xmi:version="20131001"
                 xmlns:xmi="http://www.omg.org/spec/XMI/20131001"
                 xmlns:uml="http://www.eclipse.org/uml2/5.0.0/UML"
                 xmlns:notation="http://www.eclipse.org/gmf/runtime/1.0.2/notation"
                 xmlns:ecore="http://www.eclipse.org/emf/2002/Ecore">
          <uml:Model xmi:id="model_1" name="model">
            <packagedElement xmi:type="uml:Class" xmi:id="class_1" name="Indexed Machine" classifierBehavior="machine_1">
              <ownedBehavior xmi:type="uml:StateMachine" xmi:id="machine_1" name="Indexed Machine">
                <region xmi:type="uml:Region" xmi:id="region_root" name="">
                  <transition xmi:type="uml:Transition" xmi:id="tx_init" source="init_root" target="state_run"/>
                  <subvertex xmi:type="uml:Pseudostate" xmi:id="init_root"/>
                  <subvertex xmi:type="uml:State" xmi:id="state_run" name="Run">
                    <entry xmi:type="uml:Activity" xmi:id="entry_run" name="EnterRun"/>
                    <doActivity xmi:type="uml:Activity" xmi:id="do_run" name="PulseLoop"/>
                  </subvertex>
                </region>
              </ownedBehavior>
              <ownedBehavior xmi:type="uml:Interaction" xmi:id="interaction_1" name="Scenario 1"/>
              <ownedAttribute xmi:type="uml:Property" xmi:id="prop_temp" name="temperature"/>
            </packagedElement>
            <packagedElement xmi:type="uml:Signal" xmi:id="signal_go" name="Go"/>
          </uml:Model>
          <notation:Diagram xmi:id="diagram_1" type="PapyrusUMLStateMachineDiagram"/>
          <ownedStereotype xmi:type="uml:StereotypeApplication" xmi:id="st_1" name="TimingProfile"/>
          <binaryObject xmi:type="ecore:BinaryObject" xmi:id="bin_1"/>
        </xmi:XMI>
        """,
    )

    document = load_sysdesim_raw_xmi(str(xml_file))

    assert document.namespaces["xmi"] == "http://www.omg.org/spec/XMI/20131001"
    assert document.namespaces["uml"] == "http://www.eclipse.org/uml2/5.0.0/UML"
    assert document.namespaces["notation"] == (
        "http://www.eclipse.org/gmf/runtime/1.0.2/notation"
    )
    assert document.xmi_index["machine_1"].attrib["name"] == "Indexed Machine"
    assert document.xmi_index["interaction_1"].attrib["name"] == "Scenario 1"
    assert {
        item.attrib["name"] for item in document.elements_by_xmi_type["uml:Activity"]
    } == {
        "EnterRun",
        "PulseLoop",
    }
    assert len(document.elements_by_xmi_type["uml:StateMachine"]) == 1
    assert len(document.elements_by_xmi_type["uml:Interaction"]) == 1
    assert len(document.elements_by_xmi_type["uml:Property"]) == 1
    assert len(document.elements_by_tag["ownedBehavior"]) == 2
    assert len(document.elements_by_tag["packagedElement"]) == 2
    assert {
        item.attrib["name"]
        for item in document.children_by_parent_id["class_1"]
        if "name" in item.attrib
    } == {"Indexed Machine", "Scenario 1", "temperature"}
    assert len(document.bypass_elements_by_group["notation"]) == 1
    assert len(document.bypass_elements_by_group["diagram"]) == 1
    assert len(document.bypass_elements_by_group["stereotype"]) == 1
    assert len(document.bypass_elements_by_group["binary_object"]) == 1

    summary = summarize_sysdesim_raw_xmi(document)
    assert summary.machine_names == ("Indexed Machine",)
    assert summary.interaction_names == ("Scenario 1",)
    assert summary.signal_names == ("Go",)
    assert summary.property_names == ("temperature",)
    assert summary.activity_names == ("EnterRun", "PulseLoop")
    assert summary.xmi_type_counts["uml:StateMachine"] == 1
    assert summary.xmi_type_counts["uml:Interaction"] == 1
    assert summary.tag_counts["ownedBehavior"] == 2
    assert summary.bypass_group_counts == {
        "binary_object": 1,
        "diagram": 1,
        "notation": 1,
        "stereotype": 1,
    }
    assert summary.to_dict()["machine_names"] == ["Indexed Machine"]
