"""Canonical text round-trip tests for FBMCQ parser outputs.

These tests make the parser object's string contract directly auditable:
every case parses source text into an AST/query object, checks the exact
canonical ``.fbmcq`` text returned by :func:`str`, reparses that text, and
requires the second stringification to stay byte-for-byte stable.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, NamedTuple

import pytest

from pyfcstm.bmc.parse import (
    parse_bmc_cond_expression,
    parse_bmc_num_expression,
    parse_bmc_query,
)


class TextRoundTripCase(NamedTuple):
    """One parser text round-trip case.

    :param entry: Parser entry category: ``"num"``, ``"cond"``, or ``"query"``.
    :type entry: str
    :param source: Original source text accepted by the parser.
    :type source: str
    :param expected_text: Exact canonical text expected from ``str(parsed)``.
    :type expected_text: str

    Example::

        >>> TextRoundTripCase("num", "1", "1").entry
        'num'
    """

    entry: str
    source: str
    expected_text: str


def _parse_case(case: TextRoundTripCase) -> Any:
    """Parse a text round-trip case through its selected public entry.

    :param case: Round-trip case descriptor.
    :type case: TextRoundTripCase
    :return: Parsed AST/query object.
    :rtype: object

    Example::

        >>> _parse_case(TextRoundTripCase("num", "1", "1")).to_canonical()["value"]
        1
    """
    parsers: Dict[str, Callable[[str], Any]] = {
        "num": parse_bmc_num_expression,
        "cond": parse_bmc_cond_expression,
        "query": parse_bmc_query,
    }
    return parsers[case.entry](case.source)


def _round_trip_canonical(value: Any) -> Any:
    """Return canonical data normalized for canonical-text round trips.

    :param value: Object with ``to_canonical`` or JSON-like canonical data.
    :type value: object
    :return: Canonical data with spelling-only boolean raw casing normalized.
    :rtype: object

    Example::

        >>> _round_trip_canonical(parse_bmc_cond_expression("TRUE"))["raw"]
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


NUMERIC_TEXT_ROUND_TRIP_CASES: List[TextRoundTripCase] = [
    TextRoundTripCase("num", "0", "0"),
    TextRoundTripCase("num", "00", "00"),
    TextRoundTripCase("num", "001", "001"),
    TextRoundTripCase("num", "42", "42"),
    TextRoundTripCase("num", "0x1", "0x1"),
    TextRoundTripCase("num", "0x2A", "0x2A"),
    TextRoundTripCase("num", "1.0", "1.0"),
    TextRoundTripCase("num", ".5", ".5"),
    TextRoundTripCase("num", "5.", "5."),
    TextRoundTripCase("num", "1e-3", "1e-3"),
    TextRoundTripCase("num", "2E+4", "2E+4"),
    TextRoundTripCase("num", "counter", "counter"),
    TextRoundTripCase("num", "var_7", "var_7"),
    TextRoundTripCase("num", "pi", "pi"),
    TextRoundTripCase("num", "E", "E"),
    TextRoundTripCase("num", "tau", "tau"),
    TextRoundTripCase("num", "+counter", "+counter"),
    TextRoundTripCase("num", "-counter", "-counter"),
    TextRoundTripCase("num", "-(counter + 1)", "-(counter + 1)"),
    TextRoundTripCase("num", "counter + 1", "counter + 1"),
    TextRoundTripCase("num", "counter - 1", "counter - 1"),
    TextRoundTripCase("num", "counter * 2", "counter * 2"),
    TextRoundTripCase("num", "counter / 2", "counter / 2"),
    TextRoundTripCase("num", "counter % 2", "counter % 2"),
    TextRoundTripCase("num", "counter << 1", "counter << 1"),
    TextRoundTripCase("num", "counter >> 1", "counter >> 1"),
    TextRoundTripCase("num", "counter & 3", "counter & 3"),
    TextRoundTripCase("num", "counter ^ 3", "counter ^ 3"),
    TextRoundTripCase("num", "counter | 3", "counter | 3"),
    TextRoundTripCase("num", "counter ** 2", "counter ** 2"),
    TextRoundTripCase("num", "(counter + 1) * 2", "(counter + 1) * 2"),
    TextRoundTripCase("num", "counter * (limit + 1)", "counter * (limit + 1)"),
    TextRoundTripCase("num", "sqrt(counter)", "sqrt(counter)"),
    TextRoundTripCase("num", "sin(counter + 1)", "sin(counter + 1)"),
    TextRoundTripCase("num", 'log1p(var("x"))', 'log1p(var("x"))'),
    TextRoundTripCase("num", 'var("counter")', 'var("counter")'),
    TextRoundTripCase("num", 'var("变量")', 'var("变量")'),
    TextRoundTripCase("num", "cycle", "cycle"),
    TextRoundTripCase("num", "cycle + 1", "cycle + 1"),
    TextRoundTripCase(
        "num", '(active("Root.A")) ? 1 : 0', '(active("Root.A")) ? 1 : 0'
    ),
    TextRoundTripCase(
        "num",
        '(cycle <= 3) ? var("x") + 1 : sqrt(var("y"))',
        '(cycle <= 3) ? (var("x") + 1) : sqrt(var("y"))',
    ),
]

CONDITION_TEXT_ROUND_TRIP_CASES: List[TextRoundTripCase] = [
    TextRoundTripCase("cond", "true", "true"),
    TextRoundTripCase("cond", "TRUE", "true"),
    TextRoundTripCase("cond", "False", "false"),
    TextRoundTripCase("cond", "counter < 3", "counter < 3"),
    TextRoundTripCase("cond", "counter > 3", "counter > 3"),
    TextRoundTripCase("cond", "counter <= 3", "counter <= 3"),
    TextRoundTripCase("cond", "counter >= 3", "counter >= 3"),
    TextRoundTripCase("cond", "counter == 3", "counter == 3"),
    TextRoundTripCase("cond", "counter != 3", "counter != 3"),
    TextRoundTripCase("cond", 'var("x") <= cycle', 'var("x") <= cycle'),
    TextRoundTripCase("cond", 'active("Root.A")', 'active("Root.A")'),
    TextRoundTripCase("cond", 'active("Root.A", current)', 'active("Root.A")'),
    TextRoundTripCase("cond", 'active("Root.A", 2)', 'active("Root.A", 2)'),
    TextRoundTripCase("cond", 'active("Root.\\"A\\"")', 'active("Root.\\"A\\"")'),
    TextRoundTripCase("cond", "terminated()", "terminated()"),
    TextRoundTripCase("cond", "terminated(current)", "terminated()"),
    TextRoundTripCase("cond", "terminated(4)", "terminated(4)"),
    TextRoundTripCase(
        "cond", 'event("Root.Start", current)', 'event("Root.Start", current)'
    ),
    TextRoundTripCase("cond", 'event("Root.Start", 3)', 'event("Root.Start", 3)'),
    TextRoundTripCase("cond", 'case("safe")', 'case("safe")'),
    TextRoundTripCase("cond", 'case("safe", current)', 'case("safe")'),
    TextRoundTripCase("cond", 'case("safe", 5)', 'case("safe", 5)'),
    TextRoundTripCase("cond", 'called("Hook")', 'called("Hook")'),
    TextRoundTripCase("cond", 'called("Hook", current)', 'called("Hook")'),
    TextRoundTripCase("cond", 'called("Hook", 6)', 'called("Hook", 6)'),
    TextRoundTripCase("cond", '!active("Root.A")', '!active("Root.A")'),
    TextRoundTripCase("cond", 'not active("Root.A")', '!active("Root.A")'),
    TextRoundTripCase(
        "cond", '!(active("Root.A") && true)', '!(active("Root.A") && true)'
    ),
    TextRoundTripCase(
        "cond", 'active("A") && active("B")', 'active("A") && active("B")'
    ),
    TextRoundTripCase(
        "cond", 'active("A") and active("B")', 'active("A") && active("B")'
    ),
    TextRoundTripCase(
        "cond", 'active("A") || active("B")', 'active("A") || active("B")'
    ),
    TextRoundTripCase(
        "cond", 'active("A") or active("B")', 'active("A") || active("B")'
    ),
    TextRoundTripCase(
        "cond", 'active("A") xor active("B")', 'active("A") xor active("B")'
    ),
    TextRoundTripCase(
        "cond", 'active("A") => active("B")', 'active("A") => active("B")'
    ),
    TextRoundTripCase(
        "cond", 'active("A") implies active("B")', 'active("A") => active("B")'
    ),
    TextRoundTripCase(
        "cond", 'active("A") iff active("B")', 'active("A") iff active("B")'
    ),
    TextRoundTripCase(
        "cond", 'active("A") == active("B")', 'active("A") == active("B")'
    ),
    TextRoundTripCase(
        "cond", 'active("A") != active("B")', 'active("A") != active("B")'
    ),
    TextRoundTripCase(
        "cond",
        '(active("A") && active("B")) || active("C")',
        '(active("A") && active("B")) || active("C")',
    ),
    TextRoundTripCase(
        "cond",
        'active("A") && (active("B") || active("C"))',
        'active("A") && (active("B") || active("C"))',
    ),
    TextRoundTripCase(
        "cond",
        '(cycle <= 3) ? active("A") : active("B")',
        '(cycle <= 3) ? active("A") : active("B")',
    ),
    TextRoundTripCase(
        "cond",
        '(active("A")) ? (cycle <= 2) : (var("x") >= 1)',
        '(active("A")) ? cycle <= 2 : var("x") >= 1',
    ),
]

QUERY_TEXT_ROUND_TRIP_CASES: List[TextRoundTripCase] = [
    TextRoundTripCase(
        "query", "check reach <= 1: true;", "init cold;\n\ncheck reach <= 1: true;"
    ),
    TextRoundTripCase(
        "query",
        "init cold; check forbid <= 2: false;",
        "init cold;\n\ncheck forbid <= 2: false;",
    ),
    TextRoundTripCase(
        "query",
        "init terminated; check invariant <= 3: terminated(current);",
        "init terminated;\n\ncheck invariant <= 3: terminated();",
    ),
    TextRoundTripCase(
        "query",
        'init state("Root.A"); check reach <= 4: active("Root.B", current);',
        'init state("Root.A");\n\ncheck reach <= 4: active("Root.B");',
    ),
    TextRoundTripCase(
        "query",
        'init state("Root.A") where var("x") == 0; check reach <= 5: active("Root.B");',
        'init state("Root.A") where var("x") == 0;\n\ncheck reach <= 5: active("Root.B");',
    ),
    TextRoundTripCase(
        "query",
        'assume always: cycle <= 10; check reach <= 10: active("Done");',
        'init cold;\n\nassume always: cycle <= 10;\n\ncheck reach <= 10: active("Done");',
    ),
    TextRoundTripCase(
        "query",
        'assume at 02: active("Ready", current); check forbid <= 3: active("Bad");',
        'init cold;\n\nassume at 2: active("Ready");\n\ncheck forbid <= 3: active("Bad");',
    ),
    TextRoundTripCase(
        "query",
        'assume event("Tick", *) == false; check reach <= 1: true;',
        'init cold;\n\nassume event("Tick", *) == false;\n\ncheck reach <= 1: true;',
    ),
    TextRoundTripCase(
        "query",
        'assume event("Reset", 01 .. 03) != false; check reach <= 1: true;',
        'init cold;\n\nassume event("Reset", 1..3) == true;\n\ncheck reach <= 1: true;',
    ),
    TextRoundTripCase(
        "query",
        'assume event("Point", 007) == TRUE; check reach <= 1: true;',
        'init cold;\n\nassume event("Point", 7) == true;\n\ncheck reach <= 1: true;',
    ),
    TextRoundTripCase(
        "query",
        "assume events cardinality any; check reach <= 1: true;",
        "init cold;\n\nassume events cardinality any;\n\ncheck reach <= 1: true;",
    ),
    TextRoundTripCase(
        "query",
        'assume events cardinality at_most_one {"A", "B"}; check reach <= 1: true;',
        'init cold;\n\nassume events cardinality at_most_one {\n    "A",\n    "B"\n};\n\ncheck reach <= 1: true;',
    ),
    TextRoundTripCase(
        "query",
        'check must_reach <= 6: called("Hook", current);',
        'init cold;\n\ncheck must_reach <= 6: called("Hook");',
    ),
    TextRoundTripCase(
        "query",
        'check exists_always <= 7: case("safe", 2);',
        'init cold;\n\ncheck exists_always <= 7: case("safe", 2);',
    ),
    TextRoundTripCase(
        "query",
        'check cover <= 8: event("E", current);',
        'init cold;\n\ncheck cover <= 8: event("E", current);',
    ),
    TextRoundTripCase(
        "query",
        'check response <= 9: trigger event("Fault", current) -> within 3 active("Recover", current);',
        'init cold;\n\ncheck response <= 9:\n    trigger event("Fault", current)\n    -> within 3 active("Recover");',
    ),
    TextRoundTripCase(
        "query",
        'init state("Root.Idle") where var("counter") == 0; assume always: cycle <= 10; assume at 2: active("Root.Ready", 2); check reach <= 10: active("Root.Done");',
        'init state("Root.Idle") where var("counter") == 0;\n\nassume always: cycle <= 10;\n\nassume at 2: active("Root.Ready", 2);\n\ncheck reach <= 10: active("Root.Done");',
    ),
    TextRoundTripCase(
        "query",
        'assume always: (active("A") and !active("B")); assume event("Start", 0..2) == true; check invariant <= 4: active("A") implies !active("Bad");',
        'init cold;\n\nassume always: active("A") && !active("B");\n\nassume event("Start", 0..2) == true;\n\ncheck invariant <= 4: active("A") => !active("Bad");',
    ),
    TextRoundTripCase(
        "query",
        'assume events cardinality at_most_one {"Tick", "Reset", "Stop"}; check forbid <= 5: (cycle <= 4) ? active("Bad") : false;',
        'init cold;\n\nassume events cardinality at_most_one {\n    "Tick",\n    "Reset",\n    "Stop"\n};\n\ncheck forbid <= 5: (cycle <= 4) ? active("Bad") : false;',
    ),
]

TEXT_ROUND_TRIP_CASES = (
    NUMERIC_TEXT_ROUND_TRIP_CASES
    + CONDITION_TEXT_ROUND_TRIP_CASES
    + QUERY_TEXT_ROUND_TRIP_CASES
)


@pytest.mark.unittest
def test_text_round_trip_case_count_is_intentionally_large():
    """The direct text round-trip suite stays broad enough to catch drift."""
    assert len(NUMERIC_TEXT_ROUND_TRIP_CASES) >= 40
    assert len(CONDITION_TEXT_ROUND_TRIP_CASES) >= 40
    assert len(QUERY_TEXT_ROUND_TRIP_CASES) >= 18
    assert len(TEXT_ROUND_TRIP_CASES) >= 100


@pytest.mark.unittest
@pytest.mark.parametrize(
    "case",
    TEXT_ROUND_TRIP_CASES,
    ids=lambda case: "%s:%s" % (case.entry, case.source.replace("\n", "\\n")[:72]),
)
def test_parsed_fbmcq_nodes_stringify_to_reparseable_canonical_text(
    case: TextRoundTripCase,
):
    """Parsed AST/query objects stringify to exact, stable, reparseable DSL text."""
    parsed = _parse_case(case)
    canonical_text = str(parsed)

    assert canonical_text == case.expected_text

    reparsed = _parse_case(
        TextRoundTripCase(case.entry, canonical_text, canonical_text)
    )
    assert str(reparsed) == canonical_text
    assert _round_trip_canonical(reparsed) == _round_trip_canonical(parsed)
