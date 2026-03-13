import re
from pathlib import Path

import pytest

from pyfcstm.highlight import FcstmLexer

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SAMPLE_CODE_DIR = _REPO_ROOT / 'test' / 'testfile' / 'sample_codes'
_LANGCHECK_HACK_PATH = _REPO_ROOT / 'LANGCHECK_HACK.md'
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

_LANGCHECK_HACK_SECTION_PATTERN = re.compile(
    r'^###\s+(?P<title>.+?)\n(?P<body>.*?)(?=^###\s+|\Z)',
    re.MULTILINE | re.DOTALL,
)
_LANGCHECK_HACK_CODE_PATTERN = re.compile(
    r'```[^\n]*\n(?P<code>.*?)\n```',
    re.DOTALL,
)


def _load_langcheck_hack_cases_from_markdown():
    cases = []
    markdown_text = _LANGCHECK_HACK_PATH.read_text(encoding='utf-8')

    for section in _LANGCHECK_HACK_SECTION_PATTERN.finditer(markdown_text):
        code_match = _LANGCHECK_HACK_CODE_PATTERN.search(section.group('body'))
        if code_match is None:
            continue

        cases.append((section.group('title').strip(), code_match.group('code') + '\n'))

    return cases


_SAMPLE_CODE_FILES = sorted(_SAMPLE_CODE_DIR.glob('*.fcstm'))


@pytest.mark.unittest
class TestFcstmLexerAnalyseText:
    def test_langcheck_hack_examples_are_embedded_completely(self):
        assert len(_LANGCHECK_HACK_CASES) == 100
        assert [
            (title, code) for title, _, code in _LANGCHECK_HACK_CASES
        ] == _load_langcheck_hack_cases_from_markdown()

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
