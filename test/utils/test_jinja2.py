import pytest
from jinja2 import Environment

from pyfcstm.utils import add_builtins_to_env, add_settings_for_env


@pytest.fixture
def base_env():
    return Environment()


@pytest.fixture
def env_with_builtins(base_env):
    return add_builtins_to_env(base_env)


@pytest.fixture
def env_with_settings(base_env):
    return add_settings_for_env(base_env)


@pytest.mark.unittest
class TestJinjaEnvironmentEnhancement:

    @pytest.mark.parametrize("template_str, extra_params, expected_str", [
        ("{{ len('hello') }}", {}, "5"),  # Test len() as filter
        ("{{ 'hello'|upper }}", {}, "HELLO"),  # Test existing Jinja2 filter
        ("{% if 'hello' is string %}yes{% else %}no{% endif %}", {}, "yes"),  # Test 'is string' test
        ("{{ range(3)|list }}", {}, "[0, 1, 2]"),  # Test range() and list() as filters
        ("{{ [1, 2, 3]|sum }}", {}, "6"),  # Test sum() as filter
        ("{{ {'a': 1, 'b': 2}|dict }}", {}, "{'a': 1, 'b': 2}"),  # Test dict() as filter
        ("{{ 'hello'|list }}", {}, "['h', 'e', 'l', 'l', 'o']"),  # Test list() on string
        ("{% if 42 is number %}yes{% else %}no{% endif %}", {}, "yes"),  # Test 'is number' test
        ("{{ abs(-5) }}", {}, "5"),  # Test abs() as global function
        ("{{ max(1, 2, 3) }}", {}, "3"),  # Test max() as global function
        ("{{ min(1, 2, 3) }}", {}, "1"),  # Test min() as global function
        ("{{ 'hello'|capitalize }}", {}, "Hello"),  # Test capitalize() as filter
        ("{% if none is none %}yes{% else %}no{% endif %}", {}, "yes"),  # Test 'is none' test
        ("{{ [1, 2, 3]|reversed|list }}", {}, "[3, 2, 1]"),  # Test reversed() as filter
        ("{{ {'a': 1, 'b': 2}|items|list }}", {}, "[('a', 1), ('b', 2)]"),  # Test items() as filter
        ("{{ 'hello'|enumerate|list }}", {}, "[(0, 'h'), (1, 'e'), (2, 'l'), (3, 'l'), (4, 'o')]"),
        # Test enumerate() as filter
        ("{% if 'hello' is callable %}yes{% else %}no{% endif %}", {}, "no"),  # Test 'is callable' test
        ("{{ [1, 2, 3]|map('str')|list }}", {}, "['1', '2', '3']"),  # Test map() as filter
        ("{{ [1, 2, 3]|filter(odd)|list }}", {'odd': lambda x: x % 2 == 1}, "[1, 3]"),  # Test filter() as filter
        ("{{ zip([1, 2], ['a', 'b'])|list }}", {}, "[(1, 'a'), (2, 'b')]"),  # Test zip() as filter
        ("{{ {'a': 1, 'b': 2}|sorted }}", {}, "['a', 'b']"),  # Test sorted() as filter
        ("{{ 'hello'|set|list|sort }}", {}, "['e', 'h', 'l', 'o']"),  # Test set() and sort() as filters
        ("{% if [1, 2] is iterable %}yes{% else %}no{% endif %}", {}, "yes"),  # Test 'is iterable' test
        # ("{{ 'hello'|slice(1, 4)|list }}", {}, "ell"),  # Test slice() as filter
        # ("{{ 'hello'|list|random }}", {"seed": 42}, "l"),  # Test random() as filter with seed
        # ("{{ 'hello'|list|shuffle|join }}", {"seed": 42}, "lhloe"),  # Test shuffle() as filter with seed
        ("{{ [1, 2, 3]|any }}", {}, "True"),  # Test any() as filter
        ("{{ [0, False, '']|all }}", {}, "False"),  # Test all() as filter
        ("{{ [1, 2, 3]|sum }}", {}, "6"),  # Test sum() as filter
        ("{{ 5|round(2) }}", {}, "5"),  # Test round() as filter
        ("{{ 3.14159|round(2) }}", {}, "3.14"),  # Test round() with precision
        ("{{ 'hello'[0]|ord|chr }}", {}, "h"),  # Test ord() and chr() as filters
        ("{{ 42|hex }}", {}, "0x2a"),  # Test hex() as filter
        ("{{ 42|bin }}", {}, "0b101010"),  # Test bin() as filter
        ("{{ 42|oct }}", {}, "0o52"),  # Test oct() as filter
        ("{{ 'hello'|repr }}", {}, "'hello'"),  # Test repr() as filter
        ("{{ [1, 2, 3]|reversed|list }}", {}, "[3, 2, 1]"),  # Test reversed() as filter
        ("{{ range(5)|list }}", {}, "[0, 1, 2, 3, 4]"),  # Test range() as filter
        ("{{ {'a': 1, 'b': 2}|dict|keys|list|sort }}", {}, "['a', 'b']"),  # Test dict(), keys(), and sort() as filters
        ("{{ 'hello'|list|set|list|sort }}", {}, "['e', 'h', 'l', 'o']"),  # Test list(), set(), and sort() as filters
        ("{% if 42 is instance(int) %}yes{% else %}no{% endif %}", {}, "yes"),  # Test 'is instance' test
        ("{% if int is subclass(object) %}yes{% else %}no{% endif %}", {}, "yes"),  # Test 'is subclass' test
        ("{{ 'hello'|getattr('upper')() }}", {}, "HELLO"),  # Test getattr() as filter
        ("{{ [1, 2, 3]|map('str')|join('-') }}", {}, "1-2-3"),  # Test map() and join() as filters
        ("{{ 'hello'|list|enumerate|list }}", {}, "[(0, 'h'), (1, 'e'), (2, 'l'), (3, 'l'), (4, 'o')]"),
        # Test enumerate() as filter
        ("{{ [1, 2, 3]|map('pow', 2)|list }}", {}, "[1, 4, 9]"),  # Test map() with multiple arguments
        # ("{{ [1, 2, 3]|reduce('lambda x, y: x * y') }}", {}, "6"),  # Test reduce() as filter
        # ("{{ 'hello'|slice(None, None, -1) }}", {}, "olleh"),  # Test slice() with step
        ("{{ [1, 2, 3]|map('str')|map('len')|sum }}", {}, "3"),  # Test chaining multiple map() calls
    ])
    def test_env_with_builtins(self, env_with_builtins, template_str, extra_params, expected_str):
        template = env_with_builtins.from_string(template_str)
        result = template.render(**extra_params)
        assert result == expected_str

    @pytest.mark.parametrize("template_str, extra_params, expected_str", [
        ("{{ 'Hello World'|normalize }}", {}, "Hello_World"),  # Test normalize filter
        ("{{ 'Hello World'|to_identifier }}", {}, "Hello_World"),  # Test to_identifier filter
        ("{{ indent('Hello\\nWorld', '  ') }}", {}, "  Hello\n  World"),  # Test indent global function
        ("{{ PATH }}", {"PATH": "/usr/bin"}, "/usr/bin"),  # Test environment variable as global
        ("{{ 'Hello World'|normalize|upper }}", {}, "HELLO_WORLD"),  # Test normalize and upper filters
        ("{{ 'Hello123'|to_identifier }}", {}, "Hello123"),  # Test to_identifier with numbers
        ("{{ indent('Line1\\nLine2\\nLine3', '> ') }}", {}, "> Line1\n> Line2\n> Line3"),
        # Test indent with multiple lines
        ("{{ HOME }}", {"HOME": "/home/user"}, "/home/user"),  # Test another environment variable
        ("{{ 'Mixed Case'|normalize|to_identifier }}", {}, "Mixed_Case"),  # Test normalize and to_identifier together
        ("{{ indent('Single', '* ') }}", {}, "* Single"),  # Test indent with single line
    ])
    def test_env_with_settings(self, env_with_settings, template_str, extra_params, expected_str):
        template = env_with_settings.from_string(template_str)
        result = template.render(**extra_params)
        assert result == expected_str
