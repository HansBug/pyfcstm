FCSTM Syntax Highlighting Guide
===============================================

pyfcstm provides native syntax highlighting support for FCSTM DSL code through multiple implementations, making it easy to display beautifully formatted state machine code in documentation, editors, and development tools.

Overview
---------------------------------------

Multiple complementary implementations provide comprehensive syntax highlighting and language support:

1. **Pygments Lexer** - For Python ecosystem tools (Sphinx, Jupyter, etc.)
2. **TextMate Grammar** - For editors supporting TextMate grammars (Sublime Text, etc.)
3. **VS Code Extension** - Comprehensive language support with advanced features (syntax diagnostics, code completion, document symbols, hover documentation)

All implementations are based on the ANTLR grammar and support the complete FCSTM syntax including keywords, operators, literals, comments, and built-in functions.

Using Pygments in Python
---------------------------------------

Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Pygments support is included as a core dependency and is automatically available when you install pyfcstm:

.. code-block:: bash

   pip install pyfcstm

The FCSTM lexer is registered as a Pygments entry point, making it available system-wide.

Basic Usage
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**In Python Code:**

.. code-block:: python

   from pygments import highlight
   from pygments.formatters import HtmlFormatter, TerminalFormatter
   from pygments.lexers import get_lexer_by_name

   # Load FCSTM lexer
   lexer = get_lexer_by_name("fcstm")

   # Your FCSTM code
   code = """
   def int counter = 0;

   state MyState {
       enter {
           counter = 0;
       }

       during {
           counter = counter + 1;
       }
   }
   """

   # Generate HTML with syntax highlighting
   html = highlight(code, lexer, HtmlFormatter())
   print(html)

   # Or display in terminal with colors
   terminal_output = highlight(code, lexer, TerminalFormatter())
   print(terminal_output)

**In Jupyter Notebooks:**

.. code-block:: python

   from IPython.display import HTML
   from pygments import highlight
   from pygments.formatters import HtmlFormatter
   from pygments.lexers import get_lexer_by_name

   lexer = get_lexer_by_name("fcstm")
   formatter = HtmlFormatter(style='monokai')

   code = """state Active { enter { counter = 0; } }"""

   # Display with syntax highlighting
   HTML(f"<style>{formatter.get_style_defs()}</style>{highlight(code, lexer, formatter)}")

Using in Sphinx Documentation
---------------------------------------

Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The FCSTM lexer is automatically registered in Sphinx when pyfcstm is installed. Add this to your ``conf.py``:

.. code-block:: python

   # Register FCSTM Pygments lexer for syntax highlighting
   from pyfcstm.highlight.pygments_lexer import FcstmLexer
   from sphinx.highlighting import lexers

   # Register the lexer with Sphinx
   lexers['fcstm'] = FcstmLexer()
   lexers['fcsm'] = FcstmLexer()  # Alternative alias

   print("✓ FCSTM Pygments lexer registered successfully")

This registration should be placed after importing your project metadata and before the Sphinx configuration variables.

Using in RST Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Once configured, you can use FCSTM syntax highlighting in any RST file with the ``code-block`` directive:

.. code-block:: rst

   .. code-block:: fcstm

      def int counter = 0;
      def float temperature = 25.5;

      state TrafficLight {
          >> during before {
              counter = counter + 1;
          }

          state Red {
              enter {
                  counter = 0;
              }
          }

          state Yellow;
          state Green;

          [*] -> Red;
          Red -> Green : if [counter >= 10];
          Green -> Yellow :: Change;
          Yellow -> Red;
      }

The result will be beautifully syntax-highlighted FCSTM code with proper coloring for keywords, operators, literals, and comments.

**Example Output:**

.. code-block:: fcstm

   def int counter = 0;
   def float temperature = 25.5;

   state TrafficLight {
       >> during before {
           counter = counter + 1;
       }

       state Red {
           enter {
               counter = 0;
           }
       }

       state Yellow;
       state Green;

       [*] -> Red;
       Red -> Green : if [counter >= 10];
       Green -> Yellow :: Change;
       Yellow -> Red;
   }

Using TextMate Grammar
---------------------------------------

The TextMate grammar provides syntax highlighting for editors that support TextMate grammars, including VS Code and Sublime Text.

Location
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The TextMate grammar file is located at:

.. code-block:: text

   editors/fcstm.tmLanguage.json

This grammar file serves as the foundation for editor integrations and is synchronized with the ANTLR grammar definition.

Sublime Text Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Open Sublime Text
2. Navigate to ``Preferences → Browse Packages``
3. Create a new directory: ``FCSTM``
4. Copy ``fcstm.tmLanguage.json`` to this directory
5. Restart Sublime Text
6. Files with ``.fcstm`` extension will now have syntax highlighting

VS Code Extension
---------------------------------------

The pyfcstm project includes a comprehensive VS Code extension that provides advanced language support beyond basic syntax highlighting.

Overview
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The VS Code extension is a lightweight, offline-capable tool designed for FCSTM authoring with the following principles:

- Language-neutral at runtime (no Python or Java dependencies)
- Compatible with a wide range of VS Code versions (1.60.0+)
- Fully offline for core editor features
- Grammar-driven development using ANTLR as the source of truth

Features
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The extension provides comprehensive language support:

**Basic Features:**

- Syntax highlighting for all FCSTM language elements
- Comment toggling (``Ctrl+/`` or ``Cmd+/`` for line comments)
- Block comment support (``Shift+Alt+A`` or ``Shift+Option+A``)
- Automatic bracket, quote, and comment block closing
- Code folding with region markers
- FCSTM-aware token selection for identifiers, events, and literals

**Advanced Features:**

- **Syntax Diagnostics** - Real-time error detection with clear messages in the Problems panel
- **Document Symbols** - Navigate state machine structure via Outline view

  - Variables (``def int``, ``def float``)
  - States (leaf and composite)
  - Pseudo states
  - Events
  - Nested state hierarchies

- **Code Completion** - IntelliSense support for:

  - Keywords (``state``, ``def``, ``event``, ``enter``, ``during``, ``exit``, etc.)
  - Built-in constants (``pi``, ``E``, ``tau``, ``true``, ``false``)
  - Built-in functions (``sin``, ``cos``, ``sqrt``, ``abs``, ``log``, etc.)
  - Document-local symbols (variables, states, events)

- **Hover Documentation** - Contextual help for:

  - Event scoping operators (``::`, ``:``, ``/``)
  - Pseudo-state marker (``[*]``)
  - Keywords (``pseudo``, ``effect``, ``abstract``, ``ref``, ``named``, etc.)
  - Lifecycle aspects (``during before/after``, ``>> during before/after``)

- **Code Snippets** - Quick templates for common FCSTM patterns:

  - Variable definitions (``defi``, ``deff``)
  - State declarations (``state``, ``stateb``, ``pstate``, ``staten``)
  - Event definitions (``event``, ``eventn``)
  - Transitions (``init``, ``trans``, ``transe``, ``transg``, ``transeff``, ``transfull``)
  - Lifecycle actions (``enter``, ``during``, ``exit``, ``dbefore``, ``dafter``)
  - Aspect actions (``globalbefore``, ``globalafter``)
  - Action modifiers (``eabstract``, ``eref``)

Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**From VSIX Package**

Download the ``.vsix`` file from the `GitHub releases page <https://github.com/hansbug/pyfcstm/releases>`_ and install it:

.. code-block:: bash

   code --install-extension fcstm-language-support-0.1.0.vsix

Or install via VS Code UI:

1. Open VS Code
2. Go to Extensions view (``Ctrl+Shift+X`` or ``Cmd+Shift+X``)
3. Click the ``...`` menu at the top of the Extensions view
4. Select "Install from VSIX..."
5. Choose the downloaded ``.vsix`` file
6. Reload VS Code

**Building from Source**

Prerequisites:

- Node.js (v20 or later) and npm
- Java (JDK 11 or later) - required for ANTLR parser generation
- Python (3.8 or later) - required for ANTLR setup
- Git

Build steps:

1. Clone the repository:

   .. code-block:: bash

      git clone https://github.com/hansbug/pyfcstm.git
      cd pyfcstm

2. Download ANTLR (first-time setup):

   .. code-block:: bash

      make antlr

3. Build the extension using the root Makefile:

   .. code-block:: bash

      make vscode

   This command will:

   - Install npm dependencies
   - Copy TextMate grammar files
   - Generate JavaScript parser from ANTLR grammar
   - Bundle extension with esbuild
   - Package the extension as ``.vsix``

   The built extension will be available at ``editors/vscode/build/fcstm-language-support-0.1.0.vsix``

4. Install the generated ``.vsix`` file:

   .. code-block:: bash

      code --install-extension editors/vscode/build/fcstm-language-support-0.1.0.vsix

Verifying Installation
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

After installation:

1. Open a ``.fcstm`` file in VS Code
2. Check the language mode in the bottom-right corner - it should show "FCSTM"
3. Verify that keywords, operators, and other syntax elements are highlighted
4. Open the Outline view (``Ctrl+Shift+O`` or ``Cmd+Shift+O``) to see document symbols
5. Try typing ``state`` and verify that code completion appears
6. Hover over keywords like ``pseudo`` or ``effect`` to see documentation

Extension Architecture
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The extension uses a pure JavaScript ANTLR parser generated from the canonical FCSTM grammar:

- **Grammar Source**: ``pyfcstm/dsl/grammar/Grammar.g4`` (single source of truth)
- **Generated Artifacts**: ``editors/vscode/parser/`` (GrammarLexer.js, GrammarParser.js, GrammarVisitor.js)
- **Parser Adapter**: ``src/parser.ts`` (loads generated artifacts and normalizes diagnostics)
- **Runtime**: antlr4 version 4.9.3 (exact match with generation toolchain)

The extension is bundled using esbuild into a single ``dist/extension.js`` file (246KB) that includes:

- ANTLR-generated parser (~104KB)
- antlr4 runtime (~80KB)
- Extension sources (~20KB)

This all-in-one bundle ensures:

- No runtime dependency loading issues
- Faster extension activation
- Fully offline operation
- No Python or external runtime dependencies

Development Workflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For active development:

.. code-block:: bash

   cd editors/vscode

   # Watch mode for development (with sourcemaps)
   npm run watch

   # Or build manually
   make build-dev

   # In another terminal, verify features
   make verify

When the ANTLR grammar changes:

1. Regenerate Python parser from project root:

   .. code-block:: bash

      make antlr_build

2. Verify Python tests pass:

   .. code-block:: bash

      make unittest

3. Regenerate JavaScript parser for VS Code:

   .. code-block:: bash

      cd editors/vscode
      make parser

4. Rebuild and verify:

   .. code-block:: bash

      make build
      make verify

Testing and Verification
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The extension includes comprehensive test suites:

.. code-block:: bash

   cd editors/vscode

   # Verify P0.2 - Parser Integration (32 tests)
   make verify-p0.2

   # Verify P0.3 - Syntax Diagnostics (35 tests)
   make verify-p0.3

   # Verify P0.4 - Document Symbols (35 tests)
   make verify-p0.4

   # Verify P0.5 - Code Completion (30 tests)
   make verify-p0.5

   # Verify P0.6 - Hover Documentation (35 tests)
   make verify-p0.6

   # Run all verification tests
   make verify

All tests use real FCSTM code and provide detailed error reporting for easy debugging.

Supported Syntax Elements
---------------------------------------

Both Pygments and TextMate implementations support the complete FCSTM syntax:

Keywords
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Declaration Keywords:** ``state``, ``pseudo``, ``named``, ``def``, ``event``

**Lifecycle Keywords:** ``enter``, ``during``, ``exit``, ``before``, ``after``

**Action Keywords:** ``abstract``, ``ref``, ``effect``

**Conditional Keywords:** ``if``, ``and``, ``or``, ``not``

Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``int``, ``float``

Operators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Transition Operators:** ``->``, ``>>``, ``::``, ``:``, ``/``, ``!``

**Arithmetic Operators:** ``+``, ``-``, ``*``, ``/``, ``%``, ``**``

**Bitwise Operators:** ``&``, ``|``, ``^``, ``~``, ``<<``, ``>>``

**Comparison Operators:** ``<``, ``>``, ``<=``, ``>=``, ``==``, ``!=``

**Logical Operators:** ``&&``, ``||``, ``!``

**Ternary Operator:** ``?``, ``:``

Literals
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Integers:** ``123``, ``0xFF`` (hexadecimal), ``0b1010`` (binary)

**Floats:** ``3.14``, ``1e-5``, ``2.5e10``

**Booleans:** ``True``, ``False``

**Strings:** ``"text"``, ``'text'``

**Math Constants:** ``pi``, ``E``, ``tau``

Built-in Functions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Trigonometric:** ``sin``, ``cos``, ``tan``, ``asin``, ``acos``, ``atan``, ``sinh``, ``cosh``, ``tanh``, ``asinh``, ``acosh``, ``atanh``

**Mathematical:** ``sqrt``, ``cbrt``, ``exp``, ``log``, ``log10``, ``log2``, ``log1p``, ``abs``, ``ceil``, ``floor``, ``round``, ``trunc``, ``sign``

Special Symbols
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Pseudo-state:** ``[*]``

**Comments:** ``//`` (line comment), ``/* */`` (block comment), ``#`` (Python-style comment)

Complete Example
---------------------------------------

Here's a comprehensive example demonstrating all syntax elements:

.. code-block:: fcstm

   // Traffic light controller with error handling
   def int counter = 0;
   def int error_count = 0;
   def float temperature = 25.5;
   def int flags = 0xFF;

   state TrafficLight {
       // Global aspect action for monitoring
       >> during before {
           counter = counter + 1;
           temperature = temperature + 0.1;
       }

       >> during before abstract GlobalMonitor /*
           Monitor system health across all states
           TODO: Implement hardware monitoring
       */

       state InService {
           enter {
               counter = 0;
               error_count = 0;
               flags = flags | 0x01;
           }

           enter abstract InitHardware /*
               Initialize traffic light hardware
               - Set up GPIO pins
               - Test LED functionality
               - Calibrate sensors
           */

           during before {
               // Pre-processing for all child states
               flags = flags & 0xFE;
           }

           state Red {
               during {
                   counter = (counter < 100) ? counter + 1 : 0;
                   flags = 0x1 << 2;
               }

               exit {
                   counter = 0;
               }
           }

           state Yellow {
               enter {
                   counter = 0;
               }
           }

           state Green {
               during {
                   // Use bitwise operations
                   flags = flags ^ 0x10;
               }
           }

           [*] -> Red :: Start effect {
               counter = 0;
               flags = 0x01;
           }

           Red -> Green : if [counter >= 10 && temperature < 50.0];
           Green -> Yellow :: Change effect {
               counter = 0;
           }
           Yellow -> Red : if [counter >= 3];
       }

       state Maintenance {
           enter {
               flags = 0xFF;
           }

           enter ref /GlobalCleanup;
       }

       state Error {
           enter {
               error_count = error_count + 1;
           }
       }

       // Forced transitions for emergency handling
       !* -> Error :: CriticalError;
       !InService -> Maintenance :: Emergency;

       [*] -> InService;
       InService -> Maintenance :: Maintain;
       Maintenance -> InService : if [error_count == 0];
       Error -> [*] : if [error_count > 5];
   }

Validation and Testing
---------------------------------------

Verifying Pygments Lexer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Test the Pygments lexer installation:

.. code-block:: bash

   # Verify lexer is registered
   python -c "from pygments.lexers import get_lexer_by_name; print(get_lexer_by_name('fcstm'))"

   # Run validation script
   cd editors
   python validate.py

The validation script performs comprehensive testing with 20+ checkpoints covering all ANTLR grammar rules.

Troubleshooting
---------------------------------------

Pygments Not Working in Sphinx
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Verify Pygments is installed
   pip list | grep -i pygments

   # Reinstall if needed
   pip install -r requirements.txt

   # Verify lexer registration
   python -c "from pygments.lexers import get_lexer_by_name; print(get_lexer_by_name('fcstm'))"

VS Code Extension Not Working
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Check that the extension is installed:

   - Open Extensions view (``Ctrl+Shift+X`` or ``Cmd+Shift+X``)
   - Search for "FCSTM" or check ``~/.vscode/extensions/``

2. Verify file extension is ``.fcstm``
3. Check VS Code's language mode (bottom right corner) - it should show "FCSTM"
4. Reload VS Code window (``Ctrl+Shift+P`` → "Reload Window")
5. Check the Output panel (View → Output) and select "FCSTM Language Support" for diagnostic messages

VS Code Syntax Diagnostics Not Appearing
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Ensure the file is saved (diagnostics update on save)
2. Check the Problems panel (View → Problems or ``Ctrl+Shift+M``)
3. Verify the extension is activated (check Output panel)
4. Try opening a known invalid FCSTM file to test error detection

VS Code Code Completion Not Working
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Ensure IntelliSense is enabled in VS Code settings
2. Try triggering completion manually (``Ctrl+Space``)
3. Check that you're not in a comment or string context
4. Verify the extension is activated

TextMate Grammar Not Working
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Verify the grammar file is in the correct location
2. Check that the ``scopeName`` in the grammar matches your configuration
3. Restart your editor after installing the grammar

Development and Customization
---------------------------------------

Adding New Keywords
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When extending the FCSTM grammar with new keywords:

1. Update ``pyfcstm/dsl/grammar/Grammar.g4``
2. Regenerate parser: ``make antlr_build``
3. Update ``pyfcstm/highlight/pygments_lexer.py``:

   .. code-block:: python

      # Add to appropriate words() group
      (words(('state', 'pseudo', 'named', 'your_new_keyword'), suffix=r'\b'), Keyword.Declaration),

4. Update ``editors/fcstm.tmLanguage.json``:

   .. code-block:: json

      {
        "name": "keyword.declaration.fcstm",
        "match": "\\b(state|pseudo|named|your_new_keyword)\\b"
      }

5. Run validation: ``python editors/validate.py``

Customizing Colors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**For Pygments (Sphinx):**

Choose a different Pygments style in your Sphinx ``conf.py``:

.. code-block:: python

   pygments_style = 'monokai'  # or 'github', 'vim', 'vs', etc.

**For VS Code:**

Colors are controlled by your VS Code theme. The TextMate grammar assigns scopes (e.g., ``keyword.declaration.fcstm``), and your theme determines the colors for each scope.

To customize, create a custom theme or modify your ``settings.json``:

.. code-block:: json

   {
     "editor.tokenColorCustomizations": {
       "textMateRules": [
         {
           "scope": "keyword.declaration.fcstm",
           "settings": {
             "foreground": "#FF6B6B",
             "fontStyle": "bold"
           }
         }
       ]
     }
   }

Related Resources
---------------------------------------

- **FCSTM DSL Reference:** See the DSL tutorial for complete language syntax
- **VS Code Extension:** See ``editors/vscode/README.md`` for detailed extension documentation
- **Pygments Documentation:** https://pygments.org/
- **TextMate Grammar Guide:** https://macromates.com/manual/en/language_grammars
- **VS Code Language Extensions:** https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide
- **ANTLR Documentation:** https://www.antlr.org/

File Locations
---------------------------------------

.. code-block:: text

   pyfcstm/
   ├── pyfcstm/
   │   └── highlight/
   │       ├── __init__.py              # Exports FcstmLexer
   │       └── pygments_lexer.py        # Pygments lexer implementation
   ├── editors/
   │   ├── README.md                    # Detailed implementation notes
   │   ├── fcstm.tmLanguage.json        # TextMate grammar
   │   ├── validate.py                  # Validation script
   │   └── vscode/                      # VS Code extension
   │       ├── package.json             # Extension manifest
   │       ├── language-configuration.json  # Language configuration
   │       ├── README.md                # Extension documentation
   │       ├── src/                     # Extension source code
   │       │   ├── extension.ts         # Extension entry point
   │       │   ├── parser.ts            # Parser adapter
   │       │   ├── diagnostics.ts       # Syntax diagnostics provider
   │       │   ├── symbols.ts           # Document symbols provider
   │       │   ├── completion.ts        # Code completion provider
   │       │   └── hover.ts             # Hover documentation provider
   │       ├── parser/                  # Generated ANTLR parser
   │       │   ├── GrammarLexer.js      # Generated lexer
   │       │   ├── GrammarParser.js     # Generated parser
   │       │   └── GrammarVisitor.js    # Generated visitor
   │       ├── syntaxes/
   │       │   └── fcstm.tmLanguage.json    # TextMate grammar (copy)
   │       ├── snippets/
   │       │   └── fcstm.code-snippets  # Code snippets
   │       ├── scripts/                 # Verification scripts
   │       │   ├── verify-p0.2.js       # Parser verification
   │       │   ├── verify-p0.3.js       # Diagnostics verification
   │       │   ├── verify-p0.4.js       # Symbols verification
   │       │   ├── verify-p0.5.js       # Completion verification
   │       │   └── verify-p0.6.js       # Hover verification
   │       ├── dist/                    # Bundled extension
   │       │   └── extension.js         # Single bundle (246KB)
   │       └── build/                   # VSIX packages
   │           └── fcstm-language-support-0.1.0.vsix
   ├── docs/source/conf.py              # Sphinx configuration with lexer registration
   └── setup.py                         # Pygments entry point registration
