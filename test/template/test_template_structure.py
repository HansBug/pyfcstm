"""Regression checks for built-in template structure and generated contracts."""

import ast
import json
import re
from pathlib import Path
from tempfile import TemporaryDirectory

import pathspec
import pytest
import yaml

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.template import extract_template, get_template_info, list_templates


_CURRENT_TEMPLATE_NAMES = tuple(list_templates())
_TEMPLATE_LANGUAGE_VOCABULARY = {
    "c",
    "cpp",
    "python",
    "java",
    "js",
    "rust",
    "ruby",
    "go",
}
_CONFIG_TOP_LEVEL_KEYS = {
    "expr_styles",
    "stmt_styles",
    "globals",
    "filters",
    "tests",
    "ignores",
}
_REQUIRED_TEMPLATE_FILES = {
    "c": {
        "README.md",
        "README_zh.md",
        "README.md.j2",
        "README_zh.md.j2",
        "config.yaml",
        "template.json",
        "machine.h.j2",
        "machine.c.j2",
    },
    "c_poll": {
        "README.md",
        "README_zh.md",
        "README.md.j2",
        "README_zh.md.j2",
        "config.yaml",
        "template.json",
        "machine.h.j2",
        "machine.c.j2",
    },
    "cpp": {
        "README.md",
        "README_zh.md",
        "README.md.j2",
        "README_zh.md.j2",
        "config.yaml",
        "template.json",
        "machine.h.j2",
        "machine.c.j2",
        "machine.hpp.j2",
        "machine.cpp.j2",
    },
    "cpp_poll": {
        "README.md",
        "README_zh.md",
        "README.md.j2",
        "README_zh.md.j2",
        "config.yaml",
        "template.json",
        "machine.h.j2",
        "machine.c.j2",
        "machine.hpp.j2",
        "machine.cpp.j2",
    },
    "python": {
        "README.md",
        "README_zh.md",
        "README.md.j2",
        "README_zh.md.j2",
        "config.yaml",
        "template.json",
        "machine.py.j2",
    },
}
_RUNTIME_TEMPLATES = {
    "c": ("machine.h.j2", "machine.c.j2"),
    "c_poll": ("machine.h.j2", "machine.c.j2"),
    "cpp": ("machine.h.j2", "machine.c.j2", "machine.hpp.j2", "machine.cpp.j2"),
    "cpp_poll": ("machine.h.j2", "machine.c.j2", "machine.hpp.j2", "machine.cpp.j2"),
    "python": ("machine.py.j2",),
}
_ALLOWED_PYTHON_RUNTIME_IMPORTS = {"dataclasses", "math", "types", "typing"}
_ALLOWED_C_RUNTIME_INCLUDES = {
    "machine.h",
    "math.h",
    "stddef.h",
    "stdarg.h",
    "stdio.h",
    "stdlib.h",
    "string.h",
}
_BANNED_RUNTIME_DEPENDENCIES = (
    "pyfcstm",
    "jinja2",
    "yaml",
    "pathspec",
)
_BANNED_SOURCE_WORDING = (
    "original source",
    "raw source",
    "raw dsl source",
    "original dsl source",
    "原始 dsl",
    "原始 dsl 源码",
    "原始 source",
    "原始源码",
    "原始源代码",
    "原始输入源码",
    "原始输入源代码",
    "raw 源码",
    "raw 源代码",
)


@pytest.fixture(scope="session")
def representative_model():
    dsl_code = """
    def int counter = 0;
    def int ready = 0;
    def float gain = 1.5;
    state Control {
        enter abstract Boot;
        state Idle {
            during { counter = counter + 1; }
        }
        state Active {
            enter abstract ActiveEnter;
            during before { gain = gain + 0.5; }
            state Work {
                enter { counter = counter + 2; }
                during { counter = counter + 3; }
            }
            [*] -> Work : if [ready == 1];
        }
        state Done;
        [*] -> Idle;
        Idle -> Active :: Start effect { ready = 1; counter = counter + 10; };
        Active -> Done : if [counter >= 20] effect { counter = counter + 1; };
    }
    """
    ast_node = parse_with_grammar_entry(
        re.sub(r"^ {4}", "", dsl_code, flags=re.M).strip(),
        entry_name="state_machine_dsl",
    )
    return parse_dsl_node_to_state_machine(ast_node)


@pytest.fixture(scope="session")
def rendered_templates(representative_model):
    with TemporaryDirectory() as extraction_td, TemporaryDirectory() as render_td:
        extraction_root = Path(extraction_td)
        output_root = Path(render_td)
        template_dirs = _extract_templates(extraction_root)
        yield _render_template_directories(
            template_dirs,
            representative_model,
            output_root,
        )


def _read_text(path):
    return path.read_text(encoding="utf-8")


def _extract_templates(root):
    return {
        name: Path(extract_template(name, str(root / name)))
        for name in _CURRENT_TEMPLATE_NAMES
    }


def _load_config(template_dir):
    with (template_dir / "config.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _load_template_metadata(template_dir):
    with (template_dir / "template.json").open("r", encoding="utf-8") as f:
        return json.load(f)


def _ignore_spec(config):
    return pathspec.GitIgnoreSpec.from_lines(config.get("ignores", []))


def _render_template_directories(template_dirs, model, output_root):
    rendered = {}
    for name, template_dir in template_dirs.items():
        output_dir = output_root / name
        StateMachineCodeRenderer(str(template_dir)).render(
            model=model,
            output_dir=str(output_dir),
        )
        rendered[name] = output_dir
    return rendered


def _first_c_comment_block(source):
    start = source.find("/*")
    end = source.find("*/", start)
    assert start >= 0
    assert source[:start].strip() == ""
    assert end > start
    return source[start : end + 2]


def _normalize_generated_comment(text):
    text = re.sub(r"/\*|\*/", " ", text)
    text = re.sub(r"(?m)^\s*\* ?", "", text)
    return " ".join(text.lower().split())


def _assert_banner_terms(text, *, template_name, root_name):
    normalized = _normalize_generated_comment(text)
    assert "generated" in normalized
    assert template_name in normalized
    assert root_name.lower() in normalized
    assert "do not edit" in normalized
    assert "regenerate" in normalized
    assert "self-contained" in normalized
    assert "third-party runtime" in normalized


def _assert_source_context_terms(text):
    normalized = " ".join(text.lower().split())
    compact = "".join(text.lower().split())
    assert (
        "canonical model export" in normalized
        or "normalized model export" in normalized
    )
    for banned in _BANNED_SOURCE_WORDING:
        assert banned not in normalized
        assert "".join(banned.split()) not in compact


def _assert_python_runtime_imports_are_self_contained(source):
    tree = ast.parse(source)
    imported_modules = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0
            imported_modules.add((node.module or "").split(".", 1)[0])
    assert imported_modules <= _ALLOWED_PYTHON_RUNTIME_IMPORTS
    assert not (imported_modules & set(_BANNED_RUNTIME_DEPENDENCIES))


def _assert_c_runtime_includes_are_self_contained(source):
    include_targets = re.findall(r'^\s*#include\s+[<"]([^>"]+)[>"]', source, flags=re.M)
    assert include_targets
    assert set(include_targets) <= _ALLOWED_C_RUNTIME_INCLUDES
    assert not (set(include_targets) & set(_BANNED_RUNTIME_DEPENDENCIES))


def _assert_rendered_template_contracts(rendered_templates):
    python_source = _read_text(rendered_templates["python"] / "machine.py")
    python_docstring = ast.get_docstring(ast.parse(python_source))
    assert python_docstring is not None
    _assert_banner_terms(python_docstring, template_name="python", root_name="Control")
    _assert_source_context_terms(python_docstring)
    _assert_source_context_terms(_read_text(rendered_templates["python"] / "README.md"))
    _assert_source_context_terms(
        _read_text(rendered_templates["python"] / "README_zh.md")
    )
    _assert_python_runtime_imports_are_self_contained(python_source)

    for name in ["c", "c_poll", "cpp", "cpp_poll"]:
        header_source = _read_text(rendered_templates[name] / "machine.h")
        runtime_source = _read_text(rendered_templates[name] / "machine.c")
        c_core_name = {"cpp": "c", "cpp_poll": "c_poll"}.get(name, name)
        _assert_banner_terms(
            _first_c_comment_block(header_source),
            template_name=c_core_name,
            root_name="Control",
        )
        _assert_banner_terms(
            _first_c_comment_block(runtime_source),
            template_name=c_core_name,
            root_name="Control",
        )
        for generated_text in [
            header_source,
            runtime_source,
            _read_text(rendered_templates[name] / "README.md"),
            _read_text(rendered_templates[name] / "README_zh.md"),
        ]:
            _assert_source_context_terms(generated_text)
        assert "__extension__ long long" not in header_source
        _assert_c_runtime_includes_are_self_contained(header_source)
        _assert_c_runtime_includes_are_self_contained(runtime_source)

    for name in ["cpp", "cpp_poll"]:
        wrapper_header_source = _read_text(rendered_templates[name] / "machine.hpp")
        wrapper_source = _read_text(rendered_templates[name] / "machine.cpp")
        _assert_banner_terms(
            _first_c_comment_block(wrapper_header_source),
            template_name=name,
            root_name="Control",
        )
        assert '#include "machine.h"' in wrapper_header_source
        assert '#include "machine.hpp"' in wrapper_source
        assert "pyfcstm" not in wrapper_source.replace("pyfcstm_generated", "")
        assert "throw" not in wrapper_source
        assert "try" not in wrapper_source
        assert "catch" not in wrapper_source


@pytest.mark.unittest
def test_extracted_templates_expose_required_file_contract():
    with TemporaryDirectory() as td:
        template_dirs = _extract_templates(Path(td))
        assert set(_CURRENT_TEMPLATE_NAMES) <= set(template_dirs)

        for name, template_dir in template_dirs.items():
            metadata = _load_template_metadata(template_dir)
            assert metadata["name"] == name
            assert metadata["language"] in _TEMPLATE_LANGUAGE_VOCABULARY
            if name not in _REQUIRED_TEMPLATE_FILES:
                pytest.fail(
                    "Add a required-file contract for built-in template {name!r}.".format(
                        name=name,
                    )
                )

            files = {item.name for item in template_dir.iterdir() if item.is_file()}
            assert _REQUIRED_TEMPLATE_FILES[name] <= files


@pytest.mark.unittest
def test_template_metadata_matches_packaged_asset_contract():
    with TemporaryDirectory() as td:
        template_dirs = _extract_templates(Path(td))
        assert set(_CURRENT_TEMPLATE_NAMES) == set(template_dirs)

        for name, template_dir in template_dirs.items():
            template_metadata = _load_template_metadata(template_dir)
            api_metadata = get_template_info(name)

            assert api_metadata["name"] == name
            assert api_metadata["archive"] == "{name}.zip".format(name=name)
            assert api_metadata["root_dir"] == name
            for key in ["name", "title", "description", "language", "experimental"]:
                assert api_metadata[key] == template_metadata[key]
            assert api_metadata["language"] in _TEMPLATE_LANGUAGE_VOCABULARY


@pytest.mark.unittest
def test_template_configs_keep_renderer_contract_and_ignores():
    with TemporaryDirectory() as td:
        for name, template_dir in _extract_templates(Path(td)).items():
            config = _load_config(template_dir)
            unknown_keys = set(config) - _CONFIG_TOP_LEVEL_KEYS
            assert not unknown_keys

            spec = _ignore_spec(config)
            assert not spec.match_file("README.md.j2")
            assert not spec.match_file("README_zh.md.j2")
            for runtime_template in _RUNTIME_TEMPLATES[name]:
                assert not spec.match_file(runtime_template)


@pytest.mark.unittest
def test_generated_readmes_keep_generated_guidance(rendered_templates):
    for name in _CURRENT_TEMPLATE_NAMES:
        generated_readme = _read_text(rendered_templates[name] / "README.md")
        generated_readme_zh = _read_text(rendered_templates[name] / "README_zh.md")
        for generated_text in [generated_readme, generated_readme_zh]:
            lowered = generated_text.lower()
            assert "template maintainer handbook" not in lowered
            assert "generated files" in lowered or "生成文件" in generated_text
            assert "model text" in lowered or "模型文本" in generated_text
            assert "cycle" in lowered or "周期" in generated_text


@pytest.mark.unittest
def test_c_family_readmes_document_deployment_safety_boundaries(rendered_templates):
    for name in ["c", "c_poll", "cpp", "cpp_poll"]:
        generated_readme = _read_text(rendered_templates[name] / "README.md")
        generated_readme_zh = _read_text(rendered_templates[name] / "README_zh.md")
        for text in [generated_readme, generated_readme_zh]:
            assert "pyfcstm inspect" in text
            assert "C/C++ deployment-profile" in text
            assert "Python" in text
            assert "https://github.com/HansBug/pyfcstm/issues/254" in text
            assert "https://github.com/HansBug/pyfcstm/issues/255" in text
            assert "non-reentrant" in text
            assert "volatile" in text
            assert "DMA" in text

        generated_readme_words = " ".join(generated_readme.split())
        generated_readme_zh_words = " ".join(generated_readme_zh.split())
        assert (
            "This generated runtime is not a claim of MISRA, AUTOSAR, "
            "DO-178C, IEC 61508, or ISO 26262 certification readiness."
            in generated_readme_words
        )
        assert (
            "They do not make this generated runtime MISRA, AUTOSAR, DO-178C, "
            "IEC 61508, ISO 26262, or other certification ready by themselves."
            in generated_readme_words
        )
        assert (
            "本生成运行时不宣称已经满足 MISRA、AUTOSAR、DO-178C、IEC 61508 "
            "或 ISO 26262 认证就绪要求。" in generated_readme_zh_words
        )
        assert (
            "它们本身不会让生成运行时达到 MISRA、AUTOSAR、DO-178C、IEC 61508、"
            "ISO 26262 或其他认证 ready。" in generated_readme_zh_words
        )

        assert "Integration Preflight Checklist" in generated_readme
        assert "engineering evidence" in generated_readme
        assert "集成前检查清单" in generated_readme_zh
        assert "工程证据" in generated_readme_zh

    for name in ["c_poll", "cpp_poll"]:
        generated_readme = _read_text(rendered_templates[name] / "README.md")
        generated_readme_zh = _read_text(rendered_templates[name] / "README_zh.md")
        assert "complete" in generated_readme
        assert "EventChecks" in generated_readme
        assert "完整" in generated_readme_zh
        assert "EventChecks" in generated_readme_zh

    for name in ["cpp", "cpp_poll"]:
        generated_readme = _read_text(rendered_templates[name] / "README.md")
        generated_readme_zh = _read_text(rendered_templates[name] / "README_zh.md")
        assert "wrapper surface" in generated_readme
        assert "MachineWrapper" in generated_readme
        assert "wrapper surface" in generated_readme_zh
        assert "MachineWrapper" in generated_readme_zh


@pytest.mark.unittest
def test_cpp_template_documentation_describes_early_first_class_status(
    rendered_templates,
):
    expected_metadata_descriptions = {
        "cpp": "Early-stage first-class C++ template",
        "cpp_poll": "Early-stage first-class C++ poll template",
    }
    for name, expected_description in expected_metadata_descriptions.items():
        metadata = get_template_info(name)
        assert metadata["experimental"] is True
        assert expected_description in metadata["description"]

        generated_readme = _read_text(rendered_templates[name] / "README.md")
        generated_readme_zh = _read_text(rendered_templates[name] / "README_zh.md")
        for text in [generated_readme, generated_readme_zh]:
            assert "`c`, `c_poll`, `cpp`, and `cpp_poll`" in text or (
                "`c`、`c_poll`、`cpp` 和 `cpp_poll`" in text
            )
            assert "gcc -std=c99" in text
            assert "g++ -std=c++98" in text
            assert "clang -std=c99" in text
            assert "clang++ -std=c++98" in text
            assert "cmake_minimum_required" in text


@pytest.mark.unittest
def test_generated_sources_preserve_banner_source_context_and_dependency_boundary(
    rendered_templates,
):
    _assert_rendered_template_contracts(rendered_templates)


@pytest.mark.unittest
def test_generated_source_templates_keep_source_metadata_wording():
    with TemporaryDirectory() as td:
        for name, template_dir in _extract_templates(Path(td)).items():
            for rel_path in ["README.md.j2", "README_zh.md.j2"] + list(
                _RUNTIME_TEMPLATES[name]
            ):
                source = _read_text(template_dir / rel_path)
                normalized = " ".join(source.lower().split())
                compact = "".join(source.lower().split())
                for banned in _BANNED_SOURCE_WORDING:
                    assert banned not in normalized
                    assert "".join(banned.split()) not in compact


@pytest.mark.unittest
def test_extracted_builtin_templates_preserve_source_structure_contract():
    with TemporaryDirectory() as td:
        for name, extracted_dir in _extract_templates(Path(td)).items():
            assert extracted_dir.name == get_template_info(name)["root_dir"]
            files = {item.name for item in extracted_dir.iterdir() if item.is_file()}
            assert _REQUIRED_TEMPLATE_FILES[name] <= files

            config = yaml.safe_load(_read_text(extracted_dir / "config.yaml"))
            assert not (set(config) - _CONFIG_TOP_LEVEL_KEYS)
            spec = _ignore_spec(config)
            assert not spec.match_file("README.md.j2")
            assert not spec.match_file("README_zh.md.j2")


@pytest.mark.unittest
def test_cpp_c_core_generated_outputs_match_c_templates(rendered_templates):
    for rel_path in ["machine.c", "machine.h"]:
        assert _read_text(rendered_templates["cpp"] / rel_path) == _read_text(
            rendered_templates["c"] / rel_path
        )
        assert _read_text(rendered_templates["cpp_poll"] / rel_path) == _read_text(
            rendered_templates["c_poll"] / rel_path
        )


@pytest.mark.unittest
def test_c_family_helpers_are_template_scoped():
    with TemporaryDirectory() as td:
        template_dirs = _extract_templates(Path(td))
        python_renderer = StateMachineCodeRenderer(str(template_dirs["python"]))
        c_helper_names = {
            "to_c_identifier",
            "to_c_path_identifier",
            "to_c_public_identifier",
            "to_c_public_macro_identifier",
            "is_c_public_identifier_reserved",
            "render_c_action_body",
            "render_c_condition_body",
            "render_c_reset_vars_body",
        }
        assert not (c_helper_names & set(python_renderer.env.filters))
        assert not (c_helper_names & set(python_renderer.env.globals))
        assert "c_public_identifier_reserved" not in python_renderer.env.tests

        for name in ["c", "c_poll", "cpp", "cpp_poll"]:
            renderer = StateMachineCodeRenderer(str(template_dirs[name]))
            assert c_helper_names <= (
                set(renderer.env.filters) | set(renderer.env.globals)
            )
            assert "c_public_identifier_reserved" in renderer.env.tests
