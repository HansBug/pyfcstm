# pyfcstm 项目验收安装包

This package is a focused pyfcstm project-acceptance installation artifact.
The ordinary `make package` command produces its wheel and source distribution.

The packaged runtime keeps the public `pyfcstm` command, FCSTM parsing and model
assembly, PlantUML export, simulation, diagnostics/inspect support, Pygments
syntax highlighting, and code generation with these five built-in templates:

- `python`
- `c`
- `c_poll`
- `cpp`
- `cpp_poll`

The installation archives intentionally exclude development-only material such as
repository documentation sources, tests, editor projects, LLM prompt resources,
and source template directories. It is not a PyPI release announcement or a
production-support statement.
