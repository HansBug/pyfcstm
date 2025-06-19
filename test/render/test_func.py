import jinja2
import pytest
from hbutils.reflection import quick_import_object

from pyfcstm.render.func import process_item_to_object


@pytest.fixture
def env():
    return jinja2.Environment()


@pytest.mark.unittest
class TestProcessItemToObject:
    def test_dict_template_with_params(self, env):
        f = {'type': 'template', 'params': ['a', 'b'], 'template': '{{ a }} + {{ b }}'}
        result = process_item_to_object(f, env)
        assert result(1, 2) == '1 + 2'
        assert result(3, 4, c=5) == '3 + 4'
        assert result(3, b=5) == '3 + 5'

    def test_dict_template_without_params(self, env):
        f = {'type': 'template', 'template': '{{ a }} + {{ b }}'}
        result = process_item_to_object(f, env)
        assert result(a=1, b=2) == '1 + 2'

    def test_dict_import(self, env):
        f = {'type': 'import', 'from': 'hbutils.reflection.quick_import_object'}
        result = process_item_to_object(f, env)
        assert result is quick_import_object

    def test_dict_value(self, env):
        f = {'type': 'value', 'value': 42}
        result = process_item_to_object(f, env)
        assert result == 42

    def test_dict_unknown_type(self, env):
        f = {'type': 'unknown', 'key': 'value'}
        result = process_item_to_object(f, env)
        assert result == {'key': 'value'}

    def test_non_dict(self, env):
        f = "not a dict"
        result = process_item_to_object(f, env)
        assert result == "not a dict"

    def test_dict_no_type(self, env):
        f = {'key': 'value'}
        result = process_item_to_object(f, env)
        assert result == {'key': 'value'}
