"""Tables and storage sizes the C kernel generator derives from a model."""

import re

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.render.c_kernel import (
    action_rows,
    event_paths,
    hook_rows,
    iter_action_items,
    private_storage_bytes,
    render_c_kernel_code,
    render_c_kernel_types,
    render_c_storage_macros,
)

pytestmark = pytest.mark.unittest

REGION_SOURCE = """
def int x = 0;
state Root {
    event Go;
    enter abstract Boot;
    >> during before abstract Tick;
    [*] -> P;
    state P {
        region A {
            event Ping;
            >> during after { x = x + 1; }
            [*] -> A1;
            state A1 { during abstract Work; }
        }
        region B { [*] -> B1; state B1; }
    }
}
"""

FLAT_SOURCE = "state Root { [*] -> A; state A; }"

TWO_REGIONS_SOURCE = (
    "state Root { [*] -> P; state P {"
    " region A { [*] -> A1; state A1; }"
    " region B { [*] -> B1; state B1; } } }"
)


@pytest.fixture(scope="module")
def region_model():
    return load_state_machine_from_text(REGION_SOURCE)


@pytest.mark.parametrize(
    "source, expected",
    [
        (REGION_SOURCE, ["Root.Go", "Root.P.A.Ping"]),
        (FLAT_SOURCE, []),
    ],
)
def test_event_paths_count_state_and_region_events_in_id_order(source, expected):
    assert event_paths(load_state_machine_from_text(source)) == expected


def test_iter_action_items_visits_states_with_regions_in_tree_order(region_model):
    assert [(group, item.func_name) for _, group, item in iter_action_items(region_model)] == [
        ("enter", "Root.Boot"),
        ("aspect_before", "Root.Tick"),
        ("aspect_after", "Root.P.A.<unnamed>"),
        ("during", "Root.P.A.A1.Work"),
    ]


def test_action_rows_hold_one_row_per_distinct_action(region_model):
    assert action_rows(region_model) == [
        {"func_name": "Root.Boot"},
        {"func_name": "Root.Tick"},
        {"func_name": "Root.P.A.<unnamed>"},
        {"func_name": "Root.P.A.A1.Work"},
    ]


def test_hook_rows_keep_abstract_actions_only(region_model):
    rows = hook_rows(region_model)
    assert [(row["func_name"], row["stage"], row["aspect"], row["owner_path"]) for row in rows] == [
        ("Root.Boot", "enter", None, "Root"),
        ("Root.Tick", "during", "before", "Root"),
        ("Root.P.A.A1.Work", "during", None, "Root.P.A.A1"),
    ]
    assert rows[2]["dsl_fragment"] == "during abstract Work;"
    fields = [row["hook_field"] for row in rows]
    assert len(set(fields)) == len(fields)
    assert all(re.match(r"^on_[0-9A-Za-z_]+$", field) for field in fields)


def test_hooks_reached_through_ref_share_one_row():
    model = load_state_machine_from_text(
        """
        state Root {
            enter abstract Shared;
            [*] -> A;
            state A { enter ref /Shared; }
            state B { enter ref /Shared; }
        }
        """
    )
    assert [row["func_name"] for row in hook_rows(model)] == ["Root.Shared"]


def test_private_storage_grows_with_the_search_a_model_needs():
    flat = load_state_machine_from_text(FLAT_SOURCE)
    regions = load_state_machine_from_text(TWO_REGIONS_SOURCE)
    assert private_storage_bytes(flat) < private_storage_bytes(regions)
    assert private_storage_bytes(regions, extra_bytes=48) == private_storage_bytes(regions) + 48
    assert private_storage_bytes(regions, arena_capacity=100) > private_storage_bytes(regions)
    assert private_storage_bytes(regions) % 16 == 0


def test_storage_macros_agree_with_the_computed_size():
    model = load_state_machine_from_text(TWO_REGIONS_SOURCE)
    text = render_c_storage_macros(model, "ROOT_MACHINE")
    arena = int(re.search(r"ROOT_MACHINE_ARENA_CAPACITY (\d+)", text).group(1))
    trail = int(re.search(r"ROOT_MACHINE_TRAIL_CAPACITY (\d+)", text).group(1))
    fixed, per_arena, per_trail = (
        int(value)
        for value in re.search(
            r"STORAGE_BYTES \((\d+) \+ \(ROOT_MACHINE_ARENA_CAPACITY\) \* (\d+)"
            r" \+ \(ROOT_MACHINE_TRAIL_CAPACITY\) \* (\d+)\)",
            text,
        ).groups()
    )
    # The macros are the formula behind private_storage_bytes at the default
    # capacities, so an override recomputes the same size.
    assert fixed + arena * per_arena + trail * per_trail == private_storage_bytes(model)
    assert text.count("#ifndef") == 2


def test_rendered_kernel_declares_its_capacity_macros_and_entry_points(region_model):
    types = render_c_kernel_types(region_model, "RootMachine", "ROOT_MACHINE")
    code = render_c_kernel_code(region_model, "RootMachine", "ROOT_MACHINE")
    assert "ROOT_MACHINE_ARENA_CAPACITY" in types
    assert "@" not in code.replace("@param", "")
    assert re.search(r"static int _RootMachine_run_cycle\(", code)
    # Every abstract action has a place in the hook table.
    for row in hook_rows(region_model):
        assert row["hook_field"] in code or row["hook_field"] in types
