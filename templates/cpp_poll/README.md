# cpp_poll template maintainer handbook

`cpp_poll` is the experimental C++ poll-style built-in template skeleton. It
emits the same C poll execution core as `templates/c_poll/` plus minimal
`machine.cpp` / `machine.hpp` wrapper files. The complete poll facade API is
intentionally outside this first slice.

This file is maintainer-facing documentation for `templates/cpp_poll/`. It is
ignored by the renderer and is not copied to generated output. Generated-output
user guides come from `README.md.j2` / `README_zh.md.j2`.

## Source layout

| Template source | Maintainer role | Generated output |
| --- | --- | --- |
| `machine.h.j2` | File-level symlink to `../c_poll/machine.h.j2` | `machine.h` |
| `machine.c.j2` | File-level symlink to `../c_poll/machine.c.j2` | `machine.c` |
| `machine.hpp.j2` | Minimal C++ poll-wrapper header skeleton | `machine.hpp` |
| `machine.cpp.j2` | Minimal C++ poll-wrapper implementation skeleton | `machine.cpp` |
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

Until the full poll wrapper lands, keep `machine.cpp.j2` and `machine.hpp.j2`
small, C++98-compatible, exception-free, RTTI-free, and free of STL container
requirements. Runtime behavior still comes from the generated C poll core.
