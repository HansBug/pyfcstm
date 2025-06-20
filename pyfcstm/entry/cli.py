from .dispatch import pyfcstmcli
from .generate import _add_generate_subcommand
from .plantuml import _add_plantuml_subcommand

_DECORATORS = [
    _add_generate_subcommand,
    _add_plantuml_subcommand,
]

cli = pyfcstmcli
for deco in _DECORATORS:
    cli = deco(cli)
