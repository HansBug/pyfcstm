# Generated from ./pyfcstm/dsl/grammar/Grammar.g4 by ANTLR 4.9.3
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
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3]")
        buf.write("\u02c5\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7")
        buf.write("\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r\4\16")
        buf.write("\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23\t\23")
        buf.write("\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30\4\31")
        buf.write("\t\31\4\32\t\32\4\33\t\33\4\34\t\34\4\35\t\35\4\36\t\36")
        buf.write('\4\37\t\37\4 \t \4!\t!\4"\t"\4#\t#\4$\t$\4%\t%\4&\t')
        buf.write("&\3\2\3\2\3\2\3\3\7\3Q\n\3\f\3\16\3T\13\3\3\3\3\3\3\3")
        buf.write("\3\4\3\4\3\4\3\4\3\4\3\4\3\4\3\5\5\5a\n\5\3\5\3\5\3\5")
        buf.write("\3\5\5\5g\n\5\3\5\3\5\5\5k\n\5\3\5\3\5\3\5\3\5\5\5q\n")
        buf.write("\5\3\5\3\5\7\5u\n\5\f\5\16\5x\13\5\3\5\5\5{\n\5\3\6\3")
        buf.write("\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u0089\n")
        buf.write("\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u0091\n\6\3\6\3\6\3\6\3")
        buf.write("\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u00a1\n")
        buf.write("\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u00a9\n\6\3\6\3\6\3\6\3")
        buf.write("\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u00b9\n")
        buf.write("\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u00c1\n\6\5\6\u00c3\n\6")
        buf.write("\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3")
        buf.write("\7\3\7\5\7\u00d4\n\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3")
        buf.write("\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\5\7\u00e6\n\7\3\7\3\7\3")
        buf.write("\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\5\7\u00f6")
        buf.write("\n\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3")
        buf.write("\7\3\7\5\7\u0106\n\7\3\7\5\7\u0109\n\7\3\b\3\b\5\b\u010d")
        buf.write("\n\b\3\b\3\b\3\b\3\b\3\b\3\b\3\b\3\b\3\b\3\b\3\b\5\b\u011a")
        buf.write("\n\b\3\b\3\b\3\b\5\b\u011f\n\b\3\b\3\b\3\b\3\b\5\b\u0125")
        buf.write("\n\b\3\t\3\t\5\t\u0129\n\t\3\t\3\t\3\t\3\t\3\t\3\t\3\t")
        buf.write("\3\t\3\t\3\t\3\t\5\t\u0136\n\t\3\t\3\t\3\t\5\t\u013b\n")
        buf.write("\t\3\t\3\t\3\t\3\t\5\t\u0141\n\t\3\n\3\n\5\n\u0145\n\n")
        buf.write("\3\n\5\n\u0148\n\n\3\n\3\n\3\n\3\n\3\n\3\n\5\n\u0150\n")
        buf.write("\n\3\n\3\n\3\n\3\n\3\n\5\n\u0157\n\n\3\n\3\n\5\n\u015b")
        buf.write("\n\n\3\n\3\n\3\n\5\n\u0160\n\n\3\n\5\n\u0163\n\n\3\n\3")
        buf.write("\n\3\n\3\n\5\n\u0169\n\n\3\13\3\13\3\13\3\13\5\13\u016f")
        buf.write("\n\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13")
        buf.write("\3\13\3\13\3\13\3\13\3\13\5\13\u0180\n\13\3\13\3\13\3")
        buf.write("\13\3\13\3\13\5\13\u0187\n\13\3\13\3\13\3\13\3\13\5\13")
        buf.write("\u018d\n\13\3\f\3\f\3\f\3\f\5\f\u0193\n\f\3\f\3\f\3\r")
        buf.write("\3\r\3\r\3\r\3\r\3\r\5\r\u019d\n\r\3\r\3\r\7\r\u01a1\n")
        buf.write("\r\f\r\16\r\u01a4\13\r\3\r\3\r\5\r\u01a8\n\r\3\16\3\16")
        buf.write("\3\16\5\16\u01ad\n\16\3\17\3\17\3\17\3\17\3\17\3\17\3")
        buf.write("\20\3\20\3\20\3\20\3\20\7\20\u01ba\n\20\f\20\16\20\u01bd")
        buf.write("\13\20\3\20\3\20\3\20\5\20\u01c2\n\20\3\21\3\21\3\21\5")
        buf.write("\21\u01c7\n\21\3\22\3\22\3\22\3\22\3\22\3\22\5\22\u01cf")
        buf.write("\n\22\3\22\3\22\3\23\3\23\3\23\3\23\3\23\3\24\3\24\3\24")
        buf.write("\3\24\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25")
        buf.write("\3\25\3\25\7\25\u01e8\n\25\f\25\16\25\u01eb\13\25\3\25")
        buf.write("\3\25\5\25\u01ef\n\25\3\26\3\26\3\26\5\26\u01f4\n\26\3")
        buf.write("\27\7\27\u01f7\n\27\f\27\16\27\u01fa\13\27\3\30\3\30\3")
        buf.write("\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\5\30\u0206\n\30")
        buf.write("\3\31\7\31\u0209\n\31\f\31\16\31\u020c\13\31\3\31\3\31")
        buf.write("\3\32\7\32\u0211\n\32\f\32\16\32\u0214\13\32\3\32\3\32")
        buf.write("\3\33\3\33\5\33\u021a\n\33\3\34\3\34\3\34\3\34\3\34\3")
        buf.write("\35\3\35\3\35\3\35\3\35\3\36\3\36\3\36\3\36\3\36\3\37")
        buf.write("\3\37\5\37\u022d\n\37\3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3")
        buf.write(" \3 \3 \3 \5 \u023d\n \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3")
        buf.write(" \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \7 \u0254\n \f \16 \u0257")
        buf.write("\13 \3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3")
        buf.write("!\3!\3!\3!\3!\3!\3!\5!\u0270\n!\3!\3!\3!\3!\3!\3!\3!\3")
        buf.write("!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\7!\u0287\n!\f")
        buf.write('!\16!\u028a\13!\3"\3"\3"\3"\3"\3"\3"\3"\3"\3')
        buf.write('"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"')
        buf.write('\3"\5"\u02a4\n"\3"\3"\3"\3"\3"\3"\3"\3"\3"')
        buf.write('\7"\u02af\n"\f"\16"\u02b2\13"\3#\3#\3$\3$\3%\3%\3')
        buf.write("&\5&\u02bb\n&\3&\3&\3&\7&\u02c0\n&\f&\16&\u02c3\13&\3")
        buf.write("&\2\5>@B'\2\4\6\b\n\f\16\20\22\24\26\30\32\34\36 \"$")
        buf.write("&(*,.\60\62\64\668:<>@BDFHJ\2\20\3\2\24\25\4\2''\62")
        buf.write("\62\3\2\r\16\3\2\678\4\2\64\6599\3\2\36\37\4\2\33\33\66")
        buf.write('\66\4\2 !=>\3\2"#\4\2\31\31$$\4\2\32\32%%\3\2@B\3\2C')
        buf.write("D\3\2\26\30\2\u031d\2L\3\2\2\2\4R\3\2\2\2\6X\3\2\2\2\b")
        buf.write("z\3\2\2\2\n\u00c2\3\2\2\2\f\u0108\3\2\2\2\16\u0124\3\2")
        buf.write("\2\2\20\u0140\3\2\2\2\22\u0168\3\2\2\2\24\u018c\3\2\2")
        buf.write("\2\26\u018e\3\2\2\2\30\u0196\3\2\2\2\32\u01ac\3\2\2\2")
        buf.write('\34\u01ae\3\2\2\2\36\u01c1\3\2\2\2 \u01c6\3\2\2\2"\u01c8')
        buf.write("\3\2\2\2$\u01d2\3\2\2\2&\u01d7\3\2\2\2(\u01db\3\2\2\2")
        buf.write("*\u01f3\3\2\2\2,\u01f8\3\2\2\2.\u0205\3\2\2\2\60\u020a")
        buf.write("\3\2\2\2\62\u0212\3\2\2\2\64\u0219\3\2\2\2\66\u021b\3")
        buf.write("\2\2\28\u0220\3\2\2\2:\u0225\3\2\2\2<\u022c\3\2\2\2>\u023c")
        buf.write("\3\2\2\2@\u026f\3\2\2\2B\u02a3\3\2\2\2D\u02b3\3\2\2\2")
        buf.write('F\u02b5\3\2\2\2H\u02b7\3\2\2\2J\u02ba\3\2\2\2LM\5B"\2')
        buf.write("MN\7\2\2\3N\3\3\2\2\2OQ\5\6\4\2PO\3\2\2\2QT\3\2\2\2RP")
        buf.write("\3\2\2\2RS\3\2\2\2SU\3\2\2\2TR\3\2\2\2UV\5\b\5\2VW\7\2")
        buf.write("\2\3W\5\3\2\2\2XY\7\4\2\2YZ\t\2\2\2Z[\7F\2\2[\\\7?\2\2")
        buf.write("\\]\5> \2]^\7)\2\2^\7\3\2\2\2_a\7\b\2\2`_\3\2\2\2`a\3")
        buf.write("\2\2\2ab\3\2\2\2bc\7\t\2\2cf\7F\2\2de\7\7\2\2eg\7G\2\2")
        buf.write("fd\3\2\2\2fg\3\2\2\2gh\3\2\2\2h{\7)\2\2ik\7\b\2\2ji\3")
        buf.write("\2\2\2jk\3\2\2\2kl\3\2\2\2lm\7\t\2\2mp\7F\2\2no\7\7\2")
        buf.write("\2oq\7G\2\2pn\3\2\2\2pq\3\2\2\2qr\3\2\2\2rv\7+\2\2su\5")
        buf.write(".\30\2ts\3\2\2\2ux\3\2\2\2vt\3\2\2\2vw\3\2\2\2wy\3\2\2")
        buf.write("\2xv\3\2\2\2y{\7,\2\2z`\3\2\2\2zj\3\2\2\2{\t\3\2\2\2|")
        buf.write("}\7\34\2\2}~\7(\2\2~\u0088\7F\2\2\177\u0089\3\2\2\2\u0080")
        buf.write("\u0081\t\3\2\2\u0081\u0089\5J&\2\u0082\u0083\7\62\2\2")
        buf.write("\u0083\u0084\7\22\2\2\u0084\u0085\7-\2\2\u0085\u0086\5")
        buf.write('B"\2\u0086\u0087\7.\2\2\u0087\u0089\3\2\2\2\u0088\177')
        buf.write("\3\2\2\2\u0088\u0080\3\2\2\2\u0088\u0082\3\2\2\2\u0089")
        buf.write("\u0090\3\2\2\2\u008a\u0091\7)\2\2\u008b\u008c\7\21\2\2")
        buf.write("\u008c\u008d\7+\2\2\u008d\u008e\5,\27\2\u008e\u008f\7")
        buf.write(",\2\2\u008f\u0091\3\2\2\2\u0090\u008a\3\2\2\2\u0090\u008b")
        buf.write("\3\2\2\2\u0091\u00c3\3\2\2\2\u0092\u0093\7F\2\2\u0093")
        buf.write("\u0094\7(\2\2\u0094\u00a0\7F\2\2\u0095\u00a1\3\2\2\2\u0096")
        buf.write("\u0097\7'\2\2\u0097\u00a1\7F\2\2\u0098\u0099\7\62\2\2")
        buf.write("\u0099\u00a1\5J&\2\u009a\u009b\7\62\2\2\u009b\u009c\7")
        buf.write('\22\2\2\u009c\u009d\7-\2\2\u009d\u009e\5B"\2\u009e\u009f')
        buf.write("\7.\2\2\u009f\u00a1\3\2\2\2\u00a0\u0095\3\2\2\2\u00a0")
        buf.write("\u0096\3\2\2\2\u00a0\u0098\3\2\2\2\u00a0\u009a\3\2\2\2")
        buf.write("\u00a1\u00a8\3\2\2\2\u00a2\u00a9\7)\2\2\u00a3\u00a4\7")
        buf.write("\21\2\2\u00a4\u00a5\7+\2\2\u00a5\u00a6\5,\27\2\u00a6\u00a7")
        buf.write("\7,\2\2\u00a7\u00a9\3\2\2\2\u00a8\u00a2\3\2\2\2\u00a8")
        buf.write("\u00a3\3\2\2\2\u00a9\u00c3\3\2\2\2\u00aa\u00ab\7F\2\2")
        buf.write("\u00ab\u00ac\7(\2\2\u00ac\u00b8\7\34\2\2\u00ad\u00b9\3")
        buf.write("\2\2\2\u00ae\u00af\7'\2\2\u00af\u00b9\7F\2\2\u00b0\u00b1")
        buf.write("\7\62\2\2\u00b1\u00b9\5J&\2\u00b2\u00b3\7\62\2\2\u00b3")
        buf.write('\u00b4\7\22\2\2\u00b4\u00b5\7-\2\2\u00b5\u00b6\5B"\2')
        buf.write("\u00b6\u00b7\7.\2\2\u00b7\u00b9\3\2\2\2\u00b8\u00ad\3")
        buf.write("\2\2\2\u00b8\u00ae\3\2\2\2\u00b8\u00b0\3\2\2\2\u00b8\u00b2")
        buf.write("\3\2\2\2\u00b9\u00c0\3\2\2\2\u00ba\u00c1\7)\2\2\u00bb")
        buf.write("\u00bc\7\21\2\2\u00bc\u00bd\7+\2\2\u00bd\u00be\5,\27\2")
        buf.write("\u00be\u00bf\7,\2\2\u00bf\u00c1\3\2\2\2\u00c0\u00ba\3")
        buf.write("\2\2\2\u00c0\u00bb\3\2\2\2\u00c1\u00c3\3\2\2\2\u00c2|")
        buf.write("\3\2\2\2\u00c2\u0092\3\2\2\2\u00c2\u00aa\3\2\2\2\u00c3")
        buf.write("\13\3\2\2\2\u00c4\u00c5\7\66\2\2\u00c5\u00c6\7F\2\2\u00c6")
        buf.write("\u00c7\7(\2\2\u00c7\u00d3\7F\2\2\u00c8\u00d4\3\2\2\2\u00c9")
        buf.write("\u00ca\7'\2\2\u00ca\u00d4\7F\2\2\u00cb\u00cc\7\62\2\2")
        buf.write("\u00cc\u00d4\5J&\2\u00cd\u00ce\7\62\2\2\u00ce\u00cf\7")
        buf.write('\22\2\2\u00cf\u00d0\7-\2\2\u00d0\u00d1\5B"\2\u00d1\u00d2')
        buf.write("\7.\2\2\u00d2\u00d4\3\2\2\2\u00d3\u00c8\3\2\2\2\u00d3")
        buf.write("\u00c9\3\2\2\2\u00d3\u00cb\3\2\2\2\u00d3\u00cd\3\2\2\2")
        buf.write("\u00d4\u00d5\3\2\2\2\u00d5\u0109\7)\2\2\u00d6\u00d7\7")
        buf.write("\66\2\2\u00d7\u00d8\7F\2\2\u00d8\u00d9\7(\2\2\u00d9\u00e5")
        buf.write("\7\34\2\2\u00da\u00e6\3\2\2\2\u00db\u00dc\7'\2\2\u00dc")
        buf.write("\u00e6\7F\2\2\u00dd\u00de\7\62\2\2\u00de\u00e6\5J&\2\u00df")
        buf.write("\u00e0\7\62\2\2\u00e0\u00e1\7\22\2\2\u00e1\u00e2\7-\2")
        buf.write('\2\u00e2\u00e3\5B"\2\u00e3\u00e4\7.\2\2\u00e4\u00e6\3')
        buf.write("\2\2\2\u00e5\u00da\3\2\2\2\u00e5\u00db\3\2\2\2\u00e5\u00dd")
        buf.write("\3\2\2\2\u00e5\u00df\3\2\2\2\u00e6\u00e7\3\2\2\2\u00e7")
        buf.write("\u0109\7)\2\2\u00e8\u00e9\7\66\2\2\u00e9\u00ea\7\65\2")
        buf.write("\2\u00ea\u00eb\7(\2\2\u00eb\u00f5\7F\2\2\u00ec\u00f6\3")
        buf.write("\2\2\2\u00ed\u00ee\t\3\2\2\u00ee\u00f6\5J&\2\u00ef\u00f0")
        buf.write("\7\62\2\2\u00f0\u00f1\7\22\2\2\u00f1\u00f2\7-\2\2\u00f2")
        buf.write('\u00f3\5B"\2\u00f3\u00f4\7.\2\2\u00f4\u00f6\3\2\2\2\u00f5')
        buf.write("\u00ec\3\2\2\2\u00f5\u00ed\3\2\2\2\u00f5\u00ef\3\2\2\2")
        buf.write("\u00f6\u00f7\3\2\2\2\u00f7\u0109\7)\2\2\u00f8\u00f9\7")
        buf.write("\66\2\2\u00f9\u00fa\7\65\2\2\u00fa\u00fb\7(\2\2\u00fb")
        buf.write("\u0105\7\34\2\2\u00fc\u0106\3\2\2\2\u00fd\u00fe\t\3\2")
        buf.write("\2\u00fe\u0106\5J&\2\u00ff\u0100\7\62\2\2\u0100\u0101")
        buf.write('\7\22\2\2\u0101\u0102\7-\2\2\u0102\u0103\5B"\2\u0103')
        buf.write("\u0104\7.\2\2\u0104\u0106\3\2\2\2\u0105\u00fc\3\2\2\2")
        buf.write("\u0105\u00fd\3\2\2\2\u0105\u00ff\3\2\2\2\u0106\u0107\3")
        buf.write("\2\2\2\u0107\u0109\7)\2\2\u0108\u00c4\3\2\2\2\u0108\u00d6")
        buf.write("\3\2\2\2\u0108\u00e8\3\2\2\2\u0108\u00f8\3\2\2\2\u0109")
        buf.write("\r\3\2\2\2\u010a\u010c\7\n\2\2\u010b\u010d\7F\2\2\u010c")
        buf.write("\u010b\3\2\2\2\u010c\u010d\3\2\2\2\u010d\u010e\3\2\2\2")
        buf.write("\u010e\u010f\7+\2\2\u010f\u0110\5,\27\2\u0110\u0111\7")
        buf.write(",\2\2\u0111\u0125\3\2\2\2\u0112\u0113\7\n\2\2\u0113\u0114")
        buf.write("\7\17\2\2\u0114\u0115\7F\2\2\u0115\u0125\7)\2\2\u0116")
        buf.write("\u0117\7\n\2\2\u0117\u0119\7\17\2\2\u0118\u011a\7F\2\2")
        buf.write("\u0119\u0118\3\2\2\2\u0119\u011a\3\2\2\2\u011a\u011b\3")
        buf.write("\2\2\2\u011b\u0125\7H\2\2\u011c\u011e\7\n\2\2\u011d\u011f")
        buf.write("\7F\2\2\u011e\u011d\3\2\2\2\u011e\u011f\3\2\2\2\u011f")
        buf.write("\u0120\3\2\2\2\u0120\u0121\7\20\2\2\u0121\u0122\5J&\2")
        buf.write("\u0122\u0123\7)\2\2\u0123\u0125\3\2\2\2\u0124\u010a\3")
        buf.write("\2\2\2\u0124\u0112\3\2\2\2\u0124\u0116\3\2\2\2\u0124\u011c")
        buf.write("\3\2\2\2\u0125\17\3\2\2\2\u0126\u0128\7\13\2\2\u0127\u0129")
        buf.write("\7F\2\2\u0128\u0127\3\2\2\2\u0128\u0129\3\2\2\2\u0129")
        buf.write("\u012a\3\2\2\2\u012a\u012b\7+\2\2\u012b\u012c\5,\27\2")
        buf.write("\u012c\u012d\7,\2\2\u012d\u0141\3\2\2\2\u012e\u012f\7")
        buf.write("\13\2\2\u012f\u0130\7\17\2\2\u0130\u0131\7F\2\2\u0131")
        buf.write("\u0141\7)\2\2\u0132\u0133\7\13\2\2\u0133\u0135\7\17\2")
        buf.write("\2\u0134\u0136\7F\2\2\u0135\u0134\3\2\2\2\u0135\u0136")
        buf.write("\3\2\2\2\u0136\u0137\3\2\2\2\u0137\u0141\7H\2\2\u0138")
        buf.write("\u013a\7\13\2\2\u0139\u013b\7F\2\2\u013a\u0139\3\2\2\2")
        buf.write("\u013a\u013b\3\2\2\2\u013b\u013c\3\2\2\2\u013c\u013d\7")
        buf.write("\20\2\2\u013d\u013e\5J&\2\u013e\u013f\7)\2\2\u013f\u0141")
        buf.write("\3\2\2\2\u0140\u0126\3\2\2\2\u0140\u012e\3\2\2\2\u0140")
        buf.write("\u0132\3\2\2\2\u0140\u0138\3\2\2\2\u0141\21\3\2\2\2\u0142")
        buf.write("\u0144\7\f\2\2\u0143\u0145\t\4\2\2\u0144\u0143\3\2\2\2")
        buf.write("\u0144\u0145\3\2\2\2\u0145\u0147\3\2\2\2\u0146\u0148\7")
        buf.write("F\2\2\u0147\u0146\3\2\2\2\u0147\u0148\3\2\2\2\u0148\u0149")
        buf.write("\3\2\2\2\u0149\u014a\7+\2\2\u014a\u014b\5,\27\2\u014b")
        buf.write("\u014c\7,\2\2\u014c\u0169\3\2\2\2\u014d\u014f\7\f\2\2")
        buf.write("\u014e\u0150\t\4\2\2\u014f\u014e\3\2\2\2\u014f\u0150\3")
        buf.write("\2\2\2\u0150\u0151\3\2\2\2\u0151\u0152\7\17\2\2\u0152")
        buf.write("\u0153\7F\2\2\u0153\u0169\7)\2\2\u0154\u0156\7\f\2\2\u0155")
        buf.write("\u0157\t\4\2\2\u0156\u0155\3\2\2\2\u0156\u0157\3\2\2\2")
        buf.write("\u0157\u0158\3\2\2\2\u0158\u015a\7\17\2\2\u0159\u015b")
        buf.write("\7F\2\2\u015a\u0159\3\2\2\2\u015a\u015b\3\2\2\2\u015b")
        buf.write("\u015c\3\2\2\2\u015c\u0169\7H\2\2\u015d\u015f\7\f\2\2")
        buf.write("\u015e\u0160\t\4\2\2\u015f\u015e\3\2\2\2\u015f\u0160\3")
        buf.write("\2\2\2\u0160\u0162\3\2\2\2\u0161\u0163\7F\2\2\u0162\u0161")
        buf.write("\3\2\2\2\u0162\u0163\3\2\2\2\u0163\u0164\3\2\2\2\u0164")
        buf.write("\u0165\7\20\2\2\u0165\u0166\5J&\2\u0166\u0167\7)\2\2\u0167")
        buf.write("\u0169\3\2\2\2\u0168\u0142\3\2\2\2\u0168\u014d\3\2\2\2")
        buf.write("\u0168\u0154\3\2\2\2\u0168\u015d\3\2\2\2\u0169\23\3\2")
        buf.write("\2\2\u016a\u016b\7\36\2\2\u016b\u016c\7\f\2\2\u016c\u016e")
        buf.write("\t\4\2\2\u016d\u016f\7F\2\2\u016e\u016d\3\2\2\2\u016e")
        buf.write("\u016f\3\2\2\2\u016f\u0170\3\2\2\2\u0170\u0171\7+\2\2")
        buf.write("\u0171\u0172\5,\27\2\u0172\u0173\7,\2\2\u0173\u018d\3")
        buf.write("\2\2\2\u0174\u0175\7\36\2\2\u0175\u0176\7\f\2\2\u0176")
        buf.write("\u0177\t\4\2\2\u0177\u0178\7\17\2\2\u0178\u0179\7F\2\2")
        buf.write("\u0179\u018d\7)\2\2\u017a\u017b\7\36\2\2\u017b\u017c\7")
        buf.write("\f\2\2\u017c\u017d\t\4\2\2\u017d\u017f\7\17\2\2\u017e")
        buf.write("\u0180\7F\2\2\u017f\u017e\3\2\2\2\u017f\u0180\3\2\2\2")
        buf.write("\u0180\u0181\3\2\2\2\u0181\u018d\7H\2\2\u0182\u0183\7")
        buf.write("\36\2\2\u0183\u0184\7\f\2\2\u0184\u0186\t\4\2\2\u0185")
        buf.write("\u0187\7F\2\2\u0186\u0185\3\2\2\2\u0186\u0187\3\2\2\2")
        buf.write("\u0187\u0188\3\2\2\2\u0188\u0189\7\20\2\2\u0189\u018a")
        buf.write("\5J&\2\u018a\u018b\7)\2\2\u018b\u018d\3\2\2\2\u018c\u016a")
        buf.write("\3\2\2\2\u018c\u0174\3\2\2\2\u018c\u017a\3\2\2\2\u018c")
        buf.write("\u0182\3\2\2\2\u018d\25\3\2\2\2\u018e\u018f\7\5\2\2\u018f")
        buf.write("\u0192\7F\2\2\u0190\u0191\7\7\2\2\u0191\u0193\7G\2\2\u0192")
        buf.write("\u0190\3\2\2\2\u0192\u0193\3\2\2\2\u0193\u0194\3\2\2\2")
        buf.write("\u0194\u0195\7)\2\2\u0195\27\3\2\2\2\u0196\u0197\7\3\2")
        buf.write("\2\u0197\u0198\7G\2\2\u0198\u0199\7\6\2\2\u0199\u019c")
        buf.write("\7F\2\2\u019a\u019b\7\7\2\2\u019b\u019d\7G\2\2\u019c\u019a")
        buf.write("\3\2\2\2\u019c\u019d\3\2\2\2\u019d\u01a7\3\2\2\2\u019e")
        buf.write("\u01a2\7+\2\2\u019f\u01a1\5\32\16\2\u01a0\u019f\3\2\2")
        buf.write("\2\u01a1\u01a4\3\2\2\2\u01a2\u01a0\3\2\2\2\u01a2\u01a3")
        buf.write("\3\2\2\2\u01a3\u01a5\3\2\2\2\u01a4\u01a2\3\2\2\2\u01a5")
        buf.write("\u01a8\7,\2\2\u01a6\u01a8\7)\2\2\u01a7\u019e\3\2\2\2\u01a7")
        buf.write("\u01a6\3\2\2\2\u01a8\31\3\2\2\2\u01a9\u01ad\5\34\17\2")
        buf.write('\u01aa\u01ad\5"\22\2\u01ab\u01ad\7)\2\2\u01ac\u01a9\3')
        buf.write("\2\2\2\u01ac\u01aa\3\2\2\2\u01ac\u01ab\3\2\2\2\u01ad\33")
        buf.write("\3\2\2\2\u01ae\u01af\7\4\2\2\u01af\u01b0\5\36\20\2\u01b0")
        buf.write("\u01b1\7(\2\2\u01b1\u01b2\5 \21\2\u01b2\u01b3\7)\2\2\u01b3")
        buf.write("\35\3\2\2\2\u01b4\u01c2\7\65\2\2\u01b5\u01b6\7+\2\2\u01b6")
        buf.write("\u01bb\7F\2\2\u01b7\u01b8\7*\2\2\u01b8\u01ba\7F\2\2\u01b9")
        buf.write("\u01b7\3\2\2\2\u01ba\u01bd\3\2\2\2\u01bb\u01b9\3\2\2\2")
        buf.write("\u01bb\u01bc\3\2\2\2\u01bc\u01be\3\2\2\2\u01bd\u01bb\3")
        buf.write("\2\2\2\u01be\u01c2\7,\2\2\u01bf\u01c2\7X\2\2\u01c0\u01c2")
        buf.write("\7F\2\2\u01c1\u01b4\3\2\2\2\u01c1\u01b5\3\2\2\2\u01c1")
        buf.write("\u01bf\3\2\2\2\u01c1\u01c0\3\2\2\2\u01c2\37\3\2\2\2\u01c3")
        buf.write("\u01c7\7F\2\2\u01c4\u01c7\7]\2\2\u01c5\u01c7\7\65\2\2")
        buf.write("\u01c6\u01c3\3\2\2\2\u01c6\u01c4\3\2\2\2\u01c6\u01c5\3")
        buf.write("\2\2\2\u01c7!\3\2\2\2\u01c8\u01c9\7\5\2\2\u01c9\u01ca")
        buf.write("\5J&\2\u01ca\u01cb\7(\2\2\u01cb\u01ce\5J&\2\u01cc\u01cd")
        buf.write("\7\7\2\2\u01cd\u01cf\7G\2\2\u01ce\u01cc\3\2\2\2\u01ce")
        buf.write("\u01cf\3\2\2\2\u01cf\u01d0\3\2\2\2\u01d0\u01d1\7)\2\2")
        buf.write("\u01d1#\3\2\2\2\u01d2\u01d3\7F\2\2\u01d3\u01d4\7?\2\2")
        buf.write("\u01d4\u01d5\5@!\2\u01d5\u01d6\7)\2\2\u01d6%\3\2\2\2\u01d7")
        buf.write("\u01d8\7+\2\2\u01d8\u01d9\5,\27\2\u01d9\u01da\7,\2\2\u01da")
        buf.write("'\3\2\2\2\u01db\u01dc\7\22\2\2\u01dc\u01dd\7-\2\2\u01dd")
        buf.write('\u01de\5B"\2\u01de\u01df\7.\2\2\u01df\u01e9\5&\24\2\u01e0')
        buf.write("\u01e1\7\23\2\2\u01e1\u01e2\7\22\2\2\u01e2\u01e3\7-\2")
        buf.write('\2\u01e3\u01e4\5B"\2\u01e4\u01e5\7.\2\2\u01e5\u01e6\5')
        buf.write("&\24\2\u01e6\u01e8\3\2\2\2\u01e7\u01e0\3\2\2\2\u01e8\u01eb")
        buf.write("\3\2\2\2\u01e9\u01e7\3\2\2\2\u01e9\u01ea\3\2\2\2\u01ea")
        buf.write("\u01ee\3\2\2\2\u01eb\u01e9\3\2\2\2\u01ec\u01ed\7\23\2")
        buf.write("\2\u01ed\u01ef\5&\24\2\u01ee\u01ec\3\2\2\2\u01ee\u01ef")
        buf.write("\3\2\2\2\u01ef)\3\2\2\2\u01f0\u01f4\5$\23\2\u01f1\u01f4")
        buf.write("\5(\25\2\u01f2\u01f4\7)\2\2\u01f3\u01f0\3\2\2\2\u01f3")
        buf.write("\u01f1\3\2\2\2\u01f3\u01f2\3\2\2\2\u01f4+\3\2\2\2\u01f5")
        buf.write("\u01f7\5*\26\2\u01f6\u01f5\3\2\2\2\u01f7\u01fa\3\2\2\2")
        buf.write("\u01f8\u01f6\3\2\2\2\u01f8\u01f9\3\2\2\2\u01f9-\3\2\2")
        buf.write("\2\u01fa\u01f8\3\2\2\2\u01fb\u0206\5\b\5\2\u01fc\u0206")
        buf.write("\5\n\6\2\u01fd\u0206\5\f\7\2\u01fe\u0206\5\16\b\2\u01ff")
        buf.write("\u0206\5\22\n\2\u0200\u0206\5\20\t\2\u0201\u0206\5\24")
        buf.write("\13\2\u0202\u0206\5\26\f\2\u0203\u0206\5\30\r\2\u0204")
        buf.write("\u0206\7)\2\2\u0205\u01fb\3\2\2\2\u0205\u01fc\3\2\2\2")
        buf.write("\u0205\u01fd\3\2\2\2\u0205\u01fe\3\2\2\2\u0205\u01ff\3")
        buf.write("\2\2\2\u0205\u0200\3\2\2\2\u0205\u0201\3\2\2\2\u0205\u0202")
        buf.write("\3\2\2\2\u0205\u0203\3\2\2\2\u0205\u0204\3\2\2\2\u0206")
        buf.write("/\3\2\2\2\u0207\u0209\5:\36\2\u0208\u0207\3\2\2\2\u0209")
        buf.write("\u020c\3\2\2\2\u020a\u0208\3\2\2\2\u020a\u020b\3\2\2\2")
        buf.write("\u020b\u020d\3\2\2\2\u020c\u020a\3\2\2\2\u020d\u020e\7")
        buf.write("\2\2\3\u020e\61\3\2\2\2\u020f\u0211\5\64\33\2\u0210\u020f")
        buf.write("\3\2\2\2\u0211\u0214\3\2\2\2\u0212\u0210\3\2\2\2\u0212")
        buf.write("\u0213\3\2\2\2\u0213\u0215\3\2\2\2\u0214\u0212\3\2\2\2")
        buf.write("\u0215\u0216\7\2\2\3\u0216\63\3\2\2\2\u0217\u021a\5\66")
        buf.write("\34\2\u0218\u021a\58\35\2\u0219\u0217\3\2\2\2\u0219\u0218")
        buf.write("\3\2\2\2\u021a\65\3\2\2\2\u021b\u021c\7F\2\2\u021c\u021d")
        buf.write("\7&\2\2\u021d\u021e\5> \2\u021e\u021f\7)\2\2\u021f\67")
        buf.write("\3\2\2\2\u0220\u0221\7F\2\2\u0221\u0222\7?\2\2\u0222\u0223")
        buf.write("\5> \2\u0223\u0224\7)\2\2\u02249\3\2\2\2\u0225\u0226\7")
        buf.write("F\2\2\u0226\u0227\7&\2\2\u0227\u0228\5@!\2\u0228\u0229")
        buf.write("\7)\2\2\u0229;\3\2\2\2\u022a\u022d\5@!\2\u022b\u022d\5")
        buf.write('B"\2\u022c\u022a\3\2\2\2\u022c\u022b\3\2\2\2\u022d=\3')
        buf.write("\2\2\2\u022e\u022f\b \1\2\u022f\u0230\7/\2\2\u0230\u0231")
        buf.write("\5> \2\u0231\u0232\7\60\2\2\u0232\u023d\3\2\2\2\u0233")
        buf.write("\u023d\5D#\2\u0234\u023d\5H%\2\u0235\u0236\t\5\2\2\u0236")
        buf.write("\u023d\5> \13\u0237\u0238\7E\2\2\u0238\u0239\7/\2\2\u0239")
        buf.write("\u023a\5> \2\u023a\u023b\7\60\2\2\u023b\u023d\3\2\2\2")
        buf.write("\u023c\u022e\3\2\2\2\u023c\u0233\3\2\2\2\u023c\u0234\3")
        buf.write("\2\2\2\u023c\u0235\3\2\2\2\u023c\u0237\3\2\2\2\u023d\u0255")
        buf.write("\3\2\2\2\u023e\u023f\f\n\2\2\u023f\u0240\7\35\2\2\u0240")
        buf.write("\u0254\5> \n\u0241\u0242\f\t\2\2\u0242\u0243\t\6\2\2\u0243")
        buf.write("\u0254\5> \n\u0244\u0245\f\b\2\2\u0245\u0246\t\5\2\2\u0246")
        buf.write("\u0254\5> \t\u0247\u0248\f\7\2\2\u0248\u0249\t\7\2\2\u0249")
        buf.write("\u0254\5> \b\u024a\u024b\f\6\2\2\u024b\u024c\7:\2\2\u024c")
        buf.write("\u0254\5> \7\u024d\u024e\f\5\2\2\u024e\u024f\7;\2\2\u024f")
        buf.write("\u0254\5> \6\u0250\u0251\f\4\2\2\u0251\u0252\7<\2\2\u0252")
        buf.write("\u0254\5> \5\u0253\u023e\3\2\2\2\u0253\u0241\3\2\2\2\u0253")
        buf.write("\u0244\3\2\2\2\u0253\u0247\3\2\2\2\u0253\u024a\3\2\2\2")
        buf.write("\u0253\u024d\3\2\2\2\u0253\u0250\3\2\2\2\u0254\u0257\3")
        buf.write("\2\2\2\u0255\u0253\3\2\2\2\u0255\u0256\3\2\2\2\u0256?")
        buf.write("\3\2\2\2\u0257\u0255\3\2\2\2\u0258\u0259\b!\1\2\u0259")
        buf.write("\u025a\7/\2\2\u025a\u025b\5@!\2\u025b\u025c\7\60\2\2\u025c")
        buf.write("\u0270\3\2\2\2\u025d\u0270\5D#\2\u025e\u0270\7F\2\2\u025f")
        buf.write("\u0270\5H%\2\u0260\u0261\t\5\2\2\u0261\u0270\5@!\f\u0262")
        buf.write("\u0263\7E\2\2\u0263\u0264\7/\2\2\u0264\u0265\5@!\2\u0265")
        buf.write("\u0266\7\60\2\2\u0266\u0270\3\2\2\2\u0267\u0268\7/\2\2")
        buf.write('\u0268\u0269\5B"\2\u0269\u026a\7\60\2\2\u026a\u026b\7')
        buf.write("\61\2\2\u026b\u026c\5@!\2\u026c\u026d\7\62\2\2\u026d\u026e")
        buf.write("\5@!\3\u026e\u0270\3\2\2\2\u026f\u0258\3\2\2\2\u026f\u025d")
        buf.write("\3\2\2\2\u026f\u025e\3\2\2\2\u026f\u025f\3\2\2\2\u026f")
        buf.write("\u0260\3\2\2\2\u026f\u0262\3\2\2\2\u026f\u0267\3\2\2\2")
        buf.write("\u0270\u0288\3\2\2\2\u0271\u0272\f\13\2\2\u0272\u0273")
        buf.write("\7\35\2\2\u0273\u0287\5@!\13\u0274\u0275\f\n\2\2\u0275")
        buf.write("\u0276\t\6\2\2\u0276\u0287\5@!\13\u0277\u0278\f\t\2\2")
        buf.write("\u0278\u0279\t\5\2\2\u0279\u0287\5@!\n\u027a\u027b\f\b")
        buf.write("\2\2\u027b\u027c\t\7\2\2\u027c\u0287\5@!\t\u027d\u027e")
        buf.write("\f\7\2\2\u027e\u027f\7:\2\2\u027f\u0287\5@!\b\u0280\u0281")
        buf.write("\f\6\2\2\u0281\u0282\7;\2\2\u0282\u0287\5@!\7\u0283\u0284")
        buf.write("\f\5\2\2\u0284\u0285\7<\2\2\u0285\u0287\5@!\6\u0286\u0271")
        buf.write("\3\2\2\2\u0286\u0274\3\2\2\2\u0286\u0277\3\2\2\2\u0286")
        buf.write("\u027a\3\2\2\2\u0286\u027d\3\2\2\2\u0286\u0280\3\2\2\2")
        buf.write("\u0286\u0283\3\2\2\2\u0287\u028a\3\2\2\2\u0288\u0286\3")
        buf.write("\2\2\2\u0288\u0289\3\2\2\2\u0289A\3\2\2\2\u028a\u0288")
        buf.write('\3\2\2\2\u028b\u028c\b"\1\2\u028c\u028d\7/\2\2\u028d')
        buf.write('\u028e\5B"\2\u028e\u028f\7\60\2\2\u028f\u02a4\3\2\2\2')
        buf.write("\u0290\u02a4\5F$\2\u0291\u0292\t\b\2\2\u0292\u02a4\5B")
        buf.write('"\t\u0293\u0294\5@!\2\u0294\u0295\t\t\2\2\u0295\u0296')
        buf.write("\5@!\2\u0296\u02a4\3\2\2\2\u0297\u0298\5@!\2\u0298\u0299")
        buf.write("\t\n\2\2\u0299\u029a\5@!\2\u029a\u02a4\3\2\2\2\u029b\u029c")
        buf.write('\7/\2\2\u029c\u029d\5B"\2\u029d\u029e\7\60\2\2\u029e')
        buf.write('\u029f\7\61\2\2\u029f\u02a0\5B"\2\u02a0\u02a1\7\62\2')
        buf.write('\2\u02a1\u02a2\5B"\3\u02a2\u02a4\3\2\2\2\u02a3\u028b')
        buf.write("\3\2\2\2\u02a3\u0290\3\2\2\2\u02a3\u0291\3\2\2\2\u02a3")
        buf.write("\u0293\3\2\2\2\u02a3\u0297\3\2\2\2\u02a3\u029b\3\2\2\2")
        buf.write("\u02a4\u02b0\3\2\2\2\u02a5\u02a6\f\6\2\2\u02a6\u02a7\t")
        buf.write('\n\2\2\u02a7\u02af\5B"\7\u02a8\u02a9\f\5\2\2\u02a9\u02aa')
        buf.write('\t\13\2\2\u02aa\u02af\5B"\6\u02ab\u02ac\f\4\2\2\u02ac')
        buf.write('\u02ad\t\f\2\2\u02ad\u02af\5B"\5\u02ae\u02a5\3\2\2\2')
        buf.write("\u02ae\u02a8\3\2\2\2\u02ae\u02ab\3\2\2\2\u02af\u02b2\3")
        buf.write("\2\2\2\u02b0\u02ae\3\2\2\2\u02b0\u02b1\3\2\2\2\u02b1C")
        buf.write("\3\2\2\2\u02b2\u02b0\3\2\2\2\u02b3\u02b4\t\r\2\2\u02b4")
        buf.write("E\3\2\2\2\u02b5\u02b6\t\16\2\2\u02b6G\3\2\2\2\u02b7\u02b8")
        buf.write("\t\17\2\2\u02b8I\3\2\2\2\u02b9\u02bb\7\64\2\2\u02ba\u02b9")
        buf.write("\3\2\2\2\u02ba\u02bb\3\2\2\2\u02bb\u02bc\3\2\2\2\u02bc")
        buf.write("\u02c1\7F\2\2\u02bd\u02be\7\63\2\2\u02be\u02c0\7F\2\2")
        buf.write("\u02bf\u02bd\3\2\2\2\u02c0\u02c3\3\2\2\2\u02c1\u02bf\3")
        buf.write("\2\2\2\u02c1\u02c2\3\2\2\2\u02c2K\3\2\2\2\u02c3\u02c1")
        buf.write("\3\2\2\2FR`fjpvz\u0088\u0090\u00a0\u00a8\u00b8\u00c0\u00c2")
        buf.write("\u00d3\u00e5\u00f5\u0105\u0108\u010c\u0119\u011e\u0124")
        buf.write("\u0128\u0135\u013a\u0140\u0144\u0147\u014f\u0156\u015a")
        buf.write("\u015f\u0162\u0168\u016e\u017f\u0186\u018c\u0192\u019c")
        buf.write("\u01a2\u01a7\u01ac\u01bb\u01c1\u01c6\u01ce\u01e9\u01ee")
        buf.write("\u01f3\u01f8\u0205\u020a\u0212\u0219\u022c\u023c\u0253")
        buf.write("\u0255\u026f\u0286\u0288\u02a3\u02ae\u02b0\u02ba\u02c1")
        return buf.getvalue()


class Grammar(Parser):
    grammarFileName = "Grammar.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [DFA(ds, i) for i, ds in enumerate(atn.decisionToState)]

    sharedContextCache = PredictionContextCache()

    literalNames = [
        "<INVALID>",
        "'import'",
        "'def'",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "'pseudo'",
        "'state'",
        "'enter'",
        "'exit'",
        "'during'",
        "'before'",
        "'after'",
        "'abstract'",
        "'ref'",
        "'effect'",
        "'if'",
        "'else'",
        "'int'",
        "'float'",
        "'pi'",
        "'E'",
        "'tau'",
        "'and'",
        "'or'",
        "'not'",
        "'[*]'",
        "'**'",
        "'>>'",
        "'<<'",
        "'<='",
        "'>='",
        "'=='",
        "'!='",
        "'&&'",
        "'||'",
        "':='",
        "'::'",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "'['",
        "']'",
        "'('",
        "')'",
        "'?'",
        "':'",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "'!'",
        "'+'",
        "'-'",
        "'%'",
        "'&'",
        "'^'",
        "'|'",
        "'<'",
        "'>'",
        "'='",
    ]

    symbolicNames = [
        "<INVALID>",
        "IMPORT",
        "DEF",
        "EVENT",
        "AS",
        "NAMED",
        "PSEUDO",
        "STATE",
        "ENTER",
        "EXIT",
        "DURING",
        "BEFORE",
        "AFTER",
        "ABSTRACT",
        "REF",
        "EFFECT",
        "IF",
        "ELSE",
        "INT_TYPE",
        "FLOAT_TYPE",
        "PI_CONST",
        "E_CONST",
        "TAU_CONST",
        "AND_KW",
        "OR_KW",
        "NOT_KW",
        "INIT_MARKER",
        "POW",
        "SHIFT_RIGHT",
        "SHIFT_LEFT",
        "LE",
        "GE",
        "EQ",
        "NE",
        "LOGICAL_AND",
        "LOGICAL_OR",
        "DECLARE_ASSIGN",
        "COLONCOLON",
        "ARROW",
        "SEMI",
        "COMMA",
        "LBRACE",
        "RBRACE",
        "LBRACK",
        "RBRACK",
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
        "ASSIGN",
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
        "IMPORT_HEADER_WS",
        "IMPORT_HEADER_MULTILINE_COMMENT",
        "IMPORT_HEADER_LINE_COMMENT",
        "IMPORT_HEADER_PYTHON_COMMENT",
        "IMPORT_BLOCK_WS",
        "IMPORT_BLOCK_MULTILINE_COMMENT",
        "IMPORT_BLOCK_LINE_COMMENT",
        "IMPORT_BLOCK_PYTHON_COMMENT",
        "IMPORT_DEF_SELECTOR_WS",
        "IMPORT_DEF_SELECTOR_MULTILINE_COMMENT",
        "IMPORT_DEF_SELECTOR_LINE_COMMENT",
        "IMPORT_DEF_SELECTOR_PYTHON_COMMENT",
        "IMPORT_DEF_SELECTOR_PATTERN",
        "IMPORT_DEF_TARGET_WS",
        "IMPORT_DEF_TARGET_MULTILINE_COMMENT",
        "IMPORT_DEF_TARGET_LINE_COMMENT",
        "IMPORT_DEF_TARGET_PYTHON_COMMENT",
        "IMPORT_DEF_TARGET_TEMPLATE",
    ]

    RULE_condition = 0
    RULE_state_machine_dsl = 1
    RULE_def_assignment = 2
    RULE_state_definition = 3
    RULE_transition_definition = 4
    RULE_transition_force_definition = 5
    RULE_enter_definition = 6
    RULE_exit_definition = 7
    RULE_during_definition = 8
    RULE_during_aspect_definition = 9
    RULE_event_definition = 10
    RULE_import_statement = 11
    RULE_import_mapping_statement = 12
    RULE_import_def_mapping = 13
    RULE_import_def_selector = 14
    RULE_import_def_target_template = 15
    RULE_import_event_mapping = 16
    RULE_operation_assignment = 17
    RULE_operation_block = 18
    RULE_if_statement = 19
    RULE_operational_statement = 20
    RULE_operational_statement_set = 21
    RULE_state_inner_statement = 22
    RULE_operation_program = 23
    RULE_preamble_program = 24
    RULE_preamble_statement = 25
    RULE_initial_assignment = 26
    RULE_constant_definition = 27
    RULE_operational_assignment = 28
    RULE_generic_expression = 29
    RULE_init_expression = 30
    RULE_num_expression = 31
    RULE_cond_expression = 32
    RULE_num_literal = 33
    RULE_bool_literal = 34
    RULE_math_const = 35
    RULE_chain_id = 36

    ruleNames = [
        "condition",
        "state_machine_dsl",
        "def_assignment",
        "state_definition",
        "transition_definition",
        "transition_force_definition",
        "enter_definition",
        "exit_definition",
        "during_definition",
        "during_aspect_definition",
        "event_definition",
        "import_statement",
        "import_mapping_statement",
        "import_def_mapping",
        "import_def_selector",
        "import_def_target_template",
        "import_event_mapping",
        "operation_assignment",
        "operation_block",
        "if_statement",
        "operational_statement",
        "operational_statement_set",
        "state_inner_statement",
        "operation_program",
        "preamble_program",
        "preamble_statement",
        "initial_assignment",
        "constant_definition",
        "operational_assignment",
        "generic_expression",
        "init_expression",
        "num_expression",
        "cond_expression",
        "num_literal",
        "bool_literal",
        "math_const",
        "chain_id",
    ]

    EOF = Token.EOF
    IMPORT = 1
    DEF = 2
    EVENT = 3
    AS = 4
    NAMED = 5
    PSEUDO = 6
    STATE = 7
    ENTER = 8
    EXIT = 9
    DURING = 10
    BEFORE = 11
    AFTER = 12
    ABSTRACT = 13
    REF = 14
    EFFECT = 15
    IF = 16
    ELSE = 17
    INT_TYPE = 18
    FLOAT_TYPE = 19
    PI_CONST = 20
    E_CONST = 21
    TAU_CONST = 22
    AND_KW = 23
    OR_KW = 24
    NOT_KW = 25
    INIT_MARKER = 26
    POW = 27
    SHIFT_RIGHT = 28
    SHIFT_LEFT = 29
    LE = 30
    GE = 31
    EQ = 32
    NE = 33
    LOGICAL_AND = 34
    LOGICAL_OR = 35
    DECLARE_ASSIGN = 36
    COLONCOLON = 37
    ARROW = 38
    SEMI = 39
    COMMA = 40
    LBRACE = 41
    RBRACE = 42
    LBRACK = 43
    RBRACK = 44
    LPAREN = 45
    RPAREN = 46
    QUESTION = 47
    COLON = 48
    DOT = 49
    SLASH = 50
    STAR = 51
    BANG = 52
    PLUS = 53
    MINUS = 54
    PERCENT = 55
    AMP = 56
    CARET = 57
    PIPE = 58
    LT = 59
    GT = 60
    ASSIGN = 61
    FLOAT = 62
    HEX_INT = 63
    INT = 64
    TRUE = 65
    FALSE = 66
    UFUNC_NAME = 67
    ID = 68
    STRING = 69
    MULTILINE_COMMENT = 70
    LINE_COMMENT = 71
    PYTHON_COMMENT = 72
    WS = 73
    IMPORT_HEADER_WS = 74
    IMPORT_HEADER_MULTILINE_COMMENT = 75
    IMPORT_HEADER_LINE_COMMENT = 76
    IMPORT_HEADER_PYTHON_COMMENT = 77
    IMPORT_BLOCK_WS = 78
    IMPORT_BLOCK_MULTILINE_COMMENT = 79
    IMPORT_BLOCK_LINE_COMMENT = 80
    IMPORT_BLOCK_PYTHON_COMMENT = 81
    IMPORT_DEF_SELECTOR_WS = 82
    IMPORT_DEF_SELECTOR_MULTILINE_COMMENT = 83
    IMPORT_DEF_SELECTOR_LINE_COMMENT = 84
    IMPORT_DEF_SELECTOR_PYTHON_COMMENT = 85
    IMPORT_DEF_SELECTOR_PATTERN = 86
    IMPORT_DEF_TARGET_WS = 87
    IMPORT_DEF_TARGET_MULTILINE_COMMENT = 88
    IMPORT_DEF_TARGET_LINE_COMMENT = 89
    IMPORT_DEF_TARGET_PYTHON_COMMENT = 90
    IMPORT_DEF_TARGET_TEMPLATE = 91

    def __init__(self, input: TokenStream, output: TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.9.3")
        self._interp = ParserATNSimulator(
            self, self.atn, self.decisionsToDFA, self.sharedContextCache
        )
        self._predicates = None

    class ConditionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def cond_expression(self):
            return self.getTypedRuleContext(Grammar.Cond_expressionContext, 0)

        def EOF(self):
            return self.getToken(Grammar.EOF, 0)

        def getRuleIndex(self):
            return Grammar.RULE_condition

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCondition"):
                listener.enterCondition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCondition"):
                listener.exitCondition(self)

    def condition(self):

        localctx = Grammar.ConditionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_condition)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 74
            self.cond_expression(0)
            self.state = 75
            self.match(Grammar.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class State_machine_dslContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def state_definition(self):
            return self.getTypedRuleContext(Grammar.State_definitionContext, 0)

        def EOF(self):
            return self.getToken(Grammar.EOF, 0)

        def def_assignment(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Def_assignmentContext)
            else:
                return self.getTypedRuleContext(Grammar.Def_assignmentContext, i)

        def getRuleIndex(self):
            return Grammar.RULE_state_machine_dsl

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterState_machine_dsl"):
                listener.enterState_machine_dsl(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitState_machine_dsl"):
                listener.exitState_machine_dsl(self)

    def state_machine_dsl(self):

        localctx = Grammar.State_machine_dslContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_state_machine_dsl)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 80
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == Grammar.DEF:
                self.state = 77
                self.def_assignment()
                self.state = 82
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 83
            self.state_definition()
            self.state = 84
            self.match(Grammar.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Def_assignmentContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.deftype = None  # Token

        def DEF(self):
            return self.getToken(Grammar.DEF, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def ASSIGN(self):
            return self.getToken(Grammar.ASSIGN, 0)

        def init_expression(self):
            return self.getTypedRuleContext(Grammar.Init_expressionContext, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def INT_TYPE(self):
            return self.getToken(Grammar.INT_TYPE, 0)

        def FLOAT_TYPE(self):
            return self.getToken(Grammar.FLOAT_TYPE, 0)

        def getRuleIndex(self):
            return Grammar.RULE_def_assignment

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDef_assignment"):
                listener.enterDef_assignment(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDef_assignment"):
                listener.exitDef_assignment(self)

    def def_assignment(self):

        localctx = Grammar.Def_assignmentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_def_assignment)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 86
            self.match(Grammar.DEF)
            self.state = 87
            localctx.deftype = self._input.LT(1)
            _la = self._input.LA(1)
            if not (_la == Grammar.INT_TYPE or _la == Grammar.FLOAT_TYPE):
                localctx.deftype = self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 88
            self.match(Grammar.ID)
            self.state = 89
            self.match(Grammar.ASSIGN)
            self.state = 90
            self.init_expression(0)
            self.state = 91
            self.match(Grammar.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class State_definitionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return Grammar.RULE_state_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class LeafStateDefinitionContext(State_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.State_definitionContext
            super().__init__(parser)
            self.pseudo = None  # Token
            self.state_id = None  # Token
            self.extra_name = None  # Token
            self.copyFrom(ctx)

        def STATE(self):
            return self.getToken(Grammar.STATE, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def NAMED(self):
            return self.getToken(Grammar.NAMED, 0)

        def PSEUDO(self):
            return self.getToken(Grammar.PSEUDO, 0)

        def STRING(self):
            return self.getToken(Grammar.STRING, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLeafStateDefinition"):
                listener.enterLeafStateDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLeafStateDefinition"):
                listener.exitLeafStateDefinition(self)

    class CompositeStateDefinitionContext(State_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.State_definitionContext
            super().__init__(parser)
            self.pseudo = None  # Token
            self.state_id = None  # Token
            self.extra_name = None  # Token
            self.copyFrom(ctx)

        def STATE(self):
            return self.getToken(Grammar.STATE, 0)

        def LBRACE(self):
            return self.getToken(Grammar.LBRACE, 0)

        def RBRACE(self):
            return self.getToken(Grammar.RBRACE, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def NAMED(self):
            return self.getToken(Grammar.NAMED, 0)

        def state_inner_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.State_inner_statementContext)
            else:
                return self.getTypedRuleContext(Grammar.State_inner_statementContext, i)

        def PSEUDO(self):
            return self.getToken(Grammar.PSEUDO, 0)

        def STRING(self):
            return self.getToken(Grammar.STRING, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCompositeStateDefinition"):
                listener.enterCompositeStateDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCompositeStateDefinition"):
                listener.exitCompositeStateDefinition(self)

    def state_definition(self):

        localctx = Grammar.State_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_state_definition)
        self._la = 0  # Token type
        try:
            self.state = 120
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 6, self._ctx)
            if la_ == 1:
                localctx = Grammar.LeafStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 94
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.PSEUDO:
                    self.state = 93
                    localctx.pseudo = self.match(Grammar.PSEUDO)

                self.state = 96
                self.match(Grammar.STATE)
                self.state = 97
                localctx.state_id = self.match(Grammar.ID)
                self.state = 100
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.NAMED:
                    self.state = 98
                    self.match(Grammar.NAMED)
                    self.state = 99
                    localctx.extra_name = self.match(Grammar.STRING)

                self.state = 102
                self.match(Grammar.SEMI)
                pass

            elif la_ == 2:
                localctx = Grammar.CompositeStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 104
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.PSEUDO:
                    self.state = 103
                    localctx.pseudo = self.match(Grammar.PSEUDO)

                self.state = 106
                self.match(Grammar.STATE)
                self.state = 107
                localctx.state_id = self.match(Grammar.ID)
                self.state = 110
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.NAMED:
                    self.state = 108
                    self.match(Grammar.NAMED)
                    self.state = 109
                    localctx.extra_name = self.match(Grammar.STRING)

                self.state = 112
                self.match(Grammar.LBRACE)
                self.state = 116
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while (
                    ((_la) & ~0x3F) == 0
                    and (
                        (1 << _la)
                        & (
                            (1 << Grammar.IMPORT)
                            | (1 << Grammar.EVENT)
                            | (1 << Grammar.PSEUDO)
                            | (1 << Grammar.STATE)
                            | (1 << Grammar.ENTER)
                            | (1 << Grammar.EXIT)
                            | (1 << Grammar.DURING)
                            | (1 << Grammar.INIT_MARKER)
                            | (1 << Grammar.SHIFT_RIGHT)
                            | (1 << Grammar.SEMI)
                            | (1 << Grammar.BANG)
                        )
                    )
                    != 0
                ) or _la == Grammar.ID:
                    self.state = 113
                    self.state_inner_statement()
                    self.state = 118
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 119
                self.match(Grammar.RBRACE)
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Transition_definitionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return Grammar.RULE_transition_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class NormalTransitionDefinitionContext(Transition_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Transition_definitionContext
            super().__init__(parser)
            self.from_state = None  # Token
            self.to_state = None  # Token
            self.from_id = None  # Token
            self.copyFrom(ctx)

        def ARROW(self):
            return self.getToken(Grammar.ARROW, 0)

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(Grammar.ID)
            else:
                return self.getToken(Grammar.ID, i)

        def COLONCOLON(self):
            return self.getToken(Grammar.COLONCOLON, 0)

        def COLON(self):
            return self.getToken(Grammar.COLON, 0)

        def chain_id(self):
            return self.getTypedRuleContext(Grammar.Chain_idContext, 0)

        def IF(self):
            return self.getToken(Grammar.IF, 0)

        def LBRACK(self):
            return self.getToken(Grammar.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(Grammar.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(Grammar.RBRACK, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def EFFECT(self):
            return self.getToken(Grammar.EFFECT, 0)

        def LBRACE(self):
            return self.getToken(Grammar.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(Grammar.Operational_statement_setContext, 0)

        def RBRACE(self):
            return self.getToken(Grammar.RBRACE, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterNormalTransitionDefinition"):
                listener.enterNormalTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitNormalTransitionDefinition"):
                listener.exitNormalTransitionDefinition(self)

    class EntryTransitionDefinitionContext(Transition_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Transition_definitionContext
            super().__init__(parser)
            self.to_state = None  # Token
            self.copyFrom(ctx)

        def INIT_MARKER(self):
            return self.getToken(Grammar.INIT_MARKER, 0)

        def ARROW(self):
            return self.getToken(Grammar.ARROW, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def chain_id(self):
            return self.getTypedRuleContext(Grammar.Chain_idContext, 0)

        def COLON(self):
            return self.getToken(Grammar.COLON, 0)

        def IF(self):
            return self.getToken(Grammar.IF, 0)

        def LBRACK(self):
            return self.getToken(Grammar.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(Grammar.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(Grammar.RBRACK, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def EFFECT(self):
            return self.getToken(Grammar.EFFECT, 0)

        def LBRACE(self):
            return self.getToken(Grammar.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(Grammar.Operational_statement_setContext, 0)

        def RBRACE(self):
            return self.getToken(Grammar.RBRACE, 0)

        def COLONCOLON(self):
            return self.getToken(Grammar.COLONCOLON, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEntryTransitionDefinition"):
                listener.enterEntryTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEntryTransitionDefinition"):
                listener.exitEntryTransitionDefinition(self)

    class ExitTransitionDefinitionContext(Transition_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Transition_definitionContext
            super().__init__(parser)
            self.from_state = None  # Token
            self.from_id = None  # Token
            self.copyFrom(ctx)

        def ARROW(self):
            return self.getToken(Grammar.ARROW, 0)

        def INIT_MARKER(self):
            return self.getToken(Grammar.INIT_MARKER, 0)

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(Grammar.ID)
            else:
                return self.getToken(Grammar.ID, i)

        def COLONCOLON(self):
            return self.getToken(Grammar.COLONCOLON, 0)

        def COLON(self):
            return self.getToken(Grammar.COLON, 0)

        def chain_id(self):
            return self.getTypedRuleContext(Grammar.Chain_idContext, 0)

        def IF(self):
            return self.getToken(Grammar.IF, 0)

        def LBRACK(self):
            return self.getToken(Grammar.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(Grammar.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(Grammar.RBRACK, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def EFFECT(self):
            return self.getToken(Grammar.EFFECT, 0)

        def LBRACE(self):
            return self.getToken(Grammar.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(Grammar.Operational_statement_setContext, 0)

        def RBRACE(self):
            return self.getToken(Grammar.RBRACE, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExitTransitionDefinition"):
                listener.enterExitTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExitTransitionDefinition"):
                listener.exitExitTransitionDefinition(self)

    def transition_definition(self):

        localctx = Grammar.Transition_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_transition_definition)
        self._la = 0  # Token type
        try:
            self.state = 192
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 13, self._ctx)
            if la_ == 1:
                localctx = Grammar.EntryTransitionDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 122
                self.match(Grammar.INIT_MARKER)
                self.state = 123
                self.match(Grammar.ARROW)
                self.state = 124
                localctx.to_state = self.match(Grammar.ID)
                self.state = 134
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 7, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 126
                    _la = self._input.LA(1)
                    if not (_la == Grammar.COLONCOLON or _la == Grammar.COLON):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 127
                    self.chain_id()
                    pass

                elif la_ == 3:
                    self.state = 128
                    self.match(Grammar.COLON)
                    self.state = 129
                    self.match(Grammar.IF)
                    self.state = 130
                    self.match(Grammar.LBRACK)
                    self.state = 131
                    self.cond_expression(0)
                    self.state = 132
                    self.match(Grammar.RBRACK)
                    pass

                self.state = 142
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [Grammar.SEMI]:
                    self.state = 136
                    self.match(Grammar.SEMI)
                    pass
                elif token in [Grammar.EFFECT]:
                    self.state = 137
                    self.match(Grammar.EFFECT)
                    self.state = 138
                    self.match(Grammar.LBRACE)
                    self.state = 139
                    self.operational_statement_set()
                    self.state = 140
                    self.match(Grammar.RBRACE)
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 2:
                localctx = Grammar.NormalTransitionDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 144
                localctx.from_state = self.match(Grammar.ID)
                self.state = 145
                self.match(Grammar.ARROW)
                self.state = 146
                localctx.to_state = self.match(Grammar.ID)
                self.state = 158
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 9, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 148
                    self.match(Grammar.COLONCOLON)
                    self.state = 149
                    localctx.from_id = self.match(Grammar.ID)
                    pass

                elif la_ == 3:
                    self.state = 150
                    self.match(Grammar.COLON)
                    self.state = 151
                    self.chain_id()
                    pass

                elif la_ == 4:
                    self.state = 152
                    self.match(Grammar.COLON)
                    self.state = 153
                    self.match(Grammar.IF)
                    self.state = 154
                    self.match(Grammar.LBRACK)
                    self.state = 155
                    self.cond_expression(0)
                    self.state = 156
                    self.match(Grammar.RBRACK)
                    pass

                self.state = 166
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [Grammar.SEMI]:
                    self.state = 160
                    self.match(Grammar.SEMI)
                    pass
                elif token in [Grammar.EFFECT]:
                    self.state = 161
                    self.match(Grammar.EFFECT)
                    self.state = 162
                    self.match(Grammar.LBRACE)
                    self.state = 163
                    self.operational_statement_set()
                    self.state = 164
                    self.match(Grammar.RBRACE)
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 3:
                localctx = Grammar.ExitTransitionDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 168
                localctx.from_state = self.match(Grammar.ID)
                self.state = 169
                self.match(Grammar.ARROW)
                self.state = 170
                self.match(Grammar.INIT_MARKER)
                self.state = 182
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 11, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 172
                    self.match(Grammar.COLONCOLON)
                    self.state = 173
                    localctx.from_id = self.match(Grammar.ID)
                    pass

                elif la_ == 3:
                    self.state = 174
                    self.match(Grammar.COLON)
                    self.state = 175
                    self.chain_id()
                    pass

                elif la_ == 4:
                    self.state = 176
                    self.match(Grammar.COLON)
                    self.state = 177
                    self.match(Grammar.IF)
                    self.state = 178
                    self.match(Grammar.LBRACK)
                    self.state = 179
                    self.cond_expression(0)
                    self.state = 180
                    self.match(Grammar.RBRACK)
                    pass

                self.state = 190
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [Grammar.SEMI]:
                    self.state = 184
                    self.match(Grammar.SEMI)
                    pass
                elif token in [Grammar.EFFECT]:
                    self.state = 185
                    self.match(Grammar.EFFECT)
                    self.state = 186
                    self.match(Grammar.LBRACE)
                    self.state = 187
                    self.operational_statement_set()
                    self.state = 188
                    self.match(Grammar.RBRACE)
                    pass
                else:
                    raise NoViableAltException(self)

                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Transition_force_definitionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return Grammar.RULE_transition_force_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class NormalForceTransitionDefinitionContext(Transition_force_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Transition_force_definitionContext
            super().__init__(parser)
            self.from_state = None  # Token
            self.to_state = None  # Token
            self.from_id = None  # Token
            self.copyFrom(ctx)

        def BANG(self):
            return self.getToken(Grammar.BANG, 0)

        def ARROW(self):
            return self.getToken(Grammar.ARROW, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(Grammar.ID)
            else:
                return self.getToken(Grammar.ID, i)

        def COLONCOLON(self):
            return self.getToken(Grammar.COLONCOLON, 0)

        def COLON(self):
            return self.getToken(Grammar.COLON, 0)

        def chain_id(self):
            return self.getTypedRuleContext(Grammar.Chain_idContext, 0)

        def IF(self):
            return self.getToken(Grammar.IF, 0)

        def LBRACK(self):
            return self.getToken(Grammar.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(Grammar.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(Grammar.RBRACK, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterNormalForceTransitionDefinition"):
                listener.enterNormalForceTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitNormalForceTransitionDefinition"):
                listener.exitNormalForceTransitionDefinition(self)

    class ExitAllForceTransitionDefinitionContext(Transition_force_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Transition_force_definitionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def BANG(self):
            return self.getToken(Grammar.BANG, 0)

        def STAR(self):
            return self.getToken(Grammar.STAR, 0)

        def ARROW(self):
            return self.getToken(Grammar.ARROW, 0)

        def INIT_MARKER(self):
            return self.getToken(Grammar.INIT_MARKER, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def chain_id(self):
            return self.getTypedRuleContext(Grammar.Chain_idContext, 0)

        def COLON(self):
            return self.getToken(Grammar.COLON, 0)

        def IF(self):
            return self.getToken(Grammar.IF, 0)

        def LBRACK(self):
            return self.getToken(Grammar.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(Grammar.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(Grammar.RBRACK, 0)

        def COLONCOLON(self):
            return self.getToken(Grammar.COLONCOLON, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExitAllForceTransitionDefinition"):
                listener.enterExitAllForceTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExitAllForceTransitionDefinition"):
                listener.exitExitAllForceTransitionDefinition(self)

    class NormalAllForceTransitionDefinitionContext(Transition_force_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Transition_force_definitionContext
            super().__init__(parser)
            self.to_state = None  # Token
            self.copyFrom(ctx)

        def BANG(self):
            return self.getToken(Grammar.BANG, 0)

        def STAR(self):
            return self.getToken(Grammar.STAR, 0)

        def ARROW(self):
            return self.getToken(Grammar.ARROW, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def chain_id(self):
            return self.getTypedRuleContext(Grammar.Chain_idContext, 0)

        def COLON(self):
            return self.getToken(Grammar.COLON, 0)

        def IF(self):
            return self.getToken(Grammar.IF, 0)

        def LBRACK(self):
            return self.getToken(Grammar.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(Grammar.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(Grammar.RBRACK, 0)

        def COLONCOLON(self):
            return self.getToken(Grammar.COLONCOLON, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterNormalAllForceTransitionDefinition"):
                listener.enterNormalAllForceTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitNormalAllForceTransitionDefinition"):
                listener.exitNormalAllForceTransitionDefinition(self)

    class ExitForceTransitionDefinitionContext(Transition_force_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Transition_force_definitionContext
            super().__init__(parser)
            self.from_state = None  # Token
            self.from_id = None  # Token
            self.copyFrom(ctx)

        def BANG(self):
            return self.getToken(Grammar.BANG, 0)

        def ARROW(self):
            return self.getToken(Grammar.ARROW, 0)

        def INIT_MARKER(self):
            return self.getToken(Grammar.INIT_MARKER, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(Grammar.ID)
            else:
                return self.getToken(Grammar.ID, i)

        def COLONCOLON(self):
            return self.getToken(Grammar.COLONCOLON, 0)

        def COLON(self):
            return self.getToken(Grammar.COLON, 0)

        def chain_id(self):
            return self.getTypedRuleContext(Grammar.Chain_idContext, 0)

        def IF(self):
            return self.getToken(Grammar.IF, 0)

        def LBRACK(self):
            return self.getToken(Grammar.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(Grammar.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(Grammar.RBRACK, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExitForceTransitionDefinition"):
                listener.enterExitForceTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExitForceTransitionDefinition"):
                listener.exitExitForceTransitionDefinition(self)

    def transition_force_definition(self):

        localctx = Grammar.Transition_force_definitionContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 10, self.RULE_transition_force_definition)
        self._la = 0  # Token type
        try:
            self.state = 262
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 18, self._ctx)
            if la_ == 1:
                localctx = Grammar.NormalForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 194
                self.match(Grammar.BANG)
                self.state = 195
                localctx.from_state = self.match(Grammar.ID)
                self.state = 196
                self.match(Grammar.ARROW)
                self.state = 197
                localctx.to_state = self.match(Grammar.ID)
                self.state = 209
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 14, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 199
                    self.match(Grammar.COLONCOLON)
                    self.state = 200
                    localctx.from_id = self.match(Grammar.ID)
                    pass

                elif la_ == 3:
                    self.state = 201
                    self.match(Grammar.COLON)
                    self.state = 202
                    self.chain_id()
                    pass

                elif la_ == 4:
                    self.state = 203
                    self.match(Grammar.COLON)
                    self.state = 204
                    self.match(Grammar.IF)
                    self.state = 205
                    self.match(Grammar.LBRACK)
                    self.state = 206
                    self.cond_expression(0)
                    self.state = 207
                    self.match(Grammar.RBRACK)
                    pass

                self.state = 211
                self.match(Grammar.SEMI)
                pass

            elif la_ == 2:
                localctx = Grammar.ExitForceTransitionDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 212
                self.match(Grammar.BANG)
                self.state = 213
                localctx.from_state = self.match(Grammar.ID)
                self.state = 214
                self.match(Grammar.ARROW)
                self.state = 215
                self.match(Grammar.INIT_MARKER)
                self.state = 227
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 15, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 217
                    self.match(Grammar.COLONCOLON)
                    self.state = 218
                    localctx.from_id = self.match(Grammar.ID)
                    pass

                elif la_ == 3:
                    self.state = 219
                    self.match(Grammar.COLON)
                    self.state = 220
                    self.chain_id()
                    pass

                elif la_ == 4:
                    self.state = 221
                    self.match(Grammar.COLON)
                    self.state = 222
                    self.match(Grammar.IF)
                    self.state = 223
                    self.match(Grammar.LBRACK)
                    self.state = 224
                    self.cond_expression(0)
                    self.state = 225
                    self.match(Grammar.RBRACK)
                    pass

                self.state = 229
                self.match(Grammar.SEMI)
                pass

            elif la_ == 3:
                localctx = Grammar.NormalAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 3)
                self.state = 230
                self.match(Grammar.BANG)
                self.state = 231
                self.match(Grammar.STAR)
                self.state = 232
                self.match(Grammar.ARROW)
                self.state = 233
                localctx.to_state = self.match(Grammar.ID)
                self.state = 243
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 16, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 235
                    _la = self._input.LA(1)
                    if not (_la == Grammar.COLONCOLON or _la == Grammar.COLON):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 236
                    self.chain_id()
                    pass

                elif la_ == 3:
                    self.state = 237
                    self.match(Grammar.COLON)
                    self.state = 238
                    self.match(Grammar.IF)
                    self.state = 239
                    self.match(Grammar.LBRACK)
                    self.state = 240
                    self.cond_expression(0)
                    self.state = 241
                    self.match(Grammar.RBRACK)
                    pass

                self.state = 245
                self.match(Grammar.SEMI)
                pass

            elif la_ == 4:
                localctx = Grammar.ExitAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 4)
                self.state = 246
                self.match(Grammar.BANG)
                self.state = 247
                self.match(Grammar.STAR)
                self.state = 248
                self.match(Grammar.ARROW)
                self.state = 249
                self.match(Grammar.INIT_MARKER)
                self.state = 259
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 17, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 251
                    _la = self._input.LA(1)
                    if not (_la == Grammar.COLONCOLON or _la == Grammar.COLON):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 252
                    self.chain_id()
                    pass

                elif la_ == 3:
                    self.state = 253
                    self.match(Grammar.COLON)
                    self.state = 254
                    self.match(Grammar.IF)
                    self.state = 255
                    self.match(Grammar.LBRACK)
                    self.state = 256
                    self.cond_expression(0)
                    self.state = 257
                    self.match(Grammar.RBRACK)
                    pass

                self.state = 261
                self.match(Grammar.SEMI)
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Enter_definitionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return Grammar.RULE_enter_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class EnterRefFuncContext(Enter_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Enter_definitionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def ENTER(self):
            return self.getToken(Grammar.ENTER, 0)

        def REF(self):
            return self.getToken(Grammar.REF, 0)

        def chain_id(self):
            return self.getTypedRuleContext(Grammar.Chain_idContext, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEnterRefFunc"):
                listener.enterEnterRefFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEnterRefFunc"):
                listener.exitEnterRefFunc(self)

    class EnterOperationsContext(Enter_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Enter_definitionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def ENTER(self):
            return self.getToken(Grammar.ENTER, 0)

        def LBRACE(self):
            return self.getToken(Grammar.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(Grammar.Operational_statement_setContext, 0)

        def RBRACE(self):
            return self.getToken(Grammar.RBRACE, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEnterOperations"):
                listener.enterEnterOperations(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEnterOperations"):
                listener.exitEnterOperations(self)

    class EnterAbstractFuncContext(Enter_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Enter_definitionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.raw_doc = None  # Token
            self.copyFrom(ctx)

        def ENTER(self):
            return self.getToken(Grammar.ENTER, 0)

        def ABSTRACT(self):
            return self.getToken(Grammar.ABSTRACT, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def MULTILINE_COMMENT(self):
            return self.getToken(Grammar.MULTILINE_COMMENT, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEnterAbstractFunc"):
                listener.enterEnterAbstractFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEnterAbstractFunc"):
                listener.exitEnterAbstractFunc(self)

    def enter_definition(self):

        localctx = Grammar.Enter_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_enter_definition)
        self._la = 0  # Token type
        try:
            self.state = 290
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 22, self._ctx)
            if la_ == 1:
                localctx = Grammar.EnterOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 264
                self.match(Grammar.ENTER)
                self.state = 266
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.ID:
                    self.state = 265
                    localctx.func_name = self.match(Grammar.ID)

                self.state = 268
                self.match(Grammar.LBRACE)
                self.state = 269
                self.operational_statement_set()
                self.state = 270
                self.match(Grammar.RBRACE)
                pass

            elif la_ == 2:
                localctx = Grammar.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 272
                self.match(Grammar.ENTER)
                self.state = 273
                self.match(Grammar.ABSTRACT)
                self.state = 274
                localctx.func_name = self.match(Grammar.ID)
                self.state = 275
                self.match(Grammar.SEMI)
                pass

            elif la_ == 3:
                localctx = Grammar.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 276
                self.match(Grammar.ENTER)
                self.state = 277
                self.match(Grammar.ABSTRACT)
                self.state = 279
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.ID:
                    self.state = 278
                    localctx.func_name = self.match(Grammar.ID)

                self.state = 281
                localctx.raw_doc = self.match(Grammar.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = Grammar.EnterRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 282
                self.match(Grammar.ENTER)
                self.state = 284
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.ID:
                    self.state = 283
                    localctx.func_name = self.match(Grammar.ID)

                self.state = 286
                self.match(Grammar.REF)
                self.state = 287
                self.chain_id()
                self.state = 288
                self.match(Grammar.SEMI)
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Exit_definitionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return Grammar.RULE_exit_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class ExitOperationsContext(Exit_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Exit_definitionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def EXIT(self):
            return self.getToken(Grammar.EXIT, 0)

        def LBRACE(self):
            return self.getToken(Grammar.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(Grammar.Operational_statement_setContext, 0)

        def RBRACE(self):
            return self.getToken(Grammar.RBRACE, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExitOperations"):
                listener.enterExitOperations(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExitOperations"):
                listener.exitExitOperations(self)

    class ExitRefFuncContext(Exit_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Exit_definitionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def EXIT(self):
            return self.getToken(Grammar.EXIT, 0)

        def REF(self):
            return self.getToken(Grammar.REF, 0)

        def chain_id(self):
            return self.getTypedRuleContext(Grammar.Chain_idContext, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExitRefFunc"):
                listener.enterExitRefFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExitRefFunc"):
                listener.exitExitRefFunc(self)

    class ExitAbstractFuncContext(Exit_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Exit_definitionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.raw_doc = None  # Token
            self.copyFrom(ctx)

        def EXIT(self):
            return self.getToken(Grammar.EXIT, 0)

        def ABSTRACT(self):
            return self.getToken(Grammar.ABSTRACT, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def MULTILINE_COMMENT(self):
            return self.getToken(Grammar.MULTILINE_COMMENT, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExitAbstractFunc"):
                listener.enterExitAbstractFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExitAbstractFunc"):
                listener.exitExitAbstractFunc(self)

    def exit_definition(self):

        localctx = Grammar.Exit_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_exit_definition)
        self._la = 0  # Token type
        try:
            self.state = 318
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 26, self._ctx)
            if la_ == 1:
                localctx = Grammar.ExitOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 292
                self.match(Grammar.EXIT)
                self.state = 294
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.ID:
                    self.state = 293
                    localctx.func_name = self.match(Grammar.ID)

                self.state = 296
                self.match(Grammar.LBRACE)
                self.state = 297
                self.operational_statement_set()
                self.state = 298
                self.match(Grammar.RBRACE)
                pass

            elif la_ == 2:
                localctx = Grammar.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 300
                self.match(Grammar.EXIT)
                self.state = 301
                self.match(Grammar.ABSTRACT)
                self.state = 302
                localctx.func_name = self.match(Grammar.ID)
                self.state = 303
                self.match(Grammar.SEMI)
                pass

            elif la_ == 3:
                localctx = Grammar.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 304
                self.match(Grammar.EXIT)
                self.state = 305
                self.match(Grammar.ABSTRACT)
                self.state = 307
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.ID:
                    self.state = 306
                    localctx.func_name = self.match(Grammar.ID)

                self.state = 309
                localctx.raw_doc = self.match(Grammar.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = Grammar.ExitRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 310
                self.match(Grammar.EXIT)
                self.state = 312
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.ID:
                    self.state = 311
                    localctx.func_name = self.match(Grammar.ID)

                self.state = 314
                self.match(Grammar.REF)
                self.state = 315
                self.chain_id()
                self.state = 316
                self.match(Grammar.SEMI)
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class During_definitionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return Grammar.RULE_during_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class DuringOperationsContext(During_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.During_definitionContext
            super().__init__(parser)
            self.aspect = None  # Token
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def DURING(self):
            return self.getToken(Grammar.DURING, 0)

        def LBRACE(self):
            return self.getToken(Grammar.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(Grammar.Operational_statement_setContext, 0)

        def RBRACE(self):
            return self.getToken(Grammar.RBRACE, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def BEFORE(self):
            return self.getToken(Grammar.BEFORE, 0)

        def AFTER(self):
            return self.getToken(Grammar.AFTER, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDuringOperations"):
                listener.enterDuringOperations(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDuringOperations"):
                listener.exitDuringOperations(self)

    class DuringAbstractFuncContext(During_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.During_definitionContext
            super().__init__(parser)
            self.aspect = None  # Token
            self.func_name = None  # Token
            self.raw_doc = None  # Token
            self.copyFrom(ctx)

        def DURING(self):
            return self.getToken(Grammar.DURING, 0)

        def ABSTRACT(self):
            return self.getToken(Grammar.ABSTRACT, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def BEFORE(self):
            return self.getToken(Grammar.BEFORE, 0)

        def AFTER(self):
            return self.getToken(Grammar.AFTER, 0)

        def MULTILINE_COMMENT(self):
            return self.getToken(Grammar.MULTILINE_COMMENT, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDuringAbstractFunc"):
                listener.enterDuringAbstractFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDuringAbstractFunc"):
                listener.exitDuringAbstractFunc(self)

    class DuringRefFuncContext(During_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.During_definitionContext
            super().__init__(parser)
            self.aspect = None  # Token
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def DURING(self):
            return self.getToken(Grammar.DURING, 0)

        def REF(self):
            return self.getToken(Grammar.REF, 0)

        def chain_id(self):
            return self.getTypedRuleContext(Grammar.Chain_idContext, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def BEFORE(self):
            return self.getToken(Grammar.BEFORE, 0)

        def AFTER(self):
            return self.getToken(Grammar.AFTER, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDuringRefFunc"):
                listener.enterDuringRefFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDuringRefFunc"):
                listener.exitDuringRefFunc(self)

    def during_definition(self):

        localctx = Grammar.During_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_during_definition)
        self._la = 0  # Token type
        try:
            self.state = 358
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 34, self._ctx)
            if la_ == 1:
                localctx = Grammar.DuringOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 320
                self.match(Grammar.DURING)
                self.state = 322
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.BEFORE or _la == Grammar.AFTER:
                    self.state = 321
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == Grammar.BEFORE or _la == Grammar.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 325
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.ID:
                    self.state = 324
                    localctx.func_name = self.match(Grammar.ID)

                self.state = 327
                self.match(Grammar.LBRACE)
                self.state = 328
                self.operational_statement_set()
                self.state = 329
                self.match(Grammar.RBRACE)
                pass

            elif la_ == 2:
                localctx = Grammar.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 331
                self.match(Grammar.DURING)
                self.state = 333
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.BEFORE or _la == Grammar.AFTER:
                    self.state = 332
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == Grammar.BEFORE or _la == Grammar.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 335
                self.match(Grammar.ABSTRACT)
                self.state = 336
                localctx.func_name = self.match(Grammar.ID)
                self.state = 337
                self.match(Grammar.SEMI)
                pass

            elif la_ == 3:
                localctx = Grammar.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 338
                self.match(Grammar.DURING)
                self.state = 340
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.BEFORE or _la == Grammar.AFTER:
                    self.state = 339
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == Grammar.BEFORE or _la == Grammar.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 342
                self.match(Grammar.ABSTRACT)
                self.state = 344
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.ID:
                    self.state = 343
                    localctx.func_name = self.match(Grammar.ID)

                self.state = 346
                localctx.raw_doc = self.match(Grammar.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = Grammar.DuringRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 347
                self.match(Grammar.DURING)
                self.state = 349
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.BEFORE or _la == Grammar.AFTER:
                    self.state = 348
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == Grammar.BEFORE or _la == Grammar.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 352
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.ID:
                    self.state = 351
                    localctx.func_name = self.match(Grammar.ID)

                self.state = 354
                self.match(Grammar.REF)
                self.state = 355
                self.chain_id()
                self.state = 356
                self.match(Grammar.SEMI)
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class During_aspect_definitionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return Grammar.RULE_during_aspect_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class DuringAspectRefFuncContext(During_aspect_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.During_aspect_definitionContext
            super().__init__(parser)
            self.aspect = None  # Token
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def SHIFT_RIGHT(self):
            return self.getToken(Grammar.SHIFT_RIGHT, 0)

        def DURING(self):
            return self.getToken(Grammar.DURING, 0)

        def REF(self):
            return self.getToken(Grammar.REF, 0)

        def chain_id(self):
            return self.getTypedRuleContext(Grammar.Chain_idContext, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def BEFORE(self):
            return self.getToken(Grammar.BEFORE, 0)

        def AFTER(self):
            return self.getToken(Grammar.AFTER, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDuringAspectRefFunc"):
                listener.enterDuringAspectRefFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDuringAspectRefFunc"):
                listener.exitDuringAspectRefFunc(self)

    class DuringAspectAbstractFuncContext(During_aspect_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.During_aspect_definitionContext
            super().__init__(parser)
            self.aspect = None  # Token
            self.func_name = None  # Token
            self.raw_doc = None  # Token
            self.copyFrom(ctx)

        def SHIFT_RIGHT(self):
            return self.getToken(Grammar.SHIFT_RIGHT, 0)

        def DURING(self):
            return self.getToken(Grammar.DURING, 0)

        def ABSTRACT(self):
            return self.getToken(Grammar.ABSTRACT, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def BEFORE(self):
            return self.getToken(Grammar.BEFORE, 0)

        def AFTER(self):
            return self.getToken(Grammar.AFTER, 0)

        def MULTILINE_COMMENT(self):
            return self.getToken(Grammar.MULTILINE_COMMENT, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDuringAspectAbstractFunc"):
                listener.enterDuringAspectAbstractFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDuringAspectAbstractFunc"):
                listener.exitDuringAspectAbstractFunc(self)

    class DuringAspectOperationsContext(During_aspect_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.During_aspect_definitionContext
            super().__init__(parser)
            self.aspect = None  # Token
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def SHIFT_RIGHT(self):
            return self.getToken(Grammar.SHIFT_RIGHT, 0)

        def DURING(self):
            return self.getToken(Grammar.DURING, 0)

        def LBRACE(self):
            return self.getToken(Grammar.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(Grammar.Operational_statement_setContext, 0)

        def RBRACE(self):
            return self.getToken(Grammar.RBRACE, 0)

        def BEFORE(self):
            return self.getToken(Grammar.BEFORE, 0)

        def AFTER(self):
            return self.getToken(Grammar.AFTER, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDuringAspectOperations"):
                listener.enterDuringAspectOperations(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDuringAspectOperations"):
                listener.exitDuringAspectOperations(self)

    def during_aspect_definition(self):

        localctx = Grammar.During_aspect_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_during_aspect_definition)
        self._la = 0  # Token type
        try:
            self.state = 394
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 38, self._ctx)
            if la_ == 1:
                localctx = Grammar.DuringAspectOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 360
                self.match(Grammar.SHIFT_RIGHT)
                self.state = 361
                self.match(Grammar.DURING)
                self.state = 362
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == Grammar.BEFORE or _la == Grammar.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 364
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.ID:
                    self.state = 363
                    localctx.func_name = self.match(Grammar.ID)

                self.state = 366
                self.match(Grammar.LBRACE)
                self.state = 367
                self.operational_statement_set()
                self.state = 368
                self.match(Grammar.RBRACE)
                pass

            elif la_ == 2:
                localctx = Grammar.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 370
                self.match(Grammar.SHIFT_RIGHT)
                self.state = 371
                self.match(Grammar.DURING)
                self.state = 372
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == Grammar.BEFORE or _la == Grammar.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 373
                self.match(Grammar.ABSTRACT)
                self.state = 374
                localctx.func_name = self.match(Grammar.ID)
                self.state = 375
                self.match(Grammar.SEMI)
                pass

            elif la_ == 3:
                localctx = Grammar.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 376
                self.match(Grammar.SHIFT_RIGHT)
                self.state = 377
                self.match(Grammar.DURING)
                self.state = 378
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == Grammar.BEFORE or _la == Grammar.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 379
                self.match(Grammar.ABSTRACT)
                self.state = 381
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.ID:
                    self.state = 380
                    localctx.func_name = self.match(Grammar.ID)

                self.state = 383
                localctx.raw_doc = self.match(Grammar.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = Grammar.DuringAspectRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 384
                self.match(Grammar.SHIFT_RIGHT)
                self.state = 385
                self.match(Grammar.DURING)
                self.state = 386
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == Grammar.BEFORE or _la == Grammar.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 388
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == Grammar.ID:
                    self.state = 387
                    localctx.func_name = self.match(Grammar.ID)

                self.state = 390
                self.match(Grammar.REF)
                self.state = 391
                self.chain_id()
                self.state = 392
                self.match(Grammar.SEMI)
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Event_definitionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.event_name = None  # Token
            self.extra_name = None  # Token

        def EVENT(self):
            return self.getToken(Grammar.EVENT, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def NAMED(self):
            return self.getToken(Grammar.NAMED, 0)

        def STRING(self):
            return self.getToken(Grammar.STRING, 0)

        def getRuleIndex(self):
            return Grammar.RULE_event_definition

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEvent_definition"):
                listener.enterEvent_definition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEvent_definition"):
                listener.exitEvent_definition(self)

    def event_definition(self):

        localctx = Grammar.Event_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_event_definition)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 396
            self.match(Grammar.EVENT)
            self.state = 397
            localctx.event_name = self.match(Grammar.ID)
            self.state = 400
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == Grammar.NAMED:
                self.state = 398
                self.match(Grammar.NAMED)
                self.state = 399
                localctx.extra_name = self.match(Grammar.STRING)

            self.state = 402
            self.match(Grammar.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Import_statementContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.import_path = None  # Token
            self.state_alias = None  # Token
            self.extra_name = None  # Token

        def IMPORT(self):
            return self.getToken(Grammar.IMPORT, 0)

        def AS(self):
            return self.getToken(Grammar.AS, 0)

        def STRING(self, i: int = None):
            if i is None:
                return self.getTokens(Grammar.STRING)
            else:
                return self.getToken(Grammar.STRING, i)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def LBRACE(self):
            return self.getToken(Grammar.LBRACE, 0)

        def RBRACE(self):
            return self.getToken(Grammar.RBRACE, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def NAMED(self):
            return self.getToken(Grammar.NAMED, 0)

        def import_mapping_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    Grammar.Import_mapping_statementContext
                )
            else:
                return self.getTypedRuleContext(
                    Grammar.Import_mapping_statementContext, i
                )

        def getRuleIndex(self):
            return Grammar.RULE_import_statement

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImport_statement"):
                listener.enterImport_statement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImport_statement"):
                listener.exitImport_statement(self)

    def import_statement(self):

        localctx = Grammar.Import_statementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_import_statement)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 404
            self.match(Grammar.IMPORT)
            self.state = 405
            localctx.import_path = self.match(Grammar.STRING)
            self.state = 406
            self.match(Grammar.AS)
            self.state = 407
            localctx.state_alias = self.match(Grammar.ID)
            self.state = 410
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == Grammar.NAMED:
                self.state = 408
                self.match(Grammar.NAMED)
                self.state = 409
                localctx.extra_name = self.match(Grammar.STRING)

            self.state = 421
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [Grammar.LBRACE]:
                self.state = 412
                self.match(Grammar.LBRACE)
                self.state = 416
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while ((_la) & ~0x3F) == 0 and (
                    (1 << _la)
                    & ((1 << Grammar.DEF) | (1 << Grammar.EVENT) | (1 << Grammar.SEMI))
                ) != 0:
                    self.state = 413
                    self.import_mapping_statement()
                    self.state = 418
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 419
                self.match(Grammar.RBRACE)
                pass
            elif token in [Grammar.SEMI]:
                self.state = 420
                self.match(Grammar.SEMI)
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

    class Import_mapping_statementContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def import_def_mapping(self):
            return self.getTypedRuleContext(Grammar.Import_def_mappingContext, 0)

        def import_event_mapping(self):
            return self.getTypedRuleContext(Grammar.Import_event_mappingContext, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def getRuleIndex(self):
            return Grammar.RULE_import_mapping_statement

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImport_mapping_statement"):
                listener.enterImport_mapping_statement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImport_mapping_statement"):
                listener.exitImport_mapping_statement(self)

    def import_mapping_statement(self):

        localctx = Grammar.Import_mapping_statementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_import_mapping_statement)
        try:
            self.state = 426
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [Grammar.DEF]:
                self.enterOuterAlt(localctx, 1)
                self.state = 423
                self.import_def_mapping()
                pass
            elif token in [Grammar.EVENT]:
                self.enterOuterAlt(localctx, 2)
                self.state = 424
                self.import_event_mapping()
                pass
            elif token in [Grammar.SEMI]:
                self.enterOuterAlt(localctx, 3)
                self.state = 425
                self.match(Grammar.SEMI)
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

    class Import_def_mappingContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def DEF(self):
            return self.getToken(Grammar.DEF, 0)

        def import_def_selector(self):
            return self.getTypedRuleContext(Grammar.Import_def_selectorContext, 0)

        def ARROW(self):
            return self.getToken(Grammar.ARROW, 0)

        def import_def_target_template(self):
            return self.getTypedRuleContext(
                Grammar.Import_def_target_templateContext, 0
            )

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def getRuleIndex(self):
            return Grammar.RULE_import_def_mapping

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImport_def_mapping"):
                listener.enterImport_def_mapping(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImport_def_mapping"):
                listener.exitImport_def_mapping(self)

    def import_def_mapping(self):

        localctx = Grammar.Import_def_mappingContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_import_def_mapping)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 428
            self.match(Grammar.DEF)
            self.state = 429
            self.import_def_selector()
            self.state = 430
            self.match(Grammar.ARROW)
            self.state = 431
            self.import_def_target_template()
            self.state = 432
            self.match(Grammar.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Import_def_selectorContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return Grammar.RULE_import_def_selector

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class ImportDefFallbackSelectorContext(Import_def_selectorContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Import_def_selectorContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def STAR(self):
            return self.getToken(Grammar.STAR, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImportDefFallbackSelector"):
                listener.enterImportDefFallbackSelector(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImportDefFallbackSelector"):
                listener.exitImportDefFallbackSelector(self)

    class ImportDefPatternSelectorContext(Import_def_selectorContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Import_def_selectorContext
            super().__init__(parser)
            self.selector_pattern = None  # Token
            self.copyFrom(ctx)

        def IMPORT_DEF_SELECTOR_PATTERN(self):
            return self.getToken(Grammar.IMPORT_DEF_SELECTOR_PATTERN, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImportDefPatternSelector"):
                listener.enterImportDefPatternSelector(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImportDefPatternSelector"):
                listener.exitImportDefPatternSelector(self)

    class ImportDefExactSelectorContext(Import_def_selectorContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Import_def_selectorContext
            super().__init__(parser)
            self.selector_name = None  # Token
            self.copyFrom(ctx)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImportDefExactSelector"):
                listener.enterImportDefExactSelector(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImportDefExactSelector"):
                listener.exitImportDefExactSelector(self)

    class ImportDefSetSelectorContext(Import_def_selectorContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Import_def_selectorContext
            super().__init__(parser)
            self._ID = None  # Token
            self.selector_items = list()  # of Tokens
            self.copyFrom(ctx)

        def LBRACE(self):
            return self.getToken(Grammar.LBRACE, 0)

        def RBRACE(self):
            return self.getToken(Grammar.RBRACE, 0)

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(Grammar.ID)
            else:
                return self.getToken(Grammar.ID, i)

        def COMMA(self, i: int = None):
            if i is None:
                return self.getTokens(Grammar.COMMA)
            else:
                return self.getToken(Grammar.COMMA, i)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImportDefSetSelector"):
                listener.enterImportDefSetSelector(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImportDefSetSelector"):
                listener.exitImportDefSetSelector(self)

    def import_def_selector(self):

        localctx = Grammar.Import_def_selectorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_import_def_selector)
        self._la = 0  # Token type
        try:
            self.state = 447
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [Grammar.STAR]:
                localctx = Grammar.ImportDefFallbackSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 434
                self.match(Grammar.STAR)
                pass
            elif token in [Grammar.LBRACE]:
                localctx = Grammar.ImportDefSetSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 435
                self.match(Grammar.LBRACE)
                self.state = 436
                localctx._ID = self.match(Grammar.ID)
                localctx.selector_items.append(localctx._ID)
                self.state = 441
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == Grammar.COMMA:
                    self.state = 437
                    self.match(Grammar.COMMA)
                    self.state = 438
                    localctx._ID = self.match(Grammar.ID)
                    localctx.selector_items.append(localctx._ID)
                    self.state = 443
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 444
                self.match(Grammar.RBRACE)
                pass
            elif token in [Grammar.IMPORT_DEF_SELECTOR_PATTERN]:
                localctx = Grammar.ImportDefPatternSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 445
                localctx.selector_pattern = self.match(
                    Grammar.IMPORT_DEF_SELECTOR_PATTERN
                )
                pass
            elif token in [Grammar.ID]:
                localctx = Grammar.ImportDefExactSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 446
                localctx.selector_name = self.match(Grammar.ID)
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

    class Import_def_target_templateContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.target_text = None  # Token

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def IMPORT_DEF_TARGET_TEMPLATE(self):
            return self.getToken(Grammar.IMPORT_DEF_TARGET_TEMPLATE, 0)

        def STAR(self):
            return self.getToken(Grammar.STAR, 0)

        def getRuleIndex(self):
            return Grammar.RULE_import_def_target_template

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImport_def_target_template"):
                listener.enterImport_def_target_template(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImport_def_target_template"):
                listener.exitImport_def_target_template(self)

    def import_def_target_template(self):

        localctx = Grammar.Import_def_target_templateContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 30, self.RULE_import_def_target_template)
        try:
            self.state = 452
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [Grammar.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 449
                localctx.target_text = self.match(Grammar.ID)
                pass
            elif token in [Grammar.IMPORT_DEF_TARGET_TEMPLATE]:
                self.enterOuterAlt(localctx, 2)
                self.state = 450
                localctx.target_text = self.match(Grammar.IMPORT_DEF_TARGET_TEMPLATE)
                pass
            elif token in [Grammar.STAR]:
                self.enterOuterAlt(localctx, 3)
                self.state = 451
                localctx.target_text = self.match(Grammar.STAR)
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

    class Import_event_mappingContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.source_event = None  # Chain_idContext
            self.target_event = None  # Chain_idContext
            self.extra_name = None  # Token

        def EVENT(self):
            return self.getToken(Grammar.EVENT, 0)

        def ARROW(self):
            return self.getToken(Grammar.ARROW, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def chain_id(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Chain_idContext)
            else:
                return self.getTypedRuleContext(Grammar.Chain_idContext, i)

        def NAMED(self):
            return self.getToken(Grammar.NAMED, 0)

        def STRING(self):
            return self.getToken(Grammar.STRING, 0)

        def getRuleIndex(self):
            return Grammar.RULE_import_event_mapping

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImport_event_mapping"):
                listener.enterImport_event_mapping(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImport_event_mapping"):
                listener.exitImport_event_mapping(self)

    def import_event_mapping(self):

        localctx = Grammar.Import_event_mappingContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_import_event_mapping)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 454
            self.match(Grammar.EVENT)
            self.state = 455
            localctx.source_event = self.chain_id()
            self.state = 456
            self.match(Grammar.ARROW)
            self.state = 457
            localctx.target_event = self.chain_id()
            self.state = 460
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == Grammar.NAMED:
                self.state = 458
                self.match(Grammar.NAMED)
                self.state = 459
                localctx.extra_name = self.match(Grammar.STRING)

            self.state = 462
            self.match(Grammar.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Operation_assignmentContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def ASSIGN(self):
            return self.getToken(Grammar.ASSIGN, 0)

        def num_expression(self):
            return self.getTypedRuleContext(Grammar.Num_expressionContext, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def getRuleIndex(self):
            return Grammar.RULE_operation_assignment

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterOperation_assignment"):
                listener.enterOperation_assignment(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitOperation_assignment"):
                listener.exitOperation_assignment(self)

    def operation_assignment(self):

        localctx = Grammar.Operation_assignmentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_operation_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 464
            self.match(Grammar.ID)
            self.state = 465
            self.match(Grammar.ASSIGN)
            self.state = 466
            self.num_expression(0)
            self.state = 467
            self.match(Grammar.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Operation_blockContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LBRACE(self):
            return self.getToken(Grammar.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(Grammar.Operational_statement_setContext, 0)

        def RBRACE(self):
            return self.getToken(Grammar.RBRACE, 0)

        def getRuleIndex(self):
            return Grammar.RULE_operation_block

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterOperation_block"):
                listener.enterOperation_block(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitOperation_block"):
                listener.exitOperation_block(self)

    def operation_block(self):

        localctx = Grammar.Operation_blockContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_operation_block)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 469
            self.match(Grammar.LBRACE)
            self.state = 470
            self.operational_statement_set()
            self.state = 471
            self.match(Grammar.RBRACE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class If_statementContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IF(self, i: int = None):
            if i is None:
                return self.getTokens(Grammar.IF)
            else:
                return self.getToken(Grammar.IF, i)

        def LBRACK(self, i: int = None):
            if i is None:
                return self.getTokens(Grammar.LBRACK)
            else:
                return self.getToken(Grammar.LBRACK, i)

        def cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Cond_expressionContext)
            else:
                return self.getTypedRuleContext(Grammar.Cond_expressionContext, i)

        def RBRACK(self, i: int = None):
            if i is None:
                return self.getTokens(Grammar.RBRACK)
            else:
                return self.getToken(Grammar.RBRACK, i)

        def operation_block(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Operation_blockContext)
            else:
                return self.getTypedRuleContext(Grammar.Operation_blockContext, i)

        def ELSE(self, i: int = None):
            if i is None:
                return self.getTokens(Grammar.ELSE)
            else:
                return self.getToken(Grammar.ELSE, i)

        def getRuleIndex(self):
            return Grammar.RULE_if_statement

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterIf_statement"):
                listener.enterIf_statement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitIf_statement"):
                listener.exitIf_statement(self)

    def if_statement(self):

        localctx = Grammar.If_statementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_if_statement)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 473
            self.match(Grammar.IF)
            self.state = 474
            self.match(Grammar.LBRACK)
            self.state = 475
            self.cond_expression(0)
            self.state = 476
            self.match(Grammar.RBRACK)
            self.state = 477
            self.operation_block()
            self.state = 487
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 48, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 478
                    self.match(Grammar.ELSE)
                    self.state = 479
                    self.match(Grammar.IF)
                    self.state = 480
                    self.match(Grammar.LBRACK)
                    self.state = 481
                    self.cond_expression(0)
                    self.state = 482
                    self.match(Grammar.RBRACK)
                    self.state = 483
                    self.operation_block()
                self.state = 489
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 48, self._ctx)

            self.state = 492
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == Grammar.ELSE:
                self.state = 490
                self.match(Grammar.ELSE)
                self.state = 491
                self.operation_block()

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Operational_statementContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def operation_assignment(self):
            return self.getTypedRuleContext(Grammar.Operation_assignmentContext, 0)

        def if_statement(self):
            return self.getTypedRuleContext(Grammar.If_statementContext, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def getRuleIndex(self):
            return Grammar.RULE_operational_statement

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterOperational_statement"):
                listener.enterOperational_statement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitOperational_statement"):
                listener.exitOperational_statement(self)

    def operational_statement(self):

        localctx = Grammar.Operational_statementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_operational_statement)
        try:
            self.state = 497
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [Grammar.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 494
                self.operation_assignment()
                pass
            elif token in [Grammar.IF]:
                self.enterOuterAlt(localctx, 2)
                self.state = 495
                self.if_statement()
                pass
            elif token in [Grammar.SEMI]:
                self.enterOuterAlt(localctx, 3)
                self.state = 496
                self.match(Grammar.SEMI)
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

    class Operational_statement_setContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def operational_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Operational_statementContext)
            else:
                return self.getTypedRuleContext(Grammar.Operational_statementContext, i)

        def getRuleIndex(self):
            return Grammar.RULE_operational_statement_set

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterOperational_statement_set"):
                listener.enterOperational_statement_set(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitOperational_statement_set"):
                listener.exitOperational_statement_set(self)

    def operational_statement_set(self):

        localctx = Grammar.Operational_statement_setContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_operational_statement_set)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 502
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while ((_la - 16) & ~0x3F) == 0 and (
                (1 << (_la - 16))
                & (
                    (1 << (Grammar.IF - 16))
                    | (1 << (Grammar.SEMI - 16))
                    | (1 << (Grammar.ID - 16))
                )
            ) != 0:
                self.state = 499
                self.operational_statement()
                self.state = 504
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class State_inner_statementContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def state_definition(self):
            return self.getTypedRuleContext(Grammar.State_definitionContext, 0)

        def transition_definition(self):
            return self.getTypedRuleContext(Grammar.Transition_definitionContext, 0)

        def transition_force_definition(self):
            return self.getTypedRuleContext(
                Grammar.Transition_force_definitionContext, 0
            )

        def enter_definition(self):
            return self.getTypedRuleContext(Grammar.Enter_definitionContext, 0)

        def during_definition(self):
            return self.getTypedRuleContext(Grammar.During_definitionContext, 0)

        def exit_definition(self):
            return self.getTypedRuleContext(Grammar.Exit_definitionContext, 0)

        def during_aspect_definition(self):
            return self.getTypedRuleContext(Grammar.During_aspect_definitionContext, 0)

        def event_definition(self):
            return self.getTypedRuleContext(Grammar.Event_definitionContext, 0)

        def import_statement(self):
            return self.getTypedRuleContext(Grammar.Import_statementContext, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def getRuleIndex(self):
            return Grammar.RULE_state_inner_statement

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterState_inner_statement"):
                listener.enterState_inner_statement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitState_inner_statement"):
                listener.exitState_inner_statement(self)

    def state_inner_statement(self):

        localctx = Grammar.State_inner_statementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_state_inner_statement)
        try:
            self.state = 515
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [Grammar.PSEUDO, Grammar.STATE]:
                self.enterOuterAlt(localctx, 1)
                self.state = 505
                self.state_definition()
                pass
            elif token in [Grammar.INIT_MARKER, Grammar.ID]:
                self.enterOuterAlt(localctx, 2)
                self.state = 506
                self.transition_definition()
                pass
            elif token in [Grammar.BANG]:
                self.enterOuterAlt(localctx, 3)
                self.state = 507
                self.transition_force_definition()
                pass
            elif token in [Grammar.ENTER]:
                self.enterOuterAlt(localctx, 4)
                self.state = 508
                self.enter_definition()
                pass
            elif token in [Grammar.DURING]:
                self.enterOuterAlt(localctx, 5)
                self.state = 509
                self.during_definition()
                pass
            elif token in [Grammar.EXIT]:
                self.enterOuterAlt(localctx, 6)
                self.state = 510
                self.exit_definition()
                pass
            elif token in [Grammar.SHIFT_RIGHT]:
                self.enterOuterAlt(localctx, 7)
                self.state = 511
                self.during_aspect_definition()
                pass
            elif token in [Grammar.EVENT]:
                self.enterOuterAlt(localctx, 8)
                self.state = 512
                self.event_definition()
                pass
            elif token in [Grammar.IMPORT]:
                self.enterOuterAlt(localctx, 9)
                self.state = 513
                self.import_statement()
                pass
            elif token in [Grammar.SEMI]:
                self.enterOuterAlt(localctx, 10)
                self.state = 514
                self.match(Grammar.SEMI)
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

    class Operation_programContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EOF(self):
            return self.getToken(Grammar.EOF, 0)

        def operational_assignment(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Operational_assignmentContext)
            else:
                return self.getTypedRuleContext(
                    Grammar.Operational_assignmentContext, i
                )

        def getRuleIndex(self):
            return Grammar.RULE_operation_program

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterOperation_program"):
                listener.enterOperation_program(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitOperation_program"):
                listener.exitOperation_program(self)

    def operation_program(self):

        localctx = Grammar.Operation_programContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_operation_program)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 520
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == Grammar.ID:
                self.state = 517
                self.operational_assignment()
                self.state = 522
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 523
            self.match(Grammar.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Preamble_programContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EOF(self):
            return self.getToken(Grammar.EOF, 0)

        def preamble_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Preamble_statementContext)
            else:
                return self.getTypedRuleContext(Grammar.Preamble_statementContext, i)

        def getRuleIndex(self):
            return Grammar.RULE_preamble_program

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterPreamble_program"):
                listener.enterPreamble_program(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitPreamble_program"):
                listener.exitPreamble_program(self)

    def preamble_program(self):

        localctx = Grammar.Preamble_programContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_preamble_program)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 528
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == Grammar.ID:
                self.state = 525
                self.preamble_statement()
                self.state = 530
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 531
            self.match(Grammar.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Preamble_statementContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def initial_assignment(self):
            return self.getTypedRuleContext(Grammar.Initial_assignmentContext, 0)

        def constant_definition(self):
            return self.getTypedRuleContext(Grammar.Constant_definitionContext, 0)

        def getRuleIndex(self):
            return Grammar.RULE_preamble_statement

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterPreamble_statement"):
                listener.enterPreamble_statement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitPreamble_statement"):
                listener.exitPreamble_statement(self)

    def preamble_statement(self):

        localctx = Grammar.Preamble_statementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_preamble_statement)
        try:
            self.state = 535
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 55, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 533
                self.initial_assignment()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 534
                self.constant_definition()
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Initial_assignmentContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def DECLARE_ASSIGN(self):
            return self.getToken(Grammar.DECLARE_ASSIGN, 0)

        def init_expression(self):
            return self.getTypedRuleContext(Grammar.Init_expressionContext, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def getRuleIndex(self):
            return Grammar.RULE_initial_assignment

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterInitial_assignment"):
                listener.enterInitial_assignment(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitInitial_assignment"):
                listener.exitInitial_assignment(self)

    def initial_assignment(self):

        localctx = Grammar.Initial_assignmentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_initial_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 537
            self.match(Grammar.ID)
            self.state = 538
            self.match(Grammar.DECLARE_ASSIGN)
            self.state = 539
            self.init_expression(0)
            self.state = 540
            self.match(Grammar.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Constant_definitionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def ASSIGN(self):
            return self.getToken(Grammar.ASSIGN, 0)

        def init_expression(self):
            return self.getTypedRuleContext(Grammar.Init_expressionContext, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def getRuleIndex(self):
            return Grammar.RULE_constant_definition

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterConstant_definition"):
                listener.enterConstant_definition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitConstant_definition"):
                listener.exitConstant_definition(self)

    def constant_definition(self):

        localctx = Grammar.Constant_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_constant_definition)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 542
            self.match(Grammar.ID)
            self.state = 543
            self.match(Grammar.ASSIGN)
            self.state = 544
            self.init_expression(0)
            self.state = 545
            self.match(Grammar.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Operational_assignmentContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def DECLARE_ASSIGN(self):
            return self.getToken(Grammar.DECLARE_ASSIGN, 0)

        def num_expression(self):
            return self.getTypedRuleContext(Grammar.Num_expressionContext, 0)

        def SEMI(self):
            return self.getToken(Grammar.SEMI, 0)

        def getRuleIndex(self):
            return Grammar.RULE_operational_assignment

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterOperational_assignment"):
                listener.enterOperational_assignment(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitOperational_assignment"):
                listener.exitOperational_assignment(self)

    def operational_assignment(self):

        localctx = Grammar.Operational_assignmentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_operational_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 547
            self.match(Grammar.ID)
            self.state = 548
            self.match(Grammar.DECLARE_ASSIGN)
            self.state = 549
            self.num_expression(0)
            self.state = 550
            self.match(Grammar.SEMI)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Generic_expressionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def num_expression(self):
            return self.getTypedRuleContext(Grammar.Num_expressionContext, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(Grammar.Cond_expressionContext, 0)

        def getRuleIndex(self):
            return Grammar.RULE_generic_expression

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterGeneric_expression"):
                listener.enterGeneric_expression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitGeneric_expression"):
                listener.exitGeneric_expression(self)

    def generic_expression(self):

        localctx = Grammar.Generic_expressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_generic_expression)
        try:
            self.state = 554
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 56, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 552
                self.num_expression(0)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 553
                self.cond_expression(0)
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Init_expressionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return Grammar.RULE_init_expression

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class FuncExprInitContext(Init_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Init_expressionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(Grammar.LPAREN, 0)

        def init_expression(self):
            return self.getTypedRuleContext(Grammar.Init_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(Grammar.RPAREN, 0)

        def UFUNC_NAME(self):
            return self.getToken(Grammar.UFUNC_NAME, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterFuncExprInit"):
                listener.enterFuncExprInit(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitFuncExprInit"):
                listener.exitFuncExprInit(self)

    class UnaryExprInitContext(Init_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Init_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def init_expression(self):
            return self.getTypedRuleContext(Grammar.Init_expressionContext, 0)

        def PLUS(self):
            return self.getToken(Grammar.PLUS, 0)

        def MINUS(self):
            return self.getToken(Grammar.MINUS, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterUnaryExprInit"):
                listener.enterUnaryExprInit(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitUnaryExprInit"):
                listener.exitUnaryExprInit(self)

    class BinaryExprInitContext(Init_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Init_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def init_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Init_expressionContext)
            else:
                return self.getTypedRuleContext(Grammar.Init_expressionContext, i)

        def POW(self):
            return self.getToken(Grammar.POW, 0)

        def STAR(self):
            return self.getToken(Grammar.STAR, 0)

        def SLASH(self):
            return self.getToken(Grammar.SLASH, 0)

        def PERCENT(self):
            return self.getToken(Grammar.PERCENT, 0)

        def PLUS(self):
            return self.getToken(Grammar.PLUS, 0)

        def MINUS(self):
            return self.getToken(Grammar.MINUS, 0)

        def SHIFT_LEFT(self):
            return self.getToken(Grammar.SHIFT_LEFT, 0)

        def SHIFT_RIGHT(self):
            return self.getToken(Grammar.SHIFT_RIGHT, 0)

        def AMP(self):
            return self.getToken(Grammar.AMP, 0)

        def CARET(self):
            return self.getToken(Grammar.CARET, 0)

        def PIPE(self):
            return self.getToken(Grammar.PIPE, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprInit"):
                listener.enterBinaryExprInit(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprInit"):
                listener.exitBinaryExprInit(self)

    class LiteralExprInitContext(Init_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Init_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def num_literal(self):
            return self.getTypedRuleContext(Grammar.Num_literalContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLiteralExprInit"):
                listener.enterLiteralExprInit(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLiteralExprInit"):
                listener.exitLiteralExprInit(self)

    class MathConstExprInitContext(Init_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Init_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def math_const(self):
            return self.getTypedRuleContext(Grammar.Math_constContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterMathConstExprInit"):
                listener.enterMathConstExprInit(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitMathConstExprInit"):
                listener.exitMathConstExprInit(self)

    class ParenExprInitContext(Init_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Init_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(Grammar.LPAREN, 0)

        def init_expression(self):
            return self.getTypedRuleContext(Grammar.Init_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(Grammar.RPAREN, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterParenExprInit"):
                listener.enterParenExprInit(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitParenExprInit"):
                listener.exitParenExprInit(self)

    def init_expression(self, _p: int = 0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = Grammar.Init_expressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 60
        self.enterRecursionRule(localctx, 60, self.RULE_init_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 570
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [Grammar.LPAREN]:
                localctx = Grammar.ParenExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 557
                self.match(Grammar.LPAREN)
                self.state = 558
                self.init_expression(0)
                self.state = 559
                self.match(Grammar.RPAREN)
                pass
            elif token in [Grammar.FLOAT, Grammar.HEX_INT, Grammar.INT]:
                localctx = Grammar.LiteralExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 561
                self.num_literal()
                pass
            elif token in [Grammar.PI_CONST, Grammar.E_CONST, Grammar.TAU_CONST]:
                localctx = Grammar.MathConstExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 562
                self.math_const()
                pass
            elif token in [Grammar.PLUS, Grammar.MINUS]:
                localctx = Grammar.UnaryExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 563
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == Grammar.PLUS or _la == Grammar.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 564
                self.init_expression(9)
                pass
            elif token in [Grammar.UFUNC_NAME]:
                localctx = Grammar.FuncExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 565
                localctx.func_name = self.match(Grammar.UFUNC_NAME)
                self.state = 566
                self.match(Grammar.LPAREN)
                self.state = 567
                self.init_expression(0)
                self.state = 568
                self.match(Grammar.RPAREN)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 595
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 59, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 593
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 58, self._ctx)
                    if la_ == 1:
                        localctx = Grammar.BinaryExprInitContext(
                            self,
                            Grammar.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 572
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 573
                        localctx.op = self.match(Grammar.POW)
                        self.state = 574
                        self.init_expression(8)
                        pass

                    elif la_ == 2:
                        localctx = Grammar.BinaryExprInitContext(
                            self,
                            Grammar.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 575
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 576
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la) & ~0x3F) == 0
                            and (
                                (1 << _la)
                                & (
                                    (1 << Grammar.SLASH)
                                    | (1 << Grammar.STAR)
                                    | (1 << Grammar.PERCENT)
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 577
                        self.init_expression(8)
                        pass

                    elif la_ == 3:
                        localctx = Grammar.BinaryExprInitContext(
                            self,
                            Grammar.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 578
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 579
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (_la == Grammar.PLUS or _la == Grammar.MINUS):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 580
                        self.init_expression(7)
                        pass

                    elif la_ == 4:
                        localctx = Grammar.BinaryExprInitContext(
                            self,
                            Grammar.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 581
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 582
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == Grammar.SHIFT_RIGHT or _la == Grammar.SHIFT_LEFT
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 583
                        self.init_expression(6)
                        pass

                    elif la_ == 5:
                        localctx = Grammar.BinaryExprInitContext(
                            self,
                            Grammar.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 584
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 585
                        localctx.op = self.match(Grammar.AMP)
                        self.state = 586
                        self.init_expression(5)
                        pass

                    elif la_ == 6:
                        localctx = Grammar.BinaryExprInitContext(
                            self,
                            Grammar.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 587
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 588
                        localctx.op = self.match(Grammar.CARET)
                        self.state = 589
                        self.init_expression(4)
                        pass

                    elif la_ == 7:
                        localctx = Grammar.BinaryExprInitContext(
                            self,
                            Grammar.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 590
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 591
                        localctx.op = self.match(Grammar.PIPE)
                        self.state = 592
                        self.init_expression(3)
                        pass

                self.state = 597
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 59, self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx

    class Num_expressionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return Grammar.RULE_num_expression

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class UnaryExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Num_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def num_expression(self):
            return self.getTypedRuleContext(Grammar.Num_expressionContext, 0)

        def PLUS(self):
            return self.getToken(Grammar.PLUS, 0)

        def MINUS(self):
            return self.getToken(Grammar.MINUS, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterUnaryExprNum"):
                listener.enterUnaryExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitUnaryExprNum"):
                listener.exitUnaryExprNum(self)

    class FuncExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Num_expressionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(Grammar.LPAREN, 0)

        def num_expression(self):
            return self.getTypedRuleContext(Grammar.Num_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(Grammar.RPAREN, 0)

        def UFUNC_NAME(self):
            return self.getToken(Grammar.UFUNC_NAME, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterFuncExprNum"):
                listener.enterFuncExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitFuncExprNum"):
                listener.exitFuncExprNum(self)

    class ConditionalCStyleExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(Grammar.LPAREN, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(Grammar.Cond_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(Grammar.RPAREN, 0)

        def QUESTION(self):
            return self.getToken(Grammar.QUESTION, 0)

        def num_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Num_expressionContext)
            else:
                return self.getTypedRuleContext(Grammar.Num_expressionContext, i)

        def COLON(self):
            return self.getToken(Grammar.COLON, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterConditionalCStyleExprNum"):
                listener.enterConditionalCStyleExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitConditionalCStyleExprNum"):
                listener.exitConditionalCStyleExprNum(self)

    class BinaryExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Num_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def num_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Num_expressionContext)
            else:
                return self.getTypedRuleContext(Grammar.Num_expressionContext, i)

        def POW(self):
            return self.getToken(Grammar.POW, 0)

        def STAR(self):
            return self.getToken(Grammar.STAR, 0)

        def SLASH(self):
            return self.getToken(Grammar.SLASH, 0)

        def PERCENT(self):
            return self.getToken(Grammar.PERCENT, 0)

        def PLUS(self):
            return self.getToken(Grammar.PLUS, 0)

        def MINUS(self):
            return self.getToken(Grammar.MINUS, 0)

        def SHIFT_LEFT(self):
            return self.getToken(Grammar.SHIFT_LEFT, 0)

        def SHIFT_RIGHT(self):
            return self.getToken(Grammar.SHIFT_RIGHT, 0)

        def AMP(self):
            return self.getToken(Grammar.AMP, 0)

        def CARET(self):
            return self.getToken(Grammar.CARET, 0)

        def PIPE(self):
            return self.getToken(Grammar.PIPE, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprNum"):
                listener.enterBinaryExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprNum"):
                listener.exitBinaryExprNum(self)

    class LiteralExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def num_literal(self):
            return self.getTypedRuleContext(Grammar.Num_literalContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLiteralExprNum"):
                listener.enterLiteralExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLiteralExprNum"):
                listener.exitLiteralExprNum(self)

    class MathConstExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def math_const(self):
            return self.getTypedRuleContext(Grammar.Math_constContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterMathConstExprNum"):
                listener.enterMathConstExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitMathConstExprNum"):
                listener.exitMathConstExprNum(self)

    class ParenExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(Grammar.LPAREN, 0)

        def num_expression(self):
            return self.getTypedRuleContext(Grammar.Num_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(Grammar.RPAREN, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterParenExprNum"):
                listener.enterParenExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitParenExprNum"):
                listener.exitParenExprNum(self)

    class IdExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ID(self):
            return self.getToken(Grammar.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterIdExprNum"):
                listener.enterIdExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitIdExprNum"):
                listener.exitIdExprNum(self)

    def num_expression(self, _p: int = 0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = Grammar.Num_expressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 62
        self.enterRecursionRule(localctx, 62, self.RULE_num_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 621
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 60, self._ctx)
            if la_ == 1:
                localctx = Grammar.ParenExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 599
                self.match(Grammar.LPAREN)
                self.state = 600
                self.num_expression(0)
                self.state = 601
                self.match(Grammar.RPAREN)
                pass

            elif la_ == 2:
                localctx = Grammar.LiteralExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 603
                self.num_literal()
                pass

            elif la_ == 3:
                localctx = Grammar.IdExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 604
                self.match(Grammar.ID)
                pass

            elif la_ == 4:
                localctx = Grammar.MathConstExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 605
                self.math_const()
                pass

            elif la_ == 5:
                localctx = Grammar.UnaryExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 606
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == Grammar.PLUS or _la == Grammar.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 607
                self.num_expression(10)
                pass

            elif la_ == 6:
                localctx = Grammar.FuncExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 608
                localctx.func_name = self.match(Grammar.UFUNC_NAME)
                self.state = 609
                self.match(Grammar.LPAREN)
                self.state = 610
                self.num_expression(0)
                self.state = 611
                self.match(Grammar.RPAREN)
                pass

            elif la_ == 7:
                localctx = Grammar.ConditionalCStyleExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 613
                self.match(Grammar.LPAREN)
                self.state = 614
                self.cond_expression(0)
                self.state = 615
                self.match(Grammar.RPAREN)
                self.state = 616
                self.match(Grammar.QUESTION)
                self.state = 617
                self.num_expression(0)
                self.state = 618
                self.match(Grammar.COLON)
                self.state = 619
                self.num_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 646
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 62, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 644
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 61, self._ctx)
                    if la_ == 1:
                        localctx = Grammar.BinaryExprNumContext(
                            self,
                            Grammar.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 623
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 9)"
                            )
                        self.state = 624
                        localctx.op = self.match(Grammar.POW)
                        self.state = 625
                        self.num_expression(9)
                        pass

                    elif la_ == 2:
                        localctx = Grammar.BinaryExprNumContext(
                            self,
                            Grammar.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 626
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 627
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la) & ~0x3F) == 0
                            and (
                                (1 << _la)
                                & (
                                    (1 << Grammar.SLASH)
                                    | (1 << Grammar.STAR)
                                    | (1 << Grammar.PERCENT)
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 628
                        self.num_expression(9)
                        pass

                    elif la_ == 3:
                        localctx = Grammar.BinaryExprNumContext(
                            self,
                            Grammar.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 629
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 630
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (_la == Grammar.PLUS or _la == Grammar.MINUS):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 631
                        self.num_expression(8)
                        pass

                    elif la_ == 4:
                        localctx = Grammar.BinaryExprNumContext(
                            self,
                            Grammar.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 632
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 633
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == Grammar.SHIFT_RIGHT or _la == Grammar.SHIFT_LEFT
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 634
                        self.num_expression(7)
                        pass

                    elif la_ == 5:
                        localctx = Grammar.BinaryExprNumContext(
                            self,
                            Grammar.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 635
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 636
                        localctx.op = self.match(Grammar.AMP)
                        self.state = 637
                        self.num_expression(6)
                        pass

                    elif la_ == 6:
                        localctx = Grammar.BinaryExprNumContext(
                            self,
                            Grammar.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 638
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 639
                        localctx.op = self.match(Grammar.CARET)
                        self.state = 640
                        self.num_expression(5)
                        pass

                    elif la_ == 7:
                        localctx = Grammar.BinaryExprNumContext(
                            self,
                            Grammar.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 641
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 642
                        localctx.op = self.match(Grammar.PIPE)
                        self.state = 643
                        self.num_expression(4)
                        pass

                self.state = 648
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 62, self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx

    class Cond_expressionContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def getRuleIndex(self):
            return Grammar.RULE_cond_expression

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class BinaryExprFromCondCondContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Cond_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Cond_expressionContext)
            else:
                return self.getTypedRuleContext(Grammar.Cond_expressionContext, i)

        def EQ(self):
            return self.getToken(Grammar.EQ, 0)

        def NE(self):
            return self.getToken(Grammar.NE, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprFromCondCond"):
                listener.enterBinaryExprFromCondCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprFromCondCond"):
                listener.exitBinaryExprFromCondCond(self)

    class BinaryExprCondContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Cond_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Cond_expressionContext)
            else:
                return self.getTypedRuleContext(Grammar.Cond_expressionContext, i)

        def LOGICAL_AND(self):
            return self.getToken(Grammar.LOGICAL_AND, 0)

        def AND_KW(self):
            return self.getToken(Grammar.AND_KW, 0)

        def LOGICAL_OR(self):
            return self.getToken(Grammar.LOGICAL_OR, 0)

        def OR_KW(self):
            return self.getToken(Grammar.OR_KW, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprCond"):
                listener.enterBinaryExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprCond"):
                listener.exitBinaryExprCond(self)

    class BinaryExprFromNumCondContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Cond_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def num_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Num_expressionContext)
            else:
                return self.getTypedRuleContext(Grammar.Num_expressionContext, i)

        def LT(self):
            return self.getToken(Grammar.LT, 0)

        def GT(self):
            return self.getToken(Grammar.GT, 0)

        def LE(self):
            return self.getToken(Grammar.LE, 0)

        def GE(self):
            return self.getToken(Grammar.GE, 0)

        def EQ(self):
            return self.getToken(Grammar.EQ, 0)

        def NE(self):
            return self.getToken(Grammar.NE, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprFromNumCond"):
                listener.enterBinaryExprFromNumCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprFromNumCond"):
                listener.exitBinaryExprFromNumCond(self)

    class UnaryExprCondContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Cond_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def cond_expression(self):
            return self.getTypedRuleContext(Grammar.Cond_expressionContext, 0)

        def BANG(self):
            return self.getToken(Grammar.BANG, 0)

        def NOT_KW(self):
            return self.getToken(Grammar.NOT_KW, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterUnaryExprCond"):
                listener.enterUnaryExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitUnaryExprCond"):
                listener.exitUnaryExprCond(self)

    class ParenExprCondContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Cond_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(Grammar.LPAREN, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(Grammar.Cond_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(Grammar.RPAREN, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterParenExprCond"):
                listener.enterParenExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitParenExprCond"):
                listener.exitParenExprCond(self)

    class LiteralExprCondContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Cond_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def bool_literal(self):
            return self.getTypedRuleContext(Grammar.Bool_literalContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLiteralExprCond"):
                listener.enterLiteralExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLiteralExprCond"):
                listener.exitLiteralExprCond(self)

    class ConditionalCStyleCondNumContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a Grammar.Cond_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(Grammar.LPAREN, 0)

        def cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(Grammar.Cond_expressionContext)
            else:
                return self.getTypedRuleContext(Grammar.Cond_expressionContext, i)

        def RPAREN(self):
            return self.getToken(Grammar.RPAREN, 0)

        def QUESTION(self):
            return self.getToken(Grammar.QUESTION, 0)

        def COLON(self):
            return self.getToken(Grammar.COLON, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterConditionalCStyleCondNum"):
                listener.enterConditionalCStyleCondNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitConditionalCStyleCondNum"):
                listener.exitConditionalCStyleCondNum(self)

    def cond_expression(self, _p: int = 0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = Grammar.Cond_expressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 64
        self.enterRecursionRule(localctx, 64, self.RULE_cond_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 673
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 63, self._ctx)
            if la_ == 1:
                localctx = Grammar.ParenExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 650
                self.match(Grammar.LPAREN)
                self.state = 651
                self.cond_expression(0)
                self.state = 652
                self.match(Grammar.RPAREN)
                pass

            elif la_ == 2:
                localctx = Grammar.LiteralExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 654
                self.bool_literal()
                pass

            elif la_ == 3:
                localctx = Grammar.UnaryExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 655
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == Grammar.NOT_KW or _la == Grammar.BANG):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 656
                self.cond_expression(7)
                pass

            elif la_ == 4:
                localctx = Grammar.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 657
                self.num_expression(0)
                self.state = 658
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (
                    ((_la) & ~0x3F) == 0
                    and (
                        (1 << _la)
                        & (
                            (1 << Grammar.LE)
                            | (1 << Grammar.GE)
                            | (1 << Grammar.LT)
                            | (1 << Grammar.GT)
                        )
                    )
                    != 0
                ):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 659
                self.num_expression(0)
                pass

            elif la_ == 5:
                localctx = Grammar.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 661
                self.num_expression(0)
                self.state = 662
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == Grammar.EQ or _la == Grammar.NE):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 663
                self.num_expression(0)
                pass

            elif la_ == 6:
                localctx = Grammar.ConditionalCStyleCondNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 665
                self.match(Grammar.LPAREN)
                self.state = 666
                self.cond_expression(0)
                self.state = 667
                self.match(Grammar.RPAREN)
                self.state = 668
                self.match(Grammar.QUESTION)
                self.state = 669
                self.cond_expression(0)
                self.state = 670
                self.match(Grammar.COLON)
                self.state = 671
                self.cond_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 686
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 65, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 684
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 64, self._ctx)
                    if la_ == 1:
                        localctx = Grammar.BinaryExprFromCondCondContext(
                            self,
                            Grammar.Cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_cond_expression
                        )
                        self.state = 675
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 676
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (_la == Grammar.EQ or _la == Grammar.NE):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 677
                        self.cond_expression(5)
                        pass

                    elif la_ == 2:
                        localctx = Grammar.BinaryExprCondContext(
                            self,
                            Grammar.Cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_cond_expression
                        )
                        self.state = 678
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 679
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (_la == Grammar.AND_KW or _la == Grammar.LOGICAL_AND):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 680
                        self.cond_expression(4)
                        pass

                    elif la_ == 3:
                        localctx = Grammar.BinaryExprCondContext(
                            self,
                            Grammar.Cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_cond_expression
                        )
                        self.state = 681
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 682
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (_la == Grammar.OR_KW or _la == Grammar.LOGICAL_OR):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 683
                        self.cond_expression(3)
                        pass

                self.state = 688
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 65, self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx

    class Num_literalContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def INT(self):
            return self.getToken(Grammar.INT, 0)

        def FLOAT(self):
            return self.getToken(Grammar.FLOAT, 0)

        def HEX_INT(self):
            return self.getToken(Grammar.HEX_INT, 0)

        def getRuleIndex(self):
            return Grammar.RULE_num_literal

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterNum_literal"):
                listener.enterNum_literal(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitNum_literal"):
                listener.exitNum_literal(self)

    def num_literal(self):

        localctx = Grammar.Num_literalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 66, self.RULE_num_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 689
            _la = self._input.LA(1)
            if not (
                ((_la - 62) & ~0x3F) == 0
                and (
                    (1 << (_la - 62))
                    & (
                        (1 << (Grammar.FLOAT - 62))
                        | (1 << (Grammar.HEX_INT - 62))
                        | (1 << (Grammar.INT - 62))
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
            return self.getToken(Grammar.TRUE, 0)

        def FALSE(self):
            return self.getToken(Grammar.FALSE, 0)

        def getRuleIndex(self):
            return Grammar.RULE_bool_literal

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBool_literal"):
                listener.enterBool_literal(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBool_literal"):
                listener.exitBool_literal(self)

    def bool_literal(self):

        localctx = Grammar.Bool_literalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 68, self.RULE_bool_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 691
            _la = self._input.LA(1)
            if not (_la == Grammar.TRUE or _la == Grammar.FALSE):
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
            return self.getToken(Grammar.PI_CONST, 0)

        def E_CONST(self):
            return self.getToken(Grammar.E_CONST, 0)

        def TAU_CONST(self):
            return self.getToken(Grammar.TAU_CONST, 0)

        def getRuleIndex(self):
            return Grammar.RULE_math_const

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterMath_const"):
                listener.enterMath_const(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitMath_const"):
                listener.exitMath_const(self)

    def math_const(self):

        localctx = Grammar.Math_constContext(self, self._ctx, self.state)
        self.enterRule(localctx, 70, self.RULE_math_const)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 693
            _la = self._input.LA(1)
            if not (
                ((_la) & ~0x3F) == 0
                and (
                    (1 << _la)
                    & (
                        (1 << Grammar.PI_CONST)
                        | (1 << Grammar.E_CONST)
                        | (1 << Grammar.TAU_CONST)
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

    class Chain_idContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser
            self.isabs = None  # Token

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(Grammar.ID)
            else:
                return self.getToken(Grammar.ID, i)

        def DOT(self, i: int = None):
            if i is None:
                return self.getTokens(Grammar.DOT)
            else:
                return self.getToken(Grammar.DOT, i)

        def SLASH(self):
            return self.getToken(Grammar.SLASH, 0)

        def getRuleIndex(self):
            return Grammar.RULE_chain_id

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterChain_id"):
                listener.enterChain_id(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitChain_id"):
                listener.exitChain_id(self)

    def chain_id(self):

        localctx = Grammar.Chain_idContext(self, self._ctx, self.state)
        self.enterRule(localctx, 72, self.RULE_chain_id)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 696
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == Grammar.SLASH:
                self.state = 695
                localctx.isabs = self.match(Grammar.SLASH)

            self.state = 698
            self.match(Grammar.ID)
            self.state = 703
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == Grammar.DOT:
                self.state = 699
                self.match(Grammar.DOT)
                self.state = 700
                self.match(Grammar.ID)
                self.state = 705
                self._errHandler.sync(self)
                _la = self._input.LA(1)

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
        self._predicates[30] = self.init_expression_sempred
        self._predicates[31] = self.num_expression_sempred
        self._predicates[32] = self.cond_expression_sempred
        pred = self._predicates.get(ruleIndex, None)
        if pred is None:
            raise Exception("No predicate with index:" + str(ruleIndex))
        else:
            return pred(localctx, predIndex)

    def init_expression_sempred(self, localctx: Init_expressionContext, predIndex: int):
        if predIndex == 0:
            return self.precpred(self._ctx, 8)

        if predIndex == 1:
            return self.precpred(self._ctx, 7)

        if predIndex == 2:
            return self.precpred(self._ctx, 6)

        if predIndex == 3:
            return self.precpred(self._ctx, 5)

        if predIndex == 4:
            return self.precpred(self._ctx, 4)

        if predIndex == 5:
            return self.precpred(self._ctx, 3)

        if predIndex == 6:
            return self.precpred(self._ctx, 2)

    def num_expression_sempred(self, localctx: Num_expressionContext, predIndex: int):
        if predIndex == 7:
            return self.precpred(self._ctx, 9)

        if predIndex == 8:
            return self.precpred(self._ctx, 8)

        if predIndex == 9:
            return self.precpred(self._ctx, 7)

        if predIndex == 10:
            return self.precpred(self._ctx, 6)

        if predIndex == 11:
            return self.precpred(self._ctx, 5)

        if predIndex == 12:
            return self.precpred(self._ctx, 4)

        if predIndex == 13:
            return self.precpred(self._ctx, 3)

    def cond_expression_sempred(self, localctx: Cond_expressionContext, predIndex: int):
        if predIndex == 14:
            return self.precpred(self._ctx, 4)

        if predIndex == 15:
            return self.precpred(self._ctx, 3)

        if predIndex == 16:
            return self.precpred(self._ctx, 2)
