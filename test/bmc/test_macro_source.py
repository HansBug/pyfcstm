"""Macro-step source contract tests for FCSTM BMC."""

from __future__ import annotations

import pytest

from pyfcstm.bmc import (
    STATE_DIAGNOSTIC_ID,
    STATE_TERMINATE_ID,
    BoolLiteral,
    InitialSpec,
    InvalidBmcEncoding,
    InvalidBmcQuery,
    build_bmc_domain,
)
from pyfcstm.bmc.source import (
    DIAGNOSTIC_CASE_PATH,
    TERMINATE_CASE_PATH,
    MacroStepSource,
    diagnostic_source,
    entry_source,
    source_from_initial_spec,
    stable_leaf_source,
    terminated_source,
)
from pyfcstm.model import load_state_machine_from_text


@pytest.fixture()
def source_domain():
    """Build a source-domain fixture with leaf, composite, pseudo, and sentinel-like names."""
    model = load_state_machine_from_text(
        """
        state Root {
            state STATE_DIAGNOSTIC;
            pseudo state Choice;
            state Composite {
                state Leaf;
                [*] -> Leaf;
            }
            [*] -> Composite;
        }
        """
    )
    return build_bmc_domain(model, bound=2)


@pytest.mark.unittest
def test_cold_root_entry_source_uses_initial_entry_even_when_root_is_leaf():
    """Cold starts always enter through an initial-only entry source."""
    domain = build_bmc_domain(load_state_machine_from_text("state Root;"), bound=1)

    source = source_from_initial_spec(domain, InitialSpec())

    assert source == entry_source(domain)
    assert source.to_canonical() == {
        "node": "macro_step_source",
        "kind": "entry",
        "origin": "initial",
        "source_state_id": domain.state_path_to_id("Root"),
        "source_state_path": "Root",
        "allows_semantic_delta": True,
        "uses_stable_fallback": False,
    }
    assert source.allows_semantic_delta is True
    assert source.uses_stable_fallback is False


@pytest.mark.unittest
def test_initial_hot_stable_leaf_matches_recurrence_stable_leaf_except_origin(
    source_domain,
):
    """Hot leaf and recurrence leaf sources normalize to the same semantics."""
    leaf_path = "Root.Composite.Leaf"

    initial = source_from_initial_spec(
        source_domain,
        InitialSpec(mode="state", state_path=leaf_path, predicate=BoolLiteral("true")),
    )
    recurrence = stable_leaf_source(source_domain, leaf_path, origin="recurrence")

    assert initial.kind == "stable_leaf"
    assert initial.origin == "initial"
    assert recurrence.origin == "recurrence"
    assert initial.to_semantic_canonical(
        include_origin=False
    ) == recurrence.to_semantic_canonical(include_origin=False)


@pytest.mark.unittest
def test_hot_composite_and_pseudo_are_initial_only_entry_sources(source_domain):
    """Initial state sources dispatch non-stoppable composite and pseudo states to entry."""
    composite = source_from_initial_spec(
        source_domain,
        InitialSpec(mode="state", state_path="Root.Composite"),
    )
    pseudo = source_from_initial_spec(
        source_domain,
        InitialSpec(mode="state", state_path="Root.Choice"),
    )

    assert composite.kind == "entry"
    assert composite.origin == "initial"
    assert composite.source_state_path == "Root.Composite"
    assert pseudo.kind == "entry"
    assert pseudo.origin == "initial"
    assert pseudo.source_state_path == "Root.Choice"

    with pytest.raises(InvalidBmcEncoding, match="initial-only"):
        entry_source(source_domain, "Root.Composite", origin="recurrence")


@pytest.mark.unittest
def test_non_stoppable_state_cannot_be_stable_leaf_source(source_domain):
    """Stable leaf constructors reject composite, pseudo, root, and sentinel states."""
    for state_path in ["Root", "Root.Composite", "Root.Choice"]:
        with pytest.raises(InvalidBmcEncoding, match="stable_leaf"):
            stable_leaf_source(source_domain, state_path)

    with pytest.raises(InvalidBmcEncoding, match="stable_leaf"):
        stable_leaf_source(source_domain, STATE_TERMINATE_ID)
    with pytest.raises(InvalidBmcEncoding, match="stable_leaf"):
        stable_leaf_source(source_domain, STATE_DIAGNOSTIC_ID)


@pytest.mark.unittest
def test_sentinel_sources_use_fixed_ids_and_reserved_paths(source_domain):
    """Sentinel sources cannot be impersonated by model states with similar names."""
    terminate = terminated_source(source_domain, origin="initial")
    diagnostic = diagnostic_source(source_domain)

    assert terminate.source_state_id == STATE_TERMINATE_ID
    assert terminate.source_state_path == TERMINATE_CASE_PATH
    assert terminate.kind == "terminated"
    assert diagnostic.source_state_id == STATE_DIAGNOSTIC_ID
    assert diagnostic.source_state_path == DIAGNOSTIC_CASE_PATH
    assert diagnostic.kind == "diagnostic"

    user_diagnostic = source_domain.state_path_to_id("Root.STATE_DIAGNOSTIC")
    assert user_diagnostic >= 0
    with pytest.raises(InvalidBmcEncoding, match="fixed sentinel id"):
        MacroStepSource(
            "diagnostic",
            "recurrence",
            user_diagnostic,
            DIAGNOSTIC_CASE_PATH,
            domain=source_domain,
        )
    with pytest.raises(InvalidBmcEncoding, match="reserved macro-step path"):
        MacroStepSource(
            "terminated",
            "recurrence",
            STATE_TERMINATE_ID,
            "$STATE_TERMINATE",
            domain=source_domain,
        )


@pytest.mark.unittest
def test_source_from_initial_spec_ignores_where_predicate(source_domain):
    """Initial predicates stay in I_0 and do not change source profile selection."""
    without_predicate = source_from_initial_spec(
        source_domain,
        InitialSpec(mode="state", state_path="Root.Composite.Leaf"),
    )
    with_predicate = source_from_initial_spec(
        source_domain,
        InitialSpec(
            mode="state",
            state_path="Root.Composite.Leaf",
            predicate=BoolLiteral("false"),
        ),
    )

    assert with_predicate == without_predicate
    assert "predicate" not in with_predicate.to_canonical()


@pytest.mark.unittest
def test_initial_terminated_source_is_absorb_source(source_domain):
    """Initial terminated mode maps to a terminated absorb source."""
    source = source_from_initial_spec(source_domain, InitialSpec(mode="terminated"))

    assert source == terminated_source(source_domain, origin="initial")
    assert source.to_canonical()["source_state_id"] == STATE_TERMINATE_ID


@pytest.mark.unittest
def test_source_constructors_reject_wrong_structural_values(source_domain):
    """Source contract validates primitive fields and constructor arguments."""
    with pytest.raises(InvalidBmcEncoding, match="source kind"):
        MacroStepSource("unknown", "initial", 0, "Root")
    with pytest.raises(InvalidBmcEncoding, match="source origin"):
        MacroStepSource("entry", "later", 0, "Root")
    with pytest.raises(InvalidBmcEncoding, match="initial-only"):
        MacroStepSource("entry", "recurrence", 0, "Root")
    with pytest.raises(InvalidBmcEncoding, match="model state id"):
        MacroStepSource("entry", "initial", STATE_TERMINATE_ID, TERMINATE_CASE_PATH)
    with pytest.raises(InvalidBmcEncoding, match="reserved macro-step paths"):
        MacroStepSource("entry", "initial", 0, TERMINATE_CASE_PATH)
    with pytest.raises(InvalidBmcEncoding, match="model state id"):
        MacroStepSource(
            "stable_leaf", "recurrence", STATE_DIAGNOSTIC_ID, DIAGNOSTIC_CASE_PATH
        )
    with pytest.raises(InvalidBmcEncoding, match="reserved macro-step paths"):
        MacroStepSource("stable_leaf", "recurrence", 0, DIAGNOSTIC_CASE_PATH)
    with pytest.raises(InvalidBmcEncoding, match="fixed sentinel id"):
        MacroStepSource(
            "terminated", "recurrence", STATE_DIAGNOSTIC_ID, TERMINATE_CASE_PATH
        )
    with pytest.raises(InvalidBmcEncoding, match="reserved macro-step path"):
        MacroStepSource(
            "diagnostic", "recurrence", STATE_DIAGNOSTIC_ID, TERMINATE_CASE_PATH
        )
    with pytest.raises(InvalidBmcEncoding, match="source_state_id"):
        MacroStepSource("entry", "initial", True, "Root")
    with pytest.raises(InvalidBmcEncoding, match="domain"):
        entry_source(object())
    with pytest.raises(InvalidBmcEncoding, match="state must"):
        entry_source(source_domain, object())
    with pytest.raises(InvalidBmcEncoding, match="Source path"):
        MacroStepSource(
            "entry",
            "initial",
            source_domain.state_path_to_id("Root.Composite"),
            "Root",
            domain=source_domain,
        )
    with pytest.raises(InvalidBmcEncoding, match="Unknown state id"):
        MacroStepSource("entry", "initial", 9999, "Missing", domain=source_domain)
    with pytest.raises(InvalidBmcEncoding, match="source_state_path"):
        MacroStepSource("entry", "initial", 0, "")
    with pytest.raises(InvalidBmcEncoding, match="domain"):
        MacroStepSource("entry", "initial", 0, "Root", domain=object())


@pytest.mark.unittest
def test_source_validation_rejects_additional_adversarial_shapes(source_domain):
    """Source validation covers hacked initial modes and lookup failures."""
    with pytest.raises(InvalidBmcEncoding, match="domain"):
        stable_leaf_source(object(), "Root")
    with pytest.raises(InvalidBmcEncoding, match="Unknown state path"):
        stable_leaf_source(source_domain, "Root.Missing")
    with pytest.raises(InvalidBmcEncoding, match="entry source"):
        entry_source(source_domain, "Root.Composite.Leaf")

    direct = MacroStepSource("stable_leaf", "initial", 123, "Root.A")
    assert direct.to_semantic_canonical()["origin"] == "initial"

    with pytest.raises(InvalidBmcQuery, match="InitialSpec"):
        source_from_initial_spec(source_domain, object())
    hacked = InitialSpec()
    object.__setattr__(hacked, "mode", "unknown")
    with pytest.raises(InvalidBmcQuery, match="unknown initial"):
        source_from_initial_spec(source_domain, hacked)


@pytest.mark.unittest
def test_source_validation_rejects_reserved_model_paths(
    source_domain,
):
    """Source constructors fail closed for reserved macro-step paths."""
    with pytest.raises(InvalidBmcEncoding, match="reserved macro-step paths"):
        MacroStepSource(
            "stable_leaf",
            "recurrence",
            0,
            TERMINATE_CASE_PATH,
            domain=source_domain,
        )
    with pytest.raises(InvalidBmcEncoding, match="reserved macro-step paths"):
        MacroStepSource(
            "entry",
            "initial",
            0,
            DIAGNOSTIC_CASE_PATH,
            domain=source_domain,
        )
