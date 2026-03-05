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
from typing import Optional, Tuple, TYPE_CHECKING

try:
    from typing import Literal
except ImportError:
    from typing_extensions import Literal

if TYPE_CHECKING:
    from .model import State, Event

__all__ = [
    'DetailLevelLiteral',
    'PlantUMLOptions',
    'format_state_name',
    'format_event_name',
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


def format_event_name(event: 'Event', name_format: Tuple[Literal['name', 'extra_name', 'path'], ...]) -> str:
    """
    Format event name according to the specified format tuple.

    :param event: Event object to format
    :type event: Event
    :param name_format: Tuple of display elements
    :type name_format: Tuple[Literal['name', 'extra_name', 'path'], ...]
    :return: Formatted event name
    :rtype: str

    Example::

        >>> format_event_name(event, ('extra_name', 'name'))
        '启动模块 (Start)'
    """
    parts = []
    for element in name_format:
        if element == 'name':
            parts.append(event.path[-1])
        elif element == 'extra_name':
            if event.extra_name:
                parts.append(event.extra_name)
        elif element == 'path':
            full_path = '.'.join(event.path)
            parts.append(full_path)

    # Fallback to name if all elements were skipped
    if not parts:
        return event.path[-1]

    # First part is main display, rest in parentheses
    result = parts[0]
    if len(parts) > 1:
        result += f" ({' / '.join(parts[1:])})"

    return result


DetailLevelLiteral = Literal['minimal', 'normal', 'full']


@dataclass
class PlantUMLOptions:
    """
    Configuration options for PlantUML diagram generation.

    This class provides fine-grained control over what elements are displayed
    in generated PlantUML diagrams. It supports two usage modes:

    1. Quick mode: Use detail_level presets
    2. Fine-grained mode: Configure individual options

    Configuration inheritance:

    * show_enter_actions/show_during_actions/show_exit_actions/show_aspect_actions
      inherit from show_lifecycle_actions
    * show_abstract_actions/show_concrete_actions inherit from show_lifecycle_actions
    * show_transition_guards/show_transition_effects are independently configurable

    :param detail_level: Preset detail level (``'minimal'``, ``'normal'``, or ``'full'``)
    :type detail_level: DetailLevelLiteral
    :param show_variable_definitions: Whether to show variable definitions
    :type show_variable_definitions: Optional[bool]
    :param variable_display_mode: How to display variables ('note', 'legend', or 'hide')
    :type variable_display_mode: Literal['note', 'legend', 'hide']
    :param state_name_format: Tuple of display elements for state names
    :type state_name_format: Tuple[Literal['name', 'extra_name', 'path'], ...]
    :param show_pseudo_state_style: Whether to show pseudo state styling
    :type show_pseudo_state_style: Optional[bool]
    :param collapse_empty_states: Whether to collapse states with no actions
    :type collapse_empty_states: bool
    :param show_lifecycle_actions: Master switch for lifecycle actions
    :type show_lifecycle_actions: Optional[bool]
    :param show_enter_actions: Whether to show enter actions
    :type show_enter_actions: Optional[bool]
    :param show_during_actions: Whether to show during actions
    :type show_during_actions: Optional[bool]
    :param show_exit_actions: Whether to show exit actions
    :type show_exit_actions: Optional[bool]
    :param show_aspect_actions: Whether to show aspect actions
    :type show_aspect_actions: Optional[bool]
    :param show_abstract_actions: Whether to show abstract actions
    :type show_abstract_actions: Optional[bool]
    :param show_concrete_actions: Whether to show concrete actions
    :type show_concrete_actions: Optional[bool]
    :param abstract_action_marker: How to mark abstract actions
    :type abstract_action_marker: Literal['text', 'symbol', 'none']
    :param max_action_lines: Maximum lines per action (None for unlimited)
    :type max_action_lines: Optional[int]
    :param show_transition_guards: Whether to show transition guards
    :type show_transition_guards: Optional[bool]
    :param show_transition_effects: Whether to show transition effects
    :type show_transition_effects: Optional[bool]
    :param transition_effect_mode: How to display effects
    :type transition_effect_mode: Literal['note', 'inline', 'hide']
    :param show_events: Whether to show event names
    :type show_events: Optional[bool]
    :param event_name_format: Tuple of display elements for event names
    :type event_name_format: Tuple[Literal['name', 'extra_name', 'path'], ...]
    :param event_visualization_mode: Event visualization mode
    :type event_visualization_mode: Literal['none', 'color', 'legend', 'both', 'dependency_view']
    :param max_depth: Maximum depth to expand (None for unlimited)
    :type max_depth: Optional[int]
    :param collapsed_state_marker: Marker for collapsed states
    :type collapsed_state_marker: str
    :param use_skinparam: Whether to use skinparam styling
    :type use_skinparam: bool
    :param use_stereotypes: Whether to use stereotypes
    :type use_stereotypes: bool
    :param custom_colors: Custom color mapping for events
    :type custom_colors: Optional[dict]

    Example::

        >>> options = PlantUMLOptions(
        ...     detail_level='normal',
        ...     show_lifecycle_actions=True,
        ... )
        >>> config = options.to_config()
        >>> config.show_enter_actions  # True (inherited)
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
    event_name_format: Tuple[Literal['name', 'extra_name', 'path'], ...] = ('extra_name',)
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
