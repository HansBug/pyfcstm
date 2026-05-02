"""
Raw XMI indexing helpers for SysDeSim imports.

This module keeps a lightweight, non-semantic view of the source XML/XMI
document. It is intentionally separate from the FCSTM compatibility converter
so timeline-oriented import code can inspect the original structure without
re-running state-machine normalization.

The module contains:

* :class:`SysDeSimRawXmiDocument` - Parsed XML tree plus reusable indexes.
* :class:`SysDeSimRawXmiSummary` - Stable structure summary for diagnostics.
* :func:`load_sysdesim_raw_xmi` - Build the reusable raw-document indexes.
* :func:`summarize_sysdesim_raw_xmi` - Produce a compact structure report.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

_XMI_NS = "http://www.omg.org/spec/XMI/20131001"
_XMI_ID = f"{{{_XMI_NS}}}id"
_XMI_TYPE = f"{{{_XMI_NS}}}type"
_NOTATION_NS = "http://www.eclipse.org/gmf/runtime/1.0.2/notation"

_BYPASS_GROUP_RULES = (
    (
        "notation",
        lambda raw_type, tag_name: (
            raw_type.startswith("notation:")
            or tag_name.startswith(f"{{{_NOTATION_NS}}}")
        ),
    ),
    (
        "diagram",
        lambda raw_type, tag_name: (
            "diagram" in raw_type.lower() or tag_name.lower().endswith("diagram")
        ),
    ),
    (
        "stereotype",
        lambda raw_type, tag_name: (
            "stereotype" in raw_type.lower() or "stereotype" in tag_name.lower()
        ),
    ),
    (
        "binary_object",
        lambda raw_type, tag_name: (
            "binaryobject" in raw_type.lower() or tag_name.lower() == "binaryobject"
        ),
    ),
)


def _local_name(tag: str) -> str:
    """
    Return the local XML tag name without its namespace URI.

    :param tag: Fully-qualified ElementTree tag string.
    :type tag: str
    :return: Namespace-free tag name.
    :rtype: str
    """
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _xmi_id(element: ET.Element) -> Optional[str]:
    """
    Return the element's ``xmi:id`` when available.

    :param element: XML element to inspect.
    :type element: xml.etree.ElementTree.Element
    :return: The ``xmi:id`` value, or ``None`` when absent.
    :rtype: str, optional
    """
    return element.attrib.get(_XMI_ID)


def _xmi_type(element: ET.Element) -> str:
    """
    Return the element's raw ``xmi:type`` string.

    :param element: XML element to inspect.
    :type element: xml.etree.ElementTree.Element
    :return: ``xmi:type`` value or ``''`` when absent.
    :rtype: str
    """
    return element.attrib.get(_XMI_TYPE, "")


def _capture_namespaces(xml_path: str) -> Dict[str, str]:
    """
    Capture namespace declarations from a raw XMI file.

    :param xml_path: Path to the source XML/XMI file.
    :type xml_path: str
    :return: Namespace mapping keyed by prefix.
    :rtype: dict[str, str]
    """
    namespaces: Dict[str, str] = {}
    for _, item in ET.iterparse(xml_path, events=("start-ns",)):
        prefix, uri = item
        namespaces[prefix or ""] = uri
    return namespaces


def _iter_bypass_groups(element: ET.Element) -> Iterable[str]:
    """
    Yield non-semantic element groups that should stay visible but bypassed.

    :param element: XML element to classify.
    :type element: xml.etree.ElementTree.Element
    :return: Iterator over bypass-group names.
    :rtype: collections.abc.Iterable[str]
    """
    raw_type = _xmi_type(element)
    tag_name = element.tag
    for group_name, matcher in _BYPASS_GROUP_RULES:
        if matcher(raw_type, tag_name):
            yield group_name


@dataclass
class SysDeSimRawXmiSummary:
    """
    Stable structure summary derived from one raw SysDeSim XMI document.

    :param xml_path: Source XML/XMI path.
    :type xml_path: str
    :param namespaces: Declared namespace mapping keyed by prefix.
    :type namespaces: dict[str, str]
    :param machine_names: State-machine names in document order.
    :type machine_names: tuple[str, ...]
    :param interaction_names: Interaction names in document order.
    :type interaction_names: tuple[str, ...]
    :param signal_names: UML signal names in document order.
    :type signal_names: tuple[str, ...]
    :param property_names: UML property names in document order.
    :type property_names: tuple[str, ...]
    :param activity_names: UML activity names in document order.
    :type activity_names: tuple[str, ...]
    :param xmi_type_counts: Counts keyed by raw ``xmi:type``.
    :type xmi_type_counts: dict[str, int]
    :param tag_counts: Counts keyed by local XML tag name.
    :type tag_counts: dict[str, int]
    :param bypass_group_counts: Counts of visible-but-bypassed element groups.
    :type bypass_group_counts: dict[str, int]
    """

    xml_path: str
    namespaces: Dict[str, str]
    machine_names: Tuple[str, ...]
    interaction_names: Tuple[str, ...]
    signal_names: Tuple[str, ...]
    property_names: Tuple[str, ...]
    activity_names: Tuple[str, ...]
    xmi_type_counts: Dict[str, int]
    tag_counts: Dict[str, int]
    bypass_group_counts: Dict[str, int]

    def to_dict(self) -> Dict[str, object]:
        """
        Convert the summary into a JSON-serializable dictionary.

        :return: Dictionary representation of the raw-XMI summary.
        :rtype: dict[str, object]
        """
        return {
            "xml_path": self.xml_path,
            "namespaces": dict(self.namespaces),
            "machine_names": list(self.machine_names),
            "interaction_names": list(self.interaction_names),
            "signal_names": list(self.signal_names),
            "property_names": list(self.property_names),
            "activity_names": list(self.activity_names),
            "xmi_type_counts": dict(self.xmi_type_counts),
            "tag_counts": dict(self.tag_counts),
            "bypass_group_counts": dict(self.bypass_group_counts),
        }


@dataclass
class SysDeSimRawXmiDocument:
    """
    Parsed SysDeSim XMI document with reusable raw-structure indexes.

    :param xml_path: Source XML/XMI path.
    :type xml_path: str
    :param root: Parsed XML root element.
    :type root: xml.etree.ElementTree.Element
    :param namespaces: Declared namespace mapping keyed by prefix.
    :type namespaces: dict[str, str]
    :param xmi_index: Global index keyed by ``xmi:id``.
    :type xmi_index: dict[str, xml.etree.ElementTree.Element]
    :param parent_map: Parent lookup for every non-root element.
    :type parent_map: dict[xml.etree.ElementTree.Element, xml.etree.ElementTree.Element]
    :param elements_by_xmi_type: Elements grouped by raw ``xmi:type``.
    :type elements_by_xmi_type: dict[str, tuple[xml.etree.ElementTree.Element, ...]]
    :param elements_by_tag: Elements grouped by local XML tag name.
    :type elements_by_tag: dict[str, tuple[xml.etree.ElementTree.Element, ...]]
    :param children_by_parent_id: Child elements grouped by parent ``xmi:id``.
    :type children_by_parent_id: dict[str, tuple[xml.etree.ElementTree.Element, ...]]
    :param bypass_elements_by_group: Visible-but-bypassed elements grouped by
        non-semantic layer name.
    :type bypass_elements_by_group: dict[str, tuple[xml.etree.ElementTree.Element, ...]]
    """

    xml_path: str
    root: ET.Element = field(repr=False)
    namespaces: Dict[str, str]
    xmi_index: Dict[str, ET.Element] = field(repr=False)
    parent_map: Dict[ET.Element, ET.Element] = field(repr=False)
    elements_by_xmi_type: Dict[str, Tuple[ET.Element, ...]] = field(repr=False)
    elements_by_tag: Dict[str, Tuple[ET.Element, ...]] = field(repr=False)
    children_by_parent_id: Dict[str, Tuple[ET.Element, ...]] = field(repr=False)
    bypass_elements_by_group: Dict[str, Tuple[ET.Element, ...]] = field(repr=False)

    def summarize(self) -> SysDeSimRawXmiSummary:
        """
        Produce a stable structure summary for this raw document.

        :return: Summary object describing the source structure.
        :rtype: SysDeSimRawXmiSummary
        """
        return summarize_sysdesim_raw_xmi(self)


def load_sysdesim_raw_xmi(xml_path: str) -> SysDeSimRawXmiDocument:
    """
    Parse a SysDeSim XML/XMI file and build reusable raw-structure indexes.

    :param xml_path: Path to the source XML/XMI file.
    :type xml_path: str
    :return: Parsed raw document with reusable indexes.
    :rtype: SysDeSimRawXmiDocument
    :raises OSError: If the file cannot be read.
    :raises xml.etree.ElementTree.ParseError: If the XML is malformed.
    """
    namespaces = _capture_namespaces(xml_path)
    tree = ET.parse(xml_path)
    root = tree.getroot()

    parent_map = {child: parent for parent in root.iter() for child in parent}
    xmi_index: Dict[str, ET.Element] = {}
    elements_by_xmi_type_mut: Dict[str, List[ET.Element]] = {}
    elements_by_tag_mut: Dict[str, List[ET.Element]] = {}
    children_by_parent_id_mut: Dict[str, List[ET.Element]] = {}
    bypass_elements_by_group_mut: Dict[str, List[ET.Element]] = {}

    for element in root.iter():
        element_id = _xmi_id(element)
        if element_id is not None:
            xmi_index[element_id] = element

        raw_type = _xmi_type(element)
        if raw_type:
            elements_by_xmi_type_mut.setdefault(raw_type, []).append(element)

        tag_name = _local_name(element.tag)
        elements_by_tag_mut.setdefault(tag_name, []).append(element)

        parent = parent_map.get(element)
        if parent is not None:
            parent_id = _xmi_id(parent)
            if parent_id is not None:
                children_by_parent_id_mut.setdefault(parent_id, []).append(element)

        for bypass_group in _iter_bypass_groups(element):
            bypass_elements_by_group_mut.setdefault(bypass_group, []).append(element)

    return SysDeSimRawXmiDocument(
        xml_path=xml_path,
        root=root,
        namespaces=namespaces,
        xmi_index=xmi_index,
        parent_map=parent_map,
        elements_by_xmi_type={
            key: tuple(value) for key, value in elements_by_xmi_type_mut.items()
        },
        elements_by_tag={
            key: tuple(value) for key, value in elements_by_tag_mut.items()
        },
        children_by_parent_id={
            key: tuple(value) for key, value in children_by_parent_id_mut.items()
        },
        bypass_elements_by_group={
            key: tuple(value) for key, value in bypass_elements_by_group_mut.items()
        },
    )


def _names_from_elements(elements: Iterable[ET.Element]) -> Tuple[str, ...]:
    """
    Return non-empty ``name`` attributes from an element iterable.

    :param elements: XML elements to inspect.
    :type elements: collections.abc.Iterable[xml.etree.ElementTree.Element]
    :return: Names in original iteration order.
    :rtype: tuple[str, ...]
    """
    names = []
    for element in elements:
        name = element.attrib.get("name", "")
        if name:
            names.append(name)
    return tuple(names)


def summarize_sysdesim_raw_xmi(
    document: SysDeSimRawXmiDocument,
) -> SysDeSimRawXmiSummary:
    """
    Summarize the raw structure of a parsed SysDeSim XMI document.

    :param document: Raw XMI document returned by
        :func:`load_sysdesim_raw_xmi`.
    :type document: SysDeSimRawXmiDocument
    :return: Stable structure summary for diagnostics and planning.
    :rtype: SysDeSimRawXmiSummary
    """
    return SysDeSimRawXmiSummary(
        xml_path=document.xml_path,
        namespaces=dict(document.namespaces),
        machine_names=_names_from_elements(
            document.elements_by_xmi_type.get("uml:StateMachine", ())
        ),
        interaction_names=_names_from_elements(
            document.elements_by_xmi_type.get("uml:Interaction", ())
        ),
        signal_names=_names_from_elements(
            document.elements_by_xmi_type.get("uml:Signal", ())
        ),
        property_names=_names_from_elements(
            document.elements_by_xmi_type.get("uml:Property", ())
        ),
        activity_names=_names_from_elements(
            document.elements_by_xmi_type.get("uml:Activity", ())
        ),
        xmi_type_counts={
            key: len(value)
            for key, value in sorted(document.elements_by_xmi_type.items())
        },
        tag_counts={
            key: len(value) for key, value in sorted(document.elements_by_tag.items())
        },
        bypass_group_counts={
            key: len(value)
            for key, value in sorted(document.bypass_elements_by_group.items())
        },
    )


__all__ = [
    "SysDeSimRawXmiDocument",
    "SysDeSimRawXmiSummary",
    "load_sysdesim_raw_xmi",
    "summarize_sysdesim_raw_xmi",
]
