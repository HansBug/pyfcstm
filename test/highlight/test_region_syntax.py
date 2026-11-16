"""Reserved words keep their syntax categories in every identifier position."""

import pytest
from pygments import lex
from pygments.token import Keyword, Name, Comment, String, Operator

from pyfcstm.highlight import FcstmLexer

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('source,word,token', [
    ('region Motor {', 'region', Keyword.Declaration),
    ('region\nMotor\n{', 'region', Keyword.Declaration),
    ('active("Root.Motor.Running")', 'active', Name.Builtin),
    ("active ('Ready')", 'active', Name.Builtin),
    ('def int region = 0;', 'region', Keyword.Declaration),
    ('def int active = 0;', 'active', Name.Builtin),
    ('state region;', 'region', Keyword.Declaration),
    ('state active {}', 'active', Name.Builtin),
    ('enter active {}', 'active', Name.Builtin),
    ('event region;', 'region', Keyword.Declaration),
    ('region -> active :: region;', 'active', Name.Builtin),
    ('region -> active :: region;', 'region', Keyword.Declaration),
    ('import "x" as region;', 'region', Keyword.Declaration),
    ('import "x" as Alias { var active -> region; }', 'region', Keyword.Declaration),
])
def test_reserved_syntax_tokens(source, word, token):
    matches = [kind for kind, text in lex(source, FcstmLexer()) if text == word]
    assert matches
    assert all(kind == token for kind in matches)


def test_reserved_words_inside_comments_and_strings():
    tokens = list(lex('/* region R {} active("A") */ "region active"', FcstmLexer()))
    assert all(kind in Comment or kind in String or text.isspace() for kind, text in tokens)


@pytest.mark.parametrize('word,token', [
    ('state', Keyword.Declaration), ('enter', Keyword.Reserved),
    ('float', Keyword.Type), ('and', Operator.Word),
    ('True', Keyword.Constant), ('sin', Name.Builtin),
])
@pytest.mark.parametrize('source', [
    'import "x" as %s;',
    'import "x" as Child { var %s -> target; }',
    'import "x" as Child { var value -> %s; }',
    'import "x" as Child { event ready -> /Root.%s; }',
])
def test_import_keywords_keep_their_categories(word, token, source):
    matches = [kind for kind, text in lex(source % word, FcstmLexer()) if text == word]
    assert matches == [token]


@pytest.mark.parametrize('word', ['Active', 'Region', 'active_flag', 'region_count'])
def test_keyword_prefixes_are_ordinary_names(word):
    assert list(lex(word, FcstmLexer()))[0] == (Name, word)


def test_import_template_prefixes_remain_one_token():
    tokens = list(lex('import "x" as Child { var active* -> region$1; }', FcstmLexer()))
    assert (Name.Variable, 'active*') in tokens
    assert (Name.Variable, 'region$1') in tokens
