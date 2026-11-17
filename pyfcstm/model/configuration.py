"""
Immutable recursive positions for ordinary and ordered parallel models.

A :class:`Configuration` answers "where is the machine right now?" as a
value: one active state path for an ordinary model, and, below every parallel
owner state, one recursive position per region in declaration order. It is the
position type returned for models that declare regions, and it can also be
built for ordinary models, where it degenerates to a single path.

A configuration only describes a position. It never initializes, steps or
executes the model, and it never mutates the model it is bound to. Three
validation modes separate what may be described:

* ``stable`` - a resting position: every live branch ends at a non-pseudo leaf
  and every region of an active parallel owner is present.
* ``initialization`` - one whole composite or parallel owner whose children
  have not been initialized yet (each region is ``[init]``).
* ``transient`` - an intermediate snapshot taken while a cycle is running:
  pseudo states, partially initialized regions and all-Done owners are allowed.

The text form is the shortest way to write a position. A state is a dotted
full path; an active parallel owner is followed by a ``{...}`` block that maps
each region name to a relative position, ``[init]`` (not initialized yet) or
``[done]`` (completed).

The module contains:

* :class:`Configuration` - Immutable, model-bound tree of active positions

Example::

    >>> from pyfcstm.model import Configuration, load_state_machine_from_text
    >>> model = load_state_machine_from_text('''
    ... state Root {
    ...     [*] -> Run;
    ...     state Run {
    ...         region Motion { [*] -> Stop; state Stop; state Move; Stop -> Move :: Go; }
    ...         region Guard { [*] -> Watch; state Watch; }
    ...     }
    ...     state Off;
    ...     Run -> Off :: Halt;
    ... }
    ... ''')
    >>> config = Configuration.parse(model, 'Root.Run{Motion: Stop, Guard: Watch}')
    >>> str(config)
    'Root.Run{Motion: Stop, Guard: Watch}'
    >>> [state.name for state in config.leaves]
    ['Stop', 'Watch']
    >>> config.is_active('Root.Run'), config.is_active('Root.Run.Motion.Move')
    (True, False)
    >>> Configuration.from_dict(model, config.to_dict()) == config
    True

.. note::
   Configuration paths are full paths from the root state; there is no
   implicit ancestor search. Regions are namespaces, so a region name appears
   in the path of every state it contains (``Root.Run.Motion.Stop``).
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from reprlib import Repr
from typing import Tuple, TYPE_CHECKING, Union

from .region import Region, namespace_child

if TYPE_CHECKING:
    from .model import State, StateMachine


class _RegionInit(Enum):
    """
    Marker for a region whose initial transition has not run yet.

    A region child of an active parallel owner is one of three things: a
    :class:`_Position` (live), ``None`` (Done) or :attr:`PENDING` (this marker,
    written ``[init]`` in text). The marker is never serialized by
    :meth:`Configuration.to_dict`; an omitted region entry reads back as pending.

    :cvar PENDING: The only member; the region is declared but not initialized.
    """

    PENDING = 'init'


@dataclass(frozen=True)
class _Position:
    """
    One node of the recursive position tree behind :class:`Configuration`.

    :param path: Full state path from the root state, for example
        ``('Root', 'Run')``.
    :type path: Tuple[str, ...]
    :param regions: ``(region_name, child)`` pairs for the regions of this
        state, in declaration order once validated. ``child`` is a nested
        :class:`_Position`, ``None`` for Done, or :attr:`_RegionInit.PENDING`.
        Empty for ordinary states and leaves.
    :type regions: Tuple[Tuple[str, Union[_Position, _RegionInit, None]], ...]
    """

    path: Tuple[str, ...]
    regions: Tuple[Tuple[str, Union['_Position', _RegionInit, None]], ...] = ()


_TEXT_TOKENS = re.compile(r'\[init\]|\[done\]|[A-Za-z_][A-Za-z_0-9]*|\S')
_TEXT_IDENTIFIER = re.compile(r'[A-Za-z_][A-Za-z_0-9]*')
_ERROR_REPR = Repr()
_ERROR_REPR.maxstring = 80


def _lookup(model, path):
    """
    Resolve a full path to a state or region without any ancestor search.

    :param model: State machine whose root state anchors the path.
    :type model: pyfcstm.model.model.StateMachine
    :param path: Dotted string or sequence of names; the first name must be the
        root state's own name.
    :type path: Union[str, Sequence[str]]
    :return: The :class:`~pyfcstm.model.model.State` or
        :class:`~pyfcstm.model.region.Region` the path names.
    :rtype: Union[pyfcstm.model.model.State, pyfcstm.model.region.Region]
    :raises ValueError: If the path is empty, does not start at the root state
        or names an unknown child at any step.
    """
    parts = tuple(path.split('.')) if isinstance(path, str) else tuple(path)
    current = model.root_state
    if not parts or parts[0] != current.name:
        raise ValueError('Unknown configuration path: %s.' % _ERROR_REPR.repr(path))
    for segment in parts[1:]:
        current = namespace_child(current, segment)
        if current is None:
            raise ValueError('Unknown configuration path: %s.' % _ERROR_REPR.repr(path))
    return current


class _TextParser:
    """
    Tokenize and parse configuration text into a :class:`_Position` tree.

    The parser is purely syntactic: it knows nothing about the model, so every
    semantic check (unknown names, missing regions, modes) happens later in
    :func:`_validate`. Tokens are ``[init]``, ``[done]``, identifiers and any
    other single non-space character, which lets punctuation errors point at
    the offending character instead of failing in the tokenizer.

    :param text: Configuration text.
    :type text: str
    :raises TypeError: If ``text`` is not a string.

    :ivar text: The original text, kept for line and column reporting.
    :vartype text: str
    :ivar tokens: ``(token, character offset)`` pairs in source order.
    :vartype tokens: List[Tuple[str, int]]
    :ivar index: Index of the next unread token.
    :vartype index: int
    """

    def __init__(self, text):
        """
        Tokenize ``text`` and position the parser at its first token.

        :param text: Configuration text.
        :type text: str
        :raises TypeError: If ``text`` is not a string.
        """
        if not isinstance(text, str):
            raise TypeError('Configuration text must be a string.')
        self.text = text
        self.tokens = [(match.group(), match.start()) for match in _TEXT_TOKENS.finditer(text)]
        self.index = 0

    def peek(self):
        """
        Return the next token without consuming it.

        :return: The next token, or ``''`` once the input is exhausted.
        :rtype: str
        """
        return self.tokens[self.index][0] if self.index < len(self.tokens) else ''

    def location(self):
        """
        Describe the position of the next token for error messages.

        :return: ``'line N, column M'`` with one-based numbers; newline-separated
            lines and tabs counted as one character. At the end of input the
            position just past the last character is reported.
        :rtype: str
        """
        offset = self.tokens[self.index][1] if self.index < len(self.tokens) else len(self.text)
        line = self.text.count('\n', 0, offset) + 1
        column = offset - self.text.rfind('\n', 0, offset)
        return 'line %d, column %d' % (line, column)

    def error(self, expected):
        """
        Raise a syntax error that names what was expected and what was found.

        :param expected: Human-readable description of the expected token.
        :type expected: str
        :raises ValueError: Always; the message carries the line, the column
            and a shortened excerpt of the offending token.
        """
        actual = _ERROR_REPR.repr(self.peek()) if self.peek() else 'end of input'
        raise ValueError('Expected %s at %s, got %s.' % (expected, self.location(), actual))

    def take(self, expected=None):
        """
        Consume and return the next token.

        :param expected: Exact token that must come next, or ``None`` to accept
            any token. Defaults to ``None``.
        :type expected: Optional[str]
        :return: The consumed token.
        :rtype: str
        :raises ValueError: If the input is exhausted or the token differs from
            ``expected``.
        """
        token = self.peek()
        if not token or (expected is not None and token != expected):
            self.error(repr(expected))
        self.index += 1
        return token

    def identifier(self):
        """
        Consume one identifier token.

        :return: The identifier (``[A-Za-z_][A-Za-z_0-9]*``).
        :rtype: str
        :raises ValueError: If the next token is not an identifier.
        """
        if _TEXT_IDENTIFIER.fullmatch(self.peek()) is None:
            self.error('a configuration identifier')
        return self.take()

    def position(self, base=()):
        """
        Parse one dotted path optionally followed by a ``{...}`` region block.

        Region values are parsed recursively with the region's own full path as
        ``base``, so ``Root.Run{Motion: Stop}`` reads ``Stop`` as
        ``('Root', 'Run', 'Motion', 'Stop')``. Nesting depth is bounded only by
        the interpreter stack; :meth:`Configuration.parse` converts the
        resulting ``RecursionError`` into a ``ValueError``.

        :param base: Full path of the namespace this position lives in; it is
            prepended to the parsed relative path. Defaults to ``()``.
        :type base: Tuple[str, ...]
        :return: The parsed, not yet validated, position.
        :rtype: _Position
        :raises ValueError: On any syntax error.
        """
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
    """
    Read a JSON-compatible tree into an owned, immutable :class:`_Position`.

    Nothing is validated against a model here. The ``regions`` list may omit
    pending regions (they are re-added on validation); a ``None`` configuration
    means Done.

    :param data: ``{'state': 'A.B', 'regions': [{'name': ..., 'configuration':
        ...}]}``; the outermost node may also carry ``'mode'``.
    :type data: dict
    :param outer: Whether ``data`` is the outermost node, the only one allowed
        to carry ``'mode'``. Defaults to ``False``.
    :type outer: bool
    :return: The equivalent position tree; the input is not retained.
    :rtype: _Position
    :raises TypeError: If a node is not a dict, ``state`` or a region name is
        not a string, or ``regions`` is not a list.
    :raises ValueError: If ``state`` is missing, a node has unknown keys or a
        region entry lacks ``name`` or ``configuration``.
    """
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
    """
    Convert a position tree to freshly allocated JSON-compatible containers.

    Pending regions are omitted from the output; Done regions are written as
    ``'configuration': None``.

    :param position: Position to convert.
    :type position: _Position
    :return: ``{'state': ..., 'regions': [...]}`` with no shared references.
    :rtype: dict
    """
    return {'state': '.'.join(position.path), 'regions': [
        {'name': name, 'configuration': None if child is None else _to_dict(child)}
        for name, child in position.regions if child is not _RegionInit.PENDING
    ]}


def _positions(position):
    """
    Walk the live positions of a tree, parents before children.

    Done and pending regions have no position and are skipped, so only branches
    that currently hold a state are yielded, in region declaration order.

    :param position: Root of the tree to walk.
    :type position: _Position
    :return: Every live node, starting with ``position`` itself.
    :rtype: Iterator[_Position]
    """
    yield position
    for _, child in position.regions:
        if isinstance(child, _Position):
            yield from _positions(child)


def _text(position, prefix=0):
    """
    Render a position tree as configuration text.

    The root is written as a full dotted path; nested positions drop the path
    prefix they share with their region, so the text round-trips through
    :class:`_TextParser`.

    :param position: Position to render.
    :type position: _Position
    :param prefix: Number of leading path segments already implied by the
        enclosing region. Defaults to ``0``.
    :type prefix: int
    :return: For example ``'Root.Run{Motion: Stop, Guard: [done]}'``.
    :rtype: str
    """
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
    """
    Validate one branch against the model and normalize its region order.

    Checks that every path names a state (never a region), that no parallel
    owner is skipped by a linear path, that region names are known and unique,
    and the per-mode rules (stable: non-pseudo leaf, all regions live or Done,
    not all Done; initialization and transient: looser). Regions missing from
    the input are filled in as pending and all regions are returned in model
    declaration order, which is what makes equal positions compare equal.

    :param model: State machine to validate against.
    :type model: pyfcstm.model.model.StateMachine
    :param position: Branch to validate.
    :type position: _Position
    :param base: Namespace path the branch must lie inside; ``()`` for the
        outermost branch.
    :type base: Tuple[str, ...]
    :param mode: ``'stable'``, ``'initialization'`` or ``'transient'``.
    :type mode: str
    :return: A normalized copy of ``position``.
    :rtype: _Position
    :raises ValueError: On any violated rule above.
    """
    path = position.path
    if path[:len(base)] != base or len(path) <= len(base):
        raise ValueError('Configuration path %s is outside namespace %s.' %
                         (_ERROR_REPR.repr(path), _ERROR_REPR.repr(base)))
    state = _lookup(model, path)
    if isinstance(state, Region):
        raise ValueError('A configuration branch must end at a State, not a Region.')
    # A linear path cannot skip a parallel owner and select just one region.
    for end in range(len(base) + 1, len(path)):
        ancestor = _lookup(model, path[:end])
        if getattr(ancestor, 'regions', {}):
            raise ValueError('Parallel owner %s requires a region block.' %
                             _ERROR_REPR.repr('.'.join(ancestor.path)))
    context = '.'.join(path)
    entries = dict(position.regions)
    if len(entries) != len(position.regions):
        raise ValueError('Duplicate region in configuration for %s.' % _ERROR_REPR.repr(context))
    if set(entries) - set(state.regions):
        raise ValueError('Unknown region in configuration for %s.' % _ERROR_REPR.repr(context))
    if mode == 'stable':
        if state.is_pseudo or state.substates:
            raise ValueError('Stable configuration must reach a non-pseudo leaf at %s.' % _ERROR_REPR.repr(context))
        if state.regions and set(entries) != set(state.regions):
            raise ValueError('Missing region in stable configuration for %s.' % _ERROR_REPR.repr(context))
        if any(child is _RegionInit.PENDING for child in entries.values()):
            raise ValueError('Stable configuration cannot contain pending regions at %s.' % _ERROR_REPR.repr(context))
        if state.regions and all(child is None for child in entries.values()):
            raise ValueError('All regions are Done at %s.' % _ERROR_REPR.repr(context))
    ordered = []
    for name in state.regions:
        child = entries.get(name, _RegionInit.PENDING)
        if isinstance(child, _Position):
            child = _validate(model, child, (*path, name), mode)
        ordered.append((name, child))
    return _Position(path, tuple(ordered))


@dataclass(frozen=True)
class Configuration:
    """
    An immutable, model-bound tree of active state positions.

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

    :param mode: Validation mode, ``'stable'``, ``'initialization'`` or
        ``'transient'``, defaults to ``'stable'``. The other two fields of the
        dataclass (the bound model and the validated position tree) are
        supplied by :meth:`parse` and :meth:`from_dict`; do not pass them
        directly.
    :type mode: str, optional

    :ivar mode: The validation mode this configuration was built with.
    :vartype mode: str
    :raises ValueError: If ``mode`` is unknown or the position violates the
        rules of that mode (see :meth:`parse`).

    Example::

        >>> from pyfcstm.model import Configuration, load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     [*] -> Run;
        ...     state Run {
        ...         region Motion { [*] -> Stop; state Stop; state Move; Stop -> Move :: Go; }
        ...         region Guard { [*] -> Watch; state Watch; }
        ...     }
        ...     state Off;
        ...     Run -> Off :: Halt;
        ... }
        ... ''')
        >>> config = Configuration.parse(model, 'Root.Run{Motion: Stop, Guard: Watch}')
        >>> config
        Configuration(mode='stable', position='Root.Run{Motion: Stop, Guard: Watch}')
        >>> config == Configuration.from_dict(model, config.to_dict())
        True
        >>> Configuration.parse(model, 'Root.Off').to_dict()
        {'mode': 'stable', 'state': 'Root.Off', 'regions': []}
        >>> Configuration.parse(model, 'Root.Run{Motion: [done], Guard: [done]}')
        Traceback (most recent call last):
        ...
        ValueError: All regions are Done at 'Root.Run'.
    """

    _model: 'StateMachine' = field(repr=False, compare=False)
    _position: _Position = field(repr=False)
    mode: str = 'stable'

    def __post_init__(self):
        """
        Validate the position against the model and store its normalized form.

        Runs for every construction path. The normalized tree lists the regions
        of each parallel owner in model declaration order and fills omitted
        regions in as pending, so two configurations describing the same
        position are equal however they were written.

        :return: ``None``.
        :rtype: None
        :raises ValueError: If ``mode`` is not one of the three known modes, if
            the position violates the rules of the mode, or if
            ``initialization`` mode is not exactly one composite or parallel
            owner whose regions are all pending.

        Example::

            >>> from pyfcstm.model import Configuration, load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root { state Idle; [*] -> Idle; }')
            >>> Configuration.parse(model, 'Root.Idle', mode='paused')
            Traceback (most recent call last):
            ...
            ValueError: Unknown configuration mode: 'paused'.
        """
        if self.mode not in ('stable', 'initialization', 'transient'):
            raise ValueError('Unknown configuration mode: %s.' % _ERROR_REPR.repr(self.mode))
        position = _validate(self._model, self._position, (), self.mode)
        if self.mode == 'initialization':
            state = _lookup(self._model, position.path)
            if state.is_leaf_state or any(child is not _RegionInit.PENDING for _, child in position.regions):
                raise ValueError('Initialization requires one whole owner path.')
        object.__setattr__(self, '_position', position)

    @classmethod
    def parse(cls, model, text: str, *, mode: str = 'stable'):
        """
        Parse configuration text and validate it against ``model``.

        The text is one dotted full path from the root state. When that state
        owns regions, a ``{...}`` block follows with one ``name: position``
        entry per region, separated by commas; a region value is a path
        relative to the region, ``[init]`` or ``[done]``. Whitespace, including
        newlines, is allowed between tokens.

        :param model: State machine owning all referenced paths.
        :type model: pyfcstm.model.model.StateMachine
        :param text: Full state path with optional recursive region blocks.
            Region values are relative state paths, ``[init]`` or ``[done]``.
            Whitespace, including newlines, is allowed between tokens.
        :type text: str
        :param mode: ``stable``, ``initialization`` or ``transient``, defaults
            to ``'stable'``.
        :type mode: str, optional
        :return: A new immutable configuration.
        :rtype: Configuration
        :raises TypeError: If text is not a string.
        :raises ValueError: On malformed text or invalid position. Syntax errors
            include one-based line and character column numbers; tabs count as
            one character and lines are separated by newline characters. Excessive
            nesting also raises ValueError instead of exposing RecursionError.
            Long token and path excerpts are shortened in error messages.

        Example::

            >>> from pyfcstm.model import Configuration, load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... state Root {
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion { [*] -> Stop; state Stop; state Move; Stop -> Move :: Go; }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ...     state Off;
            ...     Run -> Off :: Halt;
            ... }
            ... ''')
            >>> str(Configuration.parse(model, 'Root.Run{Motion: Move, Guard: Watch}'))
            'Root.Run{Motion: Move, Guard: Watch}'
            >>> str(Configuration.parse(model, 'Root.Run{Motion: [done], Guard: Watch}'))
            'Root.Run{Motion: [done], Guard: Watch}'

        ``initialization`` mode describes an owner whose regions have not run
        their initial transitions yet, and ``transient`` mode allows partially
        initialized regions::

            >>> str(Configuration.parse(model, 'Root.Run', mode='initialization'))
            'Root.Run{Motion: [init], Guard: [init]}'
            >>> str(Configuration.parse(model, 'Root.Run{Motion: Stop, Guard: [init]}', mode='transient'))
            'Root.Run{Motion: Stop, Guard: [init]}'

        Malformed text and impossible positions raise :class:`ValueError`::

            >>> Configuration.parse(model, 'Root.Run{Motion Stop}')
            Traceback (most recent call last):
            ...
            ValueError: Expected ':' at line 1, column 17, got 'Stop'.
            >>> Configuration.parse(model, 'Root.Run{Motion: Stop}')
            Traceback (most recent call last):
            ...
            ValueError: Missing region in stable configuration for 'Root.Run'.
            >>> Configuration.parse(model, 'Root.Run.Motion.Stop')
            Traceback (most recent call last):
            ...
            ValueError: Parallel owner 'Root.Run' requires a region block.
            >>> Configuration.parse(model, 42)
            Traceback (most recent call last):
            ...
            TypeError: Configuration text must be a string.
        """
        parser = _TextParser(text)
        try:
            position = parser.position()
            if parser.peek():
                parser.error('end of input')
            return cls(model, position, mode)
        except RecursionError:
            # RecursionError: position() parses nested blocks and cls() validates
            # the resulting recursive position tree within Python's stack limit.
            raise ValueError('Configuration nesting is too deep near %s; '
                             'reduce nested region blocks.' % parser.location()) from None

    @classmethod
    def from_dict(cls, model, data):
        """
        Read the recursive dictionary produced by :meth:`to_dict`.

        Regions omitted from the ``regions`` list are treated as pending and
        a region whose ``configuration`` is ``None`` is Done, so the output of
        :meth:`to_dict` always reads back to an equal configuration.

        :param model: State machine used for validation.
        :type model: pyfcstm.model.model.StateMachine
        :param data: JSON-compatible tree; omitted mode defaults to stable.
            Each node is ``{'state': <full path>, 'regions': [{'name': <region>,
            'configuration': <node or None>}, ...]}`` and only the outermost
            node may add ``'mode'``.
        :type data: dict
        :return: A new immutable configuration owning its position data.
        :rtype: Configuration
        :raises TypeError: If a node is not a dict, a ``state`` or region
            ``name`` is not a string, or ``regions`` is not a list.
        :raises ValueError: If a node lacks ``state``, has unknown keys, a
            region entry lacks ``name`` or ``configuration``, or the position
            is invalid for its mode.

        Example::

            >>> from pyfcstm.model import Configuration, load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... state Root {
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion { [*] -> Stop; state Stop; }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> data = {'state': 'Root.Run', 'regions': [
            ...     {'name': 'Motion', 'configuration': {'state': 'Root.Run.Motion.Stop'}},
            ...     {'name': 'Guard', 'configuration': None},
            ... ]}
            >>> str(Configuration.from_dict(model, data))
            'Root.Run{Motion: Stop, Guard: [done]}'
            >>> Configuration.from_dict(model, {'regions': []})
            Traceback (most recent call last):
            ...
            ValueError: A configuration node requires state and accepts only ['mode', 'regions', 'state'].
            >>> Configuration.from_dict(model, [])
            Traceback (most recent call last):
            ...
            TypeError: A configuration node must be a dictionary.
        """
        position = _from_dict(data, outer=True)
        return cls(model, position, data.get('mode', 'stable'))

    def to_dict(self):
        """
        Return a fresh JSON tree with mode, state and ordered regions.

        Pending regions are omitted and Done regions are written as
        ``'configuration': None``. Every call allocates new containers, so
        callers may mutate the result freely.

        :return: ``{'mode': ..., 'state': <full path>, 'regions': [...]}``;
            each region entry is ``{'name': ..., 'configuration': <node or
            None>}`` with the same ``state``/``regions`` shape, without
            ``mode``.
        :rtype: dict

        Example::

            >>> from pyfcstm.model import Configuration, load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... state Root {
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion { [*] -> Stop; state Stop; }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> config = Configuration.parse(model, 'Root.Run{Motion: Stop, Guard: [done]}')
            >>> config.to_dict()
            {'mode': 'stable', 'state': 'Root.Run', 'regions': [{'name': 'Motion', 'configuration': {'state': 'Root.Run.Motion.Stop', 'regions': []}}, {'name': 'Guard', 'configuration': None}]}
        """
        return dict(mode=self.mode, **_to_dict(self._position))

    def __str__(self):
        """
        Render the position as text that :meth:`parse` reads back.

        The text omits the mode, so pass ``mode=config.mode`` to
        :meth:`parse` to round-trip a non-stable configuration. Every region
        of an active parallel owner is listed in declaration order, using
        ``[init]`` for pending and ``[done]`` for completed regions.

        :return: Dotted root path, plus ``{region: position, ...}`` blocks.
        :rtype: str

        Example::

            >>> from pyfcstm.model import Configuration, load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... state Root {
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion { [*] -> Stop; state Stop; }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> config = Configuration.parse(model, 'Root.Run{Guard: Watch, Motion: [done]}')
            >>> str(config)
            'Root.Run{Motion: [done], Guard: Watch}'
        """
        return _text(self._position)

    def __repr__(self):
        """
        Return a debugging form that shows the mode and the position text.

        The result is not constructor syntax; use :meth:`parse` to rebuild a
        configuration from ``str(config)``.

        :return: ``Configuration(mode='...', position='...')``.
        :rtype: str

        Example::

            >>> from pyfcstm.model import Configuration, load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root { state Idle; [*] -> Idle; }')
            >>> Configuration.parse(model, 'Root')
            Traceback (most recent call last):
            ...
            ValueError: Stable configuration must reach a non-pseudo leaf at 'Root'.
            >>> Configuration.parse(model, 'Root.Idle')
            Configuration(mode='stable', position='Root.Idle')
        """
        return 'Configuration(mode=%r, position=%r)' % (self.mode, str(self))

    @property
    def leaves(self) -> Tuple['State', ...]:
        """
        Active leaf States in declaration order, excluding Done regions.

        Transient snapshots may include pseudo leaves. Pending composite owners
        contribute no leaf until their children have initialized. For an
        ordinary model the result has exactly one State; for a model with
        parallel regions it has one per live region branch.

        :return: Leaf :class:`~pyfcstm.model.model.State` objects of the bound
            model, in region declaration order.
        :rtype: Tuple[pyfcstm.model.model.State, ...]

        Example::

            >>> from pyfcstm.model import Configuration, load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... state Root {
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion { [*] -> Stop; state Stop; }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> config = Configuration.parse(model, 'Root.Run{Motion: Stop, Guard: Watch}')
            >>> [state.path for state in config.leaves]
            [('Root', 'Run', 'Motion', 'Stop'), ('Root', 'Run', 'Guard', 'Watch')]
            >>> done = Configuration.parse(model, 'Root.Run{Motion: [done], Guard: Watch}')
            >>> [state.name for state in done.leaves]
            ['Watch']
        """
        states = (_lookup(self._model, node.path) for node in _positions(self._position))
        return tuple(state for state in states if state.is_leaf_state)

    def is_active(self, path) -> bool:
        """
        Whether the State at a full string/tuple path is active.

        A state is active when it lies on a live branch, so every ancestor of
        an active leaf is active too. A state inside a Done or pending region
        is not active.

        :param path: Full path from the root state, as a dotted string or a
            tuple of names.
        :type path: Union[str, Tuple[str, ...]]
        :return: ``True`` if the state is on a live branch of this
            configuration.
        :rtype: bool
        :raises ValueError: If the path is unknown or names a Region.

        Example::

            >>> from pyfcstm.model import Configuration, load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... state Root {
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion { [*] -> Stop; state Stop; state Move; Stop -> Move :: Go; }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ... }
            ... ''')
            >>> config = Configuration.parse(model, 'Root.Run{Motion: Stop, Guard: Watch}')
            >>> config.is_active('Root.Run'), config.is_active(('Root', 'Run', 'Motion', 'Stop'))
            (True, True)
            >>> config.is_active('Root.Run.Motion.Move')
            False
            >>> config.is_active('Root.Run.Motion')
            Traceback (most recent call last):
            ...
            ValueError: is_active requires a State path.
        """
        state = _lookup(self._model, path)
        if isinstance(state, Region):
            raise ValueError('is_active requires a State path.')
        return any(node.path[:len(state.path)] == state.path for node in _positions(self._position))

    def region_status(self, path) -> str:
        """
        Return ``live``, ``done``, ``pending`` or ``inactive`` for a Region.

        Pending means the active owner has not initialized that region yet.
        Inactive means the owner is outside this configuration.

        :param path: Full path of a region (owner path plus region name), as a
            dotted string or a tuple of names.
        :type path: Union[str, Tuple[str, ...]]
        :return: ``'live'`` (holds an active state), ``'done'`` (completed),
            ``'pending'`` (owner active, region not initialized) or
            ``'inactive'`` (owner not active).
        :rtype: str
        :raises ValueError: If the path is unknown or names a State.

        Example::

            >>> from pyfcstm.model import Configuration, load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... state Root {
            ...     [*] -> Run;
            ...     state Run {
            ...         region Motion { [*] -> Stop; state Stop; }
            ...         region Guard { [*] -> Watch; state Watch; }
            ...     }
            ...     state Off;
            ...     Run -> Off :: Halt;
            ... }
            ... ''')
            >>> config = Configuration.parse(model, 'Root.Run{Motion: [done], Guard: Watch}')
            >>> config.region_status('Root.Run.Motion'), config.region_status('Root.Run.Guard')
            ('done', 'live')
            >>> Configuration.parse(model, 'Root.Run', mode='initialization').region_status('Root.Run.Guard')
            'pending'
            >>> Configuration.parse(model, 'Root.Off').region_status('Root.Run.Guard')
            'inactive'
            >>> config.region_status('Root.Run')
            Traceback (most recent call last):
            ...
            ValueError: region_status requires a Region path.
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
