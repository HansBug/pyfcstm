"""
This module provides a base interface for JSON serialization and deserialization operations.
It defines an abstract base class IJsonOp that implements common JSON/YAML file I/O operations
and requires concrete classes to implement the actual serialization logic.

The module supports both JSON and YAML formats for data persistence, with methods for reading
from and writing to files in either format.
"""

import json
from pprint import pformat

import yaml


class IJsonOp:
    """
    An interface class that provides JSON serialization/deserialization capabilities.

    This class defines a common interface for objects that need to be serialized to
    and deserialized from JSON/YAML formats. Concrete classes must implement the
    _to_json() and _from_json() methods.

    Example:
        >>> class MyData(IJsonOp):
        ...     def _to_json(self):
        ...         return {"data": self.data}
        ...
        ...     @classmethod
        ...     def _from_json(cls, data):
        ...         return cls(data["data"])
    """

    def _to_json(self):
        """
        Convert the object to a JSON-serializable format.

        :raises NotImplementedError: This method must be implemented by concrete classes.
        """
        raise NotImplementedError

    @classmethod
    def _from_json(cls, data):
        """
        Create an instance of the class from JSON-formatted data.

        :param data: The JSON data to deserialize
        :raises NotImplementedError: This method must be implemented by concrete classes.
        """
        raise NotImplementedError

    @property
    def json(self):
        """
        Get the JSON representation of the object.

        :return: JSON-serializable representation of the object
        :rtype: dict
        """
        return self._to_json()

    def to_json(self, json_file):
        """
        Save the object to a JSON file.

        :param json_file: Path to the output JSON file
        :type json_file: str
        """
        data = self._to_json()
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def to_yaml(self, yaml_file):
        """
        Save the object to a YAML file.

        :param yaml_file: Path to the output YAML file
        :type yaml_file: str
        """
        data = self._to_json()
        with open(yaml_file, 'w') as f:
            yaml.safe_dump(data, f)

    @classmethod
    def from_json(cls, data):
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
    def read_json(cls, json_file):
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
    def read_yaml(cls, yaml_file):
        """
        Create an instance by reading from a YAML file.

        :param yaml_file: Path to the input YAML file
        :type yaml_file: str
        :return: An instance of the class
        :rtype: IJsonOp
        """
        with open(yaml_file, 'r') as f:
            return cls.from_json(yaml.safe_load(f))
