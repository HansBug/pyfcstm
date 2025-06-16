from dataclasses import dataclass

from ..dsl import node as dsl_nodes


@dataclass
class AstExportable:
    def to_ast_node(self) -> dsl_nodes.ASTNode:
        raise NotImplementedError  # pragma: no cover
