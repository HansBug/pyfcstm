"""Configuration patterns for ``active(...)`` over a model with regions.

``active("Root.Run")`` asks whether the machine is in a state or below it.  For a
model with regions the same atom can also take the text of a configuration, the
way a witness prints it, and then it is a *pattern*: the regions that the text
writes have to be where it says, and the regions it leaves out are not
constrained.

* ``Root.Run{Safety: Watching}`` - ``Root.Run`` is active and the region
  ``Safety`` is in ``Watching`` (or below it); ``Motion`` may be anywhere;
* ``Root.Run{Motion: [done]}`` - ``Motion`` has finished;
* ``Root.Run{Motion: [init]}`` - ``Motion`` waits for its initialization, which
  a committed frame only shows after a hot start, and a call made while the
  group is being entered shows for the regions that have not started;
* ``Root.Run{Motion: Inner{X: x1}}`` - a region of a nested owner, written the
  way it nests.

A path without braces is the pattern that writes no region, so ``active("Root.Run")``
means what it always meant.  This differs from ``init state(...)`` on purpose:
a start *constructs* a position, so a region it leaves out waits for
initialization, while a pattern *matches* one, so a region it leaves out is free.
A position that an ``init state(...)`` text builds always matches the same text
as a pattern.

The module contains:

* :class:`ActivePattern` - A parsed pattern.
* :func:`parse_active_pattern` - Read and check a pattern against a domain.
* :func:`active_over` - The predicate of ``active(path)`` over any positions.
* :func:`pattern_predicate` - The predicate of a pattern over any positions.

Example::

    >>> from pyfcstm.bmc.domain import build_bmc_domain
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('''
    ... state Root {
    ...     region A { [*] -> P; state P; }
    ...     region B { [*] -> Q; state Q; }
    ... }
    ... ''')
    >>> pattern = parse_active_pattern(build_bmc_domain(model, 1), 'Root{A: P, B: [done]}')
    >>> pattern.state_path, [name for name, _ in pattern.regions]
    ('Root', ['Root.A', 'Root.B'])
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Union

import z3

from .domain import (
    REGION_DONE_ID,
    REGION_INACTIVE_ID,
    REGION_PENDING_ID,
    STATE_INIT_ID,
    BmcDomain,
)
from .errors import InvalidBmcDomain, InvalidBmcQuery
from pyfcstm.model.configuration import read_configuration_pattern
from pyfcstm.solver.term import and_terms, or_terms

_Provider = Callable[[str], z3.ExprRef]


class _TermMemo:
    """Terms over position expressions that many predicates of one build share.

    A predicate over the positions at the moment of a call is built once per call,
    and from one call to the next nearly every region is where it was: its
    position is the very same expression.  The memo hands back the term that was
    built for an expression before instead of building it again.  An expression
    is recognized by the object that wraps it, and failing that by the term it
    wraps, so an equal constant made a second time is recognized as well.
    """

    def __init__(self) -> None:
        self._by_object: Dict[tuple, tuple] = {}
        self._by_term: Dict[tuple, z3.BoolRef] = {}

    def equals(self, symbol: z3.ExprRef, value: int) -> z3.BoolRef:
        """Return ``symbol == z3.IntVal(value)``."""
        key = (id(symbol), value)
        found = self._by_object.get(key)
        if found is None:
            term_key = (symbol.get_id(), value)
            term = self._by_term.get(term_key)
            if term is None:
                term = symbol == z3.IntVal(value)
                self._by_term[term_key] = term
            # The object is kept so that its identity is not handed to another.
            found = (symbol, term)
            self._by_object[key] = found
        return found[1]

    def active(
        self, target_path: str, symbols: Tuple[z3.ExprRef, ...]
    ) -> Optional[z3.BoolRef]:
        """Return the predicate remembered for a state over these positions, if any."""
        found = self._by_object.get((target_path,) + tuple(map(id, symbols)))
        return None if found is None else found[1]

    def remember_active(
        self, target_path: str, symbols: Tuple[z3.ExprRef, ...], term: z3.BoolRef
    ) -> None:
        """Remember the predicate of a state over these positions."""
        self._by_object[(target_path,) + tuple(map(id, symbols))] = (symbols, term)


# A predicate that reads more places than this is not looked up as a whole: the
# key would cost what the predicate does, and it rarely repeats.
_MEMO_WIDTH = 4


@dataclass(frozen=True)
class ActivePattern:
    """A configuration pattern for ``active(...)``.

    :param state_path: Path of the state that has to be active.
    :type state_path: str
    :param regions: The regions the pattern writes, as ``(region path, wanted)``
        pairs, where ``wanted`` is a nested :class:`ActivePattern`, ``"done"`` or
        ``"init"``; empty for a plain state path.
    :type regions: Tuple[Tuple[str, Union[ActivePattern, str]], ...], optional

    Example::

        >>> ActivePattern('Root.Run').regions
        ()
    """

    state_path: str
    regions: Tuple[Tuple[str, Union["ActivePattern", str]], ...] = ()


def parse_active_pattern(domain: BmcDomain, text: str) -> ActivePattern:
    """Read the text of a configuration as a pattern and check it against a domain.

    :param domain: Domain of the model.
    :type domain: pyfcstm.bmc.domain.BmcDomain
    :param text: A state path, or configuration text with region blocks.
    :type text: str
    :return: The pattern.
    :rtype: ActivePattern
    :raises pyfcstm.bmc.errors.InvalidBmcQuery: If the text is not a pattern of
        this model: a syntax error, a state that does not exist, a region the
        state does not own, a region written twice, or region blocks in a model without regions.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root { region A { [*] -> P; state P; } region B { [*] -> Q; state Q; } }')
        >>> domain = build_bmc_domain(model, 1)
        >>> parse_active_pattern(domain, 'Root{A: P}').regions[0][0]
        'Root.A'
        >>> parse_active_pattern(domain, 'Root{C: P}')
        Traceback (most recent call last):
            ...
        pyfcstm.bmc.errors.InvalidBmcQuery: state 'Root' has no region 'C'.
    """
    # A pattern is a value, and the same text is asked about once per frame and
    # once per call, so the pattern of a text is read and checked once per domain.
    parsed = domain._index.active_patterns
    pattern = parsed.get(text)
    if pattern is None:
        try:
            tree = read_configuration_pattern(text)
        except ValueError as err:
            # ValueError: syntax error or nesting too deep in the pattern text.
            raise InvalidBmcQuery("%s" % (err,)) from err
        if tree["regions"] and not domain.regions:
            raise InvalidBmcQuery(
                "the model declares no regions, so a configuration pattern with "
                "region blocks matches nothing."
            )
        pattern = _check(domain, tree)
        parsed[text] = pattern
    return pattern


def _check(domain: BmcDomain, node: dict) -> ActivePattern:
    """Check one node of a pattern read from text and turn it into a pattern."""
    state = str(node["state"])
    try:
        domain.state_by_path(state)
    except InvalidBmcDomain as err:
        # InvalidBmcDomain: BmcDomain lookup rejects paths that are not states.
        raise InvalidBmcQuery(str(err)) from err
    owned = {
        region.name: region for region in domain._index.regions_by_owner.get(state, ())
    }
    written: List[Tuple[str, Union[ActivePattern, str]]] = []
    seen = set()
    for item in node["regions"]:
        name = item["name"]
        if name not in owned:
            raise InvalidBmcQuery("state %r has no region %r." % (state, name))
        if name in seen:
            raise InvalidBmcQuery("region %r of %r is written twice." % (name, state))
        seen.add(name)
        region = owned[name]
        wanted = item["configuration"]
        if isinstance(wanted, str):
            written.append((region.path, wanted))
            continue
        child = _check(domain, wanted)
        written.append((region.path, child))
    return ActivePattern(state, tuple(written))


def _active_places(
    domain: BmcDomain, target_path: str
) -> Tuple[Tuple[Tuple[int, Optional[str]], ...], Tuple[Optional[str], ...]]:
    """Return where ``active(target_path)`` looks, which only depends on the domain.

    The first value lists, in the order of the domain's states, every state id
    that makes the target active together with the region whose position can hold
    it, or ``None`` for the state the machine rests in outside every region.  The
    second value lists the distinct places among them, in the same order.
    """
    index = domain._index
    found = index.active_places.get(target_path)
    if found is None:
        target = domain.state_by_path(target_path)
        entries = [
            entry for entry in index.subtree(target_path) if not entry.is_sentinel
        ]
        if target.is_root and STATE_INIT_ID in index.state_by_id:
            entries.append(index.state_by_id[STATE_INIT_ID])
        entries.sort(key=index.state_position)
        looked: List[Tuple[int, Optional[str]]] = []
        places: List[Optional[str]] = []
        seen = set()
        for entry in entries:
            owner = None if entry.is_sentinel else index.nearest_region(entry.path)
            looked.append((entry.id, owner))
            if owner not in seen:
                seen.add(owner)
                places.append(owner)
        found = (tuple(looked), tuple(places))
        index.active_places[target_path] = found
    return found


def active_over(
    domain: BmcDomain,
    target_path: str,
    main: z3.ExprRef,
    region: _Provider,
    memo: Optional[_TermMemo] = None,
) -> z3.BoolRef:
    """Return the predicate of ``active(target_path)`` over some positions.

    A state is active when the state the machine rests in outside every region is
    the state or one of its descendants, or when the position of a region is the
    state or one of its descendants.  A state below a region is only ever named by
    the position of the nearest region above it, so every state is looked at once,
    for the symbol of the place it can be a position of.

    :param domain: Domain of a model with regions.
    :type domain: pyfcstm.bmc.domain.BmcDomain
    :param target_path: Path of the state asked about.
    :type target_path: str
    :param main: State the machine rests in outside every region.
    :type main: z3.ExprRef
    :param region: Position of a region, given its path.
    :type region: Callable[[str], z3.ExprRef]
    :param memo: Terms shared with the other predicates of the same build; the
        predicate is the same with and without it; defaults to ``None``.
    :type memo: _TermMemo, optional
    :return: The predicate.
    :rtype: z3.BoolRef

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root { region A { [*] -> P; state P; } region B { [*] -> Q; state Q; } }')
        >>> domain = build_bmc_domain(model, 1)
        >>> main = z3.Int('main'); a = z3.Int('a'); b = z3.Int('b')
        >>> predicate = active_over(domain, 'Root.A.P', main, {'Root.A': a, 'Root.B': b}.get)
        >>> z3.is_bool(predicate)
        True
    """
    looked, places = _active_places(domain, target_path)
    symbols = {owner: main if owner is None else region(owner) for owner in places}
    if memo is None:
        return or_terms(
            [symbols[owner] == z3.IntVal(state_id) for state_id, owner in looked]
        )
    read = None
    if len(places) <= _MEMO_WIDTH:
        read = tuple(symbols[owner] for owner in places)
        known = memo.active(target_path, read)
        if known is not None:
            return known
    result = or_terms(
        [memo.equals(symbols[owner], state_id) for state_id, owner in looked]
    )
    if read is not None:
        memo.remember_active(target_path, read, result)
    return result


def pattern_predicate(
    domain: BmcDomain,
    pattern: ActivePattern,
    main: z3.ExprRef,
    region: _Provider,
    memo: Optional[_TermMemo] = None,
) -> z3.BoolRef:
    """Return the predicate that a pattern holds over some positions.

    :param domain: Domain of a model with regions.
    :type domain: pyfcstm.bmc.domain.BmcDomain
    :param pattern: A pattern checked against the domain.
    :type pattern: ActivePattern
    :param main: State the machine rests in outside every region.
    :type main: z3.ExprRef
    :param region: Position of a region, given its path.
    :type region: Callable[[str], z3.ExprRef]
    :param memo: Terms shared with the other predicates of the same build; the
        predicate is the same with and without it; defaults to ``None``.
    :type memo: _TermMemo, optional
    :return: The predicate.
    :rtype: z3.BoolRef

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root { region A { [*] -> P; state P; } region B { [*] -> Q; state Q; } }')
        >>> domain = build_bmc_domain(model, 1)
        >>> pattern = parse_active_pattern(domain, 'Root{B: [done]}')
        >>> predicate = pattern_predicate(domain, pattern, z3.IntVal(0), {'Root.A': z3.Int('a'), 'Root.B': z3.IntVal(REGION_DONE_ID)}.get)
        >>> z3.is_true(z3.simplify(predicate)) or z3.is_false(z3.simplify(predicate))
        True
    """

    def equals(position: z3.ExprRef, value: int) -> z3.BoolRef:
        if memo is None:
            return position == z3.IntVal(value)
        return memo.equals(position, value)

    terms = [active_over(domain, pattern.state_path, main, region, memo)]
    for region_path, wanted in pattern.regions:
        if wanted == "done":
            terms.append(equals(region(region_path), REGION_DONE_ID))
        elif wanted == "init":
            # The owner is active (the pattern says so), so a region it has not yet
            # started is waiting for its start: that is a region the frame calls
            # pending, and also one that a call made while the owner is being
            # entered still holds as not placed at all.
            position = region(region_path)
            terms.append(
                or_terms(
                    [
                        equals(position, REGION_PENDING_ID),
                        equals(position, REGION_INACTIVE_ID),
                    ]
                )
            )
        else:
            terms.append(pattern_predicate(domain, wanted, main, region, memo))
    return and_terms(terms) if len(terms) > 1 else terms[0]


__all__ = [
    "ActivePattern",
    "parse_active_pattern",
    "active_over",
    "pattern_predicate",
]
