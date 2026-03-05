"""
PlantUML generation configuration and options.

This module provides configuration classes for controlling PlantUML diagram generation
from state machine models. The main class :class:`PlantUMLOptions` allows fine-grained
control over what elements are displayed in the generated diagrams.

The configuration system uses a hierarchical fallback mechanism:

1. User-specified values (non-None)
2. Parent configuration values (e.g., show_lifecycle_actions)
3. detail_level preset values
4. Final fallback defaults

The main public components are:

* :data:`DetailLevelLiteral` - Literal type for preset detail levels
* :class:`PlantUMLOptions` - Configuration class for PlantUML generation
* :func:`format_state_name` - Format state names according to configuration
* :func:`format_event_name` - Format event names according to configuration

Example::

    >>> from pyfcstm.model.plantuml import PlantUMLOptions
    >>> options = PlantUMLOptions(
    ...     detail_level='normal',
    ...     show_lifecycle_actions=True,
    ... )
    >>> config = options.to_config()
    >>> config.show_enter_actions  # True (inherited from show_lifecycle_actions)

"""

from dataclasses import dataclass
from typing import Optional, Tuple, TYPE_CHECKING, Union, Dict, List

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

if TYPE_CHECKING:
    from .model import State, Event, OnStage, OnAspect, StateMachine, Transition

__all__ = [
    'DetailLevelLiteral',
    'PlantUMLOptionsInput',
    'PlantUMLOptions',
    'format_state_name',
    'format_event_name',
    'should_show_action',
    'format_action_text',
    'collect_event_transitions',
    'assign_event_colors',
]


def format_state_name(state: 'State', name_format: Tuple[Literal['name', 'extra_name', 'path'], ...]) -> str:
    """
    Format state name according to the specified format tuple.

    :param state: State object to format
    :type state: State
    :param name_format: Tuple of display elements
    :type name_format: Tuple[Literal['name', 'extra_name', 'path'], ...]
    :return: Formatted state name
    :rtype: str

    Example::

        >>> format_state_name(state, ('extra_name', 'name'))
        '系统运行中 (Running)'
    """
    parts = []
    for element in name_format:
        if element == 'name':
            parts.append(state.name)
        elif element == 'extra_name':
            if state.extra_name:
                parts.append(state.extra_name)
        elif element == 'path':
            parts.append('.'.join(state.path))

    # Fallback to name if all elements were skipped
    if not parts:
        return state.name

    # First part is main display, rest in parentheses
    result = parts[0]
    if len(parts) > 1:
        result += f" ({' / '.join(parts[1:])})"

    return result


def format_event_name(
        event: 'Event',
        name_format: Tuple[Literal['name', 'extra_name', 'path', 'relpath'], ...],
        trans_node: Optional[object] = None
) -> str:
    """
    Format event name according to the specified format tuple.

    :param event: Event object to format
    :type event: Event
    :param name_format: Tuple of display elements
    :type name_format: Tuple[Literal['name', 'extra_name', 'path', 'relpath'], ...]
    :param trans_node: Optional transition AST node for relpath computation
    :type trans_node: Optional[object]
    :return: Formatted event name
    :rtype: str

    Example::

        >>> format_event_name(event, ('extra_name', 'name'))
        '启动模块 (Start)'
        >>> format_event_name(event, ('extra_name', 'relpath'), trans_node)
        '启动模块 (State.Start)'
    """
    parts = []
    for element in name_format:
        if element == 'name':
            parts.append(event.path[-1])
        elif element == 'extra_name':
            if event.extra_name:
                parts.append(event.extra_name)
        elif element == 'path':
            # Absolute path format: /Root.State.Event (skip first element, prepend /)
            if len(event.path) > 1:
                abs_path = '/' + '.'.join(event.path[1:])
            else:
                abs_path = '/' + event.path[0]
            parts.append(abs_path)
        elif element == 'relpath':
            # Relative path: use trans_node.event_id if available, otherwise fallback to path
            if trans_node is not None and hasattr(trans_node, 'event_id') and trans_node.event_id is not None:
                rel_path = str(trans_node.event_id)
            else:
                # Fallback to path format
                rel_path = "/" + ('.'.join(event.path[1:]) if len(event.path) > 1 else event.path[0])
            parts.append(rel_path)

    # Fallback to name if all elements were skipped
    if not parts:
        return event.path[-1]

    # First part is main display, rest in parentheses
    result = parts[0]
    if len(parts) > 1:
        result += f" ({' / '.join(parts[1:])})"

    return result


def should_show_action(action: 'Union[OnStage, OnAspect]', config: 'PlantUMLOptions') -> bool:
    """
    Determine if an action should be shown based on abstract/concrete filtering.

    :param action: Action object (OnStage or OnAspect) to check
    :type action: Union[OnStage, OnAspect]
    :param config: PlantUML configuration options
    :type config: PlantUMLOptions
    :return: True if the action should be shown, False otherwise
    :rtype: bool

    Example::

        >>> # For an abstract action
        >>> should_show_action(action, config)
        True
    """
    # Check if action is abstract or concrete
    is_abstract = action.is_abstract

    # Apply filtering based on config
    if is_abstract:
        return config.show_abstract_actions
    else:
        return config.show_concrete_actions


def format_action_text(action: 'Union[OnStage, OnAspect]', config: 'PlantUMLOptions') -> str:
    """
    Format action text with abstract marker and line limit.

    :param action: Action object (OnStage or OnAspect) to format
    :type action: Union[OnStage, OnAspect]
    :param config: PlantUML configuration options
    :type config: PlantUMLOptions
    :return: Formatted action text
    :rtype: str

    Example::

        >>> format_action_text(action, config)
        'enter abstract InitHardware'
    """
    # Convert action to AST node and get text representation
    ast_node = action.to_ast_node()
    action_text = str(ast_node)

    # Apply abstract marker if needed
    if action.is_abstract:
        if config.abstract_action_marker == 'symbol':
            # Replace 'abstract' keyword with symbol marker
            action_text = action_text.replace('abstract ', '«abstract» ', 1)
        elif config.abstract_action_marker == 'none':
            # Remove 'abstract' keyword entirely
            action_text = action_text.replace('abstract ', '', 1)
        # 'text' mode keeps the default 'abstract' keyword, no change needed

    # Apply line limit if configured
    if config.max_action_lines is not None and config.max_action_lines > 0:
        lines = action_text.split('\n')
        if len(lines) > config.max_action_lines:
            # Truncate and add ellipsis
            lines = lines[:config.max_action_lines]
            lines.append('...')
            action_text = '\n'.join(lines)

    return action_text


DetailLevelLiteral = Literal['minimal', 'normal', 'full']
PlantUMLOptionsInput = Union['PlantUMLOptions', DetailLevelLiteral, None]


@dataclass
class PlantUMLOptions:
    """
    Configuration options for PlantUML diagram generation.

    This class provides fine-grained control over what elements are displayed
    in generated PlantUML diagrams. It supports two usage modes:

    1. **Quick mode**: Use ``detail_level`` presets (``'minimal'``, ``'normal'``, ``'full'``)
    2. **Fine-grained mode**: Configure individual options explicitly

    Configuration Inheritance
    --------------------------

    The configuration system uses a hierarchical fallback mechanism:

    1. User-specified values (non-None parameters)
    2. Parent configuration values (e.g., ``show_lifecycle_actions`` controls child options)
    3. ``detail_level`` preset values
    4. Final fallback defaults

    Inheritance relationships:

    * ``show_enter_actions``, ``show_during_actions``, ``show_exit_actions``, ``show_aspect_actions``
      inherit from ``show_lifecycle_actions``
    * ``show_abstract_actions``, ``show_concrete_actions`` inherit from ``show_lifecycle_actions``
    * ``show_transition_guards``, ``show_transition_effects`` are independently configurable

    Detail Level Presets
    ---------------------

    **minimal**: Clean diagrams focusing on structure

    * Hides: variable definitions, lifecycle actions, pseudo state styling
    * Shows: transition guards, transition effects, events

    **normal** (default): Balanced view for typical use cases

    * Hides: variable definitions, lifecycle actions
    * Shows: transition guards, transition effects, events, pseudo state styling

    **full**: Complete information for detailed analysis

    * Shows: everything including variable definitions and lifecycle actions

    Parameters
    ----------

    detail_level : DetailLevelLiteral, default='normal'
        Preset detail level. One of ``'minimal'``, ``'normal'``, or ``'full'``.

        Example::

            >>> PlantUMLOptions(detail_level='minimal')  # Clean structure view
            >>> PlantUMLOptions(detail_level='full')     # Show all details

    show_variable_definitions : Optional[bool], default=None
        Whether to display variable definitions in the diagram.

        * ``True``: Show variable definitions as note or legend
        * ``False``: Hide variable definitions
        * ``None``: Use ``detail_level`` preset (False for minimal/normal, True for full)

        Example::

            >>> # Show variables in a note block
            >>> PlantUMLOptions(show_variable_definitions=True, variable_display_mode='note')
            >>> # Output: note as DefinitionNote
            >>> #         defines {
            >>> #             def int counter = 0;
            >>> #         }
            >>> #         end note

    variable_display_mode : Literal['note', 'legend', 'hide'], default='note'
        How to display variable definitions when ``show_variable_definitions=True``.

        * ``'note'``: Display as a floating note block
        * ``'legend'``: Display as a legend table (more compact)
        * ``'hide'``: Don't display (same as ``show_variable_definitions=False``)

        Example::

            >>> # Legend format (compact table)
            >>> PlantUMLOptions(show_variable_definitions=True, variable_display_mode='legend')
            >>> # Output: legend right
            >>> #         |= Variable |= Type |= Initial Value |
            >>> #         | counter | int | 0 |
            >>> #         endlegend

    state_name_format : Tuple[Literal['name', 'extra_name', 'path'], ...], default=('extra_name',)
        Tuple of display elements for state names. Elements are combined with the first
        as the main display and others in parentheses.

        * ``'name'``: State identifier (e.g., ``'Running'``)
        * ``'extra_name'``: Localized/display name (e.g., ``'运行中'``)
        * ``'path'``: Full hierarchical path (e.g., ``'System.Module.Running'``)

        Example::

            >>> # Show only extra_name (default)
            >>> PlantUMLOptions(state_name_format=('extra_name',))
            >>> # Output: state "运行中" as running

            >>> # Show extra_name with name in parentheses
            >>> PlantUMLOptions(state_name_format=('extra_name', 'name'))
            >>> # Output: state "运行中 (Running)" as running

            >>> # Show name with full path
            >>> PlantUMLOptions(state_name_format=('name', 'path'))
            >>> # Output: state "Running (System.Module.Running)" as system__module__running

    show_pseudo_state_style : Optional[bool], default=None
        Whether to apply visual styling to pseudo states (dotted border).

        * ``True``: Pseudo states shown with ``#line.dotted`` style
        * ``False``: Pseudo states shown without special styling
        * ``None``: Use ``detail_level`` preset (False for minimal, True for normal/full)

        Example::

            >>> PlantUMLOptions(show_pseudo_state_style=True)
            >>> # Output: state "PseudoState" as pseudo_state <<pseudo>> #line.dotted

    collapse_empty_states : bool, default=False
        Whether to hide action text for states with no lifecycle actions.

        * ``True``: Empty states don't show action text (cleaner diagrams)
        * ``False``: All states show their structure

        Example::

            >>> # With collapse_empty_states=True, empty states are more compact
            >>> PlantUMLOptions(collapse_empty_states=True)
            >>> # State with no actions: state "EmptyState" as empty_state
            >>> # (no "EmptyState :" line)

    show_lifecycle_actions : Optional[bool], default=None
        Master switch for all lifecycle actions (enter/during/exit/aspect).

        * ``True``: Show all lifecycle actions (unless overridden by specific options)
        * ``False``: Hide all lifecycle actions
        * ``None``: Use ``detail_level`` preset (False for minimal/normal, True for full)

        This option controls the default for ``show_enter_actions``, ``show_during_actions``,
        ``show_exit_actions``, ``show_aspect_actions``, ``show_abstract_actions``, and
        ``show_concrete_actions``.

        Example::

            >>> # Show all lifecycle actions
            >>> PlantUMLOptions(show_lifecycle_actions=True)
            >>> # Output: state "Active" as active
            >>> #         active : enter {\\n    counter = 0;\\n}\\nduring {\\n    counter++;\\n}

    show_enter_actions : Optional[bool], default=None
        Whether to show enter actions. Inherits from ``show_lifecycle_actions`` if None.

        Example::

            >>> # Show only enter actions, hide others
            >>> PlantUMLOptions(show_lifecycle_actions=False, show_enter_actions=True)

    show_during_actions : Optional[bool], default=None
        Whether to show during actions. Inherits from ``show_lifecycle_actions`` if None.

    show_exit_actions : Optional[bool], default=None
        Whether to show exit actions. Inherits from ``show_lifecycle_actions`` if None.

    show_aspect_actions : Optional[bool], default=None
        Whether to show aspect actions (``>> during before/after``).
        Inherits from ``show_lifecycle_actions`` if None.

        Example::

            >>> # Show aspect actions for cross-cutting concerns
            >>> PlantUMLOptions(show_lifecycle_actions=True, show_aspect_actions=True)
            >>> # Output: state : >> during before abstract GlobalMonitor;

    show_abstract_actions : Optional[bool], default=None
        Whether to show abstract actions (actions without implementation).
        Inherits from ``show_lifecycle_actions`` if None.

        Example::

            >>> # Show only abstract actions (API surface)
            >>> PlantUMLOptions(show_lifecycle_actions=True,
            ...                 show_abstract_actions=True,
            ...                 show_concrete_actions=False)
            >>> # Output: state : enter abstract InitHardware;

    show_concrete_actions : Optional[bool], default=None
        Whether to show concrete actions (actions with implementation).
        Inherits from ``show_lifecycle_actions`` if None.

        Example::

            >>> # Show only concrete actions (implementation details)
            >>> PlantUMLOptions(show_lifecycle_actions=True,
            ...                 show_abstract_actions=False,
            ...                 show_concrete_actions=True)
            >>> # Output: state : enter {\\n    counter = 0;\\n}

    abstract_action_marker : Literal['text', 'symbol', 'none'], default='text'
        How to mark abstract actions when displayed.

        * ``'text'``: Use ``abstract`` keyword (e.g., ``enter abstract Init``)
        * ``'symbol'``: Use guillemet markers (e.g., ``enter «abstract» Init``)
        * ``'none'``: No marker (e.g., ``enter Init``)

        Example::

            >>> PlantUMLOptions(show_lifecycle_actions=True, abstract_action_marker='symbol')
            >>> # Output: state : enter «abstract» InitHardware;

    max_action_lines : Optional[int], default=None
        Maximum number of lines to display per action. Lines beyond this limit
        are truncated with ``...`` ellipsis.

        * ``None``: No limit (show all lines)
        * ``> 0``: Limit to specified number of lines

        Example::

            >>> # Limit actions to 3 lines for compact diagrams
            >>> PlantUMLOptions(show_lifecycle_actions=True, max_action_lines=3)
            >>> # Output: state : enter {\\n    a = 1;\\n    b = 2;\\n...

    show_transition_guards : Optional[bool], default=None
        Whether to show guard conditions on transitions.

        * ``True``: Show guard conditions (e.g., ``StateA -> StateB : [counter > 10]``)
        * ``False``: Hide guard conditions
        * ``None``: Use ``detail_level`` preset (True for all levels)

        Example::

            >>> PlantUMLOptions(show_transition_guards=True)
            >>> # Output: idle --> active : [temperature > 25]

    show_transition_effects : Optional[bool], default=None
        Whether to show transition effects (operations executed during transition).

        * ``True``: Show effects according to ``transition_effect_mode``
        * ``False``: Hide effects
        * ``None``: Use ``detail_level`` preset (True for all levels)

        Example::

            >>> PlantUMLOptions(show_transition_effects=True, transition_effect_mode='inline')
            >>> # Output: idle --> active : Start / counter = 0

    transition_effect_mode : Literal['note', 'inline', 'hide'], default='note'
        How to display transition effects when ``show_transition_effects=True``.

        * ``'note'``: Display as note on link (detailed, multi-line)
        * ``'inline'``: Display inline with ``/`` separator (compact, single-line)
        * ``'hide'``: Don't display (same as ``show_transition_effects=False``)

        Example::

            >>> # Note format (detailed)
            >>> PlantUMLOptions(show_transition_effects=True, transition_effect_mode='note')
            >>> # Output: idle --> active : Start
            >>> #         note on link
            >>> #         effect {
            >>> #             counter = 0;
            >>> #         }
            >>> #         end note

            >>> # Inline format (compact)
            >>> PlantUMLOptions(show_transition_effects=True, transition_effect_mode='inline')
            >>> # Output: idle --> active : Start / counter = 0

    show_events : Optional[bool], default=None
        Whether to show event names on transitions.

        * ``True``: Show event names
        * ``False``: Hide event names (show only guards/effects)
        * ``None``: Use ``detail_level`` preset (True for all levels)

    event_name_format : Tuple[Literal['name', 'extra_name', 'path', 'relpath'], ...], default=('extra_name', 'relpath')
        Tuple of display elements for event names.

        * ``'name'``: Event identifier (e.g., ``'Start'``)
        * ``'extra_name'``: Localized/display name (e.g., ``'启动'``)
        * ``'path'``: Absolute path (e.g., ``'/System.Start'``)
        * ``'relpath'``: Relative path from transition source (e.g., ``'State.Start'``)

        Example::

            >>> # Show extra_name with relative path
            >>> PlantUMLOptions(event_name_format=('extra_name', 'relpath'))
            >>> # Output: idle --> active : 启动 (State.Start)

            >>> # Show only name
            >>> PlantUMLOptions(event_name_format=('name',))
            >>> # Output: idle --> active : Start

    event_visualization_mode : Literal['none', 'color', 'legend', 'both', 'dependency_view'], default='none'
        How to visualize events in the diagram.

        * ``'none'``: No special visualization
        * ``'color'``: Apply colors to transitions by event (colorblind-friendly palette)
        * ``'legend'``: Show event legend with transition counts
        * ``'both'``: Apply colors and show legend
        * ``'dependency_view'``: Reserved for future use

        Example::

            >>> # Color-code transitions by event
            >>> PlantUMLOptions(event_visualization_mode='color')
            >>> # Output: idle --> active : Start #4E79A7

            >>> # Show event legend
            >>> PlantUMLOptions(event_visualization_mode='legend')
            >>> # Output: legend right
            >>> #         Event Scoping
            >>> #         * Start: 3 transitions
            >>> #         endlegend

    max_depth : Optional[int], default=None
        Maximum depth to expand in state hierarchy. States beyond this depth
        are collapsed and shown with ``collapsed_state_marker``.

        * ``None``: Expand all levels (no limit)
        * ``0``: Show only root state
        * ``> 0``: Expand to specified depth

        Example::

            >>> # Show only 2 levels deep
            >>> PlantUMLOptions(max_depth=2, collapsed_state_marker='[...]')
            >>> # Output: state "Level1" as level1 {
            >>> #             state "Level2" as level1__level2 {
            >>> #                 state "[...]" as level1__level2___collapsed_
            >>> #             }
            >>> #         }

    collapsed_state_marker : str, default='...'
        Text marker to display for collapsed states when ``max_depth`` is exceeded.

        Example::

            >>> PlantUMLOptions(max_depth=1, collapsed_state_marker='[more states...]')
            >>> # Output: state "[more states...]" as parent___collapsed_

    use_skinparam : bool, default=True
        Whether to include skinparam styling block for pseudo and composite states.

        * ``True``: Include skinparam block with predefined colors
        * ``False``: No skinparam block (use PlantUML defaults)

        Example::

            >>> PlantUMLOptions(use_skinparam=True)
            >>> # Output: skinparam state {
            >>> #           BackgroundColor<<pseudo>> LightGray
            >>> #           BackgroundColor<<composite>> LightBlue
            >>> #           BorderColor<<pseudo>> Gray
            >>> #           FontStyle<<pseudo>> italic
            >>> #         }

    use_stereotypes : bool, default=True
        Whether to add stereotype markers (``<<pseudo>>``, ``<<composite>>``) to states.

        * ``True``: Add stereotypes for pseudo and composite states
        * ``False``: No stereotypes

        Example::

            >>> PlantUMLOptions(use_stereotypes=True)
            >>> # Output: state "Parent" as parent <<composite>> {
            >>> #             state "Child" as parent__child
            >>> #         }

    custom_colors : Optional[Dict[str, str]], default=None
        Custom color mapping for events. Keys are event paths (e.g., ``'Root.Start'``),
        values are hex color codes (e.g., ``'#FF0000'``).

        Only used when ``event_visualization_mode`` is ``'color'`` or ``'both'``.

        Example::

            >>> PlantUMLOptions(
            ...     event_visualization_mode='color',
            ...     custom_colors={'Root.Start': '#FF0000', 'Root.Stop': '#00FF00'}
            ... )
            >>> # Output: idle --> active : Start #FF0000
            >>> #         active --> idle : Stop #00FF00

    Examples
    --------

    **Quick mode with presets**::

        >>> # Minimal diagram for presentations
        >>> options = PlantUMLOptions(detail_level='minimal')
        >>> sm.to_plantuml(options)

        >>> # Full details for documentation
        >>> options = PlantUMLOptions(detail_level='full')
        >>> sm.to_plantuml(options)

    **Fine-grained control**::

        >>> # Show only abstract actions (API surface)
        >>> options = PlantUMLOptions(
        ...     show_lifecycle_actions=True,
        ...     show_abstract_actions=True,
        ...     show_concrete_actions=False,
        ...     abstract_action_marker='symbol'
        ... )

        >>> # Compact diagram with depth limit
        >>> options = PlantUMLOptions(
        ...     max_depth=2,
        ...     collapsed_state_marker='[...]',
        ...     collapse_empty_states=True
        ... )

        >>> # Event-focused view with colors
        >>> options = PlantUMLOptions(
        ...     event_visualization_mode='both',
        ...     event_name_format=('extra_name', 'name'),
        ...     custom_colors={'Root.Start': '#00FF00'}
        ... )

    **Combining options**::

        >>> # Custom configuration inheriting from 'normal'
        >>> options = PlantUMLOptions(
        ...     detail_level='normal',
        ...     show_lifecycle_actions=True,  # Override preset
        ...     show_enter_actions=True,      # Show only enter actions
        ...     show_during_actions=False,
        ...     show_exit_actions=False,
        ...     max_action_lines=5            # Limit verbosity
        ... )

    See Also
    --------
    format_state_name : Format state names according to configuration
    format_event_name : Format event names according to configuration
    """

    # Preset level
    detail_level: DetailLevelLiteral = 'normal'

    # Variable definitions
    show_variable_definitions: Optional[bool] = None
    variable_display_mode: Literal['note', 'legend', 'hide'] = 'note'

    # State related
    state_name_format: Tuple[Literal['name', 'extra_name', 'path'], ...] = ('extra_name',)
    show_pseudo_state_style: Optional[bool] = None
    collapse_empty_states: bool = False

    # Lifecycle actions
    show_lifecycle_actions: Optional[bool] = None
    show_enter_actions: Optional[bool] = None
    show_during_actions: Optional[bool] = None
    show_exit_actions: Optional[bool] = None
    show_aspect_actions: Optional[bool] = None

    # Action details
    show_abstract_actions: Optional[bool] = None
    show_concrete_actions: Optional[bool] = None
    abstract_action_marker: Literal['text', 'symbol', 'none'] = 'text'
    max_action_lines: Optional[int] = None

    # Transitions
    show_transition_guards: Optional[bool] = None
    show_transition_effects: Optional[bool] = None
    transition_effect_mode: Literal['note', 'inline', 'hide'] = 'note'

    # Events
    show_events: Optional[bool] = None
    event_name_format: Tuple[Literal['name', 'extra_name', 'path', 'relpath'], ...] = ('extra_name', 'relpath')
    event_visualization_mode: Literal['none', 'color', 'legend', 'both', 'dependency_view'] = 'none'

    # Hierarchy control
    max_depth: Optional[int] = None
    collapsed_state_marker: str = '...'

    # Advanced options
    use_skinparam: bool = True
    use_stereotypes: bool = True
    custom_colors: Optional[dict] = None

    def __post_init__(self):
        """
        Validate configuration after initialization.

        :raises ValueError: If name format tuples are empty
        """
        if not self.state_name_format:
            raise ValueError("state_name_format must contain at least one element")
        if not self.event_name_format:
            raise ValueError("event_name_format must contain at least one element")

    @classmethod
    def from_value(cls, value: PlantUMLOptionsInput) -> 'PlantUMLOptions':
        """
        Normalize user-provided PlantUML option input to a :class:`PlantUMLOptions` instance.

        :param value: Input configuration value. Accepts an existing options object,
            detail-level string, or ``None``.
        :type value: PlantUMLOptionsInput
        :return: Normalized PlantUML options object
        :rtype: PlantUMLOptions
        :raises TypeError: If ``value`` is not supported
        """
        if isinstance(value, cls):
            return value
        if value is None:
            return cls()
        if isinstance(value, str):
            if value in ('minimal', 'normal', 'full'):
                return cls(detail_level=value)
            raise TypeError(
                f"Invalid detail level value {value!r}, expected one of 'minimal', 'normal', 'full'."
            )

        raise TypeError(
            f"Invalid plantuml options type {type(value).__name__}, "
            f"expected PlantUMLOptions, detail level string, or None."
        )

    def to_config(self) -> 'PlantUMLOptions':
        """
        Export resolved configuration with all Optional fields resolved.

        This method resolves all Optional[bool] fields according to the inheritance
        hierarchy and detail_level presets, returning a new PlantUMLOptions instance
        where all fields have definite values (no None).

        Resolution priority (highest to lowest):

        1. User-specified values (non-None)
        2. Parent configuration values (e.g., show_lifecycle_actions)
        3. detail_level preset values
        4. Final fallback defaults

        :return: New PlantUMLOptions with all Optional fields resolved
        :rtype: PlantUMLOptions

        Example::

            >>> options = PlantUMLOptions(
            ...     detail_level='normal',
            ...     show_lifecycle_actions=True,
            ...     show_enter_actions=None,
            ... )
            >>> config = options.to_config()
            >>> config.show_lifecycle_actions  # True
            >>> config.show_enter_actions  # True (inherited)
            >>> config.show_during_actions  # True (inherited)
        """
        detail_defaults = self._get_detail_level_defaults()

        # Resolve show_lifecycle_actions
        resolved_show_lifecycle_actions = (
            self.show_lifecycle_actions if self.show_lifecycle_actions is not None
            else detail_defaults.get('show_lifecycle_actions', False)
        )

        # Resolve lifecycle action sub-fields (inherit from show_lifecycle_actions)
        resolved_show_enter_actions = (
            self.show_enter_actions if self.show_enter_actions is not None
            else resolved_show_lifecycle_actions
        )
        resolved_show_during_actions = (
            self.show_during_actions if self.show_during_actions is not None
            else resolved_show_lifecycle_actions
        )
        resolved_show_exit_actions = (
            self.show_exit_actions if self.show_exit_actions is not None
            else resolved_show_lifecycle_actions
        )
        resolved_show_aspect_actions = (
            self.show_aspect_actions if self.show_aspect_actions is not None
            else resolved_show_lifecycle_actions
        )

        # Resolve abstract/concrete actions (inherit from show_lifecycle_actions)
        resolved_show_abstract_actions = (
            self.show_abstract_actions if self.show_abstract_actions is not None
            else resolved_show_lifecycle_actions
        )
        resolved_show_concrete_actions = (
            self.show_concrete_actions if self.show_concrete_actions is not None
            else resolved_show_lifecycle_actions
        )

        # Resolve transition sub-fields
        resolved_show_transition_guards = (
            self.show_transition_guards if self.show_transition_guards is not None
            else detail_defaults.get('show_transition_guards', True)
        )
        resolved_show_transition_effects = (
            self.show_transition_effects if self.show_transition_effects is not None
            else detail_defaults.get('show_transition_effects', True)
        )

        # Resolve other fields
        resolved_show_events = (
            self.show_events if self.show_events is not None
            else detail_defaults.get('show_events', True)
        )
        resolved_show_variable_definitions = (
            self.show_variable_definitions if self.show_variable_definitions is not None
            else detail_defaults.get('show_variable_definitions', False)
        )
        resolved_show_pseudo_state_style = (
            self.show_pseudo_state_style if self.show_pseudo_state_style is not None
            else detail_defaults.get('show_pseudo_state_style', False)
        )

        return PlantUMLOptions(
            detail_level=self.detail_level,
            show_variable_definitions=resolved_show_variable_definitions,
            variable_display_mode=self.variable_display_mode,
            state_name_format=self.state_name_format,
            show_pseudo_state_style=resolved_show_pseudo_state_style,
            collapse_empty_states=self.collapse_empty_states,
            show_lifecycle_actions=resolved_show_lifecycle_actions,
            show_enter_actions=resolved_show_enter_actions,
            show_during_actions=resolved_show_during_actions,
            show_exit_actions=resolved_show_exit_actions,
            show_aspect_actions=resolved_show_aspect_actions,
            show_abstract_actions=resolved_show_abstract_actions,
            show_concrete_actions=resolved_show_concrete_actions,
            abstract_action_marker=self.abstract_action_marker,
            max_action_lines=self.max_action_lines,
            show_transition_guards=resolved_show_transition_guards,
            show_transition_effects=resolved_show_transition_effects,
            transition_effect_mode=self.transition_effect_mode,
            show_events=resolved_show_events,
            event_name_format=self.event_name_format,
            event_visualization_mode=self.event_visualization_mode,
            max_depth=self.max_depth,
            collapsed_state_marker=self.collapsed_state_marker,
            use_skinparam=self.use_skinparam,
            use_stereotypes=self.use_stereotypes,
            custom_colors=self.custom_colors,
        )

    def _get_detail_level_defaults(self) -> dict:
        """
        Get default values for the current detail_level.

        :return: Dictionary of default values for Optional fields
        :rtype: dict
        """
        if self.detail_level == 'minimal':
            return {
                'show_variable_definitions': False,
                'show_lifecycle_actions': False,
                'show_transition_guards': True,
                'show_transition_effects': True,
                'show_events': True,
                'show_pseudo_state_style': False,
            }
        elif self.detail_level == 'normal':
            return {
                'show_variable_definitions': False,
                'show_lifecycle_actions': False,
                'show_transition_guards': True,
                'show_transition_effects': True,
                'show_events': True,
                'show_pseudo_state_style': True,
            }
        else:  # FULL
            return {
                'show_variable_definitions': True,
                'show_lifecycle_actions': True,
                'show_transition_guards': True,
                'show_transition_effects': True,
                'show_events': True,
                'show_pseudo_state_style': True,
            }


def collect_event_transitions(state_machine: 'StateMachine') -> Dict[str, List[Tuple['State', 'Transition']]]:
    """
    Collect all events and their associated transitions from a state machine.

    :param state_machine: The state machine to analyze
    :type state_machine: StateMachine
    :return: Dictionary mapping event paths to list of (state, transition) tuples
    :rtype: Dict[str, List[Tuple[State, Transition]]]

    Example::

        >>> event_map = collect_event_transitions(sm)
        >>> event_map['System.ErrorEvent']
        [(state1, trans1), (state2, trans2)]
    """
    from collections import defaultdict
    event_map = defaultdict(list)

    for state in state_machine.walk_states():
        for transition in state.transitions:
            if transition.event is not None:
                event_path = '.'.join(transition.event.path)
                event_map[event_path].append((state, transition))

    return dict(event_map)


def assign_event_colors(event_map: Dict[str, List], custom_colors: Optional[dict] = None) -> Dict[str, str]:
    """
    Assign colors to events for visualization.

    Only assigns colors to events that appear 2 or more times. Events that appear
    only once will not be assigned a color (use default transition color).

    :param event_map: Dictionary mapping event paths to transitions
    :type event_map: Dict[str, List]
    :param custom_colors: Optional custom color mapping
    :type custom_colors: Optional[dict]
    :return: Dictionary mapping event paths to color codes
    :rtype: Dict[str, str]

    Example::

        >>> colors = assign_event_colors(event_map)
        >>> colors['System.ErrorEvent']  # Only if ErrorEvent appears >= 2 times
        '#FF6B6B'
    """
    # Default color palette (colorblind-friendly)
    default_palette = [
        '#4E79A7',  # Blue
        '#F28E2B',  # Orange
        '#E15759',  # Red
        '#76B7B2',  # Teal
        '#59A14F',  # Green
        '#EDC948',  # Yellow
        '#B07AA1',  # Purple
        '#FF9DA7',  # Pink
        '#9C755F',  # Brown
        '#BAB0AC',  # Gray
    ]

    event_colors = {}
    color_index = 0

    for event_path in sorted(event_map.keys()):
        # Only assign colors to events that appear 2 or more times
        if len(event_map[event_path]) < 2:
            continue

        # Check custom colors first
        if custom_colors and event_path in custom_colors:
            event_colors[event_path] = custom_colors[event_path]
        else:
            # Assign from default palette (cycle if needed)
            event_colors[event_path] = default_palette[color_index % len(default_palette)]
            color_index += 1

    return event_colors

