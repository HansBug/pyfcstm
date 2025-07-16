"""
State Machine Code Renderer Module

This module provides functionality for rendering state machine models into code using templates.
It uses Jinja2 templating engine to transform state machine models into various programming
languages and formats based on template configurations.

Template Directory Structure:
    The template directory should contain:

    - ``config.yaml``: Configuration file for the renderer
    - ``*.j2`` files: Jinja2 templates that will be rendered
    - Other files: Will be copied directly to the output directory

Configuration File (config.yaml) Structure:
    - ``expr_styles``: Dictionary defining expression rendering styles
      - ``default``: Default style configuration (will use 'dsl' as base_lang if not specified)

      - ``[style_name]``: Additional named styles
        - base_lang: Base language style ('dsl', 'c', 'cpp', 'python')
        - [additional options]: Extra rendering options for the style
    - ``globals``: Dictionary of global variables to be added to the Jinja2 environment
      Each entry can be:

      - ``type: template``: A template renderer function
        - params: List[str], means the parameter list of this template rendering function, e.g. ``['a', 'b']``.
        - template: str, means the Jinja2-format text render template, e.g. ``{{ a + b * 2 }}``.
      - ``type: import``: An imported object
        - from: str, means the import position, e.g. `math.sin`.
      - ``type: value``: A direct value
        - value: Any, means any possible value, e.g. ``1``, ``'Hello World'``.
      - Other values (e.g. ``1``, ``'Hello World'``) means directly this value itself.

    - ``filters``: Dictionary of filter functions to be added to the Jinja2 environment
      (Same format as globals)

    - ``tests``: Dictionary of test functions to be added to the Jinja2 environment
      (Same format as globals)

    - ``ignores``: List of file patterns to ignore (using gitignore syntax, e.g. ``.git``, ``*.md``, etc)

Expression Rendering:
    The expr_styles configuration allows customizing how expressions are rendered in different
    language styles. The base_lang determines the starting template set, which can be extended
    or overridden with additional configuration.

    And you can use these pre-defined styles in ``expr_render`` function/filter in the template.
    When use ``{{ expression | expr_render }}`` it will use ``default`` style to render your expression.
    When use ``{{ expression | expr_render(style='c') }}`` it will use ``c`` style to render your expression.

"""
import copy
import os.path
import pathlib
import shutil
import warnings
from functools import partial
from typing import Dict, Callable, Union, Any

import pathspec
import yaml

from .env import create_env
from .expr import create_expr_render_template, fn_expr_render, _KNOWN_STYLES
from .func import process_item_to_object
from ..dsl import node as dsl_nodes
from ..model import StateMachine
from ..utils import auto_decode


class StateMachineCodeRenderer:
    """
    Renderer for generating code from state machine models using templates.

    This class handles the rendering of state machine models into code using
    Jinja2 templates. It supports custom expression styles, global functions,
    filters, and tests through a configuration file.

    :param template_dir: Directory containing the templates and configuration
    :type template_dir: str

    :param config_file: Name of the configuration file within the template directory
    :type config_file: str, default: 'config.yaml'
    """

    def __init__(self, template_dir: str, config_file: str = 'config.yaml'):
        """
        Initialize the StateMachineCodeRenderer.

        :param template_dir: Directory containing the templates and configuration
        :type template_dir: str

        :param config_file: Name of the configuration file within the template directory
        :type config_file: str, default: 'config.yaml'
        """
        self.template_dir = os.path.abspath(template_dir)
        self.config_file = os.path.join(self.template_dir, config_file)

        self.env = create_env()
        self._ignore_patterns = ['.git']
        self._prepare_for_configs()

        self._path_spec = pathspec.PathSpec.from_lines(
            pathspec.patterns.GitWildMatchPattern, self._ignore_patterns
        )

        self._file_mappings: Dict[str, Callable] = {}
        self._prepare_for_file_mapping()

    def _prepare_for_configs(self):
        """
        Load and process the configuration file.

        This method reads the configuration file, sets up expression rendering styles,
        and registers globals, filters, and tests in the Jinja2 environment.

        :raises FileNotFoundError: If the configuration file does not exist
        :raises yaml.YAMLError: If the configuration file contains invalid YAML
        """
        with open(self.config_file, 'r') as f:
            config_info = yaml.safe_load(f)

        expr_styles = config_info.pop('expr_styles', None) or {}
        expr_styles['default'] = expr_styles.get('default') or {'base_lang': 'dsl'}
        d_templates = copy.deepcopy(_KNOWN_STYLES)
        for style_name, expr_style in expr_styles.items():
            lang_style = expr_style.pop('base_lang')
            d_templates[style_name] = create_expr_render_template(
                lang_style=lang_style,
                ext_configs=expr_style,
            )

        def _fn_expr_render(node: Union[float, int, dict, dsl_nodes.Expr, Any], style: str = 'default'):
            """
            Render an expression node using the specified style.

            :param node: The expression node to render
            :type node: Union[float, int, dict, dsl_nodes.Expr, Any]

            :param style: The expression rendering style to use
            :type style: str, default: 'default'

            :return: The rendered expression as a string
            :rtype: str
            """
            return fn_expr_render(
                node=node,
                templates=d_templates[style],
                env=self.env,
            )

        self.env.globals['expr_render'] = _fn_expr_render
        self.env.filters['expr_render'] = _fn_expr_render

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
        """
        Prepare file mappings for rendering or copying.

        This method walks through the template directory and creates mappings for:
        - .j2 files: Will be rendered using Jinja2
        - Other files: Will be copied directly to the output directory

        Files matching the ignore patterns will be excluded.
        """
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
        """
        Render a single template file.

        :param model: The state machine model to render
        :type model: StateMachine

        :param output_file: Path to the output file
        :type output_file: str

        :param template_file: Path to the template file
        :type template_file: str

        :raises jinja2.exceptions.TemplateError: If there's an error in the template
        :raises IOError: If there's an error reading or writing files
        """
        tp = self.env.from_string(auto_decode(pathlib.Path(template_file).read_bytes()))
        if os.path.dirname(output_file):
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w') as f:
            f.write(tp.render(model=model))

    def copy_one_file(self, model: StateMachine, output_file: str, src_file: str):
        """
        Copy a single file to the output directory.

        :param model: The state machine model (unused in this method)
        :type model: StateMachine

        :param output_file: Path to the output file
        :type output_file: str

        :param src_file: Path to the source file
        :type src_file: str

        :raises IOError: If there's an error copying the file
        """
        _ = model
        if os.path.dirname(output_file):
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        shutil.copyfile(src_file, output_file)

    def render(self, model: StateMachine, output_dir: str, clear_previous_directory: bool = False):
        """
        Render the state machine model to the output directory.

        This method processes all template files and copies all other files
        from the template directory to the output directory according to the
        configured mappings.

        :param model: The state machine model to render
        :type model: StateMachine

        :param output_dir: Directory where the rendered files will be placed
        :type output_dir: str

        :param clear_previous_directory: Whether to clear the output directory before rendering
        :type clear_previous_directory: bool, default: False

        :raises IOError: If there's an error accessing or writing to the output directory

        Example::

            >>> renderer = StateMachineCodeRenderer('./templates')
            >>> renderer.render(my_state_machine, './output', clear_previous_directory=True)
        """
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
                    warnings.warn(f'Unable to clean file {dst_file!r}.')  # pragma: no cover

        for rel_file, fn_op in self._file_mappings.items():
            dst_file = os.path.join(output_dir, rel_file)
            fn_op(model=model, output_file=dst_file)
