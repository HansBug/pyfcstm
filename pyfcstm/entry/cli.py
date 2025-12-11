from .convert_sysdesim import _add_convert_sysdesim_subcommand
from .dispatch import pyfcstmcli
from .generate import _add_generate_subcommand
from .plantuml import _add_plantuml_subcommand
from .reachability import _add_reachability_subcommand
from .simulate import _add_simulate_command

_DECORATORS = [
    _add_generate_subcommand,
    _add_plantuml_subcommand,
    _add_convert_sysdesim_subcommand,
    _add_reachability_subcommand,
    _add_simulate_command,
]

cli = pyfcstmcli
for deco in _DECORATORS:
    cli = deco(cli)
