"""Regression tests for generated API top-level package filtering."""

from pathlib import Path

import pytest


@pytest.mark.unittest
def test_private_selfcheck_package_is_not_in_public_top_index(tmp_path):
    """The internal self-check package stays out of the public API map."""
    from auto_rst_top_index import generate_rst_index

    source = tmp_path / "pyfcstm"
    source.mkdir()
    (source / "__init__.py").write_text("", encoding="utf-8")
    (source / "_selfcheck").mkdir()
    (source / "_selfcheck" / "__init__.py").write_text("", encoding="utf-8")
    (source / "_bootstrap.py").write_text("", encoding="utf-8")
    output = tmp_path / "api_doc_en.rst"
    generate_rst_index(str(source), str(output), "API Documentation")
    text = Path(output).read_text(encoding="utf-8")
    assert "api_doc/_selfcheck" not in text
    assert "api_doc/_bootstrap" in text
