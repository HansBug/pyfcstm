# pyfcstm

[![PyPI](https://img.shields.io/pypi/v/pyfcstm)](https://pypi.org/project/pyfcstm/)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/pyfcstm)
![PyPI - Implementation](https://img.shields.io/pypi/implementation/pyfcstm)
![PyPI - Downloads](https://img.shields.io/pypi/dm/pyfcstm)

![Loc](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/HansBug/7eb8c32d6549edaa09592ca2a5a47187/raw/loc.json)
![Comments](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/HansBug/7eb8c32d6549edaa09592ca2a5a47187/raw/comments.json)
[![Maintainability](https://api.codeclimate.com/v1/badges/5b6e14a915b63faeae90/maintainability)](https://codeclimate.com/github/HansBug/pyfcstm/maintainability)
[![codecov](https://codecov.io/gh/hansbug/pyfcstm/graph/badge.svg?token=NYSTMMTC2F)](https://codecov.io/gh/hansbug/pyfcstm)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/HansBug/pyfcstm)

[![Docs Deploy](https://github.com/hansbug/pyfcstm/workflows/Docs%20Deploy/badge.svg)](https://github.com/hansbug/pyfcstm/actions?query=workflow%3A%22Docs+Deploy%22)
[![Code Test](https://github.com/hansbug/pyfcstm/workflows/Code%20Test/badge.svg)](https://github.com/hansbug/pyfcstm/actions?query=workflow%3A%22Code+Test%22)
[![Badge Creation](https://github.com/hansbug/pyfcstm/workflows/Badge%20Creation/badge.svg)](https://github.com/hansbug/pyfcstm/actions?query=workflow%3A%22Badge+Creation%22)
[![Package Release](https://github.com/hansbug/pyfcstm/workflows/Package%20Release/badge.svg)](https://github.com/hansbug/pyfcstm/actions?query=workflow%3A%22Package+Release%22)

[![GitHub stars](https://img.shields.io/github/stars/hansbug/pyfcstm)](https://github.com/hansbug/pyfcstm/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/hansbug/pyfcstm)](https://github.com/hansbug/pyfcstm/network)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/hansbug/pyfcstm)
[![GitHub issues](https://img.shields.io/github/issues/hansbug/pyfcstm)](https://github.com/hansbug/pyfcstm/issues)
[![GitHub pulls](https://img.shields.io/github/issues-pr/hansbug/pyfcstm)](https://github.com/hansbug/pyfcstm/pulls)
[![Contributors](https://img.shields.io/github/contributors/hansbug/pyfcstm)](https://github.com/hansbug/pyfcstm/graphs/contributors)
[![GitHub license](https://img.shields.io/github/license/hansbug/pyfcstm)](https://github.com/hansbug/pyfcstm/blob/master/LICENSE)

**pyfcstm** is a powerful **Python framework** for parsing **Finite State Machine (FSM) Domain-Specific Language (DSL)**
and generating executable code in multiple target languages. It specializes in modeling **Hierarchical State Machines (
Harel Statecharts)** with a flexible Jinja2-based template system, making it ideal for embedded systems, protocol
implementations, game AI, workflow engines, and complex control logic.

## Table of Contents

- [Core Features](#core-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
    - [CLI Usage](#1-using-the-command-line-interface-cli)
    - [Python API](#2-using-the-python-api)
    - [Example DSL Code](#3-example-dsl-code-traffic-light-example)
- [DSL Syntax Overview](#dsl-syntax-overview)
- [Template System](#code-generation-template-system)
- [Use Cases](#use-cases)
- [Documentation](#documentation)
- [Contributing](#contribution--support)
- [License](#license)

## Core Features

pyfcstm aims to provide a complete solution from conceptual design to code implementation. Its core strengths include:

| Feature                         | Description                                                                                                                           | Advantage                                                                                                      | Documentation Pointer                                                                                         |
|:--------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------|:---------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------|
| **FSM DSL**                     | A concise and readable DSL syntax for defining states, nesting, transitions, events, conditions, and effects.                         | Focus on state machine logic, not programming language details.                                                | [DSL Syntax Tutorial](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)                      |
| **Hierarchical State Machines** | Supports **nested states** and **composite state** lifecycles (`enter`, `during`, `exit`).                                            | Capable of modeling complex real-time systems and protocols, enhancing maintainability.                        | [DSL Syntax Tutorial - State Definitions](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)  |
| **Expression System**           | Built-in mathematical and logical expression parser supporting variable definition, conditional guards, and state effects (`effect`). | Allows defining the state machine's internal data and behavior at the DSL level.                               | [DSL Syntax Tutorial - Expression System](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)  |
| **Templated Code Generation**   | Based on the **Jinja2** template engine, rendering the state machine model into target code (e.g., C/C++, Python, Rust).              | Extremely high flexibility, supporting code generation for virtually any programming language.                 | [Template Tutorial](https://pyfcstm.readthedocs.io/en/latest/tutorials/render/index.html)                     |
| **Cross-Language Support**      | Easily enables state machine code generation for embedded or high-performance languages like **C/C++** through the template system.   | Suitable for scenarios where state machine logic needs to be deployed across different platforms or languages. | [Template Tutorial - Expression Styles](https://pyfcstm.readthedocs.io/en/latest/tutorials/render/index.html) |
| **PlantUML Integration**        | Directly converts DSL files into **PlantUML** code for generating state diagram visualizations.                                       | Facilitates design review and documentation generation.                                                        | [CLI Guide - plantuml](https://pyfcstm.readthedocs.io/en/latest/tutorials/cli/index.html)                     |

## Installation

### Basic Installation

Install pyfcstm from PyPI using pip:

```shell
pip install pyfcstm
```

### Development Installation

For development work, clone the repository and install with development dependencies:

```shell
git clone https://github.com/HansBug/pyfcstm.git
cd pyfcstm
pip install -r requirements.txt
pip install -r requirements-dev.txt
pip install -r requirements-test.txt
```

### Verify Installation

After installation, verify that pyfcstm is working correctly:

```shell
pyfcstm --version
pyfcstm --help
```

**More Information**: See
the [Installation Documentation](https://pyfcstm.readthedocs.io/en/latest/tutorials/installation/index.html) for
detailed steps and environment requirements.

## Quick Start

### 1. Using the Command Line Interface (CLI)

pyfcstm provides two main command-line subcommands: `plantuml` for visualization and `generate` for code generation.

#### Generate PlantUML State Diagram

Use the `plantuml` subcommand to convert a DSL file into PlantUML format, which can then be used to generate a state
diagram:

```shell
# Assuming your DSL code is saved in test_dsl_code.fcstm
pyfcstm plantuml -i test_dsl_code.fcstm -o traffic_light.puml
```

**Tip**: The generated `.puml` file can be rendered online at [PlantUML Server](https://www.plantuml.com/plantuml/uml/)
or locally using the PlantUML tool.

#### Templated Code Generation

Use the `generate` subcommand, along with a template directory, to generate target language code:

```shell
# -i: Input DSL file
# -t: Path to the template directory
# -o: Output directory for the generated code
pyfcstm generate -i test_dsl_code.fcstm -t template_dir/ -o generated_code_dir/
```

**Note**: You can add the `--clear` flag to clear the output directory before generation.

### 2. Using the Python API

You can integrate pyfcstm directly into your Python projects for custom parsing and rendering workflows.

#### Basic API Usage

```python
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer

# 1. Load DSL code from file or string
with open('state_machine.fcstm', 'r') as f:
    dsl_code = f.read()

# 2. Parse the DSL code to generate an Abstract Syntax Tree (AST)
ast_node = parse_with_grammar_entry(dsl_code, entry_name='state_machine_dsl')

# 3. Convert the AST into a State Machine Model
model = parse_dsl_node_to_state_machine(ast_node)

# 4. Initialize the renderer with your template directory
renderer = StateMachineCodeRenderer(template_dir='./my_templates')

# 5. Render the model to generate code
renderer.render(model, output_dir='./generated_code')
```

#### Advanced API Usage

```python
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.model import parse_dsl_node_to_state_machine

# Parse DSL
dsl_code = """
def int counter = 0;
state MyStateMachine {
    state Idle;
    state Active;
    [*] -> Idle;
    Idle -> Active :: Start;
}
"""

ast_node = parse_with_grammar_entry(dsl_code, entry_name='state_machine_dsl')
model = parse_dsl_node_to_state_machine(ast_node)

# Explore the model programmatically
print(f"State machine name: {model.name}")
print(f"Variables: {[var.name for var in model.variables]}")

# Iterate through all states
for state in model.walk_states():
    print(f"State: {state.name}, Is leaf: {state.is_leaf_state}")

    # Access transitions
    for transition in state.transitions:
        print(f"  Transition: {transition.from_state.name} -> {transition.to_state.name}")
        if transition.event:
            print(f"    Event: {transition.event.name}")
        if transition.guard:
            print(f"    Guard: {transition.guard}")

# Export to PlantUML
plantuml_code = model.export_to_plantuml()
with open('diagram.puml', 'w') as f:
    f.write(plantuml_code)

# Export back to DSL
dsl_export = model.export_to_dsl()
print(dsl_export)
```

### 3. Example DSL Code (Traffic Light Example)

The following **Traffic Light** state machine example, included in the original `README.md`, demonstrates the core
syntax of the pyfcstm DSL:

```
def int a = 0;
def int b = 0x0;
def int round_count = 0;  // define variables
state TrafficLight {
    >> during before {
        a = 0;
    }
    >> during before abstract FFT;
    >> during before abstract TTT;
    >> during after {
        a = 0xff;
        b = 0x1;
    }

    !InService -> [*] :: Error;

    state InService {
        enter {
            a = 0;
            b = 0;
            round_count = 0;
        }

        enter abstract InServiceAbstractEnter /*
            Abstract Operation When Entering State 'InService'
            TODO: Should be Implemented In Generated Code Framework
        */

        // for non-leaf state, either 'before' or 'after' aspect keyword should be used for during block
        during before abstract InServiceBeforeEnterChild /*
            Abstract Operation Before Entering Child States of State 'InService'
            TODO: Should be Implemented In Generated Code Framework
        */

        during after abstract InServiceAfterEnterChild /*
            Abstract Operation After Entering Child States of State 'InService'
            TODO: Should be Implemented In Generated Code Framework
        */

        exit abstract InServiceAbstractExit /*
            Abstract Operation When Leaving State 'InService'
            TODO: Should be Implemented In Generated Code Framework
        */

        state Red {
            during {  // no aspect keywords ('before', 'after') should be used for during block of leaf state
                a = 0x1 << 2;
            }
        }
        state Yellow;
        state Green;
        [*] -> Red :: Start effect {
            b = 0x1;
        };
        Red -> Green effect {
            b = 0x3;
        };
        Green -> Yellow effect {
            b = 0x2;
        };
        Yellow -> Red : if [a >= 10] effect {
            b = 0x1;
            round_count = round_count + 1;
        };
        Green -> Yellow : /Idle.E2;
        Yellow -> Yellow : /E2;
    }
    state Idle;

    [*] -> InService;
    InService -> Idle :: Maintain;
    Idle -> Idle :: E2;
    Idle -> [*];
}
```

## DSL Syntax Overview

The pyfcstm DSL syntax is inspired by UML Statecharts and supports the following key elements:

| Element                 | Keyword                   | Description                                                                                                                            | Example                         | Documentation Pointer                                                                       |
|:------------------------|:--------------------------|:---------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------|:--------------------------------------------------------------------------------------------|
| **Variable Definition** | `def int/float`           | Defines integer or float variables for the state machine's internal data.                                                              | `def int counter = 0;`          | [Variable Definitions](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)   |
| **State**               | `state`                   | Defines a state, supporting **Leaf States** and **Composite States** (nesting).                                                        | `state Running { ... }`         | [State Definitions](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)      |
| **Transition**          | `->`                      | Defines transitions between states, supporting **Entry** (`[*]`) and **Exit** (`[*]`) transitions.                                     | `Red -> Green;`                 | [Transition Definitions](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html) |
| **Forced Transition**   | `!`                       | Defines a forced transition, which bypasses the source state's `exit` action.                                                          | `!InService -> [*] :: Error;`   | [Transition Definitions](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html) |
| **Event**               | `::` or `:`               | The event that triggers a transition, supporting **Local Events** (`::`) and **Global Events** (`:` or `/`).                           | `Red -> Green :: Timer;`        | [Transition Definitions](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html) |
| **Guard Condition**     | `if [...]`                | A condition that must be true for the transition to occur.                                                                             | `Yellow -> Red : if [a >= 10];` | [Expression System](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)      |
| **Effect**              | `effect { ... }`          | Operations (variable assignments) executed when the transition occurs.                                                                 | `effect { b = 0x1; }`           | [Operational Statements](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html) |
| **Lifecycle Actions**   | `enter`, `during`, `exit` | Actions executed when a state is entered, active, or exited.                                                                           | `enter { a = 0; }`              | [Lifecycle Actions](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)      |
| **Abstract Action**     | `abstract`                | Declares an abstract function that must be implemented in the generated code framework.                                                | `enter abstract Init;`          | [Lifecycle Actions](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)      |
| **Aspect Action**       | `>> during`               | Special `during` action for composite states, executed **before** (`before`) or **after** (`after`) the leaf state's `during` actions. | `>> during before { ... }`      | [Lifecycle Actions](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)      |
| **Pseudo State**        | `pseudo state`            | Special leaf state that will not apply the aspect actions of the ancestor states.                                                      | `pseudo state LeafState;`       | [Pseudo States](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)          |

### Key DSL Concepts

#### Hierarchical State Management

The DSL inherently supports **state nesting**, allowing for the creation of complex, yet organized, state machines. A
composite state's lifecycle actions (`enter`, `during`, `exit`) are executed relative to its substates.
The `>> during before/after` aspect actions provide a powerful mechanism for **Aspect-Oriented Programming (AOP)**
within the state machine, enabling logic to be injected before or after the substate's transitions or actions.

#### Action Execution Order

When a leaf state is active in a hierarchical state machine, actions execute in a precise sequence. Here's a complete
example:

```
def int log_counter = 0;

state System {
    >> during before {
        log_counter = log_counter + 1;  // Executes for ALL leaf states
    }

    >> during after {
        log_counter = log_counter + 100;  // Executes for ALL leaf states
    }

    state SubSystem {
        during before {
            log_counter = log_counter + 10;  // Executes for SubSystem's children
        }

        during after {
            log_counter = log_counter + 1000;  // Executes for SubSystem's children
        }

        state Active {
            during {
                log_counter = log_counter + 50;  // Leaf state's own action
            }
        }

        state Idle;

        [*] -> Active;
    }

    [*] -> SubSystem;
}
```

**Execution order when `System.SubSystem.Active` is the active leaf state**:

**Entry Phase** (when entering the state hierarchy):

1. `System` enter actions execute first
2. `SubSystem` enter actions execute second
3. `Active` enter actions execute last

**During Phase** (while `Active` is active):

1. `System >> during before` executes: `log_counter = log_counter + 1` → `log_counter = 1`
2. `Active during` executes: `log_counter = log_counter + 50` → `log_counter = 51`
3. `System >> during after` executes: `log_counter = log_counter + 100` → `log_counter = 151`

Note: `SubSystem during before/after` do NOT execute during the leaf state's `during` phase. They only execute when
transitioning between child states.

**Exit Phase** (when leaving the state hierarchy):

1. `Active` exit actions execute first
2. `SubSystem` exit actions execute second
3. `System` exit actions execute last

**Key Points**:

- Aspect actions (`>> during before/after`) apply to all descendant leaf states and execute during the leaf's `during`
  phase
- Composite state actions (`during before/after`) only execute when transitioning between child states, NOT during a
  leaf state's `during` phase
- Execution flows from root to leaf for `before`, and leaf to root for `after`
- Multiple actions at the same level execute in definition order

#### Event Scoping

Transitions can be triggered by events with different scopes:

* **Local Event (`::`)**: The event is scoped to the source state's namespace. E.g., `StateA -> StateB :: EventX` means
  the event is `StateA.EventX`.
* **Global Event (`: /`)**: The event is scoped from the root of the state machine.
  E.g., `StateA -> StateB : /GlobalEvent` means the event is `GlobalEvent`.
* **Chain ID (`:`)**: The event is scoped relative to the current state's parent.
  E.g., `StateA -> StateB : Parent.EventY`.

## Code Generation Template System

The core value of pyfcstm lies in its highly flexible template system, which allows users complete control over the
structure and content of the generated code.

### Template Directory Structure

The template directory follows the convention over configuration principle, containing template files and a
configuration file:

```
template_directory/
├── config.yaml          # Core configuration file, defining rendering rules, globals, and filters
├── *.j2                 # Jinja2 template files for dynamic code generation
├── *.c                  # Static files, copied directly to the output directory
└── ...                  # Directory structure is preserved
```

**More Information**:
See [Template System Architecture Details](https://pyfcstm.readthedocs.io/en/latest/tutorials/render/index.html) for a
deep dive into the structure.

### Core Configuration (`config.yaml`)

The `config.yaml` file is the "brain" of the template system, defining:

1. **`expr_styles`**: Defines expression rendering rules for different target languages (e.g., C, Python), enabling
   cross-language expression conversion. This is crucial for translating DSL expressions like `a >= 10` into the correct
   syntax for C (`a >= 10`) or Python (`a >= 10`).
2. **`globals`**: Defines global variables and functions (including importing external Python functions) accessible in
   all templates. This allows for reusable logic and constants across the generated code.
3. **`filters`**: Defines custom filters for data transformation within templates. For example, a filter could be used
   to convert a state name to a valid C function name (e.g., `{{ state.name \| to_c_func_name }}`).
4. **`ignores`**: Defines files or directories to be ignored during the code generation process, using `pathspec` for
   git-like pattern matching.

**More Information**:
See [Configuration File Deep Analysis](https://pyfcstm.readthedocs.io/en/latest/tutorials/render/index.html) for
detailed
configuration options.

### Template Rendering

In the `.j2` template files, you have access to the complete **State Machine Model Object** and can use Jinja2 syntax
combined with custom filters and global functions to generate code.

**Key Model Objects**:

* `model`: The root state machine object.
* `state`: A state object, with properties like `name`, `is_leaf_state`, `transitions`, and `parent`.
* `transition`: A transition object, with properties like `from_state`, `to_state`, `guard`, and `effects`.

**Example Template Snippet (Jinja2)**:

```jinja2
{% for state in model.walk_states() %}
void {{ state.name }}_enter() {
    // Concrete enter actions
    {% for op in state.enter_operations %}
    {{ op.var_name }} = {{ op.expr | expr_render(style='c') }};
    {% endfor %}
    
    // Abstract enter actions
    {% for abstract_func in state.enter_abstract_functions %}
    {{ abstract_func.name }}(); // {{ abstract_func.doc }}
    {% endfor %}
}
{% endfor %}
```

**More Information**:
See [Template Syntax Deep Analysis](https://pyfcstm.readthedocs.io/en/latest/tutorials/render/index.html) for a
comprehensive guide on template development.

## Use Cases

pyfcstm is designed for a wide range of applications where state machines are essential:

### Embedded Systems

- **Firmware Development**: Generate C/C++ code for microcontrollers and embedded devices
- **Real-Time Systems**: Model complex control logic with hierarchical states and timing constraints
- **Hardware State Machines**: Design and implement hardware control sequences

### Protocol Implementation

- **Network Protocols**: Implement TCP/IP, HTTP, WebSocket, or custom protocol state machines
- **Communication Protocols**: Model serial communication, CAN bus, or industrial protocols
- **Parser State Machines**: Build lexers and parsers for custom data formats

### Game Development

- **AI Behavior**: Create NPC behavior trees and decision-making systems
- **Game State Management**: Manage game modes, menus, and gameplay states
- **Animation Controllers**: Control character animations and transitions

### Workflow Engines

- **Business Process Automation**: Model approval workflows and business logic
- **Task Orchestration**: Coordinate multi-step processes and dependencies
- **State-Based Applications**: Build applications with complex state transitions

### IoT and Robotics

- **Robot Control**: Implement robot behavior and navigation logic
- **Smart Device Logic**: Model IoT device states and interactions
- **Sensor Fusion**: Coordinate multiple sensors and actuators

## Documentation

- **Full Documentation**: [https://pyfcstm.readthedocs.io/](https://pyfcstm.readthedocs.io/)
- **DSL Syntax Tutorial**: [DSL Reference](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)
- **Template System Guide**: [Template Tutorial](https://pyfcstm.readthedocs.io/en/latest/tutorials/render/index.html)
- **CLI Reference**: [CLI Guide](https://pyfcstm.readthedocs.io/en/latest/tutorials/cli/index.html)
- **API Documentation**: [API Reference](https://pyfcstm.readthedocs.io/en/latest/api/index.html)

## Contribution & Support

pyfcstm is an open-source project under the LGPLv3 license, and contributions are welcome:

- **Report Bugs**: Submit issues on [GitHub Issues](https://github.com/hansbug/pyfcstm/issues)
- **Submit Pull Requests**: See [CONTRIBUTING.md](https://github.com/hansbug/pyfcstm/blob/master/CONTRIBUTING.md) for
  guidelines
- **Suggest Features**: Discuss feature ideas in the Issues section
- **Ask Questions**: Use GitHub Discussions or Issues for questions

**Source Code**: [https://github.com/HansBug/pyfcstm](https://github.com/HansBug/pyfcstm)

## License

This project is licensed under
the [GNU Lesser General Public License v3 (LGPLv3)](https://github.com/hansbug/pyfcstm/blob/master/LICENSE).
