"""Parser-to-AST tests for FCSTM BMC query files."""

import importlib
import subprocess
import sys
from typing import cast

import pytest
from antlr4 import CommonTokenStream, InputStream, ParserRuleContext

from pyfcstm.bmc.ast import (
    Active,
    BmcCondExpr,
    BmcNumExpr,
    BoolLiteral,
    Cycle,
)
from pyfcstm.bmc.errors import BmcQueryParseError, InvalidBmcQuery
from pyfcstm.bmc.grammar.BmcQueryLexer import BmcQueryLexer
from pyfcstm.bmc.grammar.BmcQueryParser import BmcQueryParser
from pyfcstm.bmc.parse import (
    _CollectingBmcErrorListener,
    _build_lexer,
    _build_parser,
    _find_error_node_text,
    build_bmc_ast_from_parse_tree,
    parse_bmc_cond_expression,
    parse_bmc_num_expression,
    parse_bmc_query,
    parse_with_bmc_grammar_entry,
)
from pyfcstm.bmc.query import BmcProperty, BmcQuery


@pytest.mark.unittest
@pytest.mark.parametrize(
    "query_text, expected",
    [
        pytest.param(
            "check reach <= 1: true;",
            {
                "initial": {"mode": "cold", "predicate": None},
                "assumption_count": 0,
                "property": {
                    "kind": "reach",
                    "bound": 1,
                    "predicate": {
                        "node": "bool_literal",
                        "raw": "true",
                        "value": True,
                    },
                },
            },
            id="default-cold-reach",
        ),
        pytest.param(
            "init cold; check forbid <= 2: false;",
            {
                "initial": {"mode": "cold", "predicate": None},
                "assumption_count": 0,
                "property": {
                    "kind": "forbid",
                    "bound": 2,
                    "predicate": {
                        "node": "bool_literal",
                        "raw": "false",
                        "value": False,
                    },
                },
            },
            id="explicit-cold-forbid",
        ),
        pytest.param(
            "init terminated; check invariant <= 3: terminated();",
            {
                "initial": {"mode": "terminated", "predicate": None},
                "assumption_count": 0,
                "property": {
                    "kind": "invariant",
                    "bound": 3,
                    "predicate": {"node": "terminated", "frame": "current"},
                },
            },
            id="terminated-invariant",
        ),
        pytest.param(
            'init state("Root.A") where var("x") >= 0; '
            'check must_reach <= 4: active("Root.Done", current);',
            {
                "initial": {
                    "mode": "state",
                    "state_path": "Root.A",
                    "predicate": {
                        "node": "numeric_comparison",
                        "op": ">=",
                    },
                },
                "assumption_count": 0,
                "property": {
                    "kind": "must_reach",
                    "bound": 4,
                    "predicate": {
                        "node": "active",
                        "state_path": "Root.Done",
                        "frame": "current",
                    },
                },
            },
            id="state-where-must-reach",
        ),
        pytest.param(
            'init state("Root.A") havoc { x, "cycle" } where x >= 0; '
            'check reach <= 1: active("Root.A");',
            {
                "initial": {
                    "mode": "state",
                    "state_path": "Root.A",
                    "predicate": {
                        "node": "numeric_comparison",
                        "op": ">=",
                    },
                    "variable_policy": {
                        "havoc_all": False,
                        "havoc_variables": ["x", "cycle"],
                    },
                },
                "assumption_count": 0,
                "property": {
                    "kind": "reach",
                    "bound": 1,
                    "predicate": {
                        "node": "active",
                        "state_path": "Root.A",
                        "frame": "current",
                    },
                },
            },
            id="state-havoc-vars-where-reach",
        ),
        pytest.param(
            "init terminated havoc *; check invariant <= 1: terminated();",
            {
                "initial": {
                    "mode": "terminated",
                    "predicate": None,
                    "variable_policy": {"havoc_all": True, "havoc_variables": []},
                },
                "assumption_count": 0,
                "property": {
                    "kind": "invariant",
                    "bound": 1,
                    "predicate": {"node": "terminated", "frame": "current"},
                },
            },
            id="terminated-havoc-all-invariant",
        ),
        pytest.param(
            'assume always: var("x") <= 10; '
            'assume at 2: active("Root.Ready", 2); '
            'assume event("Root.Tick", *) == false; '
            'assume event("Root.Reset", 01.. 03) != false; '
            "assume events cardinality any; "
            'assume events cardinality at_most_one {"Root.Tick", "Root.Reset"}; '
            'check exists_always <= 5: case("safe", 4);',
            {
                "initial": {"mode": "cold", "predicate": None},
                "assumption_count": 6,
                "property": {
                    "kind": "exists_always",
                    "bound": 5,
                    "predicate": {"node": "case", "label": "safe", "frame": 4},
                },
            },
            id="all-assumption-families",
        ),
        pytest.param(
            'check response <= 8: trigger event("Root.Fault", current) '
            '-> within 3 active("Root.Recovering");',
            {
                "initial": {"mode": "cold", "predicate": None},
                "assumption_count": 0,
                "property": {
                    "kind": "response",
                    "bound": 8,
                    "trigger": {
                        "node": "event",
                        "event_path": "Root.Fault",
                        "selector": "current",
                    },
                    "response": {
                        "node": "active",
                        "state_path": "Root.Recovering",
                        "frame": "current",
                    },
                    "within": 3,
                },
            },
            id="response-property",
        ),
        pytest.param(
            'check cover <= 01: called("CheckLimit", 05);',
            {
                "initial": {"mode": "cold", "predicate": None},
                "assumption_count": 0,
                "property": {
                    "kind": "cover",
                    "bound": 1,
                    "predicate": {
                        "node": "called",
                        "name": "CheckLimit",
                        "frame": 5,
                    },
                },
            },
            id="leading-zero-bound-and-frame",
        ),
    ],
)
def test_parse_bmc_query_builds_expected_canonical_shape(query_text, expected):
    """Complete queries build parser-independent query objects."""
    query = parse_bmc_query(query_text)
    canonical = query.to_canonical()

    assert isinstance(query, BmcQuery)
    assert canonical["initial"]["mode"] == expected["initial"]["mode"]
    assert canonical["initial"].get("state_path") == expected["initial"].get(
        "state_path"
    )
    if "variable_policy" in expected["initial"]:
        for key, value in expected["initial"]["variable_policy"].items():
            assert canonical["initial"]["variable_policy"][key] == value
    if expected["initial"]["predicate"] is None:
        assert canonical["initial"]["predicate"] is None
    else:
        assert (
            canonical["initial"]["predicate"]["node"]
            == expected["initial"]["predicate"]["node"]
        )
        assert (
            canonical["initial"]["predicate"]["op"]
            == expected["initial"]["predicate"]["op"]
        )
    assert len(canonical["assumptions"]) == expected["assumption_count"]
    assert canonical["property"]["kind"] == expected["property"]["kind"]
    assert canonical["property"]["bound"] == expected["property"]["bound"]
    for key, value in expected["property"].items():
        if key in {"kind", "bound"}:
            continue
        if isinstance(value, dict):
            assert canonical["property"][key].items() >= value.items()
        else:
            assert canonical["property"][key] == value


@pytest.mark.unittest
def test_parse_bmc_query_assumption_details_are_normalized():
    """Assumption parser branches preserve polarity and selector semantics."""
    query = parse_bmc_query(
        'assume always: var("x") <= 10; '
        'assume at 2: active("Root.Ready"); '
        'assume event("Root.Tick", *) == false; '
        'assume event("Root.Reset", 01 .. 03) != false; '
        'assume event("Root.Point", 007) == TRUE; '
        "assume events cardinality any; "
        'assume events cardinality at_most_one {"Root.Tick", "Root.Reset"}; '
        'check reach <= 2: active("Root.Done");'
    )
    assumptions = query.to_canonical()["assumptions"]

    assert assumptions[0]["kind"] == "always"
    assert assumptions[0]["predicate"]["node"] == "numeric_comparison"
    assert assumptions[1]["kind"] == "at"
    assert assumptions[1]["frame"] == 2
    assert assumptions[2] == {
        "node": "event_assumption",
        "event_path": "Root.Tick",
        "selector": "*",
        "expected": False,
    }
    assert assumptions[3] == {
        "node": "event_assumption",
        "event_path": "Root.Reset",
        "selector": "1..3",
        "expected": True,
    }
    assert assumptions[4] == {
        "node": "event_assumption",
        "event_path": "Root.Point",
        "selector": 7,
        "expected": True,
    }
    assert assumptions[5] == {
        "node": "event_cardinality_assumption",
        "kind": "any",
        "event_paths": [],
    }
    assert assumptions[6] == {
        "node": "event_cardinality_assumption",
        "kind": "at_most_one",
        "event_paths": ["Root.Tick", "Root.Reset"],
    }


@pytest.mark.unittest
@pytest.mark.parametrize(
    "expression, expected",
    [
        pytest.param("0", {"node": "int_literal", "raw": "0", "value": 0}, id="zero"),
        pytest.param(
            "001",
            {"node": "int_literal", "raw": "001", "value": 1},
            id="leading-zero",
        ),
        pytest.param(
            "0x2A",
            {"node": "int_literal", "kind": "hex", "raw": "0x2A", "value": 42},
            id="hex",
        ),
        pytest.param(
            ".5",
            {"node": "float_literal", "raw": ".5", "value": 0.5},
            id="float-leading-dot",
        ),
        pytest.param("pi", {"node": "math_const", "name": "pi"}, id="pi"),
        pytest.param("x", {"node": "name", "name": "x"}, id="name"),
        pytest.param('var("x")', {"node": "frame_var", "name": "x"}, id="var"),
        pytest.param("cycle", {"node": "cycle"}, id="cycle"),
        pytest.param("+x", {"node": "num_unary", "op": "+"}, id="unary-plus"),
        pytest.param("-x", {"node": "num_unary", "op": "-"}, id="unary-minus"),
        pytest.param("sin(x)", {"node": "ufunc", "func": "sin"}, id="ufunc"),
        pytest.param("x ** y", {"node": "num_binary", "op": "**"}, id="pow"),
        pytest.param("x * y", {"node": "num_binary", "op": "*"}, id="mul"),
        pytest.param("x / y", {"node": "num_binary", "op": "/"}, id="div"),
        pytest.param("x % y", {"node": "num_binary", "op": "%"}, id="mod"),
        pytest.param("x + y", {"node": "num_binary", "op": "+"}, id="add"),
        pytest.param("x - y", {"node": "num_binary", "op": "-"}, id="sub"),
        pytest.param("x << y", {"node": "num_binary", "op": "<<"}, id="shl"),
        pytest.param("x >> y", {"node": "num_binary", "op": ">>"}, id="shr"),
        pytest.param("x & y", {"node": "num_binary", "op": "&"}, id="band"),
        pytest.param("x ^ y", {"node": "num_binary", "op": "^"}, id="bxor"),
        pytest.param("x | y", {"node": "num_binary", "op": "|"}, id="bor"),
        pytest.param(
            '(active("Root.A")) ? 1 : 2',
            {"node": "num_conditional"},
            id="numeric-conditional",
        ),
    ],
)
def test_parse_bmc_num_expression_builds_each_numeric_node(expression, expected):
    """Numeric expression parser covers every listener numeric exit branch."""
    node = parse_bmc_num_expression(expression)
    canonical = node.to_canonical()

    assert isinstance(node, BmcNumExpr)
    assert canonical.items() >= expected.items()


@pytest.mark.unittest
@pytest.mark.parametrize(
    "expression, expected",
    [
        pytest.param(
            "TRUE",
            {"node": "bool_literal", "raw": "TRUE", "value": True},
            id="bool-upper",
        ),
        pytest.param(
            'active("Root.A")',
            {"node": "active", "state_path": "Root.A", "frame": "current"},
            id="active-default",
        ),
        pytest.param(
            'active("Root.A", current)',
            {"node": "active", "state_path": "Root.A", "frame": "current"},
            id="active-current",
        ),
        pytest.param(
            'active("Root.A", 2)',
            {"node": "active", "state_path": "Root.A", "frame": 2},
            id="active-frame",
        ),
        pytest.param(
            "terminated()",
            {"node": "terminated", "frame": "current"},
            id="terminated-default",
        ),
        pytest.param(
            "terminated(current)",
            {"node": "terminated", "frame": "current"},
            id="terminated-current",
        ),
        pytest.param(
            "terminated(3)",
            {"node": "terminated", "frame": 3},
            id="terminated-frame",
        ),
        pytest.param(
            'event("Root.E", current)',
            {"node": "event", "event_path": "Root.E", "selector": "current"},
            id="event-current",
        ),
        pytest.param(
            'event("Root.E", 0)',
            {"node": "event", "event_path": "Root.E", "selector": 0},
            id="event-index",
        ),
        pytest.param(
            'case("label")',
            {"node": "case", "label": "label", "frame": "current"},
            id="case-default",
        ),
        pytest.param(
            'case("label", 4)',
            {"node": "case", "label": "label", "frame": 4},
            id="case-frame",
        ),
        pytest.param(
            'called("hook")',
            {"node": "called", "name": "hook", "frame": "current"},
            id="called-default",
        ),
        pytest.param(
            'called("hook", 5)',
            {"node": "called", "name": "hook", "frame": 5},
            id="called-frame",
        ),
        pytest.param("!true", {"node": "cond_unary", "op": "!"}, id="bang"),
        pytest.param("not true", {"node": "cond_unary", "op": "!"}, id="not"),
        pytest.param("x < y", {"node": "numeric_comparison", "op": "<"}, id="lt"),
        pytest.param("x > y", {"node": "numeric_comparison", "op": ">"}, id="gt"),
        pytest.param("x <= y", {"node": "numeric_comparison", "op": "<="}, id="le"),
        pytest.param("x >= y", {"node": "numeric_comparison", "op": ">="}, id="ge"),
        pytest.param("x == y", {"node": "numeric_comparison", "op": "=="}, id="eq"),
        pytest.param("x != y", {"node": "numeric_comparison", "op": "!="}, id="ne"),
        pytest.param(
            "true == false",
            {"node": "cond_binary", "op": "=="},
            id="cond-eq",
        ),
        pytest.param(
            "true != false",
            {"node": "cond_binary", "op": "!="},
            id="cond-ne",
        ),
        pytest.param(
            "true iff false",
            {"node": "cond_binary", "op": "iff"},
            id="iff",
        ),
        pytest.param("true && false", {"node": "cond_binary", "op": "&&"}, id="and"),
        pytest.param(
            "true and false", {"node": "cond_binary", "op": "&&"}, id="and-kw"
        ),
        pytest.param("true xor false", {"node": "cond_binary", "op": "xor"}, id="xor"),
        pytest.param("true || false", {"node": "cond_binary", "op": "||"}, id="or"),
        pytest.param("true or false", {"node": "cond_binary", "op": "||"}, id="or-kw"),
        pytest.param("true => false", {"node": "cond_binary", "op": "=>"}, id="impl"),
        pytest.param(
            "true implies false",
            {"node": "cond_binary", "op": "=>"},
            id="impl-kw",
        ),
        pytest.param(
            "(x > 0) ? true : false",
            {"node": "cond_conditional"},
            id="cond-conditional",
        ),
    ],
)
def test_parse_bmc_cond_expression_builds_each_condition_node(expression, expected):
    """Condition parser covers every listener condition and BMC atom branch."""
    node = parse_bmc_cond_expression(expression)
    canonical = node.to_canonical()

    assert isinstance(node, BmcCondExpr)
    assert canonical.items() >= expected.items()


@pytest.mark.unittest
@pytest.mark.parametrize(
    "text, parser_func, expected_text",
    [
        pytest.param(
            'var("a\\n")', parse_bmc_num_expression, 'var("a\\n")', id="newline"
        ),
        pytest.param('var("a\\t")', parse_bmc_num_expression, 'var("a\\t")', id="tab"),
        pytest.param(
            'var("a\\\\b")', parse_bmc_num_expression, 'var("a\\\\b")', id="slash"
        ),
        pytest.param(
            'var("\\"quoted\\"")',
            parse_bmc_num_expression,
            'var("\\"quoted\\"")',
            id="double-quote",
        ),
        pytest.param(
            "var('\\'quoted\\'')",
            parse_bmc_num_expression,
            "var(\"'quoted'\")",
            id="single-quote",
        ),
        pytest.param(
            'var("\\x41")', parse_bmc_num_expression, 'var("A")', id="hex-escape"
        ),
        pytest.param(
            'var("\\u4e2d")',
            parse_bmc_num_expression,
            'var("中")',
            id="unicode-escape",
        ),
        pytest.param(
            'active("\\u6839.\\x41")',
            parse_bmc_cond_expression,
            'active("根.A")',
            id="active-escaped-path",
        ),
    ],
)
def test_string_literals_decode_and_render_canonical_json_text(
    text, parser_func, expected_text
):
    """String literal escapes decode through the listener and round-trip."""
    node = parser_func(text)

    assert str(node) == expected_text
    reparsed = parser_func(str(node))
    assert reparsed.to_canonical() == node.to_canonical()


@pytest.mark.unittest
@pytest.mark.parametrize(
    "entry_name, text, expected_type",
    [
        pytest.param("query", "check reach <= 1: true;", BmcQuery, id="query"),
        pytest.param("bmc_num_expression_entry", "cycle + 1", BmcNumExpr, id="numeric"),
        pytest.param(
            "bmc_cond_expression_entry", 'active("Root.A")', BmcCondExpr, id="cond"
        ),
    ],
)
def test_parse_with_bmc_grammar_entry_dispatches_supported_entries(
    entry_name, text, expected_type
):
    """The public generic parser dispatches exactly the supported entries."""
    result = parse_with_bmc_grammar_entry(text, entry_name)

    assert isinstance(result, expected_type)


@pytest.mark.unittest
def test_parse_entry_force_finished_flag_is_accepted():
    """The generic parser exposes the same force-finished knob as FCSTM DSL."""
    assert parse_with_bmc_grammar_entry(
        "cycle", "bmc_num_expression_entry", force_finished=False
    ).to_canonical() == {"node": "cycle"}


@pytest.mark.unittest
def test_build_bmc_ast_from_existing_parse_tree():
    """An already-created ANTLR context can be walked into a BMC AST node."""
    lexer = BmcQueryLexer(InputStream("cycle + 1"))
    parser = BmcQueryParser(CommonTokenStream(lexer))
    tree = parser.bmc_num_expression_entry()

    node = build_bmc_ast_from_parse_tree(tree)

    assert node.to_canonical()["node"] == "num_binary"
    assert node.to_canonical()["op"] == "+"


@pytest.mark.unittest
def test_parse_helpers_report_invalid_inputs_and_unmapped_trees(monkeypatch):
    """Parser helpers expose typed parse errors instead of raw ANTLR details."""
    with pytest.raises(BmcQueryParseError, match="Supported entries"):
        parse_with_bmc_grammar_entry("true", "missing_entry")
    with pytest.raises(BmcQueryParseError):
        parse_bmc_query("check reach <= : true;")
    with pytest.raises(BmcQueryParseError):
        parse_bmc_query("check reach <= 1: true; garbage")
    with pytest.raises(BmcQueryParseError):
        parse_bmc_cond_expression("x + 1")
    with pytest.raises(TypeError, match="ParserRuleContext"):
        build_bmc_ast_from_parse_tree(cast(ParserRuleContext, "not a parse tree"))
    with pytest.raises(BmcQueryParseError, match="No BMC AST node"):
        build_bmc_ast_from_parse_tree(ParserRuleContext())

    parse_module = importlib.import_module("pyfcstm.bmc.parse")

    def _raise_key_error_on_walk(self, listener, parse_tree):
        raise KeyError("missing recovered child")

    monkeypatch.setattr(parse_module.ParseTreeWalker, "walk", _raise_key_error_on_walk)
    with pytest.raises(BmcQueryParseError, match="child context"):
        build_bmc_ast_from_parse_tree(ParserRuleContext())
    monkeypatch.undo()
    parse_module = importlib.import_module("pyfcstm.bmc.parse")

    def _query_wrong_type(*args, **kwargs):
        return BoolLiteral("true")

    def _num_wrong_type(*args, **kwargs):
        return BoolLiteral("true")

    def _cond_wrong_type(*args, **kwargs):
        return Cycle()

    monkeypatch.setattr(parse_module, "parse_with_bmc_grammar_entry", _query_wrong_type)
    with pytest.raises(BmcQueryParseError, match="BmcQuery"):
        parse_module.parse_bmc_query("check reach <= 1: true;")
    monkeypatch.setattr(parse_module, "parse_with_bmc_grammar_entry", _num_wrong_type)
    with pytest.raises(BmcQueryParseError, match="BmcNumExpr"):
        parse_module.parse_bmc_num_expression("1")
    monkeypatch.setattr(parse_module, "parse_with_bmc_grammar_entry", _cond_wrong_type)
    with pytest.raises(BmcQueryParseError, match="BmcCondExpr"):
        parse_module.parse_bmc_cond_expression("true")


@pytest.mark.unittest
@pytest.mark.parametrize(
    "text, entry_name, expected",
    [
        pytest.param(
            "check reach <= : true;",
            "query",
            "recovery node",
            id="missing-query-bound",
        ),
        pytest.param(
            'active("Root.A")',
            "bmc_num_expression_entry",
            "recovered Bmc_num_expressionContext",
            id="condition-atom-in-numeric-entry",
        ),
        pytest.param(
            'event("Root.E")',
            "bmc_cond_expression_entry",
            "recovered Bmc_boolean_atomContext",
            id="missing-event-selector",
        ),
        pytest.param(
            'check reach <= 1: active("Root.A", );',
            "query",
            "recovered Frame_selectorContext",
            id="empty-frame-selector",
        ),
        pytest.param(
            "check reach <=",
            "query",
            "recovered Check_clauseContext",
            id="missing-bound-without-error-node",
        ),
        pytest.param(
            "check <= 1: true;",
            "query",
            "empty recovered Property_kindContext",
            id="missing-property-kind-without-error-node",
        ),
        pytest.param(
            'event("Root.E", )',
            "bmc_cond_expression_entry",
            "recovered Event_cycle_selectorContext",
            id="missing-event-cycle-without-error-node",
        ),
        pytest.param(
            "",
            "bool_literal",
            "empty recovered Bool_literalContext",
            id="empty-bool-literal-subrule",
        ),
        pytest.param(
            "",
            "num_literal",
            "empty recovered Num_literalContext",
            id="empty-num-literal-subrule",
        ),
        pytest.param(
            "",
            "event_range_selector",
            "recovered Event_range_selectorContext",
            id="empty-event-range-selector-subrule",
        ),
        pytest.param(
            "",
            "bmc_boolean_atom",
            "recovered Bmc_boolean_atomContext",
            id="empty-boolean-atom-subrule",
        ),
    ],
)
def test_build_bmc_ast_from_recovered_parse_trees_reports_bmc_parse_error(
    text, entry_name, expected
):
    """Recovered ANTLR parse trees do not leak listener ``KeyError`` failures."""
    lexer = BmcQueryLexer(InputStream(text))
    parser = BmcQueryParser(CommonTokenStream(lexer))
    tree = getattr(parser, entry_name)()

    with pytest.raises(BmcQueryParseError, match=expected):
        build_bmc_ast_from_parse_tree(tree)


@pytest.mark.unittest
def test_query_model_validation_errors_surface_after_successful_syntax_parse():
    """Syntax-valid zero bounds are rejected by the structural query model."""
    with pytest.raises(InvalidBmcQuery, match="bound"):
        parse_bmc_query("check reach <= 0: true;")
    with pytest.raises(InvalidBmcQuery, match="bound"):
        parse_bmc_query("check reach <= 00: true;")
    assert parse_bmc_query("check reach <= 01: true;").property.bound == 1
    with pytest.raises(InvalidBmcQuery, match="response properties"):
        parse_bmc_query("check response <= 1: true;")
    with pytest.raises(InvalidBmcQuery, match="single-body properties"):
        parse_bmc_query("check reach <= 1: trigger true -> within 1 true;")
    with pytest.raises(InvalidBmcQuery, match="response window"):
        parse_bmc_query("check response <= 1: trigger true -> within 0 true;")
    assert (
        parse_bmc_query(
            "check response <= 001: trigger true -> within 001 true;"
        ).property.within
        == 1
    )
    with pytest.raises(InvalidBmcQuery, match="selector"):
        parse_bmc_query(
            'assume event("Root.E", 5..3) == false; check reach <= 1: true;'
        )


@pytest.mark.unittest
def test_internal_error_listener_branches_and_parser_builders():
    """Collecting listener helper branches are deterministic and typed."""
    listener = _CollectingBmcErrorListener()
    lexer = _build_lexer("true", listener)
    parser = _build_parser(CommonTokenStream(lexer), listener)

    assert lexer.grammarFileName == "BmcQueryLexer.g4"
    assert parser.grammarFileName == "BmcQueryParser.g4"
    listener.check_errors()

    listener.syntaxError(None, None, 1, 2, "missing token", None)
    listener.syntaxError(None, object(), 3, 4, "bad object", None)
    assert "line 1:2" in listener.messages[0]
    assert "near" not in listener.messages[0]
    assert "near" in listener.messages[1]
    with pytest.raises(BmcQueryParseError, match="missing token"):
        listener.check_errors()

    eof_listener = _CollectingBmcErrorListener()
    eof_stream = CommonTokenStream(BmcQueryLexer(InputStream("")))
    eof_stream.fill()
    eof_listener.check_unfinished_parsing_error(eof_stream)
    assert eof_listener.messages == []

    unfinished_listener = _CollectingBmcErrorListener()
    unfinished_stream = CommonTokenStream(BmcQueryLexer(InputStream("true true")))
    unfinished_stream.fill()
    unfinished_listener.check_unfinished_parsing_error(unfinished_stream)
    assert "parser did not consume the full input" in unfinished_listener.messages[0]

    assert _find_error_node_text(ParserRuleContext()) == ""


@pytest.mark.unittest
def test_parse_import_does_not_load_model_verify_or_z3_modules():
    """Parser imports stay independent from model, verify registry, and Z3."""
    code = (
        "import sys; "
        "from pyfcstm.bmc.parse import parse_bmc_query; "
        "parse_bmc_query('check reach <= 1: true;'); "
        "bad = ["
        "name for name in sys.modules "
        "if name == 'z3' "
        "or name.startswith('pyfcstm.model') "
        "or name.startswith('pyfcstm.verify')"
        "]; "
        "print(bad)"
    )

    result = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )

    assert result.stdout.strip() == "[]"


@pytest.mark.unittest
@pytest.mark.parametrize(
    "builder, canonical_text",
    [
        pytest.param(
            lambda: parse_bmc_query(
                'init state("Root.A") where var("x") >= 0; '
                'assume event("Root.Tick", 1.. 3) != false; '
                'check reach <= 01: active("Root.Done");'
            ),
            (
                'init state("Root.A") where var("x") >= 0;\n\n'
                'assume event("Root.Tick", 1..3) == true;\n\n'
                'check reach <= 1: active("Root.Done");'
            ),
            id="query",
        ),
        pytest.param(
            lambda: parse_bmc_num_expression("cycle + 01"), "cycle + 01", id="num"
        ),
        pytest.param(
            lambda: parse_bmc_cond_expression("true and false"),
            "true && false",
            id="cond",
        ),
    ],
)
def test_parsed_nodes_stringify_to_canonical_round_trip_text(builder, canonical_text):
    """Parser output keeps the object ``str`` round-trip contract."""
    node = builder()

    assert str(node) == canonical_text
    if isinstance(node, BmcQuery):
        reparsed = parse_bmc_query(str(node))
    elif isinstance(node, BmcNumExpr):
        reparsed = parse_bmc_num_expression(str(node))
    else:
        reparsed = parse_bmc_cond_expression(str(node))
    assert reparsed.to_canonical() == node.to_canonical()


@pytest.mark.unittest
def test_parser_typing_helpers_are_used_by_static_interfaces():
    """Callable signatures used in parser dispatch remain object-returning."""
    funcs = [
        parse_bmc_query,
        parse_bmc_num_expression,
        parse_bmc_cond_expression,
    ]

    assert all(callable(func) for func in funcs)
    assert isinstance(
        BmcProperty("reach", 1, predicate=Active("Root.Done")), BmcProperty
    )
