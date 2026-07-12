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
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3X")
        buf.write("\u01a1\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7")
        buf.write("\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r\4\16")
        buf.write("\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23\t\23")
        buf.write("\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30\4\31")
        buf.write("\t\31\4\32\t\32\4\33\t\33\4\34\t\34\4\35\t\35\4\36\t\36")
        buf.write('\4\37\t\37\4 \t \4!\t!\4"\t"\3\2\5\2F\n\2\3\2\7\2I\n')
        buf.write("\2\f\2\16\2L\13\2\3\2\3\2\3\2\3\3\3\3\3\3\3\4\3\4\3\4")
        buf.write("\3\5\3\5\3\5\5\5Z\n\5\3\5\3\5\5\5^\n\5\3\5\3\5\3\6\3\6")
        buf.write("\3\6\3\6\3\6\3\6\3\6\5\6i\n\6\3\7\3\7\3\7\3\7\3\7\3\7")
        buf.write("\3\7\7\7r\n\7\f\7\16\7u\13\7\3\7\3\7\5\7y\n\7\3\b\3\b")
        buf.write("\5\b}\n\b\3\t\3\t\3\t\5\t\u0082\n\t\3\n\3\n\3\n\3\n\5")
        buf.write("\n\u0088\n\n\3\n\3\n\3\n\3\n\3\13\3\13\3\13\3\13\3\13")
        buf.write("\3\13\3\13\3\13\3\13\3\13\3\13\3\f\3\f\3\f\3\f\3\f\3\f")
        buf.write("\3\f\3\f\3\f\5\f\u00a2\n\f\3\f\3\f\3\r\3\r\3\r\3\r\3\r")
        buf.write("\3\r\3\r\3\r\3\16\3\16\3\17\3\17\5\17\u00b2\n\17\3\20")
        buf.write("\3\20\3\20\3\20\3\20\3\20\3\20\3\21\3\21\3\21\7\21\u00be")
        buf.write("\n\21\f\21\16\21\u00c1\13\21\3\22\3\22\3\23\3\23\3\23")
        buf.write("\3\23\3\23\3\23\3\23\5\23\u00cc\n\23\3\24\3\24\5\24\u00d0")
        buf.write("\n\24\3\25\3\25\5\25\u00d4\n\25\3\26\3\26\3\27\3\27\3")
        buf.write("\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\3\27\5\27\u00e9\n\27\3\27\3\27\3\27\3")
        buf.write("\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\5\27\u00fb\n\27\3\27\3\27\3\27\3\27\3\27\3")
        buf.write("\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\3\27\3\27\7\27\u0112\n\27\f\27\16\27\u0115")
        buf.write("\13\27\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3")
        buf.write("\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30")
        buf.write("\3\30\3\30\3\30\3\30\3\30\5\30\u0130\n\30\3\30\3\30\3")
        buf.write("\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30")
        buf.write("\3\30\3\30\7\30\u0141\n\30\f\30\16\30\u0144\13\30\3\31")
        buf.write("\3\31\3\31\3\31\3\31\5\31\u014b\n\31\3\31\3\31\3\31\3")
        buf.write("\31\3\31\5\31\u0152\n\31\3\31\3\31\3\31\3\31\3\31\3\31")
        buf.write("\3\31\3\31\3\31\3\31\3\31\3\31\3\31\5\31\u0161\n\31\3")
        buf.write("\31\3\31\3\31\3\31\3\31\5\31\u0168\n\31\3\31\5\31\u016b")
        buf.write("\n\31\3\32\3\32\3\32\7\32\u0170\n\32\f\32\16\32\u0173")
        buf.write("\13\32\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3")
        buf.write("\33\5\33\u017f\n\33\3\34\3\34\3\34\5\34\u0184\n\34\3\35")
        buf.write("\3\35\3\35\3\35\5\35\u018a\n\35\3\35\3\35\5\35\u018e\n")
        buf.write("\35\5\35\u0190\n\35\3\36\3\36\3\36\3\36\3\36\5\36\u0197")
        buf.write('\n\36\3\37\3\37\3 \3 \3!\3!\3"\3"\3"\2\4,.#\2\4\6\b')
        buf.write('\n\f\16\20\22\24\26\30\32\34\36 "$&(*,.\60\62\64\668')
        buf.write(":<>@B\2\20\3\2\22\30\3\2\60\61\3\2EF\4\2BCGG\3\2,-\4\2")
        buf.write("''DD\4\2./KL\4\2))\60\61\4\2%%\62\62\4\2&&\63\63\4\2")
        buf.write('((\64\64\3\2MO\3\2PQ\3\2"$\2\u01c5\2E\3\2\2\2\4P\3\2')
        buf.write("\2\2\6S\3\2\2\2\bV\3\2\2\2\nh\3\2\2\2\fx\3\2\2\2\16|\3")
        buf.write("\2\2\2\20\u0081\3\2\2\2\22\u0083\3\2\2\2\24\u008d\3\2")
        buf.write("\2\2\26\u0098\3\2\2\2\30\u00a5\3\2\2\2\32\u00ad\3\2\2")
        buf.write('\2\34\u00b1\3\2\2\2\36\u00b3\3\2\2\2 \u00ba\3\2\2\2"')
        buf.write("\u00c2\3\2\2\2$\u00cb\3\2\2\2&\u00cf\3\2\2\2(\u00d3\3")
        buf.write("\2\2\2*\u00d5\3\2\2\2,\u00fa\3\2\2\2.\u012f\3\2\2\2\60")
        buf.write("\u016a\3\2\2\2\62\u016c\3\2\2\2\64\u017e\3\2\2\2\66\u0183")
        buf.write("\3\2\2\28\u018f\3\2\2\2:\u0196\3\2\2\2<\u0198\3\2\2\2")
        buf.write(">\u019a\3\2\2\2@\u019c\3\2\2\2B\u019e\3\2\2\2DF\5\b\5")
        buf.write("\2ED\3\2\2\2EF\3\2\2\2FJ\3\2\2\2GI\5\20\t\2HG\3\2\2\2")
        buf.write("IL\3\2\2\2JH\3\2\2\2JK\3\2\2\2KM\3\2\2\2LJ\3\2\2\2MN\5")
        buf.write("\30\r\2NO\7\2\2\3O\3\3\2\2\2PQ\5,\27\2QR\7\2\2\3R\5\3")
        buf.write("\2\2\2ST\5.\30\2TU\7\2\2\3U\7\3\2\2\2VW\7\3\2\2WY\5\n")
        buf.write("\6\2XZ\5\f\7\2YX\3\2\2\2YZ\3\2\2\2Z]\3\2\2\2[\\\7\7\2")
        buf.write("\2\\^\5.\30\2][\3\2\2\2]^\3\2\2\2^_\3\2\2\2_`\78\2\2`")
        buf.write("\t\3\2\2\2ai\7\4\2\2bi\7\5\2\2cd\7\6\2\2de\7<\2\2ef\5")
        buf.write('B"\2fg\7=\2\2gi\3\2\2\2ha\3\2\2\2hb\3\2\2\2hc\3\2\2\2')
        buf.write("i\13\3\2\2\2jk\7\b\2\2ky\7C\2\2lm\7\b\2\2mn\7:\2\2ns\5")
        buf.write("\16\b\2op\79\2\2pr\5\16\b\2qo\3\2\2\2ru\3\2\2\2sq\3\2")
        buf.write("\2\2st\3\2\2\2tv\3\2\2\2us\3\2\2\2vw\7;\2\2wy\3\2\2\2")
        buf.write('xj\3\2\2\2xl\3\2\2\2y\r\3\2\2\2z}\7S\2\2{}\5B"\2|z\3')
        buf.write("\2\2\2|{\3\2\2\2}\17\3\2\2\2~\u0082\5\22\n\2\177\u0082")
        buf.write("\5\24\13\2\u0080\u0082\5\26\f\2\u0081~\3\2\2\2\u0081\177")
        buf.write("\3\2\2\2\u0081\u0080\3\2\2\2\u0082\21\3\2\2\2\u0083\u0087")
        buf.write("\7\t\2\2\u0084\u0088\7\n\2\2\u0085\u0086\7\13\2\2\u0086")
        buf.write("\u0088\5*\26\2\u0087\u0084\3\2\2\2\u0087\u0085\3\2\2\2")
        buf.write("\u0088\u0089\3\2\2\2\u0089\u008a\7@\2\2\u008a\u008b\5")
        buf.write(".\30\2\u008b\u008c\78\2\2\u008c\23\3\2\2\2\u008d\u008e")
        buf.write("\7\t\2\2\u008e\u008f\7\f\2\2\u008f\u0090\7<\2\2\u0090")
        buf.write('\u0091\5B"\2\u0091\u0092\79\2\2\u0092\u0093\5$\23\2\u0093')
        buf.write('\u0094\7=\2\2\u0094\u0095\5"\22\2\u0095\u0096\5> \2\u0096')
        buf.write("\u0097\78\2\2\u0097\25\3\2\2\2\u0098\u0099\7\t\2\2\u0099")
        buf.write("\u009a\7\r\2\2\u009a\u00a1\7\16\2\2\u009b\u00a2\7\17\2")
        buf.write("\2\u009c\u009d\7\20\2\2\u009d\u009e\7:\2\2\u009e\u009f")
        buf.write("\5 \21\2\u009f\u00a0\7;\2\2\u00a0\u00a2\3\2\2\2\u00a1")
        buf.write("\u009b\3\2\2\2\u00a1\u009c\3\2\2\2\u00a2\u00a3\3\2\2\2")
        buf.write("\u00a3\u00a4\78\2\2\u00a4\27\3\2\2\2\u00a5\u00a6\7\21")
        buf.write("\2\2\u00a6\u00a7\5\32\16\2\u00a7\u00a8\7.\2\2\u00a8\u00a9")
        buf.write("\5*\26\2\u00a9\u00aa\7@\2\2\u00aa\u00ab\5\34\17\2\u00ab")
        buf.write("\u00ac\78\2\2\u00ac\31\3\2\2\2\u00ad\u00ae\t\2\2\2\u00ae")
        buf.write("\33\3\2\2\2\u00af\u00b2\5\36\20\2\u00b0\u00b2\5.\30\2")
        buf.write("\u00b1\u00af\3\2\2\2\u00b1\u00b0\3\2\2\2\u00b2\35\3\2")
        buf.write("\2\2\u00b3\u00b4\7\31\2\2\u00b4\u00b5\5.\30\2\u00b5\u00b6")
        buf.write("\7\65\2\2\u00b6\u00b7\7\32\2\2\u00b7\u00b8\5*\26\2\u00b8")
        buf.write('\u00b9\5.\30\2\u00b9\37\3\2\2\2\u00ba\u00bf\5B"\2\u00bb')
        buf.write('\u00bc\79\2\2\u00bc\u00be\5B"\2\u00bd\u00bb\3\2\2\2\u00be')
        buf.write("\u00c1\3\2\2\2\u00bf\u00bd\3\2\2\2\u00bf\u00c0\3\2\2\2")
        buf.write("\u00c0!\3\2\2\2\u00c1\u00bf\3\2\2\2\u00c2\u00c3\t\3\2")
        buf.write("\2\u00c3#\3\2\2\2\u00c4\u00cc\7C\2\2\u00c5\u00cc\5*\26")
        buf.write("\2\u00c6\u00c7\5*\26\2\u00c7\u00c8\7\67\2\2\u00c8\u00c9")
        buf.write("\5*\26\2\u00c9\u00cc\3\2\2\2\u00ca\u00cc\7\66\2\2\u00cb")
        buf.write("\u00c4\3\2\2\2\u00cb\u00c5\3\2\2\2\u00cb\u00c6\3\2\2\2")
        buf.write("\u00cb\u00ca\3\2\2\2\u00cc%\3\2\2\2\u00cd\u00d0\7!\2\2")
        buf.write("\u00ce\u00d0\5*\26\2\u00cf\u00cd\3\2\2\2\u00cf\u00ce\3")
        buf.write("\2\2\2\u00d0'\3\2\2\2\u00d1\u00d4\7!\2\2\u00d2\u00d4")
        buf.write("\5*\26\2\u00d3\u00d1\3\2\2\2\u00d3\u00d2\3\2\2\2\u00d4")
        buf.write(")\3\2\2\2\u00d5\u00d6\7O\2\2\u00d6+\3\2\2\2\u00d7\u00d8")
        buf.write("\b\27\1\2\u00d8\u00d9\7<\2\2\u00d9\u00da\5,\27\2\u00da")
        buf.write("\u00db\7=\2\2\u00db\u00fb\3\2\2\2\u00dc\u00fb\5<\37\2")
        buf.write("\u00dd\u00fb\7S\2\2\u00de\u00fb\5@!\2\u00df\u00e0\7\33")
        buf.write('\2\2\u00e0\u00e1\7<\2\2\u00e1\u00e2\5B"\2\u00e2\u00e3')
        buf.write("\7=\2\2\u00e3\u00fb\3\2\2\2\u00e4\u00fb\7\34\2\2\u00e5")
        buf.write("\u00e6\7\37\2\2\u00e6\u00e8\7<\2\2\u00e7\u00e9\5\62\32")
        buf.write("\2\u00e8\u00e7\3\2\2\2\u00e8\u00e9\3\2\2\2\u00e9\u00ea")
        buf.write("\3\2\2\2\u00ea\u00fb\7=\2\2\u00eb\u00ec\t\4\2\2\u00ec")
        buf.write("\u00fb\5,\27\f\u00ed\u00ee\7R\2\2\u00ee\u00ef\7<\2\2\u00ef")
        buf.write("\u00f0\5,\27\2\u00f0\u00f1\7=\2\2\u00f1\u00fb\3\2\2\2")
        buf.write("\u00f2\u00f3\7<\2\2\u00f3\u00f4\5.\30\2\u00f4\u00f5\7")
        buf.write("=\2\2\u00f5\u00f6\7>\2\2\u00f6\u00f7\5,\27\2\u00f7\u00f8")
        buf.write("\7@\2\2\u00f8\u00f9\5,\27\3\u00f9\u00fb\3\2\2\2\u00fa")
        buf.write("\u00d7\3\2\2\2\u00fa\u00dc\3\2\2\2\u00fa\u00dd\3\2\2\2")
        buf.write("\u00fa\u00de\3\2\2\2\u00fa\u00df\3\2\2\2\u00fa\u00e4\3")
        buf.write("\2\2\2\u00fa\u00e5\3\2\2\2\u00fa\u00eb\3\2\2\2\u00fa\u00ed")
        buf.write("\3\2\2\2\u00fa\u00f2\3\2\2\2\u00fb\u0113\3\2\2\2\u00fc")
        buf.write("\u00fd\f\13\2\2\u00fd\u00fe\7+\2\2\u00fe\u0112\5,\27\13")
        buf.write("\u00ff\u0100\f\n\2\2\u0100\u0101\t\5\2\2\u0101\u0112\5")
        buf.write(",\27\13\u0102\u0103\f\t\2\2\u0103\u0104\t\4\2\2\u0104")
        buf.write("\u0112\5,\27\n\u0105\u0106\f\b\2\2\u0106\u0107\t\6\2\2")
        buf.write("\u0107\u0112\5,\27\t\u0108\u0109\f\7\2\2\u0109\u010a\7")
        buf.write("H\2\2\u010a\u0112\5,\27\b\u010b\u010c\f\6\2\2\u010c\u010d")
        buf.write("\7I\2\2\u010d\u0112\5,\27\7\u010e\u010f\f\5\2\2\u010f")
        buf.write("\u0110\7J\2\2\u0110\u0112\5,\27\6\u0111\u00fc\3\2\2\2")
        buf.write("\u0111\u00ff\3\2\2\2\u0111\u0102\3\2\2\2\u0111\u0105\3")
        buf.write("\2\2\2\u0111\u0108\3\2\2\2\u0111\u010b\3\2\2\2\u0111\u010e")
        buf.write("\3\2\2\2\u0112\u0115\3\2\2\2\u0113\u0111\3\2\2\2\u0113")
        buf.write("\u0114\3\2\2\2\u0114-\3\2\2\2\u0115\u0113\3\2\2\2\u0116")
        buf.write("\u0117\b\30\1\2\u0117\u0118\7<\2\2\u0118\u0119\5.\30\2")
        buf.write("\u0119\u011a\7=\2\2\u011a\u0130\3\2\2\2\u011b\u0130\5")
        buf.write("> \2\u011c\u0130\5\60\31\2\u011d\u011e\t\7\2\2\u011e\u0130")
        buf.write("\5.\30\13\u011f\u0120\5,\27\2\u0120\u0121\t\b\2\2\u0121")
        buf.write("\u0122\5,\27\2\u0122\u0130\3\2\2\2\u0123\u0124\5,\27\2")
        buf.write("\u0124\u0125\t\3\2\2\u0125\u0126\5,\27\2\u0126\u0130\3")
        buf.write("\2\2\2\u0127\u0128\7<\2\2\u0128\u0129\5.\30\2\u0129\u012a")
        buf.write("\7=\2\2\u012a\u012b\7>\2\2\u012b\u012c\5.\30\2\u012c\u012d")
        buf.write("\7@\2\2\u012d\u012e\5.\30\3\u012e\u0130\3\2\2\2\u012f")
        buf.write("\u0116\3\2\2\2\u012f\u011b\3\2\2\2\u012f\u011c\3\2\2\2")
        buf.write("\u012f\u011d\3\2\2\2\u012f\u011f\3\2\2\2\u012f\u0123\3")
        buf.write("\2\2\2\u012f\u0127\3\2\2\2\u0130\u0142\3\2\2\2\u0131\u0132")
        buf.write("\f\b\2\2\u0132\u0133\t\t\2\2\u0133\u0141\5.\30\t\u0134")
        buf.write("\u0135\f\7\2\2\u0135\u0136\t\n\2\2\u0136\u0141\5.\30\b")
        buf.write("\u0137\u0138\f\6\2\2\u0138\u0139\7*\2\2\u0139\u0141\5")
        buf.write(".\30\7\u013a\u013b\f\5\2\2\u013b\u013c\t\13\2\2\u013c")
        buf.write("\u0141\5.\30\6\u013d\u013e\f\4\2\2\u013e\u013f\t\f\2\2")
        buf.write("\u013f\u0141\5.\30\4\u0140\u0131\3\2\2\2\u0140\u0134\3")
        buf.write("\2\2\2\u0140\u0137\3\2\2\2\u0140\u013a\3\2\2\2\u0140\u013d")
        buf.write("\3\2\2\2\u0141\u0144\3\2\2\2\u0142\u0140\3\2\2\2\u0142")
        buf.write("\u0143\3\2\2\2\u0143/\3\2\2\2\u0144\u0142\3\2\2\2\u0145")
        buf.write('\u0146\7\35\2\2\u0146\u0147\7<\2\2\u0147\u014a\5B"\2')
        buf.write("\u0148\u0149\79\2\2\u0149\u014b\5(\25\2\u014a\u0148\3")
        buf.write("\2\2\2\u014a\u014b\3\2\2\2\u014b\u014c\3\2\2\2\u014c\u014d")
        buf.write("\7=\2\2\u014d\u016b\3\2\2\2\u014e\u014f\7\5\2\2\u014f")
        buf.write("\u0151\7<\2\2\u0150\u0152\5(\25\2\u0151\u0150\3\2\2\2")
        buf.write("\u0151\u0152\3\2\2\2\u0152\u0153\3\2\2\2\u0153\u016b\7")
        buf.write("=\2\2\u0154\u0155\7\f\2\2\u0155\u0156\7<\2\2\u0156\u0157")
        buf.write('\5B"\2\u0157\u0158\79\2\2\u0158\u0159\5&\24\2\u0159\u015a')
        buf.write("\7=\2\2\u015a\u016b\3\2\2\2\u015b\u015c\7\36\2\2\u015c")
        buf.write('\u015d\7<\2\2\u015d\u0160\5B"\2\u015e\u015f\79\2\2\u015f')
        buf.write("\u0161\5(\25\2\u0160\u015e\3\2\2\2\u0160\u0161\3\2\2\2")
        buf.write("\u0161\u0162\3\2\2\2\u0162\u0163\7=\2\2\u0163\u016b\3")
        buf.write("\2\2\2\u0164\u0165\7 \2\2\u0165\u0167\7<\2\2\u0166\u0168")
        buf.write("\5\62\32\2\u0167\u0166\3\2\2\2\u0167\u0168\3\2\2\2\u0168")
        buf.write("\u0169\3\2\2\2\u0169\u016b\7=\2\2\u016a\u0145\3\2\2\2")
        buf.write("\u016a\u014e\3\2\2\2\u016a\u0154\3\2\2\2\u016a\u015b\3")
        buf.write("\2\2\2\u016a\u0164\3\2\2\2\u016b\61\3\2\2\2\u016c\u0171")
        buf.write("\5\64\33\2\u016d\u016e\79\2\2\u016e\u0170\5\64\33\2\u016f")
        buf.write("\u016d\3\2\2\2\u0170\u0173\3\2\2\2\u0171\u016f\3\2\2\2")
        buf.write("\u0171\u0172\3\2\2\2\u0172\63\3\2\2\2\u0173\u0171\3\2")
        buf.write('\2\2\u0174\u017f\5B"\2\u0175\u017f\58\35\2\u0176\u0177')
        buf.write("\7S\2\2\u0177\u0178\7?\2\2\u0178\u017f\5\66\34\2\u0179")
        buf.write('\u017a\7\6\2\2\u017a\u017b\7?\2\2\u017b\u017f\5B"\2\u017c')
        buf.write("\u017d\7\7\2\2\u017d\u017f\5.\30\2\u017e\u0174\3\2\2\2")
        buf.write("\u017e\u0175\3\2\2\2\u017e\u0176\3\2\2\2\u017e\u0179\3")
        buf.write("\2\2\2\u017e\u017c\3\2\2\2\u017f\65\3\2\2\2\u0180\u0184")
        buf.write('\5B"\2\u0181\u0184\58\35\2\u0182\u0184\7S\2\2\u0183\u0180')
        buf.write("\3\2\2\2\u0183\u0181\3\2\2\2\u0183\u0182\3\2\2\2\u0184")
        buf.write("\67\3\2\2\2\u0185\u0190\7C\2\2\u0186\u0190\7\66\2\2\u0187")
        buf.write("\u0190\5:\36\2\u0188\u018a\5:\36\2\u0189\u0188\3\2\2\2")
        buf.write("\u0189\u018a\3\2\2\2\u018a\u018b\3\2\2\2\u018b\u018d\7")
        buf.write("\67\2\2\u018c\u018e\5:\36\2\u018d\u018c\3\2\2\2\u018d")
        buf.write("\u018e\3\2\2\2\u018e\u0190\3\2\2\2\u018f\u0185\3\2\2\2")
        buf.write("\u018f\u0186\3\2\2\2\u018f\u0187\3\2\2\2\u018f\u0189\3")
        buf.write("\2\2\2\u01909\3\2\2\2\u0191\u0197\5*\26\2\u0192\u0193")
        buf.write("\7E\2\2\u0193\u0197\5*\26\2\u0194\u0195\7F\2\2\u0195\u0197")
        buf.write("\5*\26\2\u0196\u0191\3\2\2\2\u0196\u0192\3\2\2\2\u0196")
        buf.write("\u0194\3\2\2\2\u0197;\3\2\2\2\u0198\u0199\t\r\2\2\u0199")
        buf.write("=\3\2\2\2\u019a\u019b\t\16\2\2\u019b?\3\2\2\2\u019c\u019d")
        buf.write("\t\17\2\2\u019dA\3\2\2\2\u019e\u019f\7T\2\2\u019fC\3\2")
        buf.write("\2\2%EJY]hsx|\u0081\u0087\u00a1\u00b1\u00bf\u00cb\u00cf")
        buf.write("\u00d3\u00e8\u00fa\u0111\u0113\u012f\u0140\u0142\u014a")
        buf.write("\u0151\u0160\u0167\u016a\u0171\u017e\u0183\u0189\u018d")
        buf.write("\u018f\u0196")
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
        "'havoc'",
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
        "'call_count'",
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
        "'='",
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
        "HAVOC",
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
        "CALL_COUNT",
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
        "ASSIGN",
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
    RULE_init_havoc_clause = 5
    RULE_init_var_ref = 6
    RULE_assume_clause = 7
    RULE_frame_assume = 8
    RULE_event_assume = 9
    RULE_cardinality_assume = 10
    RULE_check_clause = 11
    RULE_property_kind = 12
    RULE_property_body = 13
    RULE_response_property_body = 14
    RULE_string_list = 15
    RULE_bool_cmp_op = 16
    RULE_event_range_selector = 17
    RULE_event_cycle_selector = 18
    RULE_frame_selector = 19
    RULE_integer_literal = 20
    RULE_bmc_num_expression = 21
    RULE_bmc_cond_expression = 22
    RULE_bmc_boolean_atom = 23
    RULE_call_arguments = 24
    RULE_call_argument = 25
    RULE_call_argument_value = 26
    RULE_call_step_selector = 27
    RULE_call_step_point = 28
    RULE_num_literal = 29
    RULE_bool_literal = 30
    RULE_math_const = 31
    RULE_string_literal = 32

    ruleNames = [
        "query",
        "bmc_num_expression_entry",
        "bmc_cond_expression_entry",
        "init_clause",
        "init_target",
        "init_havoc_clause",
        "init_var_ref",
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
        "integer_literal",
        "bmc_num_expression",
        "bmc_cond_expression",
        "bmc_boolean_atom",
        "call_arguments",
        "call_argument",
        "call_argument_value",
        "call_step_selector",
        "call_step_point",
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
    HAVOC = 6
    ASSUME = 7
    ALWAYS = 8
    AT = 9
    EVENT = 10
    EVENTS = 11
    CARDINALITY = 12
    ANY = 13
    AT_MOST_ONE = 14
    CHECK = 15
    REACH = 16
    FORBID = 17
    INVARIANT = 18
    MUST_REACH = 19
    EXISTS_ALWAYS = 20
    RESPONSE = 21
    COVER = 22
    TRIGGER = 23
    WITHIN = 24
    VAR = 25
    CYCLE = 26
    ACTIVE = 27
    CASE = 28
    CALL_COUNT = 29
    CALLED = 30
    CURRENT = 31
    PI_CONST = 32
    E_CONST = 33
    TAU_CONST = 34
    AND_KW = 35
    OR_KW = 36
    NOT_KW = 37
    IMPLIES_KW = 38
    IFF_KW = 39
    XOR_KW = 40
    POW = 41
    SHIFT_RIGHT = 42
    SHIFT_LEFT = 43
    LE = 44
    GE = 45
    EQ = 46
    NE = 47
    LOGICAL_AND = 48
    LOGICAL_OR = 49
    IMPLIES = 50
    ARROW = 51
    RANGE_INT = 52
    DOTDOT = 53
    SEMI = 54
    COMMA = 55
    LBRACE = 56
    RBRACE = 57
    LPAREN = 58
    RPAREN = 59
    QUESTION = 60
    ASSIGN = 61
    COLON = 62
    DOT = 63
    SLASH = 64
    STAR = 65
    BANG = 66
    PLUS = 67
    MINUS = 68
    PERCENT = 69
    AMP = 70
    CARET = 71
    PIPE = 72
    LT = 73
    GT = 74
    FLOAT = 75
    HEX_INT = 76
    INT = 77
    TRUE = 78
    FALSE = 79
    UFUNC_NAME = 80
    ID = 81
    STRING = 82
    MULTILINE_COMMENT = 83
    LINE_COMMENT = 84
    PYTHON_COMMENT = 85
    WS = 86

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
            self.state = 67
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == BmcQueryParser.INIT:
                self.state = 66
                self.init_clause()

            self.state = 72
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == BmcQueryParser.ASSUME:
                self.state = 69
                self.assume_clause()
                self.state = 74
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 75
            self.check_clause()
            self.state = 76
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
            self.state = 78
            self.bmc_num_expression(0)
            self.state = 79
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
            self.state = 81
            self.bmc_cond_expression(0)
            self.state = 82
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

        def init_havoc_clause(self):
            return self.getTypedRuleContext(BmcQueryParser.Init_havoc_clauseContext, 0)

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
            self.state = 84
            self.match(BmcQueryParser.INIT)
            self.state = 85
            self.init_target()
            self.state = 87
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == BmcQueryParser.HAVOC:
                self.state = 86
                self.init_havoc_clause()

            self.state = 91
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == BmcQueryParser.WHERE:
                self.state = 89
                self.match(BmcQueryParser.WHERE)
                self.state = 90
                self.bmc_cond_expression(0)

            self.state = 93
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
            self.state = 102
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.COLD]:
                self.enterOuterAlt(localctx, 1)
                self.state = 95
                self.match(BmcQueryParser.COLD)
                pass
            elif token in [BmcQueryParser.TERMINATED]:
                self.enterOuterAlt(localctx, 2)
                self.state = 96
                self.match(BmcQueryParser.TERMINATED)
                pass
            elif token in [BmcQueryParser.STATE]:
                self.enterOuterAlt(localctx, 3)
                self.state = 97
                self.match(BmcQueryParser.STATE)
                self.state = 98
                self.match(BmcQueryParser.LPAREN)
                self.state = 99
                self.string_literal()
                self.state = 100
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

    class Init_havoc_clauseContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def HAVOC(self):
            return self.getToken(BmcQueryParser.HAVOC, 0)

        def STAR(self):
            return self.getToken(BmcQueryParser.STAR, 0)

        def LBRACE(self):
            return self.getToken(BmcQueryParser.LBRACE, 0)

        def init_var_ref(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(BmcQueryParser.Init_var_refContext)
            else:
                return self.getTypedRuleContext(BmcQueryParser.Init_var_refContext, i)

        def RBRACE(self):
            return self.getToken(BmcQueryParser.RBRACE, 0)

        def COMMA(self, i: int = None):
            if i is None:
                return self.getTokens(BmcQueryParser.COMMA)
            else:
                return self.getToken(BmcQueryParser.COMMA, i)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_init_havoc_clause

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterInit_havoc_clause"):
                listener.enterInit_havoc_clause(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitInit_havoc_clause"):
                listener.exitInit_havoc_clause(self)

    def init_havoc_clause(self):

        localctx = BmcQueryParser.Init_havoc_clauseContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_init_havoc_clause)
        self._la = 0  # Token type
        try:
            self.state = 118
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 6, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 104
                self.match(BmcQueryParser.HAVOC)
                self.state = 105
                self.match(BmcQueryParser.STAR)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 106
                self.match(BmcQueryParser.HAVOC)
                self.state = 107
                self.match(BmcQueryParser.LBRACE)
                self.state = 108
                self.init_var_ref()
                self.state = 113
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == BmcQueryParser.COMMA:
                    self.state = 109
                    self.match(BmcQueryParser.COMMA)
                    self.state = 110
                    self.init_var_ref()
                    self.state = 115
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 116
                self.match(BmcQueryParser.RBRACE)
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Init_var_refContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(BmcQueryParser.ID, 0)

        def string_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.String_literalContext, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_init_var_ref

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterInit_var_ref"):
                listener.enterInit_var_ref(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitInit_var_ref"):
                listener.exitInit_var_ref(self)

    def init_var_ref(self):

        localctx = BmcQueryParser.Init_var_refContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_init_var_ref)
        try:
            self.state = 122
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 120
                self.match(BmcQueryParser.ID)
                pass
            elif token in [BmcQueryParser.STRING]:
                self.enterOuterAlt(localctx, 2)
                self.state = 121
                self.string_literal()
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
        self.enterRule(localctx, 14, self.RULE_assume_clause)
        try:
            self.state = 127
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 8, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 124
                self.frame_assume()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 125
                self.event_assume()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 126
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
        self.enterRule(localctx, 16, self.RULE_frame_assume)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 129
            self.match(BmcQueryParser.ASSUME)
            self.state = 133
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ALWAYS]:
                self.state = 130
                self.match(BmcQueryParser.ALWAYS)
                pass
            elif token in [BmcQueryParser.AT]:
                self.state = 131
                self.match(BmcQueryParser.AT)
                self.state = 132
                self.integer_literal()
                pass
            else:
                raise NoViableAltException(self)

            self.state = 135
            self.match(BmcQueryParser.COLON)
            self.state = 136
            self.bmc_cond_expression(0)
            self.state = 137
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
        self.enterRule(localctx, 18, self.RULE_event_assume)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 139
            self.match(BmcQueryParser.ASSUME)
            self.state = 140
            self.match(BmcQueryParser.EVENT)
            self.state = 141
            self.match(BmcQueryParser.LPAREN)
            self.state = 142
            self.string_literal()
            self.state = 143
            self.match(BmcQueryParser.COMMA)
            self.state = 144
            self.event_range_selector()
            self.state = 145
            self.match(BmcQueryParser.RPAREN)
            self.state = 146
            self.bool_cmp_op()
            self.state = 147
            self.bool_literal()
            self.state = 148
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
        self.enterRule(localctx, 20, self.RULE_cardinality_assume)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 150
            self.match(BmcQueryParser.ASSUME)
            self.state = 151
            self.match(BmcQueryParser.EVENTS)
            self.state = 152
            self.match(BmcQueryParser.CARDINALITY)
            self.state = 159
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ANY]:
                self.state = 153
                self.match(BmcQueryParser.ANY)
                pass
            elif token in [BmcQueryParser.AT_MOST_ONE]:
                self.state = 154
                self.match(BmcQueryParser.AT_MOST_ONE)
                self.state = 155
                self.match(BmcQueryParser.LBRACE)
                self.state = 156
                self.string_list()
                self.state = 157
                self.match(BmcQueryParser.RBRACE)
                pass
            else:
                raise NoViableAltException(self)

            self.state = 161
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

        def integer_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.Integer_literalContext, 0)

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
        self.enterRule(localctx, 22, self.RULE_check_clause)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 163
            self.match(BmcQueryParser.CHECK)
            self.state = 164
            self.property_kind()
            self.state = 165
            self.match(BmcQueryParser.LE)
            self.state = 166
            self.integer_literal()
            self.state = 167
            self.match(BmcQueryParser.COLON)
            self.state = 168
            self.property_body()
            self.state = 169
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
        self.enterRule(localctx, 24, self.RULE_property_kind)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 171
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
        self.enterRule(localctx, 26, self.RULE_property_body)
        try:
            self.state = 175
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.TRIGGER]:
                self.enterOuterAlt(localctx, 1)
                self.state = 173
                self.response_property_body()
                pass
            elif token in [
                BmcQueryParser.TERMINATED,
                BmcQueryParser.EVENT,
                BmcQueryParser.VAR,
                BmcQueryParser.CYCLE,
                BmcQueryParser.ACTIVE,
                BmcQueryParser.CASE,
                BmcQueryParser.CALL_COUNT,
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
                BmcQueryParser.INT,
                BmcQueryParser.TRUE,
                BmcQueryParser.FALSE,
                BmcQueryParser.UFUNC_NAME,
                BmcQueryParser.ID,
            ]:
                self.enterOuterAlt(localctx, 2)
                self.state = 174
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

        def integer_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.Integer_literalContext, 0)

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
        self.enterRule(localctx, 28, self.RULE_response_property_body)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 177
            self.match(BmcQueryParser.TRIGGER)
            self.state = 178
            self.bmc_cond_expression(0)
            self.state = 179
            self.match(BmcQueryParser.ARROW)
            self.state = 180
            self.match(BmcQueryParser.WITHIN)
            self.state = 181
            self.integer_literal()
            self.state = 182
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
        self.enterRule(localctx, 30, self.RULE_string_list)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 184
            self.string_literal()
            self.state = 189
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == BmcQueryParser.COMMA:
                self.state = 185
                self.match(BmcQueryParser.COMMA)
                self.state = 186
                self.string_literal()
                self.state = 191
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
        self.enterRule(localctx, 32, self.RULE_bool_cmp_op)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 192
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
        self.enterRule(localctx, 34, self.RULE_event_range_selector)
        try:
            self.state = 201
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 13, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 194
                self.match(BmcQueryParser.STAR)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 195
                self.integer_literal()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 196
                self.integer_literal()
                self.state = 197
                self.match(BmcQueryParser.DOTDOT)
                self.state = 198
                self.integer_literal()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 200
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
        self.enterRule(localctx, 36, self.RULE_event_cycle_selector)
        try:
            self.state = 205
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.CURRENT]:
                self.enterOuterAlt(localctx, 1)
                self.state = 203
                self.match(BmcQueryParser.CURRENT)
                pass
            elif token in [BmcQueryParser.INT]:
                self.enterOuterAlt(localctx, 2)
                self.state = 204
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
        self.enterRule(localctx, 38, self.RULE_frame_selector)
        try:
            self.state = 209
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.CURRENT]:
                self.enterOuterAlt(localctx, 1)
                self.state = 207
                self.match(BmcQueryParser.CURRENT)
                pass
            elif token in [BmcQueryParser.INT]:
                self.enterOuterAlt(localctx, 2)
                self.state = 208
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

    class Integer_literalContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

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
        self.enterRule(localctx, 40, self.RULE_integer_literal)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 211
            self.match(BmcQueryParser.INT)
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

    class CallCountExprNumContext(Bmc_num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a BmcQueryParser.Bmc_num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def CALL_COUNT(self):
            return self.getToken(BmcQueryParser.CALL_COUNT, 0)

        def LPAREN(self):
            return self.getToken(BmcQueryParser.LPAREN, 0)

        def RPAREN(self):
            return self.getToken(BmcQueryParser.RPAREN, 0)

        def call_arguments(self):
            return self.getTypedRuleContext(BmcQueryParser.Call_argumentsContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCallCountExprNum"):
                listener.enterCallCountExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCallCountExprNum"):
                listener.exitCallCountExprNum(self)

    def bmc_num_expression(self, _p: int = 0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = BmcQueryParser.Bmc_num_expressionContext(
            self, self._ctx, _parentState
        )
        _prevctx = localctx
        _startState = 42
        self.enterRecursionRule(localctx, 42, self.RULE_bmc_num_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 248
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 17, self._ctx)
            if la_ == 1:
                localctx = BmcQueryParser.ParenExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 214
                self.match(BmcQueryParser.LPAREN)
                self.state = 215
                self.bmc_num_expression(0)
                self.state = 216
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = BmcQueryParser.LiteralExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 218
                self.num_literal()
                pass

            elif la_ == 3:
                localctx = BmcQueryParser.IdExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 219
                self.match(BmcQueryParser.ID)
                pass

            elif la_ == 4:
                localctx = BmcQueryParser.MathConstExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 220
                self.math_const()
                pass

            elif la_ == 5:
                localctx = BmcQueryParser.FrameVarExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 221
                self.match(BmcQueryParser.VAR)
                self.state = 222
                self.match(BmcQueryParser.LPAREN)
                self.state = 223
                self.string_literal()
                self.state = 224
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 6:
                localctx = BmcQueryParser.CycleExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 226
                self.match(BmcQueryParser.CYCLE)
                pass

            elif la_ == 7:
                localctx = BmcQueryParser.CallCountExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 227
                self.match(BmcQueryParser.CALL_COUNT)
                self.state = 228
                self.match(BmcQueryParser.LPAREN)
                self.state = 230
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (
                    ((_la) & ~0x3F) == 0
                    and (
                        (1 << _la)
                        & (
                            (1 << BmcQueryParser.STATE)
                            | (1 << BmcQueryParser.WHERE)
                            | (1 << BmcQueryParser.RANGE_INT)
                            | (1 << BmcQueryParser.DOTDOT)
                        )
                    )
                    != 0
                ) or (
                    ((_la - 65) & ~0x3F) == 0
                    and (
                        (1 << (_la - 65))
                        & (
                            (1 << (BmcQueryParser.STAR - 65))
                            | (1 << (BmcQueryParser.PLUS - 65))
                            | (1 << (BmcQueryParser.MINUS - 65))
                            | (1 << (BmcQueryParser.INT - 65))
                            | (1 << (BmcQueryParser.ID - 65))
                            | (1 << (BmcQueryParser.STRING - 65))
                        )
                    )
                    != 0
                ):
                    self.state = 229
                    self.call_arguments()

                self.state = 232
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 8:
                localctx = BmcQueryParser.UnaryExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 233
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == BmcQueryParser.PLUS or _la == BmcQueryParser.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 234
                self.bmc_num_expression(10)
                pass

            elif la_ == 9:
                localctx = BmcQueryParser.FuncExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 235
                localctx.func_name = self.match(BmcQueryParser.UFUNC_NAME)
                self.state = 236
                self.match(BmcQueryParser.LPAREN)
                self.state = 237
                self.bmc_num_expression(0)
                self.state = 238
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 10:
                localctx = BmcQueryParser.ConditionalCStyleExprNumContext(
                    self, localctx
                )
                self._ctx = localctx
                _prevctx = localctx
                self.state = 240
                self.match(BmcQueryParser.LPAREN)
                self.state = 241
                self.bmc_cond_expression(0)
                self.state = 242
                self.match(BmcQueryParser.RPAREN)
                self.state = 243
                self.match(BmcQueryParser.QUESTION)
                self.state = 244
                self.bmc_num_expression(0)
                self.state = 245
                self.match(BmcQueryParser.COLON)
                self.state = 246
                self.bmc_num_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 273
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 19, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 271
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 18, self._ctx)
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
                        self.state = 250
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 9)"
                            )
                        self.state = 251
                        localctx.op = self.match(BmcQueryParser.POW)
                        self.state = 252
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
                        self.state = 253
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 254
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la - 64) & ~0x3F) == 0
                            and (
                                (1 << (_la - 64))
                                & (
                                    (1 << (BmcQueryParser.SLASH - 64))
                                    | (1 << (BmcQueryParser.STAR - 64))
                                    | (1 << (BmcQueryParser.PERCENT - 64))
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 255
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
                        self.state = 256
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 257
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == BmcQueryParser.PLUS or _la == BmcQueryParser.MINUS
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 258
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
                        self.state = 259
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 260
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
                        self.state = 261
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
                        self.state = 262
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 263
                        localctx.op = self.match(BmcQueryParser.AMP)
                        self.state = 264
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
                        self.state = 265
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 266
                        localctx.op = self.match(BmcQueryParser.CARET)
                        self.state = 267
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
                        self.state = 268
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 269
                        localctx.op = self.match(BmcQueryParser.PIPE)
                        self.state = 270
                        self.bmc_num_expression(4)
                        pass

                self.state = 275
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 19, self._ctx)

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
        _startState = 44
        self.enterRecursionRule(localctx, 44, self.RULE_bmc_cond_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 301
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 20, self._ctx)
            if la_ == 1:
                localctx = BmcQueryParser.ParenExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 277
                self.match(BmcQueryParser.LPAREN)
                self.state = 278
                self.bmc_cond_expression(0)
                self.state = 279
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = BmcQueryParser.LiteralExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 281
                self.bool_literal()
                pass

            elif la_ == 3:
                localctx = BmcQueryParser.AtomExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 282
                self.bmc_boolean_atom()
                pass

            elif la_ == 4:
                localctx = BmcQueryParser.UnaryExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 283
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == BmcQueryParser.NOT_KW or _la == BmcQueryParser.BANG):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 284
                self.bmc_cond_expression(9)
                pass

            elif la_ == 5:
                localctx = BmcQueryParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 285
                self.bmc_num_expression(0)
                self.state = 286
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (
                    ((_la - 44) & ~0x3F) == 0
                    and (
                        (1 << (_la - 44))
                        & (
                            (1 << (BmcQueryParser.LE - 44))
                            | (1 << (BmcQueryParser.GE - 44))
                            | (1 << (BmcQueryParser.LT - 44))
                            | (1 << (BmcQueryParser.GT - 44))
                        )
                    )
                    != 0
                ):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 287
                self.bmc_num_expression(0)
                pass

            elif la_ == 6:
                localctx = BmcQueryParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 289
                self.bmc_num_expression(0)
                self.state = 290
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == BmcQueryParser.EQ or _la == BmcQueryParser.NE):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 291
                self.bmc_num_expression(0)
                pass

            elif la_ == 7:
                localctx = BmcQueryParser.ConditionalCStyleExprCondContext(
                    self, localctx
                )
                self._ctx = localctx
                _prevctx = localctx
                self.state = 293
                self.match(BmcQueryParser.LPAREN)
                self.state = 294
                self.bmc_cond_expression(0)
                self.state = 295
                self.match(BmcQueryParser.RPAREN)
                self.state = 296
                self.match(BmcQueryParser.QUESTION)
                self.state = 297
                self.bmc_cond_expression(0)
                self.state = 298
                self.match(BmcQueryParser.COLON)
                self.state = 299
                self.bmc_cond_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 320
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 22, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 318
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 21, self._ctx)
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
                        self.state = 303
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 304
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
                        self.state = 305
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
                        self.state = 306
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 307
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
                        self.state = 308
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
                        self.state = 309
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 310
                        localctx.op = self.match(BmcQueryParser.XOR_KW)
                        self.state = 311
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
                        self.state = 312
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 313
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
                        self.state = 314
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
                        self.state = 315
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 316
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
                        self.state = 317
                        self.bmc_cond_expression(2)
                        pass

                self.state = 322
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 22, self._ctx)

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

        def call_arguments(self):
            return self.getTypedRuleContext(BmcQueryParser.Call_argumentsContext, 0)

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
        self.enterRule(localctx, 46, self.RULE_bmc_boolean_atom)
        self._la = 0  # Token type
        try:
            self.state = 360
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ACTIVE]:
                self.enterOuterAlt(localctx, 1)
                self.state = 323
                self.match(BmcQueryParser.ACTIVE)
                self.state = 324
                self.match(BmcQueryParser.LPAREN)
                self.state = 325
                self.string_literal()
                self.state = 328
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == BmcQueryParser.COMMA:
                    self.state = 326
                    self.match(BmcQueryParser.COMMA)
                    self.state = 327
                    self.frame_selector()

                self.state = 330
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.TERMINATED]:
                self.enterOuterAlt(localctx, 2)
                self.state = 332
                self.match(BmcQueryParser.TERMINATED)
                self.state = 333
                self.match(BmcQueryParser.LPAREN)
                self.state = 335
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == BmcQueryParser.CURRENT or _la == BmcQueryParser.INT:
                    self.state = 334
                    self.frame_selector()

                self.state = 337
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.EVENT]:
                self.enterOuterAlt(localctx, 3)
                self.state = 338
                self.match(BmcQueryParser.EVENT)
                self.state = 339
                self.match(BmcQueryParser.LPAREN)
                self.state = 340
                self.string_literal()
                self.state = 341
                self.match(BmcQueryParser.COMMA)
                self.state = 342
                self.event_cycle_selector()
                self.state = 343
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.CASE]:
                self.enterOuterAlt(localctx, 4)
                self.state = 345
                self.match(BmcQueryParser.CASE)
                self.state = 346
                self.match(BmcQueryParser.LPAREN)
                self.state = 347
                self.string_literal()
                self.state = 350
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == BmcQueryParser.COMMA:
                    self.state = 348
                    self.match(BmcQueryParser.COMMA)
                    self.state = 349
                    self.frame_selector()

                self.state = 352
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.CALLED]:
                self.enterOuterAlt(localctx, 5)
                self.state = 354
                self.match(BmcQueryParser.CALLED)
                self.state = 355
                self.match(BmcQueryParser.LPAREN)
                self.state = 357
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (
                    ((_la) & ~0x3F) == 0
                    and (
                        (1 << _la)
                        & (
                            (1 << BmcQueryParser.STATE)
                            | (1 << BmcQueryParser.WHERE)
                            | (1 << BmcQueryParser.RANGE_INT)
                            | (1 << BmcQueryParser.DOTDOT)
                        )
                    )
                    != 0
                ) or (
                    ((_la - 65) & ~0x3F) == 0
                    and (
                        (1 << (_la - 65))
                        & (
                            (1 << (BmcQueryParser.STAR - 65))
                            | (1 << (BmcQueryParser.PLUS - 65))
                            | (1 << (BmcQueryParser.MINUS - 65))
                            | (1 << (BmcQueryParser.INT - 65))
                            | (1 << (BmcQueryParser.ID - 65))
                            | (1 << (BmcQueryParser.STRING - 65))
                        )
                    )
                    != 0
                ):
                    self.state = 356
                    self.call_arguments()

                self.state = 359
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

    class Call_argumentsContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def call_argument(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(BmcQueryParser.Call_argumentContext)
            else:
                return self.getTypedRuleContext(BmcQueryParser.Call_argumentContext, i)

        def COMMA(self, i: int = None):
            if i is None:
                return self.getTokens(BmcQueryParser.COMMA)
            else:
                return self.getToken(BmcQueryParser.COMMA, i)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_call_arguments

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCall_arguments"):
                listener.enterCall_arguments(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCall_arguments"):
                listener.exitCall_arguments(self)

    def call_arguments(self):

        localctx = BmcQueryParser.Call_argumentsContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_call_arguments)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 362
            self.call_argument()
            self.state = 367
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == BmcQueryParser.COMMA:
                self.state = 363
                self.match(BmcQueryParser.COMMA)
                self.state = 364
                self.call_argument()
                self.state = 369
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Call_argumentContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def string_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.String_literalContext, 0)

        def call_step_selector(self):
            return self.getTypedRuleContext(BmcQueryParser.Call_step_selectorContext, 0)

        def ID(self):
            return self.getToken(BmcQueryParser.ID, 0)

        def ASSIGN(self):
            return self.getToken(BmcQueryParser.ASSIGN, 0)

        def call_argument_value(self):
            return self.getTypedRuleContext(
                BmcQueryParser.Call_argument_valueContext, 0
            )

        def STATE(self):
            return self.getToken(BmcQueryParser.STATE, 0)

        def WHERE(self):
            return self.getToken(BmcQueryParser.WHERE, 0)

        def bmc_cond_expression(self):
            return self.getTypedRuleContext(
                BmcQueryParser.Bmc_cond_expressionContext, 0
            )

        def getRuleIndex(self):
            return BmcQueryParser.RULE_call_argument

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCall_argument"):
                listener.enterCall_argument(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCall_argument"):
                listener.exitCall_argument(self)

    def call_argument(self):

        localctx = BmcQueryParser.Call_argumentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_call_argument)
        try:
            self.state = 380
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.STRING]:
                self.enterOuterAlt(localctx, 1)
                self.state = 370
                self.string_literal()
                pass
            elif token in [
                BmcQueryParser.RANGE_INT,
                BmcQueryParser.DOTDOT,
                BmcQueryParser.STAR,
                BmcQueryParser.PLUS,
                BmcQueryParser.MINUS,
                BmcQueryParser.INT,
            ]:
                self.enterOuterAlt(localctx, 2)
                self.state = 371
                self.call_step_selector()
                pass
            elif token in [BmcQueryParser.ID]:
                self.enterOuterAlt(localctx, 3)
                self.state = 372
                self.match(BmcQueryParser.ID)
                self.state = 373
                self.match(BmcQueryParser.ASSIGN)
                self.state = 374
                self.call_argument_value()
                pass
            elif token in [BmcQueryParser.STATE]:
                self.enterOuterAlt(localctx, 4)
                self.state = 375
                self.match(BmcQueryParser.STATE)
                self.state = 376
                self.match(BmcQueryParser.ASSIGN)
                self.state = 377
                self.string_literal()
                pass
            elif token in [BmcQueryParser.WHERE]:
                self.enterOuterAlt(localctx, 5)
                self.state = 378
                self.match(BmcQueryParser.WHERE)
                self.state = 379
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

    class Call_argument_valueContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def string_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.String_literalContext, 0)

        def call_step_selector(self):
            return self.getTypedRuleContext(BmcQueryParser.Call_step_selectorContext, 0)

        def ID(self):
            return self.getToken(BmcQueryParser.ID, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_call_argument_value

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCall_argument_value"):
                listener.enterCall_argument_value(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCall_argument_value"):
                listener.exitCall_argument_value(self)

    def call_argument_value(self):

        localctx = BmcQueryParser.Call_argument_valueContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 52, self.RULE_call_argument_value)
        try:
            self.state = 385
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.STRING]:
                self.enterOuterAlt(localctx, 1)
                self.state = 382
                self.string_literal()
                pass
            elif token in [
                BmcQueryParser.RANGE_INT,
                BmcQueryParser.DOTDOT,
                BmcQueryParser.STAR,
                BmcQueryParser.PLUS,
                BmcQueryParser.MINUS,
                BmcQueryParser.INT,
            ]:
                self.enterOuterAlt(localctx, 2)
                self.state = 383
                self.call_step_selector()
                pass
            elif token in [BmcQueryParser.ID]:
                self.enterOuterAlt(localctx, 3)
                self.state = 384
                self.match(BmcQueryParser.ID)
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

    class Call_step_selectorContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def STAR(self):
            return self.getToken(BmcQueryParser.STAR, 0)

        def RANGE_INT(self):
            return self.getToken(BmcQueryParser.RANGE_INT, 0)

        def call_step_point(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(BmcQueryParser.Call_step_pointContext)
            else:
                return self.getTypedRuleContext(
                    BmcQueryParser.Call_step_pointContext, i
                )

        def DOTDOT(self):
            return self.getToken(BmcQueryParser.DOTDOT, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_call_step_selector

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCall_step_selector"):
                listener.enterCall_step_selector(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCall_step_selector"):
                listener.exitCall_step_selector(self)

    def call_step_selector(self):

        localctx = BmcQueryParser.Call_step_selectorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_call_step_selector)
        self._la = 0  # Token type
        try:
            self.state = 397
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 33, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 387
                self.match(BmcQueryParser.STAR)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 388
                self.match(BmcQueryParser.RANGE_INT)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 389
                self.call_step_point()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 391
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if ((_la - 67) & ~0x3F) == 0 and (
                    (1 << (_la - 67))
                    & (
                        (1 << (BmcQueryParser.PLUS - 67))
                        | (1 << (BmcQueryParser.MINUS - 67))
                        | (1 << (BmcQueryParser.INT - 67))
                    )
                ) != 0:
                    self.state = 390
                    self.call_step_point()

                self.state = 393
                self.match(BmcQueryParser.DOTDOT)
                self.state = 395
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if ((_la - 67) & ~0x3F) == 0 and (
                    (1 << (_la - 67))
                    & (
                        (1 << (BmcQueryParser.PLUS - 67))
                        | (1 << (BmcQueryParser.MINUS - 67))
                        | (1 << (BmcQueryParser.INT - 67))
                    )
                ) != 0:
                    self.state = 394
                    self.call_step_point()

                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Call_step_pointContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def integer_literal(self):
            return self.getTypedRuleContext(BmcQueryParser.Integer_literalContext, 0)

        def PLUS(self):
            return self.getToken(BmcQueryParser.PLUS, 0)

        def MINUS(self):
            return self.getToken(BmcQueryParser.MINUS, 0)

        def getRuleIndex(self):
            return BmcQueryParser.RULE_call_step_point

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCall_step_point"):
                listener.enterCall_step_point(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCall_step_point"):
                listener.exitCall_step_point(self)

    def call_step_point(self):

        localctx = BmcQueryParser.Call_step_pointContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_call_step_point)
        try:
            self.state = 404
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.INT]:
                self.enterOuterAlt(localctx, 1)
                self.state = 399
                self.integer_literal()
                pass
            elif token in [BmcQueryParser.PLUS]:
                self.enterOuterAlt(localctx, 2)
                self.state = 400
                self.match(BmcQueryParser.PLUS)
                self.state = 401
                self.integer_literal()
                pass
            elif token in [BmcQueryParser.MINUS]:
                self.enterOuterAlt(localctx, 3)
                self.state = 402
                self.match(BmcQueryParser.MINUS)
                self.state = 403
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

    class Num_literalContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

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
        self.enterRule(localctx, 58, self.RULE_num_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 406
            _la = self._input.LA(1)
            if not (
                ((_la - 75) & ~0x3F) == 0
                and (
                    (1 << (_la - 75))
                    & (
                        (1 << (BmcQueryParser.FLOAT - 75))
                        | (1 << (BmcQueryParser.HEX_INT - 75))
                        | (1 << (BmcQueryParser.INT - 75))
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
        self.enterRule(localctx, 60, self.RULE_bool_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 408
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
        self.enterRule(localctx, 62, self.RULE_math_const)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 410
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
        self.enterRule(localctx, 64, self.RULE_string_literal)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 412
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
        self._predicates[21] = self.bmc_num_expression_sempred
        self._predicates[22] = self.bmc_cond_expression_sempred
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
