# cpp_poll template maintainer handbook

`cpp_poll` is an early-stage first-class C++ poll-style built-in template. It
emits the same C poll execution core as `templates/c_poll/` plus
`machine.cpp` / `machine.hpp` wrapper files that provide a C++98-compatible
facade over the public C poll API.

This file is maintainer-facing documentation for `templates/cpp_poll/`. It is
ignored by the renderer and is not copied to generated output. Generated-output
user guides come from `README.md.j2` / `README_zh.md.j2`.

## Source layout

| Template source | Maintainer role | Generated output |
| --- | --- | --- |
| `machine.h.j2` | File-level symlink to `../c_poll/machine.h.j2` | `machine.h` |
| `machine.c.j2` | File-level symlink to `../c_poll/machine.c.j2` | `machine.c` |
| `machine.hpp.j2` | C++ poll-wrapper header | `machine.hpp` |
| `machine.cpp.j2` | C++ poll-wrapper implementation | `machine.cpp` |
| `README.md.j2` | English generated-output guide | `README.md` |
| `README_zh.md.j2` | Chinese generated-output guide | `README_zh.md` |
| `config.yaml` | Independent renderer config with explicit C-family helper imports | Not copied |
| `template.json` | Built-in template metadata | Not copied |
| `README.md` / `README_zh.md` | Template maintainer handbooks | Not copied by the renderer, but included in packaged template archives |

## Maintenance discipline

`template.json` intentionally keeps `experimental: true` while the C++ poll
wrapper surface is still in early rollout. That flag means early first-class
template status, not an unimplemented template: packaging, wrapper API smoke
tests, shared semantic fixture alignment, and native toolchain matrix coverage
are part of the expected maintenance contract.

The C poll core symlinks are a repository-source reuse mechanism only.
Packaged `cpp_poll.zip` must contain ordinary files, not symlink entries, and
must remain self-contained when extracted without `templates/c_poll/` present.

C-family helpers are loaded from this template's `config.yaml`; do not add them
back to the global default renderer environment.

Keep `machine.cpp.j2` and `machine.hpp.j2` C++98-compatible, exception-free,
RTTI-free, and free of STL container requirements. Runtime behavior must remain
in the generated C poll core; the wrapper should call only the public C poll API
from `machine.h` and should not inspect runtime-owned struct fields directly.

Shared semantic fixture alignment for this template must exercise the
`machine.hpp` / `machine.cpp` wrapper surface. Fixture harnesses may compile
`machine.c` and include it in the final executable, but the test entrypoint must
be the C++ wrapper: harness sources should directly include only `machine.hpp`,
use `Wrapper::...` aliases for generated runtime types, and call wrapper public
methods instead of direct `...Machine_*` C functions.

Native toolchain checks should keep `cpp_poll` in the same repository-level
matrix as `c`, `c_poll`, and `cpp`. The C++ harness may link the generated C
poll core, but the public integration surface under test remains the C++ poll
wrapper. Keep generated README build examples aligned with the profiles that
the matrix actually exercises, including CMake, GCC/G++, Clang/Clang++,
no-exception, no-RTTI, and no-heap forms where applicable.

Deployment-safety wording follows the same C-family boundary as
`templates/c_poll/`. This template provides a non-certified engineering
baseline, not a certification package: C99 poll core, C++98 wrapper,
caller-owned object and no-heap integration, complete event-check installation,
shared semantic alignment, and native toolchain matrix evidence. Do not
describe generated output as MISRA, AUTOSAR, DO-178C, IEC 61508, ISO 26262, or
other certification ready. Numeric inspect warnings are default C/C++
deployment-profile diagnostics, not target-independent FCSTM model errors or
Python-template risks. Future BitVec, BMC, fixed-point, numeric-profile,
checked-arithmetic, or generated failure channel work belongs to the verify and
codegen design lines.

Generated README examples are part of the template contract. When changing the
wrapper API or compile guidance, update both generated README templates and
verify representative commands through template tests.
