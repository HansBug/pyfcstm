# Built-in Templates

This directory contains the source templates maintained by the `pyfcstm` repository.

Rules:

- Each first-level subdirectory is one built-in template source.
- Each template directory should contain its own `README.md`.
- Packaged built-in templates are emitted into `pyfcstm/template/` as zip assets.

Current template sources:

- `c`: native C99 scaffold template for the built-in template pipeline
- `c_poll`: native C99/C++98 scaffold template with hook-polled events
- `python`: native Python scaffold template for the built-in template pipeline
