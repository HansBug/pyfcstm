import json
import os
import tempfile
from unittest.mock import patch, mock_open

import pytest
import yaml

from pyfcstm.utils import IJsonOp


@pytest.fixture
def mock_json_data():
    return {"key": "value"}


@pytest.fixture
def temp_file():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        yield tmp.name
    os.unlink(tmp.name)


@pytest.mark.unittest
class TestIJsonOp:
    def test_to_json_not_implemented(self):
        class TestClass(IJsonOp):
            pass

        with pytest.raises(NotImplementedError):
            TestClass()._to_json()

    def test_from_json_not_implemented(self):
        class TestClass(IJsonOp):
            pass

        with pytest.raises(NotImplementedError):
            TestClass._from_json({})

    def test_json_property(self):
        class TestClass(IJsonOp):
            def _to_json(self):
                return {"test": "data"}

        assert TestClass().json == {"test": "data"}

    def test_to_json(self, temp_file, mock_json_data):
        class TestClass(IJsonOp):
            def _to_json(self):
                return mock_json_data

        TestClass().to_json(temp_file)
        with open(temp_file, "r") as f:
            assert json.load(f) == mock_json_data

    def test_to_yaml(self, temp_file, mock_json_data):
        class TestClass(IJsonOp):
            def _to_json(self):
                return mock_json_data

        TestClass().to_yaml(temp_file)
        with open(temp_file, "r") as f:
            assert yaml.safe_load(f) == mock_json_data

    def test_from_json_success(self):
        class TestClass(IJsonOp):
            @classmethod
            def _from_json(cls, data):
                return cls()

        assert isinstance(TestClass.from_json({}), TestClass)

    def test_from_json_type_error(self):
        class TestClass(IJsonOp):
            @classmethod
            def _from_json(cls, data):
                return "not a TestClass instance"

        with pytest.raises(TypeError):
            TestClass.from_json({})

    def test_read_json(self, mock_json_data):
        class TestClass(IJsonOp):
            @classmethod
            def _from_json(cls, data):
                return cls()

        with patch("builtins.open", mock_open(read_data=json.dumps(mock_json_data))):
            assert isinstance(TestClass.read_json("fake_file.json"), TestClass)

    def test_read_yaml(self, mock_json_data):
        class TestClass(IJsonOp):
            @classmethod
            def _from_json(cls, data):
                return cls()

        with patch("builtins.open", mock_open(read_data=yaml.dump(mock_json_data))):
            assert isinstance(TestClass.read_yaml("fake_file.yaml"), TestClass)
