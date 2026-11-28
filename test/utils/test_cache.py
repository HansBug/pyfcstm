"""Bounded and scoped tables for caches that outlive a single call."""

import threading

import pytest

from pyfcstm.utils import BoundedTable, ScopedMemo

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize("limit", [0, -1, 1.5, True, "3", None])
def test_a_table_needs_a_positive_integer_limit(limit) -> None:
    with pytest.raises(ValueError, match="limit must be a positive int"):
        BoundedTable(limit)


def test_a_table_stores_and_returns_values() -> None:
    table = BoundedTable(4)
    table.put("a", 1)

    assert table.get("a") == 1
    assert table.get("missing") is None
    assert table.get("missing", "fallback") == "fallback"
    assert "a" in table and "missing" not in table and len(table) == 1


def test_a_full_table_is_emptied_before_the_next_store() -> None:
    table = BoundedTable(2)
    table.put("a", 1)
    table.put("b", 2)
    table.put("c", 3)

    assert len(table) == 1
    assert table.get("a") is None and table.get("c") == 3
    assert table.stats()["clears"] == 1


def test_overwriting_a_key_does_not_count_as_growth() -> None:
    table = BoundedTable(2)
    table.put("a", 1)
    table.put("a", 2)
    table.put("b", 3)

    assert table.get("a") == 2 and table.stats()["clears"] == 0


def test_the_statistics_describe_use() -> None:
    table = BoundedTable(3)
    table.put("a", 1)
    table.get("a")
    table.get("a")
    table.get("b")
    table.clear()

    assert table.stats() == {
        "entries": 0,
        "limit": 3,
        "hits": 2,
        "misses": 1,
        "clears": 1,
    }


def test_a_table_keeps_what_it_holds_alive_until_it_is_emptied() -> None:
    import gc
    import weakref

    class Probe:
        pass

    probe = Probe()
    reference = weakref.ref(probe)
    table = BoundedTable(2)
    table.put(id(probe), (probe, "value"))
    del probe
    gc.collect()
    assert reference() is not None
    table.clear()
    gc.collect()
    assert reference() is None


def test_a_memo_has_no_table_outside_a_scope() -> None:
    assert ScopedMemo().table is None


def test_a_scope_creates_and_drops_the_table() -> None:
    memo = ScopedMemo()
    with memo.scope(4) as table:
        table.put("k", 1)
        assert memo.table is table and memo.table.get("k") == 1

    assert memo.table is None


def test_a_nested_scope_joins_the_outer_table_and_its_limit() -> None:
    memo = ScopedMemo()
    with memo.scope(8) as outer:
        outer.put("k", 1)
        with memo.scope(1) as inner:
            assert inner is outer and inner.limit == 8
        assert memo.table is outer and outer.get("k") == 1

    assert memo.table is None


def test_an_exception_still_drops_the_table() -> None:
    memo = ScopedMemo()
    with pytest.raises(RuntimeError):
        with memo.scope(4):
            raise RuntimeError("stop")

    assert memo.table is None


def test_an_invalid_limit_leaves_no_table_behind() -> None:
    memo = ScopedMemo()
    with pytest.raises(ValueError):
        with memo.scope(0):
            pass

    assert memo.table is None


def test_scopes_of_different_threads_are_independent() -> None:
    memo = ScopedMemo()
    seen = []
    with memo.scope(4) as table:
        table.put("k", 1)
        worker = threading.Thread(target=lambda: seen.append(memo.table))
        worker.start()
        worker.join()
        assert memo.table is table

    assert seen == [None]


def test_scopes_are_independent_between_memos() -> None:
    first, second = ScopedMemo(), ScopedMemo()
    with first.scope(4):
        assert second.table is None
