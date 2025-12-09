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
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3F")
        buf.write("\u0267\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7")
        buf.write("\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r\4\16")
        buf.write("\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23\t\23")
        buf.write("\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30\4\31")
        buf.write("\t\31\4\32\t\32\4\33\t\33\4\34\t\34\3\2\3\2\3\2\3\3\7")
        buf.write("\3=\n\3\f\3\16\3@\13\3\3\3\3\3\3\3\3\4\3\4\3\4\3\4\3\4")
        buf.write("\3\4\3\4\3\5\5\5M\n\5\3\5\3\5\3\5\3\5\5\5S\n\5\3\5\3\5")
        buf.write("\5\5W\n\5\3\5\3\5\3\5\3\5\5\5]\n\5\3\5\3\5\7\5a\n\5\f")
        buf.write("\5\16\5d\13\5\3\5\5\5g\n\5\3\6\3\6\3\6\3\6\3\6\3\6\3\6")
        buf.write("\3\6\3\6\3\6\3\6\3\6\5\6u\n\6\3\6\3\6\3\6\3\6\7\6{\n\6")
        buf.write("\f\6\16\6~\13\6\3\6\5\6\u0081\n\6\3\6\3\6\3\6\3\6\3\6")
        buf.write("\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u0091\n\6\3\6")
        buf.write("\3\6\3\6\3\6\7\6\u0097\n\6\f\6\16\6\u009a\13\6\3\6\5\6")
        buf.write("\u009d\n\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6")
        buf.write("\3\6\3\6\3\6\5\6\u00ad\n\6\3\6\3\6\3\6\3\6\7\6\u00b3\n")
        buf.write("\6\f\6\16\6\u00b6\13\6\3\6\5\6\u00b9\n\6\5\6\u00bb\n\6")
        buf.write("\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3")
        buf.write("\7\3\7\5\7\u00cc\n\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3")
        buf.write("\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\5\7\u00de\n\7\3\7\3\7\3")
        buf.write("\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\5\7\u00ee")
        buf.write("\n\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3")
        buf.write("\7\3\7\5\7\u00fe\n\7\3\7\5\7\u0101\n\7\3\b\3\b\5\b\u0105")
        buf.write("\n\b\3\b\3\b\7\b\u0109\n\b\f\b\16\b\u010c\13\b\3\b\3\b")
        buf.write("\3\b\3\b\3\b\3\b\3\b\3\b\5\b\u0116\n\b\3\b\3\b\3\b\5\b")
        buf.write("\u011b\n\b\3\b\3\b\3\b\3\b\5\b\u0121\n\b\3\t\3\t\5\t\u0125")
        buf.write("\n\t\3\t\3\t\7\t\u0129\n\t\f\t\16\t\u012c\13\t\3\t\3\t")
        buf.write("\3\t\3\t\3\t\3\t\3\t\3\t\5\t\u0136\n\t\3\t\3\t\3\t\5\t")
        buf.write("\u013b\n\t\3\t\3\t\3\t\3\t\5\t\u0141\n\t\3\n\3\n\5\n\u0145")
        buf.write("\n\n\3\n\5\n\u0148\n\n\3\n\3\n\7\n\u014c\n\n\f\n\16\n")
        buf.write("\u014f\13\n\3\n\3\n\3\n\5\n\u0154\n\n\3\n\3\n\3\n\3\n")
        buf.write("\3\n\5\n\u015b\n\n\3\n\3\n\5\n\u015f\n\n\3\n\3\n\3\n\5")
        buf.write("\n\u0164\n\n\3\n\5\n\u0167\n\n\3\n\3\n\3\n\3\n\5\n\u016d")
        buf.write("\n\n\3\13\3\13\3\13\3\13\5\13\u0173\n\13\3\13\3\13\7\13")
        buf.write("\u0177\n\13\f\13\16\13\u017a\13\13\3\13\3\13\3\13\3\13")
        buf.write("\3\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13\5\13\u0188\n")
        buf.write("\13\3\13\3\13\3\13\3\13\3\13\5\13\u018f\n\13\3\13\3\13")
        buf.write("\3\13\3\13\5\13\u0195\n\13\3\f\3\f\3\f\3\f\3\f\3\r\3\r")
        buf.write("\5\r\u019e\n\r\3\16\3\16\3\16\3\16\3\16\3\16\3\16\3\16")
        buf.write("\5\16\u01a8\n\16\3\17\7\17\u01ab\n\17\f\17\16\17\u01ae")
        buf.write("\13\17\3\17\3\17\3\20\7\20\u01b3\n\20\f\20\16\20\u01b6")
        buf.write("\13\20\3\20\3\20\3\21\3\21\5\21\u01bc\n\21\3\22\3\22\3")
        buf.write("\22\3\22\3\22\3\23\3\23\3\23\3\23\3\23\3\24\3\24\3\24")
        buf.write("\3\24\3\24\3\25\3\25\5\25\u01cf\n\25\3\26\3\26\3\26\3")
        buf.write("\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26")
        buf.write("\5\26\u01df\n\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3")
        buf.write("\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26")
        buf.write("\3\26\3\26\3\26\7\26\u01f6\n\26\f\26\16\26\u01f9\13\26")
        buf.write("\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\5\27\u0212\n\27\3\27\3\27\3\27\3\27\3\27\3\27\3")
        buf.write("\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\3\27\7\27\u0229\n\27\f\27\16\27\u022c")
        buf.write("\13\27\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3")
        buf.write("\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30")
        buf.write("\3\30\3\30\3\30\3\30\5\30\u0246\n\30\3\30\3\30\3\30\3")
        buf.write("\30\3\30\3\30\3\30\3\30\3\30\7\30\u0251\n\30\f\30\16\30")
        buf.write("\u0254\13\30\3\31\3\31\3\32\3\32\3\33\3\33\3\34\5\34\u025d")
        buf.write("\n\34\3\34\3\34\3\34\7\34\u0262\n\34\f\34\16\34\u0265")
        buf.write("\13\34\3\34\2\5*,.\35\2\4\6\b\n\f\16\20\22\24\26\30\32")
        buf.write('\34\36 "$&(*,.\60\62\64\66\2\20\3\2\4\5\3\2\17\20\3\2')
        buf.write("\34\35\3\2\"#\4\2\26\26%&\4\2\36\36''\4\2\25\25,,\3")
        buf.write("\2-\60\3\2\61\62\3\2\63\64\3\2\65\66\3\2;=\3\2>?\3\2\67")
        buf.write("9\2\u02bd\28\3\2\2\2\4>\3\2\2\2\6D\3\2\2\2\bf\3\2\2\2")
        buf.write("\n\u00ba\3\2\2\2\f\u0100\3\2\2\2\16\u0120\3\2\2\2\20\u0140")
        buf.write("\3\2\2\2\22\u016c\3\2\2\2\24\u0194\3\2\2\2\26\u0196\3")
        buf.write("\2\2\2\30\u019d\3\2\2\2\32\u01a7\3\2\2\2\34\u01ac\3\2")
        buf.write('\2\2\36\u01b4\3\2\2\2 \u01bb\3\2\2\2"\u01bd\3\2\2\2$')
        buf.write("\u01c2\3\2\2\2&\u01c7\3\2\2\2(\u01ce\3\2\2\2*\u01de\3")
        buf.write("\2\2\2,\u0211\3\2\2\2.\u0245\3\2\2\2\60\u0255\3\2\2\2")
        buf.write("\62\u0257\3\2\2\2\64\u0259\3\2\2\2\66\u025c\3\2\2\289")
        buf.write("\5.\30\29:\7\2\2\3:\3\3\2\2\2;=\5\6\4\2<;\3\2\2\2=@\3")
        buf.write("\2\2\2><\3\2\2\2>?\3\2\2\2?A\3\2\2\2@>\3\2\2\2AB\5\b\5")
        buf.write("\2BC\7\2\2\3C\5\3\2\2\2DE\7\3\2\2EF\t\2\2\2FG\7A\2\2G")
        buf.write("H\7\6\2\2HI\5*\26\2IJ\7\7\2\2J\7\3\2\2\2KM\7\b\2\2LK\3")
        buf.write("\2\2\2LM\3\2\2\2MN\3\2\2\2NO\7\t\2\2OR\7A\2\2PQ\7\n\2")
        buf.write("\2QS\7B\2\2RP\3\2\2\2RS\3\2\2\2ST\3\2\2\2Tg\7\7\2\2UW")
        buf.write("\7\b\2\2VU\3\2\2\2VW\3\2\2\2WX\3\2\2\2XY\7\t\2\2Y\\\7")
        buf.write("A\2\2Z[\7\n\2\2[]\7B\2\2\\Z\3\2\2\2\\]\3\2\2\2]^\3\2\2")
        buf.write("\2^b\7\13\2\2_a\5\32\16\2`_\3\2\2\2ad\3\2\2\2b`\3\2\2")
        buf.write("\2bc\3\2\2\2ce\3\2\2\2db\3\2\2\2eg\7\f\2\2fL\3\2\2\2f")
        buf.write("V\3\2\2\2g\t\3\2\2\2hi\7\r\2\2ij\7\16\2\2jt\7A\2\2ku\3")
        buf.write("\2\2\2lm\t\3\2\2mu\5\66\34\2no\7\17\2\2op\7\21\2\2pq\7")
        buf.write("\22\2\2qr\5.\30\2rs\7\23\2\2su\3\2\2\2tk\3\2\2\2tl\3\2")
        buf.write("\2\2tn\3\2\2\2u\u0080\3\2\2\2v\u0081\7\7\2\2wx\7\24\2")
        buf.write("\2x|\7\13\2\2y{\5\30\r\2zy\3\2\2\2{~\3\2\2\2|z\3\2\2\2")
        buf.write("|}\3\2\2\2}\177\3\2\2\2~|\3\2\2\2\177\u0081\7\f\2\2\u0080")
        buf.write("v\3\2\2\2\u0080w\3\2\2\2\u0081\u00bb\3\2\2\2\u0082\u0083")
        buf.write("\7A\2\2\u0083\u0084\7\16\2\2\u0084\u0090\7A\2\2\u0085")
        buf.write("\u0091\3\2\2\2\u0086\u0087\7\20\2\2\u0087\u0091\7A\2\2")
        buf.write("\u0088\u0089\7\17\2\2\u0089\u0091\5\66\34\2\u008a\u008b")
        buf.write("\7\17\2\2\u008b\u008c\7\21\2\2\u008c\u008d\7\22\2\2\u008d")
        buf.write("\u008e\5.\30\2\u008e\u008f\7\23\2\2\u008f\u0091\3\2\2")
        buf.write("\2\u0090\u0085\3\2\2\2\u0090\u0086\3\2\2\2\u0090\u0088")
        buf.write("\3\2\2\2\u0090\u008a\3\2\2\2\u0091\u009c\3\2\2\2\u0092")
        buf.write("\u009d\7\7\2\2\u0093\u0094\7\24\2\2\u0094\u0098\7\13\2")
        buf.write("\2\u0095\u0097\5\30\r\2\u0096\u0095\3\2\2\2\u0097\u009a")
        buf.write("\3\2\2\2\u0098\u0096\3\2\2\2\u0098\u0099\3\2\2\2\u0099")
        buf.write("\u009b\3\2\2\2\u009a\u0098\3\2\2\2\u009b\u009d\7\f\2\2")
        buf.write("\u009c\u0092\3\2\2\2\u009c\u0093\3\2\2\2\u009d\u00bb\3")
        buf.write("\2\2\2\u009e\u009f\7A\2\2\u009f\u00a0\7\16\2\2\u00a0\u00ac")
        buf.write("\7\r\2\2\u00a1\u00ad\3\2\2\2\u00a2\u00a3\7\20\2\2\u00a3")
        buf.write("\u00ad\7A\2\2\u00a4\u00a5\7\17\2\2\u00a5\u00ad\5\66\34")
        buf.write("\2\u00a6\u00a7\7\17\2\2\u00a7\u00a8\7\21\2\2\u00a8\u00a9")
        buf.write("\7\22\2\2\u00a9\u00aa\5.\30\2\u00aa\u00ab\7\23\2\2\u00ab")
        buf.write("\u00ad\3\2\2\2\u00ac\u00a1\3\2\2\2\u00ac\u00a2\3\2\2\2")
        buf.write("\u00ac\u00a4\3\2\2\2\u00ac\u00a6\3\2\2\2\u00ad\u00b8\3")
        buf.write("\2\2\2\u00ae\u00b9\7\7\2\2\u00af\u00b0\7\24\2\2\u00b0")
        buf.write("\u00b4\7\13\2\2\u00b1\u00b3\5\30\r\2\u00b2\u00b1\3\2\2")
        buf.write("\2\u00b3\u00b6\3\2\2\2\u00b4\u00b2\3\2\2\2\u00b4\u00b5")
        buf.write("\3\2\2\2\u00b5\u00b7\3\2\2\2\u00b6\u00b4\3\2\2\2\u00b7")
        buf.write("\u00b9\7\f\2\2\u00b8\u00ae\3\2\2\2\u00b8\u00af\3\2\2\2")
        buf.write("\u00b9\u00bb\3\2\2\2\u00bah\3\2\2\2\u00ba\u0082\3\2\2")
        buf.write("\2\u00ba\u009e\3\2\2\2\u00bb\13\3\2\2\2\u00bc\u00bd\7")
        buf.write("\25\2\2\u00bd\u00be\7A\2\2\u00be\u00bf\7\16\2\2\u00bf")
        buf.write("\u00cb\7A\2\2\u00c0\u00cc\3\2\2\2\u00c1\u00c2\7\20\2\2")
        buf.write("\u00c2\u00cc\7A\2\2\u00c3\u00c4\7\17\2\2\u00c4\u00cc\5")
        buf.write("\66\34\2\u00c5\u00c6\7\17\2\2\u00c6\u00c7\7\21\2\2\u00c7")
        buf.write("\u00c8\7\22\2\2\u00c8\u00c9\5.\30\2\u00c9\u00ca\7\23\2")
        buf.write("\2\u00ca\u00cc\3\2\2\2\u00cb\u00c0\3\2\2\2\u00cb\u00c1")
        buf.write("\3\2\2\2\u00cb\u00c3\3\2\2\2\u00cb\u00c5\3\2\2\2\u00cc")
        buf.write("\u00cd\3\2\2\2\u00cd\u0101\7\7\2\2\u00ce\u00cf\7\25\2")
        buf.write("\2\u00cf\u00d0\7A\2\2\u00d0\u00d1\7\16\2\2\u00d1\u00dd")
        buf.write("\7\r\2\2\u00d2\u00de\3\2\2\2\u00d3\u00d4\7\20\2\2\u00d4")
        buf.write("\u00de\7A\2\2\u00d5\u00d6\7\17\2\2\u00d6\u00de\5\66\34")
        buf.write("\2\u00d7\u00d8\7\17\2\2\u00d8\u00d9\7\21\2\2\u00d9\u00da")
        buf.write("\7\22\2\2\u00da\u00db\5.\30\2\u00db\u00dc\7\23\2\2\u00dc")
        buf.write("\u00de\3\2\2\2\u00dd\u00d2\3\2\2\2\u00dd\u00d3\3\2\2\2")
        buf.write("\u00dd\u00d5\3\2\2\2\u00dd\u00d7\3\2\2\2\u00de\u00df\3")
        buf.write("\2\2\2\u00df\u0101\7\7\2\2\u00e0\u00e1\7\25\2\2\u00e1")
        buf.write("\u00e2\7\26\2\2\u00e2\u00e3\7\16\2\2\u00e3\u00ed\7A\2")
        buf.write("\2\u00e4\u00ee\3\2\2\2\u00e5\u00e6\t\3\2\2\u00e6\u00ee")
        buf.write("\5\66\34\2\u00e7\u00e8\7\17\2\2\u00e8\u00e9\7\21\2\2\u00e9")
        buf.write("\u00ea\7\22\2\2\u00ea\u00eb\5.\30\2\u00eb\u00ec\7\23\2")
        buf.write("\2\u00ec\u00ee\3\2\2\2\u00ed\u00e4\3\2\2\2\u00ed\u00e5")
        buf.write("\3\2\2\2\u00ed\u00e7\3\2\2\2\u00ee\u00ef\3\2\2\2\u00ef")
        buf.write("\u0101\7\7\2\2\u00f0\u00f1\7\25\2\2\u00f1\u00f2\7\26\2")
        buf.write("\2\u00f2\u00f3\7\16\2\2\u00f3\u00fd\7\r\2\2\u00f4\u00fe")
        buf.write("\3\2\2\2\u00f5\u00f6\t\3\2\2\u00f6\u00fe\5\66\34\2\u00f7")
        buf.write("\u00f8\7\17\2\2\u00f8\u00f9\7\21\2\2\u00f9\u00fa\7\22")
        buf.write("\2\2\u00fa\u00fb\5.\30\2\u00fb\u00fc\7\23\2\2\u00fc\u00fe")
        buf.write("\3\2\2\2\u00fd\u00f4\3\2\2\2\u00fd\u00f5\3\2\2\2\u00fd")
        buf.write("\u00f7\3\2\2\2\u00fe\u00ff\3\2\2\2\u00ff\u0101\7\7\2\2")
        buf.write("\u0100\u00bc\3\2\2\2\u0100\u00ce\3\2\2\2\u0100\u00e0\3")
        buf.write("\2\2\2\u0100\u00f0\3\2\2\2\u0101\r\3\2\2\2\u0102\u0104")
        buf.write("\7\27\2\2\u0103\u0105\7A\2\2\u0104\u0103\3\2\2\2\u0104")
        buf.write("\u0105\3\2\2\2\u0105\u0106\3\2\2\2\u0106\u010a\7\13\2")
        buf.write("\2\u0107\u0109\5\30\r\2\u0108\u0107\3\2\2\2\u0109\u010c")
        buf.write("\3\2\2\2\u010a\u0108\3\2\2\2\u010a\u010b\3\2\2\2\u010b")
        buf.write("\u010d\3\2\2\2\u010c\u010a\3\2\2\2\u010d\u0121\7\f\2\2")
        buf.write("\u010e\u010f\7\27\2\2\u010f\u0110\7\30\2\2\u0110\u0111")
        buf.write("\7A\2\2\u0111\u0121\7\7\2\2\u0112\u0113\7\27\2\2\u0113")
        buf.write("\u0115\7\30\2\2\u0114\u0116\7A\2\2\u0115\u0114\3\2\2\2")
        buf.write("\u0115\u0116\3\2\2\2\u0116\u0117\3\2\2\2\u0117\u0121\7")
        buf.write("D\2\2\u0118\u011a\7\27\2\2\u0119\u011b\7A\2\2\u011a\u0119")
        buf.write("\3\2\2\2\u011a\u011b\3\2\2\2\u011b\u011c\3\2\2\2\u011c")
        buf.write("\u011d\7\31\2\2\u011d\u011e\5\66\34\2\u011e\u011f\7\7")
        buf.write("\2\2\u011f\u0121\3\2\2\2\u0120\u0102\3\2\2\2\u0120\u010e")
        buf.write("\3\2\2\2\u0120\u0112\3\2\2\2\u0120\u0118\3\2\2\2\u0121")
        buf.write("\17\3\2\2\2\u0122\u0124\7\32\2\2\u0123\u0125\7A\2\2\u0124")
        buf.write("\u0123\3\2\2\2\u0124\u0125\3\2\2\2\u0125\u0126\3\2\2\2")
        buf.write("\u0126\u012a\7\13\2\2\u0127\u0129\5\30\r\2\u0128\u0127")
        buf.write("\3\2\2\2\u0129\u012c\3\2\2\2\u012a\u0128\3\2\2\2\u012a")
        buf.write("\u012b\3\2\2\2\u012b\u012d\3\2\2\2\u012c\u012a\3\2\2\2")
        buf.write("\u012d\u0141\7\f\2\2\u012e\u012f\7\32\2\2\u012f\u0130")
        buf.write("\7\30\2\2\u0130\u0131\7A\2\2\u0131\u0141\7\7\2\2\u0132")
        buf.write("\u0133\7\32\2\2\u0133\u0135\7\30\2\2\u0134\u0136\7A\2")
        buf.write("\2\u0135\u0134\3\2\2\2\u0135\u0136\3\2\2\2\u0136\u0137")
        buf.write("\3\2\2\2\u0137\u0141\7D\2\2\u0138\u013a\7\32\2\2\u0139")
        buf.write("\u013b\7A\2\2\u013a\u0139\3\2\2\2\u013a\u013b\3\2\2\2")
        buf.write("\u013b\u013c\3\2\2\2\u013c\u013d\7\31\2\2\u013d\u013e")
        buf.write("\5\66\34\2\u013e\u013f\7\7\2\2\u013f\u0141\3\2\2\2\u0140")
        buf.write("\u0122\3\2\2\2\u0140\u012e\3\2\2\2\u0140\u0132\3\2\2\2")
        buf.write("\u0140\u0138\3\2\2\2\u0141\21\3\2\2\2\u0142\u0144\7\33")
        buf.write("\2\2\u0143\u0145\t\4\2\2\u0144\u0143\3\2\2\2\u0144\u0145")
        buf.write("\3\2\2\2\u0145\u0147\3\2\2\2\u0146\u0148\7A\2\2\u0147")
        buf.write("\u0146\3\2\2\2\u0147\u0148\3\2\2\2\u0148\u0149\3\2\2\2")
        buf.write("\u0149\u014d\7\13\2\2\u014a\u014c\5\30\r\2\u014b\u014a")
        buf.write("\3\2\2\2\u014c\u014f\3\2\2\2\u014d\u014b\3\2\2\2\u014d")
        buf.write("\u014e\3\2\2\2\u014e\u0150\3\2\2\2\u014f\u014d\3\2\2\2")
        buf.write("\u0150\u016d\7\f\2\2\u0151\u0153\7\33\2\2\u0152\u0154")
        buf.write("\t\4\2\2\u0153\u0152\3\2\2\2\u0153\u0154\3\2\2\2\u0154")
        buf.write("\u0155\3\2\2\2\u0155\u0156\7\30\2\2\u0156\u0157\7A\2\2")
        buf.write("\u0157\u016d\7\7\2\2\u0158\u015a\7\33\2\2\u0159\u015b")
        buf.write("\t\4\2\2\u015a\u0159\3\2\2\2\u015a\u015b\3\2\2\2\u015b")
        buf.write("\u015c\3\2\2\2\u015c\u015e\7\30\2\2\u015d\u015f\7A\2\2")
        buf.write("\u015e\u015d\3\2\2\2\u015e\u015f\3\2\2\2\u015f\u0160\3")
        buf.write("\2\2\2\u0160\u016d\7D\2\2\u0161\u0163\7\33\2\2\u0162\u0164")
        buf.write("\t\4\2\2\u0163\u0162\3\2\2\2\u0163\u0164\3\2\2\2\u0164")
        buf.write("\u0166\3\2\2\2\u0165\u0167\7A\2\2\u0166\u0165\3\2\2\2")
        buf.write("\u0166\u0167\3\2\2\2\u0167\u0168\3\2\2\2\u0168\u0169\7")
        buf.write("\31\2\2\u0169\u016a\5\66\34\2\u016a\u016b\7\7\2\2\u016b")
        buf.write("\u016d\3\2\2\2\u016c\u0142\3\2\2\2\u016c\u0151\3\2\2\2")
        buf.write("\u016c\u0158\3\2\2\2\u016c\u0161\3\2\2\2\u016d\23\3\2")
        buf.write("\2\2\u016e\u016f\7\36\2\2\u016f\u0170\7\33\2\2\u0170\u0172")
        buf.write("\t\4\2\2\u0171\u0173\7A\2\2\u0172\u0171\3\2\2\2\u0172")
        buf.write("\u0173\3\2\2\2\u0173\u0174\3\2\2\2\u0174\u0178\7\13\2")
        buf.write("\2\u0175\u0177\5\30\r\2\u0176\u0175\3\2\2\2\u0177\u017a")
        buf.write("\3\2\2\2\u0178\u0176\3\2\2\2\u0178\u0179\3\2\2\2\u0179")
        buf.write("\u017b\3\2\2\2\u017a\u0178\3\2\2\2\u017b\u0195\7\f\2\2")
        buf.write("\u017c\u017d\7\36\2\2\u017d\u017e\7\33\2\2\u017e\u017f")
        buf.write("\t\4\2\2\u017f\u0180\7\30\2\2\u0180\u0181\7A\2\2\u0181")
        buf.write("\u0195\7\7\2\2\u0182\u0183\7\36\2\2\u0183\u0184\7\33\2")
        buf.write("\2\u0184\u0185\t\4\2\2\u0185\u0187\7\30\2\2\u0186\u0188")
        buf.write("\7A\2\2\u0187\u0186\3\2\2\2\u0187\u0188\3\2\2\2\u0188")
        buf.write("\u0189\3\2\2\2\u0189\u0195\7D\2\2\u018a\u018b\7\36\2\2")
        buf.write("\u018b\u018c\7\33\2\2\u018c\u018e\t\4\2\2\u018d\u018f")
        buf.write("\7A\2\2\u018e\u018d\3\2\2\2\u018e\u018f\3\2\2\2\u018f")
        buf.write("\u0190\3\2\2\2\u0190\u0191\7\31\2\2\u0191\u0192\5\66\34")
        buf.write("\2\u0192\u0193\7\7\2\2\u0193\u0195\3\2\2\2\u0194\u016e")
        buf.write("\3\2\2\2\u0194\u017c\3\2\2\2\u0194\u0182\3\2\2\2\u0194")
        buf.write("\u018a\3\2\2\2\u0195\25\3\2\2\2\u0196\u0197\7A\2\2\u0197")
        buf.write("\u0198\7\6\2\2\u0198\u0199\5,\27\2\u0199\u019a\7\7\2\2")
        buf.write("\u019a\27\3\2\2\2\u019b\u019e\5\26\f\2\u019c\u019e\7\7")
        buf.write("\2\2\u019d\u019b\3\2\2\2\u019d\u019c\3\2\2\2\u019e\31")
        buf.write("\3\2\2\2\u019f\u01a8\5\b\5\2\u01a0\u01a8\5\n\6\2\u01a1")
        buf.write("\u01a8\5\f\7\2\u01a2\u01a8\5\16\b\2\u01a3\u01a8\5\22\n")
        buf.write("\2\u01a4\u01a8\5\20\t\2\u01a5\u01a8\5\24\13\2\u01a6\u01a8")
        buf.write("\7\7\2\2\u01a7\u019f\3\2\2\2\u01a7\u01a0\3\2\2\2\u01a7")
        buf.write("\u01a1\3\2\2\2\u01a7\u01a2\3\2\2\2\u01a7\u01a3\3\2\2\2")
        buf.write("\u01a7\u01a4\3\2\2\2\u01a7\u01a5\3\2\2\2\u01a7\u01a6\3")
        buf.write("\2\2\2\u01a8\33\3\2\2\2\u01a9\u01ab\5&\24\2\u01aa\u01a9")
        buf.write("\3\2\2\2\u01ab\u01ae\3\2\2\2\u01ac\u01aa\3\2\2\2\u01ac")
        buf.write("\u01ad\3\2\2\2\u01ad\u01af\3\2\2\2\u01ae\u01ac\3\2\2\2")
        buf.write("\u01af\u01b0\7\2\2\3\u01b0\35\3\2\2\2\u01b1\u01b3\5 \21")
        buf.write("\2\u01b2\u01b1\3\2\2\2\u01b3\u01b6\3\2\2\2\u01b4\u01b2")
        buf.write("\3\2\2\2\u01b4\u01b5\3\2\2\2\u01b5\u01b7\3\2\2\2\u01b6")
        buf.write("\u01b4\3\2\2\2\u01b7\u01b8\7\2\2\3\u01b8\37\3\2\2\2\u01b9")
        buf.write('\u01bc\5"\22\2\u01ba\u01bc\5$\23\2\u01bb\u01b9\3\2\2')
        buf.write("\2\u01bb\u01ba\3\2\2\2\u01bc!\3\2\2\2\u01bd\u01be\7A\2")
        buf.write("\2\u01be\u01bf\7\37\2\2\u01bf\u01c0\5*\26\2\u01c0\u01c1")
        buf.write("\7\7\2\2\u01c1#\3\2\2\2\u01c2\u01c3\7A\2\2\u01c3\u01c4")
        buf.write("\7\6\2\2\u01c4\u01c5\5*\26\2\u01c5\u01c6\7\7\2\2\u01c6")
        buf.write("%\3\2\2\2\u01c7\u01c8\7A\2\2\u01c8\u01c9\7\37\2\2\u01c9")
        buf.write("\u01ca\5,\27\2\u01ca\u01cb\7\7\2\2\u01cb'\3\2\2\2\u01cc")
        buf.write("\u01cf\5,\27\2\u01cd\u01cf\5.\30\2\u01ce\u01cc\3\2\2\2")
        buf.write("\u01ce\u01cd\3\2\2\2\u01cf)\3\2\2\2\u01d0\u01d1\b\26\1")
        buf.write("\2\u01d1\u01d2\7 \2\2\u01d2\u01d3\5*\26\2\u01d3\u01d4")
        buf.write("\7!\2\2\u01d4\u01df\3\2\2\2\u01d5\u01df\5\60\31\2\u01d6")
        buf.write("\u01df\5\64\33\2\u01d7\u01d8\t\5\2\2\u01d8\u01df\5*\26")
        buf.write("\13\u01d9\u01da\7@\2\2\u01da\u01db\7 \2\2\u01db\u01dc")
        buf.write("\5*\26\2\u01dc\u01dd\7!\2\2\u01dd\u01df\3\2\2\2\u01de")
        buf.write("\u01d0\3\2\2\2\u01de\u01d5\3\2\2\2\u01de\u01d6\3\2\2\2")
        buf.write("\u01de\u01d7\3\2\2\2\u01de\u01d9\3\2\2\2\u01df\u01f7\3")
        buf.write("\2\2\2\u01e0\u01e1\f\n\2\2\u01e1\u01e2\7$\2\2\u01e2\u01f6")
        buf.write("\5*\26\n\u01e3\u01e4\f\t\2\2\u01e4\u01e5\t\6\2\2\u01e5")
        buf.write("\u01f6\5*\26\n\u01e6\u01e7\f\b\2\2\u01e7\u01e8\t\5\2\2")
        buf.write("\u01e8\u01f6\5*\26\t\u01e9\u01ea\f\7\2\2\u01ea\u01eb\t")
        buf.write("\7\2\2\u01eb\u01f6\5*\26\b\u01ec\u01ed\f\6\2\2\u01ed\u01ee")
        buf.write("\7(\2\2\u01ee\u01f6\5*\26\7\u01ef\u01f0\f\5\2\2\u01f0")
        buf.write("\u01f1\7)\2\2\u01f1\u01f6\5*\26\6\u01f2\u01f3\f\4\2\2")
        buf.write("\u01f3\u01f4\7*\2\2\u01f4\u01f6\5*\26\5\u01f5\u01e0\3")
        buf.write("\2\2\2\u01f5\u01e3\3\2\2\2\u01f5\u01e6\3\2\2\2\u01f5\u01e9")
        buf.write("\3\2\2\2\u01f5\u01ec\3\2\2\2\u01f5\u01ef\3\2\2\2\u01f5")
        buf.write("\u01f2\3\2\2\2\u01f6\u01f9\3\2\2\2\u01f7\u01f5\3\2\2\2")
        buf.write("\u01f7\u01f8\3\2\2\2\u01f8+\3\2\2\2\u01f9\u01f7\3\2\2")
        buf.write("\2\u01fa\u01fb\b\27\1\2\u01fb\u01fc\7 \2\2\u01fc\u01fd")
        buf.write("\5,\27\2\u01fd\u01fe\7!\2\2\u01fe\u0212\3\2\2\2\u01ff")
        buf.write("\u0212\5\60\31\2\u0200\u0212\7A\2\2\u0201\u0212\5\64\33")
        buf.write("\2\u0202\u0203\t\5\2\2\u0203\u0212\5,\27\f\u0204\u0205")
        buf.write("\7@\2\2\u0205\u0206\7 \2\2\u0206\u0207\5,\27\2\u0207\u0208")
        buf.write("\7!\2\2\u0208\u0212\3\2\2\2\u0209\u020a\7 \2\2\u020a\u020b")
        buf.write("\5.\30\2\u020b\u020c\7!\2\2\u020c\u020d\7+\2\2\u020d\u020e")
        buf.write("\5,\27\2\u020e\u020f\7\17\2\2\u020f\u0210\5,\27\3\u0210")
        buf.write("\u0212\3\2\2\2\u0211\u01fa\3\2\2\2\u0211\u01ff\3\2\2\2")
        buf.write("\u0211\u0200\3\2\2\2\u0211\u0201\3\2\2\2\u0211\u0202\3")
        buf.write("\2\2\2\u0211\u0204\3\2\2\2\u0211\u0209\3\2\2\2\u0212\u022a")
        buf.write("\3\2\2\2\u0213\u0214\f\13\2\2\u0214\u0215\7$\2\2\u0215")
        buf.write("\u0229\5,\27\13\u0216\u0217\f\n\2\2\u0217\u0218\t\6\2")
        buf.write("\2\u0218\u0229\5,\27\13\u0219\u021a\f\t\2\2\u021a\u021b")
        buf.write("\t\5\2\2\u021b\u0229\5,\27\n\u021c\u021d\f\b\2\2\u021d")
        buf.write("\u021e\t\7\2\2\u021e\u0229\5,\27\t\u021f\u0220\f\7\2\2")
        buf.write("\u0220\u0221\7(\2\2\u0221\u0229\5,\27\b\u0222\u0223\f")
        buf.write("\6\2\2\u0223\u0224\7)\2\2\u0224\u0229\5,\27\7\u0225\u0226")
        buf.write("\f\5\2\2\u0226\u0227\7*\2\2\u0227\u0229\5,\27\6\u0228")
        buf.write("\u0213\3\2\2\2\u0228\u0216\3\2\2\2\u0228\u0219\3\2\2\2")
        buf.write("\u0228\u021c\3\2\2\2\u0228\u021f\3\2\2\2\u0228\u0222\3")
        buf.write("\2\2\2\u0228\u0225\3\2\2\2\u0229\u022c\3\2\2\2\u022a\u0228")
        buf.write("\3\2\2\2\u022a\u022b\3\2\2\2\u022b-\3\2\2\2\u022c\u022a")
        buf.write("\3\2\2\2\u022d\u022e\b\30\1\2\u022e\u022f\7 \2\2\u022f")
        buf.write("\u0230\5.\30\2\u0230\u0231\7!\2\2\u0231\u0246\3\2\2\2")
        buf.write("\u0232\u0246\5\62\32\2\u0233\u0234\t\b\2\2\u0234\u0246")
        buf.write("\5.\30\t\u0235\u0236\5,\27\2\u0236\u0237\t\t\2\2\u0237")
        buf.write("\u0238\5,\27\2\u0238\u0246\3\2\2\2\u0239\u023a\5,\27\2")
        buf.write("\u023a\u023b\t\n\2\2\u023b\u023c\5,\27\2\u023c\u0246\3")
        buf.write("\2\2\2\u023d\u023e\7 \2\2\u023e\u023f\5.\30\2\u023f\u0240")
        buf.write("\7!\2\2\u0240\u0241\7+\2\2\u0241\u0242\5.\30\2\u0242\u0243")
        buf.write("\7\17\2\2\u0243\u0244\5.\30\3\u0244\u0246\3\2\2\2\u0245")
        buf.write("\u022d\3\2\2\2\u0245\u0232\3\2\2\2\u0245\u0233\3\2\2\2")
        buf.write("\u0245\u0235\3\2\2\2\u0245\u0239\3\2\2\2\u0245\u023d\3")
        buf.write("\2\2\2\u0246\u0252\3\2\2\2\u0247\u0248\f\6\2\2\u0248\u0249")
        buf.write("\t\n\2\2\u0249\u0251\5.\30\7\u024a\u024b\f\5\2\2\u024b")
        buf.write("\u024c\t\13\2\2\u024c\u0251\5.\30\6\u024d\u024e\f\4\2")
        buf.write("\2\u024e\u024f\t\f\2\2\u024f\u0251\5.\30\5\u0250\u0247")
        buf.write("\3\2\2\2\u0250\u024a\3\2\2\2\u0250\u024d\3\2\2\2\u0251")
        buf.write("\u0254\3\2\2\2\u0252\u0250\3\2\2\2\u0252\u0253\3\2\2\2")
        buf.write("\u0253/\3\2\2\2\u0254\u0252\3\2\2\2\u0255\u0256\t\r\2")
        buf.write("\2\u0256\61\3\2\2\2\u0257\u0258\t\16\2\2\u0258\63\3\2")
        buf.write("\2\2\u0259\u025a\t\17\2\2\u025a\65\3\2\2\2\u025b\u025d")
        buf.write("\7%\2\2\u025c\u025b\3\2\2\2\u025c\u025d\3\2\2\2\u025d")
        buf.write("\u025e\3\2\2\2\u025e\u0263\7A\2\2\u025f\u0260\7:\2\2\u0260")
        buf.write("\u0262\7A\2\2\u0261\u025f\3\2\2\2\u0262\u0265\3\2\2\2")
        buf.write("\u0263\u0261\3\2\2\2\u0263\u0264\3\2\2\2\u0264\67\3\2")
        buf.write("\2\2\u0265\u0263\3\2\2\2A>LRV\\bft|\u0080\u0090\u0098")
        buf.write("\u009c\u00ac\u00b4\u00b8\u00ba\u00cb\u00dd\u00ed\u00fd")
        buf.write("\u0100\u0104\u010a\u0115\u011a\u0120\u0124\u012a\u0135")
        buf.write("\u013a\u0140\u0144\u0147\u014d\u0153\u015a\u015e\u0163")
        buf.write("\u0166\u016c\u0172\u0178\u0187\u018e\u0194\u019d\u01a7")
        buf.write("\u01ac\u01b4\u01bb\u01ce\u01de\u01f5\u01f7\u0211\u0228")
        buf.write("\u022a\u0245\u0250\u0252\u025c\u0263")
        return buf.getvalue()


class GrammarParser(Parser):
    grammarFileName = "Grammar.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [DFA(ds, i) for i, ds in enumerate(atn.decisionToState)]

    sharedContextCache = PredictionContextCache()

    literalNames = [
        "<INVALID>",
        "'def'",
        "'int'",
        "'float'",
        "'='",
        "';'",
        "'pseudo'",
        "'state'",
        "'named'",
        "'{'",
        "'}'",
        "'[*]'",
        "'->'",
        "':'",
        "'::'",
        "'if'",
        "'['",
        "']'",
        "'effect'",
        "'!'",
        "'*'",
        "'enter'",
        "'abstract'",
        "'ref'",
        "'exit'",
        "'during'",
        "'before'",
        "'after'",
        "'>>'",
        "':='",
        "'('",
        "')'",
        "'+'",
        "'-'",
        "'**'",
        "'/'",
        "'%'",
        "'<<'",
        "'&'",
        "'^'",
        "'|'",
        "'?'",
        "'not'",
        "'<'",
        "'>'",
        "'<='",
        "'>='",
        "'=='",
        "'!='",
        "'&&'",
        "'and'",
        "'||'",
        "'or'",
        "'pi'",
        "'E'",
        "'tau'",
        "'.'",
    ]

    symbolicNames = [
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "<INVALID>",
        "FLOAT",
        "INT",
        "HEX_INT",
        "TRUE",
        "FALSE",
        "UFUNC_NAME",
        "ID",
        "STRING",
        "WS",
        "MULTILINE_COMMENT",
        "LINE_COMMENT",
        "PYTHON_COMMENT",
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
    RULE_operation_assignment = 10
    RULE_operational_statement = 11
    RULE_state_inner_statement = 12
    RULE_operation_program = 13
    RULE_preamble_program = 14
    RULE_preamble_statement = 15
    RULE_initial_assignment = 16
    RULE_constant_definition = 17
    RULE_operational_assignment = 18
    RULE_generic_expression = 19
    RULE_init_expression = 20
    RULE_num_expression = 21
    RULE_cond_expression = 22
    RULE_num_literal = 23
    RULE_bool_literal = 24
    RULE_math_const = 25
    RULE_chain_id = 26

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
        "operation_assignment",
        "operational_statement",
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
    T__28 = 29
    T__29 = 30
    T__30 = 31
    T__31 = 32
    T__32 = 33
    T__33 = 34
    T__34 = 35
    T__35 = 36
    T__36 = 37
    T__37 = 38
    T__38 = 39
    T__39 = 40
    T__40 = 41
    T__41 = 42
    T__42 = 43
    T__43 = 44
    T__44 = 45
    T__45 = 46
    T__46 = 47
    T__47 = 48
    T__48 = 49
    T__49 = 50
    T__50 = 51
    T__51 = 52
    T__52 = 53
    T__53 = 54
    T__54 = 55
    T__55 = 56
    FLOAT = 57
    INT = 58
    HEX_INT = 59
    TRUE = 60
    FALSE = 61
    UFUNC_NAME = 62
    ID = 63
    STRING = 64
    WS = 65
    MULTILINE_COMMENT = 66
    LINE_COMMENT = 67
    PYTHON_COMMENT = 68

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
            self.state = 54
            self.cond_expression(0)
            self.state = 55
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
            self.state = 60
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.T__0:
                self.state = 57
                self.def_assignment()
                self.state = 62
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 63
            self.state_definition()
            self.state = 64
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

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def init_expression(self):
            return self.getTypedRuleContext(GrammarParser.Init_expressionContext, 0)

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
            self.state = 66
            self.match(GrammarParser.T__0)
            self.state = 67
            localctx.deftype = self._input.LT(1)
            _la = self._input.LA(1)
            if not (_la == GrammarParser.T__1 or _la == GrammarParser.T__2):
                localctx.deftype = self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 68
            self.match(GrammarParser.ID)
            self.state = 69
            self.match(GrammarParser.T__3)
            self.state = 70
            self.init_expression(0)
            self.state = 71
            self.match(GrammarParser.T__4)
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

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

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

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def state_inner_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.State_inner_statementContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.State_inner_statementContext, i
                )

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
            self.state = 100
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 6, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.LeafStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 74
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__5:
                    self.state = 73
                    localctx.pseudo = self.match(GrammarParser.T__5)

                self.state = 76
                self.match(GrammarParser.T__6)
                self.state = 77
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 80
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__7:
                    self.state = 78
                    self.match(GrammarParser.T__7)
                    self.state = 79
                    localctx.extra_name = self.match(GrammarParser.STRING)

                self.state = 82
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 2:
                localctx = GrammarParser.CompositeStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 84
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__5:
                    self.state = 83
                    localctx.pseudo = self.match(GrammarParser.T__5)

                self.state = 86
                self.match(GrammarParser.T__6)
                self.state = 87
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 90
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__7:
                    self.state = 88
                    self.match(GrammarParser.T__7)
                    self.state = 89
                    localctx.extra_name = self.match(GrammarParser.STRING)

                self.state = 92
                self.match(GrammarParser.T__8)
                self.state = 96
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while ((_la) & ~0x3F) == 0 and (
                    (1 << _la)
                    & (
                        (1 << GrammarParser.T__4)
                        | (1 << GrammarParser.T__5)
                        | (1 << GrammarParser.T__6)
                        | (1 << GrammarParser.T__10)
                        | (1 << GrammarParser.T__18)
                        | (1 << GrammarParser.T__20)
                        | (1 << GrammarParser.T__23)
                        | (1 << GrammarParser.T__24)
                        | (1 << GrammarParser.T__27)
                        | (1 << GrammarParser.ID)
                    )
                ) != 0:
                    self.state = 93
                    self.state_inner_statement()
                    self.state = 98
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 99
                self.match(GrammarParser.T__9)
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

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.ID)
            else:
                return self.getToken(GrammarParser.ID, i)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def operational_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Operational_statementContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Operational_statementContext, i
                )

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

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def operational_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Operational_statementContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Operational_statementContext, i
                )

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

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.ID)
            else:
                return self.getToken(GrammarParser.ID, i)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def operational_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Operational_statementContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Operational_statementContext, i
                )

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
            self.state = 184
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 16, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EntryTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 102
                self.match(GrammarParser.T__10)
                self.state = 103
                self.match(GrammarParser.T__11)
                self.state = 104
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 114
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 7, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 106
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__12 or _la == GrammarParser.T__13):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 107
                    self.chain_id()
                    pass

                elif la_ == 3:
                    self.state = 108
                    self.match(GrammarParser.T__12)
                    self.state = 109
                    self.match(GrammarParser.T__14)
                    self.state = 110
                    self.match(GrammarParser.T__15)
                    self.state = 111
                    self.cond_expression(0)
                    self.state = 112
                    self.match(GrammarParser.T__16)
                    pass

                self.state = 126
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.T__4]:
                    self.state = 116
                    self.match(GrammarParser.T__4)
                    pass
                elif token in [GrammarParser.T__17]:
                    self.state = 117
                    self.match(GrammarParser.T__17)
                    self.state = 118
                    self.match(GrammarParser.T__8)
                    self.state = 122
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la == GrammarParser.T__4 or _la == GrammarParser.ID:
                        self.state = 119
                        self.operational_statement()
                        self.state = 124
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)

                    self.state = 125
                    self.match(GrammarParser.T__9)
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 2:
                localctx = GrammarParser.NormalTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 2)
                self.state = 128
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 129
                self.match(GrammarParser.T__11)
                self.state = 130
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 142
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 10, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 132
                    self.match(GrammarParser.T__13)
                    self.state = 133
                    localctx.from_id = self.match(GrammarParser.ID)
                    pass

                elif la_ == 3:
                    self.state = 134
                    self.match(GrammarParser.T__12)
                    self.state = 135
                    self.chain_id()
                    pass

                elif la_ == 4:
                    self.state = 136
                    self.match(GrammarParser.T__12)
                    self.state = 137
                    self.match(GrammarParser.T__14)
                    self.state = 138
                    self.match(GrammarParser.T__15)
                    self.state = 139
                    self.cond_expression(0)
                    self.state = 140
                    self.match(GrammarParser.T__16)
                    pass

                self.state = 154
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.T__4]:
                    self.state = 144
                    self.match(GrammarParser.T__4)
                    pass
                elif token in [GrammarParser.T__17]:
                    self.state = 145
                    self.match(GrammarParser.T__17)
                    self.state = 146
                    self.match(GrammarParser.T__8)
                    self.state = 150
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la == GrammarParser.T__4 or _la == GrammarParser.ID:
                        self.state = 147
                        self.operational_statement()
                        self.state = 152
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)

                    self.state = 153
                    self.match(GrammarParser.T__9)
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 3:
                localctx = GrammarParser.ExitTransitionDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 156
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 157
                self.match(GrammarParser.T__11)
                self.state = 158
                self.match(GrammarParser.T__10)
                self.state = 170
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 13, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 160
                    self.match(GrammarParser.T__13)
                    self.state = 161
                    localctx.from_id = self.match(GrammarParser.ID)
                    pass

                elif la_ == 3:
                    self.state = 162
                    self.match(GrammarParser.T__12)
                    self.state = 163
                    self.chain_id()
                    pass

                elif la_ == 4:
                    self.state = 164
                    self.match(GrammarParser.T__12)
                    self.state = 165
                    self.match(GrammarParser.T__14)
                    self.state = 166
                    self.match(GrammarParser.T__15)
                    self.state = 167
                    self.cond_expression(0)
                    self.state = 168
                    self.match(GrammarParser.T__16)
                    pass

                self.state = 182
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.T__4]:
                    self.state = 172
                    self.match(GrammarParser.T__4)
                    pass
                elif token in [GrammarParser.T__17]:
                    self.state = 173
                    self.match(GrammarParser.T__17)
                    self.state = 174
                    self.match(GrammarParser.T__8)
                    self.state = 178
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la == GrammarParser.T__4 or _la == GrammarParser.ID:
                        self.state = 175
                        self.operational_statement()
                        self.state = 180
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)

                    self.state = 181
                    self.match(GrammarParser.T__9)
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

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.ID)
            else:
                return self.getToken(GrammarParser.ID, i)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

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

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

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

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

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

        def ID(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.ID)
            else:
                return self.getToken(GrammarParser.ID, i)

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

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
            self.state = 254
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 21, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.NormalForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 186
                self.match(GrammarParser.T__18)
                self.state = 187
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 188
                self.match(GrammarParser.T__11)
                self.state = 189
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 201
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 17, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 191
                    self.match(GrammarParser.T__13)
                    self.state = 192
                    localctx.from_id = self.match(GrammarParser.ID)
                    pass

                elif la_ == 3:
                    self.state = 193
                    self.match(GrammarParser.T__12)
                    self.state = 194
                    self.chain_id()
                    pass

                elif la_ == 4:
                    self.state = 195
                    self.match(GrammarParser.T__12)
                    self.state = 196
                    self.match(GrammarParser.T__14)
                    self.state = 197
                    self.match(GrammarParser.T__15)
                    self.state = 198
                    self.cond_expression(0)
                    self.state = 199
                    self.match(GrammarParser.T__16)
                    pass

                self.state = 203
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 2:
                localctx = GrammarParser.ExitForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 2)
                self.state = 204
                self.match(GrammarParser.T__18)
                self.state = 205
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 206
                self.match(GrammarParser.T__11)
                self.state = 207
                self.match(GrammarParser.T__10)
                self.state = 219
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 18, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 209
                    self.match(GrammarParser.T__13)
                    self.state = 210
                    localctx.from_id = self.match(GrammarParser.ID)
                    pass

                elif la_ == 3:
                    self.state = 211
                    self.match(GrammarParser.T__12)
                    self.state = 212
                    self.chain_id()
                    pass

                elif la_ == 4:
                    self.state = 213
                    self.match(GrammarParser.T__12)
                    self.state = 214
                    self.match(GrammarParser.T__14)
                    self.state = 215
                    self.match(GrammarParser.T__15)
                    self.state = 216
                    self.cond_expression(0)
                    self.state = 217
                    self.match(GrammarParser.T__16)
                    pass

                self.state = 221
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 3:
                localctx = GrammarParser.NormalAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 3)
                self.state = 222
                self.match(GrammarParser.T__18)
                self.state = 223
                self.match(GrammarParser.T__19)
                self.state = 224
                self.match(GrammarParser.T__11)
                self.state = 225
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 235
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 19, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 227
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__12 or _la == GrammarParser.T__13):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 228
                    self.chain_id()
                    pass

                elif la_ == 3:
                    self.state = 229
                    self.match(GrammarParser.T__12)
                    self.state = 230
                    self.match(GrammarParser.T__14)
                    self.state = 231
                    self.match(GrammarParser.T__15)
                    self.state = 232
                    self.cond_expression(0)
                    self.state = 233
                    self.match(GrammarParser.T__16)
                    pass

                self.state = 237
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 4:
                localctx = GrammarParser.ExitAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 4)
                self.state = 238
                self.match(GrammarParser.T__18)
                self.state = 239
                self.match(GrammarParser.T__19)
                self.state = 240
                self.match(GrammarParser.T__11)
                self.state = 241
                self.match(GrammarParser.T__10)
                self.state = 251
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 20, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 243
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__12 or _la == GrammarParser.T__13):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 244
                    self.chain_id()
                    pass

                elif la_ == 3:
                    self.state = 245
                    self.match(GrammarParser.T__12)
                    self.state = 246
                    self.match(GrammarParser.T__14)
                    self.state = 247
                    self.match(GrammarParser.T__15)
                    self.state = 248
                    self.cond_expression(0)
                    self.state = 249
                    self.match(GrammarParser.T__16)
                    pass

                self.state = 253
                self.match(GrammarParser.T__4)
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

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

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

        def operational_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Operational_statementContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Operational_statementContext, i
                )

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
            self.state = 286
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 26, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EnterOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 256
                self.match(GrammarParser.T__20)
                self.state = 258
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 257
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 260
                self.match(GrammarParser.T__8)
                self.state = 264
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == GrammarParser.T__4 or _la == GrammarParser.ID:
                    self.state = 261
                    self.operational_statement()
                    self.state = 266
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 267
                self.match(GrammarParser.T__9)
                pass

            elif la_ == 2:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 268
                self.match(GrammarParser.T__20)
                self.state = 269
                self.match(GrammarParser.T__21)
                self.state = 270
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 271
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 3:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 272
                self.match(GrammarParser.T__20)
                self.state = 273
                self.match(GrammarParser.T__21)
                self.state = 275
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 274
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 277
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.EnterRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 278
                self.match(GrammarParser.T__20)
                self.state = 280
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 279
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 282
                self.match(GrammarParser.T__22)
                self.state = 283
                self.chain_id()
                self.state = 284
                self.match(GrammarParser.T__4)
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

        def operational_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Operational_statementContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Operational_statementContext, i
                )

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

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

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
            self.state = 318
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 31, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ExitOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 288
                self.match(GrammarParser.T__23)
                self.state = 290
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 289
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 292
                self.match(GrammarParser.T__8)
                self.state = 296
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == GrammarParser.T__4 or _la == GrammarParser.ID:
                    self.state = 293
                    self.operational_statement()
                    self.state = 298
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 299
                self.match(GrammarParser.T__9)
                pass

            elif la_ == 2:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 300
                self.match(GrammarParser.T__23)
                self.state = 301
                self.match(GrammarParser.T__21)
                self.state = 302
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 303
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 3:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 304
                self.match(GrammarParser.T__23)
                self.state = 305
                self.match(GrammarParser.T__21)
                self.state = 307
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 306
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 309
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.ExitRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 310
                self.match(GrammarParser.T__23)
                self.state = 312
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 311
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 314
                self.match(GrammarParser.T__22)
                self.state = 315
                self.chain_id()
                self.state = 316
                self.match(GrammarParser.T__4)
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

        def operational_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Operational_statementContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Operational_statementContext, i
                )

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

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

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

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

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

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
            self.state = 362
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 40, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.DuringOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 320
                self.match(GrammarParser.T__24)
                self.state = 322
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__25 or _la == GrammarParser.T__26:
                    self.state = 321
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 325
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 324
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 327
                self.match(GrammarParser.T__8)
                self.state = 331
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == GrammarParser.T__4 or _la == GrammarParser.ID:
                    self.state = 328
                    self.operational_statement()
                    self.state = 333
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 334
                self.match(GrammarParser.T__9)
                pass

            elif la_ == 2:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 335
                self.match(GrammarParser.T__24)
                self.state = 337
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__25 or _la == GrammarParser.T__26:
                    self.state = 336
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 339
                self.match(GrammarParser.T__21)
                self.state = 340
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 341
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 3:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 342
                self.match(GrammarParser.T__24)
                self.state = 344
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__25 or _la == GrammarParser.T__26:
                    self.state = 343
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 346
                self.match(GrammarParser.T__21)
                self.state = 348
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 347
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 350
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.DuringRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 351
                self.match(GrammarParser.T__24)
                self.state = 353
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__25 or _la == GrammarParser.T__26:
                    self.state = 352
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 356
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 355
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 358
                self.match(GrammarParser.T__22)
                self.state = 359
                self.chain_id()
                self.state = 360
                self.match(GrammarParser.T__4)
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

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

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

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

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

        def operational_statement(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Operational_statementContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Operational_statementContext, i
                )

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
            self.state = 402
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 45, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.DuringAspectOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 364
                self.match(GrammarParser.T__27)
                self.state = 365
                self.match(GrammarParser.T__24)
                self.state = 366
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 368
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 367
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 370
                self.match(GrammarParser.T__8)
                self.state = 374
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == GrammarParser.T__4 or _la == GrammarParser.ID:
                    self.state = 371
                    self.operational_statement()
                    self.state = 376
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 377
                self.match(GrammarParser.T__9)
                pass

            elif la_ == 2:
                localctx = GrammarParser.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 378
                self.match(GrammarParser.T__27)
                self.state = 379
                self.match(GrammarParser.T__24)
                self.state = 380
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 381
                self.match(GrammarParser.T__21)
                self.state = 382
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 383
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 3:
                localctx = GrammarParser.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 384
                self.match(GrammarParser.T__27)
                self.state = 385
                self.match(GrammarParser.T__24)
                self.state = 386
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 387
                self.match(GrammarParser.T__21)
                self.state = 389
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 388
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 391
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.DuringAspectRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 392
                self.match(GrammarParser.T__27)
                self.state = 393
                self.match(GrammarParser.T__24)
                self.state = 394
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 396
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 395
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 398
                self.match(GrammarParser.T__22)
                self.state = 399
                self.chain_id()
                self.state = 400
                self.match(GrammarParser.T__4)
                pass

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

        def num_expression(self):
            return self.getTypedRuleContext(GrammarParser.Num_expressionContext, 0)

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
        self.enterRule(localctx, 20, self.RULE_operation_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 404
            self.match(GrammarParser.ID)
            self.state = 405
            self.match(GrammarParser.T__3)
            self.state = 406
            self.num_expression(0)
            self.state = 407
            self.match(GrammarParser.T__4)
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
        self.enterRule(localctx, 22, self.RULE_operational_statement)
        try:
            self.state = 411
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 409
                self.operation_assignment()
                pass
            elif token in [GrammarParser.T__4]:
                self.enterOuterAlt(localctx, 2)
                self.state = 410
                self.match(GrammarParser.T__4)
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
        self.enterRule(localctx, 24, self.RULE_state_inner_statement)
        try:
            self.state = 421
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.T__5, GrammarParser.T__6]:
                self.enterOuterAlt(localctx, 1)
                self.state = 413
                self.state_definition()
                pass
            elif token in [GrammarParser.T__10, GrammarParser.ID]:
                self.enterOuterAlt(localctx, 2)
                self.state = 414
                self.transition_definition()
                pass
            elif token in [GrammarParser.T__18]:
                self.enterOuterAlt(localctx, 3)
                self.state = 415
                self.transition_force_definition()
                pass
            elif token in [GrammarParser.T__20]:
                self.enterOuterAlt(localctx, 4)
                self.state = 416
                self.enter_definition()
                pass
            elif token in [GrammarParser.T__24]:
                self.enterOuterAlt(localctx, 5)
                self.state = 417
                self.during_definition()
                pass
            elif token in [GrammarParser.T__23]:
                self.enterOuterAlt(localctx, 6)
                self.state = 418
                self.exit_definition()
                pass
            elif token in [GrammarParser.T__27]:
                self.enterOuterAlt(localctx, 7)
                self.state = 419
                self.during_aspect_definition()
                pass
            elif token in [GrammarParser.T__4]:
                self.enterOuterAlt(localctx, 8)
                self.state = 420
                self.match(GrammarParser.T__4)
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
        self.enterRule(localctx, 26, self.RULE_operation_program)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 426
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 423
                self.operational_assignment()
                self.state = 428
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 429
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
        self.enterRule(localctx, 28, self.RULE_preamble_program)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 434
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 431
                self.preamble_statement()
                self.state = 436
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 437
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
        self.enterRule(localctx, 30, self.RULE_preamble_statement)
        try:
            self.state = 441
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 50, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 439
                self.initial_assignment()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 440
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

        def init_expression(self):
            return self.getTypedRuleContext(GrammarParser.Init_expressionContext, 0)

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
        self.enterRule(localctx, 32, self.RULE_initial_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 443
            self.match(GrammarParser.ID)
            self.state = 444
            self.match(GrammarParser.T__28)
            self.state = 445
            self.init_expression(0)
            self.state = 446
            self.match(GrammarParser.T__4)
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

        def init_expression(self):
            return self.getTypedRuleContext(GrammarParser.Init_expressionContext, 0)

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
        self.enterRule(localctx, 34, self.RULE_constant_definition)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 448
            self.match(GrammarParser.ID)
            self.state = 449
            self.match(GrammarParser.T__3)
            self.state = 450
            self.init_expression(0)
            self.state = 451
            self.match(GrammarParser.T__4)
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

        def num_expression(self):
            return self.getTypedRuleContext(GrammarParser.Num_expressionContext, 0)

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
        self.enterRule(localctx, 36, self.RULE_operational_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 453
            self.match(GrammarParser.ID)
            self.state = 454
            self.match(GrammarParser.T__28)
            self.state = 455
            self.num_expression(0)
            self.state = 456
            self.match(GrammarParser.T__4)
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
        self.enterRule(localctx, 38, self.RULE_generic_expression)
        try:
            self.state = 460
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 51, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 458
                self.num_expression(0)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 459
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
            self.function = None  # Token
            self.copyFrom(ctx)

        def init_expression(self):
            return self.getTypedRuleContext(GrammarParser.Init_expressionContext, 0)

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

        def init_expression(self):
            return self.getTypedRuleContext(GrammarParser.Init_expressionContext, 0)

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
        _startState = 40
        self.enterRecursionRule(localctx, 40, self.RULE_init_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 476
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.T__29]:
                localctx = GrammarParser.ParenExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 463
                self.match(GrammarParser.T__29)
                self.state = 464
                self.init_expression(0)
                self.state = 465
                self.match(GrammarParser.T__30)
                pass
            elif token in [
                GrammarParser.FLOAT,
                GrammarParser.INT,
                GrammarParser.HEX_INT,
            ]:
                localctx = GrammarParser.LiteralExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 467
                self.num_literal()
                pass
            elif token in [
                GrammarParser.T__52,
                GrammarParser.T__53,
                GrammarParser.T__54,
            ]:
                localctx = GrammarParser.MathConstExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 468
                self.math_const()
                pass
            elif token in [GrammarParser.T__31, GrammarParser.T__32]:
                localctx = GrammarParser.UnaryExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 469
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__31 or _la == GrammarParser.T__32):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 470
                self.init_expression(9)
                pass
            elif token in [GrammarParser.UFUNC_NAME]:
                localctx = GrammarParser.FuncExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 471
                localctx.function = self.match(GrammarParser.UFUNC_NAME)
                self.state = 472
                self.match(GrammarParser.T__29)
                self.state = 473
                self.init_expression(0)
                self.state = 474
                self.match(GrammarParser.T__30)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 501
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 54, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 499
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 53, self._ctx)
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
                        self.state = 478
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 479
                        localctx.op = self.match(GrammarParser.T__33)
                        self.state = 480
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
                        self.state = 481
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 482
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la) & ~0x3F) == 0
                            and (
                                (1 << _la)
                                & (
                                    (1 << GrammarParser.T__19)
                                    | (1 << GrammarParser.T__34)
                                    | (1 << GrammarParser.T__35)
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 483
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
                        self.state = 484
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 485
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__31 or _la == GrammarParser.T__32
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 486
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
                        self.state = 487
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 488
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__27 or _la == GrammarParser.T__36
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 489
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
                        self.state = 490
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 491
                        localctx.op = self.match(GrammarParser.T__37)
                        self.state = 492
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
                        self.state = 493
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 494
                        localctx.op = self.match(GrammarParser.T__38)
                        self.state = 495
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
                        self.state = 496
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 497
                        localctx.op = self.match(GrammarParser.T__39)
                        self.state = 498
                        self.init_expression(3)
                        pass

                self.state = 503
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 54, self._ctx)

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
            self.function = None  # Token
            self.copyFrom(ctx)

        def num_expression(self):
            return self.getTypedRuleContext(GrammarParser.Num_expressionContext, 0)

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

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def num_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Num_expressionContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Num_expressionContext, i)

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

        def num_expression(self):
            return self.getTypedRuleContext(GrammarParser.Num_expressionContext, 0)

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
        _startState = 42
        self.enterRecursionRule(localctx, 42, self.RULE_num_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 527
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 55, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 505
                self.match(GrammarParser.T__29)
                self.state = 506
                self.num_expression(0)
                self.state = 507
                self.match(GrammarParser.T__30)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 509
                self.num_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.IdExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 510
                self.match(GrammarParser.ID)
                pass

            elif la_ == 4:
                localctx = GrammarParser.MathConstExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 511
                self.math_const()
                pass

            elif la_ == 5:
                localctx = GrammarParser.UnaryExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 512
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__31 or _la == GrammarParser.T__32):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 513
                self.num_expression(10)
                pass

            elif la_ == 6:
                localctx = GrammarParser.FuncExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 514
                localctx.function = self.match(GrammarParser.UFUNC_NAME)
                self.state = 515
                self.match(GrammarParser.T__29)
                self.state = 516
                self.num_expression(0)
                self.state = 517
                self.match(GrammarParser.T__30)
                pass

            elif la_ == 7:
                localctx = GrammarParser.ConditionalCStyleExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 519
                self.match(GrammarParser.T__29)
                self.state = 520
                self.cond_expression(0)
                self.state = 521
                self.match(GrammarParser.T__30)
                self.state = 522
                self.match(GrammarParser.T__40)
                self.state = 523
                self.num_expression(0)
                self.state = 524
                self.match(GrammarParser.T__12)
                self.state = 525
                self.num_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 552
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 57, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 550
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 56, self._ctx)
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
                        self.state = 529
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 9)"
                            )
                        self.state = 530
                        localctx.op = self.match(GrammarParser.T__33)
                        self.state = 531
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
                        self.state = 532
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 533
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la) & ~0x3F) == 0
                            and (
                                (1 << _la)
                                & (
                                    (1 << GrammarParser.T__19)
                                    | (1 << GrammarParser.T__34)
                                    | (1 << GrammarParser.T__35)
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 534
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
                        self.state = 535
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 536
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__31 or _la == GrammarParser.T__32
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 537
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
                        self.state = 538
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 539
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__27 or _la == GrammarParser.T__36
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 540
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
                        self.state = 541
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 542
                        localctx.op = self.match(GrammarParser.T__37)
                        self.state = 543
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
                        self.state = 544
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 545
                        localctx.op = self.match(GrammarParser.T__38)
                        self.state = 546
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
                        self.state = 547
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 548
                        localctx.op = self.match(GrammarParser.T__39)
                        self.state = 549
                        self.num_expression(4)
                        pass

                self.state = 554
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 57, self._ctx)

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

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

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

        def cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Cond_expressionContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, i)

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
        _startState = 44
        self.enterRecursionRule(localctx, 44, self.RULE_cond_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 579
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 58, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 556
                self.match(GrammarParser.T__29)
                self.state = 557
                self.cond_expression(0)
                self.state = 558
                self.match(GrammarParser.T__30)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 560
                self.bool_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.UnaryExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 561
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__18 or _la == GrammarParser.T__41):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 562
                self.cond_expression(7)
                pass

            elif la_ == 4:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 563
                self.num_expression(0)
                self.state = 564
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (
                    ((_la) & ~0x3F) == 0
                    and (
                        (1 << _la)
                        & (
                            (1 << GrammarParser.T__42)
                            | (1 << GrammarParser.T__43)
                            | (1 << GrammarParser.T__44)
                            | (1 << GrammarParser.T__45)
                        )
                    )
                    != 0
                ):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 565
                self.num_expression(0)
                pass

            elif la_ == 5:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 567
                self.num_expression(0)
                self.state = 568
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__46 or _la == GrammarParser.T__47):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 569
                self.num_expression(0)
                pass

            elif la_ == 6:
                localctx = GrammarParser.ConditionalCStyleCondNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 571
                self.match(GrammarParser.T__29)
                self.state = 572
                self.cond_expression(0)
                self.state = 573
                self.match(GrammarParser.T__30)
                self.state = 574
                self.match(GrammarParser.T__40)
                self.state = 575
                self.cond_expression(0)
                self.state = 576
                self.match(GrammarParser.T__12)
                self.state = 577
                self.cond_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 592
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 60, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 590
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 59, self._ctx)
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
                        self.state = 581
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 582
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__46 or _la == GrammarParser.T__47
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 583
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
                        self.state = 584
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 585
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__48 or _la == GrammarParser.T__49
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 586
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
                        self.state = 587
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 588
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__50 or _la == GrammarParser.T__51
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 589
                        self.cond_expression(3)
                        pass

                self.state = 594
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 60, self._ctx)

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
        self.enterRule(localctx, 46, self.RULE_num_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 595
            _la = self._input.LA(1)
            if not (
                ((_la) & ~0x3F) == 0
                and (
                    (1 << _la)
                    & (
                        (1 << GrammarParser.FLOAT)
                        | (1 << GrammarParser.INT)
                        | (1 << GrammarParser.HEX_INT)
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
        self.enterRule(localctx, 48, self.RULE_bool_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 597
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
        self.enterRule(localctx, 50, self.RULE_math_const)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 599
            _la = self._input.LA(1)
            if not (
                ((_la) & ~0x3F) == 0
                and (
                    (1 << _la)
                    & (
                        (1 << GrammarParser.T__52)
                        | (1 << GrammarParser.T__53)
                        | (1 << GrammarParser.T__54)
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
        self.enterRule(localctx, 52, self.RULE_chain_id)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 602
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.T__34:
                self.state = 601
                localctx.isabs = self.match(GrammarParser.T__34)

            self.state = 604
            self.match(GrammarParser.ID)
            self.state = 609
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.T__55:
                self.state = 605
                self.match(GrammarParser.T__55)
                self.state = 606
                self.match(GrammarParser.ID)
                self.state = 611
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
        self._predicates[20] = self.init_expression_sempred
        self._predicates[21] = self.num_expression_sempred
        self._predicates[22] = self.cond_expression_sempred
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
