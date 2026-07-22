import hashlib
import re

import pytest

import pyfcstm.model.model as model_module
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.utils import ModelValidationError


def _build_model(source):
    return parse_dsl_node_to_state_machine(
        parse_with_grammar_entry(source, entry_name="state_machine_dsl")
    )


def _transition_signature(transition):
    return {
        "from": "[*]"
        if str(transition.from_state) == "INIT_STATE"
        else transition.from_state,
        "to": "[*]"
        if str(transition.to_state) == "EXIT_STATE"
        else transition.to_state,
        "event": transition.event.path_name if transition.event is not None else None,
        "guard": str(transition.guard) if transition.guard is not None else None,
        "effects": [str(item.to_ast_node()) for item in transition.effects],
        "origins": [
            {
                "origin_id": ref.origin_id,
                "term_index": ref.term_index,
                "role": ref.role,
                "consumes_term": ref.consumes_term,
                "term_text": ref.term_text,
            }
            for ref in getattr(transition, "combo_origin_refs", [])
        ],
        "projection_key": getattr(transition, "combo_projection_key", None),
        "projection_order": getattr(transition, "combo_projection_order_key", None),
        "reuse_group": getattr(transition, "combo_reuse_group_id", None),
        "priority_identity": getattr(transition, "combo_priority_run_identity", None),
        "priority_index": getattr(transition, "combo_priority_run_index", None),
    }


def _root_transition_signatures(model):
    return [_transition_signature(item) for item in model.root_state.transitions]


@pytest.mark.unittest
class TestComboModelExpansion:
    def test_combo_model_builds_pseudo_chain_and_runs_event_guard_event(self):
        model = _build_model(
            """
            def int x = 1;
            state Root {
                state S1;
                state S2;
                [*] -> S1;
                S1 -> S2 :: E1 + [x > 0] + E2;
            }
            """
        )

        combo_states = [s for s in model.root_state.substates.values() if s.is_pseudo]
        assert len(combo_states) == 2
        assert all(state.name.startswith("__combo_") for state in combo_states)
        assert all(re.search(r"_h[0-9a-f]{12}$", state.name) for state in combo_states)
        assert [state.extra_name for state in combo_states] == [
            "combo after E1",
            "combo after E1 + [x > 0]",
        ]

        signatures = _root_transition_signatures(model)
        assert signatures[0]["from"] == "[*]"
        assert signatures[0]["to"] == "S1"
        assert signatures[1]["from"] == "S1"
        assert signatures[1]["to"] == combo_states[0].name
        assert signatures[1]["event"] == "Root.S1.E1"
        assert signatures[2]["from"] == combo_states[0].name
        assert signatures[2]["to"] == combo_states[1].name
        assert signatures[2]["guard"] == "x > 0"
        assert signatures[3]["from"] == combo_states[1].name
        assert signatures[3]["to"] == "S2"
        assert signatures[3]["event"] == "Root.S1.E2"
        assert signatures[3]["origins"][-1]["role"] == "terminal"

        runtime = SimulationRuntime(model)
        runtime.cycle()
        runtime.cycle(["Root.S1.E1", "Root.S1.E2"])
        assert runtime.current_state.path == ("Root", "S2")

    def test_combo_guard_false_rolls_back_to_source(self):
        model = _build_model(
            """
            def int x = 0;
            state Root {
                state S1;
                state S2;
                [*] -> S1;
                S1 -> S2 :: E1 + [x > 0] + E2;
            }
            """
        )

        runtime = SimulationRuntime(model)
        runtime.cycle()
        result = runtime.cycle(["Root.S1.E1", "Root.S1.E2"])
        assert runtime.current_state.path == ("Root", "S1")
        assert result.consumed_events == ()

    def test_guard_first_combo_runs_guard_before_event_term(self):
        model = _build_model(
            """
            def int x = 1;
            state Root {
                state S1;
                state S2;
                [*] -> S1;
                S1 -> S2 :: [x > 0] + E1;
            }
            """
        )

        signatures = [
            _transition_signature(item)
            for item in model.root_state.transitions
            if item.combo_origin_refs
        ]

        assert signatures[0]["from"] == "S1"
        assert signatures[0]["guard"] == "x > 0"
        assert signatures[1]["from"] == signatures[0]["to"]
        assert signatures[1]["event"] == "Root.S1.E1"

        runtime = SimulationRuntime(model)
        runtime.cycle()
        runtime.cycle(["Root.S1.E1"])
        assert runtime.current_state.path == ("Root", "S2")

    def test_multi_guard_combo_uses_pseudo_validation_for_all_guard_terms(self):
        model = _build_model(
            """
            def int x = 1;
            def int y = 4;
            state Root {
                state S1;
                state S2;
                state S3;
                [*] -> S1;
                S1 -> S2 : [x > 0] + [y < 3];
                S1 -> S3 : [x > 0];
            }
            """
        )

        runtime = SimulationRuntime(model)
        runtime.cycle()
        runtime.cycle()
        assert runtime.current_state.path == ("Root", "S3")

    def test_chain_and_absolute_combo_events_resolve_from_original_scope(self):
        model = _build_model(
            """
            state Root {
                state Bus {
                    state Idle;
                    [*] -> Idle;
                }
                state S1;
                state S2;
                state S3;
                [*] -> S1;
                S1 -> S2 : E1 + E2;
                S1 -> S3 : /Bus.E1 + /Bus.E2;
            }
            """
        )

        generated = [
            item for item in model.root_state.transitions if item.combo_origin_refs
        ]
        assert [item.event.path_name for item in generated] == [
            "Root.E1",
            "Root.E2",
            "Root.Bus.E1",
            "Root.Bus.E2",
        ]

        runtime = SimulationRuntime(model)
        runtime.cycle()
        runtime.cycle(["Root.Bus.E1", "Root.Bus.E2"])
        assert runtime.current_state.path == ("Root", "S3")

    def test_priority_fence_prevents_late_combo_from_outranking_plain_event(self):
        model = _build_model(
            """
            state Root {
                state S1;
                state S2;
                state S3;
                state S4;
                [*] -> S1;
                S1 -> S2 :: E1 + E2;
                S1 -> S4 :: E1;
                S1 -> S3 :: E1 + E3;
            }
            """
        )

        first_targets = [
            t.to_state for t in model.root_state.transitions if t.from_state == "S1"
        ]
        assert first_targets[0] != first_targets[2]

        runtime = SimulationRuntime(model)
        runtime.cycle()
        runtime.cycle(["Root.S1.E1", "Root.S1.E3"])
        assert runtime.current_state.path == ("Root", "S4")

    @pytest.mark.parametrize(
        ["declarations", "events", "expected"],
        [
            (
                "S1 -> S2 :: E1 + E2;\nS1 -> S3 :: E1 + E2 + E3;",
                ["Root.S1.E1", "Root.S1.E2", "Root.S1.E3"],
                "S2",
            ),
            (
                "S1 -> S3 :: E1 + E2 + E3;\nS1 -> S2 :: E1 + E2;",
                ["Root.S1.E1", "Root.S1.E2", "Root.S1.E3"],
                "S3",
            ),
            (
                "S1 -> S3 :: E1 + E2 + E3;\nS1 -> S2 :: E1 + E2;",
                ["Root.S1.E1", "Root.S1.E2"],
                "S2",
            ),
        ],
    )
    def test_prefix_of_other_respects_declaration_order(
        self, declarations, events, expected
    ):
        model = _build_model(
            f"""
            state Root {{
                state S1;
                state S2;
                state S3;
                [*] -> S1;
                {declarations}
            }}
            """
        )

        runtime = SimulationRuntime(model)
        runtime.cycle()
        runtime.cycle(events)
        assert runtime.current_state.path == ("Root", expected)

    def test_entry_and_exit_combo_expand_under_owner_composite(self):
        entry_model = _build_model(
            """
            state Root {
                state S1;
                [*] -> S1 :: E1 + E2;
            }
            """
        )
        entry_pseudo = [
            s for s in entry_model.root_state.substates.values() if s.is_pseudo
        ]
        assert len(entry_pseudo) == 1
        assert entry_pseudo[0].parent is entry_model.root_state

        runtime = SimulationRuntime(entry_model)
        runtime.cycle(["Root.E1", "Root.E2"])
        assert runtime.current_state.path == ("Root", "S1")

        exit_model = _build_model(
            """
            state Root {
                state S1;
                [*] -> S1;
                S1 -> [*] :: E1 + E2;
            }
            """
        )
        exit_pseudo = [
            s for s in exit_model.root_state.substates.values() if s.is_pseudo
        ]
        assert len(exit_pseudo) == 1
        assert exit_pseudo[0].parent is exit_model.root_state

        runtime = SimulationRuntime(exit_model)
        runtime.cycle()
        runtime.cycle(["Root.S1.E1", "Root.S1.E2"])
        assert runtime.is_ended

    def test_combo_effect_runs_only_on_terminal_hop(self):
        model = _build_model(
            """
            def int x = 0;
            state Root {
                state S1;
                state S2;
                [*] -> S1;
                S1 -> S2 :: E1 + E2 effect { x = x + 1; }
            }
            """
        )

        combo_transitions = [
            item for item in model.root_state.transitions if item.combo_origin_refs
        ]
        assert [len(item.effects) for item in combo_transitions] == [0, 1]

        runtime = SimulationRuntime(model)
        runtime.cycle()
        runtime.cycle(["Root.S1.E1", "Root.S1.E2"])
        assert runtime.current_state.path == ("Root", "S2")
        assert runtime.vars["x"] == 1

    def test_projection_metadata_snapshots_shared_and_split_runs(self):
        model = _build_model(
            """
            state Root {
                state S1;
                state S2;
                state S3;
                state S4;
                [*] -> S1;
                S1 -> S2 :: E1 + E2;
                S1 -> S3 :: E1 + E3;
                S1 -> S4 :: E1 + E4;
            }
            """
        )

        generated = [
            _transition_signature(item)
            for item in model.root_state.transitions
            if item.combo_origin_refs
        ]

        assert len(generated) == 4
        assert generated[0]["from"] == "S1"
        assert generated[0]["event"] == "Root.S1.E1"
        assert [ref["term_index"] for ref in generated[0]["origins"]] == [0, 0, 0]
        assert [item["priority_index"] for item in generated] == [0, 1, 2, 3]
        assert [item["projection_order"][-1] for item in generated] == [
            "prefix",
            "terminal",
            "terminal",
            "terminal",
        ]
        assert all(
            item["priority_identity"] == generated[0]["priority_identity"]
            for item in generated[:1]
        )
        assert generated[1]["priority_identity"][0].endswith(":: E1 + E2")
        assert generated[2]["priority_identity"][0].endswith(":: E1 + E3")
        assert generated[3]["priority_identity"][0].endswith(":: E1 + E4")
        assert generated[0]["priority_identity"][0] in generated[0]["reuse_group"]

    def test_same_prefix_split_by_plain_transition_has_distinct_run_identity(self):
        model = _build_model(
            """
            state Root {
                state S1;
                state S2;
                state S3;
                state S4;
                [*] -> S1;
                S1 -> S2 :: E1 + E2;
                S1 -> S4 :: E1;
                S1 -> S3 :: E1 + E3;
            }
            """
        )

        prefix_edges = [
            item
            for item in model.root_state.transitions
            if item.combo_origin_refs and item.combo_origin_refs[0].role == "prefix"
        ]

        assert len(prefix_edges) == 2
        assert prefix_edges[0].to_state != prefix_edges[1].to_state
        assert prefix_edges[0].combo_priority_run_identity != (
            prefix_edges[1].combo_priority_run_identity
        )

    def test_different_chooser_transition_does_not_break_logical_combo_run(self):
        model = _build_model(
            """
            state Root {
                state S1;
                state S2;
                state S3;
                state S4;
                [*] -> S1;
                S1 -> S2 :: E1 + E2;
                S2 -> S4 :: Other;
                S1 -> S3 :: E1 + E3;
            }
            """
        )

        transitions = model.root_state.transitions
        assert any(
            item.from_state == "S2" and item.to_state == "S4" for item in transitions
        )
        s1_prefix_edges = [
            item
            for item in transitions
            if item.from_state == "S1"
            and item.combo_origin_refs
            and item.combo_origin_refs[0].role == "prefix"
        ]

        assert len(s1_prefix_edges) == 1
        assert len(s1_prefix_edges[0].combo_origin_refs) == 2

        runtime = SimulationRuntime(model)
        runtime.cycle()
        runtime.cycle(["Root.S1.E1", "Root.S1.E3"])
        assert runtime.current_state.path == ("Root", "S3")

    def test_interleaved_different_chooser_transition_does_not_rename_prefix(self):
        base = _build_model(
            """
            state Root {
                state S1;
                state S2;
                state S3;
                state S4;
                [*] -> S1;
                S1 -> S2 :: E1 + E2;
                S1 -> S3 :: E1 + E3;
                S2 -> S4 :: Other;
            }
            """
        )
        inserted = _build_model(
            """
            state Root {
                state S1;
                state S2;
                state S3;
                state S4;
                [*] -> S1;
                S1 -> S2 :: E1 + E2;
                S2 -> S4 :: Other;
                S1 -> S3 :: E1 + E3;
            }
            """
        )

        def _combo_names(model):
            return [
                state.name
                for state in model.root_state.substates.values()
                if state.is_pseudo
            ]

        assert _combo_names(base) == _combo_names(inserted)
        assert len(_combo_names(inserted)) == 1

    def test_combo_alternatives_split_when_second_terms_differ(self):
        model = _build_model(
            """
            state Root {
                state S1;
                state S2;
                state S3;
                state S4;
                state S5;
                [*] -> S1;
                S1 -> S2 :: E1 + E2 + E3;
                S1 -> S3 :: E1 + E4 + E5;
            }
            """
        )

        prefix_edges = [
            item
            for item in model.root_state.transitions
            if item.combo_origin_refs and item.combo_origin_refs[0].role == "prefix"
        ]
        first_edges = [item for item in prefix_edges if item.from_state == "S1"]
        second_edges = [item for item in prefix_edges if item.from_state != "S1"]

        assert len(first_edges) == 1
        assert len(second_edges) == 2
        assert {item.event.path_name for item in second_edges} == {
            "Root.S1.E2",
            "Root.S1.E4",
        }
        assert len({item.to_state for item in second_edges}) == 2

    def test_identical_combos_reuse_pseudo_and_emit_terminal_edges(self):
        model = _build_model(
            """
            state Root {
                state A;
                state B;
                [*] -> A;
                A -> B :: E1 + E2;
                A -> B :: E1 + E2;
            }
            """
        )

        pseudo_states = [
            item for item in model.root_state.substates.values() if item.is_pseudo
        ]
        generated = [
            item for item in model.root_state.transitions if item.combo_origin_refs
        ]
        prefix_edges = [
            item for item in generated if item.combo_origin_refs[0].role == "prefix"
        ]
        terminal_edges = [
            item for item in generated if item.combo_origin_refs[0].role == "terminal"
        ]

        assert len(pseudo_states) == 1
        assert len(prefix_edges) == 1
        assert len(prefix_edges[0].combo_origin_refs) == 2
        assert len(terminal_edges) == 2
        assert {item.from_state for item in terminal_edges} == {pseudo_states[0].name}

    def test_generated_combo_pseudo_round_trips_through_ast_export(self):
        model = _build_model(
            """
            state Root {
                state A;
                state B;
                [*] -> A;
                A -> B :: E1 + E2;
            }
            """
        )

        round_tripped = parse_dsl_node_to_state_machine(model.to_ast_node())

        assert [
            item.name
            for item in round_tripped.root_state.substates.values()
            if item.is_pseudo
        ] == [
            item.name for item in model.root_state.substates.values() if item.is_pseudo
        ]
        runtime = SimulationRuntime(round_tripped)
        runtime.cycle()
        runtime.cycle(["Root.A.E1", "Root.A.E2"])
        assert runtime.current_state.path == ("Root", "B")

    def test_generated_combo_pseudo_ast_export_can_round_trip_repeatedly(self):
        model = _build_model(
            """
            state Root {
                state A;
                state B;
                [*] -> A;
                A -> B :: E1 + E2;
            }
            """
        )

        first_round_tripped = parse_dsl_node_to_state_machine(model.to_ast_node())
        second_round_tripped = parse_dsl_node_to_state_machine(
            first_round_tripped.to_ast_node()
        )

        assert [
            item.name
            for item in second_round_tripped.root_state.substates.values()
            if item.is_pseudo
        ] == [
            item.name for item in model.root_state.substates.values() if item.is_pseudo
        ]
        assert [
            (
                item.from_state,
                item.to_state,
                item.event_scope,
                item.event.path_name if item.event is not None else None,
                len(item.combo_origin_refs),
                item.combo_projection_key,
                item.combo_projection_order_key,
            )
            for item in second_round_tripped.root_state.transitions
            if item.from_state != "INIT_STATE"
        ] == [
            (
                item.from_state,
                item.to_state,
                item.event_scope,
                item.event.path_name if item.event is not None else None,
                len(item.combo_origin_refs),
                item.combo_projection_key,
                item.combo_projection_order_key,
            )
            for item in model.root_state.transitions
            if item.from_state != "INIT_STATE"
        ]
        assert (
            "local"
            in second_round_tripped.root_state.substates["A"].events["E2"].origins
        )
        assert (
            "chain"
            not in second_round_tripped.root_state.substates["A"].events["E2"].origins
        )

    def test_mutated_trusted_combo_ast_export_uses_plain_validation(self):
        model = _build_model(
            """
            state Root {
                state A;
                state B;
                [*] -> A;
                A -> B :: E1 + E2;
            }
            """
        )
        program = model.to_ast_node()
        pseudo = next(
            state
            for state in program.root_state.substates
            if state.name.startswith("__combo_")
        )
        for transition in program.root_state.transitions:
            if transition.from_state == pseudo.name:
                transition.to_state = "A"
                break

        _, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)

        assert "E_MISSING_STATE" in [item.code for item in diagnostics]
        with pytest.raises(ModelValidationError) as exc_info:
            parse_dsl_node_to_state_machine(program)
        assert [item.code for item in exc_info.value.diagnostics] == ["E_MISSING_STATE"]

    def test_generated_combo_pseudo_text_export_reimports_as_plain_relay(self):
        model = _build_model(
            """
            state Root {
                state A;
                state B;
                [*] -> A;
                A -> B :: E1 + E2;
            }
            """
        )

        exported = str(model.to_ast_node())
        parsed = parse_with_grammar_entry(exported, entry_name="state_machine_dsl")
        round_tripped, diagnostics = parse_dsl_node_to_state_machine(
            parsed, collect=True
        )

        assert "pseudo state __combo_" in exported
        assert diagnostics == []
        assert [
            item.name
            for item in round_tripped.root_state.substates.values()
            if item.is_pseudo
        ] == [
            item.name for item in model.root_state.substates.values() if item.is_pseudo
        ]
        assert not any(
            item.combo_origin_refs for item in round_tripped.root_state.transitions
        )
        runtime = SimulationRuntime(round_tripped)
        runtime.cycle()
        runtime.cycle(["Root.A.E1", "Root.A.E2"])
        assert runtime.current_state.path == ("Root", "B")

    def test_forged_generated_combo_pseudo_marker_does_not_block_pure_relay(self):
        program = parse_with_grammar_entry(
            """
            state Root {
                pseudo state __combo_user;
                [*] -> __combo_user;
            }
            """,
            entry_name="state_machine_dsl",
        )
        program.root_state.substates[0]._generated_combo_pseudo = True

        model, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)

        assert diagnostics == []
        assert model.root_state.substates["__combo_user"].is_pseudo
        parse_dsl_node_to_state_machine(program)

    def test_nested_same_name_sources_keep_distinct_pseudo_names(self):
        model = _build_model(
            """
            state Root {
                state Left {
                    state S1;
                    state S2;
                    [*] -> S1;
                    S1 -> S2 :: E1 + E2;
                }
                state Right {
                    state S1;
                    state S2;
                    [*] -> S1;
                    S1 -> S2 :: E1 + E2;
                }
                [*] -> Left;
            }
            """
        )

        left_pseudo = [
            state.name
            for state in model.root_state.substates["Left"].substates.values()
            if state.is_pseudo
        ]
        right_pseudo = [
            state.name
            for state in model.root_state.substates["Right"].substates.values()
            if state.is_pseudo
        ]

        assert len(left_pseudo) == len(right_pseudo) == 1
        assert left_pseudo != right_pseudo

    def test_local_scope_semantic_key_uses_original_source_state(self):
        model = _build_model(
            """
            state Root {
                state A;
                state B;
                state C;
                state D;
                [*] -> A;
                A -> C :: Go + Done;
                B -> D :: Go + Done;
            }
            """
        )

        first_edges = [
            item
            for item in model.root_state.transitions
            if item.combo_origin_refs and item.combo_origin_refs[0].term_index == 0
        ]

        assert len(first_edges) == 2
        assert first_edges[0].to_state != first_edges[1].to_state
        assert first_edges[0].event.path_name == "Root.A.Go"
        assert first_edges[1].event.path_name == "Root.B.Go"

    def test_unrelated_transition_insert_does_not_rename_existing_combo_pseudo(self):
        base = _build_model(
            """
            state Root {
                state S1;
                state S2;
                state Other;
                [*] -> S1;
                S1 -> S2 :: E1 + E2;
            }
            """
        )
        with_unrelated = _build_model(
            """
            state Root {
                state S1;
                state S2;
                state Other;
                [*] -> S1;
                Other -> S2 :: Ignore;
                S1 -> S2 :: E1 + E2;
            }
            """
        )

        def _combo_names(model):
            return [
                state.name
                for state in model.root_state.substates.values()
                if state.is_pseudo
            ]

        assert _combo_names(base) == _combo_names(with_unrelated)

    @pytest.mark.parametrize(
        ["source", "expected_kind"],
        [
            (
                """
                state Root {
                    state __combo_user;
                    [*] -> __combo_user;
                }
                """,
                "state",
            ),
            (
                """
                state Root {
                    state __combo_group {
                        state Child;
                        [*] -> Child;
                    }
                    [*] -> __combo_group;
                }
                """,
                "composite",
            ),
        ],
    )
    def test_non_pseudo_reserved_prefix_warns_without_blocking(
        self, source, expected_kind
    ):
        program = parse_with_grammar_entry(source, entry_name="state_machine_dsl")

        model, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)

        assert model.root_state.substates
        diagnostic = next(
            item
            for item in diagnostics
            if item.code == "W_COMBO_RESERVED_PREFIX_STATE_KIND"
        )
        assert diagnostic.severity == "warning"
        assert diagnostic.refs["reserved_prefix"] == "__combo_"
        assert diagnostic.refs["state_kind"] == expected_kind
        parse_dsl_node_to_state_machine(program)

    def test_pure_reserved_prefix_pseudo_is_valid_relay_text(self):
        program = parse_with_grammar_entry(
            """
            state Root {
                state Target;
                pseudo state __combo_user named 'combo after UserEvent';
                [*] -> __combo_user;
                __combo_user -> Target :: Done;
            }
            """,
            entry_name="state_machine_dsl",
        )

        model, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)

        assert diagnostics == []
        assert model.root_state.substates["__combo_user"].is_pseudo
        parse_dsl_node_to_state_machine(program)

    def test_root_reserved_prefix_pseudo_is_handled_by_public_loader(self):
        program = parse_with_grammar_entry(
            "pseudo state __combo_root;", entry_name="state_machine_dsl"
        )

        model, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)

        assert diagnostics == []
        assert model.root_state.is_pseudo
        assert model.root_state.name == "__combo_root"

    def test_reserved_prefix_pseudo_with_actions_warns_without_blocking(self):
        program = parse_with_grammar_entry(
            """
            def int x = 0;
            state Root {
                pseudo state __combo_user {
                    enter { x = x + 1; }
                    during { x = x + 2; }
                    exit { x = x + 3; }
                    >> during before { x = x + 4; }
                }
                state Target;
                [*] -> __combo_user;
                __combo_user -> Target :: Done;
            }
            """,
            entry_name="state_machine_dsl",
        )

        model, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)

        assert model.root_state.substates["__combo_user"].is_pseudo
        diagnostic = next(
            item
            for item in diagnostics
            if item.code == "W_COMBO_RELAY_PSEUDO_HAS_ACTIONS"
        )
        assert diagnostic.severity == "warning"
        assert diagnostic.refs["reserved_prefix"] == "__combo_"
        assert diagnostic.refs["action_kinds"] == [
            "enter",
            "during",
            "exit",
            "during_aspect",
        ]
        assert {item.code for item in diagnostics} == {
            "W_COMBO_RELAY_PSEUDO_HAS_ACTIONS"
        }
        parse_dsl_node_to_state_machine(program)

    @pytest.mark.parametrize(
        "source",
        [
            """
            state Root {
                state A;
                pseudo state __combo_root_a__e1_hbafca7f66598 named 'combo after E1';
                [*] -> A;
            }
            """,
            """
            state Root {
                state A;
                state B;
                pseudo state __combo_root_a__e1_hbafca7f66598 named 'combo after E1';
                [*] -> A;
                A -> __combo_root_a__e1_hbafca7f66598 :: E1;
                __combo_root_a__e1_hbafca7f66598 -> B : A.E2;
            }
            """,
            """
            state Root {
                state A {
                    event E1;
                    event E2;
                }
                state B;
                pseudo state __combo_root_a__e1_h000000000000 named 'combo after E1';
                [*] -> A;
                A -> __combo_root_a__e1_h000000000000 :: E1;
                __combo_root_a__e1_h000000000000 -> B : A.E2;
            }
            """,
        ],
    )
    def test_legacy_export_shape_checks_are_plain_relay_reimports(self, source):
        program = parse_with_grammar_entry(source, entry_name="state_machine_dsl")

        _, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)

        assert diagnostics == []
        parse_dsl_node_to_state_machine(program)

    def test_collect_mode_does_not_duplicate_combo_endpoint_diagnostics(self):
        program = parse_with_grammar_entry(
            """
            state Root {
                state S1;
                Missing -> S1 :: E1 + E2;
                Missing -> S1 :: E1 + E3;
            }
            """,
            entry_name="state_machine_dsl",
        )

        _, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)

        dangling = [
            diag for diag in diagnostics if diag.code == "E_DANGLING_TRANSITION"
        ]
        assert [diag.refs["src"] for diag in dangling] == ["Missing", "Missing"]

    def test_collect_mode_skips_invalid_combo_alternative_after_valid_sibling(self):
        program = parse_with_grammar_entry(
            """
            state Root {
                state S1;
                state S2;
                [*] -> S1;
                S1 -> S2 :: E1 + E2;
                S1 -> Missing :: E1 + E3;
            }
            """,
            entry_name="state_machine_dsl",
        )

        model, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)

        generated = [
            item for item in model.root_state.transitions if item.combo_origin_refs
        ]
        assert [item.event.path_name for item in generated] == [
            "Root.S1.E1",
            "Root.S1.E2",
        ]
        assert any(
            item.code == "E_DANGLING_TRANSITION" and item.refs["tgt"] == "Missing"
            for item in diagnostics
        )

    @pytest.mark.parametrize(
        ["declaration", "expected_warning"],
        [
            ("state {name};", True),
            ("pseudo state {name};", False),
        ],
    )
    def test_hash_extension_resolves_collision_with_user_authored_state(
        self, declaration, expected_warning
    ):
        base = _build_model(
            """
            state Root {
                state S1;
                state S2;
                [*] -> S1;
                S1 -> S2 :: E1 + E2;
            }
            """
        )
        default_name = next(
            state.name
            for state in base.root_state.substates.values()
            if state.is_pseudo
        )
        occupied_declaration = declaration.format(name=default_name)
        program = parse_with_grammar_entry(
            f"""
            state Root {{
                state S1;
                state S2;
                {occupied_declaration}
                [*] -> S1;
                S1 -> S2 :: E1 + E2;
            }}
            """,
            entry_name="state_machine_dsl",
        )

        model, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)

        combo_names = [
            state.name
            for state in model.root_state.substates.values()
            if state.is_pseudo and state.name.startswith("__combo_")
        ]
        assert default_name in model.root_state.substates
        if expected_warning:
            assert default_name not in combo_names
        else:
            assert default_name in combo_names
        generated_names = [
            state.name
            for state in model.root_state.substates.values()
            if state.is_pseudo and state.extra_name == "combo after E1"
        ]
        assert len(generated_names) == 1
        assert generated_names[0] != default_name
        assert re.search(r"_h[0-9a-f]{16}$", generated_names[0])
        info = next(
            item for item in diagnostics if item.code == "I_COMBO_PSEUDO_NAME_EXTENDED"
        )
        assert info.severity == "info"
        assert info.refs["default_digest_size"] == 12
        assert info.refs["final_digest_size"] == 16
        assert (
            any(
                item.code == "W_COMBO_RESERVED_PREFIX_STATE_KIND"
                for item in diagnostics
            )
            is expected_warning
        )
        parse_dsl_node_to_state_machine(program)

    def test_hash_extension_separates_distinct_payloads_sharing_prefix(
        self, monkeypatch
    ):
        def shared_prefix_digest(payload):
            digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            return "a" * 12 + digest[12:]

        monkeypatch.setattr(
            model_module,
            "_combo_payload_digest",
            shared_prefix_digest,
        )
        program = parse_with_grammar_entry(
            """
            state Root {
                state S1;
                state S2;
                state S3;
                state S4;
                [*] -> S1;
                S1 -> S2 :: E1 + E2;
                S1 -> S4 :: E1;
                S1 -> S3 :: E1 + E3;
            }
            """,
            entry_name="state_machine_dsl",
        )

        model, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)

        combo_names = [
            state.name
            for state in model.root_state.substates.values()
            if state.is_pseudo
        ]
        assert len(combo_names) == 2
        assert sorted(len(name.rsplit("_h", 1)[1]) for name in combo_names) == [12, 16]
        assert [
            item.refs["final_digest_size"]
            for item in diagnostics
            if item.code == "I_COMBO_PSEUDO_NAME_EXTENDED"
        ] == [16]
        parse_dsl_node_to_state_machine(program)

    def test_full_digest_collision_fails_after_extension(self, monkeypatch):
        collision_name = f"__combo_root_s1__e1_h{'0' * 64}"
        occupied_recovery_name = collision_name + "__collision_1"
        occupied_names = "\n".join(
            [
                *(
                    f"state __combo_root_s1__e1_h{'0' * size};"
                    for size in range(12, 65, 4)
                ),
                f"state {occupied_recovery_name};",
            ]
        )
        program = parse_with_grammar_entry(
            f"""
            state Root {{
                state S1;
                state S2;
                {occupied_names}
                [*] -> S1;
                S1 -> S2 :: E1 + E2;
            }}
            """,
            entry_name="state_machine_dsl",
        )

        monkeypatch.setattr(
            model_module,
            "_combo_payload_digest",
            lambda payload: "0" * 64,
        )
        with pytest.raises(ModelValidationError) as exc_info:
            parse_dsl_node_to_state_machine(program)
        collision = next(
            diag
            for diag in exc_info.value.diagnostics
            if diag.code == "E_COMBO_PSEUDO_NAME_COLLISION"
        )
        assert collision.refs["pseudo_name"].endswith("0" * 64)

        model, diagnostics = parse_dsl_node_to_state_machine(program, collect=True)
        collect_collisions = [
            diag for diag in diagnostics if diag.code == "E_COMBO_PSEUDO_NAME_COLLISION"
        ]
        assert len(collect_collisions) == 1
        assert model.root_state.substates[collision_name].is_pseudo is False
        generated_recovery_name = collision_name + "__collision_2"
        assert model.root_state.substates[generated_recovery_name].is_pseudo is True
        assert all(
            transition.from_state != collision_name
            and transition.to_state != collision_name
            for transition in model.root_state.transitions
        )

    def test_combo_pseudo_keeps_current_aspect_skip_behavior(self):
        model = _build_model(
            """
            def int x = 0;
            state Root {
                >> during before { x = x + 10; }
                state S1;
                state S2;
                [*] -> S1;
                S1 -> S2 :: E1 + E2;
            }
            """
        )

        runtime = SimulationRuntime(model)
        runtime.cycle()
        assert runtime.vars["x"] == 10
        runtime.cycle(["Root.S1.E1", "Root.S1.E2"])
        assert runtime.current_state.path == ("Root", "S2")
        assert runtime.vars["x"] == 20
