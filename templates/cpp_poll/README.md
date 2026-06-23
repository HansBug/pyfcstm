# cpp_poll template maintainer handbook

`cpp_poll` is the experimental C++ poll-style built-in template. It emits the
same C poll execution core as `templates/c_poll/` plus `machine.cpp` /
`machine.hpp` wrapper files that provide a C++98-compatible facade over the
public C poll API.

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

The C poll core symlinks are a repository-source reuse mechanism only.
Packaged `cpp_poll.zip` must contain ordinary files, not symlink entries, and
must remain self-contained when extracted without `templates/c_poll/` present.

C-family helpers are loaded from this template's `config.yaml`; do not add them
back to the global default renderer environment.

Keep `machine.cpp.j2` and `machine.hpp.j2` C++98-compatible, exception-free,
RTTI-free, and free of STL container requirements. Runtime behavior must remain
in the generated C poll core; the wrapper should call only the public C poll API
from `machine.h` and should not inspect runtime-owned struct fields directly.

Generated README examples are part of the template contract. When changing the
wrapper API or compile guidance, update both generated README templates and
verify representative commands through template tests.
