"""
State Machine DSL to PlantUML CLI Integration.

This module integrates a PlantUML generator into a Click-based command-line
interface. It provides a subcommand that reads state machine DSL code from a
file, parses it into an internal model, and emits PlantUML text either to a
file or to standard output.

The module is intended to be used as part of a larger CLI application that
manages multiple subcommands. It exposes the shared PlantUML option resolver
and source builder used by the ``plantuml`` and ``visualize`` entry points,
alongside the helper that registers the subcommand.

.. note::
   The CLI entry point relies on :func:`pyfcstm.dsl.parse.parse_with_grammar_entry`
   and :func:`pyfcstm.model.model.parse_dsl_node_to_state_machine` to build the
   model and assumes the input file contains valid state machine DSL content.

Example::

    >>> import click
    >>> from pyfcstm.entry.plantuml import _add_plantuml_subcommand
    >>> cli = click.Group()
    >>> _add_plantuml_subcommand(cli)  # doctest: +ELLIPSIS
    <...Group...>

"""

import difflib
import pathlib
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple, Union

import click
from click.core import ParameterSource

from .base import CONTEXT_SETTINGS, ClickErrorException
from ..dsl import parse_with_grammar_entry
from ..model import parse_dsl_node_to_state_machine
from ..model.plantuml import PlantUMLOptions
from ..utils import auto_decode, parse_key_value_pairs

@dataclass(frozen=True)
class _PlantUMLOptionSpec:
    """Metadata for one PlantUML option exposed at the CLI boundary."""

    type_hint: Optional[Union[type, str]]
    choices: Tuple[str, ...] = ()
    element_choices: Tuple[str, ...] = ()
    python_only: bool = False


_DETAIL_LEVEL_CHOICES = ('minimal', 'normal', 'full')
_LEGEND_POSITION_CHOICES = (
    'top left', 'top center', 'top right',
    'bottom left', 'bottom center', 'bottom right',
    'left', 'right', 'center',
)


# This registry is the single source for CLI types, choices, supported-key
# diagnostics, and the Python-only field classification.
_PLANTUML_OPTION_REGISTRY: Dict[str, _PlantUMLOptionSpec] = {
    'detail_level': _PlantUMLOptionSpec(str, choices=_DETAIL_LEVEL_CHOICES),
    'show_variable_definitions': _PlantUMLOptionSpec(bool),
    'variable_display_mode': _PlantUMLOptionSpec(
        str, choices=('note', 'legend', 'hide')
    ),
    'variable_legend_position': _PlantUMLOptionSpec(
        str, choices=_LEGEND_POSITION_CHOICES
    ),
    'state_name_format': _PlantUMLOptionSpec(
        'tuple[str, ...]', element_choices=('name', 'extra_name', 'path')
    ),
    'show_pseudo_state_style': _PlantUMLOptionSpec(bool),
    'collapse_empty_states': _PlantUMLOptionSpec(bool),
    'show_lifecycle_actions': _PlantUMLOptionSpec(bool),
    'show_enter_actions': _PlantUMLOptionSpec(bool),
    'show_during_actions': _PlantUMLOptionSpec(bool),
    'show_exit_actions': _PlantUMLOptionSpec(bool),
    'show_aspect_actions': _PlantUMLOptionSpec(bool),
    'show_abstract_actions': _PlantUMLOptionSpec(bool),
    'show_concrete_actions': _PlantUMLOptionSpec(bool),
    'abstract_action_marker': _PlantUMLOptionSpec(
        str, choices=('text', 'symbol', 'none')
    ),
    'max_action_lines': _PlantUMLOptionSpec(int),
    'show_transition_guards': _PlantUMLOptionSpec(bool),
    'show_transition_effects': _PlantUMLOptionSpec(bool),
    'transition_effect_mode': _PlantUMLOptionSpec(
        str, choices=('note', 'inline', 'hide')
    ),
    'show_events': _PlantUMLOptionSpec(bool),
    'event_name_format': _PlantUMLOptionSpec(
        'tuple[str, ...]',
        element_choices=('name', 'extra_name', 'path', 'relpath'),
    ),
    'event_visualization_mode': _PlantUMLOptionSpec(
        str, choices=('none', 'color', 'legend', 'both', 'dependency_view')
    ),
    'event_legend_position': _PlantUMLOptionSpec(
        str, choices=_LEGEND_POSITION_CHOICES
    ),
    'max_depth': _PlantUMLOptionSpec(int),
    'collapsed_state_marker': _PlantUMLOptionSpec(str),
    'use_skinparam': _PlantUMLOptionSpec(bool),
    'use_stereotypes': _PlantUMLOptionSpec(bool),
    'custom_colors': _PlantUMLOptionSpec(None, python_only=True),
}

# Kept as a derived compatibility view for callers that only need parser type
# hints. No key or type is maintained independently from the registry above.
_PLANTUML_OPTION_TYPES: Dict[str, Union[type, str]] = {
    key: spec.type_hint
    for key, spec in _PLANTUML_OPTION_REGISTRY.items()
    if not spec.python_only and spec.type_hint is not None
}
_PLANTUML_PYTHON_ONLY_OPTIONS = frozenset(
    key for key, spec in _PLANTUML_OPTION_REGISTRY.items() if spec.python_only
)

# Preserve the pre-existing public mapping for callers that imported it
# directly; its contents remain derived from the registry above.
PLANTUML_OPTION_TYPES = _PLANTUML_OPTION_TYPES


@dataclass(frozen=True)
class _PlantUMLOptionAssignment:
    """One normalized option assignment with its user-visible source label."""

    key: str
    value: Any
    source: str


def _format_supported_plantuml_options() -> str:
    """Format supported CLI options from the single registry."""
    groups = (
        ('Boolean', lambda hint: hint is bool),
        ('Integer', lambda hint: hint is int),
        ('Tuple', lambda hint: isinstance(hint, str) and hint.startswith('tuple[')),
        ('String', lambda hint: hint is str),
    )
    lines = ['Supported --config options:']
    for label, predicate in groups:
        names = sorted(
            key for key, spec in _PLANTUML_OPTION_REGISTRY.items()
            if not spec.python_only and predicate(spec.type_hint)
        )
        lines.append(f'  {label}: {", ".join(names)}')
    lines.append('Dedicated option: detail_level is also available as -l/--level.')
    lines.append('Python API only: custom_colors')
    return '\n'.join(lines)


def _unknown_plantuml_option_error(key: str) -> str:
    """Build a strict unknown-key diagnostic with an optional suggestion."""
    message = f"Unknown PlantUML configuration option {key!r}."
    suggestion = difflib.get_close_matches(
        key, sorted(_PLANTUML_OPTION_REGISTRY), n=1, cutoff=0.6
    )
    if suggestion:
        message += f"\nDid you mean {suggestion[0]!r}?"
    return f'{message}\n\n{_format_supported_plantuml_options()}'


def _canonical_choice(key: str, value: Any, choices: Tuple[str, ...]) -> str:
    """Normalize a case-insensitive string choice or raise a CLI error."""
    if not isinstance(value, str):
        raise ClickErrorException(
            f"Invalid value for PlantUML option {key!r}: {value!r}. "
            f'Expected one of: {", ".join(choices)}.'
        )
    normalized = value.strip().casefold()
    for choice in choices:
        if choice.casefold() == normalized:
            return choice
    raise ClickErrorException(
        f"Invalid value for PlantUML option {key!r}: {value!r}. "
        f'Expected one of: {", ".join(choices)}.'
    )


def _canonical_option_value(key: str, value: Any, spec: _PlantUMLOptionSpec) -> Any:
    """Apply registry choices and tuple-element validation to a parsed value."""
    if spec.choices:
        return _canonical_choice(key, value, spec.choices)
    if spec.element_choices:
        if not isinstance(value, tuple):
            raise ClickErrorException(
                f"Invalid value for PlantUML option {key!r}: {value!r}. "
                'Expected a tuple value.'
            )
        if not value or not any(str(element).strip() for element in value):
            raise ClickErrorException(
                f"Invalid value for PlantUML option {key!r}: "
                'expected at least one element.'
            )
        canonical = []
        for index, element in enumerate(value):
            try:
                canonical.append(_canonical_choice(key, element, spec.element_choices))
            except ClickErrorException as err:
                # _canonical_choice rejects an invalid enum or tuple element.
                raise ClickErrorException(f'{err} (element {index})')
        return tuple(canonical)
    return value


def _parse_plantuml_config_assignment(pair: str, index: int) -> _PlantUMLOptionAssignment:
    """Validate and parse one raw ``key=value`` CLI assignment."""
    if '=' not in pair:
        raise ClickErrorException(f"Option must be in 'key=value' format, got: {pair}")
    key, raw_value = pair.split('=', 1)
    key = key.strip()
    if not key:
        raise ClickErrorException('PlantUML configuration option key cannot be empty.')
    spec = _PLANTUML_OPTION_REGISTRY.get(key)
    if spec is None:
        raise ClickErrorException(_unknown_plantuml_option_error(key))
    if spec.python_only:
        raise ClickErrorException(
            f'PlantUML option {key!r} requires a mapping and is Python API only; '
            f'use PlantUMLOptions({key}={{...}}) instead.'
        )
    try:
        parsed = parse_key_value_pairs((pair,), type_hints=_PLANTUML_OPTION_TYPES)[key]
    except ValueError as err:
        # parse_key_value_pairs rejects a value that cannot match the registry type hint.
        raise ClickErrorException(str(err))
    value = _canonical_option_value(key, parsed, spec)
    return _PlantUMLOptionAssignment(key, value, f'--config[{index}]')


def _format_option_conflict(
    key: str,
    assignments: Tuple[_PlantUMLOptionAssignment, ...],
    winner: _PlantUMLOptionAssignment,
) -> str:
    """Format one stable warning for all conflicting assignments of a key."""
    lines = [f"conflicting explicit values for PlantUML option {key!r}:"]
    lines.extend(f'  {item.source}: {item.value!r}' for item in assignments)
    lines.append(f'Using {winner.value!r} from {winner.source}.')
    return '\n'.join(lines)


def resolve_plantuml_options(
    config_options: Tuple[str, ...] = (),
    dedicated_detail_level: Optional[str] = None,
) -> Tuple[PlantUMLOptions, Tuple[str, ...]]:
    """
    Resolve PlantUML CLI options from explicit generic and dedicated sources.

    :param config_options: Raw ``key=value`` assignments from ``-c``.
    :type config_options: Tuple[str, ...]
    :param dedicated_detail_level: Explicit ``-l/--level`` value, or ``None``
        when the Click default was used.
    :type dedicated_detail_level: str or None
    :return: Effective options and zero or more warning messages.
    :rtype: Tuple[PlantUMLOptions, Tuple[str, ...]]
    :raises pyfcstm.entry.base.ClickErrorException: If a key/value is invalid or
        ``PlantUMLOptions`` rejects the effective configuration.

    Example::

        >>> options, warnings = resolve_plantuml_options(('max_depth=2',))
        >>> options.max_depth
        2
        >>> warnings
        ()
    """
    assignments = [
        _parse_plantuml_config_assignment(pair, index)
        for index, pair in enumerate(config_options, 1)
    ]
    if dedicated_detail_level is not None:
        detail_spec = _PLANTUML_OPTION_REGISTRY['detail_level']
        assignments.append(
            _PlantUMLOptionAssignment(
                'detail_level',
                _canonical_option_value('detail_level', dedicated_detail_level, detail_spec),
                '--level',
            )
        )

    by_key: Dict[str, list] = {}
    for assignment in assignments:
        by_key.setdefault(assignment.key, []).append(assignment)

    effective: Dict[str, Any] = {}
    warnings = []
    for key, grouped in by_key.items():
        grouped_tuple = tuple(grouped)
        dedicated = next(
            (item for item in grouped_tuple if item.source == '--level'), None
        )
        winner = dedicated or grouped_tuple[-1]
        if any(item.value != grouped_tuple[0].value for item in grouped_tuple[1:]):
            warnings.append(_format_option_conflict(key, grouped_tuple, winner))
        effective[key] = winner.value

    try:
        options = PlantUMLOptions(**effective)
    except ValueError as err:
        # PlantUMLOptions.__post_init__ rejects an invalid cross-field configuration.
        raise ClickErrorException(f'Invalid PlantUML configuration: {err}')
    return options, tuple(warnings)


def _emit_plantuml_warnings(warnings: Tuple[str, ...]) -> None:
    """Write resolver warnings to stderr without changing command success."""
    for warning in warnings:
        click.echo(f'Warning: {warning}', err=True)


def _render_plantuml_source(input_code_file: str, options: PlantUMLOptions) -> str:
    """Parse a DSL file and render it with already-resolved options."""
    input_path = pathlib.Path(input_code_file)
    try:
        code = auto_decode(input_path.read_bytes())
    except FileNotFoundError:
        # Path.read_bytes raises this when the requested DSL file does not exist.
        raise ClickErrorException(f'Input DSL file not found: {input_code_file}')
    except OSError as err:
        # Path.read_bytes raises OSError for other filesystem/read failures.
        raise ClickErrorException(f'Failed to read input DSL file {input_code_file}: {err}')

    ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
    model = parse_dsl_node_to_state_machine(ast_node, path=input_code_file)
    return model.to_plantuml(options)


def build_plantuml_output(
    input_code_file: str,
    detail_level: Optional[str] = None,
    config_options: Tuple[str, ...] = (),
) -> str:
    """
    Build PlantUML text from a state machine DSL file.

    This helper centralizes the common CLI workflow for reading DSL code,
    parsing the state machine model, applying PlantUML options, and rendering
    the final PlantUML text representation.

    :param input_code_file: Path to the input DSL file.
    :type input_code_file: str
    :param detail_level: Explicit PlantUML detail level preset. ``None`` means
        that the built-in ``'normal'`` default was not explicitly supplied.
    :type detail_level: str or None, optional
    :param config_options: Additional PlantUML configuration options in
        ``key=value`` format.
    :type config_options: Tuple[str, ...], optional
    :return: Rendered PlantUML text.
    :rtype: str
    :raises pyfcstm.entry.base.ClickErrorException: If the input file cannot be
        read or a config option is invalid.
    :raises UnicodeDecodeError: If the input file cannot be decoded.
    :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.
    :raises SyntaxError: If the parsed DSL contains invalid state machine
        constructs.

    Example::

        >>> plantuml_text = build_plantuml_output('traffic_light.fcstm', detail_level='minimal')
        >>> plantuml_text.startswith('@startuml')
        True
    """
    options, warnings = resolve_plantuml_options(
        config_options=config_options,
        dedicated_detail_level=detail_level,
    )
    _emit_plantuml_warnings(warnings)
    return _render_plantuml_source(input_code_file, options)


def _add_plantuml_subcommand(cli: click.Group) -> click.Group:
    """
    Add the ``plantuml`` subcommand to a Click CLI group.

    This function registers a subcommand that converts state machine DSL code
    into PlantUML format. The registered command reads DSL code from a file,
    parses it into a state machine model, and outputs the corresponding
    PlantUML text to a file or stdout.

    :param cli: The Click group to which the subcommand should be added.
    :type cli: click.Group
    :return: The same CLI group instance with the subcommand registered.
    :rtype: click.Group

    Example::

        >>> from click import Group
        >>> cli = Group()
        >>> _add_plantuml_subcommand(cli)  # doctest: +ELLIPSIS
        <...Group...>
    """

    @cli.command(
        'plantuml',
        help=(
            'Create PlantUML source from a state machine DSL file.\n\n'
            'Configuration reference:\n'
            'https://pyfcstm.readthedocs.io/en/latest/reference/visualization_options/'
        ),
        context_settings=CONTEXT_SETTINGS,
    )
    @click.option(
        '-i',
        '--input-code',
        'input_code_file',
        type=str,
        required=True,
        help='Input code file of state machine DSL.',
    )
    @click.option(
        '-o',
        '--output',
        'output_file',
        type=str,
        default=None,
        help='Output file for PlantUML code, output to stdout when not assigned.',
    )
    @click.option(
        '-l',
        '--level',
        'detail_level',
        type=click.Choice(['minimal', 'normal', 'full'], case_sensitive=False),
        default='normal',
        help='Detail level preset (minimal/normal/full). Default: normal.',
    )
    @click.option(
        '-c',
        '--config',
        'config_options',
        multiple=True,
        help='Configuration options in key=value format. Can be specified multiple times. '
             'Example: -c show_events=true -c max_depth=2',
    )
    def plantuml(
        input_code_file: str,
        output_file: Optional[str],
        detail_level: str,
        config_options: Tuple[str, ...],
    ) -> None:
        """
        Convert state machine DSL code to PlantUML format.

        This command reads DSL code from the specified file, parses it into a
        state machine model, and emits PlantUML text either to the specified
        output file or to stdout when no output path is provided.

        The command supports flexible configuration through detail level presets
        and individual option overrides:

        * Use ``-l/--level`` to select a preset (minimal/normal/full)
        * Use ``-c/--config`` to override specific options with key=value pairs

        :param input_code_file: Path to the file containing state machine DSL code.
        :type input_code_file: str
        :param output_file: Path to the output file for PlantUML code. If
            ``None``, output is written to stdout.
        :type output_file: str or None
        :param detail_level: Detail level preset (minimal/normal/full).
        :type detail_level: str
        :param config_options: Tuple of key=value configuration options.
        :type config_options: Tuple[str, ...]
        :return: ``None``. Output is written to a file or stdout.
        :rtype: None

        :raises UnicodeDecodeError: If the input file cannot be decoded by
            :func:`pyfcstm.utils.decode.auto_decode`.
        :raises AttributeError: If the grammar entry name does not exist in the
            DSL parser.
        :raises pyfcstm.dsl.error.GrammarParseError: If parsing fails for the
            provided DSL input.
        :raises SyntaxError: If the parsed DSL contains invalid state machine
            constructs.
        :raises click.BadParameter: If a config option is not in key=value format.

        Example::

            >>> # Basic usage with default settings
            >>> # pyfcstm plantuml -i example.dsl -o example.puml

            >>> # Use minimal detail level
            >>> # pyfcstm plantuml -i example.dsl -l minimal

            >>> # Override specific options
            >>> # pyfcstm plantuml -i example.dsl -c show_events=true -c max_depth=2

            >>> # Combine preset with overrides
            >>> # pyfcstm plantuml -i example.dsl -l full -c max_depth=3 -c event_visualization_mode=color
        """
        context = click.get_current_context()
        dedicated_detail_level = (
            detail_level
            if context.get_parameter_source('detail_level') is ParameterSource.COMMANDLINE
            else None
        )
        options, warnings = resolve_plantuml_options(
            config_options=config_options,
            dedicated_detail_level=dedicated_detail_level,
        )
        _emit_plantuml_warnings(warnings)
        plantuml_output = _render_plantuml_source(input_code_file, options)

        # Write output
        if output_file is not None:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(plantuml_output)
        else:
            click.echo(plantuml_output)

    return cli
