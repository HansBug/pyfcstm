import glob
import os.path
import pathlib
import shutil
import warnings
from typing import Optional, Dict

from .env import create_env
from .expr import add_expr_render_to_env
from ..model import StateMachine


def render_from_template_dir(model: StateMachine, template_dir: str, output_dir: str,
                             lang_style: str = 'dsl', ext_configs: Optional[Dict[str, str]] = None,
                             clear_previous_directory: bool = False):
    output_dir = os.path.abspath(output_dir)

    env = create_env()
    env = add_expr_render_to_env(env, lang_style=lang_style, ext_configs=ext_configs)

    os.makedirs(output_dir, exist_ok=True)
    if clear_previous_directory:
        for file in os.listdir(output_dir):
            dst_file = os.path.join(output_dir, file)
            if os.path.isfile(dst_file):
                os.remove(dst_file)
            elif os.path.isdir(dst_file):
                shutil.rmtree(dst_file)
            elif os.path.islink(dst_file):
                os.unlink(dst_file)
            else:
                warnings.warn(f'Unable to clean file {dst_file!r}.')

    for template_file in glob.glob(os.path.join(template_dir, '**', '*.j2'), recursive=True):
        rel_file = os.path.splitext(os.path.relpath(template_file, template_dir))[0]
        tp = env.from_string(pathlib.Path(template_file).read_text())
        dst_file = os.path.join(output_dir, rel_file)
        os.makedirs(os.path.dirname(dst_file), exist_ok=True)
        with open(dst_file, 'w') as f:
            f.write(tp.render(model=model))
