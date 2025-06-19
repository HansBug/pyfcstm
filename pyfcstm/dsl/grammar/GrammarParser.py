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
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3C")
        buf.write("\u01be\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7")
        buf.write("\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r\4\16")
        buf.write("\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23\t\23")
        buf.write("\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30\4\31")
        buf.write("\t\31\4\32\t\32\3\2\3\2\3\2\3\3\7\39\n\3\f\3\16\3<\13")
        buf.write("\3\3\3\3\3\3\3\3\4\3\4\3\4\3\4\3\4\3\4\3\4\3\5\3\5\3\5")
        buf.write("\3\5\3\5\3\5\3\5\7\5O\n\5\f\5\16\5R\13\5\3\5\5\5U\n\5")
        buf.write("\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6c")
        buf.write("\n\6\3\6\3\6\3\6\3\6\7\6i\n\6\f\6\16\6l\13\6\3\6\5\6o")
        buf.write("\n\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3")
        buf.write("\6\3\6\5\6\177\n\6\3\6\3\6\3\6\3\6\7\6\u0085\n\6\f\6\16")
        buf.write("\6\u0088\13\6\3\6\5\6\u008b\n\6\3\6\3\6\3\6\3\6\3\6\3")
        buf.write("\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u009b\n\6\3\6\3")
        buf.write("\6\3\6\3\6\7\6\u00a1\n\6\f\6\16\6\u00a4\13\6\3\6\5\6\u00a7")
        buf.write("\n\6\5\6\u00a9\n\6\3\7\3\7\3\7\7\7\u00ae\n\7\f\7\16\7")
        buf.write("\u00b1\13\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\5\7\u00bb")
        buf.write("\n\7\3\7\5\7\u00be\n\7\3\b\3\b\3\b\7\b\u00c3\n\b\f\b\16")
        buf.write("\b\u00c6\13\b\3\b\3\b\3\b\3\b\3\b\3\b\3\b\3\b\5\b\u00d0")
        buf.write("\n\b\3\b\5\b\u00d3\n\b\3\t\3\t\5\t\u00d7\n\t\3\t\3\t\7")
        buf.write("\t\u00db\n\t\f\t\16\t\u00de\13\t\3\t\3\t\3\t\5\t\u00e3")
        buf.write("\n\t\3\t\3\t\3\t\3\t\3\t\5\t\u00ea\n\t\3\t\3\t\5\t\u00ee")
        buf.write("\n\t\3\t\5\t\u00f1\n\t\3\n\3\n\3\n\3\n\3\n\3\13\3\13\5")
        buf.write("\13\u00fa\n\13\3\f\3\f\3\f\3\f\3\f\3\f\5\f\u0102\n\f\3")
        buf.write("\r\7\r\u0105\n\r\f\r\16\r\u0108\13\r\3\r\3\r\3\16\7\16")
        buf.write("\u010d\n\16\f\16\16\16\u0110\13\16\3\16\3\16\3\17\3\17")
        buf.write("\5\17\u0116\n\17\3\20\3\20\3\20\3\20\3\20\3\21\3\21\3")
        buf.write("\21\3\21\3\21\3\22\3\22\3\22\3\22\3\22\3\23\3\23\5\23")
        buf.write("\u0129\n\23\3\24\3\24\3\24\3\24\3\24\3\24\3\24\3\24\3")
        buf.write("\24\3\24\3\24\3\24\3\24\3\24\5\24\u0139\n\24\3\24\3\24")
        buf.write("\3\24\3\24\3\24\3\24\3\24\3\24\3\24\3\24\3\24\3\24\3\24")
        buf.write("\3\24\3\24\3\24\3\24\3\24\3\24\3\24\3\24\7\24\u0150\n")
        buf.write("\24\f\24\16\24\u0153\13\24\3\25\3\25\3\25\3\25\3\25\3")
        buf.write("\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25")
        buf.write("\3\25\3\25\3\25\3\25\3\25\3\25\3\25\5\25\u016c\n\25\3")
        buf.write("\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25")
        buf.write("\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\7\25")
        buf.write("\u0183\n\25\f\25\16\25\u0186\13\25\3\26\3\26\3\26\3\26")
        buf.write("\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26")
        buf.write("\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\5\26\u01a0")
        buf.write("\n\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\7\26")
        buf.write("\u01ab\n\26\f\26\16\26\u01ae\13\26\3\27\3\27\3\30\3\30")
        buf.write("\3\31\3\31\3\32\3\32\3\32\7\32\u01b9\n\32\f\32\16\32\u01bc")
        buf.write("\13\32\3\32\2\5&(*\33\2\4\6\b\n\f\16\20\22\24\26\30\32")
        buf.write('\34\36 "$&(*,.\60\62\2\20\3\2\4\5\3\2\r\16\3\2\27\30')
        buf.write('\3\2\34\35\3\2\37!\3\2"#\3\2()\3\2*-\3\2./\3\2\60\61')
        buf.write("\3\2\62\63\3\28:\3\2;<\3\2\64\66\2\u01f1\2\64\3\2\2\2")
        buf.write("\4:\3\2\2\2\6@\3\2\2\2\bT\3\2\2\2\n\u00a8\3\2\2\2\f\u00bd")
        buf.write("\3\2\2\2\16\u00d2\3\2\2\2\20\u00f0\3\2\2\2\22\u00f2\3")
        buf.write("\2\2\2\24\u00f9\3\2\2\2\26\u0101\3\2\2\2\30\u0106\3\2")
        buf.write("\2\2\32\u010e\3\2\2\2\34\u0115\3\2\2\2\36\u0117\3\2\2")
        buf.write('\2 \u011c\3\2\2\2"\u0121\3\2\2\2$\u0128\3\2\2\2&\u0138')
        buf.write("\3\2\2\2(\u016b\3\2\2\2*\u019f\3\2\2\2,\u01af\3\2\2\2")
        buf.write(".\u01b1\3\2\2\2\60\u01b3\3\2\2\2\62\u01b5\3\2\2\2\64\65")
        buf.write("\5*\26\2\65\66\7\2\2\3\66\3\3\2\2\2\679\5\6\4\28\67\3")
        buf.write("\2\2\29<\3\2\2\2:8\3\2\2\2:;\3\2\2\2;=\3\2\2\2<:\3\2\2")
        buf.write("\2=>\5\b\5\2>?\7\2\2\3?\5\3\2\2\2@A\7\3\2\2AB\t\2\2\2")
        buf.write("BC\7>\2\2CD\7\6\2\2DE\5&\24\2EF\7\7\2\2F\7\3\2\2\2GH\7")
        buf.write("\b\2\2HI\7>\2\2IU\7\7\2\2JK\7\b\2\2KL\7>\2\2LP\7\t\2\2")
        buf.write("MO\5\26\f\2NM\3\2\2\2OR\3\2\2\2PN\3\2\2\2PQ\3\2\2\2QS")
        buf.write("\3\2\2\2RP\3\2\2\2SU\7\n\2\2TG\3\2\2\2TJ\3\2\2\2U\t\3")
        buf.write("\2\2\2VW\7\13\2\2WX\7\f\2\2Xb\7>\2\2Yc\3\2\2\2Z[\t\3\2")
        buf.write("\2[c\5\62\32\2\\]\7\r\2\2]^\7\17\2\2^_\7\20\2\2_`\5*\26")
        buf.write("\2`a\7\21\2\2ac\3\2\2\2bY\3\2\2\2bZ\3\2\2\2b\\\3\2\2\2")
        buf.write("cn\3\2\2\2do\7\7\2\2ef\7\22\2\2fj\7\t\2\2gi\5\24\13\2")
        buf.write("hg\3\2\2\2il\3\2\2\2jh\3\2\2\2jk\3\2\2\2km\3\2\2\2lj\3")
        buf.write("\2\2\2mo\7\n\2\2nd\3\2\2\2ne\3\2\2\2o\u00a9\3\2\2\2pq")
        buf.write("\7>\2\2qr\7\f\2\2r~\7>\2\2s\177\3\2\2\2tu\7\16\2\2u\177")
        buf.write("\7>\2\2vw\7\r\2\2w\177\5\62\32\2xy\7\r\2\2yz\7\17\2\2")
        buf.write("z{\7\20\2\2{|\5*\26\2|}\7\21\2\2}\177\3\2\2\2~s\3\2\2")
        buf.write("\2~t\3\2\2\2~v\3\2\2\2~x\3\2\2\2\177\u008a\3\2\2\2\u0080")
        buf.write("\u008b\7\7\2\2\u0081\u0082\7\22\2\2\u0082\u0086\7\t\2")
        buf.write("\2\u0083\u0085\5\24\13\2\u0084\u0083\3\2\2\2\u0085\u0088")
        buf.write("\3\2\2\2\u0086\u0084\3\2\2\2\u0086\u0087\3\2\2\2\u0087")
        buf.write("\u0089\3\2\2\2\u0088\u0086\3\2\2\2\u0089\u008b\7\n\2\2")
        buf.write("\u008a\u0080\3\2\2\2\u008a\u0081\3\2\2\2\u008b\u00a9\3")
        buf.write("\2\2\2\u008c\u008d\7>\2\2\u008d\u008e\7\f\2\2\u008e\u009a")
        buf.write("\7\13\2\2\u008f\u009b\3\2\2\2\u0090\u0091\7\16\2\2\u0091")
        buf.write("\u009b\7>\2\2\u0092\u0093\7\r\2\2\u0093\u009b\5\62\32")
        buf.write("\2\u0094\u0095\7\r\2\2\u0095\u0096\7\17\2\2\u0096\u0097")
        buf.write("\7\20\2\2\u0097\u0098\5*\26\2\u0098\u0099\7\21\2\2\u0099")
        buf.write("\u009b\3\2\2\2\u009a\u008f\3\2\2\2\u009a\u0090\3\2\2\2")
        buf.write("\u009a\u0092\3\2\2\2\u009a\u0094\3\2\2\2\u009b\u00a6\3")
        buf.write("\2\2\2\u009c\u00a7\7\7\2\2\u009d\u009e\7\22\2\2\u009e")
        buf.write("\u00a2\7\t\2\2\u009f\u00a1\5\24\13\2\u00a0\u009f\3\2\2")
        buf.write("\2\u00a1\u00a4\3\2\2\2\u00a2\u00a0\3\2\2\2\u00a2\u00a3")
        buf.write("\3\2\2\2\u00a3\u00a5\3\2\2\2\u00a4\u00a2\3\2\2\2\u00a5")
        buf.write("\u00a7\7\n\2\2\u00a6\u009c\3\2\2\2\u00a6\u009d\3\2\2\2")
        buf.write("\u00a7\u00a9\3\2\2\2\u00a8V\3\2\2\2\u00a8p\3\2\2\2\u00a8")
        buf.write("\u008c\3\2\2\2\u00a9\13\3\2\2\2\u00aa\u00ab\7\23\2\2\u00ab")
        buf.write("\u00af\7\t\2\2\u00ac\u00ae\5\24\13\2\u00ad\u00ac\3\2\2")
        buf.write("\2\u00ae\u00b1\3\2\2\2\u00af\u00ad\3\2\2\2\u00af\u00b0")
        buf.write("\3\2\2\2\u00b0\u00b2\3\2\2\2\u00b1\u00af\3\2\2\2\u00b2")
        buf.write("\u00be\7\n\2\2\u00b3\u00b4\7\23\2\2\u00b4\u00b5\7\24\2")
        buf.write("\2\u00b5\u00b6\7>\2\2\u00b6\u00be\7\7\2\2\u00b7\u00b8")
        buf.write("\7\23\2\2\u00b8\u00ba\7\24\2\2\u00b9\u00bb\7>\2\2\u00ba")
        buf.write("\u00b9\3\2\2\2\u00ba\u00bb\3\2\2\2\u00bb\u00bc\3\2\2\2")
        buf.write("\u00bc\u00be\7A\2\2\u00bd\u00aa\3\2\2\2\u00bd\u00b3\3")
        buf.write("\2\2\2\u00bd\u00b7\3\2\2\2\u00be\r\3\2\2\2\u00bf\u00c0")
        buf.write("\7\25\2\2\u00c0\u00c4\7\t\2\2\u00c1\u00c3\5\24\13\2\u00c2")
        buf.write("\u00c1\3\2\2\2\u00c3\u00c6\3\2\2\2\u00c4\u00c2\3\2\2\2")
        buf.write("\u00c4\u00c5\3\2\2\2\u00c5\u00c7\3\2\2\2\u00c6\u00c4\3")
        buf.write("\2\2\2\u00c7\u00d3\7\n\2\2\u00c8\u00c9\7\25\2\2\u00c9")
        buf.write("\u00ca\7\24\2\2\u00ca\u00cb\7>\2\2\u00cb\u00d3\7\7\2\2")
        buf.write("\u00cc\u00cd\7\25\2\2\u00cd\u00cf\7\24\2\2\u00ce\u00d0")
        buf.write("\7>\2\2\u00cf\u00ce\3\2\2\2\u00cf\u00d0\3\2\2\2\u00d0")
        buf.write("\u00d1\3\2\2\2\u00d1\u00d3\7A\2\2\u00d2\u00bf\3\2\2\2")
        buf.write("\u00d2\u00c8\3\2\2\2\u00d2\u00cc\3\2\2\2\u00d3\17\3\2")
        buf.write("\2\2\u00d4\u00d6\7\26\2\2\u00d5\u00d7\t\4\2\2\u00d6\u00d5")
        buf.write("\3\2\2\2\u00d6\u00d7\3\2\2\2\u00d7\u00d8\3\2\2\2\u00d8")
        buf.write("\u00dc\7\t\2\2\u00d9\u00db\5\24\13\2\u00da\u00d9\3\2\2")
        buf.write("\2\u00db\u00de\3\2\2\2\u00dc\u00da\3\2\2\2\u00dc\u00dd")
        buf.write("\3\2\2\2\u00dd\u00df\3\2\2\2\u00de\u00dc\3\2\2\2\u00df")
        buf.write("\u00f1\7\n\2\2\u00e0\u00e2\7\26\2\2\u00e1\u00e3\t\4\2")
        buf.write("\2\u00e2\u00e1\3\2\2\2\u00e2\u00e3\3\2\2\2\u00e3\u00e4")
        buf.write("\3\2\2\2\u00e4\u00e5\7\24\2\2\u00e5\u00e6\7>\2\2\u00e6")
        buf.write("\u00f1\7\7\2\2\u00e7\u00e9\7\26\2\2\u00e8\u00ea\t\4\2")
        buf.write("\2\u00e9\u00e8\3\2\2\2\u00e9\u00ea\3\2\2\2\u00ea\u00eb")
        buf.write("\3\2\2\2\u00eb\u00ed\7\24\2\2\u00ec\u00ee\7>\2\2\u00ed")
        buf.write("\u00ec\3\2\2\2\u00ed\u00ee\3\2\2\2\u00ee\u00ef\3\2\2\2")
        buf.write("\u00ef\u00f1\7A\2\2\u00f0\u00d4\3\2\2\2\u00f0\u00e0\3")
        buf.write("\2\2\2\u00f0\u00e7\3\2\2\2\u00f1\21\3\2\2\2\u00f2\u00f3")
        buf.write("\7>\2\2\u00f3\u00f4\7\6\2\2\u00f4\u00f5\5(\25\2\u00f5")
        buf.write("\u00f6\7\7\2\2\u00f6\23\3\2\2\2\u00f7\u00fa\5\22\n\2\u00f8")
        buf.write("\u00fa\7\7\2\2\u00f9\u00f7\3\2\2\2\u00f9\u00f8\3\2\2\2")
        buf.write("\u00fa\25\3\2\2\2\u00fb\u0102\5\b\5\2\u00fc\u0102\5\n")
        buf.write("\6\2\u00fd\u0102\5\f\7\2\u00fe\u0102\5\20\t\2\u00ff\u0102")
        buf.write("\5\16\b\2\u0100\u0102\7\7\2\2\u0101\u00fb\3\2\2\2\u0101")
        buf.write("\u00fc\3\2\2\2\u0101\u00fd\3\2\2\2\u0101\u00fe\3\2\2\2")
        buf.write("\u0101\u00ff\3\2\2\2\u0101\u0100\3\2\2\2\u0102\27\3\2")
        buf.write('\2\2\u0103\u0105\5"\22\2\u0104\u0103\3\2\2\2\u0105\u0108')
        buf.write("\3\2\2\2\u0106\u0104\3\2\2\2\u0106\u0107\3\2\2\2\u0107")
        buf.write("\u0109\3\2\2\2\u0108\u0106\3\2\2\2\u0109\u010a\7\2\2\3")
        buf.write("\u010a\31\3\2\2\2\u010b\u010d\5\34\17\2\u010c\u010b\3")
        buf.write("\2\2\2\u010d\u0110\3\2\2\2\u010e\u010c\3\2\2\2\u010e\u010f")
        buf.write("\3\2\2\2\u010f\u0111\3\2\2\2\u0110\u010e\3\2\2\2\u0111")
        buf.write("\u0112\7\2\2\3\u0112\33\3\2\2\2\u0113\u0116\5\36\20\2")
        buf.write("\u0114\u0116\5 \21\2\u0115\u0113\3\2\2\2\u0115\u0114\3")
        buf.write("\2\2\2\u0116\35\3\2\2\2\u0117\u0118\7>\2\2\u0118\u0119")
        buf.write("\7\31\2\2\u0119\u011a\5&\24\2\u011a\u011b\7\7\2\2\u011b")
        buf.write("\37\3\2\2\2\u011c\u011d\7>\2\2\u011d\u011e\7\6\2\2\u011e")
        buf.write("\u011f\5&\24\2\u011f\u0120\7\7\2\2\u0120!\3\2\2\2\u0121")
        buf.write("\u0122\7>\2\2\u0122\u0123\7\31\2\2\u0123\u0124\5(\25\2")
        buf.write("\u0124\u0125\7\7\2\2\u0125#\3\2\2\2\u0126\u0129\5(\25")
        buf.write("\2\u0127\u0129\5*\26\2\u0128\u0126\3\2\2\2\u0128\u0127")
        buf.write("\3\2\2\2\u0129%\3\2\2\2\u012a\u012b\b\24\1\2\u012b\u012c")
        buf.write("\7\32\2\2\u012c\u012d\5&\24\2\u012d\u012e\7\33\2\2\u012e")
        buf.write("\u0139\3\2\2\2\u012f\u0139\5,\27\2\u0130\u0139\5\60\31")
        buf.write("\2\u0131\u0132\t\5\2\2\u0132\u0139\5&\24\13\u0133\u0134")
        buf.write("\7=\2\2\u0134\u0135\7\32\2\2\u0135\u0136\5&\24\2\u0136")
        buf.write("\u0137\7\33\2\2\u0137\u0139\3\2\2\2\u0138\u012a\3\2\2")
        buf.write("\2\u0138\u012f\3\2\2\2\u0138\u0130\3\2\2\2\u0138\u0131")
        buf.write("\3\2\2\2\u0138\u0133\3\2\2\2\u0139\u0151\3\2\2\2\u013a")
        buf.write("\u013b\f\n\2\2\u013b\u013c\7\36\2\2\u013c\u0150\5&\24")
        buf.write("\n\u013d\u013e\f\t\2\2\u013e\u013f\t\6\2\2\u013f\u0150")
        buf.write("\5&\24\n\u0140\u0141\f\b\2\2\u0141\u0142\t\5\2\2\u0142")
        buf.write("\u0150\5&\24\t\u0143\u0144\f\7\2\2\u0144\u0145\t\7\2\2")
        buf.write("\u0145\u0150\5&\24\b\u0146\u0147\f\6\2\2\u0147\u0148\7")
        buf.write("$\2\2\u0148\u0150\5&\24\7\u0149\u014a\f\5\2\2\u014a\u014b")
        buf.write("\7%\2\2\u014b\u0150\5&\24\6\u014c\u014d\f\4\2\2\u014d")
        buf.write("\u014e\7&\2\2\u014e\u0150\5&\24\5\u014f\u013a\3\2\2\2")
        buf.write("\u014f\u013d\3\2\2\2\u014f\u0140\3\2\2\2\u014f\u0143\3")
        buf.write("\2\2\2\u014f\u0146\3\2\2\2\u014f\u0149\3\2\2\2\u014f\u014c")
        buf.write("\3\2\2\2\u0150\u0153\3\2\2\2\u0151\u014f\3\2\2\2\u0151")
        buf.write("\u0152\3\2\2\2\u0152'\3\2\2\2\u0153\u0151\3\2\2\2\u0154")
        buf.write("\u0155\b\25\1\2\u0155\u0156\7\32\2\2\u0156\u0157\5(\25")
        buf.write("\2\u0157\u0158\7\33\2\2\u0158\u016c\3\2\2\2\u0159\u016c")
        buf.write("\5,\27\2\u015a\u016c\7>\2\2\u015b\u016c\5\60\31\2\u015c")
        buf.write("\u015d\t\5\2\2\u015d\u016c\5(\25\f\u015e\u015f\7=\2\2")
        buf.write("\u015f\u0160\7\32\2\2\u0160\u0161\5(\25\2\u0161\u0162")
        buf.write("\7\33\2\2\u0162\u016c\3\2\2\2\u0163\u0164\7\32\2\2\u0164")
        buf.write("\u0165\5*\26\2\u0165\u0166\7\33\2\2\u0166\u0167\7'\2")
        buf.write("\2\u0167\u0168\5(\25\2\u0168\u0169\7\r\2\2\u0169\u016a")
        buf.write("\5(\25\3\u016a\u016c\3\2\2\2\u016b\u0154\3\2\2\2\u016b")
        buf.write("\u0159\3\2\2\2\u016b\u015a\3\2\2\2\u016b\u015b\3\2\2\2")
        buf.write("\u016b\u015c\3\2\2\2\u016b\u015e\3\2\2\2\u016b\u0163\3")
        buf.write("\2\2\2\u016c\u0184\3\2\2\2\u016d\u016e\f\13\2\2\u016e")
        buf.write("\u016f\7\36\2\2\u016f\u0183\5(\25\13\u0170\u0171\f\n\2")
        buf.write("\2\u0171\u0172\t\6\2\2\u0172\u0183\5(\25\13\u0173\u0174")
        buf.write("\f\t\2\2\u0174\u0175\t\5\2\2\u0175\u0183\5(\25\n\u0176")
        buf.write("\u0177\f\b\2\2\u0177\u0178\t\7\2\2\u0178\u0183\5(\25\t")
        buf.write("\u0179\u017a\f\7\2\2\u017a\u017b\7$\2\2\u017b\u0183\5")
        buf.write("(\25\b\u017c\u017d\f\6\2\2\u017d\u017e\7%\2\2\u017e\u0183")
        buf.write("\5(\25\7\u017f\u0180\f\5\2\2\u0180\u0181\7&\2\2\u0181")
        buf.write("\u0183\5(\25\6\u0182\u016d\3\2\2\2\u0182\u0170\3\2\2\2")
        buf.write("\u0182\u0173\3\2\2\2\u0182\u0176\3\2\2\2\u0182\u0179\3")
        buf.write("\2\2\2\u0182\u017c\3\2\2\2\u0182\u017f\3\2\2\2\u0183\u0186")
        buf.write("\3\2\2\2\u0184\u0182\3\2\2\2\u0184\u0185\3\2\2\2\u0185")
        buf.write(")\3\2\2\2\u0186\u0184\3\2\2\2\u0187\u0188\b\26\1\2\u0188")
        buf.write("\u0189\7\32\2\2\u0189\u018a\5*\26\2\u018a\u018b\7\33\2")
        buf.write("\2\u018b\u01a0\3\2\2\2\u018c\u01a0\5.\30\2\u018d\u018e")
        buf.write("\t\b\2\2\u018e\u01a0\5*\26\t\u018f\u0190\5(\25\2\u0190")
        buf.write("\u0191\t\t\2\2\u0191\u0192\5(\25\2\u0192\u01a0\3\2\2\2")
        buf.write("\u0193\u0194\5(\25\2\u0194\u0195\t\n\2\2\u0195\u0196\5")
        buf.write("(\25\2\u0196\u01a0\3\2\2\2\u0197\u0198\7\32\2\2\u0198")
        buf.write("\u0199\5*\26\2\u0199\u019a\7\33\2\2\u019a\u019b\7'\2")
        buf.write("\2\u019b\u019c\5*\26\2\u019c\u019d\7\r\2\2\u019d\u019e")
        buf.write("\5*\26\3\u019e\u01a0\3\2\2\2\u019f\u0187\3\2\2\2\u019f")
        buf.write("\u018c\3\2\2\2\u019f\u018d\3\2\2\2\u019f\u018f\3\2\2\2")
        buf.write("\u019f\u0193\3\2\2\2\u019f\u0197\3\2\2\2\u01a0\u01ac\3")
        buf.write("\2\2\2\u01a1\u01a2\f\6\2\2\u01a2\u01a3\t\n\2\2\u01a3\u01ab")
        buf.write("\5*\26\7\u01a4\u01a5\f\5\2\2\u01a5\u01a6\t\13\2\2\u01a6")
        buf.write("\u01ab\5*\26\6\u01a7\u01a8\f\4\2\2\u01a8\u01a9\t\f\2\2")
        buf.write("\u01a9\u01ab\5*\26\5\u01aa\u01a1\3\2\2\2\u01aa\u01a4\3")
        buf.write("\2\2\2\u01aa\u01a7\3\2\2\2\u01ab\u01ae\3\2\2\2\u01ac\u01aa")
        buf.write("\3\2\2\2\u01ac\u01ad\3\2\2\2\u01ad+\3\2\2\2\u01ae\u01ac")
        buf.write("\3\2\2\2\u01af\u01b0\t\r\2\2\u01b0-\3\2\2\2\u01b1\u01b2")
        buf.write("\t\16\2\2\u01b2/\3\2\2\2\u01b3\u01b4\t\17\2\2\u01b4\61")
        buf.write("\3\2\2\2\u01b5\u01ba\7>\2\2\u01b6\u01b7\7\67\2\2\u01b7")
        buf.write("\u01b9\7>\2\2\u01b8\u01b6\3\2\2\2\u01b9\u01bc\3\2\2\2")
        buf.write("\u01ba\u01b8\3\2\2\2\u01ba\u01bb\3\2\2\2\u01bb\63\3\2")
        buf.write("\2\2\u01bc\u01ba\3\2\2\2+:PTbjn~\u0086\u008a\u009a\u00a2")
        buf.write("\u00a6\u00a8\u00af\u00ba\u00bd\u00c4\u00cf\u00d2\u00d6")
        buf.write("\u00dc\u00e2\u00e9\u00ed\u00f0\u00f9\u0101\u0106\u010e")
        buf.write("\u0115\u0128\u0138\u014f\u0151\u016b\u0182\u0184\u019f")
        buf.write("\u01aa\u01ac\u01ba")
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
        "'state'",
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
        "'enter'",
        "'abstract'",
        "'exit'",
        "'during'",
        "'before'",
        "'after'",
        "':='",
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
        "'^'",
        "'|'",
        "'?'",
        "'!'",
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
    RULE_enter_definition = 5
    RULE_exit_definition = 6
    RULE_during_definition = 7
    RULE_operation_assignment = 8
    RULE_operational_statement = 9
    RULE_state_inner_statement = 10
    RULE_operation_program = 11
    RULE_preamble_program = 12
    RULE_preamble_statement = 13
    RULE_initial_assignment = 14
    RULE_constant_definition = 15
    RULE_operational_assignment = 16
    RULE_generic_expression = 17
    RULE_init_expression = 18
    RULE_num_expression = 19
    RULE_cond_expression = 20
    RULE_num_literal = 21
    RULE_bool_literal = 22
    RULE_math_const = 23
    RULE_chain_id = 24

    ruleNames = [
        "condition",
        "state_machine_dsl",
        "def_assignment",
        "state_definition",
        "transition_definition",
        "enter_definition",
        "exit_definition",
        "during_definition",
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
    FLOAT = 54
    INT = 55
    HEX_INT = 56
    TRUE = 57
    FALSE = 58
    UFUNC_NAME = 59
    ID = 60
    STRING = 61
    WS = 62
    MULTILINE_COMMENT = 63
    LINE_COMMENT = 64
    PYTHON_COMMENT = 65

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
            self.state = 50
            self.cond_expression(0)
            self.state = 51
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
            self.state = 56
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.T__0:
                self.state = 53
                self.def_assignment()
                self.state = 58
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 59
            self.state_definition()
            self.state = 60
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
            self.state = 62
            self.match(GrammarParser.T__0)
            self.state = 63
            localctx.deftype = self._input.LT(1)
            _la = self._input.LA(1)
            if not (_la == GrammarParser.T__1 or _la == GrammarParser.T__2):
                localctx.deftype = self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 64
            self.match(GrammarParser.ID)
            self.state = 65
            self.match(GrammarParser.T__3)
            self.state = 66
            self.init_expression(0)
            self.state = 67
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
            self.state_id = None  # Token
            self.copyFrom(ctx)

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

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
            self.state_id = None  # Token
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
            self.state = 82
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 2, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.LeafStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 69
                self.match(GrammarParser.T__5)
                self.state = 70
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 71
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 2:
                localctx = GrammarParser.CompositeStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 72
                self.match(GrammarParser.T__5)
                self.state = 73
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 74
                self.match(GrammarParser.T__6)
                self.state = 78
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while ((_la) & ~0x3F) == 0 and (
                    (1 << _la)
                    & (
                        (1 << GrammarParser.T__4)
                        | (1 << GrammarParser.T__5)
                        | (1 << GrammarParser.T__8)
                        | (1 << GrammarParser.T__16)
                        | (1 << GrammarParser.T__18)
                        | (1 << GrammarParser.T__19)
                        | (1 << GrammarParser.ID)
                    )
                ) != 0:
                    self.state = 75
                    self.state_inner_statement()
                    self.state = 80
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 81
                self.match(GrammarParser.T__7)
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
            self.state = 166
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 12, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EntryTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 84
                self.match(GrammarParser.T__8)
                self.state = 85
                self.match(GrammarParser.T__9)
                self.state = 86
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 96
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 3, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 88
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__10 or _la == GrammarParser.T__11):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 89
                    self.chain_id()
                    pass

                elif la_ == 3:
                    self.state = 90
                    self.match(GrammarParser.T__10)
                    self.state = 91
                    self.match(GrammarParser.T__12)
                    self.state = 92
                    self.match(GrammarParser.T__13)
                    self.state = 93
                    self.cond_expression(0)
                    self.state = 94
                    self.match(GrammarParser.T__14)
                    pass

                self.state = 108
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.T__4]:
                    self.state = 98
                    self.match(GrammarParser.T__4)
                    pass
                elif token in [GrammarParser.T__15]:
                    self.state = 99
                    self.match(GrammarParser.T__15)
                    self.state = 100
                    self.match(GrammarParser.T__6)
                    self.state = 104
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la == GrammarParser.T__4 or _la == GrammarParser.ID:
                        self.state = 101
                        self.operational_statement()
                        self.state = 106
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)

                    self.state = 107
                    self.match(GrammarParser.T__7)
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 2:
                localctx = GrammarParser.NormalTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 2)
                self.state = 110
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 111
                self.match(GrammarParser.T__9)
                self.state = 112
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 124
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 6, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 114
                    self.match(GrammarParser.T__11)
                    self.state = 115
                    localctx.from_id = self.match(GrammarParser.ID)
                    pass

                elif la_ == 3:
                    self.state = 116
                    self.match(GrammarParser.T__10)
                    self.state = 117
                    self.chain_id()
                    pass

                elif la_ == 4:
                    self.state = 118
                    self.match(GrammarParser.T__10)
                    self.state = 119
                    self.match(GrammarParser.T__12)
                    self.state = 120
                    self.match(GrammarParser.T__13)
                    self.state = 121
                    self.cond_expression(0)
                    self.state = 122
                    self.match(GrammarParser.T__14)
                    pass

                self.state = 136
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.T__4]:
                    self.state = 126
                    self.match(GrammarParser.T__4)
                    pass
                elif token in [GrammarParser.T__15]:
                    self.state = 127
                    self.match(GrammarParser.T__15)
                    self.state = 128
                    self.match(GrammarParser.T__6)
                    self.state = 132
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la == GrammarParser.T__4 or _la == GrammarParser.ID:
                        self.state = 129
                        self.operational_statement()
                        self.state = 134
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)

                    self.state = 135
                    self.match(GrammarParser.T__7)
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 3:
                localctx = GrammarParser.ExitTransitionDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 138
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 139
                self.match(GrammarParser.T__9)
                self.state = 140
                self.match(GrammarParser.T__8)
                self.state = 152
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 9, self._ctx)
                if la_ == 1:
                    pass

                elif la_ == 2:
                    self.state = 142
                    self.match(GrammarParser.T__11)
                    self.state = 143
                    localctx.from_id = self.match(GrammarParser.ID)
                    pass

                elif la_ == 3:
                    self.state = 144
                    self.match(GrammarParser.T__10)
                    self.state = 145
                    self.chain_id()
                    pass

                elif la_ == 4:
                    self.state = 146
                    self.match(GrammarParser.T__10)
                    self.state = 147
                    self.match(GrammarParser.T__12)
                    self.state = 148
                    self.match(GrammarParser.T__13)
                    self.state = 149
                    self.cond_expression(0)
                    self.state = 150
                    self.match(GrammarParser.T__14)
                    pass

                self.state = 164
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.T__4]:
                    self.state = 154
                    self.match(GrammarParser.T__4)
                    pass
                elif token in [GrammarParser.T__15]:
                    self.state = 155
                    self.match(GrammarParser.T__15)
                    self.state = 156
                    self.match(GrammarParser.T__6)
                    self.state = 160
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    while _la == GrammarParser.T__4 or _la == GrammarParser.ID:
                        self.state = 157
                        self.operational_statement()
                        self.state = 162
                        self._errHandler.sync(self)
                        _la = self._input.LA(1)

                    self.state = 163
                    self.match(GrammarParser.T__7)
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

    class EnterOperationsContext(Enter_definitionContext):
        def __init__(
            self, parser, ctx: ParserRuleContext
        ):  # actually a GrammarParser.Enter_definitionContext
            super().__init__(parser)
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
        self.enterRule(localctx, 10, self.RULE_enter_definition)
        self._la = 0  # Token type
        try:
            self.state = 187
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 15, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EnterOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 168
                self.match(GrammarParser.T__16)
                self.state = 169
                self.match(GrammarParser.T__6)
                self.state = 173
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == GrammarParser.T__4 or _la == GrammarParser.ID:
                    self.state = 170
                    self.operational_statement()
                    self.state = 175
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 176
                self.match(GrammarParser.T__7)
                pass

            elif la_ == 2:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 177
                self.match(GrammarParser.T__16)
                self.state = 178
                self.match(GrammarParser.T__17)
                self.state = 179
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 180
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 3:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 181
                self.match(GrammarParser.T__16)
                self.state = 182
                self.match(GrammarParser.T__17)
                self.state = 184
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 183
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 186
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
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

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterExitOperations"):
                listener.enterExitOperations(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitExitOperations"):
                listener.exitExitOperations(self)

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
        self.enterRule(localctx, 12, self.RULE_exit_definition)
        self._la = 0  # Token type
        try:
            self.state = 208
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 18, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ExitOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 189
                self.match(GrammarParser.T__18)
                self.state = 190
                self.match(GrammarParser.T__6)
                self.state = 194
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == GrammarParser.T__4 or _la == GrammarParser.ID:
                    self.state = 191
                    self.operational_statement()
                    self.state = 196
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 197
                self.match(GrammarParser.T__7)
                pass

            elif la_ == 2:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 198
                self.match(GrammarParser.T__18)
                self.state = 199
                self.match(GrammarParser.T__17)
                self.state = 200
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 201
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 3:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 202
                self.match(GrammarParser.T__18)
                self.state = 203
                self.match(GrammarParser.T__17)
                self.state = 205
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 204
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 207
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
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

    def during_definition(self):
        localctx = GrammarParser.During_definitionContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_during_definition)
        self._la = 0  # Token type
        try:
            self.state = 238
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 24, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.DuringOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 210
                self.match(GrammarParser.T__19)
                self.state = 212
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__20 or _la == GrammarParser.T__21:
                    self.state = 211
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__20 or _la == GrammarParser.T__21):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 214
                self.match(GrammarParser.T__6)
                self.state = 218
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == GrammarParser.T__4 or _la == GrammarParser.ID:
                    self.state = 215
                    self.operational_statement()
                    self.state = 220
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 221
                self.match(GrammarParser.T__7)
                pass

            elif la_ == 2:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 222
                self.match(GrammarParser.T__19)
                self.state = 224
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__20 or _la == GrammarParser.T__21:
                    self.state = 223
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__20 or _la == GrammarParser.T__21):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 226
                self.match(GrammarParser.T__17)
                self.state = 227
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 228
                self.match(GrammarParser.T__4)
                pass

            elif la_ == 3:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 229
                self.match(GrammarParser.T__19)
                self.state = 231
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.T__20 or _la == GrammarParser.T__21:
                    self.state = 230
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.T__20 or _la == GrammarParser.T__21):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 233
                self.match(GrammarParser.T__17)
                self.state = 235
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 234
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 237
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
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
        self.enterRule(localctx, 16, self.RULE_operation_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 240
            self.match(GrammarParser.ID)
            self.state = 241
            self.match(GrammarParser.T__3)
            self.state = 242
            self.num_expression(0)
            self.state = 243
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
        self.enterRule(localctx, 18, self.RULE_operational_statement)
        try:
            self.state = 247
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 245
                self.operation_assignment()
                pass
            elif token in [GrammarParser.T__4]:
                self.enterOuterAlt(localctx, 2)
                self.state = 246
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

        def enter_definition(self):
            return self.getTypedRuleContext(GrammarParser.Enter_definitionContext, 0)

        def during_definition(self):
            return self.getTypedRuleContext(GrammarParser.During_definitionContext, 0)

        def exit_definition(self):
            return self.getTypedRuleContext(GrammarParser.Exit_definitionContext, 0)

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
        self.enterRule(localctx, 20, self.RULE_state_inner_statement)
        try:
            self.state = 255
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.T__5]:
                self.enterOuterAlt(localctx, 1)
                self.state = 249
                self.state_definition()
                pass
            elif token in [GrammarParser.T__8, GrammarParser.ID]:
                self.enterOuterAlt(localctx, 2)
                self.state = 250
                self.transition_definition()
                pass
            elif token in [GrammarParser.T__16]:
                self.enterOuterAlt(localctx, 3)
                self.state = 251
                self.enter_definition()
                pass
            elif token in [GrammarParser.T__19]:
                self.enterOuterAlt(localctx, 4)
                self.state = 252
                self.during_definition()
                pass
            elif token in [GrammarParser.T__18]:
                self.enterOuterAlt(localctx, 5)
                self.state = 253
                self.exit_definition()
                pass
            elif token in [GrammarParser.T__4]:
                self.enterOuterAlt(localctx, 6)
                self.state = 254
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
        self.enterRule(localctx, 22, self.RULE_operation_program)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 260
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 257
                self.operational_assignment()
                self.state = 262
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 263
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
        self.enterRule(localctx, 24, self.RULE_preamble_program)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 268
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 265
                self.preamble_statement()
                self.state = 270
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 271
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
        self.enterRule(localctx, 26, self.RULE_preamble_statement)
        try:
            self.state = 275
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 29, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 273
                self.initial_assignment()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 274
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
        self.enterRule(localctx, 28, self.RULE_initial_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 277
            self.match(GrammarParser.ID)
            self.state = 278
            self.match(GrammarParser.T__22)
            self.state = 279
            self.init_expression(0)
            self.state = 280
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
        self.enterRule(localctx, 30, self.RULE_constant_definition)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 282
            self.match(GrammarParser.ID)
            self.state = 283
            self.match(GrammarParser.T__3)
            self.state = 284
            self.init_expression(0)
            self.state = 285
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
        self.enterRule(localctx, 32, self.RULE_operational_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 287
            self.match(GrammarParser.ID)
            self.state = 288
            self.match(GrammarParser.T__22)
            self.state = 289
            self.num_expression(0)
            self.state = 290
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
        self.enterRule(localctx, 34, self.RULE_generic_expression)
        try:
            self.state = 294
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 30, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 292
                self.num_expression(0)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 293
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
        _startState = 36
        self.enterRecursionRule(localctx, 36, self.RULE_init_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 310
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.T__23]:
                localctx = GrammarParser.ParenExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 297
                self.match(GrammarParser.T__23)
                self.state = 298
                self.init_expression(0)
                self.state = 299
                self.match(GrammarParser.T__24)
                pass
            elif token in [
                GrammarParser.FLOAT,
                GrammarParser.INT,
                GrammarParser.HEX_INT,
            ]:
                localctx = GrammarParser.LiteralExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 301
                self.num_literal()
                pass
            elif token in [
                GrammarParser.T__49,
                GrammarParser.T__50,
                GrammarParser.T__51,
            ]:
                localctx = GrammarParser.MathConstExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 302
                self.math_const()
                pass
            elif token in [GrammarParser.T__25, GrammarParser.T__26]:
                localctx = GrammarParser.UnaryExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 303
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 304
                self.init_expression(9)
                pass
            elif token in [GrammarParser.UFUNC_NAME]:
                localctx = GrammarParser.FuncExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 305
                localctx.function = self.match(GrammarParser.UFUNC_NAME)
                self.state = 306
                self.match(GrammarParser.T__23)
                self.state = 307
                self.init_expression(0)
                self.state = 308
                self.match(GrammarParser.T__24)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 335
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 33, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 333
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 32, self._ctx)
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
                        self.state = 312
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 313
                        localctx.op = self.match(GrammarParser.T__27)
                        self.state = 314
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
                        self.state = 315
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 316
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la) & ~0x3F) == 0
                            and (
                                (1 << _la)
                                & (
                                    (1 << GrammarParser.T__28)
                                    | (1 << GrammarParser.T__29)
                                    | (1 << GrammarParser.T__30)
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 317
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
                        self.state = 318
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 319
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__25 or _la == GrammarParser.T__26
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 320
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
                        self.state = 321
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 322
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__31 or _la == GrammarParser.T__32
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 323
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
                        self.state = 324
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 325
                        localctx.op = self.match(GrammarParser.T__33)
                        self.state = 326
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
                        self.state = 327
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 328
                        localctx.op = self.match(GrammarParser.T__34)
                        self.state = 329
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
                        self.state = 330
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 331
                        localctx.op = self.match(GrammarParser.T__35)
                        self.state = 332
                        self.init_expression(3)
                        pass

                self.state = 337
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 33, self._ctx)

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
        _startState = 38
        self.enterRecursionRule(localctx, 38, self.RULE_num_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 361
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 34, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 339
                self.match(GrammarParser.T__23)
                self.state = 340
                self.num_expression(0)
                self.state = 341
                self.match(GrammarParser.T__24)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 343
                self.num_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.IdExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 344
                self.match(GrammarParser.ID)
                pass

            elif la_ == 4:
                localctx = GrammarParser.MathConstExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 345
                self.math_const()
                pass

            elif la_ == 5:
                localctx = GrammarParser.UnaryExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 346
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__25 or _la == GrammarParser.T__26):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 347
                self.num_expression(10)
                pass

            elif la_ == 6:
                localctx = GrammarParser.FuncExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 348
                localctx.function = self.match(GrammarParser.UFUNC_NAME)
                self.state = 349
                self.match(GrammarParser.T__23)
                self.state = 350
                self.num_expression(0)
                self.state = 351
                self.match(GrammarParser.T__24)
                pass

            elif la_ == 7:
                localctx = GrammarParser.ConditionalCStyleExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 353
                self.match(GrammarParser.T__23)
                self.state = 354
                self.cond_expression(0)
                self.state = 355
                self.match(GrammarParser.T__24)
                self.state = 356
                self.match(GrammarParser.T__36)
                self.state = 357
                self.num_expression(0)
                self.state = 358
                self.match(GrammarParser.T__10)
                self.state = 359
                self.num_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 386
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 36, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 384
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 35, self._ctx)
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
                        self.state = 363
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 9)"
                            )
                        self.state = 364
                        localctx.op = self.match(GrammarParser.T__27)
                        self.state = 365
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
                        self.state = 366
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 367
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la) & ~0x3F) == 0
                            and (
                                (1 << _la)
                                & (
                                    (1 << GrammarParser.T__28)
                                    | (1 << GrammarParser.T__29)
                                    | (1 << GrammarParser.T__30)
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 368
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
                        self.state = 369
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 370
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__25 or _la == GrammarParser.T__26
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 371
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
                        self.state = 372
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 373
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__31 or _la == GrammarParser.T__32
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 374
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
                        self.state = 375
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 376
                        localctx.op = self.match(GrammarParser.T__33)
                        self.state = 377
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
                        self.state = 378
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 379
                        localctx.op = self.match(GrammarParser.T__34)
                        self.state = 380
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
                        self.state = 381
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 382
                        localctx.op = self.match(GrammarParser.T__35)
                        self.state = 383
                        self.num_expression(4)
                        pass

                self.state = 388
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 36, self._ctx)

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
        _startState = 40
        self.enterRecursionRule(localctx, 40, self.RULE_cond_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 413
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 37, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 390
                self.match(GrammarParser.T__23)
                self.state = 391
                self.cond_expression(0)
                self.state = 392
                self.match(GrammarParser.T__24)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 394
                self.bool_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.UnaryExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 395
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__37 or _la == GrammarParser.T__38):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 396
                self.cond_expression(7)
                pass

            elif la_ == 4:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 397
                self.num_expression(0)
                self.state = 398
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (
                    ((_la) & ~0x3F) == 0
                    and (
                        (1 << _la)
                        & (
                            (1 << GrammarParser.T__39)
                            | (1 << GrammarParser.T__40)
                            | (1 << GrammarParser.T__41)
                            | (1 << GrammarParser.T__42)
                        )
                    )
                    != 0
                ):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 399
                self.num_expression(0)
                pass

            elif la_ == 5:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 401
                self.num_expression(0)
                self.state = 402
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.T__43 or _la == GrammarParser.T__44):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 403
                self.num_expression(0)
                pass

            elif la_ == 6:
                localctx = GrammarParser.ConditionalCStyleCondNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 405
                self.match(GrammarParser.T__23)
                self.state = 406
                self.cond_expression(0)
                self.state = 407
                self.match(GrammarParser.T__24)
                self.state = 408
                self.match(GrammarParser.T__36)
                self.state = 409
                self.cond_expression(0)
                self.state = 410
                self.match(GrammarParser.T__10)
                self.state = 411
                self.cond_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 426
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 39, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 424
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 38, self._ctx)
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
                        self.state = 415
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 416
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__43 or _la == GrammarParser.T__44
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 417
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
                        self.state = 418
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 419
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__45 or _la == GrammarParser.T__46
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 420
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
                        self.state = 421
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 422
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.T__47 or _la == GrammarParser.T__48
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 423
                        self.cond_expression(3)
                        pass

                self.state = 428
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 39, self._ctx)

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
        self.enterRule(localctx, 42, self.RULE_num_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 429
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
        self.enterRule(localctx, 44, self.RULE_bool_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 431
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
        self.enterRule(localctx, 46, self.RULE_math_const)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 433
            _la = self._input.LA(1)
            if not (
                ((_la) & ~0x3F) == 0
                and (
                    (1 << _la)
                    & (
                        (1 << GrammarParser.T__49)
                        | (1 << GrammarParser.T__50)
                        | (1 << GrammarParser.T__51)
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
        self.enterRule(localctx, 48, self.RULE_chain_id)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 435
            self.match(GrammarParser.ID)
            self.state = 440
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.T__52:
                self.state = 436
                self.match(GrammarParser.T__52)
                self.state = 437
                self.match(GrammarParser.ID)
                self.state = 442
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
        self._predicates[18] = self.init_expression_sempred
        self._predicates[19] = self.num_expression_sempred
        self._predicates[20] = self.cond_expression_sempred
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
