import os.path
import pathlib
import shutil
import warnings
from functools import partial
from typing import Optional, Dict, Callable

import pathspec
import yaml

from .env import create_env
from .expr import add_expr_render_to_env
from .func import process_item_to_object
from ..model import StateMachine


class StateMachineCodeRenderer:
    def __init__(self, template_dir: str, config_file: str = 'config.yaml'):
        self.template_dir = os.path.abspath(template_dir)
        self.config_file = os.path.join(self.template_dir, config_file)

        self.env = create_env()
        self._lang_style: Optional[str] = None
        self._lang_ext_configs: Optional[dict] = None
        self._ignore_patterns = ['.git']
        self._prepare_for_configs()
        self.env = add_expr_render_to_env(
            self.env,
            lang_style=self._lang_style,
            ext_configs=self._lang_ext_configs,
        )
        self._path_spec = pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern, self._ignore_patterns
        )

        self._file_mappings: Dict[str, Callable] = {}
        self._prepare_for_file_mapping()

    def _prepare_for_configs(self):
        with open(self.config_file, 'r') as f:
            config_info = yaml.safe_load(f)

        expr_style = config_info.pop('expr_style', 'dsl')
        if isinstance(expr_style, str):
            self._lang_style = expr_style
            self._lang_ext_configs = {}
        else:
            self._lang_style = expr_style.pop('base_lang', 'dsl')
            self._lang_ext_configs = expr_style

        globals_ = config_info.pop('globals', None) or {}
        for name, value in globals_.items():
            self.env.globals[name] = process_item_to_object(value, env=self.env)
        filters_ = config_info.pop('filters', None) or {}
        for name, value in filters_.items():
            self.env.filters[name] = process_item_to_object(value, env=self.env)
        tests = config_info.pop('tests', None) or {}
        for name, value in tests.items():
            self.env.tests[name] = process_item_to_object(value, env=self.env)

        ignores = list(config_info.pop('ignores', None) or [])
        self._ignore_patterns.extend(ignores)

    def _prepare_for_file_mapping(self):
        for root, _, files in os.walk(self.template_dir):
            for file in files:
                _, ext = os.path.splitext(file)
                current_file = os.path.abspath(os.path.join(root, file))
                rel_file = os.path.relpath(current_file, self.template_dir)
                if self._path_spec.match_file(rel_file):
                    continue
                if ext == '.j2':
                    rel_file = os.path.splitext(rel_file)[0]
                    self._file_mappings[rel_file] = partial(
                        self.render_one_file,
                        template_file=current_file,
                    )
                elif not os.path.samefile(current_file, self.config_file):
                    self._file_mappings[rel_file] = partial(
                        self.copy_one_file,
                        src_file=current_file,
                    )

    def render_one_file(self, model: StateMachine, output_file: str, template_file: str):
        tp = self.env.from_string(pathlib.Path(template_file).read_text())
        if os.path.dirname(output_file):
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(tp.render(model=model))

    def copy_one_file(self, model: StateMachine, output_file: str, src_file: str):
        _ = model
        if os.path.dirname(output_file):
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        shutil.copyfile(src_file, output_file)

    def render(self, model: StateMachine, output_dir: str, clear_previous_directory: bool = False):
        output_dir = os.path.abspath(output_dir)
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

        for rel_file, fn_op in self._file_mappings.items():
            dst_file = os.path.join(output_dir, rel_file)
            fn_op(model=model, output_file=dst_file)
