import pathlib

import click

from .base import CONTEXT_SETTINGS
from ..algorithm.reachability import path_reachability
from ..dsl import parse_with_grammar_entry, INIT_STATE, EXIT_STATE
from ..model import parse_dsl_node_to_state_machine


def _add_reachability_subcommand(cli: click.Group) -> click.Group:
    @cli.command('reachability', help='Calculate reachability.',
                 context_settings=CONTEXT_SETTINGS)
    @click.option('-i', '--input-code', 'input_code_file', type=str, required=True,
                  help='Input code file of pyfcstm.')
    @click.option('-p', '--path', 'path', type=str, default=None,
                  help='State path to check')
    @click.option('-src', '--source-state', 'source_state', type=str, required=True,
                  help='Source state')
    @click.option('-dst', '--destination-state', 'destination_state', type=str, required=True,
                  help='Destination state')
    def reachability(input_code_file, path, source_state, destination_state):
        ast_node = parse_with_grammar_entry(pathlib.Path(input_code_file).read_text(), entry_name='state_machine_dsl')
        model = parse_dsl_node_to_state_machine(ast_node)
        path = tuple(filter(bool, (path or '').split('.')))
        state = model.root_state
        for segment in path:
            state = state.substates[segment]

        if source_state == '[*]' or source_state == 'INIT_STATE':
            from_state = INIT_STATE
        else:
            from_state = source_state

        if destination_state == '[*]' or source_state == 'EXIT_STATE':
            to_state = EXIT_STATE
        else:
            to_state = destination_state

        is_reachable, reach_path = path_reachability(state, from_state, to_state)
        print(f'Is reachable: {"yes" if is_reachable else "no"}')
        if is_reachable:
            print(f'Path: {" --> ".join(map(str, reach_path))}')

    return cli
