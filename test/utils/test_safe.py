from unittest.mock import patch

import pytest

from pyfcstm.utils import sequence_safe


@pytest.fixture
def valid_string_segments():
    return ["CamelCase", "snake_case", "kebab-case"]


@pytest.fixture
def empty_segments():
    return []


@pytest.fixture
def single_segment():
    return ["SingleWord"]


@pytest.fixture
def segments_with_numbers():
    return ["Test123", "number456Test"]


@pytest.fixture
def segments_with_special_chars():
    return ["Test@#$", "Special!Chars"]


@pytest.fixture
def segments_with_multiple_underscores():
    return ["test___multiple", "under____scores"]


@pytest.fixture
def mixed_case_segments():
    return ["XMLHttpRequest", "HTMLParser", "JSONData"]


@pytest.fixture
def segments_with_spaces():
    return ["test with spaces", "another test"]


@pytest.fixture
def non_string_sequence():
    return [123, 456, 789]


@pytest.fixture
def empty_string_segments():
    return ["", "", ""]


@pytest.mark.unittest
class TestSequenceSafe:

    def test_valid_string_segments(self, valid_string_segments):
        result = sequence_safe(valid_string_segments)
        assert isinstance(result, str)
        assert '__' in result

    def test_empty_segments(self, empty_segments):
        result = sequence_safe(empty_segments)
        assert result == ""

    def test_single_segment(self, single_segment):
        result = sequence_safe(single_segment)
        assert result == "single_word"

    def test_segments_with_numbers(self, segments_with_numbers):
        result = sequence_safe(segments_with_numbers)
        assert '__' in result
        assert result.count('__') == 1

    def test_segments_with_special_chars(self, segments_with_special_chars):
        result = sequence_safe(segments_with_special_chars)
        assert '__' in result

    def test_segments_with_multiple_underscores(self, segments_with_multiple_underscores):
        result = sequence_safe(segments_with_multiple_underscores)
        assert '___' not in result
        assert '__' in result

    def test_mixed_case_segments(self, mixed_case_segments):
        result = sequence_safe(mixed_case_segments)
        assert 'xml_http_request' in result
        assert 'html_parser' in result
        assert 'json_data' in result

    def test_segments_with_spaces(self, segments_with_spaces):
        result = sequence_safe(segments_with_spaces)
        assert '__' in result

    def test_empty_string_segments(self, empty_string_segments):
        result = sequence_safe(empty_string_segments)
        assert result == "____"

    @patch('pyfcstm.utils.safe.underscore')
    def test_underscore_function_called(self, mock_underscore, valid_string_segments):
        mock_underscore.side_effect = lambda x: x.lower()
        sequence_safe(valid_string_segments)
        assert mock_underscore.call_count == len(valid_string_segments)

    def test_regex_substitution_multiple_underscores(self):
        segments = ["test"]
        with patch('pyfcstm.utils.safe.underscore', return_value='test___multiple____underscores'):
            result = sequence_safe(segments)
            assert result == "test_multiple_underscores"

    def test_regex_substitution_single_underscore(self):
        segments = ["test"]
        with patch('pyfcstm.utils.safe.underscore', return_value='test_single_underscore'):
            result = sequence_safe(segments)
            assert result == "test_single_underscore"

    def test_regex_substitution_no_underscores(self):
        segments = ["test"]
        with patch('pyfcstm.utils.safe.underscore', return_value='testnounderscores'):
            result = sequence_safe(segments)
            assert result == "testnounderscores"

    def test_map_function_application(self):
        segments = ["Test1", "Test2"]
        with patch('pyfcstm.utils.safe.underscore', side_effect=['test_1', 'test_2']):
            result = sequence_safe(segments)
            assert result == "test_1__test_2"

    def test_join_with_double_underscore(self):
        segments = ["a", "b", "c"]
        with patch('pyfcstm.utils.safe.underscore', side_effect=['a', 'b', 'c']):
            result = sequence_safe(segments)
            assert result == "a__b__c"
