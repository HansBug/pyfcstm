"""Contextual syntax highlighting does not reserve ordinary identifiers."""

import pytest
from pygments import lex
from pygments.token import Keyword, Name, Comment, String

from pyfcstm.highlight import FcstmLexer

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('source,word,token', [
    ('region Motor {', 'region', Keyword.Declaration),
    ('region\nMotor\n{', 'region', Keyword.Declaration),
    ('active("Root.Motor.Running")', 'active', Name.Builtin),
    ("active ('Ready')", 'active', Name.Builtin),
    ('def int region = 0;', 'region', Name),
    ('def int active = 0;', 'active', Name),
    ('state region;', 'region', Name),
    ('state active {}', 'active', Name),
    ('enter active {}', 'active', Name),
    ('event region;', 'region', Name),
    ('region -> active :: region;', 'active', Name),
    ('region -> active :: region;', 'region', Name),
    ('import "x" as region;', 'region', Name),
    ('import "x" as Alias { var active -> region; }', 'region', Name.Variable),
])
def test_contextual_syntax_tokens(source, word, token):
    matches = [kind for kind, text in lex(source, FcstmLexer()) if text == word]
    assert matches
    assert all(kind == token for kind in matches)


def test_contextual_words_inside_comments_and_strings():
    tokens = list(lex('/* region R {} active("A") */ "region active"', FcstmLexer()))
    assert all(kind in Comment or kind in String or text.isspace() for kind, text in tokens)
