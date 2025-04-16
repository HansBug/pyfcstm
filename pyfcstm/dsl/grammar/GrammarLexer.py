# Generated from ./pyfcstm/dsl/grammar/Grammar.g4 by ANTLR 4.9.3
from antlr4 import *
from io import StringIO
import sys

if sys.version_info[1] > 5:
    from typing import TextIO
else:
    from typing.io import TextIO


def serializedATN():
    with StringIO() as buf:
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\2%")
        buf.write("\u0103\b\1\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7")
        buf.write("\t\7\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r")
        buf.write("\4\16\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23")
        buf.write("\t\23\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30")
        buf.write("\4\31\t\31\4\32\t\32\4\33\t\33\4\34\t\34\4\35\t\35\4\36")
        buf.write('\t\36\4\37\t\37\4 \t \4!\t!\4"\t"\4#\t#\4$\t$\3\2\3')
        buf.write("\2\3\2\3\3\3\3\3\4\3\4\3\5\3\5\3\6\3\6\3\7\3\7\3\b\3\b")
        buf.write("\3\t\3\t\3\t\3\n\3\n\3\13\3\13\3\f\3\f\3\r\3\r\3\r\3\16")
        buf.write("\3\16\3\16\3\17\3\17\3\20\3\20\3\21\3\21\3\22\3\22\3\23")
        buf.write("\3\23\3\24\3\24\3\25\3\25\3\25\3\26\3\26\3\26\3\27\3\27")
        buf.write("\3\27\3\30\3\30\3\30\3\31\3\31\3\31\3\32\3\32\3\32\3\33")
        buf.write("\3\33\3\33\3\34\3\34\3\35\3\35\3\35\3\35\3\36\3\36\7\36")
        buf.write("\u0091\n\36\f\36\16\36\u0094\13\36\3\37\6\37\u0097\n\37")
        buf.write("\r\37\16\37\u0098\3\37\3\37\7\37\u009d\n\37\f\37\16\37")
        buf.write("\u00a0\13\37\3\37\3\37\5\37\u00a4\n\37\3\37\6\37\u00a7")
        buf.write("\n\37\r\37\16\37\u00a8\5\37\u00ab\n\37\3\37\3\37\6\37")
        buf.write("\u00af\n\37\r\37\16\37\u00b0\3\37\3\37\5\37\u00b5\n\37")
        buf.write("\3\37\6\37\u00b8\n\37\r\37\16\37\u00b9\5\37\u00bc\n\37")
        buf.write("\3\37\6\37\u00bf\n\37\r\37\16\37\u00c0\3\37\3\37\5\37")
        buf.write("\u00c5\n\37\3\37\6\37\u00c8\n\37\r\37\16\37\u00c9\5\37")
        buf.write("\u00cc\n\37\3 \6 \u00cf\n \r \16 \u00d0\3!\3!\3!\3!\3")
        buf.write('!\3!\3!\3!\3!\3!\3!\3!\5!\u00df\n!\3"\3"\3"\3"\3"')
        buf.write('\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"\5"\u00f0\n"')
        buf.write("\3#\6#\u00f3\n#\r#\16#\u00f4\3#\3#\3$\3$\3$\3$\7$\u00fd")
        buf.write("\n$\f$\16$\u0100\13$\3$\3$\2\2%\3\3\5\4\7\5\t\6\13\7\r")
        buf.write("\b\17\t\21\n\23\13\25\f\27\r\31\16\33\17\35\20\37\21!")
        buf.write("\22#\23%\24'\25)\26+\27-\30/\31\61\32\63\33\65\34\67")
        buf.write('\359\36;\37= ?!A"C#E$G%\3\2\t\5\2C\\aac|\6\2\62;C\\a')
        buf.write('ac|\3\2\62;\4\2GGgg\4\2--//\5\2\13\f\17\17""\4\2\f\f')
        buf.write("\17\17\2\u0118\2\3\3\2\2\2\2\5\3\2\2\2\2\7\3\2\2\2\2\t")
        buf.write("\3\2\2\2\2\13\3\2\2\2\2\r\3\2\2\2\2\17\3\2\2\2\2\21\3")
        buf.write("\2\2\2\2\23\3\2\2\2\2\25\3\2\2\2\2\27\3\2\2\2\2\31\3\2")
        buf.write("\2\2\2\33\3\2\2\2\2\35\3\2\2\2\2\37\3\2\2\2\2!\3\2\2\2")
        buf.write("\2#\3\2\2\2\2%\3\2\2\2\2'\3\2\2\2\2)\3\2\2\2\2+\3\2\2")
        buf.write("\2\2-\3\2\2\2\2/\3\2\2\2\2\61\3\2\2\2\2\63\3\2\2\2\2\65")
        buf.write("\3\2\2\2\2\67\3\2\2\2\29\3\2\2\2\2;\3\2\2\2\2=\3\2\2\2")
        buf.write("\2?\3\2\2\2\2A\3\2\2\2\2C\3\2\2\2\2E\3\2\2\2\2G\3\2\2")
        buf.write("\2\3I\3\2\2\2\5L\3\2\2\2\7N\3\2\2\2\tP\3\2\2\2\13R\3\2")
        buf.write("\2\2\rT\3\2\2\2\17V\3\2\2\2\21X\3\2\2\2\23[\3\2\2\2\25")
        buf.write("]\3\2\2\2\27_\3\2\2\2\31a\3\2\2\2\33d\3\2\2\2\35g\3\2")
        buf.write("\2\2\37i\3\2\2\2!k\3\2\2\2#m\3\2\2\2%o\3\2\2\2'q\3\2")
        buf.write("\2\2)s\3\2\2\2+v\3\2\2\2-y\3\2\2\2/|\3\2\2\2\61\177\3")
        buf.write("\2\2\2\63\u0082\3\2\2\2\65\u0085\3\2\2\2\67\u0088\3\2")
        buf.write("\2\29\u008a\3\2\2\2;\u008e\3\2\2\2=\u00cb\3\2\2\2?\u00ce")
        buf.write("\3\2\2\2A\u00de\3\2\2\2C\u00ef\3\2\2\2E\u00f2\3\2\2\2")
        buf.write("G\u00f8\3\2\2\2IJ\7<\2\2JK\7?\2\2K\4\3\2\2\2LM\7=\2\2")
        buf.write("M\6\3\2\2\2NO\7?\2\2O\b\3\2\2\2PQ\7*\2\2Q\n\3\2\2\2RS")
        buf.write("\7+\2\2S\f\3\2\2\2TU\7-\2\2U\16\3\2\2\2VW\7/\2\2W\20\3")
        buf.write("\2\2\2XY\7,\2\2YZ\7,\2\2Z\22\3\2\2\2[\\\7,\2\2\\\24\3")
        buf.write("\2\2\2]^\7\61\2\2^\26\3\2\2\2_`\7'\2\2`\30\3\2\2\2ab")
        buf.write("\7>\2\2bc\7>\2\2c\32\3\2\2\2de\7@\2\2ef\7@\2\2f\34\3\2")
        buf.write("\2\2gh\7(\2\2h\36\3\2\2\2ij\7~\2\2j \3\2\2\2kl\7`\2\2")
        buf.write('l"\3\2\2\2mn\7#\2\2n$\3\2\2\2op\7>\2\2p&\3\2\2\2qr\7')
        buf.write("@\2\2r(\3\2\2\2st\7>\2\2tu\7?\2\2u*\3\2\2\2vw\7@\2\2w")
        buf.write("x\7?\2\2x,\3\2\2\2yz\7?\2\2z{\7?\2\2{.\3\2\2\2|}\7#\2")
        buf.write("\2}~\7?\2\2~\60\3\2\2\2\177\u0080\7(\2\2\u0080\u0081\7")
        buf.write("(\2\2\u0081\62\3\2\2\2\u0082\u0083\7~\2\2\u0083\u0084")
        buf.write("\7~\2\2\u0084\64\3\2\2\2\u0085\u0086\7r\2\2\u0086\u0087")
        buf.write("\7k\2\2\u0087\66\3\2\2\2\u0088\u0089\7g\2\2\u00898\3\2")
        buf.write("\2\2\u008a\u008b\7v\2\2\u008b\u008c\7c\2\2\u008c\u008d")
        buf.write("\7w\2\2\u008d:\3\2\2\2\u008e\u0092\t\2\2\2\u008f\u0091")
        buf.write("\t\3\2\2\u0090\u008f\3\2\2\2\u0091\u0094\3\2\2\2\u0092")
        buf.write("\u0090\3\2\2\2\u0092\u0093\3\2\2\2\u0093<\3\2\2\2\u0094")
        buf.write("\u0092\3\2\2\2\u0095\u0097\t\4\2\2\u0096\u0095\3\2\2\2")
        buf.write("\u0097\u0098\3\2\2\2\u0098\u0096\3\2\2\2\u0098\u0099\3")
        buf.write("\2\2\2\u0099\u009a\3\2\2\2\u009a\u009e\7\60\2\2\u009b")
        buf.write("\u009d\t\4\2\2\u009c\u009b\3\2\2\2\u009d\u00a0\3\2\2\2")
        buf.write("\u009e\u009c\3\2\2\2\u009e\u009f\3\2\2\2\u009f\u00aa\3")
        buf.write("\2\2\2\u00a0\u009e\3\2\2\2\u00a1\u00a3\t\5\2\2\u00a2\u00a4")
        buf.write("\t\6\2\2\u00a3\u00a2\3\2\2\2\u00a3\u00a4\3\2\2\2\u00a4")
        buf.write("\u00a6\3\2\2\2\u00a5\u00a7\t\4\2\2\u00a6\u00a5\3\2\2\2")
        buf.write("\u00a7\u00a8\3\2\2\2\u00a8\u00a6\3\2\2\2\u00a8\u00a9\3")
        buf.write("\2\2\2\u00a9\u00ab\3\2\2\2\u00aa\u00a1\3\2\2\2\u00aa\u00ab")
        buf.write("\3\2\2\2\u00ab\u00cc\3\2\2\2\u00ac\u00ae\7\60\2\2\u00ad")
        buf.write("\u00af\t\4\2\2\u00ae\u00ad\3\2\2\2\u00af\u00b0\3\2\2\2")
        buf.write("\u00b0\u00ae\3\2\2\2\u00b0\u00b1\3\2\2\2\u00b1\u00bb\3")
        buf.write("\2\2\2\u00b2\u00b4\t\5\2\2\u00b3\u00b5\t\6\2\2\u00b4\u00b3")
        buf.write("\3\2\2\2\u00b4\u00b5\3\2\2\2\u00b5\u00b7\3\2\2\2\u00b6")
        buf.write("\u00b8\t\4\2\2\u00b7\u00b6\3\2\2\2\u00b8\u00b9\3\2\2\2")
        buf.write("\u00b9\u00b7\3\2\2\2\u00b9\u00ba\3\2\2\2\u00ba\u00bc\3")
        buf.write("\2\2\2\u00bb\u00b2\3\2\2\2\u00bb\u00bc\3\2\2\2\u00bc\u00cc")
        buf.write("\3\2\2\2\u00bd\u00bf\t\4\2\2\u00be\u00bd\3\2\2\2\u00bf")
        buf.write("\u00c0\3\2\2\2\u00c0\u00be\3\2\2\2\u00c0\u00c1\3\2\2\2")
        buf.write("\u00c1\u00c2\3\2\2\2\u00c2\u00c4\t\5\2\2\u00c3\u00c5\t")
        buf.write("\6\2\2\u00c4\u00c3\3\2\2\2\u00c4\u00c5\3\2\2\2\u00c5\u00c7")
        buf.write("\3\2\2\2\u00c6\u00c8\t\4\2\2\u00c7\u00c6\3\2\2\2\u00c8")
        buf.write("\u00c9\3\2\2\2\u00c9\u00c7\3\2\2\2\u00c9\u00ca\3\2\2\2")
        buf.write("\u00ca\u00cc\3\2\2\2\u00cb\u0096\3\2\2\2\u00cb\u00ac\3")
        buf.write("\2\2\2\u00cb\u00be\3\2\2\2\u00cc>\3\2\2\2\u00cd\u00cf")
        buf.write("\t\4\2\2\u00ce\u00cd\3\2\2\2\u00cf\u00d0\3\2\2\2\u00d0")
        buf.write("\u00ce\3\2\2\2\u00d0\u00d1\3\2\2\2\u00d1@\3\2\2\2\u00d2")
        buf.write("\u00d3\7V\2\2\u00d3\u00d4\7t\2\2\u00d4\u00d5\7w\2\2\u00d5")
        buf.write("\u00df\7g\2\2\u00d6\u00d7\7v\2\2\u00d7\u00d8\7t\2\2\u00d8")
        buf.write("\u00d9\7w\2\2\u00d9\u00df\7g\2\2\u00da\u00db\7V\2\2\u00db")
        buf.write("\u00dc\7T\2\2\u00dc\u00dd\7W\2\2\u00dd\u00df\7G\2\2\u00de")
        buf.write("\u00d2\3\2\2\2\u00de\u00d6\3\2\2\2\u00de\u00da\3\2\2\2")
        buf.write("\u00dfB\3\2\2\2\u00e0\u00e1\7H\2\2\u00e1\u00e2\7c\2\2")
        buf.write("\u00e2\u00e3\7n\2\2\u00e3\u00e4\7u\2\2\u00e4\u00f0\7g")
        buf.write("\2\2\u00e5\u00e6\7h\2\2\u00e6\u00e7\7c\2\2\u00e7\u00e8")
        buf.write("\7n\2\2\u00e8\u00e9\7u\2\2\u00e9\u00f0\7g\2\2\u00ea\u00eb")
        buf.write("\7H\2\2\u00eb\u00ec\7C\2\2\u00ec\u00ed\7N\2\2\u00ed\u00ee")
        buf.write("\7U\2\2\u00ee\u00f0\7G\2\2\u00ef\u00e0\3\2\2\2\u00ef\u00e5")
        buf.write("\3\2\2\2\u00ef\u00ea\3\2\2\2\u00f0D\3\2\2\2\u00f1\u00f3")
        buf.write("\t\7\2\2\u00f2\u00f1\3\2\2\2\u00f3\u00f4\3\2\2\2\u00f4")
        buf.write("\u00f2\3\2\2\2\u00f4\u00f5\3\2\2\2\u00f5\u00f6\3\2\2\2")
        buf.write("\u00f6\u00f7\b#\2\2\u00f7F\3\2\2\2\u00f8\u00f9\7\61\2")
        buf.write("\2\u00f9\u00fa\7\61\2\2\u00fa\u00fe\3\2\2\2\u00fb\u00fd")
        buf.write("\n\b\2\2\u00fc\u00fb\3\2\2\2\u00fd\u0100\3\2\2\2\u00fe")
        buf.write("\u00fc\3\2\2\2\u00fe\u00ff\3\2\2\2\u00ff\u0101\3\2\2\2")
        buf.write("\u0100\u00fe\3\2\2\2\u0101\u0102\b$\2\2\u0102H\3\2\2\2")
        buf.write("\26\2\u0092\u0098\u009e\u00a3\u00a8\u00aa\u00b0\u00b4")
        buf.write("\u00b9\u00bb\u00c0\u00c4\u00c9\u00cb\u00d0\u00de\u00ef")
        buf.write("\u00f4\u00fe\3\b\2\2")
        return buf.getvalue()


class GrammarLexer(Lexer):
    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [DFA(ds, i) for i, ds in enumerate(atn.decisionToState)]

    T__0 = 1
    T__1 = 2
    T__2 = 3
    T__3 = 4
    T__4 = 5
    T__5 = 6
    T__6 = 7
    T__7 = 8
    T__8 = 9
    T__9 = 10
    T__10 = 11
    T__11 = 12
    T__12 = 13
    T__13 = 14
    T__14 = 15
    T__15 = 16
    T__16 = 17
    T__17 = 18
    T__18 = 19
    T__19 = 20
    T__20 = 21
    T__21 = 22
    T__22 = 23
    T__23 = 24
    T__24 = 25
    T__25 = 26
    T__26 = 27
    T__27 = 28
    ID = 29
    FLOAT = 30
    INT = 31
    TRUE = 32
    FALSE = 33
    WS = 34
    SL_COMMENT = 35

    channelNames = ["DEFAULT_TOKEN_CHANNEL", "HIDDEN"]

    modeNames = ["DEFAULT_MODE"]

    literalNames = [
        "<INVALID>",
        "':='",
        "';'",
        "'='",
        "'('",
        "')'",
        "'+'",
        "'-'",
        "'**'",
        "'*'",
        "'/'",
        "'%'",
        "'<<'",
        "'>>'",
        "'&'",
        "'|'",
        "'^'",
        "'!'",
        "'<'",
        "'>'",
        "'<='",
        "'>='",
        "'=='",
        "'!='",
        "'&&'",
        "'||'",
        "'pi'",
        "'e'",
        "'tau'",
    ]

    symbolicNames = [
        "<INVALID>",
        "ID",
        "FLOAT",
        "INT",
        "TRUE",
        "FALSE",
        "WS",
        "SL_COMMENT",
    ]

    ruleNames = [
        "T__0",
        "T__1",
        "T__2",
        "T__3",
        "T__4",
        "T__5",
        "T__6",
        "T__7",
        "T__8",
        "T__9",
        "T__10",
        "T__11",
        "T__12",
        "T__13",
        "T__14",
        "T__15",
        "T__16",
        "T__17",
        "T__18",
        "T__19",
        "T__20",
        "T__21",
        "T__22",
        "T__23",
        "T__24",
        "T__25",
        "T__26",
        "T__27",
        "ID",
        "FLOAT",
        "INT",
        "TRUE",
        "FALSE",
        "WS",
        "SL_COMMENT",
    ]

    grammarFileName = "Grammar.g4"

    def __init__(self, input=None, output: TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.9.3")
        self._interp = LexerATNSimulator(
            self, self.atn, self.decisionsToDFA, PredictionContextCache()
        )
        self._actions = None
        self._predicates = None
