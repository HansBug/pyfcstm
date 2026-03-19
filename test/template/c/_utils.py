import ctypes
import os
import shutil
import subprocess
import sys
import textwrap
from contextlib import contextmanager
from tempfile import TemporaryDirectory

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.template import extract_template
from pyfcstm.utils import to_identifier


def _find_c_compiler():
    return shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')


def _find_cmake():
    return shutil.which('cmake')


def _machine_macro_name(model):
    return '{name}_MACHINE'.format(name=to_identifier(model.root_state.name).upper())


def write_test_build_files(output_dir, model):
    macro_name = _machine_macro_name(model)
    makefile = os.path.join(output_dir, 'Makefile')
    cmakelists = os.path.join(output_dir, 'CMakeLists.txt')

    with open(makefile, 'w', encoding='utf-8') as f:
        f.write(
            'CC ?= cc\n'
            'AR ?= ar\n'
            'RANLIB ?= ranlib\n'
            'CFLAGS ?= -O2\n'
            'CPPFLAGS ?=\n'
            'WARN_CFLAGS ?= -Wall -Wextra -pedantic\n'
            'STD_CFLAGS ?= -std=c99\n'
            'PIC_CFLAGS ?= -fPIC\n'
            'LIBS ?= -lm\n'
            '\n'
            'UNAME_S := $(shell uname -s 2>/dev/null || echo Unknown)\n'
            'SHARED_NAME = libmachine.so\n'
            'SHARED_LDFLAGS = -shared\n'
            '\n'
            'ifeq ($(UNAME_S),Darwin)\n'
            'SHARED_NAME = libmachine.dylib\n'
            'SHARED_LDFLAGS = -dynamiclib\n'
            'endif\n'
            '\n'
            'all: libmachine.a $(SHARED_NAME)\n'
            '\n'
            'machine.o: machine.c machine.h\n'
            '\t$(CC) $(CPPFLAGS) $(CFLAGS) $(WARN_CFLAGS) $(STD_CFLAGS) $(PIC_CFLAGS) -c machine.c -o $@\n'
            '\n'
            'libmachine.a: machine.o\n'
            '\t$(AR) rcs $@ machine.o\n'
            '\t$(RANLIB) $@\n'
            '\n'
            '$(SHARED_NAME): machine.o\n'
            '\t$(CC) $(CFLAGS) $(SHARED_LDFLAGS) -o $@ machine.o $(LIBS)\n'
            '\n'
            'clean:\n'
            '\t$(RM) machine.o libmachine.a libmachine.so libmachine.dylib libmachine.dll\n'
            '\n'
            '.PHONY: all clean\n'
        )

    with open(cmakelists, 'w', encoding='utf-8') as f:
        f.write(
            'cmake_minimum_required(VERSION 2.8)\n'
            'project({name} C)\n'
            '\n'
            'include_directories(${{CMAKE_CURRENT_SOURCE_DIR}})\n'
            '\n'
            'if(MSVC)\n'
            '    set(CMAKE_C_FLAGS "${{CMAKE_C_FLAGS}} /TC")\n'
            'else()\n'
            '    set(CMAKE_C_FLAGS "${{CMAKE_C_FLAGS}} -std=c99")\n'
            'endif()\n'
            '\n'
            'add_library(machine_static STATIC machine.c)\n'
            'set_target_properties(machine_static PROPERTIES OUTPUT_NAME machine)\n'
            '\n'
            'add_library(machine_shared SHARED machine.c)\n'
            'set_target_properties(\n'
            '    machine_shared\n'
            '    PROPERTIES\n'
            '    OUTPUT_NAME machine\n'
            '    COMPILE_DEFINITIONS {macro}_BUILD_SHARED=1\n'
            ')\n'
            '\n'
            'if(NOT WIN32)\n'
            '    target_link_libraries(machine_static m)\n'
            '    target_link_libraries(machine_shared m)\n'
            'endif()\n'.format(
                name=to_identifier(model.root_state.name) + 'Machine',
                macro=macro_name,
            )
        )

    return {
        'makefile': makefile,
        'cmakelists': cmakelists,
    }


def _find_built_shared_library(build_dir):
    search_dirs = [
        build_dir,
        os.path.join(build_dir, 'Release'),
        os.path.join(build_dir, 'RelWithDebInfo'),
        os.path.join(build_dir, 'Debug'),
        os.path.join(build_dir, 'MinSizeRel'),
    ]
    candidate_names = [
        'machine.dll',
        'libmachine.so',
        'libmachine.dylib',
        'machine.so',
        'machine.dylib',
    ]

    for directory in search_dirs:
        if not os.path.isdir(directory):
            continue
        for filename in candidate_names:
            path = os.path.join(directory, filename)
            if os.path.isfile(path):
                return path

    for root, _, files in os.walk(build_dir):
        for filename in files:
            if filename.lower() in {
                'machine.dll',
                'libmachine.so',
                'libmachine.dylib',
                'machine.so',
                'machine.dylib',
            }:
                return os.path.join(root, filename)

    raise FileNotFoundError(
        'Cannot find built shared library under {!r}.'.format(build_dir)
    )


def build_shared_library(output_dir, model):
    build_files = write_test_build_files(output_dir, model)
    cmake_executable = _find_cmake()
    if cmake_executable is None:
        if os.name == 'nt':
            pytest.skip('cmake is required to build the C runtime on Windows test environments')

        compiler = _find_c_compiler()
        if compiler is None:
            pytest.skip('Neither cmake nor a direct C compiler is available in this test environment')

        shared_name = 'libmachine.dylib' if sys.platform == 'darwin' else 'libmachine.so'
        if sys.platform == 'darwin':
            build_cmd = [compiler, '-std=c99', '-dynamiclib', 'machine.c', '-lm', '-o', shared_name]
        else:
            build_cmd = [compiler, '-std=c99', '-shared', '-fPIC', 'machine.c', '-lm', '-o', shared_name]

        subprocess.run(
            build_cmd,
            cwd=output_dir,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return {
            'build_files': build_files,
            'build_dir': output_dir,
            'shared_lib': os.path.join(output_dir, shared_name),
            'cmake': None,
            'compiler': compiler,
        }

    build_dir = os.path.join(output_dir, 'cmake-runtime-build')
    os.makedirs(build_dir, exist_ok=True)

    subprocess.run(
        [cmake_executable, os.path.abspath(output_dir)],
        cwd=build_dir,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    subprocess.run(
        [cmake_executable, '--build', '.', '--config', 'Release'],
        cwd=build_dir,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    return {
        'build_files': build_files,
        'build_dir': build_dir,
        'shared_lib': _find_built_shared_library(build_dir),
        'cmake': cmake_executable,
        'compiler': _find_c_compiler(),
    }


class _ExecutionContextView:
    def __init__(self, runtime, machine_ptr, ctx_struct):
        self._runtime = runtime
        self._machine_ptr = machine_ptr
        self.action_name = ctx_struct.action_name.decode('utf-8')
        self.action_stage = ctx_struct.action_stage.decode('utf-8')
        self.state_path = ctx_struct.state_path.decode('utf-8')

    def get_var(self, name):
        return self._runtime._get_var_from_ptr(self._machine_ptr, name)

    def has_var(self, name):
        return name in self._runtime._var_types

    def get_state_name(self):
        return self.state_path.split('.')[-1] if self.state_path else ''

    def get_full_state_path(self):
        return self.state_path


class _CRuntime:
    def __init__(self, lib, model):
        self._lib = lib
        self._model = model
        self._prefix = '{name}Machine'.format(name=model.root_state.name)
        self._var_types = {
            def_item.name: def_item.type for def_item in model.defines.values()
        }
        self._var_names = list(model.defines.keys())
        self._machine = self._bind_function('{prefix}_create', restype=ctypes.c_void_p)()
        self._destroy = self._bind_function('{prefix}_destroy', argtypes=[ctypes.c_void_p])
        self._hot_start = self._bind_function(
            '{prefix}_hot_start',
            argtypes=[ctypes.c_void_p, ctypes.c_char_p, ctypes.c_void_p],
            restype=ctypes.c_int,
        )
        self._cycle = self._bind_function(
            '{prefix}_cycle',
            argtypes=[ctypes.c_void_p, ctypes.POINTER(ctypes.c_char_p), ctypes.c_size_t],
            restype=ctypes.c_int,
        )
        self._set_hooks = self._bind_function(
            '{prefix}_set_hooks',
            argtypes=[ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p],
        )
        self._current_state_path = self._bind_function(
            '{prefix}_current_state_path', argtypes=[ctypes.c_void_p], restype=ctypes.c_char_p
        )
        self._is_ended = self._bind_function(
            '{prefix}_is_ended', argtypes=[ctypes.c_void_p], restype=ctypes.c_int
        )
        self._stack_size = self._bind_function(
            '{prefix}_stack_size', argtypes=[ctypes.c_void_p], restype=ctypes.c_size_t
        )
        self._stack_state_path = self._bind_function(
            '{prefix}_stack_state_path',
            argtypes=[ctypes.c_void_p, ctypes.c_size_t],
            restype=ctypes.c_char_p,
        )
        self._stack_mode = self._bind_function(
            '{prefix}_stack_mode',
            argtypes=[ctypes.c_void_p, ctypes.c_size_t],
            restype=ctypes.c_char_p,
        )
        self._last_error = self._bind_function(
            '{prefix}_last_error', argtypes=[ctypes.c_void_p], restype=ctypes.c_char_p
        )
        self._abstract_hook_count = self._bind_function(
            '{prefix}_abstract_hook_count', restype=ctypes.c_size_t
        )
        self._abstract_hook_info = self._bind_function(
            '{prefix}_abstract_hook_info',
            argtypes=[
                ctypes.c_size_t,
                ctypes.POINTER(ctypes.c_char_p),
                ctypes.POINTER(ctypes.c_char_p),
                ctypes.POINTER(ctypes.c_char_p),
                ctypes.POINTER(ctypes.c_char_p),
            ],
            restype=ctypes.c_int,
        )
        self._get_var_int = self._bind_function(
            '{prefix}_get_var_int',
            argtypes=[ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_longlong)],
            restype=ctypes.c_int,
        )
        self._set_var_int = self._bind_function(
            '{prefix}_set_var_int',
            argtypes=[ctypes.c_void_p, ctypes.c_char_p, ctypes.c_longlong],
            restype=ctypes.c_int,
        )
        self._get_var_float = self._bind_function(
            '{prefix}_get_var_float',
            argtypes=[ctypes.c_void_p, ctypes.c_char_p, ctypes.POINTER(ctypes.c_double)],
            restype=ctypes.c_int,
        )
        self._set_var_float = self._bind_function(
            '{prefix}_set_var_float',
            argtypes=[ctypes.c_void_p, ctypes.c_char_p, ctypes.c_double],
            restype=ctypes.c_int,
        )

        class _ContextStruct(ctypes.Structure):
            _fields_ = [
                ('state_path', ctypes.c_char_p),
                ('vars', ctypes.c_void_p),
                ('action_name', ctypes.c_char_p),
                ('action_stage', ctypes.c_char_p),
            ]

        self._context_struct = _ContextStruct
        self._hook_fn = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
        self._hook_info_rows = self._load_hook_info()
        hook_fields = [
            (row['hook_field'], self._hook_fn)
            for row in self._hook_info_rows
        ] or [('_unused_placeholder', ctypes.c_int)]

        class _HooksStruct(ctypes.Structure):
            _fields_ = hook_fields

        self._hooks_struct = _HooksStruct
        self._hook_callbacks = []
        self._hook_values = None

    def close(self):
        if self._machine:
            self._destroy(self._machine)
            self._machine = None
        temporary_directory = getattr(self, '_temporary_directory', None)
        if temporary_directory is not None:
            temporary_directory.cleanup()
            self._temporary_directory = None

    def _bind_function(self, template, argtypes=None, restype=None):
        fn = getattr(self._lib, template.format(prefix=self._prefix))
        if argtypes is not None:
            fn.argtypes = argtypes
        if restype is not None:
            fn.restype = restype
        return fn

    def _load_hook_info(self):
        rows = []
        for index in range(self._abstract_hook_count()):
            dsl_action_path = ctypes.c_char_p()
            hook_field = ctypes.c_char_p()
            owner_state_path = ctypes.c_char_p()
            action_stage = ctypes.c_char_p()
            assert self._abstract_hook_info(
                index,
                ctypes.byref(dsl_action_path),
                ctypes.byref(hook_field),
                ctypes.byref(owner_state_path),
                ctypes.byref(action_stage),
            ) == 1
            rows.append({
                'dsl_action_path': dsl_action_path.value.decode('utf-8'),
                'hook_field': hook_field.value.decode('utf-8'),
                'owner_state_path': owner_state_path.value.decode('utf-8'),
                'action_stage': action_stage.value.decode('utf-8'),
            })
        return rows

    def _raise_last_error(self):
        message = self._last_error(self._machine)
        raise RuntimeError(message.decode('utf-8') if message else 'unknown C runtime error')

    def _get_var_from_ptr(self, machine_ptr, name):
        if self._var_types[name] == 'int':
            value = ctypes.c_longlong()
            if self._get_var_int(machine_ptr, name.encode('utf-8'), ctypes.byref(value)) != 1:
                self._raise_last_error()
            return value.value
        value = ctypes.c_double()
        if self._get_var_float(machine_ptr, name.encode('utf-8'), ctypes.byref(value)) != 1:
            self._raise_last_error()
        return value.value

    def _set_var_from_ptr(self, machine_ptr, name, value):
        if self._var_types[name] == 'int':
            if self._set_var_int(machine_ptr, name.encode('utf-8'), int(value)) != 1:
                self._raise_last_error()
        else:
            if self._set_var_float(machine_ptr, name.encode('utf-8'), float(value)) != 1:
                self._raise_last_error()

    def hot_start(self, initial_state, initial_vars):
        if set(initial_vars.keys()) != set(self._var_names):
            raise ValueError('initial_vars must provide all variables exactly once.')
        values = self._create_initial_vars(initial_vars)
        if self._hot_start(self._machine, initial_state.encode('utf-8'), ctypes.byref(values)) != 1:
            self._raise_last_error()

    def _create_initial_vars(self, initial_vars):
        field_defs = []
        for def_item in self._model.defines.values():
            if def_item.type == 'int':
                field_defs.append((def_item.name, ctypes.c_longlong))
            else:
                field_defs.append((def_item.name, ctypes.c_double))
        if not field_defs:
            field_defs = [('_unused_placeholder', ctypes.c_int)]

        class _VarsStruct(ctypes.Structure):
            _fields_ = field_defs

        values = _VarsStruct()
        if field_defs[0][0] == '_unused_placeholder':
            values._unused_placeholder = 0
        for name, value in initial_vars.items():
            setattr(values, name, value)
        return values

    def install_hooks(self, callback_map):
        if not self._hook_info_rows:
            return

        callbacks = []
        kwargs = {}
        for row in self._hook_info_rows:
            field_name = row['hook_field']
            py_callback = callback_map.get(field_name)
            if py_callback is None:
                kwargs[field_name] = self._hook_fn()
                continue

            def _make_callback(fn):
                @self._hook_fn
                def _callback(machine_ptr, ctx_ptr, user_data):
                    ctx = ctypes.cast(ctx_ptr, ctypes.POINTER(self._context_struct)).contents
                    fn(_ExecutionContextView(self, machine_ptr, ctx))

                return _callback

            callback = _make_callback(py_callback)
            callbacks.append(callback)
            kwargs[field_name] = callback

        self._hook_callbacks = callbacks
        self._hook_values = self._hooks_struct(**kwargs)
        self._set_hooks(self._machine, ctypes.byref(self._hook_values), None)

    def cycle(self, events=None):
        if events is None:
            event_array = None
            event_count = 0
        else:
            event_array = (ctypes.c_char_p * len(events))(
                *[item.encode('utf-8') for item in events]
            )
            event_count = len(events)
        if self._cycle(self._machine, event_array, event_count) != 1:
            self._raise_last_error()

    @property
    def vars(self):
        return {name: self._get_var_from_ptr(self._machine, name) for name in self._var_names}

    @property
    def is_ended(self):
        return bool(self._is_ended(self._machine))

    @property
    def current_state_path(self):
        value = self._current_state_path(self._machine)
        if not value:
            return None
        return tuple(value.decode('utf-8').split('.'))

    @property
    def brief_stack(self):
        items = []
        for index in range(self._stack_size(self._machine)):
            path = self._stack_state_path(self._machine, index)
            mode = self._stack_mode(self._machine, index)
            items.append((tuple(path.decode('utf-8').split('.')), mode.decode('utf-8')))
        return items

    def get_abstract_hook_map(self):
        return {
            row['dsl_action_path']: row['hook_field']
            for row in self._hook_info_rows
        }


@contextmanager
def render_c_artifacts(dsl_code):
    ast_node = parse_with_grammar_entry(
        textwrap.dedent(dsl_code).strip(),
        entry_name='state_machine_dsl',
    )
    model = parse_dsl_node_to_state_machine(ast_node)

    with TemporaryDirectory() as td:
        template_dir = extract_template('c', td)
        output_dir = os.path.join(td, 'out')
        StateMachineCodeRenderer(template_dir).render(model=model, output_dir=output_dir)
        build_info = build_shared_library(output_dir, model)
        yield {
            'model': model,
            'output_dir': output_dir,
            'machine_h_file': os.path.join(output_dir, 'machine.h'),
            'machine_c_file': os.path.join(output_dir, 'machine.c'),
            'readme_file': os.path.join(output_dir, 'README.md'),
            'readme_zh_file': os.path.join(output_dir, 'README_zh.md'),
            'shared_lib': build_info['shared_lib'],
            'build_dir': build_info['build_dir'],
            'build_files': build_info['build_files'],
            'cmake': build_info['cmake'],
            'compiler': build_info['compiler'],
        }


@contextmanager
def render_c_runtime(dsl_code):
    with render_c_artifacts(dsl_code) as artifacts:
        lib = ctypes.CDLL(artifacts['shared_lib'])
        runtime = _CRuntime(lib, artifacts['model'])
        try:
            yield runtime, artifacts
        finally:
            runtime.close()


def build_c_runtime(dsl_code, initial_state=None, initial_vars=None):
    ast_node = parse_with_grammar_entry(
        textwrap.dedent(dsl_code).strip(),
        entry_name='state_machine_dsl',
    )
    model = parse_dsl_node_to_state_machine(ast_node)

    tempdir = TemporaryDirectory()
    template_dir = extract_template('c', tempdir.name)
    output_dir = os.path.join(tempdir.name, 'out')
    StateMachineCodeRenderer(template_dir).render(model=model, output_dir=output_dir)
    build_info = build_shared_library(output_dir, model)

    runtime = _CRuntime(ctypes.CDLL(build_info['shared_lib']), model)
    if initial_state is not None:
        runtime.hot_start(initial_state, initial_vars or {})
    runtime._temporary_directory = tempdir
    return runtime
