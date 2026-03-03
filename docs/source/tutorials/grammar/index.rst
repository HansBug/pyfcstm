FCSTM Syntax Highlighting Guide
===============================================

pyfcstm provides native syntax highlighting support for FCSTM DSL code through multiple implementations, making it easy to display beautifully formatted state machine code in documentation, editors, and development tools.

Overview
---------------------------------------

Two complementary implementations provide comprehensive syntax highlighting:

1. **Pygments Lexer** - For Python ecosystem tools (Sphinx, Jupyter, etc.)
2. **TextMate Grammar** - For editors and platforms supporting TextMate grammars (VS Code, GitHub, GitLab, etc.)

Both implementations are based on the ANTLR grammar and support the complete FCSTM syntax including keywords, operators, literals, comments, and built-in functions.

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

The TextMate grammar provides syntax highlighting for editors and platforms that support TextMate grammars, including VS Code, Sublime Text, Atom, GitHub, and GitLab.

Location
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The TextMate grammar file is located at:

.. code-block:: text

   editors/fcstm.tmLanguage.json

VS Code Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Method 1: Create a VS Code Extension (Recommended)**

1. Create a new directory for your extension:

   .. code-block:: bash

      mkdir fcstm-vscode
      cd fcstm-vscode

2. Create ``package.json``:

   .. code-block:: json

      {
        "name": "fcstm-language-support",
        "displayName": "FCSTM Language Support",
        "description": "Syntax highlighting for FCSTM state machine DSL",
        "version": "1.0.0",
        "engines": {
          "vscode": "^1.60.0"
        },
        "categories": ["Programming Languages"],
        "contributes": {
          "languages": [{
            "id": "fcstm",
            "aliases": ["FCSTM", "fcstm"],
            "extensions": [".fcstm", ".fcsm"],
            "configuration": "./language-configuration.json"
          }],
          "grammars": [{
            "language": "fcstm",
            "scopeName": "source.fcstm",
            "path": "./syntaxes/fcstm.tmLanguage.json"
          }]
        }
      }

3. Create ``language-configuration.json``:

   .. code-block:: json

      {
        "comments": {
          "lineComment": "//",
          "blockComment": ["/*", "*/"]
        },
        "brackets": [
          ["{", "}"],
          ["[", "]"],
          ["(", ")"]
        ],
        "autoClosingPairs": [
          { "open": "{", "close": "}" },
          { "open": "[", "close": "]" },
          { "open": "(", "close": ")" },
          { "open": "\"", "close": "\"" },
          { "open": "'", "close": "'" }
        ],
        "surroundingPairs": [
          ["{", "}"],
          ["[", "]"],
          ["(", ")"],
          ["\"", "\""],
          ["'", "'"]
        ]
      }

4. Create the syntaxes directory and copy the grammar:

   .. code-block:: bash

      mkdir syntaxes
      cp /path/to/pyfcstm/editors/fcstm.tmLanguage.json syntaxes/

5. Install the extension:

   .. code-block:: bash

      # Copy to VS Code extensions directory
      cp -r . ~/.vscode/extensions/fcstm-language-support-1.0.0/

      # Or use vsce to package and install
      npm install -g vsce
      vsce package
      code --install-extension fcstm-language-support-1.0.0.vsix

6. Restart VS Code. Files with ``.fcstm`` or ``.fcsm`` extensions will now have syntax highlighting.

**Method 2: Manual Configuration**

For quick testing without creating an extension:

1. Open VS Code settings (``Ctrl+,`` or ``Cmd+,``)
2. Search for "files.associations"
3. Add the following to your ``settings.json``:

   .. code-block:: json

      {
        "files.associations": {
          "*.fcstm": "fcstm",
          "*.fcsm": "fcstm"
        }
      }

Note: This method requires the extension from Method 1 to be installed for the grammar to work.

Sublime Text Integration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Open Sublime Text
2. Navigate to ``Preferences → Browse Packages``
3. Create a new directory: ``FCSTM``
4. Copy ``fcstm.tmLanguage.json`` to this directory
5. Restart Sublime Text
6. Files with ``.fcstm`` extension will now have syntax highlighting

GitHub and GitLab
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

GitHub and GitLab automatically recognize TextMate grammars for syntax highlighting in repositories.

**For Repository Owners:**

1. Add the grammar file to your repository:

   .. code-block:: bash

      mkdir -p .github/linguist
      cp editors/fcstm.tmLanguage.json .github/linguist/

2. Create ``.gitattributes`` to associate file extensions:

   .. code-block:: text

      *.fcstm linguist-language=FCSTM
      *.fcsm linguist-language=FCSTM

3. Commit and push. GitHub will now syntax-highlight ``.fcstm`` files in your repository.

**Note:** Full GitHub Linguist integration requires submitting the grammar to the Linguist project. The above method works for individual repositories.

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

VS Code Not Highlighting
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Check that the extension is installed in ``~/.vscode/extensions/``
2. Verify file extension is ``.fcstm`` or ``.fcsm``
3. Restart VS Code
4. Check VS Code's language mode (bottom right corner) - it should show "FCSTM"

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
- **Pygments Documentation:** https://pygments.org/
- **TextMate Grammar Guide:** https://macromates.com/manual/en/language_grammars
- **VS Code Language Extensions:** https://code.visualstudio.com/api/language-extensions/syntax-highlight-guide
- **GitHub Linguist:** https://github.com/github/linguist

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
   │   └── validate.py                  # Validation script
   ├── docs/source/conf.py              # Sphinx configuration with lexer registration
   └── setup.py                         # Pygments entry point registration
