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
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3H")
        buf.write("\u027c\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7")
        buf.write("\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r\4\16")
        buf.write("\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23\t\23")
        buf.write("\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30\4\31")
        buf.write("\t\31\4\32\t\32\4\33\t\33\4\34\t\34\4\35\t\35\4\36\t\36")
        buf.write("\4\37\t\37\4 \t \3\2\3\2\3\2\3\3\7\3E\n\3\f\3\16\3H\13")
        buf.write("\3\3\3\3\3\3\3\3\4\3\4\3\4\3\4\3\4\3\4\3\4\3\5\5\5U\n")
        buf.write("\5\3\5\3\5\3\5\3\5\5\5[\n\5\3\5\3\5\5\5_\n\5\3\5\3\5\3")
        buf.write("\5\3\5\5\5e\n\5\3\5\3\5\7\5i\n\5\f\5\16\5l\13\5\3\5\5")
        buf.write("\5o\n\5\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3")
        buf.write("\6\5\6}\n\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u0085\n\6\3\6")
        buf.write("\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5")
        buf.write("\6\u0095\n\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u009d\n\6\3\6")
        buf.write("\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5")
        buf.write("\6\u00ad\n\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u00b5\n\6\5\6")
        buf.write("\u00b7\n\6\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7")
        buf.write("\3\7\3\7\3\7\3\7\5\7\u00c8\n\7\3\7\3\7\3\7\3\7\3\7\3\7")
        buf.write("\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\5\7\u00da\n\7")
        buf.write("\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3")
        buf.write("\7\5\7\u00ea\n\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3")
        buf.write("\7\3\7\3\7\3\7\3\7\5\7\u00fa\n\7\3\7\5\7\u00fd\n\7\3\b")
        buf.write("\3\b\5\b\u0101\n\b\3\b\3\b\3\b\3\b\3\b\3\b\3\b\3\b\3\b")
        buf.write("\3\b\3\b\5\b\u010e\n\b\3\b\3\b\3\b\5\b\u0113\n\b\3\b\3")
        buf.write("\b\3\b\3\b\5\b\u0119\n\b\3\t\3\t\5\t\u011d\n\t\3\t\3\t")
        buf.write("\3\t\3\t\3\t\3\t\3\t\3\t\3\t\3\t\3\t\5\t\u012a\n\t\3\t")
        buf.write("\3\t\3\t\5\t\u012f\n\t\3\t\3\t\3\t\3\t\5\t\u0135\n\t\3")
        buf.write("\n\3\n\5\n\u0139\n\n\3\n\5\n\u013c\n\n\3\n\3\n\3\n\3\n")
        buf.write("\3\n\3\n\5\n\u0144\n\n\3\n\3\n\3\n\3\n\3\n\5\n\u014b\n")
        buf.write("\n\3\n\3\n\5\n\u014f\n\n\3\n\3\n\3\n\5\n\u0154\n\n\3\n")
        buf.write("\5\n\u0157\n\n\3\n\3\n\3\n\3\n\5\n\u015d\n\n\3\13\3\13")
        buf.write("\3\13\3\13\5\13\u0163\n\13\3\13\3\13\3\13\3\13\3\13\3")
        buf.write("\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13\5\13")
        buf.write("\u0174\n\13\3\13\3\13\3\13\3\13\3\13\5\13\u017b\n\13\3")
        buf.write("\13\3\13\3\13\3\13\5\13\u0181\n\13\3\f\3\f\3\f\3\f\5\f")
        buf.write("\u0187\n\f\3\f\3\f\3\r\3\r\3\r\3\r\3\r\3\16\3\16\3\16")
        buf.write("\3\16\3\17\3\17\3\17\3\17\3\17\3\17\3\17\3\17\3\17\3\17")
        buf.write("\3\17\3\17\7\17\u01a0\n\17\f\17\16\17\u01a3\13\17\3\17")
        buf.write("\3\17\5\17\u01a7\n\17\3\20\3\20\3\20\5\20\u01ac\n\20\3")
        buf.write("\21\7\21\u01af\n\21\f\21\16\21\u01b2\13\21\3\22\3\22\3")
        buf.write("\22\3\22\3\22\3\22\3\22\3\22\3\22\5\22\u01bd\n\22\3\23")
        buf.write("\7\23\u01c0\n\23\f\23\16\23\u01c3\13\23\3\23\3\23\3\24")
        buf.write("\7\24\u01c8\n\24\f\24\16\24\u01cb\13\24\3\24\3\24\3\25")
        buf.write("\3\25\5\25\u01d1\n\25\3\26\3\26\3\26\3\26\3\26\3\27\3")
        buf.write("\27\3\27\3\27\3\27\3\30\3\30\3\30\3\30\3\30\3\31\3\31")
        buf.write("\5\31\u01e4\n\31\3\32\3\32\3\32\3\32\3\32\3\32\3\32\3")
        buf.write("\32\3\32\3\32\3\32\3\32\3\32\3\32\5\32\u01f4\n\32\3\32")
        buf.write("\3\32\3\32\3\32\3\32\3\32\3\32\3\32\3\32\3\32\3\32\3\32")
        buf.write("\3\32\3\32\3\32\3\32\3\32\3\32\3\32\3\32\3\32\7\32\u020b")
        buf.write("\n\32\f\32\16\32\u020e\13\32\3\33\3\33\3\33\3\33\3\33")
        buf.write("\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33")
        buf.write("\3\33\3\33\3\33\3\33\3\33\3\33\3\33\5\33\u0227\n\33\3")
        buf.write("\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33")
        buf.write("\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\7\33")
        buf.write("\u023e\n\33\f\33\16\33\u0241\13\33\3\34\3\34\3\34\3\34")
        buf.write("\3\34\3\34\3\34\3\34\3\34\3\34\3\34\3\34\3\34\3\34\3\34")
        buf.write("\3\34\3\34\3\34\3\34\3\34\3\34\3\34\3\34\3\34\5\34\u025b")
        buf.write("\n\34\3\34\3\34\3\34\3\34\3\34\3\34\3\34\3\34\3\34\7\34")
        buf.write("\u0266\n\34\f\34\16\34\u0269\13\34\3\35\3\35\3\36\3\36")
        buf.write("\3\37\3\37\3 \5 \u0272\n \3 \3 \3 \7 \u0277\n \f \16 ")
        buf.write("\u027a\13 \3 \2\5\62\64\66!\2\4\6\b\n\f\16\20\22\24\26")
        buf.write('\30\32\34\36 "$&(*,.\60\62\64\668:<>\2\20\3\2\4\5\3\2')
        buf.write("\17\20\3\2\34\35\3\2$%\4\2\26\26'(\4\2\36\36))\4\2\25")
        buf.write("\25..\3\2/\62\3\2\63\64\3\2\65\66\3\2\678\3\2=?\3\2@A")
        buf.write("\3\29;\2\u02cd\2@\3\2\2\2\4F\3\2\2\2\6L\3\2\2\2\bn\3\2")
        buf.write("\2\2\n\u00b6\3\2\2\2\f\u00fc\3\2\2\2\16\u0118\3\2\2\2")
        buf.write("\20\u0134\3\2\2\2\22\u015c\3\2\2\2\24\u0180\3\2\2\2\26")
        buf.write("\u0182\3\2\2\2\30\u018a\3\2\2\2\32\u018f\3\2\2\2\34\u0193")
        buf.write('\3\2\2\2\36\u01ab\3\2\2\2 \u01b0\3\2\2\2"\u01bc\3\2\2')
        buf.write("\2$\u01c1\3\2\2\2&\u01c9\3\2\2\2(\u01d0\3\2\2\2*\u01d2")
        buf.write("\3\2\2\2,\u01d7\3\2\2\2.\u01dc\3\2\2\2\60\u01e3\3\2\2")
        buf.write("\2\62\u01f3\3\2\2\2\64\u0226\3\2\2\2\66\u025a\3\2\2\2")
        buf.write("8\u026a\3\2\2\2:\u026c\3\2\2\2<\u026e\3\2\2\2>\u0271\3")
        buf.write("\2\2\2@A\5\66\34\2AB\7\2\2\3B\3\3\2\2\2CE\5\6\4\2DC\3")
        buf.write("\2\2\2EH\3\2\2\2FD\3\2\2\2FG\3\2\2\2GI\3\2\2\2HF\3\2\2")
        buf.write("\2IJ\5\b\5\2JK\7\2\2\3K\5\3\2\2\2LM\7\3\2\2MN\t\2\2\2")
        buf.write("NO\7C\2\2OP\7\6\2\2PQ\5\62\32\2QR\7\7\2\2R\7\3\2\2\2S")
        buf.write("U\7\b\2\2TS\3\2\2\2TU\3\2\2\2UV\3\2\2\2VW\7\t\2\2WZ\7")
        buf.write("C\2\2XY\7\n\2\2Y[\7D\2\2ZX\3\2\2\2Z[\3\2\2\2[\\\3\2\2")
        buf.write("\2\\o\7\7\2\2]_\7\b\2\2^]\3\2\2\2^_\3\2\2\2_`\3\2\2\2")
        buf.write("`a\7\t\2\2ad\7C\2\2bc\7\n\2\2ce\7D\2\2db\3\2\2\2de\3\2")
        buf.write('\2\2ef\3\2\2\2fj\7\13\2\2gi\5"\22\2hg\3\2\2\2il\3\2\2')
        buf.write("\2jh\3\2\2\2jk\3\2\2\2km\3\2\2\2lj\3\2\2\2mo\7\f\2\2n")
        buf.write("T\3\2\2\2n^\3\2\2\2o\t\3\2\2\2pq\7\r\2\2qr\7\16\2\2r|")
        buf.write("\7C\2\2s}\3\2\2\2tu\t\3\2\2u}\5> \2vw\7\17\2\2wx\7\21")
        buf.write("\2\2xy\7\22\2\2yz\5\66\34\2z{\7\23\2\2{}\3\2\2\2|s\3\2")
        buf.write("\2\2|t\3\2\2\2|v\3\2\2\2}\u0084\3\2\2\2~\u0085\7\7\2\2")
        buf.write("\177\u0080\7\24\2\2\u0080\u0081\7\13\2\2\u0081\u0082\5")
        buf.write(" \21\2\u0082\u0083\7\f\2\2\u0083\u0085\3\2\2\2\u0084~")
        buf.write("\3\2\2\2\u0084\177\3\2\2\2\u0085\u00b7\3\2\2\2\u0086\u0087")
        buf.write("\7C\2\2\u0087\u0088\7\16\2\2\u0088\u0094\7C\2\2\u0089")
        buf.write("\u0095\3\2\2\2\u008a\u008b\7\20\2\2\u008b\u0095\7C\2\2")
        buf.write("\u008c\u008d\7\17\2\2\u008d\u0095\5> \2\u008e\u008f\7")
        buf.write("\17\2\2\u008f\u0090\7\21\2\2\u0090\u0091\7\22\2\2\u0091")
        buf.write("\u0092\5\66\34\2\u0092\u0093\7\23\2\2\u0093\u0095\3\2")
        buf.write("\2\2\u0094\u0089\3\2\2\2\u0094\u008a\3\2\2\2\u0094\u008c")
        buf.write("\3\2\2\2\u0094\u008e\3\2\2\2\u0095\u009c\3\2\2\2\u0096")
        buf.write("\u009d\7\7\2\2\u0097\u0098\7\24\2\2\u0098\u0099\7\13\2")
        buf.write("\2\u0099\u009a\5 \21\2\u009a\u009b\7\f\2\2\u009b\u009d")
        buf.write("\3\2\2\2\u009c\u0096\3\2\2\2\u009c\u0097\3\2\2\2\u009d")
        buf.write("\u00b7\3\2\2\2\u009e\u009f\7C\2\2\u009f\u00a0\7\16\2\2")
        buf.write("\u00a0\u00ac\7\r\2\2\u00a1\u00ad\3\2\2\2\u00a2\u00a3\7")
        buf.write("\20\2\2\u00a3\u00ad\7C\2\2\u00a4\u00a5\7\17\2\2\u00a5")
        buf.write("\u00ad\5> \2\u00a6\u00a7\7\17\2\2\u00a7\u00a8\7\21\2\2")
        buf.write("\u00a8\u00a9\7\22\2\2\u00a9\u00aa\5\66\34\2\u00aa\u00ab")
        buf.write("\7\23\2\2\u00ab\u00ad\3\2\2\2\u00ac\u00a1\3\2\2\2\u00ac")
        buf.write("\u00a2\3\2\2\2\u00ac\u00a4\3\2\2\2\u00ac\u00a6\3\2\2\2")
        buf.write("\u00ad\u00b4\3\2\2\2\u00ae\u00b5\7\7\2\2\u00af\u00b0\7")
        buf.write("\24\2\2\u00b0\u00b1\7\13\2\2\u00b1\u00b2\5 \21\2\u00b2")
        buf.write("\u00b3\7\f\2\2\u00b3\u00b5\3\2\2\2\u00b4\u00ae\3\2\2\2")
        buf.write("\u00b4\u00af\3\2\2\2\u00b5\u00b7\3\2\2\2\u00b6p\3\2\2")
        buf.write("\2\u00b6\u0086\3\2\2\2\u00b6\u009e\3\2\2\2\u00b7\13\3")
        buf.write("\2\2\2\u00b8\u00b9\7\25\2\2\u00b9\u00ba\7C\2\2\u00ba\u00bb")
        buf.write("\7\16\2\2\u00bb\u00c7\7C\2\2\u00bc\u00c8\3\2\2\2\u00bd")
        buf.write("\u00be\7\20\2\2\u00be\u00c8\7C\2\2\u00bf\u00c0\7\17\2")
        buf.write("\2\u00c0\u00c8\5> \2\u00c1\u00c2\7\17\2\2\u00c2\u00c3")
        buf.write("\7\21\2\2\u00c3\u00c4\7\22\2\2\u00c4\u00c5\5\66\34\2\u00c5")
        buf.write("\u00c6\7\23\2\2\u00c6\u00c8\3\2\2\2\u00c7\u00bc\3\2\2")
        buf.write("\2\u00c7\u00bd\3\2\2\2\u00c7\u00bf\3\2\2\2\u00c7\u00c1")
        buf.write("\3\2\2\2\u00c8\u00c9\3\2\2\2\u00c9\u00fd\7\7\2\2\u00ca")
        buf.write("\u00cb\7\25\2\2\u00cb\u00cc\7C\2\2\u00cc\u00cd\7\16\2")
        buf.write("\2\u00cd\u00d9\7\r\2\2\u00ce\u00da\3\2\2\2\u00cf\u00d0")
        buf.write("\7\20\2\2\u00d0\u00da\7C\2\2\u00d1\u00d2\7\17\2\2\u00d2")
        buf.write("\u00da\5> \2\u00d3\u00d4\7\17\2\2\u00d4\u00d5\7\21\2\2")
        buf.write("\u00d5\u00d6\7\22\2\2\u00d6\u00d7\5\66\34\2\u00d7\u00d8")
        buf.write("\7\23\2\2\u00d8\u00da\3\2\2\2\u00d9\u00ce\3\2\2\2\u00d9")
        buf.write("\u00cf\3\2\2\2\u00d9\u00d1\3\2\2\2\u00d9\u00d3\3\2\2\2")
        buf.write("\u00da\u00db\3\2\2\2\u00db\u00fd\7\7\2\2\u00dc\u00dd\7")
        buf.write("\25\2\2\u00dd\u00de\7\26\2\2\u00de\u00df\7\16\2\2\u00df")
        buf.write("\u00e9\7C\2\2\u00e0\u00ea\3\2\2\2\u00e1\u00e2\t\3\2\2")
        buf.write("\u00e2\u00ea\5> \2\u00e3\u00e4\7\17\2\2\u00e4\u00e5\7")
        buf.write("\21\2\2\u00e5\u00e6\7\22\2\2\u00e6\u00e7\5\66\34\2\u00e7")
        buf.write("\u00e8\7\23\2\2\u00e8\u00ea\3\2\2\2\u00e9\u00e0\3\2\2")
        buf.write("\2\u00e9\u00e1\3\2\2\2\u00e9\u00e3\3\2\2\2\u00ea\u00eb")
        buf.write("\3\2\2\2\u00eb\u00fd\7\7\2\2\u00ec\u00ed\7\25\2\2\u00ed")
        buf.write("\u00ee\7\26\2\2\u00ee\u00ef\7\16\2\2\u00ef\u00f9\7\r\2")
        buf.write("\2\u00f0\u00fa\3\2\2\2\u00f1\u00f2\t\3\2\2\u00f2\u00fa")
        buf.write("\5> \2\u00f3\u00f4\7\17\2\2\u00f4\u00f5\7\21\2\2\u00f5")
        buf.write("\u00f6\7\22\2\2\u00f6\u00f7\5\66\34\2\u00f7\u00f8\7\23")
        buf.write("\2\2\u00f8\u00fa\3\2\2\2\u00f9\u00f0\3\2\2\2\u00f9\u00f1")
        buf.write("\3\2\2\2\u00f9\u00f3\3\2\2\2\u00fa\u00fb\3\2\2\2\u00fb")
        buf.write("\u00fd\7\7\2\2\u00fc\u00b8\3\2\2\2\u00fc\u00ca\3\2\2\2")
        buf.write("\u00fc\u00dc\3\2\2\2\u00fc\u00ec\3\2\2\2\u00fd\r\3\2\2")
        buf.write("\2\u00fe\u0100\7\27\2\2\u00ff\u0101\7C\2\2\u0100\u00ff")
        buf.write("\3\2\2\2\u0100\u0101\3\2\2\2\u0101\u0102\3\2\2\2\u0102")
        buf.write("\u0103\7\13\2\2\u0103\u0104\5 \21\2\u0104\u0105\7\f\2")
        buf.write("\2\u0105\u0119\3\2\2\2\u0106\u0107\7\27\2\2\u0107\u0108")
        buf.write("\7\30\2\2\u0108\u0109\7C\2\2\u0109\u0119\7\7\2\2\u010a")
        buf.write("\u010b\7\27\2\2\u010b\u010d\7\30\2\2\u010c\u010e\7C\2")
        buf.write("\2\u010d\u010c\3\2\2\2\u010d\u010e\3\2\2\2\u010e\u010f")
        buf.write("\3\2\2\2\u010f\u0119\7F\2\2\u0110\u0112\7\27\2\2\u0111")
        buf.write("\u0113\7C\2\2\u0112\u0111\3\2\2\2\u0112\u0113\3\2\2\2")
        buf.write("\u0113\u0114\3\2\2\2\u0114\u0115\7\31\2\2\u0115\u0116")
        buf.write("\5> \2\u0116\u0117\7\7\2\2\u0117\u0119\3\2\2\2\u0118\u00fe")
        buf.write("\3\2\2\2\u0118\u0106\3\2\2\2\u0118\u010a\3\2\2\2\u0118")
        buf.write("\u0110\3\2\2\2\u0119\17\3\2\2\2\u011a\u011c\7\32\2\2\u011b")
        buf.write("\u011d\7C\2\2\u011c\u011b\3\2\2\2\u011c\u011d\3\2\2\2")
        buf.write("\u011d\u011e\3\2\2\2\u011e\u011f\7\13\2\2\u011f\u0120")
        buf.write("\5 \21\2\u0120\u0121\7\f\2\2\u0121\u0135\3\2\2\2\u0122")
        buf.write("\u0123\7\32\2\2\u0123\u0124\7\30\2\2\u0124\u0125\7C\2")
        buf.write("\2\u0125\u0135\7\7\2\2\u0126\u0127\7\32\2\2\u0127\u0129")
        buf.write("\7\30\2\2\u0128\u012a\7C\2\2\u0129\u0128\3\2\2\2\u0129")
        buf.write("\u012a\3\2\2\2\u012a\u012b\3\2\2\2\u012b\u0135\7F\2\2")
        buf.write("\u012c\u012e\7\32\2\2\u012d\u012f\7C\2\2\u012e\u012d\3")
        buf.write("\2\2\2\u012e\u012f\3\2\2\2\u012f\u0130\3\2\2\2\u0130\u0131")
        buf.write("\7\31\2\2\u0131\u0132\5> \2\u0132\u0133\7\7\2\2\u0133")
        buf.write("\u0135\3\2\2\2\u0134\u011a\3\2\2\2\u0134\u0122\3\2\2\2")
        buf.write("\u0134\u0126\3\2\2\2\u0134\u012c\3\2\2\2\u0135\21\3\2")
        buf.write("\2\2\u0136\u0138\7\33\2\2\u0137\u0139\t\4\2\2\u0138\u0137")
        buf.write("\3\2\2\2\u0138\u0139\3\2\2\2\u0139\u013b\3\2\2\2\u013a")
        buf.write("\u013c\7C\2\2\u013b\u013a\3\2\2\2\u013b\u013c\3\2\2\2")
        buf.write("\u013c\u013d\3\2\2\2\u013d\u013e\7\13\2\2\u013e\u013f")
        buf.write("\5 \21\2\u013f\u0140\7\f\2\2\u0140\u015d\3\2\2\2\u0141")
        buf.write("\u0143\7\33\2\2\u0142\u0144\t\4\2\2\u0143\u0142\3\2\2")
        buf.write("\2\u0143\u0144\3\2\2\2\u0144\u0145\3\2\2\2\u0145\u0146")
        buf.write("\7\30\2\2\u0146\u0147\7C\2\2\u0147\u015d\7\7\2\2\u0148")
        buf.write("\u014a\7\33\2\2\u0149\u014b\t\4\2\2\u014a\u0149\3\2\2")
        buf.write("\2\u014a\u014b\3\2\2\2\u014b\u014c\3\2\2\2\u014c\u014e")
        buf.write("\7\30\2\2\u014d\u014f\7C\2\2\u014e\u014d\3\2\2\2\u014e")
        buf.write("\u014f\3\2\2\2\u014f\u0150\3\2\2\2\u0150\u015d\7F\2\2")
        buf.write("\u0151\u0153\7\33\2\2\u0152\u0154\t\4\2\2\u0153\u0152")
        buf.write("\3\2\2\2\u0153\u0154\3\2\2\2\u0154\u0156\3\2\2\2\u0155")
        buf.write("\u0157\7C\2\2\u0156\u0155\3\2\2\2\u0156\u0157\3\2\2\2")
        buf.write("\u0157\u0158\3\2\2\2\u0158\u0159\7\31\2\2\u0159\u015a")
        buf.write("\5> \2\u015a\u015b\7\7\2\2\u015b\u015d\3\2\2\2\u015c\u0136")
        buf.write("\3\2\2\2\u015c\u0141\3\2\2\2\u015c\u0148\3\2\2\2\u015c")
        buf.write("\u0151\3\2\2\2\u015d\23\3\2\2\2\u015e\u015f\7\36\2\2\u015f")
        buf.write("\u0160\7\33\2\2\u0160\u0162\t\4\2\2\u0161\u0163\7C\2\2")
        buf.write("\u0162\u0161\3\2\2\2\u0162\u0163\3\2\2\2\u0163\u0164\3")
        buf.write("\2\2\2\u0164\u0165\7\13\2\2\u0165\u0166\5 \21\2\u0166")
        buf.write("\u0167\7\f\2\2\u0167\u0181\3\2\2\2\u0168\u0169\7\36\2")
        buf.write("\2\u0169\u016a\7\33\2\2\u016a\u016b\t\4\2\2\u016b\u016c")
        buf.write("\7\30\2\2\u016c\u016d\7C\2\2\u016d\u0181\7\7\2\2\u016e")
        buf.write("\u016f\7\36\2\2\u016f\u0170\7\33\2\2\u0170\u0171\t\4\2")
        buf.write("\2\u0171\u0173\7\30\2\2\u0172\u0174\7C\2\2\u0173\u0172")
        buf.write("\3\2\2\2\u0173\u0174\3\2\2\2\u0174\u0175\3\2\2\2\u0175")
        buf.write("\u0181\7F\2\2\u0176\u0177\7\36\2\2\u0177\u0178\7\33\2")
        buf.write("\2\u0178\u017a\t\4\2\2\u0179\u017b\7C\2\2\u017a\u0179")
        buf.write("\3\2\2\2\u017a\u017b\3\2\2\2\u017b\u017c\3\2\2\2\u017c")
        buf.write("\u017d\7\31\2\2\u017d\u017e\5> \2\u017e\u017f\7\7\2\2")
        buf.write("\u017f\u0181\3\2\2\2\u0180\u015e\3\2\2\2\u0180\u0168\3")
        buf.write("\2\2\2\u0180\u016e\3\2\2\2\u0180\u0176\3\2\2\2\u0181\25")
        buf.write("\3\2\2\2\u0182\u0183\7\37\2\2\u0183\u0186\7C\2\2\u0184")
        buf.write("\u0185\7\n\2\2\u0185\u0187\7D\2\2\u0186\u0184\3\2\2\2")
        buf.write("\u0186\u0187\3\2\2\2\u0187\u0188\3\2\2\2\u0188\u0189\7")
        buf.write("\7\2\2\u0189\27\3\2\2\2\u018a\u018b\7C\2\2\u018b\u018c")
        buf.write("\7\6\2\2\u018c\u018d\5\64\33\2\u018d\u018e\7\7\2\2\u018e")
        buf.write("\31\3\2\2\2\u018f\u0190\7\13\2\2\u0190\u0191\5 \21\2\u0191")
        buf.write("\u0192\7\f\2\2\u0192\33\3\2\2\2\u0193\u0194\7\21\2\2\u0194")
        buf.write("\u0195\7\22\2\2\u0195\u0196\5\66\34\2\u0196\u0197\7\23")
        buf.write("\2\2\u0197\u01a1\5\32\16\2\u0198\u0199\7 \2\2\u0199\u019a")
        buf.write("\7\21\2\2\u019a\u019b\7\22\2\2\u019b\u019c\5\66\34\2\u019c")
        buf.write("\u019d\7\23\2\2\u019d\u019e\5\32\16\2\u019e\u01a0\3\2")
        buf.write("\2\2\u019f\u0198\3\2\2\2\u01a0\u01a3\3\2\2\2\u01a1\u019f")
        buf.write("\3\2\2\2\u01a1\u01a2\3\2\2\2\u01a2\u01a6\3\2\2\2\u01a3")
        buf.write("\u01a1\3\2\2\2\u01a4\u01a5\7 \2\2\u01a5\u01a7\5\32\16")
        buf.write("\2\u01a6\u01a4\3\2\2\2\u01a6\u01a7\3\2\2\2\u01a7\35\3")
        buf.write("\2\2\2\u01a8\u01ac\5\30\r\2\u01a9\u01ac\5\34\17\2\u01aa")
        buf.write("\u01ac\7\7\2\2\u01ab\u01a8\3\2\2\2\u01ab\u01a9\3\2\2\2")
        buf.write("\u01ab\u01aa\3\2\2\2\u01ac\37\3\2\2\2\u01ad\u01af\5\36")
        buf.write("\20\2\u01ae\u01ad\3\2\2\2\u01af\u01b2\3\2\2\2\u01b0\u01ae")
        buf.write("\3\2\2\2\u01b0\u01b1\3\2\2\2\u01b1!\3\2\2\2\u01b2\u01b0")
        buf.write("\3\2\2\2\u01b3\u01bd\5\b\5\2\u01b4\u01bd\5\n\6\2\u01b5")
        buf.write("\u01bd\5\f\7\2\u01b6\u01bd\5\16\b\2\u01b7\u01bd\5\22\n")
        buf.write("\2\u01b8\u01bd\5\20\t\2\u01b9\u01bd\5\24\13\2\u01ba\u01bd")
        buf.write("\5\26\f\2\u01bb\u01bd\7\7\2\2\u01bc\u01b3\3\2\2\2\u01bc")
        buf.write("\u01b4\3\2\2\2\u01bc\u01b5\3\2\2\2\u01bc\u01b6\3\2\2\2")
        buf.write("\u01bc\u01b7\3\2\2\2\u01bc\u01b8\3\2\2\2\u01bc\u01b9\3")
        buf.write("\2\2\2\u01bc\u01ba\3\2\2\2\u01bc\u01bb\3\2\2\2\u01bd#")
        buf.write("\3\2\2\2\u01be\u01c0\5.\30\2\u01bf\u01be\3\2\2\2\u01c0")
        buf.write("\u01c3\3\2\2\2\u01c1\u01bf\3\2\2\2\u01c1\u01c2\3\2\2\2")
        buf.write("\u01c2\u01c4\3\2\2\2\u01c3\u01c1\3\2\2\2\u01c4\u01c5\7")
        buf.write("\2\2\3\u01c5%\3\2\2\2\u01c6\u01c8\5(\25\2\u01c7\u01c6")
        buf.write("\3\2\2\2\u01c8\u01cb\3\2\2\2\u01c9\u01c7\3\2\2\2\u01c9")
        buf.write("\u01ca\3\2\2\2\u01ca\u01cc\3\2\2\2\u01cb\u01c9\3\2\2\2")
        buf.write("\u01cc\u01cd\7\2\2\3\u01cd'\3\2\2\2\u01ce\u01d1\5*\26")
        buf.write("\2\u01cf\u01d1\5,\27\2\u01d0\u01ce\3\2\2\2\u01d0\u01cf")
        buf.write("\3\2\2\2\u01d1)\3\2\2\2\u01d2\u01d3\7C\2\2\u01d3\u01d4")
        buf.write("\7!\2\2\u01d4\u01d5\5\62\32\2\u01d5\u01d6\7\7\2\2\u01d6")
        buf.write("+\3\2\2\2\u01d7\u01d8\7C\2\2\u01d8\u01d9\7\6\2\2\u01d9")
        buf.write("\u01da\5\62\32\2\u01da\u01db\7\7\2\2\u01db-\3\2\2\2\u01dc")
        buf.write("\u01dd\7C\2\2\u01dd\u01de\7!\2\2\u01de\u01df\5\64\33\2")
        buf.write("\u01df\u01e0\7\7\2\2\u01e0/\3\2\2\2\u01e1\u01e4\5\64\33")
        buf.write("\2\u01e2\u01e4\5\66\34\2\u01e3\u01e1\3\2\2\2\u01e3\u01e2")
        buf.write("\3\2\2\2\u01e4\61\3\2\2\2\u01e5\u01e6\b\32\1\2\u01e6\u01e7")
        buf.write('\7"\2\2\u01e7\u01e8\5\62\32\2\u01e8\u01e9\7#\2\2\u01e9')
        buf.write("\u01f4\3\2\2\2\u01ea\u01f4\58\35\2\u01eb\u01f4\5<\37\2")
        buf.write("\u01ec\u01ed\t\5\2\2\u01ed\u01f4\5\62\32\13\u01ee\u01ef")
        buf.write('\7B\2\2\u01ef\u01f0\7"\2\2\u01f0\u01f1\5\62\32\2\u01f1')
        buf.write("\u01f2\7#\2\2\u01f2\u01f4\3\2\2\2\u01f3\u01e5\3\2\2\2")
        buf.write("\u01f3\u01ea\3\2\2\2\u01f3\u01eb\3\2\2\2\u01f3\u01ec\3")
        buf.write("\2\2\2\u01f3\u01ee\3\2\2\2\u01f4\u020c\3\2\2\2\u01f5\u01f6")
        buf.write("\f\n\2\2\u01f6\u01f7\7&\2\2\u01f7\u020b\5\62\32\n\u01f8")
        buf.write("\u01f9\f\t\2\2\u01f9\u01fa\t\6\2\2\u01fa\u020b\5\62\32")
        buf.write("\n\u01fb\u01fc\f\b\2\2\u01fc\u01fd\t\5\2\2\u01fd\u020b")
        buf.write("\5\62\32\t\u01fe\u01ff\f\7\2\2\u01ff\u0200\t\7\2\2\u0200")
        buf.write("\u020b\5\62\32\b\u0201\u0202\f\6\2\2\u0202\u0203\7*\2")
        buf.write("\2\u0203\u020b\5\62\32\7\u0204\u0205\f\5\2\2\u0205\u0206")
        buf.write("\7+\2\2\u0206\u020b\5\62\32\6\u0207\u0208\f\4\2\2\u0208")
        buf.write("\u0209\7,\2\2\u0209\u020b\5\62\32\5\u020a\u01f5\3\2\2")
        buf.write("\2\u020a\u01f8\3\2\2\2\u020a\u01fb\3\2\2\2\u020a\u01fe")
        buf.write("\3\2\2\2\u020a\u0201\3\2\2\2\u020a\u0204\3\2\2\2\u020a")
        buf.write("\u0207\3\2\2\2\u020b\u020e\3\2\2\2\u020c\u020a\3\2\2\2")
        buf.write("\u020c\u020d\3\2\2\2\u020d\63\3\2\2\2\u020e\u020c\3\2")
        buf.write('\2\2\u020f\u0210\b\33\1\2\u0210\u0211\7"\2\2\u0211\u0212')
        buf.write("\5\64\33\2\u0212\u0213\7#\2\2\u0213\u0227\3\2\2\2\u0214")
        buf.write("\u0227\58\35\2\u0215\u0227\7C\2\2\u0216\u0227\5<\37\2")
        buf.write("\u0217\u0218\t\5\2\2\u0218\u0227\5\64\33\f\u0219\u021a")
        buf.write('\7B\2\2\u021a\u021b\7"\2\2\u021b\u021c\5\64\33\2\u021c')
        buf.write('\u021d\7#\2\2\u021d\u0227\3\2\2\2\u021e\u021f\7"\2\2')
        buf.write("\u021f\u0220\5\66\34\2\u0220\u0221\7#\2\2\u0221\u0222")
        buf.write("\7-\2\2\u0222\u0223\5\64\33\2\u0223\u0224\7\17\2\2\u0224")
        buf.write("\u0225\5\64\33\3\u0225\u0227\3\2\2\2\u0226\u020f\3\2\2")
        buf.write("\2\u0226\u0214\3\2\2\2\u0226\u0215\3\2\2\2\u0226\u0216")
        buf.write("\3\2\2\2\u0226\u0217\3\2\2\2\u0226\u0219\3\2\2\2\u0226")
        buf.write("\u021e\3\2\2\2\u0227\u023f\3\2\2\2\u0228\u0229\f\13\2")
        buf.write("\2\u0229\u022a\7&\2\2\u022a\u023e\5\64\33\13\u022b\u022c")
        buf.write("\f\n\2\2\u022c\u022d\t\6\2\2\u022d\u023e\5\64\33\13\u022e")
        buf.write("\u022f\f\t\2\2\u022f\u0230\t\5\2\2\u0230\u023e\5\64\33")
        buf.write("\n\u0231\u0232\f\b\2\2\u0232\u0233\t\7\2\2\u0233\u023e")
        buf.write("\5\64\33\t\u0234\u0235\f\7\2\2\u0235\u0236\7*\2\2\u0236")
        buf.write("\u023e\5\64\33\b\u0237\u0238\f\6\2\2\u0238\u0239\7+\2")
        buf.write("\2\u0239\u023e\5\64\33\7\u023a\u023b\f\5\2\2\u023b\u023c")
        buf.write("\7,\2\2\u023c\u023e\5\64\33\6\u023d\u0228\3\2\2\2\u023d")
        buf.write("\u022b\3\2\2\2\u023d\u022e\3\2\2\2\u023d\u0231\3\2\2\2")
        buf.write("\u023d\u0234\3\2\2\2\u023d\u0237\3\2\2\2\u023d\u023a\3")
        buf.write("\2\2\2\u023e\u0241\3\2\2\2\u023f\u023d\3\2\2\2\u023f\u0240")
        buf.write("\3\2\2\2\u0240\65\3\2\2\2\u0241\u023f\3\2\2\2\u0242\u0243")
        buf.write('\b\34\1\2\u0243\u0244\7"\2\2\u0244\u0245\5\66\34\2\u0245')
        buf.write("\u0246\7#\2\2\u0246\u025b\3\2\2\2\u0247\u025b\5:\36\2")
        buf.write("\u0248\u0249\t\b\2\2\u0249\u025b\5\66\34\t\u024a\u024b")
        buf.write("\5\64\33\2\u024b\u024c\t\t\2\2\u024c\u024d\5\64\33\2\u024d")
        buf.write("\u025b\3\2\2\2\u024e\u024f\5\64\33\2\u024f\u0250\t\n\2")
        buf.write("\2\u0250\u0251\5\64\33\2\u0251\u025b\3\2\2\2\u0252\u0253")
        buf.write('\7"\2\2\u0253\u0254\5\66\34\2\u0254\u0255\7#\2\2\u0255')
        buf.write("\u0256\7-\2\2\u0256\u0257\5\66\34\2\u0257\u0258\7\17\2")
        buf.write("\2\u0258\u0259\5\66\34\3\u0259\u025b\3\2\2\2\u025a\u0242")
        buf.write("\3\2\2\2\u025a\u0247\3\2\2\2\u025a\u0248\3\2\2\2\u025a")
        buf.write("\u024a\3\2\2\2\u025a\u024e\3\2\2\2\u025a\u0252\3\2\2\2")
        buf.write("\u025b\u0267\3\2\2\2\u025c\u025d\f\6\2\2\u025d\u025e\t")
        buf.write("\n\2\2\u025e\u0266\5\66\34\7\u025f\u0260\f\5\2\2\u0260")
        buf.write("\u0261\t\13\2\2\u0261\u0266\5\66\34\6\u0262\u0263\f\4")
        buf.write("\2\2\u0263\u0264\t\f\2\2\u0264\u0266\5\66\34\5\u0265\u025c")
        buf.write("\3\2\2\2\u0265\u025f\3\2\2\2\u0265\u0262\3\2\2\2\u0266")
        buf.write("\u0269\3\2\2\2\u0267\u0265\3\2\2\2\u0267\u0268\3\2\2\2")
        buf.write("\u0268\67\3\2\2\2\u0269\u0267\3\2\2\2\u026a\u026b\t\r")
        buf.write("\2\2\u026b9\3\2\2\2\u026c\u026d\t\16\2\2\u026d;\3\2\2")
        buf.write("\2\u026e\u026f\t\17\2\2\u026f=\3\2\2\2\u0270\u0272\7'")
        buf.write("\2\2\u0271\u0270\3\2\2\2\u0271\u0272\3\2\2\2\u0272\u0273")
        buf.write("\3\2\2\2\u0273\u0278\7C\2\2\u0274\u0275\7<\2\2\u0275\u0277")
        buf.write("\7C\2\2\u0276\u0274\3\2\2\2\u0277\u027a\3\2\2\2\u0278")
        buf.write("\u0276\3\2\2\2\u0278\u0279\3\2\2\2\u0279?\3\2\2\2\u027a")
        buf.write("\u0278\3\2\2\2>FTZ^djn|\u0084\u0094\u009c\u00ac\u00b4")
        buf.write("\u00b6\u00c7\u00d9\u00e9\u00f9\u00fc\u0100\u010d\u0112")
        buf.write("\u0118\u011c\u0129\u012e\u0134\u0138\u013b\u0143\u014a")
        buf.write("\u014e\u0153\u0156\u015c\u0162\u0173\u017a\u0180\u0186")
        buf.write("\u01a1\u01a6\u01ab\u01b0\u01bc\u01c1\u01c9\u01d0\u01e3")
        buf.write("\u01f3\u020a\u020c\u0226\u023d\u023f\u025a\u0265\u0267")
        buf.write("\u0271\u0278")
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
        "'event'",
        "'else'",
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
    RULE_event_definition = 10
    RULE_operation_assignment = 11
    RULE_operation_block = 12
    RULE_if_statement = 13
    RULE_operational_statement = 14
    RULE_operational_statement_set = 15
    RULE_state_inner_statement = 16
    RULE_operation_program = 17
    RULE_preamble_program = 18
    RULE_preamble_statement = 19
    RULE_initial_assignment = 20
    RULE_constant_definition = 21
    RULE_operational_assignment = 22
    RULE_generic_expression = 23
    RULE_init_expression = 24
    RULE_num_expression = 25
    RULE_cond_expression = 26
    RULE_num_literal = 27
    RULE_bool_literal = 28
    RULE_math_const = 29
    RULE_chain_id = 30

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
    T__56 = 57
    T__57 = 58
    FLOAT = 59
    INT = 60
    HEX_INT = 61
    TRUE = 62
    FALSE = 63
    UFUNC_NAME = 64
    ID = 65
    STRING = 66
    WS = 67
    MULTILINE_COMMENT = 68
    LINE_COMMENT = 69
    PYTHON_COMMENT = 70

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
            self.state = 62
            self.cond_expression(0)
            self.state = 63
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
            self.state = 68
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.T__0:
                self.state = 65
                self.def_assignment()
                self.state = 70
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 71
            self.state_definition()
            self.state = 72
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
            self.state = 74
            self.match(GrammarParser.T__0)
            self.state = 75
            localctx.deftype = self._input.LT(1)
            _la = self._input.LA(1)
            if not (_la == GrammarParser.T__1 or _la == GrammarParser.T__2):
                localctx.deftype = self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 76
            self.match(GrammarParser.ID)
            self.state = 77
            self.match(GrammarParser.T__3)
            self.state = 78
            self.init_expression(0)
            self.state = 79
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
            self.state = 108
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 6, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.LeafStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 82
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__5:
                    self.state = 81
                    localctx.pseudo = self.match(GrammarParser.T__5)

                self.state = 84
                self.match(GrammarParser.T__6)
                self.state = 85
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 88
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__7:
                    self.state = 86
                    self.match(GrammarParser.T__7)
                    self.state = 87
                    localctx.extra_name = self.match(GrammarParser.STRING)

                self.state = 90
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 2:
                localctx = GrammarParser.CompositeStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 92
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__5:
                    self.state = 91
                    localctx.pseudo = self.match(GrammarParser.T__5)

                self.state = 94
                self.match(GrammarParser.T__6)
                self.state = 95
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 98
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__7:
                    self.state = 96
                    self.match(GrammarParser.T__7)
                    self.state = 97
                    localctx.extra_name = self.match(GrammarParser.STRING)

                self.state = 100
                self.match(GrammarParser.T__8)
                self.state = 104
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while ((_la - 5) & ~0x3F) == 0 and (
                    (1 << (_la - 5))
                    & (
                        (1 << (GrammarParser.T__4 - 5))
                        | (1 << (GrammarParser.T__5 - 5))
                        | (1 << (GrammarParser.T__6 - 5))
                        | (1 << (GrammarParser.T__10 - 5))
                        | (1 << (GrammarParser.T__18 - 5))
                        | (1 << (GrammarParser.T__20 - 5))
                        | (1 << (GrammarParser.T__23 - 5))
                        | (1 << (GrammarParser.T__24 - 5))
                        | (1 << (GrammarParser.T__27 - 5))
                        | (1 << (GrammarParser.T__28 - 5))
                        | (1 << (GrammarParser.ID - 5))
                    )
                ) != 0:
                    self.state = 101
                    self.state_inner_statement()
                    self.state = 106
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 107
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

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
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

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
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

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
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
            self.state = 180
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 13, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EntryTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 110
                self.match(GrammarParser.T__10)
                self.state = 111
                self.match(GrammarParser.T__11)
                self.state = 112
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 122
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 7, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 114
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__12 or _la == GrammarParser.T__13):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 115
                    self.chain_id()
                    pass

                elif la_ == 3:
                    self.state = 116
                    self.match(GrammarParser.T__12)
                    self.state = 117
                    self.match(GrammarParser.T__14)
                    self.state = 118
                    self.match(GrammarParser.T__15)
                    self.state = 119
                    self.cond_expression(0)
                    self.state = 120
                    self.match(GrammarParser.T__16)
                    pass

                self.state = 130
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.T__4]:
                    self.state = 124
                    self.match(GrammarParser.T__4)
                    pass
                elif token in [GrammarParser.T__17]:
                    self.state = 125
                    self.match(GrammarParser.T__17)
                    self.state = 126
                    self.match(GrammarParser.T__8)
                    self.state = 127
                    self.operational_statement_set()
                    self.state = 128
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
                self.state = 132
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 133
                self.match(GrammarParser.T__11)
                self.state = 134
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 146
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 9, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 136
                    self.match(GrammarParser.T__13)
                    self.state = 137
                    localctx.from_id = self.match(GrammarParser.ID)
                    pass

                elif la_ == 3:
                    self.state = 138
                    self.match(GrammarParser.T__12)
                    self.state = 139
                    self.chain_id()
                    pass

                elif la_ == 4:
                    self.state = 140
                    self.match(GrammarParser.T__12)
                    self.state = 141
                    self.match(GrammarParser.T__14)
                    self.state = 142
                    self.match(GrammarParser.T__15)
                    self.state = 143
                    self.cond_expression(0)
                    self.state = 144
                    self.match(GrammarParser.T__16)
                    pass

                self.state = 154
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.T__4]:
                    self.state = 148
                    self.match(GrammarParser.T__4)
                    pass
                elif token in [GrammarParser.T__17]:
                    self.state = 149
                    self.match(GrammarParser.T__17)
                    self.state = 150
                    self.match(GrammarParser.T__8)
                    self.state = 151
                    self.operational_statement_set()
                    self.state = 152
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
                la_ = self._interp.adaptivePredict(self._input, 11, self._ctx)
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

                self.state = 178
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
                    self.state = 175
                    self.operational_statement_set()
                    self.state = 176
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
            self.state = 250
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 18, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.NormalForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 182
                self.match(GrammarParser.T__18)
                self.state = 183
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 184
                self.match(GrammarParser.T__11)
                self.state = 185
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 197
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 14, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 187
                    self.match(GrammarParser.T__13)
                    self.state = 188
                    localctx.from_id = self.match(GrammarParser.ID)
                    pass

                elif la_ == 3:
                    self.state = 189
                    self.match(GrammarParser.T__12)
                    self.state = 190
                    self.chain_id()
                    pass

                elif la_ == 4:
                    self.state = 191
                    self.match(GrammarParser.T__12)
                    self.state = 192
                    self.match(GrammarParser.T__14)
                    self.state = 193
                    self.match(GrammarParser.T__15)
                    self.state = 194
                    self.cond_expression(0)
                    self.state = 195
                    self.match(GrammarParser.T__16)
                    pass

                self.state = 199
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 2:
                localctx = GrammarParser.ExitForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 2)
                self.state = 200
                self.match(GrammarParser.T__18)
                self.state = 201
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 202
                self.match(GrammarParser.T__11)
                self.state = 203
                self.match(GrammarParser.T__10)
                self.state = 215
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 15, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 205
                    self.match(GrammarParser.T__13)
                    self.state = 206
                    localctx.from_id = self.match(GrammarParser.ID)
                    pass

                elif la_ == 3:
                    self.state = 207
                    self.match(GrammarParser.T__12)
                    self.state = 208
                    self.chain_id()
                    pass

                elif la_ == 4:
                    self.state = 209
                    self.match(GrammarParser.T__12)
                    self.state = 210
                    self.match(GrammarParser.T__14)
                    self.state = 211
                    self.match(GrammarParser.T__15)
                    self.state = 212
                    self.cond_expression(0)
                    self.state = 213
                    self.match(GrammarParser.T__16)
                    pass

                self.state = 217
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 3:
                localctx = GrammarParser.NormalAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 3)
                self.state = 218
                self.match(GrammarParser.T__18)
                self.state = 219
                self.match(GrammarParser.T__19)
                self.state = 220
                self.match(GrammarParser.T__11)
                self.state = 221
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 231
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 16, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 223
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__12 or _la == GrammarParser.T__13):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 224
                    self.chain_id()
                    pass

                elif la_ == 3:
                    self.state = 225
                    self.match(GrammarParser.T__12)
                    self.state = 226
                    self.match(GrammarParser.T__14)
                    self.state = 227
                    self.match(GrammarParser.T__15)
                    self.state = 228
                    self.cond_expression(0)
                    self.state = 229
                    self.match(GrammarParser.T__16)
                    pass

                self.state = 233
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 4:
                localctx = GrammarParser.ExitAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 4)
                self.state = 234
                self.match(GrammarParser.T__18)
                self.state = 235
                self.match(GrammarParser.T__19)
                self.state = 236
                self.match(GrammarParser.T__11)
                self.state = 237
                self.match(GrammarParser.T__10)
                self.state = 247
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 17, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 239
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__12 or _la == GrammarParser.T__13):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 240
                    self.chain_id()
                    pass

                elif la_ == 3:
                    self.state = 241
                    self.match(GrammarParser.T__12)
                    self.state = 242
                    self.match(GrammarParser.T__14)
                    self.state = 243
                    self.match(GrammarParser.T__15)
                    self.state = 244
                    self.cond_expression(0)
                    self.state = 245
                    self.match(GrammarParser.T__16)
                    pass

                self.state = 249
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

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
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
            self.state = 278
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 22, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EnterOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 252
                self.match(GrammarParser.T__20)
                self.state = 254
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 253
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 256
                self.match(GrammarParser.T__8)
                self.state = 257
                self.operational_statement_set()
                self.state = 258
                self.match(GrammarParser.T__9)
                pass

            elif la_ == 2:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 260
                self.match(GrammarParser.T__20)
                self.state = 261
                self.match(GrammarParser.T__21)
                self.state = 262
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 263
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 3:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 264
                self.match(GrammarParser.T__20)
                self.state = 265
                self.match(GrammarParser.T__21)
                self.state = 267
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 266
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 269
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.EnterRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 270
                self.match(GrammarParser.T__20)
                self.state = 272
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 271
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 274
                self.match(GrammarParser.T__22)
                self.state = 275
                self.chain_id()
                self.state = 276
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

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
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
            self.state = 306
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 26, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ExitOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 280
                self.match(GrammarParser.T__23)
                self.state = 282
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 281
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 284
                self.match(GrammarParser.T__8)
                self.state = 285
                self.operational_statement_set()
                self.state = 286
                self.match(GrammarParser.T__9)
                pass

            elif la_ == 2:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 288
                self.match(GrammarParser.T__23)
                self.state = 289
                self.match(GrammarParser.T__21)
                self.state = 290
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 291
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 3:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 292
                self.match(GrammarParser.T__23)
                self.state = 293
                self.match(GrammarParser.T__21)
                self.state = 295
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 294
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 297
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.ExitRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 298
                self.match(GrammarParser.T__23)
                self.state = 300
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 299
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 302
                self.match(GrammarParser.T__22)
                self.state = 303
                self.chain_id()
                self.state = 304
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

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
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
            self.state = 346
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 34, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.DuringOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 308
                self.match(GrammarParser.T__24)
                self.state = 310
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__25 or _la == GrammarParser.T__26:
                    self.state = 309
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 313
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 312
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 315
                self.match(GrammarParser.T__8)
                self.state = 316
                self.operational_statement_set()
                self.state = 317
                self.match(GrammarParser.T__9)
                pass

            elif la_ == 2:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 319
                self.match(GrammarParser.T__24)
                self.state = 321
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__25 or _la == GrammarParser.T__26:
                    self.state = 320
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 323
                self.match(GrammarParser.T__21)
                self.state = 324
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 325
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 3:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 326
                self.match(GrammarParser.T__24)
                self.state = 328
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__25 or _la == GrammarParser.T__26:
                    self.state = 327
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 330
                self.match(GrammarParser.T__21)
                self.state = 332
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 331
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 334
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.DuringRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
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

                self.state = 340
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 339
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 342
                self.match(GrammarParser.T__22)
                self.state = 343
                self.chain_id()
                self.state = 344
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

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
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
            self.state = 382
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 38, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.DuringAspectOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 348
                self.match(GrammarParser.T__27)
                self.state = 349
                self.match(GrammarParser.T__24)
                self.state = 350
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 352
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 351
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 354
                self.match(GrammarParser.T__8)
                self.state = 355
                self.operational_statement_set()
                self.state = 356
                self.match(GrammarParser.T__9)
                pass

            elif la_ == 2:
                localctx = GrammarParser.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 358
                self.match(GrammarParser.T__27)
                self.state = 359
                self.match(GrammarParser.T__24)
                self.state = 360
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 361
                self.match(GrammarParser.T__21)
                self.state = 362
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 363
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 3:
                localctx = GrammarParser.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
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
                self.state = 367
                self.match(GrammarParser.T__21)
                self.state = 369
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 368
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 371
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.DuringAspectRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 372
                self.match(GrammarParser.T__27)
                self.state = 373
                self.match(GrammarParser.T__24)
                self.state = 374
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 376
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 375
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 378
                self.match(GrammarParser.T__22)
                self.state = 379
                self.chain_id()
                self.state = 380
                self.match(GrammarParser.T__4)
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

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

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
            self.state = 384
            self.match(GrammarParser.T__28)
            self.state = 385
            localctx.event_name = self.match(GrammarParser.ID)
            self.state = 388
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.T__7:
                self.state = 386
                self.match(GrammarParser.T__7)
                self.state = 387
                localctx.extra_name = self.match(GrammarParser.STRING)

            self.state = 390
            self.match(GrammarParser.T__4)
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
        self.enterRule(localctx, 22, self.RULE_operation_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 392
            self.match(GrammarParser.ID)
            self.state = 393
            self.match(GrammarParser.T__3)
            self.state = 394
            self.num_expression(0)
            self.state = 395
            self.match(GrammarParser.T__4)
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

        def operational_statement_set(self):
            return self.getTypedRuleContext(
                GrammarParser.Operational_statement_setContext, 0
            )

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
        self.enterRule(localctx, 24, self.RULE_operation_block)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 397
            self.match(GrammarParser.T__8)
            self.state = 398
            self.operational_statement_set()
            self.state = 399
            self.match(GrammarParser.T__9)
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

        def cond_expression(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Cond_expressionContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, i)

        def operation_block(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(GrammarParser.Operation_blockContext)
            else:
                return self.getTypedRuleContext(GrammarParser.Operation_blockContext, i)

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
        self.enterRule(localctx, 26, self.RULE_if_statement)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 401
            self.match(GrammarParser.T__14)
            self.state = 402
            self.match(GrammarParser.T__15)
            self.state = 403
            self.cond_expression(0)
            self.state = 404
            self.match(GrammarParser.T__16)
            self.state = 405
            self.operation_block()
            self.state = 415
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 40, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 406
                    self.match(GrammarParser.T__29)
                    self.state = 407
                    self.match(GrammarParser.T__14)
                    self.state = 408
                    self.match(GrammarParser.T__15)
                    self.state = 409
                    self.cond_expression(0)
                    self.state = 410
                    self.match(GrammarParser.T__16)
                    self.state = 411
                    self.operation_block()
                self.state = 417
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 40, self._ctx)

            self.state = 420
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.T__29:
                self.state = 418
                self.match(GrammarParser.T__29)
                self.state = 419
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
        self.enterRule(localctx, 28, self.RULE_operational_statement)
        try:
            self.state = 425
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 422
                self.operation_assignment()
                pass
            elif token in [GrammarParser.T__14]:
                self.enterOuterAlt(localctx, 2)
                self.state = 423
                self.if_statement()
                pass
            elif token in [GrammarParser.T__4]:
                self.enterOuterAlt(localctx, 3)
                self.state = 424
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
        self.enterRule(localctx, 30, self.RULE_operational_statement_set)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 430
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while ((_la - 5) & ~0x3F) == 0 and (
                (1 << (_la - 5))
                & (
                    (1 << (GrammarParser.T__4 - 5))
                    | (1 << (GrammarParser.T__14 - 5))
                    | (1 << (GrammarParser.ID - 5))
                )
            ) != 0:
                self.state = 427
                self.operational_statement()
                self.state = 432
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
        self.enterRule(localctx, 32, self.RULE_state_inner_statement)
        try:
            self.state = 442
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.T__5, GrammarParser.T__6]:
                self.enterOuterAlt(localctx, 1)
                self.state = 433
                self.state_definition()
                pass
            elif token in [GrammarParser.T__10, GrammarParser.ID]:
                self.enterOuterAlt(localctx, 2)
                self.state = 434
                self.transition_definition()
                pass
            elif token in [GrammarParser.T__18]:
                self.enterOuterAlt(localctx, 3)
                self.state = 435
                self.transition_force_definition()
                pass
            elif token in [GrammarParser.T__20]:
                self.enterOuterAlt(localctx, 4)
                self.state = 436
                self.enter_definition()
                pass
            elif token in [GrammarParser.T__24]:
                self.enterOuterAlt(localctx, 5)
                self.state = 437
                self.during_definition()
                pass
            elif token in [GrammarParser.T__23]:
                self.enterOuterAlt(localctx, 6)
                self.state = 438
                self.exit_definition()
                pass
            elif token in [GrammarParser.T__27]:
                self.enterOuterAlt(localctx, 7)
                self.state = 439
                self.during_aspect_definition()
                pass
            elif token in [GrammarParser.T__28]:
                self.enterOuterAlt(localctx, 8)
                self.state = 440
                self.event_definition()
                pass
            elif token in [GrammarParser.T__4]:
                self.enterOuterAlt(localctx, 9)
                self.state = 441
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
        self.enterRule(localctx, 34, self.RULE_operation_program)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 447
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 444
                self.operational_assignment()
                self.state = 449
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 450
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
        self.enterRule(localctx, 36, self.RULE_preamble_program)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 455
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 452
                self.preamble_statement()
                self.state = 457
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 458
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
        self.enterRule(localctx, 38, self.RULE_preamble_statement)
        try:
            self.state = 462
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 47, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 460
                self.initial_assignment()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 461
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
        self.enterRule(localctx, 40, self.RULE_initial_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 464
            self.match(GrammarParser.ID)
            self.state = 465
            self.match(GrammarParser.T__30)
            self.state = 466
            self.init_expression(0)
            self.state = 467
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
        self.enterRule(localctx, 42, self.RULE_constant_definition)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 469
            self.match(GrammarParser.ID)
            self.state = 470
            self.match(GrammarParser.T__3)
            self.state = 471
            self.init_expression(0)
            self.state = 472
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
        self.enterRule(localctx, 44, self.RULE_operational_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 474
            self.match(GrammarParser.ID)
            self.state = 475
            self.match(GrammarParser.T__30)
            self.state = 476
            self.num_expression(0)
            self.state = 477
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
        self.enterRule(localctx, 46, self.RULE_generic_expression)
        try:
            self.state = 481
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 48, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 479
                self.num_expression(0)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 480
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
        _startState = 48
        self.enterRecursionRule(localctx, 48, self.RULE_init_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 497
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.T__31]:
                localctx = GrammarParser.ParenExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 484
                self.match(GrammarParser.T__31)
                self.state = 485
                self.init_expression(0)
                self.state = 486
                self.match(GrammarParser.T__32)
                pass
            elif token in [
                GrammarParser.FLOAT,
                GrammarParser.INT,
                GrammarParser.HEX_INT,
            ]:
                localctx = GrammarParser.LiteralExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 488
                self.num_literal()
                pass
            elif token in [
                GrammarParser.T__54,
                GrammarParser.T__55,
                GrammarParser.T__56,
            ]:
                localctx = GrammarParser.MathConstExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 489
                self.math_const()
                pass
            elif token in [GrammarParser.T__33, GrammarParser.T__34]:
                localctx = GrammarParser.UnaryExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 490
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__33 or _la == GrammarParser.T__34):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 491
                self.init_expression(9)
                pass
            elif token in [GrammarParser.UFUNC_NAME]:
                localctx = GrammarParser.FuncExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 492
                localctx.func_name = self.match(GrammarParser.UFUNC_NAME)
                self.state = 493
                self.match(GrammarParser.T__31)
                self.state = 494
                self.init_expression(0)
                self.state = 495
                self.match(GrammarParser.T__32)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 522
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 51, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 520
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 50, self._ctx)
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
                        self.state = 499
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 500
                        localctx.op = self.match(GrammarParser.T__35)
                        self.state = 501
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
                        self.state = 502
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 503
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la) & ~0x3F) == 0
                            and (
                                (1 << _la)
                                & (
                                    (1 << GrammarParser.T__19)
                                    | (1 << GrammarParser.T__36)
                                    | (1 << GrammarParser.T__37)
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 504
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
                        self.state = 505
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 506
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__33 or _la == GrammarParser.T__34
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 507
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
                        self.state = 508
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 509
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__27 or _la == GrammarParser.T__38
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 510
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
                        self.state = 511
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 512
                        localctx.op = self.match(GrammarParser.T__39)
                        self.state = 513
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
                        self.state = 514
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 515
                        localctx.op = self.match(GrammarParser.T__40)
                        self.state = 516
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
                        self.state = 517
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 518
                        localctx.op = self.match(GrammarParser.T__41)
                        self.state = 519
                        self.init_expression(3)
                        pass

                self.state = 524
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 51, self._ctx)

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
            self.func_name = None  # Token
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
        _startState = 50
        self.enterRecursionRule(localctx, 50, self.RULE_num_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 548
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 52, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 526
                self.match(GrammarParser.T__31)
                self.state = 527
                self.num_expression(0)
                self.state = 528
                self.match(GrammarParser.T__32)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 530
                self.num_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.IdExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 531
                self.match(GrammarParser.ID)
                pass

            elif la_ == 4:
                localctx = GrammarParser.MathConstExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 532
                self.math_const()
                pass

            elif la_ == 5:
                localctx = GrammarParser.UnaryExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 533
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__33 or _la == GrammarParser.T__34):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 534
                self.num_expression(10)
                pass

            elif la_ == 6:
                localctx = GrammarParser.FuncExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 535
                localctx.func_name = self.match(GrammarParser.UFUNC_NAME)
                self.state = 536
                self.match(GrammarParser.T__31)
                self.state = 537
                self.num_expression(0)
                self.state = 538
                self.match(GrammarParser.T__32)
                pass

            elif la_ == 7:
                localctx = GrammarParser.ConditionalCStyleExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 540
                self.match(GrammarParser.T__31)
                self.state = 541
                self.cond_expression(0)
                self.state = 542
                self.match(GrammarParser.T__32)
                self.state = 543
                self.match(GrammarParser.T__42)
                self.state = 544
                self.num_expression(0)
                self.state = 545
                self.match(GrammarParser.T__12)
                self.state = 546
                self.num_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 573
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 54, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 571
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 53, self._ctx)
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
                        self.state = 550
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 9)"
                            )
                        self.state = 551
                        localctx.op = self.match(GrammarParser.T__35)
                        self.state = 552
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
                        self.state = 553
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 554
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la) & ~0x3F) == 0
                            and (
                                (1 << _la)
                                & (
                                    (1 << GrammarParser.T__19)
                                    | (1 << GrammarParser.T__36)
                                    | (1 << GrammarParser.T__37)
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 555
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
                        self.state = 556
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 557
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__33 or _la == GrammarParser.T__34
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 558
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
                        self.state = 559
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 560
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__27 or _la == GrammarParser.T__38
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 561
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
                        self.state = 562
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 563
                        localctx.op = self.match(GrammarParser.T__39)
                        self.state = 564
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
                        self.state = 565
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 566
                        localctx.op = self.match(GrammarParser.T__40)
                        self.state = 567
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
                        self.state = 568
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 569
                        localctx.op = self.match(GrammarParser.T__41)
                        self.state = 570
                        self.num_expression(4)
                        pass

                self.state = 575
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 54, self._ctx)

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
        _startState = 52
        self.enterRecursionRule(localctx, 52, self.RULE_cond_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 600
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 55, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 577
                self.match(GrammarParser.T__31)
                self.state = 578
                self.cond_expression(0)
                self.state = 579
                self.match(GrammarParser.T__32)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 581
                self.bool_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.UnaryExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 582
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__18 or _la == GrammarParser.T__43):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 583
                self.cond_expression(7)
                pass

            elif la_ == 4:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 584
                self.num_expression(0)
                self.state = 585
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (
                    ((_la) & ~0x3F) == 0
                    and (
                        (1 << _la)
                        & (
                            (1 << GrammarParser.T__44)
                            | (1 << GrammarParser.T__45)
                            | (1 << GrammarParser.T__46)
                            | (1 << GrammarParser.T__47)
                        )
                    )
                    != 0
                ):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 586
                self.num_expression(0)
                pass

            elif la_ == 5:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 588
                self.num_expression(0)
                self.state = 589
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__48 or _la == GrammarParser.T__49):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 590
                self.num_expression(0)
                pass

            elif la_ == 6:
                localctx = GrammarParser.ConditionalCStyleCondNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 592
                self.match(GrammarParser.T__31)
                self.state = 593
                self.cond_expression(0)
                self.state = 594
                self.match(GrammarParser.T__32)
                self.state = 595
                self.match(GrammarParser.T__42)
                self.state = 596
                self.cond_expression(0)
                self.state = 597
                self.match(GrammarParser.T__12)
                self.state = 598
                self.cond_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 613
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 57, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 611
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 56, self._ctx)
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
                        self.state = 602
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 603
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__48 or _la == GrammarParser.T__49
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 604
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
                        self.state = 605
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 606
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__50 or _la == GrammarParser.T__51
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 607
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
                        self.state = 608
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 609
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__52 or _la == GrammarParser.T__53
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 610
                        self.cond_expression(3)
                        pass

                self.state = 615
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 57, self._ctx)

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
        self.enterRule(localctx, 54, self.RULE_num_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 616
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
        self.enterRule(localctx, 56, self.RULE_bool_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 618
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
        self.enterRule(localctx, 58, self.RULE_math_const)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 620
            _la = self._input.LA(1)
            if not (
                ((_la) & ~0x3F) == 0
                and (
                    (1 << _la)
                    & (
                        (1 << GrammarParser.T__54)
                        | (1 << GrammarParser.T__55)
                        | (1 << GrammarParser.T__56)
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
        self.enterRule(localctx, 60, self.RULE_chain_id)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 623
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.T__36:
                self.state = 622
                localctx.isabs = self.match(GrammarParser.T__36)

            self.state = 625
            self.match(GrammarParser.ID)
            self.state = 630
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.T__57:
                self.state = 626
                self.match(GrammarParser.T__57)
                self.state = 627
                self.match(GrammarParser.ID)
                self.state = 632
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
        self._predicates[24] = self.init_expression_sempred
        self._predicates[25] = self.num_expression_sempred
        self._predicates[26] = self.cond_expression_sempred
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
