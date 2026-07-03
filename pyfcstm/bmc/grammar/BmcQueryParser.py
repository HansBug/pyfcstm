# Generated from ./pyfcstm/bmc/grammar/BmcQueryParser.g4 by ANTLR 4.9.3
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys

if sys.version_info[1] > 5:
    from typing import TextIO
else:
    from typing.io import TextIO


def serializedATN():
    with StringIO() as buf:
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3V")
        buf.write("\u0151\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7")
        buf.write("\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r\4\16")
        buf.write("\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23\t\23")
        buf.write("\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30\4\31")
        buf.write("\t\31\4\32\t\32\4\33\t\33\4\34\t\34\3\2\5\2:\n\2\3\2\7")
        buf.write("\2=\n\2\f\2\16\2@\13\2\3\2\3\2\3\2\3\3\3\3\3\3\3\4\3\4")
        buf.write("\3\4\3\5\3\5\3\5\3\5\5\5O\n\5\3\5\3\5\3\6\3\6\3\6\3\6")
        buf.write("\3\6\3\6\3\6\5\6Z\n\6\3\7\3\7\3\7\5\7_\n\7\3\b\3\b\3\b")
        buf.write("\3\b\5\be\n\b\3\b\3\b\3\b\3\b\3\t\3\t\3\t\3\t\3\t\3\t")
        buf.write("\3\t\3\t\3\t\3\t\3\t\3\n\3\n\3\n\3\n\3\n\3\n\3\n\3\n\3")
        buf.write("\n\5\n\177\n\n\3\n\3\n\3\13\3\13\3\13\3\13\3\13\3\13\3")
        buf.write("\13\3\13\3\f\3\f\3\r\3\r\5\r\u008f\n\r\3\16\3\16\3\16")
        buf.write("\3\16\3\16\3\16\3\16\3\17\3\17\3\17\7\17\u009b\n\17\f")
        buf.write("\17\16\17\u009e\13\17\3\20\3\20\3\21\3\21\3\21\3\21\3")
        buf.write("\21\3\21\3\21\5\21\u00a9\n\21\3\22\3\22\5\22\u00ad\n\22")
        buf.write("\3\23\3\23\5\23\u00b1\n\23\3\24\3\24\3\25\3\25\3\26\3")
        buf.write("\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26")
        buf.write("\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26")
        buf.write("\3\26\3\26\3\26\3\26\3\26\3\26\5\26\u00d4\n\26\3\26\3")
        buf.write("\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26")
        buf.write("\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\7\26\u00eb")
        buf.write("\n\26\f\26\16\26\u00ee\13\26\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\5\27\u0109")
        buf.write("\n\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\3\27\3\27\7\27\u011a\n\27\f\27\16\27\u011d")
        buf.write("\13\27\3\30\3\30\3\30\3\30\3\30\5\30\u0124\n\30\3\30\3")
        buf.write("\30\3\30\3\30\3\30\5\30\u012b\n\30\3\30\3\30\3\30\3\30")
        buf.write("\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\5\30\u013a")
        buf.write("\n\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\5\30\u0143\n")
        buf.write("\30\3\30\3\30\5\30\u0147\n\30\3\31\3\31\3\32\3\32\3\33")
        buf.write("\3\33\3\34\3\34\3\34\2\4*,\35\2\4\6\b\n\f\16\20\22\24")
        buf.write('\26\30\32\34\36 "$&(*,.\60\62\64\66\2\21\3\2\21\27\3')
        buf.write("\2./\3\2LM\3\2BC\4\2?@DD\3\2*+\4\2%%AA\4\2,-HI\4\2''")
        buf.write("./\4\2##\60\60\4\2$$\61\61\4\2&&\62\62\3\2JM\3\2NO\3\2")
        buf.write(' "\2\u0167\29\3\2\2\2\4D\3\2\2\2\6G\3\2\2\2\bJ\3\2\2')
        buf.write("\2\nY\3\2\2\2\f^\3\2\2\2\16`\3\2\2\2\20j\3\2\2\2\22u\3")
        buf.write("\2\2\2\24\u0082\3\2\2\2\26\u008a\3\2\2\2\30\u008e\3\2")
        buf.write("\2\2\32\u0090\3\2\2\2\34\u0097\3\2\2\2\36\u009f\3\2\2")
        buf.write('\2 \u00a8\3\2\2\2"\u00ac\3\2\2\2$\u00b0\3\2\2\2&\u00b2')
        buf.write("\3\2\2\2(\u00b4\3\2\2\2*\u00d3\3\2\2\2,\u0108\3\2\2\2")
        buf.write(".\u0146\3\2\2\2\60\u0148\3\2\2\2\62\u014a\3\2\2\2\64\u014c")
        buf.write("\3\2\2\2\66\u014e\3\2\2\28:\5\b\5\298\3\2\2\29:\3\2\2")
        buf.write("\2:>\3\2\2\2;=\5\f\7\2<;\3\2\2\2=@\3\2\2\2><\3\2\2\2>")
        buf.write("?\3\2\2\2?A\3\2\2\2@>\3\2\2\2AB\5\24\13\2BC\7\2\2\3C\3")
        buf.write("\3\2\2\2DE\5*\26\2EF\7\2\2\3F\5\3\2\2\2GH\5,\27\2HI\7")
        buf.write("\2\2\3I\7\3\2\2\2JK\7\3\2\2KN\5\n\6\2LM\7\7\2\2MO\5,\27")
        buf.write("\2NL\3\2\2\2NO\3\2\2\2OP\3\2\2\2PQ\7\66\2\2Q\t\3\2\2\2")
        buf.write("RZ\7\4\2\2SZ\7\5\2\2TU\7\6\2\2UV\7:\2\2VW\5\66\34\2WX")
        buf.write("\7;\2\2XZ\3\2\2\2YR\3\2\2\2YS\3\2\2\2YT\3\2\2\2Z\13\3")
        buf.write("\2\2\2[_\5\16\b\2\\_\5\20\t\2]_\5\22\n\2^[\3\2\2\2^\\")
        buf.write("\3\2\2\2^]\3\2\2\2_\r\3\2\2\2`d\7\b\2\2ae\7\t\2\2bc\7")
        buf.write("\n\2\2ce\5(\25\2da\3\2\2\2db\3\2\2\2ef\3\2\2\2fg\7=\2")
        buf.write("\2gh\5,\27\2hi\7\66\2\2i\17\3\2\2\2jk\7\b\2\2kl\7\13\2")
        buf.write("\2lm\7:\2\2mn\5\66\34\2no\7\67\2\2op\5 \21\2pq\7;\2\2")
        buf.write("qr\5\36\20\2rs\5\62\32\2st\7\66\2\2t\21\3\2\2\2uv\7\b")
        buf.write("\2\2vw\7\f\2\2w~\7\r\2\2x\177\7\16\2\2yz\7\17\2\2z{\7")
        buf.write("8\2\2{|\5\34\17\2|}\79\2\2}\177\3\2\2\2~x\3\2\2\2~y\3")
        buf.write("\2\2\2\177\u0080\3\2\2\2\u0080\u0081\7\66\2\2\u0081\23")
        buf.write("\3\2\2\2\u0082\u0083\7\20\2\2\u0083\u0084\5\26\f\2\u0084")
        buf.write("\u0085\7,\2\2\u0085\u0086\5&\24\2\u0086\u0087\7=\2\2\u0087")
        buf.write("\u0088\5\30\r\2\u0088\u0089\7\66\2\2\u0089\25\3\2\2\2")
        buf.write("\u008a\u008b\t\2\2\2\u008b\27\3\2\2\2\u008c\u008f\5\32")
        buf.write("\16\2\u008d\u008f\5,\27\2\u008e\u008c\3\2\2\2\u008e\u008d")
        buf.write("\3\2\2\2\u008f\31\3\2\2\2\u0090\u0091\7\30\2\2\u0091\u0092")
        buf.write("\5,\27\2\u0092\u0093\7\63\2\2\u0093\u0094\7\31\2\2\u0094")
        buf.write("\u0095\5&\24\2\u0095\u0096\5,\27\2\u0096\33\3\2\2\2\u0097")
        buf.write("\u009c\5\66\34\2\u0098\u0099\7\67\2\2\u0099\u009b\5\66")
        buf.write("\34\2\u009a\u0098\3\2\2\2\u009b\u009e\3\2\2\2\u009c\u009a")
        buf.write("\3\2\2\2\u009c\u009d\3\2\2\2\u009d\35\3\2\2\2\u009e\u009c")
        buf.write("\3\2\2\2\u009f\u00a0\t\3\2\2\u00a0\37\3\2\2\2\u00a1\u00a9")
        buf.write("\7@\2\2\u00a2\u00a9\5(\25\2\u00a3\u00a4\5(\25\2\u00a4")
        buf.write("\u00a5\7\65\2\2\u00a5\u00a6\5(\25\2\u00a6\u00a9\3\2\2")
        buf.write("\2\u00a7\u00a9\7\64\2\2\u00a8\u00a1\3\2\2\2\u00a8\u00a2")
        buf.write("\3\2\2\2\u00a8\u00a3\3\2\2\2\u00a8\u00a7\3\2\2\2\u00a9")
        buf.write("!\3\2\2\2\u00aa\u00ad\7\37\2\2\u00ab\u00ad\5(\25\2\u00ac")
        buf.write("\u00aa\3\2\2\2\u00ac\u00ab\3\2\2\2\u00ad#\3\2\2\2\u00ae")
        buf.write("\u00b1\7\37\2\2\u00af\u00b1\5(\25\2\u00b0\u00ae\3\2\2")
        buf.write("\2\u00b0\u00af\3\2\2\2\u00b1%\3\2\2\2\u00b2\u00b3\7L\2")
        buf.write("\2\u00b3'\3\2\2\2\u00b4\u00b5\t\4\2\2\u00b5)\3\2\2\2")
        buf.write("\u00b6\u00b7\b\26\1\2\u00b7\u00b8\7:\2\2\u00b8\u00b9\5")
        buf.write("*\26\2\u00b9\u00ba\7;\2\2\u00ba\u00d4\3\2\2\2\u00bb\u00d4")
        buf.write("\5\60\31\2\u00bc\u00d4\7Q\2\2\u00bd\u00d4\5\64\33\2\u00be")
        buf.write("\u00bf\7\32\2\2\u00bf\u00c0\7:\2\2\u00c0\u00c1\5\66\34")
        buf.write("\2\u00c1\u00c2\7;\2\2\u00c2\u00d4\3\2\2\2\u00c3\u00d4")
        buf.write("\7\33\2\2\u00c4\u00c5\t\5\2\2\u00c5\u00d4\5*\26\f\u00c6")
        buf.write("\u00c7\7P\2\2\u00c7\u00c8\7:\2\2\u00c8\u00c9\5*\26\2\u00c9")
        buf.write("\u00ca\7;\2\2\u00ca\u00d4\3\2\2\2\u00cb\u00cc\7:\2\2\u00cc")
        buf.write("\u00cd\5,\27\2\u00cd\u00ce\7;\2\2\u00ce\u00cf\7<\2\2\u00cf")
        buf.write("\u00d0\5*\26\2\u00d0\u00d1\7=\2\2\u00d1\u00d2\5*\26\3")
        buf.write("\u00d2\u00d4\3\2\2\2\u00d3\u00b6\3\2\2\2\u00d3\u00bb\3")
        buf.write("\2\2\2\u00d3\u00bc\3\2\2\2\u00d3\u00bd\3\2\2\2\u00d3\u00be")
        buf.write("\3\2\2\2\u00d3\u00c3\3\2\2\2\u00d3\u00c4\3\2\2\2\u00d3")
        buf.write("\u00c6\3\2\2\2\u00d3\u00cb\3\2\2\2\u00d4\u00ec\3\2\2\2")
        buf.write("\u00d5\u00d6\f\13\2\2\u00d6\u00d7\7)\2\2\u00d7\u00eb\5")
        buf.write("*\26\13\u00d8\u00d9\f\n\2\2\u00d9\u00da\t\6\2\2\u00da")
        buf.write("\u00eb\5*\26\13\u00db\u00dc\f\t\2\2\u00dc\u00dd\t\5\2")
        buf.write("\2\u00dd\u00eb\5*\26\n\u00de\u00df\f\b\2\2\u00df\u00e0")
        buf.write("\t\7\2\2\u00e0\u00eb\5*\26\t\u00e1\u00e2\f\7\2\2\u00e2")
        buf.write("\u00e3\7E\2\2\u00e3\u00eb\5*\26\b\u00e4\u00e5\f\6\2\2")
        buf.write("\u00e5\u00e6\7F\2\2\u00e6\u00eb\5*\26\7\u00e7\u00e8\f")
        buf.write("\5\2\2\u00e8\u00e9\7G\2\2\u00e9\u00eb\5*\26\6\u00ea\u00d5")
        buf.write("\3\2\2\2\u00ea\u00d8\3\2\2\2\u00ea\u00db\3\2\2\2\u00ea")
        buf.write("\u00de\3\2\2\2\u00ea\u00e1\3\2\2\2\u00ea\u00e4\3\2\2\2")
        buf.write("\u00ea\u00e7\3\2\2\2\u00eb\u00ee\3\2\2\2\u00ec\u00ea\3")
        buf.write("\2\2\2\u00ec\u00ed\3\2\2\2\u00ed+\3\2\2\2\u00ee\u00ec")
        buf.write("\3\2\2\2\u00ef\u00f0\b\27\1\2\u00f0\u00f1\7:\2\2\u00f1")
        buf.write("\u00f2\5,\27\2\u00f2\u00f3\7;\2\2\u00f3\u0109\3\2\2\2")
        buf.write("\u00f4\u0109\5\62\32\2\u00f5\u0109\5.\30\2\u00f6\u00f7")
        buf.write("\t\b\2\2\u00f7\u0109\5,\27\13\u00f8\u00f9\5*\26\2\u00f9")
        buf.write("\u00fa\t\t\2\2\u00fa\u00fb\5*\26\2\u00fb\u0109\3\2\2\2")
        buf.write("\u00fc\u00fd\5*\26\2\u00fd\u00fe\t\3\2\2\u00fe\u00ff\5")
        buf.write("*\26\2\u00ff\u0109\3\2\2\2\u0100\u0101\7:\2\2\u0101\u0102")
        buf.write("\5,\27\2\u0102\u0103\7;\2\2\u0103\u0104\7<\2\2\u0104\u0105")
        buf.write("\5,\27\2\u0105\u0106\7=\2\2\u0106\u0107\5,\27\3\u0107")
        buf.write("\u0109\3\2\2\2\u0108\u00ef\3\2\2\2\u0108\u00f4\3\2\2\2")
        buf.write("\u0108\u00f5\3\2\2\2\u0108\u00f6\3\2\2\2\u0108\u00f8\3")
        buf.write("\2\2\2\u0108\u00fc\3\2\2\2\u0108\u0100\3\2\2\2\u0109\u011b")
        buf.write("\3\2\2\2\u010a\u010b\f\b\2\2\u010b\u010c\t\n\2\2\u010c")
        buf.write("\u011a\5,\27\t\u010d\u010e\f\7\2\2\u010e\u010f\t\13\2")
        buf.write("\2\u010f\u011a\5,\27\b\u0110\u0111\f\6\2\2\u0111\u0112")
        buf.write("\7(\2\2\u0112\u011a\5,\27\7\u0113\u0114\f\5\2\2\u0114")
        buf.write("\u0115\t\f\2\2\u0115\u011a\5,\27\6\u0116\u0117\f\4\2\2")
        buf.write("\u0117\u0118\t\r\2\2\u0118\u011a\5,\27\4\u0119\u010a\3")
        buf.write("\2\2\2\u0119\u010d\3\2\2\2\u0119\u0110\3\2\2\2\u0119\u0113")
        buf.write("\3\2\2\2\u0119\u0116\3\2\2\2\u011a\u011d\3\2\2\2\u011b")
        buf.write("\u0119\3\2\2\2\u011b\u011c\3\2\2\2\u011c-\3\2\2\2\u011d")
        buf.write("\u011b\3\2\2\2\u011e\u011f\7\34\2\2\u011f\u0120\7:\2\2")
        buf.write("\u0120\u0123\5\66\34\2\u0121\u0122\7\67\2\2\u0122\u0124")
        buf.write("\5$\23\2\u0123\u0121\3\2\2\2\u0123\u0124\3\2\2\2\u0124")
        buf.write("\u0125\3\2\2\2\u0125\u0126\7;\2\2\u0126\u0147\3\2\2\2")
        buf.write("\u0127\u0128\7\5\2\2\u0128\u012a\7:\2\2\u0129\u012b\5")
        buf.write("$\23\2\u012a\u0129\3\2\2\2\u012a\u012b\3\2\2\2\u012b\u012c")
        buf.write("\3\2\2\2\u012c\u0147\7;\2\2\u012d\u012e\7\13\2\2\u012e")
        buf.write("\u012f\7:\2\2\u012f\u0130\5\66\34\2\u0130\u0131\7\67\2")
        buf.write('\2\u0131\u0132\5"\22\2\u0132\u0133\7;\2\2\u0133\u0147')
        buf.write("\3\2\2\2\u0134\u0135\7\35\2\2\u0135\u0136\7:\2\2\u0136")
        buf.write("\u0139\5\66\34\2\u0137\u0138\7\67\2\2\u0138\u013a\5$\23")
        buf.write("\2\u0139\u0137\3\2\2\2\u0139\u013a\3\2\2\2\u013a\u013b")
        buf.write("\3\2\2\2\u013b\u013c\7;\2\2\u013c\u0147\3\2\2\2\u013d")
        buf.write("\u013e\7\36\2\2\u013e\u013f\7:\2\2\u013f\u0142\5\66\34")
        buf.write("\2\u0140\u0141\7\67\2\2\u0141\u0143\5$\23\2\u0142\u0140")
        buf.write("\3\2\2\2\u0142\u0143\3\2\2\2\u0143\u0144\3\2\2\2\u0144")
        buf.write("\u0145\7;\2\2\u0145\u0147\3\2\2\2\u0146\u011e\3\2\2\2")
        buf.write("\u0146\u0127\3\2\2\2\u0146\u012d\3\2\2\2\u0146\u0134\3")
        buf.write("\2\2\2\u0146\u013d\3\2\2\2\u0147/\3\2\2\2\u0148\u0149")
        buf.write("\t\16\2\2\u0149\61\3\2\2\2\u014a\u014b\t\17\2\2\u014b")
        buf.write("\63\3\2\2\2\u014c\u014d\t\20\2\2\u014d\65\3\2\2\2\u014e")
        buf.write("\u014f\7R\2\2\u014f\67\3\2\2\2\319>NY^d~\u008e\u009c\u00a8")
        buf.write("\u00ac\u00b0\u00d3\u00ea\u00ec\u0108\u0119\u011b\u0123")
        buf.write("\u012a\u0139\u0142\u0146")
        return buf.getvalue()


class BmcQueryParser(Parser):
    grammarFileName = "BmcQueryParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [DFA(ds, i) for i, ds in enumerate(atn.decisionToState)]

    sharedContextCache = PredictionContextCache()

    literalNames = [
        "<INVALID>",
        "'init'",
        "'cold'",
        "'terminated'",
        "'state'",
        "'where'",
        "'assume'",
        "'always'",
        "'at'",
        "'event'",
        "'events'",
        "'cardinality'",
        "'any'",
        "'at_most_one'",
        "'check'",
        "'reach'",
        "'forbid'",
        "'invariant'",
        "'must_reach'",
        "'exists_always'",
        "'response'",
        "'cover'",
        "'trigger'",
        "'within'",
        "'var'",
        "'cycle'",
        "'active'",
        "'case'",
        "'called'",
        "'current'",
        "'pi'",
        "'E'",
        "'tau'",
        "'and'",
        "'or'",
        "'not'",
        "'implies'",
        "'iff'",
        "'xor'",
        "'**'",
        "'>>'",
        "'<<'",
        "'<='",
        "'>='",
        "'=='",
        "'!='",
        "'&&'",
        "'||'",
        "'=>'",
        "'->'",
        "<INVALID>",
        "'..'",
        "';'",
        "','",
        "'{'",
        "'}'",
        "'('",
        "')'",
        "'?'",
        "':'",
        "'.'",
        "'/'",
        "'*'",
        "'!'",
        "'+'",
        "'-'",
        "'%'",
        "'&'",
        "'^'",
        "'|'",
        "'<'",
        "'>'",
    ]

    symbolicNames = [
        "<INVALID>",
        "INIT",
        "COLD",
        "TERMINATED",
        "STATE",
        "WHERE",
        "ASSUME",
        "ALWAYS",
        "AT",
        "EVENT",
        "EVENTS",
        "CARDINALITY",
        "ANY",
        "AT_MOST_ONE",
        "CHECK",
        "REACH",
        "FORBID",
        "INVARIANT",
        "MUST_REACH",
        "EXISTS_ALWAYS",
        "RESPONSE",
        "COVER",
        "TRIGGER",
        "WITHIN",
        "VAR",
        "CYCLE",
        "ACTIVE",
        "CASE",
        "CALLED",
        "CURRENT",
        "PI_CONST",
        "E_CONST",
        "TAU_CONST",
        "AND_KW",
        "OR_KW",
        "NOT_KW",
        "IMPLIES_KW",
        "IFF_KW",
        "XOR_KW",
        "POW",
        "SHIFT_RIGHT",
        "SHIFT_LEFT",
        "LE",
        "GE",
        "EQ",
        "NE",
        "LOGICAL_AND",
        "LOGICAL_OR",
        "IMPLIES",
        "ARROW",
        "RANGE_INT",
        "DOTDOT",
        "SEMI",
        "COMMA",
        "LBRACE",
        "RBRACE",
        "LPAREN",
        "RPAREN",
        "QUESTION",
        "COLON",
        "DOT",
        "SLASH",
        "STAR",
        "BANG",
        "PLUS",
        "MINUS",
        "PERCENT",
        "AMP",
        "CARET",
        "PIPE",
        "LT",
        "GT",
        "FLOAT",
        "HEX_INT",
        "POSITIVE_INT",
        "INT",
        "TRUE",
        "FALSE",
        "UFUNC_NAME",
        "ID",
        "STRING",
        "MULTILINE_COMMENT",
        "LINE_COMMENT",
        "PYTHON_COMMENT",
        "WS",
    ]

    RULE_query = 0
    RULE_bmc_num_expression_entry = 1
    RULE_bmc_cond_expression_entry = 2
    RULE_init_clause = 3
    RULE_init_target = 4
    RULE_assume_clause = 5
    RULE_frame_assume = 6
    RULE_event_assume = 7
    RULE_cardinality_assume = 8
    RULE_check_clause = 9
    RULE_property_kind = 10
    RULE_property_body = 11
    RULE_response_property_body = 12
    RULE_string_list = 13
    RULE_bool_cmp_op = 14
    RULE_event_range_selector = 15
    RULE_event_cycle_selector = 16
    RULE_frame_selector = 17
    RULE_positive_integer = 18
    RULE_integer_literal = 19
    RULE_bmc_num_expression = 20
    RULE_bmc_cond_expression = 21
    RULE_bmc_boolean_atom = 22
    RULE_num_literal = 23
    RULE_bool_literal = 24
    RULE_math_const = 25
    RULE_string_literal = 26

    ruleNames = [
        "query",
        "bmc_num_expression_entry",
        "bmc_cond_expression_entry",
        "init_clause",
        "init_target",
        "assume_clause",
        "frame_assume",
        "event_assume",
        "cardinality_assume",
        "check_clause",
        "property_kind",
        "property_body",
        "response_property_body",
        "string_list",
        "bool_cmp_op",
        "event_range_selector",
        "event_cycle_selector",
        "frame_selector",
        "positive_integer",
        "integer_literal",
        "bmc_num_expression",
        "bmc_cond_expression",
        "bmc_boolean_atom",
        "num_literal",
        "bool_literal",
        "math_const",
        "string_literal",
    ]

    EOF = Token.EOF
    INIT = 1
    COLD = 2
    TERMINATED = 3
    STATE = 4
    WHERE = 5
    ASSUME = 6
    ALWAYS = 7
    AT = 8
    EVENT = 9
    EVENTS = 10
    CARDINALITY = 11
    ANY = 12
    AT_MOST_ONE = 13
    CHECK = 14
    REACH = 15
    FORBID = 16
    INVARIANT = 17
    MUST_REACH = 18
    EXISTS_ALWAYS = 19
    RESPONSE = 20
    COVER = 21
    TRIGGER = 22
    WITHIN = 23
    VAR = 24
    CYCLE = 25
    ACTIVE = 26
    CASE = 27
    CALLED = 28
    CURRENT = 29
    PI_CONST = 30
    E_CONST = 31
    TAU_CONST = 32
    AND_KW = 33
    OR_KW = 34
    NOT_KW = 35
    IMPLIES_KW = 36
    IFF_KW = 37
    XOR_KW = 38
    POW = 39
    SHIFT_RIGHT = 40
    SHIFT_LEFT = 41
    LE = 42
    GE = 43
    EQ = 44
    NE = 45
    LOGICAL_AND = 46
    LOGICAL_OR = 47
    IMPLIES = 48
    ARROW = 49
    RANGE_INT = 50
    DOTDOT = 51
    SEMI = 52
    COMMA = 53
    LBRACE = 54
    RBRACE = 55
    LPAREN = 56
    RPAREN = 57
    QUESTION = 58
    COLON = 59
    DOT = 60
    SLASH = 61
    STAR = 62
    BANG = 63
    PLUS = 64
    MINUS = 65
    PERCENT = 66
    AMP = 67
    CARET = 68
    PIPE = 69
    LT = 70
    GT = 71
    FLOAT = 72
    HEX_INT = 73
    POSITIVE_INT = 74
    INT = 75
    TRUE = 76
    FALSE = 77
    UFUNC_NAME = 78
    ID = 79
    STRING = 80
    MULTILINE_COMMENT = 81
    LINE_COMMENT = 82
    PYTHON_COMMENT = 83
    WS = 84

    def __init__(self, input: TokenStream, output: TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.9.3")
        self._interp = ParserATNSimulator(
            self, self.atn, self.decisionsToDFA, self.sharedContextCache
        )
        self._predicates = None

    class QueryContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def check_clause(self):
            return self.getTypedRuleContext(BmcQueryParser.Check_clauseContext, 0)

        def EOF(self):
            return self.getToken(BmcQueryParser.EOF, 0)

        def init_clause(self):
            return self.getTypedRuleContext(BmcQueryParser.Init_clauseContext, 0)

        def assume_clause(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(BmcQueryParser.Assume_clauseContext)
            else:
                return self.getTypedRuleContext(BmcQueryParser.Assume_clauseContext, i)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_query

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterQuery"):
                listener.enterQuery(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitQuery"):
                listener.exitQuery(self)

    def query(self):

        localctx = BmcQueryParser.QueryContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_query)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 55
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == BmcQueryParser.INIT:
                self.state = 54
                self.init_clause()

            self.state = 60
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == BmcQueryParser.ASSUME:
                self.state = 57
                self.assume_clause()
                self.state = 62
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 63
            self.check_clause()
            self.state = 64
            self.match(BmcQueryParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Bmc_num_expression_entryContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def bmc_num_expression(self):
            return self.getTypedRuleContext(BmcQueryParser.Bmc_num_expressionContext, 0)

        def EOF(self):
            return self.getToken(BmcQueryParser.EOF, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_bmc_num_expression_entry

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBmc_num_expression_entry"):
                listener.enterBmc_num_expression_entry(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBmc_num_expression_entry"):
                listener.exitBmc_num_expression_entry(self)

    def bmc_num_expression_entry(self):

        localctx = BmcQueryParser.Bmc_num_expression_entryContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 2, self.RULE_bmc_num_expression_entry)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 66
            self.bmc_num_expression(0)
            self.state = 67
            self.match(BmcQueryParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Bmc_cond_expression_entryContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def bmc_cond_expression(self):
            return self.getTypedRuleContext(
                BmcQueryParser.Bmc_cond_expressionContext, 0
            )

        def EOF(self):
            return self.getToken(BmcQueryParser.EOF, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_bmc_cond_expression_entry

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBmc_cond_expression_entry"):
                listener.enterBmc_cond_expression_entry(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBmc_cond_expression_entry"):
                listener.exitBmc_cond_expression_entry(self)

    def bmc_cond_expression_entry(self):

        localctx = BmcQueryParser.Bmc_cond_expression_entryContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 4, self.RULE_bmc_cond_expression_entry)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 69
            self.bmc_cond_expression(0)
            self.state = 70
            self.match(BmcQueryParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Init_clauseContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def INIT(self):
            return self.getToken(BmcQueryParser.INIT, 0)

        def init_target(self):
            return self.getTypedRuleContext(BmcQueryParser.Init_targetContext, 0)

        def SEMI(self):
            return self.getToken(BmcQueryParser.SEMI, 0)

        def WHERE(self):
            return self.getToken(BmcQueryParser.WHERE, 0)

        def bmc_cond_expression(self):
            return self.getTypedRuleContext(
                BmcQueryParser.Bmc_cond_expressionContext, 0
            )

        def getRuleIndex(self):
            return BmcQueryParser.RULE_init_clause

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterInit_clause"):
                listener.enterInit_clause(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitInit_clause"):
                listener.exitInit_clause(self)

    def init_clause(self):

        localctx = BmcQueryParser.Init_clauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_init_clause)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 72
            self.match(BmcQueryParser.INIT)
            self.state = 73
            self.init_target()
            self.state = 76
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == BmcQueryParser.WHERE:
                self.state = 74
                self.match(BmcQueryParser.WHERE)
                self.state = 75
                self.bmc_cond_expression(0)

            self.state = 78
            self.match(BmcQueryParser.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Init_targetContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def COLD(self):
            return self.getToken(BmcQueryParser.COLD, 0)

        def TERMINATED(self):
            return self.getToken(BmcQueryParser.TERMINATED, 0)

        def STATE(self):
            return self.getToken(BmcQueryParser.STATE, 0)

        def LPAREN(self):
            return self.getToken(BmcQueryParser.LPAREN, 0)

        def string_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.String_literalContext, 0)

        def RPAREN(self):
            return self.getToken(BmcQueryParser.RPAREN, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_init_target

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterInit_target"):
                listener.enterInit_target(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitInit_target"):
                listener.exitInit_target(self)

    def init_target(self):

        localctx = BmcQueryParser.Init_targetContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_init_target)
        try:
            self.state = 87
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.COLD]:
                self.enterOuterAlt(localctx, 1)
                self.state = 80
                self.match(BmcQueryParser.COLD)
                pass
            elif token in [BmcQueryParser.TERMINATED]:
                self.enterOuterAlt(localctx, 2)
                self.state = 81
                self.match(BmcQueryParser.TERMINATED)
                pass
            elif token in [BmcQueryParser.STATE]:
                self.enterOuterAlt(localctx, 3)
                self.state = 82
                self.match(BmcQueryParser.STATE)
                self.state = 83
                self.match(BmcQueryParser.LPAREN)
                self.state = 84
                self.string_literal()
                self.state = 85
                self.match(BmcQueryParser.RPAREN)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Assume_clauseContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def frame_assume(self):
            return self.getTypedRuleContext(BmcQueryParser.Frame_assumeContext, 0)

        def event_assume(self):
            return self.getTypedRuleContext(BmcQueryParser.Event_assumeContext, 0)

        def cardinality_assume(self):
            return self.getTypedRuleContext(BmcQueryParser.Cardinality_assumeContext, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_assume_clause

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterAssume_clause"):
                listener.enterAssume_clause(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitAssume_clause"):
                listener.exitAssume_clause(self)

    def assume_clause(self):

        localctx = BmcQueryParser.Assume_clauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_assume_clause)
        try:
            self.state = 92
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 4, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 89
                self.frame_assume()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 90
                self.event_assume()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 91
                self.cardinality_assume()
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Frame_assumeContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ASSUME(self):
            return self.getToken(BmcQueryParser.ASSUME, 0)

        def COLON(self):
            return self.getToken(BmcQueryParser.COLON, 0)

        def bmc_cond_expression(self):
            return self.getTypedRuleContext(
                BmcQueryParser.Bmc_cond_expressionContext, 0
            )

        def SEMI(self):
            return self.getToken(BmcQueryParser.SEMI, 0)

        def ALWAYS(self):
            return self.getToken(BmcQueryParser.ALWAYS, 0)

        def AT(self):
            return self.getToken(BmcQueryParser.AT, 0)

        def integer_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.Integer_literalContext, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_frame_assume

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterFrame_assume"):
                listener.enterFrame_assume(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitFrame_assume"):
                listener.exitFrame_assume(self)

    def frame_assume(self):

        localctx = BmcQueryParser.Frame_assumeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_frame_assume)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 94
            self.match(BmcQueryParser.ASSUME)
            self.state = 98
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ALWAYS]:
                self.state = 95
                self.match(BmcQueryParser.ALWAYS)
                pass
            elif token in [BmcQueryParser.AT]:
                self.state = 96
                self.match(BmcQueryParser.AT)
                self.state = 97
                self.integer_literal()
                pass
            else:
                raise NoViableAltException(self)

            self.state = 100
            self.match(BmcQueryParser.COLON)
            self.state = 101
            self.bmc_cond_expression(0)
            self.state = 102
            self.match(BmcQueryParser.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Event_assumeContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ASSUME(self):
            return self.getToken(BmcQueryParser.ASSUME, 0)

        def EVENT(self):
            return self.getToken(BmcQueryParser.EVENT, 0)

        def LPAREN(self):
            return self.getToken(BmcQueryParser.LPAREN, 0)

        def string_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.String_literalContext, 0)

        def COMMA(self):
            return self.getToken(BmcQueryParser.COMMA, 0)

        def event_range_selector(self):
            return self.getTypedRuleContext(
                BmcQueryParser.Event_range_selectorContext, 0
            )

        def RPAREN(self):
            return self.getToken(BmcQueryParser.RPAREN, 0)

        def bool_cmp_op(self):
            return self.getTypedRuleContext(BmcQueryParser.Bool_cmp_opContext, 0)

        def bool_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.Bool_literalContext, 0)

        def SEMI(self):
            return self.getToken(BmcQueryParser.SEMI, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_event_assume

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEvent_assume"):
                listener.enterEvent_assume(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEvent_assume"):
                listener.exitEvent_assume(self)

    def event_assume(self):

        localctx = BmcQueryParser.Event_assumeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_event_assume)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 104
            self.match(BmcQueryParser.ASSUME)
            self.state = 105
            self.match(BmcQueryParser.EVENT)
            self.state = 106
            self.match(BmcQueryParser.LPAREN)
            self.state = 107
            self.string_literal()
            self.state = 108
            self.match(BmcQueryParser.COMMA)
            self.state = 109
            self.event_range_selector()
            self.state = 110
            self.match(BmcQueryParser.RPAREN)
            self.state = 111
            self.bool_cmp_op()
            self.state = 112
            self.bool_literal()
            self.state = 113
            self.match(BmcQueryParser.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Cardinality_assumeContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ASSUME(self):
            return self.getToken(BmcQueryParser.ASSUME, 0)

        def EVENTS(self):
            return self.getToken(BmcQueryParser.EVENTS, 0)

        def CARDINALITY(self):
            return self.getToken(BmcQueryParser.CARDINALITY, 0)

        def SEMI(self):
            return self.getToken(BmcQueryParser.SEMI, 0)

        def ANY(self):
            return self.getToken(BmcQueryParser.ANY, 0)

        def AT_MOST_ONE(self):
            return self.getToken(BmcQueryParser.AT_MOST_ONE, 0)

        def LBRACE(self):
            return self.getToken(BmcQueryParser.LBRACE, 0)

        def string_list(self):
            return self.getTypedRuleContext(BmcQueryParser.String_listContext, 0)

        def RBRACE(self):
            return self.getToken(BmcQueryParser.RBRACE, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_cardinality_assume

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCardinality_assume"):
                listener.enterCardinality_assume(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCardinality_assume"):
                listener.exitCardinality_assume(self)

    def cardinality_assume(self):

        localctx = BmcQueryParser.Cardinality_assumeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_cardinality_assume)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 115
            self.match(BmcQueryParser.ASSUME)
            self.state = 116
            self.match(BmcQueryParser.EVENTS)
            self.state = 117
            self.match(BmcQueryParser.CARDINALITY)
            self.state = 124
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ANY]:
                self.state = 118
                self.match(BmcQueryParser.ANY)
                pass
            elif token in [BmcQueryParser.AT_MOST_ONE]:
                self.state = 119
                self.match(BmcQueryParser.AT_MOST_ONE)
                self.state = 120
                self.match(BmcQueryParser.LBRACE)
                self.state = 121
                self.string_list()
                self.state = 122
                self.match(BmcQueryParser.RBRACE)
                pass
            else:
                raise NoViableAltException(self)

            self.state = 126
            self.match(BmcQueryParser.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Check_clauseContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def CHECK(self):
            return self.getToken(BmcQueryParser.CHECK, 0)

        def property_kind(self):
            return self.getTypedRuleContext(BmcQueryParser.Property_kindContext, 0)

        def LE(self):
            return self.getToken(BmcQueryParser.LE, 0)

        def positive_integer(self):
            return self.getTypedRuleContext(BmcQueryParser.Positive_integerContext, 0)

        def COLON(self):
            return self.getToken(BmcQueryParser.COLON, 0)

        def property_body(self):
            return self.getTypedRuleContext(BmcQueryParser.Property_bodyContext, 0)

        def SEMI(self):
            return self.getToken(BmcQueryParser.SEMI, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_check_clause

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCheck_clause"):
                listener.enterCheck_clause(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCheck_clause"):
                listener.exitCheck_clause(self)

    def check_clause(self):

        localctx = BmcQueryParser.Check_clauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_check_clause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 128
            self.match(BmcQueryParser.CHECK)
            self.state = 129
            self.property_kind()
            self.state = 130
            self.match(BmcQueryParser.LE)
            self.state = 131
            self.positive_integer()
            self.state = 132
            self.match(BmcQueryParser.COLON)
            self.state = 133
            self.property_body()
            self.state = 134
            self.match(BmcQueryParser.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Property_kindContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def REACH(self):
            return self.getToken(BmcQueryParser.REACH, 0)

        def FORBID(self):
            return self.getToken(BmcQueryParser.FORBID, 0)

        def INVARIANT(self):
            return self.getToken(BmcQueryParser.INVARIANT, 0)

        def MUST_REACH(self):
            return self.getToken(BmcQueryParser.MUST_REACH, 0)

        def EXISTS_ALWAYS(self):
            return self.getToken(BmcQueryParser.EXISTS_ALWAYS, 0)

        def RESPONSE(self):
            return self.getToken(BmcQueryParser.RESPONSE, 0)

        def COVER(self):
            return self.getToken(BmcQueryParser.COVER, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_property_kind

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterProperty_kind"):
                listener.enterProperty_kind(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitProperty_kind"):
                listener.exitProperty_kind(self)

    def property_kind(self):

        localctx = BmcQueryParser.Property_kindContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_property_kind)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 136
            _la = self._input.LA(1)
            if not (
                ((_la) & ~0x3F) == 0
                and (
                    (1 << _la)
                    & (
                        (1 << BmcQueryParser.REACH)
                        | (1 << BmcQueryParser.FORBID)
                        | (1 << BmcQueryParser.INVARIANT)
                        | (1 << BmcQueryParser.MUST_REACH)
                        | (1 << BmcQueryParser.EXISTS_ALWAYS)
                        | (1 << BmcQueryParser.RESPONSE)
                        | (1 << BmcQueryParser.COVER)
                    )
                )
                != 0
            ):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Property_bodyContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def response_property_body(self):
            return self.getTypedRuleContext(
                BmcQueryParser.Response_property_bodyContext, 0
            )

        def bmc_cond_expression(self):
            return self.getTypedRuleContext(
                BmcQueryParser.Bmc_cond_expressionContext, 0
            )

        def getRuleIndex(self):
            return BmcQueryParser.RULE_property_body

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterProperty_body"):
                listener.enterProperty_body(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitProperty_body"):
                listener.exitProperty_body(self)

    def property_body(self):

        localctx = BmcQueryParser.Property_bodyContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_property_body)
        try:
            self.state = 140
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.TRIGGER]:
                self.enterOuterAlt(localctx, 1)
                self.state = 138
                self.response_property_body()
                pass
            elif token in [
                BmcQueryParser.TERMINATED,
                BmcQueryParser.EVENT,
                BmcQueryParser.VAR,
                BmcQueryParser.CYCLE,
                BmcQueryParser.ACTIVE,
                BmcQueryParser.CASE,
                BmcQueryParser.CALLED,
                BmcQueryParser.PI_CONST,
                BmcQueryParser.E_CONST,
                BmcQueryParser.TAU_CONST,
                BmcQueryParser.NOT_KW,
                BmcQueryParser.LPAREN,
                BmcQueryParser.BANG,
                BmcQueryParser.PLUS,
                BmcQueryParser.MINUS,
                BmcQueryParser.FLOAT,
                BmcQueryParser.HEX_INT,
                BmcQueryParser.POSITIVE_INT,
                BmcQueryParser.INT,
                BmcQueryParser.TRUE,
                BmcQueryParser.FALSE,
                BmcQueryParser.UFUNC_NAME,
                BmcQueryParser.ID,
            ]:
                self.enterOuterAlt(localctx, 2)
                self.state = 139
                self.bmc_cond_expression(0)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Response_property_bodyContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def TRIGGER(self):
            return self.getToken(BmcQueryParser.TRIGGER, 0)

        def bmc_cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    BmcQueryParser.Bmc_cond_expressionContext
                )
            else:
                return self.getTypedRuleContext(
                    BmcQueryParser.Bmc_cond_expressionContext, i
                )

        def ARROW(self):
            return self.getToken(BmcQueryParser.ARROW, 0)

        def WITHIN(self):
            return self.getToken(BmcQueryParser.WITHIN, 0)

        def positive_integer(self):
            return self.getTypedRuleContext(BmcQueryParser.Positive_integerContext, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_response_property_body

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterResponse_property_body"):
                listener.enterResponse_property_body(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitResponse_property_body"):
                listener.exitResponse_property_body(self)

    def response_property_body(self):

        localctx = BmcQueryParser.Response_property_bodyContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 24, self.RULE_response_property_body)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 142
            self.match(BmcQueryParser.TRIGGER)
            self.state = 143
            self.bmc_cond_expression(0)
            self.state = 144
            self.match(BmcQueryParser.ARROW)
            self.state = 145
            self.match(BmcQueryParser.WITHIN)
            self.state = 146
            self.positive_integer()
            self.state = 147
            self.bmc_cond_expression(0)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class String_listContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def string_literal(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(BmcQueryParser.String_literalContext)
            else:
                return self.getTypedRuleContext(BmcQueryParser.String_literalContext, i)

        def COMMA(self, i: int = None):
            if i is None:
                return self.getTokens(BmcQueryParser.COMMA)
            else:
                return self.getToken(BmcQueryParser.COMMA, i)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_string_list

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterString_list"):
                listener.enterString_list(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitString_list"):
                listener.exitString_list(self)

    def string_list(self):

        localctx = BmcQueryParser.String_listContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_string_list)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 149
            self.string_literal()
            self.state = 154
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == BmcQueryParser.COMMA:
                self.state = 150
                self.match(BmcQueryParser.COMMA)
                self.state = 151
                self.string_literal()
                self.state = 156
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Bool_cmp_opContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EQ(self):
            return self.getToken(BmcQueryParser.EQ, 0)

        def NE(self):
            return self.getToken(BmcQueryParser.NE, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_bool_cmp_op

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBool_cmp_op"):
                listener.enterBool_cmp_op(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBool_cmp_op"):
                listener.exitBool_cmp_op(self)

    def bool_cmp_op(self):

        localctx = BmcQueryParser.Bool_cmp_opContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_bool_cmp_op)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 157
            _la = self._input.LA(1)
            if not (_la == BmcQueryParser.EQ or _la == BmcQueryParser.NE):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Event_range_selectorContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def STAR(self):
            return self.getToken(BmcQueryParser.STAR, 0)

        def integer_literal(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(BmcQueryParser.Integer_literalContext)
            else:
                return self.getTypedRuleContext(
                    BmcQueryParser.Integer_literalContext, i
                )

        def DOTDOT(self):
            return self.getToken(BmcQueryParser.DOTDOT, 0)

        def RANGE_INT(self):
            return self.getToken(BmcQueryParser.RANGE_INT, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_event_range_selector

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEvent_range_selector"):
                listener.enterEvent_range_selector(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEvent_range_selector"):
                listener.exitEvent_range_selector(self)

    def event_range_selector(self):

        localctx = BmcQueryParser.Event_range_selectorContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 30, self.RULE_event_range_selector)
        try:
            self.state = 166
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 9, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 159
                self.match(BmcQueryParser.STAR)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 160
                self.integer_literal()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 161
                self.integer_literal()
                self.state = 162
                self.match(BmcQueryParser.DOTDOT)
                self.state = 163
                self.integer_literal()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 165
                self.match(BmcQueryParser.RANGE_INT)
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Event_cycle_selectorContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def CURRENT(self):
            return self.getToken(BmcQueryParser.CURRENT, 0)

        def integer_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.Integer_literalContext, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_event_cycle_selector

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEvent_cycle_selector"):
                listener.enterEvent_cycle_selector(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEvent_cycle_selector"):
                listener.exitEvent_cycle_selector(self)

    def event_cycle_selector(self):

        localctx = BmcQueryParser.Event_cycle_selectorContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 32, self.RULE_event_cycle_selector)
        try:
            self.state = 170
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.CURRENT]:
                self.enterOuterAlt(localctx, 1)
                self.state = 168
                self.match(BmcQueryParser.CURRENT)
                pass
            elif token in [BmcQueryParser.POSITIVE_INT, BmcQueryParser.INT]:
                self.enterOuterAlt(localctx, 2)
                self.state = 169
                self.integer_literal()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Frame_selectorContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def CURRENT(self):
            return self.getToken(BmcQueryParser.CURRENT, 0)

        def integer_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.Integer_literalContext, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_frame_selector

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterFrame_selector"):
                listener.enterFrame_selector(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitFrame_selector"):
                listener.exitFrame_selector(self)

    def frame_selector(self):

        localctx = BmcQueryParser.Frame_selectorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_frame_selector)
        try:
            self.state = 174
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.CURRENT]:
                self.enterOuterAlt(localctx, 1)
                self.state = 172
                self.match(BmcQueryParser.CURRENT)
                pass
            elif token in [BmcQueryParser.POSITIVE_INT, BmcQueryParser.INT]:
                self.enterOuterAlt(localctx, 2)
                self.state = 173
                self.integer_literal()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Positive_integerContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def POSITIVE_INT(self):
            return self.getToken(BmcQueryParser.POSITIVE_INT, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_positive_integer

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterPositive_integer"):
                listener.enterPositive_integer(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitPositive_integer"):
                listener.exitPositive_integer(self)

    def positive_integer(self):

        localctx = BmcQueryParser.Positive_integerContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_positive_integer)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 176
            self.match(BmcQueryParser.POSITIVE_INT)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Integer_literalContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def POSITIVE_INT(self):
            return self.getToken(BmcQueryParser.POSITIVE_INT, 0)

        def INT(self):
            return self.getToken(BmcQueryParser.INT, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_integer_literal

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterInteger_literal"):
                listener.enterInteger_literal(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitInteger_literal"):
                listener.exitInteger_literal(self)

    def integer_literal(self):

        localctx = BmcQueryParser.Integer_literalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_integer_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 178
            _la = self._input.LA(1)
            if not (_la == BmcQueryParser.POSITIVE_INT or _la == BmcQueryParser.INT):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Bmc_num_expressionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return BmcQueryParser.RULE_bmc_num_expression

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class FrameVarExprNumContext(Bmc_num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def VAR(self):
            return self.getToken(BmcQueryParser.VAR, 0)

        def LPAREN(self):
            return self.getToken(BmcQueryParser.LPAREN, 0)

        def string_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.String_literalContext, 0)

        def RPAREN(self):
            return self.getToken(BmcQueryParser.RPAREN, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterFrameVarExprNum"):
                listener.enterFrameVarExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitFrameVarExprNum"):
                listener.exitFrameVarExprNum(self)

    class CycleExprNumContext(Bmc_num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def CYCLE(self):
            return self.getToken(BmcQueryParser.CYCLE, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCycleExprNum"):
                listener.enterCycleExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCycleExprNum"):
                listener.exitCycleExprNum(self)

    class UnaryExprNumContext(Bmc_num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_num_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def bmc_num_expression(self):
            return self.getTypedRuleContext(BmcQueryParser.Bmc_num_expressionContext, 0)

        def PLUS(self):
            return self.getToken(BmcQueryParser.PLUS, 0)

        def MINUS(self):
            return self.getToken(BmcQueryParser.MINUS, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterUnaryExprNum"):
                listener.enterUnaryExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitUnaryExprNum"):
                listener.exitUnaryExprNum(self)

    class FuncExprNumContext(Bmc_num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_num_expressionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(BmcQueryParser.LPAREN, 0)

        def bmc_num_expression(self):
            return self.getTypedRuleContext(BmcQueryParser.Bmc_num_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(BmcQueryParser.RPAREN, 0)

        def UFUNC_NAME(self):
            return self.getToken(BmcQueryParser.UFUNC_NAME, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterFuncExprNum"):
                listener.enterFuncExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitFuncExprNum"):
                listener.exitFuncExprNum(self)

    class ConditionalCStyleExprNumContext(Bmc_num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(BmcQueryParser.LPAREN, 0)

        def bmc_cond_expression(self):
            return self.getTypedRuleContext(
                BmcQueryParser.Bmc_cond_expressionContext, 0
            )

        def RPAREN(self):
            return self.getToken(BmcQueryParser.RPAREN, 0)

        def QUESTION(self):
            return self.getToken(BmcQueryParser.QUESTION, 0)

        def bmc_num_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    BmcQueryParser.Bmc_num_expressionContext
                )
            else:
                return self.getTypedRuleContext(
                    BmcQueryParser.Bmc_num_expressionContext, i
                )

        def COLON(self):
            return self.getToken(BmcQueryParser.COLON, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterConditionalCStyleExprNum"):
                listener.enterConditionalCStyleExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitConditionalCStyleExprNum"):
                listener.exitConditionalCStyleExprNum(self)

    class BinaryExprNumContext(Bmc_num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_num_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def bmc_num_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    BmcQueryParser.Bmc_num_expressionContext
                )
            else:
                return self.getTypedRuleContext(
                    BmcQueryParser.Bmc_num_expressionContext, i
                )

        def POW(self):
            return self.getToken(BmcQueryParser.POW, 0)

        def STAR(self):
            return self.getToken(BmcQueryParser.STAR, 0)

        def SLASH(self):
            return self.getToken(BmcQueryParser.SLASH, 0)

        def PERCENT(self):
            return self.getToken(BmcQueryParser.PERCENT, 0)

        def PLUS(self):
            return self.getToken(BmcQueryParser.PLUS, 0)

        def MINUS(self):
            return self.getToken(BmcQueryParser.MINUS, 0)

        def SHIFT_LEFT(self):
            return self.getToken(BmcQueryParser.SHIFT_LEFT, 0)

        def SHIFT_RIGHT(self):
            return self.getToken(BmcQueryParser.SHIFT_RIGHT, 0)

        def AMP(self):
            return self.getToken(BmcQueryParser.AMP, 0)

        def CARET(self):
            return self.getToken(BmcQueryParser.CARET, 0)

        def PIPE(self):
            return self.getToken(BmcQueryParser.PIPE, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprNum"):
                listener.enterBinaryExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprNum"):
                listener.exitBinaryExprNum(self)

    class LiteralExprNumContext(Bmc_num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def num_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.Num_literalContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLiteralExprNum"):
                listener.enterLiteralExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLiteralExprNum"):
                listener.exitLiteralExprNum(self)

    class MathConstExprNumContext(Bmc_num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def math_const(self):
            return self.getTypedRuleContext(BmcQueryParser.Math_constContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterMathConstExprNum"):
                listener.enterMathConstExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitMathConstExprNum"):
                listener.exitMathConstExprNum(self)

    class ParenExprNumContext(Bmc_num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(BmcQueryParser.LPAREN, 0)

        def bmc_num_expression(self):
            return self.getTypedRuleContext(BmcQueryParser.Bmc_num_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(BmcQueryParser.RPAREN, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterParenExprNum"):
                listener.enterParenExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitParenExprNum"):
                listener.exitParenExprNum(self)

    class IdExprNumContext(Bmc_num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ID(self):
            return self.getToken(BmcQueryParser.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterIdExprNum"):
                listener.enterIdExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitIdExprNum"):
                listener.exitIdExprNum(self)

    def bmc_num_expression(self, _p: int = 0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = BmcQueryParser.Bmc_num_expressionContext(
            self, self._ctx, _parentState
        )
        _prevctx = localctx
        _startState = 40
        self.enterRecursionRule(localctx, 40, self.RULE_bmc_num_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 209
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 12, self._ctx)
            if la_ == 1:
                localctx = BmcQueryParser.ParenExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 181
                self.match(BmcQueryParser.LPAREN)
                self.state = 182
                self.bmc_num_expression(0)
                self.state = 183
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = BmcQueryParser.LiteralExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 185
                self.num_literal()
                pass

            elif la_ == 3:
                localctx = BmcQueryParser.IdExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 186
                self.match(BmcQueryParser.ID)
                pass

            elif la_ == 4:
                localctx = BmcQueryParser.MathConstExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 187
                self.math_const()
                pass

            elif la_ == 5:
                localctx = BmcQueryParser.FrameVarExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 188
                self.match(BmcQueryParser.VAR)
                self.state = 189
                self.match(BmcQueryParser.LPAREN)
                self.state = 190
                self.string_literal()
                self.state = 191
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 6:
                localctx = BmcQueryParser.CycleExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 193
                self.match(BmcQueryParser.CYCLE)
                pass

            elif la_ == 7:
                localctx = BmcQueryParser.UnaryExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 194
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == BmcQueryParser.PLUS or _la == BmcQueryParser.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 195
                self.bmc_num_expression(10)
                pass

            elif la_ == 8:
                localctx = BmcQueryParser.FuncExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 196
                localctx.func_name = self.match(BmcQueryParser.UFUNC_NAME)
                self.state = 197
                self.match(BmcQueryParser.LPAREN)
                self.state = 198
                self.bmc_num_expression(0)
                self.state = 199
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 9:
                localctx = BmcQueryParser.ConditionalCStyleExprNumContext(
                    self, localctx
                )
                self._ctx = localctx
                _prevctx = localctx
                self.state = 201
                self.match(BmcQueryParser.LPAREN)
                self.state = 202
                self.bmc_cond_expression(0)
                self.state = 203
                self.match(BmcQueryParser.RPAREN)
                self.state = 204
                self.match(BmcQueryParser.QUESTION)
                self.state = 205
                self.bmc_num_expression(0)
                self.state = 206
                self.match(BmcQueryParser.COLON)
                self.state = 207
                self.bmc_num_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 234
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 14, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 232
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 13, self._ctx)
                    if la_ == 1:
                        localctx = BmcQueryParser.BinaryExprNumContext(
                            self,
                            BmcQueryParser.Bmc_num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_bmc_num_expression
                        )
                        self.state = 211
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 9)"
                            )
                        self.state = 212
                        localctx.op = self.match(BmcQueryParser.POW)
                        self.state = 213
                        self.bmc_num_expression(9)
                        pass

                    elif la_ == 2:
                        localctx = BmcQueryParser.BinaryExprNumContext(
                            self,
                            BmcQueryParser.Bmc_num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_bmc_num_expression
                        )
                        self.state = 214
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 215
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la - 61) & ~0x3F) == 0
                            and (
                                (1 << (_la - 61))
                                & (
                                    (1 << (BmcQueryParser.SLASH - 61))
                                    | (1 << (BmcQueryParser.STAR - 61))
                                    | (1 << (BmcQueryParser.PERCENT - 61))
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 216
                        self.bmc_num_expression(9)
                        pass

                    elif la_ == 3:
                        localctx = BmcQueryParser.BinaryExprNumContext(
                            self,
                            BmcQueryParser.Bmc_num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_bmc_num_expression
                        )
                        self.state = 217
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 218
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == BmcQueryParser.PLUS or _la == BmcQueryParser.MINUS
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 219
                        self.bmc_num_expression(8)
                        pass

                    elif la_ == 4:
                        localctx = BmcQueryParser.BinaryExprNumContext(
                            self,
                            BmcQueryParser.Bmc_num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_bmc_num_expression
                        )
                        self.state = 220
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 221
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == BmcQueryParser.SHIFT_RIGHT
                            or _la == BmcQueryParser.SHIFT_LEFT
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 222
                        self.bmc_num_expression(7)
                        pass

                    elif la_ == 5:
                        localctx = BmcQueryParser.BinaryExprNumContext(
                            self,
                            BmcQueryParser.Bmc_num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_bmc_num_expression
                        )
                        self.state = 223
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 224
                        localctx.op = self.match(BmcQueryParser.AMP)
                        self.state = 225
                        self.bmc_num_expression(6)
                        pass

                    elif la_ == 6:
                        localctx = BmcQueryParser.BinaryExprNumContext(
                            self,
                            BmcQueryParser.Bmc_num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_bmc_num_expression
                        )
                        self.state = 226
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 227
                        localctx.op = self.match(BmcQueryParser.CARET)
                        self.state = 228
                        self.bmc_num_expression(5)
                        pass

                    elif la_ == 7:
                        localctx = BmcQueryParser.BinaryExprNumContext(
                            self,
                            BmcQueryParser.Bmc_num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_bmc_num_expression
                        )
                        self.state = 229
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 230
                        localctx.op = self.match(BmcQueryParser.PIPE)
                        self.state = 231
                        self.bmc_num_expression(4)
                        pass

                self.state = 236
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 14, self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx

    class Bmc_cond_expressionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return BmcQueryParser.RULE_bmc_cond_expression

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class ConditionalCStyleExprCondContext(Bmc_cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_cond_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(BmcQueryParser.LPAREN, 0)

        def bmc_cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    BmcQueryParser.Bmc_cond_expressionContext
                )
            else:
                return self.getTypedRuleContext(
                    BmcQueryParser.Bmc_cond_expressionContext, i
                )

        def RPAREN(self):
            return self.getToken(BmcQueryParser.RPAREN, 0)

        def QUESTION(self):
            return self.getToken(BmcQueryParser.QUESTION, 0)

        def COLON(self):
            return self.getToken(BmcQueryParser.COLON, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterConditionalCStyleExprCond"):
                listener.enterConditionalCStyleExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitConditionalCStyleExprCond"):
                listener.exitConditionalCStyleExprCond(self)

    class AtomExprCondContext(Bmc_cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_cond_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def bmc_boolean_atom(self):
            return self.getTypedRuleContext(BmcQueryParser.Bmc_boolean_atomContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterAtomExprCond"):
                listener.enterAtomExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitAtomExprCond"):
                listener.exitAtomExprCond(self)

    class BinaryExprFromCondCondContext(Bmc_cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_cond_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def bmc_cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    BmcQueryParser.Bmc_cond_expressionContext
                )
            else:
                return self.getTypedRuleContext(
                    BmcQueryParser.Bmc_cond_expressionContext, i
                )

        def EQ(self):
            return self.getToken(BmcQueryParser.EQ, 0)

        def NE(self):
            return self.getToken(BmcQueryParser.NE, 0)

        def IFF_KW(self):
            return self.getToken(BmcQueryParser.IFF_KW, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprFromCondCond"):
                listener.enterBinaryExprFromCondCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprFromCondCond"):
                listener.exitBinaryExprFromCondCond(self)

    class BinaryExprCondContext(Bmc_cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_cond_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def bmc_cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    BmcQueryParser.Bmc_cond_expressionContext
                )
            else:
                return self.getTypedRuleContext(
                    BmcQueryParser.Bmc_cond_expressionContext, i
                )

        def LOGICAL_AND(self):
            return self.getToken(BmcQueryParser.LOGICAL_AND, 0)

        def AND_KW(self):
            return self.getToken(BmcQueryParser.AND_KW, 0)

        def XOR_KW(self):
            return self.getToken(BmcQueryParser.XOR_KW, 0)

        def LOGICAL_OR(self):
            return self.getToken(BmcQueryParser.LOGICAL_OR, 0)

        def OR_KW(self):
            return self.getToken(BmcQueryParser.OR_KW, 0)

        def IMPLIES(self):
            return self.getToken(BmcQueryParser.IMPLIES, 0)

        def IMPLIES_KW(self):
            return self.getToken(BmcQueryParser.IMPLIES_KW, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprCond"):
                listener.enterBinaryExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprCond"):
                listener.exitBinaryExprCond(self)

    class BinaryExprFromNumCondContext(Bmc_cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_cond_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def bmc_num_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    BmcQueryParser.Bmc_num_expressionContext
                )
            else:
                return self.getTypedRuleContext(
                    BmcQueryParser.Bmc_num_expressionContext, i
                )

        def LT(self):
            return self.getToken(BmcQueryParser.LT, 0)

        def GT(self):
            return self.getToken(BmcQueryParser.GT, 0)

        def LE(self):
            return self.getToken(BmcQueryParser.LE, 0)

        def GE(self):
            return self.getToken(BmcQueryParser.GE, 0)

        def EQ(self):
            return self.getToken(BmcQueryParser.EQ, 0)

        def NE(self):
            return self.getToken(BmcQueryParser.NE, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprFromNumCond"):
                listener.enterBinaryExprFromNumCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprFromNumCond"):
                listener.exitBinaryExprFromNumCond(self)

    class UnaryExprCondContext(Bmc_cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_cond_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def bmc_cond_expression(self):
            return self.getTypedRuleContext(
                BmcQueryParser.Bmc_cond_expressionContext, 0
            )

        def BANG(self):
            return self.getToken(BmcQueryParser.BANG, 0)

        def NOT_KW(self):
            return self.getToken(BmcQueryParser.NOT_KW, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterUnaryExprCond"):
                listener.enterUnaryExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitUnaryExprCond"):
                listener.exitUnaryExprCond(self)

    class ParenExprCondContext(Bmc_cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_cond_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(BmcQueryParser.LPAREN, 0)

        def bmc_cond_expression(self):
            return self.getTypedRuleContext(
                BmcQueryParser.Bmc_cond_expressionContext, 0
            )

        def RPAREN(self):
            return self.getToken(BmcQueryParser.RPAREN, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterParenExprCond"):
                listener.enterParenExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitParenExprCond"):
                listener.exitParenExprCond(self)

    class LiteralExprCondContext(Bmc_cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_cond_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def bool_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.Bool_literalContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLiteralExprCond"):
                listener.enterLiteralExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLiteralExprCond"):
                listener.exitLiteralExprCond(self)

    def bmc_cond_expression(self, _p: int = 0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = BmcQueryParser.Bmc_cond_expressionContext(
            self, self._ctx, _parentState
        )
        _prevctx = localctx
        _startState = 42
        self.enterRecursionRule(localctx, 42, self.RULE_bmc_cond_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 262
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 15, self._ctx)
            if la_ == 1:
                localctx = BmcQueryParser.ParenExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 238
                self.match(BmcQueryParser.LPAREN)
                self.state = 239
                self.bmc_cond_expression(0)
                self.state = 240
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = BmcQueryParser.LiteralExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 242
                self.bool_literal()
                pass

            elif la_ == 3:
                localctx = BmcQueryParser.AtomExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 243
                self.bmc_boolean_atom()
                pass

            elif la_ == 4:
                localctx = BmcQueryParser.UnaryExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 244
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == BmcQueryParser.NOT_KW or _la == BmcQueryParser.BANG):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 245
                self.bmc_cond_expression(9)
                pass

            elif la_ == 5:
                localctx = BmcQueryParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 246
                self.bmc_num_expression(0)
                self.state = 247
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (
                    ((_la - 42) & ~0x3F) == 0
                    and (
                        (1 << (_la - 42))
                        & (
                            (1 << (BmcQueryParser.LE - 42))
                            | (1 << (BmcQueryParser.GE - 42))
                            | (1 << (BmcQueryParser.LT - 42))
                            | (1 << (BmcQueryParser.GT - 42))
                        )
                    )
                    != 0
                ):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 248
                self.bmc_num_expression(0)
                pass

            elif la_ == 6:
                localctx = BmcQueryParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 250
                self.bmc_num_expression(0)
                self.state = 251
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == BmcQueryParser.EQ or _la == BmcQueryParser.NE):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 252
                self.bmc_num_expression(0)
                pass

            elif la_ == 7:
                localctx = BmcQueryParser.ConditionalCStyleExprCondContext(
                    self, localctx
                )
                self._ctx = localctx
                _prevctx = localctx
                self.state = 254
                self.match(BmcQueryParser.LPAREN)
                self.state = 255
                self.bmc_cond_expression(0)
                self.state = 256
                self.match(BmcQueryParser.RPAREN)
                self.state = 257
                self.match(BmcQueryParser.QUESTION)
                self.state = 258
                self.bmc_cond_expression(0)
                self.state = 259
                self.match(BmcQueryParser.COLON)
                self.state = 260
                self.bmc_cond_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 281
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 17, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 279
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 16, self._ctx)
                    if la_ == 1:
                        localctx = BmcQueryParser.BinaryExprFromCondCondContext(
                            self,
                            BmcQueryParser.Bmc_cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_bmc_cond_expression
                        )
                        self.state = 264
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 265
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la) & ~0x3F) == 0
                            and (
                                (1 << _la)
                                & (
                                    (1 << BmcQueryParser.IFF_KW)
                                    | (1 << BmcQueryParser.EQ)
                                    | (1 << BmcQueryParser.NE)
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 266
                        self.bmc_cond_expression(7)
                        pass

                    elif la_ == 2:
                        localctx = BmcQueryParser.BinaryExprCondContext(
                            self,
                            BmcQueryParser.Bmc_cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_bmc_cond_expression
                        )
                        self.state = 267
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 268
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == BmcQueryParser.AND_KW
                            or _la == BmcQueryParser.LOGICAL_AND
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 269
                        self.bmc_cond_expression(6)
                        pass

                    elif la_ == 3:
                        localctx = BmcQueryParser.BinaryExprCondContext(
                            self,
                            BmcQueryParser.Bmc_cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_bmc_cond_expression
                        )
                        self.state = 270
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 271
                        localctx.op = self.match(BmcQueryParser.XOR_KW)
                        self.state = 272
                        self.bmc_cond_expression(5)
                        pass

                    elif la_ == 4:
                        localctx = BmcQueryParser.BinaryExprCondContext(
                            self,
                            BmcQueryParser.Bmc_cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_bmc_cond_expression
                        )
                        self.state = 273
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 274
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == BmcQueryParser.OR_KW
                            or _la == BmcQueryParser.LOGICAL_OR
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 275
                        self.bmc_cond_expression(4)
                        pass

                    elif la_ == 5:
                        localctx = BmcQueryParser.BinaryExprCondContext(
                            self,
                            BmcQueryParser.Bmc_cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_bmc_cond_expression
                        )
                        self.state = 276
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 277
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == BmcQueryParser.IMPLIES_KW
                            or _la == BmcQueryParser.IMPLIES
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 278
                        self.bmc_cond_expression(2)
                        pass

                self.state = 283
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 17, self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx

    class Bmc_boolean_atomContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ACTIVE(self):
            return self.getToken(BmcQueryParser.ACTIVE, 0)

        def LPAREN(self):
            return self.getToken(BmcQueryParser.LPAREN, 0)

        def string_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.String_literalContext, 0)

        def RPAREN(self):
            return self.getToken(BmcQueryParser.RPAREN, 0)

        def COMMA(self):
            return self.getToken(BmcQueryParser.COMMA, 0)

        def frame_selector(self):
            return self.getTypedRuleContext(BmcQueryParser.Frame_selectorContext, 0)

        def TERMINATED(self):
            return self.getToken(BmcQueryParser.TERMINATED, 0)

        def EVENT(self):
            return self.getToken(BmcQueryParser.EVENT, 0)

        def event_cycle_selector(self):
            return self.getTypedRuleContext(
                BmcQueryParser.Event_cycle_selectorContext, 0
            )

        def CASE(self):
            return self.getToken(BmcQueryParser.CASE, 0)

        def CALLED(self):
            return self.getToken(BmcQueryParser.CALLED, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_bmc_boolean_atom

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBmc_boolean_atom"):
                listener.enterBmc_boolean_atom(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBmc_boolean_atom"):
                listener.exitBmc_boolean_atom(self)

    def bmc_boolean_atom(self):

        localctx = BmcQueryParser.Bmc_boolean_atomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_bmc_boolean_atom)
        self._la = 0  # Token type
        try:
            self.state = 324
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ACTIVE]:
                self.enterOuterAlt(localctx, 1)
                self.state = 284
                self.match(BmcQueryParser.ACTIVE)
                self.state = 285
                self.match(BmcQueryParser.LPAREN)
                self.state = 286
                self.string_literal()
                self.state = 289
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == BmcQueryParser.COMMA:
                    self.state = 287
                    self.match(BmcQueryParser.COMMA)
                    self.state = 288
                    self.frame_selector()

                self.state = 291
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.TERMINATED]:
                self.enterOuterAlt(localctx, 2)
                self.state = 293
                self.match(BmcQueryParser.TERMINATED)
                self.state = 294
                self.match(BmcQueryParser.LPAREN)
                self.state = 296
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if ((_la - 29) & ~0x3F) == 0 and (
                    (1 << (_la - 29))
                    & (
                        (1 << (BmcQueryParser.CURRENT - 29))
                        | (1 << (BmcQueryParser.POSITIVE_INT - 29))
                        | (1 << (BmcQueryParser.INT - 29))
                    )
                ) != 0:
                    self.state = 295
                    self.frame_selector()

                self.state = 298
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.EVENT]:
                self.enterOuterAlt(localctx, 3)
                self.state = 299
                self.match(BmcQueryParser.EVENT)
                self.state = 300
                self.match(BmcQueryParser.LPAREN)
                self.state = 301
                self.string_literal()
                self.state = 302
                self.match(BmcQueryParser.COMMA)
                self.state = 303
                self.event_cycle_selector()
                self.state = 304
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.CASE]:
                self.enterOuterAlt(localctx, 4)
                self.state = 306
                self.match(BmcQueryParser.CASE)
                self.state = 307
                self.match(BmcQueryParser.LPAREN)
                self.state = 308
                self.string_literal()
                self.state = 311
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == BmcQueryParser.COMMA:
                    self.state = 309
                    self.match(BmcQueryParser.COMMA)
                    self.state = 310
                    self.frame_selector()

                self.state = 313
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.CALLED]:
                self.enterOuterAlt(localctx, 5)
                self.state = 315
                self.match(BmcQueryParser.CALLED)
                self.state = 316
                self.match(BmcQueryParser.LPAREN)
                self.state = 317
                self.string_literal()
                self.state = 320
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == BmcQueryParser.COMMA:
                    self.state = 318
                    self.match(BmcQueryParser.COMMA)
                    self.state = 319
                    self.frame_selector()

                self.state = 322
                self.match(BmcQueryParser.RPAREN)
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Num_literalContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def POSITIVE_INT(self):
            return self.getToken(BmcQueryParser.POSITIVE_INT, 0)

        def INT(self):
            return self.getToken(BmcQueryParser.INT, 0)

        def FLOAT(self):
            return self.getToken(BmcQueryParser.FLOAT, 0)

        def HEX_INT(self):
            return self.getToken(BmcQueryParser.HEX_INT, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_num_literal

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterNum_literal"):
                listener.enterNum_literal(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitNum_literal"):
                listener.exitNum_literal(self)

    def num_literal(self):

        localctx = BmcQueryParser.Num_literalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_num_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 326
            _la = self._input.LA(1)
            if not (
                ((_la - 72) & ~0x3F) == 0
                and (
                    (1 << (_la - 72))
                    & (
                        (1 << (BmcQueryParser.FLOAT - 72))
                        | (1 << (BmcQueryParser.HEX_INT - 72))
                        | (1 << (BmcQueryParser.POSITIVE_INT - 72))
                        | (1 << (BmcQueryParser.INT - 72))
                    )
                )
                != 0
            ):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Bool_literalContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def TRUE(self):
            return self.getToken(BmcQueryParser.TRUE, 0)

        def FALSE(self):
            return self.getToken(BmcQueryParser.FALSE, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_bool_literal

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBool_literal"):
                listener.enterBool_literal(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBool_literal"):
                listener.exitBool_literal(self)

    def bool_literal(self):

        localctx = BmcQueryParser.Bool_literalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_bool_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 328
            _la = self._input.LA(1)
            if not (_la == BmcQueryParser.TRUE or _la == BmcQueryParser.FALSE):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Math_constContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def PI_CONST(self):
            return self.getToken(BmcQueryParser.PI_CONST, 0)

        def E_CONST(self):
            return self.getToken(BmcQueryParser.E_CONST, 0)

        def TAU_CONST(self):
            return self.getToken(BmcQueryParser.TAU_CONST, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_math_const

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterMath_const"):
                listener.enterMath_const(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitMath_const"):
                listener.exitMath_const(self)

    def math_const(self):

        localctx = BmcQueryParser.Math_constContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_math_const)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 330
            _la = self._input.LA(1)
            if not (
                ((_la) & ~0x3F) == 0
                and (
                    (1 << _la)
                    & (
                        (1 << BmcQueryParser.PI_CONST)
                        | (1 << BmcQueryParser.E_CONST)
                        | (1 << BmcQueryParser.TAU_CONST)
                    )
                )
                != 0
            ):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class String_literalContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def STRING(self):
            return self.getToken(BmcQueryParser.STRING, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_string_literal

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterString_literal"):
                listener.enterString_literal(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitString_literal"):
                listener.exitString_literal(self)

    def string_literal(self):

        localctx = BmcQueryParser.String_literalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_string_literal)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 332
            self.match(BmcQueryParser.STRING)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    def sempred(self, localctx: RuleContext, ruleIndex: int, predIndex: int):
        if self._predicates == None:
            self._predicates = dict()
        self._predicates[20] = self.bmc_num_expression_sempred
        self._predicates[21] = self.bmc_cond_expression_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def bmc_num_expression_sempred(
        self, localctx: Bmc_num_expressionContext, predIndex: int
    ):
        if predIndex == 0:
            return self.precpred(self._ctx, 9)

        if predIndex == 1:
            return self.precpred(self._ctx, 8)

        if predIndex == 2:
            return self.precpred(self._ctx, 7)

        if predIndex == 3:
            return self.precpred(self._ctx, 6)

        if predIndex == 4:
            return self.precpred(self._ctx, 5)

        if predIndex == 5:
            return self.precpred(self._ctx, 4)

        if predIndex == 6:
            return self.precpred(self._ctx, 3)

    def bmc_cond_expression_sempred(
        self, localctx: Bmc_cond_expressionContext, predIndex: int
    ):
        if predIndex == 7:
            return self.precpred(self._ctx, 6)

        if predIndex == 8:
            return self.precpred(self._ctx, 5)

        if predIndex == 9:
            return self.precpred(self._ctx, 4)

        if predIndex == 10:
            return self.precpred(self._ctx, 3)

        if predIndex == 11:
            return self.precpred(self._ctx, 2)
