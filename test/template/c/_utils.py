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
from pyfcstm.utils import to_c_identifier


def _find_c_compiler():
    return shutil.which('cc') or shutil.which('gcc') or shutil.which('clang')


def _find_cpp_compiler():
    return shutil.which('c++') or shutil.which('g++') or shutil.which('clang++')


def _find_cmake():
    return shutil.which('cmake')


def _machine_macro_name(model):
    return '{name}_MACHINE'.format(name=to_c_identifier(model.root_state.name).upper())


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
                name=to_c_identifier(model.root_state.name) + 'Machine',
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
        [
            cmake_executable,
            '-DCMAKE_POLICY_VERSION_MINIMUM=3.5',
            os.path.abspath(output_dir),
        ],
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


def _load_runtime_library(shared_lib):
    temporary_directory = None
    dll_directory_handle = None
    load_path = shared_lib

    if os.name == 'nt':
        temporary_directory = TemporaryDirectory()
        load_path = os.path.join(temporary_directory.name, os.path.basename(shared_lib))
        shutil.copy2(shared_lib, load_path)
        if hasattr(os, 'add_dll_directory'):
            dll_directory_handle = os.add_dll_directory(temporary_directory.name)

    return ctypes.CDLL(load_path), temporary_directory, dll_directory_handle


def _collect_hook_info_rows(model):
    rows = []
    seen = set()
    for state in model.walk_states():
        groups = [
            state.list_on_enters(with_ids=True),
            state.list_on_durings(aspect=None, with_ids=True),
            state.list_on_exits(with_ids=True),
            state.list_on_durings(aspect='before', with_ids=True),
            state.list_on_durings(aspect='after', with_ids=True),
            state.list_on_during_aspects(aspect='before', with_ids=True),
            state.list_on_during_aspects(aspect='after', with_ids=True),
        ]
        for group in groups:
            for _, item in group:
                resolved = item
                for _ in range(16):
                    if resolved.ref is None:
                        break
                    resolved = resolved.ref
                if not resolved.is_abstract or resolved.func_name in seen:
                    continue
                seen.add(resolved.func_name)
                rows.append({
                    'dsl_action_path': resolved.func_name,
                    'hook_field': 'on_{name}'.format(name=to_c_identifier(resolved.func_name)),
                    'owner_state_path': '.'.join(resolved.parent.path),
                    'action_stage': resolved.stage,
                })
    return rows


class _ExecutionContextView:
    def __init__(self, runtime, ctx_struct):
        self._runtime = runtime
        self._vars_ptr = ctx_struct.vars
        self.action_name = ctx_struct.action_name.decode('utf-8')
        self.action_stage = ctx_struct.action_stage.decode('utf-8')
        self.state_path = ctx_struct.state_path.decode('utf-8')

    def get_var(self, name):
        return self._runtime._get_var_from_vars_ptr(self._vars_ptr, name)

    def has_var(self, name):
        return name in self._runtime._var_types

    def get_state_name(self):
        return self.state_path.split('.')[-1] if self.state_path else ''

    def get_full_state_path(self):
        return self.state_path


class _CRuntime:
    def __init__(self, lib, model, temporary_directories=None, dll_directory_handle=None):
        self._lib = lib
        self._model = model
        self._temporary_directories = list(temporary_directories or [])
        self._dll_directory_handle = dll_directory_handle
        self._prefix = '{name}Machine'.format(name=to_c_identifier(model.root_state.name))
        self._var_types = {
            def_item.name: def_item.type for def_item in model.defines.values()
        }
        self._var_names = list(model.defines.keys())
        self._generated_var_names = {
            name: to_c_identifier(name) for name in self._var_names
        }
        self._state_paths = ['.'.join(state.path) for state in model.walk_states()]
        self._state_ids = {
            path: index for index, path in enumerate(self._state_paths)
        }
        self._event_paths = []
        for state in model.walk_states():
            for event in state.events.values():
                self._event_paths.append(event.path_name)
        self._event_ids = {
            path: index for index, path in enumerate(self._event_paths)
        }
        self._vars_struct = self._build_vars_struct_type()
        self._machine = self._bind_function('{prefix}_create', restype=ctypes.c_void_p)()
        self._destroy = self._bind_function('{prefix}_destroy', argtypes=[ctypes.c_void_p])
        self._hot_start = self._bind_function(
            '{prefix}_hot_start',
            argtypes=[ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p],
            restype=ctypes.c_int,
        )
        self._cycle = self._bind_function(
            '{prefix}_cycle',
            argtypes=[ctypes.c_void_p, ctypes.POINTER(ctypes.c_int), ctypes.c_size_t],
            restype=ctypes.c_int,
        )
        self._set_hooks = self._bind_function(
            '{prefix}_set_hooks',
            argtypes=[ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p],
        )
        self._vars = self._bind_function(
            '{prefix}_vars',
            argtypes=[ctypes.c_void_p],
            restype=ctypes.POINTER(self._vars_struct),
        )
        self._current_state_path = self._bind_function(
            '{prefix}_current_state_path', argtypes=[ctypes.c_void_p], restype=ctypes.c_char_p
        )
        self._is_ended = self._bind_function(
            '{prefix}_is_ended', argtypes=[ctypes.c_void_p], restype=ctypes.c_int
        )
        self._last_error = self._bind_function(
            '{prefix}_last_error', argtypes=[ctypes.c_void_p], restype=ctypes.c_char_p
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
        self._hook_info_rows = _collect_hook_info_rows(model)
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
        if os.name == 'nt' and self._lib is not None and getattr(self._lib, '_handle', None):
            free_library = ctypes.windll.kernel32.FreeLibrary
            free_library.argtypes = [ctypes.c_void_p]
            free_library.restype = ctypes.c_int
            free_library(self._lib._handle)
        self._lib = None
        if self._dll_directory_handle is not None:
            self._dll_directory_handle.close()
            self._dll_directory_handle = None
        for temporary_directory in reversed(self._temporary_directories):
            temporary_directory.cleanup()
        self._temporary_directories = []

    def _bind_function(self, template, argtypes=None, restype=None):
        fn = getattr(self._lib, template.format(prefix=self._prefix))
        if argtypes is not None:
            fn.argtypes = argtypes
        if restype is not None:
            fn.restype = restype
        return fn

    def _build_vars_struct_type(self):
        field_defs = []
        for def_item in self._model.defines.values():
            if def_item.type == 'int':
                field_defs.append((to_c_identifier(def_item.name), ctypes.c_longlong))
            else:
                field_defs.append((to_c_identifier(def_item.name), ctypes.c_double))
        if not field_defs:
            field_defs = [('_unused_placeholder', ctypes.c_int)]

        class _VarsStruct(ctypes.Structure):
            _fields_ = field_defs

        return _VarsStruct

    def _raise_last_error(self):
        message = self._last_error(self._machine)
        raise RuntimeError(message.decode('utf-8') if message else 'unknown C runtime error')

    def _get_var_from_vars_ptr(self, vars_ptr, name):
        values = ctypes.cast(vars_ptr, ctypes.POINTER(self._vars_struct)).contents
        return getattr(values, self._generated_var_names[name])

    def _get_var_from_ptr(self, machine_ptr, name):
        return self._get_var_from_vars_ptr(self._vars(machine_ptr), name)

    def _resolve_state_id(self, initial_state):
        if isinstance(initial_state, int):
            return initial_state
        if not isinstance(initial_state, str):
            raise TypeError('initial_state must be an int state id or a state-path string.')
        if initial_state not in self._state_ids:
            raise ValueError('Unknown state path: {!r}'.format(initial_state))
        return self._state_ids[initial_state]

    def _resolve_event_id(self, event_ref):
        if isinstance(event_ref, int):
            return event_ref
        if not isinstance(event_ref, str):
            raise TypeError('event items must be integers or event-path strings.')
        if not event_ref:
            raise ValueError('event items cannot be empty strings.')

        current_path_tuple = self.current_state_path
        current_path = '.'.join(current_path_tuple) if current_path_tuple is not None else None
        root_path = '.'.join(self._model.root_state.path)

        if current_path is None:
            if event_ref not in self._event_ids:
                raise ValueError('Cannot resolve event path after runtime end: {!r}'.format(event_ref))
            return self._event_ids[event_ref]

        if event_ref.startswith('/'):
            remaining = event_ref[1:]
            if not remaining:
                raise ValueError("Absolute event reference cannot be just '/'.")
            resolved = root_path + '.' + remaining
        elif event_ref.startswith('.'):
            dot_count = len(event_ref) - len(event_ref.lstrip('.'))
            remaining = event_ref[dot_count:]
            if not remaining:
                raise ValueError(
                    'Parent-relative event reference cannot end with dots: {!r}'.format(event_ref)
                )
            parts = current_path.split('.')
            if dot_count >= len(parts):
                raise ValueError(
                    'Parent-relative event reference goes beyond root state: {!r}'.format(event_ref)
                )
            resolved = '.'.join(parts[:-dot_count] + [remaining])
        elif event_ref in self._event_ids:
            resolved = event_ref
        else:
            resolved = current_path + '.' + event_ref

        if resolved not in self._event_ids:
            raise ValueError('Unknown event path: {!r}'.format(event_ref))
        return self._event_ids[resolved]

    def hot_start(self, initial_state, initial_vars):
        if set(initial_vars.keys()) != set(self._var_names):
            raise ValueError('initial_vars must provide all variables exactly once.')
        values = self._create_initial_vars(initial_vars)
        state_id = self._resolve_state_id(initial_state)
        if self._hot_start(self._machine, state_id, ctypes.byref(values)) != 1:
            self._raise_last_error()

    def _create_initial_vars(self, initial_vars):
        values = self._vars_struct()
        if not self._var_names:
            values._unused_placeholder = 0
        for name, value in initial_vars.items():
            setattr(values, self._generated_var_names[name], value)
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
                    fn(_ExecutionContextView(self, ctx))

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
            event_ids = [self._resolve_event_id(item) for item in events]
            if event_ids:
                event_array = (ctypes.c_int * len(event_ids))(*event_ids)
                event_count = len(event_ids)
            else:
                event_array = None
                event_count = 0
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
            'cpp_compiler': _find_cpp_compiler(),
        }


@contextmanager
def render_c_runtime(dsl_code):
    with render_c_artifacts(dsl_code) as artifacts:
        lib, runtime_tempdir, dll_directory_handle = _load_runtime_library(artifacts['shared_lib'])
        temporary_directories = [runtime_tempdir] if runtime_tempdir is not None else []
        runtime = _CRuntime(
            lib,
            artifacts['model'],
            temporary_directories=temporary_directories,
            dll_directory_handle=dll_directory_handle,
        )
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

    lib, runtime_tempdir, dll_directory_handle = _load_runtime_library(build_info['shared_lib'])
    temporary_directories = [tempdir]
    if runtime_tempdir is not None:
        temporary_directories.append(runtime_tempdir)
    runtime = _CRuntime(
        lib,
        model,
        temporary_directories=temporary_directories,
        dll_directory_handle=dll_directory_handle,
    )
    if initial_state is not None:
        runtime.hot_start(initial_state, initial_vars or {})
    return runtime
