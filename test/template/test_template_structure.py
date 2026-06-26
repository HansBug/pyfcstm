"""Regression checks for built-in template structure and generated contracts."""

import ast
import json
import os
import re
import stat
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

import pathspec
import pytest
import yaml

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.template import extract_template, get_template_info, list_templates
from tools.package_templates import package_templates, _resolve_archive_source


_REPO_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_DIR = _REPO_ROOT / "templates"
_PACKAGED_TEMPLATE_DIR = _REPO_ROOT / "pyfcstm" / "template"
_CURRENT_TEMPLATE_NAMES = ("c", "c_poll", "cpp", "cpp_poll", "python")
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
_MAINTAINER_ONLY_FILES = {"README.md", "README_zh.md", "template.json"}
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


def _extract_archives(package_dir, output_root):
    template_dirs = {}
    for name in _CURRENT_TEMPLATE_NAMES:
        archive_path = package_dir / "{name}.zip".format(name=name)
        with zipfile.ZipFile(str(archive_path), "r") as zf:
            zf.extractall(str(output_root / name))
        template_dirs[name] = output_root / name / name
    return template_dirs


@pytest.fixture(scope="session")
def rendered_templates(representative_model):
    with TemporaryDirectory() as package_td:
        with TemporaryDirectory() as extraction_td:
            with TemporaryDirectory() as render_td:
                package_root = Path(package_td)
                extraction_root = Path(extraction_td)
                output_root = Path(render_td)
                package_templates(str(_TEMPLATES_DIR), str(package_root), verbose=False)
                yield _render_template_directories(
                    _extract_archives(package_root, extraction_root),
                    representative_model,
                    output_root,
                )


@pytest.fixture(scope="session")
def extracted_rendered_templates(representative_model):
    with TemporaryDirectory() as extraction_td, TemporaryDirectory() as render_td:
        extraction_root = Path(extraction_td)
        output_root = Path(render_td)
        template_dirs = {
            name: Path(extract_template(name, str(extraction_root / name)))
            for name in _CURRENT_TEMPLATE_NAMES
        }
        yield _render_template_directories(
            template_dirs,
            representative_model,
            output_root,
        )


def _repository_template_names():
    return tuple(
        item.name
        for item in sorted(_TEMPLATES_DIR.iterdir())
        if item.is_dir() and not item.name.startswith(".")
    )


def _read_json(path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _read_text(path):
    return path.read_text(encoding="utf-8")


def _load_template_metadata(name):
    return _read_json(_TEMPLATES_DIR / name / "template.json")


def _load_config(name):
    with (_TEMPLATES_DIR / name / "config.yaml").open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


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
def test_repository_templates_expose_required_file_contract():
    template_names = _repository_template_names()
    assert set(_CURRENT_TEMPLATE_NAMES) <= set(template_names)

    for name in template_names:
        metadata = _load_template_metadata(name)
        assert metadata["name"] == name
        assert metadata["language"] in _TEMPLATE_LANGUAGE_VOCABULARY
        if name not in _REQUIRED_TEMPLATE_FILES:
            pytest.fail(
                "Add a required-file contract for built-in template {name!r}.".format(
                    name=name,
                )
            )

        files = {
            item.name for item in (_TEMPLATES_DIR / name).iterdir() if item.is_file()
        }
        assert _REQUIRED_TEMPLATE_FILES[name] <= files


@pytest.mark.unittest
def test_template_metadata_matches_packaged_index_contract():
    index = _read_json(_PACKAGED_TEMPLATE_DIR / "index.json")
    index_items = {item["name"]: item for item in index["templates"]}
    repository_names = set(_repository_template_names())

    assert set(list_templates()) == repository_names
    assert set(index_items) == repository_names

    for name in repository_names:
        repo_metadata = _load_template_metadata(name)
        indexed_metadata = index_items[name]
        api_metadata = get_template_info(name)

        assert api_metadata == indexed_metadata
        assert indexed_metadata["name"] == name
        assert indexed_metadata["archive"] == "{name}.zip".format(name=name)
        assert indexed_metadata["root_dir"] == name
        for key in ["title", "description", "language", "experimental"]:
            assert indexed_metadata[key] == repo_metadata[key]
        assert indexed_metadata["language"] in _TEMPLATE_LANGUAGE_VOCABULARY


@pytest.mark.unittest
def test_template_configs_keep_renderer_contract_and_ignores():
    for name in _repository_template_names():
        config = _load_config(name)
        unknown_keys = set(config) - _CONFIG_TOP_LEVEL_KEYS
        assert not unknown_keys

        spec = _ignore_spec(config)
        for maintainer_file in _MAINTAINER_ONLY_FILES:
            assert spec.match_file(maintainer_file)
        assert not spec.match_file("README.md.j2")
        assert not spec.match_file("README_zh.md.j2")
        for runtime_template in _RUNTIME_TEMPLATES[name]:
            assert not spec.match_file(runtime_template)


@pytest.mark.unittest
def test_template_readmes_keep_maintainer_and_generated_guidance_separate(
    rendered_templates,
):
    root_readme = _read_text(_TEMPLATES_DIR / "README.md")
    root_readme_zh = _read_text(_TEMPLATES_DIR / "README_zh.md")
    for expected in [
        "python",
        "c",
        "c_poll",
        "cpp",
        "cpp_poll",
        "java",
        "js",
        "rust",
        "ruby",
        "go",
    ]:
        assert expected in root_readme
        assert expected in root_readme_zh

    for name in _repository_template_names():
        template_dir = _TEMPLATES_DIR / name
        maintainer_readme = _read_text(template_dir / "README.md").lower()
        maintainer_readme_zh = _read_text(template_dir / "README_zh.md").lower()
        assert "maintainer" in maintainer_readme
        assert "template" in maintainer_readme
        assert "not copied" in maintainer_readme or "ignored" in maintainer_readme
        assert "template" in maintainer_readme_zh or "模板" in maintainer_readme_zh

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
    root_readme = _read_text(_TEMPLATES_DIR / "README.md")
    root_readme_zh = _read_text(_TEMPLATES_DIR / "README_zh.md")

    assert "C/C++ deployment safety wording" in root_readme
    assert "C/C++ 部署安全表述" in root_readme_zh

    for name in ["c", "c_poll", "cpp", "cpp_poll"]:
        maintainer_readme = _read_text(_TEMPLATES_DIR / name / "README.md")
        maintainer_readme_zh = _read_text(_TEMPLATES_DIR / name / "README_zh.md")
        maintainer_readme_words = " ".join(maintainer_readme.split())
        maintainer_readme_zh_words = " ".join(maintainer_readme_zh.split())
        assert "engineering baseline" in maintainer_readme_words
        assert "not a certification package" in maintainer_readme_words
        assert "不是认证包" in maintainer_readme_zh_words
        assert (
            "Numeric inspect warning" in maintainer_readme
            or "Numeric-risk wording" in maintainer_readme
        )
        assert (
            "Numeric inspect warning" in maintainer_readme_zh
            or "数值风险表述" in maintainer_readme_zh
        )

        generated_readme = _read_text(rendered_templates[name] / "README.md")
        generated_readme_zh = _read_text(rendered_templates[name] / "README_zh.md")
        for text in [generated_readme, generated_readme_zh]:
            assert "pyfcstm inspect" in text
            assert "C/C++ deployment-profile" in text
            assert "Python" in text
            assert "https://github.com/HansBug/pyfcstm/issues/254" in text
            assert "https://github.com/HansBug/pyfcstm/issues/255" in text
            for certification_term in [
                "MISRA",
                "AUTOSAR",
                "DO-178C",
                "IEC 61508",
                "ISO 26262",
            ]:
                assert certification_term in text
            assert "non-reentrant" in text
            assert "volatile" in text
            assert "DMA" in text

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
    root_readme = _read_text(_TEMPLATES_DIR / "README.md")
    root_readme_zh = _read_text(_TEMPLATES_DIR / "README_zh.md")
    for text in [root_readme, root_readme_zh]:
        lowered = text.lower()
        assert "cpp" in lowered
        assert "cpp_poll" in lowered
        assert "early" in lowered or "早期" in text
        assert "first-class" in lowered or "一等" in text
        assert "experimental: true" in text
        assert "skeleton" not in lowered
        assert "prototype" not in lowered
        assert "原型" not in text

    expected_metadata_descriptions = {
        "cpp": "Early-stage first-class C++ template",
        "cpp_poll": "Early-stage first-class C++ poll template",
    }
    for name, expected_description in expected_metadata_descriptions.items():
        metadata = _load_template_metadata(name)
        assert metadata["experimental"] is True
        assert expected_description in metadata["description"]

        maintainer_readme = _read_text(_TEMPLATES_DIR / name / "README.md")
        maintainer_readme_zh = _read_text(_TEMPLATES_DIR / name / "README_zh.md")
        for text in [maintainer_readme, maintainer_readme_zh]:
            lowered = text.lower()
            assert "experimental: true" in text
            assert "early" in lowered or "早期" in text
            assert "first-class" in lowered or "一等" in text
            assert "unimplemented" in lowered or "未实现" in text
            assert "wrapper" in lowered
            assert "native toolchain" in lowered or "原生工具链" in text
            assert "skeleton" not in lowered
            assert "prototype" not in lowered
            assert "原型" not in text

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
    extracted_rendered_templates,
):
    _assert_rendered_template_contracts(rendered_templates)
    _assert_rendered_template_contracts(extracted_rendered_templates)


@pytest.mark.unittest
def test_generated_source_templates_keep_source_metadata_wording():
    for name in _repository_template_names():
        for rel_path in ["README.md.j2", "README_zh.md.j2"] + list(
            _RUNTIME_TEMPLATES[name]
        ):
            source = _read_text(_TEMPLATES_DIR / name / rel_path)
            normalized = " ".join(source.lower().split())
            compact = "".join(source.lower().split())
            for banned in _BANNED_SOURCE_WORDING:
                assert banned not in normalized
                assert "".join(banned.split()) not in compact


@pytest.mark.unittest
def test_packaging_output_preserves_metadata_and_archive_roots():
    with TemporaryDirectory() as td:
        output_dir = Path(td)
        stale_zip = output_dir / "stale.zip"
        stale_zip.write_bytes(b"stale")

        package_templates(str(_TEMPLATES_DIR), str(output_dir), verbose=False)

        assert not stale_zip.exists()
        index = _read_json(output_dir / "index.json")
        assert [item["name"] for item in index["templates"]] == list(
            _repository_template_names()
        )

        for item in index["templates"]:
            name = item["name"]
            repo_metadata = _load_template_metadata(name)
            assert item["archive"] == "{name}.zip".format(name=name)
            assert item["root_dir"] == name
            for key in ["title", "description", "language", "experimental"]:
                assert item[key] == repo_metadata[key]

            archive_path = output_dir / item["archive"]
            assert archive_path.is_file()
            with zipfile.ZipFile(str(archive_path), "r") as zf:
                names = zf.namelist()
            assert names
            assert all(path.startswith(name + "/") for path in names)
            archived_rel_paths = {path[len(name) + 1 :] for path in names}
            assert _REQUIRED_TEMPLATE_FILES[name] <= archived_rel_paths
            assert not any("__pycache__" in path for path in names)


@pytest.mark.unittest
def test_distribution_metadata_keeps_template_assets_declared():
    setup_text = _read_text(_REPO_ROOT / "setup.py")
    manifest_text = _read_text(_REPO_ROOT / "MANIFEST.in")

    assert "from tools.package_templates import package_templates" in setup_text
    assert "package_templates(" in setup_text
    assert "package_data" in setup_text
    assert "*.zip" in setup_text
    assert "*.json" in setup_text
    assert "recursive-include pyfcstm/template *.zip *.json" in manifest_text


@pytest.mark.unittest
def test_extracted_builtin_templates_preserve_source_structure_contract():
    with TemporaryDirectory() as td:
        for name in _repository_template_names():
            extracted_dir = Path(extract_template(name, td))
            assert extracted_dir.name == get_template_info(name)["root_dir"]
            files = {item.name for item in extracted_dir.iterdir() if item.is_file()}
            assert _REQUIRED_TEMPLATE_FILES[name] <= files

            config = yaml.safe_load(_read_text(extracted_dir / "config.yaml"))
            assert not (set(config) - _CONFIG_TOP_LEVEL_KEYS)
            spec = _ignore_spec(config)
            for maintainer_file in _MAINTAINER_ONLY_FILES:
                assert spec.match_file(maintainer_file)


def _zip_payload(output_dir, template_name, rel_path):
    with zipfile.ZipFile(
        str(output_dir / "{name}.zip".format(name=template_name)), "r"
    ) as zf:
        info = zf.getinfo("{name}/{rel}".format(name=template_name, rel=rel_path))
        payload = zf.read(info)
    return info, payload


@pytest.mark.unittest
def test_cpp_templates_reuse_c_core_as_packaged_file_payloads():
    with TemporaryDirectory() as td:
        output_dir = Path(td)
        package_templates(str(_TEMPLATES_DIR), str(output_dir), verbose=False)

        for template_name, source_template in [("cpp", "c"), ("cpp_poll", "c_poll")]:
            for rel_path in ["machine.c.j2", "machine.h.j2"]:
                info, payload = _zip_payload(output_dir, template_name, rel_path)
                assert stat.S_IFMT(info.external_attr >> 16) != stat.S_IFLNK
                assert (
                    payload
                    == (_TEMPLATES_DIR / source_template / rel_path).read_bytes()
                )
                assert payload.strip() != (
                    "../{source}/{rel}".format(source=source_template, rel=rel_path)
                ).encode("utf-8")


@pytest.mark.unittest
def test_cpp_template_packaging_accepts_symlink_when_realpath_does_not_resolve(
    monkeypatch,
):
    src_file = _TEMPLATES_DIR / "cpp" / "machine.c.j2"
    target_file = _TEMPLATES_DIR / "c" / "machine.c.j2"
    realpath = os.path.realpath

    def unresolved_realpath(path):
        if os.path.abspath(path) == os.path.abspath(str(src_file)):
            return os.path.abspath(path)
        return realpath(path)

    monkeypatch.setattr(os.path, "realpath", unresolved_realpath)

    assert _resolve_archive_source(
        str(_TEMPLATES_DIR / "cpp"),
        str(src_file),
        "cpp",
        "machine.c.j2",
    ) == str(target_file)


@pytest.mark.unittest
def test_cpp_template_packaging_resolves_windows_symlink_text_stubs():
    with TemporaryDirectory() as source_td, TemporaryDirectory() as output_td:
        source_root = Path(source_td) / "templates"
        output_dir = Path(output_td)
        for name in ["c", "c_poll", "cpp", "cpp_poll"]:
            src_dir = _TEMPLATES_DIR / name
            dst_dir = source_root / name
            dst_dir.mkdir(parents=True)
            for item in src_dir.iterdir():
                if item.is_file() or item.is_symlink():
                    if item.is_symlink():
                        target = Path(os.readlink(str(item))).as_posix()
                        (dst_dir / item.name).write_text(
                            target + "\n", encoding="utf-8"
                        )
                    else:
                        (dst_dir / item.name).write_bytes(item.read_bytes())

        package_templates(str(source_root), str(output_dir), verbose=False)

        _, cpp_c_payload = _zip_payload(output_dir, "cpp", "machine.c.j2")
        _, cpp_h_payload = _zip_payload(output_dir, "cpp", "machine.h.j2")
        _, cpp_poll_c_payload = _zip_payload(output_dir, "cpp_poll", "machine.c.j2")
        _, cpp_poll_h_payload = _zip_payload(output_dir, "cpp_poll", "machine.h.j2")
        assert cpp_c_payload == (source_root / "c" / "machine.c.j2").read_bytes()
        assert cpp_h_payload == (source_root / "c" / "machine.h.j2").read_bytes()
        assert (
            cpp_poll_c_payload == (source_root / "c_poll" / "machine.c.j2").read_bytes()
        )
        assert (
            cpp_poll_h_payload == (source_root / "c_poll" / "machine.h.j2").read_bytes()
        )


@pytest.mark.unittest
def test_cpp_template_packaging_rejects_unexpected_windows_symlink_text_stub():
    with TemporaryDirectory() as source_td, TemporaryDirectory() as output_td:
        source_root = Path(source_td) / "templates"
        output_dir = Path(output_td)
        for name in ["c", "c_poll", "cpp", "cpp_poll"]:
            src_dir = _TEMPLATES_DIR / name
            dst_dir = source_root / name
            dst_dir.mkdir(parents=True)
            for item in src_dir.iterdir():
                if item.is_file() or item.is_symlink():
                    if item.is_symlink():
                        target = Path(os.readlink(str(item))).as_posix()
                        (dst_dir / item.name).write_text(
                            target + "\n", encoding="utf-8"
                        )
                    else:
                        (dst_dir / item.name).write_bytes(item.read_bytes())

        (source_root / "cpp" / "machine.c.j2").write_text(
            "../c_poll/machine.c.j2", encoding="utf-8"
        )

        with pytest.raises(ValueError, match="expected checkout stub"):
            package_templates(str(source_root), str(output_dir), verbose=False)


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
    python_renderer = StateMachineCodeRenderer(str(_TEMPLATES_DIR / "python"))
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
        renderer = StateMachineCodeRenderer(str(_TEMPLATES_DIR / name))
        assert c_helper_names <= (set(renderer.env.filters) | set(renderer.env.globals))
        assert "c_public_identifier_reserved" in renderer.env.tests
