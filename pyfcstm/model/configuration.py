"""Immutable recursive positions for ordinary and ordered parallel models.

Configurations describe position without initializing or executing a model.
Stable, initialization and transient positions have separate validation modes.
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Tuple, TYPE_CHECKING, Union

from .region import Region, namespace_child

if TYPE_CHECKING:
    from .model import State, StateMachine


class _RegionInit(Enum):
    """A region position before its initial transition has run."""

    PENDING = 'init'


@dataclass(frozen=True)
class _Position:
    path: Tuple[str, ...]
    regions: Tuple[Tuple[str, Union['_Position', _RegionInit, None]], ...] = ()


_TEXT_TOKENS = re.compile(r'\[init\]|\[done\]|[A-Za-z_][A-Za-z_0-9]*|\S')
_TEXT_IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z_0-9]*')


def _lookup(model, path):
    """Resolve a full namespace path without implicit ancestor search."""
    parts = tuple(path.split('.')) if isinstance(path, str) else tuple(path)
    current = model.root_state
    if not parts or parts[0] != current.name:
        raise ValueError('Unknown configuration path: %r.' % (path,))
    for segment in parts[1:]:
        current = namespace_child(current, segment)
        if current is None:
            raise ValueError('Unknown configuration path: %r.' % (path,))
    return current


class _TextParser:
    """Parse paths and region blocks independently of runtime state."""

    def __init__(self, text):
        if not isinstance(text, str):
            raise TypeError('Configuration text must be a string.')
        self.text = text
        self.tokens = [(match.group(), match.start()) for match in _TEXT_TOKENS.finditer(text)]
        self.index = 0

    def peek(self):
        return self.tokens[self.index][0] if self.index < len(self.tokens) else ''

    def error(self, expected):
        offset = self.tokens[self.index][1] if self.index < len(self.tokens) else len(self.text)
        line = self.text.count('\n', 0, offset) + 1
        column = offset - self.text.rfind('\n', 0, offset)
        raise ValueError('Expected %s at line %d, column %d, got %r.' %
                         (expected, line, column, self.peek()))

    def take(self, expected=None):
        token = self.peek()
        if not token or (expected is not None and token != expected):
            self.error(repr(expected))
        self.index += 1
        return token

    def identifier(self):
        if _TEXT_IDENTIFIER.fullmatch(self.peek()) is None:
            self.error('a configuration identifier')
        return self.take()

    def position(self, base=()):
        path = [self.identifier()]
        while self.peek() == '.':
            self.take('.')
            path.append(self.identifier())
        path = (*base, *path)
        regions = []
        if self.peek() == '{':
            self.take('{')
            while True:
                name = self.identifier()
                self.take(':')
                if self.peek() == '[done]':
                    self.take('[done]')
                    child = None
                elif self.peek() == '[init]':
                    self.take('[init]')
                    child = _RegionInit.PENDING
                else:
                    child = self.position((*path, name))
                regions.append((name, child))
                if self.peek() != ',':
                    break
                self.take(',')
            self.take('}')
        return _Position(path, tuple(regions))


def _from_dict(data, outer=False):
    """Read JSON-compatible values into owned immutable tuples."""
    if not isinstance(data, dict):
        raise TypeError('A configuration node must be a dictionary.')
    allowed = {'state', 'regions', 'mode'} if outer else {'state', 'regions'}
    if 'state' not in data or set(data) - allowed:
        raise ValueError('A configuration node requires state and accepts only %s.' % sorted(allowed))
    if not isinstance(data['state'], str):
        raise TypeError('Configuration state must be a full path string.')
    regions = data.get('regions', [])
    if not isinstance(regions, list):
        raise TypeError('Configuration regions must be an ordered list.')
    result = []
    for entry in regions:
        if not isinstance(entry, dict) or set(entry) != {'name', 'configuration'}:
            raise ValueError('Each region requires name and configuration.')
        if not isinstance(entry['name'], str):
            raise TypeError('Region name must be a string.')
        child = entry['configuration']
        result.append((entry['name'], None if child is None else _from_dict(child)))
    return _Position(tuple(data['state'].split('.')), tuple(result))


def _to_dict(position):
    """Return newly allocated JSON-compatible containers."""
    return {'state': '.'.join(position.path), 'regions': [
        {'name': name, 'configuration': None if child is None else _to_dict(child)}
        for name, child in position.regions if child is not _RegionInit.PENDING
    ]}


def _positions(position):
    """Walk active positions in model declaration order."""
    yield position
    for _, child in position.regions:
        if isinstance(child, _Position):
            yield from _positions(child)


def _text(position, prefix=0):
    result = '.'.join(position.path[prefix:])
    if position.regions:
        parts = []
        for name, child in position.regions:
            if child is None:
                value = '[done]'
            elif child is _RegionInit.PENDING:
                value = '[init]'
            else:
                value = _text(child, len(position.path) + 1)
            parts.append('%s: %s' % (name, value))
        result += '{' + ', '.join(parts) + '}'
    return result


def _validate(model, position, base, mode):
    """Validate one branch, then return a declaration-ordered value."""
    path = position.path
    if path[:len(base)] != base or len(path) <= len(base):
        raise ValueError('Configuration path %r is outside namespace %r.' % (path, base))
    state = _lookup(model, path)
    if isinstance(state, Region):
        raise ValueError('A configuration branch must end at a State, not a Region.')
    # A linear path cannot skip a parallel owner and select just one region.
    for end in range(len(base) + 1, len(path)):
        ancestor = _lookup(model, path[:end])
        if getattr(ancestor, 'regions', {}):
            raise ValueError('Parallel owner %s requires a region block.' % '.'.join(ancestor.path))
    context = '.'.join(path)
    entries = dict(position.regions)
    if len(entries) != len(position.regions):
        raise ValueError('Duplicate region in configuration for %s.' % context)
    if set(entries) - set(state.regions):
        raise ValueError('Unknown region in configuration for %s.' % context)
    if mode == 'stable':
        if state.is_pseudo or state.substates:
            raise ValueError('Stable configuration must reach a non-pseudo leaf at %s.' % context)
        if state.regions and set(entries) != set(state.regions):
            raise ValueError('Missing region in stable configuration for %s.' % context)
        if any(child is _RegionInit.PENDING for child in entries.values()):
            raise ValueError('Stable configuration cannot contain pending regions at %s.' % context)
        if state.regions and all(child is None for child in entries.values()):
            raise ValueError('All regions are Done at %s.' % context)
    ordered = []
    for name in state.regions:
        child = entries.get(name, _RegionInit.PENDING)
        if isinstance(child, _Position):
            child = _validate(model, child, (*path, name), mode)
        ordered.append((name, child))
    return _Position(path, tuple(ordered))


@dataclass(frozen=True)
class Configuration:
    """An immutable, model-bound tree of active state positions.

    Construct values with :meth:`parse` or :meth:`from_dict`. ``stable`` mode
    requires complete region configurations and a non-pseudo leaf on each live
    branch. ``initialization`` accepts one whole composite/parallel owner path.
    ``transient`` also accepts intermediate pseudo states, partial region
    initialization and all-Done snapshots; it does not execute them.

    Text uses ``[init]`` for pending regions and ``[done]`` for completed ones.
    ``str(config)`` includes every region of each active parallel owner in
    declaration order. ``repr(config)`` includes both position and mode for
    debugging; it is not constructor syntax. Text omits mode, so use
    ``Configuration.parse(model, str(config), mode=config.mode)`` to roundtrip.
    JSON retains omitted pending entries and ``null`` for completed regions.

    Equality and hashing compare the mode and ordered paths by value. The model
    supplies State objects returned by :attr:`leaves`, but is not part of value
    equality. Returned JSON containers are independent copies.

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root { state Idle; [*] -> Idle; }')
        >>> config = Configuration.parse(model, 'Root.Idle')
        >>> str(config), config.is_active('Root')
        ('Root.Idle', True)
        >>> Configuration.from_dict(model, config.to_dict()) == config
        True
    """

    _model: 'StateMachine' = field(repr=False, compare=False)
    _position: _Position = field(repr=False)
    mode: str = 'stable'

    def __post_init__(self):
        if self.mode not in ('stable', 'initialization', 'transient'):
            raise ValueError('Unknown configuration mode: %r.' % self.mode)
        position = _validate(self._model, self._position, (), self.mode)
        if self.mode == 'initialization':
            state = _lookup(self._model, position.path)
            if state.is_leaf_state or any(child is not _RegionInit.PENDING for _, child in position.regions):
                raise ValueError('Initialization requires one whole owner path.')
        object.__setattr__(self, '_position', position)

    @classmethod
    def parse(cls, model, text: str, *, mode: str = 'stable'):
        """Parse configuration text and validate it against ``model``.

        :param model: State machine owning all referenced paths.
        :param text: Full state path with optional recursive region blocks.
            Region values are relative state paths, ``[init]`` or ``[done]``.
            Whitespace, including newlines, is allowed between tokens.
        :param mode: ``stable``, ``initialization`` or ``transient``.
        :return: A new immutable configuration.
        :raises TypeError: If text is not a string.
        :raises ValueError: On malformed text or invalid position. Syntax errors
            include one-based line and character column numbers; tabs count as
            one character and lines are separated by newline characters.
        """
        parser = _TextParser(text)
        position = parser.position()
        if parser.peek():
            parser.error('end of input')
        return cls(model, position, mode)

    @classmethod
    def from_dict(cls, model, data):
        """Read the recursive dictionary produced by :meth:`to_dict`.

        :param model: State machine used for validation.
        :param data: JSON-compatible tree; omitted mode defaults to stable.
        :return: A new immutable configuration owning its position data.
        """
        position = _from_dict(data, outer=True)
        return cls(model, position, data.get('mode', 'stable'))

    def to_dict(self):
        """Return a fresh JSON tree with mode, state and ordered regions."""
        return dict(mode=self.mode, **_to_dict(self._position))

    def __str__(self):
        return _text(self._position)

    def __repr__(self):
        return 'Configuration(mode=%r, position=%r)' % (self.mode, str(self))

    @property
    def leaves(self) -> Tuple['State', ...]:
        """Active leaf States in declaration order, excluding Done regions.

        Transient snapshots may include pseudo leaves. Pending composite owners
        contribute no leaf until their children have initialized.
        """
        states = (_lookup(self._model, node.path) for node in _positions(self._position))
        return tuple(state for state in states if state.is_leaf_state)

    def is_active(self, path) -> bool:
        """Whether the State at a full string/tuple path is active.

        :raises ValueError: If the path is unknown or names a Region.
        """
        state = _lookup(self._model, path)
        if isinstance(state, Region):
            raise ValueError('is_active requires a State path.')
        return any(node.path[:len(state.path)] == state.path for node in _positions(self._position))

    def region_status(self, path) -> str:
        """Return ``live``, ``done``, ``pending`` or ``inactive`` for a Region.

        Pending means the active owner has not initialized that region yet.
        Inactive means the owner is outside this configuration.
        :raises ValueError: If the path is unknown or names a State.
        """
        region = _lookup(self._model, path)
        if not isinstance(region, Region):
            raise ValueError('region_status requires a Region path.')
        for position in _positions(self._position):
            if position.path == region.path[:-1]:
                children = dict(position.regions)
                if children[region.name] is _RegionInit.PENDING:
                    return 'pending'
                return 'done' if children[region.name] is None else 'live'
        return 'inactive'
