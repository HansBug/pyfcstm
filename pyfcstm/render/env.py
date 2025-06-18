import jinja2

from ..dsl import INIT_STATE, EXIT_STATE
from ..utils import add_settings_for_env


def create_env():
    env = jinja2.Environment()
    env = add_settings_for_env(env)
    env.globals['INIT_STATE'] = INIT_STATE
    env.globals['EXIT_STATE'] = EXIT_STATE
    return env
