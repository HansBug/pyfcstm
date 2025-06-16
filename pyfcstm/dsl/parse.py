from antlr4 import CommonTokenStream, InputStream, ParseTreeWalker

from .error import CollectingErrorListener
from .grammar import GrammarParser, GrammarLexer
from .listener import GrammarParseListener


def _parse_as_element(input_text, fn_element, force_finished: bool = True):
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
    if force_finished:
        error_listener.check_unfinished_parsing_error(stream)
    error_listener.check_errors()

    listener = GrammarParseListener()
    walker = ParseTreeWalker()
    walker.walk(listener, parse_tree)
    return listener.nodes[parse_tree]


def parse_with_grammar_entry(input_text: str, entry_name: str, force_finished: bool = True):
    return _parse_as_element(
        input_text=input_text,
        fn_element=getattr(GrammarParser, entry_name),
        force_finished=force_finished
    )


def parse_condition(input_text: str):
    return parse_with_grammar_entry(input_text, 'condition')


def parse_preamble(input_text: str):
    return parse_with_grammar_entry(input_text, 'preamble_program')


def parse_operation(input_text: str):
    return parse_with_grammar_entry(input_text, 'operation_program')
