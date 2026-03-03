"""
Exportable interface definitions for AST and PlantUML representations.

This module defines lightweight abstract interfaces for model objects that can
be exported into two target formats used throughout the package:

* :class:`AstExportable` - Interface for objects that can be converted to
  :class:`pyfcstm.dsl.node.ASTNode` instances.
* :class:`PlantUMLExportable` - Interface for objects that can be rendered as
  PlantUML diagram syntax.

The interfaces are intentionally minimal and provide a clear contract for
implementations that participate in AST serialization or diagram generation.

Example::

    >>> from pyfcstm.model.base import AstExportable, PlantUMLExportable
    >>> class MyNode(AstExportable, PlantUMLExportable):
    ...     def to_ast_node(self):
    ...         from pyfcstm.dsl import node as dsl_nodes
    ...         return dsl_nodes.Name("example")
    ...
    ...     def to_plantuml(self):
    ...         return "state example"
    >>> node = MyNode()
    >>> str(node.to_ast_node())
    'example'
    >>> node.to_plantuml()
    'state example'

"""

from ..dsl import node as dsl_nodes


class AstExportable:
    """
    Abstract base class for objects that can be exported to AST nodes.

    Implementations should provide a concrete :meth:`to_ast_node` method that
    converts the object into a :class:`pyfcstm.dsl.node.ASTNode` instance.

    :raises NotImplementedError: If the subclass does not implement
        :meth:`to_ast_node`.
    """

    def to_ast_node(self) -> dsl_nodes.ASTNode:
        """
        Convert the object to an AST node representation.

        :return: An AST node representing this object.
        :rtype: pyfcstm.dsl.node.ASTNode
        :raises NotImplementedError: This method must be implemented by subclasses.

        Example::

            >>> class Example(AstExportable):
            ...     def to_ast_node(self):
            ...         from pyfcstm.dsl import node as dsl_nodes
            ...         return dsl_nodes.Name("example")
            >>> Example().to_ast_node()
            Name(name='example')

        """
        raise NotImplementedError  # pragma: no cover


class PlantUMLExportable:
    """
    Abstract base class for objects that can be exported to PlantUML format.

    Implementations should provide a concrete :meth:`to_plantuml` method that
    returns PlantUML diagram syntax as a string.

    :raises NotImplementedError: If the subclass does not implement
        :meth:`to_plantuml`.
    """

    def to_plantuml(self) -> str:
        """
        Convert the object to a PlantUML diagram representation.

        :return: A string containing PlantUML syntax representing this object.
        :rtype: str
        :raises NotImplementedError: This method must be implemented by subclasses.

        Example::

            >>> class Example(PlantUMLExportable):
            ...     def to_plantuml(self):
            ...         return "state example"
            >>> Example().to_plantuml()
            'state example'

        """
        raise NotImplementedError  # pragma: no cover
