from pathlib import Path

import pytest

from pyfcstm.highlight import FcstmLexer

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SAMPLE_CODE_DIR = _REPO_ROOT / 'test' / 'testfile' / 'sample_codes'
_LANGCHECK_HACK_CASES = [
    (
        'C-1 Block Comment (1.00)',
        'c',
        '/*\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n*/\nint main(void) { return 0; }\n',
    ),
    (
        'C-2 Line Comment (1.00)',
        'c',
        '//\n//[*]\n//state S {\n//def int x = 1;\n//enter {}\n//}\n//>> enter\n//a::b\n//a -> b\n//! -> c\n//pseudo named abstract ref effect\nint main(void) { return 0; }\n',
    ),
    (
        'C-3 String Literal (1.00)',
        'c',
        'static const char *bait =\n    "[*]\\n"\n    "state S {\\n"\n    "def int x = 1;\\n"\n    "enter {}\\n"\n    "}\\n"\n    ">> enter\\n"\n    "a::b\\n"\n    "a -> b\\n"\n    "! -> c\\n"\n    "pseudo named abstract ref effect\\n";\n\nint main(void) { return bait != 0; }\n',
    ),
    (
        'C-4 Disabled Preprocessor Block (1.00)',
        'c',
        '#if 0\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n#endif\nint main(void) { return 0; }\n',
    ),
    (
        'C-5 Function-Local Comment (1.00)',
        'c',
        'int main(void) {\n    /*\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n    */\n    return 0;\n}\n',
    ),
    (
        'CXX-1 Block Comment (1.00)',
        'cpp',
        '/*\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n*/\nint main() { return 0; }\n',
    ),
    (
        'CXX-2 Line Comment (1.00)',
        'cpp',
        '//\n//[*]\n//state S {\n//def int x = 1;\n//enter {}\n//}\n//>> enter\n//a::b\n//a -> b\n//! -> c\n//pseudo named abstract ref effect\nint main() { return 0; }\n',
    ),
    (
        'CXX-3 Raw String (1.00)',
        'cpp',
        'const char* bait = R"FCSTM([*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n)FCSTM";\nint main() { return bait != 0; }\n',
    ),
    (
        'CXX-4 String Literal (1.00)',
        'cpp',
        'const char* bait =\n    "[*]\\n"\n    "state S {\\n"\n    "def int x = 1;\\n"\n    "enter {}\\n"\n    "}\\n"\n    ">> enter\\n"\n    "a::b\\n"\n    "a -> b\\n"\n    "! -> c\\n"\n    "pseudo named abstract ref effect\\n";\n\nint main() { return bait != 0; }\n',
    ),
    (
        'CXX-5 Disabled Preprocessor Block (1.00)',
        'cpp',
        '#if 0\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n#endif\nint main() { return 0; }\n',
    ),
    (
        'JAVA-1 Package Plus Block Comment (1.00)',
        'java',
        'package demo;\n/*\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n*/\n',
    ),
    (
        'JAVA-2 Package Plus Line Comment (1.00)',
        'java',
        'package demo;\n//\n//[*]\n//state S {\n//def int x = 1;\n//enter {}\n//}\n//>> enter\n//a::b\n//a -> b\n//! -> c\n//pseudo named abstract ref effect\n',
    ),
    (
        'JAVA-3 Concatenated String (1.00)',
        'java',
        'package demo;\nclass Demo {\n    String bait =\n        "[*]\\n" +\n        "state S {\\n" +\n        "def int x = 1;\\n" +\n        "enter {}\\n" +\n        "}\\n" +\n        ">> enter\\n" +\n        "a::b\\n" +\n        "a -> b\\n" +\n        "! -> c\\n" +\n        "pseudo named abstract ref effect\\n";\n}\n',
    ),
    (
        'JAVA-4 String.join (1.00)',
        'java',
        'package demo;\nclass Demo {\n    String bait = String.join("\\n",\n        "[*]",\n        "state S {",\n        "def int x = 1;",\n        "enter {}",\n        "}",\n        ">> enter",\n        "a::b",\n        "a -> b",\n        "! -> c",\n        "pseudo named abstract ref effect"\n    );\n}\n',
    ),
    (
        'JAVA-5 Javadoc And Class (1.00)',
        'java',
        '/**\n * [*]\n * state S {\n * def int x = 1;\n * enter {}\n * }\n * >> enter\n * a::b\n * a -> b\n * ! -> c\n * pseudo named abstract ref effect\n */\npackage demo;\nclass Demo {}\n',
    ),
    (
        'JS-1 Block Comment (1.00)',
        'javascript',
        '/*\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n*/\nglobalThis.ready = true;\n',
    ),
    (
        'JS-2 Line Comment (1.00)',
        'javascript',
        '//\n//[*]\n//state S {\n//def int x = 1;\n//enter {}\n//}\n//>> enter\n//a::b\n//a -> b\n//! -> c\n//pseudo named abstract ref effect\nglobalThis.ready = true;\n',
    ),
    (
        'JS-3 Template Literal (1.00)',
        'javascript',
        'globalThis.bait = `\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n`;\n',
    ),
    (
        'JS-4 String.raw Tagged Template (1.00)',
        'javascript',
        'globalThis.bait = String.raw`\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n`;\n',
    ),
    (
        'JS-5 Array Join (1.00)',
        'javascript',
        "globalThis.bait = [\n  '[*]',\n  'state S {',\n  'def int x = 1;',\n  'enter {}',\n  '}',\n  '>> enter',\n  'a::b',\n  'a -> b',\n  '! -> c',\n  'pseudo named abstract ref effect',\n].join('\\n');\n",
    ),
    (
        'TS-1 Block Comment (1.00)',
        'typescript',
        '/*\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n*/\nexport {};\n',
    ),
    (
        'TS-2 Line Comment (1.00)',
        'typescript',
        '//\n//[*]\n//state S {\n//def int x = 1;\n//enter {}\n//}\n//>> enter\n//a::b\n//a -> b\n//! -> c\n//pseudo named abstract ref effect\nexport {};\n',
    ),
    (
        'TS-3 Typed Template Literal (1.00)',
        'typescript',
        'const bait: string = `\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n`;\nexport { bait };\n',
    ),
    (
        'TS-4 Interface Wrapper (1.00)',
        'typescript',
        'interface Box { bait: string; }\nconst box: Box = {\n    bait: `\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n`\n};\nexport { box };\n',
    ),
    (
        'TS-5 Typed String.raw (1.00)',
        'typescript',
        'type PayloadBox = { bait: string };\nconst payloadBox: PayloadBox = {\n    bait: String.raw`\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n`\n};\nexport default payloadBox;\n',
    ),
    (
        'PY-1 Module Docstring (1.00)',
        'python',
        '"""\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n"""\nvalue = 0\n',
    ),
    (
        'PY-2 Triple Quoted String (1.00)',
        'python',
        'bait = """\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n"""\n',
    ),
    (
        'PY-3 Raw Triple Quoted String (1.00)',
        'python',
        'bait = r"""\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n"""\n',
    ),
    (
        'PY-4 Line Comment (1.00)',
        'python',
        '#\n#[*]\n#state S {\n#def int x = 1;\n#enter {}\n#}\n#>> enter\n#a::b\n#a -> b\n#! -> c\n#pseudo named abstract ref effect\nvalue = 0\n',
    ),
    (
        'PY-5 Implicit Concatenation (1.00)',
        'python',
        'bait = (\n    "[*]\\n"\n    "state S {\\n"\n    "def int x = 1;\\n"\n    "enter {}\\n"\n    "}\\n"\n    ">> enter\\n"\n    "a::b\\n"\n    "a -> b\\n"\n    "! -> c\\n"\n    "pseudo named abstract ref effect\\n"\n)\n',
    ),
    (
        'RB-1 begin/end Comment (1.00)',
        'ruby',
        '=begin\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n=end\nvalue = nil\n',
    ),
    (
        'RB-2 Line Comment (1.00)',
        'ruby',
        '#\n#[*]\n#state S {\n#def int x = 1;\n#enter {}\n#}\n#>> enter\n#a::b\n#a -> b\n#! -> c\n#pseudo named abstract ref effect\nvalue = nil\n',
    ),
    (
        'RB-3 Heredoc (1.00)',
        'ruby',
        "payload = <<~'FCSTM'\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\nFCSTM\n",
    ),
    (
        'RB-4 Percent String (1.00)',
        'ruby',
        'payload = %Q|\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n|\n',
    ),
    (
        'RB-5 Array Join (1.00)',
        'ruby',
        'payload = [\n  \'[*]\',\n  \'state S {\',\n  \'def int x = 1;\',\n  \'enter {}\',\n  \'}\',\n  \'>> enter\',\n  \'a::b\',\n  \'a -> b\',\n  \'! -> c\',\n  \'pseudo named abstract ref effect\',\n].join("\\n")\n',
    ),
    (
        'RS-1 Block Comment (1.00)',
        'rust',
        '/*\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n*/\nfn main() {}\n',
    ),
    (
        'RS-2 Line Comment (1.00)',
        'rust',
        '//\n//[*]\n//state S {\n//def int x = 1;\n//enter {}\n//}\n//>> enter\n//a::b\n//a -> b\n//! -> c\n//pseudo named abstract ref effect\nfn main() {}\n',
    ),
    (
        'RS-3 Raw String (1.00)',
        'rust',
        'const BAIT: &str = r#"[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n"#;\nfn main() {}\n',
    ),
    (
        'RS-4 concat! Macro (1.00)',
        'rust',
        'const BAIT: &str = concat!(\n    "[*]\\n",\n    "state S {\\n",\n    "def int x = 1;\\n",\n    "enter {}\\n",\n    "}\\n",\n    ">> enter\\n",\n    "a::b\\n",\n    "a -> b\\n",\n    "! -> c\\n",\n    "pseudo named abstract ref effect\\n",\n);\nfn main() {}\n',
    ),
    (
        'RS-5 Crate Doc Comment (1.00)',
        'rust',
        '//!\n//! [*]\n//! state S {\n//! def int x = 1;\n//! enter {}\n//! }\n//! >> enter\n//! a::b\n//! a -> b\n//! ! -> c\n//! pseudo named abstract ref effect\nfn main() {}\n',
    ),
    (
        'GO-1 Block Comment (1.00)',
        'go',
        '/*\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n*/\npackage main\nfunc main() {}\n',
    ),
    (
        'GO-2 Line Comment (1.00)',
        'go',
        '//\n//[*]\n//state S {\n//def int x = 1;\n//enter {}\n//}\n//>> enter\n//a::b\n//a -> b\n//! -> c\n//pseudo named abstract ref effect\npackage main\nfunc main() {}\n',
    ),
    (
        'GO-3 Raw String (1.00)',
        'go',
        'package main\nconst bait = `\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n`\nfunc main() {}\n',
    ),
    (
        'GO-4 Concatenated String (1.00)',
        'go',
        'package main\nconst bait =\n    "[*]\\n" +\n    "state S {\\n" +\n    "def int x = 1;\\n" +\n    "enter {}\\n" +\n    "}\\n" +\n    ">> enter\\n" +\n    "a::b\\n" +\n    "a -> b\\n" +\n    "! -> c\\n" +\n    "pseudo named abstract ref effect\\n"\nfunc main() {}\n',
    ),
    (
        'GO-5 Function-Local Comment (1.00)',
        'go',
        'package main\nfunc main() {\n    /*\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\n    */\n}\n',
    ),
    (
        'PUML-1 Sequence Diagram Comments (1.00)',
        'plantuml',
        "@startuml\n' [*]\n' state S {\n' def int x = 1;\n' enter {}\n' }\n' >> enter\n' a::b\n' a -> b\n' ! -> c\n' pseudo named abstract ref effect\nAlice -> Bob : ok\n@enduml\n",
    ),
    (
        'PUML-2 Floating Note (1.00)',
        'plantuml',
        '@startuml\nnote as N1\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\nend note\n@enduml\n',
    ),
    (
        'PUML-3 Legend Block (1.00)',
        'plantuml',
        '@startuml\nlegend left\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\nendlegend\n@enduml\n',
    ),
    (
        'PUML-4 State Note (1.00)',
        'plantuml',
        '@startuml\nstate Dummy\nnote right of Dummy\n[*]\nstate S {\ndef int x = 1;\nenter {}\n}\n>> enter\na::b\na -> b\n! -> c\npseudo named abstract ref effect\nend note\n@enduml\n',
    ),
    (
        'PUML-5 State Diagram Comments (1.00)',
        'plantuml',
        "@startuml\nstate Dummy\n' [*]\n' state S {\n' def int x = 1;\n' enter {}\n' }\n' >> enter\n' a::b\n' a -> b\n' ! -> c\n' pseudo named abstract ref effect\nDummy --> Dummy : ok\n@enduml\n",
    ),
]
_SAMPLE_CODE_FILES = sorted(_SAMPLE_CODE_DIR.glob('*.fcstm'))


@pytest.mark.unittest
class TestFcstmLexerAnalyseText:
    def test_langcheck_hack_examples_are_embedded_completely(self):
        assert len(_LANGCHECK_HACK_CASES) == 50
        assert [title for title, _, _ in _LANGCHECK_HACK_CASES] == [
            'C-1 Block Comment (1.00)',
            'C-2 Line Comment (1.00)',
            'C-3 String Literal (1.00)',
            'C-4 Disabled Preprocessor Block (1.00)',
            'C-5 Function-Local Comment (1.00)',
            'CXX-1 Block Comment (1.00)',
            'CXX-2 Line Comment (1.00)',
            'CXX-3 Raw String (1.00)',
            'CXX-4 String Literal (1.00)',
            'CXX-5 Disabled Preprocessor Block (1.00)',
            'JAVA-1 Package Plus Block Comment (1.00)',
            'JAVA-2 Package Plus Line Comment (1.00)',
            'JAVA-3 Concatenated String (1.00)',
            'JAVA-4 String.join (1.00)',
            'JAVA-5 Javadoc And Class (1.00)',
            'JS-1 Block Comment (1.00)',
            'JS-2 Line Comment (1.00)',
            'JS-3 Template Literal (1.00)',
            'JS-4 String.raw Tagged Template (1.00)',
            'JS-5 Array Join (1.00)',
            'TS-1 Block Comment (1.00)',
            'TS-2 Line Comment (1.00)',
            'TS-3 Typed Template Literal (1.00)',
            'TS-4 Interface Wrapper (1.00)',
            'TS-5 Typed String.raw (1.00)',
            'PY-1 Module Docstring (1.00)',
            'PY-2 Triple Quoted String (1.00)',
            'PY-3 Raw Triple Quoted String (1.00)',
            'PY-4 Line Comment (1.00)',
            'PY-5 Implicit Concatenation (1.00)',
            'RB-1 begin/end Comment (1.00)',
            'RB-2 Line Comment (1.00)',
            'RB-3 Heredoc (1.00)',
            'RB-4 Percent String (1.00)',
            'RB-5 Array Join (1.00)',
            'RS-1 Block Comment (1.00)',
            'RS-2 Line Comment (1.00)',
            'RS-3 Raw String (1.00)',
            'RS-4 concat! Macro (1.00)',
            'RS-5 Crate Doc Comment (1.00)',
            'GO-1 Block Comment (1.00)',
            'GO-2 Line Comment (1.00)',
            'GO-3 Raw String (1.00)',
            'GO-4 Concatenated String (1.00)',
            'GO-5 Function-Local Comment (1.00)',
            'PUML-1 Sequence Diagram Comments (1.00)',
            'PUML-2 Floating Note (1.00)',
            'PUML-3 Legend Block (1.00)',
            'PUML-4 State Note (1.00)',
            'PUML-5 State Diagram Comments (1.00)',
        ]

    @pytest.mark.parametrize(
        ('title', 'language', 'code'),
        _LANGCHECK_HACK_CASES,
        ids=[title for title, _, _ in _LANGCHECK_HACK_CASES],
    )
    def test_langcheck_hack_examples_do_not_look_like_fcstm(self, title, language, code):
        score = FcstmLexer.analyse_text(code)

        assert score < 0.15, (
            f'{title} ({language}) should be rejected by the FCSTM lexer, '
            f'but analyse_text returned {score:.2f}.'
        )

    @pytest.mark.parametrize(
        'path',
        _SAMPLE_CODE_FILES,
        ids=[path.name for path in _SAMPLE_CODE_FILES],
    )
    def test_real_fcstm_samples_remain_detectable(self, path):
        score = FcstmLexer.analyse_text(path.read_text(encoding='utf-8'))

        assert score >= 0.70, (
            f'{path.name} is real FCSTM input and should keep a strong score, '
            f'but analyse_text returned {score:.2f}.'
        )
