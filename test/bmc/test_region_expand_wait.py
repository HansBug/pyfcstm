"""The wait unit of a state that only a cycle can leave, through its public expander."""

import pytest

from pyfcstm.bmc.domain import build_bmc_domain
from pyfcstm.bmc.errors import InvalidBmcEncoding
from pyfcstm.bmc.region_expand import expand_wait_unit
from pyfcstm.model import load_state_machine_from_text

pytestmark = pytest.mark.unittest

MODEL = """
state Root {
    region A {
        [*] -> C;
        state C { [*] -> L; state L; }
        state S;
        pseudo state P;
        P -> S;
    }
    region B { [*] -> Q; state Q; }
}
"""


def domain():
    return build_bmc_domain(load_state_machine_from_text(MODEL), 1)


def test_a_plain_composite_state_waits_for_its_initial_transition():
    unit = expand_wait_unit(domain(), "Root.A.C")
    assert [(case.kind, case.target_state_path) for case in unit.cases] == [
        ("initial", "Root.A.C.L")
    ]


def test_a_pseudo_state_leaves_through_its_transition():
    unit = expand_wait_unit(domain(), "Root.A.P")
    assert [(case.kind, case.target_state_path) for case in unit.cases] == [
        ("transition", "Root.A.S")
    ]


@pytest.mark.parametrize(
    "argument, path",
    [
        ("not a domain", "Root.A.C"),
        (None, "Root.A.C"),
    ],
)
def test_a_wait_unit_needs_a_domain(argument, path):
    with pytest.raises(InvalidBmcEncoding, match="domain must be BmcDomain"):
        expand_wait_unit(argument, path)


@pytest.mark.parametrize(
    "path, message",
    [
        ("Root.Nowhere", None),
        ("Root.A.S", "wait unit starts at"),
        ("Root", "wait unit starts at"),
    ],
)
def test_a_wait_unit_refuses_what_is_not_a_waiting_state(path, message):
    with pytest.raises(InvalidBmcEncoding, match=message):
        expand_wait_unit(domain(), path)
