from unittest.mock import patch

import pytest

from pyfcstm.utils.doc import format_multiline_comment


@pytest.fixture
def sample_raw_doc():
    return """
    /**
     * This is a sample
     * multiline comment
     * with varying indentation
     */
    """


@pytest.fixture
def expected_formatted_doc():
    return "* This is a sample\n* multiline comment\n* with varying indentation"


@pytest.fixture
def sample_raw_doc_2():
    return """
    /*
    This is a sample
        * multiline comment
        * with varying indentation
     */
    """


@pytest.fixture
def expected_formatted_doc_2():
    return "This is a sample\n    * multiline comment\n    * with varying indentation"


@pytest.mark.unittest
class TestFormatMultilineComment:
    def test_basic_formatting(self, sample_raw_doc, expected_formatted_doc, text_aligner):
        result = format_multiline_comment(sample_raw_doc)
        text_aligner.assert_equal(
            expect=expected_formatted_doc,
            actual=result,
        )

    def test_basic_formatting_2(self, sample_raw_doc_2, expected_formatted_doc_2, text_aligner):
        result = format_multiline_comment(sample_raw_doc_2)
        text_aligner.assert_equal(
            expect=expected_formatted_doc_2,
            actual=result,
        )

    def test_empty_comment(self):
        result = format_multiline_comment("/**/")
        assert result == ""

    def test_single_line_comment(self):
        result = format_multiline_comment("/* Single line comment */")
        assert result == "Single line comment"

    def test_multiple_asterisks(self):
        result = format_multiline_comment("/*** Multiple asterisks ***/")
        assert result == "Multiple asterisks"

    def test_no_closing_marker(self):
        result = format_multiline_comment("/* No closing marker")
        assert result == "No closing marker"

    def test_no_opening_marker(self):
        result = format_multiline_comment("No opening marker */")
        assert result == "No opening marker"

    def test_extra_whitespace(self):
        raw_doc = """
        /*
            Extra
                Whitespace
        */
        """
        expected = "Extra\n    Whitespace"
        result = format_multiline_comment(raw_doc)
        assert result == expected

    def test_empty_lines_removal(self):
        raw_doc = """
        /*

        Content with empty lines

        */
        """
        expected = "Content with empty lines"
        result = format_multiline_comment(raw_doc)
        assert result == expected

    @patch('os.linesep', '\r\n')
    def test_different_line_separator(self, sample_raw_doc):
        result = format_multiline_comment(sample_raw_doc)
        assert '\r\n' in result

    def test_unicode_characters(self):
        raw_doc = "/* Unicode: áéíóú */"
        result = format_multiline_comment(raw_doc)
        assert result == "Unicode: áéíóú"
