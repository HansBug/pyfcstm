"""Macro-step source contract tests for FCSTM BMC."""

from __future__ import annotations

import pytest

from pyfcstm.bmc import (
    STATE_INIT_ID,
    STATE_TERMINATE_ID,
    BoolLiteral,
    BmcDomain,
    InitialSpec,
    InvalidBmcEncoding,
    InvalidBmcQuery,
    build_bmc_domain,
)
from pyfcstm.bmc.source import (
    INIT_CASE_PATH,
    TERMINATE_CASE_PATH,
    MacroStepSource,
    init_source,
    entry_source,
    source_from_initial_spec,
    stable_leaf_source,
    terminated_source,
)
from pyfcstm.model import load_state_machine_from_text


def _unsafe_clone_state(entry, **updates):
    """Clone a state-domain entry while bypassing constructor validation."""
    cloned = object.__new__(type(entry))
    for field_name in (
        "id",
        "path",
        "name",
        "kind",
        "parent_path",
        "is_root",
        "is_stoppable",
        "is_sentinel",
        "is_generated_combo_pseudo",
    ):
        object.__setattr__(
            cloned,
            field_name,
            updates.get(field_name, getattr(entry, field_name)),
        )
    return cloned


def _unsafe_clone_domain(domain, **updates):
    """Clone a BMC domain while bypassing snapshot validation."""
    cloned = object.__new__(BmcDomain)
    for field_name in (
        "bound",
        "states",
        "events",
        "variables",
        "frames",
        "steps",
        "event_inputs",
        "initial_state_ids",
        "stable_state_ids",
    ):
        object.__setattr__(
            cloned,
            field_name,
            updates.get(field_name, getattr(domain, field_name)),
        )
    return cloned


@pytest.fixture()
def source_domain():
    """Build a source-domain fixture with leaf, composite, pseudo, and sentinel-like names."""
    model = load_state_machine_from_text(
        """
        state Root {
            state STATE_INIT;
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
def test_cold_source_uses_internal_init_sentinel_even_when_root_is_leaf():
    """Cold starts enter through the internal init sentinel source."""
    domain = build_bmc_domain(load_state_machine_from_text("state Root;"), bound=1)

    source = source_from_initial_spec(domain, InitialSpec())

    assert source == init_source(domain)
    assert source.to_canonical() == {
        "node": "macro_step_source",
        "kind": "init",
        "origin": "initial",
        "source_state_id": STATE_INIT_ID,
        "source_state_path": INIT_CASE_PATH,
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
def test_hot_composite_and_pseudo_are_entry_sources_for_initial_and_recurrence(
    source_domain,
):
    """Non-stoppable model states use entry sources in both initial and recurrence steps."""
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

    recurrence = entry_source(source_domain, "Root.Composite", origin="recurrence")
    assert recurrence.kind == "entry"
    assert recurrence.origin == "recurrence"
    assert recurrence.source_state_path == "Root.Composite"


@pytest.mark.unittest
def test_non_stoppable_state_cannot_be_stable_leaf_source(source_domain):
    """Stable leaf constructors reject composite, pseudo, root, and sentinel states."""
    for state_path in ["Root", "Root.Composite", "Root.Choice"]:
        with pytest.raises(InvalidBmcEncoding, match="stable_leaf"):
            stable_leaf_source(source_domain, state_path)

    with pytest.raises(InvalidBmcEncoding, match="stable_leaf"):
        stable_leaf_source(source_domain, STATE_TERMINATE_ID)
    with pytest.raises(InvalidBmcEncoding, match="stable_leaf"):
        stable_leaf_source(source_domain, STATE_INIT_ID)


@pytest.mark.unittest
def test_sentinel_sources_use_fixed_ids_and_reserved_paths(source_domain):
    """Sentinel sources cannot be impersonated by model states with similar names."""
    terminate = terminated_source(source_domain, origin="initial")
    init = init_source(source_domain)

    assert terminate.source_state_id == STATE_TERMINATE_ID
    assert terminate.source_state_path == TERMINATE_CASE_PATH
    assert terminate.kind == "terminated"
    assert init.source_state_id == STATE_INIT_ID
    assert init.source_state_path == INIT_CASE_PATH
    assert init.kind == "init"

    user_init = source_domain.state_path_to_id("Root.STATE_INIT")
    assert user_init >= 0
    with pytest.raises(InvalidBmcEncoding, match="fixed sentinel id"):
        MacroStepSource(
            "init",
            "recurrence",
            user_init,
            INIT_CASE_PATH,
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
    recurrence_entry = MacroStepSource("entry", "recurrence", 0, "Root")
    assert recurrence_entry.origin == "recurrence"
    with pytest.raises(InvalidBmcEncoding, match="source kind"):
        # Private malformed-object check: the retired diagnostic source kind is
        # no longer a supported public constructor path.
        MacroStepSource("diagnostic", "recurrence", STATE_INIT_ID, INIT_CASE_PATH)
    with pytest.raises(InvalidBmcEncoding, match="model state id"):
        MacroStepSource("entry", "initial", STATE_TERMINATE_ID, TERMINATE_CASE_PATH)
    with pytest.raises(InvalidBmcEncoding, match="reserved macro-step paths"):
        MacroStepSource("entry", "initial", 0, TERMINATE_CASE_PATH)
    with pytest.raises(InvalidBmcEncoding, match="model state id"):
        MacroStepSource("stable_leaf", "recurrence", STATE_INIT_ID, INIT_CASE_PATH)
    with pytest.raises(InvalidBmcEncoding, match="reserved macro-step paths"):
        MacroStepSource("stable_leaf", "recurrence", 0, INIT_CASE_PATH)
    with pytest.raises(InvalidBmcEncoding, match="fixed sentinel id"):
        MacroStepSource("terminated", "recurrence", STATE_INIT_ID, TERMINATE_CASE_PATH)
    with pytest.raises(InvalidBmcEncoding, match="reserved macro-step path"):
        MacroStepSource("init", "recurrence", STATE_INIT_ID, TERMINATE_CASE_PATH)
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
            INIT_CASE_PATH,
            domain=source_domain,
        )


@pytest.mark.unittest
def test_source_validation_rejects_forged_domain_root_and_state_metadata(
    source_domain,
):
    """Source constructors fail closed when a domain snapshot is corrupted."""
    root = source_domain.state_by_path("Root")
    composite = source_domain.state_by_path("Root.Composite")
    terminate = source_domain.state_by_id(STATE_TERMINATE_ID)

    no_root_domain = _unsafe_clone_domain(
        source_domain,
        states=tuple(
            _unsafe_clone_state(entry, is_root=False) if entry.is_root else entry
            for entry in source_domain.states
        ),
    )
    with pytest.raises(InvalidBmcEncoding, match="exactly one model root"):
        entry_source(no_root_domain)

    sentinel_entry_domain = _unsafe_clone_domain(
        source_domain,
        states=tuple(
            _unsafe_clone_state(root, is_sentinel=True)
            if entry.path == root.path
            else entry
            for entry in source_domain.states
        ),
    )
    with pytest.raises(InvalidBmcEncoding, match="sentinel states"):
        MacroStepSource(
            "entry", "initial", root.id, root.path, domain=sentinel_entry_domain
        )

    recurrence_entry = object.__new__(MacroStepSource)
    object.__setattr__(recurrence_entry, "kind", "entry")
    object.__setattr__(recurrence_entry, "origin", "recurrence")
    object.__setattr__(recurrence_entry, "source_state_id", root.id)
    object.__setattr__(recurrence_entry, "source_state_path", root.path)
    recurrence_entry._validate_against_domain(source_domain)

    unstable_stable_domain = _unsafe_clone_domain(
        source_domain,
        stable_state_ids=source_domain.stable_state_ids + (composite.id,),
    )
    with pytest.raises(InvalidBmcEncoding, match="non-sentinel stoppable leaf"):
        MacroStepSource(
            "stable_leaf",
            "recurrence",
            composite.id,
            composite.path,
            domain=unstable_stable_domain,
        )

    reserved_path_domain = _unsafe_clone_domain(
        source_domain,
        states=tuple(
            _unsafe_clone_state(
                root,
                path=TERMINATE_CASE_PATH,
                name=TERMINATE_CASE_PATH,
            )
            if entry.path == root.path
            else entry
            for entry in source_domain.states
        ),
    )
    forged_reserved_source = object.__new__(MacroStepSource)
    object.__setattr__(forged_reserved_source, "kind", "entry")
    object.__setattr__(forged_reserved_source, "origin", "initial")
    object.__setattr__(forged_reserved_source, "source_state_id", root.id)
    object.__setattr__(
        forged_reserved_source,
        "source_state_path",
        TERMINATE_CASE_PATH,
    )
    with pytest.raises(InvalidBmcEncoding, match="reserved macro-step paths"):
        forged_reserved_source._validate_against_domain(reserved_path_domain)

    missing_terminate_domain = _unsafe_clone_domain(
        source_domain,
        states=tuple(
            entry for entry in source_domain.states if entry.id != STATE_TERMINATE_ID
        ),
    )
    with pytest.raises(InvalidBmcEncoding, match="Unknown state id"):
        terminated_source(missing_terminate_domain)

    missing_init_domain = _unsafe_clone_domain(
        source_domain,
        states=tuple(
            entry for entry in source_domain.states if entry.id != STATE_INIT_ID
        ),
    )
    with pytest.raises(InvalidBmcEncoding, match="Unknown state id"):
        init_source(missing_init_domain)

    forged_terminated = object.__new__(MacroStepSource)
    object.__setattr__(forged_terminated, "source_state_id", root.id)
    object.__setattr__(forged_terminated, "source_state_path", TERMINATE_CASE_PATH)
    with pytest.raises(InvalidBmcEncoding, match="fixed sentinel id"):
        forged_terminated._validate_sentinel_source(
            source_domain,
            STATE_TERMINATE_ID,
            TERMINATE_CASE_PATH,
            "terminated",
        )

    forged_bad_path = object.__new__(MacroStepSource)
    object.__setattr__(forged_bad_path, "source_state_id", terminate.id)
    object.__setattr__(forged_bad_path, "source_state_path", "$STATE_TERMINATE")
    with pytest.raises(InvalidBmcEncoding, match="reserved macro-step path"):
        forged_bad_path._validate_sentinel_source(
            source_domain,
            STATE_TERMINATE_ID,
            TERMINATE_CASE_PATH,
            "terminated",
        )
