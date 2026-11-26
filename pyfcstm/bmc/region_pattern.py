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
from typing import Callable, List, Tuple, Union

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

_Provider = Callable[[str], z3.ExprRef]


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
    return _check(domain, tree)


def _check(domain: BmcDomain, node: dict) -> ActivePattern:
    """Check one node of a pattern read from text and turn it into a pattern."""
    state = str(node["state"])
    try:
        domain.state_by_path(state)
    except InvalidBmcDomain as err:
        # InvalidBmcDomain: BmcDomain lookup rejects paths that are not states.
        raise InvalidBmcQuery(str(err)) from err
    owned = {region.name: region for region in domain.regions if region.owner_path == state}
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


def active_over(
    domain: BmcDomain, target_path: str, main: z3.ExprRef, region: _Provider
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
    target = domain.state_by_path(target_path)
    by_path = {entry.path: entry for entry in domain.states}

    def below_target(entry) -> bool:
        current = entry
        while True:
            if current.path == target.path:
                return True
            if current.parent_path is None:
                return False
            current = by_path[current.parent_path]

    def nearest_region(entry):
        current = entry
        while current.region_path is None and current.parent_path is not None:
            current = by_path[current.parent_path]
        return current.region_path

    terms: List[z3.BoolRef] = []
    for entry in domain.states:
        if entry.is_sentinel:
            if entry.id == STATE_INIT_ID and target.is_root:
                terms.append(main == z3.IntVal(entry.id))
            continue
        if not below_target(entry):
            continue
        owner = nearest_region(entry)
        symbol = main if owner is None else region(owner)
        terms.append(symbol == z3.IntVal(entry.id))
    return z3.Or(*terms) if terms else z3.BoolVal(False)


def pattern_predicate(
    domain: BmcDomain, pattern: ActivePattern, main: z3.ExprRef, region: _Provider
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
    terms = [active_over(domain, pattern.state_path, main, region)]
    for region_path, wanted in pattern.regions:
        if wanted == "done":
            terms.append(region(region_path) == z3.IntVal(REGION_DONE_ID))
        elif wanted == "init":
            # The owner is active (the pattern says so), so a region it has not yet
            # started is waiting for its start: that is a region the frame calls
            # pending, and also one that a call made while the owner is being
            # entered still holds as not placed at all.
            position = region(region_path)
            terms.append(
                z3.Or(
                    position == z3.IntVal(REGION_PENDING_ID),
                    position == z3.IntVal(REGION_INACTIVE_ID),
                )
            )
        else:
            terms.append(pattern_predicate(domain, wanted, main, region))
    return z3.And(*terms) if len(terms) > 1 else terms[0]


__all__ = [
    "ActivePattern",
    "parse_active_pattern",
    "active_over",
    "pattern_predicate",
]
