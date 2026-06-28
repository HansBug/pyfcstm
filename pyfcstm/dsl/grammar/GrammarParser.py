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
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3a")
        buf.write("\u0325\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7")
        buf.write("\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r\4\16")
        buf.write("\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23\t\23")
        buf.write("\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30\4\31")
        buf.write("\t\31\4\32\t\32\4\33\t\33\4\34\t\34\4\35\t\35\4\36\t\36")
        buf.write('\4\37\t\37\4 \t \4!\t!\4"\t"\4#\t#\4$\t$\4%\t%\4&\t')
        buf.write("&\4'\t'\4(\t(\4)\t)\4*\t*\4+\t+\4,\t,\4-\t-\4.\t.\4")
        buf.write("/\t/\4\60\t\60\4\61\t\61\4\62\t\62\4\63\t\63\4\64\t\64")
        buf.write("\3\2\3\2\3\2\3\3\7\3m\n\3\f\3\16\3p\13\3\3\3\3\3\3\3\3")
        buf.write("\4\3\4\3\4\3\4\3\4\3\4\3\4\3\5\5\5}\n\5\3\5\3\5\3\5\3")
        buf.write("\5\5\5\u0083\n\5\3\5\3\5\5\5\u0087\n\5\3\5\3\5\3\5\3\5")
        buf.write("\5\5\u008d\n\5\3\5\3\5\7\5\u0091\n\5\f\5\16\5\u0094\13")
        buf.write("\5\3\5\5\5\u0097\n\5\3\6\3\6\3\6\3\6\5\6\u009d\n\6\3\6")
        buf.write("\3\6\3\6\3\6\3\6\3\6\5\6\u00a5\n\6\3\6\3\6\3\6\3\6\5\6")
        buf.write("\u00ab\n\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u00b3\n\6\3\6\3")
        buf.write("\6\3\6\3\6\5\6\u00b9\n\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u00c1")
        buf.write("\n\6\5\6\u00c3\n\6\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7")
        buf.write("\3\7\5\7\u00cf\n\7\3\b\7\b\u00d2\n\b\f\b\16\b\u00d5\13")
        buf.write("\b\3\b\3\b\3\b\7\b\u00da\n\b\f\b\16\b\u00dd\13\b\3\t\3")
        buf.write("\t\3\t\3\n\3\n\5\n\u00e4\n\n\3\13\3\13\3\13\3\13\3\13")
        buf.write("\3\13\3\13\3\13\3\13\3\13\5\13\u00f0\n\13\3\f\7\f\u00f3")
        buf.write("\n\f\f\f\16\f\u00f6\13\f\3\f\3\f\3\f\7\f\u00fb\n\f\f\f")
        buf.write("\16\f\u00fe\13\f\3\r\3\r\3\r\3\16\3\16\5\16\u0105\n\16")
        buf.write("\3\17\3\17\3\20\3\20\3\20\3\20\3\20\3\20\7\20\u010f\n")
        buf.write("\20\f\20\16\20\u0112\13\20\3\20\5\20\u0115\n\20\3\21\3")
        buf.write("\21\3\22\3\22\5\22\u011b\n\22\3\23\3\23\3\24\3\24\3\24")
        buf.write("\3\24\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25")
        buf.write("\3\25\3\25\3\25\3\25\5\25\u0131\n\25\3\25\3\25\3\25\3")
        buf.write("\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25")
        buf.write("\3\25\5\25\u0142\n\25\3\25\3\25\3\25\3\25\3\25\3\25\3")
        buf.write("\25\3\25\3\25\3\25\3\25\3\25\3\25\5\25\u0151\n\25\3\25")
        buf.write("\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25")
        buf.write("\3\25\5\25\u0160\n\25\3\25\5\25\u0163\n\25\3\26\3\26\5")
        buf.write("\26\u0167\n\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26\3\26")
        buf.write("\3\26\3\26\3\26\5\26\u0174\n\26\3\26\3\26\3\26\5\26\u0179")
        buf.write("\n\26\3\26\3\26\3\26\3\26\5\26\u017f\n\26\3\27\3\27\5")
        buf.write("\27\u0183\n\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\5\27\u0190\n\27\3\27\3\27\3\27\5\27\u0195")
        buf.write("\n\27\3\27\3\27\3\27\3\27\5\27\u019b\n\27\3\30\3\30\5")
        buf.write("\30\u019f\n\30\3\30\5\30\u01a2\n\30\3\30\3\30\3\30\3\30")
        buf.write("\3\30\3\30\5\30\u01aa\n\30\3\30\3\30\3\30\3\30\3\30\5")
        buf.write("\30\u01b1\n\30\3\30\3\30\5\30\u01b5\n\30\3\30\3\30\3\30")
        buf.write("\5\30\u01ba\n\30\3\30\5\30\u01bd\n\30\3\30\3\30\3\30\3")
        buf.write("\30\5\30\u01c3\n\30\3\31\3\31\3\31\3\31\5\31\u01c9\n\31")
        buf.write("\3\31\3\31\3\31\3\31\3\31\3\31\3\31\3\31\3\31\3\31\3\31")
        buf.write("\3\31\3\31\3\31\3\31\5\31\u01da\n\31\3\31\3\31\3\31\3")
        buf.write("\31\3\31\5\31\u01e1\n\31\3\31\3\31\3\31\3\31\5\31\u01e7")
        buf.write("\n\31\3\32\3\32\3\32\3\32\5\32\u01ed\n\32\3\32\3\32\3")
        buf.write("\33\3\33\3\33\3\33\3\33\3\33\5\33\u01f7\n\33\3\33\3\33")
        buf.write("\7\33\u01fb\n\33\f\33\16\33\u01fe\13\33\3\33\3\33\5\33")
        buf.write("\u0202\n\33\3\34\3\34\3\34\5\34\u0207\n\34\3\35\3\35\3")
        buf.write("\35\3\35\3\35\3\35\3\36\3\36\3\36\3\36\3\36\7\36\u0214")
        buf.write("\n\36\f\36\16\36\u0217\13\36\3\36\3\36\3\36\5\36\u021c")
        buf.write("\n\36\3\37\3\37\3\37\5\37\u0221\n\37\3 \3 \3 \3 \3 \3")
        buf.write(' \5 \u0229\n \3 \3 \3!\3!\3!\3!\3!\3"\3"\3"\3"\3#')
        buf.write("\3#\3#\3#\3#\3#\3#\3#\3#\3#\3#\3#\7#\u0242\n#\f#\16#\u0245")
        buf.write("\13#\3#\3#\5#\u0249\n#\3$\3$\3$\5$\u024e\n$\3%\7%\u0251")
        buf.write("\n%\f%\16%\u0254\13%\3&\3&\3&\3&\3&\3&\3&\3&\3&\3&\5&")
        buf.write("\u0260\n&\3'\7'\u0263\n'\f'\16'\u0266\13'\3'\3")
        buf.write("'\3(\7(\u026b\n(\f(\16(\u026e\13(\3(\3(\3)\3)\5)\u0274")
        buf.write("\n)\3*\3*\3*\3*\3*\3+\3+\3+\3+\3+\3,\3,\3,\3,\3,\3-\3")
        buf.write("-\5-\u0287\n-\3.\3.\3.\3.\3.\3.\3.\3.\3.\3.\3.\3.\3.\3")
        buf.write(".\5.\u0297\n.\3.\3.\3.\3.\3.\3.\3.\3.\3.\3.\3.\3.\3.\3")
        buf.write(".\3.\3.\3.\3.\3.\3.\3.\7.\u02ae\n.\f.\16.\u02b1\13.\3")
        buf.write("/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3")
        buf.write("/\3/\3/\3/\3/\5/\u02ca\n/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3")
        buf.write("/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\7/\u02e1\n/\f/\16/")
        buf.write("\u02e4\13/\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60")
        buf.write("\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60")
        buf.write("\3\60\3\60\3\60\3\60\5\60\u02fe\n\60\3\60\3\60\3\60\3")
        buf.write("\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60")
        buf.write("\3\60\7\60\u030f\n\60\f\60\16\60\u0312\13\60\3\61\3\61")
        buf.write("\3\62\3\62\3\63\3\63\3\64\5\64\u031b\n\64\3\64\3\64\3")
        buf.write("\64\7\64\u0320\n\64\f\64\16\64\u0323\13\64\3\64\2\5Z\\")
        buf.write('^\65\2\4\6\b\n\f\16\20\22\24\26\30\32\34\36 "$&(*,.\60')
        buf.write("\62\64\668:<>@BDFHJLNPRTVXZ\\^`bdf\2\22\3\2\24\25\4\2")
        buf.write('++\66\66\3\2\r\16\3\2;<\4\289==\3\2!"\4\2\33\33::\4\2')
        buf.write("#$AB\3\2%&\4\2\35\35%&\4\2\31\31''\4\2\32\32((\4\2\34")
        buf.write("\34))\3\2DF\3\2GH\3\2\26\30\2\u037a\2h\3\2\2\2\4n\3\2")
        buf.write("\2\2\6t\3\2\2\2\b\u0096\3\2\2\2\n\u00c2\3\2\2\2\f\u00ce")
        buf.write("\3\2\2\2\16\u00d3\3\2\2\2\20\u00de\3\2\2\2\22\u00e3\3")
        buf.write("\2\2\2\24\u00ef\3\2\2\2\26\u00f4\3\2\2\2\30\u00ff\3\2")
        buf.write("\2\2\32\u0104\3\2\2\2\34\u0106\3\2\2\2\36\u0114\3\2\2")
        buf.write('\2 \u0116\3\2\2\2"\u011a\3\2\2\2$\u011c\3\2\2\2&\u011e')
        buf.write("\3\2\2\2(\u0162\3\2\2\2*\u017e\3\2\2\2,\u019a\3\2\2\2")
        buf.write(".\u01c2\3\2\2\2\60\u01e6\3\2\2\2\62\u01e8\3\2\2\2\64\u01f0")
        buf.write("\3\2\2\2\66\u0206\3\2\2\28\u0208\3\2\2\2:\u021b\3\2\2")
        buf.write("\2<\u0220\3\2\2\2>\u0222\3\2\2\2@\u022c\3\2\2\2B\u0231")
        buf.write("\3\2\2\2D\u0235\3\2\2\2F\u024d\3\2\2\2H\u0252\3\2\2\2")
        buf.write("J\u025f\3\2\2\2L\u0264\3\2\2\2N\u026c\3\2\2\2P\u0273\3")
        buf.write("\2\2\2R\u0275\3\2\2\2T\u027a\3\2\2\2V\u027f\3\2\2\2X\u0286")
        buf.write("\3\2\2\2Z\u0296\3\2\2\2\\\u02c9\3\2\2\2^\u02fd\3\2\2\2")
        buf.write("`\u0313\3\2\2\2b\u0315\3\2\2\2d\u0317\3\2\2\2f\u031a\3")
        buf.write("\2\2\2hi\5^\60\2ij\7\2\2\3j\3\3\2\2\2km\5\6\4\2lk\3\2")
        buf.write("\2\2mp\3\2\2\2nl\3\2\2\2no\3\2\2\2oq\3\2\2\2pn\3\2\2\2")
        buf.write("qr\5\b\5\2rs\7\2\2\3s\5\3\2\2\2tu\7\4\2\2uv\t\2\2\2vw")
        buf.write("\7J\2\2wx\7C\2\2xy\5Z.\2yz\7-\2\2z\7\3\2\2\2{}\7\b\2\2")
        buf.write("|{\3\2\2\2|}\3\2\2\2}~\3\2\2\2~\177\7\t\2\2\177\u0082")
        buf.write("\7J\2\2\u0080\u0081\7\7\2\2\u0081\u0083\7K\2\2\u0082\u0080")
        buf.write("\3\2\2\2\u0082\u0083\3\2\2\2\u0083\u0084\3\2\2\2\u0084")
        buf.write("\u0097\7-\2\2\u0085\u0087\7\b\2\2\u0086\u0085\3\2\2\2")
        buf.write("\u0086\u0087\3\2\2\2\u0087\u0088\3\2\2\2\u0088\u0089\7")
        buf.write("\t\2\2\u0089\u008c\7J\2\2\u008a\u008b\7\7\2\2\u008b\u008d")
        buf.write("\7K\2\2\u008c\u008a\3\2\2\2\u008c\u008d\3\2\2\2\u008d")
        buf.write("\u008e\3\2\2\2\u008e\u0092\7/\2\2\u008f\u0091\5J&\2\u0090")
        buf.write("\u008f\3\2\2\2\u0091\u0094\3\2\2\2\u0092\u0090\3\2\2\2")
        buf.write("\u0092\u0093\3\2\2\2\u0093\u0095\3\2\2\2\u0094\u0092\3")
        buf.write("\2\2\2\u0095\u0097\7\60\2\2\u0096|\3\2\2\2\u0096\u0086")
        buf.write("\3\2\2\2\u0097\t\3\2\2\2\u0098\u0099\7\37\2\2\u0099\u009a")
        buf.write("\7,\2\2\u009a\u009c\7J\2\2\u009b\u009d\5\f\7\2\u009c\u009b")
        buf.write("\3\2\2\2\u009c\u009d\3\2\2\2\u009d\u00a4\3\2\2\2\u009e")
        buf.write("\u00a5\7-\2\2\u009f\u00a0\7\21\2\2\u00a0\u00a1\7/\2\2")
        buf.write("\u00a1\u00a2\5H%\2\u00a2\u00a3\7\60\2\2\u00a3\u00a5\3")
        buf.write("\2\2\2\u00a4\u009e\3\2\2\2\u00a4\u009f\3\2\2\2\u00a5\u00c3")
        buf.write("\3\2\2\2\u00a6\u00a7\7J\2\2\u00a7\u00a8\7,\2\2\u00a8\u00aa")
        buf.write("\7J\2\2\u00a9\u00ab\5\24\13\2\u00aa\u00a9\3\2\2\2\u00aa")
        buf.write("\u00ab\3\2\2\2\u00ab\u00b2\3\2\2\2\u00ac\u00b3\7-\2\2")
        buf.write("\u00ad\u00ae\7\21\2\2\u00ae\u00af\7/\2\2\u00af\u00b0\5")
        buf.write("H%\2\u00b0\u00b1\7\60\2\2\u00b1\u00b3\3\2\2\2\u00b2\u00ac")
        buf.write("\3\2\2\2\u00b2\u00ad\3\2\2\2\u00b3\u00c3\3\2\2\2\u00b4")
        buf.write("\u00b5\7J\2\2\u00b5\u00b6\7,\2\2\u00b6\u00b8\7\37\2\2")
        buf.write("\u00b7\u00b9\5\24\13\2\u00b8\u00b7\3\2\2\2\u00b8\u00b9")
        buf.write("\3\2\2\2\u00b9\u00c0\3\2\2\2\u00ba\u00c1\7-\2\2\u00bb")
        buf.write("\u00bc\7\21\2\2\u00bc\u00bd\7/\2\2\u00bd\u00be\5H%\2\u00be")
        buf.write("\u00bf\7\60\2\2\u00bf\u00c1\3\2\2\2\u00c0\u00ba\3\2\2")
        buf.write("\2\u00c0\u00bb\3\2\2\2\u00c1\u00c3\3\2\2\2\u00c2\u0098")
        buf.write("\3\2\2\2\u00c2\u00a6\3\2\2\2\u00c2\u00b4\3\2\2\2\u00c3")
        buf.write("\13\3\2\2\2\u00c4\u00c5\7+\2\2\u00c5\u00cf\5\16\b\2\u00c6")
        buf.write("\u00c7\7\66\2\2\u00c7\u00c8\7\22\2\2\u00c8\u00c9\7\61")
        buf.write("\2\2\u00c9\u00ca\5^\60\2\u00ca\u00cb\7\62\2\2\u00cb\u00cf")
        buf.write("\3\2\2\2\u00cc\u00cd\7\66\2\2\u00cd\u00cf\5\36\20\2\u00ce")
        buf.write("\u00c4\3\2\2\2\u00ce\u00c6\3\2\2\2\u00ce\u00cc\3\2\2\2")
        buf.write("\u00cf\r\3\2\2\2\u00d0\u00d2\5\20\t\2\u00d1\u00d0\3\2")
        buf.write("\2\2\u00d2\u00d5\3\2\2\2\u00d3\u00d1\3\2\2\2\u00d3\u00d4")
        buf.write("\3\2\2\2\u00d4\u00d6\3\2\2\2\u00d5\u00d3\3\2\2\2\u00d6")
        buf.write("\u00db\5$\23\2\u00d7\u00d8\7;\2\2\u00d8\u00da\5\22\n\2")
        buf.write("\u00d9\u00d7\3\2\2\2\u00da\u00dd\3\2\2\2\u00db\u00d9\3")
        buf.write("\2\2\2\u00db\u00dc\3\2\2\2\u00dc\17\3\2\2\2\u00dd\u00db")
        buf.write("\3\2\2\2\u00de\u00df\5&\24\2\u00df\u00e0\7;\2\2\u00e0")
        buf.write("\21\3\2\2\2\u00e1\u00e4\5$\23\2\u00e2\u00e4\5&\24\2\u00e3")
        buf.write("\u00e1\3\2\2\2\u00e3\u00e2\3\2\2\2\u00e4\23\3\2\2\2\u00e5")
        buf.write("\u00e6\7+\2\2\u00e6\u00f0\5\26\f\2\u00e7\u00e8\7\66\2")
        buf.write("\2\u00e8\u00e9\7\22\2\2\u00e9\u00ea\7\61\2\2\u00ea\u00eb")
        buf.write("\5^\60\2\u00eb\u00ec\7\62\2\2\u00ec\u00f0\3\2\2\2\u00ed")
        buf.write("\u00ee\7\66\2\2\u00ee\u00f0\5\36\20\2\u00ef\u00e5\3\2")
        buf.write("\2\2\u00ef\u00e7\3\2\2\2\u00ef\u00ed\3\2\2\2\u00f0\25")
        buf.write("\3\2\2\2\u00f1\u00f3\5\30\r\2\u00f2\u00f1\3\2\2\2\u00f3")
        buf.write("\u00f6\3\2\2\2\u00f4\u00f2\3\2\2\2\u00f4\u00f5\3\2\2\2")
        buf.write("\u00f5\u00f7\3\2\2\2\u00f6\u00f4\3\2\2\2\u00f7\u00fc\5")
        buf.write("\34\17\2\u00f8\u00f9\7;\2\2\u00f9\u00fb\5\32\16\2\u00fa")
        buf.write("\u00f8\3\2\2\2\u00fb\u00fe\3\2\2\2\u00fc\u00fa\3\2\2\2")
        buf.write("\u00fc\u00fd\3\2\2\2\u00fd\27\3\2\2\2\u00fe\u00fc\3\2")
        buf.write("\2\2\u00ff\u0100\5&\24\2\u0100\u0101\7;\2\2\u0101\31\3")
        buf.write("\2\2\2\u0102\u0105\5\34\17\2\u0103\u0105\5&\24\2\u0104")
        buf.write("\u0102\3\2\2\2\u0104\u0103\3\2\2\2\u0105\33\3\2\2\2\u0106")
        buf.write("\u0107\7J\2\2\u0107\35\3\2\2\2\u0108\u0115\5 \21\2\u0109")
        buf.write('\u010a\5"\22\2\u010a\u010b\7;\2\2\u010b\u0110\5"\22')
        buf.write('\2\u010c\u010d\7;\2\2\u010d\u010f\5"\22\2\u010e\u010c')
        buf.write("\3\2\2\2\u010f\u0112\3\2\2\2\u0110\u010e\3\2\2\2\u0110")
        buf.write("\u0111\3\2\2\2\u0111\u0115\3\2\2\2\u0112\u0110\3\2\2\2")
        buf.write("\u0113\u0115\5$\23\2\u0114\u0108\3\2\2\2\u0114\u0109\3")
        buf.write("\2\2\2\u0114\u0113\3\2\2\2\u0115\37\3\2\2\2\u0116\u0117")
        buf.write("\5&\24\2\u0117!\3\2\2\2\u0118\u011b\5$\23\2\u0119\u011b")
        buf.write("\5&\24\2\u011a\u0118\3\2\2\2\u011a\u0119\3\2\2\2\u011b")
        buf.write("#\3\2\2\2\u011c\u011d\5f\64\2\u011d%\3\2\2\2\u011e\u011f")
        buf.write("\7\61\2\2\u011f\u0120\5^\60\2\u0120\u0121\7\62\2\2\u0121")
        buf.write("'\3\2\2\2\u0122\u0123\7:\2\2\u0123\u0124\7J\2\2\u0124")
        buf.write("\u0125\7,\2\2\u0125\u0130\7J\2\2\u0126\u0127\7+\2\2\u0127")
        buf.write("\u0131\7J\2\2\u0128\u0129\7\66\2\2\u0129\u0131\5f\64\2")
        buf.write("\u012a\u012b\7\66\2\2\u012b\u012c\7\22\2\2\u012c\u012d")
        buf.write("\7\61\2\2\u012d\u012e\5^\60\2\u012e\u012f\7\62\2\2\u012f")
        buf.write("\u0131\3\2\2\2\u0130\u0126\3\2\2\2\u0130\u0128\3\2\2\2")
        buf.write("\u0130\u012a\3\2\2\2\u0130\u0131\3\2\2\2\u0131\u0132\3")
        buf.write("\2\2\2\u0132\u0163\7-\2\2\u0133\u0134\7:\2\2\u0134\u0135")
        buf.write("\7J\2\2\u0135\u0136\7,\2\2\u0136\u0141\7\37\2\2\u0137")
        buf.write("\u0138\7+\2\2\u0138\u0142\7J\2\2\u0139\u013a\7\66\2\2")
        buf.write("\u013a\u0142\5f\64\2\u013b\u013c\7\66\2\2\u013c\u013d")
        buf.write("\7\22\2\2\u013d\u013e\7\61\2\2\u013e\u013f\5^\60\2\u013f")
        buf.write("\u0140\7\62\2\2\u0140\u0142\3\2\2\2\u0141\u0137\3\2\2")
        buf.write("\2\u0141\u0139\3\2\2\2\u0141\u013b\3\2\2\2\u0141\u0142")
        buf.write("\3\2\2\2\u0142\u0143\3\2\2\2\u0143\u0163\7-\2\2\u0144")
        buf.write("\u0145\7:\2\2\u0145\u0146\79\2\2\u0146\u0147\7,\2\2\u0147")
        buf.write("\u0150\7J\2\2\u0148\u0149\t\3\2\2\u0149\u0151\5f\64\2")
        buf.write("\u014a\u014b\7\66\2\2\u014b\u014c\7\22\2\2\u014c\u014d")
        buf.write("\7\61\2\2\u014d\u014e\5^\60\2\u014e\u014f\7\62\2\2\u014f")
        buf.write("\u0151\3\2\2\2\u0150\u0148\3\2\2\2\u0150\u014a\3\2\2\2")
        buf.write("\u0150\u0151\3\2\2\2\u0151\u0152\3\2\2\2\u0152\u0163\7")
        buf.write("-\2\2\u0153\u0154\7:\2\2\u0154\u0155\79\2\2\u0155\u0156")
        buf.write("\7,\2\2\u0156\u015f\7\37\2\2\u0157\u0158\t\3\2\2\u0158")
        buf.write("\u0160\5f\64\2\u0159\u015a\7\66\2\2\u015a\u015b\7\22\2")
        buf.write("\2\u015b\u015c\7\61\2\2\u015c\u015d\5^\60\2\u015d\u015e")
        buf.write("\7\62\2\2\u015e\u0160\3\2\2\2\u015f\u0157\3\2\2\2\u015f")
        buf.write("\u0159\3\2\2\2\u015f\u0160\3\2\2\2\u0160\u0161\3\2\2\2")
        buf.write("\u0161\u0163\7-\2\2\u0162\u0122\3\2\2\2\u0162\u0133\3")
        buf.write("\2\2\2\u0162\u0144\3\2\2\2\u0162\u0153\3\2\2\2\u0163)")
        buf.write("\3\2\2\2\u0164\u0166\7\n\2\2\u0165\u0167\7J\2\2\u0166")
        buf.write("\u0165\3\2\2\2\u0166\u0167\3\2\2\2\u0167\u0168\3\2\2\2")
        buf.write("\u0168\u0169\7/\2\2\u0169\u016a\5H%\2\u016a\u016b\7\60")
        buf.write("\2\2\u016b\u017f\3\2\2\2\u016c\u016d\7\n\2\2\u016d\u016e")
        buf.write("\7\17\2\2\u016e\u016f\7J\2\2\u016f\u017f\7-\2\2\u0170")
        buf.write("\u0171\7\n\2\2\u0171\u0173\7\17\2\2\u0172\u0174\7J\2\2")
        buf.write("\u0173\u0172\3\2\2\2\u0173\u0174\3\2\2\2\u0174\u0175\3")
        buf.write("\2\2\2\u0175\u017f\7L\2\2\u0176\u0178\7\n\2\2\u0177\u0179")
        buf.write("\7J\2\2\u0178\u0177\3\2\2\2\u0178\u0179\3\2\2\2\u0179")
        buf.write("\u017a\3\2\2\2\u017a\u017b\7\20\2\2\u017b\u017c\5f\64")
        buf.write("\2\u017c\u017d\7-\2\2\u017d\u017f\3\2\2\2\u017e\u0164")
        buf.write("\3\2\2\2\u017e\u016c\3\2\2\2\u017e\u0170\3\2\2\2\u017e")
        buf.write("\u0176\3\2\2\2\u017f+\3\2\2\2\u0180\u0182\7\13\2\2\u0181")
        buf.write("\u0183\7J\2\2\u0182\u0181\3\2\2\2\u0182\u0183\3\2\2\2")
        buf.write("\u0183\u0184\3\2\2\2\u0184\u0185\7/\2\2\u0185\u0186\5")
        buf.write("H%\2\u0186\u0187\7\60\2\2\u0187\u019b\3\2\2\2\u0188\u0189")
        buf.write("\7\13\2\2\u0189\u018a\7\17\2\2\u018a\u018b\7J\2\2\u018b")
        buf.write("\u019b\7-\2\2\u018c\u018d\7\13\2\2\u018d\u018f\7\17\2")
        buf.write("\2\u018e\u0190\7J\2\2\u018f\u018e\3\2\2\2\u018f\u0190")
        buf.write("\3\2\2\2\u0190\u0191\3\2\2\2\u0191\u019b\7L\2\2\u0192")
        buf.write("\u0194\7\13\2\2\u0193\u0195\7J\2\2\u0194\u0193\3\2\2\2")
        buf.write("\u0194\u0195\3\2\2\2\u0195\u0196\3\2\2\2\u0196\u0197\7")
        buf.write("\20\2\2\u0197\u0198\5f\64\2\u0198\u0199\7-\2\2\u0199\u019b")
        buf.write("\3\2\2\2\u019a\u0180\3\2\2\2\u019a\u0188\3\2\2\2\u019a")
        buf.write("\u018c\3\2\2\2\u019a\u0192\3\2\2\2\u019b-\3\2\2\2\u019c")
        buf.write("\u019e\7\f\2\2\u019d\u019f\t\4\2\2\u019e\u019d\3\2\2\2")
        buf.write("\u019e\u019f\3\2\2\2\u019f\u01a1\3\2\2\2\u01a0\u01a2\7")
        buf.write("J\2\2\u01a1\u01a0\3\2\2\2\u01a1\u01a2\3\2\2\2\u01a2\u01a3")
        buf.write("\3\2\2\2\u01a3\u01a4\7/\2\2\u01a4\u01a5\5H%\2\u01a5\u01a6")
        buf.write("\7\60\2\2\u01a6\u01c3\3\2\2\2\u01a7\u01a9\7\f\2\2\u01a8")
        buf.write("\u01aa\t\4\2\2\u01a9\u01a8\3\2\2\2\u01a9\u01aa\3\2\2\2")
        buf.write("\u01aa\u01ab\3\2\2\2\u01ab\u01ac\7\17\2\2\u01ac\u01ad")
        buf.write("\7J\2\2\u01ad\u01c3\7-\2\2\u01ae\u01b0\7\f\2\2\u01af\u01b1")
        buf.write("\t\4\2\2\u01b0\u01af\3\2\2\2\u01b0\u01b1\3\2\2\2\u01b1")
        buf.write("\u01b2\3\2\2\2\u01b2\u01b4\7\17\2\2\u01b3\u01b5\7J\2\2")
        buf.write("\u01b4\u01b3\3\2\2\2\u01b4\u01b5\3\2\2\2\u01b5\u01b6\3")
        buf.write("\2\2\2\u01b6\u01c3\7L\2\2\u01b7\u01b9\7\f\2\2\u01b8\u01ba")
        buf.write("\t\4\2\2\u01b9\u01b8\3\2\2\2\u01b9\u01ba\3\2\2\2\u01ba")
        buf.write("\u01bc\3\2\2\2\u01bb\u01bd\7J\2\2\u01bc\u01bb\3\2\2\2")
        buf.write("\u01bc\u01bd\3\2\2\2\u01bd\u01be\3\2\2\2\u01be\u01bf\7")
        buf.write("\20\2\2\u01bf\u01c0\5f\64\2\u01c0\u01c1\7-\2\2\u01c1\u01c3")
        buf.write("\3\2\2\2\u01c2\u019c\3\2\2\2\u01c2\u01a7\3\2\2\2\u01c2")
        buf.write("\u01ae\3\2\2\2\u01c2\u01b7\3\2\2\2\u01c3/\3\2\2\2\u01c4")
        buf.write("\u01c5\7!\2\2\u01c5\u01c6\7\f\2\2\u01c6\u01c8\t\4\2\2")
        buf.write("\u01c7\u01c9\7J\2\2\u01c8\u01c7\3\2\2\2\u01c8\u01c9\3")
        buf.write("\2\2\2\u01c9\u01ca\3\2\2\2\u01ca\u01cb\7/\2\2\u01cb\u01cc")
        buf.write("\5H%\2\u01cc\u01cd\7\60\2\2\u01cd\u01e7\3\2\2\2\u01ce")
        buf.write("\u01cf\7!\2\2\u01cf\u01d0\7\f\2\2\u01d0\u01d1\t\4\2\2")
        buf.write("\u01d1\u01d2\7\17\2\2\u01d2\u01d3\7J\2\2\u01d3\u01e7\7")
        buf.write("-\2\2\u01d4\u01d5\7!\2\2\u01d5\u01d6\7\f\2\2\u01d6\u01d7")
        buf.write("\t\4\2\2\u01d7\u01d9\7\17\2\2\u01d8\u01da\7J\2\2\u01d9")
        buf.write("\u01d8\3\2\2\2\u01d9\u01da\3\2\2\2\u01da\u01db\3\2\2\2")
        buf.write("\u01db\u01e7\7L\2\2\u01dc\u01dd\7!\2\2\u01dd\u01de\7\f")
        buf.write("\2\2\u01de\u01e0\t\4\2\2\u01df\u01e1\7J\2\2\u01e0\u01df")
        buf.write("\3\2\2\2\u01e0\u01e1\3\2\2\2\u01e1\u01e2\3\2\2\2\u01e2")
        buf.write("\u01e3\7\20\2\2\u01e3\u01e4\5f\64\2\u01e4\u01e5\7-\2\2")
        buf.write("\u01e5\u01e7\3\2\2\2\u01e6\u01c4\3\2\2\2\u01e6\u01ce\3")
        buf.write("\2\2\2\u01e6\u01d4\3\2\2\2\u01e6\u01dc\3\2\2\2\u01e7\61")
        buf.write("\3\2\2\2\u01e8\u01e9\7\5\2\2\u01e9\u01ec\7J\2\2\u01ea")
        buf.write("\u01eb\7\7\2\2\u01eb\u01ed\7K\2\2\u01ec\u01ea\3\2\2\2")
        buf.write("\u01ec\u01ed\3\2\2\2\u01ed\u01ee\3\2\2\2\u01ee\u01ef\7")
        buf.write("-\2\2\u01ef\63\3\2\2\2\u01f0\u01f1\7\3\2\2\u01f1\u01f2")
        buf.write("\7K\2\2\u01f2\u01f3\7\6\2\2\u01f3\u01f6\7J\2\2\u01f4\u01f5")
        buf.write("\7\7\2\2\u01f5\u01f7\7K\2\2\u01f6\u01f4\3\2\2\2\u01f6")
        buf.write("\u01f7\3\2\2\2\u01f7\u0201\3\2\2\2\u01f8\u01fc\7/\2\2")
        buf.write("\u01f9\u01fb\5\66\34\2\u01fa\u01f9\3\2\2\2\u01fb\u01fe")
        buf.write("\3\2\2\2\u01fc\u01fa\3\2\2\2\u01fc\u01fd\3\2\2\2\u01fd")
        buf.write("\u01ff\3\2\2\2\u01fe\u01fc\3\2\2\2\u01ff\u0202\7\60\2")
        buf.write("\2\u0200\u0202\7-\2\2\u0201\u01f8\3\2\2\2\u0201\u0200")
        buf.write("\3\2\2\2\u0202\65\3\2\2\2\u0203\u0207\58\35\2\u0204\u0207")
        buf.write("\5> \2\u0205\u0207\7-\2\2\u0206\u0203\3\2\2\2\u0206\u0204")
        buf.write("\3\2\2\2\u0206\u0205\3\2\2\2\u0207\67\3\2\2\2\u0208\u0209")
        buf.write("\7\4\2\2\u0209\u020a\5:\36\2\u020a\u020b\7,\2\2\u020b")
        buf.write("\u020c\5<\37\2\u020c\u020d\7-\2\2\u020d9\3\2\2\2\u020e")
        buf.write("\u021c\79\2\2\u020f\u0210\7/\2\2\u0210\u0215\7J\2\2\u0211")
        buf.write("\u0212\7.\2\2\u0212\u0214\7J\2\2\u0213\u0211\3\2\2\2\u0214")
        buf.write("\u0217\3\2\2\2\u0215\u0213\3\2\2\2\u0215\u0216\3\2\2\2")
        buf.write("\u0216\u0218\3\2\2\2\u0217\u0215\3\2\2\2\u0218\u021c\7")
        buf.write("\60\2\2\u0219\u021c\7\\\2\2\u021a\u021c\7J\2\2\u021b\u020e")
        buf.write("\3\2\2\2\u021b\u020f\3\2\2\2\u021b\u0219\3\2\2\2\u021b")
        buf.write("\u021a\3\2\2\2\u021c;\3\2\2\2\u021d\u0221\7J\2\2\u021e")
        buf.write("\u0221\7a\2\2\u021f\u0221\79\2\2\u0220\u021d\3\2\2\2\u0220")
        buf.write("\u021e\3\2\2\2\u0220\u021f\3\2\2\2\u0221=\3\2\2\2\u0222")
        buf.write("\u0223\7\5\2\2\u0223\u0224\5f\64\2\u0224\u0225\7,\2\2")
        buf.write("\u0225\u0228\5f\64\2\u0226\u0227\7\7\2\2\u0227\u0229\7")
        buf.write("K\2\2\u0228\u0226\3\2\2\2\u0228\u0229\3\2\2\2\u0229\u022a")
        buf.write("\3\2\2\2\u022a\u022b\7-\2\2\u022b?\3\2\2\2\u022c\u022d")
        buf.write("\7J\2\2\u022d\u022e\7C\2\2\u022e\u022f\5\\/\2\u022f\u0230")
        buf.write("\7-\2\2\u0230A\3\2\2\2\u0231\u0232\7/\2\2\u0232\u0233")
        buf.write("\5H%\2\u0233\u0234\7\60\2\2\u0234C\3\2\2\2\u0235\u0236")
        buf.write("\7\22\2\2\u0236\u0237\7\61\2\2\u0237\u0238\5^\60\2\u0238")
        buf.write('\u0239\7\62\2\2\u0239\u0243\5B"\2\u023a\u023b\7\23\2')
        buf.write("\2\u023b\u023c\7\22\2\2\u023c\u023d\7\61\2\2\u023d\u023e")
        buf.write('\5^\60\2\u023e\u023f\7\62\2\2\u023f\u0240\5B"\2\u0240')
        buf.write("\u0242\3\2\2\2\u0241\u023a\3\2\2\2\u0242\u0245\3\2\2\2")
        buf.write("\u0243\u0241\3\2\2\2\u0243\u0244\3\2\2\2\u0244\u0248\3")
        buf.write("\2\2\2\u0245\u0243\3\2\2\2\u0246\u0247\7\23\2\2\u0247")
        buf.write('\u0249\5B"\2\u0248\u0246\3\2\2\2\u0248\u0249\3\2\2\2')
        buf.write("\u0249E\3\2\2\2\u024a\u024e\5@!\2\u024b\u024e\5D#\2\u024c")
        buf.write("\u024e\7-\2\2\u024d\u024a\3\2\2\2\u024d\u024b\3\2\2\2")
        buf.write("\u024d\u024c\3\2\2\2\u024eG\3\2\2\2\u024f\u0251\5F$\2")
        buf.write("\u0250\u024f\3\2\2\2\u0251\u0254\3\2\2\2\u0252\u0250\3")
        buf.write("\2\2\2\u0252\u0253\3\2\2\2\u0253I\3\2\2\2\u0254\u0252")
        buf.write("\3\2\2\2\u0255\u0260\5\b\5\2\u0256\u0260\5\n\6\2\u0257")
        buf.write("\u0260\5(\25\2\u0258\u0260\5*\26\2\u0259\u0260\5.\30\2")
        buf.write("\u025a\u0260\5,\27\2\u025b\u0260\5\60\31\2\u025c\u0260")
        buf.write("\5\62\32\2\u025d\u0260\5\64\33\2\u025e\u0260\7-\2\2\u025f")
        buf.write("\u0255\3\2\2\2\u025f\u0256\3\2\2\2\u025f\u0257\3\2\2\2")
        buf.write("\u025f\u0258\3\2\2\2\u025f\u0259\3\2\2\2\u025f\u025a\3")
        buf.write("\2\2\2\u025f\u025b\3\2\2\2\u025f\u025c\3\2\2\2\u025f\u025d")
        buf.write("\3\2\2\2\u025f\u025e\3\2\2\2\u0260K\3\2\2\2\u0261\u0263")
        buf.write("\5V,\2\u0262\u0261\3\2\2\2\u0263\u0266\3\2\2\2\u0264\u0262")
        buf.write("\3\2\2\2\u0264\u0265\3\2\2\2\u0265\u0267\3\2\2\2\u0266")
        buf.write("\u0264\3\2\2\2\u0267\u0268\7\2\2\3\u0268M\3\2\2\2\u0269")
        buf.write("\u026b\5P)\2\u026a\u0269\3\2\2\2\u026b\u026e\3\2\2\2\u026c")
        buf.write("\u026a\3\2\2\2\u026c\u026d\3\2\2\2\u026d\u026f\3\2\2\2")
        buf.write("\u026e\u026c\3\2\2\2\u026f\u0270\7\2\2\3\u0270O\3\2\2")
        buf.write("\2\u0271\u0274\5R*\2\u0272\u0274\5T+\2\u0273\u0271\3\2")
        buf.write("\2\2\u0273\u0272\3\2\2\2\u0274Q\3\2\2\2\u0275\u0276\7")
        buf.write("J\2\2\u0276\u0277\7*\2\2\u0277\u0278\5Z.\2\u0278\u0279")
        buf.write("\7-\2\2\u0279S\3\2\2\2\u027a\u027b\7J\2\2\u027b\u027c")
        buf.write("\7C\2\2\u027c\u027d\5Z.\2\u027d\u027e\7-\2\2\u027eU\3")
        buf.write("\2\2\2\u027f\u0280\7J\2\2\u0280\u0281\7*\2\2\u0281\u0282")
        buf.write("\5\\/\2\u0282\u0283\7-\2\2\u0283W\3\2\2\2\u0284\u0287")
        buf.write("\5\\/\2\u0285\u0287\5^\60\2\u0286\u0284\3\2\2\2\u0286")
        buf.write("\u0285\3\2\2\2\u0287Y\3\2\2\2\u0288\u0289\b.\1\2\u0289")
        buf.write("\u028a\7\63\2\2\u028a\u028b\5Z.\2\u028b\u028c\7\64\2\2")
        buf.write("\u028c\u0297\3\2\2\2\u028d\u0297\5`\61\2\u028e\u0297\5")
        buf.write("d\63\2\u028f\u0290\t\5\2\2\u0290\u0297\5Z.\13\u0291\u0292")
        buf.write("\7I\2\2\u0292\u0293\7\63\2\2\u0293\u0294\5Z.\2\u0294\u0295")
        buf.write("\7\64\2\2\u0295\u0297\3\2\2\2\u0296\u0288\3\2\2\2\u0296")
        buf.write("\u028d\3\2\2\2\u0296\u028e\3\2\2\2\u0296\u028f\3\2\2\2")
        buf.write("\u0296\u0291\3\2\2\2\u0297\u02af\3\2\2\2\u0298\u0299\f")
        buf.write("\n\2\2\u0299\u029a\7 \2\2\u029a\u02ae\5Z.\n\u029b\u029c")
        buf.write("\f\t\2\2\u029c\u029d\t\6\2\2\u029d\u02ae\5Z.\n\u029e\u029f")
        buf.write("\f\b\2\2\u029f\u02a0\t\5\2\2\u02a0\u02ae\5Z.\t\u02a1\u02a2")
        buf.write("\f\7\2\2\u02a2\u02a3\t\7\2\2\u02a3\u02ae\5Z.\b\u02a4\u02a5")
        buf.write("\f\6\2\2\u02a5\u02a6\7>\2\2\u02a6\u02ae\5Z.\7\u02a7\u02a8")
        buf.write("\f\5\2\2\u02a8\u02a9\7?\2\2\u02a9\u02ae\5Z.\6\u02aa\u02ab")
        buf.write("\f\4\2\2\u02ab\u02ac\7@\2\2\u02ac\u02ae\5Z.\5\u02ad\u0298")
        buf.write("\3\2\2\2\u02ad\u029b\3\2\2\2\u02ad\u029e\3\2\2\2\u02ad")
        buf.write("\u02a1\3\2\2\2\u02ad\u02a4\3\2\2\2\u02ad\u02a7\3\2\2\2")
        buf.write("\u02ad\u02aa\3\2\2\2\u02ae\u02b1\3\2\2\2\u02af\u02ad\3")
        buf.write("\2\2\2\u02af\u02b0\3\2\2\2\u02b0[\3\2\2\2\u02b1\u02af")
        buf.write("\3\2\2\2\u02b2\u02b3\b/\1\2\u02b3\u02b4\7\63\2\2\u02b4")
        buf.write("\u02b5\5\\/\2\u02b5\u02b6\7\64\2\2\u02b6\u02ca\3\2\2\2")
        buf.write("\u02b7\u02ca\5`\61\2\u02b8\u02ca\7J\2\2\u02b9\u02ca\5")
        buf.write("d\63\2\u02ba\u02bb\t\5\2\2\u02bb\u02ca\5\\/\f\u02bc\u02bd")
        buf.write("\7I\2\2\u02bd\u02be\7\63\2\2\u02be\u02bf\5\\/\2\u02bf")
        buf.write("\u02c0\7\64\2\2\u02c0\u02ca\3\2\2\2\u02c1\u02c2\7\63\2")
        buf.write("\2\u02c2\u02c3\5^\60\2\u02c3\u02c4\7\64\2\2\u02c4\u02c5")
        buf.write("\7\65\2\2\u02c5\u02c6\5\\/\2\u02c6\u02c7\7\66\2\2\u02c7")
        buf.write("\u02c8\5\\/\3\u02c8\u02ca\3\2\2\2\u02c9\u02b2\3\2\2\2")
        buf.write("\u02c9\u02b7\3\2\2\2\u02c9\u02b8\3\2\2\2\u02c9\u02b9\3")
        buf.write("\2\2\2\u02c9\u02ba\3\2\2\2\u02c9\u02bc\3\2\2\2\u02c9\u02c1")
        buf.write("\3\2\2\2\u02ca\u02e2\3\2\2\2\u02cb\u02cc\f\13\2\2\u02cc")
        buf.write("\u02cd\7 \2\2\u02cd\u02e1\5\\/\13\u02ce\u02cf\f\n\2\2")
        buf.write("\u02cf\u02d0\t\6\2\2\u02d0\u02e1\5\\/\13\u02d1\u02d2\f")
        buf.write("\t\2\2\u02d2\u02d3\t\5\2\2\u02d3\u02e1\5\\/\n\u02d4\u02d5")
        buf.write("\f\b\2\2\u02d5\u02d6\t\7\2\2\u02d6\u02e1\5\\/\t\u02d7")
        buf.write("\u02d8\f\7\2\2\u02d8\u02d9\7>\2\2\u02d9\u02e1\5\\/\b\u02da")
        buf.write("\u02db\f\6\2\2\u02db\u02dc\7?\2\2\u02dc\u02e1\5\\/\7\u02dd")
        buf.write("\u02de\f\5\2\2\u02de\u02df\7@\2\2\u02df\u02e1\5\\/\6\u02e0")
        buf.write("\u02cb\3\2\2\2\u02e0\u02ce\3\2\2\2\u02e0\u02d1\3\2\2\2")
        buf.write("\u02e0\u02d4\3\2\2\2\u02e0\u02d7\3\2\2\2\u02e0\u02da\3")
        buf.write("\2\2\2\u02e0\u02dd\3\2\2\2\u02e1\u02e4\3\2\2\2\u02e2\u02e0")
        buf.write("\3\2\2\2\u02e2\u02e3\3\2\2\2\u02e3]\3\2\2\2\u02e4\u02e2")
        buf.write("\3\2\2\2\u02e5\u02e6\b\60\1\2\u02e6\u02e7\7\63\2\2\u02e7")
        buf.write("\u02e8\5^\60\2\u02e8\u02e9\7\64\2\2\u02e9\u02fe\3\2\2")
        buf.write("\2\u02ea\u02fe\5b\62\2\u02eb\u02ec\t\b\2\2\u02ec\u02fe")
        buf.write("\5^\60\13\u02ed\u02ee\5\\/\2\u02ee\u02ef\t\t\2\2\u02ef")
        buf.write("\u02f0\5\\/\2\u02f0\u02fe\3\2\2\2\u02f1\u02f2\5\\/\2\u02f2")
        buf.write("\u02f3\t\n\2\2\u02f3\u02f4\5\\/\2\u02f4\u02fe\3\2\2\2")
        buf.write("\u02f5\u02f6\7\63\2\2\u02f6\u02f7\5^\60\2\u02f7\u02f8")
        buf.write("\7\64\2\2\u02f8\u02f9\7\65\2\2\u02f9\u02fa\5^\60\2\u02fa")
        buf.write("\u02fb\7\66\2\2\u02fb\u02fc\5^\60\3\u02fc\u02fe\3\2\2")
        buf.write("\2\u02fd\u02e5\3\2\2\2\u02fd\u02ea\3\2\2\2\u02fd\u02eb")
        buf.write("\3\2\2\2\u02fd\u02ed\3\2\2\2\u02fd\u02f1\3\2\2\2\u02fd")
        buf.write("\u02f5\3\2\2\2\u02fe\u0310\3\2\2\2\u02ff\u0300\f\b\2\2")
        buf.write("\u0300\u0301\t\13\2\2\u0301\u030f\5^\60\t\u0302\u0303")
        buf.write("\f\7\2\2\u0303\u0304\t\f\2\2\u0304\u030f\5^\60\b\u0305")
        buf.write("\u0306\f\6\2\2\u0306\u0307\7\36\2\2\u0307\u030f\5^\60")
        buf.write("\7\u0308\u0309\f\5\2\2\u0309\u030a\t\r\2\2\u030a\u030f")
        buf.write("\5^\60\6\u030b\u030c\f\4\2\2\u030c\u030d\t\16\2\2\u030d")
        buf.write("\u030f\5^\60\4\u030e\u02ff\3\2\2\2\u030e\u0302\3\2\2\2")
        buf.write("\u030e\u0305\3\2\2\2\u030e\u0308\3\2\2\2\u030e\u030b\3")
        buf.write("\2\2\2\u030f\u0312\3\2\2\2\u0310\u030e\3\2\2\2\u0310\u0311")
        buf.write("\3\2\2\2\u0311_\3\2\2\2\u0312\u0310\3\2\2\2\u0313\u0314")
        buf.write("\t\17\2\2\u0314a\3\2\2\2\u0315\u0316\t\20\2\2\u0316c\3")
        buf.write("\2\2\2\u0317\u0318\t\21\2\2\u0318e\3\2\2\2\u0319\u031b")
        buf.write("\78\2\2\u031a\u0319\3\2\2\2\u031a\u031b\3\2\2\2\u031b")
        buf.write("\u031c\3\2\2\2\u031c\u0321\7J\2\2\u031d\u031e\7\67\2\2")
        buf.write("\u031e\u0320\7J\2\2\u031f\u031d\3\2\2\2\u0320\u0323\3")
        buf.write("\2\2\2\u0321\u031f\3\2\2\2\u0321\u0322\3\2\2\2\u0322g")
        buf.write("\3\2\2\2\u0323\u0321\3\2\2\2Qn|\u0082\u0086\u008c\u0092")
        buf.write("\u0096\u009c\u00a4\u00aa\u00b2\u00b8\u00c0\u00c2\u00ce")
        buf.write("\u00d3\u00db\u00e3\u00ef\u00f4\u00fc\u0104\u0110\u0114")
        buf.write("\u011a\u0130\u0141\u0150\u015f\u0162\u0166\u0173\u0178")
        buf.write("\u017e\u0182\u018f\u0194\u019a\u019e\u01a1\u01a9\u01b0")
        buf.write("\u01b4\u01b9\u01bc\u01c2\u01c8\u01d9\u01e0\u01e6\u01ec")
        buf.write("\u01f6\u01fc\u0201\u0206\u0215\u021b\u0220\u0228\u0243")
        buf.write("\u0248\u024d\u0252\u025f\u0264\u026c\u0273\u0286\u0296")
        buf.write("\u02ad\u02af\u02c9\u02e0\u02e2\u02fd\u030e\u0310\u031a")
        buf.write("\u0321")
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
        "'implies'",
        "'iff'",
        "'xor'",
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
        "'=>'",
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
        "IMPLIES_KW",
        "IFF_KW",
        "XOR_KW",
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
        "IMPLIES",
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
    RULE_entry_combo_transition_trigger = 5
    RULE_entry_chain_combo_trigger = 6
    RULE_entry_chain_combo_leading_guard = 7
    RULE_entry_chain_combo_trigger_term = 8
    RULE_combo_transition_trigger = 9
    RULE_local_combo_trigger = 10
    RULE_local_combo_leading_guard = 11
    RULE_local_combo_trigger_term = 12
    RULE_local_combo_event_term = 13
    RULE_chain_combo_trigger = 14
    RULE_chain_combo_guard_alias = 15
    RULE_combo_trigger_term = 16
    RULE_combo_event_term = 17
    RULE_combo_guard_term = 18
    RULE_transition_force_definition = 19
    RULE_enter_definition = 20
    RULE_exit_definition = 21
    RULE_during_definition = 22
    RULE_during_aspect_definition = 23
    RULE_event_definition = 24
    RULE_import_statement = 25
    RULE_import_mapping_statement = 26
    RULE_import_def_mapping = 27
    RULE_import_def_selector = 28
    RULE_import_def_target_template = 29
    RULE_import_event_mapping = 30
    RULE_operation_assignment = 31
    RULE_operation_block = 32
    RULE_if_statement = 33
    RULE_operational_statement = 34
    RULE_operational_statement_set = 35
    RULE_state_inner_statement = 36
    RULE_operation_program = 37
    RULE_preamble_program = 38
    RULE_preamble_statement = 39
    RULE_initial_assignment = 40
    RULE_constant_definition = 41
    RULE_operational_assignment = 42
    RULE_generic_expression = 43
    RULE_init_expression = 44
    RULE_num_expression = 45
    RULE_cond_expression = 46
    RULE_num_literal = 47
    RULE_bool_literal = 48
    RULE_math_const = 49
    RULE_chain_id = 50

    ruleNames = [
        "condition",
        "state_machine_dsl",
        "def_assignment",
        "state_definition",
        "transition_definition",
        "entry_combo_transition_trigger",
        "entry_chain_combo_trigger",
        "entry_chain_combo_leading_guard",
        "entry_chain_combo_trigger_term",
        "combo_transition_trigger",
        "local_combo_trigger",
        "local_combo_leading_guard",
        "local_combo_trigger_term",
        "local_combo_event_term",
        "chain_combo_trigger",
        "chain_combo_guard_alias",
        "combo_trigger_term",
        "combo_event_term",
        "combo_guard_term",
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
    IMPLIES_KW = 26
    IFF_KW = 27
    XOR_KW = 28
    INIT_MARKER = 29
    POW = 30
    SHIFT_RIGHT = 31
    SHIFT_LEFT = 32
    LE = 33
    GE = 34
    EQ = 35
    NE = 36
    LOGICAL_AND = 37
    LOGICAL_OR = 38
    IMPLIES = 39
    DECLARE_ASSIGN = 40
    COLONCOLON = 41
    ARROW = 42
    SEMI = 43
    COMMA = 44
    LBRACE = 45
    RBRACE = 46
    LBRACK = 47
    RBRACK = 48
    LPAREN = 49
    RPAREN = 50
    QUESTION = 51
    COLON = 52
    DOT = 53
    SLASH = 54
    STAR = 55
    BANG = 56
    PLUS = 57
    MINUS = 58
    PERCENT = 59
    AMP = 60
    CARET = 61
    PIPE = 62
    LT = 63
    GT = 64
    ASSIGN = 65
    FLOAT = 66
    HEX_INT = 67
    INT = 68
    TRUE = 69
    FALSE = 70
    UFUNC_NAME = 71
    ID = 72
    STRING = 73
    MULTILINE_COMMENT = 74
    LINE_COMMENT = 75
    PYTHON_COMMENT = 76
    WS = 77
    IMPORT_HEADER_WS = 78
    IMPORT_HEADER_MULTILINE_COMMENT = 79
    IMPORT_HEADER_LINE_COMMENT = 80
    IMPORT_HEADER_PYTHON_COMMENT = 81
    IMPORT_BLOCK_WS = 82
    IMPORT_BLOCK_MULTILINE_COMMENT = 83
    IMPORT_BLOCK_LINE_COMMENT = 84
    IMPORT_BLOCK_PYTHON_COMMENT = 85
    IMPORT_DEF_SELECTOR_WS = 86
    IMPORT_DEF_SELECTOR_MULTILINE_COMMENT = 87
    IMPORT_DEF_SELECTOR_LINE_COMMENT = 88
    IMPORT_DEF_SELECTOR_PYTHON_COMMENT = 89
    IMPORT_DEF_SELECTOR_PATTERN = 90
    IMPORT_DEF_TARGET_WS = 91
    IMPORT_DEF_TARGET_MULTILINE_COMMENT = 92
    IMPORT_DEF_TARGET_LINE_COMMENT = 93
    IMPORT_DEF_TARGET_PYTHON_COMMENT = 94
    IMPORT_DEF_TARGET_TEMPLATE = 95

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
            self.state = 102
            self.cond_expression(0)
            self.state = 103
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
            self.state = 108
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.DEF:
                self.state = 105
                self.def_assignment()
                self.state = 110
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 111
            self.state_definition()
            self.state = 112
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
            self.state = 114
            self.match(GrammarParser.DEF)
            self.state = 115
            localctx.deftype = self._input.LT(1)
            _la = self._input.LA(1)
            if not (_la == GrammarParser.INT_TYPE or _la == GrammarParser.FLOAT_TYPE):
                localctx.deftype = self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 116
            self.match(GrammarParser.ID)
            self.state = 117
            self.match(GrammarParser.ASSIGN)
            self.state = 118
            self.init_expression(0)
            self.state = 119
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
            self.state = 148
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 6, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.LeafStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 122
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.PSEUDO:
                    self.state = 121
                    localctx.pseudo = self.match(GrammarParser.PSEUDO)

                self.state = 124
                self.match(GrammarParser.STATE)
                self.state = 125
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 128
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.NAMED:
                    self.state = 126
                    self.match(GrammarParser.NAMED)
                    self.state = 127
                    localctx.extra_name = self.match(GrammarParser.STRING)

                self.state = 130
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 2:
                localctx = GrammarParser.CompositeStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 132
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.PSEUDO:
                    self.state = 131
                    localctx.pseudo = self.match(GrammarParser.PSEUDO)

                self.state = 134
                self.match(GrammarParser.STATE)
                self.state = 135
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 138
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.NAMED:
                    self.state = 136
                    self.match(GrammarParser.NAMED)
                    self.state = 137
                    localctx.extra_name = self.match(GrammarParser.STRING)

                self.state = 140
                self.match(GrammarParser.LBRACE)
                self.state = 144
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
                    self.state = 141
                    self.state_inner_statement()
                    self.state = 146
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 147
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

        def combo_transition_trigger(self):
            return self.getTypedRuleContext(
                GrammarParser.Combo_transition_triggerContext, 0
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

        def entry_combo_transition_trigger(self):
            return self.getTypedRuleContext(
                GrammarParser.Entry_combo_transition_triggerContext, 0
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
            self.copyFrom(ctx)

        def ARROW(self):
            return self.getToken(GrammarParser.ARROW, 0)

        def INIT_MARKER(self):
            return self.getToken(GrammarParser.INIT_MARKER, 0)

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

        def combo_transition_trigger(self):
            return self.getTypedRuleContext(
                GrammarParser.Combo_transition_triggerContext, 0
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
            self.state = 192
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 13, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EntryTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 150
                self.match(GrammarParser.INIT_MARKER)
                self.state = 151
                self.match(GrammarParser.ARROW)
                self.state = 152
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 154
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON:
                    self.state = 153
                    self.entry_combo_transition_trigger()

                self.state = 162
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.SEMI]:
                    self.state = 156
                    self.match(GrammarParser.SEMI)
                    pass
                elif token in [GrammarParser.EFFECT]:
                    self.state = 157
                    self.match(GrammarParser.EFFECT)
                    self.state = 158
                    self.match(GrammarParser.LBRACE)
                    self.state = 159
                    self.operational_statement_set()
                    self.state = 160
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
                self.state = 164
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 165
                self.match(GrammarParser.ARROW)
                self.state = 166
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 168
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON:
                    self.state = 167
                    self.combo_transition_trigger()

                self.state = 176
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.SEMI]:
                    self.state = 170
                    self.match(GrammarParser.SEMI)
                    pass
                elif token in [GrammarParser.EFFECT]:
                    self.state = 171
                    self.match(GrammarParser.EFFECT)
                    self.state = 172
                    self.match(GrammarParser.LBRACE)
                    self.state = 173
                    self.operational_statement_set()
                    self.state = 174
                    self.match(GrammarParser.RBRACE)
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 3:
                localctx = GrammarParser.ExitTransitionDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 178
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 179
                self.match(GrammarParser.ARROW)
                self.state = 180
                self.match(GrammarParser.INIT_MARKER)
                self.state = 182
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON:
                    self.state = 181
                    self.combo_transition_trigger()

                self.state = 190
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.SEMI]:
                    self.state = 184
                    self.match(GrammarParser.SEMI)
                    pass
                elif token in [GrammarParser.EFFECT]:
                    self.state = 185
                    self.match(GrammarParser.EFFECT)
                    self.state = 186
                    self.match(GrammarParser.LBRACE)
                    self.state = 187
                    self.operational_statement_set()
                    self.state = 188
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

    class Entry_combo_transition_triggerContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def COLONCOLON(self):
            return self.getToken(GrammarParser.COLONCOLON, 0)

        def entry_chain_combo_trigger(self):
            return self.getTypedRuleContext(
                GrammarParser.Entry_chain_combo_triggerContext, 0
            )

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

        def chain_combo_trigger(self):
            return self.getTypedRuleContext(GrammarParser.Chain_combo_triggerContext, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_entry_combo_transition_trigger

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEntry_combo_transition_trigger"):
                listener.enterEntry_combo_transition_trigger(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEntry_combo_transition_trigger"):
                listener.exitEntry_combo_transition_trigger(self)

    def entry_combo_transition_trigger(self):

        localctx = GrammarParser.Entry_combo_transition_triggerContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 10, self.RULE_entry_combo_transition_trigger)
        try:
            self.state = 204
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 14, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 194
                self.match(GrammarParser.COLONCOLON)
                self.state = 195
                self.entry_chain_combo_trigger()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 196
                self.match(GrammarParser.COLON)
                self.state = 197
                self.match(GrammarParser.IF)
                self.state = 198
                self.match(GrammarParser.LBRACK)
                self.state = 199
                self.cond_expression(0)
                self.state = 200
                self.match(GrammarParser.RBRACK)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 202
                self.match(GrammarParser.COLON)
                self.state = 203
                self.chain_combo_trigger()
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Entry_chain_combo_triggerContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def combo_event_term(self):
            return self.getTypedRuleContext(GrammarParser.Combo_event_termContext, 0)

        def entry_chain_combo_leading_guard(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Entry_chain_combo_leading_guardContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Entry_chain_combo_leading_guardContext, i
                )

        def PLUS(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.PLUS)
            else:
                return self.getToken(GrammarParser.PLUS, i)

        def entry_chain_combo_trigger_term(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Entry_chain_combo_trigger_termContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Entry_chain_combo_trigger_termContext, i
                )

        def getRuleIndex(self):
            return GrammarParser.RULE_entry_chain_combo_trigger

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEntry_chain_combo_trigger"):
                listener.enterEntry_chain_combo_trigger(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEntry_chain_combo_trigger"):
                listener.exitEntry_chain_combo_trigger(self)

    def entry_chain_combo_trigger(self):

        localctx = GrammarParser.Entry_chain_combo_triggerContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 12, self.RULE_entry_chain_combo_trigger)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 209
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.LBRACK:
                self.state = 206
                self.entry_chain_combo_leading_guard()
                self.state = 211
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 212
            self.combo_event_term()
            self.state = 217
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.PLUS:
                self.state = 213
                self.match(GrammarParser.PLUS)
                self.state = 214
                self.entry_chain_combo_trigger_term()
                self.state = 219
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Entry_chain_combo_leading_guardContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def combo_guard_term(self):
            return self.getTypedRuleContext(GrammarParser.Combo_guard_termContext, 0)

        def PLUS(self):
            return self.getToken(GrammarParser.PLUS, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_entry_chain_combo_leading_guard

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEntry_chain_combo_leading_guard"):
                listener.enterEntry_chain_combo_leading_guard(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEntry_chain_combo_leading_guard"):
                listener.exitEntry_chain_combo_leading_guard(self)

    def entry_chain_combo_leading_guard(self):

        localctx = GrammarParser.Entry_chain_combo_leading_guardContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 14, self.RULE_entry_chain_combo_leading_guard)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 220
            self.combo_guard_term()
            self.state = 221
            self.match(GrammarParser.PLUS)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Entry_chain_combo_trigger_termContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def combo_event_term(self):
            return self.getTypedRuleContext(GrammarParser.Combo_event_termContext, 0)

        def combo_guard_term(self):
            return self.getTypedRuleContext(GrammarParser.Combo_guard_termContext, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_entry_chain_combo_trigger_term

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterEntry_chain_combo_trigger_term"):
                listener.enterEntry_chain_combo_trigger_term(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitEntry_chain_combo_trigger_term"):
                listener.exitEntry_chain_combo_trigger_term(self)

    def entry_chain_combo_trigger_term(self):

        localctx = GrammarParser.Entry_chain_combo_trigger_termContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 16, self.RULE_entry_chain_combo_trigger_term)
        try:
            self.state = 225
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.SLASH, GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 223
                self.combo_event_term()
                pass
            elif token in [GrammarParser.LBRACK]:
                self.enterOuterAlt(localctx, 2)
                self.state = 224
                self.combo_guard_term()
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

    class Combo_transition_triggerContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def COLONCOLON(self):
            return self.getToken(GrammarParser.COLONCOLON, 0)

        def local_combo_trigger(self):
            return self.getTypedRuleContext(GrammarParser.Local_combo_triggerContext, 0)

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

        def chain_combo_trigger(self):
            return self.getTypedRuleContext(GrammarParser.Chain_combo_triggerContext, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_combo_transition_trigger

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCombo_transition_trigger"):
                listener.enterCombo_transition_trigger(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCombo_transition_trigger"):
                listener.exitCombo_transition_trigger(self)

    def combo_transition_trigger(self):

        localctx = GrammarParser.Combo_transition_triggerContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 18, self.RULE_combo_transition_trigger)
        try:
            self.state = 237
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 18, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 227
                self.match(GrammarParser.COLONCOLON)
                self.state = 228
                self.local_combo_trigger()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 229
                self.match(GrammarParser.COLON)
                self.state = 230
                self.match(GrammarParser.IF)
                self.state = 231
                self.match(GrammarParser.LBRACK)
                self.state = 232
                self.cond_expression(0)
                self.state = 233
                self.match(GrammarParser.RBRACK)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 235
                self.match(GrammarParser.COLON)
                self.state = 236
                self.chain_combo_trigger()
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Local_combo_triggerContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def local_combo_event_term(self):
            return self.getTypedRuleContext(
                GrammarParser.Local_combo_event_termContext, 0
            )

        def local_combo_leading_guard(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Local_combo_leading_guardContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Local_combo_leading_guardContext, i
                )

        def PLUS(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.PLUS)
            else:
                return self.getToken(GrammarParser.PLUS, i)

        def local_combo_trigger_term(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Local_combo_trigger_termContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Local_combo_trigger_termContext, i
                )

        def getRuleIndex(self):
            return GrammarParser.RULE_local_combo_trigger

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLocal_combo_trigger"):
                listener.enterLocal_combo_trigger(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLocal_combo_trigger"):
                listener.exitLocal_combo_trigger(self)

    def local_combo_trigger(self):

        localctx = GrammarParser.Local_combo_triggerContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_local_combo_trigger)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 242
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.LBRACK:
                self.state = 239
                self.local_combo_leading_guard()
                self.state = 244
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 245
            self.local_combo_event_term()
            self.state = 250
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.PLUS:
                self.state = 246
                self.match(GrammarParser.PLUS)
                self.state = 247
                self.local_combo_trigger_term()
                self.state = 252
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Local_combo_leading_guardContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def combo_guard_term(self):
            return self.getTypedRuleContext(GrammarParser.Combo_guard_termContext, 0)

        def PLUS(self):
            return self.getToken(GrammarParser.PLUS, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_local_combo_leading_guard

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLocal_combo_leading_guard"):
                listener.enterLocal_combo_leading_guard(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLocal_combo_leading_guard"):
                listener.exitLocal_combo_leading_guard(self)

    def local_combo_leading_guard(self):

        localctx = GrammarParser.Local_combo_leading_guardContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 22, self.RULE_local_combo_leading_guard)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 253
            self.combo_guard_term()
            self.state = 254
            self.match(GrammarParser.PLUS)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Local_combo_trigger_termContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def local_combo_event_term(self):
            return self.getTypedRuleContext(
                GrammarParser.Local_combo_event_termContext, 0
            )

        def combo_guard_term(self):
            return self.getTypedRuleContext(GrammarParser.Combo_guard_termContext, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_local_combo_trigger_term

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLocal_combo_trigger_term"):
                listener.enterLocal_combo_trigger_term(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLocal_combo_trigger_term"):
                listener.exitLocal_combo_trigger_term(self)

    def local_combo_trigger_term(self):

        localctx = GrammarParser.Local_combo_trigger_termContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 24, self.RULE_local_combo_trigger_term)
        try:
            self.state = 258
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 256
                self.local_combo_event_term()
                pass
            elif token in [GrammarParser.LBRACK]:
                self.enterOuterAlt(localctx, 2)
                self.state = 257
                self.combo_guard_term()
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

    class Local_combo_event_termContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ID(self):
            return self.getToken(GrammarParser.ID, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_local_combo_event_term

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterLocal_combo_event_term"):
                listener.enterLocal_combo_event_term(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitLocal_combo_event_term"):
                listener.exitLocal_combo_event_term(self)

    def local_combo_event_term(self):

        localctx = GrammarParser.Local_combo_event_termContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 26, self.RULE_local_combo_event_term)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 260
            self.match(GrammarParser.ID)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Chain_combo_triggerContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def chain_combo_guard_alias(self):
            return self.getTypedRuleContext(
                GrammarParser.Chain_combo_guard_aliasContext, 0
            )

        def combo_trigger_term(self, i: int = None):
            if i is None:
                return self.getTypedRuleContexts(
                    GrammarParser.Combo_trigger_termContext
                )
            else:
                return self.getTypedRuleContext(
                    GrammarParser.Combo_trigger_termContext, i
                )

        def PLUS(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.PLUS)
            else:
                return self.getToken(GrammarParser.PLUS, i)

        def combo_event_term(self):
            return self.getTypedRuleContext(GrammarParser.Combo_event_termContext, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_chain_combo_trigger

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterChain_combo_trigger"):
                listener.enterChain_combo_trigger(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitChain_combo_trigger"):
                listener.exitChain_combo_trigger(self)

    def chain_combo_trigger(self):

        localctx = GrammarParser.Chain_combo_triggerContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_chain_combo_trigger)
        self._la = 0  # Token type
        try:
            self.state = 274
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 23, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 262
                self.chain_combo_guard_alias()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 263
                self.combo_trigger_term()
                self.state = 264
                self.match(GrammarParser.PLUS)
                self.state = 265
                self.combo_trigger_term()
                self.state = 270
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == GrammarParser.PLUS:
                    self.state = 266
                    self.match(GrammarParser.PLUS)
                    self.state = 267
                    self.combo_trigger_term()
                    self.state = 272
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 273
                self.combo_event_term()
                pass

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Chain_combo_guard_aliasContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def combo_guard_term(self):
            return self.getTypedRuleContext(GrammarParser.Combo_guard_termContext, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_chain_combo_guard_alias

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterChain_combo_guard_alias"):
                listener.enterChain_combo_guard_alias(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitChain_combo_guard_alias"):
                listener.exitChain_combo_guard_alias(self)

    def chain_combo_guard_alias(self):

        localctx = GrammarParser.Chain_combo_guard_aliasContext(
            self, self._ctx, self.state
        )
        self.enterRule(localctx, 30, self.RULE_chain_combo_guard_alias)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 276
            self.combo_guard_term()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Combo_trigger_termContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def combo_event_term(self):
            return self.getTypedRuleContext(GrammarParser.Combo_event_termContext, 0)

        def combo_guard_term(self):
            return self.getTypedRuleContext(GrammarParser.Combo_guard_termContext, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_combo_trigger_term

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCombo_trigger_term"):
                listener.enterCombo_trigger_term(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCombo_trigger_term"):
                listener.exitCombo_trigger_term(self)

    def combo_trigger_term(self):

        localctx = GrammarParser.Combo_trigger_termContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_combo_trigger_term)
        try:
            self.state = 280
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.SLASH, GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 278
                self.combo_event_term()
                pass
            elif token in [GrammarParser.LBRACK]:
                self.enterOuterAlt(localctx, 2)
                self.state = 279
                self.combo_guard_term()
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

    class Combo_event_termContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def chain_id(self):
            return self.getTypedRuleContext(GrammarParser.Chain_idContext, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_combo_event_term

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCombo_event_term"):
                listener.enterCombo_event_term(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCombo_event_term"):
                listener.exitCombo_event_term(self)

    def combo_event_term(self):

        localctx = GrammarParser.Combo_event_termContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_combo_event_term)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 282
            self.chain_id()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx

    class Combo_guard_termContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LBRACK(self):
            return self.getToken(GrammarParser.LBRACK, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def RBRACK(self):
            return self.getToken(GrammarParser.RBRACK, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_combo_guard_term

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCombo_guard_term"):
                listener.enterCombo_guard_term(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCombo_guard_term"):
                listener.exitCombo_guard_term(self)

    def combo_guard_term(self):

        localctx = GrammarParser.Combo_guard_termContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_combo_guard_term)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 284
            self.match(GrammarParser.LBRACK)
            self.state = 285
            self.cond_expression(0)
            self.state = 286
            self.match(GrammarParser.RBRACK)
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
        self.enterRule(localctx, 38, self.RULE_transition_force_definition)
        self._la = 0  # Token type
        try:
            self.state = 352
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 29, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.NormalForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 288
                self.match(GrammarParser.BANG)
                self.state = 289
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 290
                self.match(GrammarParser.ARROW)
                self.state = 291
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 302
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 25, self._ctx)
                if la_ == 1:
                    self.state = 292
                    self.match(GrammarParser.COLONCOLON)
                    self.state = 293
                    localctx.from_id = self.match(GrammarParser.ID)

                elif la_ == 2:
                    self.state = 294
                    self.match(GrammarParser.COLON)
                    self.state = 295
                    self.chain_id()

                elif la_ == 3:
                    self.state = 296
                    self.match(GrammarParser.COLON)
                    self.state = 297
                    self.match(GrammarParser.IF)
                    self.state = 298
                    self.match(GrammarParser.LBRACK)
                    self.state = 299
                    self.cond_expression(0)
                    self.state = 300
                    self.match(GrammarParser.RBRACK)

                self.state = 304
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 2:
                localctx = GrammarParser.ExitForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 2)
                self.state = 305
                self.match(GrammarParser.BANG)
                self.state = 306
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 307
                self.match(GrammarParser.ARROW)
                self.state = 308
                self.match(GrammarParser.INIT_MARKER)
                self.state = 319
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 26, self._ctx)
                if la_ == 1:
                    self.state = 309
                    self.match(GrammarParser.COLONCOLON)
                    self.state = 310
                    localctx.from_id = self.match(GrammarParser.ID)

                elif la_ == 2:
                    self.state = 311
                    self.match(GrammarParser.COLON)
                    self.state = 312
                    self.chain_id()

                elif la_ == 3:
                    self.state = 313
                    self.match(GrammarParser.COLON)
                    self.state = 314
                    self.match(GrammarParser.IF)
                    self.state = 315
                    self.match(GrammarParser.LBRACK)
                    self.state = 316
                    self.cond_expression(0)
                    self.state = 317
                    self.match(GrammarParser.RBRACK)

                self.state = 321
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.NormalAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 3)
                self.state = 322
                self.match(GrammarParser.BANG)
                self.state = 323
                self.match(GrammarParser.STAR)
                self.state = 324
                self.match(GrammarParser.ARROW)
                self.state = 325
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 334
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 27, self._ctx)
                if la_ == 1:
                    self.state = 326
                    _la = self._input.LA(1)
                    if not (
                        _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON
                    ):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 327
                    self.chain_id()

                elif la_ == 2:
                    self.state = 328
                    self.match(GrammarParser.COLON)
                    self.state = 329
                    self.match(GrammarParser.IF)
                    self.state = 330
                    self.match(GrammarParser.LBRACK)
                    self.state = 331
                    self.cond_expression(0)
                    self.state = 332
                    self.match(GrammarParser.RBRACK)

                self.state = 336
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 4:
                localctx = GrammarParser.ExitAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 4)
                self.state = 337
                self.match(GrammarParser.BANG)
                self.state = 338
                self.match(GrammarParser.STAR)
                self.state = 339
                self.match(GrammarParser.ARROW)
                self.state = 340
                self.match(GrammarParser.INIT_MARKER)
                self.state = 349
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 28, self._ctx)
                if la_ == 1:
                    self.state = 341
                    _la = self._input.LA(1)
                    if not (
                        _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON
                    ):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 342
                    self.chain_id()

                elif la_ == 2:
                    self.state = 343
                    self.match(GrammarParser.COLON)
                    self.state = 344
                    self.match(GrammarParser.IF)
                    self.state = 345
                    self.match(GrammarParser.LBRACK)
                    self.state = 346
                    self.cond_expression(0)
                    self.state = 347
                    self.match(GrammarParser.RBRACK)

                self.state = 351
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
        self.enterRule(localctx, 40, self.RULE_enter_definition)
        self._la = 0  # Token type
        try:
            self.state = 380
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 33, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EnterOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 354
                self.match(GrammarParser.ENTER)
                self.state = 356
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 355
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 358
                self.match(GrammarParser.LBRACE)
                self.state = 359
                self.operational_statement_set()
                self.state = 360
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 362
                self.match(GrammarParser.ENTER)
                self.state = 363
                self.match(GrammarParser.ABSTRACT)
                self.state = 364
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 365
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 366
                self.match(GrammarParser.ENTER)
                self.state = 367
                self.match(GrammarParser.ABSTRACT)
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
                localctx = GrammarParser.EnterRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 372
                self.match(GrammarParser.ENTER)
                self.state = 374
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 373
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 376
                self.match(GrammarParser.REF)
                self.state = 377
                self.chain_id()
                self.state = 378
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
        self.enterRule(localctx, 42, self.RULE_exit_definition)
        self._la = 0  # Token type
        try:
            self.state = 408
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 37, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ExitOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 382
                self.match(GrammarParser.EXIT)
                self.state = 384
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 383
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 386
                self.match(GrammarParser.LBRACE)
                self.state = 387
                self.operational_statement_set()
                self.state = 388
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 390
                self.match(GrammarParser.EXIT)
                self.state = 391
                self.match(GrammarParser.ABSTRACT)
                self.state = 392
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 393
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 394
                self.match(GrammarParser.EXIT)
                self.state = 395
                self.match(GrammarParser.ABSTRACT)
                self.state = 397
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 396
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 399
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.ExitRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 400
                self.match(GrammarParser.EXIT)
                self.state = 402
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 401
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 404
                self.match(GrammarParser.REF)
                self.state = 405
                self.chain_id()
                self.state = 406
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
        self.enterRule(localctx, 44, self.RULE_during_definition)
        self._la = 0  # Token type
        try:
            self.state = 448
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 45, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.DuringOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 410
                self.match(GrammarParser.DURING)
                self.state = 412
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 411
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 415
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 414
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 417
                self.match(GrammarParser.LBRACE)
                self.state = 418
                self.operational_statement_set()
                self.state = 419
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 421
                self.match(GrammarParser.DURING)
                self.state = 423
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 422
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 425
                self.match(GrammarParser.ABSTRACT)
                self.state = 426
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 427
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 428
                self.match(GrammarParser.DURING)
                self.state = 430
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 429
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 432
                self.match(GrammarParser.ABSTRACT)
                self.state = 434
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 433
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 436
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.DuringRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 437
                self.match(GrammarParser.DURING)
                self.state = 439
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 438
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 442
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 441
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 444
                self.match(GrammarParser.REF)
                self.state = 445
                self.chain_id()
                self.state = 446
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
        self.enterRule(localctx, 46, self.RULE_during_aspect_definition)
        self._la = 0  # Token type
        try:
            self.state = 484
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 49, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.DuringAspectOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 450
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 451
                self.match(GrammarParser.DURING)
                self.state = 452
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 454
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 453
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 456
                self.match(GrammarParser.LBRACE)
                self.state = 457
                self.operational_statement_set()
                self.state = 458
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 460
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 461
                self.match(GrammarParser.DURING)
                self.state = 462
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 463
                self.match(GrammarParser.ABSTRACT)
                self.state = 464
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 465
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 466
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 467
                self.match(GrammarParser.DURING)
                self.state = 468
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 469
                self.match(GrammarParser.ABSTRACT)
                self.state = 471
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 470
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 473
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.DuringAspectRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 474
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 475
                self.match(GrammarParser.DURING)
                self.state = 476
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 478
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 477
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 480
                self.match(GrammarParser.REF)
                self.state = 481
                self.chain_id()
                self.state = 482
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
        self.enterRule(localctx, 48, self.RULE_event_definition)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 486
            self.match(GrammarParser.EVENT)
            self.state = 487
            localctx.event_name = self.match(GrammarParser.ID)
            self.state = 490
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.NAMED:
                self.state = 488
                self.match(GrammarParser.NAMED)
                self.state = 489
                localctx.extra_name = self.match(GrammarParser.STRING)

            self.state = 492
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
        self.enterRule(localctx, 50, self.RULE_import_statement)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 494
            self.match(GrammarParser.IMPORT)
            self.state = 495
            localctx.import_path = self.match(GrammarParser.STRING)
            self.state = 496
            self.match(GrammarParser.AS)
            self.state = 497
            localctx.state_alias = self.match(GrammarParser.ID)
            self.state = 500
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.NAMED:
                self.state = 498
                self.match(GrammarParser.NAMED)
                self.state = 499
                localctx.extra_name = self.match(GrammarParser.STRING)

            self.state = 511
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.LBRACE]:
                self.state = 502
                self.match(GrammarParser.LBRACE)
                self.state = 506
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
                    self.state = 503
                    self.import_mapping_statement()
                    self.state = 508
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 509
                self.match(GrammarParser.RBRACE)
                pass
            elif token in [GrammarParser.SEMI]:
                self.state = 510
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
        self.enterRule(localctx, 52, self.RULE_import_mapping_statement)
        try:
            self.state = 516
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.DEF]:
                self.enterOuterAlt(localctx, 1)
                self.state = 513
                self.import_def_mapping()
                pass
            elif token in [GrammarParser.EVENT]:
                self.enterOuterAlt(localctx, 2)
                self.state = 514
                self.import_event_mapping()
                pass
            elif token in [GrammarParser.SEMI]:
                self.enterOuterAlt(localctx, 3)
                self.state = 515
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
        self.enterRule(localctx, 54, self.RULE_import_def_mapping)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 518
            self.match(GrammarParser.DEF)
            self.state = 519
            self.import_def_selector()
            self.state = 520
            self.match(GrammarParser.ARROW)
            self.state = 521
            self.import_def_target_template()
            self.state = 522
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
        self.enterRule(localctx, 56, self.RULE_import_def_selector)
        self._la = 0  # Token type
        try:
            self.state = 537
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.STAR]:
                localctx = GrammarParser.ImportDefFallbackSelectorContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 524
                self.match(GrammarParser.STAR)
                pass
            elif token in [GrammarParser.LBRACE]:
                localctx = GrammarParser.ImportDefSetSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 525
                self.match(GrammarParser.LBRACE)
                self.state = 526
                localctx._ID = self.match(GrammarParser.ID)
                localctx.selector_items.append(localctx._ID)
                self.state = 531
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == GrammarParser.COMMA:
                    self.state = 527
                    self.match(GrammarParser.COMMA)
                    self.state = 528
                    localctx._ID = self.match(GrammarParser.ID)
                    localctx.selector_items.append(localctx._ID)
                    self.state = 533
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 534
                self.match(GrammarParser.RBRACE)
                pass
            elif token in [GrammarParser.IMPORT_DEF_SELECTOR_PATTERN]:
                localctx = GrammarParser.ImportDefPatternSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 535
                localctx.selector_pattern = self.match(
                    GrammarParser.IMPORT_DEF_SELECTOR_PATTERN
                )
                pass
            elif token in [GrammarParser.ID]:
                localctx = GrammarParser.ImportDefExactSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 536
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
        self.enterRule(localctx, 58, self.RULE_import_def_target_template)
        try:
            self.state = 542
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 539
                localctx.target_text = self.match(GrammarParser.ID)
                pass
            elif token in [GrammarParser.IMPORT_DEF_TARGET_TEMPLATE]:
                self.enterOuterAlt(localctx, 2)
                self.state = 540
                localctx.target_text = self.match(
                    GrammarParser.IMPORT_DEF_TARGET_TEMPLATE
                )
                pass
            elif token in [GrammarParser.STAR]:
                self.enterOuterAlt(localctx, 3)
                self.state = 541
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
        self.enterRule(localctx, 60, self.RULE_import_event_mapping)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 544
            self.match(GrammarParser.EVENT)
            self.state = 545
            localctx.source_event = self.chain_id()
            self.state = 546
            self.match(GrammarParser.ARROW)
            self.state = 547
            localctx.target_event = self.chain_id()
            self.state = 550
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.NAMED:
                self.state = 548
                self.match(GrammarParser.NAMED)
                self.state = 549
                localctx.extra_name = self.match(GrammarParser.STRING)

            self.state = 552
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
        self.enterRule(localctx, 62, self.RULE_operation_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 554
            self.match(GrammarParser.ID)
            self.state = 555
            self.match(GrammarParser.ASSIGN)
            self.state = 556
            self.num_expression(0)
            self.state = 557
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
        self.enterRule(localctx, 64, self.RULE_operation_block)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 559
            self.match(GrammarParser.LBRACE)
            self.state = 560
            self.operational_statement_set()
            self.state = 561
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
        self.enterRule(localctx, 66, self.RULE_if_statement)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 563
            self.match(GrammarParser.IF)
            self.state = 564
            self.match(GrammarParser.LBRACK)
            self.state = 565
            self.cond_expression(0)
            self.state = 566
            self.match(GrammarParser.RBRACK)
            self.state = 567
            self.operation_block()
            self.state = 577
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 59, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 568
                    self.match(GrammarParser.ELSE)
                    self.state = 569
                    self.match(GrammarParser.IF)
                    self.state = 570
                    self.match(GrammarParser.LBRACK)
                    self.state = 571
                    self.cond_expression(0)
                    self.state = 572
                    self.match(GrammarParser.RBRACK)
                    self.state = 573
                    self.operation_block()
                self.state = 579
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 59, self._ctx)

            self.state = 582
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.ELSE:
                self.state = 580
                self.match(GrammarParser.ELSE)
                self.state = 581
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
        self.enterRule(localctx, 68, self.RULE_operational_statement)
        try:
            self.state = 587
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 584
                self.operation_assignment()
                pass
            elif token in [GrammarParser.IF]:
                self.enterOuterAlt(localctx, 2)
                self.state = 585
                self.if_statement()
                pass
            elif token in [GrammarParser.SEMI]:
                self.enterOuterAlt(localctx, 3)
                self.state = 586
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
        self.enterRule(localctx, 70, self.RULE_operational_statement_set)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 592
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
                self.state = 589
                self.operational_statement()
                self.state = 594
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
        self.enterRule(localctx, 72, self.RULE_state_inner_statement)
        try:
            self.state = 605
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.PSEUDO, GrammarParser.STATE]:
                self.enterOuterAlt(localctx, 1)
                self.state = 595
                self.state_definition()
                pass
            elif token in [GrammarParser.INIT_MARKER, GrammarParser.ID]:
                self.enterOuterAlt(localctx, 2)
                self.state = 596
                self.transition_definition()
                pass
            elif token in [GrammarParser.BANG]:
                self.enterOuterAlt(localctx, 3)
                self.state = 597
                self.transition_force_definition()
                pass
            elif token in [GrammarParser.ENTER]:
                self.enterOuterAlt(localctx, 4)
                self.state = 598
                self.enter_definition()
                pass
            elif token in [GrammarParser.DURING]:
                self.enterOuterAlt(localctx, 5)
                self.state = 599
                self.during_definition()
                pass
            elif token in [GrammarParser.EXIT]:
                self.enterOuterAlt(localctx, 6)
                self.state = 600
                self.exit_definition()
                pass
            elif token in [GrammarParser.SHIFT_RIGHT]:
                self.enterOuterAlt(localctx, 7)
                self.state = 601
                self.during_aspect_definition()
                pass
            elif token in [GrammarParser.EVENT]:
                self.enterOuterAlt(localctx, 8)
                self.state = 602
                self.event_definition()
                pass
            elif token in [GrammarParser.IMPORT]:
                self.enterOuterAlt(localctx, 9)
                self.state = 603
                self.import_statement()
                pass
            elif token in [GrammarParser.SEMI]:
                self.enterOuterAlt(localctx, 10)
                self.state = 604
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
        self.enterRule(localctx, 74, self.RULE_operation_program)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 610
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 607
                self.operational_assignment()
                self.state = 612
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 613
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
        self.enterRule(localctx, 76, self.RULE_preamble_program)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 618
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 615
                self.preamble_statement()
                self.state = 620
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 621
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
        self.enterRule(localctx, 78, self.RULE_preamble_statement)
        try:
            self.state = 625
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 66, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 623
                self.initial_assignment()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 624
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
        self.enterRule(localctx, 80, self.RULE_initial_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 627
            self.match(GrammarParser.ID)
            self.state = 628
            self.match(GrammarParser.DECLARE_ASSIGN)
            self.state = 629
            self.init_expression(0)
            self.state = 630
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
        self.enterRule(localctx, 82, self.RULE_constant_definition)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 632
            self.match(GrammarParser.ID)
            self.state = 633
            self.match(GrammarParser.ASSIGN)
            self.state = 634
            self.init_expression(0)
            self.state = 635
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
        self.enterRule(localctx, 84, self.RULE_operational_assignment)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 637
            self.match(GrammarParser.ID)
            self.state = 638
            self.match(GrammarParser.DECLARE_ASSIGN)
            self.state = 639
            self.num_expression(0)
            self.state = 640
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
        self.enterRule(localctx, 86, self.RULE_generic_expression)
        try:
            self.state = 644
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 67, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 642
                self.num_expression(0)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 643
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
        _startState = 88
        self.enterRecursionRule(localctx, 88, self.RULE_init_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 660
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.LPAREN]:
                localctx = GrammarParser.ParenExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 647
                self.match(GrammarParser.LPAREN)
                self.state = 648
                self.init_expression(0)
                self.state = 649
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
                self.state = 651
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
                self.state = 652
                self.math_const()
                pass
            elif token in [GrammarParser.PLUS, GrammarParser.MINUS]:
                localctx = GrammarParser.UnaryExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 653
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.PLUS or _la == GrammarParser.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 654
                self.init_expression(9)
                pass
            elif token in [GrammarParser.UFUNC_NAME]:
                localctx = GrammarParser.FuncExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 655
                localctx.func_name = self.match(GrammarParser.UFUNC_NAME)
                self.state = 656
                self.match(GrammarParser.LPAREN)
                self.state = 657
                self.init_expression(0)
                self.state = 658
                self.match(GrammarParser.RPAREN)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 685
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 70, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 683
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 69, self._ctx)
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
                        self.state = 662
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 663
                        localctx.op = self.match(GrammarParser.POW)
                        self.state = 664
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
                        self.state = 665
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 666
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
                        self.state = 667
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
                        self.state = 668
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 669
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.PLUS or _la == GrammarParser.MINUS
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 670
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
                        self.state = 671
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 672
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
                        self.state = 673
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
                        self.state = 674
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 675
                        localctx.op = self.match(GrammarParser.AMP)
                        self.state = 676
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
                        self.state = 677
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 678
                        localctx.op = self.match(GrammarParser.CARET)
                        self.state = 679
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
                        self.state = 680
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 681
                        localctx.op = self.match(GrammarParser.PIPE)
                        self.state = 682
                        self.init_expression(3)
                        pass

                self.state = 687
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 70, self._ctx)

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
        _startState = 90
        self.enterRecursionRule(localctx, 90, self.RULE_num_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 711
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 71, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 689
                self.match(GrammarParser.LPAREN)
                self.state = 690
                self.num_expression(0)
                self.state = 691
                self.match(GrammarParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 693
                self.num_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.IdExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 694
                self.match(GrammarParser.ID)
                pass

            elif la_ == 4:
                localctx = GrammarParser.MathConstExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 695
                self.math_const()
                pass

            elif la_ == 5:
                localctx = GrammarParser.UnaryExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 696
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.PLUS or _la == GrammarParser.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 697
                self.num_expression(10)
                pass

            elif la_ == 6:
                localctx = GrammarParser.FuncExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 698
                localctx.func_name = self.match(GrammarParser.UFUNC_NAME)
                self.state = 699
                self.match(GrammarParser.LPAREN)
                self.state = 700
                self.num_expression(0)
                self.state = 701
                self.match(GrammarParser.RPAREN)
                pass

            elif la_ == 7:
                localctx = GrammarParser.ConditionalCStyleExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 703
                self.match(GrammarParser.LPAREN)
                self.state = 704
                self.cond_expression(0)
                self.state = 705
                self.match(GrammarParser.RPAREN)
                self.state = 706
                self.match(GrammarParser.QUESTION)
                self.state = 707
                self.num_expression(0)
                self.state = 708
                self.match(GrammarParser.COLON)
                self.state = 709
                self.num_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 736
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 73, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 734
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 72, self._ctx)
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
                        self.state = 713
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 9)"
                            )
                        self.state = 714
                        localctx.op = self.match(GrammarParser.POW)
                        self.state = 715
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
                        self.state = 716
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 717
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
                        self.state = 718
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
                        self.state = 719
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 720
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.PLUS or _la == GrammarParser.MINUS
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 721
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
                        self.state = 722
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 723
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
                        self.state = 724
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
                        self.state = 725
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 726
                        localctx.op = self.match(GrammarParser.AMP)
                        self.state = 727
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
                        self.state = 728
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 729
                        localctx.op = self.match(GrammarParser.CARET)
                        self.state = 730
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
                        self.state = 731
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 732
                        localctx.op = self.match(GrammarParser.PIPE)
                        self.state = 733
                        self.num_expression(4)
                        pass

                self.state = 738
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 73, self._ctx)

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

        def IFF_KW(self):
            return self.getToken(GrammarParser.IFF_KW, 0)

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

        def XOR_KW(self):
            return self.getToken(GrammarParser.XOR_KW, 0)

        def LOGICAL_OR(self):
            return self.getToken(GrammarParser.LOGICAL_OR, 0)

        def OR_KW(self):
            return self.getToken(GrammarParser.OR_KW, 0)

        def IMPLIES(self):
            return self.getToken(GrammarParser.IMPLIES, 0)

        def IMPLIES_KW(self):
            return self.getToken(GrammarParser.IMPLIES_KW, 0)

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
        _startState = 92
        self.enterRecursionRule(localctx, 92, self.RULE_cond_expression, _p)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 763
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 74, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 740
                self.match(GrammarParser.LPAREN)
                self.state = 741
                self.cond_expression(0)
                self.state = 742
                self.match(GrammarParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 744
                self.bool_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.UnaryExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 745
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.NOT_KW or _la == GrammarParser.BANG):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 746
                self.cond_expression(9)
                pass

            elif la_ == 4:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 747
                self.num_expression(0)
                self.state = 748
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (
                    ((_la - 33) & ~0x3F) == 0
                    and (
                        (1 << (_la - 33))
                        & (
                            (1 << (GrammarParser.LE - 33))
                            | (1 << (GrammarParser.GE - 33))
                            | (1 << (GrammarParser.LT - 33))
                            | (1 << (GrammarParser.GT - 33))
                        )
                    )
                    != 0
                ):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 749
                self.num_expression(0)
                pass

            elif la_ == 5:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 751
                self.num_expression(0)
                self.state = 752
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.EQ or _la == GrammarParser.NE):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 753
                self.num_expression(0)
                pass

            elif la_ == 6:
                localctx = GrammarParser.ConditionalCStyleCondNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 755
                self.match(GrammarParser.LPAREN)
                self.state = 756
                self.cond_expression(0)
                self.state = 757
                self.match(GrammarParser.RPAREN)
                self.state = 758
                self.match(GrammarParser.QUESTION)
                self.state = 759
                self.cond_expression(0)
                self.state = 760
                self.match(GrammarParser.COLON)
                self.state = 761
                self.cond_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 782
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 76, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 780
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 75, self._ctx)
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
                        self.state = 765
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 766
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la) & ~0x3F) == 0
                            and (
                                (1 << _la)
                                & (
                                    (1 << GrammarParser.IFF_KW)
                                    | (1 << GrammarParser.EQ)
                                    | (1 << GrammarParser.NE)
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 767
                        self.cond_expression(7)
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
                        self.state = 768
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 769
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
                        self.state = 770
                        self.cond_expression(6)
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
                        self.state = 771
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 772
                        localctx.op = self.match(GrammarParser.XOR_KW)
                        self.state = 773
                        self.cond_expression(5)
                        pass

                    elif la_ == 4:
                        localctx = GrammarParser.BinaryExprCondContext(
                            self,
                            GrammarParser.Cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_cond_expression
                        )
                        self.state = 774
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 775
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
                        self.state = 776
                        self.cond_expression(4)
                        pass

                    elif la_ == 5:
                        localctx = GrammarParser.BinaryExprCondContext(
                            self,
                            GrammarParser.Cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_cond_expression
                        )
                        self.state = 777
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 778
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.IMPLIES_KW
                            or _la == GrammarParser.IMPLIES
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 779
                        self.cond_expression(2)
                        pass

                self.state = 784
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 76, self._ctx)

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
        self.enterRule(localctx, 94, self.RULE_num_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 785
            _la = self._input.LA(1)
            if not (
                ((_la - 66) & ~0x3F) == 0
                and (
                    (1 << (_la - 66))
                    & (
                        (1 << (GrammarParser.FLOAT - 66))
                        | (1 << (GrammarParser.HEX_INT - 66))
                        | (1 << (GrammarParser.INT - 66))
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
        self.enterRule(localctx, 96, self.RULE_bool_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 787
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
        self.enterRule(localctx, 98, self.RULE_math_const)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 789
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
        self.enterRule(localctx, 100, self.RULE_chain_id)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 792
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.SLASH:
                self.state = 791
                localctx.isabs = self.match(GrammarParser.SLASH)

            self.state = 794
            self.match(GrammarParser.ID)
            self.state = 799
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.DOT:
                self.state = 795
                self.match(GrammarParser.DOT)
                self.state = 796
                self.match(GrammarParser.ID)
                self.state = 801
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
        self._predicates[44] = self.init_expression_sempred
        self._predicates[45] = self.num_expression_sempred
        self._predicates[46] = self.cond_expression_sempred
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
            return self.precpred(self._ctx, 6)

        if predIndex == 15:
            return self.precpred(self._ctx, 5)

        if predIndex == 16:
            return self.precpred(self._ctx, 4)

        if predIndex == 17:
            return self.precpred(self._ctx, 3)

        if predIndex == 18:
            return self.precpred(self._ctx, 2)
