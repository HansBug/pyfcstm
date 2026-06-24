# cpp template maintainer handbook

`cpp` is the experimental C++ built-in template. It emits the same C99
execution core as `templates/c/` plus `machine.cpp` / `machine.hpp` wrapper
files that provide a C++98-compatible facade over the public C API.

This file is maintainer-facing documentation for `templates/cpp/`. It is
ignored by the renderer and is not copied to generated output. Generated-output
user guides come from `README.md.j2` / `README_zh.md.j2`.

## Source layout

| Template source | Maintainer role | Generated output |
| --- | --- | --- |
| `machine.h.j2` | File-level symlink to `../c/machine.h.j2` | `machine.h` |
| `machine.c.j2` | File-level symlink to `../c/machine.c.j2` | `machine.c` |
| `machine.hpp.j2` | C++ wrapper header | `machine.hpp` |
| `machine.cpp.j2` | C++ wrapper implementation | `machine.cpp` |
| `README.md.j2` | English generated-output guide | `README.md` |
| `README_zh.md.j2` | Chinese generated-output guide | `README_zh.md` |
| `config.yaml` | Independent renderer config with explicit C-family helper imports | Not copied |
| `template.json` | Built-in template metadata | Not copied |
| `README.md` / `README_zh.md` | Template maintainer handbooks | Not copied by the renderer, but included in packaged template archives |

## Maintenance discipline

The C core symlinks are a repository-source reuse mechanism only. Packaged
`cpp.zip` must contain ordinary files, not symlink entries, and must remain
self-contained when extracted without `templates/c/` present.

C-family helpers such as `to_c_identifier`, `to_c_path_identifier`, and
`render_c_action_body` are loaded from this template's `config.yaml`. Do not add
these helpers back to the global default renderer environment.

Keep `machine.cpp.j2` and `machine.hpp.j2` C++98-compatible, exception-free,
RTTI-free, and free of STL container requirements. Runtime behavior must remain
in the generated C core; the wrapper should call only the public C API from
`machine.h` and should not inspect runtime-owned struct fields directly.

Shared semantic fixture alignment for this template must exercise the
`machine.hpp` / `machine.cpp` wrapper surface. Fixture harnesses may compile
`machine.c` and include it in the final executable, but the test entrypoint must
be the C++ wrapper: harness sources should directly include only `machine.hpp`,
use `Wrapper::...` aliases for generated runtime types, and call wrapper public
methods instead of direct `...Machine_*` C functions.

Generated README examples are part of the template contract. When changing the
wrapper API or compile guidance, update both generated README templates and
verify representative commands through template tests.
