import click

from .base import CONTEXT_SETTINGS
from ..convert.sysdesim.ast import convert_state_machine_to_ast_node
from ..convert.sysdesim.parser import SysDesimParser


def _add_convert_sysdesim_subcommand(cli: click.Group) -> click.Group:
    @cli.command('convert_sysdesim', help='Convert sysdesim model to DSL code.',
                 context_settings=CONTEXT_SETTINGS)
    @click.option('-i', '--input-file', 'input_file', type=str, required=True,
                  help='Input code file of sysdesim.')
    def convert_sysdesim(input_file):
        s = SysDesimParser.parse_file(input_file)
        model = s.parse_model(s.get_model_elements()[0])
        print(convert_state_machine_to_ast_node(model.clazz.state_machine, model))

    return cli
