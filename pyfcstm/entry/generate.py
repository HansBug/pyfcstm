import click

from .base import CONTEXT_SETTINGS


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
        pass

    return cli
