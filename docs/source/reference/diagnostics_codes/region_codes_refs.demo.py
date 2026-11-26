"""Print the structured diagnostics that model construction collects.

A span is printed as [line, column, end_line, end_column].
"""
import json
from pathlib import Path

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine

FILES = [
    "region_diag_empty_region.fcstm",
    "region_diag_history_boundary.fcstm",
    "region_diag_duplicate.fcstm",
    "region_diag_active_not_found.fcstm",
    "region_diag_active_invalid_path.fcstm",
    "region_diag_active_region.fcstm",
    "region_diag_active_pseudo.fcstm",
]

for name in FILES:
    ast = parse_with_grammar_entry(Path(name).read_text(), "state_machine_dsl")
    model, diagnostics = parse_dsl_node_to_state_machine(ast, collect=True)
    print("---", name, "model is None:", model is None)
    for item in diagnostics:
        span = item.span
        print(json.dumps({
            "code": item.code,
            "severity": item.severity,
            "message": item.message,
            "span": [span.line, span.column, span.end_line, span.end_column] if span else None,
            "refs": item.refs,
        }, sort_keys=True, default=lambda span: [span.line, span.column, span.end_line, span.end_column]))
