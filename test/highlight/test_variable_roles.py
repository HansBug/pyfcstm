"""Syntax highlighting for reserved variable-role keywords."""

import pytest
from pygments import lex
from pygments.token import Keyword, Name
from pyfcstm.highlight.pygments_lexer import FcstmLexer


@pytest.mark.unittest
@pytest.mark.parametrize(
    "keyword", ["control", "input", "param", "output"]
)
def test_variable_role_keywords(keyword):
    assert list(lex(keyword, FcstmLexer()))[0] == (Keyword.Declaration, keyword)


@pytest.mark.unittest
@pytest.mark.parametrize("spelling", ["var", "def"])
def test_import_mapping_keyword_and_template(spelling):
    source = 'state Root { import "./child.fcstm" as Child { %s sensor_* -> host_$1; } }' % spelling
    tokens = list(lex(source, FcstmLexer()))
    assert (Keyword.Declaration, spelling) in tokens
    assert FcstmLexer.analyse_text(source) > 0


@pytest.mark.unittest
@pytest.mark.parametrize("name", ["dynamic", "static"])
def test_removed_input_modifiers_highlight_as_identifiers(name):
    assert list(lex(name, FcstmLexer()))[0] == (Name, name)
