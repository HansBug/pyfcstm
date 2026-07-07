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
        buf.write("\u0168\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7")
        buf.write("\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r\4\16")
        buf.write("\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23\t\23")
        buf.write("\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30\4\31")
        buf.write("\t\31\4\32\t\32\4\33\t\33\4\34\t\34\4\35\t\35\3\2\5\2")
        buf.write("<\n\2\3\2\7\2?\n\2\f\2\16\2B\13\2\3\2\3\2\3\2\3\3\3\3")
        buf.write("\3\3\3\4\3\4\3\4\3\5\3\5\3\5\5\5P\n\5\3\5\3\5\5\5T\n\5")
        buf.write("\3\5\3\5\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6_\n\6\3\7\3\7")
        buf.write("\3\7\3\7\3\7\3\7\3\7\7\7h\n\7\f\7\16\7k\13\7\3\7\3\7\5")
        buf.write("\7o\n\7\3\b\3\b\5\bs\n\b\3\t\3\t\3\t\5\tx\n\t\3\n\3\n")
        buf.write("\3\n\3\n\5\n~\n\n\3\n\3\n\3\n\3\n\3\13\3\13\3\13\3\13")
        buf.write("\3\13\3\13\3\13\3\13\3\13\3\13\3\13\3\f\3\f\3\f\3\f\3")
        buf.write("\f\3\f\3\f\3\f\3\f\5\f\u0098\n\f\3\f\3\f\3\r\3\r\3\r\3")
        buf.write("\r\3\r\3\r\3\r\3\r\3\16\3\16\3\17\3\17\5\17\u00a8\n\17")
        buf.write("\3\20\3\20\3\20\3\20\3\20\3\20\3\20\3\21\3\21\3\21\7\21")
        buf.write("\u00b4\n\21\f\21\16\21\u00b7\13\21\3\22\3\22\3\23\3\23")
        buf.write("\3\23\3\23\3\23\3\23\3\23\5\23\u00c2\n\23\3\24\3\24\5")
        buf.write("\24\u00c6\n\24\3\25\3\25\5\25\u00ca\n\25\3\26\3\26\3\27")
        buf.write("\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\3\27\3\27\3\27\5\27\u00eb\n\27\3\27\3")
        buf.write("\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\7\27\u0102")
        buf.write("\n\27\f\27\16\27\u0105\13\27\3\30\3\30\3\30\3\30\3\30")
        buf.write("\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30")
        buf.write("\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\5\30\u0120")
        buf.write("\n\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30")
        buf.write("\3\30\3\30\3\30\3\30\3\30\7\30\u0131\n\30\f\30\16\30\u0134")
        buf.write("\13\30\3\31\3\31\3\31\3\31\3\31\5\31\u013b\n\31\3\31\3")
        buf.write("\31\3\31\3\31\3\31\5\31\u0142\n\31\3\31\3\31\3\31\3\31")
        buf.write("\3\31\3\31\3\31\3\31\3\31\3\31\3\31\3\31\3\31\5\31\u0151")
        buf.write("\n\31\3\31\3\31\3\31\3\31\3\31\3\31\3\31\5\31\u015a\n")
        buf.write("\31\3\31\3\31\5\31\u015e\n\31\3\32\3\32\3\33\3\33\3\34")
        buf.write("\3\34\3\35\3\35\3\35\2\4,.\36\2\4\6\b\n\f\16\20\22\24")
        buf.write('\26\30\32\34\36 "$&(*,.\60\62\64\668\2\20\3\2\22\30\3')
        buf.write("\2/\60\3\2CD\4\2@AEE\3\2+,\4\2&&BB\4\2-.IJ\4\2((/\60\4")
        buf.write("\2$$\61\61\4\2%%\62\62\4\2''\63\63\3\2KM\3\2NO\3\2!")
        buf.write("#\2\u0181\2;\3\2\2\2\4F\3\2\2\2\6I\3\2\2\2\bL\3\2\2\2")
        buf.write("\n^\3\2\2\2\fn\3\2\2\2\16r\3\2\2\2\20w\3\2\2\2\22y\3\2")
        buf.write("\2\2\24\u0083\3\2\2\2\26\u008e\3\2\2\2\30\u009b\3\2\2")
        buf.write("\2\32\u00a3\3\2\2\2\34\u00a7\3\2\2\2\36\u00a9\3\2\2\2")
        buf.write(' \u00b0\3\2\2\2"\u00b8\3\2\2\2$\u00c1\3\2\2\2&\u00c5')
        buf.write("\3\2\2\2(\u00c9\3\2\2\2*\u00cb\3\2\2\2,\u00ea\3\2\2\2")
        buf.write(".\u011f\3\2\2\2\60\u015d\3\2\2\2\62\u015f\3\2\2\2\64\u0161")
        buf.write("\3\2\2\2\66\u0163\3\2\2\28\u0165\3\2\2\2:<\5\b\5\2;:\3")
        buf.write("\2\2\2;<\3\2\2\2<@\3\2\2\2=?\5\20\t\2>=\3\2\2\2?B\3\2")
        buf.write("\2\2@>\3\2\2\2@A\3\2\2\2AC\3\2\2\2B@\3\2\2\2CD\5\30\r")
        buf.write("\2DE\7\2\2\3E\3\3\2\2\2FG\5,\27\2GH\7\2\2\3H\5\3\2\2\2")
        buf.write("IJ\5.\30\2JK\7\2\2\3K\7\3\2\2\2LM\7\3\2\2MO\5\n\6\2NP")
        buf.write("\5\f\7\2ON\3\2\2\2OP\3\2\2\2PS\3\2\2\2QR\7\7\2\2RT\5.")
        buf.write("\30\2SQ\3\2\2\2ST\3\2\2\2TU\3\2\2\2UV\7\67\2\2V\t\3\2")
        buf.write("\2\2W_\7\4\2\2X_\7\5\2\2YZ\7\6\2\2Z[\7;\2\2[\\\58\35\2")
        buf.write("\\]\7<\2\2]_\3\2\2\2^W\3\2\2\2^X\3\2\2\2^Y\3\2\2\2_\13")
        buf.write("\3\2\2\2`a\7\b\2\2ao\7A\2\2bc\7\b\2\2cd\79\2\2di\5\16")
        buf.write("\b\2ef\78\2\2fh\5\16\b\2ge\3\2\2\2hk\3\2\2\2ig\3\2\2\2")
        buf.write("ij\3\2\2\2jl\3\2\2\2ki\3\2\2\2lm\7:\2\2mo\3\2\2\2n`\3")
        buf.write("\2\2\2nb\3\2\2\2o\r\3\2\2\2ps\7Q\2\2qs\58\35\2rp\3\2\2")
        buf.write("\2rq\3\2\2\2s\17\3\2\2\2tx\5\22\n\2ux\5\24\13\2vx\5\26")
        buf.write("\f\2wt\3\2\2\2wu\3\2\2\2wv\3\2\2\2x\21\3\2\2\2y}\7\t\2")
        buf.write("\2z~\7\n\2\2{|\7\13\2\2|~\5*\26\2}z\3\2\2\2}{\3\2\2\2")
        buf.write("~\177\3\2\2\2\177\u0080\7>\2\2\u0080\u0081\5.\30\2\u0081")
        buf.write("\u0082\7\67\2\2\u0082\23\3\2\2\2\u0083\u0084\7\t\2\2\u0084")
        buf.write("\u0085\7\f\2\2\u0085\u0086\7;\2\2\u0086\u0087\58\35\2")
        buf.write("\u0087\u0088\78\2\2\u0088\u0089\5$\23\2\u0089\u008a\7")
        buf.write('<\2\2\u008a\u008b\5"\22\2\u008b\u008c\5\64\33\2\u008c')
        buf.write("\u008d\7\67\2\2\u008d\25\3\2\2\2\u008e\u008f\7\t\2\2\u008f")
        buf.write("\u0090\7\r\2\2\u0090\u0097\7\16\2\2\u0091\u0098\7\17\2")
        buf.write("\2\u0092\u0093\7\20\2\2\u0093\u0094\79\2\2\u0094\u0095")
        buf.write("\5 \21\2\u0095\u0096\7:\2\2\u0096\u0098\3\2\2\2\u0097")
        buf.write("\u0091\3\2\2\2\u0097\u0092\3\2\2\2\u0098\u0099\3\2\2\2")
        buf.write("\u0099\u009a\7\67\2\2\u009a\27\3\2\2\2\u009b\u009c\7\21")
        buf.write("\2\2\u009c\u009d\5\32\16\2\u009d\u009e\7-\2\2\u009e\u009f")
        buf.write("\5*\26\2\u009f\u00a0\7>\2\2\u00a0\u00a1\5\34\17\2\u00a1")
        buf.write("\u00a2\7\67\2\2\u00a2\31\3\2\2\2\u00a3\u00a4\t\2\2\2\u00a4")
        buf.write("\33\3\2\2\2\u00a5\u00a8\5\36\20\2\u00a6\u00a8\5.\30\2")
        buf.write("\u00a7\u00a5\3\2\2\2\u00a7\u00a6\3\2\2\2\u00a8\35\3\2")
        buf.write("\2\2\u00a9\u00aa\7\31\2\2\u00aa\u00ab\5.\30\2\u00ab\u00ac")
        buf.write("\7\64\2\2\u00ac\u00ad\7\32\2\2\u00ad\u00ae\5*\26\2\u00ae")
        buf.write("\u00af\5.\30\2\u00af\37\3\2\2\2\u00b0\u00b5\58\35\2\u00b1")
        buf.write("\u00b2\78\2\2\u00b2\u00b4\58\35\2\u00b3\u00b1\3\2\2\2")
        buf.write("\u00b4\u00b7\3\2\2\2\u00b5\u00b3\3\2\2\2\u00b5\u00b6\3")
        buf.write("\2\2\2\u00b6!\3\2\2\2\u00b7\u00b5\3\2\2\2\u00b8\u00b9")
        buf.write("\t\3\2\2\u00b9#\3\2\2\2\u00ba\u00c2\7A\2\2\u00bb\u00c2")
        buf.write("\5*\26\2\u00bc\u00bd\5*\26\2\u00bd\u00be\7\66\2\2\u00be")
        buf.write("\u00bf\5*\26\2\u00bf\u00c2\3\2\2\2\u00c0\u00c2\7\65\2")
        buf.write("\2\u00c1\u00ba\3\2\2\2\u00c1\u00bb\3\2\2\2\u00c1\u00bc")
        buf.write("\3\2\2\2\u00c1\u00c0\3\2\2\2\u00c2%\3\2\2\2\u00c3\u00c6")
        buf.write("\7 \2\2\u00c4\u00c6\5*\26\2\u00c5\u00c3\3\2\2\2\u00c5")
        buf.write("\u00c4\3\2\2\2\u00c6'\3\2\2\2\u00c7\u00ca\7 \2\2\u00c8")
        buf.write("\u00ca\5*\26\2\u00c9\u00c7\3\2\2\2\u00c9\u00c8\3\2\2\2")
        buf.write("\u00ca)\3\2\2\2\u00cb\u00cc\7M\2\2\u00cc+\3\2\2\2\u00cd")
        buf.write("\u00ce\b\27\1\2\u00ce\u00cf\7;\2\2\u00cf\u00d0\5,\27\2")
        buf.write("\u00d0\u00d1\7<\2\2\u00d1\u00eb\3\2\2\2\u00d2\u00eb\5")
        buf.write("\62\32\2\u00d3\u00eb\7Q\2\2\u00d4\u00eb\5\66\34\2\u00d5")
        buf.write("\u00d6\7\33\2\2\u00d6\u00d7\7;\2\2\u00d7\u00d8\58\35\2")
        buf.write("\u00d8\u00d9\7<\2\2\u00d9\u00eb\3\2\2\2\u00da\u00eb\7")
        buf.write("\34\2\2\u00db\u00dc\t\4\2\2\u00dc\u00eb\5,\27\f\u00dd")
        buf.write("\u00de\7P\2\2\u00de\u00df\7;\2\2\u00df\u00e0\5,\27\2\u00e0")
        buf.write("\u00e1\7<\2\2\u00e1\u00eb\3\2\2\2\u00e2\u00e3\7;\2\2\u00e3")
        buf.write("\u00e4\5.\30\2\u00e4\u00e5\7<\2\2\u00e5\u00e6\7=\2\2\u00e6")
        buf.write("\u00e7\5,\27\2\u00e7\u00e8\7>\2\2\u00e8\u00e9\5,\27\3")
        buf.write("\u00e9\u00eb\3\2\2\2\u00ea\u00cd\3\2\2\2\u00ea\u00d2\3")
        buf.write("\2\2\2\u00ea\u00d3\3\2\2\2\u00ea\u00d4\3\2\2\2\u00ea\u00d5")
        buf.write("\3\2\2\2\u00ea\u00da\3\2\2\2\u00ea\u00db\3\2\2\2\u00ea")
        buf.write("\u00dd\3\2\2\2\u00ea\u00e2\3\2\2\2\u00eb\u0103\3\2\2\2")
        buf.write("\u00ec\u00ed\f\13\2\2\u00ed\u00ee\7*\2\2\u00ee\u0102\5")
        buf.write(",\27\13\u00ef\u00f0\f\n\2\2\u00f0\u00f1\t\5\2\2\u00f1")
        buf.write("\u0102\5,\27\13\u00f2\u00f3\f\t\2\2\u00f3\u00f4\t\4\2")
        buf.write("\2\u00f4\u0102\5,\27\n\u00f5\u00f6\f\b\2\2\u00f6\u00f7")
        buf.write("\t\6\2\2\u00f7\u0102\5,\27\t\u00f8\u00f9\f\7\2\2\u00f9")
        buf.write("\u00fa\7F\2\2\u00fa\u0102\5,\27\b\u00fb\u00fc\f\6\2\2")
        buf.write("\u00fc\u00fd\7G\2\2\u00fd\u0102\5,\27\7\u00fe\u00ff\f")
        buf.write("\5\2\2\u00ff\u0100\7H\2\2\u0100\u0102\5,\27\6\u0101\u00ec")
        buf.write("\3\2\2\2\u0101\u00ef\3\2\2\2\u0101\u00f2\3\2\2\2\u0101")
        buf.write("\u00f5\3\2\2\2\u0101\u00f8\3\2\2\2\u0101\u00fb\3\2\2\2")
        buf.write("\u0101\u00fe\3\2\2\2\u0102\u0105\3\2\2\2\u0103\u0101\3")
        buf.write("\2\2\2\u0103\u0104\3\2\2\2\u0104-\3\2\2\2\u0105\u0103")
        buf.write("\3\2\2\2\u0106\u0107\b\30\1\2\u0107\u0108\7;\2\2\u0108")
        buf.write("\u0109\5.\30\2\u0109\u010a\7<\2\2\u010a\u0120\3\2\2\2")
        buf.write("\u010b\u0120\5\64\33\2\u010c\u0120\5\60\31\2\u010d\u010e")
        buf.write("\t\7\2\2\u010e\u0120\5.\30\13\u010f\u0110\5,\27\2\u0110")
        buf.write("\u0111\t\b\2\2\u0111\u0112\5,\27\2\u0112\u0120\3\2\2\2")
        buf.write("\u0113\u0114\5,\27\2\u0114\u0115\t\3\2\2\u0115\u0116\5")
        buf.write(",\27\2\u0116\u0120\3\2\2\2\u0117\u0118\7;\2\2\u0118\u0119")
        buf.write("\5.\30\2\u0119\u011a\7<\2\2\u011a\u011b\7=\2\2\u011b\u011c")
        buf.write("\5.\30\2\u011c\u011d\7>\2\2\u011d\u011e\5.\30\3\u011e")
        buf.write("\u0120\3\2\2\2\u011f\u0106\3\2\2\2\u011f\u010b\3\2\2\2")
        buf.write("\u011f\u010c\3\2\2\2\u011f\u010d\3\2\2\2\u011f\u010f\3")
        buf.write("\2\2\2\u011f\u0113\3\2\2\2\u011f\u0117\3\2\2\2\u0120\u0132")
        buf.write("\3\2\2\2\u0121\u0122\f\b\2\2\u0122\u0123\t\t\2\2\u0123")
        buf.write("\u0131\5.\30\t\u0124\u0125\f\7\2\2\u0125\u0126\t\n\2\2")
        buf.write("\u0126\u0131\5.\30\b\u0127\u0128\f\6\2\2\u0128\u0129\7")
        buf.write(")\2\2\u0129\u0131\5.\30\7\u012a\u012b\f\5\2\2\u012b\u012c")
        buf.write("\t\13\2\2\u012c\u0131\5.\30\6\u012d\u012e\f\4\2\2\u012e")
        buf.write("\u012f\t\f\2\2\u012f\u0131\5.\30\4\u0130\u0121\3\2\2\2")
        buf.write("\u0130\u0124\3\2\2\2\u0130\u0127\3\2\2\2\u0130\u012a\3")
        buf.write("\2\2\2\u0130\u012d\3\2\2\2\u0131\u0134\3\2\2\2\u0132\u0130")
        buf.write("\3\2\2\2\u0132\u0133\3\2\2\2\u0133/\3\2\2\2\u0134\u0132")
        buf.write("\3\2\2\2\u0135\u0136\7\35\2\2\u0136\u0137\7;\2\2\u0137")
        buf.write("\u013a\58\35\2\u0138\u0139\78\2\2\u0139\u013b\5(\25\2")
        buf.write("\u013a\u0138\3\2\2\2\u013a\u013b\3\2\2\2\u013b\u013c\3")
        buf.write("\2\2\2\u013c\u013d\7<\2\2\u013d\u015e\3\2\2\2\u013e\u013f")
        buf.write("\7\5\2\2\u013f\u0141\7;\2\2\u0140\u0142\5(\25\2\u0141")
        buf.write("\u0140\3\2\2\2\u0141\u0142\3\2\2\2\u0142\u0143\3\2\2\2")
        buf.write("\u0143\u015e\7<\2\2\u0144\u0145\7\f\2\2\u0145\u0146\7")
        buf.write(";\2\2\u0146\u0147\58\35\2\u0147\u0148\78\2\2\u0148\u0149")
        buf.write("\5&\24\2\u0149\u014a\7<\2\2\u014a\u015e\3\2\2\2\u014b")
        buf.write("\u014c\7\36\2\2\u014c\u014d\7;\2\2\u014d\u0150\58\35\2")
        buf.write("\u014e\u014f\78\2\2\u014f\u0151\5(\25\2\u0150\u014e\3")
        buf.write("\2\2\2\u0150\u0151\3\2\2\2\u0151\u0152\3\2\2\2\u0152\u0153")
        buf.write("\7<\2\2\u0153\u015e\3\2\2\2\u0154\u0155\7\37\2\2\u0155")
        buf.write("\u0156\7;\2\2\u0156\u0159\58\35\2\u0157\u0158\78\2\2\u0158")
        buf.write("\u015a\5(\25\2\u0159\u0157\3\2\2\2\u0159\u015a\3\2\2\2")
        buf.write("\u015a\u015b\3\2\2\2\u015b\u015c\7<\2\2\u015c\u015e\3")
        buf.write("\2\2\2\u015d\u0135\3\2\2\2\u015d\u013e\3\2\2\2\u015d\u0144")
        buf.write("\3\2\2\2\u015d\u014b\3\2\2\2\u015d\u0154\3\2\2\2\u015e")
        buf.write("\61\3\2\2\2\u015f\u0160\t\r\2\2\u0160\63\3\2\2\2\u0161")
        buf.write("\u0162\t\16\2\2\u0162\65\3\2\2\2\u0163\u0164\t\17\2\2")
        buf.write("\u0164\67\3\2\2\2\u0165\u0166\7R\2\2\u01669\3\2\2\2\35")
        buf.write(";@OS^inrw}\u0097\u00a7\u00b5\u00c1\u00c5\u00c9\u00ea\u0101")
        buf.write("\u0103\u011f\u0130\u0132\u013a\u0141\u0150\u0159\u015d")
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
    RULE_num_literal = 24
    RULE_bool_literal = 25
    RULE_math_const = 26
    RULE_string_literal = 27

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
    CALLED = 29
    CURRENT = 30
    PI_CONST = 31
    E_CONST = 32
    TAU_CONST = 33
    AND_KW = 34
    OR_KW = 35
    NOT_KW = 36
    IMPLIES_KW = 37
    IFF_KW = 38
    XOR_KW = 39
    POW = 40
    SHIFT_RIGHT = 41
    SHIFT_LEFT = 42
    LE = 43
    GE = 44
    EQ = 45
    NE = 46
    LOGICAL_AND = 47
    LOGICAL_OR = 48
    IMPLIES = 49
    ARROW = 50
    RANGE_INT = 51
    DOTDOT = 52
    SEMI = 53
    COMMA = 54
    LBRACE = 55
    RBRACE = 56
    LPAREN = 57
    RPAREN = 58
    QUESTION = 59
    COLON = 60
    DOT = 61
    SLASH = 62
    STAR = 63
    BANG = 64
    PLUS = 65
    MINUS = 66
    PERCENT = 67
    AMP = 68
    CARET = 69
    PIPE = 70
    LT = 71
    GT = 72
    FLOAT = 73
    HEX_INT = 74
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
            self.state = 57
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == BmcQueryParser.INIT:
                self.state = 56
                self.init_clause()

            self.state = 62
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == BmcQueryParser.ASSUME:
                self.state = 59
                self.assume_clause()
                self.state = 64
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 65
            self.check_clause()
            self.state = 66
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
            self.state = 68
            self.bmc_num_expression(0)
            self.state = 69
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
            self.state = 71
            self.bmc_cond_expression(0)
            self.state = 72
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
            self.state = 74
            self.match(BmcQueryParser.INIT)
            self.state = 75
            self.init_target()
            self.state = 77
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == BmcQueryParser.HAVOC:
                self.state = 76
                self.init_havoc_clause()

            self.state = 81
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == BmcQueryParser.WHERE:
                self.state = 79
                self.match(BmcQueryParser.WHERE)
                self.state = 80
                self.bmc_cond_expression(0)

            self.state = 83
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
            self.state = 92
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.COLD]:
                self.enterOuterAlt(localctx, 1)
                self.state = 85
                self.match(BmcQueryParser.COLD)
                pass
            elif token in [BmcQueryParser.TERMINATED]:
                self.enterOuterAlt(localctx, 2)
                self.state = 86
                self.match(BmcQueryParser.TERMINATED)
                pass
            elif token in [BmcQueryParser.STATE]:
                self.enterOuterAlt(localctx, 3)
                self.state = 87
                self.match(BmcQueryParser.STATE)
                self.state = 88
                self.match(BmcQueryParser.LPAREN)
                self.state = 89
                self.string_literal()
                self.state = 90
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
            self.state = 108
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 6, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 94
                self.match(BmcQueryParser.HAVOC)
                self.state = 95
                self.match(BmcQueryParser.STAR)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 96
                self.match(BmcQueryParser.HAVOC)
                self.state = 97
                self.match(BmcQueryParser.LBRACE)
                self.state = 98
                self.init_var_ref()
                self.state = 103
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == BmcQueryParser.COMMA:
                    self.state = 99
                    self.match(BmcQueryParser.COMMA)
                    self.state = 100
                    self.init_var_ref()
                    self.state = 105
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 106
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
            self.state = 112
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 110
                self.match(BmcQueryParser.ID)
                pass
            elif token in [BmcQueryParser.STRING]:
                self.enterOuterAlt(localctx, 2)
                self.state = 111
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
            self.state = 117
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 8, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 114
                self.frame_assume()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 115
                self.event_assume()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 116
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
            self.state = 119
            self.match(BmcQueryParser.ASSUME)
            self.state = 123
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ALWAYS]:
                self.state = 120
                self.match(BmcQueryParser.ALWAYS)
                pass
            elif token in [BmcQueryParser.AT]:
                self.state = 121
                self.match(BmcQueryParser.AT)
                self.state = 122
                self.integer_literal()
                pass
            else:
                raise NoViableAltException(self)

            self.state = 125
            self.match(BmcQueryParser.COLON)
            self.state = 126
            self.bmc_cond_expression(0)
            self.state = 127
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
            self.state = 129
            self.match(BmcQueryParser.ASSUME)
            self.state = 130
            self.match(BmcQueryParser.EVENT)
            self.state = 131
            self.match(BmcQueryParser.LPAREN)
            self.state = 132
            self.string_literal()
            self.state = 133
            self.match(BmcQueryParser.COMMA)
            self.state = 134
            self.event_range_selector()
            self.state = 135
            self.match(BmcQueryParser.RPAREN)
            self.state = 136
            self.bool_cmp_op()
            self.state = 137
            self.bool_literal()
            self.state = 138
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
            self.state = 140
            self.match(BmcQueryParser.ASSUME)
            self.state = 141
            self.match(BmcQueryParser.EVENTS)
            self.state = 142
            self.match(BmcQueryParser.CARDINALITY)
            self.state = 149
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ANY]:
                self.state = 143
                self.match(BmcQueryParser.ANY)
                pass
            elif token in [BmcQueryParser.AT_MOST_ONE]:
                self.state = 144
                self.match(BmcQueryParser.AT_MOST_ONE)
                self.state = 145
                self.match(BmcQueryParser.LBRACE)
                self.state = 146
                self.string_list()
                self.state = 147
                self.match(BmcQueryParser.RBRACE)
                pass
            else:
                raise NoViableAltException(self)

            self.state = 151
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
            self.state = 153
            self.match(BmcQueryParser.CHECK)
            self.state = 154
            self.property_kind()
            self.state = 155
            self.match(BmcQueryParser.LE)
            self.state = 156
            self.integer_literal()
            self.state = 157
            self.match(BmcQueryParser.COLON)
            self.state = 158
            self.property_body()
            self.state = 159
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
            self.state = 161
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
            self.state = 165
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.TRIGGER]:
                self.enterOuterAlt(localctx, 1)
                self.state = 163
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
                BmcQueryParser.INT,
                BmcQueryParser.TRUE,
                BmcQueryParser.FALSE,
                BmcQueryParser.UFUNC_NAME,
                BmcQueryParser.ID,
            ]:
                self.enterOuterAlt(localctx, 2)
                self.state = 164
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
            self.state = 167
            self.match(BmcQueryParser.TRIGGER)
            self.state = 168
            self.bmc_cond_expression(0)
            self.state = 169
            self.match(BmcQueryParser.ARROW)
            self.state = 170
            self.match(BmcQueryParser.WITHIN)
            self.state = 171
            self.integer_literal()
            self.state = 172
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
            self.state = 174
            self.string_literal()
            self.state = 179
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == BmcQueryParser.COMMA:
                self.state = 175
                self.match(BmcQueryParser.COMMA)
                self.state = 176
                self.string_literal()
                self.state = 181
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
            self.state = 182
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
            self.state = 191
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 13, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 184
                self.match(BmcQueryParser.STAR)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 185
                self.integer_literal()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 186
                self.integer_literal()
                self.state = 187
                self.match(BmcQueryParser.DOTDOT)
                self.state = 188
                self.integer_literal()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 190
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
            self.state = 195
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.CURRENT]:
                self.enterOuterAlt(localctx, 1)
                self.state = 193
                self.match(BmcQueryParser.CURRENT)
                pass
            elif token in [BmcQueryParser.INT]:
                self.enterOuterAlt(localctx, 2)
                self.state = 194
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
            self.state = 199
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.CURRENT]:
                self.enterOuterAlt(localctx, 1)
                self.state = 197
                self.match(BmcQueryParser.CURRENT)
                pass
            elif token in [BmcQueryParser.INT]:
                self.enterOuterAlt(localctx, 2)
                self.state = 198
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
            self.state = 201
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
            self.state = 232
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 16, self._ctx)
            if la_ == 1:
                localctx = BmcQueryParser.ParenExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 204
                self.match(BmcQueryParser.LPAREN)
                self.state = 205
                self.bmc_num_expression(0)
                self.state = 206
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = BmcQueryParser.LiteralExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 208
                self.num_literal()
                pass

            elif la_ == 3:
                localctx = BmcQueryParser.IdExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 209
                self.match(BmcQueryParser.ID)
                pass

            elif la_ == 4:
                localctx = BmcQueryParser.MathConstExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 210
                self.math_const()
                pass

            elif la_ == 5:
                localctx = BmcQueryParser.FrameVarExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 211
                self.match(BmcQueryParser.VAR)
                self.state = 212
                self.match(BmcQueryParser.LPAREN)
                self.state = 213
                self.string_literal()
                self.state = 214
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 6:
                localctx = BmcQueryParser.CycleExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 216
                self.match(BmcQueryParser.CYCLE)
                pass

            elif la_ == 7:
                localctx = BmcQueryParser.UnaryExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 217
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == BmcQueryParser.PLUS or _la == BmcQueryParser.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 218
                self.bmc_num_expression(10)
                pass

            elif la_ == 8:
                localctx = BmcQueryParser.FuncExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 219
                localctx.func_name = self.match(BmcQueryParser.UFUNC_NAME)
                self.state = 220
                self.match(BmcQueryParser.LPAREN)
                self.state = 221
                self.bmc_num_expression(0)
                self.state = 222
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 9:
                localctx = BmcQueryParser.ConditionalCStyleExprNumContext(
                    self, localctx
                )
                self._ctx = localctx
                _prevctx = localctx
                self.state = 224
                self.match(BmcQueryParser.LPAREN)
                self.state = 225
                self.bmc_cond_expression(0)
                self.state = 226
                self.match(BmcQueryParser.RPAREN)
                self.state = 227
                self.match(BmcQueryParser.QUESTION)
                self.state = 228
                self.bmc_num_expression(0)
                self.state = 229
                self.match(BmcQueryParser.COLON)
                self.state = 230
                self.bmc_num_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 257
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 18, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 255
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 17, self._ctx)
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
                        self.state = 234
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 9)"
                            )
                        self.state = 235
                        localctx.op = self.match(BmcQueryParser.POW)
                        self.state = 236
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
                        self.state = 237
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 238
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la - 62) & ~0x3F) == 0
                            and (
                                (1 << (_la - 62))
                                & (
                                    (1 << (BmcQueryParser.SLASH - 62))
                                    | (1 << (BmcQueryParser.STAR - 62))
                                    | (1 << (BmcQueryParser.PERCENT - 62))
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 239
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
                        self.state = 240
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 241
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == BmcQueryParser.PLUS or _la == BmcQueryParser.MINUS
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 242
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
                        self.state = 243
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 244
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
                        self.state = 245
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
                        self.state = 246
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 247
                        localctx.op = self.match(BmcQueryParser.AMP)
                        self.state = 248
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
                        self.state = 249
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 250
                        localctx.op = self.match(BmcQueryParser.CARET)
                        self.state = 251
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
                        self.state = 252
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 253
                        localctx.op = self.match(BmcQueryParser.PIPE)
                        self.state = 254
                        self.bmc_num_expression(4)
                        pass

                self.state = 259
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 18, self._ctx)

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
            self.state = 285
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 19, self._ctx)
            if la_ == 1:
                localctx = BmcQueryParser.ParenExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 261
                self.match(BmcQueryParser.LPAREN)
                self.state = 262
                self.bmc_cond_expression(0)
                self.state = 263
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = BmcQueryParser.LiteralExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 265
                self.bool_literal()
                pass

            elif la_ == 3:
                localctx = BmcQueryParser.AtomExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 266
                self.bmc_boolean_atom()
                pass

            elif la_ == 4:
                localctx = BmcQueryParser.UnaryExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 267
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == BmcQueryParser.NOT_KW or _la == BmcQueryParser.BANG):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 268
                self.bmc_cond_expression(9)
                pass

            elif la_ == 5:
                localctx = BmcQueryParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 269
                self.bmc_num_expression(0)
                self.state = 270
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (
                    ((_la - 43) & ~0x3F) == 0
                    and (
                        (1 << (_la - 43))
                        & (
                            (1 << (BmcQueryParser.LE - 43))
                            | (1 << (BmcQueryParser.GE - 43))
                            | (1 << (BmcQueryParser.LT - 43))
                            | (1 << (BmcQueryParser.GT - 43))
                        )
                    )
                    != 0
                ):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 271
                self.bmc_num_expression(0)
                pass

            elif la_ == 6:
                localctx = BmcQueryParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 273
                self.bmc_num_expression(0)
                self.state = 274
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == BmcQueryParser.EQ or _la == BmcQueryParser.NE):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 275
                self.bmc_num_expression(0)
                pass

            elif la_ == 7:
                localctx = BmcQueryParser.ConditionalCStyleExprCondContext(
                    self, localctx
                )
                self._ctx = localctx
                _prevctx = localctx
                self.state = 277
                self.match(BmcQueryParser.LPAREN)
                self.state = 278
                self.bmc_cond_expression(0)
                self.state = 279
                self.match(BmcQueryParser.RPAREN)
                self.state = 280
                self.match(BmcQueryParser.QUESTION)
                self.state = 281
                self.bmc_cond_expression(0)
                self.state = 282
                self.match(BmcQueryParser.COLON)
                self.state = 283
                self.bmc_cond_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 304
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 21, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 302
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 20, self._ctx)
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
                        self.state = 287
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 288
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
                        self.state = 289
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
                        self.state = 290
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 291
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
                        self.state = 292
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
                        self.state = 293
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 294
                        localctx.op = self.match(BmcQueryParser.XOR_KW)
                        self.state = 295
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
                        self.state = 296
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 297
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
                        self.state = 298
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
                        self.state = 299
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 300
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
                        self.state = 301
                        self.bmc_cond_expression(2)
                        pass

                self.state = 306
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 21, self._ctx)

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
        self.enterRule(localctx, 46, self.RULE_bmc_boolean_atom)
        self._la = 0  # Token type
        try:
            self.state = 347
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ACTIVE]:
                self.enterOuterAlt(localctx, 1)
                self.state = 307
                self.match(BmcQueryParser.ACTIVE)
                self.state = 308
                self.match(BmcQueryParser.LPAREN)
                self.state = 309
                self.string_literal()
                self.state = 312
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == BmcQueryParser.COMMA:
                    self.state = 310
                    self.match(BmcQueryParser.COMMA)
                    self.state = 311
                    self.frame_selector()

                self.state = 314
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.TERMINATED]:
                self.enterOuterAlt(localctx, 2)
                self.state = 316
                self.match(BmcQueryParser.TERMINATED)
                self.state = 317
                self.match(BmcQueryParser.LPAREN)
                self.state = 319
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == BmcQueryParser.CURRENT or _la == BmcQueryParser.INT:
                    self.state = 318
                    self.frame_selector()

                self.state = 321
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.EVENT]:
                self.enterOuterAlt(localctx, 3)
                self.state = 322
                self.match(BmcQueryParser.EVENT)
                self.state = 323
                self.match(BmcQueryParser.LPAREN)
                self.state = 324
                self.string_literal()
                self.state = 325
                self.match(BmcQueryParser.COMMA)
                self.state = 326
                self.event_cycle_selector()
                self.state = 327
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.CASE]:
                self.enterOuterAlt(localctx, 4)
                self.state = 329
                self.match(BmcQueryParser.CASE)
                self.state = 330
                self.match(BmcQueryParser.LPAREN)
                self.state = 331
                self.string_literal()
                self.state = 334
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == BmcQueryParser.COMMA:
                    self.state = 332
                    self.match(BmcQueryParser.COMMA)
                    self.state = 333
                    self.frame_selector()

                self.state = 336
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.CALLED]:
                self.enterOuterAlt(localctx, 5)
                self.state = 338
                self.match(BmcQueryParser.CALLED)
                self.state = 339
                self.match(BmcQueryParser.LPAREN)
                self.state = 340
                self.string_literal()
                self.state = 343
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == BmcQueryParser.COMMA:
                    self.state = 341
                    self.match(BmcQueryParser.COMMA)
                    self.state = 342
                    self.frame_selector()

                self.state = 345
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
        self.enterRule(localctx, 48, self.RULE_num_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 349
            _la = self._input.LA(1)
            if not (
                ((_la - 73) & ~0x3F) == 0
                and (
                    (1 << (_la - 73))
                    & (
                        (1 << (BmcQueryParser.FLOAT - 73))
                        | (1 << (BmcQueryParser.HEX_INT - 73))
                        | (1 << (BmcQueryParser.INT - 73))
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
        self.enterRule(localctx, 50, self.RULE_bool_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 351
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
        self.enterRule(localctx, 52, self.RULE_math_const)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 353
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
        self.enterRule(localctx, 54, self.RULE_string_literal)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 355
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
