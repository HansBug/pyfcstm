"""
This module provides CLI functionality for analyzing mutual exclusivity between paths in multiple state machines.

The module adds an 'exclusive' subcommand to the CLI that uses Z3 constraint solving to determine if
paths in different state machines are mutually exclusive. It loads multiple DSL models, validates their
variable consistency, and checks if the combined constraints can be satisfied simultaneously.
"""

import pathlib
from typing import List, Tuple

import click
import z3

from .base import CONTEXT_SETTINGS
from ..dsl import parse_with_grammar_entry
from ..model import parse_dsl_node_to_state_machine, StateMachine
from ..utils import auto_decode
from ..validate.eval import z3_evaluate
from ..validate.search import get_search_expr
from ..validate.solve import solve_expr


def _parse_model_spec(spec: str) -> Tuple[str, str, str]:
    """
    Parse a model specification string into components.

    :param spec: Model specification in format "path/to/file.fcstm:src_state:dst_state"
    :type spec: str

    :return: Tuple of (file_path, source_state, destination_state)
    :rtype: Tuple[str, str, str]

    :raises ValueError: If the specification format is invalid
    """
    parts = spec.split(':')
    if len(parts) != 3:
        raise ValueError(
            f"Invalid model specification format: '{spec}'. Expected format: 'path/to/file.fcstm:src_state:dst_state'")

    file_path, src_state, dst_state = parts

    if not file_path.strip():
        raise ValueError(f"Empty file path in specification: '{spec}'")
    if not src_state.strip():
        raise ValueError(f"Empty source state in specification: '{spec}'")
    if not dst_state.strip():
        raise ValueError(f"Empty destination state in specification: '{spec}'")

    return file_path.strip(), src_state.strip(), dst_state.strip()


def _validate_variable_consistency(models: List[Tuple[str, StateMachine]]) -> None:
    """
    Validate that all models have consistent variable definitions.

    :param models: List of tuples containing (model_name, StateMachine)
    :type models: List[Tuple[str, StateMachine]]

    :raises ValueError: If variable definitions are inconsistent across models
    """
    if not models:
        return

    reference_name, reference_model = models[0]
    reference_vars = reference_model.defines

    for model_name, model in models[1:]:
        current_vars = model.defines

        # Check if variable names match
        ref_var_names = set(reference_vars.keys())
        cur_var_names = set(current_vars.keys())

        if ref_var_names != cur_var_names:
            missing_in_current = ref_var_names - cur_var_names
            extra_in_current = cur_var_names - ref_var_names

            error_msg = f"Variable definitions inconsistent between '{reference_name}' and '{model_name}'"
            if missing_in_current:
                error_msg += f"\n  Missing in '{model_name}': {sorted(missing_in_current)}"
            if extra_in_current:
                error_msg += f"\n  Extra in '{model_name}': {sorted(extra_in_current)}"

            raise ValueError(error_msg)

        # Check if variable types match
        for var_name in ref_var_names:
            ref_type = reference_vars[var_name].type
            cur_type = current_vars[var_name].type

            if ref_type != cur_type:
                raise ValueError(
                    f"Variable '{var_name}' has inconsistent types:\n"
                    f"  In '{reference_name}': {ref_type}\n"
                    f"  In '{model_name}': {cur_type}"
                )


def _add_exclusive_subcommand(cli: click.Group) -> click.Group:
    """
    Add the 'exclusive' subcommand to the CLI group.

    This function adds an 'exclusive' subcommand to the provided CLI group that allows users to
    analyze mutual exclusivity between paths in multiple state machine DSL files using Z3 constraint solving.

    :param cli: The click Group object to which the subcommand will be added
    :type cli: click.Group

    :return: The modified CLI group with the 'exclusive' subcommand added
    :rtype: click.Group
    """

    @cli.command('exclusive', help='Analyze mutual exclusivity between paths in multiple state machine DSLs.',
                 context_settings=CONTEXT_SETTINGS)
    @click.option('-i', '--input-model', 'input_models', type=str, multiple=True, required=True,
                  help='Input model specifications in format "path/to/file.fcstm:src_state:dst_state". '
                       'Can be specified multiple times. At least 2 models required.')
    @click.option('-p', '--max-path-length', 'max_path_length', type=int, default=30,
                  help='Maximum number of transitions allowed in a path (default: 30).')
    @click.option('-c', '--max-cycle-length', 'max_cycle_length', type=int, default=20,
                  help='Maximum number of non-pseudo states allowed in a path (default: 20).')
    @click.option('--show-constraints', 'show_constraints', is_flag=True,
                  help='Show the generated Z3 constraint expressions for each model.')
    @click.option('--show-variables', 'show_variables', is_flag=True,
                  help='Show the Z3 variable definitions.')
    def exclusive(input_models: Tuple[str, ...], max_path_length: int, max_cycle_length: int,
                  show_constraints: bool, show_variables: bool):
        """
        Analyze mutual exclusivity between paths in multiple state machines.

        This function loads multiple state machine DSL files, validates their variable consistency,
        and uses Z3 constraint solving to determine if the paths are mutually exclusive. If paths
        are not mutually exclusive, it shows the execution traces for each model under a satisfying
        assignment.

        :param input_models: Tuple of model specification strings
        :type input_models: Tuple[str, ...]

        :param max_path_length: Maximum number of transitions allowed in a path
        :type max_path_length: int

        :param max_cycle_length: Maximum number of non-pseudo states allowed in a path
        :type max_cycle_length: int

        :param show_constraints: Whether to display the generated Z3 constraints
        :type show_constraints: bool

        :param show_variables: Whether to display the Z3 variable definitions
        :type show_variables: bool
        """
        try:
            # Validate input count
            if len(input_models) < 2:
                click.echo("❌ Error: At least 2 input models are required for exclusivity analysis", err=True)
                return

            click.echo(f"🔍 Loading {len(input_models)} state machine models...")

            # Parse and load all models
            models = []
            model_specs = []

            for i, model_spec in enumerate(input_models):
                try:
                    file_path, src_state, dst_state = _parse_model_spec(model_spec)
                    model_name = f"Model_{i + 1}({pathlib.Path(file_path).stem})"

                    click.echo(f"   📂 Loading {model_name}: {file_path}")

                    # Load and parse the DSL file
                    if not pathlib.Path(file_path).exists():
                        raise FileNotFoundError(f"File not found: {file_path}")

                    code = auto_decode(pathlib.Path(file_path).read_bytes())
                    ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
                    model = parse_dsl_node_to_state_machine(ast_node)

                    models.append((model_name, model))
                    model_specs.append((model_name, file_path, src_state, dst_state))

                    click.echo(f"   ✅ {model_name} loaded successfully")

                except Exception as e:
                    click.echo(f"   ❌ Failed to load model from '{model_spec}': {str(e)}", err=True)
                    return

            # Validate variable consistency
            click.echo(f"\n🔧 Validating variable consistency across models...")
            try:
                _validate_variable_consistency(models)
                click.echo(f"✅ All models have consistent variable definitions")
            except ValueError as e:
                click.echo(f"❌ Variable consistency check failed:\n{str(e)}", err=True)
                return

            # Generate constraints for each model
            click.echo(f"\n🔎 Generating path constraints for each model...")

            model_constraints = []
            shared_variables = None
            all_search_items = []

            for i, ((model_name, model), (_, _, src_state, dst_state)) in enumerate(zip(models, model_specs)):
                click.echo(f"   🛤️  {model_name}: '{src_state}' → '{dst_state}'")

                try:
                    variables, expr, items = get_search_expr(
                        model,
                        src_state,
                        dst_state,
                        max_path_length=max_path_length,
                        max_cycle_length=max_cycle_length
                    )

                    if shared_variables is None:
                        shared_variables = variables

                    model_constraints.append((model_name, expr))
                    all_search_items.append((model_name, items))

                    click.echo(f"      ✅ Constraints generated successfully")

                except Exception as e:
                    click.echo(f"      ❌ Failed to generate constraints: {str(e)}", err=True)
                    return

            # Show variables if requested
            if show_variables:
                click.echo(f"\n📊 Z3 Variables:")
                for name, var in shared_variables.items():
                    click.echo(f"   {name}: {var}")

            # Show constraints if requested
            if show_constraints:
                click.echo(f"\n🔗 Z3 Constraints:")
                for model_name, expr in model_constraints:
                    click.echo(f"   {model_name}:")
                    click.echo(f"      {expr}")

            # Combine all constraints with AND
            click.echo(f"\n⚡ Analyzing mutual exclusivity...")
            combined_constraint = z3.And(*[expr for _, expr in model_constraints])

            # Solve the combined constraints
            solve_result = solve_expr(combined_constraint, shared_variables, max_solutions=1)

            # Display results
            if solve_result.type == 'sat' and solve_result.solutions:
                click.echo(f"❌ Paths are NOT mutually exclusive!")
                click.echo(f"   Found a satisfying assignment where all paths can be executed simultaneously.")

                solution = solve_result.solutions[0]

                click.echo(f"\n{'=' * 80}")
                click.echo(f"🎯 SATISFYING ASSIGNMENT")
                click.echo(f"{'=' * 80}")

                # Show variable values
                click.echo(f"📋 Variable Values:")
                for var_name, var_value in solution.items():
                    if var_value is not None:
                        click.echo(f"   {var_name} = {var_value}")

                # Show execution traces for each model
                for i, ((model_name, _), (_, items)) in enumerate(zip(model_constraints, all_search_items)):
                    click.echo(f"\n{'─' * 60}")
                    click.echo(f"🛤️  EXECUTION TRACE: {model_name}")
                    click.echo(f"{'─' * 60}")

                    # Find the corresponding search state item for this model
                    matching_item = None
                    for item in items:
                        try:
                            if z3_evaluate(
                                    expr=item.get_constraint(),
                                    variables=shared_variables,
                                    values=solution,
                            ):
                                matching_item = item
                                break
                        except:
                            continue

                    if not matching_item:
                        click.echo("❌ Error: Could not find corresponding execution trace")
                        continue

                    # Build the execution path
                    path = []
                    current_item = matching_item
                    while current_item:
                        var_values = {}
                        try:
                            var_values = {
                                name: z3_evaluate(expr, shared_variables, solution)
                                for name, expr in current_item.variables.items()
                            }
                        except:
                            pass

                        path.append((
                            '.'.join(current_item.state.path),
                            var_values,
                            current_item.path_length,
                            current_item.cycle_length
                        ))
                        current_item = current_item.pre_state

                    path = path[::-1]  # Reverse to show from start to end

                    # Display the path
                    for j, (state_path, var_values, path_len, cycle_len) in enumerate(path):
                        if j == 0:
                            click.echo(f"🏁 START: {state_path:<25} [Path: {path_len:2d}, Cycle: {cycle_len:2d}]")
                        elif j == len(path) - 1:
                            click.echo(f"🎯 END:   {state_path:<25} [Path: {path_len:2d}, Cycle: {cycle_len:2d}]")
                        else:
                            click.echo(f"📍 STEP:  {state_path:<25} [Path: {path_len:2d}, Cycle: {cycle_len:2d}]")

                        if var_values:
                            for var_name, var_value in var_values.items():
                                click.echo(f"       {var_name} = {var_value}")

                        if j < len(path) - 1:
                            click.echo("       ⬇️")

            elif solve_result.type == 'unsat':
                click.echo(f"✅ Paths are mutually exclusive!")
                click.echo(f"   No satisfying assignment exists where all paths can be executed simultaneously.")
                click.echo(f"   The combined constraints are unsatisfiable.")

            else:  # undetermined
                click.echo(f"❓ Could not determine mutual exclusivity")
                click.echo(f"   The Z3 solver returned an undetermined result.")
                click.echo(f"   Try adjusting the path length limits or simplifying the constraints.")

        except Exception as e:
            click.echo(f"❌ Error during exclusivity analysis: {str(e)}", err=True)
            if click.get_current_context().obj and click.get_current_context().obj.get('debug'):
                import traceback
                click.echo(traceback.format_exc(), err=True)

    return cli
