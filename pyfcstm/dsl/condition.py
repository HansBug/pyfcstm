from pprint import pprint

from antlr4 import CommonTokenStream, InputStream, ParseTreeWalker

from .error import CollectingErrorListener
from .grammar import GrammarListener, GrammarParser, GrammarLexer
from .node import Integer, Float, Constant, Boolean


class ConditionGrammarListener(GrammarListener):
    def __init__(self):
        super().__init__()
        self.nodes = {}

    def exitCondition(self, ctx: GrammarParser.ConditionContext):
        super().exitCondition(ctx)

    def exitUnaryExprNum(self, ctx: GrammarParser.UnaryExprNumContext):
        super().exitUnaryExprNum(ctx)

    def exitFuncExprNum(self, ctx: GrammarParser.FuncExprNumContext):
        super().exitFuncExprNum(ctx)

    def exitBinaryExprNum(self, ctx: GrammarParser.BinaryExprNumContext):
        super().exitBinaryExprNum(ctx)

    def exitLiteralExprNum(self, ctx: GrammarParser.LiteralExprNumContext):
        super().exitLiteralExprNum(ctx)

    def exitMathConstExprNum(self, ctx: GrammarParser.MathConstExprNumContext):
        super().exitMathConstExprNum(ctx)

    def exitParenExprNum(self, ctx: GrammarParser.ParenExprNumContext):
        super().exitParenExprNum(ctx)

    def exitIdExprNum(self, ctx: GrammarParser.IdExprNumContext):
        super().exitIdExprNum(ctx)

    def exitBinaryExprCond(self, ctx: GrammarParser.BinaryExprCondContext):
        super().exitBinaryExprCond(ctx)

    def exitUnaryExprCond(self, ctx: GrammarParser.UnaryExprCondContext):
        super().exitUnaryExprCond(ctx)

    def exitParenExprCond(self, ctx: GrammarParser.ParenExprCondContext):
        super().exitParenExprCond(ctx)

    def exitLiteralExprCond(self, ctx: GrammarParser.LiteralExprCondContext):
        super().exitLiteralExprCond(ctx)

    def exitNum_literal(self, ctx: GrammarParser.Num_literalContext):
        super().exitNum_literal(ctx)
        if ctx.INT():
            node = Integer(str(ctx.INT()))
        elif ctx.FLOAT():
            node = Float(str(ctx.FLOAT()))
        else:
            assert False, f'Should not reach this line - {ctx!r}.'
        self.nodes[ctx] = node

    def exitBool_literal(self, ctx: GrammarParser.Bool_literalContext):
        super().exitBool_literal(ctx)
        node = Boolean(ctx.getText().lower())
        self.nodes[ctx] = node

    def exitMath_const(self, ctx: GrammarParser.Math_constContext):
        super().exitMath_const(ctx)
        node = Constant(ctx.getText())
        self.nodes[ctx] = node


def parse_condition(input_text):
    error_listener = CollectingErrorListener()

    input_stream = InputStream(input_text)
    lexer = GrammarLexer(input_stream)
    lexer.removeErrorListeners()
    lexer.addErrorListener(error_listener)

    stream = CommonTokenStream(lexer)
    parser = GrammarParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(error_listener)

    parse_tree = parser.condition()
    error_listener.check_errors()

    listener = ConditionGrammarListener()
    walker = ParseTreeWalker()
    walker.walk(listener, parse_tree)
    pprint(listener.nodes)
    return listener.nodes[parse_tree]
