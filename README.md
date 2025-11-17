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

**pyfcstm** is a powerful **Python framework** designed for parsing a **Finite State Machine (FSM) Domain-Specific
Language (DSL)** and generating executable code in multiple target languages based on user-defined templates. It focuses
on modeling **Hierarchical State Machines (Harel Statecharts)** and automating code generation, making it ideal for
developing embedded systems, protocol implementations, and complex control logic.

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

You can easily install pyfcstm using the `pip` command line from the official PyPI site:

```shell
pip install pyfcstm
```

**More Information**: Please refer to
the [Installation Documentation](https://pyfcstm.readthedocs.io/en/latest/tutorials/installation/index.html) for
detailed steps and environment
checks.

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

You can also use pyfcstm's core API directly within your Python projects for custom parsing and rendering workflows.

```python
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer

# 1. Define or load the DSL code
dsl_code = """
def int a = 0;
def int b = 0x0;
def int round_count = 0;  // define variables
state TrafficLight {
    // ... state and transition definitions ...
    state Red {
        during {
            a = 0x1 << 2;
        }
    }
    state Yellow;
    state Green;
    [*] -> Red :: Start effect {
        b = 0x1;
    };
    // ... more transitions ...
}
"""

if __name__ == '__main__':
    # 2. Parse the DSL code to generate an Abstract Syntax Tree (AST)
    ast_node = parse_with_grammar_entry(dsl_code, entry_name='state_machine_dsl')

    # 3. Convert the AST into a State Machine Model
    model = parse_dsl_node_to_state_machine(ast_node)

    # 4. Initialize the renderer and specify the template directory
    renderer = StateMachineCodeRenderer(
        template_dir='../fsm_generation_template'
    )

    # 5. Render the model to generate code in the specified directory
    renderer.render(model, 'test_output_x')
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

**More Information**: Please refer to
the [Template Syntax Deep Analysis](https://pyfcstm.readthedocs.io/en/latest/tutorials/render/index.html) for a
comprehensive guide on
template development.

## Contribution & Support

pyfcstm is an open-source project, and contributions in all forms are welcome:

* **Report Bugs**: If you find any issues, please submit them
  on [GitHub Issues](https://github.com/hansbug/pyfcstm/issues).
* **Submit Pull Requests**: Code improvements, new features, or documentation updates are highly appreciated.
* **Suggest Features**: Feel free to discuss any feature suggestions or improvement ideas in the Issues section.

**Documentation**: [https://pyfcstm.readthedocs.io/](https://pyfcstm.readthedocs.io/)
**Source Code**: [https://github.com/HansBug/pyfcstm](https://github.com/HansBug/pyfcstm)
**License**: [MIT License](https://github.com/hansbug/pyfcstm/blob/master/LICENSE)
