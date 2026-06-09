"""
Preview options accepted by :func:`pyfcstm.visualize.render_svg` and
:func:`pyfcstm.visualize.render_png`.

The shape mirrors ``ResolvedFcstmDiagramPreviewOptions`` from jsfcstm —
see ``editors/jsfcstm/src/diagram/options.ts``. Defaults are left to
the JS side: any field set to ``None`` here is omitted before serialising
so jsfcstm's :func:`resolveFcstmDiagramPreviewOptions` fills in the
documented defaults.
"""
import dataclasses
from typing import List, Optional

try:
    # Python 3.8+: Literal is part of typing.
    from typing import Literal
except ImportError:  # pragma: no cover - Python 3.7 fallback
    # On Python 3.7 Literal is only available via ``typing_extensions``,
    # which is not a hard dependency. Degrade gracefully so the module
    # still imports — Literal becomes a runtime no-op that returns ``str``,
    # type checkers can still pick up the annotations from a stub.
    class _LiteralStub:
        def __getitem__(self, _args):
            return str
    Literal = _LiteralStub()  # type: ignore[assignment]

DetailLevel = Literal['minimal', 'normal', 'full']
Direction = Literal['UP', 'DOWN', 'LEFT', 'RIGHT', 'TB', 'BT', 'LR', 'RL']
TransitionEffectMode = Literal['inline', 'note', 'hide']
EventVisualizationMode = Literal['legend', 'color', 'both', 'hide']
EventNameFormatPart = Literal['name', 'extra_name', 'path', 'relpath']

__all__ = [
    'VisualizeOptions',
    'DetailLevel',
    'Direction',
    'TransitionEffectMode',
    'EventVisualizationMode',
    'EventNameFormatPart',
]


@dataclasses.dataclass
class VisualizeOptions:
    """
    User-facing options forwarded to jsfcstm's preview-options resolver.

    Every field is optional: ``None`` means "let jsfcstm pick the
    default for the active ``detail_level``".

    :param detail_level: ``'minimal' | 'normal' | 'full'``; controls the
        defaults for the show-* flags.
    :param direction: ELK layout direction; ``'TB'`` (top-to-bottom)
        is the jsfcstm default.
    :param show_variable_definitions: Whether ``def`` blocks render.
    :param show_events: Whether transition event labels render.
    :param event_name_format: Components glued together to form the
        event label, e.g. ``['extra_name', 'relpath']``.
    :param show_transition_guards: Whether ``[guard]`` markers render.
    :param show_transition_effects: Whether transition ``effect {...}``
        bodies render.
    :param transition_effect_mode: ``'inline' | 'note' | 'hide'``.
    :param event_visualization_mode: ``'legend' | 'color' | 'both' | 'hide'``.
    :param show_state_events: Whether per-state event chips render.
    :param show_state_actions: Whether per-state action chips render.
    :param max_state_events: Cap on per-state event chips.
    :param max_state_actions: Cap on per-state action chips.
    :param max_transition_effect_lines: Cap on inline-effect lines.
    :param max_label_length: Truncate state / transition labels longer
        than this many characters.
    """

    detail_level: Optional[DetailLevel] = None
    direction: Optional[Direction] = None
    show_variable_definitions: Optional[bool] = None
    show_events: Optional[bool] = None
    event_name_format: Optional[List[EventNameFormatPart]] = None
    show_transition_guards: Optional[bool] = None
    show_transition_effects: Optional[bool] = None
    transition_effect_mode: Optional[TransitionEffectMode] = None
    event_visualization_mode: Optional[EventVisualizationMode] = None
    show_state_events: Optional[bool] = None
    show_state_actions: Optional[bool] = None
    max_state_events: Optional[int] = None
    max_state_actions: Optional[int] = None
    max_transition_effect_lines: Optional[int] = None
    max_label_length: Optional[int] = None

    _CAMEL_CASE = {
        'detail_level': 'detailLevel',
        'direction': 'direction',
        'show_variable_definitions': 'showVariableDefinitions',
        'show_events': 'showEvents',
        'event_name_format': 'eventNameFormat',
        'show_transition_guards': 'showTransitionGuards',
        'show_transition_effects': 'showTransitionEffects',
        'transition_effect_mode': 'transitionEffectMode',
        'event_visualization_mode': 'eventVisualizationMode',
        'show_state_events': 'showStateEvents',
        'show_state_actions': 'showStateActions',
        'max_state_events': 'maxStateEvents',
        'max_state_actions': 'maxStateActions',
        'max_transition_effect_lines': 'maxTransitionEffectLines',
        'max_label_length': 'maxLabelLength',
    }

    def to_jsfcstm_dict(self) -> dict:
        """
        Serialise to the camelCase shape jsfcstm expects.

        Fields whose value is ``None`` are omitted entirely so jsfcstm's
        :func:`resolveFcstmDiagramPreviewOptions` fills in the proper
        per-detail-level default (e.g. ``transitionEffectMode='note'``
        for ``detail_level='normal'`` but ``'inline'`` for ``'minimal'``).
        """
        out: dict = {}
        for python_name, js_name in self._CAMEL_CASE.items():
            value = getattr(self, python_name)
            if value is not None:
                out[js_name] = value
        return out
