from .dispatch import pyfcstmcli
from .generate import _add_generate_subcommand

_DECORATORS = [
    _add_generate_subcommand,
]

cli = pyfcstmcli
for deco in _DECORATORS:
    cli = deco(cli)
