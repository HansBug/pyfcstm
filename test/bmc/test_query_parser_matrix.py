"""High-volume parser matrix tests for FCSTM BMC query AST nodes.

The parser matrix deliberately keeps the generated ``.fbmcq`` syntax and the
expected parser-independent AST objects next to each other.  This makes the
coverage requirements auditable: every concrete expression/query node introduced
by the parser has at least forty standalone FBMCQ parse cases, every
FCSTM-compatible expression node has at least forty strict FCSTM-vs-FBMCQ
alignment cases, and one hundred complete medium/high-complexity query files are
parsed and round-tripped as integrated trees.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, List, NamedTuple, Tuple

import pytest

from pyfcstm.bmc import ast as bmc_nodes
from pyfcstm.bmc import query as bmc_query_nodes
from pyfcstm.bmc.parse import (
    parse_bmc_cond_expression,
    parse_bmc_num_expression,
    parse_bmc_query,
)
from pyfcstm.dsl.parse import parse_with_grammar_entry
from test.bmc.test_query_expression_parity import (
    _bmc_to_fcstm_expr,
    _fcstm_to_bmc_expr,
    _shared_shape_from_bmc,
    _shared_shape_from_fcstm,
)


class NodeParseCase(NamedTuple):
    """One FBMCQ parse case for a concrete node target.

    :param target: Human-readable concrete node name tracked by the coverage
        audit.
    :type target: str
    :param source: FBMCQ source text parsed by this case.
    :type source: str
    :param entry: Parser entry category: ``"num"``, ``"cond"``, or
        ``"query"``.
    :type entry: str
    :param expected: Canonical expected object or selected query sub-object.
    :type expected: object
    :param selector: Function that extracts the asserted object from the parsed
        root.
    :type selector: Callable[[object], object]

    Example::

        >>> case = _expression_case("IntLiteral", "1", bmc_nodes.IntLiteral("1"))
        >>> case.target
        'IntLiteral'
    """

    target: str
    source: str
    entry: str
    expected: Any
    selector: Callable[[Any], Any]


class ParityCase(NamedTuple):
    """One FCSTM/FBMCQ expression alignment case.

    :param target: Concrete FBMCQ node expected at the root of the aligned
        expression.
    :type target: str
    :param expression: Expression parsed through both FCSTM and FBMCQ grammar
        entries.
    :type expression: str
    :param category: Expression category: ``"num"`` or ``"cond"``.
    :type category: str

    Example::

        >>> ParityCase("IntLiteral", "1", "num").category
        'num'
    """

    target: str
    expression: str
    category: str


class ComplexQueryCase(NamedTuple):
    """One complete medium/high-complexity FBMCQ file case.

    :param case_index: Stable case index used by test ids and assertions.
    :type case_index: int
    :param source: Complete FBMCQ query source text.
    :type source: str
    :param expected: Expected parser-independent query object.
    :type expected: pyfcstm.bmc.query.BmcQuery

    Example::

        >>> case = _complex_query_cases()[0]
        >>> case.case_index
        0
    """

    case_index: int
    source: str
    expected: bmc_query_nodes.BmcQuery


_REQUIRED_STANDALONE_NODES = (
    "IntLiteral",
    "FloatLiteral",
    "BoolLiteral",
    "NameRef",
    "MathConst",
    "NumUnaryOp",
    "NumBinaryOp",
    "NumConditionalOp",
    "UFuncCall",
    "CondUnaryOp",
    "NumericComparison",
    "CondBinaryOp",
    "CondConditionalOp",
    "FrameVar",
    "Cycle",
    "Active",
    "Terminated",
    "Event",
    "Case",
    "Called",
    "InitialVariablePolicy",
    "InitialSpec",
    "FrameAssumption",
    "EventAssumption",
    "EventCardinalityAssumption",
    "BmcProperty",
    "BmcQuery",
)

_REQUIRED_PARITY_NODES = (
    "IntLiteral",
    "FloatLiteral",
    "BoolLiteral",
    "NameRef",
    "MathConst",
    "NumUnaryOp",
    "NumBinaryOp",
    "NumConditionalOp",
    "UFuncCall",
    "CondUnaryOp",
    "NumericComparison",
    "CondBinaryOp",
    "CondConditionalOp",
)

_UFUNC_NAMES = (
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
)

_NUM_BINARY_OPS = ("**", "*", "/", "%", "+", "-", "<<", ">>", "&", "^", "|")
_NUM_COMPARE_OPS = ("<", ">", "<=", ">=", "==", "!=")
_COND_BINARY_OPS = ("&&", "and", "||", "or", "xor", "=>", "implies", "iff", "==", "!=")
_PROPERTY_KINDS = (
    "reach",
    "forbid",
    "invariant",
    "must_reach",
    "exists_always",
    "cover",
)


def _entry_for_expression(expr: bmc_nodes.BmcExpr) -> str:
    """Return the parser entry category for an expression object.

    :param expr: Expression object under test.
    :type expr: pyfcstm.bmc.ast.BmcExpr
    :return: ``"num"`` for numeric expressions, otherwise ``"cond"``.
    :rtype: str

    Example::

        >>> _entry_for_expression(bmc_nodes.Cycle())
        'num'
    """
    if isinstance(expr, bmc_nodes.BmcNumExpr):
        return "num"
    return "cond"


def _parse_entry(entry: str, source: str) -> Any:
    """Parse source text using the matrix-selected entry point.

    :param entry: Parser entry category.
    :type entry: str
    :param source: Source text for that entry.
    :type source: str
    :return: Parsed AST/query object.
    :rtype: object

    Example::

        >>> _parse_entry("num", "1").to_canonical()["value"]
        1
    """
    if entry == "num":
        return parse_bmc_num_expression(source)
    if entry == "cond":
        return parse_bmc_cond_expression(source)
    return parse_bmc_query(source)


def _root(value: Any) -> Any:
    """Return a parsed root unchanged for expression and query-root cases.

    :param value: Parsed object.
    :type value: object
    :return: The same object.
    :rtype: object

    Example::

        >>> _root(1)
        1
    """
    return value


def _query_initial(value: bmc_query_nodes.BmcQuery) -> bmc_query_nodes.InitialSpec:
    """Select the initial clause from a parsed query.

    :param value: Parsed query object.
    :type value: pyfcstm.bmc.query.BmcQuery
    :return: Query initial specification.
    :rtype: pyfcstm.bmc.query.InitialSpec

    Example::

        >>> _query_initial(parse_bmc_query('check reach <= 1: true;')).mode
        'cold'
    """
    return value.initial


def _query_initial_variable_policy(
    value: bmc_query_nodes.BmcQuery,
) -> bmc_query_nodes.InitialVariablePolicy:
    """Select the initial variable policy from a parsed query.

    :param value: Parsed query object.
    :type value: pyfcstm.bmc.query.BmcQuery
    :return: Query initial variable policy.
    :rtype: pyfcstm.bmc.query.InitialVariablePolicy

    Example::

        >>> _query_initial_variable_policy(parse_bmc_query('check reach <= 1: true;')).is_empty
        True
    """
    return value.initial.variable_policy


def _query_first_assumption(
    value: bmc_query_nodes.BmcQuery,
) -> bmc_query_nodes.BmcAssumption:
    """Select the first assumption from a parsed query.

    :param value: Parsed query object.
    :type value: pyfcstm.bmc.query.BmcQuery
    :return: First assumption.
    :rtype: pyfcstm.bmc.query.BmcAssumption

    Example::

        >>> query = parse_bmc_query('assume always: true; check reach <= 1: true;')
        >>> _query_first_assumption(query).to_canonical()['kind']
        'always'
    """
    return value.assumptions[0]


def _query_property(value: bmc_query_nodes.BmcQuery) -> bmc_query_nodes.BmcProperty:
    """Select the property from a parsed query.

    :param value: Parsed query object.
    :type value: pyfcstm.bmc.query.BmcQuery
    :return: Query property.
    :rtype: pyfcstm.bmc.query.BmcProperty

    Example::

        >>> _query_property(parse_bmc_query('check reach <= 1: true;')).kind
        'reach'
    """
    return value.property


def _canonical(value: Any) -> Any:
    """Return the canonical dictionary for a BMC object.

    :param value: Object with ``to_canonical``.
    :type value: object
    :return: Canonical dictionary.
    :rtype: object

    Example::

        >>> _canonical(bmc_nodes.IntLiteral("1"))["node"]
        'int_literal'
    """
    return value.to_canonical()


def _expression_case(
    target: str, source: str, expected: bmc_nodes.BmcExpr
) -> NodeParseCase:
    """Build one standalone expression parser case.

    :param target: Concrete node name.
    :type target: str
    :param source: FBMCQ expression source text.
    :type source: str
    :param expected: Expected expression object.
    :type expected: pyfcstm.bmc.ast.BmcExpr
    :return: Matrix parse case.
    :rtype: NodeParseCase

    Example::

        >>> _expression_case("Cycle", "cycle", bmc_nodes.Cycle()).entry
        'num'
    """
    return NodeParseCase(
        target, source, _entry_for_expression(expected), expected, _root
    )


def _query_case(
    target: str,
    source: str,
    expected: Any,
    selector: Callable[[Any], Any],
) -> NodeParseCase:
    """Build one standalone query parser case.

    :param target: Concrete query node name.
    :type target: str
    :param source: Complete FBMCQ query source text.
    :type source: str
    :param expected: Expected selected query object.
    :type expected: object
    :param selector: Parsed-query selector for ``expected``.
    :type selector: Callable[[object], object]
    :return: Matrix parse case.
    :rtype: NodeParseCase

    Example::

        >>> prop = bmc_query_nodes.BmcProperty("reach", 1, predicate=bmc_nodes.BoolLiteral("true"))
        >>> _query_case("BmcProperty", str(prop), prop, _query_property).entry
        'query'
    """
    return NodeParseCase(target, source, "query", expected, selector)


def _decorated_expression_sources(base: str, count: int = 40) -> List[str]:
    """Return whitespace/comment/parenthesis variants for one expression.

    :param base: Base expression text.
    :type base: str
    :param count: Number of variants to return, defaults to ``40``.
    :type count: int, optional
    :return: Source variants that parse to the same root expression.
    :rtype: list

    Example::

        >>> len(_decorated_expression_sources("cycle", 3))
        3
    """
    variants = []
    for index in range(count):
        style = index % 10
        if style == 0:
            text = base
        elif style == 1:
            text = "  %s  " % base
        elif style == 2:
            text = "(%s)" % base
        elif style == 3:
            text = "/* before_%d */ %s" % (index, base)
        elif style == 4:
            text = "%s /* after_%d */" % (base, index)
        elif style == 5:
            text = "/* left_%d */ (%s) /* right_%d */" % (index, base, index)
        elif style == 6:
            text = "// line_%d\n%s" % (index, base)
        elif style == 7:
            text = "# hash_%d\n%s" % (index, base)
        elif style == 8:
            text = "(\n%s\n)" % base
        else:
            text = "\n\t%s\n" % base
        variants.append(text)
    return variants


def _string(index: int, prefix: str) -> str:
    """Return a stable query string value with occasional escaped characters.

    :param index: Case index.
    :type index: int
    :param prefix: Value prefix.
    :type prefix: str
    :return: String value for a quoted FBMCQ atom.
    :rtype: str

    Example::

        >>> _string(1, "Root.State")
        'Root.State1'
    """
    if index % 10 == 7:
        return '%s%d."quoted"' % (prefix, index)
    if index % 10 == 8:
        return "%s%d.中文" % (prefix, index)
    if index % 10 == 9:
        return "%s%d.back\\slash" % (prefix, index)
    return "%s%d" % (prefix, index)


def _num_leaf(index: int) -> bmc_nodes.BmcNumExpr:
    """Return a numeric leaf expression used by matrix factories.

    :param index: Case index.
    :type index: int
    :return: Numeric expression leaf.
    :rtype: pyfcstm.bmc.ast.BmcNumExpr

    Example::

        >>> isinstance(_num_leaf(0), bmc_nodes.BmcNumExpr)
        True
    """
    choices = (
        bmc_nodes.NameRef("x%d" % index),
        bmc_nodes.IntLiteral(str(index + 1)),
        bmc_nodes.FloatLiteral("%d.%d" % (index + 1, index % 10)),
        bmc_nodes.MathConst(("pi", "E", "tau")[index % 3]),
        bmc_nodes.FrameVar(_string(index, "var")),
        bmc_nodes.Cycle(),
    )
    return choices[index % len(choices)]


def _comparison(index: int) -> bmc_nodes.NumericComparison:
    """Return a numeric comparison with varied operators and operands.

    :param index: Case index.
    :type index: int
    :return: Numeric comparison expression.
    :rtype: pyfcstm.bmc.ast.NumericComparison

    Example::

        >>> _comparison(0).to_canonical()["node"]
        'numeric_comparison'
    """
    left = bmc_nodes.NumBinaryOp(
        _num_leaf(index),
        _NUM_BINARY_OPS[index % len(_NUM_BINARY_OPS)],
        _num_leaf(index + 1),
    )
    right = bmc_nodes.UFuncCall(
        _UFUNC_NAMES[index % len(_UFUNC_NAMES)], _num_leaf(index + 2)
    )
    return bmc_nodes.NumericComparison(
        left, _NUM_COMPARE_OPS[index % len(_NUM_COMPARE_OPS)], right
    )


def _condition(index: int) -> bmc_nodes.BmcCondExpr:
    """Return a medium-complexity condition expression.

    :param index: Case index.
    :type index: int
    :return: Condition expression.
    :rtype: pyfcstm.bmc.ast.BmcCondExpr

    Example::

        >>> isinstance(_condition(0), bmc_nodes.BmcCondExpr)
        True
    """
    active = bmc_nodes.Active(_string(index, "Root.State"), frame=index % 5)
    event = bmc_nodes.Event(_string(index, "Root.Event"), selector=index % 4)
    selected_case = bmc_nodes.Case(_string(index, "Root.Case"), frame=(index + 1) % 5)
    called = bmc_nodes.Called(_string(index, "Hook"), frame=(index + 2) % 5)
    left = bmc_nodes.CondBinaryOp(_comparison(index), "&&", active)
    right = bmc_nodes.CondBinaryOp(
        event, "xor", bmc_nodes.CondBinaryOp(selected_case, "||", called)
    )
    implication = bmc_nodes.CondBinaryOp(left, "=>", right)
    if index % 3 == 0:
        return bmc_nodes.CondConditionalOp(
            _comparison(index + 3), implication, bmc_nodes.BoolLiteral("false")
        )
    if index % 3 == 1:
        return bmc_nodes.CondUnaryOp("!", implication)
    return bmc_nodes.CondBinaryOp(
        implication, "iff", bmc_nodes.Terminated(frame=index % 5)
    )


def _single_property(index: int) -> bmc_query_nodes.BmcProperty:
    """Return a non-response property for generated complete query cases.

    :param index: Case index.
    :type index: int
    :return: Property object.
    :rtype: pyfcstm.bmc.query.BmcProperty

    Example::

        >>> _single_property(0).bound
        1
    """
    return bmc_query_nodes.BmcProperty(
        _PROPERTY_KINDS[index % len(_PROPERTY_KINDS)],
        bound=index + 1,
        predicate=_condition(index),
    )


def _response_property(index: int) -> bmc_query_nodes.BmcProperty:
    """Return a response property for generated complete query cases.

    :param index: Case index.
    :type index: int
    :return: Response property object.
    :rtype: pyfcstm.bmc.query.BmcProperty

    Example::

        >>> _response_property(0).kind
        'response'
    """
    return bmc_query_nodes.BmcProperty(
        "response",
        bound=index + 2,
        trigger=_condition(index),
        response=_condition(index + 1),
        within=(index % 7) + 1,
    )


def _query_with_initial(
    initial: bmc_query_nodes.InitialSpec, index: int
) -> bmc_query_nodes.BmcQuery:
    """Embed an initial spec in a complete parseable query.

    :param initial: Initial specification under test.
    :type initial: pyfcstm.bmc.query.InitialSpec
    :param index: Case index.
    :type index: int
    :return: Complete query object.
    :rtype: pyfcstm.bmc.query.BmcQuery

    Example::

        >>> _query_with_initial(bmc_query_nodes.InitialSpec(), 0).initial.mode
        'cold'
    """
    return bmc_query_nodes.BmcQuery(initial=initial, property=_single_property(index))


def _query_with_assumption(
    assumption: bmc_query_nodes.BmcAssumption, index: int
) -> bmc_query_nodes.BmcQuery:
    """Embed an assumption in a complete parseable query.

    :param assumption: Assumption under test.
    :type assumption: pyfcstm.bmc.query.BmcAssumption
    :param index: Case index.
    :type index: int
    :return: Complete query object.
    :rtype: pyfcstm.bmc.query.BmcQuery

    Example::

        >>> assumption = bmc_query_nodes.FrameAssumption("always", bmc_nodes.BoolLiteral("true"))
        >>> len(_query_with_assumption(assumption, 0).assumptions)
        1
    """
    return bmc_query_nodes.BmcQuery(
        assumptions=(assumption,), property=_single_property(index)
    )


def _initial_specs() -> List[bmc_query_nodes.InitialSpec]:
    """Return at least forty initial specifications.

    :return: Initial specifications.
    :rtype: list

    Example::

        >>> len(_initial_specs()) >= 40
        True
    """
    specs = []
    for index in range(40):
        mode = index % 6
        if mode == 0:
            spec = bmc_query_nodes.InitialSpec()
        elif mode == 1:
            spec = bmc_query_nodes.InitialSpec(mode="terminated")
        elif mode == 2:
            spec = bmc_query_nodes.InitialSpec(
                mode="state", state_path=_string(index, "Root.Init")
            )
        elif mode == 3:
            spec = bmc_query_nodes.InitialSpec(mode="cold", predicate=_condition(index))
        elif mode == 4:
            spec = bmc_query_nodes.InitialSpec(
                mode="terminated", predicate=_condition(index)
            )
        else:
            spec = bmc_query_nodes.InitialSpec(
                mode="state",
                state_path=_string(index, "Root.Init"),
                predicate=_condition(index),
            )
        specs.append(spec)
    return specs


def _initial_variable_policies() -> List[bmc_query_nodes.InitialVariablePolicy]:
    """Return at least forty initial variable policy cases.

    :return: Initial variable policies.
    :rtype: list

    Example::

        >>> len(_initial_variable_policies()) >= 40
        True
    """
    policies = []
    names = (
        ("x",),
        ("x", "y"),
        ("counter_1",),
        ("cycle",),
        ("event",),
        ("state", "where"),
        ("变量",),
        ("x", "cycle", "event"),
    )
    for index in range(40):
        mode = index % 5
        if mode == 0:
            policy = bmc_query_nodes.InitialVariablePolicy()
        elif mode == 1:
            policy = bmc_query_nodes.InitialVariablePolicy(havoc_all=True)
        else:
            policy = bmc_query_nodes.InitialVariablePolicy(
                havoc_variables=names[index % len(names)]
            )
        policies.append(policy)
    return policies


def _frame_assumptions() -> List[bmc_query_nodes.FrameAssumption]:
    """Return at least forty frame assumptions.

    :return: Frame assumptions.
    :rtype: list

    Example::

        >>> len(_frame_assumptions()) >= 40
        True
    """
    assumptions = []
    for index in range(40):
        if index % 2 == 0:
            assumptions.append(
                bmc_query_nodes.FrameAssumption("always", _condition(index))
            )
        else:
            assumptions.append(
                bmc_query_nodes.FrameAssumption(
                    "at", _condition(index), frame=index % 9
                )
            )
    return assumptions


def _event_assumptions() -> List[bmc_query_nodes.EventAssumption]:
    """Return at least forty event assumptions.

    :return: Event assumptions.
    :rtype: list

    Example::

        >>> len(_event_assumptions()) >= 40
        True
    """
    selectors: Tuple[Any, ...] = ("*", 0, 1, "0..3", "01..03", "02..02", 7)
    return [
        bmc_query_nodes.EventAssumption(
            _string(index, "Root.Event"),
            selector=selectors[index % len(selectors)],
            expected=index % 3 != 0,
        )
        for index in range(40)
    ]


def _event_cardinality_assumptions() -> List[
    bmc_query_nodes.EventCardinalityAssumption
]:
    """Return at least forty event-cardinality assumptions.

    :return: Event-cardinality assumptions.
    :rtype: list

    Example::

        >>> len(_event_cardinality_assumptions()) >= 40
        True
    """
    assumptions = []
    for index in range(40):
        if index % 4 == 0:
            assumptions.append(bmc_query_nodes.EventCardinalityAssumption("any"))
        else:
            assumptions.append(
                bmc_query_nodes.EventCardinalityAssumption(
                    "at_most_one",
                    tuple(
                        _string(index + offset, "Root.Event")
                        for offset in range(2 + index % 3)
                    ),
                )
            )
    return assumptions


def _properties() -> List[bmc_query_nodes.BmcProperty]:
    """Return at least forty BMC properties.

    :return: BMC properties.
    :rtype: list

    Example::

        >>> len(_properties()) >= 40
        True
    """
    properties = []
    for index in range(40):
        if index % 7 == 6:
            properties.append(_response_property(index))
        else:
            properties.append(_single_property(index))
    return properties


def _complex_query(index: int) -> bmc_query_nodes.BmcQuery:
    """Return a complete query with several clauses and nested predicates.

    :param index: Case index.
    :type index: int
    :return: Complete BMC query object.
    :rtype: pyfcstm.bmc.query.BmcQuery

    Example::

        >>> len(_complex_query(0).assumptions) >= 5
        True
    """
    initial = _initial_specs()[index % 40]
    event_a = _string(index, "Root.Event")
    event_b = _string(index + 1, "Root.Event")
    event_c = _string(index + 2, "Root.Event")
    assumptions = (
        bmc_query_nodes.FrameAssumption("always", _condition(index)),
        bmc_query_nodes.FrameAssumption("at", _condition(index + 1), frame=index % 10),
        bmc_query_nodes.EventAssumption(event_a, selector="*", expected=index % 2 == 0),
        bmc_query_nodes.EventAssumption(
            event_b,
            selector="%d..%d" % (index % 3, index % 3 + 2),
            expected=index % 3 != 0,
        ),
        bmc_query_nodes.EventCardinalityAssumption(
            "at_most_one", (event_a, event_b, event_c)
        ),
        bmc_query_nodes.EventCardinalityAssumption("any"),
    )
    property_node = (
        _response_property(index) if index % 5 == 0 else _single_property(index)
    )
    return bmc_query_nodes.BmcQuery(
        initial=initial,
        assumptions=assumptions,
        property=property_node,
    )


def _expression_node_cases() -> List[NodeParseCase]:
    """Build standalone FBMCQ expression cases for every concrete expression node.

    :return: Matrix cases.
    :rtype: list

    Example::

        >>> any(case.target == "Cycle" for case in _expression_node_cases())
        True
    """
    cases: List[NodeParseCase] = []

    int_values = ["0", "00", "01", "001", "42"] + [str(index) for index in range(2, 25)]
    int_values.extend("0x%X" % index for index in range(1, 14))
    for index, raw in enumerate(int_values[:40]):
        expr = bmc_nodes.IntLiteral(raw)
        cases.append(
            _expression_case(
                "IntLiteral", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    float_values = ["%d.%d" % (index + 1, index % 10) for index in range(12)]
    float_values.extend(".%d" % (index + 1) for index in range(10))
    float_values.extend("%de-%d" % (index + 1, index % 5 + 1) for index in range(10))
    float_values.extend("%dE+%d" % (index + 1, index % 4 + 1) for index in range(8))
    for index, raw in enumerate(float_values[:40]):
        expr = bmc_nodes.FloatLiteral(raw)
        cases.append(
            _expression_case(
                "FloatLiteral", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    bool_values = ("true", "True", "TRUE", "false", "False", "FALSE")
    for index in range(40):
        raw = bool_values[index % len(bool_values)]
        expr = bmc_nodes.BoolLiteral(raw)
        cases.append(
            _expression_case(
                "BoolLiteral", _decorated_expression_sources(raw)[index], expr
            )
        )

    for index in range(40):
        expr = bmc_nodes.NameRef("var_%d" % index)
        cases.append(
            _expression_case(
                "NameRef", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    const_values = ("pi", "E", "tau")
    for index in range(40):
        expr = bmc_nodes.MathConst(const_values[index % len(const_values)])
        cases.append(
            _expression_case(
                "MathConst", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    for index in range(40):
        operand = _num_leaf(index)
        expr = bmc_nodes.NumUnaryOp(("+", "-")[index % 2], operand)
        cases.append(
            _expression_case(
                "NumUnaryOp", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    for index in range(40):
        expr = bmc_nodes.NumBinaryOp(
            _num_leaf(index),
            _NUM_BINARY_OPS[index % len(_NUM_BINARY_OPS)],
            _num_leaf(index + 1),
        )
        cases.append(
            _expression_case(
                "NumBinaryOp", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    for index in range(40):
        expr = bmc_nodes.NumConditionalOp(
            _condition(index),
            bmc_nodes.NumBinaryOp(_num_leaf(index), "+", _num_leaf(index + 1)),
            bmc_nodes.UFuncCall(
                _UFUNC_NAMES[index % len(_UFUNC_NAMES)], _num_leaf(index + 2)
            ),
        )
        cases.append(
            _expression_case(
                "NumConditionalOp",
                _decorated_expression_sources(str(expr))[index],
                expr,
            )
        )

    for index in range(40):
        expr = bmc_nodes.UFuncCall(
            _UFUNC_NAMES[index % len(_UFUNC_NAMES)], _num_leaf(index)
        )
        cases.append(
            _expression_case(
                "UFuncCall", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    for index in range(40):
        operand = (
            _condition(index)
            if index % 2
            else bmc_nodes.Active(_string(index, "Root.State"))
        )
        expr = bmc_nodes.CondUnaryOp(("!", "not")[index % 2], operand)
        cases.append(
            _expression_case(
                "CondUnaryOp", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    for index in range(40):
        expr = _comparison(index)
        cases.append(
            _expression_case(
                "NumericComparison",
                _decorated_expression_sources(str(expr))[index],
                expr,
            )
        )

    for index in range(40):
        left = (
            _condition(index)
            if index % 2
            else bmc_nodes.Active(_string(index, "Root.Left"))
        )
        right = (
            _condition(index + 1)
            if index % 3
            else bmc_nodes.Event(_string(index, "Root.Right"))
        )
        expr = bmc_nodes.CondBinaryOp(
            left, _COND_BINARY_OPS[index % len(_COND_BINARY_OPS)], right
        )
        cases.append(
            _expression_case(
                "CondBinaryOp", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    for index in range(40):
        expr = bmc_nodes.CondConditionalOp(
            _comparison(index),
            _condition(index),
            bmc_nodes.CondUnaryOp("!", _condition(index + 1)),
        )
        cases.append(
            _expression_case(
                "CondConditionalOp",
                _decorated_expression_sources(str(expr))[index],
                expr,
            )
        )

    for index in range(40):
        expr = bmc_nodes.FrameVar(_string(index, "var"))
        cases.append(
            _expression_case(
                "FrameVar", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    for index, source in enumerate(_decorated_expression_sources("cycle")):
        cases.append(_expression_case("Cycle", source, bmc_nodes.Cycle()))

    for index in range(40):
        expr = bmc_nodes.Active(
            _string(index, "Root.State"),
            frame="current" if index % 3 == 0 else index % 8,
        )
        cases.append(
            _expression_case(
                "Active", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    for index in range(40):
        expr = bmc_nodes.Terminated(frame="current" if index % 3 == 0 else index % 8)
        cases.append(
            _expression_case(
                "Terminated", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    for index in range(40):
        expr = bmc_nodes.Event(
            _string(index, "Root.Event"),
            selector="current" if index % 3 == 0 else index % 8,
        )
        cases.append(
            _expression_case(
                "Event", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    for index in range(40):
        expr = bmc_nodes.Case(
            _string(index, "Root.Case"),
            frame="current" if index % 3 == 0 else index % 8,
        )
        cases.append(
            _expression_case(
                "Case", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    for index in range(40):
        expr = bmc_nodes.Called(
            _string(index, "Hook"), frame="current" if index % 3 == 0 else index % 8
        )
        cases.append(
            _expression_case(
                "Called", _decorated_expression_sources(str(expr))[index], expr
            )
        )

    return cases


def _query_node_cases() -> List[NodeParseCase]:
    """Build standalone FBMCQ complete-query cases for query-level nodes.

    :return: Matrix cases.
    :rtype: list

    Example::

        >>> any(case.target == "BmcQuery" for case in _query_node_cases())
        True
    """
    cases: List[NodeParseCase] = []

    for index, initial in enumerate(_initial_specs()):
        query = _query_with_initial(initial, index)
        cases.append(_query_case("InitialSpec", str(query), initial, _query_initial))

    for index, policy in enumerate(_initial_variable_policies()):
        initial = bmc_query_nodes.InitialSpec(variable_policy=policy)
        query = _query_with_initial(initial, index)
        cases.append(
            _query_case(
                "InitialVariablePolicy",
                str(query),
                policy,
                _query_initial_variable_policy,
            )
        )

    for index, assumption in enumerate(_frame_assumptions()):
        query = _query_with_assumption(assumption, index)
        cases.append(
            _query_case(
                "FrameAssumption", str(query), assumption, _query_first_assumption
            )
        )

    for index, assumption in enumerate(_event_assumptions()):
        query = _query_with_assumption(assumption, index)
        cases.append(
            _query_case(
                "EventAssumption", str(query), assumption, _query_first_assumption
            )
        )

    for index, assumption in enumerate(_event_cardinality_assumptions()):
        query = _query_with_assumption(assumption, index)
        cases.append(
            _query_case(
                "EventCardinalityAssumption",
                str(query),
                assumption,
                _query_first_assumption,
            )
        )

    for index, property_node in enumerate(_properties()):
        query = bmc_query_nodes.BmcQuery(property=property_node)
        cases.append(
            _query_case("BmcProperty", str(query), property_node, _query_property)
        )

    for index in range(40):
        query = _complex_query(index)
        cases.append(_query_case("BmcQuery", str(query), query, _root))

    return cases


def _standalone_node_cases() -> List[NodeParseCase]:
    """Return all standalone node parser cases.

    :return: Expression and query matrix cases.
    :rtype: list

    Example::

        >>> len(_standalone_node_cases()) >= 40 * len(_REQUIRED_STANDALONE_NODES)
        True
    """
    return _expression_node_cases() + _query_node_cases()


def _parity_cases() -> List[ParityCase]:
    """Return FCSTM-compatible expression alignment cases.

    :return: Parity matrix cases.
    :rtype: list

    Example::

        >>> len(_parity_cases()) >= 40 * len(_REQUIRED_PARITY_NODES)
        True
    """
    cases: List[ParityCase] = []

    int_expressions = ["0", "00", "01", "001", "42"] + [
        str(index) for index in range(2, 25)
    ]
    int_expressions.extend("0x%X" % index for index in range(1, 14))
    cases.extend(
        ParityCase("IntLiteral", expression, "num")
        for expression in int_expressions[:40]
    )

    float_expressions = ["%d.%d" % (index + 1, index % 10) for index in range(12)]
    float_expressions.extend(".%d" % (index + 1) for index in range(10))
    float_expressions.extend(
        "%de-%d" % (index + 1, index % 5 + 1) for index in range(10)
    )
    float_expressions.extend(
        "%dE+%d" % (index + 1, index % 4 + 1) for index in range(8)
    )
    cases.extend(
        ParityCase("FloatLiteral", expression, "num")
        for expression in float_expressions[:40]
    )

    bool_values = ("true", "True", "TRUE", "false", "False", "FALSE")
    for index in range(40):
        raw = bool_values[index % len(bool_values)]
        expression = raw if index % 2 == 0 else "(%s)" % raw
        cases.append(ParityCase("BoolLiteral", expression, "cond"))

    for index in range(40):
        cases.append(ParityCase("NameRef", "var_%d" % index, "num"))

    const_values = ("pi", "E", "tau")
    for index in range(40):
        expression = const_values[index % len(const_values)]
        if index % 2:
            expression = "(%s)" % expression
        cases.append(ParityCase("MathConst", expression, "num"))

    for index in range(40):
        operand = "var_%d" % index if index % 3 else "(var_%d + 1)" % index
        cases.append(
            ParityCase("NumUnaryOp", "%s%s" % (("+", "-")[index % 2], operand), "num")
        )

    for index in range(40):
        left = "a_%d" % index
        right = "b_%d + %d" % (index, index + 1) if index % 2 else "b_%d" % index
        cases.append(
            ParityCase(
                "NumBinaryOp",
                "%s %s %s"
                % (left, _NUM_BINARY_OPS[index % len(_NUM_BINARY_OPS)], right),
                "num",
            )
        )

    for index in range(40):
        cases.append(
            ParityCase(
                "NumConditionalOp",
                "((x_%d + 1) >= y_%d) ? (a_%d + b_%d) : (c_%d * d_%d)"
                % (index, index, index, index, index, index),
                "num",
            )
        )

    for index in range(40):
        operand = "-x_%d" % index if index % 3 == 0 else "x_%d + 1" % index
        cases.append(
            ParityCase(
                "UFuncCall",
                "%s(%s)" % (_UFUNC_NAMES[index % len(_UFUNC_NAMES)], operand),
                "num",
            )
        )

    for index in range(40):
        op = "!" if index % 2 == 0 else "not "
        cases.append(
            ParityCase(
                "CondUnaryOp", "%s(x_%d > 0 && y_%d > 0)" % (op, index, index), "cond"
            )
        )

    for index in range(40):
        expression = "(x_%d + 1) %s sqrt(y_%d)" % (
            index,
            _NUM_COMPARE_OPS[index % len(_NUM_COMPARE_OPS)],
            index,
        )
        cases.append(ParityCase("NumericComparison", expression, "cond"))

    cond_ops = ("&&", "and", "||", "or", "xor", "=>", "implies", "iff", "==", "!=")
    for index in range(40):
        left = "x_%d > 0" % index
        right = "y_%d <= z_%d" % (index, index)
        cases.append(
            ParityCase(
                "CondBinaryOp",
                "(%s) %s (%s)" % (left, cond_ops[index % len(cond_ops)], right),
                "cond",
            )
        )

    for index in range(40):
        expression = "(x_%d > 0) ? (y_%d > 0 && z_%d > 0) : (a_%d <= b_%d)" % (
            index,
            index,
            index,
            index,
            index,
        )
        cases.append(ParityCase("CondConditionalOp", expression, "cond"))

    return cases


def _complex_query_source(index: int, query: bmc_query_nodes.BmcQuery) -> str:
    """Return a nontrivial source variant for a complex query object.

    :param index: Case index.
    :type index: int
    :param query: Query object whose semantics should be parsed back.
    :type query: pyfcstm.bmc.query.BmcQuery
    :return: Complete FBMCQ source with harmless trivia or operator aliases.
    :rtype: str

    Example::

        >>> _complex_query_source(0, _complex_query(0)).lstrip().startswith('//')
        True
    """
    source = str(query)
    if index % 2 == 0:
        source = source.replace(" && ", " and ", 1)
    if index % 3 == 0:
        source = source.replace(" || ", " or ", 1)
    if index % 4 == 0:
        source = source.replace(" => ", " implies ", 1)
    if index % 5 == 0:
        source = source.replace(
            "\n\n", "\n\n/* integrated matrix case %d */\n" % index, 1
        )
    if index % 7 == 0:
        source = source.replace(
            "check ", "# property clause for case %d\ncheck " % index, 1
        )
    return "// complex fbmcq case %d\n%s\n" % (index, source)


def _complex_query_cases() -> List[ComplexQueryCase]:
    """Return one hundred complete medium/high-complexity query cases.

    :return: Complex integrated query cases.
    :rtype: list

    Example::

        >>> len(_complex_query_cases())
        100
    """
    cases = []
    for index in range(100):
        query = _complex_query(index)
        cases.append(
            ComplexQueryCase(index, _complex_query_source(index, query), query)
        )
    return cases


STANDALONE_NODE_CASES = _standalone_node_cases()
PARITY_CASES = _parity_cases()
COMPLEX_QUERY_CASES = _complex_query_cases()


def _case_counts(cases: Iterable[Any]) -> Dict[str, int]:
    """Count matrix cases by target node name.

    :param cases: Cases with a ``target`` field.
    :type cases: Iterable[object]
    :return: Counts keyed by target name.
    :rtype: Dict[str, int]

    Example::

        >>> _case_counts([ParityCase("IntLiteral", "1", "num")])["IntLiteral"]
        1
    """
    counts: Dict[str, int] = {}
    for case in cases:
        counts[case.target] = counts.get(case.target, 0) + 1
    return counts


def _round_trip_canonical(value: Any) -> Any:
    """Return canonical data normalized for canonical-text round trips.

    :param value: Canonical dictionary/list/scalar or object with
        ``to_canonical``.
    :type value: object
    :return: Canonical value with spelling-only boolean raw casing normalized.
    :rtype: object

    Example::

        >>> _round_trip_canonical(bmc_nodes.BoolLiteral("TRUE"))["raw"]
        'true'
    """
    if hasattr(value, "to_canonical"):
        value = value.to_canonical()
    if isinstance(value, dict):
        normalized = {key: _round_trip_canonical(child) for key, child in value.items()}
        if normalized.get("node") == "bool_literal" and "raw" in normalized:
            normalized["raw"] = str(normalized["raw"]).lower()
        return normalized
    if isinstance(value, list):
        return [_round_trip_canonical(child) for child in value]
    return value


def _canonical_node_count(value: Any) -> int:
    """Count nested canonical dictionaries that carry a ``node`` tag.

    :param value: Canonical dictionary/list/scalar.
    :type value: object
    :return: Number of node-tagged dictionaries in ``value``.
    :rtype: int

    Example::

        >>> _canonical_node_count({"node": "x", "child": {"node": "y"}})
        2
    """
    if isinstance(value, dict):
        current = 1 if "node" in value else 0
        return current + sum(_canonical_node_count(child) for child in value.values())
    if isinstance(value, list):
        return sum(_canonical_node_count(child) for child in value)
    return 0


@pytest.mark.unittest
def test_standalone_fbmcq_matrix_has_forty_cases_per_concrete_node():
    """Every concrete parser node has at least forty standalone FBMCQ cases."""
    counts = _case_counts(STANDALONE_NODE_CASES)

    assert set(counts) == set(_REQUIRED_STANDALONE_NODES)
    assert all(counts[node] >= 40 for node in _REQUIRED_STANDALONE_NODES)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "case",
    STANDALONE_NODE_CASES,
    ids=lambda case: "%s:%s" % (case.target, case.source.replace("\n", "\\n")[:48]),
)
def test_standalone_fbmcq_matrix_parses_expected_ast_node(case: NodeParseCase):
    """Standalone FBMCQ cases parse to the exact expected canonical node."""
    parsed_root = _parse_entry(case.entry, case.source)
    parsed_node = case.selector(parsed_root)

    assert parsed_node.__class__ is case.expected.__class__
    assert _canonical(parsed_node) == _canonical(case.expected)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "case",
    STANDALONE_NODE_CASES,
    ids=lambda case: "%s:%s" % (case.target, case.source.replace("\n", "\\n")[:48]),
)
def test_standalone_fbmcq_matrix_round_trips_through_canonical_text(
    case: NodeParseCase,
):
    """Every standalone matrix case round-trips through ``str(node)``."""
    parsed_root = _parse_entry(case.entry, case.source)
    parsed_node = case.selector(parsed_root)
    if case.entry == "query":
        canonical_text = str(parsed_root)
        reparsed_root = parse_bmc_query(canonical_text)
        reparsed_node = case.selector(reparsed_root)
    else:
        canonical_text = str(parsed_node)
        reparsed_node = _parse_entry(case.entry, canonical_text)

    assert reparsed_node.__class__ is parsed_node.__class__
    assert _round_trip_canonical(reparsed_node) == _round_trip_canonical(parsed_node)


@pytest.mark.unittest
def test_fcstm_fbmcq_parity_matrix_has_forty_cases_per_compatible_node():
    """Every FCSTM-compatible expression node has forty strict parity cases."""
    counts = _case_counts(PARITY_CASES)

    assert set(counts) == set(_REQUIRED_PARITY_NODES)
    assert all(counts[node] >= 40 for node in _REQUIRED_PARITY_NODES)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "case",
    PARITY_CASES,
    ids=lambda case: "%s:%s" % (case.target, case.expression[:60]),
)
def test_fcstm_fbmcq_parity_matrix_aligns_ast_shapes(case: ParityCase):
    """FCSTM and FBMCQ expression parsers produce bidirectionally aligned ASTs."""
    if case.category == "num":
        fcstm_node = parse_with_grammar_entry(case.expression, "num_expression")
        bmc_node = parse_bmc_num_expression(case.expression)
    else:
        fcstm_node = parse_with_grammar_entry(case.expression, "cond_expression")
        bmc_node = parse_bmc_cond_expression(case.expression)

    converted_bmc = _fcstm_to_bmc_expr(fcstm_node, case.category)
    converted_fcstm = _bmc_to_fcstm_expr(bmc_node)

    assert converted_bmc.__class__.__name__ == case.target
    assert bmc_node.__class__.__name__ == case.target
    assert _shared_shape_from_bmc(converted_bmc) == _shared_shape_from_bmc(bmc_node)
    assert _shared_shape_from_fcstm(
        converted_fcstm, case.category
    ) == _shared_shape_from_fcstm(fcstm_node, case.category)


@pytest.mark.unittest
def test_complex_query_matrix_has_one_hundred_integrated_cases():
    """The integrated matrix contains exactly one hundred complex query files."""
    assert len(COMPLEX_QUERY_CASES) == 100


@pytest.mark.unittest
@pytest.mark.parametrize(
    "case",
    COMPLEX_QUERY_CASES,
    ids=lambda case: "complex-%03d" % case.case_index,
)
def test_complex_query_matrix_parses_expected_tree(case: ComplexQueryCase):
    """Complex complete FBMCQ files parse into the exact expected AST tree."""
    parsed = parse_bmc_query(case.source)

    assert parsed.to_canonical() == case.expected.to_canonical()
    assert len(parsed.assumptions) >= 5
    assert _canonical_node_count(parsed.to_canonical()) >= 50


@pytest.mark.unittest
@pytest.mark.parametrize(
    "case",
    COMPLEX_QUERY_CASES,
    ids=lambda case: "complex-round-trip-%03d" % case.case_index,
)
def test_complex_query_matrix_round_trips_canonical_text(case: ComplexQueryCase):
    """Complex complete FBMCQ files survive canonical string round-trip."""
    parsed = parse_bmc_query(case.source)
    canonical_text = str(parsed)
    reparsed = parse_bmc_query(canonical_text)

    assert _round_trip_canonical(reparsed) == _round_trip_canonical(parsed)
