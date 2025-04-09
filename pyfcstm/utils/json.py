import json
from pprint import pformat

import yaml


class IJsonOp:
    def _to_json(self):
        raise NotImplementedError

    @classmethod
    def _from_json(cls, data):
        raise NotImplementedError

    @property
    def json(self):
        return self._to_json()

    def to_json(self, json_file):
        data = self._to_json()
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    def to_yaml(self, yaml_file):
        data = self._to_json()
        with open(yaml_file, 'w') as f:
            yaml.safe_dump(data, f)

    @classmethod
    def from_json(cls, data):
        obj = cls._from_json(data)
        if not isinstance(obj, cls):
            raise TypeError(f'{cls!r} type expected, but {type(obj)!r} found in data:\n'
                            f'{pformat(data)}')
        return obj

    @classmethod
    def read_json(cls, json_file):
        with open(json_file, 'r') as f:
            return cls.from_json(json.load(f))

    @classmethod
    def read_yaml(cls, yaml_file):
        with open(yaml_file, 'r') as f:
            return cls.from_json(yaml.safe_load(f))
