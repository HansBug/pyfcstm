# NOTE:
# Keep this regression file fully self-contained.
# Do not load cases or case metadata from LANGCHECK_HACK.md or any other
# external document/source file. All regression examples and identifying
# information must stay encoded directly in this test module.
# The only allowed external inputs are real FCSTM positive samples stored
# under test/testfile; do not add Markdown/docs-based fixtures here.

import inspect
from pathlib import Path
from textwrap import dedent

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.highlight import FcstmLexer
from pyfcstm.highlight import pygments_lexer as pygments_lexer_module
from pyfcstm.model import StateMachine, parse_dsl_node_to_state_machine

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
    (
        '51. C-6 Typedef Globals And Main (1.00)',
        'c',
        'typedef int state;\ntypedef int event;\n\nstruct sink { int b; };\n\nint pseudo, named, abstract, ref, effect, enter;\nstruct sink *a;\nstate S;\nevent Tick;\n\nint main(void) {\n    enter;\n    a -> b;\n    return 0;\n}\n',
    ),
    (
        '52. C-7 Struct Holder Plus during (1.00)',
        'c',
        'typedef int state;\ntypedef int event;\n\nstruct sink { int b; };\n\nstruct bag {\n    state S;\n    event Tick;\n    int pseudo, named, abstract, ref, effect;\n};\n\nint during;\nstruct sink *a;\n\nint probe(void) {\n    during;\n    a -> b;\n    return 0;\n}\n',
    ),
    (
        '53. C-8 Local State/Event Decls (1.00)',
        'c',
        'typedef int state;\ntypedef int event;\n\nstruct sink { int b; };\n\nint pseudo, named, abstract, ref, effect, exit;\nstruct sink *a;\n\nvoid probe(void) {\n    state S;\n    event Tick;\n    exit;\n    a -> b;\n}\n',
    ),
    (
        '54. C-9 Mixed Alias And Pointer Target (1.00)',
        'c',
        'typedef struct sink { int b; } sink;\ntypedef int state;\ntypedef sink *event;\n\nint pseudo, named, abstract, ref, effect, enter;\nstate S;\nevent Tick;\n\nint probe(void) {\n    sink *a = Tick;\n    enter;\n    a -> b;\n    return S;\n}\n',
    ),
    (
        '55. C-10 Function-Local Typedefs (1.00)',
        'c',
        'struct sink { int b; };\n\nint pseudo, named, abstract, ref, effect;\n\nint probe(void) {\n    typedef int state;\n    typedef int event;\n    state S;\n    event Tick;\n    int enter;\n    struct sink *a = 0;\n\n    enter;\n    a -> b;\n    return Tick + S;\n}\n',
    ),
    (
        '56. CXX-6 Using Aliases And Main (1.00)',
        'cpp',
        'using state = int;\nusing event = int;\n\nstruct sink { int b; };\n\nint pseudo, named, abstract, ref, effect, enter;\nsink *a;\nstate S;\nevent Tick;\n\nint main() {\n    enter;\n    a -> b;\n    return 0;\n}\n',
    ),
    (
        '57. CXX-7 Member Fields Plus during (1.00)',
        'cpp',
        'using state = int;\nusing event = int;\n\nstruct sink { int b; };\n\nstruct bag {\n    state S;\n    event Tick;\n    int pseudo, named, abstract, ref, effect;\n    int during;\n    sink *a;\n\n    void probe() {\n        during;\n        a -> b;\n    }\n};\n',
    ),
    (
        '58. CXX-8 Local Aliases In Helper (1.00)',
        'cpp',
        'struct sink { int b; };\n\nvoid probe() {\n    using state = int;\n    using event = int;\n\n    int pseudo, named, abstract, ref, effect, exit;\n    sink *a = nullptr;\n    state S;\n    event Tick;\n\n    exit;\n    a -> b;\n}\n',
    ),
    (
        '59. CXX-9 Lambda Body Payload (1.00)',
        'cpp',
        'using state = int;\nusing event = int;\n\nstruct sink { int b; };\n\nauto probe = [] {\n    int pseudo, named, abstract, ref, effect, enter;\n    sink *a = nullptr;\n    state S;\n    event Tick;\n\n    enter;\n    a -> b;\n};\n',
    ),
    (
        '60. CXX-10 Constructor Body Payload (1.00)',
        'cpp',
        'using state = int;\nusing event = int;\n\nstruct sink { int b; };\n\nstruct probe {\n    int pseudo, named, abstract, ref, effect, enter;\n    sink *a;\n    state S;\n    event Tick;\n\n    probe() : a(nullptr) {\n        enter;\n        a -> b;\n    }\n};\n',
    ),
    (
        '61. JAVA-6 Fields Plus Method Reference Lambda (0.95)',
        'java',
        'abstract class pseudo {}\nclass named {}\nclass ref {}\nclass effect {\n    static String build() { return ""; }\n}\nclass state {}\nclass event {}\n\nclass Demo {\n    state S;\n    event Tick;\n    java.util.function.Function<Object, java.util.function.Supplier<String>> f =\n        a -> effect::build;\n}\n',
    ),
    (
        '62. JAVA-7 Instance Initializer Payload (0.95)',
        'java',
        'abstract class pseudo {}\nclass named {}\nclass ref {}\nclass effect {\n    static String build() { return ""; }\n}\nclass state {}\nclass event {}\n\nclass Demo {\n    {\n        state S;\n        event Tick;\n        java.util.function.Function<Object, java.util.function.Supplier<String>> f =\n            a -> effect::build;\n    }\n}\n',
    ),
    (
        '63. JAVA-8 Static Initializer Payload (0.95)',
        'java',
        'abstract class pseudo {}\nclass named {}\nclass ref {}\nclass effect {\n    static String build() { return ""; }\n}\nclass state {}\nclass event {}\n\nclass Demo {\n    static {\n        state S;\n        event Tick;\n        java.util.function.Function<Object, java.util.function.Supplier<String>> f =\n            a -> effect::build;\n    }\n}\n',
    ),
    (
        '64. JAVA-9 Constructor-Local Payload (0.95)',
        'java',
        'abstract class pseudo {}\nclass named {}\nclass ref {}\nclass effect {\n    static String build() { return ""; }\n}\nclass state {}\nclass event {}\n\nclass Demo {\n    Demo() {\n        state S;\n        event Tick;\n        java.util.function.Function<Object, java.util.function.Supplier<String>> f =\n            a -> effect::build;\n    }\n}\n',
    ),
    (
        '65. JAVA-10 Anonymous Inner Class Fields (0.95)',
        'java',
        'abstract class pseudo {}\nclass named {}\nclass ref {}\nclass effect {\n    static String build() { return ""; }\n}\nclass state {}\nclass event {}\n\nclass Demo {\n    Object box = new Object() {\n        state S;\n        event Tick;\n        java.util.function.Function<Object, java.util.function.Supplier<String>> f =\n            a -> effect::build;\n    };\n}\n',
    ),
    (
        '66. JS-6 Top-Level Newline Stitching (1.00)',
        'javascript',
        'const pseudo = 1, named = 2, abstract = 3, ref = 4, effect = 5;\n/[*]/;\nstate\nS;\nevent\nTick;\ndef\nint\nx = 1;\nenter;\n',
    ),
    (
        '67. JS-7 Function Body Newline Stitching (1.00)',
        'javascript',
        'const pseudo = 1, named = 2, abstract = 3, ref = 4, effect = 5;\n\nfunction demo() {\n  /[*]/;\n  state\n  S;\n  event\n  Tick;\n  def\n  int\n  x = 1;\n  during;\n}\n',
    ),
    (
        '68. JS-8 IIFE Payload (1.00)',
        'javascript',
        'const pseudo = 1, named = 2, abstract = 3, ref = 4, effect = 5;\n\n(() => {\n  /[*]/;\n  state\n  S;\n  event\n  Tick;\n  def\n  int\n  x = 1;\n  exit;\n})();\n',
    ),
    (
        '69. JS-9 Class Static Block (1.00)',
        'javascript',
        'const pseudo = 1, named = 2, abstract = 3, ref = 4, effect = 5;\n\nclass Demo {\n  static {\n    /[*]/;\n    state\n    S;\n    event\n    Tick;\n    def\n    int\n    x = 1;\n    enter;\n  }\n}\n',
    ),
    (
        '70. JS-10 try/finally Wrapper (1.00)',
        'javascript',
        'const pseudo = 1, named = 2, abstract = 3, ref = 4, effect = 5;\n\ntry {\n  /[*]/;\n  state\n  S;\n  event\n  Tick;\n  def\n  int\n  x = 1;\n  enter;\n} finally {}\n',
    ),
    (
        '71. TS-6 Typed Prelude Plus Newline Stitching (1.00)',
        'typescript',
        'let x: number;\nconst tags: Record<string, number> = { pseudo: 1, named: 2, abstract: 3, ref: 4, effect: 5 };\n/[*]/;\nstate\nS;\nevent\nTick;\ndef\nint\nx = 1;\nenter;\n',
    ),
    (
        '72. TS-7 Function Body Payload (1.00)',
        'typescript',
        'const tags: Record<string, number> = { pseudo: 1, named: 2, abstract: 3, ref: 4, effect: 5 };\n\nfunction demo(): void {\n  let x: number;\n  /[*]/;\n  state\n  S;\n  event\n  Tick;\n  def\n  int\n  x = 1;\n  during;\n}\n',
    ),
    (
        '73. TS-8 Namespace Wrapper (1.00)',
        'typescript',
        'namespace demo {\n  let x: number;\n  const tags: Record<string, number> = { pseudo: 1, named: 2, abstract: 3, ref: 4, effect: 5 };\n  /[*]/;\n  state\n  S;\n  event\n  Tick;\n  def\n  int\n  x = 1;\n  exit;\n}\n',
    ),
    (
        '74. TS-9 Class Static Block (1.00)',
        'typescript',
        'const tags: Record<string, number> = { pseudo: 1, named: 2, abstract: 3, ref: 4, effect: 5 };\n\nclass Demo {\n  static {\n    let x: number;\n    /[*]/;\n    state\n    S;\n    event\n    Tick;\n    def\n    int\n    x = 1;\n    enter;\n  }\n}\n',
    ),
    (
        '75. TS-10 try/finally Wrapper (1.00)',
        'typescript',
        'const tags: Record<string, number> = { pseudo: 1, named: 2, abstract: 3, ref: 4, effect: 5 };\n\ntry {\n  let x: number;\n  /[*]/;\n  state\n  S;\n  event\n  Tick;\n  def\n  int\n  x = 1;\n  enter;\n} finally {}\n',
    ),
    (
        '76. PY-6 Top-Level Bare Expressions (0.87)',
        'python',
        'pseudo = named = abstract = ref = effect = event = state = S = Tick = enter = 1\n\nstate\nS;\nevent\nTick;\nenter;\n',
    ),
    (
        '77. PY-7 Class Body Bare Expressions (0.87)',
        'python',
        'class Box:\n    pseudo = named = abstract = ref = effect = event = state = S = Tick = during = 1\n\n    state\n    S;\n    event\n    Tick;\n    during;\n',
    ),
    (
        '78. PY-8 if-Block Bare Expressions (0.87)',
        'python',
        'if True:\n    pseudo = named = abstract = ref = effect = event = state = S = Tick = exit = 1\n\n    state\n    S;\n    event\n    Tick;\n    exit;\n',
    ),
    (
        '79. PY-9 for-Block Bare Expressions (0.87)',
        'python',
        'for _ in [0]:\n    pseudo = named = abstract = ref = effect = event = state = S = Tick = enter = 1\n\n    state\n    S;\n    event\n    Tick;\n    enter;\n',
    ),
    (
        '80. PY-10 try/finally Bare Expressions (0.87)',
        'python',
        'try:\n    pseudo = named = abstract = ref = effect = event = state = S = Tick = enter = 1\n\n    state\n    S;\n    event\n    Tick;\n    enter;\nfinally:\n    pass\n',
    ),
    (
        '81. RB-6 Top-Level Regex Literal Plus Calls (0.99)',
        'ruby',
        'pseudo = named = abstract = ref = effect = 1\n/[*]/\nstate S;\nevent Tick;\nenter;\n',
    ),
    (
        '82. RB-7 Class Body Payload (0.99)',
        'ruby',
        'class Box\n  pseudo = named = abstract = ref = effect = 1\n  /[*]/\n  state S;\n  event Tick;\n  during;\nend\n',
    ),
    (
        '83. RB-8 Module Body Payload (0.99)',
        'ruby',
        'module Box\n  pseudo = named = abstract = ref = effect = 1\n  /[*]/\n  state S;\n  event Tick;\n  exit;\nend\n',
    ),
    (
        '84. RB-9 Lambda Body Payload (0.99)',
        'ruby',
        'probe = -> do\n  pseudo = named = abstract = ref = effect = 1\n  /[*]/\n  state S;\n  event Tick;\n  enter;\nend\n',
    ),
    (
        '85. RB-10 BEGIN Block Payload (0.99)',
        'ruby',
        'BEGIN {\n  pseudo = named = abstract = ref = effect = 1\n  /[*]/\n  state S;\n  event Tick;\n  enter;\n}\n',
    ),
    (
        '86. RS-6 Item Macro With Braces (1.00)',
        'rust',
        'macro_rules! bait { ($($tt:tt)*) => {}; }\n\nbait! {\n    [*]\n    state S;\n    event Tick;\n    def int x = 1;\n    enter;\n    >> enter {}\n    a -> b::c;\n    pseudo named abstract ref effect\n}\n',
    ),
    (
        '87. RS-7 Item Macro With Parentheses (1.00)',
        'rust',
        'macro_rules! bait { ($($tt:tt)*) => {}; }\n\nbait!(\n    [*]\n    state S;\n    event Tick;\n    def int x = 1;\n    during;\n    a -> b::c;\n    pseudo named abstract ref effect\n);\n',
    ),
    (
        '88. RS-8 Item Macro With Brackets (1.00)',
        'rust',
        'macro_rules! bait { ($($tt:tt)*) => {}; }\n\nbait![\n    [*]\n    state S;\n    event Tick;\n    def int x = 1;\n    exit;\n    a -> b::c;\n    pseudo named abstract ref effect\n];\n',
    ),
    (
        '89. RS-9 Const Block Wrapper (1.00)',
        'rust',
        'macro_rules! bait { ($($tt:tt)*) => {}; }\n\nconst _: () = {\n    bait! {\n        [*]\n        state S;\n        event Tick;\n        def int x = 1;\n        enter;\n        a -> b::c;\n        pseudo named abstract ref effect\n    }\n};\n',
    ),
    (
        '90. RS-10 Nested Token Tree Wrapper (1.00)',
        'rust',
        'macro_rules! bait { ($($tt:tt)*) => {}; }\n\nbait! {\n    wrapper {\n        [*]\n        state S;\n        event Tick;\n        def int x = 1;\n        enter;\n        a -> b::c;\n        pseudo named abstract ref effect\n    }\n}\n',
    ),
    (
        '91. GO-6 Named Struct Fields (0.87)',
        'go',
        'package bait\n\ntype state int\ntype event int\ntype enter int\ntype S int\ntype Tick int\n\ntype Box struct {\n    state S;\n    event Tick;\n    enter;\n    pseudo, named, abstract, ref, effect int;\n}\n',
    ),
    (
        '92. GO-7 Anonymous Struct Variable (0.87)',
        'go',
        'package bait\n\ntype state int\ntype event int\ntype enter int\ntype S int\ntype Tick int\n\nvar _ = struct {\n    state S;\n    event Tick;\n    enter;\n    pseudo, named, abstract, ref, effect int;\n}{}\n',
    ),
    (
        '93. GO-8 Function-Local Type Declaration (0.87)',
        'go',
        'package bait\n\ntype state int\ntype event int\ntype enter int\ntype S int\ntype Tick int\n\nfunc probe() {\n    type Box struct {\n        state S;\n        event Tick;\n        enter;\n        pseudo, named, abstract, ref, effect int;\n    }\n\n    _ = Box{}\n}\n',
    ),
    (
        '94. GO-9 Nested Struct Field (0.87)',
        'go',
        'package bait\n\ntype state int\ntype event int\ntype enter int\ntype S int\ntype Tick int\n\ntype Outer struct {\n    inner struct {\n        state S;\n        event Tick;\n        enter;\n        pseudo, named, abstract, ref, effect int;\n    };\n}\n',
    ),
    (
        '95. GO-10 Slice Of Anonymous Structs (0.87)',
        'go',
        'package bait\n\ntype state int\ntype event int\ntype enter int\ntype S int\ntype Tick int\n\nvar _ = []struct {\n    state S;\n    event Tick;\n    enter;\n    pseudo, named, abstract, ref, effect int;\n}{\n    {},\n}\n',
    ),
    (
        '96. PUML-6 allowmixing Plus Class Body (0.87)',
        'plantuml',
        '@startuml\nallowmixing\nclass Dummy {\n  state S;\n  event Tick;\n  enter;\n  pseudo\n  named\n  abstract\n  ref\n  effect\n}\n[*] -> Dummy : ref;\n@enduml\n',
    ),
    (
        '97. PUML-7 allowmixing Plus Abstract Class Body (0.87)',
        'plantuml',
        '@startuml\nallowmixing\nabstract class Harness {\n  state S;\n  event Tick;\n  enter;\n  pseudo\n  named\n  abstract\n  ref\n  effect\n}\n[*] -> Harness : ref;\n@enduml\n',
    ),
    (
        '98. PUML-8 allowmixing Plus Annotation Body (0.87)',
        'plantuml',
        '@startuml\nallowmixing\nannotation Gateway {\n  state S;\n  event Tick;\n  enter;\n  pseudo\n  named\n  abstract\n  ref\n  effect\n}\n[*] -> Gateway : ref;\n@enduml\n',
    ),
    (
        '99. PUML-9 allowmixing Plus Entity Body (0.87)',
        'plantuml',
        '@startuml\nallowmixing\nentity Ledger {\n  state S;\n  event Tick;\n  enter;\n  pseudo\n  named\n  abstract\n  ref\n  effect\n}\n[*] -> Ledger : ref;\n@enduml\n',
    ),
    (
        '100. PUML-10 allowmixing Plus Object Body (0.87)',
        'plantuml',
        '@startuml\nallowmixing\nobject Cache {\n  state S;\n  event Tick;\n  enter;\n  pseudo\n  named\n  abstract\n  ref\n  effect\n}\n[*] -> Cache : ref;\n@enduml\n',
    ),
]

_LANGCHECK_POSITIVE_CASES = [
    (
        '1. Minimal Leaf Stair-Step',
        'state\nS\n;\n',
    ),
    (
        '2. Pseudo Leaf Stair-Step',
        'pseudo\nstate\nP\n;\n',
    ),
    (
        '3. Named Leaf Stair-Step',
        'state\nNamed\nnamed\n"alias"\n;\n',
    ),
    (
        '4. Slash-Comment Split Leaf',
        'state // split\nSlash\n;\n',
    ),
    (
        '5. Hash-Comment Split Leaf',
        'state # split\nHash\n;\n',
    ),
    (
        '6. Composite With Split Entry',
        dedent('''\
            state
            Root
            {
                [*]
                ->
                A
                ;
                state
                A
                ;
            }
        '''),
    ),
    (
        '7. Composite With Split Normal Transition',
        dedent('''\
            state
            Root
            {
                [*]
                ->
                A
                ;
                A
                ->
                B
                ;
                state
                A
                ;
                state
                B
                ;
            }
        '''),
    ),
    (
        '8. Composite With Split Exit Transition',
        dedent('''\
            state
            Root
            {
                [*]
                ->
                A
                ;
                A
                ->
                [*]
                ;
                state
                A
                ;
            }
        '''),
    ),
    (
        '9. Split Force Transition',
        dedent('''\
            state
            Root
            {
                !
                A
                ->
                B
                ;
                [*]
                ->
                A
                ;
                state
                A
                ;
                state
                B
                ;
            }
        '''),
    ),
    (
        '10. Split All-Force Transition',
        dedent('''\
            state
            Root
            {
                !
                *
                ->
                [*]
                ;
                [*]
                ->
                A
                ;
                state
                A
                ;
            }
        '''),
    ),
    (
        '11. Multiline Int Def',
        dedent('''\
            def
            int
            x
            =
            0
            ;
            state
            S
            ;
        '''),
    ),
    (
        '12. Multiline Float Def Expr',
        dedent('''\
            def
            float
            gain
            =
            1
            +
            2
            /
            3
            ;
            state
            S
            ;
        '''),
    ),
    (
        '13. Split Event Declaration',
        dedent('''\
            state
            Root
            {
                [*]
                ->
                A
                ;
                event
                Tick
                ;
                state
                A
                ;
            }
        '''),
    ),
    (
        '14. Split Named Event Declaration',
        dedent('''\
            state
            Root
            {
                [*]
                ->
                A
                ;
                event
                Tick
                named
                "tick"
                ;
                state
                A
                ;
            }
        '''),
    ),
    (
        '15. Split Enter Operations',
        dedent('''\
            def
            int
            x
            =
            0
            ;
            state
            Leaf
            {
                enter
                hook
                {
                    x
                    =
                    1
                    ;
                }
            }
        '''),
    ),
    (
        '16. Split Enter Abstract',
        dedent('''\
            state
            Leaf
            {
                enter
                abstract
                hook
                ;
            }
        '''),
    ),
    (
        '17. Split Enter Ref',
        dedent('''\
            state
            Leaf
            {
                exit
                abstract
                base
                ;
                enter
                alias
                ref
                base
                ;
            }
        '''),
    ),
    (
        '18. Split Exit Operations',
        dedent('''\
            def
            int
            x
            =
            0
            ;
            state
            Leaf
            {
                exit
                hook
                {
                    x
                    =
                    2
                    ;
                }
            }
        '''),
    ),
    (
        '19. Split Exit Abstract Doc',
        dedent('''\
            state
            Leaf
            {
                exit
                abstract
                hook
                /* doc */
            }
        '''),
    ),
    (
        '20. Split Exit Ref Absolute',
        dedent('''\
            state
            Leaf
            {
                enter
                abstract
                base
                ;
                exit
                alias
                ref
                /
                base
                ;
            }
        '''),
    ),
    (
        '21. Split Leaf During Operations',
        dedent('''\
            def
            int
            x
            =
            0
            ;
            state
            Leaf
            {
                during
                hook
                {
                    x
                    =
                    x
                    +
                    1
                    ;
                }
            }
        '''),
    ),
    (
        '22. Split Composite During Before Ops',
        dedent('''\
            def
            int
            x
            =
            0
            ;
            state
            Root
            {
                [*]
                ->
                A
                ;
                during
                before
                hook
                {
                    x
                    =
                    1
                    ;
                }
                state
                A
                ;
            }
        '''),
    ),
    (
        '23. Split Composite During After Abstract',
        dedent('''\
            state
            Root
            {
                [*]
                ->
                A
                ;
                during
                after
                abstract
                hook
                ;
                state
                A
                ;
            }
        '''),
    ),
    (
        '24. Split Composite During Before Ref',
        dedent('''\
            state
            Root
            {
                [*]
                ->
                A
                ;
                during
                before
                abstract
                base
                ;
                during
                before
                alias
                ref
                base
                ;
                state
                A
                ;
            }
        '''),
    ),
    (
        '25. Split During Aspect Ops',
        dedent('''\
            def
            int
            x
            =
            0
            ;
            state
            Leaf
            {
                >>
                during
                before
                hook
                {
                    x
                    =
                    1
                    ;
                }
            }
        '''),
    ),
    (
        '26. Split During Aspect Abstract Doc',
        dedent('''\
            state
            Leaf
            {
                >>
                during
                after
                abstract
                hook
                /* doc */
            }
        '''),
    ),
    (
        '27. Split Transition Event Auto-Create',
        dedent('''\
            state
            Root
            {
                [*]
                ->
                A
                ;
                A
                ->
                B
                ::
                Tick
                ;
                state
                A
                ;
                state
                B
                ;
            }
        '''),
    ),
    (
        '28. Split Transition Absolute Event Path',
        dedent('''\
            state
            Root
            {
                [*]
                ->
                A
                ;
                A
                ->
                B
                :
                /
                Tick
                ;
                state
                A
                ;
                state
                B
                ;
            }
        '''),
    ),
    (
        '29. Split Transition Guard',
        dedent('''\
            def
            int
            x
            =
            0
            ;
            state
            Root
            {
                [*]
                ->
                A
                ;
                A
                ->
                B
                :
                if
                [
                    x
                    >
                    0
                ]
                ;
                state
                A
                ;
                state
                B
                ;
            }
        '''),
    ),
    (
        '30. Split Transition Effect Block',
        dedent('''\
            def
            int
            x
            =
            0
            ;
            state
            Root
            {
                [*]
                ->
                A
                ;
                A
                ->
                B
                effect
                {
                    x
                    =
                    3
                    ;
                }
                state
                A
                ;
                state
                B
                ;
            }
        '''),
    ),
    (
        '31. Nested Absolute Ref',
        dedent('''\
            state
            Root
            {
                [*]
                ->
                A
                ;
                enter
                abstract
                helper
                ;
                state
                A
                {
                    [*]
                    ->
                    B
                    ;
                    enter
                    alias
                    ref
                    /
                    helper
                    ;
                    state
                    B
                    ;
                }
            }
        '''),
    ),
    (
        '32. Pseudo Substate With Split Entry',
        dedent('''\
            state
            Root
            {
                [*]
                ->
                P
                ;
                pseudo
                state
                P
                ;
            }
        '''),
    ),
    (
        '33. Mixed Comments And No-Op Statements',
        dedent('''\
            state
            Root
            {
                ;
                [*] // init source
                ->
                A
                ;
                ;
                state # child decl
                A
                ;
                ;
            }
        '''),
    ),
    (
        '34. Split Dotted Ref Path',
        dedent('''\
            state
            Root
            {
                [*]
                ->
                A
                ;
                state
                A
                {
                    [*]
                    ->
                    B
                    ;
                    exit
                    abstract
                    helper
                    ;
                    state
                    B
                    {
                        enter
                        alias
                        ref
                        /
                        A
                        .
                        helper
                        ;
                    }
                }
            }
        '''),
    ),
    (
        '35. Deep Hierarchy Auto-Created Path Event',
        dedent('''\
            state
            Root
            {
                [*]
                ->
                A
                ;
                state
                A
                {
                    [*]
                    ->
                    B
                    ;
                    B
                    ->
                    [*]
                    :
                    /
                    A
                    .
                    Tick
                    ;
                    state
                    B
                    ;
                }
            }
        '''),
    ),
]

_LANGCHECK_POSITIVE_CASES += [
    (
        '36. Enter Keyword Spray',
        dedent('''\
            def int allowmixing = 0;
            def int object = 0;
            def int class = 0;
            def int package = 0;
            def int impl = 0;
            def int public = 0;
            def int export = 0;
            def int struct = 0;
            def int module = 0;
            def int const = 0;
            state Root {
                [*] -> Work;
                state Work {
                    enter {
                        allowmixing = 1;
                        object = 2;
                        class = 3;
                        package = 4;
                        impl = 5;
                        public = 6;
                        export = 7;
                        struct = 8;
                        module = 9;
                        const = 10;
                    }
                }
            }
        '''),
    ),
    (
        '37. Exit Keyword Spray',
        dedent('''\
            def int allowmixing = 0;
            def int boundary = 0;
            def int type = 0;
            def int trait = 0;
            def int private = 0;
            def int interface = 0;
            def int nullptr = 0;
            def int end = 0;
            def int let = 0;
            state Root {
                [*] -> Work;
                state Work {
                    exit {
                        allowmixing = 1;
                        boundary = 2;
                        type = 3;
                        trait = 4;
                        private = 5;
                        interface = 6;
                        nullptr = 7;
                        end = 8;
                        let = 9;
                    }
                }
            }
        '''),
    ),
    (
        '38. Composite During-Before Keyword Spray',
        dedent('''\
            def int allowmixing = 0;
            def int annotation = 0;
            def int func = 0;
            def int pub = 0;
            def int protected = 0;
            def int namespace = 0;
            def int typedef = 0;
            def int function = 0;
            def int module = 0;
            state Root {
                [*] -> Work;
                during before {
                    allowmixing = 1;
                    annotation = 2;
                    func = 3;
                    pub = 4;
                    protected = 5;
                    namespace = 6;
                    typedef = 7;
                    function = 8;
                    module = 9;
                }
                state Work;
            }
        '''),
    ),
    (
        '39. Composite During-After Keyword Spray',
        dedent('''\
            def int allowmixing = 0;
            def int database = 0;
            def int var = 0;
            def int impl = 0;
            def int public = 0;
            def int globalThis = 0;
            def int struct = 0;
            def int module = 0;
            def int try = 0;
            state Root {
                [*] -> Work;
                during after {
                    allowmixing = 1;
                    database = 2;
                    var = 3;
                    impl = 4;
                    public = 5;
                    globalThis = 6;
                    struct = 7;
                    module = 8;
                    try = 9;
                }
                state Work;
            }
        '''),
    ),
    (
        '40. Aspect-Before Keyword Spray',
        dedent('''\
            def int allowmixing = 0;
            def int object = 0;
            def int class = 0;
            def int package = 0;
            def int impl = 0;
            def int public = 0;
            def int export = 0;
            def int struct = 0;
            def int module = 0;
            def int const = 0;
            state Root {
                [*] -> Work;
                state Work {
                    >> during before {
                        allowmixing = 1;
                        object = 2;
                        class = 3;
                        package = 4;
                        impl = 5;
                        public = 6;
                        export = 7;
                        struct = 8;
                        module = 9;
                        const = 10;
                    }
                }
            }
        '''),
    ),
    (
        '41. Aspect-After Keyword Spray',
        dedent('''\
            def int allowmixing = 0;
            def int boundary = 0;
            def int type = 0;
            def int trait = 0;
            def int private = 0;
            def int interface = 0;
            def int nullptr = 0;
            def int end = 0;
            def int let = 0;
            state Root {
                [*] -> Work;
                >> during after {
                    allowmixing = 1;
                    boundary = 2;
                    type = 3;
                    trait = 4;
                    private = 5;
                    interface = 6;
                    nullptr = 7;
                    end = 8;
                    let = 9;
                }
                state Work;
            }
        '''),
    ),
    (
        '42. Entry Effect Keyword Spray',
        dedent('''\
            def int allowmixing = 0;
            def int annotation = 0;
            def int func = 0;
            def int pub = 0;
            def int protected = 0;
            def int namespace = 0;
            def int typedef = 0;
            def int function = 0;
            def int module = 0;
            state Root {
                [*] -> Work effect {
                    allowmixing = 1;
                    annotation = 2;
                    func = 3;
                    pub = 4;
                    protected = 5;
                    namespace = 6;
                    typedef = 7;
                    function = 8;
                    module = 9;
                }
                state Work;
            }
        '''),
    ),
    (
        '43. Normal Effect Keyword Spray',
        dedent('''\
            def int allowmixing = 0;
            def int database = 0;
            def int var = 0;
            def int impl = 0;
            def int public = 0;
            def int globalThis = 0;
            def int struct = 0;
            def int module = 0;
            def int try = 0;
            state Root {
                [*] -> A;
                A -> B effect {
                    allowmixing = 1;
                    database = 2;
                    var = 3;
                    impl = 4;
                    public = 5;
                    globalThis = 6;
                    struct = 7;
                    module = 8;
                    try = 9;
                }
                state A;
                state B;
            }
        '''),
    ),
    (
        '44. Exit Effect Keyword Spray',
        dedent('''\
            def int allowmixing = 0;
            def int object = 0;
            def int class = 0;
            def int package = 0;
            def int impl = 0;
            def int public = 0;
            def int export = 0;
            def int struct = 0;
            def int module = 0;
            def int const = 0;
            state Root {
                [*] -> A;
                A -> [*] effect {
                    allowmixing = 1;
                    object = 2;
                    class = 3;
                    package = 4;
                    impl = 5;
                    public = 6;
                    export = 7;
                    struct = 8;
                    module = 9;
                    const = 10;
                }
                state A;
            }
        '''),
    ),
    (
        '45. Nested Effect Keyword Spray',
        dedent('''\
            def int allowmixing = 0;
            def int boundary = 0;
            def int type = 0;
            def int trait = 0;
            def int private = 0;
            def int interface = 0;
            def int nullptr = 0;
            def int end = 0;
            def int let = 0;
            state Root {
                [*] -> A;
                state A {
                    [*] -> B;
                    B -> C effect {
                        allowmixing = 1;
                        boundary = 2;
                        type = 3;
                        trait = 4;
                        private = 5;
                        interface = 6;
                        nullptr = 7;
                        end = 8;
                        let = 9;
                    }
                    state B;
                    state C;
                }
            }
        '''),
    ),
    (
        '46. Foreign-Named Transition Chain',
        dedent('''\
            state Root {
                [*] -> allowmixing;
                allowmixing -> do;
                object -> class;
                package -> impl;
                public -> export;
                struct -> module;
                const -> do;
                state allowmixing;
                state do;
                state object;
                state class;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module;
                state const;
            }
        '''),
    ),
    (
        '47. Forced Foreign-Named Transition Chain',
        dedent('''\
            state Root {
                [*] -> allowmixing;
                ! object -> class;
                allowmixing -> do;
                package -> impl;
                public -> export;
                struct -> module;
                const -> do;
                state allowmixing;
                state object;
                state class;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module;
                state const;
                state do;
            }
        '''),
    ),
    (
        '48. All-Force Into Do',
        dedent('''\
            state Root {
                [*] -> object;
                ! * -> do;
                allowmixing -> class;
                package -> impl;
                public -> export;
                struct -> module;
                const -> do;
                state object;
                state do;
                state allowmixing;
                state class;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module;
                state const;
            }
        '''),
    ),
    (
        '49. Exit Cascade With Keyword Sources',
        dedent('''\
            state Root {
                [*] -> allowmixing;
                class -> [*];
                object -> class;
                package -> impl;
                public -> do;
                struct -> module;
                state allowmixing;
                state class;
                state object;
                state package;
                state impl;
                state public;
                state struct;
                state module;
                state do;
            }
        '''),
    ),
    (
        '50. Class Colon Trap',
        dedent('''\
            state Root {
                [*] -> class;
                class -> do :
                    /Tick;
                allowmixing -> object;
                package -> impl;
                public -> export;
                struct -> module;
                state class;
                state do;
                state allowmixing;
                state object;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module;
            }
        '''),
    ),
    (
        '51. For Colon Trap',
        dedent('''\
            state Root {
                [*] -> for;
                for -> do :
                    /Tick;
                allowmixing -> object;
                package -> impl;
                public -> export;
                struct -> module;
                state for;
                state do;
                state allowmixing;
                state object;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module;
            }
        '''),
    ),
    (
        '52. Finally Colon Trap',
        dedent('''\
            state Root {
                [*] -> finally;
                finally -> do :
                    /Tick;
                allowmixing -> object;
                class -> package;
                impl -> public;
                export -> struct;
                state finally;
                state do;
                state allowmixing;
                state object;
                state class;
                state package;
                state impl;
                state public;
                state export;
                state struct;
            }
        '''),
    ),
    (
        '53. Scoped Event GlobalThis',
        dedent('''\
            state Root {
                [*] -> allowmixing;
                object -> class :: globalThis;
                package -> impl;
                public -> export;
                struct -> module;
                const -> do;
                state allowmixing;
                state object;
                state class;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module;
                state const;
                state do;
            }
        '''),
    ),
    (
        '54. Absolute Event `java.util.function`',
        dedent('''\
            state Root {
                [*] -> allowmixing;
                allowmixing -> do : /java.util.function;
                object -> class;
                package -> impl;
                public -> export;
                struct -> module;
                state allowmixing;
                state do;
                state object;
                state class;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module;
                state java {
                    [*] -> util;
                    state util;
                }
            }
        '''),
    ),
    (
        '55. Absolute Event `String.raw`',
        dedent('''\
            state Root {
                [*] -> allowmixing;
                allowmixing -> do : /String.raw;
                object -> class;
                package -> impl;
                public -> export;
                struct -> module;
                state allowmixing;
                state do;
                state object;
                state class;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module;
                state String;
            }
        '''),
    ),
    (
        '56. Ref Path `globalThis.bridge`',
        dedent('''\
            state Root {
                [*] -> allowmixing;
                allowmixing -> do;
                object -> class;
                package -> impl;
                public -> export;
                struct -> module;
                state allowmixing;
                state do;
                state object;
                state class;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module;
                state globalThis {
                    enter abstract bridge;
                }
                state Worker {
                    enter alias ref /globalThis.bridge;
                }
            }
        '''),
    ),
    (
        '57. Ref Path `String.raw`',
        dedent('''\
            state Root {
                [*] -> allowmixing;
                allowmixing -> do;
                object -> class;
                package -> impl;
                public -> export;
                struct -> module;
                state allowmixing;
                state do;
                state object;
                state class;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module;
                state String {
                    exit abstract raw;
                }
                state Worker {
                    exit alias ref /String.raw;
                }
            }
        '''),
    ),
    (
        '58. Ref Path `java.util.function`',
        dedent('''\
            state Root {
                [*] -> allowmixing;
                allowmixing -> do;
                object -> class;
                package -> impl;
                public -> export;
                struct -> module;
                state allowmixing;
                state do;
                state object;
                state class;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module;
                state java {
                    [*] -> util;
                    state util {
                        enter abstract function;
                    }
                }
                state Worker {
                    enter alias ref /java.util.function;
                }
            }
        '''),
    ),
    (
        '59. Dense Pseudo-Named-Abstract-Ref-Effect Line',
        dedent('''\
            def int allowmixing = 0;
            def int object = 0;
            def int class = 0;
            def int package = 0;
            def int impl = 0;
            def int public = 0;
            def int export = 0;
            def int struct = 0;
            def int module = 0;
            def int const = 0;
            state Root {
                pseudo state Meta named "m"; [*] -> allowmixing effect { allowmixing = 1; object = 2; class = 3; package = 4; impl = 5; public = 6; export = 7; struct = 8; module = 9; const = 10; } enter abstract hook; exit alias ref hook;
                allowmixing -> do;
                state allowmixing {
                    enter {
                        allowmixing = 1;
                        object = 2;
                        class = 3;
                        package = 4;
                        impl = 5;
                        public = 6;
                        export = 7;
                        struct = 8;
                        module = 9;
                        const = 10;
                    }
                }
                state do;
            }
        '''),
    ),
    (
        '60. Dense Line Plus `String.raw` Ref',
        dedent('''\
            def int allowmixing = 0;
            def int boundary = 0;
            def int type = 0;
            def int trait = 0;
            def int private = 0;
            def int interface = 0;
            def int nullptr = 0;
            def int end = 0;
            def int let = 0;
            state Root {
                pseudo state Meta named "m"; [*] -> Work effect { allowmixing = 1; boundary = 2; type = 3; trait = 4; private = 5; interface = 6; nullptr = 7; end = 8; let = 9; } enter abstract hook; state String { exit abstract raw; } state Work { exit alias ref /String.raw; }
                allowmixing -> do;
                state allowmixing;
                state do;
                state Sink {
                    exit {
                        allowmixing = 1;
                        boundary = 2;
                        type = 3;
                        trait = 4;
                        private = 5;
                        interface = 6;
                        nullptr = 7;
                        end = 8;
                        let = 9;
                    }
                }
            }
        '''),
    ),
    (
        '61. Dense Line Plus `java.util.function` Event',
        dedent('''\
            def int allowmixing = 0;
            def int annotation = 0;
            def int func = 0;
            def int pub = 0;
            def int protected = 0;
            def int namespace = 0;
            def int typedef = 0;
            def int function = 0;
            def int module = 0;
            state Root {
                pseudo state Meta named "m"; [*] -> Work effect { allowmixing = 1; annotation = 2; func = 3; pub = 4; protected = 5; namespace = 6; typedef = 7; function = 8; module = 9; } enter abstract hook; exit alias ref hook; state java { [*] -> util; state util; } state Work;
                allowmixing -> do : /java.util.function;
                state allowmixing;
                state do;
                >> during after {
                    allowmixing = 1;
                    annotation = 2;
                    func = 3;
                    pub = 4;
                    protected = 5;
                    namespace = 6;
                    typedef = 7;
                    function = 8;
                    module = 9;
                }
            }
        '''),
    ),
    (
        '62. Pseudo Sibling Plus Keyword Chain',
        dedent('''\
            state Root {
                [*] -> allowmixing;
                allowmixing -> do;
                object -> class;
                package -> impl;
                public -> export;
                struct -> module;
                pseudo state pseudoNode;
                state allowmixing;
                state do;
                state object;
                state class;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module;
            }
        '''),
    ),
    (
        '63. Named State Plus Local Event Keyword Bait',
        dedent('''\
            state Root {
                [*] -> allowmixing;
                allowmixing -> do;
                object -> class :: globalThis;
                package -> impl;
                public -> export;
                struct -> module;
                state allowmixing named "live";
                state do;
                state object;
                state class;
                state package;
                state impl;
                state public;
                state export named "pub";
                state struct;
                state module;
            }
        '''),
    ),
    (
        '64. Deep Hierarchy Keyword Parents',
        dedent('''\
            state Root {
                [*] -> allowmixing;
                allowmixing -> do : /module.const.Tick;
                object -> class;
                package -> impl;
                public -> export;
                struct -> module;
                state allowmixing;
                state do;
                state object;
                state class;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module {
                    [*] -> const;
                    state const;
                }
            }
        '''),
    ),
    (
        '65. Mixed Ref And Colon Trap',
        dedent('''\
            state Root {
                [*] -> class;
                class -> do :
                    /namespace.Tick;
                allowmixing -> object;
                package -> impl;
                public -> export;
                struct -> module;
                state class;
                state do;
                state allowmixing;
                state object;
                state package;
                state impl;
                state public;
                state export;
                state struct;
                state module;
                state globalThis {
                    enter abstract bridge;
                }
                state Worker {
                    enter alias ref /globalThis.bridge;
                }
                state namespace;
            }
        '''),
    ),
    (
        '66. Elevator Door Reopen Cycle',
        dedent('''\
            // Elevator door controller with obstruction reopen logic
            def int door_pos = 0;
            def int hold_ticks = 0;
            def int reopen_count = 0;

            state ElevatorDoor {
                state Closed;

                state Opening {
                    during {
                        door_pos = door_pos + 50;
                    }
                }

                state Opened {
                    during {
                        hold_ticks = hold_ticks + 1;
                    }
                }

                state Closing {
                    during {
                        door_pos = door_pos - 50;
                    }
                }

                [*] -> Closed;
                Closed -> Opening : HallCall effect {
                    hold_ticks = 0;
                };
                Opening -> Opened : if [door_pos >= 100] effect {
                    door_pos = 100;
                    hold_ticks = 0;
                };
                Opened -> Closing : if [hold_ticks >= 2];
                Closing -> Opened : BeamBlocked effect {
                    reopen_count = reopen_count + 1;
                    door_pos = 100;
                    hold_ticks = 0;
                };
                Closing -> Closed : if [door_pos <= 0] effect {
                    door_pos = 0;
                };
            }
        '''),
    ),
    (
        '67. Two-Phase Traffic Signal',
        dedent('''\
            // Main road plus pedestrian request phase
            def int green_ticks = 0;
            def int yellow_ticks = 0;
            def int walk_ticks = 0;
            def int ped_waiting = 0;

            state TrafficSignal {
                state MainGreen {
                    during {
                        green_ticks = green_ticks + 1;
                    }
                }

                state PedestrianPhase {
                    state MainYellow {
                        during {
                            yellow_ticks = yellow_ticks + 1;
                        }
                    }

                    state Walk {
                        during {
                            walk_ticks = walk_ticks + 1;
                        }
                    }

                    [*] -> MainYellow;
                    MainYellow -> Walk : if [yellow_ticks >= 1];
                    Walk -> [*] : if [walk_ticks >= 2];
                }

                [*] -> MainGreen;
                MainGreen -> PedestrianPhase : if [ped_waiting == 1 && green_ticks >= 3] effect {
                    ped_waiting = 0;
                    yellow_ticks = 0;
                    walk_ticks = 0;
                };
                MainGreen -> MainGreen : PedestrianRequest effect {
                    ped_waiting = 1;
                };
                PedestrianPhase -> MainGreen effect {
                    green_ticks = 0;
                };
            }
        '''),
    ),
    (
        '68. Water Tank Fill Controller',
        dedent('''\
            // Maintain tank level and stop on overflow
            def int level = 55;
            def int fill_cycles = 0;
            def int overflow_count = 0;

            state WaterTank {
                state Idle {
                    during {
                        level = level - 1;
                    }
                }

                state Filling {
                    during {
                        level = level + 4;
                        fill_cycles = fill_cycles + 1;
                    }
                }

                state Alarm {
                    enter {
                        overflow_count = overflow_count + 1;
                    }
                }

                [*] -> Idle;
                Idle -> Filling : if [level <= 40];
                Filling -> Idle : if [level >= 70];
                Filling -> Alarm : if [level > 90];
                Alarm -> Idle : Reset effect {
                    level = 60;
                };
            }
        '''),
    ),
    (
        '69. Batch Mixer Recipe Flow',
        dedent('''\
            // Mixing skid with load, mix and discharge phases
            def int mix_ticks = 0;
            def int discharge_ticks = 0;
            def int batch_count = 0;

            state MixerSkid {
                state Ready;

                state BatchCycle {
                    state Load {
                        enter {
                            mix_ticks = 0;
                            discharge_ticks = 0;
                        }
                    }

                    state Mix {
                        during {
                            mix_ticks = mix_ticks + 1;
                        }
                    }

                    state Discharge {
                        during {
                            discharge_ticks = discharge_ticks + 1;
                        }
                    }

                    [*] -> Load;
                    Load -> Mix : IngredientsReady;
                    Mix -> Discharge : if [mix_ticks >= 3];
                    Discharge -> [*] : if [discharge_ticks >= 2];
                }

                [*] -> Ready;
                Ready -> BatchCycle : StartBatch;
                BatchCycle -> Ready effect {
                    batch_count = batch_count + 1;
                };
            }
        '''),
    ),
    (
        '70. Turnstile Entry Control',
        dedent('''\
            // Standard paid-entry turnstile
            def int passage_count = 0;
            def int alarm_count = 0;

            state Turnstile {
                state Locked;
                state Unlocked;

                state Alarm {
                    enter {
                        alarm_count = alarm_count + 1;
                    }
                }

                [*] -> Locked;
                Locked -> Unlocked : Coin;
                Locked -> Alarm : Push;
                Unlocked -> Locked : Push effect {
                    passage_count = passage_count + 1;
                };
                Alarm -> Locked : Reset;
            }
        '''),
    ),
    (
        '71. Vending Machine Dispense Cycle',
        dedent('''\
            // Simple snack vending workflow
            def int credit = 0;
            def int stock = 5;
            def int vend_count = 0;

            state VendingMachine {
                state Idle;

                state CreditReady {
                    during {
                        credit = credit + 0;
                    }
                }

                state Dispensing {
                    enter {
                        stock = stock - 1;
                        vend_count = vend_count + 1;
                    }
                }

                state OutOfService;

                [*] -> Idle;
                Idle -> CreditReady : InsertCoin effect {
                    credit = credit + 1;
                };
                CreditReady -> Dispensing : SelectItem effect {
                    credit = credit - 1;
                };
                Dispensing -> Idle : DispenseDone;
                Dispensing -> OutOfService : if [stock <= 0];
                OutOfService -> Idle : Refill effect {
                    stock = 5;
                };
            }
        '''),
    ),
    (
        '72. Smart Lock Auto Relock',
        dedent('''\
            // Badge access lock with timed relock
            def int relock_ticks = 0;
            def int invalid_tries = 0;

            state SmartLock {
                state Locked;

                state Unlocked {
                    during {
                        relock_ticks = relock_ticks + 1;
                    }
                }

                state Alarm {
                    enter {
                        invalid_tries = invalid_tries + 1;
                    }
                }

                [*] -> Locked;
                Locked -> Unlocked : ValidBadge effect {
                    relock_ticks = 0;
                };
                Locked -> Alarm : InvalidBadge;
                Unlocked -> Locked : if [relock_ticks >= 3];
                Alarm -> Locked : MasterReset effect {
                    invalid_tries = 0;
                };
            }
        '''),
    ),
    (
        '73. Conveyor Jam Recovery',
        dedent('''\
            // Conveyor with manual jam clearing sequence
            def int run_ticks = 0;
            def int clear_ticks = 0;
            def int jam_count = 0;

            state ConveyorLine {
                state Stopped;

                state Running {
                    during {
                        run_ticks = run_ticks + 1;
                    }
                }

                state Jam {
                    enter {
                        jam_count = jam_count + 1;
                    }
                }

                state Clearing {
                    during {
                        clear_ticks = clear_ticks + 1;
                    }
                }

                [*] -> Stopped;
                Stopped -> Running : StartCommand effect {
                    run_ticks = 0;
                };
                Running -> Stopped : StopCommand;
                Running -> Jam : JamDetected;
                Jam -> Clearing : ClearJam effect {
                    clear_ticks = 0;
                };
                Clearing -> Running : if [clear_ticks >= 2] effect {
                    run_ticks = 0;
                };
            }
        '''),
    ),
    (
        '74. HVAC Occupancy Scheduler',
        dedent('''\
            // Occupancy-based zone conditioning schedule
            def int setpoint = 26;
            def int prestart_ticks = 0;
            def int occupied_ticks = 0;

            state ZoneScheduler {
                event OccupancyStart named "occupancy-start";
                event OccupancyEnd named "occupancy-end";

                state Unoccupied {
                    during {
                        prestart_ticks = prestart_ticks + 1;
                    }
                }

                state PreCool {
                    during {
                        setpoint = 23;
                    }
                }

                state Occupied named "day-mode" {
                    during {
                        occupied_ticks = occupied_ticks + 1;
                    }
                }

                [*] -> Unoccupied;
                Unoccupied -> PreCool : if [prestart_ticks >= 2];
                PreCool -> Occupied : OccupancyStart effect {
                    occupied_ticks = 0;
                };
                Occupied -> Unoccupied : OccupancyEnd effect {
                    setpoint = 26;
                    prestart_ticks = 0;
                };
            }
        '''),
    ),
    (
        '75. Battery Charger Three Stage',
        dedent('''\
            // Bulk, absorption and float charging controller
            def int pack_voltage = 300;
            def int charge_ticks = 0;
            def int temp_c = 25;
            def int fault_count = 0;

            state BatteryCharger {
                state Idle;

                state Bulk {
                    during {
                        pack_voltage = pack_voltage + 20;
                        charge_ticks = charge_ticks + 1;
                    }
                }

                state Absorption {
                    during {
                        pack_voltage = pack_voltage + 5;
                        charge_ticks = charge_ticks + 1;
                    }
                }

                state Float;

                state Fault {
                    enter {
                        fault_count = fault_count + 1;
                    }
                }

                [*] -> Idle;
                Idle -> Bulk : PlugIn effect {
                    charge_ticks = 0;
                };
                Bulk -> Absorption : if [pack_voltage >= 360];
                Absorption -> Float : if [charge_ticks >= 4];
                Bulk -> Fault : if [temp_c > 60];
                Absorption -> Fault : if [temp_c > 60];
                Float -> Idle : Unplug;
                Fault -> Idle : Reset effect {
                    temp_c = 25;
                };
            }
        '''),
    ),
    (
        '76. Garage Door Obstacle Handling',
        dedent('''\
            // Residential garage door with obstacle reversal
            def int travel = 0;
            def int open_hold = 0;

            state GarageDoor named "garage-door" {
                event RemotePulse named "remote-pulse";
                state Closed;

                state Opening {
                    during {
                        travel = travel + 25;
                    }
                }

                state Open {
                    during {
                        open_hold = open_hold + 1;
                    }
                }

                state Closing {
                    during {
                        travel = travel - 25;
                    }
                }

                [*] -> Closed;
                Closed -> Opening : RemotePulse;
                Opening -> Open : if [travel >= 100] effect {
                    travel = 100;
                    open_hold = 0;
                };
                Open -> Closing : if [open_hold >= 2];
                Closing -> Opening : Obstruction effect {
                    travel = 25;
                };
                Closing -> Closed : if [travel <= 0] effect {
                    travel = 0;
                };
            }
        '''),
    ),
    (
        '77. Printer Job Lifecycle',
        dedent('''\
            // Office printer with pause and jam handling
            def int pages_left = 0;
            def int completed_jobs = 0;
            def int error_count = 0;

            state PrintServer {
                state Idle;

                state Printing {
                    during {
                        pages_left = pages_left - 1;
                    }
                }

                state Paused;

                state Error {
                    enter {
                        error_count = error_count + 1;
                    }
                }

                [*] -> Idle;
                Idle -> Printing : SubmitJob effect {
                    pages_left = 3;
                };
                Printing -> Paused : PauseJob;
                Paused -> Printing : ResumeJob;
                Printing -> Idle : if [pages_left <= 0] effect {
                    completed_jobs = completed_jobs + 1;
                };
                Printing -> Error : JamDetected;
                Error -> Idle : ClearJam effect {
                    pages_left = 0;
                };
            }
        '''),
    ),
    (
        '78. Network Link Reconnect Backoff',
        dedent('''\
            // Client retries with an increasing reconnect delay
            def int retries = 0;
            def int backoff_ticks = 0;
            def int online_ticks = 0;

            state NetworkClient {
                state Disconnected;
                state Connecting;

                state Online {
                    during {
                        online_ticks = online_ticks + 1;
                    }
                }

                state Backoff {
                    during {
                        backoff_ticks = backoff_ticks + 1;
                    }
                }

                [*] -> Disconnected;
                Disconnected -> Connecting : StartLink;
                Connecting -> Online : LinkUp effect {
                    retries = 0;
                    online_ticks = 0;
                };
                Connecting -> Backoff : LinkFailed effect {
                    retries = retries + 1;
                    backoff_ticks = 0;
                };
                Online -> Connecting : LinkDropped;
                Backoff -> Connecting : if [backoff_ticks >= retries + 1];
            }
        '''),
    ),
    (
        '79. Boiler Burner Lockout',
        dedent('''\
            // Burner start-up with purge, ignition and lockout
            def int purge_ticks = 0;
            def int trial_count = 0;
            def int run_ticks = 0;
            def int lockouts = 0;

            state BoilerBurner {
                state Idle;

                state Purge {
                    during {
                        purge_ticks = purge_ticks + 1;
                    }
                }

                state Igniting;

                state Run {
                    during {
                        run_ticks = run_ticks + 1;
                    }
                }

                state Lockout {
                    enter {
                        lockouts = lockouts + 1;
                    }
                }

                [*] -> Idle;
                Idle -> Purge : HeatDemand effect {
                    purge_ticks = 0;
                };
                Purge -> Igniting : if [purge_ticks >= 2];
                Igniting -> Run : FlameProven effect {
                    run_ticks = 0;
                };
                Igniting -> Lockout : IgnitionFailed effect {
                    trial_count = trial_count + 1;
                };
                Run -> Idle : DemandSatisfied;
                Lockout -> Idle : ResetBurner effect {
                    trial_count = 0;
                };
            }
        '''),
    ),
    (
        '80. EV Charger Session Flow',
        dedent('''\
            // Public charger session from plug-in to fault reset
            def int energy_pulses = 0;
            def int auth_ok = 0;
            def int fault_count = 0;

            state EVCharger {
                state Available;
                state Handshake;

                state Charging {
                    during {
                        energy_pulses = energy_pulses + 1;
                    }
                }

                state Fault {
                    enter {
                        fault_count = fault_count + 1;
                    }
                }

                [*] -> Available;
                Available -> Handshake : PlugIn;
                Handshake -> Charging : Authorize effect {
                    auth_ok = 1;
                    energy_pulses = 0;
                };
                Handshake -> Available : CancelSession;
                Charging -> Available : Unplug effect {
                    auth_ok = 0;
                };
                Charging -> Fault : GroundFault;
                Fault -> Available : ResetFault effect {
                    auth_ok = 0;
                };
            }
        '''),
    ),
    (
        '81. Refrigerator Defrost Cycle',
        dedent('''\
            // Refrigeration loop with defrost and drain wait
            def int compressor_ticks = 0;
            def int frost_level = 0;
            def int drain_ticks = 0;

            state Refrigerator {
                state Cooling {
                    during {
                        compressor_ticks = compressor_ticks + 1;
                        frost_level = frost_level + 1;
                    }
                }

                state Defrost {
                    during {
                        frost_level = frost_level - 2;
                    }
                }

                state DrainWait {
                    during {
                        drain_ticks = drain_ticks + 1;
                    }
                }

                [*] -> Cooling;
                Cooling -> Defrost : if [frost_level >= 5] effect {
                    drain_ticks = 0;
                };
                Defrost -> DrainWait : if [frost_level <= 0];
                DrainWait -> Cooling : if [drain_ticks >= 2] effect {
                    compressor_ticks = 0;
                };
            }
        '''),
    ),
    (
        '82. Railway Crossing Gate',
        dedent('''\
            // Road crossing gate around train approach events
            def int warning_ticks = 0;
            def int gate_cycles = 0;
            def int train_detected = 0;

            state RailCrossing {
                state Clear;

                state Warning {
                    during {
                        warning_ticks = warning_ticks + 1;
                    }
                }

                state Lowered;
                state Raising;

                [*] -> Clear;
                Clear -> Warning : TrackOccupied effect {
                    train_detected = 1;
                    warning_ticks = 0;
                };
                Warning -> Lowered : if [warning_ticks >= 2];
                Lowered -> Raising : TrackClear effect {
                    train_detected = 0;
                };
                Raising -> Clear : GateUp effect {
                    gate_cycles = gate_cycles + 1;
                };
            }
        '''),
    ),
    (
        '83. Pump Lead-Lag Swap',
        dedent('''\
            // Alternate duty between primary and secondary pumps
            def int primary_starts = 0;
            def int secondary_starts = 0;
            def int demand = 0;
            def int fault_count = 0;

            state PumpPair {
                state Standby;

                state PrimaryRun {
                    enter {
                        primary_starts = primary_starts + 1;
                    }
                }

                state SecondaryRun {
                    enter {
                        secondary_starts = secondary_starts + 1;
                    }
                }

                state Fault {
                    enter {
                        fault_count = fault_count + 1;
                    }
                }

                [*] -> Standby;
                Standby -> PrimaryRun : StartDemand effect {
                    demand = 1;
                };
                PrimaryRun -> Standby : StopDemand effect {
                    demand = 0;
                };
                PrimaryRun -> SecondaryRun : PrimaryFault;
                SecondaryRun -> Standby : StopDemand effect {
                    demand = 0;
                };
                SecondaryRun -> Fault : SecondaryFault;
                Fault -> Standby : ResetPumps;
            }
        '''),
    ),
    (
        '84. AGV Docking Procedure',
        dedent('''\
            // Automated guided vehicle docking and verification
            def int align_ticks = 0;
            def int dock_ticks = 0;
            def int mission_count = 0;
            def int dock_ok = 1;

            state AGVDocking {
                state Idle;
                state Navigate;

                state Align {
                    during {
                        align_ticks = align_ticks + 1;
                    }
                }

                pseudo state VerifyDock;

                state Docked {
                    during {
                        dock_ticks = dock_ticks + 1;
                    }
                }

                state Error;

                [*] -> Idle;
                Idle -> Navigate : DispatchToDock;
                Navigate -> Align : AtStation effect {
                    align_ticks = 0;
                };
                Align -> VerifyDock : if [align_ticks >= 2];
                VerifyDock -> Docked : if [dock_ok == 1];
                VerifyDock -> Error : if [dock_ok == 0];
                Docked -> Idle : Undock effect {
                    mission_count = mission_count + 1;
                };
                Error -> Navigate : RetryDock;
            }
        '''),
    ),
    (
        '85. Air Compressor Pressure Band',
        dedent('''\
            // Compressor starts and stops on pressure bands
            def int pressure = 85;
            def int cooldown_ticks = 0;
            def int high_temp_count = 0;

            state AirCompressor {
                state Off {
                    during {
                        pressure = pressure - 2;
                    }
                }

                state Running {
                    during {
                        pressure = pressure + 4;
                    }
                }

                state Cooldown {
                    during {
                        cooldown_ticks = cooldown_ticks + 1;
                    }
                }

                state Fault {
                    enter {
                        high_temp_count = high_temp_count + 1;
                    }
                }

                [*] -> Off;
                Off -> Running : if [pressure <= 70];
                Running -> Cooldown : if [pressure >= 95] effect {
                    cooldown_ticks = 0;
                };
                Running -> Fault : OverTemp;
                Cooldown -> Off : if [cooldown_ticks >= 2];
                Fault -> Off : ResetCompressor effect {
                    pressure = 85;
                };
            }
        '''),
    ),
    (
        '86. Security Alarm Arming Flow',
        dedent('''\
            // Intrusion panel with exit and entry delays
            def int exit_delay = 0;
            def int entry_delay = 0;
            def int siren_count = 0;

            state SecurityPanel {
                event ArmAway named "arm-away";
                event Disarm named "disarm";

                state Disarmed;

                state ExitDelay {
                    during {
                        exit_delay = exit_delay + 1;
                    }
                }

                state Armed;

                state EntryDelay {
                    during {
                        entry_delay = entry_delay + 1;
                    }
                }

                state Alarm {
                    enter {
                        siren_count = siren_count + 1;
                    }
                }

                [*] -> Disarmed;
                Disarmed -> ExitDelay : ArmAway effect {
                    exit_delay = 0;
                };
                ExitDelay -> Armed : if [exit_delay >= 2];
                Armed -> EntryDelay : DoorOpen effect {
                    entry_delay = 0;
                };
                EntryDelay -> Alarm : if [entry_delay >= 2];
                EntryDelay -> Disarmed : Disarm;
                Armed -> Disarmed : Disarm;
                Alarm -> Disarmed : Disarm;
            }
        '''),
    ),
    (
        '87. Camera Recording Policy',
        dedent('''\
            // Recorder with prebuffer, clip close and upload
            def int motion_ticks = 0;
            def int clip_count = 0;
            def int upload_ticks = 0;

            state CameraRecorder {
                event MotionStart named "motion-start";
                event MotionEnd named "motion-end";

                state Standby;

                state Prebuffer {
                    during {
                        motion_ticks = motion_ticks + 1;
                    }
                }

                state Recording {
                    during {
                        motion_ticks = motion_ticks + 1;
                    }
                }

                state Uploading {
                    during {
                        upload_ticks = upload_ticks + 1;
                    }
                }

                [*] -> Standby;
                Standby -> Prebuffer : MotionStart effect {
                    motion_ticks = 0;
                };
                Prebuffer -> Recording : if [motion_ticks >= 1];
                Recording -> Uploading : MotionEnd effect {
                    clip_count = clip_count + 1;
                    upload_ticks = 0;
                };
                Uploading -> Standby : if [upload_ticks >= 2];
            }
        '''),
    ),
    (
        '88. Solar Inverter Grid Support',
        dedent('''\
            // PV inverter from sunrise wait to generation and fault
            def int irradiance = 0;
            def int sync_ticks = 0;
            def int fault_count = 0;

            state SolarInverter {
                state WaitingSun;

                state Sync {
                    during {
                        sync_ticks = sync_ticks + 1;
                    }
                }

                state Generating {
                    during {
                        irradiance = irradiance + 0;
                    }
                }

                state Fault {
                    enter {
                        fault_count = fault_count + 1;
                    }
                }

                [*] -> WaitingSun;
                WaitingSun -> Sync : if [irradiance >= 4] effect {
                    sync_ticks = 0;
                };
                Sync -> Generating : if [sync_ticks >= 2];
                Generating -> WaitingSun : if [irradiance <= 1];
                Generating -> Fault : GridFault;
                Fault -> WaitingSun : ResetGridFault;
            }
        '''),
    ),
    (
        '89. Cleanroom Airlock Interlock',
        dedent('''\
            // Personnel airlock keeps only one door sequence active
            def int transfer_ticks = 0;
            def int cycle_count = 0;

            state Airlock named "airlock-1" {
                state Idle;
                state OuterOpen;

                state Transfer {
                    during {
                        transfer_ticks = transfer_ticks + 1;
                    }
                }

                state InnerOpen;

                [*] -> Idle;
                Idle -> OuterOpen : OuterRequest;
                OuterOpen -> Transfer : OuterClosed effect {
                    transfer_ticks = 0;
                };
                Transfer -> InnerOpen : if [transfer_ticks >= 1];
                InnerOpen -> Idle : InnerClosed effect {
                    cycle_count = cycle_count + 1;
                };
            }
        '''),
    ),
    (
        '90. Fire Pump Weekly Test',
        dedent('''\
            // Scheduled weekly churn test for a fire pump
            def int test_ticks = 0;
            def int ready_flag = 0;
            def int fail_count = 0;

            state FirePumpTest {
                state Idle;

                state Testing {
                    during {
                        test_ticks = test_ticks + 1;
                    }
                }

                state Ready {
                    enter {
                        ready_flag = 1;
                    }
                }

                state Fault {
                    enter {
                        fail_count = fail_count + 1;
                    }
                }

                [*] -> Idle;
                Idle -> Testing : WeeklySchedule effect {
                    test_ticks = 0;
                    ready_flag = 0;
                };
                Testing -> Ready : if [test_ticks >= 2];
                Testing -> Fault : TestFail;
                Ready -> Idle : TestComplete effect {
                    ready_flag = 0;
                };
                Fault -> Idle : ResetTest;
            }
        '''),
    ),
    (
        '91. Escalator Energy Save',
        dedent('''\
            // Escalator wakes on demand and idles after cooldown
            def int people_seen = 0;
            def int run_ticks = 0;
            def int cooldown_ticks = 0;

            state Escalator {
                state Sleep;
                state Starting;

                state Running {
                    during {
                        run_ticks = run_ticks + 1;
                    }
                }

                state Cooldown {
                    during {
                        cooldown_ticks = cooldown_ticks + 1;
                    }
                }

                state Fault;

                [*] -> Sleep;
                Sleep -> Starting : PersonDetected effect {
                    people_seen = people_seen + 1;
                };
                Starting -> Running : MotorReady effect {
                    run_ticks = 0;
                };
                Running -> Cooldown : NoPassenger effect {
                    cooldown_ticks = 0;
                };
                Cooldown -> Sleep : if [cooldown_ticks >= 2];
                Running -> Fault : SafetyTrip;
                Fault -> Sleep : ResetEscalator;
            }
        '''),
    ),
    (
        '92. Pipeline Valve Remote Local',
        dedent('''\
            // Remote/local handover for a pipeline block valve
            def int command_source = 0;
            def int cycle_count = 0;

            state PipelineValve named "remote-valve" {
                event RemoteOpen named "remote-open";
                event RemoteClose named "remote-close";

                state Local;
                state RemoteClosed named "closed";
                state RemoteOpenState named "open";

                [*] -> Local;
                Local -> RemoteClosed : HandToRemote effect {
                    command_source = 1;
                };
                RemoteClosed -> RemoteOpenState : RemoteOpen effect {
                    cycle_count = cycle_count + 1;
                };
                RemoteOpenState -> RemoteClosed : RemoteClose effect {
                    cycle_count = cycle_count + 1;
                };
                RemoteClosed -> Local : HandToLocal effect {
                    command_source = 0;
                };
                RemoteOpenState -> Local : HandToLocal effect {
                    command_source = 0;
                };
            }
        '''),
    ),
    (
        '93. Medical Infusion Pump',
        dedent('''\
            // Infusion pump from prime to infusion and KVO
            def int prime_ticks = 0;
            def int volume_left = 20;
            def int alarm_count = 0;

            state InfusionPump {
                state Idle;

                state Priming {
                    during {
                        prime_ticks = prime_ticks + 1;
                    }
                }

                state Infusing {
                    during {
                        volume_left = volume_left - 2;
                    }
                }

                state KVO;

                state Alarm {
                    enter {
                        alarm_count = alarm_count + 1;
                    }
                }

                [*] -> Idle;
                Idle -> Priming : StartSet effect {
                    prime_ticks = 0;
                    volume_left = 20;
                };
                Priming -> Infusing : if [prime_ticks >= 2];
                Infusing -> KVO : if [volume_left <= 0];
                Infusing -> Alarm : OcclusionDetected;
                KVO -> Idle : StopInfusion;
                Alarm -> Idle : AcknowledgeAlarm;
            }
        '''),
    ),
    (
        '94. Data Center UPS Transfer',
        dedent('''\
            // UPS transfers between mains, battery and bypass
            def int battery_level = 100;
            def int transfer_count = 0;
            def int bypass_count = 0;

            state UPSController {
                state Normal {
                    during {
                        battery_level = battery_level + 0;
                    }
                }

                state OnBattery {
                    during {
                        battery_level = battery_level - 5;
                    }
                }

                state Bypass {
                    enter {
                        bypass_count = bypass_count + 1;
                    }
                }

                state Fault;

                [*] -> Normal;
                Normal -> OnBattery : MainsLost effect {
                    transfer_count = transfer_count + 1;
                };
                OnBattery -> Normal : MainsRestored;
                OnBattery -> Bypass : if [battery_level <= 20];
                OnBattery -> Fault : BatteryFault;
                Bypass -> Normal : ManualReturn;
                Fault -> Normal : ResetUPS effect {
                    battery_level = 100;
                };
            }
        '''),
    ),
    (
        '95. Warehouse Sorter Merge',
        dedent('''\
            // Merge sorter alternates between induction and diverting
            def int cartons_seen = 0;
            def int divert_ticks = 0;
            def int jam_count = 0;

            state SorterMerge {
                state Idle;

                state Inducting {
                    during {
                        cartons_seen = cartons_seen + 1;
                    }
                }

                state Diverting {
                    during {
                        divert_ticks = divert_ticks + 1;
                    }
                }

                state Jam {
                    enter {
                        jam_count = jam_count + 1;
                    }
                }

                [*] -> Idle;
                Idle -> Inducting : StartWave;
                Inducting -> Diverting : DivertCommand effect {
                    divert_ticks = 0;
                };
                Diverting -> Inducting : if [divert_ticks >= 1];
                Inducting -> Jam : MergeBlocked;
                Jam -> Idle : ClearSorter;
            }
        '''),
    ),
    (
        '96. Robot Cell Maintenance Mode',
        dedent('''\
            // Robot cell switches between auto, manual and fault states
            def int part_count = 0;
            def int fault_count = 0;

            state RobotCell {
                enter abstract LockCell;
                exit abstract UnlockCell;
                >> during before abstract AuditCell;

                state Auto {
                    state Load;

                    state Process {
                        during {
                            part_count = part_count + 1;
                        }
                    }

                    [*] -> Load;
                    Load -> Process : PartPresent;
                    Process -> Load : CycleComplete;
                }

                state Manual {
                    enter ref /LockCell;
                    exit ref /UnlockCell;
                }

                state Fault {
                    enter {
                        fault_count = fault_count + 1;
                    }
                }

                [*] -> Auto;
                Auto -> Manual : MaintenanceRequest;
                Manual -> Auto : ResumeAuto;
                Auto -> Fault : SafetyGateOpen;
                Fault -> Manual : ResetCell;
            }
        '''),
    ),
    (
        '97. Heat Pump Defrost Recovery',
        dedent('''\
            // Heat pump periodically defrosts the outdoor coil
            def int coil_temp = -5;
            def int defrost_ticks = 0;
            def int room_heat = 0;

            state HeatPump {
                state Heating {
                    during {
                        coil_temp = coil_temp - 1;
                        room_heat = room_heat + 1;
                    }
                }

                state Defrost {
                    during {
                        coil_temp = coil_temp + 3;
                        defrost_ticks = defrost_ticks + 1;
                    }
                }

                state DripDelay {
                    during {
                        defrost_ticks = defrost_ticks + 1;
                    }
                }

                state Fault;

                [*] -> Heating;
                Heating -> Defrost : if [coil_temp <= -10] effect {
                    defrost_ticks = 0;
                };
                Defrost -> DripDelay : if [coil_temp >= 2] effect {
                    defrost_ticks = 0;
                };
                DripDelay -> Heating : if [defrost_ticks >= 1];
                Heating -> Fault : SensorFault;
                Fault -> Heating : ResetHeatPump effect {
                    coil_temp = -5;
                };
            }
        '''),
    ),
    (
        '98. Reactor Temperature Control',
        dedent('''\
            // Batch reactor with heat, hold and cool phases
            def int temp = 20;
            def int hold_ticks = 0;
            def int batch_done = 0;

            state ReactorControl {
                state Idle;

                state Batch {
                    state Heat {
                        during {
                            temp = temp + 10;
                        }
                    }

                    state Hold {
                        during {
                            hold_ticks = hold_ticks + 1;
                        }
                    }

                    state Cool {
                        during {
                            temp = temp - 8;
                        }
                    }

                    [*] -> Heat;
                    Heat -> Hold : if [temp >= 80] effect {
                        hold_ticks = 0;
                    };
                    Hold -> Cool : if [hold_ticks >= 3];
                    Cool -> [*] : if [temp <= 30];
                }

                state Abort;

                [*] -> Idle;
                Idle -> Batch : StartBatch effect {
                    temp = 20;
                };
                Batch -> Idle effect {
                    batch_done = batch_done + 1;
                };
                Batch -> Abort : EmergencyStop;
                Abort -> Idle : ResetReactor effect {
                    temp = 20;
                };
            }
        '''),
    ),
    (
        '99. Loading Dock Leveler',
        dedent('''\
            // Dock leveler deploys, serves a truck and returns home
            def int platform_pos = 0;
            def int service_ticks = 0;
            def int fault_count = 0;

            state DockLeveler {
                state Stored;

                state Deploying {
                    during {
                        platform_pos = platform_pos + 50;
                    }
                }

                state Service {
                    during {
                        service_ticks = service_ticks + 1;
                    }
                }

                state Returning {
                    during {
                        platform_pos = platform_pos - 50;
                    }
                }

                state Fault {
                    enter {
                        fault_count = fault_count + 1;
                    }
                }

                [*] -> Stored;
                Stored -> Deploying : DockTruck;
                Deploying -> Service : if [platform_pos >= 100] effect {
                    platform_pos = 100;
                    service_ticks = 0;
                };
                Service -> Returning : LoadComplete;
                Returning -> Stored : if [platform_pos <= 0] effect {
                    platform_pos = 0;
                };
                Service -> Fault : VehicleMoved;
                Fault -> Stored : ResetLeveler effect {
                    platform_pos = 0;
                };
            }
        '''),
    ),
    (
        '100. Wind Turbine Yaw Alignment',
        dedent('''\
            // Wind turbine aligns nacelle before generating power
            def int yaw_error = 12;
            def int power_ticks = 0;
            def int storm_count = 0;

            state WindTurbine {
                state Parked;

                state Yawing {
                    during {
                        yaw_error = yaw_error - 4;
                    }
                }

                state Generating {
                    during {
                        power_ticks = power_ticks + 1;
                    }
                }

                state StormLock {
                    enter {
                        storm_count = storm_count + 1;
                    }
                }

                [*] -> Parked;
                Parked -> Yawing : WindAvailable;
                Yawing -> Generating : if [yaw_error <= 0] effect {
                    power_ticks = 0;
                };
                Generating -> Parked : WindGone effect {
                    yaw_error = 12;
                };
                Generating -> StormLock : HighWind;
                StormLock -> Parked : ResetTurbine effect {
                    yaw_error = 12;
                };
            }
        '''),
    ),
    (
        '101. Reservoir Level Band Control',
        dedent('''\
            // Reservoir fill control with normal, full and alarm bands
            def int level = 50;
            def int fill_ticks = 0;
            def int alarm_count = 0;

            state Reservoir {
                state Normal {
                    during {
                        level = level - 1;
                    }
                }

                state Filling {
                    during {
                        level = level + 3;
                        fill_ticks = fill_ticks + 1;
                    }
                }

                state Full;

                state Alarm {
                    enter {
                        alarm_count = alarm_count + 1;
                    }
                }

                [*] -> Normal;
                Normal -> Filling : if [level <= 35] effect {
                    fill_ticks = 0;
                };
                Filling -> Full : if [level >= 70];
                Full -> Normal : DemandDraw effect {
                    level = 60;
                };
                Filling -> Alarm : if [fill_ticks >= 20];
                Alarm -> Normal : ResetReservoir effect {
                    level = 50;
                };
            }
        '''),
    ),
    (
        '102. Parcel Locker Pickup Session',
        dedent('''\
            // Locker reservation expires if pickup never happens
            def int reserve_ticks = 0;
            def int door_ticks = 0;
            def int expired_count = 0;

            state ParcelLocker {
                event PickupCode named "pickup-code";

                state Available;

                state Reserved {
                    during {
                        reserve_ticks = reserve_ticks + 1;
                    }
                }

                state DoorOpen {
                    during {
                        door_ticks = door_ticks + 1;
                    }
                }

                state Expired {
                    enter {
                        expired_count = expired_count + 1;
                    }
                }

                state Fault;

                [*] -> Available;
                Available -> Reserved : PlaceParcel effect {
                    reserve_ticks = 0;
                };
                Reserved -> DoorOpen : PickupCode effect {
                    door_ticks = 0;
                };
                Reserved -> Expired : if [reserve_ticks >= 3];
                DoorOpen -> Available : if [door_ticks >= 1];
                DoorOpen -> Fault : DoorForced;
                Expired -> Available : ClearExpired;
                Fault -> Available : ResetLocker;
            }
        '''),
    ),
    (
        '103. CNC Spindle Warmup Sequence',
        dedent('''\
            // CNC spindle warms up before cutting production parts
            def int warm_ticks = 0;
            def int cut_ticks = 0;
            def int part_count = 0;
            def int fault_count = 0;

            state CNCMachine {
                >> during before abstract SampleSpindle;

                state Idle;

                state Warmup {
                    during {
                        warm_ticks = warm_ticks + 1;
                    }
                }

                state Ready;

                state Cutting {
                    during {
                        cut_ticks = cut_ticks + 1;
                    }
                }

                state Fault {
                    enter {
                        fault_count = fault_count + 1;
                    }
                }

                [*] -> Idle;
                Idle -> Warmup : StartMachine effect {
                    warm_ticks = 0;
                };
                Warmup -> Ready : if [warm_ticks >= 2];
                Ready -> Cutting : StartCycle effect {
                    cut_ticks = 0;
                };
                Cutting -> Ready : if [cut_ticks >= 3] effect {
                    part_count = part_count + 1;
                };
                Cutting -> Fault : SpindleTrip;
                Fault -> Idle : ResetMachine;
            }
        '''),
    ),
    (
        '104. Building Access Visitor Flow',
        dedent('''\
            // Lobby visitor flow from badge scan to door release
            def int approval_ticks = 0;
            def int release_ticks = 0;
            def int alarm_count = 0;

            state VisitorAccess {
                state Idle;
                state BadgeScan;

                state Approval {
                    during {
                        approval_ticks = approval_ticks + 1;
                    }
                }

                state DoorRelease {
                    during {
                        release_ticks = release_ticks + 1;
                    }
                }

                state Alarm {
                    enter {
                        alarm_count = alarm_count + 1;
                    }
                }

                [*] -> Idle;
                Idle -> BadgeScan : BadgePresented;
                BadgeScan -> Approval : VisitorSelected effect {
                    approval_ticks = 0;
                };
                Approval -> DoorRelease : HostApproved effect {
                    release_ticks = 0;
                };
                Approval -> Alarm : if [approval_ticks >= 3];
                DoorRelease -> Idle : if [release_ticks >= 1];
                Alarm -> Idle : ResetLobby;
            }
        '''),
    ),
    (
        '105. Machine Vision Inspection Cell',
        dedent('''\
            // Inspection cell captures an image and branches on result
            def int capture_ticks = 0;
            def int reject_count = 0;
            def int inspection_ok = 1;

            state VisionCell {
                state Waiting;

                state Capture {
                    during {
                        capture_ticks = capture_ticks + 1;
                    }
                }

                pseudo state DecideGrade;
                state Pass;

                state Reject {
                    enter {
                        reject_count = reject_count + 1;
                    }
                }

                state Fault;

                [*] -> Waiting;
                Waiting -> Capture : PartArrived effect {
                    capture_ticks = 0;
                };
                Capture -> DecideGrade : if [capture_ticks >= 1];
                DecideGrade -> Pass : if [inspection_ok == 1];
                DecideGrade -> Reject : if [inspection_ok == 0];
                Pass -> Waiting : TransferPart;
                Reject -> Waiting : BinReject;
                Capture -> Fault : CameraFault;
                Fault -> Waiting : ResetVision;
            }
        '''),
    ),
    (
        '106. Fleet Drone Mission Supervisor',
        dedent('''\
            // Drone mission with takeoff, mission, return and error handling
            def int leg_ticks = 0;
            def int sortie_count = 0;
            def int battery_low = 0;

            state DroneMission {
                state Ready;

                state Takeoff {
                    during {
                        leg_ticks = leg_ticks + 1;
                    }
                }

                state Mission {
                    state Survey {
                        during {
                            leg_ticks = leg_ticks + 1;
                        }
                    }

                    state Deliver;

                    [*] -> Survey;
                    Survey -> Deliver : WaypointReached;
                    Deliver -> [*] : PackageDropped;
                }

                state ReturnHome;
                state Error;

                [*] -> Ready;
                Ready -> Takeoff : Launch effect {
                    leg_ticks = 0;
                };
                Takeoff -> Mission : if [leg_ticks >= 1] effect {
                    leg_ticks = 0;
                };
                Mission -> ReturnHome : if [battery_low == 1];
                ReturnHome -> Ready : Landed effect {
                    sortie_count = sortie_count + 1;
                };
                Mission -> Error : LostLink;
                Error -> Ready : ResetDrone effect {
                    battery_low = 0;
                };
            }
        '''),
    ),
    (
        '107. Water Treatment Backwash',
        dedent('''\
            // Filter train backwashes when pressure drop rises too high
            def int filter_dp = 0;
            def int rinse_ticks = 0;
            def int service_count = 0;
            def int fault_count = 0;

            state FilterTrain {
                state Filtering {
                    during {
                        filter_dp = filter_dp + 1;
                    }
                }

                state Backwash {
                    during {
                        filter_dp = filter_dp - 2;
                    }
                }

                state Rinse {
                    during {
                        rinse_ticks = rinse_ticks + 1;
                    }
                }

                state Service;

                state Fault {
                    enter {
                        fault_count = fault_count + 1;
                    }
                }

                [*] -> Filtering;
                Filtering -> Backwash : if [filter_dp >= 5] effect {
                    rinse_ticks = 0;
                };
                Backwash -> Rinse : if [filter_dp <= 0];
                Rinse -> Service : if [rinse_ticks >= 2] effect {
                    service_count = service_count + 1;
                };
                Service -> Filtering : ReturnToFilter;
                Filtering -> Fault : PumpTrip;
                Fault -> Filtering : ResetTrain effect {
                    filter_dp = 0;
                };
            }
        '''),
    ),
    (
        '108. Cold Storage Door Alarm',
        dedent('''\
            // Cold room alarm when the insulated door stays open too long
            def int open_ticks = 0;
            def int alarm_count = 0;

            state ColdRoomDoor {
                state Closed;

                state Open {
                    during {
                        open_ticks = open_ticks + 1;
                    }
                }

                state Alarm {
                    enter {
                        alarm_count = alarm_count + 1;
                    }
                }

                state Acked;

                [*] -> Closed;
                Closed -> Open : DoorOpened effect {
                    open_ticks = 0;
                };
                Open -> Closed : DoorClosed;
                Open -> Alarm : if [open_ticks >= 2];
                Alarm -> Acked : SilenceAlarm;
                Acked -> Closed : DoorClosed;
            }
        '''),
    ),
    (
        '109. Microgrid Islanding Controller',
        dedent('''\
            // Microgrid islands on utility loss and later resynchronizes
            def int sync_ticks = 0;
            def int island_count = 0;
            def int fault_count = 0;

            state Microgrid {
                event UtilityRecovered named "utility-recovered";

                state GridTied;

                state IslandPrep {
                    during {
                        sync_ticks = sync_ticks + 1;
                    }
                }

                state Islanded;

                state Resync {
                    during {
                        sync_ticks = sync_ticks + 1;
                    }
                }

                state Fault {
                    enter {
                        fault_count = fault_count + 1;
                    }
                }

                [*] -> GridTied;
                GridTied -> IslandPrep : UtilityLost effect {
                    sync_ticks = 0;
                };
                IslandPrep -> Islanded : if [sync_ticks >= 1] effect {
                    island_count = island_count + 1;
                };
                Islanded -> Resync : UtilityRecovered effect {
                    sync_ticks = 0;
                };
                Resync -> GridTied : if [sync_ticks >= 2];
                Islanded -> Fault : InverterFault;
                Fault -> GridTied : ResetMicrogrid;
            }
        '''),
    ),
    (
        '110. Packaging Cartoner Changeover',
        dedent('''\
            // Cartoner line handles starvation, recipe change and jam reset
            def int carton_count = 0;
            def int starve_ticks = 0;
            def int changeover_ticks = 0;
            def int fault_count = 0;

            state Cartoner {
                state Production {
                    during {
                        carton_count = carton_count + 1;
                    }
                }

                state Starve {
                    during {
                        starve_ticks = starve_ticks + 1;
                    }
                }

                state Changeover named "recipe-change" {
                    during {
                        changeover_ticks = changeover_ticks + 1;
                    }
                }

                state Ready;

                state Fault {
                    enter {
                        fault_count = fault_count + 1;
                    }
                }

                [*] -> Production;
                Production -> Starve : NoInfeed effect {
                    starve_ticks = 0;
                };
                Starve -> Production : ProductArrived;
                Production -> Changeover : RecipeChange effect {
                    changeover_ticks = 0;
                };
                Changeover -> Ready : if [changeover_ticks >= 2];
                Ready -> Production : ResumeRun;
                Production -> Fault : CartonJam;
                Fault -> Ready : ResetCartoner;
            }
        '''),
    ),
]

_SAMPLE_CODE_FILES = sorted(_SAMPLE_CODE_DIR.glob('*.fcstm'))


def _parse_state_machine(code: str) -> StateMachine:
    ast = parse_with_grammar_entry(code, 'state_machine_dsl')
    state_machine = parse_dsl_node_to_state_machine(ast)
    assert isinstance(state_machine, StateMachine)
    return state_machine


@pytest.mark.unittest
class TestFcstmLexerAnalyseText:
    def test_analyse_text_remains_string_based(self):
        source = inspect.getsource(pygments_lexer_module)

        assert 'parse_with_grammar_entry' not in source
        assert 'parse_dsl_node_to_state_machine' not in source

    def test_langcheck_positive_examples_are_embedded_completely(self):
        titles = [title for title, _ in _LANGCHECK_POSITIVE_CASES]

        assert len(_LANGCHECK_POSITIVE_CASES) == 110
        assert titles[0] == '1. Minimal Leaf Stair-Step'
        assert titles[-1] == '110. Packaging Cartoner Changeover'
        assert len(set(titles)) == 110
        assert [int(title.split('.', 1)[0]) for title in titles] == list(range(1, 111))

    @pytest.mark.parametrize(
        ('title', 'code'),
        _LANGCHECK_POSITIVE_CASES,
        ids=[title for title, _ in _LANGCHECK_POSITIVE_CASES],
    )
    def test_langcheck_positive_examples_are_detected_as_fcstm(self, title, code):
        state_machine = _parse_state_machine(code)
        score = FcstmLexer.analyse_text(code)

        assert isinstance(state_machine, StateMachine), f'{title} should round-trip into a StateMachine.'
        assert score >= 0.95, (
            f'{title} is valid FCSTM input and should keep a strong score, '
            f'but analyse_text returned {score:.2f}.'
        )

    def test_langcheck_hack_examples_are_embedded_completely(self):
        assert len(_LANGCHECK_HACK_CASES) == 100
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
            '51. C-6 Typedef Globals And Main (1.00)',
            '52. C-7 Struct Holder Plus during (1.00)',
            '53. C-8 Local State/Event Decls (1.00)',
            '54. C-9 Mixed Alias And Pointer Target (1.00)',
            '55. C-10 Function-Local Typedefs (1.00)',
            '56. CXX-6 Using Aliases And Main (1.00)',
            '57. CXX-7 Member Fields Plus during (1.00)',
            '58. CXX-8 Local Aliases In Helper (1.00)',
            '59. CXX-9 Lambda Body Payload (1.00)',
            '60. CXX-10 Constructor Body Payload (1.00)',
            '61. JAVA-6 Fields Plus Method Reference Lambda (0.95)',
            '62. JAVA-7 Instance Initializer Payload (0.95)',
            '63. JAVA-8 Static Initializer Payload (0.95)',
            '64. JAVA-9 Constructor-Local Payload (0.95)',
            '65. JAVA-10 Anonymous Inner Class Fields (0.95)',
            '66. JS-6 Top-Level Newline Stitching (1.00)',
            '67. JS-7 Function Body Newline Stitching (1.00)',
            '68. JS-8 IIFE Payload (1.00)',
            '69. JS-9 Class Static Block (1.00)',
            '70. JS-10 try/finally Wrapper (1.00)',
            '71. TS-6 Typed Prelude Plus Newline Stitching (1.00)',
            '72. TS-7 Function Body Payload (1.00)',
            '73. TS-8 Namespace Wrapper (1.00)',
            '74. TS-9 Class Static Block (1.00)',
            '75. TS-10 try/finally Wrapper (1.00)',
            '76. PY-6 Top-Level Bare Expressions (0.87)',
            '77. PY-7 Class Body Bare Expressions (0.87)',
            '78. PY-8 if-Block Bare Expressions (0.87)',
            '79. PY-9 for-Block Bare Expressions (0.87)',
            '80. PY-10 try/finally Bare Expressions (0.87)',
            '81. RB-6 Top-Level Regex Literal Plus Calls (0.99)',
            '82. RB-7 Class Body Payload (0.99)',
            '83. RB-8 Module Body Payload (0.99)',
            '84. RB-9 Lambda Body Payload (0.99)',
            '85. RB-10 BEGIN Block Payload (0.99)',
            '86. RS-6 Item Macro With Braces (1.00)',
            '87. RS-7 Item Macro With Parentheses (1.00)',
            '88. RS-8 Item Macro With Brackets (1.00)',
            '89. RS-9 Const Block Wrapper (1.00)',
            '90. RS-10 Nested Token Tree Wrapper (1.00)',
            '91. GO-6 Named Struct Fields (0.87)',
            '92. GO-7 Anonymous Struct Variable (0.87)',
            '93. GO-8 Function-Local Type Declaration (0.87)',
            '94. GO-9 Nested Struct Field (0.87)',
            '95. GO-10 Slice Of Anonymous Structs (0.87)',
            '96. PUML-6 allowmixing Plus Class Body (0.87)',
            '97. PUML-7 allowmixing Plus Abstract Class Body (0.87)',
            '98. PUML-8 allowmixing Plus Annotation Body (0.87)',
            '99. PUML-9 allowmixing Plus Entity Body (0.87)',
            '100. PUML-10 allowmixing Plus Object Body (0.87)',
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
