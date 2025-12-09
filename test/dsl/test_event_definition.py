import pytest

from pyfcstm.dsl import parse_with_grammar_entry, GrammarParseError, EventDefinition


@pytest.mark.unittest
class TestDSLEventDefinition:
    @pytest.mark.parametrize(
        ["input_text", "expected"],
        [
            (
                    """
                    event myEvent;
                    """,
                    EventDefinition(name='myEvent', extra_name=None)
            ),  # Simple event definition without named clause
            (
                    """
                    event onClick;
                    """,
                    EventDefinition(name='onClick', extra_name=None)
            ),  # Event with camelCase name
            (
                    """
                    event button_click;
                    """,
                    EventDefinition(name='button_click', extra_name=None)
            ),  # Event with underscore in name
            (
                    """
                    event EVENT_NAME;
                    """,
                    EventDefinition(name='EVENT_NAME', extra_name=None)
            ),  # Event with uppercase name
            (
                    """
                    event _privateEvent;
                    """,
                    EventDefinition(name='_privateEvent', extra_name=None)
            ),  # Event starting with underscore
            (
                    """
                    event event123;
                    """,
                    EventDefinition(name='event123', extra_name=None)
            ),  # Event name with numbers
            (
                    """
                    event a;
                    """,
                    EventDefinition(name='a', extra_name=None)
            ),  # Single character event name
            (
                    """
                    event myEvent named "My Event";
                    """,
                    EventDefinition(name='myEvent', extra_name='My Event')
            ),  # Event with named clause using double quotes
            (
                    """
                    event onClick named "Button Click Event";
                    """,
                    EventDefinition(name='onClick', extra_name='Button Click Event')
            ),  # Event with descriptive name in double quotes
            (
                    """
                    event userInput named "User Input Handler";
                    """,
                    EventDefinition(name='userInput', extra_name='User Input Handler')
            ),  # Event with space-separated description
            (
                    """
                    event errorOccurred named "Error has occurred!";
                    """,
                    EventDefinition(name='errorOccurred', extra_name='Error has occurred!')
            ),  # Event with punctuation in description
            (
                    """
                    event dataReady named "";
                    """,
                    EventDefinition(name='dataReady', extra_name='')
            ),  # Event with empty string description
            (
                    """
                    event testEvent named "Event with \\"escaped\\" quotes";
                    """,
                    EventDefinition(name='testEvent', extra_name='Event with "escaped" quotes')
            ),  # Event with escaped quotes in description
            (
                    """
                    event fileEvent named "File\\nNew\\tLine";
                    """,
                    EventDefinition(name='fileEvent', extra_name='File\nNew\tLine')
            ),  # Event with escape sequences
            (
                    """
                    event myEvent named 'My Event';
                    """,
                    EventDefinition(name='myEvent', extra_name='My Event')
            ),  # Event with named clause using single quotes
            (
                    """
                    event onClick named 'Button Click Event';
                    """,
                    EventDefinition(name='onClick', extra_name='Button Click Event')
            ),  # Event with descriptive name in single quotes
            (
                    """
                    event userInput named 'User Input Handler';
                    """,
                    EventDefinition(name='userInput', extra_name='User Input Handler')
            ),  # Event with space-separated description in single quotes
            (
                    """
                    event errorOccurred named 'Error has occurred!';
                    """,
                    EventDefinition(name='errorOccurred', extra_name='Error has occurred!')
            ),  # Event with punctuation in single quotes
            (
                    """
                    event dataReady named '';
                    """,
                    EventDefinition(name='dataReady', extra_name='')
            ),  # Event with empty string in single quotes
            (
                    """
                    event testEvent named 'Event with \\'escaped\\' quotes';
                    """,
                    EventDefinition(name='testEvent', extra_name="Event with 'escaped' quotes")
            ),  # Event with escaped single quotes
            (
                    """
                    event mixedEvent named 'Contains "double" quotes';
                    """,
                    EventDefinition(name='mixedEvent', extra_name='Contains "double" quotes')
            ),  # Event with double quotes inside single quotes

        ]
    )
    def test_positive_cases(self, input_text, expected):
        assert parse_with_grammar_entry(input_text, entry_name="event_definition") == expected

    @pytest.mark.parametrize(
        ["input_text", "expected_str"],
        [
            (
                    """
                    event myEvent;
                    """,
                    'event myEvent;'
            ),  # Simple event definition without named clause
            (
                    """
                    event onClick;
                    """,
                    'event onClick;'
            ),  # Event with camelCase name
            (
                    """
                    event button_click;
                    """,
                    'event button_click;'
            ),  # Event with underscore in name
            (
                    """
                    event EVENT_NAME;
                    """,
                    'event EVENT_NAME;'
            ),  # Event with uppercase name
            (
                    """
                    event _privateEvent;
                    """,
                    'event _privateEvent;'
            ),  # Event starting with underscore
            (
                    """
                    event event123;
                    """,
                    'event event123;'
            ),  # Event name with numbers
            (
                    """
                    event a;
                    """,
                    'event a;'
            ),  # Single character event name
            (
                    """
                    event myEvent named "My Event";
                    """,
                    "event myEvent named 'My Event';"
            ),  # Event with named clause using double quotes
            (
                    """
                    event onClick named "Button Click Event";
                    """,
                    "event onClick named 'Button Click Event';"
            ),  # Event with descriptive name in double quotes
            (
                    """
                    event userInput named "User Input Handler";
                    """,
                    "event userInput named 'User Input Handler';"
            ),  # Event with space-separated description
            (
                    """
                    event errorOccurred named "Error has occurred!";
                    """,
                    "event errorOccurred named 'Error has occurred!';"
            ),  # Event with punctuation in description
            (
                    """
                    event dataReady named "";
                    """,
                    "event dataReady named '';"
            ),  # Event with empty string description
            (
                    """
                    event testEvent named "Event with \\"escaped\\" quotes";
                    """,
                    'event testEvent named \'Event with "escaped" quotes\';'
            ),  # Event with escaped quotes in description
            (
                    """
                    event fileEvent named "File\\nNew\\tLine";
                    """,
                    "event fileEvent named 'File\\nNew\\tLine';"
            ),  # Event with escape sequences
            (
                    """
                    event myEvent named 'My Event';
                    """,
                    "event myEvent named 'My Event';"
            ),  # Event with named clause using single quotes
            (
                    """
                    event onClick named 'Button Click Event';
                    """,
                    "event onClick named 'Button Click Event';"
            ),  # Event with descriptive name in single quotes
            (
                    """
                    event userInput named 'User Input Handler';
                    """,
                    "event userInput named 'User Input Handler';"
            ),  # Event with space-separated description in single quotes
            (
                    """
                    event errorOccurred named 'Error has occurred!';
                    """,
                    "event errorOccurred named 'Error has occurred!';"
            ),  # Event with punctuation in single quotes
            (
                    """
                    event dataReady named '';
                    """,
                    "event dataReady named '';"
            ),  # Event with empty string in single quotes
            (
                    """
                    event testEvent named 'Event with \\'escaped\\' quotes';
                    """,
                    'event testEvent named "Event with \'escaped\' quotes";'
            ),  # Event with escaped single quotes
            (
                    """
                    event mixedEvent named 'Contains "double" quotes';
                    """,
                    'event mixedEvent named \'Contains "double" quotes\';'
            ),  # Event with double quotes inside single quotes
        ]
    )
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expect=expected_str,
            actual=str(parse_with_grammar_entry(input_text, entry_name="event_definition")),
        )

    @pytest.mark.parametrize(
        ["input_text"],
        [
            (
                    """
                    event myEvent
                    """,
            ),  # Event definition missing semicolon
            (
                    """
                    event myEvent named "Test"
                    """,
            ),  # Event with named clause missing semicolon
            (
                    """
                    event 123invalid;
                    """,
            ),  # Event name starting with number
            (
                    """
                    event my-event;
                    """,
            ),  # Event name with dash
            (
                    """
                    event my event;
                    """,
            ),  # Event name with space
            (
                    """
                    event my@event;
                    """,
            ),  # Event name with special character
            (
                    """
                    event ;
                    """,
            ),  # Missing event name
            (
                    """
                    event myEvent named;
                    """,
            ),  # Named keyword without string value
            (
                    """
                    event myEvent named Test;
                    """,
            ),  # Named with unquoted string
            (
                    """
                    event myEvent named 123;
                    """,
            ),  # Named with number instead of string
            (
                    """
                    event myEvent named myVar;
                    """,
            ),  # Named with identifier instead of string
            (
                    """
                    event myEvent named "unclosed string;
                    """,
            ),  # Unclosed double quote string
            (
                    """
                    event myEvent named 'unclosed string;
                    """,
            ),  # Unclosed single quote string
            (
                    """
                    event myEvent named "mixed quotes';
                    """,
            ),  # Mismatched quote types
            (
                    """
                    event myEvent named 'mixed quotes";
                    """,
            ),  # Mismatched quote types reversed
            (
                    """
                    myEvent named "Test";
                    """,
            ),  # Missing event keyword
            (
                    """
                    event named "Test";
                    """,
            ),  # Missing event name
            (
                    """
                    event myEvent named "First" named "Second";
                    """,
            ),  # Multiple named clauses
            (
                    """
                    named event myEvent "Test";
                    """,
            ),  # Wrong keyword order
            (
                    """
                    event named myEvent "Test";
                    """,
            ),  # Named keyword in wrong position
            (
                    """
                    event myEvent extra named "Test";
                    """,
            ),  # Extra token before named
            (
                    """
                    event myEvent named "Test" extra;
                    """,
            ),  # Extra token after named
            (
                    """
                    event;
                    """,
            ),  # Event keyword only
            (
                    """
                    named "Test";
                    """,
            ),  # Named clause without event
            (
                    """
                    ;
                    """,
            ),  # Semicolon only
            (
                    """
            
                    """,
            ),  # Empty string
        ]
    )
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(
                input_text, entry_name="event_definition"
            )

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f"Found {len(err.errors)} errors during parsing:" in err.args[0]
