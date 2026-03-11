# AGENTS.md

This file provides guidance to coding agents working in this repository.

## Working Rule

Prefer existing project documentation over duplicating instructions here. Use repository-relative Markdown links only.
Do not introduce agent-only companion files when an existing document already covers the topic.

## Primary References

- Project overview and architecture: [CLAUDE.md](./CLAUDE.md)
- User-facing overview and quick start: [README.md](./README.md)
- Contribution workflow and development setup: [CONTRIBUTING.md](./CONTRIBUTING.md)
- Simulation design details: [SIMULATE_DESIGN.md](./SIMULATE_DESIGN.md)

## What To Read In CLAUDE.md

[CLAUDE.md](./CLAUDE.md) is the main repository-oriented context file for coding agents. It is the first document to
read when you need implementation context, command references, or architectural orientation.

It contains the following kinds of information:

- Project overview:
  explains what `pyfcstm` is, what problem it solves, and the repository's main technical scope.
- Common commands:
  lists day-to-day commands for testing, packaging, documentation, ANTLR grammar regeneration, sample generation,
  VSCode extension build, logo generation, and CLI usage.
- Architecture overview:
  describes the main code areas and how the system is organized.
- Core components:
  identifies the main packages and files, including parsing, model building, rendering, simulation, solver, CLI
  entrypoints, configuration, and utility modules.
- Key architectural patterns:
  summarizes the main design ideas such as the DSL-to-AST-to-model-to-render pipeline, the Jinja2 template system,
  hierarchical state machine support, and event scoping rules.
- DSL language reference:
  documents the DSL concepts and syntax, including variable definitions, state definitions, transitions, forced
  transitions, events, and related semantics.

## When To Enter CLAUDE.md

Open [CLAUDE.md](./CLAUDE.md) before making assumptions in any of these situations:

- You need the correct command to test, build, package, or regenerate generated artifacts.
- You need to understand where a feature is implemented.
- You need to trace a DSL concept to the parser, model, renderer, or simulator.
- You are modifying grammar, simulation behavior, rendering behavior, or CLI flow.
- You need repository-specific terminology or architecture context before editing code.

## How To Use CLAUDE.md Efficiently

Use [CLAUDE.md](./CLAUDE.md) as an index into the codebase instead of treating it as a generic policy file.

- Start at the project overview to confirm the repository purpose.
- Read the common commands section before running tests or build steps.
- Read the architecture and core component sections before changing implementation code.
- Read the DSL reference section before changing parser, model, rendering, or simulation logic tied to syntax.
- Follow the file and package pointers in `CLAUDE.md` to move into the actual source tree under [pyfcstm/](./pyfcstm/).

## Practical Entry Points

- Python package source: [pyfcstm/](./pyfcstm/)
- Tests: [test/](./test/)
- VSCode extension: [editors/vscode/README.md](./editors/vscode/README.md)

## Agent Notes

- For common commands, architecture, DSL semantics, and workflow expectations, follow [CLAUDE.md](./CLAUDE.md).
- For setup, testing, formatting, and contribution expectations, follow [CONTRIBUTING.md](./CONTRIBUTING.md).
- When linking within repository docs, keep using relative paths like `./CLAUDE.md` or `./pyfcstm/` so links remain Git-friendly and cross-platform.
- If task context is unclear, prefer reading [CLAUDE.md](./CLAUDE.md) first, then drill into the referenced source files.
