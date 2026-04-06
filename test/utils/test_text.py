import pytest

from pyfcstm.utils import (
    normalize,
    to_c_identifier,
    to_cpp_identifier,
    to_go_identifier,
    to_identifier,
    to_java_identifier,
    to_js_identifier,
    to_python_identifier,
    to_ruby_identifier,
    to_rust_identifier,
    to_ts_identifier,
)

_LANGUAGE_HELPERS = {
    'c': to_c_identifier,
    'cpp': to_cpp_identifier,
    'python': to_python_identifier,
    'java': to_java_identifier,
    'ruby': to_ruby_identifier,
    'ts': to_ts_identifier,
    'js': to_js_identifier,
    'rust': to_rust_identifier,
    'go': to_go_identifier,
}

_EXPLICIT_ESCAPE_KEYWORDS = {
    'c': [
        'auto', 'break', 'case', 'char', 'const', 'continue', 'default', 'do',
        'double', 'else', 'enum', 'extern', 'float', 'for', 'goto', 'if',
        'inline', 'int', 'long', 'register', 'restrict', 'return', 'short',
        'signed', 'sizeof', 'static', 'struct', 'switch', 'typedef', 'union',
        'unsigned', 'void', 'volatile', 'while', 'alignas', 'alignof', 'and',
        'bool', 'class', 'namespace', 'nullptr', 'operator', 'template',
        'thread_local', 'true', 'false',
    ],
    'python': [
        'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await',
        'break', 'class', 'continue', 'def', 'del', 'elif', 'else', 'except',
        'finally', 'for', 'from', 'global', 'if', 'import', 'in', 'is',
        'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try',
        'while', 'with', 'yield',
    ],
    'java': [
        'abstract', 'assert', 'boolean', 'break', 'byte', 'case', 'catch',
        'char', 'class', 'const', 'continue', 'default', 'do', 'double',
        'else', 'enum', 'extends', 'false', 'final', 'finally', 'float',
        'for', 'goto', 'if', 'implements', 'import', 'instanceof', 'int',
        'interface', 'long', 'module', 'native', 'new', 'null', 'package',
        'private', 'protected', 'public', 'record', 'requires', 'return',
        'sealed', 'static', 'super', 'switch', 'this', 'throw', 'throws',
        'true', 'try', 'void', 'volatile', 'while', 'yield',
    ],
    'ruby': [
        'BEGIN', 'END', 'alias', 'and', 'begin', 'break', 'case', 'class',
        'def', 'defined', 'do', 'else', 'elsif', 'end', 'ensure', 'false',
        'for', 'if', 'in', 'module', 'next', 'nil', 'not', 'or', 'redo',
        'rescue', 'retry', 'return', 'self', 'super', 'then', 'true', 'undef',
        'unless', 'until', 'when', 'while', 'yield', 'begin', 'end', 'module',
    ],
    'ts': [
        'abstract', 'any', 'as', 'asserts', 'await', 'bigint', 'boolean',
        'break', 'case', 'catch', 'class', 'const', 'constructor', 'continue',
        'declare', 'default', 'delete', 'do', 'else', 'enum', 'export',
        'extends', 'false', 'finally', 'for', 'from', 'function', 'get',
        'global', 'if', 'implements', 'import', 'in', 'infer', 'interface',
        'is', 'keyof', 'let', 'module', 'namespace', 'never', 'new', 'null',
        'number', 'object', 'override', 'private', 'protected', 'public',
        'readonly', 'require', 'return', 'set', 'static', 'string', 'super',
        'symbol', 'this', 'throw', 'true', 'try', 'type', 'typeof', 'unique',
        'unknown', 'using', 'var', 'void', 'while',
    ],
    'js': [
        'await', 'break', 'case', 'catch', 'class', 'const', 'continue',
        'debugger', 'default', 'delete', 'do', 'else', 'enum', 'export',
        'extends', 'false', 'finally', 'for', 'function', 'if', 'implements',
        'import', 'in', 'instanceof', 'interface', 'let', 'new', 'null',
        'package', 'private', 'protected', 'public', 'return', 'static',
        'super', 'switch', 'this', 'throw', 'true', 'try', 'typeof', 'var',
        'void', 'while', 'with', 'yield',
    ],
    'rust': [
        'Self', 'abstract', 'as', 'async', 'await', 'become', 'box', 'break',
        'const', 'continue', 'crate', 'do', 'dyn', 'else', 'enum', 'extern',
        'false', 'final', 'fn', 'for', 'if', 'impl', 'in', 'let', 'loop',
        'macro', 'match', 'mod', 'move', 'mut', 'override', 'priv', 'pub',
        'ref', 'return', 'self', 'static', 'struct', 'super', 'trait', 'true',
        'try', 'type', 'typeof', 'union', 'unsafe', 'unsized', 'use',
        'virtual', 'where', 'while', 'yield',
    ],
    'go': [
        'break', 'case', 'chan', 'const', 'continue', 'default', 'defer',
        'else', 'fallthrough', 'for', 'func', 'go', 'goto', 'if', 'import',
        'interface', 'map', 'package', 'range', 'return', 'select', 'struct',
        'switch', 'type', 'var',
    ],
}

_EXPLICIT_ESCAPE_KEYWORDS['cpp'] = list(_EXPLICIT_ESCAPE_KEYWORDS['c'])

_ESCAPE_VARIANT_SUFFIXES = ['!', '?', '-', '+++', '@@@', '   ']


def _build_keyword_escape_cases(language: str, minimum_count: int = 40):
    keywords = list(_EXPLICIT_ESCAPE_KEYWORDS[language])
    cases = [(keyword, keyword + '_') for keyword in keywords]

    if len(cases) >= minimum_count:
        return cases[:minimum_count]

    index = 0
    while len(cases) < minimum_count:
        keyword = keywords[index % len(keywords)]
        suffix = _ESCAPE_VARIANT_SUFFIXES[(index // len(keywords)) % len(_ESCAPE_VARIANT_SUFFIXES)]
        cases.append((keyword + suffix, keyword + '_'))
        index += 1

    return cases
_BULK_ESCAPE_CASES = {
    language: _build_keyword_escape_cases(language)
    for language in _LANGUAGE_HELPERS
}

_DIVERSE_SAFE_CASES = [
    ('Alpha Beta 01', 'Alpha_Beta_01'),
    ('HTTP Server#2', 'HTTP_Server_2'),
    ('snake-case+mix', 'snake_case_mix'),
    ('Camel Case / Path', 'Camel_Case_Path'),
    ('MAX value%', 'MAX_value'),
    ('delta.signal@node', 'delta_signal_node'),
    ('Привет Мир 5', 'Privet_Mir_5'),
    ('数据-Bridge 8', 'Shu_Ju_Bridge_8'),
    ('東京 Tower 3', 'Dong_Jing_Tower_3'),
    ('안녕-Route 9', 'annyeong_Route_9'),
    ('Noble\tVector\nLane', 'Noble_Vector_Lane'),
    ('GraphQL Resolver 7', 'GraphQL_Resolver_7'),
    ('user/profile:url', 'user_profile_url'),
    ('Space-Time Continuum', 'Space_Time_Continuum'),
    ('Version(Next) Build', 'Version_Next_Build'),
    ('München Straße 4', 'Munchen_Strasse_4'),
    ('façade+naïve=combo', 'facade_naive_combo'),
    ('Señor Árbol Ruta', 'Senor_Arbol_Ruta'),
    ('crème brûlée set', 'creme_brulee_set'),
    ('smile🙂signal', 'smilesignal'),
    ('data&analytics*hub', 'data_analytics_hub'),
    ('North-West Gateway', 'North_West_Gateway'),
    ('sensor[alpha]beta', 'sensor_alpha_beta'),
    ('queue{main}<fast>', 'queue_main_fast'),
    ('lambda=>stream/path', 'lambda_stream_path'),
    ('orbit.matrix::sync', 'orbit_matrix_sync'),
    ('peak^value|check', 'peak_value_check'),
    ('line\\break//join', 'line_break_join'),
    ('price$delta€zone', 'price_deltaEURzone'),
    ('مرحبا Signal Hub', 'mrHb_Signal_Hub'),
    ('γειά σου Node', 'geia_sou_Node'),
    ('नमस्ते Bridge Link', 'nmste_Bridge_Link'),
    ('שלום Query Port', 'SHlvm_Query_Port'),
    ('Xin chào Harbor', 'Xin_chao_Harbor'),
    ('Olá Mundo Canal', 'Ola_Mundo_Canal'),
    ('Bonjour Réseau Flux', 'Bonjour_Reseau_Flux'),
    ('Cześć Trasa Punkt', 'Czesc_Trasa_Punkt'),
    ('Hej Värld Sluss', 'Hej_Varld_Sluss'),
    ('Ahoj Stanice Proud', 'Ahoj_Stanice_Proud'),
    ('Merhaba Ağ Geçidi', 'Merhaba_Ag_Gecidi'),
    ('Pipeline--Stage__A', 'Pipeline_Stage_A'),
    ('XMLHttp Request Mode', 'XMLHttp_Request_Mode'),
    ('GPU/CPU Balance', 'GPU_CPU_Balance'),
    ('IoT Edge Device', 'IoT_Edge_Device'),
    ('Beta+Gamma=Omega', 'Beta_Gamma_Omega'),
    ('Ready?Set!Go!', 'Ready_Set_Go'),
    ('File.Name.With.Dots', 'File_Name_With_Dots'),
    ('UpperCASE_and-mixed', 'UpperCASE_and_mixed'),
    ('OneMore测试Case', 'OneMoreCe_Shi_Case'),
    ('Signal_日本_Line', 'Signal_Ri_Ben_Line'),
]

_BULK_SAFE_CASES = {
    language: list(_DIVERSE_SAFE_CASES)
    for language in _LANGUAGE_HELPERS
}

_BULK_TO_IDENTIFIER_ESCAPE_CASES = [
    (language, input_string, expected)
    for language, cases in _BULK_ESCAPE_CASES.items()
    for input_string, expected in cases
]

_BULK_TO_IDENTIFIER_SAFE_CASES = [
    (language, input_string, expected)
    for language, cases in _BULK_SAFE_CASES.items()
    for input_string, expected in cases
]

_BULK_NORMALIZE_ESCAPE_CASES = list(_BULK_TO_IDENTIFIER_ESCAPE_CASES)

_BULK_NORMALIZE_SAFE_CASES = list(_BULK_TO_IDENTIFIER_SAFE_CASES)

_BULK_HELPER_ESCAPE_CASES = [
    (language, input_string, expected)
    for language, cases in _BULK_ESCAPE_CASES.items()
    for input_string, expected in cases
]

_BULK_HELPER_SAFE_CASES = [
    (language, input_string, expected)
    for language, cases in _BULK_SAFE_CASES.items()
    for input_string, expected in cases
]


@pytest.mark.unittest
class TestIdentifierConversion:
    def test_keyword_case_inventory(self):
        for language, cases in _BULK_ESCAPE_CASES.items():
            assert len(cases) >= 40, language

        for language, cases in _BULK_SAFE_CASES.items():
            assert len(cases) >= 50, language

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
        "input_string, keyword_safe_for, expected",
        [
            ("class", ["python"], "class_"),
            ("Class", ["python"], "Class"),
            ("namespace", ["cpp"], "namespace_"),
            ("interface", ["js"], "interface_"),
            ("type", ["ts"], "type_"),
            ("record", ["java"], "record_"),
            ("module", ["ruby"], "module_"),
            ("match", ["rust"], "match_"),
            ("func", ["go"], "func_"),
            ("class", ["python", "java"], "class_"),
            ("123 class", ["python"], "123_class"),
            ("", ["python"], ""),
        ],
    )
    def test_normalize_with_keyword_safety(self, input_string, keyword_safe_for, expected):
        assert normalize(input_string, keyword_safe_for=keyword_safe_for) == expected

    @pytest.mark.parametrize(
        "language, input_string, expected",
        _BULK_NORMALIZE_ESCAPE_CASES,
    )
    def test_normalize_bulk_keyword_escape_cases(self, language, input_string, expected):
        assert normalize(input_string, keyword_safe_for=[language]) == expected

    @pytest.mark.parametrize(
        "language, input_string, expected",
        _BULK_NORMALIZE_SAFE_CASES,
    )
    def test_normalize_bulk_keyword_safe_cases(self, language, input_string, expected):
        assert normalize(input_string, keyword_safe_for=[language]) == expected

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

    @pytest.mark.parametrize(
        "input_string, strict_mode, keyword_safe_for, expected",
        [
            ("class", True, ["python"], "class_"),
            ("Class", True, ["python"], "Class"),
            ("Class", True, ["c"], "Class_"),
            ("namespace", True, ["cpp"], "namespace_"),
            ("interface", True, ["js"], "interface_"),
            ("type", True, ["ts"], "type_"),
            ("record", True, ["java"], "record_"),
            ("module", True, ["ruby"], "module_"),
            ("match", True, ["rust"], "match_"),
            ("func", True, ["go"], "func_"),
            ("class", True, ["python", "java"], "class_"),
            ("class", True, ["c", "cpp"], "class_"),
            ("123_abc", True, ["python"], "_123_abc"),
            ("", True, ["python"], "_empty"),
        ],
    )
    def test_to_identifier_with_keyword_safety(self, input_string, strict_mode, keyword_safe_for, expected):
        assert to_identifier(input_string, strict_mode, keyword_safe_for=keyword_safe_for) == expected

    @pytest.mark.parametrize(
        "language, input_string, expected",
        _BULK_TO_IDENTIFIER_ESCAPE_CASES,
    )
    def test_to_identifier_bulk_keyword_escape_cases(self, language, input_string, expected):
        assert to_identifier(input_string, keyword_safe_for=[language]) == expected

    @pytest.mark.parametrize(
        "language, input_string, expected",
        _BULK_TO_IDENTIFIER_SAFE_CASES,
    )
    def test_to_identifier_bulk_keyword_safe_cases(self, language, input_string, expected):
        assert to_identifier(input_string, keyword_safe_for=[language]) == expected

    def test_consecutive_special_chars(self):
        assert to_identifier("a!!b@@c##d") == "a_b_c_d"

    def test_trailing_underscore_removal(self):
        assert to_identifier("hello_world_") == "hello_world"

    def test_to_identifier_rejects_unknown_keyword_language(self):
        with pytest.raises(ValueError, match='Unsupported identifier keyword-safe language'):
            to_identifier("hello", keyword_safe_for=['unknown'])

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

    @pytest.mark.parametrize(
        "func, input_string, expected",
        [
            (to_cpp_identifier, "namespace", "namespace_"),
            (to_python_identifier, "class", "class_"),
            (to_java_identifier, "record", "record_"),
            (to_ruby_identifier, "module", "module_"),
            (to_ts_identifier, "type", "type_"),
            (to_js_identifier, "interface", "interface_"),
            (to_rust_identifier, "match", "match_"),
            (to_go_identifier, "func", "func_"),
        ],
    )
    def test_language_specific_identifier_helpers(self, func, input_string, expected):
        assert func(input_string) == expected

    @pytest.mark.parametrize(
        "language, input_string, expected",
        _BULK_HELPER_ESCAPE_CASES,
    )
    def test_language_specific_identifier_helpers_bulk_escape_cases(self, language, input_string, expected):
        assert _LANGUAGE_HELPERS[language](input_string) == expected

    @pytest.mark.parametrize(
        "language, input_string, expected",
        _BULK_HELPER_SAFE_CASES,
    )
    def test_language_specific_identifier_helpers_bulk_safe_cases(self, language, input_string, expected):
        assert _LANGUAGE_HELPERS[language](input_string) == expected
