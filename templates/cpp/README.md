# cpp template maintainer handbook

`cpp` is the experimental C++ built-in template skeleton. It emits the same
C99 execution core as `templates/c/` plus minimal `machine.cpp` / `machine.hpp`
wrapper files. The complete C++ facade API is intentionally outside this first
slice and belongs to the follow-up wrapper work.

This file is maintainer-facing documentation for `templates/cpp/`. It is
ignored by the renderer and is not copied to generated output. Generated-output
user guides come from `README.md.j2` / `README_zh.md.j2`.

## Source layout

| Template source | Maintainer role | Generated output |
| --- | --- | --- |
| `machine.h.j2` | File-level symlink to `../c/machine.h.j2` | `machine.h` |
| `machine.c.j2` | File-level symlink to `../c/machine.c.j2` | `machine.c` |
| `machine.hpp.j2` | Minimal C++ wrapper header skeleton | `machine.hpp` |
| `machine.cpp.j2` | Minimal C++ wrapper implementation skeleton | `machine.cpp` |
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

Until the full wrapper lands, keep `machine.cpp.j2` and `machine.hpp.j2` small,
C++98-compatible, exception-free, RTTI-free, and free of STL container
requirements. Runtime behavior still comes from the generated C core.
