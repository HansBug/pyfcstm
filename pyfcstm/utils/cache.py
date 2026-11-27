"""
Bounded and scoped tables for caches that outlive a single call.

A cache that lives as long as the process, or as long as a block of work, must
state three things: how many entries it may hold, what happens when it is full,
and when it is dropped.  The two tables here fix those answers once so that every
shared cache of :mod:`pyfcstm` answers them the same way and can report them.

The module contains:

* :class:`BoundedTable` - A table with an entry limit that is emptied when full
* :class:`ScopedMemo` - A per-thread :class:`BoundedTable` that exists only
  while a block runs

.. note::
   A table that is keyed by ``id(obj)`` is only correct while ``obj`` is alive,
   because Python hands the number of a freed object to the next one.  Store the
   object in the entry, next to the value, so that the number stays taken for as
   long as the entry exists.  Both tables hold what they are given, so entries
   made this way keep their objects alive until the table is emptied or dropped.

Example::

    >>> table = BoundedTable(2)
    >>> table.put("a", 1)
    >>> table.put("b", 2)
    >>> table.get("a"), table.get("missing")
    (1, None)
    >>> table.put("c", 3)
    >>> len(table), table.get("a"), table.stats()["clears"]
    (1, None, 1)
"""

import contextlib
import threading
from typing import Any, Dict, Generic, Hashable, Iterator, Optional, TypeVar

__all__ = [
    "BoundedTable",
    "ScopedMemo",
]

_K = TypeVar("_K", bound=Hashable)
_V = TypeVar("_V")


def _require_limit(limit: Any) -> int:
    """Return ``limit`` after checking that it is a positive plain ``int``.

    :param limit: Candidate entry limit.
    :type limit: Any
    :return: The same limit.
    :rtype: int
    :raises ValueError: If ``limit`` is not a positive ``int``.

    Example::

        >>> _require_limit(3)
        3
        >>> _require_limit(0)
        Traceback (most recent call last):
          ...
        ValueError: limit must be a positive int, got 0.
    """
    if type(limit) is not int or limit <= 0:
        raise ValueError("limit must be a positive int, got %r." % (limit,))
    return limit


class BoundedTable(Generic[_K, _V]):
    """A key-value table that is emptied when it reaches its limit.

    The table never evicts one entry at a time: it keeps the cost of a store at
    one dictionary write, and it drops everything it holds, together with
    whatever the entries keep alive, in one step.  It is meant for caches whose
    entries are cheap to rebuild.

    :param limit: Number of entries after which the next store empties the
        table first.
    :type limit: int
    :raises ValueError: If ``limit`` is not a positive ``int``.

    :ivar limit: Entry limit.
    :vartype limit: int

    Example::

        >>> table = BoundedTable(1)
        >>> table.put("x", 10)
        >>> table.get("x")
        10
        >>> table.put("y", 20)
        >>> "x" in table, table.get("y")
        (False, 20)
    """

    __slots__ = ("_items", "limit", "_hits", "_misses", "_clears")

    def __init__(self, limit: int) -> None:
        self.limit = _require_limit(limit)
        self._items: Dict[_K, _V] = {}
        self._hits = 0
        self._misses = 0
        self._clears = 0

    def get(self, key: _K, default: Optional[_V] = None) -> Optional[_V]:
        """Return the value stored under ``key``.

        :param key: Key to look up.
        :type key: Hashable
        :param default: Returned when there is no entry, defaults to ``None``.
        :type default: Any, optional
        :return: The stored value or ``default``.
        :rtype: Any

        Example::

            >>> table = BoundedTable(4)
            >>> table.get("k", "none")
            'none'
        """
        try:
            value = self._items[key]
        except KeyError:
            # KeyError: the ordinary miss; counted and answered with the default.
            self._misses += 1
            return default
        self._hits += 1
        return value

    def put(self, key: _K, value: _V) -> None:
        """Store ``value`` under ``key``, emptying the table first when it is full.

        :param key: Key to store under.
        :type key: Hashable
        :param value: Value to keep.
        :type value: Any
        :return: ``None``.
        :rtype: None

        Example::

            >>> table = BoundedTable(4)
            >>> table.put("k", 1)
            >>> table.get("k")
            1
        """
        if len(self._items) >= self.limit:
            self.clear()
        self._items[key] = value

    def clear(self) -> None:
        """Drop every entry.

        :return: ``None``.
        :rtype: None

        Example::

            >>> table = BoundedTable(4)
            >>> table.put("k", 1)
            >>> table.clear()
            >>> len(table)
            0
        """
        self._items.clear()
        self._clears += 1

    def __len__(self) -> int:
        return len(self._items)

    def __contains__(self, key: object) -> bool:
        return key in self._items

    def stats(self) -> Dict[str, int]:
        """Return what the table holds and how it has been used.

        :return: ``entries``, ``limit``, ``hits``, ``misses`` and ``clears``
            (how often the table was emptied, by a full store or by
            :meth:`clear`).
        :rtype: Dict[str, int]

        Example::

            >>> table = BoundedTable(4)
            >>> table.put("k", 1)
            >>> table.get("k"), table.get("other")
            (1, None)
            >>> table.stats()
            {'entries': 1, 'limit': 4, 'hits': 1, 'misses': 1, 'clears': 0}
        """
        return {
            "entries": len(self._items),
            "limit": self.limit,
            "hits": self._hits,
            "misses": self._misses,
            "clears": self._clears,
        }


class _Slot(threading.local):
    """Per-thread holder of the table of the open scope.

    :ivar table: Table of the outermost open scope of this thread, or ``None``.
    :vartype table: Optional[BoundedTable]
    """

    def __init__(self) -> None:
        self.table: Optional[BoundedTable] = None


class ScopedMemo:
    """A table that exists on each thread only while a block runs.

    Work that asks the same question many times can open a scope around itself
    and look answers up in :attr:`table`.  The table is created by the outermost
    scope of a thread and dropped when that scope exits, also when it exits
    with an exception, so nothing outlives the work that needed it.  A scope
    opened inside another one on the same thread joins it and shares its table
    and its limit.

    Example::

        >>> memo = ScopedMemo()
        >>> memo.table is None
        True
        >>> with memo.scope(8):
        ...     memo.table.put("k", 1)
        ...     with memo.scope(2):
        ...         joined = memo.table.get("k")
        >>> joined, memo.table is None
        (1, True)
    """

    def __init__(self) -> None:
        self._slot = _Slot()

    @property
    def table(self) -> Optional[BoundedTable]:
        """The table of the open scope of the calling thread.

        :return: The table, or ``None`` outside every scope.
        :rtype: Optional[BoundedTable]
        """
        return self._slot.table

    @contextlib.contextmanager
    def scope(self, limit: int) -> Iterator[BoundedTable]:
        """Open a scope, or join the one that is already open on this thread.

        :param limit: Entry limit of the table when this scope creates it;
            ignored by a scope that joins.
        :type limit: int
        :return: A context manager yielding the table of the scope.
        :rtype: Iterator[BoundedTable]
        :raises ValueError: If ``limit`` is not a positive ``int`` and this scope
            has to create the table.

        Example::

            >>> memo = ScopedMemo()
            >>> with memo.scope(4) as table:
            ...     table.put("k", 1)
            ...     inside = memo.table is table
            >>> inside, memo.table is None
            (True, True)
        """
        if self._slot.table is not None:
            yield self._slot.table
            return
        try:
            self._slot.table = BoundedTable(limit)
            yield self._slot.table
        finally:
            self._slot.table = None
