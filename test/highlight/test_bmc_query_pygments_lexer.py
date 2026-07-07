"""Tests for the FCSTM BMC Query Pygments lexer."""

import sys
import types
from textwrap import dedent

import pytest
from pygments.token import Keyword, Name, Number, Operator, String

from pyfcstm.highlight import FcstmBmcQueryLexer


QUERY_SAMPLE = dedent(
    """\
    init state("Root.System.A") havoc { x } where x >= 0 and active("Root.System.A");

    assume always: var("x") <= 1000;
    assume at 0: x == var("x");
    assume event("Root.System.A.Tick", 0..3) != false;
    assume events cardinality at_most_one {
        "Root.System.A.Tick",
        "Root.System.A.Reset"
    };

    check response <= 10:
        trigger event("Root.System.A.Tick", current) && active("Root.System.A")
        -> within 3 active("Root.Recovering");
    """
)

COVER_SAMPLE = dedent(
    """\
    init cold;

    check cover <= 6:
        case("Root.System.A::transition::Root.System.B::1");
    """
)


def _token_pairs(source):
    return [
        (token_type, text)
        for token_type, text in FcstmBmcQueryLexer().get_tokens(source)
        if text.strip()
    ]


@pytest.mark.unittest
def test_bmc_query_lexer_metadata_and_registry_aliases():
    """Pygments metadata identifies ``*.fbmcq`` query files."""
    assert FcstmBmcQueryLexer.name == "FCSTM BMC Query"
    assert FcstmBmcQueryLexer.aliases == ["fbmcq", "fcstm-bmc-query"]
    assert FcstmBmcQueryLexer.filenames == ["*.fbmcq"]
    assert FcstmBmcQueryLexer.mimetypes == ["text/x-fcstm-bmc-query"]
    setup_text = open("setup.py", encoding="utf-8").read()
    assert "fbmcq = pyfcstm.highlight.bmc_query_lexer:FcstmBmcQueryLexer" in setup_text


@pytest.mark.unittest
def test_bmc_query_lexer_highlights_top_level_query_tokens():
    """Representative query clauses receive stable Pygments token classes."""
    tokens = _token_pairs(QUERY_SAMPLE)

    assert (Keyword.Declaration, "init") in tokens
    assert (Keyword.Declaration, "state") in tokens
    assert (Keyword.Reserved, "havoc") in tokens
    assert (Keyword.Reserved, "where") in tokens
    assert (Keyword.Declaration, "assume") in tokens
    assert (Keyword.Reserved, "always") in tokens
    assert (Keyword.Reserved, "at") in tokens
    assert (Name.Builtin, "event") in tokens
    assert (Keyword.Declaration, "events") in tokens
    assert (Keyword.Reserved, "cardinality") in tokens
    assert (Name.Builtin, "at_most_one") in tokens
    assert (Keyword.Declaration, "check") in tokens
    assert (Keyword.Reserved, "response") in tokens
    assert (Keyword.Reserved, "trigger") in tokens
    assert (Keyword.Reserved, "within") in tokens
    assert (String.Double, '"Root.System.A"') in tokens
    assert (Number.Integer, "1000") in tokens
    assert (Operator.Word, "and") in tokens
    assert (Operator, "&&") in tokens
    assert (Operator, "->") in tokens
    assert (Operator, "..") in tokens


@pytest.mark.unittest
def test_bmc_query_lexer_highlights_cover_case_tokens():
    """Cover queries highlight ``cover`` and ``case`` without FCSTM state syntax."""
    tokens = _token_pairs(COVER_SAMPLE)

    assert (Keyword.Reserved, "cold") in tokens
    assert (Keyword.Reserved, "cover") in tokens
    assert (Name.Builtin, "case") in tokens
    assert (String.Double, '"Root.System.A::transition::Root.System.B::1"') in tokens


@pytest.mark.unittest
def test_bmc_query_lexer_disambiguates_dual_role_keywords():
    """Dual-role query words stay stable in clause and atom-call contexts."""
    tokens = _token_pairs(
        dedent(
            """\
            init terminated;

            assume event("Root.Tick", current) != false;
            assume events cardinality any {
                "Root.Tick"
            };

            check reach <= 2: terminated(current);
            """
        )
    )

    assert (Keyword.Reserved, "terminated") in tokens
    assert (Name.Builtin, "terminated") in tokens
    assert (Name.Builtin, "event") in tokens
    assert (Keyword.Declaration, "events") in tokens


@pytest.mark.unittest
def test_bmc_query_lexer_highlights_full_expression_surface():
    """The lexer covers FCSTM-compatible expression operators used by queries."""
    source = dedent(
        """\
        init cold;
        assume always: ((~flags & 0xFF) == 0) or (cycle << 1) >= +2 and (-x <= 3.5e-1);
        assume at 0: .5 + 1. + 1e2 >= var("x");
        check reach <= 2: sin(pi) >= 0 xor false iff true;
        """
    )

    tokens = _token_pairs(source)

    for expected in ["~", "&", "<<", "+", "-", "<=", ">=", "xor", "iff"]:
        assert any(token_text == expected for _, token_text in tokens), expected
    assert (Number.Hex, "0xFF") in tokens
    assert (Number.Float, "3.5e-1") in tokens
    assert (Number.Float, ".5") in tokens
    assert (Number.Float, "1.") in tokens
    assert (Number.Float, "1e2") in tokens
    assert (Name.Builtin, "cycle") in tokens
    assert (Name.Builtin, "sin") in tokens
    assert (Name.Constant, "pi") in tokens
    assert (Keyword.Constant, "false") in tokens
    assert (Keyword.Constant, "true") in tokens


@pytest.mark.unittest
def test_bmc_query_analyse_text_is_string_based(monkeypatch):
    """Language detection must not import or call the parser layer."""
    sentinel = types.ModuleType("pyfcstm.bmc.parse")

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("analyse_text must not call parse_bmc_query")

    sentinel.parse_bmc_query = fail_if_called
    monkeypatch.setitem(sys.modules, "pyfcstm.bmc.parse", sentinel)

    score = FcstmBmcQueryLexer.analyse_text(QUERY_SAMPLE)

    assert 0.0 <= score <= 1.0
    assert score >= 0.80
    assert sys.modules["pyfcstm.bmc.parse"] is sentinel
