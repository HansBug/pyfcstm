"""Domain numbering tests for FCSTM BMC."""

from __future__ import annotations

import pytest

from pyfcstm.bmc import (
    STATE_INIT_ID,
    STATE_TERMINATE_ID,
    BmcDomain,
    EventInputRef,
    FrameRef,
    InvalidBmcDomain,
    StepRef,
    build_bmc_domain,
)
from pyfcstm.model import load_state_machine_from_text


@pytest.fixture()
def adversarial_model():
    """Build a model with pseudo, combo, nested events, and sentinel-like names."""
    return load_state_machine_from_text(
        """
        def int counter = 0;
        def float pressure = 1.5;
        state Root {
            event Boot;
            state STATE_TERMINATE;
            pseudo state __combo_user;
            state Plant {
                event Ping;
                state Idle;
                state Busy;
                [*] -> Idle;
                Idle -> Busy :: Ping + Boot;
            }
            state Backup {
                event Ping;
                state Idle;
                [*] -> Idle;
            }
            [*] -> Plant;
        }
        """
    )


@pytest.mark.unittest
def test_frame_and_step_refs_enforce_bounded_ranges():
    """Frame and step refs expose distinct bounded index domains."""
    assert FrameRef(0, 2).to_canonical() == {
        "node": "frame_ref",
        "index": 0,
        "bound": 2,
        "name": "F_0",
        "role": "initial",
    }
    assert FrameRef(2, 2).role == "transition"
    assert str(FrameRef(2, 2)) == "F_2"
    assert StepRef(0, 2).to_canonical() == {
        "node": "step_ref",
        "index": 0,
        "bound": 2,
        "name": "E_0",
    }
    assert str(StepRef(1, 2)) == "E_1"

    invalid_frame_args = [(-1, 2), (3, 2), (0, 0), (False, 2), (0, True)]
    for index, bound in invalid_frame_args:
        with pytest.raises(InvalidBmcDomain):
            FrameRef(index, bound)

    invalid_step_args = [(-1, 2), (2, 2), (0, 0), (False, 2), (0, True)]
    for index, bound in invalid_step_args:
        with pytest.raises(InvalidBmcDomain):
            StepRef(index, bound)


@pytest.mark.unittest
def test_domain_builds_stable_state_and_sentinel_indexes(adversarial_model):
    """State domains keep sentinel ids separate from user state ids."""
    domain = build_bmc_domain(adversarial_model, bound=2)

    assert isinstance(domain, BmcDomain)
    assert domain.bound == 2
    assert STATE_TERMINATE_ID == -1
    assert STATE_INIT_ID == -3
    assert domain.state_by_path("$STATE_TERMINATE").id == STATE_TERMINATE_ID
    assert domain.state_by_path("$STATE_INIT").id == STATE_INIT_ID
    assert domain.state_id_to_path(STATE_TERMINATE_ID) == "$STATE_TERMINATE"
    assert domain.state_id_to_path(STATE_INIT_ID) == "$STATE_INIT"

    user_terminate_id = domain.state_path_to_id("Root.STATE_TERMINATE")
    assert domain.state_by_id(STATE_TERMINATE_ID).name == "STATE_TERMINATE"
    assert domain.state_by_id(STATE_INIT_ID).name == "STATE_INIT"
    assert user_terminate_id >= 0
    assert user_terminate_id not in {STATE_TERMINATE_ID, STATE_INIT_ID}

    root_id = domain.state_path_to_id("Root")
    composite_id = domain.state_path_to_id("Root.Plant")
    leaf_id = domain.state_path_to_id("Root.Plant.Idle")
    user_pseudo_id = domain.state_path_to_id("Root.__combo_user")
    generated_combo_ids = [
        entry.id for entry in domain.states if entry.is_generated_combo_pseudo
    ]

    assert root_id in domain.initial_state_ids
    assert composite_id in domain.initial_state_ids
    assert leaf_id in domain.initial_state_ids
    assert user_pseudo_id in domain.initial_state_ids
    assert STATE_TERMINATE_ID in domain.initial_state_ids
    assert STATE_INIT_ID in domain.initial_state_ids

    assert leaf_id in domain.stable_state_ids
    assert STATE_TERMINATE_ID in domain.stable_state_ids
    assert STATE_INIT_ID not in domain.stable_state_ids
    assert root_id not in domain.stable_state_ids
    assert composite_id not in domain.stable_state_ids
    assert user_pseudo_id not in domain.stable_state_ids
    assert all(
        combo_id not in domain.stable_state_ids for combo_id in generated_combo_ids
    )

    root_entry = domain.state_by_path("Root")
    assert root_entry.kind == "composite"
    assert root_entry.is_root is True
    assert root_entry.is_stoppable is False

    leaf_entry = domain.state_by_path("Root.Plant.Idle")
    assert leaf_entry.kind == "leaf"
    assert leaf_entry.is_stoppable is True

    user_pseudo_entry = domain.state_by_path("Root.__combo_user")
    assert user_pseudo_entry.kind == "pseudo"
    assert user_pseudo_entry.is_generated_combo_pseudo is False

    assert generated_combo_ids, "combo transition should create generated pseudo states"
    for combo_id in generated_combo_ids:
        combo_entry = domain.state_by_id(combo_id)
        assert combo_entry.kind == "pseudo"
        assert ".__combo_" in combo_entry.path
        assert combo_entry.is_generated_combo_pseudo is True

    with pytest.raises(InvalidBmcDomain):
        domain.state_by_path("Root.Missing")
    with pytest.raises(InvalidBmcDomain):
        domain.state_by_id(9999)


@pytest.mark.unittest
def test_domain_builds_full_event_variable_and_step_input_indexes(adversarial_model):
    """Event and variable domains use stable ids with reversible lookup."""
    domain = build_bmc_domain(adversarial_model, bound=2)

    event_paths = [entry.path for entry in domain.events]
    assert event_paths == sorted(event_paths)
    assert "Root.Boot" in event_paths
    assert "Root.Plant.Ping" in event_paths
    assert "Root.Backup.Ping" in event_paths
    assert "Root.__combo_user.Boot" not in event_paths

    root_boot = domain.event_by_path("Root.Boot")
    plant_ping = domain.event_by_path("Root.Plant.Ping")
    backup_ping = domain.event_by_path("Root.Backup.Ping")
    assert root_boot.owner_state_path == "Root"
    assert plant_ping.owner_state_path == "Root.Plant"
    assert backup_ping.owner_state_path == "Root.Backup"
    assert domain.event_id_to_path(plant_ping.id) == "Root.Plant.Ping"
    assert domain.event_path_to_id("Root.Backup.Ping") == backup_ping.id
    assert plant_ping.id != backup_ping.id
    assert all(not entry.owner_is_generated_combo_pseudo for entry in domain.events)

    var_names = [entry.name for entry in domain.variables]
    assert var_names == ["counter", "pressure"]
    assert domain.variable_by_name("counter").declared_type == "int"
    assert domain.variable_by_name("pressure").declared_type == "float"
    assert (
        domain.variable_id_to_name(domain.variable_name_to_id("counter")) == "counter"
    )

    assert len(domain.frames) == 3
    assert [frame.name for frame in domain.frames] == ["F_0", "F_1", "F_2"]
    assert [frame.role for frame in domain.frames] == [
        "initial",
        "transition",
        "transition",
    ]
    assert len(domain.steps) == 2
    assert [step.name for step in domain.steps] == ["E_0", "E_1"]

    input_ref = domain.event_input(StepRef(0, 2), plant_ping.id)
    assert isinstance(input_ref, EventInputRef)
    assert input_ref.to_canonical() == {
        "node": "event_input_ref",
        "step_index": 0,
        "event_id": plant_ping.id,
        "event_path": "Root.Plant.Ping",
        "name": "E_0[Root.Plant.Ping]",
    }

    same_step_inputs = [
        domain.event_input(StepRef(0, 2), plant_ping.id),
        domain.event_input(StepRef(0, 2), backup_ping.id),
    ]
    assert len({item.event_id for item in same_step_inputs}) == 2
    assert len(domain.event_inputs) == len(domain.steps) * len(domain.events)

    with pytest.raises(InvalidBmcDomain):
        domain.event_by_path("Root.Missing.Go")
    with pytest.raises(InvalidBmcDomain):
        domain.variable_by_name("missing")
    with pytest.raises(InvalidBmcDomain):
        domain.event_input(StepRef(0, 2), 9999)


@pytest.mark.unittest
def test_domain_canonical_dump_is_json_stable(adversarial_model):
    """Canonical domain output contains only stable primitive structures."""
    domain = build_bmc_domain(adversarial_model, bound=1)
    dump = domain.to_canonical()

    assert dump["node"] == "bmc_domain"
    assert dump["bound"] == 1
    assert dump["sentinels"] == {
        "terminate": STATE_TERMINATE_ID,
        "init": STATE_INIT_ID,
    }
    assert all(isinstance(item["id"], int) for item in dump["states"])
    assert all(isinstance(item["id"], int) for item in dump["events"])
    assert all(isinstance(item["id"], int) for item in dump["variables"])
    assert [item["node"] for item in dump["frames"]] == [
        "frame_ref",
        "frame_ref",
    ]
    assert [item["node"] for item in dump["steps"]] == ["step_ref"]
    assert all(item["node"] == "event_input_ref" for item in dump["event_inputs"])
    assert dump["initial_state_ids"] == list(domain.initial_state_ids)
    assert dump["frame0_state_ids"] == list(domain.frame0_state_ids)
    assert dump["stable_state_ids"] == list(domain.stable_state_ids)
    assert dump["recurrence_state_ids"] == list(domain.recurrence_state_ids)
    assert dump == build_bmc_domain(adversarial_model, bound=1).to_canonical()


@pytest.mark.unittest
def test_domain_public_constructor_normalizes_canonical_sequence_order():
    """Public snapshots emit canonical dumps independent of caller order."""
    from pyfcstm.bmc import EventDomainEntry, StateDomainEntry, VarDomainEntry

    root = StateDomainEntry(0, "Root", "Root", "composite", is_root=True)
    leaf = StateDomainEntry(
        1,
        "Root.Leaf",
        "Leaf",
        "leaf",
        parent_path="Root",
        is_stoppable=True,
    )
    terminate = StateDomainEntry(
        STATE_TERMINATE_ID,
        "$STATE_TERMINATE",
        "STATE_TERMINATE",
        "sentinel",
        is_sentinel=True,
    )
    init = StateDomainEntry(
        STATE_INIT_ID,
        "$STATE_INIT",
        "STATE_INIT",
        "sentinel",
        is_sentinel=True,
    )
    go = EventDomainEntry(0, "Root.Go", "Go", "Root", 0)
    stop = EventDomainEntry(1, "Root.Leaf.Stop", "Stop", "Root.Leaf", 1)
    counter = VarDomainEntry(0, "counter", "int")
    pressure = VarDomainEntry(1, "pressure", "float")

    canonical = BmcDomain(
        bound=2,
        states=(init, terminate, root, leaf),
        events=(go, stop),
        variables=(counter, pressure),
        frames=(FrameRef(0, 2), FrameRef(1, 2), FrameRef(2, 2)),
        steps=(StepRef(0, 2), StepRef(1, 2)),
        event_inputs=(
            EventInputRef(0, 0, "Root.Go"),
            EventInputRef(0, 1, "Root.Leaf.Stop"),
            EventInputRef(1, 0, "Root.Go"),
            EventInputRef(1, 1, "Root.Leaf.Stop"),
        ),
        initial_state_ids=(STATE_INIT_ID, STATE_TERMINATE_ID, 0, 1),
        stable_state_ids=(STATE_TERMINATE_ID, 1),
    )
    shuffled = BmcDomain(
        bound=2,
        states=(leaf, root, terminate, init),
        events=(stop, go),
        variables=(pressure, counter),
        frames=(FrameRef(2, 2), FrameRef(0, 2), FrameRef(1, 2)),
        steps=(StepRef(1, 2), StepRef(0, 2)),
        event_inputs=(
            EventInputRef(1, 1, "Root.Leaf.Stop"),
            EventInputRef(0, 1, "Root.Leaf.Stop"),
            EventInputRef(1, 0, "Root.Go"),
            EventInputRef(0, 0, "Root.Go"),
        ),
        initial_state_ids=(1, 0, STATE_TERMINATE_ID, STATE_INIT_ID),
        stable_state_ids=(1, STATE_TERMINATE_ID),
    )

    assert [entry.id for entry in shuffled.states] == [
        STATE_INIT_ID,
        STATE_TERMINATE_ID,
        0,
        1,
    ]
    assert [entry.id for entry in shuffled.events] == [0, 1]
    assert [entry.id for entry in shuffled.variables] == [0, 1]
    assert [entry.index for entry in shuffled.frames] == [0, 1, 2]
    assert [entry.index for entry in shuffled.steps] == [0, 1]
    assert [(entry.step_index, entry.event_id) for entry in shuffled.event_inputs] == [
        (0, 0),
        (0, 1),
        (1, 0),
        (1, 1),
    ]
    assert shuffled.to_canonical() == canonical.to_canonical()


@pytest.mark.unittest
def test_root_state_can_use_sentinel_like_name_without_collision():
    """A user root named like a sentinel still receives a normal state id."""
    model = load_state_machine_from_text("state STATE_TERMINATE;")
    domain = build_bmc_domain(model, bound=1)

    assert domain.state_path_to_id("STATE_TERMINATE") >= 0
    assert domain.state_by_id(STATE_TERMINATE_ID).path == "$STATE_TERMINATE"
    assert domain.state_by_id(STATE_TERMINATE_ID).name == "STATE_TERMINATE"
    assert domain.state_path_to_id("$STATE_TERMINATE") == STATE_TERMINATE_ID


@pytest.mark.unittest
def test_build_domain_rejects_invalid_model_or_bound(adversarial_model):
    """Domain construction rejects non-positive bounds and wrong model types."""
    with pytest.raises(InvalidBmcDomain):
        build_bmc_domain(adversarial_model, bound=0)
    with pytest.raises(InvalidBmcDomain):
        build_bmc_domain(adversarial_model, bound=-1)
    with pytest.raises(InvalidBmcDomain):
        build_bmc_domain(adversarial_model, bound=True)
    with pytest.raises(InvalidBmcDomain):
        build_bmc_domain(object(), bound=1)

    domain = build_bmc_domain(adversarial_model, bound=1)
    with pytest.raises(InvalidBmcDomain, match="model must be StateMachine"):
        BmcDomain(
            domain.bound,
            domain.states,
            domain.events,
            domain.variables,
            domain.frames,
            domain.steps,
            domain.event_inputs,
            domain.initial_state_ids,
            domain.stable_state_ids,
            model=object(),
        )


@pytest.mark.unittest
def test_domain_entry_validation_rejects_malformed_values():
    """Domain value objects reject malformed ids, paths, and kinds."""
    from pyfcstm.bmc import EventDomainEntry, StateDomainEntry, VarDomainEntry

    invalid_factories = [
        lambda: StateDomainEntry(0, "Root", "Root", "bad"),
        lambda: StateDomainEntry(0, "", "Root", "leaf"),
        lambda: StateDomainEntry(-3, "Root", "Root", "leaf"),
        lambda: StateDomainEntry(0, "S", "S", "sentinel", is_sentinel=True),
        lambda: StateDomainEntry(0, "Root", "Root", "pseudo", is_root=True),
        lambda: StateDomainEntry(
            0, "Parent.Root", "Root", "leaf", parent_path="Parent", is_root=True
        ),
        lambda: StateDomainEntry(0, "Root.Child", "Child", "leaf", is_root=True),
        lambda: StateDomainEntry(0, "Root.Child", "Other", "leaf", "Root"),
        lambda: StateDomainEntry(
            STATE_TERMINATE_ID,
            "$STATE_TERMINATE",
            "STATE_TERMINATE",
            "sentinel",
            is_sentinel=True,
            is_stoppable=True,
        ),
        lambda: StateDomainEntry(0, "Root", "Root", "composite", is_stoppable=True),
        lambda: StateDomainEntry(
            0, "Root.Leaf", "Leaf", "leaf", is_generated_combo_pseudo=True
        ),
        lambda: EventDomainEntry(-1, "Root.Go", "Go", "Root", 0),
        lambda: EventDomainEntry(0, "Root.Go", "Go", "Root", -1),
        lambda: EventDomainEntry(0, "", "Go", "Root", 0),
        lambda: EventDomainEntry(0, "Other.Go", "Go", "Root", 0),
        lambda: EventDomainEntry(0, "Root.Other", "Go", "Root", 0),
        lambda: EventDomainEntry(0, "Root.Go", "Go", "Root", 0, 0),
        lambda: VarDomainEntry(-1, "x", "int"),
        lambda: VarDomainEntry(0, "", "int"),
        lambda: EventInputRef(-1, 0, "Root.Go"),
        lambda: EventInputRef(0, -1, "Root.Go"),
        lambda: EventInputRef(0, 0, ""),
    ]

    for factory in invalid_factories:
        with pytest.raises(InvalidBmcDomain):
            factory()


@pytest.mark.unittest
def test_domain_snapshot_validation_rejects_inconsistent_collections():
    """BmcDomain detects duplicate and incomplete internal collections."""
    from pyfcstm.bmc import StateDomainEntry

    state = StateDomainEntry(0, "Root", "Root", "leaf")
    frames = (FrameRef(0, 1), FrameRef(1, 1))
    steps = (StepRef(0, 1),)

    with pytest.raises(InvalidBmcDomain):
        BmcDomain(
            bound=1,
            states=(state, StateDomainEntry(0, "Other", "Other", "leaf")),
            events=(),
            variables=(),
            frames=frames,
            steps=steps,
            event_inputs=(),
            initial_state_ids=(0,),
            stable_state_ids=(0,),
        )
    with pytest.raises(InvalidBmcDomain):
        BmcDomain(
            bound=1,
            states=(object(),),
            events=(),
            variables=(),
            frames=frames,
            steps=steps,
            event_inputs=(),
            initial_state_ids=(0,),
            stable_state_ids=(0,),
        )
    with pytest.raises(InvalidBmcDomain):
        BmcDomain(
            bound=1,
            states="not-a-sequence",
            events=(),
            variables=(),
            frames=frames,
            steps=steps,
            event_inputs=(),
            initial_state_ids=(0,),
            stable_state_ids=(0,),
        )
    with pytest.raises(InvalidBmcDomain):
        BmcDomain(
            bound=1,
            states=(state,),
            events=(),
            variables=(),
            frames=frames,
            steps=steps,
            event_inputs=(),
            initial_state_ids="not-a-sequence",
            stable_state_ids=(0,),
        )
    with pytest.raises(InvalidBmcDomain):
        BmcDomain(
            bound=1,
            states=(state,),
            events=(),
            variables=(),
            frames=frames,
            steps=steps,
            event_inputs=(),
            initial_state_ids=(True,),
            stable_state_ids=(0,),
        )
    with pytest.raises(InvalidBmcDomain):
        BmcDomain(
            bound=1,
            states=(state,),
            events=(),
            variables=(),
            frames=(FrameRef(0, 1),),
            steps=steps,
            event_inputs=(),
            initial_state_ids=(0,),
            stable_state_ids=(0,),
        )
    with pytest.raises(InvalidBmcDomain):
        BmcDomain(
            bound=1,
            states=(state,),
            events=(),
            variables=(),
            frames=frames,
            steps=(),
            event_inputs=(),
            initial_state_ids=(0,),
            stable_state_ids=(0,),
        )


@pytest.mark.unittest
def test_domain_snapshot_validation_rejects_bad_trace_and_input_metadata():
    """BmcDomain validates complete frame, step, sentinel, and input metadata."""
    from pyfcstm.bmc import EventDomainEntry, StateDomainEntry

    leaf = StateDomainEntry(0, "Root", "Root", "leaf", is_root=True, is_stoppable=True)
    terminate = StateDomainEntry(
        STATE_TERMINATE_ID,
        "$STATE_TERMINATE",
        "STATE_TERMINATE",
        "sentinel",
        is_sentinel=True,
    )
    init = StateDomainEntry(
        STATE_INIT_ID,
        "$STATE_INIT",
        "STATE_INIT",
        "sentinel",
        is_sentinel=True,
    )
    event = EventDomainEntry(0, "Root.Go", "Go", "Root", 0)

    def unsafe_event_entry(
        owner_state_path,
        owner_state_id,
        owner_is_generated_combo_pseudo=False,
        path="Root.Go",
        name="Go",
    ):
        entry = object.__new__(EventDomainEntry)
        object.__setattr__(entry, "id", 0)
        object.__setattr__(entry, "path", path)
        object.__setattr__(entry, "name", name)
        object.__setattr__(entry, "owner_state_path", owner_state_path)
        object.__setattr__(entry, "owner_state_id", owner_state_id)
        object.__setattr__(
            entry,
            "owner_is_generated_combo_pseudo",
            owner_is_generated_combo_pseudo,
        )
        return entry

    frames = (FrameRef(0, 1), FrameRef(1, 1))
    steps = (StepRef(0, 1),)
    inputs = (EventInputRef(0, 0, "Root.Go"),)
    other_root = StateDomainEntry(1, "Other", "Other", "composite", is_root=True)
    orphan = StateDomainEntry(1, "Orphan", "Orphan", "composite")
    unknown_parent = StateDomainEntry(
        1, "Missing.Child", "Child", "composite", parent_path="Missing"
    )
    missing_event_field = object.__new__(EventDomainEntry)
    for field_name, value in {
        "id": 0,
        "path": "Root.Go",
        "owner_state_path": "Root",
        "owner_state_id": 0,
        "owner_is_generated_combo_pseudo": False,
    }.items():
        object.__setattr__(missing_event_field, field_name, value)

    valid_kwargs = dict(
        bound=1,
        states=(init, terminate, leaf),
        events=(event,),
        variables=(),
        frames=frames,
        steps=steps,
        event_inputs=inputs,
        initial_state_ids=(STATE_INIT_ID, STATE_TERMINATE_ID, 0),
        stable_state_ids=(STATE_TERMINATE_ID, 0),
    )
    assert (
        BmcDomain(**valid_kwargs).event_input(StepRef(0, 1), 0).event_path == "Root.Go"
    )
    unsorted_domain = BmcDomain(
        **dict(
            valid_kwargs,
            initial_state_ids=(0, STATE_TERMINATE_ID, STATE_INIT_ID),
            stable_state_ids=(0, STATE_TERMINATE_ID),
        )
    )
    assert unsorted_domain.initial_state_ids == (STATE_INIT_ID, STATE_TERMINATE_ID, 0)
    assert unsorted_domain.stable_state_ids == (STATE_TERMINATE_ID, 0)

    bad_cases = [
        dict(states=(terminate, leaf)),
        dict(states=(init, leaf)),
        dict(
            states=(
                init,
                StateDomainEntry(
                    STATE_TERMINATE_ID,
                    "$bad",
                    "STATE_TERMINATE",
                    "sentinel",
                    is_sentinel=True,
                ),
                leaf,
            )
        ),
        dict(
            states=(
                StateDomainEntry(
                    STATE_INIT_ID,
                    "$bad",
                    "STATE_INIT",
                    "sentinel",
                    is_sentinel=True,
                ),
                terminate,
                leaf,
            )
        ),
        dict(
            states=(init, terminate, leaf, other_root),
            initial_state_ids=(STATE_INIT_ID, STATE_TERMINATE_ID, 0, 1),
        ),
        dict(
            states=(init, terminate, leaf, orphan),
            initial_state_ids=(STATE_INIT_ID, STATE_TERMINATE_ID, 0, 1),
        ),
        dict(
            states=(init, terminate, leaf, unknown_parent),
            initial_state_ids=(STATE_INIT_ID, STATE_TERMINATE_ID, 0, 1),
        ),
        dict(frames=(FrameRef(0, 1),)),
        dict(steps=()),
        dict(frames=(FrameRef(0, 1), FrameRef(0, 2))),
        dict(frames=(FrameRef(0, 2), FrameRef(2, 2))),
        dict(frames=(FrameRef(0, 2), FrameRef(1, 2))),
        dict(steps=(StepRef(1, 2),)),
        dict(steps=(StepRef(0, 2),)),
        dict(events=(unsafe_event_entry("Missing", 999, path="Missing.Go"),)),
        dict(events=(unsafe_event_entry("$STATE_TERMINATE", STATE_TERMINATE_ID),)),
        dict(events=(unsafe_event_entry("Missing", 0, path="Missing.Go"),)),
        dict(events=(missing_event_field,)),
        dict(events=(EventDomainEntry(0, "Root.Go", "Go", "Root", 0, True),)),
        dict(events=(unsafe_event_entry("Root", 0, 0),)),
        dict(events=(unsafe_event_entry("Root", 0, path="Other.Go"),)),
        dict(events=(unsafe_event_entry("Root", 0, path="Root.Other"),)),
        dict(events=(unsafe_event_entry("Root", 0, name="Other"),)),
        dict(event_inputs=(EventInputRef(1, 0, "Root.Go"),)),
        dict(event_inputs=(EventInputRef(0, 1, "Root.Go"),)),
        dict(event_inputs=(EventInputRef(0, 0, "Root.Bad"),)),
        dict(initial_state_ids=(0, 0)),
        dict(stable_state_ids=(0, 0)),
        dict(initial_state_ids=(999,)),
        dict(stable_state_ids=(999,)),
        dict(initial_state_ids=(STATE_TERMINATE_ID, 0)),
        dict(stable_state_ids=(STATE_INIT_ID, STATE_TERMINATE_ID, 0)),
    ]

    for overrides in bad_cases:
        kwargs = dict(valid_kwargs)
        kwargs.update(overrides)
        with pytest.raises(InvalidBmcDomain):
            BmcDomain(**kwargs)


@pytest.mark.unittest
def test_domain_snapshot_validation_rejects_hacked_state_entries():
    """BmcDomain revalidates state entries at the snapshot boundary."""
    from pyfcstm.bmc import StateDomainEntry

    def clone_state(entry, **updates):
        hacked = object.__new__(StateDomainEntry)
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
                hacked, field_name, updates.get(field_name, getattr(entry, field_name))
            )
        return hacked

    def rebuild(domain, bad_path, bad_entry):
        return BmcDomain(
            bound=domain.bound,
            states=tuple(
                bad_entry if entry.path == bad_path else entry
                for entry in domain.states
            ),
            events=domain.events,
            variables=domain.variables,
            frames=domain.frames,
            steps=domain.steps,
            event_inputs=domain.event_inputs,
            initial_state_ids=domain.initial_state_ids,
            stable_state_ids=domain.stable_state_ids,
        )

    model = load_state_machine_from_text(
        """
        state Root {
          pseudo state Choice;
          state Composite {
            state A;
            [*] -> A;
          }
          [*] -> Composite;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    by_path = {entry.path: entry for entry in domain.states}

    hacked_cases = [
        (
            "$STATE_TERMINATE",
            clone_state(by_path["$STATE_TERMINATE"], is_stoppable=True),
        ),
        (
            "$STATE_TERMINATE",
            clone_state(by_path["$STATE_TERMINATE"], parent_path="Root"),
        ),
        (
            "$STATE_TERMINATE",
            clone_state(by_path["$STATE_TERMINATE"], is_root=True),
        ),
        (
            "$STATE_TERMINATE",
            clone_state(by_path["$STATE_TERMINATE"], is_generated_combo_pseudo=True),
        ),
        (
            "Root.Composite",
            clone_state(by_path["Root.Composite"], is_stoppable=True),
        ),
        (
            "Root.Composite.A",
            clone_state(by_path["Root.Composite.A"], is_generated_combo_pseudo=True),
        ),
        (
            "Root.Choice",
            clone_state(by_path["Root.Choice"], is_sentinel=True),
        ),
        (
            "Root.Composite.A",
            clone_state(by_path["Root.Composite.A"], kind="sentinel"),
        ),
        (
            "Root.Composite.A",
            clone_state(by_path["Root.Composite.A"], is_stoppable="yes"),
        ),
        (
            "Root.Composite",
            clone_state(by_path["Root.Composite"], is_root=True),
        ),
        (
            "Root.Composite.A",
            clone_state(by_path["Root.Composite.A"], parent_path=None),
        ),
        (
            "Root.Composite.A",
            clone_state(by_path["Root.Composite.A"], parent_path="Root.Missing"),
        ),
        (
            "Root.Composite.A",
            clone_state(
                by_path["Root.Composite.A"],
                path="Root.Choice.A",
                parent_path="Root.Choice",
            ),
        ),
        (
            "Root.Composite.A",
            clone_state(by_path["Root.Composite.A"], name="B"),
        ),
        (
            "Root",
            clone_state(by_path["Root"], parent_path="Root.Composite"),
        ),
        (
            "Root",
            clone_state(by_path["Root"], name="NotRoot"),
        ),
    ]

    for bad_path, bad_entry in hacked_cases:
        with pytest.raises(InvalidBmcDomain):
            rebuild(domain, bad_path, bad_entry)

    extra_sentinel = object.__new__(StateDomainEntry)
    for field_name, value in {
        "id": -3,
        "path": "$EXTRA",
        "name": "EXTRA",
        "kind": "sentinel",
        "parent_path": None,
        "is_root": False,
        "is_stoppable": False,
        "is_sentinel": True,
        "is_generated_combo_pseudo": False,
    }.items():
        object.__setattr__(extra_sentinel, field_name, value)

    with pytest.raises(InvalidBmcDomain):
        BmcDomain(
            bound=domain.bound,
            states=domain.states + (extra_sentinel,),
            events=domain.events,
            variables=domain.variables,
            frames=domain.frames,
            steps=domain.steps,
            event_inputs=domain.event_inputs,
            initial_state_ids=domain.initial_state_ids,
            stable_state_ids=domain.stable_state_ids,
        )

    missing_field = object.__new__(StateDomainEntry)
    for field_name, value in {
        "id": 0,
        "path": "Root",
        "kind": "leaf",
        "parent_path": None,
        "is_root": True,
        "is_stoppable": True,
        "is_sentinel": False,
        "is_generated_combo_pseudo": False,
    }.items():
        object.__setattr__(missing_field, field_name, value)

    with pytest.raises(InvalidBmcDomain):
        BmcDomain(
            bound=domain.bound,
            states=(missing_field,) + domain.states[1:],
            events=domain.events,
            variables=domain.variables,
            frames=domain.frames,
            steps=domain.steps,
            event_inputs=domain.event_inputs,
            initial_state_ids=domain.initial_state_ids,
            stable_state_ids=domain.stable_state_ids,
        )


@pytest.mark.unittest
def test_domain_snapshot_validation_rejects_wrong_allowed_state_sets():
    """BmcDomain enforces frame-state set semantics for public construction."""
    model = load_state_machine_from_text(
        """
        state Root {
          pseudo state Choice;
          state Composite {
            state A;
            [*] -> A;
          }
          [*] -> Composite;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)

    root_id = domain.state_path_to_id("Root")
    composite_id = domain.state_path_to_id("Root.Composite")
    pseudo_id = domain.state_path_to_id("Root.Choice")
    leaf_id = domain.state_path_to_id("Root.Composite.A")
    assert domain.stable_state_ids == (STATE_TERMINATE_ID, leaf_id)

    for forbidden_id in (root_id, composite_id, pseudo_id):
        with pytest.raises(InvalidBmcDomain):
            BmcDomain(
                bound=domain.bound,
                states=domain.states,
                events=domain.events,
                variables=domain.variables,
                frames=domain.frames,
                steps=domain.steps,
                event_inputs=domain.event_inputs,
                initial_state_ids=domain.initial_state_ids,
                stable_state_ids=tuple(
                    sorted(domain.stable_state_ids + (forbidden_id,))
                ),
            )

    with pytest.raises(InvalidBmcDomain):
        BmcDomain(
            bound=domain.bound,
            states=domain.states,
            events=domain.events,
            variables=domain.variables,
            frames=domain.frames,
            steps=domain.steps,
            event_inputs=domain.event_inputs,
            initial_state_ids=tuple(
                item for item in domain.initial_state_ids if item != root_id
            ),
            stable_state_ids=domain.stable_state_ids,
        )

    with pytest.raises(InvalidBmcDomain):
        BmcDomain(
            bound=domain.bound,
            states=domain.states,
            events=domain.events,
            variables=domain.variables,
            frames=domain.frames,
            steps=domain.steps,
            event_inputs=domain.event_inputs,
            initial_state_ids=domain.initial_state_ids + (-2,),
            stable_state_ids=domain.stable_state_ids,
        )


@pytest.mark.unittest
def test_domain_lookup_validation_rejects_wrong_reference_types(adversarial_model):
    """Lookup helpers reject wrong id types, stale steps, and malformed paths."""
    domain = build_bmc_domain(adversarial_model, bound=2)

    with pytest.raises(InvalidBmcDomain):
        domain.state_by_id(True)
    with pytest.raises(InvalidBmcDomain):
        domain.state_by_path("")
    with pytest.raises(InvalidBmcDomain):
        domain.event_by_id(True)
    with pytest.raises(InvalidBmcDomain):
        domain.event_by_path("")
    with pytest.raises(InvalidBmcDomain):
        domain.variable_by_id(True)
    with pytest.raises(InvalidBmcDomain):
        domain.variable_by_name("")
    with pytest.raises(InvalidBmcDomain):
        domain.event_input(object(), domain.events[0].id)
    with pytest.raises(InvalidBmcDomain):
        domain.event_input(StepRef(0, 1), domain.events[0].id)


@pytest.mark.unittest
def test_domain_reports_inconsistent_event_owners_and_missing_input_slots():
    """Domain construction and lookup expose impossible internal references."""
    from pyfcstm.model import Event, State, StateMachine, Transition

    root = State(
        name="Root",
        path=("Root",),
        substates={},
        transitions=[
            Transition(
                from_state="Root",
                to_state="Root",
                event=Event("Ghost", ("Missing",)),
                guard=None,
                effects=[],
            )
        ],
    )
    model = StateMachine(defines={}, root_state=root)

    with pytest.raises(InvalidBmcDomain):
        build_bmc_domain(model, bound=1)

    event_domain = build_bmc_domain(
        load_state_machine_from_text("state Root { event Go; state A; [*] -> A; }"),
        bound=1,
    )
    with pytest.raises(InvalidBmcDomain):
        BmcDomain(
            bound=1,
            states=event_domain.states,
            events=event_domain.events,
            variables=event_domain.variables,
            frames=event_domain.frames,
            steps=event_domain.steps,
            event_inputs=(),
            initial_state_ids=event_domain.initial_state_ids,
            stable_state_ids=event_domain.stable_state_ids,
        )

    unsafe_domain = object.__new__(BmcDomain)
    object.__setattr__(unsafe_domain, "bound", 1)
    object.__setattr__(unsafe_domain, "states", event_domain.states)
    object.__setattr__(unsafe_domain, "events", event_domain.events)
    object.__setattr__(unsafe_domain, "variables", event_domain.variables)
    object.__setattr__(unsafe_domain, "frames", event_domain.frames)
    object.__setattr__(unsafe_domain, "steps", event_domain.steps)
    object.__setattr__(unsafe_domain, "event_inputs", ())
    object.__setattr__(
        unsafe_domain, "initial_state_ids", event_domain.initial_state_ids
    )
    object.__setattr__(unsafe_domain, "stable_state_ids", event_domain.stable_state_ids)

    with pytest.raises(InvalidBmcDomain):
        unsafe_domain.event_input(StepRef(0, 1), event_domain.events[0].id)

    with pytest.raises(InvalidBmcDomain):
        event_domain.variable_by_id(999)
    with pytest.raises(InvalidBmcDomain):
        event_domain.variable_by_id(0)
    with pytest.raises(InvalidBmcDomain):
        build_bmc_domain(
            load_state_machine_from_text("def int x = 0; state Root;"), bound=1
        ).variable_by_id(999)
