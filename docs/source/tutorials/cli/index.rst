PyFCSTM Command Line Guide
===============================================

pyfcstm is a state machine DSL tool that provides a command-line interface for state machine code conversion and generation.

Installation and Execution
---------------------------------------

Installation Methods
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. **pip Installation** (Recommended):

   .. code-block:: bash

      pip install pyfcstm

   After installation, you can use the ``pyfcstm`` command directly.

2. **Module Execution**:

   .. code-block:: bash

      python -m pyfcstm

3. **Pre-compiled Executable**:
   Download pre-compiled versions from GitHub Releases:
   https://github.com/HansBug/pyfcstm/releases

Basic Usage
---------------------

Check Version Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   pyfcstm --version

Check Help Information
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Check main command help
   pyfcstm --help

   # Check subcommand help
   pyfcstm generate --help
   pyfcstm plantuml --help

Command Function Details
-------------------------------------

plantuml Subcommand
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Convert state machine DSL code to PlantUML format code.

**Usage**:

.. code-block:: bash

   pyfcstm plantuml -i <input_file> [-o <output_file>]

**Parameter Description**:

- ``-i, --input-code``: Path to input state machine DSL file (required)
- ``-o, --output``: Path to output PlantUML file (optional, outputs to stdout if not specified)

**Examples**:

.. code-block:: bash

   # Convert and output to file
   pyfcstm plantuml -i machine.dsl -o machine.puml

   # Convert and output to console
   pyfcstm plantuml -i machine.dsl

**Next Steps**:
The generated PlantUML code needs to be used with PlantUML tools to create diagrams:

- **Online Generation**: Visit https://www.plantuml.com/plantuml/uml/ and paste the code
- **Local Generation**: Install PlantUML locally, see details at https://www.plantuml.com/

generate Subcommand
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Generate control code (such as C code) based on state machine DSL and templates.

**Usage**:

.. code-block:: bash

   pyfcstm generate -i <input_file> -t <template_dir> -o <output_dir> [--clear]

**Parameter Description**:

- ``-i, --input-code``: Path to input state machine DSL file (required)
- ``-t, --template-dir``: Path to template file directory (required)
- ``-o, --output-dir``: Output directory for generated code (required)
- ``--clear``: Clear output directory (optional flag)

**Examples**:

.. code-block:: bash

   # Generate code using templates
   pyfcstm generate -i machine.dsl -t ./templates -o ./generated

   # Clear directory before generating code
   pyfcstm generate -i machine.dsl -t ./templates -o ./generated --clear

**Description**:
This function uses preset code generation templates to automatically generate corresponding control logic code based on the state machine DSL, suitable for scenarios such as embedded systems and automated control.

Notes
----------------

- Ensure the input state machine DSL file has correct syntax
- When using the generate command, the template directory needs to contain valid template files
- The plantuml command only generates code; additional steps are required to create diagrams
- All file paths support both relative and absolute paths

For more information, please refer to the project documentation: https://github.com/HansBug/pyfcstm
