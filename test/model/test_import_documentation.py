"""Documentation propagation contracts for model-layer imports."""

import pytest

import pyfcstm.model.imports as imports_module
from pyfcstm.diagnostics.sink import DiagnosticSink
from pyfcstm.dsl import node as dsl_nodes


pytestmark = pytest.mark.unittest


def _event_mapping(source_path, target_path):
    return dsl_nodes.ImportEventMapping(
        source_event=dsl_nodes.ChainID(list(source_path), is_absolute=True),
        target_event=dsl_nodes.ChainID(list(target_path), is_absolute=False),
    )


def test_mapped_event_documentation_is_aggregated_into_host_event():
    imported = dsl_nodes.StateMachineDSLProgram(
        definitions=[],
        root_state=dsl_nodes.StateDefinition(
            name="Worker",
            substates=[
                dsl_nodes.StateDefinition(
                    name="Idle",
                    events=[dsl_nodes.EventDefinition("Start", doc="source docs")],
                )
            ],
            transitions=[
                dsl_nodes.TransitionDefinition(
                    from_state="Idle",
                    to_state="Idle",
                    event_id=dsl_nodes.ChainID(["Idle", "Start"]),
                    condition_expr=None,
                    post_operations=[],
                )
            ],
        ),
    )
    host = dsl_nodes.StateMachineDSLProgram(
        definitions=[],
        root_state=dsl_nodes.StateDefinition(
            name="Root",
            events=[dsl_nodes.EventDefinition("Shared", doc="host docs")],
        ),
    )
    import_item = dsl_nodes.ImportStatement(
        source_path="./worker.fcstm",
        alias="Worker",
        mappings=[_event_mapping(("Idle", "Start"), ("Shared",))],
    )
    resolved = imports_module._resolve_import_event_mappings(
        imported, import_item, ("Root",), DiagnosticSink(collect=False)
    )

    imports_module._apply_import_event_mappings(
        imported,
        host,
        import_item,
        ("Root",),
        resolved,
        DiagnosticSink(collect=False),
    )

    assert resolved[("Idle", "Start")].source_doc == "source docs"
    assert host.root_state.events[0].doc == "host docs\n\nsource docs"


def test_compatible_imported_definition_documentation_is_aggregated():
    host = dsl_nodes.StateMachineDSLProgram(
        definitions=[
            dsl_nodes.DefAssignment(
                name="host_x",
                type="int",
                expr=dsl_nodes.Integer("0"),
                doc="host docs",
            )
        ],
        root_state=dsl_nodes.StateDefinition(name="Root"),
    )
    imported = dsl_nodes.StateMachineDSLProgram(
        definitions=[
            dsl_nodes.DefAssignment(
                name="host_x",
                type="int",
                expr=dsl_nodes.Integer("0"),
                doc="import docs",
            )
        ],
        root_state=dsl_nodes.StateDefinition(name="Worker"),
    )

    imports_module._merge_imported_definitions(
        host,
        imported,
        host_explicit_def_names=set(),
        import_item=dsl_nodes.ImportStatement("./worker.fcstm", "Worker"),
        owner_state_path=("Root",),
        sink=DiagnosticSink(collect=False),
    )

    assert host.definitions[0].doc == "host docs\n\nimport docs"
    assert imported.definitions == []


def test_declaration_only_event_mapping_updates_existing_event_without_phantom():
    imported = dsl_nodes.StateMachineDSLProgram(
        definitions=[],
        root_state=dsl_nodes.StateDefinition(
            name="Worker",
            events=[dsl_nodes.EventDefinition("Start", doc="source docs")],
        ),
    )
    host = dsl_nodes.StateMachineDSLProgram(
        definitions=[],
        root_state=dsl_nodes.StateDefinition(
            name="Root",
            substates=[dsl_nodes.StateDefinition(name="Bus")],
        ),
    )
    import_item = dsl_nodes.ImportStatement(
        source_path="./worker.fcstm",
        alias="Worker",
        mappings=[_event_mapping(("Start",), ("Bus", "Shared"))],
    )
    resolved = imports_module._resolve_import_event_mappings(
        imported, import_item, ("Root",), DiagnosticSink(collect=False)
    )
    imports_module._apply_import_event_mappings(
        imported,
        host,
        import_item,
        ("Root",),
        resolved,
        DiagnosticSink(collect=False),
    )
    assert host.root_state.substates[0].events == []

    host.root_state.substates[0].events.append(
        dsl_nodes.EventDefinition("Shared", doc="host docs")
    )
    imports_module._apply_import_event_mappings(
        imported,
        host,
        import_item,
        ("Root",),
        resolved,
        DiagnosticSink(collect=False),
    )
    assert host.root_state.substates[0].events[0].doc == "host docs\n\nsource docs"
