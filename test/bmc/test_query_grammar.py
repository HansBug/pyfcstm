"""Grammar-level tests for the FCSTM BMC query ANTLR parser."""

import pytest
from antlr4 import CommonTokenStream, InputStream, Token
from antlr4.error.ErrorListener import ErrorListener

from pyfcstm.dsl.grammar.GrammarLexer import GrammarLexer
from pyfcstm.bmc.grammar.BmcQueryLexer import BmcQueryLexer
from pyfcstm.bmc.grammar.BmcQueryParser import BmcQueryParser
from pyfcstm.bmc.grammar.BmcQueryParserListener import BmcQueryParserListener


class _CollectingSyntaxErrorListener(ErrorListener):
    """Collect lexer and parser syntax errors without building BMC AST nodes."""

    def __init__(self):
        self.messages = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):
        """Record the ANTLR syntax error callback payload.

        :param recognizer: Lexer or parser that reported the error.
        :type recognizer: object
        :param offendingSymbol: Token or text near the failure.
        :type offendingSymbol: object
        :param line: One-based input line number.
        :type line: int
        :param column: Zero-based input column number.
        :type column: int
        :param msg: ANTLR diagnostic message.
        :type msg: str
        :param e: Optional ANTLR recognition exception.
        :type e: object
        :return: ``None``.
        :rtype: None

        Example::

            >>> listener = _CollectingSyntaxErrorListener()
            >>> listener.syntaxError(None, None, 1, 0, "bad", None)
            >>> listener.messages[0][0]
            1
        """
        self.messages.append((line, column, str(offendingSymbol), msg))


def _collect_errors(text, entry_rule):
    """Parse text with a BMC grammar entry and return syntax diagnostics.

    :param text: Query or expression source text.
    :type text: str
    :param entry_rule: Name of the parser entry rule to call.
    :type entry_rule: str
    :return: Collected lexer/parser diagnostics.
    :rtype: list

    Example::

        >>> _collect_errors('check reach <= 1: true;', 'query')
        []
    """
    error_listener = _CollectingSyntaxErrorListener()
    lexer = BmcQueryLexer(InputStream(text))
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)

    stream = CommonTokenStream(lexer)
    parser = BmcQueryParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    getattr(parser, entry_rule)()
    if stream.LA(1) != Token.EOF:
        error_listener.messages.append(
            (0, 0, str(stream.LT(1)), "parser did not consume EOF")
        )
    return error_listener.messages


def _assert_parses(text, entry_rule="query"):
    """Assert that a query or expression parses without grammar errors.

    :param text: Query or expression text.
    :type text: str
    :param entry_rule: Parser entry rule, defaults to ``"query"``.
    :type entry_rule: str, optional
    :return: ``None``.
    :rtype: None

    Example::

        >>> _assert_parses('check reach <= 1: true;')
    """
    assert _collect_errors(text, entry_rule) == []


def _assert_rejected(text, entry_rule="query"):
    """Assert that a query or expression is rejected by grammar parsing.

    :param text: Query or expression text.
    :type text: str
    :param entry_rule: Parser entry rule, defaults to ``"query"``.
    :type entry_rule: str, optional
    :return: ``None``.
    :rtype: None

    Example::

        >>> _assert_rejected('check reach <= 1: true; garbage')
    """
    assert _collect_errors(text, entry_rule) != []


@pytest.mark.unittest
def test_generated_bmc_query_parser_imports_are_available():
    """Generated lexer, parser, and listener modules import successfully."""
    assert BmcQueryLexer(InputStream("")).grammarFileName == "BmcQueryLexer.g4"
    assert BmcQueryParser(CommonTokenStream(BmcQueryLexer(InputStream(""))))
    assert issubclass(BmcQueryParserListener, object)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "text",
    [
        pytest.param("0", id="zero"),
        pytest.param("00", id="double-zero"),
        pytest.param("01", id="leading-zero-one"),
        pytest.param("001", id="leading-zero-many"),
        pytest.param("42", id="ordinary-decimal"),
    ],
)
def test_fbmcq_decimal_integer_tokens_match_fcstm_lexer(text):
    """FBMCQ decimal integers keep the FCSTM ``INT`` token surface."""
    fcstm_token = GrammarLexer(InputStream(text)).nextToken()
    fbmcq_token = BmcQueryLexer(InputStream(text)).nextToken()

    assert fcstm_token is not None
    assert fbmcq_token is not None
    assert GrammarLexer.symbolicNames[fcstm_token.type] == "INT"
    assert BmcQueryLexer.symbolicNames[fbmcq_token.type] == "INT"
    assert fbmcq_token.text == text


@pytest.mark.unittest
@pytest.mark.parametrize(
    "query_text",
    [
        pytest.param(
            'init cold; check reach <= 1: active("Root.A");',
            id="cold-reach",
        ),
        pytest.param(
            'init state("Root.A") where var("x") >= 0; '
            'check forbid <= 8: active("Root.Fault") or x > 10;',
            id="state-where-forbid",
        ),
        pytest.param(
            "init terminated; check invariant <= 4: terminated() || cycle >= 3;",
            id="terminated-invariant",
        ),
        pytest.param(
            'assume always: var("x") <= 10; '
            'assume at 2: active("Root.Ready"); '
            'check exists_always <= 5: active("Root.Safe");',
            id="frame-assumptions",
        ),
        pytest.param(
            'assume event("Root.Tick", *) == false; '
            'check reach <= 2: event("Root.Tick", 0);',
            id="event-assumption",
        ),
        pytest.param(
            "assume events cardinality any; "
            'check must_reach <= 7: active("Root.Done");',
            id="cardinality-any",
        ),
        pytest.param(
            'assume events cardinality at_most_one {"Root.Tick", "Root.Reset"}; '
            'check forbid <= 7: event("Root.Reset", current);',
            id="cardinality-set",
        ),
        pytest.param(
            'check response <= 8: trigger event("Root.Fault", current) '
            '-> within 3 active("Root.Recovering");',
            id="response",
        ),
        pytest.param(
            "init cold;\n\n"
            "assume events cardinality at_most_one {\n"
            '    "Root.Tick",\n'
            '    "Root.Reset"\n'
            "};\n\n"
            "check response <= 8:\n"
            '    trigger event("Root.Fault", current)\n'
            '    -> within 3 active("Root.Recovering");',
            id="canonical-multiline-response",
        ),
        pytest.param(
            'check cover <= 5: case("Root.A::transition::Root.B::0");',
            id="cover",
        ),
        pytest.param(
            """
            // comments and whitespace are syntax-only trivia.
            init cold;
            assume always: /* block */ var("x") >= 0;
            # python-style comments are accepted too.
            check reach <= 3: active("Root.Done");
            """,
            id="comments",
        ),
    ],
)
def test_valid_complete_fbmcq_queries_parse(query_text):
    """Representative complete ``.fbmcq`` queries parse at grammar level."""
    _assert_parses(query_text)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "selector, expected, bool_case",
    [
        pytest.param("*", "==", "true", id="any-true"),
        pytest.param("*", "==", "false", id="any-false"),
        pytest.param("0", "!=", "true", id="point-not-true"),
        pytest.param("2", "==", "TRUE", id="point-upper-true"),
        pytest.param("1..3", "!=", "false", id="compact-range"),
        pytest.param("1 .. 3", "==", "False", id="spaced-range"),
        pytest.param("1.. 3", "!=", "False", id="range-space-after-dots"),
    ],
)
def test_event_assumption_selectors_and_polarity_parse(selector, expected, bool_case):
    """Event assumptions cover selectors, polarity, and boolean spellings."""
    _assert_parses(
        'assume event("Root.E", %s) %s %s; check reach <= 1: true;'
        % (selector, expected, bool_case)
    )


@pytest.mark.unittest
@pytest.mark.parametrize(
    "expression",
    [
        pytest.param("0", id="decimal-zero"),
        pytest.param("00", id="decimal-double-zero"),
        pytest.param("01", id="decimal-leading-zero-one"),
        pytest.param("001", id="decimal-leading-zero-many"),
        pytest.param("42", id="decimal"),
        pytest.param("0x2A", id="hex"),
        pytest.param(".5", id="float-leading-dot"),
        pytest.param("1.", id="float-trailing-dot"),
        pytest.param("3.5e1", id="float-exp"),
        pytest.param("1e-3", id="float-negative-exp"),
        pytest.param("pi", id="const-pi"),
        pytest.param("E", id="const-e"),
        pytest.param("tau", id="const-tau"),
        pytest.param("x", id="bare-name"),
        pytest.param('var("x")', id="frame-var"),
        pytest.param('var("中文变量")', id="unicode-frame-var"),
        pytest.param("cycle", id="cycle"),
        pytest.param("+x", id="unary-plus"),
        pytest.param('-var("x")', id="unary-minus"),
        pytest.param("x ** y ** z", id="pow-associativity"),
        pytest.param("x * y / z % 2", id="multiplicative"),
        pytest.param("x + y - 3", id="additive"),
        pytest.param("x << 1", id="shift-left"),
        pytest.param("x >> 1", id="shift-right"),
        pytest.param("x & y", id="bit-and"),
        pytest.param("x ^ y", id="bit-xor"),
        pytest.param("x | y", id="bit-or"),
        pytest.param("x + y * z ** 2", id="precedence"),
        pytest.param('(active("Root.A")) ? 1 : 0', id="ternary"),
    ],
)
def test_fcstm_compatible_numeric_expressions_parse(expression):
    """Numeric expression entry tracks FCSTM-compatible expression syntax."""
    _assert_parses(expression, "bmc_num_expression_entry")


@pytest.mark.unittest
@pytest.mark.parametrize(
    "func_name",
    [
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "sinh",
        "cosh",
        "tanh",
        "asinh",
        "acosh",
        "atanh",
        "sqrt",
        "cbrt",
        "exp",
        "log",
        "log10",
        "log2",
        "log1p",
        "abs",
        "ceil",
        "floor",
        "round",
        "trunc",
        "sign",
    ],
)
def test_all_fcstm_unary_functions_parse(func_name):
    """All FCSTM ``UFUNC_NAME`` tokens parse as numeric function calls."""
    _assert_parses("%s(x)" % func_name, "bmc_num_expression_entry")


@pytest.mark.unittest
@pytest.mark.parametrize(
    "expression",
    [
        pytest.param("true", id="bool-lower"),
        pytest.param("True", id="bool-title"),
        pytest.param("TRUE", id="bool-upper"),
        pytest.param("false", id="bool-false"),
        pytest.param('active("Root.A")', id="active-current"),
        pytest.param('active("Root.A", current)', id="active-explicit-current"),
        pytest.param('active("Root.A", 2)', id="active-frame"),
        pytest.param("terminated()", id="terminated-current"),
        pytest.param("terminated(current)", id="terminated-explicit-current"),
        pytest.param("terminated(3)", id="terminated-frame"),
        pytest.param('event("Root.E", current)', id="event-current"),
        pytest.param('event("Root.E", 0)', id="event-index"),
        pytest.param('case("label")', id="case-current"),
        pytest.param('case("label", current)', id="case-explicit-current"),
        pytest.param('case("label", 4)', id="case-frame"),
        pytest.param('called("hook")', id="called-current"),
        pytest.param('called("hook", current)', id="called-explicit-current"),
        pytest.param('called("hook", 5)', id="called-frame"),
        pytest.param('!active("Root.A")', id="bang"),
        pytest.param("not false", id="not-keyword"),
        pytest.param("x < y", id="lt"),
        pytest.param("x > y", id="gt"),
        pytest.param("x <= y", id="le"),
        pytest.param("x >= y", id="ge"),
        pytest.param("x == y", id="num-eq"),
        pytest.param("x != y", id="num-ne"),
        pytest.param("true == false", id="cond-eq"),
        pytest.param("true != false", id="cond-ne"),
        pytest.param("true iff false", id="iff"),
        pytest.param("true && false", id="and-symbol"),
        pytest.param("true and false", id="and-keyword"),
        pytest.param("true xor false", id="xor"),
        pytest.param("true || false", id="or-symbol"),
        pytest.param("true or false", id="or-keyword"),
        pytest.param("true => false", id="implies-symbol"),
        pytest.param("true implies false", id="implies-keyword"),
        pytest.param(
            '(x > 0) ? active("Root.A") : false',
            id="condition-ternary",
        ),
        pytest.param(
            '(active("Root.A") && !called("hook")) => cycle <= 5',
            id="precedence-mixed",
        ),
    ],
)
def test_fcstm_compatible_condition_expressions_and_bmc_atoms_parse(expression):
    """Condition expression entry tracks FCSTM operators plus BMC atoms."""
    _assert_parses(expression, "bmc_cond_expression_entry")


@pytest.mark.unittest
@pytest.mark.parametrize(
    "query_text",
    [
        pytest.param(
            'assume always: event("Root.E", 0); check reach <= 1: true;',
            id="event-in-frame-assumption",
        ),
        pytest.param(
            'init cold; check cover <= 3: active("Root.A") and case("case-label");',
            id="compound-cover",
        ),
        pytest.param(
            'init cold; check reach <= 5: event("Root.E", current);',
            id="event-current-in-property",
        ),
        pytest.param(
            'init cold; check reach <= 5: called("hook");',
            id="called-in-property",
        ),
        pytest.param(
            'assume event("Root.E", 5..3) == false; check reach <= 1: true;',
            id="descending-event-range",
        ),
        pytest.param(
            "check reach <= 0: true;",
            id="zero-check-bound-deferred-to-query-model",
        ),
        pytest.param(
            "check reach <= 00: true;",
            id="double-zero-check-bound-deferred-to-query-model",
        ),
        pytest.param(
            "check reach <= 01: true;",
            id="leading-zero-check-bound",
        ),
        pytest.param(
            "check response <= 1: trigger true -> within 0 true;",
            id="zero-response-window-deferred-to-query-model",
        ),
        pytest.param(
            "check response <= 001: trigger true -> within 01 true;",
            id="leading-zero-response-bound-and-window",
        ),
    ],
)
def test_later_binding_or_normalization_queries_parse(query_text):
    """Grammar does not swallow later binder diagnostics or normalization."""
    _assert_parses(query_text)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "query_text",
    [
        pytest.param(
            "init cold check reach <= 1: true;",
            id="missing-init-semicolon",
        ),
        pytest.param("init cold;", id="missing-check-clause"),
        pytest.param("check <= 5: true;", id="missing-property-kind"),
        pytest.param(
            "check reach <= -1: true;",
            id="negative-check-bound",
        ),
        pytest.param(
            "check reach <= 0x1: true;",
            id="hex-check-bound",
        ),
        pytest.param(
            "check response <= 1: trigger true -> within 1.5 true;",
            id="float-response-window",
        ),
        pytest.param(
            'check reach <= 1: active("Root.A);',
            id="malformed-string",
        ),
        pytest.param(
            'assume event("Root.E", 1..2..3) == true; check reach <= 1: true;',
            id="malformed-event-range",
        ),
        pytest.param(
            'check reach <= 1: active("Root.A") + 1 > 2;',
            id="boolean-atom-in-numeric-operator",
        ),
        pytest.param(
            "check reach <= 1: x + 1;",
            id="numeric-expression-direct-predicate",
        ),
        pytest.param(
            "check reach <= 1: true; garbage",
            id="trailing-garbage",
        ),
        pytest.param(
            'check reach <= 1: event("Root.E");',
            id="event-atom-missing-selector",
        ),
    ],
)
def test_syntax_invalid_fbmcq_queries_are_rejected(query_text):
    """Malformed query files are rejected and trailing tokens are not ignored."""
    _assert_rejected(query_text)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "expression, entry_rule",
    [
        pytest.param('active("Root.A") + 1', "bmc_num_expression_entry"),
        pytest.param("x + 1", "bmc_cond_expression_entry"),
        pytest.param('event("Root.E")', "bmc_cond_expression_entry"),
        pytest.param("true", "bmc_num_expression_entry"),
        pytest.param("x < y", "bmc_num_expression_entry"),
    ],
)
def test_expression_category_boundaries_are_enforced(expression, entry_rule):
    """Numeric and condition grammar entries remain strictly separated."""
    _assert_rejected(expression, entry_rule)
