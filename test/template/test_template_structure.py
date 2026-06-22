"""Regression checks for built-in template structure and generated contracts."""

import ast
import json
import re
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
from tools.package_templates import package_templates


_REPO_ROOT = Path(__file__).resolve().parents[2]
_TEMPLATES_DIR = _REPO_ROOT / "templates"
_PACKAGED_TEMPLATE_DIR = _REPO_ROOT / "pyfcstm" / "template"
_CURRENT_TEMPLATE_NAMES = ("c", "c_poll", "python")
_TEMPLATE_LANGUAGE_VOCABULARY = {"c", "python", "java", "js", "rust", "ruby", "go"}
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
    with TemporaryDirectory() as td:
        output_root = Path(td)
        yield _render_template_directories(
            {name: _TEMPLATES_DIR / name for name in _CURRENT_TEMPLATE_NAMES},
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

    for name in ["c", "c_poll"]:
        header_source = _read_text(rendered_templates[name] / "machine.h")
        runtime_source = _read_text(rendered_templates[name] / "machine.c")
        _assert_banner_terms(
            _first_c_comment_block(header_source),
            template_name=name,
            root_name="Control",
        )
        _assert_banner_terms(
            _first_c_comment_block(runtime_source),
            template_name=name,
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
    for expected in ["python", "c", "c_poll", "java", "js", "rust", "ruby", "go"]:
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
