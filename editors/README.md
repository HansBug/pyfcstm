# FCSTM Syntax Highlighting Support

Syntax highlighting support for FCSTM (Finite State Machine) DSL.

## Overview

Two implementations provide syntax highlighting for FCSTM-related code:

1. **Pygments lexers** - For Sphinx documentation and Python-based tools
2. **TextMate grammars** - For VSCode, GitHub, GitLab, and other platforms supporting TextMate grammars

The main `*.fcstm` assets follow the FCSTM DSL grammar. The `*.fbmcq` assets follow the separate FCSTM BMC Query grammar under `pyfcstm/bmc/grammar/`. Both surfaces are syntax highlighters only; model-aware validation remains in the parser, binder, simulator, and verification layers.

## Quick Start

### Pygments (Sphinx Documentation)

Pygments is included as a core dependency and is automatically available.

Use FCSTM model code in Sphinx RST files:

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

This registration should be placed after importing your project metadata and before the Sphinx configuration variables. Register `FcstmBmcQueryLexer` in the same place when documentation uses `.. code-block:: fbmcq` or `.. code-block:: fcstm-bmc-query`.

### TextMate Grammar

The TextMate grammar (`editors/fcstm.tmLanguage.json`) provides syntax highlighting for platforms that support TextMate grammars, including GitHub and GitLab. The BMC query grammar lives in `editors/fcstm-bmc-query.tmLanguage.json`; the VSCode extension ships copied assets under `editors/vscode/syntaxes/`.

## Supported Syntax

Both implementations support the complete FCSTM syntax, including the import
statement, block-form import mappings, wildcard selectors, and target templates.
The Pygments lexer and the TextMate / VSCode grammar are kept aligned and share
the same validation checkpoints in `editors/validate.py`.

**Keywords:** `state`, `pseudo`, `import`, `as`, `named`, `def`, `event`, `enter`, `during`, `exit`, `before`, `after`, `abstract`, `ref`, `effect`, `if`, `else`, `and`, `or`, `not`, `implies`, `xor`, `iff`

**Types:** `int`, `float`

**Operators:** `->`, `=>`, `>>`, `::`, `:`, `/`, `!`, `**`, `<<`, `>>`, `+`, `-`, `*`, `/`, `%`, `&`, `|`, `^`, `~`, `<`, `>`, `<=`, `>=`, `==`, `!=`, `&&`, `||`, `?`

`^` is numeric bitwise xor. Boolean exclusive-or in guard conditions is spelled
with the `xor` keyword; `->` remains transition syntax, so implication uses
`=>` or `implies`.

**Literals:** integers (`123`), hex (`0xFF`), floats (`3.14`, `1e-5`), booleans (`True`, `False`), strings (`"text"`, `'text'`), math constants (`pi`, `E`, `tau`)

**Built-in Functions:** `sin`, `cos`, `tan`, `asin`, `acos`, `atan`, `sinh`, `cosh`, `tanh`, `asinh`, `acosh`, `atanh`, `sqrt`, `cbrt`, `exp`, `log`, `log10`, `log2`, `log1p`, `abs`, `ceil`, `floor`, `round`, `trunc`, `sign`

**Special Symbols:** `[*]` (pseudo-state), `//` (line comment), `/* */` (block comment), `#` (Python-style comment)

**Import Mapping Forms:** `import "./worker.fcstm" as Worker { ... }`, `def sensor_* -> io_$1;`, `def * -> Worker_${1};`, `event /Start -> Start named "Mapped Start";`


### FCSTM BMC Query (`*.fbmcq`)

The BMC query language has its own highlighter so query files do not reuse the main FCSTM model scopes.

**Frozen identifiers:**

- File extension: `.fbmcq`
- VSCode language id: `fcstm-bmc-query`
- TextMate scope: `source.fcstm.bmc.query`
- Pygments aliases: `fbmcq`, `fcstm-bmc-query`
- MIME type: `text/x-fcstm-bmc-query`

The highlighter covers query clauses (`init`, `assume`, `check`), initial variable policy (`havoc`), property kinds (`reach`, `forbid`, `invariant`, `must_reach`, `exists_always`, `response`, `cover`), BMC atoms (`var`, `cycle`, `active`, `terminated`, `event`, `case`, `call_count`, `called`), call filters (`action`, `step`, `stage`, `role`, `state`, `active_leaf`, `named_ref`, `null`), event cardinality (`at_most_one`), FCSTM-compatible expression operators, literals, strings, and comments. It intentionally does not add `warm` or `hot` init targets because the current `.fbmcq` grammar only accepts `cold`, `terminated`, and `state("...")`.

`^` is highlighted as a numeric bitwise operator. Boolean exclusive-or remains the `xor` keyword.

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

**Locations:**
- `pyfcstm/highlight/pygments_lexer.py` for `*.fcstm`
- `pyfcstm/highlight/bmc_query_lexer.py` for `*.fbmcq`

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
        'fbmcq = pyfcstm.highlight.bmc_query_lexer:FcstmBmcQueryLexer',
    ],
}
```

### TextMate Grammar

**Locations:**
- `editors/fcstm.tmLanguage.json` for `*.fcstm`
- `editors/fcstm-bmc-query.tmLanguage.json` for `*.fbmcq`

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
- FCSTM Pygments lexer validation with 20+ checkpoints
- FCSTM TextMate grammar synchronization checks for the VSCode-packaged asset
- FBMCQ Pygments lexer metadata and token smoke checks
- FBMCQ TextMate grammar synchronization and operator-order checks
- VSCode `package.json` positive checks for `.fbmcq` language/grammar contributions
- VSCode negative checks to ensure `.fbmcq` does not activate the `.fcstm` preview or language-server surfaces

### Running Tests

```bash
# Validate syntax-highlighting assets
python editors/validate.py
```

### Test Results

All tests pass successfully:
- FCSTM Pygments: PASSED
- FCSTM TextMate: PASSED
- FBMCQ Pygments: PASSED
- FBMCQ TextMate and VSCode contribution checks: PASSED

## File Structure

```
pyfcstm/
├── pyfcstm/
│   └── highlight/
│       ├── __init__.py              # Direct import of public lexers
│       ├── bmc_query_lexer.py       # FBMCQ Pygments lexer implementation
│       └── pygments_lexer.py        # FCSTM Pygments lexer implementation
├── editors/
│   ├── README.md                    # This file
│   ├── fcstm.tmLanguage.json        # FCSTM TextMate grammar
│   ├── fcstm-bmc-query.tmLanguage.json  # FBMCQ TextMate grammar
│   ├── validate.py                  # Validation script
│   └── vscode/syntaxes/             # VSCode-packaged grammar copies
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

1. Update the relevant ANTLR grammar: `pyfcstm/dsl/grammar/GrammarParser.g4` / `GrammarLexer.g4` for `*.fcstm`, or `pyfcstm/bmc/grammar/BmcQueryParser.g4` / `BmcQueryLexer.g4` for `*.fbmcq`.
2. Regenerate parser: `make antlr_build`
3. Update `pyfcstm/highlight/pygments_lexer.py`
4. Update `editors/fcstm.tmLanguage.json` for `*.fcstm`, or `editors/fcstm-bmc-query.tmLanguage.json` for `*.fbmcq`.
5. Sync the VSCode grammar copy under `editors/vscode/syntaxes/`.
6. Update `editors/validate.py` to fit the new grammar (if necessary).

### Consistency

Both implementations should be kept in sync. The Pygments lexer serves as the reference implementation, with the TextMate grammar derived from it.

## Related Documentation

- [FCSTM DSL Language Reference](../CLAUDE.md#dsl-language-reference)
- [FCSTM Parser Grammar](../pyfcstm/dsl/grammar/GrammarParser.g4) and [FCSTM Lexer Grammar](../pyfcstm/dsl/grammar/GrammarLexer.g4)
- [Pygments Documentation](https://pygments.org/)
- [TextMate Grammar Documentation](https://macromates.com/manual/en/language_grammars)

## License

LGPL-3.0 - See [LICENSE](../LICENSE) for details
