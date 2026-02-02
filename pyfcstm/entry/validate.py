import pathlib

import click

from .base import CONTEXT_SETTINGS
from ..dsl import parse_with_grammar_entry
from ..model import parse_dsl_node_to_state_machine
from ..utils import auto_decode
from ..validate.eval import z3_evaluate
from ..validate.search import get_search_expr
from ..validate.solve import solve_expr


def _add_validate_subcommand(cli: click.Group) -> click.Group:
    """
    Add the 'validate' subcommand to the CLI group.

    This function adds a 'validate' subcommand to the provided CLI group that allows users to
    validate and analyze paths between states in a state machine DSL file using Z3 constraint solving.

    :param cli: The click Group object to which the subcommand will be added
    :type cli: click.Group

    :return: The modified CLI group with the 'validate' subcommand added
    :rtype: click.Group

    Example::

        >>> app = click.Group()
        >>> app = _add_validate_subcommand(app)
    """

    @cli.command('validate', help='Validate and analyze paths between states in a state machine DSL.',
                 context_settings=CONTEXT_SETTINGS)
    @click.option('-i', '--input-code', 'input_code_file', type=str, required=True,
                  help='Input code file of state machine DSL.')
    @click.option('-s', '--source-state', '--src-state', 'source_state', type=str, required=True,
                  help='Source state path for path validation.')
    @click.option('-d', '--destination-state', '--dst-state', 'destination_state', type=str, required=True,
                  help='Destination state path for path validation.')
    @click.option('-p', '--max-path-length', 'max_path_length', type=int, default=30,
                  help='Maximum number of transitions allowed in a path (default: 30).')
    @click.option('-c', '--max-cycle-length', 'max_cycle_length', type=int, default=20,
                  help='Maximum number of non-pseudo states allowed in a path (default: 20).')
    @click.option('-n', '--max-solutions', 'max_solutions', type=int, default=10,
                  help='Maximum number of solutions to find (default: 10).')
    @click.option('--show-constraints', 'show_constraints', is_flag=True,
                  help='Show the generated Z3 constraint expressions.')
    @click.option('--show-variables', 'show_variables', is_flag=True,
                  help='Show the Z3 variable definitions.')
    def validate(input_code_file, source_state, destination_state, max_path_length,
                 max_cycle_length, max_solutions, show_constraints, show_variables):
        """
        Validate and analyze paths between states in a state machine.

        This function reads a state machine DSL file, parses it into a model, and uses Z3
        constraint solving to find valid paths from the source state to the destination state.
        It displays detailed information about the paths including variable values at each step.

        :param input_code_file: Path to the input DSL code file
        :type input_code_file: str

        :param source_state: Path string identifying the source state
        :type source_state: str

        :param destination_state: Path string identifying the destination state
        :type destination_state: str

        :param max_path_length: Maximum number of transitions allowed in a path
        :type max_path_length: int

        :param max_cycle_length: Maximum number of non-pseudo states allowed in a path
        :type max_cycle_length: int

        :param max_solutions: Maximum number of solutions to find
        :type max_solutions: int

        :param show_constraints: Whether to display the generated Z3 constraints
        :type show_constraints: bool

        :param show_variables: Whether to display the Z3 variable definitions
        :type show_variables: bool

        :return: None
        """
        try:
            # Parse the DSL code
            click.echo(f"🔍 Loading state machine from: {input_code_file}")
            code = auto_decode(pathlib.Path(input_code_file).read_bytes())
            ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
            model = parse_dsl_node_to_state_machine(ast_node)
            click.echo(f"✅ State machine loaded successfully")

            # Generate search expressions
            click.echo(f"\n🔎 Searching paths from '{source_state}' to '{destination_state}'")
            click.echo(f"   Max path length: {max_path_length}")
            click.echo(f"   Max cycle length: {max_cycle_length}")

            variables, expr, items = get_search_expr(
                model,
                source_state,
                destination_state,
                max_path_length=max_path_length,
                max_cycle_length=max_cycle_length
            )

            # Show variables if requested
            if show_variables:
                click.echo(f"\n📊 Z3 Variables:")
                for name, var in variables.items():
                    click.echo(f"   {name}: {var}")

            # Show constraints if requested
            if show_constraints:
                click.echo(f"\n🔗 Z3 Constraints:")
                click.echo(f"   {expr}")

            # Solve the constraints
            click.echo(f"\n⚡ Solving constraints...")
            solve_result = solve_expr(expr, variables, max_solutions=max_solutions)

            # Display results
            if solve_result.type == 'sat':
                click.echo(f"✅ Found {len(solve_result.solutions)} valid path(s)")

                for i, solution in enumerate(solve_result.solutions, 1):
                    click.echo(f"\n{'=' * 60}")
                    click.echo(f"🛤️  PATH {i}")
                    click.echo(f"{'=' * 60}")

                    # Find the corresponding search state item
                    state_item = None
                    for item in items:
                        if z3_evaluate(
                                expr=item.get_constraint(),
                                variables=variables,
                                values=solution,
                        ):
                            state_item = item
                            break

                    if not state_item:
                        click.echo("❌ Error: Could not find corresponding state item")
                        continue

                    # Build the path
                    path = []
                    current_item = state_item
                    while current_item:
                        var_values = {
                            name: z3_evaluate(expr, variables, solution)
                            for name, expr in current_item.variables.items()
                        }
                        path.append(('.'.join(current_item.state.path), var_values))
                        current_item = current_item.pre_state

                    path = path[::-1]  # Reverse to show from start to end

                    # Display the path beautifully
                    for j, (state_path, var_values) in enumerate(path):
                        if j == 0:
                            click.echo(f"🏁 START: {state_path}")
                        elif j == len(path) - 1:
                            click.echo(f"🎯 END:   {state_path}")
                        else:
                            click.echo(f"📍 STEP:  {state_path}")

                        if var_values:
                            for var_name, var_value in var_values.items():
                                click.echo(f"       {var_name} = {var_value}")

                        if j < len(path) - 1:
                            click.echo("       ⬇️")

            elif solve_result.type == 'unsat':
                click.echo(f"❌ No valid path found from '{source_state}' to '{destination_state}'")
                click.echo("   The constraints cannot be satisfied with the given parameters.")

            else:  # undetermined
                click.echo(f"❓ Could not determine if a valid path exists")
                click.echo("   The Z3 solver returned an undetermined result.")
                click.echo("   Try adjusting the path length limits or simplifying the constraints.")

        except FileNotFoundError:
            click.echo(f"❌ Error: Input file '{input_code_file}' not found", err=True)
        except Exception as e:
            click.echo(f"❌ Error during validation: {str(e)}", err=True)
            if click.get_current_context().obj and click.get_current_context().obj.get('debug'):
                import traceback
                click.echo(traceback.format_exc(), err=True)

    return cli
