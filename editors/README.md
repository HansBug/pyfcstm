# FCSTM Syntax Highlighting Support

Syntax highlighting support for FCSTM (Finite State Machine) DSL.

## Overview

Two implementations provide syntax highlighting for FCSTM code:

1. **Pygments Lexer** - For Sphinx documentation and Python-based tools
2. **TextMate Grammar** - For GitHub, GitLab, and other platforms supporting TextMate grammars

Both implementations are based on the ANTLR grammar (`pyfcstm/dsl/grammar/Grammar.g4`) and have been thoroughly tested.

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

### TextMate Grammar

The TextMate grammar (`editors/fcstm.tmLanguage.json`) provides syntax highlighting for platforms that support TextMate grammars, including GitHub and GitLab.

## Supported Syntax

Both implementations support the complete FCSTM syntax:

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
- 200 lines, generates 277 tokens for typical code

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

**Location:** `editors/fcstm.tmLanguage.json`

**Features:**
- Scope-based syntax highlighting
- GitHub/GitLab syntax highlighting support
- Escape sequence highlighting in strings
- Declaration-name highlighting for variables, states, and events

**Design:**
- Based on Pygments lexer for consistency
- Kept aligned with the FCSTM ANTLR grammar
- Canonical grammar source lives in `editors/fcstm.tmLanguage.json`
- VSCode ships a copied grammar asset under `editors/vscode/syntaxes/`

## Testing and Validation

### Validation Script

**`editors/validate.py`** - Comprehensive validation:
- Pygments lexer validation with 20+ checkpoints
- TextMate grammar synchronization checks for the VSCode-packaged asset
- Ordering-sensitive operator coverage checks
- Terminal-based highlighting display
- Token type verification

### Running Tests

```bash
# Validate syntax-highlighting assets
python editors/validate.py
```

### Test Results

All tests pass successfully:
- Pygments Lexer: PASSED (20/20 checkpoints)
- Language detection score: 1.00
- Token generation: 1861 tokens for comprehensive test code

## File Structure

```
pyfcstm/
├── pyfcstm/
│   └── highlight/
│       ├── __init__.py              # Direct import of FcstmLexer
│       └── pygments_lexer.py        # Pygments lexer implementation
├── editors/
│   ├── README.md                    # This file
│   ├── fcstm.tmLanguage.json        # TextMate grammar
│   └── validate.py                  # Validation script
├── requirements.txt                 # Includes pygments>=2.10.0
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

## Development

### Adding New Keywords

When adding new keywords to the FCSTM grammar:

1. Update `pyfcstm/dsl/grammar/Grammar.g4`
2. Regenerate parser: `make antlr_build`
3. Update `pyfcstm/highlight/pygments_lexer.py`
4. Update `editors/fcstm.tmLanguage.json`
5. Update `editors/validate.py` to fit the new grammar (if necessary)

### Consistency

Both implementations should be kept in sync. The Pygments lexer serves as the reference implementation, with the TextMate grammar derived from it.

## Related Documentation

- [FCSTM DSL Language Reference](../CLAUDE.md#dsl-language-reference)
- [ANTLR Grammar](../pyfcstm/dsl/grammar/Grammar.g4)
- [Pygments Documentation](https://pygments.org/)
- [TextMate Grammar Documentation](https://macromates.com/manual/en/language_grammars)

## License

LGPL-3.0 - See [LICENSE](../LICENSE) for details
