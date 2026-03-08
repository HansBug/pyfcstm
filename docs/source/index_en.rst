Welcome to pyfcstm's Documentation
=========================================================

.. raw:: html

   <div align="center">
     <img src="_static/logos/logo_banner.svg" alt="pyfcstm - Python Finite State Machine Framework" style="width: 100%; max-width: 800px; margin: 20px 0;">
   </div>

Overview
-------------

**pyfcstm** is a powerful Python framework for parsing Finite State Machine (FSM) Domain-Specific Language (DSL) and generating executable code in multiple target languages. It specializes in modeling **Hierarchical State Machines (Harel Statecharts)** with a flexible Jinja2-based template system.

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

Basic Usage
~~~~~~~~~~~~~

**1. Define a State Machine in DSL**

Create a file ``traffic_light.fcstm``:

.. code-block:: fcstm

   def int timer = 0;

   state TrafficLight {
       [*] -> Red;

       state Red {
           enter { timer = 0; }
           during { timer = timer + 1; }
       }

       state Yellow {
           enter { timer = 0; }
           during { timer = timer + 1; }
       }

       state Green {
           enter { timer = 0; }
           during { timer = timer + 1; }
       }

       Red -> Green : if [timer >= 30];
       Green -> Yellow : if [timer >= 25];
       Yellow -> Red : if [timer >= 5];
   }

**2. Generate Code**

.. code-block:: bash

   pyfcstm generate -i traffic_light.fcstm -t templates/c/ -o output/

**3. Visualize with PlantUML**

.. code-block:: bash

   pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml

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

Documentation Structure
-------------------------

.. toctree::
    :maxdepth: 2
    :caption: Tutorials

    tutorials/installation/index
    tutorials/structure/index
    tutorials/dsl/index
    tutorials/render/index
    tutorials/visualization/index
    tutorials/cli/index
    tutorials/grammar/index

.. toctree::
    :maxdepth: 2
    :caption: Best Practice

.. include:: api_doc_en.rst

.. toctree::
    :maxdepth: 2
    :caption: Contributor Guide

Community and Support
-----------------------

* **GitHub Repository**: https://github.com/HansBug/pyfcstm
* **Issue Tracker**: https://github.com/HansBug/pyfcstm/issues
* **PyPI Package**: https://pypi.org/project/pyfcstm/

License
---------

pyfcstm is released under the Apache License 2.0. See the LICENSE file for details.
