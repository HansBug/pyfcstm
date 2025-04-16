from antlr4 import CommonTokenStream, InputStream, ParseTreeWalker

from .error import CollectingErrorListener
from .grammar import GrammarParser, GrammarLexer
from .listener import GrammarParseListener


def _parse_as_element(input_text, fn_element):
    error_listener = CollectingErrorListener()

    input_stream = InputStream(input_text)
    lexer = GrammarLexer(input_stream)
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)

    stream = CommonTokenStream(lexer)
    parser = GrammarParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    parse_tree = fn_element(parser)
    error_listener.check_errors()

    listener = GrammarParseListener()
    walker = ParseTreeWalker()
    walker.walk(listener, parse_tree)
    return listener.nodes[parse_tree]


def parse_condition(input_text):
    return _parse_as_element(
        input_text=input_text,
        fn_element=GrammarParser.condition,
    )


def parse_preamble(input_text):
    return _parse_as_element(
        input_text=input_text,
        fn_element=GrammarParser.preamble_program,
    )


def parse_operation(input_text):
    return _parse_as_element(
        input_text=input_text,
        fn_element=GrammarParser.operation_program,
    )
