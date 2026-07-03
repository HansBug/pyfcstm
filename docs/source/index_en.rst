Welcome to pyfcstm (Python Finite Control State Machine Framework)
==================================================================

.. image:: _static/logos/logo_banner.svg
   :alt: pyfcstm - Python Finite Control State Machine Framework
   :align: center
   :width: 800px

Overview
-------------

**pyfcstm** (Python Finite Control State Machine Framework) is a powerful Python framework for parsing the **FCSTM (Finite Control State Machine) Domain-Specific Language (DSL)** and generating executable code in multiple target languages. It specializes in modeling **Hierarchical State Machines (Harel Statecharts)** with a flexible Jinja2-based template system.

Key Features
~~~~~~~~~~~~~

* **Expressive DSL Syntax**: Intuitive domain-specific language for defining states, transitions, events, and lifecycle actions
* **Hierarchical State Machines**: Full support for nested states with parent-child relationships and aspect-oriented programming
* **Multi-Language Code Generation**: Template-based rendering system supporting C, C++, Python, and custom target languages
* **PlantUML Visualization**: Automatic generation of state machine diagrams for documentation
* **ANTLR4-Based Parser**: Robust grammar parsing with detailed error reporting
* **Flexible Event System**: Local, chain, and global event scoping for complex state machine coordination
* **Lifecycle Actions**: Enter, during, and exit actions with before/after aspect support
* **Abstract and Reference Actions**: Declare abstract functions and reuse actions across states

Use Cases
~~~~~~~~~~~~~

pyfcstm is ideal for:

* **Embedded Systems**: Generate efficient state machine code for microcontrollers and IoT devices
* **Protocol Implementations**: Model communication protocols with complex state transitions
* **Game AI**: Design character behaviors and game logic with hierarchical state machines
* **Workflow Engines**: Implement business process workflows with clear state definitions
* **Control Systems**: Build industrial control logic with safety-critical state management

Quick Start
-------------

Installation
~~~~~~~~~~~~~

.. code-block:: bash

   pip install pyfcstm

The full installation checklist is in :doc:`tutorials/installation/index`.

Fast Path
~~~~~~~~~

Create ``traffic_light.fcstm`` and follow the complete walkthrough in
:doc:`tutorials/quick_start/index`. The shortest command sequence is:

.. code-block:: bash

   pyfcstm simulate -i traffic_light.fcstm -e "cycle; cycle; current"
   pyfcstm inspect -i traffic_light.fcstm --format json -o traffic_light.inspect.json
   pyfcstm generate -i traffic_light.fcstm --template python -o generated --clear
   pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml

Use ``--template`` for packaged built-in templates. Use ``-t/--template-dir``
only when rendering with a custom template directory.

Architecture
-------------

pyfcstm follows a three-stage pipeline:

1. **DSL Parsing**: ANTLR4-based parser converts DSL text into Abstract Syntax Tree (AST)
2. **Model Construction**: AST nodes are transformed into a queryable state machine model
3. **Code Generation**: Jinja2 templates render the model into target language code

The framework provides:

* **DSL Layer** (``pyfcstm.dsl``): Grammar definition, parser, and AST nodes
* **Model Layer** (``pyfcstm.model``): State machine model classes with validation
* **Rendering Engine** (``pyfcstm.render``): Template-based code generation with expression styles
* **CLI Tools** (``pyfcstm.entry``): Command-line interface for common operations

Tutorials
-------------------------

.. toctree::
    :maxdepth: 2
    :caption: Tutorials
    :hidden:

    tutorials/installation/index
    tutorials/quick_start/index
    tutorials/dsl/index
    tutorials/simulation/index
    tutorials/inspect/index
    tutorials/generation/index
    tutorials/visualization/index
    tutorials/cli/index
    tutorials/render/index
    tutorials/grammar/index
    tutorials/structure/index

* :doc:`tutorials/installation/index`
* :doc:`tutorials/quick_start/index`
* :doc:`tutorials/dsl/index`
* :doc:`tutorials/simulation/index`
* :doc:`tutorials/inspect/index`
* :doc:`tutorials/generation/index`
* :doc:`tutorials/visualization/index`
* :doc:`tutorials/cli/index`
* :doc:`tutorials/render/index`
* :doc:`tutorials/grammar/index`
* :doc:`tutorials/structure/index`

Release Notes
-------------------------

.. toctree::
    :maxdepth: 1
    :caption: Release Notes
    :hidden:

    release_notes

* :doc:`release_notes`

Best Practice
-------------------------

.. toctree::
    :maxdepth: 2
    :caption: Best Practice

.. include:: api_doc_en.rst

Community and Support
-----------------------

* **GitHub Repository**: https://github.com/HansBug/pyfcstm
* **Issue Tracker**: https://github.com/HansBug/pyfcstm/issues
* **PyPI Package**: https://pypi.org/project/pyfcstm/

License
---------

pyfcstm is released under the Apache License 2.0. See the LICENSE file for details.
