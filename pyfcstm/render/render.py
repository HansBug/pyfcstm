"""
State machine code renderer for Jinja2 template-based code generation.

This module provides the :class:`StateMachineCodeRenderer` class, which renders
state machine models into code files using a template directory. The renderer
supports configuration-driven expression styles, Jinja2 globals, filters, and
tests. Template files with the ``.j2`` extension are rendered, while all other
files are copied directly to the output directory.

The template directory is expected to contain:

* ``config.yaml`` - Configuration file for the renderer (see below)
* ``*.j2`` files - Jinja2 templates to render
* Other files - Copied verbatim to the output directory

Configuration file (``config.yaml``) structure:

* ``expr_styles`` - Mapping of expression rendering styles. Each style is a
  mapping with a ``base_lang`` key and optional template overrides.
  The ``default`` style is always created if absent.
* ``stmt_styles`` - Mapping of statement rendering styles. Each style is a
  mapping with a ``base_lang`` key and optional overrides such as
  ``declare_temp`` and ``temp_type_aliases`` for static-language backends.
* ``globals`` - Mapping of Jinja2 globals (see :func:`pyfcstm.render.func.process_item_to_object`)
* ``filters`` - Mapping of Jinja2 filters (same structure as ``globals``)
* ``tests`` - Mapping of Jinja2 tests (same structure as ``globals``)
* ``ignores`` - Git-style ignore patterns to skip files in the template directory

Expression rendering:

* Use ``{{ expression | expr_render }}`` to render with the ``default`` style
* Use ``{{ expression | expr_render(style='c') }}`` to render with a named style

The module depends on :mod:`jinja2`, :mod:`pyyaml`, and :mod:`pathspec` for
templating, YAML configuration, and ignore pattern handling.

Example::

    >>> from pyfcstm.render.render import StateMachineCodeRenderer
    >>> from pyfcstm.model import StateMachine
    >>> renderer = StateMachineCodeRenderer('./templates')
    >>> renderer.render(StateMachine(defines={}, root_state=some_state), './output')

"""
import copy
import os.path
import pathlib
import re
import shutil
import warnings
from functools import partial
from typing import Dict, Callable, Union, Any

import pathspec
import yaml

from .env import create_env
from .expr import create_expr_render_template, fn_expr_render, _KNOWN_STYLES, _normalize_lang_style
from .statement import (
    create_stmt_render_template, fn_stmt_render, fn_stmts_render,
    _KNOWN_STMT_STYLES, _normalize_stmt_style,
)
from .func import process_item_to_object
from ..dsl import node as dsl_nodes
from ..model import StateMachine
from ..utils import auto_decode


class StateMachineCodeRenderer:
    """
    Renderer for generating code from state machine models using templates.

    This class handles rendering of state machine models into code by combining
    a template directory with a configuration file. It creates a Jinja2
    environment, registers expression rendering styles, and maps template files
    to rendering operations or file copying operations.

    :param template_dir: Directory containing the templates and configuration
    :type template_dir: str
    :param config_file: Name of the configuration file within the template directory,
        defaults to ``'config.yaml'``
    :type config_file: str, optional

    :ivar template_dir: Absolute path to the template directory
    :vartype template_dir: str
    :ivar config_file: Absolute path to the configuration file
    :vartype config_file: str
    :ivar env: Jinja2 environment used for rendering
    :vartype env: jinja2.Environment
    :ivar _ignore_patterns: List of git-style ignore patterns
    :vartype _ignore_patterns: List[str]
    :ivar _file_mappings: Mapping of relative template paths to render/copy callables
    :vartype _file_mappings: Dict[str, Callable]

    Example::

        >>> renderer = StateMachineCodeRenderer('./templates')
        >>> renderer.render(my_state_machine, './output', clear_previous_directory=True)
    """

    def __init__(self, template_dir: str, config_file: str = 'config.yaml') -> None:
        """
        Initialize the StateMachineCodeRenderer.

        :param template_dir: Directory containing the templates and configuration
        :type template_dir: str
        :param config_file: Name of the configuration file within the template directory,
            defaults to ``'config.yaml'``
        :type config_file: str, optional
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

    def _prepare_for_configs(self) -> None:
        """
        Load and process the configuration file.

        This method reads the configuration file, sets up expression and
        statement rendering styles, and registers globals, filters, and tests
        in the Jinja2 environment.

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

        def _fn_expr_render(node: Union[float, int, dict, dsl_nodes.Expr, Any],
                            style: str = 'default') -> str:
            """
            Render an expression node using the specified style.

            :param node: The expression node to render
            :type node: Union[float, int, dict, dsl_nodes.Expr, Any]
            :param style: The expression rendering style to use, defaults to ``'default'``
            :type style: str, optional
            :return: The rendered expression as a string
            :rtype: str
            """
            style = _normalize_lang_style(style)
            return fn_expr_render(
                node=node,
                templates=d_templates[style],
                env=self.env,
            )

        self.env.globals['expr_render'] = _fn_expr_render
        self.env.filters['expr_render'] = _fn_expr_render

        stmt_styles = config_info.pop('stmt_styles', None) or {}
        stmt_styles['default'] = stmt_styles.get('default') or {'base_lang': 'dsl'}
        d_stmt_templates = {
            style_name: create_stmt_render_template(style_name)
            for style_name in _KNOWN_STMT_STYLES.keys()
        }
        for style_name, stmt_style in stmt_styles.items():
            stmt_style = copy.deepcopy(stmt_style)
            lang_style = stmt_style.pop('base_lang')
            d_stmt_templates[style_name] = create_stmt_render_template(
                lang_style=lang_style,
                ext_configs=stmt_style,
            )

        def _fn_stmt_render(node, style: str = 'default', state_vars=None, var_types=None,
                            visible_names=None, visible_var_types=None,
                            indent: str = '    ', level: int = 0) -> str:
            style = _normalize_stmt_style(style)
            return fn_stmt_render(
                node=node,
                templates=d_stmt_templates[style],
                env=self.env,
                state_vars=self.env.globals.get('_stmt_default_state_vars') if state_vars is None else state_vars,
                var_types=self.env.globals.get('_stmt_default_var_types') if var_types is None else var_types,
                visible_names=visible_names,
                visible_var_types=visible_var_types,
                indent=indent,
                level=level,
            )

        def _fn_stmts_render(nodes, style: str = 'default', state_vars=None, var_types=None,
                             visible_names=None, visible_var_types=None,
                             indent: str = '    ', level: int = 0, sep: str = '\n') -> str:
            style = _normalize_stmt_style(style)
            return fn_stmts_render(
                nodes=nodes,
                templates=d_stmt_templates[style],
                env=self.env,
                state_vars=self.env.globals.get('_stmt_default_state_vars') if state_vars is None else state_vars,
                var_types=self.env.globals.get('_stmt_default_var_types') if var_types is None else var_types,
                visible_names=visible_names,
                visible_var_types=visible_var_types,
                indent=indent,
                level=level,
                sep=sep,
            )

        self.env.globals['stmt_render'] = _fn_stmt_render
        self.env.filters['stmt_render'] = _fn_stmt_render
        self.env.globals['stmts_render'] = _fn_stmts_render
        self.env.filters['stmts_render'] = _fn_stmts_render

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

    def _prepare_for_file_mapping(self) -> None:
        """
        Prepare file mappings for rendering or copying.

        This method walks through the template directory and creates mappings for:

        * ``.j2`` files: Rendered using Jinja2 and written without the ``.j2`` extension
        * Other files: Copied directly to the output directory

        Files matching the configured ignore patterns are excluded.
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

    def render_one_file(self, model: StateMachine, output_file: str, template_file: str) -> None:
        """
        Render a single template file.

        :param model: The state machine model to render
        :type model: StateMachine
        :param output_file: Path to the output file
        :type output_file: str
        :param template_file: Path to the template file
        :type template_file: str
        :raises jinja2.exceptions.TemplateError: If there is an error in the template
        :raises IOError: If there is an error reading or writing files
        """
        previous_state_vars = self.env.globals.get('_stmt_default_state_vars')
        previous_var_types = self.env.globals.get('_stmt_default_var_types')
        self.env.globals['_stmt_default_state_vars'] = tuple(model.defines.keys())
        self.env.globals['_stmt_default_var_types'] = {
            name: define.type for name, define in model.defines.items()
        }
        tp = self.env.from_string(auto_decode(pathlib.Path(template_file).read_bytes()))
        if os.path.dirname(output_file):
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        try:
            rendered = tp.render(model=model)
            if os.path.basename(template_file) == 'machine.py.j2':
                rendered = re.sub(r'([\(\[\{]\n)\n+', r'\1', rendered)
                rendered = re.sub(r'\n{3,}', '\n\n', rendered)
                rendered = re.sub(r',\n\n([ \t]*["\]\}])', r',\n\1', rendered)
                rendered = re.sub(r'\n\n(?=(?:class|def|@))', '\n\n\n', rendered)
                rendered = re.sub(
                    r'\n([ \t]*)\n(?=[ \t]*[\]\)\}](?:,)?\n)',
                    r'\n\1',
                    rendered,
                )
                rendered = re.sub(r'\n+\Z', '\n', rendered)
            with open(output_file, 'w', encoding='utf-8', newline='\n') as f:
                f.write(rendered)
        finally:
            if previous_state_vars is None:
                self.env.globals.pop('_stmt_default_state_vars', None)
            else:
                self.env.globals['_stmt_default_state_vars'] = previous_state_vars
            if previous_var_types is None:
                self.env.globals.pop('_stmt_default_var_types', None)
            else:
                self.env.globals['_stmt_default_var_types'] = previous_var_types

    def copy_one_file(self, model: StateMachine, output_file: str, src_file: str) -> None:
        """
        Copy a single file to the output directory.

        :param model: The state machine model (unused in this method)
        :type model: StateMachine
        :param output_file: Path to the output file
        :type output_file: str
        :param src_file: Path to the source file
        :type src_file: str
        :raises IOError: If there is an error copying the file
        """
        _ = model
        if os.path.dirname(output_file):
            os.makedirs(os.path.dirname(self.config_file), exist_ok=True)
        shutil.copyfile(src_file, output_file)

    def render(self, model: StateMachine, output_dir: str, clear_previous_directory: bool = False) -> None:
        """
        Render the state machine model to the output directory.

        This method processes all template files and copies all other files
        from the template directory to the output directory according to the
        configured mappings.

        :param model: The state machine model to render
        :type model: StateMachine
        :param output_dir: Directory where the rendered files will be placed
        :type output_dir: str
        :param clear_previous_directory: Whether to clear the output directory before rendering,
            defaults to ``False``
        :type clear_previous_directory: bool, optional
        :raises IOError: If there is an error accessing or writing to the output directory

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
