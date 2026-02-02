import logging
import os

import click

from .base import CONTEXT_SETTINGS
from ..convert.sysdesim.ast import convert_state_machine_to_ast_node
from ..convert.sysdesim.parser import SysDesimParser
from ..dsl import parse_with_grammar_entry
from ..model.model import parse_dsl_node_to_state_machine


def _audit_model_topology(node, model_index):
    """
    Audit the generated AST for topology issues, checking for logical breaks.
    Robustness feature: automatically discover isolated nodes by analyzing state transition relationships.
    """
    states = [s.name for s in node.substates if s.name != '[*]']
    # Collect all sources and targets that appear in transitions
    sources = {t.from_state for t in node.transitions if t.from_state}
    targets = {t.to_state for t in node.transitions if t.to_state}

    logging.info(f"--- Model [{model_index}] Topology Audit Report ---")
    logging.info(f"  Total states: {len(states)} | Total transitions: {len(node.transitions)}")

    isolated_states = []
    for s in states:
        if s not in sources and s not in targets:
            isolated_states.append(s)

    if not isolated_states:
        logging.info(
            "  ✅ Topology check passed: No isolated state nodes found (all states have incoming or outgoing transitions).")
    else:
        logging.warning(
            f"  ⚠️ Topology warning: Found isolated nodes {isolated_states}. Please verify if corresponding transitions are defined in XML.")


def _generate_output_filename(base_output_file, index):
    """
    Generate output filename based on index.
    First model uses the original name, subsequent models add index before extension.
    """
    if index == 0:
        return base_output_file

    # Split filename and extension
    base_name, ext = os.path.splitext(base_output_file)
    return f"{base_name}.{index}{ext}"


def _add_convert_sysdesim_subcommand(cli: click.Group) -> click.Group:
    @cli.command('convert_sysdesim', help='Convert sysdesim model to DSL code.',
                 context_settings=CONTEXT_SETTINGS)
    @click.option('-i', '--input-file', 'input_file', type=str, required=True,
                  help='Input code file of sysdesim.')
    @click.option('-o', '--output-file', 'output_file', type=str, required=True,
                  help='Output DSL file path. Multiple models will be numbered sequentially.')
    @click.option('-wp', '--with-plantuml', 'with_plantuml', is_flag=True, default=False,
                  help='Generate corresponding PlantUML files for each DSL model.')
    def convert_sysdesim(input_file, output_file, with_plantuml):
        if not os.path.exists(input_file):
            logging.error(f"Input file not found: {input_file}")
            return

        logging.info(f"=== Starting comprehensive robustness verification: {input_file} ===")

        # 1. Load XML
        s = SysDesimParser.parse_file(input_file)
        model = s.parse_model(s.get_model_elements()[0])
        logging.info("✅ Step 1: XML data parsing completed")

        # 2. Execute conversion (calling SysMLConverter class logic)
        nodes = convert_state_machine_to_ast_node(model.clazz.state_machine, model)
        logging.info(
            f"✅ Step 2: Conversion completed, identified {len(nodes)} concurrent regions and performed splitting")

        # 3. Process each model individually
        for i, node in enumerate(nodes):
            # Execute closed-loop parsing verification
            dsl_code = str(node)
            try:
                ast_node = parse_with_grammar_entry(dsl_code, entry_name='state_machine_dsl')
                parse_dsl_node_to_state_machine(ast_node)
                logging.info(f"✅ Model [{i}] closed-loop parsing verification successful (100% legal syntax)")
            except Exception as e:
                logging.error(f"❌ Model [{i}] closed-loop parsing failed: {e}")
                continue

            # Execute topology audit (detect break issues)
            _audit_model_topology(node, i)

            # Output DSL file if output_file is specified
            dsl_filename = _generate_output_filename(output_file, i)
            # Ensure output directory exists
            if os.path.dirname(dsl_filename):
                os.makedirs(os.path.dirname(dsl_filename), exist_ok=True)
            with open(dsl_filename, "w", encoding="utf-8") as f:
                f.write(dsl_code)
            logging.info(f"  👉 DSL model saved to: {dsl_filename}")

            # Generate PlantUML file if requested
            if with_plantuml:
                puml_filename = f"{dsl_filename}.puml"
                with open(puml_filename, "w", encoding="utf-8") as f:
                    # Re-read model to call to_plantuml
                    re_model = parse_dsl_node_to_state_machine(ast_node)
                    f.write(re_model.to_plantuml())
                logging.info(f"  👉 PlantUML visualization saved to: {puml_filename}")

    return cli
