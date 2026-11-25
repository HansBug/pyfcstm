"""Read the start position of a hot start of a model with regions.

``init state("...")`` of a query names a state, or for a model with regions a whole
position tree, and the machine rests there when the trace begins; the first cycle
then runs from it without entering anything.  A position can be spelled the ways
the simulator accepts for a hot start:

* a configuration text such as ``Controller.Running{Safety: Watching, Motion: On}``,
  where a region that is left out, or written ``[init]``, waits for initialization
  and ``[done]`` is a region that finished;
* a dotted path of a state, which may pass through regions: the regions on the way
  hold that one branch and the other regions of their owners wait;
* the path of an owner or of a plain composite state alone: the state waits for
  initialization as a whole.

The module reads such a start against the domain of a model.  It does not build any
formula: :class:`RegionStart` only says where every region is when the trace begins.

The module contains:

* :class:`RegionStart` - Where the machine rests when a hot-start trace begins.
* :func:`resolve_region_start` - Read a start position against a model.

Example::

    >>> from pyfcstm.bmc.domain import build_bmc_domain
    >>> from pyfcstm.bmc.region_start import resolve_region_start
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('''
    ... state Root {
    ...     region A { [*] -> P; state P; }
    ...     region B { [*] -> Q; state Q; }
    ... }
    ... ''')
    >>> start = resolve_region_start(build_bmc_domain(model, 1), 'Root{A: P}')
    >>> (start.main, dict(start.positions))
    ('Root', {'Root.A': 'Root.A.P', 'Root.B': 'pending'})
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Tuple

from .domain import BmcDomain
from .errors import InvalidBmcDomain, InvalidBmcQuery
from pyfcstm.model import Configuration

DONE = "done"
PENDING = "pending"


@dataclass(frozen=True)
class RegionStart:
    """Where the machine rests when the trace of a hot start begins.

    :param main: Path of the state the machine rests in outside every region: the
        outermost owner on the way to the named position, or the named state
        itself when it sits in no region.
    :type main: str
    :param positions: For every region of every owner that is resting, the path
        of the state the region's branch is in, ``"done"`` for a region that
        finished, or ``"pending"`` for a region that waits for initialization.
        A state that is not a leaf, or a pseudo state, is a branch that waits for
        its first cycle.
    :type positions: Mapping[str, str]

    Example::

        >>> RegionStart('Root', {'Root.A': 'pending'}).main
        'Root'
    """

    main: str
    positions: Mapping[str, str]


def _read(
    domain: BmcDomain, node: Mapping[str, object], positions: Dict[str, str]
) -> None:
    """Record the positions of the regions of one configuration node, nested ones included.

    :raises InvalidBmcQuery: If every region of an owner is done.
    """
    owner = str(node["state"])
    declared = [region for region in domain.regions if region.owner_path == owner]
    given = {item["name"]: item["configuration"] for item in node.get("regions") or []}
    done = 0
    for region in declared:
        if region.name not in given:
            positions[region.path] = PENDING
        elif given[region.name] is None:
            positions[region.path] = DONE
            done += 1
        else:
            child = given[region.name]
            positions[region.path] = str(child["state"])
            _read(domain, child, positions)
    if declared and done == len(declared):
        raise InvalidBmcQuery(
            "all regions are done at %r; a finished owner cannot be hot-started."
            % owner
        )


def _node_of_state(domain: BmcDomain, path: str) -> Dict[str, object]:
    """Return the configuration node that holds one state and lets everything else wait.

    The node is rooted at the outermost owner on the way to the state, with the
    regions on the way holding their branch.  The state may sit below composite
    states inside a region; those are part of its path.
    """
    node: Dict[str, object] = {"state": path, "regions": []}
    current = domain.state_by_path(path)
    while True:
        if current.region_path is not None:
            region = next(
                item for item in domain.regions if item.path == current.region_path
            )
            node = {
                "state": region.owner_path,
                "regions": [{"name": region.name, "configuration": node}],
            }
            current = domain.state_by_path(region.owner_path)
        elif current.parent_path is not None:
            current = domain.state_by_path(current.parent_path)
        else:
            return node


def resolve_region_start(domain: BmcDomain, start: str) -> RegionStart:
    """Read a start position of a hot start against the domain of a model.

    The text is read the way the simulator reads the ``initial_state`` of a hot
    start, so a position that works there works here and the other way round.

    :param domain: Domain of a model that declares regions.
    :type domain: pyfcstm.bmc.domain.BmcDomain
    :param start: Configuration text (anything with a ``{``), or a dotted state
        path that may pass through regions.
    :type start: str
    :return: Where the machine rests when the trace begins.
    :rtype: RegionStart
    :raises pyfcstm.bmc.errors.InvalidBmcQuery: If the text is not a position of
        this model, names a state that does not exist or a region instead of a
        state, or leaves every region of some owner done.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.bmc.region_start import resolve_region_start
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     region A { [*] -> P; state P; P -> [*]; }
        ...     region B { [*] -> Q; state Q; Q -> [*]; }
        ... }
        ... ''')
        >>> domain = build_bmc_domain(model, 1)
        >>> dict(resolve_region_start(domain, 'Root.A.P').positions)
        {'Root.A': 'Root.A.P', 'Root.B': 'pending'}
        >>> resolve_region_start(domain, 'Root{A: [done], B: [done]}')
        Traceback (most recent call last):
            ...
        pyfcstm.bmc.errors.InvalidBmcQuery: all regions are done at 'Root'; a finished owner cannot be hot-started.
    """
    if "{" in start:
        try:
            tree = Configuration.parse(domain.model, start, mode="transient").to_dict()
        except (ValueError, TypeError) as err:
            # ValueError: the text is not a position of this model; TypeError: the
            # text is not text.
            raise InvalidBmcQuery("%s" % (err,)) from err
    else:
        try:
            tree = _node_of_state(domain, start)
        except InvalidBmcDomain as err:
            # InvalidBmcDomain: BmcDomain lookup rejects paths that are not states.
            raise InvalidBmcQuery(str(err)) from err
    positions: Dict[str, str] = {}
    _read(domain, tree, positions)
    return RegionStart(str(tree["state"]), positions)


__all__ = ["DONE", "PENDING", "RegionStart", "resolve_region_start"]
