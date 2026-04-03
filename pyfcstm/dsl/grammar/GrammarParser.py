# Generated from ./pyfcstm/dsl/grammar/GrammarParser.g4 by ANTLR 4.9.3
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
        buf.write("\u02be\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7")
        buf.write("\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r\4\16")
        buf.write("\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23\t\23")
        buf.write("\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30\4\31")
        buf.write("\t\31\4\32\t\32\4\33\t\33\4\34\t\34\4\35\t\35\4\36\t\36")
        buf.write('\4\37\t\37\4 \t \4!\t!\4"\t"\4#\t#\4$\t$\4%\t%\4&\t')
        buf.write("&\3\2\3\2\3\2\3\3\7\3Q\n\3\f\3\16\3T\13\3\3\3\3\3\3\3")
        buf.write("\3\4\3\4\3\4\3\4\3\4\3\4\3\4\3\5\5\5a\n\5\3\5\3\5\3\5")
        buf.write("\3\5\5\5g\n\5\3\5\3\5\5\5k\n\5\3\5\3\5\3\5\3\5\5\5q\n")
        buf.write("\5\3\5\3\5\7\5u\n\5\f\5\16\5x\13\5\3\5\5\5{\n\5\3\6\3")
        buf.write("\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u0088\n\6\3")
        buf.write("\6\3\6\3\6\3\6\3\6\3\6\5\6\u0090\n\6\3\6\3\6\3\6\3\6\3")
        buf.write("\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u009f\n\6\3\6\3")
        buf.write("\6\3\6\3\6\3\6\3\6\5\6\u00a7\n\6\3\6\3\6\3\6\3\6\3\6\3")
        buf.write("\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u00b6\n\6\3\6\3\6\3")
        buf.write("\6\3\6\3\6\3\6\5\6\u00be\n\6\5\6\u00c0\n\6\3\7\3\7\3\7")
        buf.write("\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\5\7\u00d0")
        buf.write("\n\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3")
        buf.write("\7\3\7\3\7\5\7\u00e1\n\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3")
        buf.write("\7\3\7\3\7\3\7\3\7\3\7\5\7\u00f0\n\7\3\7\3\7\3\7\3\7\3")
        buf.write("\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\5\7\u00ff\n\7\3\7\5")
        buf.write("\7\u0102\n\7\3\b\3\b\5\b\u0106\n\b\3\b\3\b\3\b\3\b\3\b")
        buf.write("\3\b\3\b\3\b\3\b\3\b\3\b\5\b\u0113\n\b\3\b\3\b\3\b\5\b")
        buf.write("\u0118\n\b\3\b\3\b\3\b\3\b\5\b\u011e\n\b\3\t\3\t\5\t\u0122")
        buf.write("\n\t\3\t\3\t\3\t\3\t\3\t\3\t\3\t\3\t\3\t\3\t\3\t\5\t\u012f")
        buf.write("\n\t\3\t\3\t\3\t\5\t\u0134\n\t\3\t\3\t\3\t\3\t\5\t\u013a")
        buf.write("\n\t\3\n\3\n\5\n\u013e\n\n\3\n\5\n\u0141\n\n\3\n\3\n\3")
        buf.write("\n\3\n\3\n\3\n\5\n\u0149\n\n\3\n\3\n\3\n\3\n\3\n\5\n\u0150")
        buf.write("\n\n\3\n\3\n\5\n\u0154\n\n\3\n\3\n\3\n\5\n\u0159\n\n\3")
        buf.write("\n\5\n\u015c\n\n\3\n\3\n\3\n\3\n\5\n\u0162\n\n\3\13\3")
        buf.write("\13\3\13\3\13\5\13\u0168\n\13\3\13\3\13\3\13\3\13\3\13")
        buf.write("\3\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13\5\13")
        buf.write("\u0179\n\13\3\13\3\13\3\13\3\13\3\13\5\13\u0180\n\13\3")
        buf.write("\13\3\13\3\13\3\13\5\13\u0186\n\13\3\f\3\f\3\f\3\f\5\f")
        buf.write("\u018c\n\f\3\f\3\f\3\r\3\r\3\r\3\r\3\r\3\r\5\r\u0196\n")
        buf.write("\r\3\r\3\r\7\r\u019a\n\r\f\r\16\r\u019d\13\r\3\r\3\r\5")
        buf.write("\r\u01a1\n\r\3\16\3\16\3\16\5\16\u01a6\n\16\3\17\3\17")
        buf.write("\3\17\3\17\3\17\3\17\3\20\3\20\3\20\3\20\3\20\7\20\u01b3")
        buf.write("\n\20\f\20\16\20\u01b6\13\20\3\20\3\20\3\20\5\20\u01bb")
        buf.write("\n\20\3\21\3\21\3\21\5\21\u01c0\n\21\3\22\3\22\3\22\3")
        buf.write("\22\3\22\3\22\5\22\u01c8\n\22\3\22\3\22\3\23\3\23\3\23")
        buf.write("\3\23\3\23\3\24\3\24\3\24\3\24\3\25\3\25\3\25\3\25\3\25")
        buf.write("\3\25\3\25\3\25\3\25\3\25\3\25\3\25\7\25\u01e1\n\25\f")
        buf.write("\25\16\25\u01e4\13\25\3\25\3\25\5\25\u01e8\n\25\3\26\3")
        buf.write("\26\3\26\5\26\u01ed\n\26\3\27\7\27\u01f0\n\27\f\27\16")
        buf.write("\27\u01f3\13\27\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30")
        buf.write("\3\30\3\30\5\30\u01ff\n\30\3\31\7\31\u0202\n\31\f\31\16")
        buf.write("\31\u0205\13\31\3\31\3\31\3\32\7\32\u020a\n\32\f\32\16")
        buf.write("\32\u020d\13\32\3\32\3\32\3\33\3\33\5\33\u0213\n\33\3")
        buf.write("\34\3\34\3\34\3\34\3\34\3\35\3\35\3\35\3\35\3\35\3\36")
        buf.write("\3\36\3\36\3\36\3\36\3\37\3\37\5\37\u0226\n\37\3 \3 \3")
        buf.write(" \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \5 \u0236\n \3 \3 \3")
        buf.write(" \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3")
        buf.write(" \7 \u024d\n \f \16 \u0250\13 \3!\3!\3!\3!\3!\3!\3!\3")
        buf.write("!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\5!\u0269")
        buf.write("\n!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3")
        buf.write('!\3!\3!\3!\3!\7!\u0280\n!\f!\16!\u0283\13!\3"\3"\3"')
        buf.write('\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3')
        buf.write('"\3"\3"\3"\3"\3"\3"\3"\5"\u029d\n"\3"\3"\3')
        buf.write('"\3"\3"\3"\3"\3"\3"\7"\u02a8\n"\f"\16"\u02ab')
        buf.write('\13"\3#\3#\3$\3$\3%\3%\3&\5&\u02b4\n&\3&\3&\3&\7&\u02b9')
        buf.write("\n&\f&\16&\u02bc\13&\3&\2\5>@B'\2\4\6\b\n\f\16\20\22")
        buf.write('\24\26\30\32\34\36 "$&(*,.\60\62\64\668:<>@BDFHJ\2\20')
        buf.write("\3\2\24\25\4\2''\62\62\3\2\r\16\3\2\678\4\2\64\6599")
        buf.write('\3\2\36\37\4\2\33\33\66\66\4\2 !=>\3\2"#\4\2\31\31$$')
        buf.write("\4\2\32\32%%\3\2@B\3\2CD\3\2\26\30\2\u0316\2L\3\2\2\2")
        buf.write("\4R\3\2\2\2\6X\3\2\2\2\bz\3\2\2\2\n\u00bf\3\2\2\2\f\u0101")
        buf.write("\3\2\2\2\16\u011d\3\2\2\2\20\u0139\3\2\2\2\22\u0161\3")
        buf.write("\2\2\2\24\u0185\3\2\2\2\26\u0187\3\2\2\2\30\u018f\3\2")
        buf.write("\2\2\32\u01a5\3\2\2\2\34\u01a7\3\2\2\2\36\u01ba\3\2\2")
        buf.write('\2 \u01bf\3\2\2\2"\u01c1\3\2\2\2$\u01cb\3\2\2\2&\u01d0')
        buf.write("\3\2\2\2(\u01d4\3\2\2\2*\u01ec\3\2\2\2,\u01f1\3\2\2\2")
        buf.write(".\u01fe\3\2\2\2\60\u0203\3\2\2\2\62\u020b\3\2\2\2\64\u0212")
        buf.write("\3\2\2\2\66\u0214\3\2\2\28\u0219\3\2\2\2:\u021e\3\2\2")
        buf.write("\2<\u0225\3\2\2\2>\u0235\3\2\2\2@\u0268\3\2\2\2B\u029c")
        buf.write("\3\2\2\2D\u02ac\3\2\2\2F\u02ae\3\2\2\2H\u02b0\3\2\2\2")
        buf.write('J\u02b3\3\2\2\2LM\5B"\2MN\7\2\2\3N\3\3\2\2\2OQ\5\6\4')
        buf.write("\2PO\3\2\2\2QT\3\2\2\2RP\3\2\2\2RS\3\2\2\2SU\3\2\2\2T")
        buf.write("R\3\2\2\2UV\5\b\5\2VW\7\2\2\3W\5\3\2\2\2XY\7\4\2\2YZ\t")
        buf.write("\2\2\2Z[\7F\2\2[\\\7?\2\2\\]\5> \2]^\7)\2\2^\7\3\2\2\2")
        buf.write("_a\7\b\2\2`_\3\2\2\2`a\3\2\2\2ab\3\2\2\2bc\7\t\2\2cf\7")
        buf.write("F\2\2de\7\7\2\2eg\7G\2\2fd\3\2\2\2fg\3\2\2\2gh\3\2\2\2")
        buf.write("h{\7)\2\2ik\7\b\2\2ji\3\2\2\2jk\3\2\2\2kl\3\2\2\2lm\7")
        buf.write("\t\2\2mp\7F\2\2no\7\7\2\2oq\7G\2\2pn\3\2\2\2pq\3\2\2\2")
        buf.write("qr\3\2\2\2rv\7+\2\2su\5.\30\2ts\3\2\2\2ux\3\2\2\2vt\3")
        buf.write("\2\2\2vw\3\2\2\2wy\3\2\2\2xv\3\2\2\2y{\7,\2\2z`\3\2\2")
        buf.write("\2zj\3\2\2\2{\t\3\2\2\2|}\7\34\2\2}~\7(\2\2~\u0087\7F")
        buf.write("\2\2\177\u0080\t\3\2\2\u0080\u0088\5J&\2\u0081\u0082\7")
        buf.write("\62\2\2\u0082\u0083\7\22\2\2\u0083\u0084\7-\2\2\u0084")
        buf.write('\u0085\5B"\2\u0085\u0086\7.\2\2\u0086\u0088\3\2\2\2\u0087')
        buf.write("\177\3\2\2\2\u0087\u0081\3\2\2\2\u0087\u0088\3\2\2\2\u0088")
        buf.write("\u008f\3\2\2\2\u0089\u0090\7)\2\2\u008a\u008b\7\21\2\2")
        buf.write("\u008b\u008c\7+\2\2\u008c\u008d\5,\27\2\u008d\u008e\7")
        buf.write(",\2\2\u008e\u0090\3\2\2\2\u008f\u0089\3\2\2\2\u008f\u008a")
        buf.write("\3\2\2\2\u0090\u00c0\3\2\2\2\u0091\u0092\7F\2\2\u0092")
        buf.write("\u0093\7(\2\2\u0093\u009e\7F\2\2\u0094\u0095\7'\2\2\u0095")
        buf.write("\u009f\7F\2\2\u0096\u0097\7\62\2\2\u0097\u009f\5J&\2\u0098")
        buf.write("\u0099\7\62\2\2\u0099\u009a\7\22\2\2\u009a\u009b\7-\2")
        buf.write('\2\u009b\u009c\5B"\2\u009c\u009d\7.\2\2\u009d\u009f\3')
        buf.write("\2\2\2\u009e\u0094\3\2\2\2\u009e\u0096\3\2\2\2\u009e\u0098")
        buf.write("\3\2\2\2\u009e\u009f\3\2\2\2\u009f\u00a6\3\2\2\2\u00a0")
        buf.write("\u00a7\7)\2\2\u00a1\u00a2\7\21\2\2\u00a2\u00a3\7+\2\2")
        buf.write("\u00a3\u00a4\5,\27\2\u00a4\u00a5\7,\2\2\u00a5\u00a7\3")
        buf.write("\2\2\2\u00a6\u00a0\3\2\2\2\u00a6\u00a1\3\2\2\2\u00a7\u00c0")
        buf.write("\3\2\2\2\u00a8\u00a9\7F\2\2\u00a9\u00aa\7(\2\2\u00aa\u00b5")
        buf.write("\7\34\2\2\u00ab\u00ac\7'\2\2\u00ac\u00b6\7F\2\2\u00ad")
        buf.write("\u00ae\7\62\2\2\u00ae\u00b6\5J&\2\u00af\u00b0\7\62\2\2")
        buf.write("\u00b0\u00b1\7\22\2\2\u00b1\u00b2\7-\2\2\u00b2\u00b3\5")
        buf.write('B"\2\u00b3\u00b4\7.\2\2\u00b4\u00b6\3\2\2\2\u00b5\u00ab')
        buf.write("\3\2\2\2\u00b5\u00ad\3\2\2\2\u00b5\u00af\3\2\2\2\u00b5")
        buf.write("\u00b6\3\2\2\2\u00b6\u00bd\3\2\2\2\u00b7\u00be\7)\2\2")
        buf.write("\u00b8\u00b9\7\21\2\2\u00b9\u00ba\7+\2\2\u00ba\u00bb\5")
        buf.write(",\27\2\u00bb\u00bc\7,\2\2\u00bc\u00be\3\2\2\2\u00bd\u00b7")
        buf.write("\3\2\2\2\u00bd\u00b8\3\2\2\2\u00be\u00c0\3\2\2\2\u00bf")
        buf.write("|\3\2\2\2\u00bf\u0091\3\2\2\2\u00bf\u00a8\3\2\2\2\u00c0")
        buf.write("\13\3\2\2\2\u00c1\u00c2\7\66\2\2\u00c2\u00c3\7F\2\2\u00c3")
        buf.write("\u00c4\7(\2\2\u00c4\u00cf\7F\2\2\u00c5\u00c6\7'\2\2\u00c6")
        buf.write("\u00d0\7F\2\2\u00c7\u00c8\7\62\2\2\u00c8\u00d0\5J&\2\u00c9")
        buf.write("\u00ca\7\62\2\2\u00ca\u00cb\7\22\2\2\u00cb\u00cc\7-\2")
        buf.write('\2\u00cc\u00cd\5B"\2\u00cd\u00ce\7.\2\2\u00ce\u00d0\3')
        buf.write("\2\2\2\u00cf\u00c5\3\2\2\2\u00cf\u00c7\3\2\2\2\u00cf\u00c9")
        buf.write("\3\2\2\2\u00cf\u00d0\3\2\2\2\u00d0\u00d1\3\2\2\2\u00d1")
        buf.write("\u0102\7)\2\2\u00d2\u00d3\7\66\2\2\u00d3\u00d4\7F\2\2")
        buf.write("\u00d4\u00d5\7(\2\2\u00d5\u00e0\7\34\2\2\u00d6\u00d7\7")
        buf.write("'\2\2\u00d7\u00e1\7F\2\2\u00d8\u00d9\7\62\2\2\u00d9\u00e1")
        buf.write("\5J&\2\u00da\u00db\7\62\2\2\u00db\u00dc\7\22\2\2\u00dc")
        buf.write('\u00dd\7-\2\2\u00dd\u00de\5B"\2\u00de\u00df\7.\2\2\u00df')
        buf.write("\u00e1\3\2\2\2\u00e0\u00d6\3\2\2\2\u00e0\u00d8\3\2\2\2")
        buf.write("\u00e0\u00da\3\2\2\2\u00e0\u00e1\3\2\2\2\u00e1\u00e2\3")
        buf.write("\2\2\2\u00e2\u0102\7)\2\2\u00e3\u00e4\7\66\2\2\u00e4\u00e5")
        buf.write("\7\65\2\2\u00e5\u00e6\7(\2\2\u00e6\u00ef\7F\2\2\u00e7")
        buf.write("\u00e8\t\3\2\2\u00e8\u00f0\5J&\2\u00e9\u00ea\7\62\2\2")
        buf.write("\u00ea\u00eb\7\22\2\2\u00eb\u00ec\7-\2\2\u00ec\u00ed\5")
        buf.write('B"\2\u00ed\u00ee\7.\2\2\u00ee\u00f0\3\2\2\2\u00ef\u00e7')
        buf.write("\3\2\2\2\u00ef\u00e9\3\2\2\2\u00ef\u00f0\3\2\2\2\u00f0")
        buf.write("\u00f1\3\2\2\2\u00f1\u0102\7)\2\2\u00f2\u00f3\7\66\2\2")
        buf.write("\u00f3\u00f4\7\65\2\2\u00f4\u00f5\7(\2\2\u00f5\u00fe\7")
        buf.write("\34\2\2\u00f6\u00f7\t\3\2\2\u00f7\u00ff\5J&\2\u00f8\u00f9")
        buf.write("\7\62\2\2\u00f9\u00fa\7\22\2\2\u00fa\u00fb\7-\2\2\u00fb")
        buf.write('\u00fc\5B"\2\u00fc\u00fd\7.\2\2\u00fd\u00ff\3\2\2\2\u00fe')
        buf.write("\u00f6\3\2\2\2\u00fe\u00f8\3\2\2\2\u00fe\u00ff\3\2\2\2")
        buf.write("\u00ff\u0100\3\2\2\2\u0100\u0102\7)\2\2\u0101\u00c1\3")
        buf.write("\2\2\2\u0101\u00d2\3\2\2\2\u0101\u00e3\3\2\2\2\u0101\u00f2")
        buf.write("\3\2\2\2\u0102\r\3\2\2\2\u0103\u0105\7\n\2\2\u0104\u0106")
        buf.write("\7F\2\2\u0105\u0104\3\2\2\2\u0105\u0106\3\2\2\2\u0106")
        buf.write("\u0107\3\2\2\2\u0107\u0108\7+\2\2\u0108\u0109\5,\27\2")
        buf.write("\u0109\u010a\7,\2\2\u010a\u011e\3\2\2\2\u010b\u010c\7")
        buf.write("\n\2\2\u010c\u010d\7\17\2\2\u010d\u010e\7F\2\2\u010e\u011e")
        buf.write("\7)\2\2\u010f\u0110\7\n\2\2\u0110\u0112\7\17\2\2\u0111")
        buf.write("\u0113\7F\2\2\u0112\u0111\3\2\2\2\u0112\u0113\3\2\2\2")
        buf.write("\u0113\u0114\3\2\2\2\u0114\u011e\7H\2\2\u0115\u0117\7")
        buf.write("\n\2\2\u0116\u0118\7F\2\2\u0117\u0116\3\2\2\2\u0117\u0118")
        buf.write("\3\2\2\2\u0118\u0119\3\2\2\2\u0119\u011a\7\20\2\2\u011a")
        buf.write("\u011b\5J&\2\u011b\u011c\7)\2\2\u011c\u011e\3\2\2\2\u011d")
        buf.write("\u0103\3\2\2\2\u011d\u010b\3\2\2\2\u011d\u010f\3\2\2\2")
        buf.write("\u011d\u0115\3\2\2\2\u011e\17\3\2\2\2\u011f\u0121\7\13")
        buf.write("\2\2\u0120\u0122\7F\2\2\u0121\u0120\3\2\2\2\u0121\u0122")
        buf.write("\3\2\2\2\u0122\u0123\3\2\2\2\u0123\u0124\7+\2\2\u0124")
        buf.write("\u0125\5,\27\2\u0125\u0126\7,\2\2\u0126\u013a\3\2\2\2")
        buf.write("\u0127\u0128\7\13\2\2\u0128\u0129\7\17\2\2\u0129\u012a")
        buf.write("\7F\2\2\u012a\u013a\7)\2\2\u012b\u012c\7\13\2\2\u012c")
        buf.write("\u012e\7\17\2\2\u012d\u012f\7F\2\2\u012e\u012d\3\2\2\2")
        buf.write("\u012e\u012f\3\2\2\2\u012f\u0130\3\2\2\2\u0130\u013a\7")
        buf.write("H\2\2\u0131\u0133\7\13\2\2\u0132\u0134\7F\2\2\u0133\u0132")
        buf.write("\3\2\2\2\u0133\u0134\3\2\2\2\u0134\u0135\3\2\2\2\u0135")
        buf.write("\u0136\7\20\2\2\u0136\u0137\5J&\2\u0137\u0138\7)\2\2\u0138")
        buf.write("\u013a\3\2\2\2\u0139\u011f\3\2\2\2\u0139\u0127\3\2\2\2")
        buf.write("\u0139\u012b\3\2\2\2\u0139\u0131\3\2\2\2\u013a\21\3\2")
        buf.write("\2\2\u013b\u013d\7\f\2\2\u013c\u013e\t\4\2\2\u013d\u013c")
        buf.write("\3\2\2\2\u013d\u013e\3\2\2\2\u013e\u0140\3\2\2\2\u013f")
        buf.write("\u0141\7F\2\2\u0140\u013f\3\2\2\2\u0140\u0141\3\2\2\2")
        buf.write("\u0141\u0142\3\2\2\2\u0142\u0143\7+\2\2\u0143\u0144\5")
        buf.write(",\27\2\u0144\u0145\7,\2\2\u0145\u0162\3\2\2\2\u0146\u0148")
        buf.write("\7\f\2\2\u0147\u0149\t\4\2\2\u0148\u0147\3\2\2\2\u0148")
        buf.write("\u0149\3\2\2\2\u0149\u014a\3\2\2\2\u014a\u014b\7\17\2")
        buf.write("\2\u014b\u014c\7F\2\2\u014c\u0162\7)\2\2\u014d\u014f\7")
        buf.write("\f\2\2\u014e\u0150\t\4\2\2\u014f\u014e\3\2\2\2\u014f\u0150")
        buf.write("\3\2\2\2\u0150\u0151\3\2\2\2\u0151\u0153\7\17\2\2\u0152")
        buf.write("\u0154\7F\2\2\u0153\u0152\3\2\2\2\u0153\u0154\3\2\2\2")
        buf.write("\u0154\u0155\3\2\2\2\u0155\u0162\7H\2\2\u0156\u0158\7")
        buf.write("\f\2\2\u0157\u0159\t\4\2\2\u0158\u0157\3\2\2\2\u0158\u0159")
        buf.write("\3\2\2\2\u0159\u015b\3\2\2\2\u015a\u015c\7F\2\2\u015b")
        buf.write("\u015a\3\2\2\2\u015b\u015c\3\2\2\2\u015c\u015d\3\2\2\2")
        buf.write("\u015d\u015e\7\20\2\2\u015e\u015f\5J&\2\u015f\u0160\7")
        buf.write(")\2\2\u0160\u0162\3\2\2\2\u0161\u013b\3\2\2\2\u0161\u0146")
        buf.write("\3\2\2\2\u0161\u014d\3\2\2\2\u0161\u0156\3\2\2\2\u0162")
        buf.write("\23\3\2\2\2\u0163\u0164\7\36\2\2\u0164\u0165\7\f\2\2\u0165")
        buf.write("\u0167\t\4\2\2\u0166\u0168\7F\2\2\u0167\u0166\3\2\2\2")
        buf.write("\u0167\u0168\3\2\2\2\u0168\u0169\3\2\2\2\u0169\u016a\7")
        buf.write("+\2\2\u016a\u016b\5,\27\2\u016b\u016c\7,\2\2\u016c\u0186")
        buf.write("\3\2\2\2\u016d\u016e\7\36\2\2\u016e\u016f\7\f\2\2\u016f")
        buf.write("\u0170\t\4\2\2\u0170\u0171\7\17\2\2\u0171\u0172\7F\2\2")
        buf.write("\u0172\u0186\7)\2\2\u0173\u0174\7\36\2\2\u0174\u0175\7")
        buf.write("\f\2\2\u0175\u0176\t\4\2\2\u0176\u0178\7\17\2\2\u0177")
        buf.write("\u0179\7F\2\2\u0178\u0177\3\2\2\2\u0178\u0179\3\2\2\2")
        buf.write("\u0179\u017a\3\2\2\2\u017a\u0186\7H\2\2\u017b\u017c\7")
        buf.write("\36\2\2\u017c\u017d\7\f\2\2\u017d\u017f\t\4\2\2\u017e")
        buf.write("\u0180\7F\2\2\u017f\u017e\3\2\2\2\u017f\u0180\3\2\2\2")
        buf.write("\u0180\u0181\3\2\2\2\u0181\u0182\7\20\2\2\u0182\u0183")
        buf.write("\5J&\2\u0183\u0184\7)\2\2\u0184\u0186\3\2\2\2\u0185\u0163")
        buf.write("\3\2\2\2\u0185\u016d\3\2\2\2\u0185\u0173\3\2\2\2\u0185")
        buf.write("\u017b\3\2\2\2\u0186\25\3\2\2\2\u0187\u0188\7\5\2\2\u0188")
        buf.write("\u018b\7F\2\2\u0189\u018a\7\7\2\2\u018a\u018c\7G\2\2\u018b")
        buf.write("\u0189\3\2\2\2\u018b\u018c\3\2\2\2\u018c\u018d\3\2\2\2")
        buf.write("\u018d\u018e\7)\2\2\u018e\27\3\2\2\2\u018f\u0190\7\3\2")
        buf.write("\2\u0190\u0191\7G\2\2\u0191\u0192\7\6\2\2\u0192\u0195")
        buf.write("\7F\2\2\u0193\u0194\7\7\2\2\u0194\u0196\7G\2\2\u0195\u0193")
        buf.write("\3\2\2\2\u0195\u0196\3\2\2\2\u0196\u01a0\3\2\2\2\u0197")
        buf.write("\u019b\7+\2\2\u0198\u019a\5\32\16\2\u0199\u0198\3\2\2")
        buf.write("\2\u019a\u019d\3\2\2\2\u019b\u0199\3\2\2\2\u019b\u019c")
        buf.write("\3\2\2\2\u019c\u019e\3\2\2\2\u019d\u019b\3\2\2\2\u019e")
        buf.write("\u01a1\7,\2\2\u019f\u01a1\7)\2\2\u01a0\u0197\3\2\2\2\u01a0")
        buf.write("\u019f\3\2\2\2\u01a1\31\3\2\2\2\u01a2\u01a6\5\34\17\2")
        buf.write('\u01a3\u01a6\5"\22\2\u01a4\u01a6\7)\2\2\u01a5\u01a2\3')
        buf.write("\2\2\2\u01a5\u01a3\3\2\2\2\u01a5\u01a4\3\2\2\2\u01a6\33")
        buf.write("\3\2\2\2\u01a7\u01a8\7\4\2\2\u01a8\u01a9\5\36\20\2\u01a9")
        buf.write("\u01aa\7(\2\2\u01aa\u01ab\5 \21\2\u01ab\u01ac\7)\2\2\u01ac")
        buf.write("\35\3\2\2\2\u01ad\u01bb\7\65\2\2\u01ae\u01af\7+\2\2\u01af")
        buf.write("\u01b4\7F\2\2\u01b0\u01b1\7*\2\2\u01b1\u01b3\7F\2\2\u01b2")
        buf.write("\u01b0\3\2\2\2\u01b3\u01b6\3\2\2\2\u01b4\u01b2\3\2\2\2")
        buf.write("\u01b4\u01b5\3\2\2\2\u01b5\u01b7\3\2\2\2\u01b6\u01b4\3")
        buf.write("\2\2\2\u01b7\u01bb\7,\2\2\u01b8\u01bb\7X\2\2\u01b9\u01bb")
        buf.write("\7F\2\2\u01ba\u01ad\3\2\2\2\u01ba\u01ae\3\2\2\2\u01ba")
        buf.write("\u01b8\3\2\2\2\u01ba\u01b9\3\2\2\2\u01bb\37\3\2\2\2\u01bc")
        buf.write("\u01c0\7F\2\2\u01bd\u01c0\7]\2\2\u01be\u01c0\7\65\2\2")
        buf.write("\u01bf\u01bc\3\2\2\2\u01bf\u01bd\3\2\2\2\u01bf\u01be\3")
        buf.write("\2\2\2\u01c0!\3\2\2\2\u01c1\u01c2\7\5\2\2\u01c2\u01c3")
        buf.write("\5J&\2\u01c3\u01c4\7(\2\2\u01c4\u01c7\5J&\2\u01c5\u01c6")
        buf.write("\7\7\2\2\u01c6\u01c8\7G\2\2\u01c7\u01c5\3\2\2\2\u01c7")
        buf.write("\u01c8\3\2\2\2\u01c8\u01c9\3\2\2\2\u01c9\u01ca\7)\2\2")
        buf.write("\u01ca#\3\2\2\2\u01cb\u01cc\7F\2\2\u01cc\u01cd\7?\2\2")
        buf.write("\u01cd\u01ce\5@!\2\u01ce\u01cf\7)\2\2\u01cf%\3\2\2\2\u01d0")
        buf.write("\u01d1\7+\2\2\u01d1\u01d2\5,\27\2\u01d2\u01d3\7,\2\2\u01d3")
        buf.write("'\3\2\2\2\u01d4\u01d5\7\22\2\2\u01d5\u01d6\7-\2\2\u01d6")
        buf.write('\u01d7\5B"\2\u01d7\u01d8\7.\2\2\u01d8\u01e2\5&\24\2\u01d9')
        buf.write("\u01da\7\23\2\2\u01da\u01db\7\22\2\2\u01db\u01dc\7-\2")
        buf.write('\2\u01dc\u01dd\5B"\2\u01dd\u01de\7.\2\2\u01de\u01df\5')
        buf.write("&\24\2\u01df\u01e1\3\2\2\2\u01e0\u01d9\3\2\2\2\u01e1\u01e4")
        buf.write("\3\2\2\2\u01e2\u01e0\3\2\2\2\u01e2\u01e3\3\2\2\2\u01e3")
        buf.write("\u01e7\3\2\2\2\u01e4\u01e2\3\2\2\2\u01e5\u01e6\7\23\2")
        buf.write("\2\u01e6\u01e8\5&\24\2\u01e7\u01e5\3\2\2\2\u01e7\u01e8")
        buf.write("\3\2\2\2\u01e8)\3\2\2\2\u01e9\u01ed\5$\23\2\u01ea\u01ed")
        buf.write("\5(\25\2\u01eb\u01ed\7)\2\2\u01ec\u01e9\3\2\2\2\u01ec")
        buf.write("\u01ea\3\2\2\2\u01ec\u01eb\3\2\2\2\u01ed+\3\2\2\2\u01ee")
        buf.write("\u01f0\5*\26\2\u01ef\u01ee\3\2\2\2\u01f0\u01f3\3\2\2\2")
        buf.write("\u01f1\u01ef\3\2\2\2\u01f1\u01f2\3\2\2\2\u01f2-\3\2\2")
        buf.write("\2\u01f3\u01f1\3\2\2\2\u01f4\u01ff\5\b\5\2\u01f5\u01ff")
        buf.write("\5\n\6\2\u01f6\u01ff\5\f\7\2\u01f7\u01ff\5\16\b\2\u01f8")
        buf.write("\u01ff\5\22\n\2\u01f9\u01ff\5\20\t\2\u01fa\u01ff\5\24")
        buf.write("\13\2\u01fb\u01ff\5\26\f\2\u01fc\u01ff\5\30\r\2\u01fd")
        buf.write("\u01ff\7)\2\2\u01fe\u01f4\3\2\2\2\u01fe\u01f5\3\2\2\2")
        buf.write("\u01fe\u01f6\3\2\2\2\u01fe\u01f7\3\2\2\2\u01fe\u01f8\3")
        buf.write("\2\2\2\u01fe\u01f9\3\2\2\2\u01fe\u01fa\3\2\2\2\u01fe\u01fb")
        buf.write("\3\2\2\2\u01fe\u01fc\3\2\2\2\u01fe\u01fd\3\2\2\2\u01ff")
        buf.write("/\3\2\2\2\u0200\u0202\5:\36\2\u0201\u0200\3\2\2\2\u0202")
        buf.write("\u0205\3\2\2\2\u0203\u0201\3\2\2\2\u0203\u0204\3\2\2\2")
        buf.write("\u0204\u0206\3\2\2\2\u0205\u0203\3\2\2\2\u0206\u0207\7")
        buf.write("\2\2\3\u0207\61\3\2\2\2\u0208\u020a\5\64\33\2\u0209\u0208")
        buf.write("\3\2\2\2\u020a\u020d\3\2\2\2\u020b\u0209\3\2\2\2\u020b")
        buf.write("\u020c\3\2\2\2\u020c\u020e\3\2\2\2\u020d\u020b\3\2\2\2")
        buf.write("\u020e\u020f\7\2\2\3\u020f\63\3\2\2\2\u0210\u0213\5\66")
        buf.write("\34\2\u0211\u0213\58\35\2\u0212\u0210\3\2\2\2\u0212\u0211")
        buf.write("\3\2\2\2\u0213\65\3\2\2\2\u0214\u0215\7F\2\2\u0215\u0216")
        buf.write("\7&\2\2\u0216\u0217\5> \2\u0217\u0218\7)\2\2\u0218\67")
        buf.write("\3\2\2\2\u0219\u021a\7F\2\2\u021a\u021b\7?\2\2\u021b\u021c")
        buf.write("\5> \2\u021c\u021d\7)\2\2\u021d9\3\2\2\2\u021e\u021f\7")
        buf.write("F\2\2\u021f\u0220\7&\2\2\u0220\u0221\5@!\2\u0221\u0222")
        buf.write("\7)\2\2\u0222;\3\2\2\2\u0223\u0226\5@!\2\u0224\u0226\5")
        buf.write('B"\2\u0225\u0223\3\2\2\2\u0225\u0224\3\2\2\2\u0226=\3')
        buf.write("\2\2\2\u0227\u0228\b \1\2\u0228\u0229\7/\2\2\u0229\u022a")
        buf.write("\5> \2\u022a\u022b\7\60\2\2\u022b\u0236\3\2\2\2\u022c")
        buf.write("\u0236\5D#\2\u022d\u0236\5H%\2\u022e\u022f\t\5\2\2\u022f")
        buf.write("\u0236\5> \13\u0230\u0231\7E\2\2\u0231\u0232\7/\2\2\u0232")
        buf.write("\u0233\5> \2\u0233\u0234\7\60\2\2\u0234\u0236\3\2\2\2")
        buf.write("\u0235\u0227\3\2\2\2\u0235\u022c\3\2\2\2\u0235\u022d\3")
        buf.write("\2\2\2\u0235\u022e\3\2\2\2\u0235\u0230\3\2\2\2\u0236\u024e")
        buf.write("\3\2\2\2\u0237\u0238\f\n\2\2\u0238\u0239\7\35\2\2\u0239")
        buf.write("\u024d\5> \n\u023a\u023b\f\t\2\2\u023b\u023c\t\6\2\2\u023c")
        buf.write("\u024d\5> \n\u023d\u023e\f\b\2\2\u023e\u023f\t\5\2\2\u023f")
        buf.write("\u024d\5> \t\u0240\u0241\f\7\2\2\u0241\u0242\t\7\2\2\u0242")
        buf.write("\u024d\5> \b\u0243\u0244\f\6\2\2\u0244\u0245\7:\2\2\u0245")
        buf.write("\u024d\5> \7\u0246\u0247\f\5\2\2\u0247\u0248\7;\2\2\u0248")
        buf.write("\u024d\5> \6\u0249\u024a\f\4\2\2\u024a\u024b\7<\2\2\u024b")
        buf.write("\u024d\5> \5\u024c\u0237\3\2\2\2\u024c\u023a\3\2\2\2\u024c")
        buf.write("\u023d\3\2\2\2\u024c\u0240\3\2\2\2\u024c\u0243\3\2\2\2")
        buf.write("\u024c\u0246\3\2\2\2\u024c\u0249\3\2\2\2\u024d\u0250\3")
        buf.write("\2\2\2\u024e\u024c\3\2\2\2\u024e\u024f\3\2\2\2\u024f?")
        buf.write("\3\2\2\2\u0250\u024e\3\2\2\2\u0251\u0252\b!\1\2\u0252")
        buf.write("\u0253\7/\2\2\u0253\u0254\5@!\2\u0254\u0255\7\60\2\2\u0255")
        buf.write("\u0269\3\2\2\2\u0256\u0269\5D#\2\u0257\u0269\7F\2\2\u0258")
        buf.write("\u0269\5H%\2\u0259\u025a\t\5\2\2\u025a\u0269\5@!\f\u025b")
        buf.write("\u025c\7E\2\2\u025c\u025d\7/\2\2\u025d\u025e\5@!\2\u025e")
        buf.write("\u025f\7\60\2\2\u025f\u0269\3\2\2\2\u0260\u0261\7/\2\2")
        buf.write('\u0261\u0262\5B"\2\u0262\u0263\7\60\2\2\u0263\u0264\7')
        buf.write("\61\2\2\u0264\u0265\5@!\2\u0265\u0266\7\62\2\2\u0266\u0267")
        buf.write("\5@!\3\u0267\u0269\3\2\2\2\u0268\u0251\3\2\2\2\u0268\u0256")
        buf.write("\3\2\2\2\u0268\u0257\3\2\2\2\u0268\u0258\3\2\2\2\u0268")
        buf.write("\u0259\3\2\2\2\u0268\u025b\3\2\2\2\u0268\u0260\3\2\2\2")
        buf.write("\u0269\u0281\3\2\2\2\u026a\u026b\f\13\2\2\u026b\u026c")
        buf.write("\7\35\2\2\u026c\u0280\5@!\13\u026d\u026e\f\n\2\2\u026e")
        buf.write("\u026f\t\6\2\2\u026f\u0280\5@!\13\u0270\u0271\f\t\2\2")
        buf.write("\u0271\u0272\t\5\2\2\u0272\u0280\5@!\n\u0273\u0274\f\b")
        buf.write("\2\2\u0274\u0275\t\7\2\2\u0275\u0280\5@!\t\u0276\u0277")
        buf.write("\f\7\2\2\u0277\u0278\7:\2\2\u0278\u0280\5@!\b\u0279\u027a")
        buf.write("\f\6\2\2\u027a\u027b\7;\2\2\u027b\u0280\5@!\7\u027c\u027d")
        buf.write("\f\5\2\2\u027d\u027e\7<\2\2\u027e\u0280\5@!\6\u027f\u026a")
        buf.write("\3\2\2\2\u027f\u026d\3\2\2\2\u027f\u0270\3\2\2\2\u027f")
        buf.write("\u0273\3\2\2\2\u027f\u0276\3\2\2\2\u027f\u0279\3\2\2\2")
        buf.write("\u027f\u027c\3\2\2\2\u0280\u0283\3\2\2\2\u0281\u027f\3")
        buf.write("\2\2\2\u0281\u0282\3\2\2\2\u0282A\3\2\2\2\u0283\u0281")
        buf.write('\3\2\2\2\u0284\u0285\b"\1\2\u0285\u0286\7/\2\2\u0286')
        buf.write('\u0287\5B"\2\u0287\u0288\7\60\2\2\u0288\u029d\3\2\2\2')
        buf.write("\u0289\u029d\5F$\2\u028a\u028b\t\b\2\2\u028b\u029d\5B")
        buf.write('"\t\u028c\u028d\5@!\2\u028d\u028e\t\t\2\2\u028e\u028f')
        buf.write("\5@!\2\u028f\u029d\3\2\2\2\u0290\u0291\5@!\2\u0291\u0292")
        buf.write("\t\n\2\2\u0292\u0293\5@!\2\u0293\u029d\3\2\2\2\u0294\u0295")
        buf.write('\7/\2\2\u0295\u0296\5B"\2\u0296\u0297\7\60\2\2\u0297')
        buf.write('\u0298\7\61\2\2\u0298\u0299\5B"\2\u0299\u029a\7\62\2')
        buf.write('\2\u029a\u029b\5B"\3\u029b\u029d\3\2\2\2\u029c\u0284')
        buf.write("\3\2\2\2\u029c\u0289\3\2\2\2\u029c\u028a\3\2\2\2\u029c")
        buf.write("\u028c\3\2\2\2\u029c\u0290\3\2\2\2\u029c\u0294\3\2\2\2")
        buf.write("\u029d\u02a9\3\2\2\2\u029e\u029f\f\6\2\2\u029f\u02a0\t")
        buf.write('\n\2\2\u02a0\u02a8\5B"\7\u02a1\u02a2\f\5\2\2\u02a2\u02a3')
        buf.write('\t\13\2\2\u02a3\u02a8\5B"\6\u02a4\u02a5\f\4\2\2\u02a5')
        buf.write('\u02a6\t\f\2\2\u02a6\u02a8\5B"\5\u02a7\u029e\3\2\2\2')
        buf.write("\u02a7\u02a1\3\2\2\2\u02a7\u02a4\3\2\2\2\u02a8\u02ab\3")
        buf.write("\2\2\2\u02a9\u02a7\3\2\2\2\u02a9\u02aa\3\2\2\2\u02aaC")
        buf.write("\3\2\2\2\u02ab\u02a9\3\2\2\2\u02ac\u02ad\t\r\2\2\u02ad")
        buf.write("E\3\2\2\2\u02ae\u02af\t\16\2\2\u02afG\3\2\2\2\u02b0\u02b1")
        buf.write("\t\17\2\2\u02b1I\3\2\2\2\u02b2\u02b4\7\64\2\2\u02b3\u02b2")
        buf.write("\3\2\2\2\u02b3\u02b4\3\2\2\2\u02b4\u02b5\3\2\2\2\u02b5")
        buf.write("\u02ba\7F\2\2\u02b6\u02b7\7\63\2\2\u02b7\u02b9\7F\2\2")
        buf.write("\u02b8\u02b6\3\2\2\2\u02b9\u02bc\3\2\2\2\u02ba\u02b8\3")
        buf.write("\2\2\2\u02ba\u02bb\3\2\2\2\u02bbK\3\2\2\2\u02bc\u02ba")
        buf.write("\3\2\2\2FR`fjpvz\u0087\u008f\u009e\u00a6\u00b5\u00bd\u00bf")
        buf.write("\u00cf\u00e0\u00ef\u00fe\u0101\u0105\u0112\u0117\u011d")
        buf.write("\u0121\u012e\u0133\u0139\u013d\u0140\u0148\u014f\u0153")
        buf.write("\u0158\u015b\u0161\u0167\u0178\u017f\u0185\u018b\u0195")
        buf.write("\u019b\u01a0\u01a5\u01b4\u01ba\u01bf\u01c7\u01e2\u01e7")
        buf.write("\u01ec\u01f1\u01fe\u0203\u020b\u0212\u0225\u0235\u024c")
        buf.write("\u024e\u0268\u027f\u0281\u029c\u02a7\u02a9\u02b3\u02ba")
        return buf.getvalue()


class GrammarParser(Parser):
    grammarFileName = "GrammarParser.g4"

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
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def EOF(self):
            return self.getToken(GrammarParser.EOF, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_condition

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCondition"):
                listener.enterCondition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCondition"):
                listener.exitCondition(self)

    def condition(self):

        localctx = GrammarParser.ConditionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_condition)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 74
            self.cond_expression(0)
            self.state = 75
            self.match(GrammarParser.EOF)
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
            return self.getTypedRuleContext(GrammarParser.State_definitionContext, 0)

        def EOF(self):
            return self.getToken(GrammarParser.EOF, 0)

        def def_assignment(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Def_assignmentContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Def_assignmentContext, i)

        def getRuleIndex(self):
            return GrammarParser.RULE_state_machine_dsl

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterState_machine_dsl"):
                listener.enterState_machine_dsl(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitState_machine_dsl"):
                listener.exitState_machine_dsl(self)

    def state_machine_dsl(self):

        localctx = GrammarParser.State_machine_dslContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_state_machine_dsl)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 80
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.DEF:
                self.state = 77
                self.def_assignment()
                self.state = 82
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 83
            self.state_definition()
            self.state = 84
            self.match(GrammarParser.EOF)
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
            return self.getToken(GrammarParser.DEF, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def ASSIGN(self):
            return self.getToken(GrammarParser.ASSIGN, 0)

        def init_expression(self):
            return self.getTypedRuleContext(GrammarParser.Init_expressionContext, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def INT_TYPE(self):
            return self.getToken(GrammarParser.INT_TYPE, 0)

        def FLOAT_TYPE(self):
            return self.getToken(GrammarParser.FLOAT_TYPE, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_def_assignment

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDef_assignment"):
                listener.enterDef_assignment(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDef_assignment"):
                listener.exitDef_assignment(self)

    def def_assignment(self):

        localctx = GrammarParser.Def_assignmentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_def_assignment)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 86
            self.match(GrammarParser.DEF)
            self.state = 87
            localctx.deftype = self._input.LT(1)
            _la = self._input.LA(1)
            if not (_la == GrammarParser.INT_TYPE or _la == GrammarParser.FLOAT_TYPE):
                localctx.deftype = self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 88
            self.match(GrammarParser.ID)
            self.state = 89
            self.match(GrammarParser.ASSIGN)
            self.state = 90
            self.init_expression(0)
            self.state = 91
            self.match(GrammarParser.SEMI)
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
            return GrammarParser.RULE_state_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class LeafStateDefinitionContext(State_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.State_definitionContext
            super().__init__(parser)
            self.pseudo = None  # Token
            self.state_id = None  # Token
            self.extra_name = None  # Token
            self.copyFrom(ctx)

        def STATE(self):
            return self.getToken(GrammarParser.STATE, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def NAMED(self):
            return self.getToken(GrammarParser.NAMED, 0)

        def PSEUDO(self):
            return self.getToken(GrammarParser.PSEUDO, 0)

        def STRING(self):
            return self.getToken(GrammarParser.STRING, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLeafStateDefinition"):
                listener.enterLeafStateDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLeafStateDefinition"):
                listener.exitLeafStateDefinition(self)

    class CompositeStateDefinitionContext(State_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.State_definitionContext
            super().__init__(parser)
            self.pseudo = None  # Token
            self.state_id = None  # Token
            self.extra_name = None  # Token
            self.copyFrom(ctx)

        def STATE(self):
            return self.getToken(GrammarParser.STATE, 0)

        def LBRACE(self):
            return self.getToken(GrammarParser.LBRACE, 0)

        def RBRACE(self):
            return self.getToken(GrammarParser.RBRACE, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def NAMED(self):
            return self.getToken(GrammarParser.NAMED, 0)

        def state_inner_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.State_inner_statementContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.State_inner_statementContext, i
                )

        def PSEUDO(self):
            return self.getToken(GrammarParser.PSEUDO, 0)

        def STRING(self):
            return self.getToken(GrammarParser.STRING, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCompositeStateDefinition"):
                listener.enterCompositeStateDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCompositeStateDefinition"):
                listener.exitCompositeStateDefinition(self)

    def state_definition(self):

        localctx = GrammarParser.State_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_state_definition)
        self._la = 0  # Token type
        try:
            self.state = 120
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 6, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.LeafStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 94
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.PSEUDO:
                    self.state = 93
                    localctx.pseudo = self.match(GrammarParser.PSEUDO)

                self.state = 96
                self.match(GrammarParser.STATE)
                self.state = 97
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 100
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.NAMED:
                    self.state = 98
                    self.match(GrammarParser.NAMED)
                    self.state = 99
                    localctx.extra_name = self.match(GrammarParser.STRING)

                self.state = 102
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 2:
                localctx = GrammarParser.CompositeStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 104
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.PSEUDO:
                    self.state = 103
                    localctx.pseudo = self.match(GrammarParser.PSEUDO)

                self.state = 106
                self.match(GrammarParser.STATE)
                self.state = 107
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 110
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.NAMED:
                    self.state = 108
                    self.match(GrammarParser.NAMED)
                    self.state = 109
                    localctx.extra_name = self.match(GrammarParser.STRING)

                self.state = 112
                self.match(GrammarParser.LBRACE)
                self.state = 116
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while (
                    ((_la) & ~0x3F) == 0
                    and (
                        (1 << _la)
                        & (
                            (1 << GrammarParser.IMPORT)
                            | (1 << GrammarParser.EVENT)
                            | (1 << GrammarParser.PSEUDO)
                            | (1 << GrammarParser.STATE)
                            | (1 << GrammarParser.ENTER)
                            | (1 << GrammarParser.EXIT)
                            | (1 << GrammarParser.DURING)
                            | (1 << GrammarParser.INIT_MARKER)
                            | (1 << GrammarParser.SHIFT_RIGHT)
                            | (1 << GrammarParser.SEMI)
                            | (1 << GrammarParser.BANG)
                        )
                    )
                    != 0
                ) or _la == GrammarParser.ID:
                    self.state = 113
                    self.state_inner_statement()
                    self.state = 118
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 119
                self.match(GrammarParser.RBRACE)
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
            return GrammarParser.RULE_transition_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class NormalTransitionDefinitionContext(Transition_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Transition_definitionContext
            super().__init__(parser)
            self.from_state = None  # Token
            self.to_state = None  # Token
            self.from_id = None  # Token
            self.copyFrom(ctx)

        def ARROW(self):
            return self.getToken(GrammarParser.ARROW, 0)

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.ID)
            else:
                return self.getToken(GrammarParser.ID, i)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def EFFECT(self):
            return self.getToken(GrammarParser.EFFECT, 0)

        def LBRACE(self):
            return self.getToken(GrammarParser.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
            )

        def RBRACE(self):
            return self.getToken(GrammarParser.RBRACE, 0)

        def COLONCOLON(self):
            return self.getToken(GrammarParser.COLONCOLON, 0)

        def COLON(self):
            return self.getToken(GrammarParser.COLON, 0)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def IF(self):
            return self.getToken(GrammarParser.IF, 0)

        def LBRACK(self):
            return self.getToken(GrammarParser.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(GrammarParser.RBRACK, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterNormalTransitionDefinition"):
                listener.enterNormalTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitNormalTransitionDefinition"):
                listener.exitNormalTransitionDefinition(self)

    class EntryTransitionDefinitionContext(Transition_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Transition_definitionContext
            super().__init__(parser)
            self.to_state = None  # Token
            self.copyFrom(ctx)

        def INIT_MARKER(self):
            return self.getToken(GrammarParser.INIT_MARKER, 0)

        def ARROW(self):
            return self.getToken(GrammarParser.ARROW, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def EFFECT(self):
            return self.getToken(GrammarParser.EFFECT, 0)

        def LBRACE(self):
            return self.getToken(GrammarParser.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
            )

        def RBRACE(self):
            return self.getToken(GrammarParser.RBRACE, 0)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def COLON(self):
            return self.getToken(GrammarParser.COLON, 0)

        def IF(self):
            return self.getToken(GrammarParser.IF, 0)

        def LBRACK(self):
            return self.getToken(GrammarParser.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(GrammarParser.RBRACK, 0)

        def COLONCOLON(self):
            return self.getToken(GrammarParser.COLONCOLON, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEntryTransitionDefinition"):
                listener.enterEntryTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEntryTransitionDefinition"):
                listener.exitEntryTransitionDefinition(self)

    class ExitTransitionDefinitionContext(Transition_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Transition_definitionContext
            super().__init__(parser)
            self.from_state = None  # Token
            self.from_id = None  # Token
            self.copyFrom(ctx)

        def ARROW(self):
            return self.getToken(GrammarParser.ARROW, 0)

        def INIT_MARKER(self):
            return self.getToken(GrammarParser.INIT_MARKER, 0)

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.ID)
            else:
                return self.getToken(GrammarParser.ID, i)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def EFFECT(self):
            return self.getToken(GrammarParser.EFFECT, 0)

        def LBRACE(self):
            return self.getToken(GrammarParser.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
            )

        def RBRACE(self):
            return self.getToken(GrammarParser.RBRACE, 0)

        def COLONCOLON(self):
            return self.getToken(GrammarParser.COLONCOLON, 0)

        def COLON(self):
            return self.getToken(GrammarParser.COLON, 0)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def IF(self):
            return self.getToken(GrammarParser.IF, 0)

        def LBRACK(self):
            return self.getToken(GrammarParser.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(GrammarParser.RBRACK, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExitTransitionDefinition"):
                listener.enterExitTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExitTransitionDefinition"):
                listener.exitExitTransitionDefinition(self)

    def transition_definition(self):

        localctx = GrammarParser.Transition_definitionContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 8, self.RULE_transition_definition)
        self._la = 0  # Token type
        try:
            self.state = 189
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 13, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EntryTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 122
                self.match(GrammarParser.INIT_MARKER)
                self.state = 123
                self.match(GrammarParser.ARROW)
                self.state = 124
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 133
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 7, self._ctx)
                if la_ == 1:
                    self.state = 125
                    _la = self._input.LA(1)
                    if not (
                        _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON
                    ):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 126
                    self.chain_id()

                elif la_ == 2:
                    self.state = 127
                    self.match(GrammarParser.COLON)
                    self.state = 128
                    self.match(GrammarParser.IF)
                    self.state = 129
                    self.match(GrammarParser.LBRACK)
                    self.state = 130
                    self.cond_expression(0)
                    self.state = 131
                    self.match(GrammarParser.RBRACK)

                self.state = 141
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.SEMI]:
                    self.state = 135
                    self.match(GrammarParser.SEMI)
                    pass
                elif token in [GrammarParser.EFFECT]:
                    self.state = 136
                    self.match(GrammarParser.EFFECT)
                    self.state = 137
                    self.match(GrammarParser.LBRACE)
                    self.state = 138
                    self.operational_statement_set()
                    self.state = 139
                    self.match(GrammarParser.RBRACE)
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 2:
                localctx = GrammarParser.NormalTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 2)
                self.state = 143
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 144
                self.match(GrammarParser.ARROW)
                self.state = 145
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 156
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 9, self._ctx)
                if la_ == 1:
                    self.state = 146
                    self.match(GrammarParser.COLONCOLON)
                    self.state = 147
                    localctx.from_id = self.match(GrammarParser.ID)

                elif la_ == 2:
                    self.state = 148
                    self.match(GrammarParser.COLON)
                    self.state = 149
                    self.chain_id()

                elif la_ == 3:
                    self.state = 150
                    self.match(GrammarParser.COLON)
                    self.state = 151
                    self.match(GrammarParser.IF)
                    self.state = 152
                    self.match(GrammarParser.LBRACK)
                    self.state = 153
                    self.cond_expression(0)
                    self.state = 154
                    self.match(GrammarParser.RBRACK)

                self.state = 164
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.SEMI]:
                    self.state = 158
                    self.match(GrammarParser.SEMI)
                    pass
                elif token in [GrammarParser.EFFECT]:
                    self.state = 159
                    self.match(GrammarParser.EFFECT)
                    self.state = 160
                    self.match(GrammarParser.LBRACE)
                    self.state = 161
                    self.operational_statement_set()
                    self.state = 162
                    self.match(GrammarParser.RBRACE)
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 3:
                localctx = GrammarParser.ExitTransitionDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 166
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 167
                self.match(GrammarParser.ARROW)
                self.state = 168
                self.match(GrammarParser.INIT_MARKER)
                self.state = 179
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 11, self._ctx)
                if la_ == 1:
                    self.state = 169
                    self.match(GrammarParser.COLONCOLON)
                    self.state = 170
                    localctx.from_id = self.match(GrammarParser.ID)

                elif la_ == 2:
                    self.state = 171
                    self.match(GrammarParser.COLON)
                    self.state = 172
                    self.chain_id()

                elif la_ == 3:
                    self.state = 173
                    self.match(GrammarParser.COLON)
                    self.state = 174
                    self.match(GrammarParser.IF)
                    self.state = 175
                    self.match(GrammarParser.LBRACK)
                    self.state = 176
                    self.cond_expression(0)
                    self.state = 177
                    self.match(GrammarParser.RBRACK)

                self.state = 187
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.SEMI]:
                    self.state = 181
                    self.match(GrammarParser.SEMI)
                    pass
                elif token in [GrammarParser.EFFECT]:
                    self.state = 182
                    self.match(GrammarParser.EFFECT)
                    self.state = 183
                    self.match(GrammarParser.LBRACE)
                    self.state = 184
                    self.operational_statement_set()
                    self.state = 185
                    self.match(GrammarParser.RBRACE)
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
            return GrammarParser.RULE_transition_force_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class NormalForceTransitionDefinitionContext(Transition_force_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Transition_force_definitionContext
            super().__init__(parser)
            self.from_state = None  # Token
            self.to_state = None  # Token
            self.from_id = None  # Token
            self.copyFrom(ctx)

        def BANG(self):
            return self.getToken(GrammarParser.BANG, 0)

        def ARROW(self):
            return self.getToken(GrammarParser.ARROW, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.ID)
            else:
                return self.getToken(GrammarParser.ID, i)

        def COLONCOLON(self):
            return self.getToken(GrammarParser.COLONCOLON, 0)

        def COLON(self):
            return self.getToken(GrammarParser.COLON, 0)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def IF(self):
            return self.getToken(GrammarParser.IF, 0)

        def LBRACK(self):
            return self.getToken(GrammarParser.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(GrammarParser.RBRACK, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterNormalForceTransitionDefinition"):
                listener.enterNormalForceTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitNormalForceTransitionDefinition"):
                listener.exitNormalForceTransitionDefinition(self)

    class ExitAllForceTransitionDefinitionContext(Transition_force_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Transition_force_definitionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def BANG(self):
            return self.getToken(GrammarParser.BANG, 0)

        def STAR(self):
            return self.getToken(GrammarParser.STAR, 0)

        def ARROW(self):
            return self.getToken(GrammarParser.ARROW, 0)

        def INIT_MARKER(self):
            return self.getToken(GrammarParser.INIT_MARKER, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def COLON(self):
            return self.getToken(GrammarParser.COLON, 0)

        def IF(self):
            return self.getToken(GrammarParser.IF, 0)

        def LBRACK(self):
            return self.getToken(GrammarParser.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(GrammarParser.RBRACK, 0)

        def COLONCOLON(self):
            return self.getToken(GrammarParser.COLONCOLON, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExitAllForceTransitionDefinition"):
                listener.enterExitAllForceTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExitAllForceTransitionDefinition"):
                listener.exitExitAllForceTransitionDefinition(self)

    class NormalAllForceTransitionDefinitionContext(Transition_force_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Transition_force_definitionContext
            super().__init__(parser)
            self.to_state = None  # Token
            self.copyFrom(ctx)

        def BANG(self):
            return self.getToken(GrammarParser.BANG, 0)

        def STAR(self):
            return self.getToken(GrammarParser.STAR, 0)

        def ARROW(self):
            return self.getToken(GrammarParser.ARROW, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def COLON(self):
            return self.getToken(GrammarParser.COLON, 0)

        def IF(self):
            return self.getToken(GrammarParser.IF, 0)

        def LBRACK(self):
            return self.getToken(GrammarParser.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(GrammarParser.RBRACK, 0)

        def COLONCOLON(self):
            return self.getToken(GrammarParser.COLONCOLON, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterNormalAllForceTransitionDefinition"):
                listener.enterNormalAllForceTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitNormalAllForceTransitionDefinition"):
                listener.exitNormalAllForceTransitionDefinition(self)

    class ExitForceTransitionDefinitionContext(Transition_force_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Transition_force_definitionContext
            super().__init__(parser)
            self.from_state = None  # Token
            self.from_id = None  # Token
            self.copyFrom(ctx)

        def BANG(self):
            return self.getToken(GrammarParser.BANG, 0)

        def ARROW(self):
            return self.getToken(GrammarParser.ARROW, 0)

        def INIT_MARKER(self):
            return self.getToken(GrammarParser.INIT_MARKER, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.ID)
            else:
                return self.getToken(GrammarParser.ID, i)

        def COLONCOLON(self):
            return self.getToken(GrammarParser.COLONCOLON, 0)

        def COLON(self):
            return self.getToken(GrammarParser.COLON, 0)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def IF(self):
            return self.getToken(GrammarParser.IF, 0)

        def LBRACK(self):
            return self.getToken(GrammarParser.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(GrammarParser.RBRACK, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExitForceTransitionDefinition"):
                listener.enterExitForceTransitionDefinition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExitForceTransitionDefinition"):
                listener.exitExitForceTransitionDefinition(self)

    def transition_force_definition(self):

        localctx = GrammarParser.Transition_force_definitionContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 10, self.RULE_transition_force_definition)
        self._la = 0  # Token type
        try:
            self.state = 255
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 18, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.NormalForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 191
                self.match(GrammarParser.BANG)
                self.state = 192
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 193
                self.match(GrammarParser.ARROW)
                self.state = 194
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 205
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 14, self._ctx)
                if la_ == 1:
                    self.state = 195
                    self.match(GrammarParser.COLONCOLON)
                    self.state = 196
                    localctx.from_id = self.match(GrammarParser.ID)

                elif la_ == 2:
                    self.state = 197
                    self.match(GrammarParser.COLON)
                    self.state = 198
                    self.chain_id()

                elif la_ == 3:
                    self.state = 199
                    self.match(GrammarParser.COLON)
                    self.state = 200
                    self.match(GrammarParser.IF)
                    self.state = 201
                    self.match(GrammarParser.LBRACK)
                    self.state = 202
                    self.cond_expression(0)
                    self.state = 203
                    self.match(GrammarParser.RBRACK)

                self.state = 207
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 2:
                localctx = GrammarParser.ExitForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 2)
                self.state = 208
                self.match(GrammarParser.BANG)
                self.state = 209
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 210
                self.match(GrammarParser.ARROW)
                self.state = 211
                self.match(GrammarParser.INIT_MARKER)
                self.state = 222
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 15, self._ctx)
                if la_ == 1:
                    self.state = 212
                    self.match(GrammarParser.COLONCOLON)
                    self.state = 213
                    localctx.from_id = self.match(GrammarParser.ID)

                elif la_ == 2:
                    self.state = 214
                    self.match(GrammarParser.COLON)
                    self.state = 215
                    self.chain_id()

                elif la_ == 3:
                    self.state = 216
                    self.match(GrammarParser.COLON)
                    self.state = 217
                    self.match(GrammarParser.IF)
                    self.state = 218
                    self.match(GrammarParser.LBRACK)
                    self.state = 219
                    self.cond_expression(0)
                    self.state = 220
                    self.match(GrammarParser.RBRACK)

                self.state = 224
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.NormalAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 3)
                self.state = 225
                self.match(GrammarParser.BANG)
                self.state = 226
                self.match(GrammarParser.STAR)
                self.state = 227
                self.match(GrammarParser.ARROW)
                self.state = 228
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 237
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 16, self._ctx)
                if la_ == 1:
                    self.state = 229
                    _la = self._input.LA(1)
                    if not (
                        _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON
                    ):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 230
                    self.chain_id()

                elif la_ == 2:
                    self.state = 231
                    self.match(GrammarParser.COLON)
                    self.state = 232
                    self.match(GrammarParser.IF)
                    self.state = 233
                    self.match(GrammarParser.LBRACK)
                    self.state = 234
                    self.cond_expression(0)
                    self.state = 235
                    self.match(GrammarParser.RBRACK)

                self.state = 239
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 4:
                localctx = GrammarParser.ExitAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 4)
                self.state = 240
                self.match(GrammarParser.BANG)
                self.state = 241
                self.match(GrammarParser.STAR)
                self.state = 242
                self.match(GrammarParser.ARROW)
                self.state = 243
                self.match(GrammarParser.INIT_MARKER)
                self.state = 252
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 17, self._ctx)
                if la_ == 1:
                    self.state = 244
                    _la = self._input.LA(1)
                    if not (
                        _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON
                    ):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 245
                    self.chain_id()

                elif la_ == 2:
                    self.state = 246
                    self.match(GrammarParser.COLON)
                    self.state = 247
                    self.match(GrammarParser.IF)
                    self.state = 248
                    self.match(GrammarParser.LBRACK)
                    self.state = 249
                    self.cond_expression(0)
                    self.state = 250
                    self.match(GrammarParser.RBRACK)

                self.state = 254
                self.match(GrammarParser.SEMI)
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
            return GrammarParser.RULE_enter_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class EnterRefFuncContext(Enter_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Enter_definitionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def ENTER(self):
            return self.getToken(GrammarParser.ENTER, 0)

        def REF(self):
            return self.getToken(GrammarParser.REF, 0)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEnterRefFunc"):
                listener.enterEnterRefFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEnterRefFunc"):
                listener.exitEnterRefFunc(self)

    class EnterOperationsContext(Enter_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Enter_definitionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def ENTER(self):
            return self.getToken(GrammarParser.ENTER, 0)

        def LBRACE(self):
            return self.getToken(GrammarParser.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
            )

        def RBRACE(self):
            return self.getToken(GrammarParser.RBRACE, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEnterOperations"):
                listener.enterEnterOperations(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEnterOperations"):
                listener.exitEnterOperations(self)

    class EnterAbstractFuncContext(Enter_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Enter_definitionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.raw_doc = None  # Token
            self.copyFrom(ctx)

        def ENTER(self):
            return self.getToken(GrammarParser.ENTER, 0)

        def ABSTRACT(self):
            return self.getToken(GrammarParser.ABSTRACT, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEnterAbstractFunc"):
                listener.enterEnterAbstractFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEnterAbstractFunc"):
                listener.exitEnterAbstractFunc(self)

    def enter_definition(self):

        localctx = GrammarParser.Enter_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_enter_definition)
        self._la = 0  # Token type
        try:
            self.state = 283
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 22, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EnterOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 257
                self.match(GrammarParser.ENTER)
                self.state = 259
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 258
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 261
                self.match(GrammarParser.LBRACE)
                self.state = 262
                self.operational_statement_set()
                self.state = 263
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 265
                self.match(GrammarParser.ENTER)
                self.state = 266
                self.match(GrammarParser.ABSTRACT)
                self.state = 267
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 268
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 269
                self.match(GrammarParser.ENTER)
                self.state = 270
                self.match(GrammarParser.ABSTRACT)
                self.state = 272
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 271
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 274
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.EnterRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 275
                self.match(GrammarParser.ENTER)
                self.state = 277
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 276
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 279
                self.match(GrammarParser.REF)
                self.state = 280
                self.chain_id()
                self.state = 281
                self.match(GrammarParser.SEMI)
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
            return GrammarParser.RULE_exit_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class ExitOperationsContext(Exit_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Exit_definitionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def EXIT(self):
            return self.getToken(GrammarParser.EXIT, 0)

        def LBRACE(self):
            return self.getToken(GrammarParser.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
            )

        def RBRACE(self):
            return self.getToken(GrammarParser.RBRACE, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExitOperations"):
                listener.enterExitOperations(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExitOperations"):
                listener.exitExitOperations(self)

    class ExitRefFuncContext(Exit_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Exit_definitionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def EXIT(self):
            return self.getToken(GrammarParser.EXIT, 0)

        def REF(self):
            return self.getToken(GrammarParser.REF, 0)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExitRefFunc"):
                listener.enterExitRefFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExitRefFunc"):
                listener.exitExitRefFunc(self)

    class ExitAbstractFuncContext(Exit_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Exit_definitionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.raw_doc = None  # Token
            self.copyFrom(ctx)

        def EXIT(self):
            return self.getToken(GrammarParser.EXIT, 0)

        def ABSTRACT(self):
            return self.getToken(GrammarParser.ABSTRACT, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExitAbstractFunc"):
                listener.enterExitAbstractFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExitAbstractFunc"):
                listener.exitExitAbstractFunc(self)

    def exit_definition(self):

        localctx = GrammarParser.Exit_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_exit_definition)
        self._la = 0  # Token type
        try:
            self.state = 311
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 26, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ExitOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 285
                self.match(GrammarParser.EXIT)
                self.state = 287
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 286
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 289
                self.match(GrammarParser.LBRACE)
                self.state = 290
                self.operational_statement_set()
                self.state = 291
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 293
                self.match(GrammarParser.EXIT)
                self.state = 294
                self.match(GrammarParser.ABSTRACT)
                self.state = 295
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 296
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 297
                self.match(GrammarParser.EXIT)
                self.state = 298
                self.match(GrammarParser.ABSTRACT)
                self.state = 300
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 299
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 302
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.ExitRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 303
                self.match(GrammarParser.EXIT)
                self.state = 305
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 304
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 307
                self.match(GrammarParser.REF)
                self.state = 308
                self.chain_id()
                self.state = 309
                self.match(GrammarParser.SEMI)
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
            return GrammarParser.RULE_during_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class DuringOperationsContext(During_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.During_definitionContext
            super().__init__(parser)
            self.aspect = None  # Token
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def DURING(self):
            return self.getToken(GrammarParser.DURING, 0)

        def LBRACE(self):
            return self.getToken(GrammarParser.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
            )

        def RBRACE(self):
            return self.getToken(GrammarParser.RBRACE, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def BEFORE(self):
            return self.getToken(GrammarParser.BEFORE, 0)

        def AFTER(self):
            return self.getToken(GrammarParser.AFTER, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDuringOperations"):
                listener.enterDuringOperations(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDuringOperations"):
                listener.exitDuringOperations(self)

    class DuringAbstractFuncContext(During_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.During_definitionContext
            super().__init__(parser)
            self.aspect = None  # Token
            self.func_name = None  # Token
            self.raw_doc = None  # Token
            self.copyFrom(ctx)

        def DURING(self):
            return self.getToken(GrammarParser.DURING, 0)

        def ABSTRACT(self):
            return self.getToken(GrammarParser.ABSTRACT, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def BEFORE(self):
            return self.getToken(GrammarParser.BEFORE, 0)

        def AFTER(self):
            return self.getToken(GrammarParser.AFTER, 0)

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDuringAbstractFunc"):
                listener.enterDuringAbstractFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDuringAbstractFunc"):
                listener.exitDuringAbstractFunc(self)

    class DuringRefFuncContext(During_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.During_definitionContext
            super().__init__(parser)
            self.aspect = None  # Token
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def DURING(self):
            return self.getToken(GrammarParser.DURING, 0)

        def REF(self):
            return self.getToken(GrammarParser.REF, 0)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def BEFORE(self):
            return self.getToken(GrammarParser.BEFORE, 0)

        def AFTER(self):
            return self.getToken(GrammarParser.AFTER, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDuringRefFunc"):
                listener.enterDuringRefFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDuringRefFunc"):
                listener.exitDuringRefFunc(self)

    def during_definition(self):

        localctx = GrammarParser.During_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_during_definition)
        self._la = 0  # Token type
        try:
            self.state = 351
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 34, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.DuringOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 313
                self.match(GrammarParser.DURING)
                self.state = 315
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 314
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 318
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 317
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 320
                self.match(GrammarParser.LBRACE)
                self.state = 321
                self.operational_statement_set()
                self.state = 322
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 324
                self.match(GrammarParser.DURING)
                self.state = 326
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 325
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 328
                self.match(GrammarParser.ABSTRACT)
                self.state = 329
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 330
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 331
                self.match(GrammarParser.DURING)
                self.state = 333
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 332
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 335
                self.match(GrammarParser.ABSTRACT)
                self.state = 337
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 336
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 339
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.DuringRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 340
                self.match(GrammarParser.DURING)
                self.state = 342
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 341
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 345
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 344
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 347
                self.match(GrammarParser.REF)
                self.state = 348
                self.chain_id()
                self.state = 349
                self.match(GrammarParser.SEMI)
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
            return GrammarParser.RULE_during_aspect_definition

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class DuringAspectRefFuncContext(During_aspect_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.During_aspect_definitionContext
            super().__init__(parser)
            self.aspect = None  # Token
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def SHIFT_RIGHT(self):
            return self.getToken(GrammarParser.SHIFT_RIGHT, 0)

        def DURING(self):
            return self.getToken(GrammarParser.DURING, 0)

        def REF(self):
            return self.getToken(GrammarParser.REF, 0)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def BEFORE(self):
            return self.getToken(GrammarParser.BEFORE, 0)

        def AFTER(self):
            return self.getToken(GrammarParser.AFTER, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDuringAspectRefFunc"):
                listener.enterDuringAspectRefFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDuringAspectRefFunc"):
                listener.exitDuringAspectRefFunc(self)

    class DuringAspectAbstractFuncContext(During_aspect_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.During_aspect_definitionContext
            super().__init__(parser)
            self.aspect = None  # Token
            self.func_name = None  # Token
            self.raw_doc = None  # Token
            self.copyFrom(ctx)

        def SHIFT_RIGHT(self):
            return self.getToken(GrammarParser.SHIFT_RIGHT, 0)

        def DURING(self):
            return self.getToken(GrammarParser.DURING, 0)

        def ABSTRACT(self):
            return self.getToken(GrammarParser.ABSTRACT, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def BEFORE(self):
            return self.getToken(GrammarParser.BEFORE, 0)

        def AFTER(self):
            return self.getToken(GrammarParser.AFTER, 0)

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDuringAspectAbstractFunc"):
                listener.enterDuringAspectAbstractFunc(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDuringAspectAbstractFunc"):
                listener.exitDuringAspectAbstractFunc(self)

    class DuringAspectOperationsContext(During_aspect_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.During_aspect_definitionContext
            super().__init__(parser)
            self.aspect = None  # Token
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def SHIFT_RIGHT(self):
            return self.getToken(GrammarParser.SHIFT_RIGHT, 0)

        def DURING(self):
            return self.getToken(GrammarParser.DURING, 0)

        def LBRACE(self):
            return self.getToken(GrammarParser.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
            )

        def RBRACE(self):
            return self.getToken(GrammarParser.RBRACE, 0)

        def BEFORE(self):
            return self.getToken(GrammarParser.BEFORE, 0)

        def AFTER(self):
            return self.getToken(GrammarParser.AFTER, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterDuringAspectOperations"):
                listener.enterDuringAspectOperations(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitDuringAspectOperations"):
                listener.exitDuringAspectOperations(self)

    def during_aspect_definition(self):

        localctx = GrammarParser.During_aspect_definitionContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 18, self.RULE_during_aspect_definition)
        self._la = 0  # Token type
        try:
            self.state = 387
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 38, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.DuringAspectOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 353
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 354
                self.match(GrammarParser.DURING)
                self.state = 355
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 357
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 356
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 359
                self.match(GrammarParser.LBRACE)
                self.state = 360
                self.operational_statement_set()
                self.state = 361
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 363
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 364
                self.match(GrammarParser.DURING)
                self.state = 365
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 366
                self.match(GrammarParser.ABSTRACT)
                self.state = 367
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 368
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 369
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 370
                self.match(GrammarParser.DURING)
                self.state = 371
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 372
                self.match(GrammarParser.ABSTRACT)
                self.state = 374
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 373
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 376
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.DuringAspectRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 377
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 378
                self.match(GrammarParser.DURING)
                self.state = 379
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 381
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 380
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 383
                self.match(GrammarParser.REF)
                self.state = 384
                self.chain_id()
                self.state = 385
                self.match(GrammarParser.SEMI)
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
            return self.getToken(GrammarParser.EVENT, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def NAMED(self):
            return self.getToken(GrammarParser.NAMED, 0)

        def STRING(self):
            return self.getToken(GrammarParser.STRING, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_event_definition

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEvent_definition"):
                listener.enterEvent_definition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEvent_definition"):
                listener.exitEvent_definition(self)

    def event_definition(self):

        localctx = GrammarParser.Event_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_event_definition)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 389
            self.match(GrammarParser.EVENT)
            self.state = 390
            localctx.event_name = self.match(GrammarParser.ID)
            self.state = 393
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.NAMED:
                self.state = 391
                self.match(GrammarParser.NAMED)
                self.state = 392
                localctx.extra_name = self.match(GrammarParser.STRING)

            self.state = 395
            self.match(GrammarParser.SEMI)
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
            return self.getToken(GrammarParser.IMPORT, 0)

        def AS(self):
            return self.getToken(GrammarParser.AS, 0)

        def STRING(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.STRING)
            else:
                return self.getToken(GrammarParser.STRING, i)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def LBRACE(self):
            return self.getToken(GrammarParser.LBRACE, 0)

        def RBRACE(self):
            return self.getToken(GrammarParser.RBRACE, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def NAMED(self):
            return self.getToken(GrammarParser.NAMED, 0)

        def import_mapping_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Import_mapping_statementContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Import_mapping_statementContext, i
                )

        def getRuleIndex(self):
            return GrammarParser.RULE_import_statement

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImport_statement"):
                listener.enterImport_statement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImport_statement"):
                listener.exitImport_statement(self)

    def import_statement(self):

        localctx = GrammarParser.Import_statementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_import_statement)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 397
            self.match(GrammarParser.IMPORT)
            self.state = 398
            localctx.import_path = self.match(GrammarParser.STRING)
            self.state = 399
            self.match(GrammarParser.AS)
            self.state = 400
            localctx.state_alias = self.match(GrammarParser.ID)
            self.state = 403
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.NAMED:
                self.state = 401
                self.match(GrammarParser.NAMED)
                self.state = 402
                localctx.extra_name = self.match(GrammarParser.STRING)

            self.state = 414
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.LBRACE]:
                self.state = 405
                self.match(GrammarParser.LBRACE)
                self.state = 409
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while ((_la) & ~0x3F) == 0 and (
                    (1 << _la)
                    & (
                        (1 << GrammarParser.DEF)
                        | (1 << GrammarParser.EVENT)
                        | (1 << GrammarParser.SEMI)
                    )
                ) != 0:
                    self.state = 406
                    self.import_mapping_statement()
                    self.state = 411
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 412
                self.match(GrammarParser.RBRACE)
                pass
            elif token in [GrammarParser.SEMI]:
                self.state = 413
                self.match(GrammarParser.SEMI)
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
            return self.getTypedRuleContext(GrammarParser.Import_def_mappingContext, 0)

        def import_event_mapping(self):
            return self.getTypedRuleContext(
                GrammarParser.Import_event_mappingContext, 0
            )

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_import_mapping_statement

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImport_mapping_statement"):
                listener.enterImport_mapping_statement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImport_mapping_statement"):
                listener.exitImport_mapping_statement(self)

    def import_mapping_statement(self):

        localctx = GrammarParser.Import_mapping_statementContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 24, self.RULE_import_mapping_statement)
        try:
            self.state = 419
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.DEF]:
                self.enterOuterAlt(localctx, 1)
                self.state = 416
                self.import_def_mapping()
                pass
            elif token in [GrammarParser.EVENT]:
                self.enterOuterAlt(localctx, 2)
                self.state = 417
                self.import_event_mapping()
                pass
            elif token in [GrammarParser.SEMI]:
                self.enterOuterAlt(localctx, 3)
                self.state = 418
                self.match(GrammarParser.SEMI)
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
            return self.getToken(GrammarParser.DEF, 0)

        def import_def_selector(self):
            return self.getTypedRuleContext(GrammarParser.Import_def_selectorContext, 0)

        def ARROW(self):
            return self.getToken(GrammarParser.ARROW, 0)

        def import_def_target_template(self):
            return self.getTypedRuleContext(
                GrammarParser.Import_def_target_templateContext, 0
            )

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_import_def_mapping

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImport_def_mapping"):
                listener.enterImport_def_mapping(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImport_def_mapping"):
                listener.exitImport_def_mapping(self)

    def import_def_mapping(self):

        localctx = GrammarParser.Import_def_mappingContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_import_def_mapping)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 421
            self.match(GrammarParser.DEF)
            self.state = 422
            self.import_def_selector()
            self.state = 423
            self.match(GrammarParser.ARROW)
            self.state = 424
            self.import_def_target_template()
            self.state = 425
            self.match(GrammarParser.SEMI)
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
            return GrammarParser.RULE_import_def_selector

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class ImportDefFallbackSelectorContext(Import_def_selectorContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Import_def_selectorContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def STAR(self):
            return self.getToken(GrammarParser.STAR, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImportDefFallbackSelector"):
                listener.enterImportDefFallbackSelector(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImportDefFallbackSelector"):
                listener.exitImportDefFallbackSelector(self)

    class ImportDefPatternSelectorContext(Import_def_selectorContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Import_def_selectorContext
            super().__init__(parser)
            self.selector_pattern = None  # Token
            self.copyFrom(ctx)

        def IMPORT_DEF_SELECTOR_PATTERN(self):
            return self.getToken(GrammarParser.IMPORT_DEF_SELECTOR_PATTERN, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImportDefPatternSelector"):
                listener.enterImportDefPatternSelector(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImportDefPatternSelector"):
                listener.exitImportDefPatternSelector(self)

    class ImportDefExactSelectorContext(Import_def_selectorContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Import_def_selectorContext
            super().__init__(parser)
            self.selector_name = None  # Token
            self.copyFrom(ctx)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImportDefExactSelector"):
                listener.enterImportDefExactSelector(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImportDefExactSelector"):
                listener.exitImportDefExactSelector(self)

    class ImportDefSetSelectorContext(Import_def_selectorContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Import_def_selectorContext
            super().__init__(parser)
            self._ID = None  # Token
            self.selector_items = list()  # of Tokens
            self.copyFrom(ctx)

        def LBRACE(self):
            return self.getToken(GrammarParser.LBRACE, 0)

        def RBRACE(self):
            return self.getToken(GrammarParser.RBRACE, 0)

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.ID)
            else:
                return self.getToken(GrammarParser.ID, i)

        def COMMA(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.COMMA)
            else:
                return self.getToken(GrammarParser.COMMA, i)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImportDefSetSelector"):
                listener.enterImportDefSetSelector(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImportDefSetSelector"):
                listener.exitImportDefSetSelector(self)

    def import_def_selector(self):

        localctx = GrammarParser.Import_def_selectorContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_import_def_selector)
        self._la = 0  # Token type
        try:
            self.state = 440
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.STAR]:
                localctx = GrammarParser.ImportDefFallbackSelectorContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 427
                self.match(GrammarParser.STAR)
                pass
            elif token in [GrammarParser.LBRACE]:
                localctx = GrammarParser.ImportDefSetSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 428
                self.match(GrammarParser.LBRACE)
                self.state = 429
                localctx._ID = self.match(GrammarParser.ID)
                localctx.selector_items.append(localctx._ID)
                self.state = 434
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == GrammarParser.COMMA:
                    self.state = 430
                    self.match(GrammarParser.COMMA)
                    self.state = 431
                    localctx._ID = self.match(GrammarParser.ID)
                    localctx.selector_items.append(localctx._ID)
                    self.state = 436
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 437
                self.match(GrammarParser.RBRACE)
                pass
            elif token in [GrammarParser.IMPORT_DEF_SELECTOR_PATTERN]:
                localctx = GrammarParser.ImportDefPatternSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 438
                localctx.selector_pattern = self.match(
                    GrammarParser.IMPORT_DEF_SELECTOR_PATTERN
                )
                pass
            elif token in [GrammarParser.ID]:
                localctx = GrammarParser.ImportDefExactSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 439
                localctx.selector_name = self.match(GrammarParser.ID)
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
            return self.getToken(GrammarParser.ID, 0)

        def IMPORT_DEF_TARGET_TEMPLATE(self):
            return self.getToken(GrammarParser.IMPORT_DEF_TARGET_TEMPLATE, 0)

        def STAR(self):
            return self.getToken(GrammarParser.STAR, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_import_def_target_template

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImport_def_target_template"):
                listener.enterImport_def_target_template(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImport_def_target_template"):
                listener.exitImport_def_target_template(self)

    def import_def_target_template(self):

        localctx = GrammarParser.Import_def_target_templateContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 30, self.RULE_import_def_target_template)
        try:
            self.state = 445
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 442
                localctx.target_text = self.match(GrammarParser.ID)
                pass
            elif token in [GrammarParser.IMPORT_DEF_TARGET_TEMPLATE]:
                self.enterOuterAlt(localctx, 2)
                self.state = 443
                localctx.target_text = self.match(
                    GrammarParser.IMPORT_DEF_TARGET_TEMPLATE
                )
                pass
            elif token in [GrammarParser.STAR]:
                self.enterOuterAlt(localctx, 3)
                self.state = 444
                localctx.target_text = self.match(GrammarParser.STAR)
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
            return self.getToken(GrammarParser.EVENT, 0)

        def ARROW(self):
            return self.getToken(GrammarParser.ARROW, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def chain_id(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Chain_idContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Chain_idContext, i)

        def NAMED(self):
            return self.getToken(GrammarParser.NAMED, 0)

        def STRING(self):
            return self.getToken(GrammarParser.STRING, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_import_event_mapping

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterImport_event_mapping"):
                listener.enterImport_event_mapping(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitImport_event_mapping"):
                listener.exitImport_event_mapping(self)

    def import_event_mapping(self):

        localctx = GrammarParser.Import_event_mappingContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 32, self.RULE_import_event_mapping)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 447
            self.match(GrammarParser.EVENT)
            self.state = 448
            localctx.source_event = self.chain_id()
            self.state = 449
            self.match(GrammarParser.ARROW)
            self.state = 450
            localctx.target_event = self.chain_id()
            self.state = 453
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.NAMED:
                self.state = 451
                self.match(GrammarParser.NAMED)
                self.state = 452
                localctx.extra_name = self.match(GrammarParser.STRING)

            self.state = 455
            self.match(GrammarParser.SEMI)
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
            return self.getToken(GrammarParser.ID, 0)

        def ASSIGN(self):
            return self.getToken(GrammarParser.ASSIGN, 0)

        def num_expression(self):
            return self.getTypedRuleContext(GrammarParser.Num_expressionContext, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_operation_assignment

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterOperation_assignment"):
                listener.enterOperation_assignment(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitOperation_assignment"):
                listener.exitOperation_assignment(self)

    def operation_assignment(self):

        localctx = GrammarParser.Operation_assignmentContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 34, self.RULE_operation_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 457
            self.match(GrammarParser.ID)
            self.state = 458
            self.match(GrammarParser.ASSIGN)
            self.state = 459
            self.num_expression(0)
            self.state = 460
            self.match(GrammarParser.SEMI)
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
            return self.getToken(GrammarParser.LBRACE, 0)

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
            )

        def RBRACE(self):
            return self.getToken(GrammarParser.RBRACE, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_operation_block

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterOperation_block"):
                listener.enterOperation_block(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitOperation_block"):
                listener.exitOperation_block(self)

    def operation_block(self):

        localctx = GrammarParser.Operation_blockContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_operation_block)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 462
            self.match(GrammarParser.LBRACE)
            self.state = 463
            self.operational_statement_set()
            self.state = 464
            self.match(GrammarParser.RBRACE)
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
                return self.getTokens(GrammarParser.IF)
            else:
                return self.getToken(GrammarParser.IF, i)

        def LBRACK(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.LBRACK)
            else:
                return self.getToken(GrammarParser.LBRACK, i)

        def cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Cond_expressionContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, i)

        def RBRACK(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.RBRACK)
            else:
                return self.getToken(GrammarParser.RBRACK, i)

        def operation_block(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Operation_blockContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Operation_blockContext, i)

        def ELSE(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.ELSE)
            else:
                return self.getToken(GrammarParser.ELSE, i)

        def getRuleIndex(self):
            return GrammarParser.RULE_if_statement

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterIf_statement"):
                listener.enterIf_statement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitIf_statement"):
                listener.exitIf_statement(self)

    def if_statement(self):

        localctx = GrammarParser.If_statementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_if_statement)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 466
            self.match(GrammarParser.IF)
            self.state = 467
            self.match(GrammarParser.LBRACK)
            self.state = 468
            self.cond_expression(0)
            self.state = 469
            self.match(GrammarParser.RBRACK)
            self.state = 470
            self.operation_block()
            self.state = 480
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 48, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 471
                    self.match(GrammarParser.ELSE)
                    self.state = 472
                    self.match(GrammarParser.IF)
                    self.state = 473
                    self.match(GrammarParser.LBRACK)
                    self.state = 474
                    self.cond_expression(0)
                    self.state = 475
                    self.match(GrammarParser.RBRACK)
                    self.state = 476
                    self.operation_block()
                self.state = 482
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 48, self._ctx)

            self.state = 485
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.ELSE:
                self.state = 483
                self.match(GrammarParser.ELSE)
                self.state = 484
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
            return self.getTypedRuleContext(
                GrammarParser.Operation_assignmentContext, 0
            )

        def if_statement(self):
            return self.getTypedRuleContext(GrammarParser.If_statementContext, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_operational_statement

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterOperational_statement"):
                listener.enterOperational_statement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitOperational_statement"):
                listener.exitOperational_statement(self)

    def operational_statement(self):

        localctx = GrammarParser.Operational_statementContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 40, self.RULE_operational_statement)
        try:
            self.state = 490
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 487
                self.operation_assignment()
                pass
            elif token in [GrammarParser.IF]:
                self.enterOuterAlt(localctx, 2)
                self.state = 488
                self.if_statement()
                pass
            elif token in [GrammarParser.SEMI]:
                self.enterOuterAlt(localctx, 3)
                self.state = 489
                self.match(GrammarParser.SEMI)
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
                return self.getTypedRuleContexts(
                    GrammarParser.Operational_statementContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Operational_statementContext, i
                )

        def getRuleIndex(self):
            return GrammarParser.RULE_operational_statement_set

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterOperational_statement_set"):
                listener.enterOperational_statement_set(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitOperational_statement_set"):
                listener.exitOperational_statement_set(self)

    def operational_statement_set(self):

        localctx = GrammarParser.Operational_statement_setContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 42, self.RULE_operational_statement_set)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 495
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while ((_la - 16) & ~0x3F) == 0 and (
                (1 << (_la - 16))
                & (
                    (1 << (GrammarParser.IF - 16))
                    | (1 << (GrammarParser.SEMI - 16))
                    | (1 << (GrammarParser.ID - 16))
                )
            ) != 0:
                self.state = 492
                self.operational_statement()
                self.state = 497
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
            return self.getTypedRuleContext(GrammarParser.State_definitionContext, 0)

        def transition_definition(self):
            return self.getTypedRuleContext(
                GrammarParser.Transition_definitionContext, 0
            )

        def transition_force_definition(self):
            return self.getTypedRuleContext(
                GrammarParser.Transition_force_definitionContext, 0
            )

        def enter_definition(self):
            return self.getTypedRuleContext(GrammarParser.Enter_definitionContext, 0)

        def during_definition(self):
            return self.getTypedRuleContext(GrammarParser.During_definitionContext, 0)

        def exit_definition(self):
            return self.getTypedRuleContext(GrammarParser.Exit_definitionContext, 0)

        def during_aspect_definition(self):
            return self.getTypedRuleContext(
                GrammarParser.During_aspect_definitionContext, 0
            )

        def event_definition(self):
            return self.getTypedRuleContext(GrammarParser.Event_definitionContext, 0)

        def import_statement(self):
            return self.getTypedRuleContext(GrammarParser.Import_statementContext, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_state_inner_statement

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterState_inner_statement"):
                listener.enterState_inner_statement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitState_inner_statement"):
                listener.exitState_inner_statement(self)

    def state_inner_statement(self):

        localctx = GrammarParser.State_inner_statementContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 44, self.RULE_state_inner_statement)
        try:
            self.state = 508
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.PSEUDO, GrammarParser.STATE]:
                self.enterOuterAlt(localctx, 1)
                self.state = 498
                self.state_definition()
                pass
            elif token in [GrammarParser.INIT_MARKER, GrammarParser.ID]:
                self.enterOuterAlt(localctx, 2)
                self.state = 499
                self.transition_definition()
                pass
            elif token in [GrammarParser.BANG]:
                self.enterOuterAlt(localctx, 3)
                self.state = 500
                self.transition_force_definition()
                pass
            elif token in [GrammarParser.ENTER]:
                self.enterOuterAlt(localctx, 4)
                self.state = 501
                self.enter_definition()
                pass
            elif token in [GrammarParser.DURING]:
                self.enterOuterAlt(localctx, 5)
                self.state = 502
                self.during_definition()
                pass
            elif token in [GrammarParser.EXIT]:
                self.enterOuterAlt(localctx, 6)
                self.state = 503
                self.exit_definition()
                pass
            elif token in [GrammarParser.SHIFT_RIGHT]:
                self.enterOuterAlt(localctx, 7)
                self.state = 504
                self.during_aspect_definition()
                pass
            elif token in [GrammarParser.EVENT]:
                self.enterOuterAlt(localctx, 8)
                self.state = 505
                self.event_definition()
                pass
            elif token in [GrammarParser.IMPORT]:
                self.enterOuterAlt(localctx, 9)
                self.state = 506
                self.import_statement()
                pass
            elif token in [GrammarParser.SEMI]:
                self.enterOuterAlt(localctx, 10)
                self.state = 507
                self.match(GrammarParser.SEMI)
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
            return self.getToken(GrammarParser.EOF, 0)

        def operational_assignment(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Operational_assignmentContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Operational_assignmentContext, i
                )

        def getRuleIndex(self):
            return GrammarParser.RULE_operation_program

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterOperation_program"):
                listener.enterOperation_program(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitOperation_program"):
                listener.exitOperation_program(self)

    def operation_program(self):

        localctx = GrammarParser.Operation_programContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_operation_program)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 513
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 510
                self.operational_assignment()
                self.state = 515
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 516
            self.match(GrammarParser.EOF)
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
            return self.getToken(GrammarParser.EOF, 0)

        def preamble_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Preamble_statementContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Preamble_statementContext, i
                )

        def getRuleIndex(self):
            return GrammarParser.RULE_preamble_program

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterPreamble_program"):
                listener.enterPreamble_program(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitPreamble_program"):
                listener.exitPreamble_program(self)

    def preamble_program(self):

        localctx = GrammarParser.Preamble_programContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_preamble_program)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 521
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 518
                self.preamble_statement()
                self.state = 523
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 524
            self.match(GrammarParser.EOF)
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
            return self.getTypedRuleContext(GrammarParser.Initial_assignmentContext, 0)

        def constant_definition(self):
            return self.getTypedRuleContext(GrammarParser.Constant_definitionContext, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_preamble_statement

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterPreamble_statement"):
                listener.enterPreamble_statement(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitPreamble_statement"):
                listener.exitPreamble_statement(self)

    def preamble_statement(self):

        localctx = GrammarParser.Preamble_statementContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_preamble_statement)
        try:
            self.state = 528
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 55, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 526
                self.initial_assignment()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 527
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
            return self.getToken(GrammarParser.ID, 0)

        def DECLARE_ASSIGN(self):
            return self.getToken(GrammarParser.DECLARE_ASSIGN, 0)

        def init_expression(self):
            return self.getTypedRuleContext(GrammarParser.Init_expressionContext, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_initial_assignment

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterInitial_assignment"):
                listener.enterInitial_assignment(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitInitial_assignment"):
                listener.exitInitial_assignment(self)

    def initial_assignment(self):

        localctx = GrammarParser.Initial_assignmentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_initial_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 530
            self.match(GrammarParser.ID)
            self.state = 531
            self.match(GrammarParser.DECLARE_ASSIGN)
            self.state = 532
            self.init_expression(0)
            self.state = 533
            self.match(GrammarParser.SEMI)
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
            return self.getToken(GrammarParser.ID, 0)

        def ASSIGN(self):
            return self.getToken(GrammarParser.ASSIGN, 0)

        def init_expression(self):
            return self.getTypedRuleContext(GrammarParser.Init_expressionContext, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_constant_definition

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterConstant_definition"):
                listener.enterConstant_definition(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitConstant_definition"):
                listener.exitConstant_definition(self)

    def constant_definition(self):

        localctx = GrammarParser.Constant_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_constant_definition)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 535
            self.match(GrammarParser.ID)
            self.state = 536
            self.match(GrammarParser.ASSIGN)
            self.state = 537
            self.init_expression(0)
            self.state = 538
            self.match(GrammarParser.SEMI)
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
            return self.getToken(GrammarParser.ID, 0)

        def DECLARE_ASSIGN(self):
            return self.getToken(GrammarParser.DECLARE_ASSIGN, 0)

        def num_expression(self):
            return self.getTypedRuleContext(GrammarParser.Num_expressionContext, 0)

        def SEMI(self):
            return self.getToken(GrammarParser.SEMI, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_operational_assignment

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterOperational_assignment"):
                listener.enterOperational_assignment(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitOperational_assignment"):
                listener.exitOperational_assignment(self)

    def operational_assignment(self):

        localctx = GrammarParser.Operational_assignmentContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 56, self.RULE_operational_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 540
            self.match(GrammarParser.ID)
            self.state = 541
            self.match(GrammarParser.DECLARE_ASSIGN)
            self.state = 542
            self.num_expression(0)
            self.state = 543
            self.match(GrammarParser.SEMI)
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
            return self.getTypedRuleContext(GrammarParser.Num_expressionContext, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_generic_expression

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterGeneric_expression"):
                listener.enterGeneric_expression(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitGeneric_expression"):
                listener.exitGeneric_expression(self)

    def generic_expression(self):

        localctx = GrammarParser.Generic_expressionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_generic_expression)
        try:
            self.state = 547
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 56, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 545
                self.num_expression(0)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 546
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
            return GrammarParser.RULE_init_expression

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class FuncExprInitContext(Init_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Init_expressionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(GrammarParser.LPAREN, 0)

        def init_expression(self):
            return self.getTypedRuleContext(GrammarParser.Init_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(GrammarParser.RPAREN, 0)

        def UFUNC_NAME(self):
            return self.getToken(GrammarParser.UFUNC_NAME, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterFuncExprInit"):
                listener.enterFuncExprInit(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitFuncExprInit"):
                listener.exitFuncExprInit(self)

    class UnaryExprInitContext(Init_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Init_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def init_expression(self):
            return self.getTypedRuleContext(GrammarParser.Init_expressionContext, 0)

        def PLUS(self):
            return self.getToken(GrammarParser.PLUS, 0)

        def MINUS(self):
            return self.getToken(GrammarParser.MINUS, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterUnaryExprInit"):
                listener.enterUnaryExprInit(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitUnaryExprInit"):
                listener.exitUnaryExprInit(self)

    class BinaryExprInitContext(Init_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Init_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def init_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Init_expressionContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Init_expressionContext, i)

        def POW(self):
            return self.getToken(GrammarParser.POW, 0)

        def STAR(self):
            return self.getToken(GrammarParser.STAR, 0)

        def SLASH(self):
            return self.getToken(GrammarParser.SLASH, 0)

        def PERCENT(self):
            return self.getToken(GrammarParser.PERCENT, 0)

        def PLUS(self):
            return self.getToken(GrammarParser.PLUS, 0)

        def MINUS(self):
            return self.getToken(GrammarParser.MINUS, 0)

        def SHIFT_LEFT(self):
            return self.getToken(GrammarParser.SHIFT_LEFT, 0)

        def SHIFT_RIGHT(self):
            return self.getToken(GrammarParser.SHIFT_RIGHT, 0)

        def AMP(self):
            return self.getToken(GrammarParser.AMP, 0)

        def CARET(self):
            return self.getToken(GrammarParser.CARET, 0)

        def PIPE(self):
            return self.getToken(GrammarParser.PIPE, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprInit"):
                listener.enterBinaryExprInit(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprInit"):
                listener.exitBinaryExprInit(self)

    class LiteralExprInitContext(Init_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Init_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def num_literal(self):
            return self.getTypedRuleContext(GrammarParser.Num_literalContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLiteralExprInit"):
                listener.enterLiteralExprInit(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLiteralExprInit"):
                listener.exitLiteralExprInit(self)

    class MathConstExprInitContext(Init_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Init_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def math_const(self):
            return self.getTypedRuleContext(GrammarParser.Math_constContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterMathConstExprInit"):
                listener.enterMathConstExprInit(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitMathConstExprInit"):
                listener.exitMathConstExprInit(self)

    class ParenExprInitContext(Init_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Init_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(GrammarParser.LPAREN, 0)

        def init_expression(self):
            return self.getTypedRuleContext(GrammarParser.Init_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(GrammarParser.RPAREN, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterParenExprInit"):
                listener.enterParenExprInit(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitParenExprInit"):
                listener.exitParenExprInit(self)

    def init_expression(self, _p: int = 0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = GrammarParser.Init_expressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 60
        self.enterRecursionRule(localctx, 60, self.RULE_init_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 563
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.LPAREN]:
                localctx = GrammarParser.ParenExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 550
                self.match(GrammarParser.LPAREN)
                self.state = 551
                self.init_expression(0)
                self.state = 552
                self.match(GrammarParser.RPAREN)
                pass
            elif token in [
                GrammarParser.FLOAT,
                GrammarParser.HEX_INT,
                GrammarParser.INT,
            ]:
                localctx = GrammarParser.LiteralExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 554
                self.num_literal()
                pass
            elif token in [
                GrammarParser.PI_CONST,
                GrammarParser.E_CONST,
                GrammarParser.TAU_CONST,
            ]:
                localctx = GrammarParser.MathConstExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 555
                self.math_const()
                pass
            elif token in [GrammarParser.PLUS, GrammarParser.MINUS]:
                localctx = GrammarParser.UnaryExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 556
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.PLUS or _la == GrammarParser.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 557
                self.init_expression(9)
                pass
            elif token in [GrammarParser.UFUNC_NAME]:
                localctx = GrammarParser.FuncExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 558
                localctx.func_name = self.match(GrammarParser.UFUNC_NAME)
                self.state = 559
                self.match(GrammarParser.LPAREN)
                self.state = 560
                self.init_expression(0)
                self.state = 561
                self.match(GrammarParser.RPAREN)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 588
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 59, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 586
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 58, self._ctx)
                    if la_ == 1:
                        localctx = GrammarParser.BinaryExprInitContext(
                            self,
                            GrammarParser.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 565
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 566
                        localctx.op = self.match(GrammarParser.POW)
                        self.state = 567
                        self.init_expression(8)
                        pass

                    elif la_ == 2:
                        localctx = GrammarParser.BinaryExprInitContext(
                            self,
                            GrammarParser.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 568
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 569
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la) & ~0x3F) == 0
                            and (
                                (1 << _la)
                                & (
                                    (1 << GrammarParser.SLASH)
                                    | (1 << GrammarParser.STAR)
                                    | (1 << GrammarParser.PERCENT)
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 570
                        self.init_expression(8)
                        pass

                    elif la_ == 3:
                        localctx = GrammarParser.BinaryExprInitContext(
                            self,
                            GrammarParser.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 571
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 572
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.PLUS or _la == GrammarParser.MINUS
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 573
                        self.init_expression(7)
                        pass

                    elif la_ == 4:
                        localctx = GrammarParser.BinaryExprInitContext(
                            self,
                            GrammarParser.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 574
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 575
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.SHIFT_RIGHT
                            or _la == GrammarParser.SHIFT_LEFT
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 576
                        self.init_expression(6)
                        pass

                    elif la_ == 5:
                        localctx = GrammarParser.BinaryExprInitContext(
                            self,
                            GrammarParser.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 577
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 578
                        localctx.op = self.match(GrammarParser.AMP)
                        self.state = 579
                        self.init_expression(5)
                        pass

                    elif la_ == 6:
                        localctx = GrammarParser.BinaryExprInitContext(
                            self,
                            GrammarParser.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 580
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 581
                        localctx.op = self.match(GrammarParser.CARET)
                        self.state = 582
                        self.init_expression(4)
                        pass

                    elif la_ == 7:
                        localctx = GrammarParser.BinaryExprInitContext(
                            self,
                            GrammarParser.Init_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_init_expression
                        )
                        self.state = 583
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 584
                        localctx.op = self.match(GrammarParser.PIPE)
                        self.state = 585
                        self.init_expression(3)
                        pass

                self.state = 590
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
            return GrammarParser.RULE_num_expression

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class UnaryExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Num_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def num_expression(self):
            return self.getTypedRuleContext(GrammarParser.Num_expressionContext, 0)

        def PLUS(self):
            return self.getToken(GrammarParser.PLUS, 0)

        def MINUS(self):
            return self.getToken(GrammarParser.MINUS, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterUnaryExprNum"):
                listener.enterUnaryExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitUnaryExprNum"):
                listener.exitUnaryExprNum(self)

    class FuncExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Num_expressionContext
            super().__init__(parser)
            self.func_name = None  # Token
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(GrammarParser.LPAREN, 0)

        def num_expression(self):
            return self.getTypedRuleContext(GrammarParser.Num_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(GrammarParser.RPAREN, 0)

        def UFUNC_NAME(self):
            return self.getToken(GrammarParser.UFUNC_NAME, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterFuncExprNum"):
                listener.enterFuncExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitFuncExprNum"):
                listener.exitFuncExprNum(self)

    class ConditionalCStyleExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(GrammarParser.LPAREN, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(GrammarParser.RPAREN, 0)

        def QUESTION(self):
            return self.getToken(GrammarParser.QUESTION, 0)

        def num_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Num_expressionContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Num_expressionContext, i)

        def COLON(self):
            return self.getToken(GrammarParser.COLON, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterConditionalCStyleExprNum"):
                listener.enterConditionalCStyleExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitConditionalCStyleExprNum"):
                listener.exitConditionalCStyleExprNum(self)

    class BinaryExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Num_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def num_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Num_expressionContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Num_expressionContext, i)

        def POW(self):
            return self.getToken(GrammarParser.POW, 0)

        def STAR(self):
            return self.getToken(GrammarParser.STAR, 0)

        def SLASH(self):
            return self.getToken(GrammarParser.SLASH, 0)

        def PERCENT(self):
            return self.getToken(GrammarParser.PERCENT, 0)

        def PLUS(self):
            return self.getToken(GrammarParser.PLUS, 0)

        def MINUS(self):
            return self.getToken(GrammarParser.MINUS, 0)

        def SHIFT_LEFT(self):
            return self.getToken(GrammarParser.SHIFT_LEFT, 0)

        def SHIFT_RIGHT(self):
            return self.getToken(GrammarParser.SHIFT_RIGHT, 0)

        def AMP(self):
            return self.getToken(GrammarParser.AMP, 0)

        def CARET(self):
            return self.getToken(GrammarParser.CARET, 0)

        def PIPE(self):
            return self.getToken(GrammarParser.PIPE, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprNum"):
                listener.enterBinaryExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprNum"):
                listener.exitBinaryExprNum(self)

    class LiteralExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def num_literal(self):
            return self.getTypedRuleContext(GrammarParser.Num_literalContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLiteralExprNum"):
                listener.enterLiteralExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLiteralExprNum"):
                listener.exitLiteralExprNum(self)

    class MathConstExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def math_const(self):
            return self.getTypedRuleContext(GrammarParser.Math_constContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterMathConstExprNum"):
                listener.enterMathConstExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitMathConstExprNum"):
                listener.exitMathConstExprNum(self)

    class ParenExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(GrammarParser.LPAREN, 0)

        def num_expression(self):
            return self.getTypedRuleContext(GrammarParser.Num_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(GrammarParser.RPAREN, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterParenExprNum"):
                listener.enterParenExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitParenExprNum"):
                listener.exitParenExprNum(self)

    class IdExprNumContext(Num_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Num_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterIdExprNum"):
                listener.enterIdExprNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitIdExprNum"):
                listener.exitIdExprNum(self)

    def num_expression(self, _p: int = 0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = GrammarParser.Num_expressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 62
        self.enterRecursionRule(localctx, 62, self.RULE_num_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 614
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 60, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 592
                self.match(GrammarParser.LPAREN)
                self.state = 593
                self.num_expression(0)
                self.state = 594
                self.match(GrammarParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 596
                self.num_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.IdExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 597
                self.match(GrammarParser.ID)
                pass

            elif la_ == 4:
                localctx = GrammarParser.MathConstExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 598
                self.math_const()
                pass

            elif la_ == 5:
                localctx = GrammarParser.UnaryExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 599
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.PLUS or _la == GrammarParser.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 600
                self.num_expression(10)
                pass

            elif la_ == 6:
                localctx = GrammarParser.FuncExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 601
                localctx.func_name = self.match(GrammarParser.UFUNC_NAME)
                self.state = 602
                self.match(GrammarParser.LPAREN)
                self.state = 603
                self.num_expression(0)
                self.state = 604
                self.match(GrammarParser.RPAREN)
                pass

            elif la_ == 7:
                localctx = GrammarParser.ConditionalCStyleExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 606
                self.match(GrammarParser.LPAREN)
                self.state = 607
                self.cond_expression(0)
                self.state = 608
                self.match(GrammarParser.RPAREN)
                self.state = 609
                self.match(GrammarParser.QUESTION)
                self.state = 610
                self.num_expression(0)
                self.state = 611
                self.match(GrammarParser.COLON)
                self.state = 612
                self.num_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 639
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 62, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 637
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 61, self._ctx)
                    if la_ == 1:
                        localctx = GrammarParser.BinaryExprNumContext(
                            self,
                            GrammarParser.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 616
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 9)"
                            )
                        self.state = 617
                        localctx.op = self.match(GrammarParser.POW)
                        self.state = 618
                        self.num_expression(9)
                        pass

                    elif la_ == 2:
                        localctx = GrammarParser.BinaryExprNumContext(
                            self,
                            GrammarParser.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 619
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 620
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la) & ~0x3F) == 0
                            and (
                                (1 << _la)
                                & (
                                    (1 << GrammarParser.SLASH)
                                    | (1 << GrammarParser.STAR)
                                    | (1 << GrammarParser.PERCENT)
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 621
                        self.num_expression(9)
                        pass

                    elif la_ == 3:
                        localctx = GrammarParser.BinaryExprNumContext(
                            self,
                            GrammarParser.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 622
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 623
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.PLUS or _la == GrammarParser.MINUS
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 624
                        self.num_expression(8)
                        pass

                    elif la_ == 4:
                        localctx = GrammarParser.BinaryExprNumContext(
                            self,
                            GrammarParser.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 625
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 626
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.SHIFT_RIGHT
                            or _la == GrammarParser.SHIFT_LEFT
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 627
                        self.num_expression(7)
                        pass

                    elif la_ == 5:
                        localctx = GrammarParser.BinaryExprNumContext(
                            self,
                            GrammarParser.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 628
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 629
                        localctx.op = self.match(GrammarParser.AMP)
                        self.state = 630
                        self.num_expression(6)
                        pass

                    elif la_ == 6:
                        localctx = GrammarParser.BinaryExprNumContext(
                            self,
                            GrammarParser.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 631
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 632
                        localctx.op = self.match(GrammarParser.CARET)
                        self.state = 633
                        self.num_expression(5)
                        pass

                    elif la_ == 7:
                        localctx = GrammarParser.BinaryExprNumContext(
                            self,
                            GrammarParser.Num_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_num_expression
                        )
                        self.state = 634
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 635
                        localctx.op = self.match(GrammarParser.PIPE)
                        self.state = 636
                        self.num_expression(4)
                        pass

                self.state = 641
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
            return GrammarParser.RULE_cond_expression

        def copyFrom(self, ctx: ParserRuleContext):
            super().copyFrom(ctx)

    class BinaryExprFromCondCondContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Cond_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Cond_expressionContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, i)

        def EQ(self):
            return self.getToken(GrammarParser.EQ, 0)

        def NE(self):
            return self.getToken(GrammarParser.NE, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprFromCondCond"):
                listener.enterBinaryExprFromCondCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprFromCondCond"):
                listener.exitBinaryExprFromCondCond(self)

    class BinaryExprCondContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Cond_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Cond_expressionContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, i)

        def LOGICAL_AND(self):
            return self.getToken(GrammarParser.LOGICAL_AND, 0)

        def AND_KW(self):
            return self.getToken(GrammarParser.AND_KW, 0)

        def LOGICAL_OR(self):
            return self.getToken(GrammarParser.LOGICAL_OR, 0)

        def OR_KW(self):
            return self.getToken(GrammarParser.OR_KW, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprCond"):
                listener.enterBinaryExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprCond"):
                listener.exitBinaryExprCond(self)

    class BinaryExprFromNumCondContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Cond_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def num_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Num_expressionContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Num_expressionContext, i)

        def LT(self):
            return self.getToken(GrammarParser.LT, 0)

        def GT(self):
            return self.getToken(GrammarParser.GT, 0)

        def LE(self):
            return self.getToken(GrammarParser.LE, 0)

        def GE(self):
            return self.getToken(GrammarParser.GE, 0)

        def EQ(self):
            return self.getToken(GrammarParser.EQ, 0)

        def NE(self):
            return self.getToken(GrammarParser.NE, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBinaryExprFromNumCond"):
                listener.enterBinaryExprFromNumCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBinaryExprFromNumCond"):
                listener.exitBinaryExprFromNumCond(self)

    class UnaryExprCondContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Cond_expressionContext
            super().__init__(parser)
            self.op = None  # Token
            self.copyFrom(ctx)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def BANG(self):
            return self.getToken(GrammarParser.BANG, 0)

        def NOT_KW(self):
            return self.getToken(GrammarParser.NOT_KW, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterUnaryExprCond"):
                listener.enterUnaryExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitUnaryExprCond"):
                listener.exitUnaryExprCond(self)

    class ParenExprCondContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Cond_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(GrammarParser.LPAREN, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(GrammarParser.RPAREN, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterParenExprCond"):
                listener.enterParenExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitParenExprCond"):
                listener.exitParenExprCond(self)

    class LiteralExprCondContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Cond_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def bool_literal(self):
            return self.getTypedRuleContext(GrammarParser.Bool_literalContext, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLiteralExprCond"):
                listener.enterLiteralExprCond(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLiteralExprCond"):
                listener.exitLiteralExprCond(self)

    class ConditionalCStyleCondNumContext(Cond_expressionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Cond_expressionContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(GrammarParser.LPAREN, 0)

        def cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Cond_expressionContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, i)

        def RPAREN(self):
            return self.getToken(GrammarParser.RPAREN, 0)

        def QUESTION(self):
            return self.getToken(GrammarParser.QUESTION, 0)

        def COLON(self):
            return self.getToken(GrammarParser.COLON, 0)

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterConditionalCStyleCondNum"):
                listener.enterConditionalCStyleCondNum(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitConditionalCStyleCondNum"):
                listener.exitConditionalCStyleCondNum(self)

    def cond_expression(self, _p: int = 0):
        _parentctx = self._ctx
        _parentState = self.state
        localctx = GrammarParser.Cond_expressionContext(self, self._ctx, _parentState)
        _prevctx = localctx
        _startState = 64
        self.enterRecursionRule(localctx, 64, self.RULE_cond_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 666
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 63, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 643
                self.match(GrammarParser.LPAREN)
                self.state = 644
                self.cond_expression(0)
                self.state = 645
                self.match(GrammarParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 647
                self.bool_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.UnaryExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 648
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.NOT_KW or _la == GrammarParser.BANG):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 649
                self.cond_expression(7)
                pass

            elif la_ == 4:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 650
                self.num_expression(0)
                self.state = 651
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (
                    ((_la) & ~0x3F) == 0
                    and (
                        (1 << _la)
                        & (
                            (1 << GrammarParser.LE)
                            | (1 << GrammarParser.GE)
                            | (1 << GrammarParser.LT)
                            | (1 << GrammarParser.GT)
                        )
                    )
                    != 0
                ):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 652
                self.num_expression(0)
                pass

            elif la_ == 5:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 654
                self.num_expression(0)
                self.state = 655
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.EQ or _la == GrammarParser.NE):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 656
                self.num_expression(0)
                pass

            elif la_ == 6:
                localctx = GrammarParser.ConditionalCStyleCondNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 658
                self.match(GrammarParser.LPAREN)
                self.state = 659
                self.cond_expression(0)
                self.state = 660
                self.match(GrammarParser.RPAREN)
                self.state = 661
                self.match(GrammarParser.QUESTION)
                self.state = 662
                self.cond_expression(0)
                self.state = 663
                self.match(GrammarParser.COLON)
                self.state = 664
                self.cond_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 679
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 65, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 677
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 64, self._ctx)
                    if la_ == 1:
                        localctx = GrammarParser.BinaryExprFromCondCondContext(
                            self,
                            GrammarParser.Cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_cond_expression
                        )
                        self.state = 668
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 669
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (_la == GrammarParser.EQ or _la == GrammarParser.NE):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 670
                        self.cond_expression(5)
                        pass

                    elif la_ == 2:
                        localctx = GrammarParser.BinaryExprCondContext(
                            self,
                            GrammarParser.Cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_cond_expression
                        )
                        self.state = 671
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 672
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.AND_KW
                            or _la == GrammarParser.LOGICAL_AND
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 673
                        self.cond_expression(4)
                        pass

                    elif la_ == 3:
                        localctx = GrammarParser.BinaryExprCondContext(
                            self,
                            GrammarParser.Cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_cond_expression
                        )
                        self.state = 674
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 675
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.OR_KW
                            or _la == GrammarParser.LOGICAL_OR
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 676
                        self.cond_expression(3)
                        pass

                self.state = 681
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
            return self.getToken(GrammarParser.INT, 0)

        def FLOAT(self):
            return self.getToken(GrammarParser.FLOAT, 0)

        def HEX_INT(self):
            return self.getToken(GrammarParser.HEX_INT, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_num_literal

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterNum_literal"):
                listener.enterNum_literal(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitNum_literal"):
                listener.exitNum_literal(self)

    def num_literal(self):

        localctx = GrammarParser.Num_literalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 66, self.RULE_num_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 682
            _la = self._input.LA(1)
            if not (
                ((_la - 62) & ~0x3F) == 0
                and (
                    (1 << (_la - 62))
                    & (
                        (1 << (GrammarParser.FLOAT - 62))
                        | (1 << (GrammarParser.HEX_INT - 62))
                        | (1 << (GrammarParser.INT - 62))
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
            return self.getToken(GrammarParser.TRUE, 0)

        def FALSE(self):
            return self.getToken(GrammarParser.FALSE, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_bool_literal

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterBool_literal"):
                listener.enterBool_literal(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitBool_literal"):
                listener.exitBool_literal(self)

    def bool_literal(self):

        localctx = GrammarParser.Bool_literalContext(self, self._ctx, self.state)
        self.enterRule(localctx, 68, self.RULE_bool_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 684
            _la = self._input.LA(1)
            if not (_la == GrammarParser.TRUE or _la == GrammarParser.FALSE):
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
            return self.getToken(GrammarParser.PI_CONST, 0)

        def E_CONST(self):
            return self.getToken(GrammarParser.E_CONST, 0)

        def TAU_CONST(self):
            return self.getToken(GrammarParser.TAU_CONST, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_math_const

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterMath_const"):
                listener.enterMath_const(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitMath_const"):
                listener.exitMath_const(self)

    def math_const(self):

        localctx = GrammarParser.Math_constContext(self, self._ctx, self.state)
        self.enterRule(localctx, 70, self.RULE_math_const)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 686
            _la = self._input.LA(1)
            if not (
                ((_la) & ~0x3F) == 0
                and (
                    (1 << _la)
                    & (
                        (1 << GrammarParser.PI_CONST)
                        | (1 << GrammarParser.E_CONST)
                        | (1 << GrammarParser.TAU_CONST)
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
                return self.getTokens(GrammarParser.ID)
            else:
                return self.getToken(GrammarParser.ID, i)

        def DOT(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.DOT)
            else:
                return self.getToken(GrammarParser.DOT, i)

        def SLASH(self):
            return self.getToken(GrammarParser.SLASH, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_chain_id

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterChain_id"):
                listener.enterChain_id(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitChain_id"):
                listener.exitChain_id(self)

    def chain_id(self):

        localctx = GrammarParser.Chain_idContext(self, self._ctx, self.state)
        self.enterRule(localctx, 72, self.RULE_chain_id)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 689
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.SLASH:
                self.state = 688
                localctx.isabs = self.match(GrammarParser.SLASH)

            self.state = 691
            self.match(GrammarParser.ID)
            self.state = 696
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.DOT:
                self.state = 692
                self.match(GrammarParser.DOT)
                self.state = 693
                self.match(GrammarParser.ID)
                self.state = 698
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
