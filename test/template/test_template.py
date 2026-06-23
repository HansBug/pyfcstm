import os.path
import subprocess
import sys

import pytest
from hbutils.system import TemporaryDirectory

from pyfcstm.template import (
    list_templates,
    has_template,
    get_template_info,
    extract_template,
)


@pytest.mark.unittest
class TestBuiltinTemplateModule:
    def test_list_templates(self):
        templates = list_templates()
        assert "c" in templates
        assert "c_poll" in templates
        assert "cpp" in templates
        assert "cpp_poll" in templates
        assert "python" in templates

    def test_has_template(self):
        assert has_template("c") is True
        assert has_template("c_poll") is True
        assert has_template("cpp") is True
        assert has_template("cpp_poll") is True
        assert has_template("python") is True
        assert has_template("not_exists") is False

    def test_get_template_info(self):
        info = get_template_info("c")
        assert info["name"] == "c"
        assert info["archive"] == "c.zip"
        assert info["language"] == "c"

        info = get_template_info("c_poll")
        assert info["name"] == "c_poll"
        assert info["archive"] == "c_poll.zip"
        assert info["language"] == "c"

        info = get_template_info("cpp")
        assert info["name"] == "cpp"
        assert info["archive"] == "cpp.zip"
        assert info["language"] == "cpp"
        assert info["experimental"] is True

        info = get_template_info("cpp_poll")
        assert info["name"] == "cpp_poll"
        assert info["archive"] == "cpp_poll.zip"
        assert info["language"] == "cpp"
        assert info["experimental"] is True

        info = get_template_info("python")
        assert info["name"] == "python"
        assert info["archive"] == "python.zip"
        assert info["language"] == "python"

    def test_extract_template(self):
        with TemporaryDirectory() as td:
            template_dir = extract_template("c", td)
            assert os.path.isdir(template_dir)
            assert os.path.isfile(os.path.join(template_dir, "config.yaml"))
            assert os.path.isfile(os.path.join(template_dir, "README.md"))
            assert os.path.isfile(os.path.join(template_dir, "README_zh.md"))
            assert os.path.isfile(os.path.join(template_dir, "README.md.j2"))
            assert os.path.isfile(os.path.join(template_dir, "README_zh.md.j2"))
            assert os.path.isfile(os.path.join(template_dir, "machine.h.j2"))
            assert os.path.isfile(os.path.join(template_dir, "machine.c.j2"))
            assert not os.path.exists(os.path.join(template_dir, "Makefile.j2"))
            assert not os.path.exists(os.path.join(template_dir, "CMakeLists.txt.j2"))
            assert not os.path.exists(os.path.join(template_dir, "__init__.py.j2"))

        with TemporaryDirectory() as td:
            template_dir = extract_template("c_poll", td)
            assert os.path.isdir(template_dir)
            assert os.path.isfile(os.path.join(template_dir, "config.yaml"))
            assert os.path.isfile(os.path.join(template_dir, "README.md"))
            assert os.path.isfile(os.path.join(template_dir, "README_zh.md"))
            assert os.path.isfile(os.path.join(template_dir, "README.md.j2"))
            assert os.path.isfile(os.path.join(template_dir, "README_zh.md.j2"))
            assert os.path.isfile(os.path.join(template_dir, "machine.h.j2"))
            assert os.path.isfile(os.path.join(template_dir, "machine.c.j2"))
            assert not os.path.exists(os.path.join(template_dir, "Makefile.j2"))
            assert not os.path.exists(os.path.join(template_dir, "CMakeLists.txt.j2"))
            assert not os.path.exists(os.path.join(template_dir, "__init__.py.j2"))

        with TemporaryDirectory() as td:
            template_dir = extract_template("cpp", td)
            assert os.path.isdir(template_dir)
            assert os.path.isfile(os.path.join(template_dir, "config.yaml"))
            assert os.path.isfile(os.path.join(template_dir, "README.md"))
            assert os.path.isfile(os.path.join(template_dir, "README_zh.md"))
            assert os.path.isfile(os.path.join(template_dir, "README.md.j2"))
            assert os.path.isfile(os.path.join(template_dir, "README_zh.md.j2"))
            assert os.path.isfile(os.path.join(template_dir, "machine.h.j2"))
            assert os.path.isfile(os.path.join(template_dir, "machine.c.j2"))
            assert os.path.isfile(os.path.join(template_dir, "machine.hpp.j2"))
            assert os.path.isfile(os.path.join(template_dir, "machine.cpp.j2"))
            assert not os.path.exists(os.path.join(template_dir, "Makefile.j2"))
            assert not os.path.exists(os.path.join(template_dir, "CMakeLists.txt.j2"))
            assert not os.path.exists(os.path.join(template_dir, "__init__.py.j2"))

        with TemporaryDirectory() as td:
            template_dir = extract_template("cpp_poll", td)
            assert os.path.isdir(template_dir)
            assert os.path.isfile(os.path.join(template_dir, "config.yaml"))
            assert os.path.isfile(os.path.join(template_dir, "README.md"))
            assert os.path.isfile(os.path.join(template_dir, "README_zh.md"))
            assert os.path.isfile(os.path.join(template_dir, "README.md.j2"))
            assert os.path.isfile(os.path.join(template_dir, "README_zh.md.j2"))
            assert os.path.isfile(os.path.join(template_dir, "machine.h.j2"))
            assert os.path.isfile(os.path.join(template_dir, "machine.c.j2"))
            assert os.path.isfile(os.path.join(template_dir, "machine.hpp.j2"))
            assert os.path.isfile(os.path.join(template_dir, "machine.cpp.j2"))
            assert not os.path.exists(os.path.join(template_dir, "Makefile.j2"))
            assert not os.path.exists(os.path.join(template_dir, "CMakeLists.txt.j2"))
            assert not os.path.exists(os.path.join(template_dir, "__init__.py.j2"))

        with TemporaryDirectory() as td:
            template_dir = extract_template("python", td)
            assert os.path.isdir(template_dir)
            assert os.path.isfile(os.path.join(template_dir, "config.yaml"))
            assert os.path.isfile(os.path.join(template_dir, "README.md"))
            assert os.path.isfile(os.path.join(template_dir, "README_zh.md"))
            assert os.path.isfile(os.path.join(template_dir, "README.md.j2"))
            assert os.path.isfile(os.path.join(template_dir, "README_zh.md.j2"))
            assert os.path.isfile(os.path.join(template_dir, "machine.py.j2"))
            assert not os.path.exists(os.path.join(template_dir, "__init__.py.j2"))

    def test_extract_template_not_found(self):
        with TemporaryDirectory() as td:
            with pytest.raises(LookupError):
                extract_template("not_exists", td)

    def test_source_install_extracts_builtin_template_outside_checkout(self):
        with TemporaryDirectory() as build_root:
            install_dir = os.path.join(build_root, "install")
            command = [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--quiet",
                "--no-deps",
                "--target",
                install_dir,
                ".",
            ]
            subprocess.run(
                command,
                cwd=os.path.abspath(
                    os.path.join(os.path.dirname(__file__), "..", "..")
                ),
                check=True,
            )

            probe_code = (
                "import os\n"
                "from tempfile import TemporaryDirectory\n"
                "from pyfcstm.template import extract_template\n"
                "with TemporaryDirectory() as td:\n"
                "    path = extract_template('python', td)\n"
                "    assert os.path.basename(path) == 'python', path\n"
                "    assert os.path.isfile(os.path.join(path, 'config.yaml')), path\n"
                "    assert os.path.isfile(os.path.join(path, 'machine.py.j2')), path\n"
                "    print('ok')\n"
            )
            probe = subprocess.run(
                [sys.executable, "-c", probe_code],
                cwd=build_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env={
                    **os.environ,
                    "PYTHONPATH": install_dir,
                },
            )
            assert probe.stdout.strip() == "ok"
