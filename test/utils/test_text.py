import pytest

from pyfcstm.utils import normalize, to_identifier


@pytest.mark.unittest
class TestIdentifierConversion:
    @pytest.mark.parametrize("input_string, expected", [
        ("Hello World", "Hello_World"),
        ("123_abc", "123_abc"),
        ("!@#$%^&*()_+", ""),
        ("中文测试", "Zhong_Wen_Ce_Shi"),
        ("こんにちは", "konnichiha"),
        ("안녕하세요", "annyeonghaseyo"),
        ("Привет", "Privet"),
        ("", ""),
        # (None, ""),
    ])
    def test_normalize(self, input_string, expected):
        assert normalize(input_string) == expected

    @pytest.mark.parametrize("input_string, strict_mode, expected", [
        ("Hello World", True, "Hello_World"),
        ("123_abc", True, "_123_abc"),
        ("!@#$%^&*()_+", True, "_empty"),
        ("中文测试", True, "Zhong_Wen_Ce_Shi"),
        ("こんにちは", True, "konnichiha"),
        ("안녕하세요", True, "annyeonghaseyo"),
        ("Привет", True, "Privet"),
        ("", True, "_empty"),
        # (None, True, "_empty"),
        ("Hello World", False, "Hello_World"),
        ("123_abc", False, "123_abc"),
        ("!@#$%^&*()_+", False, ""),
        ("中文测试", False, "Zhong_Wen_Ce_Shi"),
        ("こんにちは", False, "konnichiha"),
        ("안녕하세요", False, "annyeonghaseyo"),
        ("Привет", False, "Privet"),
        ("", False, ""),
        # (None, False, ""),
    ])
    def test_to_identifier(self, input_string, strict_mode, expected):
        assert to_identifier(input_string, strict_mode) == expected

    def test_consecutive_special_chars(self):
        assert to_identifier("a!!b@@c##d") == "a_b_c_d"

    def test_trailing_underscore_removal(self):
        assert to_identifier("hello_world_") == "hello_world"
