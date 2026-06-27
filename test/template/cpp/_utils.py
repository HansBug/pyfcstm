import os
import shutil
import subprocess
import textwrap
from contextlib import contextmanager
from tempfile import TemporaryDirectory

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.template import extract_template


def _extract_cpp_template(work_dir):
    return extract_template("cpp", os.path.join(work_dir, "template"))


def _find_cmake():
    return shutil.which("cmake")


def _cmake_generator_args():
    if os.name == "nt":
        return ["-G", "MinGW Makefiles"]
    return []


def _find_built_executable(build_dir, stem):
    candidate_names = [stem + ".exe", stem]
    search_dirs = [
        build_dir,
        os.path.join(build_dir, "Release"),
        os.path.join(build_dir, "RelWithDebInfo"),
        os.path.join(build_dir, "Debug"),
        os.path.join(build_dir, "MinSizeRel"),
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
            if filename in candidate_names:
                return os.path.join(root, filename)

    raise FileNotFoundError(
        "Cannot find built executable {!r} under {!r}.".format(stem, build_dir)
    )


@contextmanager
def render_cpp_artifacts(dsl_code):
    ast_node = parse_with_grammar_entry(
        textwrap.dedent(dsl_code).strip(),
        entry_name="state_machine_dsl",
    )
    model = parse_dsl_node_to_state_machine(ast_node)

    with TemporaryDirectory() as td:
        template_dir = _extract_cpp_template(td)
        output_dir = os.path.join(td, "out")
        StateMachineCodeRenderer(template_dir).render(
            model=model, output_dir=output_dir
        )
        yield {
            "model": model,
            "output_dir": output_dir,
            "machine_h_file": os.path.join(output_dir, "machine.h"),
            "machine_c_file": os.path.join(output_dir, "machine.c"),
            "machine_hpp_file": os.path.join(output_dir, "machine.hpp"),
            "machine_cpp_file": os.path.join(output_dir, "machine.cpp"),
            "readme_file": os.path.join(output_dir, "README.md"),
            "readme_zh_file": os.path.join(output_dir, "README_zh.md"),
            "cmake": _find_cmake(),
        }


def compile_and_run_cpp_wrapper_harness(
    artifacts,
    stem,
    source_code,
    *,
    compile_definitions=None,
    c_compiler=None,
    cxx_compiler=None,
    cxx_compile_options=None,
):
    cmake_executable = artifacts["cmake"]
    if cmake_executable is None:
        pytest.skip("cmake is required for generated C++ wrapper tests.")

    project_dir = os.path.join(artifacts["output_dir"], stem + "_cmake_project")
    build_dir = os.path.join(project_dir, "build")
    os.makedirs(project_dir, exist_ok=True)
    os.makedirs(build_dir, exist_ok=True)

    source_file = os.path.join(project_dir, stem + ".cpp")
    cmakelists = os.path.join(project_dir, "CMakeLists.txt")
    with open(source_file, "w", encoding="utf-8") as f:
        f.write(source_code)
    with open(cmakelists, "w", encoding="utf-8") as f:
        cmake_lines = [
            "cmake_minimum_required(VERSION 3.5)",
            "project({project_name} C CXX)".format(project_name=stem + "_project"),
            "",
            'include_directories("{machine_dir}")'.format(
                machine_dir=artifacts["output_dir"].replace("\\", "/")
            ),
            "",
            "add_executable({target_name}".format(target_name=stem),
            '    "{machine_c_file}"'.format(
                machine_c_file=artifacts["machine_c_file"].replace("\\", "/")
            ),
            '    "{machine_cpp_file}"'.format(
                machine_cpp_file=artifacts["machine_cpp_file"].replace("\\", "/")
            ),
            '    "{source_file}"'.format(source_file=source_file.replace("\\", "/")),
            ")",
            "",
            "set_target_properties(",
            "    {target_name}".format(target_name=stem),
            "    PROPERTIES",
            "    C_STANDARD 99",
            "    C_STANDARD_REQUIRED YES",
            "    C_EXTENSIONS NO",
            "    CXX_STANDARD 98",
            "    CXX_STANDARD_REQUIRED YES",
            "    CXX_EXTENSIONS NO",
            ")",
            "",
        ]
        if compile_definitions:
            cmake_lines.extend(
                [
                    "target_compile_definitions(",
                    "    {target_name}".format(target_name=stem),
                    "    PRIVATE",
                ]
            )
            cmake_lines.extend(
                "    {definition}".format(definition=definition)
                for definition in compile_definitions
            )
            cmake_lines.extend(
                [
                    ")",
                    "",
                ]
            )
        if cxx_compile_options:
            cmake_lines.extend(
                [
                    "target_compile_options(",
                    "    {target_name}".format(target_name=stem),
                    "    PRIVATE",
                ]
            )
            cmake_lines.extend(
                '    "$<$<COMPILE_LANGUAGE:CXX>:{option}>"'.format(option=option)
                for option in cxx_compile_options
            )
            cmake_lines.extend(
                [
                    ")",
                    "",
                ]
            )
        cmake_lines.extend(
            [
                "if (NOT WIN32)",
                "    target_link_libraries({target_name} m)".format(target_name=stem),
                "endif()",
                "",
            ]
        )
        f.write("\n".join(cmake_lines))

    configure_command = [cmake_executable] + _cmake_generator_args()
    if c_compiler is not None:
        configure_command.append("-DCMAKE_C_COMPILER={}".format(c_compiler))
    if cxx_compiler is not None:
        configure_command.append("-DCMAKE_CXX_COMPILER={}".format(cxx_compiler))
    configure_command.extend(
        [
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            os.path.abspath(project_dir),
        ]
    )

    configure_result = subprocess.run(
        configure_command,
        cwd=build_dir,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if configure_result.returncode != 0:
        pytest.fail(
            "CMake configure failed for {stem}.\nstdout:\n{stdout}\nstderr:\n{stderr}".format(
                stem=stem,
                stdout=configure_result.stdout,
                stderr=configure_result.stderr,
            )
        )

    build_result = subprocess.run(
        [cmake_executable, "--build", ".", "--config", "Release"],
        cwd=build_dir,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if build_result.returncode != 0:
        pytest.fail(
            "CMake build failed for {stem}.\nstdout:\n{stdout}\nstderr:\n{stderr}".format(
                stem=stem,
                stdout=build_result.stdout,
                stderr=build_result.stderr,
            )
        )

    return subprocess.run(
        [_find_built_executable(build_dir, stem)],
        cwd=build_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def available_compiler_pair(c_compiler_name, cxx_compiler_name):
    c_compiler = shutil.which(c_compiler_name)
    cxx_compiler = shutil.which(cxx_compiler_name)
    if c_compiler is None or cxx_compiler is None:
        pytest.skip(
            "{c_compiler_name}/{cxx_compiler_name} are required for this wrapper compile gate.".format(
                c_compiler_name=c_compiler_name,
                cxx_compiler_name=cxx_compiler_name,
            )
        )
    return c_compiler, cxx_compiler


def compile_with_msvc_like_tool(artifacts, stem, source_code, tool_name):
    if os.name != "nt":
        pytest.skip(
            "{tool_name} wrapper gate only runs on Windows.".format(tool_name=tool_name)
        )

    compiler = shutil.which(tool_name)
    if compiler is None:
        pytest.skip(
            "{tool_name} is required for this wrapper compile gate.".format(
                tool_name=tool_name
            )
        )

    project_dir = os.path.join(artifacts["output_dir"], stem + "_msvc_project")
    os.makedirs(project_dir, exist_ok=True)
    source_file = os.path.join(project_dir, stem + ".cpp")
    with open(source_file, "w", encoding="utf-8") as f:
        f.write(source_code)

    common_args = [
        compiler,
        "/nologo",
        "/c",
        "/I" + artifacts["output_dir"],
        "/GR-",
    ]
    commands = [
        common_args
        + [
            "/TC",
            artifacts["machine_c_file"],
            "/Fo" + os.path.join(project_dir, "machine_c.obj"),
        ],
        common_args
        + [
            artifacts["machine_cpp_file"],
            "/Fo" + os.path.join(project_dir, "machine_cpp.obj"),
        ],
        common_args + [source_file, "/Fo" + os.path.join(project_dir, "harness.obj")],
    ]
    for command in commands:
        result = subprocess.run(
            command,
            cwd=project_dir,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(
                "{tool_name} compile gate failed for {stem}.\ncommand: {command}\nstdout:\n{stdout}\nstderr:\n{stderr}".format(
                    tool_name=tool_name,
                    stem=stem,
                    command=" ".join(command),
                    stdout=result.stdout,
                    stderr=result.stderr,
                )
            )
