import pytest

from pyfcstm.utils import (
    aggregate_documentation,
    format_multiline_comment,
    validate_documentation_for_export,
)

pytestmark = pytest.mark.unittest


NORMAL_GOLDENS = (
    ("empty", "/* */", "", "/*\n */"),
    ("single", "/* text */", "text", "/*\n * text\n */"),
    ("single_star", "/* * item */", "* item", "/*\n * * item\n */"),
    ("star_multi", "/*\n * A\n * B\n */", "A\nB", "/*\n * A\n * B\n */"),
    ("inline_head", "/* A\n * B\n */", "A\nB", "/*\n * A\n * B\n */"),
    ("plain_indent", "/*\n    A\n      B\n*/", "A\n  B", "/*\n * A\n *   B\n */"),
    ("star_bullets", "/*\n * * one\n * * two\n */", "* one\n* two", "/*\n * * one\n * * two\n */"),
    ("tail_spaces", "/*\n * A  \n * B\n */", "A  \nB", "/*\n * A  \n * B\n */"),
    ("internal_blank_lines", "/*\n * A\n *\n *\n * B\n */", "A\n\n\nB", "/*\n * A\n *\n *\n * B\n */"),
    ("literal_star", "/*\n * *\n */", "*", "/*\n * *\n */"),
    ("blank_line_no_margin", "/*\n * A\n\n * B\n */", "A\n\nB", "/*\n * A\n *\n * B\n */"),
    ("bare_margin_only", "/*\n *\n */", "", "/*\n */"),
    ("blank_after_margin_strip", "/*\n *\n * A\n */", "A", "/*\n * A\n */"),
    ("tab_indent", "/*\n\tA\n\t\tB\n*/", "A\n\tB", "/*\n * A\n * \tB\n */"),
)

RECOVERABLE_GOLDENS = (
    ("outer_ws", "\n  /* text */ \n", "text", "/*\n * text\n */"),
    ("crlf", "/*\r\n * A  \r\n * B\r\n */", "A  \nB", "/*\n * A  \n * B\n */"),
    ("lone_cr", "/*\r * A\r * B\r */", "A\nB", "/*\n * A\n * B\n */"),
    ("javadoc", "/** text */", "text", "/*\n * text\n */"),
    ("doxygen", "/*! text */", "text", "/*\n * text\n */"),
    ("extra_open", "/*** text */", "* text", "/*\n * * text\n */"),
    ("extra_close", "/* text **/", "text *", "/*\n * text *\n */"),
    ("extra_open_close", "/*** text ***/", "* text **", "/*\n * * text **\n */"),
    ("mixed_margin", "/*\n * first\nsecond\n */", "* first\nsecond", "/*\n * * first\n * second\n */"),
    ("unaligned_margin", "/*\n * A\n     * B\n */", "A\nB", "/*\n * A\n * B\n */"),
    ("own_line_no_margin", "/*\nA\n * B\n */", "A\n * B", "/*\n * A\n *  * B\n */"),
)

AGGREGATE_GOLDENS = (
    ("empty_input", (), None),
    ("all_none", (None, None), None),
    ("all_empty", ("", ""), ""),
    ("none_then_empty", (None, ""), ""),
    ("empty_dropped_when_text_present", ("", "A", ""), "A"),
    ("none_skipped", (None, "A", None, "B"), "A\n\nB"),
    ("dedup_keeps_first_position", ("A", "A", "B"), "A\n\nB"),
    ("order_follows_input", ("B", "A"), "B\n\nA"),
    ("empty_after_text", ("A", ""), "A"),
)


@pytest.mark.unittest
@pytest.mark.parametrize("case_id, raw, expected, canonical", NORMAL_GOLDENS)
def test_normal_documentation_goldens(case_id, raw, expected, canonical):
    del case_id
    assert format_multiline_comment(raw) == expected
    assert format_multiline_comment(canonical) == expected


@pytest.mark.unittest
@pytest.mark.parametrize("case_id, raw, expected, canonical", RECOVERABLE_GOLDENS)
def test_recoverable_documentation_goldens(case_id, raw, expected, canonical):
    del case_id
    assert format_multiline_comment(raw) == expected
    assert format_multiline_comment(canonical) == expected


@pytest.mark.unittest
@pytest.mark.parametrize("case_id, docs, expected", AGGREGATE_GOLDENS)
def test_documentation_aggregation(case_id, docs, expected):
    del case_id
    assert aggregate_documentation(docs) == expected
    if expected is not None:
        validate_documentation_for_export(expected)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "raw, error, fragment",
    (
        ("text */", ValueError, "complete"),
        ("/* text", ValueError, "complete"),
        ("/* text */ trailing", ValueError, "terminator"),
        ("/* outer /* inner */ outer */", ValueError, "terminator"),
        ("/*\n * a /* b\n */", ValueError, "/*"),
        (123, TypeError, "str"),
    ),
)
def test_documentation_helper_errors(raw, error, fragment):
    with pytest.raises(error, match=fragment):
        format_multiline_comment(raw)


@pytest.mark.unittest
@pytest.mark.parametrize(
    "doc, fragment",
    (
        (" ", "boundary"),
        (" text", "boundary"),
        ("text  ", "boundary"),
        ("\ntext", "boundary"),
        ("text\n", "boundary"),
        ("text */ more", r"\*/"),
        ("A\n   \nB", "whitespace-only"),
        ("a\rb", "CR"),
        ("text /* more", "/*"),
    ),
)
def test_documentation_export_errors(doc, fragment):
    with pytest.raises(ValueError, match=fragment):
        validate_documentation_for_export(doc)


def test_documentation_normalizes_lf_without_unittest(monkeypatch):
    monkeypatch.delenv("UNITTEST", raising=False)
    assert format_multiline_comment("/*\r\n * A\r * B\r\n */") == "A\nB"


def test_unicode_documentation_is_opaque():
    assert format_multiline_comment("/* Unicode: áéíóú */") == "Unicode: áéíóú"
