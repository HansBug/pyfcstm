"""Tests for the collection gate that rejects tests no selector reaches.

The gate in :mod:`test.conftest` is the only thing standing between a new test module
and the silent deselection that hid 102 tests from ``make unittest``. It is also the
kind of check that fails open: if it stopped recognising an unmarked item, nothing
would go red and the protection would be gone without a signal. These tests keep it
honest by asserting both halves -- that it reports an unmarked item, and that it stays
quiet for every marker that legitimately opts out.
"""

import pytest

from test.conftest import (
    _OUT_OF_SUITE_MARKERS,
    _SUITE_MARKER,
    _items_no_selector_reaches,
    _unreached_items_message,
)

pytestmark = pytest.mark.unittest


class _StubMarker:
    """The one attribute the gate reads off a marker."""

    def __init__(self, name):
        self.name = name


class _StubItem:
    """A pytest item stand-in carrying only what the gate reads.

    A real item needs a session, a module and a collection to exist, none of which the
    gate looks at. Building the two things it does read keeps the test about the gate
    rather than about pytest's collection internals.

    ``keywords`` is populated too, holding the test name the way pytest does, so that a
    gate reading keywords instead of markers would fail the mixed-batch test below
    instead of passing it by accident.
    """

    def __init__(self, nodeid, markers=()):
        self.nodeid = nodeid
        self._markers = tuple(_StubMarker(name) for name in markers)
        self.keywords = {nodeid.rsplit("::", 1)[-1]: True}

    def iter_markers(self):
        return iter(self._markers)


def test_an_unmarked_item_is_reported():
    items = [_StubItem("test/pkg/test_thing.py::test_one")]

    assert _items_no_selector_reaches(items) == ["test/pkg/test_thing.py::test_one"]


def test_the_suite_marker_satisfies_the_gate():
    items = [_StubItem("test/pkg/test_thing.py::test_one", (_SUITE_MARKER,))]

    assert _items_no_selector_reaches(items) == []


@pytest.mark.parametrize(
    "marker",
    sorted(_OUT_OF_SUITE_MARKERS),
    # The ids are prefixed because a bare id equal to a marker name lands in the item's
    # keywords, and the native-toolchain gate elsewhere in conftest reads keywords -- so
    # the `native_toolchain` case was skipped rather than run, which is the same silent
    # non-execution this whole gate exists to prevent.
    ids=lambda name: "marker-%s" % name,
)
def test_each_out_of_suite_marker_satisfies_the_gate(marker):
    # Parametrised over the set rather than over a hand-written list: adding a marker to
    # _OUT_OF_SUITE_MARKERS without meaning it to exempt anything then fails here.
    items = [_StubItem("test/pkg/test_thing.py::test_one", (marker,))]

    assert _items_no_selector_reaches(items) == []


def test_only_the_unmarked_items_of_a_mixed_batch_are_reported():
    items = [
        _StubItem("test/a/test_marked.py::test_one", (_SUITE_MARKER,)),
        _StubItem("test/b/test_bare.py::test_two"),
        _StubItem("test/c/test_optin.py::test_three", ("native_toolchain",)),
        _StubItem("test/b/test_bare.py::test_four"),
    ]

    assert _items_no_selector_reaches(items) == [
        "test/b/test_bare.py::test_two",
        "test/b/test_bare.py::test_four",
    ]


def test_the_message_names_each_module_and_its_count():
    message = _unreached_items_message(
        [
            "test/b/test_bare.py::test_two",
            "test/b/test_bare.py::test_four",
            "test/a/test_other.py::test_one",
        ]
    )

    # The count and the module names are what turn the failure into an actionable
    # instruction; a bare total would leave the reader grepping for the cause.
    assert "3 test(s)" in message
    assert "test/b/test_bare.py (2 test(s))" in message
    assert "test/a/test_other.py (1 test(s))" in message
    assert "pytest.mark.%s" % _SUITE_MARKER in message
    for marker in _OUT_OF_SUITE_MARKERS:
        assert marker in message
