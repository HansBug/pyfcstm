"""
Modeling package initialization and explicit public re-exports.

This module aggregates the public classes, functions, and type aliases used by
the :mod:`pyfcstm.model` namespace. The re-export surface is explicit so the
top-level model API remains easy to inspect and stable for callers.

The following public components are re-exported here:

* :class:`AstExportable` - Abstract base class for AST serialization support
* :class:`PlantUMLExportable` - Abstract base class for PlantUML serialization support
* :class:`Expr` - Base class for model-layer expressions
* :class:`Integer` - Integer literal expression
* :class:`Float` - Floating-point literal expression
* :class:`Boolean` - Boolean literal expression
* :class:`Op` - Base class for operator expressions
* :class:`UnaryOp` - Unary operator expression
* :class:`BinaryOp` - Binary operator expression
* :class:`ConditionalOp` - Ternary conditional expression
* :class:`UFunc` - Unary mathematical function expression
* :class:`Variable` - Variable reference expression
* :func:`parse_expr_node_to_expr` - Convert DSL AST nodes to model expressions
* :func:`parse_expr_from_string` - Parse DSL expression text into model expressions
* :func:`parse_expr` - Unified expression parser
* :class:`OperationStatement` - Base class for operation statements
* :class:`Operation` - Assignment operation statement
* :class:`IfBlockBranch` - Branch inside an ``if`` operation block
* :class:`IfBlock` - Conditional operation block
* :class:`Event` - State-machine event model
* :class:`Transition` - State transition model
* :class:`OnStage` - Enter/during/exit action model
* :class:`OnAspect` - Aspect-oriented during action model
* :class:`State` - Hierarchical state model
* :class:`VarDefine` - Variable definition model
* :class:`StateMachine` - Root state-machine model
* :func:`parse_dsl_node_to_state_machine` - Build a model from DSL AST
* :class:`DetailLevelLiteral` - PlantUML detail level literal type
* :class:`PlantUMLOptionsInput` - Accepted PlantUML option input type
* :class:`PlantUMLOptions` - PlantUML rendering options
* :func:`format_state_name` - Format state labels for PlantUML
* :func:`format_event_name` - Format event labels for PlantUML
* :func:`escape_plantuml_table_cell` - Escape PlantUML legend/table content
* :func:`should_show_action` - Decide whether an action should be rendered
* :func:`format_action_text` - Format action text for PlantUML output
* :func:`collect_event_transitions` - Collect transitions grouped by event
* :func:`assign_event_colors` - Assign PlantUML colors to events
* :func:`load_state_machine_from_file` - Convenience model loader from file
* :func:`load_state_machine_from_text` - Convenience model loader from DSL text

Example::

    >>> from pyfcstm.model import (
    ...     AstExportable,
    ...     PlantUMLExportable,
    ...     StateMachine,
    ...     load_state_machine_from_text,
    ... )
    >>> isinstance(AstExportable(), AstExportable)
    True
    >>> isinstance(PlantUMLExportable(), PlantUMLExportable)
    True
    >>> model = load_state_machine_from_text('state Root;')
    >>> isinstance(model, StateMachine)
    True
"""

from .base import AstExportable, PlantUMLExportable
from .expr import (
    Expr,
    Integer,
    Float,
    Boolean,
    Op,
    UnaryOp,
    BinaryOp,
    ConditionalOp,
    UFunc,
    Variable,
    parse_expr_node_to_expr,
    parse_expr_from_string,
    parse_expr,
)
from .load import load_state_machine_from_file, load_state_machine_from_text
from .model import (
    OperationStatement,
    Operation,
    IfBlockBranch,
    IfBlock,
    Event,
    Transition,
    OnStage,
    OnAspect,
    State,
    VarDefine,
    StateMachine,
    parse_dsl_node_to_state_machine,
)
from .plantuml import (
    DetailLevelLiteral,
    PlantUMLOptionsInput,
    PlantUMLOptions,
    format_state_name,
    format_event_name,
    escape_plantuml_table_cell,
    should_show_action,
    format_action_text,
    collect_event_transitions,
    assign_event_colors,
)

__all__ = [
    "AstExportable",
    "PlantUMLExportable",
    "Expr",
    "Integer",
    "Float",
    "Boolean",
    "Op",
    "UnaryOp",
    "BinaryOp",
    "ConditionalOp",
    "UFunc",
    "Variable",
    "parse_expr_node_to_expr",
    "parse_expr_from_string",
    "parse_expr",
    "OperationStatement",
    "Operation",
    "IfBlockBranch",
    "IfBlock",
    "Event",
    "Transition",
    "OnStage",
    "OnAspect",
    "State",
    "VarDefine",
    "StateMachine",
    "parse_dsl_node_to_state_machine",
    "DetailLevelLiteral",
    "PlantUMLOptionsInput",
    "PlantUMLOptions",
    "format_state_name",
    "format_event_name",
    "escape_plantuml_table_cell",
    "should_show_action",
    "format_action_text",
    "collect_event_transitions",
    "assign_event_colors",
    "load_state_machine_from_file",
    "load_state_machine_from_text",
]
