import pathlib

import click

from .base import CONTEXT_SETTINGS
from ..dsl import parse_with_grammar_entry
from ..model import parse_dsl_node_to_state_machine


def _add_plantuml_subcommand(cli: click.Group) -> click.Group:
    @cli.command('plantuml', help='Create Plantuml code of a given state machine DSL code.',
                 context_settings=CONTEXT_SETTINGS)
    @click.option('-i', '--input-code', 'input_code_file', type=str, required=True,
                  help='Input code file of state machine DSL.')
    @click.option('-o', '--output', 'output_file', type=str, default=None,
                  help='Output directory of the code generation, output to stdout when not assigned.')
    def plantuml(input_code_file, output_file):
        code = pathlib.Path(input_code_file).read_text()
        ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
        model = parse_dsl_node_to_state_machine(ast_node)
        if output_file is not None:
            with open(output_file, 'w') as f:
                f.write(model.to_plantuml())
        else:
            click.echo(model.to_plantuml())

    return cli
