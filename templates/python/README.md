# python template maintainer handbook

`python` is the built-in template that emits a native Python state-machine
runtime for one FCSTM model. This file is the maintainer-facing handbook for the
template source under `templates/python/`; it is not copied to generated output.
The generated user guide is produced from `README.md.j2` / `README_zh.md.j2`.

## Target and non-targets

Use this template when the desired output is an importable, dependency-free
Python runtime that can be embedded into applications, tests, examples, or
small automation scripts.

This template is not the simulator implementation and should not depend on the
`pyfcstm` runtime package after generation. It should also avoid becoming a
large framework around generated code: downstream users should change the FCSTM
DSL and regenerate instead of maintaining hand-edited generated runtime logic.

## Source layout and generated output

| Template source | Maintainer role | Generated output |
| --- | --- | --- |
| `machine.py.j2` | Runtime source template | `machine.py` |
| `README.md.j2` | English generated-output guide | `README.md` |
| `README_zh.md.j2` | Chinese generated-output guide | `README_zh.md` |
| `config.yaml` | Renderer configuration, Python statement rendering, Jinja helpers, and ignore rules | Not copied |
| `template.json` | Built-in template metadata | Not copied |
| `README.md` / `README_zh.md` | Template maintainer handbooks | Not copied by the renderer, but included in packaged template archives |

`config.yaml` ignores `README.md`, `README_zh.md`, and `template.json` so they
do not leak into generated output. `make tpl` still packages the complete
template source directory, so changes to these maintainer README files must be validated with a
refreshed local `pyfcstm/template/python.zip`. The archive is ignored by git in
normal checkouts; setup and packaging commands recreate it from source.

## Compatibility and runtime dependency boundary

Generated `machine.py` should keep these defaults:

- Python 3.7 or newer.
- Python standard library only.
- No import from `pyfcstm` or repository test helpers.
- No third-party runtime dependency.
- No syntax that unnecessarily raises the minimum supported Python version.

Generation-time dependencies such as Jinja2, YAML parsing, renderer filters, and
statement renderers belong to `pyfcstm` and must not become generated-runtime
requirements.

## Public integration surface

Generated users primarily interact with one machine class whose name is derived
from the root state. The stable integration surface should remain concentrated
around:

- constructing the generated machine class;
- calling `cycle(...)` with event names or event collections supported by the
generated API;
- reading the current state and persistent variable snapshot;
- using hot start with an explicit state and complete variable snapshot;
- subclassing the generated class to implement abstract lifecycle hooks.

Abstract lifecycle actions should stay discoverable through stable protected
hook method names. Hook names must map clearly back to DSL abstract action names
so a DSL author can find the right override with IDE completion.

## Semantics and alignment expectations

The generated Python runtime is a product artifact, not a thin wrapper around
`pyfcstm.simulate.SimulationRuntime`. Its visible behavior must still align with
the simulator for supported FCSTM semantics:

- cold start and hot start;
- initial transitions and composite entry ordering;
- lifecycle action order, including aspect actions;
- event scoping and transition priority;
- guard, effect, rollback, and validation behavior;
- abstract hook invocation timing and context values.

Semantic alignment tests are maintained outside this README. A documentation-only
change to this file should not modify those tests, but runtime template changes
must use them as a correctness gate.

## Generated implementation strategy

Generated `machine.py` may favor direct, generated control flow over manual
readability when that improves predictable runtime behavior. Keep the public
class API and generated README clear; the implementation body can be more
mechanical as long as it stays deterministic, self-contained, and formatter-
stable.

Formatter and linter checks are quality gates for professionalism and
integration hygiene. They should not drive runtime design in a way that weakens
FCSTM semantics or performance.

## Maintenance workflow

Use the smallest verification set that matches the change:

1. For maintainer README-only edits, review the English and Chinese files for
   section parity and factual consistency.
2. Run `make rst_auto` before committing repository changes. This README should
   not normally produce generated RST changes.
3. Run `make tpl` after changing any file under `templates/python/`, including
   this README, because packaged built-in template archives include the template
   source directory.
4. Inspect packaged asset changes. A README-only change should refresh the local generated
   `pyfcstm/template/python.zip` archive; because zip archives are ignored by
   git in normal checkouts, the tracked `pyfcstm/template/index.json` should
   normally stay content-equivalent.
5. For runtime template changes, generate representative outputs and run Python
   template tests and simulator-alignment tests.

Useful commands:

```bash
make rst_auto
make tpl
pytest test/template/python -v
SKIP_SLOW_TESTS=1 make unittest
```

## Language-specific verification

Representative generated `machine.py` files should satisfy:

```bash
ruff check path/to/generated/machine.py
ruff format --check path/to/generated/machine.py
```

The generated code should be lint-clean and formatter-stable without asking
users to edit generated files. If a rare generated construct needs an exception,
keep it narrow, documented in the template, and justified by runtime semantics
or compatibility.

## Documentation layering

Keep the three documentation layers separate:

- this file explains how to maintain the `python` template;
- `README.md.j2` / `README_zh.md.j2` explain how to use one generated output
  directory;
- root `templates/README.md` / `README_zh.md` explain repository-wide template
  system rules.

Do not move packaging internals into generated READMEs. A downstream user or LLM
that only sees generated output should learn how to instantiate and run the
machine, not how the repository packages templates.
