import pytest

from pyfcstm.utils import normalize, to_c_identifier, to_identifier


@pytest.mark.unittest
class TestIdentifierConversion:
    @pytest.mark.parametrize(
        "input_string, expected",
        [
            ("Hello World", "Hello_World"),
            ("123_abc", "123_abc"),
            ("!@#$%^&*()_+", ""),
            ("中文测试", "Zhong_Wen_Ce_Shi"),
            ("こんにちは", "konnichiha"),
            ("안녕하세요", "annyeonghaseyo"),
            ("Привет", "Privet"),
            ("", ""),
            # (None, ""),
        ],
    )
    def test_normalize(self, input_string, expected):
        assert normalize(input_string) == expected

    @pytest.mark.parametrize(
        "input_string, strict_mode, expected",
        [
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
        ],
    )
    def test_to_identifier(self, input_string, strict_mode, expected):
        assert to_identifier(input_string, strict_mode) == expected

    def test_consecutive_special_chars(self):
        assert to_identifier("a!!b@@c##d") == "a_b_c_d"

    def test_trailing_underscore_removal(self):
        assert to_identifier("hello_world_") == "hello_world"

    @pytest.mark.parametrize(
        "input_string, strict_mode, expected",
        [
            ("Hello World", True, "Hello_World"),
            ("hello_world", True, "hello_world"),
            ("class", True, "class_"),
            ("Class", True, "Class_"),
            ("template", True, "template_"),
            ("Template", True, "Template_"),
            ("namespace", True, "namespace_"),
            ("compl", True, "compl_"),
            ("xor_eq", True, "xor_eq_"),
            ("thread_local", True, "thread_local_"),
            ("noexcept", True, "noexcept_"),
            ("alignas", True, "alignas_"),
            ("static_assert", True, "static_assert_"),
            ("operator", True, "operator_"),
            ("union", True, "union_"),
            ("volatile", True, "volatile_"),
            ("auto", True, "auto_"),
            ("bool", True, "bool_"),
            ("true", True, "true_"),
            ("false", True, "false_"),
            ("nullptr", True, "nullptr_"),
            ("requires", True, "requires_"),
            ("concept", True, "concept_"),
            ("and", True, "and_"),
            ("or", True, "or_"),
            ("not", True, "not_"),
            ("bitor", True, "bitor_"),
            ("char32_t", True, "char32_t_"),
            ("wchar_t", True, "wchar_t_"),
            ("_Atomic", True, "_Atomic_"),
            ("_Thread_local", True, "_Thread_local_"),
            ("123_abc", True, "_123_abc"),
            ("!@#$%^&*()_+", True, "_empty"),
            ("namespace_", True, "namespace_"),
            ("class-name", True, "class_name"),
            ("friend class", True, "friend_class"),
            ("中文 class", True, "Zhong_Wen_class"),
            ("Hello World", False, "Hello_World"),
            ("hello_world", False, "hello_world"),
            ("class", False, "class_"),
            ("Class", False, "Class_"),
            ("template", False, "template_"),
            ("Template", False, "Template_"),
            ("namespace", False, "namespace_"),
            ("compl", False, "compl_"),
            ("xor_eq", False, "xor_eq_"),
            ("thread_local", False, "thread_local_"),
            ("noexcept", False, "noexcept_"),
            ("alignas", False, "alignas_"),
            ("static_assert", False, "static_assert_"),
            ("operator", False, "operator_"),
            ("union", False, "union_"),
            ("volatile", False, "volatile_"),
            ("auto", False, "auto_"),
            ("bool", False, "bool_"),
            ("true", False, "true_"),
            ("false", False, "false_"),
            ("nullptr", False, "nullptr_"),
            ("requires", False, "requires_"),
            ("concept", False, "concept_"),
            ("and", False, "and_"),
            ("or", False, "or_"),
            ("not", False, "not_"),
            ("bitor", False, "bitor_"),
            ("char32_t", False, "char32_t_"),
            ("wchar_t", False, "wchar_t_"),
            ("_Atomic", False, "_Atomic_"),
            ("_Thread_local", False, "_Thread_local_"),
            ("123_abc", False, "123_abc"),
            ("!@#$%^&*()_+", False, ""),
            ("namespace_", False, "namespace_"),
            ("class-name", False, "class_name"),
            ("friend class", False, "friend_class"),
            ("中文 class", False, "Zhong_Wen_class"),
        ],
    )
    def test_to_c_identifier(self, input_string, strict_mode, expected):
        assert to_c_identifier(input_string, strict_mode) == expected

    def test_to_c_identifier_leaves_non_reserved_names_unchanged(self):
        assert to_c_identifier("hello_world") == "hello_world"

    def test_to_c_identifier_applies_reserved_check_after_normalization(self):
        assert to_c_identifier("namespace_") == "namespace_"
