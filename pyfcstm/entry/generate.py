import pathlib

import click

from .base import CONTEXT_SETTINGS
from ..dsl import parse_with_grammar_entry
from ..model import parse_dsl_node_to_state_machine
from ..render import StateMachineCodeRenderer


def _add_generate_subcommand(cli: click.Group) -> click.Group:
    @cli.command('generate', help='Generate code with template of a given state machine DSL code.',
                 context_settings=CONTEXT_SETTINGS)
    @click.option('-i', '--input-code', 'input_code_file', type=str, required=True,
                  help='Input code file of state machine DSL.')
    @click.option('-t', '--template-dir', 'template_dir', type=str, required=True,
                  help='Template directory of the code generation.')
    @click.option('-o', '--output-dir', 'output_dir', type=str, required=True,
                  help='Output directory of the code generation.')
    @click.option('--clear', '--clear-directory', 'clear_directory', type=bool, is_flag=True,
                  help='Clear the destination directory of the output directory.')
    def generate(input_code_file, template_dir, output_dir, clear_directory):
        code = pathlib.Path(input_code_file).read_text()
        ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
        model = parse_dsl_node_to_state_machine(ast_node)

        renderer = StateMachineCodeRenderer(
            template_dir=template_dir,
        )
        renderer.render(
            model,
            output_dir=output_dir,
            clear_previous_directory=clear_directory
        )

    return cli
