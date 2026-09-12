"""Syntax highlighting for reserved variable-role keywords."""

import pytest
from pygments import lex
from pygments.token import Keyword
from pyfcstm.highlight.pygments_lexer import FcstmLexer


@pytest.mark.unittest
@pytest.mark.parametrize(
    "keyword", ["control", "input", "dynamic", "static", "param", "output"]
)
def test_variable_role_keywords(keyword):
    assert list(lex(keyword, FcstmLexer()))[0] == (Keyword.Declaration, keyword)
