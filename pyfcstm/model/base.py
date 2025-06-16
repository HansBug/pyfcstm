from ..dsl import node as dsl_nodes


class AstExportable:
    def to_ast_node(self) -> dsl_nodes.ASTNode:
        raise NotImplementedError  # pragma: no cover


class PlantUMLExportable:
    def to_plantuml(self) -> str:
        raise NotImplementedError  # pragma: no cover
