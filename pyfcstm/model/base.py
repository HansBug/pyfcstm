"""
Module for defining exportable interfaces for AST and PlantUML formats.

This module provides abstract base classes that define interfaces for objects
that can be exported to Abstract Syntax Tree (AST) nodes or PlantUML diagram
representations.
"""

from ..dsl import node as dsl_nodes


class AstExportable:
    """
    Abstract base class for objects that can be exported to AST nodes.

    Classes that inherit from this interface should implement the to_ast_node
    method to convert themselves into appropriate AST node representations.

    :raises NotImplementedError: If the subclass does not implement the to_ast_node method.
    """

    def to_ast_node(self) -> dsl_nodes.ASTNode:
        """
        Convert the object to an AST node representation.

        :return: An AST node representing this object
        :rtype: dsl_nodes.ASTNode
        :raises NotImplementedError: This is an abstract method that must be implemented by subclasses
        """
        raise NotImplementedError  # pragma: no cover


class PlantUMLExportable:
    """
    Abstract base class for objects that can be exported to PlantUML format.

    Classes that inherit from this interface should implement the to_plantuml
    method to convert themselves into PlantUML diagram syntax.

    :raises NotImplementedError: If the subclass does not implement the to_plantuml method.
    """

    def to_plantuml(self) -> str:
        """
        Convert the object to a PlantUML diagram representation.

        :return: A string containing PlantUML syntax representing this object
        :rtype: str
        :raises NotImplementedError: This is an abstract method that must be implemented by subclasses
        """
        raise NotImplementedError  # pragma: no cover
