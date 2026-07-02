# pyfcstm (Python Finite Control State Machine Framework)

<div align="center">
  <img src="logos/logo_banner.svg" alt="pyfcstm - Python Finite Control State Machine Framework" width="800"/>
</div>

<div align="center">

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
[![GitHub license](https://img.shields.io/github/license/hansbug/pyfcstm)](https://github.com/hansbug/pyfcstm/blob/main/LICENSE)

</div>

---

**pyfcstm** is the **Python Finite Control State Machine Framework**, a powerful Python framework for parsing the
**FCSTM (Finite Control State Machine) Domain-Specific Language (DSL)** and generating executable code in multiple
target languages. It specializes in modeling **Hierarchical State Machines (Harel Statecharts)** with a flexible
Jinja2-based template system, making it ideal for embedded systems, protocol implementations, game AI, workflow
engines, and complex control logic.

Out of the box, pyfcstm can parse, visualize, simulate, inspect, and generate code from FCSTM state machines. For
source-code generation, pyfcstm ships packaged built-in templates for common starting points and still supports fully
custom target-language template directories.

## Table of Contents

- [Core Features](#core-features)
- [Installation](#installation)
- [Quick Start](#quick-start)
    - [CLI Usage](#1-using-the-command-line-interface-cli)
    - [Python API](#2-using-the-python-api)
    - [Example DSL Code](#3-example-dsl-code-traffic-light-example)
- [DSL Syntax Overview](#dsl-syntax-overview)
- [Template System](#code-generation-template-system)
- [Static Diagnostics — Code List](#static-diagnostics-codes)
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
| **Templated Code Generation**   | Based on the **Jinja2** template engine, rendering the state machine model into target code through packaged built-in templates or custom template directories. | Use built-in `python`, `c`, `c_poll`, `cpp`, and `cpp_poll` templates as starting points, or generate for virtually any language with your own templates. | [Template Tutorial](https://pyfcstm.readthedocs.io/en/latest/tutorials/render/index.html)                     |
| **Cross-Language Support**      | Easily enables state machine code generation for embedded or high-performance languages like **C/C++** through the template system.   | Suitable for scenarios where state machine logic needs to be deployed across different platforms or languages. | [Template Tutorial - Expression Styles](https://pyfcstm.readthedocs.io/en/latest/tutorials/render/index.html) |
| **PlantUML Integration**        | Directly converts DSL files into **PlantUML** code, with preset detail levels and fine-grained visualization options.                | Facilitates design review and documentation generation.                                                        | [Visualization Guide](https://pyfcstm.readthedocs.io/en/latest/tutorials/visualization/index.html)            |
| **Simulation Runtime**          | Runs FCSTM models directly in Python or from an interactive CLI REPL / batch executor.                                                | Lets you validate behavior before committing to generated code.                                                | [Simulation Guide](https://pyfcstm.readthedocs.io/en/latest/tutorials/simulation/index.html)                  |
| **Syntax Highlighting**         | Includes FCSTM syntax highlighting for Pygments and editor integrations, including a VS Code extension in this repository.            | Improves authoring, documentation, and review workflows around `.fcstm` files.                                 | [Syntax Highlighting Guide](https://pyfcstm.readthedocs.io/en/latest/tutorials/grammar/index.html)            |
| **Structured Diagnostics**      | `pyfcstm.diagnostics` ships **59 diagnostic codes** (20 errors / 32 warnings / 7 infos) covering parse errors, design-health issues (deadlock, unreachable, redundant transitions, const-folded guards, etc.), Layer 0 use-def dataflow analysis, and optional verify-backed checks. | Replace ad-hoc regex / message scraping with a stable structured API; codes carry `for_llm` payloads to drive LLM-assisted repair. | [Diagnostics Code List](#static-diagnostics-codes) |
| **`inspect_model()` API**       | One-call structured view of a state machine: states / transitions / variables / events / metrics + reachability graph + var dataflow + aspect impact map + diagnostics. Round-trippable via `to_json()` against a published JSON schema. | Drop-in replacement for hand-written model walkers; single source of truth for downstream tooling.             | [inspect_model API](https://pyfcstm.readthedocs.io/en/latest/api_doc/diagnostics/inspect.html)                |
| **`pyfcstm inspect` CLI**       | Emits a human-readable diagnostic report by default, while `--format json` preserves the full stable inspect JSON; verify-backed diagnostics stay disabled unless `--enable-verify` is passed. | Makes diagnostics usable for humans first and still scriptable for CI, editor tooling, and LLM repair loops.  | [CLI Guide](https://pyfcstm.readthedocs.io/en/latest/tutorials/cli/index.html)                                |
| **Suggested-Fix + VS Code Quick-Fix** | Selected diagnostics carry a `suggested_fix` payload (kind / anchor / text template) that the VS Code extension consumes as auto-apply quick-fixes; each fix is parse-back-verified. | Auto-fix loop for both humans and LLM agents; no regex patching. | [VS Code Extension](https://pyfcstm.readthedocs.io/en/latest/tutorials/grammar/index.html) |
| **Cross-End Parity (py / js)**  | Python `inspect_model().diagnostics` and `@pyfcstm/jsfcstm` `inspectModel().diagnostics` emit byte-equivalent sets (normalized `code + severity + refs`), locked by cross-end parity tests. | Same diagnostics surface in CLI tooling, server-side processors, and browser-based editors / language servers. | [Diagnostics Code List](#static-diagnostics-codes) |

## Installation

### Basic Installation

pyfcstm requires Python 3.7+ and is tested on CPython 3.7 through 3.14. It is published on PyPI:

```shell
pip install pyfcstm
```

You can invoke the CLI either as `pyfcstm` or as a Python module:

```shell
python -m pyfcstm --help
```

The GitHub Actions unit test matrix covers CPython 3.7 through 3.14 on Linux, Windows, and macOS.

### Install the Latest Main Branch

If you want the newest code before the next release:

```shell
pip install -U git+https://github.com/hansbug/pyfcstm@main
```

### Development Installation

For local development, install the package itself in editable mode first, then add the extra dependency groups you
need:

```shell
git clone https://github.com/HansBug/pyfcstm.git
cd pyfcstm
pip install -e .
pip install -e ".[dev,test,doc]"
```

If you also need packaging helpers, install the build extras as well:

```shell
pip install -e ".[build]"
```

### Verify Installation

After installation, verify that pyfcstm is working correctly:

```shell
pyfcstm --version
pyfcstm --help
python -m pyfcstm --help
```

**More Information**: See
the [Installation Documentation](https://pyfcstm.readthedocs.io/en/latest/tutorials/installation/index.html) for
detailed steps and environment requirements.

## Quick Start

### 1. Using the Command Line Interface (CLI)

pyfcstm provides several command-line subcommands, including:

- `plantuml` for visualization
- `generate` for template-based code generation
- `simulate` for interactive or batch execution
- `inspect` for human-readable diagnostics by default, or structured model and diagnostic JSON with `--format json`

Before using them, create a small FCSTM file such as `traffic_light.fcstm`:

```fcstm
def int timer = 0;

state TrafficLight {
    [*] -> Red;

    state Red {
        during {
            timer = timer + 1;
        }
    }

    state Yellow {
        during {
            timer = timer + 1;
        }
    }

    state Green {
        during {
            timer = timer + 1;
        }
    }

    Red -> Green : if [timer >= 30] effect { timer = 0; };
    Green -> Yellow : if [timer >= 25] effect { timer = 0; };
    Yellow -> Red : if [timer >= 5] effect { timer = 0; };
}
```

#### Generate PlantUML State Diagram

Use the `plantuml` subcommand to convert a DSL file into PlantUML format:

```shell
pyfcstm plantuml -i traffic_light.fcstm -o traffic_light.puml

# Use a full-detail preset and override specific options
pyfcstm plantuml -i traffic_light.fcstm -l full \
  -c show_variable_definitions=true \
  -c show_lifecycle_actions=true \
  -o traffic_light_full.puml
```

**Tip**: The generated `.puml` file can be rendered online at [PlantUML Server](https://www.plantuml.com/plantuml/uml/)
or locally using the PlantUML tool. If `-o/--output` is omitted, PlantUML is written to stdout.

#### Run the State Machine in the CLI Simulator

Use the `simulate` subcommand when you want to validate the DSL behavior before writing templates:

```shell
# Interactive REPL
pyfcstm simulate -i traffic_light.fcstm

# Batch mode
pyfcstm simulate -i traffic_light.fcstm -e "current; cycle 3; history 3"
```

In interactive mode, useful commands include `cycle`, `current`, `events`, `history`, `init`, and `export`.

#### Templated Code Generation

Use the `generate` subcommand with either a packaged built-in template or a custom template directory.

Built-in templates are selected with `--template`:

```shell
pyfcstm generate -i traffic_light.fcstm --template python -o ./generated/python --clear
```

Custom templates are still supported with `-t/--template-dir`:

```shell
pyfcstm generate -i traffic_light.fcstm -t ./templates/c -o ./generated/c --clear
```

Built-in templates currently include `python`, `c`, `c_poll`, `cpp`, and `cpp_poll`; they are packaged from the repository
`templates/` tree and exposed through `pyfcstm generate --template ...`. The `cpp` and `cpp_poll` templates are early first-class C++ templates that keep `experimental: true` while their integration surface stabilizes. A custom template directory must contain a
`config.yaml`; any `.j2` files are rendered, and non-template files are copied as-is.

### 2. Using the Python API

You can integrate pyfcstm directly into your Python projects for custom parsing and rendering workflows.

#### Parse, Inspect, and Visualize a Model

```python
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.model.plantuml import PlantUMLOptions

# 1. Load DSL code from file or string
with open('traffic_light.fcstm', 'r', encoding='utf-8') as f:
    dsl_code = f.read()

# 2. Parse the DSL code to generate an Abstract Syntax Tree (AST)
ast_node = parse_with_grammar_entry(dsl_code, entry_name='state_machine_dsl')

# 3. Convert the AST into a State Machine Model
model = parse_dsl_node_to_state_machine(ast_node)

# 4. Inspect the parsed model
print(f"Root state: {model.root_state.name}")
print(f"Variables: {list(model.defines)}")

for state in model.walk_states():
    print(f"State: {'.'.join(state.path)} (leaf={state.is_leaf_state})")

# 5. Export to PlantUML
plantuml_code = model.to_plantuml(
    PlantUMLOptions(detail_level='full', show_lifecycle_actions=True)
)
with open('diagram.puml', 'w', encoding='utf-8') as f:
    f.write(plantuml_code)

# 6. Export back to DSL text
print(str(model.to_ast_node()))
```

#### Inspect a Model and Read Structured Diagnostics

From the command line, inspect a model with the default human-readable report, or request the full stable JSON explicitly:

```shell
pyfcstm inspect -i buggy.fcstm
pyfcstm inspect -i buggy.fcstm --color always
pyfcstm inspect -i buggy.fcstm --format json -o inspect_report.json
pyfcstm inspect -i buggy.fcstm --format json --enable-verify --max-complexity-tier smt_linear --smt-timeout-ms 1000
```

The default CLI path is a checker-style human report and does not run verify-backed checks. Human and draft LLM-oriented formats include a small source context window around each diagnostic so nearby state and transition structure remain visible. Use `--color auto|always|never` to control ANSI color for that human report only; `--format json`, `--format llm-json`, and `--format llm-md` never include ANSI escapes. Pass `--format json` when scripts, CI jobs, or editor tooling need the full `inspect_model(model).to_json()` contract. Draft LLM-oriented formats are also available as `--format llm-json` and `--format llm-md`. Pass `--enable-verify` explicitly to append inspect-eligible `pyfcstm.verify` diagnostics. `bmc_search`, `k_unrollings`, and
`k_unrollings_times_branching` remain forbidden in the automatic inspect path. `--smt-timeout-ms 0` is forwarded
unchanged to the SMT solver layer and follows Z3 semantics, where `0` means no finite timeout is configured.

The human report is plain ASCII when color is disabled or unavailable:

```text
[WARN] W_UNWRITTEN_READ_VAR
  Variable 'x' is read but never written by any action or transition effect.
  --> buggy.fcstm:1:1
   |
 1 | def int x = 0;
   | ^^^^^^^^^^^^^^
 2 | state Root {
   |
   = source: inspect-static
   = why: The variable is used as input but never updated after its initial definition, so model behavior may be accidentally constant.
   = fix: kind: add_write; target: action_or_effect; rationale: Add the intended update if the variable should change.
   = do-not: Do not add a meaningless self-assignment.
```

```python
from pyfcstm.diagnostics import inspect_model

# Reuse the `model` object from the previous example.
report = inspect_model(model)

# 1. Structured view: states, transitions, variables, events, metrics,
#    plus reachability_graph / var_dataflow / aspect_impact_map / action_ref_graph.
for variable in report.variables:
    print(
        variable.name,
        'reads:', variable.read_in_guards,
        'writes:', variable.written_in_effects,
        'affects guard (direct/indirect):',
        variable.affects_guard_directly, variable.affects_guard_indirectly,
    )

# 2. Diagnostics: 59 codes (20 E / 32 W / 7 I), structured + LLM-friendly.
for diag in report.diagnostics:
    print(f'[{diag.severity}] {diag.code}: {diag.message}')
    if diag.refs.get('suggested_fix'):
        print('  quick-fix:', diag.refs['suggested_fix'])

# 3. Round-trip to JSON (stable schema, see pyfcstm/diagnostics/schema.json).
import json
json.dumps(report.to_json(), indent=2)
```

**Real-world showcase.** The following DSL is the kind of LLM-generated input pyfcstm catches in one pass — five
distinct issues across parse, dataflow, redundancy, and structural buckets:

```fcstm
def int counter = 0;          // written but never read       → W_WRITE_ONLY_VAR
def int unused = 0;           // doesn't affect any guard     → W_UNREFERENCED_VAR
def int ready  = 0;           // read in guard, never written → W_UNWRITTEN_READ_VAR + W_GUARD_VARS_NEVER_CHANGE

state Root {
    state A;
    state B;
    state Orphan;             //                              → W_UNREACHABLE_STATE
    [*] -> A;
    A -> B : if [ready > 0];  // guard vars never change      → W_GUARD_VARS_NEVER_CHANGE
    A -> B : if [ready > 0];  // duplicate of the above       → W_REDUNDANT_TRANSITION
    B -> A effect { counter = counter; };  //                 → W_EFFECT_SELF_ASSIGN
}
```

```python
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.diagnostics import inspect_model

dsl = open('buggy.fcstm').read()
model = parse_dsl_node_to_state_machine(parse_with_grammar_entry(dsl, 'state_machine_dsl'))
report = inspect_model(model)
for d in report.diagnostics:
    print(f'{d.severity:7} {d.code:30} {d.message}')
```

The equivalent CLI path is:

```shell
pyfcstm inspect -i buggy.fcstm --format json --enable-verify --max-complexity-tier smt_linear
```

The full catalog of codes (with minimal triggering DSL for each) is documented under
[Static Diagnostics — Code List](#static-diagnostics-codes) further down.

#### Render Code and Simulate in Python

```python
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.simulate import SimulationRuntime

# Reuse the `model` object from the previous example.

renderer = StateMachineCodeRenderer(template_dir='./templates/c')
renderer.render(model, output_dir='./generated/c', clear_previous_directory=True)

runtime = SimulationRuntime(model)
runtime.cycle()

print(f"Current state: {'.'.join(runtime.current_state.path)}")
print(f"Variables: {runtime.vars}")
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
| **Forced Transition**   | `!`                       | A shorthand that expands into one or more normal transitions; exit actions still execute normally.                                     | `! * -> ErrorHandler :: Error;` | [Transition Definitions](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html) |
| **Event Definition**    | `event`                   | Optionally declares an event explicitly, including a display name for visualization.                                                   | `event Start named "Start";`    | [Event Definitions](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)      |
| **Event Reference**     | `::`, `:`, `/`            | Triggers a transition with local (`::`), chain (`:`), or root-relative absolute (`/`) event scoping.                                  | `Red -> Green :: Timer;`        | [Event Scoping](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)          |
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

Understanding how actions execute in hierarchical state machines is crucial for building correct state machine logic.
The execution order differs significantly between **leaf states** (states with no children) and **composite states** (
states with children).

Here's a complete example demonstrating the execution order:

```
def int log_counter = 0;

state System {
    // Aspect actions with >> apply to ALL descendant leaf states
    // These execute during the leaf state's "during" phase
    >> during before {
        log_counter = log_counter + 1;  // Executes for ALL leaf states (Active, Idle)
    }

    >> during after {
        log_counter = log_counter + 100;  // Executes for ALL leaf states (Active, Idle)
    }

    state SubSystem {
        // Composite state actions (without >>) execute ONLY when entering/exiting the composite state
        // CRITICAL: during before/after are NOT triggered during child-to-child transitions!

        // during before: executes ONLY on [*] -> Child (entering composite state from parent)
        //                AFTER SubSystem.enter but BEFORE Child.enter
        //                NOT executed on Child1 -> Child2 transitions
        during before {
            log_counter = log_counter + 10;  // Only when entering from parent: [*] -> Active
        }

        // during after: executes ONLY on Child -> [*] (exiting composite state to parent)
        //               AFTER Child.exit but BEFORE SubSystem.exit
        //               NOT executed on Child1 -> Child2 transitions
        during after {
            log_counter = log_counter + 1000;  // Only when exiting to parent: Idle -> [*]
        }

        state Active {
            // Leaf state's own during action
            during {
                log_counter = log_counter + 50;  // Executes every cycle while Active is the current state
            }
        }

        state Idle {
            during {
                log_counter = log_counter + 5;
            }
        }

        [*] -> Active;                        // Triggers SubSystem.during before
        Active -> Idle :: Pause;              // Does NOT trigger during before/after
        Idle -> Active :: Resume;             // Does NOT trigger during before/after
        Idle -> [*] :: Stop;                  // Triggers SubSystem.during after
    }

    [*] -> SubSystem;
}
```

**Complete Execution Order for `System.SubSystem.Active`**:

**Scenario 1: Initial Entry** (`System.[*] -> SubSystem -> [*] -> Active`)

**Entry Phase**:

1. `System.enter` - Root state enter actions
2. `SubSystem.enter` - Composite state enter actions
3. `SubSystem.during before` - **Triggered** (because `[*] -> Active`)
4. `Active.enter` - Leaf state enter actions

**During Phase** (each cycle while `Active` remains active):

1. `System >> during before` - Aspect action (executes for ALL leaf states)
2. `Active.during` - Leaf state's own during action
3. `System >> during after` - Aspect action (executes for ALL leaf states)

Note: `SubSystem.during before/after` do **NOT** execute during the `during` phase.

**Scenario 2: Child-to-Child Transition** (`Active -> Idle :: Pause`)

**Transition Sequence**:

1. `Active.exit` - Leaf state exit actions
2. (Transition effect, if any)
3. `Idle.enter` - Leaf state enter actions

**CRITICAL**: `SubSystem.during before/after` are **NOT triggered** during child-to-child transitions!

**Scenario 3: Exit from Composite State** (`Idle -> [*] :: Stop`)

**Exit Phase**:

1. `Idle.exit` - Leaf state exit actions
2. `SubSystem.during after` - **Triggered** (because `Idle -> [*]`)
3. `SubSystem.exit` - Composite state exit actions
4. `System.exit` - Root state exit actions

**Key Concepts**:

**Aspect Actions (`>> during before/after`)**:

- Apply to **all descendant leaf states** in the hierarchy
- Execute during the **leaf state's `during` phase** (every cycle)
- Flow from root to leaf for `before`, leaf to root for `after`
- Enable cross-cutting concerns like logging, monitoring, validation

**Composite State Actions (`during before/after` without `>>`)**:

- `during before`: Executes **ONLY** when entering composite state from parent (`[*] -> Child`)
    - Executes AFTER composite state's `enter` but BEFORE child state's `enter`
    - **NOT triggered** during child-to-child transitions (`Child1 -> Child2`)
- `during after`: Executes **ONLY** when exiting composite state to parent (`Child -> [*]`)
    - Executes AFTER child state's `exit` but BEFORE composite state's `exit`
    - **NOT triggered** during child-to-child transitions (`Child1 -> Child2`)
- Do **NOT** execute during a leaf state's `during` phase
- Used for setup/cleanup when entering/exiting the composite state boundary

**Leaf State Actions (`during`)**:

- Execute every cycle while the leaf state is active
- Sandwiched between ancestor aspect `before` and `after` actions

**Execution Flow Summary**:

- **Entry** (from parent): `State.enter` → `State.during before` → `Child.enter`
- **During** (each cycle): Aspect `>> during before` → Leaf `during` → Aspect `>> during after`
- **Exit** (to parent): `Child.exit` → `State.during after` → `State.exit`
- **Child-to-Child Transition**: `Child1.exit` → (transition effect) → `Child2.enter` (no `during before/after`)

#### Event Scoping

Transitions can be triggered by events with different scopes:

* **Local Event (`::`)**: The event is scoped to the source state's namespace. E.g., `StateA -> StateB :: EventX` means
  the event becomes `Root.StateA.EventX`.
* **Chain Event (`:`)**: The event is scoped to the parent state's namespace, so sibling transitions can share it.
  E.g., `StateA -> StateB : EventX` means the event becomes `Root.EventX`.
* **Absolute Event (`: /...`)**: The event is resolved from the root state explicitly.
  E.g., `StateA -> StateB : /System.Reset` means the event path is `Root.System.Reset`.

If you want an event to appear with a human-friendly label in diagrams, declare it explicitly first, for example
`event Reset named "System Reset";`.

## Code Generation Template System

The core value of pyfcstm lies in its highly flexible template system, which allows users complete control over the
structure and content of the generated code.

### Template Directory Structure

The template directory follows the convention-over-configuration principle and contains a required configuration file
plus any mix of renderable or static assets:

```
template_directory/
├── config.yaml          # Core configuration file, defining rendering rules, globals, and filters
├── *.j2                 # Jinja2 template files for dynamic code generation
├── *.c                  # Static files, copied directly to the output directory
└── ...                  # Directory structure is preserved
```

pyfcstm ships packaged built-in templates declared in `pyfcstm/template/index.json`, currently `python`, `c`,
`c_poll`, `cpp`, and `cpp_poll`. Use them when you want a ready reference runtime:

```shell
pyfcstm generate -i machine.fcstm --template python -o ./out --clear
```

For project-specific runtime/framework integration, prepare a custom template directory and pass it to
`pyfcstm generate -t`:

```shell
pyfcstm generate -i machine.fcstm -t ./template_directory -o ./out --clear
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

* `model`: The root state machine object, with `model.defines`, `model.root_state`, and `model.walk_states()`.
* `state`: A state object, with properties like `name`, `path`, `is_leaf_state`, `transitions`, and helper methods
  such as `list_on_enters()` / `list_on_durings()` / `list_on_exits()`.
* `transition`: A transition object, with properties like `from_state`, `to_state`, `guard`, and `effects`.

**Example Template Snippet (Jinja2)**:

```jinja2
{% for state in model.walk_states() %}
void {{ state.name }}_enter() {
    {% for id, enter in state.list_on_enters(with_ids=True) %}
    {% if enter.is_abstract %}
    {{ enter.name }}();
    {% else %}
    {% for op in enter.operations %}
    {{ op.var_name }} = {{ op.expr | expr_render(style='c') }};
    {% endfor %}
    {% endif %}
    {% endfor %}
}
{% endfor %}
```

**More Information**:
See [Template Syntax Deep Analysis](https://pyfcstm.readthedocs.io/en/latest/tutorials/render/index.html) for a
comprehensive guide on template development.

## Static Diagnostics — Code List <a name="static-diagnostics-codes"></a>

Calling `inspect_model(machine).diagnostics` on a parsed model returns a list of `ModelDiagnostic` objects. The
catalog covers **59 codes — 20 errors / 32 warnings / 7 infos**. The default inspect analysis path remains static and does not
run an SMT backend; verify-backed diagnostics require `enable_verify=True` or `pyfcstm inspect --enable-verify`. The CLI defaults to a human-readable report; use `pyfcstm inspect --format json` for the full stable JSON payload.
Every code is reachable from the minimal DSL snippet in the right-hand column; see
[`pyfcstm/diagnostics/codes.yaml`](pyfcstm/diagnostics/codes.yaml) for full per-code metadata (refs schema,
`for_llm` payload, suggested-fix template, parity flags).

#### Errors (`E_*`) — model is invalid, must fix (20)

| Code | What it catches | Minimal DSL example |
|------|-----------------|---------------------|
| `E_UNDEFINED_VAR` | A guard, effect, or lifecycle-action block references a name that was never declared with a top-level `def`. | `def int x = 0; state Root { state A; state B; A -> B : if [unknown_var > 0]; }` |
| `E_DUPLICATE_VAR` | A top-level `def` re-declares an identifier defined earlier in the file. | `def int x = 0; def int x = 1; state Root { state A; }` |
| `E_MISSING_STATE` | A transition target references a state path that cannot be resolved in the surrounding hierarchy. | `state Root { state A; A -> NoSuch; }` |
| `E_DUPLICATE_STATE` | Two states share the same name within the same parent scope. | `state Root { state A; state A; }` |
| `E_EVENT_REF_INVALID` | The textual form of an event reference is syntactically invalid. | `state Root { state A; state B; A -> B : /; }` |
| `E_EVENT_NOT_FOUND` | An event reference parses correctly but does not resolve to any event defined in the targeted scope. | `state Root { state A; state B; A -> B :: NoEvent; }` |
| `E_DANGLING_TRANSITION` | A transition cannot resolve either its source or its target. | `state Root { state A; NoSuch -> A; }` |
| `E_TYPE_MISMATCH` | A guard, effect, or assignment mixes the arithmetic and boolean expression categories. | `def int x = 0; state Root { state A; state B; A -> B : if [x]; }` |
| `E_FORCED_TRANSITION_EXPANSION` | A forced transition (`!State -> ...` or `!*`) cannot be expanded because the source or target is unresolved. | `state Root { state A; !NoSuch -> A; }` |
| `E_INITIAL_TRANSITION_INVALID` | A composite state either lacks an entry transition (`[*] -> child`) or declares one targeting a non-direct child. | `state Root { state Outer { state Inner; } }` |
| `E_DUPLICATE_FUNCTION_NAME` | Two named lifecycle actions within the same state share the same name. | `state Root { state A { enter Foo { } enter Foo { } } }` |
| `E_DURING_ASPECT_INVALID` | A `during` block is declared inconsistently with the host state's leaf/composite kind. | `state Root { state A { during before { } } }` |
| `E_PSEUDO_NOT_LEAF` | A state was declared with the `pseudo` keyword but has nested substates. | `state Root { pseudo state Outer { state Inner; [*] -> Inner; } }` |
| `E_NAMED_FUNCTION_REF_CYCLE` | A lifecycle action `ref` chain forms a cycle and never reaches a concrete or abstract action. | `state Root { state A { enter First ref Second; enter Second ref First; } [*] -> A; }` |
| `E_NAMED_FUNCTION_REF_NOT_FOUND` | A `ref` lifecycle action could not resolve its target named action. | `state Root { state A { enter ref NoSuch.NoSuch; } }` |
| `E_IMPORT_NOT_FOUND` | An `import` statement points at a source file that cannot be found, read, or parsed. | `state System { import "missing.fcstm" as Sub; }` |
| `E_IMPORT_CIRCULAR` | A cycle was detected while resolving `import` statements between two or more state-machine source files. | `# a.fcstm state A { import "b.fcstm" as B; } # b.fcstm state B { import "a.fcstm" as A; }` |
| `E_IMPORT_ALIAS_CONFLICT` | An `import` alias clashes with an existing child state (or another import alias) under the same composite. | `state System { state Worker; import "worker.fcstm" as Worker; }` |
| `E_IMPORT_DUPLICATE_MAPPING` | Two or more mapping clauses under the same `import { ... }` block target the same imported name. | `state System { import "sub.fcstm" as Sub { def x = a; def x = b; } }` |
| `E_IMPORT_MAPPING_INVALID` | An import-mapping clause refers to a source name that does not exist in the imported machine. | `state System { import "sub.fcstm" as Sub { def x = no_such_var; } }` |

#### Warnings (`W_*`) — high-confidence design-health issues (32)

| Code | What it catches | Minimal DSL example |
|------|-----------------|---------------------|
| `W_UNREACHABLE_STATE` | A state is not reachable from the model's root entry path via any sequence of normal or forced transitions. | `state Root { state Idle; state Orphan; [*] -> Idle; }` |
| `W_GUARD_CONST_FALSE` | A transition guard folds to literal `false` via the built-in constant folder — transition never fires. | `state Root { state A; state B; [*] -> A; A -> B : if [(0x0F & 0xF0) != 0]; }` |
| `W_GUARD_CONST_TRUE` | A transition guard folds to literal `true` via the built-in constant folder — transition always fires. | `state Root { state A; state B; [*] -> A; A -> B : if [(1 + 2) == 3]; }` |
| `W_DURING_CONST_ASSIGN` | A concrete `during` action assigns a variable to the same literal-only numeric value every cycle. | `def int counter = 0; state Root { state Idle { during { counter = (2 + 3) * 4; } } [*] -> Idle; }` |
| `W_UNUSED_EVENT` | An `event` declaration is never referenced by any transition. | `state Root { event Unused; state A; state B; [*] -> A; A -> B :: SomethingElse; }` |
| `W_DEADLOCK_LEAF` | A non-pseudo leaf state has no outgoing transition. | `state Root { state A; [*] -> A; }` |
| `W_INITIAL_UNCONDITIONAL_MISSING` | A composite state has no unconditional `[*] -> child` entry transition. | `def int ready = 0; state Root { state A; [*] -> A : if [ready > 0]; }` |
| `W_FORCED_NEVER_EXPANDS` | A forced transition declaration has no concrete child state in its scope to expand from. | `state Root { state A { !* -> [*]; } [*] -> A; }` |
| `W_DEAD_NAMED_ACTION` | A named action belongs to an unreachable state and is not referenced by any reachable action ref. | `state Root { state A; state B { enter Cleanup {} } [*] -> A; }` |
| `W_UNREFERENCED_VAR` | (Layer 0) A variable cannot affect any transition guard either directly or through the use-def graph, with no abstract action in scope. | `def int unused = 0; def int ready = 0; state Root { state A; state B; [*] -> A; A -> B : if [ready > 0]; }` |
| `W_GUARD_VARS_NEVER_CHANGE` | A transition guard reads variables that are never changed by any lifecycle action or transition effect. | `def int ready = 0; state Root { state A; state B; [*] -> A; A -> B : if [ready > 0]; }` |
| `W_UNWRITTEN_READ_VAR` | A variable is read in guards or actions but is never written by any lifecycle action or transition effect. | `def int ready = 0; state Root { state A; state B; [*] -> A; A -> B : if [ready > 0]; }` |
| `W_WRITE_ONLY_VAR` | A variable is written by actions or effects but is never read by any guard, action, or effect. | `def int counter = 0; state Root { state A { during { counter = 1; } } [*] -> A; }` |
| `W_REDUNDANT_TRANSITION` | Multiple transitions share the same source, target, event, guard, and effect. | `state Root { state A; state B; [*] -> A; A -> B :: Go; A -> B :: Go; }` |
| `W_SELF_TRANSITION_NOP` | A leaf self-transition has no event, guard, effect, lifecycle action, or ancestor aspect action. | `state Root { state A; [*] -> A; A -> A; }` |
| `W_EFFECT_SELF_ASSIGN` | An effect statement assigns a variable directly to itself. | `def int x = 0; state Root { state A; state B; [*] -> A; A -> B effect { x = x; } }` |
| `W_FORCED_OVERRIDES_NORMAL` | A forced transition expands to the same source, target, event, and guard as an existing normal transition. | `state Root { state A; state B; [*] -> A; A -> B :: Go; !A -> B :: Go; }` |
| `W_SHADOWED_EVENT` | A local event name shadows a chain or absolute event with the same leaf name. | `state Root { event Tick; state A; state B; [*] -> A; A -> B : Tick; B -> A :: Tick; }` |
| `W_NAMED_ACTION_SHADOWS_ANCESTOR` | A named lifecycle action reuses the same function name as an ancestor-scoped named action. | `state Root { enter Sync { } state Child { enter Sync { } } [*] -> Child; }` |
| `W_LITERAL_TYPE_NARROWING` | An `int` variable is initialized or assigned directly from a floating-point literal (silent truncation). | `def int truncated = 3.5; state Root { state A; [*] -> A; }` |
| `W_ASPECT_NO_DESCENDANT_LEAF` | A `>> during` aspect is attached to a state with no descendant non-pseudo leaf states. | `state Root { pseudo state Marker; [*] -> Marker; >> during before { } }` |
| `W_HIGH_VAR_TO_LEAF_RATIO` | The number of variables is high relative to the number of non-pseudo leaf states (fact-flag bloat heuristic). | `def int a = 0; def int b = 0; def int c = 0; state Root { state A; [*] -> A; }` |
| `W_DEEP_HIERARCHY` | The state hierarchy exceeds the configured maximum depth. | `state Root { state A { state B { state C; [*] -> C; } [*] -> B; } [*] -> A; }` |
| `W_LARGE_COMPOSITE` | A composite state has more direct children than the configured threshold. | `state Root { state A; state B; state C; [*] -> A; }` |
| `W_TOPOLOGICAL_NOEXIT` | A root-reachable leaf or cycle has no guard-agnostic route to the root exit sink. | `state System { state A; state B; [*] -> A; A -> B; }` |
| `W_EVENT_UNREACHABLE_EMIT` | A used event has no consumer source that is reachable in the guard-agnostic topology graph. | `state System { event Panic; state A; state LostA; state LostB; [*] -> A; LostA -> A : Panic; LostB -> A : Panic; }` |
| `W_DEAD_GUARD` | SMT proves a transition guard is unsatisfiable under model variable type and runtime-definedness constraints. | `def int x = 0; state System { state A; state B; [*] -> A; A -> B : if [x > 1 && x < 0]; }` |
| `W_GUARD_TAUTOLOGY` | SMT proves a transition guard is true for every valid variable valuation. | `def int x = 0; state System { state A; state B; [*] -> A; A -> B : if [x >= 0 || x < 0]; }` |
| `W_FORCED_GUARD_UNSAT` | A forced-transition guard cannot be satisfied under declaration initializer values. | `def int x = 0; state System { state A; state B; [*] -> A; !A -> B : if [x > 0]; }` |
| `W_EFFECT_SMT_NO_OP` | SMT proves a transition effect leaves all persistent model variables unchanged whenever the transition can run. | `def int x = 0; state System { state A; state B; [*] -> A; A -> B : if [x >= 0] effect { x = x + 0; }; }` |
| `W_TRANSITION_SHADOWED` | A later outgoing transition is fully covered by earlier same-source triggers and therefore cannot be selected. | `state System { state A; state B; state C; [*] -> A; A -> B; A -> C; }` |
| `W_COMPOSITE_INIT_INCOMPLETE` | A composite state's initial transitions do not jointly cover all variable and event inputs. | `def int x = 0; state System { state A; state B; [*] -> A : if [x > 0]; [*] -> B : if [x < 0]; }` |

#### Infos (`I_*`) — observations that may be intentional (7)

| Code | What it observes | Minimal DSL example |
|------|------------------|---------------------|
| `I_UNREFERENCED_VAR_MAYBE_ABSTRACT` | A variable cannot affect any transition guard through DSL data-flow, but at least one visible abstract action may use it externally. | `def int maybe_external = 0; def int ready = 0; state Root { state A { enter abstract ExternalHook; } state B; [*] -> A; A -> B : if [ready > 0]; }` |
| `I_TRANSITION_TO_SELF_VIA_PARENT` | A composite state transitions to itself, intentionally forcing a re-entry through child initialization. | `state Root { state Active { state Leaf; [*] -> Leaf; } [*] -> Active; Active -> Active; }` |
| `I_TRANSITION_NEVER_EVENT_TRIGGERED` | A normal transition has no event and no guard — an unconditional fall-through. | `state Root { state A; state B; [*] -> A; A -> B; }` |
| `I_NONTRIVIAL_SCC` | A non-trivial strongly connected component exists in the guard-agnostic leaf-level topology graph. | `state System { state A; state B; [*] -> A; A -> B; B -> A; }` |
| `I_TOPOLOGICAL_NON_TERMINATING` | The topology does not force all root-reachable executions to eventually reach the root terminator. | `state System { state A; [*] -> A; A -> A; A -> [*]; }` |
| `I_EFFECT_GUARD_CONTRADICT` | A transition effect makes the same transition guard false after every guarded, runtime-defined execution. | `def int x = 0; state System { state A; state B; [*] -> A; A -> B : if [x > 0] effect { x = 0; }; }` |
| `I_ENTER_DURING_CONTRADICT` | Entry-time assignments make a first-cycle `during` branch condition predetermined. | `def int x = 0; state System { state A { enter { x = 1; } during { if [x > 0] { x = x + 1; } else { x = x - 1; } } } [*] -> A; }` |

> **Configurable thresholds.** `inspect_model(machine, *, deep_hierarchy_threshold=6, large_composite_threshold=12, var_to_leaf_ratio_threshold=2.0)` accepts override knobs for the three threshold-based warnings (`W_DEEP_HIERARCHY` / `W_LARGE_COMPOSITE` / `W_HIGH_VAR_TO_LEAF_RATIO`). jsfcstm `inspectModel(model, { deepHierarchyThreshold, largeCompositeThreshold, varToLeafRatioThreshold })` mirrors the same defaults.

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
- **Installation Guide**: [Installation](https://pyfcstm.readthedocs.io/en/latest/tutorials/installation/index.html)
- **Project Structure Guide**: [Structure](https://pyfcstm.readthedocs.io/en/latest/tutorials/structure/index.html)
- **DSL Syntax Tutorial**: [DSL Reference](https://pyfcstm.readthedocs.io/en/latest/tutorials/dsl/index.html)
- **Visualization Guide**: [PlantUML Visualization](https://pyfcstm.readthedocs.io/en/latest/tutorials/visualization/index.html)
- **Simulation Guide**: [Simulation Runtime](https://pyfcstm.readthedocs.io/en/latest/tutorials/simulation/index.html)
- **Template System Guide**: [Template Tutorial](https://pyfcstm.readthedocs.io/en/latest/tutorials/render/index.html)
- **CLI Reference**: [CLI Guide](https://pyfcstm.readthedocs.io/en/latest/tutorials/cli/index.html)
- **Syntax Highlighting Guide**: [Grammar and Editor Support](https://pyfcstm.readthedocs.io/en/latest/tutorials/grammar/index.html)
- **API Documentation**: [API Reference](https://pyfcstm.readthedocs.io/en/latest/api_doc/index.html)

## Contribution & Support

pyfcstm is an open-source project under the LGPLv3 license, and contributions are welcome:

- **Report Bugs**: Submit issues on [GitHub Issues](https://github.com/hansbug/pyfcstm/issues)
- **Submit Pull Requests**: See [CONTRIBUTING.md](https://github.com/hansbug/pyfcstm/blob/main/CONTRIBUTING.md) for
  guidelines
- **Suggest Features**: Discuss feature ideas in the Issues section
- **Ask Questions**: Open an issue if you need help with the DSL, templates, or simulator

**Source Code**: [https://github.com/HansBug/pyfcstm](https://github.com/HansBug/pyfcstm)

## License

This project is licensed under
the [GNU Lesser General Public License v3 (LGPLv3)](https://github.com/hansbug/pyfcstm/blob/main/LICENSE).
