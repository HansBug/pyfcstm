import os.path

import pytest
from hbutils.system import TemporaryDirectory

from pyfcstm.template import list_templates, has_template, get_template_info, extract_template


@pytest.mark.unittest
class TestBuiltinTemplateModule:
    def test_list_templates(self):
        templates = list_templates()
        assert "python" in templates

    def test_has_template(self):
        assert has_template("python") is True
        assert has_template("not_exists") is False

    def test_get_template_info(self):
        info = get_template_info("python")
        assert info["name"] == "python"
        assert info["archive"] == "python.zip"
        assert info["language"] == "python"

    def test_extract_template(self):
        with TemporaryDirectory() as td:
            template_dir = extract_template("python", td)
            assert os.path.isdir(template_dir)
            assert os.path.isfile(os.path.join(template_dir, "config.yaml"))
            assert os.path.isfile(os.path.join(template_dir, "machine.py.j2"))
            assert not os.path.exists(os.path.join(template_dir, "__init__.py.j2"))

    def test_extract_template_not_found(self):
        with TemporaryDirectory() as td:
            with pytest.raises(LookupError):
                extract_template("not_exists", td)
