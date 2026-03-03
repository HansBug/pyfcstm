# FCSTM Syntax Highlighting Support

Complete syntax highlighting support for FCSTM (Finite State Machine) DSL across multiple editors and platforms.

## Overview

Three complete implementations provide syntax highlighting for FCSTM code:

1. **Pygments Lexer** - For Sphinx documentation and Python-based tools
2. **TextMate Grammar** - For VSCode, GitHub, and GitLab
3. **JetBrains Language Definition** - For IntelliJ IDEA, PyCharm, WebStorm, CLion, etc.

All implementations are based on the ANTLR grammar (`pyfcstm/dsl/grammar/Grammar.g4`) and have been thoroughly tested.

## Quick Start

### Pygments (Sphinx Documentation)

Pygments is included as a core dependency and is automatically available.

Use in Sphinx RST files:

```rst
.. code-block:: fcstm

    def int counter = 0;
    state MyState {
        enter { counter = 0; }
    }
```

**Sphinx Configuration:**

To enable FCSTM syntax highlighting in Sphinx documentation, add the following to your `conf.py`:

```python
# Register FCSTM Pygments lexer for syntax highlighting
from pygments.lexers import get_lexer_by_name
from pyfcstm.highlight.pygments_lexer import FcstmLexer
from sphinx.highlighting import lexers

# Register the lexer with Sphinx
lexers['fcstm'] = FcstmLexer()
lexers['fcsm'] = FcstmLexer()  # Alternative alias

print("✓ FCSTM Pygments lexer registered successfully")
```

This registration should be placed after importing your project metadata and before the Sphinx configuration variables. The lexer will then be automatically available for all `.. code-block:: fcstm` directives in your documentation.

### VSCode

```bash
# Copy extension to VSCode extensions directory
cp -r editors/vscode ~/.vscode/extensions/fcstm-language-support/

# Reload VSCode (Cmd+Shift+P -> "Reload Window")
```

### JetBrains IDEs

**Linux:**
```bash
cp editors/jetbrains/fcstm.xml ~/.config/JetBrains/<Product><Version>/filetypes/
```

**macOS:**
```bash
cp editors/jetbrains/fcstm.xml ~/Library/Application\ Support/JetBrains/<Product><Version>/filetypes/
```

**Windows:**
```cmd
copy editors\jetbrains\fcstm.xml %APPDATA%\JetBrains\<Product><Version>\filetypes\
```

Then restart your IDE.

## Supported Syntax

All implementations support the complete FCSTM syntax:

**Keywords:** `state`, `pseudo`, `named`, `def`, `event`, `enter`, `during`, `exit`, `before`, `after`, `abstract`, `ref`, `effect`, `if`, `and`, `or`, `not`

**Types:** `int`, `float`

**Operators:** `->`, `>>`, `::`, `:`, `/`, `!`, `**`, `<<`, `>>`, `+`, `-`, `*`, `/`, `%`, `&`, `|`, `^`, `~`, `<`, `>`, `<=`, `>=`, `==`, `!=`, `&&`, `||`, `?`

**Literals:** integers (`123`), hex (`0xFF`), floats (`3.14`, `1e-5`), booleans (`True`, `False`), strings (`"text"`, `'text'`), math constants (`pi`, `E`, `tau`)

**Built-in Functions:** `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh`, `sqrt`, `cbrt`, `exp`, `log`, `log10`, `log2`, `log1p`, `abs`, `ceil`, `floor`, `round`, `trunc`, `sign`

**Special Symbols:** `[*]` (pseudo-state), `//` (line comment), `/* */` (block comment), `#` (Python-style comment)

## Example

```fcstm
// Traffic light state machine
def int counter = 0;
def float temperature = 25.5;

state TrafficLight {
    // Aspect action for all child states
    >> during before {
        counter = counter + 1;
    }

    state InService {
        enter {
            counter = 0;
        }

        enter abstract InitHardware /*
            Initialize hardware peripherals
            TODO: Implement in generated code
        */

        state Red {
            during {
                counter = 0x1 << 2;
            }
        }

        state Yellow;
        state Green;

        [*] -> Red :: Start effect {
            counter = 0x1;
        }

        Red -> Green : if [counter >= 10];
        Green -> Yellow :: Change;
        Yellow -> Red : if [temperature > 30.0];
    }

    state Maintenance;

    // Forced transition from all states
    ! * -> Maintenance :: Emergency;

    [*] -> InService;
    InService -> Maintenance :: Maintain;
    Maintenance -> InService :: Resume;
}
```

## Implementation Details

### Pygments Lexer

**Location:** `pyfcstm/highlight/pygments_lexer.py`

**Features:**
- Token-based syntax highlighting
- Language detection (score: 1.00 for FCSTM code)
- Integration with Sphinx via entry point
- Automatically available as a core dependency

**Design:**
- Core dependency (included in `requirements.txt`)
- Direct import in `pyfcstm/highlight/__init__.py`
- Registered as Pygments entry point in `setup.py`
- 195 lines, generates 277 tokens for typical code

**Entry Point Registration:**

```python
entry_points={
    'console_scripts': [
        'pyfcstm=pyfcstm.entry:pyfcstmcli'
    ],
    'pygments.lexers': [
        'fcstm = pyfcstm.highlight.pygments_lexer:FcstmLexer',
    ],
}
```

### TextMate Grammar

**Location:** `editors/vscode/syntaxes/fcstm.tmLanguage.json`

**Features:**
- Scope-based syntax highlighting
- VSCode integration via `package.json`
- GitHub/GitLab syntax highlighting support
- Bracket matching and auto-closing
- Comment toggling support

**Files:**
- `package.json` - VSCode extension manifest
- `language-configuration.json` - Language behavior configuration
- `syntaxes/fcstm.tmLanguage.json` - TextMate grammar (145 lines)
- `README.md` - Installation and usage instructions

**Design:**
- Based on Pygments lexer for consistency
- Comprehensive scope definitions
- Support for nested comments
- Escape sequence highlighting in strings

### JetBrains Language Definition

**Location:** `editors/jetbrains/fcstm.xml`

**Features:**
- Basic syntax highlighting
- Comment toggling (Ctrl+/, Cmd+/)
- Block comment support (Ctrl+Shift+/, Cmd+Shift+/)
- Bracket matching
- File type association

**Limitations:**
- Basic highlighting only (no semantic analysis)
- No code completion or error checking
- No refactoring support

**Design:**
- XML-based language definition (85 lines)
- Keyword grouping for different syntax categories
- Support for multiple comment styles

## Testing and Validation

### Test Scripts

**`test_highlight.py`** - Tests Pygments lexer functionality:
- Tokenization test
- Language detection test
- Terminal output test
- HTML output test
- Token type verification

**`validate_highlight.py`** - Comprehensive validation:
- Pygments lexer validation
- TextMate grammar structure validation
- JetBrains XML validation
- VSCode package.json validation

### Running Tests

```bash
# Test Pygments lexer
python test_highlight.py

# Test on specific file
python test_highlight.py docs/source/tutorials/dsl/example.fcstm

# Validate all implementations
python validate_highlight.py
```

### Test Results

All tests pass successfully:
- Pygments Lexer: PASSED
- TextMate Grammar: PASSED
- JetBrains Definition: PASSED
- VSCode Package: PASSED

## File Structure

```
pyfcstm/
├── pyfcstm/
│   └── highlight/
│       ├── __init__.py              # Direct import of FcstmLexer
│       └── pygments_lexer.py        # Pygments lexer implementation
├── editors/
│   ├── README.md                    # This file
│   ├── vscode/
│   │   ├── package.json             # VSCode extension manifest
│   │   ├── language-configuration.json
│   │   ├── syntaxes/
│   │   │   └── fcstm.tmLanguage.json
│   │   └── README.md
│   └── jetbrains/
│       ├── fcstm.xml                # JetBrains language definition
│       └── README.md
├── requirements.txt                 # Includes pygments>=2.10.0
├── test_highlight.py                # Pygments lexer test script
├── validate_highlight.py            # Comprehensive validation script
└── setup.py                         # Updated with Pygments entry point
```

## Troubleshooting

### Pygments not working in Sphinx

```bash
# Verify Pygments is installed
pip list | grep -i pygments

# Reinstall if needed
pip install -r requirements.txt

# Verify lexer is registered
python -c "from pygments.lexers import get_lexer_by_name; print(get_lexer_by_name('fcstm'))"
```

### VSCode not highlighting `.fcstm` files

1. Check extension is in `~/.vscode/extensions/fcstm-language-support/`
2. Reload VSCode window (Cmd+Shift+P -> "Reload Window")
3. Open a `.fcstm` file and check bottom-right corner shows "FCSTM"

### JetBrains not highlighting `.fcstm` files

1. Check `fcstm.xml` is in correct filetypes directory
2. Restart IDE completely
3. Open Settings -> Editor -> File Types -> verify FCSTM is listed

## Development

### Adding New Keywords

When adding new keywords to the FCSTM grammar:

1. Update `pyfcstm/dsl/grammar/Grammar.g4`
2. Regenerate parser: `make antlr_build`
3. Update `pyfcstm/highlight/pygments_lexer.py`
4. Update `editors/vscode/syntaxes/fcstm.tmLanguage.json`
5. Update `editors/jetbrains/fcstm.xml`
6. Update `editors/validate.py` to fit the new grammar (if necessary)

### Consistency

All three implementations should be kept in sync. The Pygments lexer serves as the reference implementation, with TextMate and JetBrains definitions derived from it.

## Future Enhancements

**VSCode Extension:**
- Publish to VSCode Marketplace
- Add semantic highlighting
- Add code completion
- Add error checking via language server

**JetBrains Plugin:**
- Create full plugin (not just file type)
- Add semantic highlighting
- Add code completion
- Add error checking

**Language Server Protocol (LSP):**
- Implement LSP server for FCSTM
- Provide cross-editor support
- Add advanced features (go-to-definition, find references, etc.)

## Related Documentation

- [FCSTM DSL Language Reference](../CLAUDE.md#dsl-language-reference)
- [ANTLR Grammar](../pyfcstm/dsl/grammar/Grammar.g4)
- [Pygments Documentation](https://pygments.org/)
- [TextMate Grammar Documentation](https://macromates.com/manual/en/language_grammars)
- [JetBrains Language Definition](https://www.jetbrains.com/help/idea/language-and-file-type.html)

## License

LGPL-3.0 - See [LICENSE](../LICENSE) for details
