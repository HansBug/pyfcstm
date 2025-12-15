import logging
import pathlib

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

from .base import CONTEXT_SETTINGS
from ..dsl import parse_with_grammar_entry
from ..model import parse_dsl_node_to_state_machine
from ..simulate import SimulationRuntime
from ..utils.logging import ColoredFormatter


def _add_simulate_command(cli: click.Group) -> click.Group:
    @cli.command('simulate', help='Simulate a model.',
                 context_settings=CONTEXT_SETTINGS)
    @click.option('-i', '--input-code', 'input_code_file', type=str, required=True,
                  help='Input code file of pyfcstm.')
    def simulate(input_code_file):
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(ColoredFormatter())
        logger.addHandler(console_handler)

        ast_node = parse_with_grammar_entry(pathlib.Path(input_code_file).read_text(), entry_name='state_machine_dsl')
        model = parse_dsl_node_to_state_machine(ast_node)

        sr = SimulationRuntime(model)

        history_file = f'{input_code_file}.cli_history'
        session = PromptSession(history=FileHistory(history_file))
        print('Full Model:')
        print(model.to_ast_node())

        while True:
            try:
                cmd = session.prompt('>>> ')
                if cmd.strip() == 'exit':
                    break
                elif cmd.strip() == 'cycle':
                    sr.cycle()
                elif cmd.strip():
                    print('Unknown command, please use \'cycle\' for run a cycle or exit to quit.')


            except KeyboardInterrupt:
                continue
            except EOFError:
                break

    return cli
