"""
JSON/YAML serialization utilities for persistent storage.

This module provides a lightweight interface for serializing and deserializing
objects to and from JSON and YAML formats. It defines a base class,
:class:`IJsonOp`, that supplies file I/O helpers and a consistent contract for
converting objects to JSON-serializable structures.

The module contains the following main components:

* :class:`IJsonOp` - Base interface for JSON/YAML serialization operations

Example::

    >>> class MyData(IJsonOp):
    ...     def __init__(self, data):
    ...         self.data = data
    ...
    ...     def _to_json(self):
    ...         return {"data": self.data}
    ...
    ...     @classmethod
    ...     def _from_json(cls, data):
    ...         return cls(data["data"])
    ...
    >>> obj = MyData([1, 2, 3])
    >>> obj.to_json("example.json")
    >>> loaded = MyData.read_json("example.json")
    >>> loaded.data
    [1, 2, 3]

.. note::
   The serialization logic is defined by subclasses via :meth:`_to_json` and
   :meth:`_from_json`. The base class only handles file I/O and validation.

"""

import json
from pprint import pformat
from typing import Any, Dict, Type, TypeVar

import yaml

T = TypeVar("T", bound="IJsonOp")


class IJsonOp:
    """
    An interface class that provides JSON serialization/deserialization capabilities.

    This class defines a common interface for objects that need to be serialized to
    and deserialized from JSON/YAML formats. Concrete classes must implement the
    :meth:`_to_json` and :meth:`_from_json` methods.

    Example::

        >>> class MyData(IJsonOp):
        ...     def __init__(self, data):
        ...         self.data = data
        ...
        ...     def _to_json(self):
        ...         return {"data": self.data}
        ...
        ...     @classmethod
        ...     def _from_json(cls, data):
        ...         return cls(data["data"])

    """

    def _to_json(self) -> Dict[str, Any]:
        """
        Convert the object to a JSON-serializable format.

        :return: JSON-serializable representation of the object
        :rtype: dict
        :raises NotImplementedError: This method must be implemented by concrete classes.
        """
        raise NotImplementedError

    @classmethod
    def _from_json(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Create an instance of the class from JSON-formatted data.

        :param data: The JSON data to deserialize
        :type data: dict
        :return: An instance constructed from the provided JSON data
        :rtype: IJsonOp
        :raises NotImplementedError: This method must be implemented by concrete classes.
        """
        raise NotImplementedError

    @property
    def json(self) -> Dict[str, Any]:
        """
        Get the JSON representation of the object.

        :return: JSON-serializable representation of the object
        :rtype: dict
        """
        return self._to_json()

    def to_json(self, json_file: str) -> None:
        """
        Save the object to a JSON file.

        :param json_file: Path to the output JSON file
        :type json_file: str
        """
        data = self._to_json()
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def to_yaml(self, yaml_file: str) -> None:
        """
        Save the object to a YAML file.

        :param yaml_file: Path to the output YAML file
        :type yaml_file: str
        """
        data = self._to_json()
        with open(yaml_file, 'w') as f:
            yaml.safe_dump(data, f)

    @classmethod
    def from_json(cls: Type[T], data: Dict[str, Any]) -> T:
        """
        Create an instance from JSON data.

        :param data: JSON-formatted data
        :type data: dict
        :return: An instance of the class
        :rtype: IJsonOp
        :raises TypeError: If the created object is not an instance of the class
        """
        obj = cls._from_json(data)
        if not isinstance(obj, cls):
            raise TypeError(f'{cls!r} type expected, but {type(obj)!r} found in data:\n'
                            f'{pformat(data)}')
        return obj

    @classmethod
    def read_json(cls: Type[T], json_file: str) -> T:
        """
        Create an instance by reading from a JSON file.

        :param json_file: Path to the input JSON file
        :type json_file: str
        :return: An instance of the class
        :rtype: IJsonOp
        """
        with open(json_file, 'r') as f:
            return cls.from_json(json.load(f))

    @classmethod
    def read_yaml(cls: Type[T], yaml_file: str) -> T:
        """
        Create an instance by reading from a YAML file.

        :param yaml_file: Path to the input YAML file
        :type yaml_file: str
        :return: An instance of the class
        :rtype: IJsonOp
        """
        with open(yaml_file, 'r') as f:
            return cls.from_json(yaml.safe_load(f))
