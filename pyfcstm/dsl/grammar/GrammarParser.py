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
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3b")
        buf.write("\u0376\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7")
        buf.write("\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r\4\16")
        buf.write("\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23\t\23")
        buf.write("\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30\4\31")
        buf.write("\t\31\4\32\t\32\4\33\t\33\4\34\t\34\4\35\t\35\4\36\t\36")
        buf.write('\4\37\t\37\4 \t \4!\t!\4"\t"\4#\t#\4$\t$\4%\t%\4&\t')
        buf.write("&\4'\t'\4(\t(\4)\t)\4*\t*\4+\t+\4,\t,\4-\t-\4.\t.\4")
        buf.write("/\t/\4\60\t\60\4\61\t\61\4\62\t\62\4\63\t\63\4\64\t\64")
        buf.write("\3\2\3\2\3\2\3\3\7\3m\n\3\f\3\16\3p\13\3\3\3\3\3\3\3\3")
        buf.write("\4\5\4v\n\4\3\4\3\4\3\4\3\4\3\4\3\4\3\4\3\5\5\5\u0080")
        buf.write("\n\5\3\5\5\5\u0083\n\5\3\5\3\5\3\5\3\5\5\5\u0089\n\5\3")
        buf.write("\5\3\5\5\5\u008d\n\5\3\5\5\5\u0090\n\5\3\5\3\5\3\5\3\5")
        buf.write("\5\5\u0096\n\5\3\5\3\5\7\5\u009a\n\5\f\5\16\5\u009d\13")
        buf.write("\5\3\5\5\5\u00a0\n\5\3\6\5\6\u00a3\n\6\3\6\3\6\3\6\3\6")
        buf.write("\5\6\u00a9\n\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u00b1\n\6\3")
        buf.write("\6\5\6\u00b4\n\6\3\6\3\6\3\6\3\6\5\6\u00ba\n\6\3\6\3\6")
        buf.write("\3\6\3\6\3\6\3\6\5\6\u00c2\n\6\3\6\5\6\u00c5\n\6\3\6\3")
        buf.write("\6\3\6\3\6\5\6\u00cb\n\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u00d3")
        buf.write("\n\6\5\6\u00d5\n\6\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7")
        buf.write("\3\7\5\7\u00e1\n\7\3\b\7\b\u00e4\n\b\f\b\16\b\u00e7\13")
        buf.write("\b\3\b\3\b\3\b\7\b\u00ec\n\b\f\b\16\b\u00ef\13\b\3\t\3")
        buf.write("\t\3\t\3\n\3\n\5\n\u00f6\n\n\3\13\3\13\3\13\3\13\3\13")
        buf.write("\3\13\3\13\3\13\3\13\3\13\5\13\u0102\n\13\3\f\7\f\u0105")
        buf.write("\n\f\f\f\16\f\u0108\13\f\3\f\3\f\3\f\7\f\u010d\n\f\f\f")
        buf.write("\16\f\u0110\13\f\3\r\3\r\3\r\3\16\3\16\5\16\u0117\n\16")
        buf.write("\3\17\3\17\3\20\3\20\3\20\3\20\3\20\3\20\7\20\u0121\n")
        buf.write("\20\f\20\16\20\u0124\13\20\3\20\5\20\u0127\n\20\3\21\3")
        buf.write("\21\3\22\3\22\5\22\u012d\n\22\3\23\3\23\3\24\3\24\3\24")
        buf.write("\3\24\3\25\5\25\u0136\n\25\3\25\3\25\3\25\3\25\3\25\3")
        buf.write("\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\5\25\u0146")
        buf.write("\n\25\3\25\3\25\5\25\u014a\n\25\3\25\3\25\3\25\3\25\3")
        buf.write("\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\5\25")
        buf.write("\u015a\n\25\3\25\3\25\5\25\u015e\n\25\3\25\3\25\3\25\3")
        buf.write("\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\5\25\u016c")
        buf.write("\n\25\3\25\3\25\5\25\u0170\n\25\3\25\3\25\3\25\3\25\3")
        buf.write("\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\5\25\u017e\n\25")
        buf.write("\3\25\5\25\u0181\n\25\3\26\5\26\u0184\n\26\3\26\3\26\5")
        buf.write("\26\u0188\n\26\3\26\3\26\3\26\3\26\3\26\5\26\u018f\n\26")
        buf.write("\3\26\3\26\3\26\3\26\3\26\5\26\u0196\n\26\3\26\3\26\3")
        buf.write("\26\5\26\u019b\n\26\3\26\3\26\5\26\u019f\n\26\3\26\3\26")
        buf.write("\5\26\u01a3\n\26\3\26\3\26\3\26\3\26\5\26\u01a9\n\26\3")
        buf.write("\27\5\27\u01ac\n\27\3\27\3\27\5\27\u01b0\n\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\5\27\u01b7\n\27\3\27\3\27\3\27\3\27\3")
        buf.write("\27\5\27\u01be\n\27\3\27\3\27\3\27\5\27\u01c3\n\27\3\27")
        buf.write("\3\27\5\27\u01c7\n\27\3\27\3\27\5\27\u01cb\n\27\3\27\3")
        buf.write("\27\3\27\3\27\5\27\u01d1\n\27\3\30\5\30\u01d4\n\30\3\30")
        buf.write("\3\30\5\30\u01d8\n\30\3\30\5\30\u01db\n\30\3\30\3\30\3")
        buf.write("\30\3\30\3\30\5\30\u01e2\n\30\3\30\3\30\5\30\u01e6\n\30")
        buf.write("\3\30\3\30\3\30\3\30\5\30\u01ec\n\30\3\30\3\30\5\30\u01f0")
        buf.write("\n\30\3\30\3\30\5\30\u01f4\n\30\3\30\3\30\5\30\u01f8\n")
        buf.write("\30\3\30\3\30\5\30\u01fc\n\30\3\30\5\30\u01ff\n\30\3\30")
        buf.write("\3\30\3\30\3\30\5\30\u0205\n\30\3\31\5\31\u0208\n\31\3")
        buf.write("\31\3\31\3\31\3\31\5\31\u020e\n\31\3\31\3\31\3\31\3\31")
        buf.write("\3\31\5\31\u0215\n\31\3\31\3\31\3\31\3\31\3\31\3\31\3")
        buf.write("\31\5\31\u021e\n\31\3\31\3\31\3\31\3\31\3\31\5\31\u0225")
        buf.write("\n\31\3\31\3\31\5\31\u0229\n\31\3\31\3\31\3\31\3\31\5")
        buf.write("\31\u022f\n\31\3\31\3\31\3\31\3\31\5\31\u0235\n\31\3\32")
        buf.write("\5\32\u0238\n\32\3\32\3\32\3\32\3\32\5\32\u023e\n\32\3")
        buf.write("\32\3\32\3\33\3\33\3\33\3\33\3\33\3\33\5\33\u0248\n\33")
        buf.write("\3\33\3\33\7\33\u024c\n\33\f\33\16\33\u024f\13\33\3\33")
        buf.write("\3\33\5\33\u0253\n\33\3\34\3\34\3\34\5\34\u0258\n\34\3")
        buf.write("\35\3\35\3\35\3\35\3\35\3\35\3\36\3\36\3\36\3\36\3\36")
        buf.write("\7\36\u0265\n\36\f\36\16\36\u0268\13\36\3\36\3\36\3\36")
        buf.write("\5\36\u026d\n\36\3\37\3\37\3\37\5\37\u0272\n\37\3 \3 ")
        buf.write('\3 \3 \3 \3 \5 \u027a\n \3 \3 \3!\3!\3!\3!\3!\3"\3"')
        buf.write('\3"\3"\3#\3#\3#\3#\3#\3#\3#\3#\3#\3#\3#\3#\7#\u0293')
        buf.write("\n#\f#\16#\u0296\13#\3#\3#\5#\u029a\n#\3$\3$\3$\5$\u029f")
        buf.write("\n$\3%\7%\u02a2\n%\f%\16%\u02a5\13%\3&\3&\3&\3&\3&\3&")
        buf.write("\3&\3&\3&\3&\5&\u02b1\n&\3'\7'\u02b4\n'\f'\16'\u02b7")
        buf.write("\13'\3'\3'\3(\7(\u02bc\n(\f(\16(\u02bf\13(\3(\3(\3")
        buf.write(")\3)\5)\u02c5\n)\3*\3*\3*\3*\3*\3+\3+\3+\3+\3+\3,\3,\3")
        buf.write(",\3,\3,\3-\3-\5-\u02d8\n-\3.\3.\3.\3.\3.\3.\3.\3.\3.\3")
        buf.write(".\3.\3.\3.\3.\5.\u02e8\n.\3.\3.\3.\3.\3.\3.\3.\3.\3.\3")
        buf.write(".\3.\3.\3.\3.\3.\3.\3.\3.\3.\3.\3.\7.\u02ff\n.\f.\16.")
        buf.write("\u0302\13.\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3")
        buf.write("/\3/\3/\3/\3/\3/\3/\3/\3/\5/\u031b\n/\3/\3/\3/\3/\3/\3")
        buf.write("/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\3/\7/\u0332")
        buf.write("\n/\f/\16/\u0335\13/\3\60\3\60\3\60\3\60\3\60\3\60\3\60")
        buf.write("\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60")
        buf.write("\3\60\3\60\3\60\3\60\3\60\3\60\5\60\u034f\n\60\3\60\3")
        buf.write("\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60\3\60")
        buf.write("\3\60\3\60\3\60\7\60\u0360\n\60\f\60\16\60\u0363\13\60")
        buf.write("\3\61\3\61\3\62\3\62\3\63\3\63\3\64\5\64\u036c\n\64\3")
        buf.write("\64\3\64\3\64\7\64\u0371\n\64\f\64\16\64\u0374\13\64\3")
        buf.write("\64\2\5Z\\^\65\2\4\6\b\n\f\16\20\22\24\26\30\32\34\36")
        buf.write(' "$&(*,.\60\62\64\668:<>@BDFHJLNPRTVXZ\\^`bdf\2\22\3')
        buf.write('\2\24\25\4\2++\66\66\3\2\r\16\3\2;<\4\289==\3\2!"\4\2')
        buf.write("\33\33::\4\2#$AB\3\2%&\4\2\35\35%&\4\2\31\31''\4\2\32")
        buf.write("\32((\4\2\34\34))\3\2DF\3\2GH\3\2\26\30\2\u03e6\2h\3\2")
        buf.write("\2\2\4n\3\2\2\2\6u\3\2\2\2\b\u009f\3\2\2\2\n\u00d4\3\2")
        buf.write("\2\2\f\u00e0\3\2\2\2\16\u00e5\3\2\2\2\20\u00f0\3\2\2\2")
        buf.write("\22\u00f5\3\2\2\2\24\u0101\3\2\2\2\26\u0106\3\2\2\2\30")
        buf.write("\u0111\3\2\2\2\32\u0116\3\2\2\2\34\u0118\3\2\2\2\36\u0126")
        buf.write('\3\2\2\2 \u0128\3\2\2\2"\u012c\3\2\2\2$\u012e\3\2\2\2')
        buf.write("&\u0130\3\2\2\2(\u0180\3\2\2\2*\u01a8\3\2\2\2,\u01d0\3")
        buf.write("\2\2\2.\u0204\3\2\2\2\60\u0234\3\2\2\2\62\u0237\3\2\2")
        buf.write("\2\64\u0241\3\2\2\2\66\u0257\3\2\2\28\u0259\3\2\2\2:\u026c")
        buf.write("\3\2\2\2<\u0271\3\2\2\2>\u0273\3\2\2\2@\u027d\3\2\2\2")
        buf.write("B\u0282\3\2\2\2D\u0286\3\2\2\2F\u029e\3\2\2\2H\u02a3\3")
        buf.write("\2\2\2J\u02b0\3\2\2\2L\u02b5\3\2\2\2N\u02bd\3\2\2\2P\u02c4")
        buf.write("\3\2\2\2R\u02c6\3\2\2\2T\u02cb\3\2\2\2V\u02d0\3\2\2\2")
        buf.write("X\u02d7\3\2\2\2Z\u02e7\3\2\2\2\\\u031a\3\2\2\2^\u034e")
        buf.write("\3\2\2\2`\u0364\3\2\2\2b\u0366\3\2\2\2d\u0368\3\2\2\2")
        buf.write("f\u036b\3\2\2\2hi\5^\60\2ij\7\2\2\3j\3\3\2\2\2km\5\6\4")
        buf.write("\2lk\3\2\2\2mp\3\2\2\2nl\3\2\2\2no\3\2\2\2oq\3\2\2\2p")
        buf.write("n\3\2\2\2qr\5\b\5\2rs\7\2\2\3s\5\3\2\2\2tv\7L\2\2ut\3")
        buf.write("\2\2\2uv\3\2\2\2vw\3\2\2\2wx\7\4\2\2xy\t\2\2\2yz\7J\2")
        buf.write("\2z{\7C\2\2{|\5Z.\2|}\7-\2\2}\7\3\2\2\2~\u0080\7L\2\2")
        buf.write("\177~\3\2\2\2\177\u0080\3\2\2\2\u0080\u0082\3\2\2\2\u0081")
        buf.write("\u0083\7\b\2\2\u0082\u0081\3\2\2\2\u0082\u0083\3\2\2\2")
        buf.write("\u0083\u0084\3\2\2\2\u0084\u0085\7\t\2\2\u0085\u0088\7")
        buf.write("J\2\2\u0086\u0087\7\7\2\2\u0087\u0089\7K\2\2\u0088\u0086")
        buf.write("\3\2\2\2\u0088\u0089\3\2\2\2\u0089\u008a\3\2\2\2\u008a")
        buf.write("\u00a0\7-\2\2\u008b\u008d\7L\2\2\u008c\u008b\3\2\2\2\u008c")
        buf.write("\u008d\3\2\2\2\u008d\u008f\3\2\2\2\u008e\u0090\7\b\2\2")
        buf.write("\u008f\u008e\3\2\2\2\u008f\u0090\3\2\2\2\u0090\u0091\3")
        buf.write("\2\2\2\u0091\u0092\7\t\2\2\u0092\u0095\7J\2\2\u0093\u0094")
        buf.write("\7\7\2\2\u0094\u0096\7K\2\2\u0095\u0093\3\2\2\2\u0095")
        buf.write("\u0096\3\2\2\2\u0096\u0097\3\2\2\2\u0097\u009b\7/\2\2")
        buf.write("\u0098\u009a\5J&\2\u0099\u0098\3\2\2\2\u009a\u009d\3\2")
        buf.write("\2\2\u009b\u0099\3\2\2\2\u009b\u009c\3\2\2\2\u009c\u009e")
        buf.write("\3\2\2\2\u009d\u009b\3\2\2\2\u009e\u00a0\7\60\2\2\u009f")
        buf.write("\177\3\2\2\2\u009f\u008c\3\2\2\2\u00a0\t\3\2\2\2\u00a1")
        buf.write("\u00a3\7L\2\2\u00a2\u00a1\3\2\2\2\u00a2\u00a3\3\2\2\2")
        buf.write("\u00a3\u00a4\3\2\2\2\u00a4\u00a5\7\37\2\2\u00a5\u00a6")
        buf.write("\7,\2\2\u00a6\u00a8\7J\2\2\u00a7\u00a9\5\f\7\2\u00a8\u00a7")
        buf.write("\3\2\2\2\u00a8\u00a9\3\2\2\2\u00a9\u00b0\3\2\2\2\u00aa")
        buf.write("\u00b1\7-\2\2\u00ab\u00ac\7\21\2\2\u00ac\u00ad\7/\2\2")
        buf.write("\u00ad\u00ae\5H%\2\u00ae\u00af\7\60\2\2\u00af\u00b1\3")
        buf.write("\2\2\2\u00b0\u00aa\3\2\2\2\u00b0\u00ab\3\2\2\2\u00b1\u00d5")
        buf.write("\3\2\2\2\u00b2\u00b4\7L\2\2\u00b3\u00b2\3\2\2\2\u00b3")
        buf.write("\u00b4\3\2\2\2\u00b4\u00b5\3\2\2\2\u00b5\u00b6\7J\2\2")
        buf.write("\u00b6\u00b7\7,\2\2\u00b7\u00b9\7J\2\2\u00b8\u00ba\5\24")
        buf.write("\13\2\u00b9\u00b8\3\2\2\2\u00b9\u00ba\3\2\2\2\u00ba\u00c1")
        buf.write("\3\2\2\2\u00bb\u00c2\7-\2\2\u00bc\u00bd\7\21\2\2\u00bd")
        buf.write("\u00be\7/\2\2\u00be\u00bf\5H%\2\u00bf\u00c0\7\60\2\2\u00c0")
        buf.write("\u00c2\3\2\2\2\u00c1\u00bb\3\2\2\2\u00c1\u00bc\3\2\2\2")
        buf.write("\u00c2\u00d5\3\2\2\2\u00c3\u00c5\7L\2\2\u00c4\u00c3\3")
        buf.write("\2\2\2\u00c4\u00c5\3\2\2\2\u00c5\u00c6\3\2\2\2\u00c6\u00c7")
        buf.write("\7J\2\2\u00c7\u00c8\7,\2\2\u00c8\u00ca\7\37\2\2\u00c9")
        buf.write("\u00cb\5\24\13\2\u00ca\u00c9\3\2\2\2\u00ca\u00cb\3\2\2")
        buf.write("\2\u00cb\u00d2\3\2\2\2\u00cc\u00d3\7-\2\2\u00cd\u00ce")
        buf.write("\7\21\2\2\u00ce\u00cf\7/\2\2\u00cf\u00d0\5H%\2\u00d0\u00d1")
        buf.write("\7\60\2\2\u00d1\u00d3\3\2\2\2\u00d2\u00cc\3\2\2\2\u00d2")
        buf.write("\u00cd\3\2\2\2\u00d3\u00d5\3\2\2\2\u00d4\u00a2\3\2\2\2")
        buf.write("\u00d4\u00b3\3\2\2\2\u00d4\u00c4\3\2\2\2\u00d5\13\3\2")
        buf.write("\2\2\u00d6\u00d7\7+\2\2\u00d7\u00e1\5\16\b\2\u00d8\u00d9")
        buf.write("\7\66\2\2\u00d9\u00da\7\22\2\2\u00da\u00db\7\61\2\2\u00db")
        buf.write("\u00dc\5^\60\2\u00dc\u00dd\7\62\2\2\u00dd\u00e1\3\2\2")
        buf.write("\2\u00de\u00df\7\66\2\2\u00df\u00e1\5\36\20\2\u00e0\u00d6")
        buf.write("\3\2\2\2\u00e0\u00d8\3\2\2\2\u00e0\u00de\3\2\2\2\u00e1")
        buf.write("\r\3\2\2\2\u00e2\u00e4\5\20\t\2\u00e3\u00e2\3\2\2\2\u00e4")
        buf.write("\u00e7\3\2\2\2\u00e5\u00e3\3\2\2\2\u00e5\u00e6\3\2\2\2")
        buf.write("\u00e6\u00e8\3\2\2\2\u00e7\u00e5\3\2\2\2\u00e8\u00ed\5")
        buf.write("$\23\2\u00e9\u00ea\7;\2\2\u00ea\u00ec\5\22\n\2\u00eb\u00e9")
        buf.write("\3\2\2\2\u00ec\u00ef\3\2\2\2\u00ed\u00eb\3\2\2\2\u00ed")
        buf.write("\u00ee\3\2\2\2\u00ee\17\3\2\2\2\u00ef\u00ed\3\2\2\2\u00f0")
        buf.write("\u00f1\5&\24\2\u00f1\u00f2\7;\2\2\u00f2\21\3\2\2\2\u00f3")
        buf.write("\u00f6\5$\23\2\u00f4\u00f6\5&\24\2\u00f5\u00f3\3\2\2\2")
        buf.write("\u00f5\u00f4\3\2\2\2\u00f6\23\3\2\2\2\u00f7\u00f8\7+\2")
        buf.write("\2\u00f8\u0102\5\26\f\2\u00f9\u00fa\7\66\2\2\u00fa\u00fb")
        buf.write("\7\22\2\2\u00fb\u00fc\7\61\2\2\u00fc\u00fd\5^\60\2\u00fd")
        buf.write("\u00fe\7\62\2\2\u00fe\u0102\3\2\2\2\u00ff\u0100\7\66\2")
        buf.write("\2\u0100\u0102\5\36\20\2\u0101\u00f7\3\2\2\2\u0101\u00f9")
        buf.write("\3\2\2\2\u0101\u00ff\3\2\2\2\u0102\25\3\2\2\2\u0103\u0105")
        buf.write("\5\30\r\2\u0104\u0103\3\2\2\2\u0105\u0108\3\2\2\2\u0106")
        buf.write("\u0104\3\2\2\2\u0106\u0107\3\2\2\2\u0107\u0109\3\2\2\2")
        buf.write("\u0108\u0106\3\2\2\2\u0109\u010e\5\34\17\2\u010a\u010b")
        buf.write("\7;\2\2\u010b\u010d\5\32\16\2\u010c\u010a\3\2\2\2\u010d")
        buf.write("\u0110\3\2\2\2\u010e\u010c\3\2\2\2\u010e\u010f\3\2\2\2")
        buf.write("\u010f\27\3\2\2\2\u0110\u010e\3\2\2\2\u0111\u0112\5&\24")
        buf.write("\2\u0112\u0113\7;\2\2\u0113\31\3\2\2\2\u0114\u0117\5\34")
        buf.write("\17\2\u0115\u0117\5&\24\2\u0116\u0114\3\2\2\2\u0116\u0115")
        buf.write("\3\2\2\2\u0117\33\3\2\2\2\u0118\u0119\7J\2\2\u0119\35")
        buf.write('\3\2\2\2\u011a\u0127\5 \21\2\u011b\u011c\5"\22\2\u011c')
        buf.write('\u011d\7;\2\2\u011d\u0122\5"\22\2\u011e\u011f\7;\2\2')
        buf.write('\u011f\u0121\5"\22\2\u0120\u011e\3\2\2\2\u0121\u0124')
        buf.write("\3\2\2\2\u0122\u0120\3\2\2\2\u0122\u0123\3\2\2\2\u0123")
        buf.write("\u0127\3\2\2\2\u0124\u0122\3\2\2\2\u0125\u0127\5$\23\2")
        buf.write("\u0126\u011a\3\2\2\2\u0126\u011b\3\2\2\2\u0126\u0125\3")
        buf.write("\2\2\2\u0127\37\3\2\2\2\u0128\u0129\5&\24\2\u0129!\3\2")
        buf.write("\2\2\u012a\u012d\5$\23\2\u012b\u012d\5&\24\2\u012c\u012a")
        buf.write("\3\2\2\2\u012c\u012b\3\2\2\2\u012d#\3\2\2\2\u012e\u012f")
        buf.write("\5f\64\2\u012f%\3\2\2\2\u0130\u0131\7\61\2\2\u0131\u0132")
        buf.write("\5^\60\2\u0132\u0133\7\62\2\2\u0133'\3\2\2\2\u0134\u0136")
        buf.write("\7L\2\2\u0135\u0134\3\2\2\2\u0135\u0136\3\2\2\2\u0136")
        buf.write("\u0137\3\2\2\2\u0137\u0138\7:\2\2\u0138\u0139\7J\2\2\u0139")
        buf.write("\u013a\7,\2\2\u013a\u0145\7J\2\2\u013b\u013c\7+\2\2\u013c")
        buf.write("\u0146\7J\2\2\u013d\u013e\7\66\2\2\u013e\u0146\5f\64\2")
        buf.write("\u013f\u0140\7\66\2\2\u0140\u0141\7\22\2\2\u0141\u0142")
        buf.write("\7\61\2\2\u0142\u0143\5^\60\2\u0143\u0144\7\62\2\2\u0144")
        buf.write("\u0146\3\2\2\2\u0145\u013b\3\2\2\2\u0145\u013d\3\2\2\2")
        buf.write("\u0145\u013f\3\2\2\2\u0145\u0146\3\2\2\2\u0146\u0147\3")
        buf.write("\2\2\2\u0147\u0181\7-\2\2\u0148\u014a\7L\2\2\u0149\u0148")
        buf.write("\3\2\2\2\u0149\u014a\3\2\2\2\u014a\u014b\3\2\2\2\u014b")
        buf.write("\u014c\7:\2\2\u014c\u014d\7J\2\2\u014d\u014e\7,\2\2\u014e")
        buf.write("\u0159\7\37\2\2\u014f\u0150\7+\2\2\u0150\u015a\7J\2\2")
        buf.write("\u0151\u0152\7\66\2\2\u0152\u015a\5f\64\2\u0153\u0154")
        buf.write("\7\66\2\2\u0154\u0155\7\22\2\2\u0155\u0156\7\61\2\2\u0156")
        buf.write("\u0157\5^\60\2\u0157\u0158\7\62\2\2\u0158\u015a\3\2\2")
        buf.write("\2\u0159\u014f\3\2\2\2\u0159\u0151\3\2\2\2\u0159\u0153")
        buf.write("\3\2\2\2\u0159\u015a\3\2\2\2\u015a\u015b\3\2\2\2\u015b")
        buf.write("\u0181\7-\2\2\u015c\u015e\7L\2\2\u015d\u015c\3\2\2\2\u015d")
        buf.write("\u015e\3\2\2\2\u015e\u015f\3\2\2\2\u015f\u0160\7:\2\2")
        buf.write("\u0160\u0161\79\2\2\u0161\u0162\7,\2\2\u0162\u016b\7J")
        buf.write("\2\2\u0163\u0164\t\3\2\2\u0164\u016c\5f\64\2\u0165\u0166")
        buf.write("\7\66\2\2\u0166\u0167\7\22\2\2\u0167\u0168\7\61\2\2\u0168")
        buf.write("\u0169\5^\60\2\u0169\u016a\7\62\2\2\u016a\u016c\3\2\2")
        buf.write("\2\u016b\u0163\3\2\2\2\u016b\u0165\3\2\2\2\u016b\u016c")
        buf.write("\3\2\2\2\u016c\u016d\3\2\2\2\u016d\u0181\7-\2\2\u016e")
        buf.write("\u0170\7L\2\2\u016f\u016e\3\2\2\2\u016f\u0170\3\2\2\2")
        buf.write("\u0170\u0171\3\2\2\2\u0171\u0172\7:\2\2\u0172\u0173\7")
        buf.write("9\2\2\u0173\u0174\7,\2\2\u0174\u017d\7\37\2\2\u0175\u0176")
        buf.write("\t\3\2\2\u0176\u017e\5f\64\2\u0177\u0178\7\66\2\2\u0178")
        buf.write("\u0179\7\22\2\2\u0179\u017a\7\61\2\2\u017a\u017b\5^\60")
        buf.write("\2\u017b\u017c\7\62\2\2\u017c\u017e\3\2\2\2\u017d\u0175")
        buf.write("\3\2\2\2\u017d\u0177\3\2\2\2\u017d\u017e\3\2\2\2\u017e")
        buf.write("\u017f\3\2\2\2\u017f\u0181\7-\2\2\u0180\u0135\3\2\2\2")
        buf.write("\u0180\u0149\3\2\2\2\u0180\u015d\3\2\2\2\u0180\u016f\3")
        buf.write("\2\2\2\u0181)\3\2\2\2\u0182\u0184\7L\2\2\u0183\u0182\3")
        buf.write("\2\2\2\u0183\u0184\3\2\2\2\u0184\u0185\3\2\2\2\u0185\u0187")
        buf.write("\7\n\2\2\u0186\u0188\7J\2\2\u0187\u0186\3\2\2\2\u0187")
        buf.write("\u0188\3\2\2\2\u0188\u0189\3\2\2\2\u0189\u018a\7/\2\2")
        buf.write("\u018a\u018b\5H%\2\u018b\u018c\7\60\2\2\u018c\u01a9\3")
        buf.write("\2\2\2\u018d\u018f\7L\2\2\u018e\u018d\3\2\2\2\u018e\u018f")
        buf.write("\3\2\2\2\u018f\u0190\3\2\2\2\u0190\u0191\7\n\2\2\u0191")
        buf.write("\u0192\7\17\2\2\u0192\u0193\7J\2\2\u0193\u01a9\7-\2\2")
        buf.write("\u0194\u0196\7L\2\2\u0195\u0194\3\2\2\2\u0195\u0196\3")
        buf.write("\2\2\2\u0196\u0197\3\2\2\2\u0197\u0198\7\n\2\2\u0198\u019a")
        buf.write("\7\17\2\2\u0199\u019b\7J\2\2\u019a\u0199\3\2\2\2\u019a")
        buf.write("\u019b\3\2\2\2\u019b\u019c\3\2\2\2\u019c\u01a9\7L\2\2")
        buf.write("\u019d\u019f\7L\2\2\u019e\u019d\3\2\2\2\u019e\u019f\3")
        buf.write("\2\2\2\u019f\u01a0\3\2\2\2\u01a0\u01a2\7\n\2\2\u01a1\u01a3")
        buf.write("\7J\2\2\u01a2\u01a1\3\2\2\2\u01a2\u01a3\3\2\2\2\u01a3")
        buf.write("\u01a4\3\2\2\2\u01a4\u01a5\7\20\2\2\u01a5\u01a6\5f\64")
        buf.write("\2\u01a6\u01a7\7-\2\2\u01a7\u01a9\3\2\2\2\u01a8\u0183")
        buf.write("\3\2\2\2\u01a8\u018e\3\2\2\2\u01a8\u0195\3\2\2\2\u01a8")
        buf.write("\u019e\3\2\2\2\u01a9+\3\2\2\2\u01aa\u01ac\7L\2\2\u01ab")
        buf.write("\u01aa\3\2\2\2\u01ab\u01ac\3\2\2\2\u01ac\u01ad\3\2\2\2")
        buf.write("\u01ad\u01af\7\13\2\2\u01ae\u01b0\7J\2\2\u01af\u01ae\3")
        buf.write("\2\2\2\u01af\u01b0\3\2\2\2\u01b0\u01b1\3\2\2\2\u01b1\u01b2")
        buf.write("\7/\2\2\u01b2\u01b3\5H%\2\u01b3\u01b4\7\60\2\2\u01b4\u01d1")
        buf.write("\3\2\2\2\u01b5\u01b7\7L\2\2\u01b6\u01b5\3\2\2\2\u01b6")
        buf.write("\u01b7\3\2\2\2\u01b7\u01b8\3\2\2\2\u01b8\u01b9\7\13\2")
        buf.write("\2\u01b9\u01ba\7\17\2\2\u01ba\u01bb\7J\2\2\u01bb\u01d1")
        buf.write("\7-\2\2\u01bc\u01be\7L\2\2\u01bd\u01bc\3\2\2\2\u01bd\u01be")
        buf.write("\3\2\2\2\u01be\u01bf\3\2\2\2\u01bf\u01c0\7\13\2\2\u01c0")
        buf.write("\u01c2\7\17\2\2\u01c1\u01c3\7J\2\2\u01c2\u01c1\3\2\2\2")
        buf.write("\u01c2\u01c3\3\2\2\2\u01c3\u01c4\3\2\2\2\u01c4\u01d1\7")
        buf.write("L\2\2\u01c5\u01c7\7L\2\2\u01c6\u01c5\3\2\2\2\u01c6\u01c7")
        buf.write("\3\2\2\2\u01c7\u01c8\3\2\2\2\u01c8\u01ca\7\13\2\2\u01c9")
        buf.write("\u01cb\7J\2\2\u01ca\u01c9\3\2\2\2\u01ca\u01cb\3\2\2\2")
        buf.write("\u01cb\u01cc\3\2\2\2\u01cc\u01cd\7\20\2\2\u01cd\u01ce")
        buf.write("\5f\64\2\u01ce\u01cf\7-\2\2\u01cf\u01d1\3\2\2\2\u01d0")
        buf.write("\u01ab\3\2\2\2\u01d0\u01b6\3\2\2\2\u01d0\u01bd\3\2\2\2")
        buf.write("\u01d0\u01c6\3\2\2\2\u01d1-\3\2\2\2\u01d2\u01d4\7L\2\2")
        buf.write("\u01d3\u01d2\3\2\2\2\u01d3\u01d4\3\2\2\2\u01d4\u01d5\3")
        buf.write("\2\2\2\u01d5\u01d7\7\f\2\2\u01d6\u01d8\t\4\2\2\u01d7\u01d6")
        buf.write("\3\2\2\2\u01d7\u01d8\3\2\2\2\u01d8\u01da\3\2\2\2\u01d9")
        buf.write("\u01db\7J\2\2\u01da\u01d9\3\2\2\2\u01da\u01db\3\2\2\2")
        buf.write("\u01db\u01dc\3\2\2\2\u01dc\u01dd\7/\2\2\u01dd\u01de\5")
        buf.write("H%\2\u01de\u01df\7\60\2\2\u01df\u0205\3\2\2\2\u01e0\u01e2")
        buf.write("\7L\2\2\u01e1\u01e0\3\2\2\2\u01e1\u01e2\3\2\2\2\u01e2")
        buf.write("\u01e3\3\2\2\2\u01e3\u01e5\7\f\2\2\u01e4\u01e6\t\4\2\2")
        buf.write("\u01e5\u01e4\3\2\2\2\u01e5\u01e6\3\2\2\2\u01e6\u01e7\3")
        buf.write("\2\2\2\u01e7\u01e8\7\17\2\2\u01e8\u01e9\7J\2\2\u01e9\u0205")
        buf.write("\7-\2\2\u01ea\u01ec\7L\2\2\u01eb\u01ea\3\2\2\2\u01eb\u01ec")
        buf.write("\3\2\2\2\u01ec\u01ed\3\2\2\2\u01ed\u01ef\7\f\2\2\u01ee")
        buf.write("\u01f0\t\4\2\2\u01ef\u01ee\3\2\2\2\u01ef\u01f0\3\2\2\2")
        buf.write("\u01f0\u01f1\3\2\2\2\u01f1\u01f3\7\17\2\2\u01f2\u01f4")
        buf.write("\7J\2\2\u01f3\u01f2\3\2\2\2\u01f3\u01f4\3\2\2\2\u01f4")
        buf.write("\u01f5\3\2\2\2\u01f5\u0205\7L\2\2\u01f6\u01f8\7L\2\2\u01f7")
        buf.write("\u01f6\3\2\2\2\u01f7\u01f8\3\2\2\2\u01f8\u01f9\3\2\2\2")
        buf.write("\u01f9\u01fb\7\f\2\2\u01fa\u01fc\t\4\2\2\u01fb\u01fa\3")
        buf.write("\2\2\2\u01fb\u01fc\3\2\2\2\u01fc\u01fe\3\2\2\2\u01fd\u01ff")
        buf.write("\7J\2\2\u01fe\u01fd\3\2\2\2\u01fe\u01ff\3\2\2\2\u01ff")
        buf.write("\u0200\3\2\2\2\u0200\u0201\7\20\2\2\u0201\u0202\5f\64")
        buf.write("\2\u0202\u0203\7-\2\2\u0203\u0205\3\2\2\2\u0204\u01d3")
        buf.write("\3\2\2\2\u0204\u01e1\3\2\2\2\u0204\u01eb\3\2\2\2\u0204")
        buf.write("\u01f7\3\2\2\2\u0205/\3\2\2\2\u0206\u0208\7L\2\2\u0207")
        buf.write("\u0206\3\2\2\2\u0207\u0208\3\2\2\2\u0208\u0209\3\2\2\2")
        buf.write("\u0209\u020a\7!\2\2\u020a\u020b\7\f\2\2\u020b\u020d\t")
        buf.write("\4\2\2\u020c\u020e\7J\2\2\u020d\u020c\3\2\2\2\u020d\u020e")
        buf.write("\3\2\2\2\u020e\u020f\3\2\2\2\u020f\u0210\7/\2\2\u0210")
        buf.write("\u0211\5H%\2\u0211\u0212\7\60\2\2\u0212\u0235\3\2\2\2")
        buf.write("\u0213\u0215\7L\2\2\u0214\u0213\3\2\2\2\u0214\u0215\3")
        buf.write("\2\2\2\u0215\u0216\3\2\2\2\u0216\u0217\7!\2\2\u0217\u0218")
        buf.write("\7\f\2\2\u0218\u0219\t\4\2\2\u0219\u021a\7\17\2\2\u021a")
        buf.write("\u021b\7J\2\2\u021b\u0235\7-\2\2\u021c\u021e\7L\2\2\u021d")
        buf.write("\u021c\3\2\2\2\u021d\u021e\3\2\2\2\u021e\u021f\3\2\2\2")
        buf.write("\u021f\u0220\7!\2\2\u0220\u0221\7\f\2\2\u0221\u0222\t")
        buf.write("\4\2\2\u0222\u0224\7\17\2\2\u0223\u0225\7J\2\2\u0224\u0223")
        buf.write("\3\2\2\2\u0224\u0225\3\2\2\2\u0225\u0226\3\2\2\2\u0226")
        buf.write("\u0235\7L\2\2\u0227\u0229\7L\2\2\u0228\u0227\3\2\2\2\u0228")
        buf.write("\u0229\3\2\2\2\u0229\u022a\3\2\2\2\u022a\u022b\7!\2\2")
        buf.write("\u022b\u022c\7\f\2\2\u022c\u022e\t\4\2\2\u022d\u022f\7")
        buf.write("J\2\2\u022e\u022d\3\2\2\2\u022e\u022f\3\2\2\2\u022f\u0230")
        buf.write("\3\2\2\2\u0230\u0231\7\20\2\2\u0231\u0232\5f\64\2\u0232")
        buf.write("\u0233\7-\2\2\u0233\u0235\3\2\2\2\u0234\u0207\3\2\2\2")
        buf.write("\u0234\u0214\3\2\2\2\u0234\u021d\3\2\2\2\u0234\u0228\3")
        buf.write("\2\2\2\u0235\61\3\2\2\2\u0236\u0238\7L\2\2\u0237\u0236")
        buf.write("\3\2\2\2\u0237\u0238\3\2\2\2\u0238\u0239\3\2\2\2\u0239")
        buf.write("\u023a\7\5\2\2\u023a\u023d\7J\2\2\u023b\u023c\7\7\2\2")
        buf.write("\u023c\u023e\7K\2\2\u023d\u023b\3\2\2\2\u023d\u023e\3")
        buf.write("\2\2\2\u023e\u023f\3\2\2\2\u023f\u0240\7-\2\2\u0240\63")
        buf.write("\3\2\2\2\u0241\u0242\7\3\2\2\u0242\u0243\7K\2\2\u0243")
        buf.write("\u0244\7\6\2\2\u0244\u0247\7J\2\2\u0245\u0246\7\7\2\2")
        buf.write("\u0246\u0248\7K\2\2\u0247\u0245\3\2\2\2\u0247\u0248\3")
        buf.write("\2\2\2\u0248\u0252\3\2\2\2\u0249\u024d\7/\2\2\u024a\u024c")
        buf.write("\5\66\34\2\u024b\u024a\3\2\2\2\u024c\u024f\3\2\2\2\u024d")
        buf.write("\u024b\3\2\2\2\u024d\u024e\3\2\2\2\u024e\u0250\3\2\2\2")
        buf.write("\u024f\u024d\3\2\2\2\u0250\u0253\7\60\2\2\u0251\u0253")
        buf.write("\7-\2\2\u0252\u0249\3\2\2\2\u0252\u0251\3\2\2\2\u0253")
        buf.write("\65\3\2\2\2\u0254\u0258\58\35\2\u0255\u0258\5> \2\u0256")
        buf.write("\u0258\7-\2\2\u0257\u0254\3\2\2\2\u0257\u0255\3\2\2\2")
        buf.write("\u0257\u0256\3\2\2\2\u0258\67\3\2\2\2\u0259\u025a\7\4")
        buf.write("\2\2\u025a\u025b\5:\36\2\u025b\u025c\7,\2\2\u025c\u025d")
        buf.write("\5<\37\2\u025d\u025e\7-\2\2\u025e9\3\2\2\2\u025f\u026d")
        buf.write("\79\2\2\u0260\u0261\7/\2\2\u0261\u0266\7J\2\2\u0262\u0263")
        buf.write("\7.\2\2\u0263\u0265\7J\2\2\u0264\u0262\3\2\2\2\u0265\u0268")
        buf.write("\3\2\2\2\u0266\u0264\3\2\2\2\u0266\u0267\3\2\2\2\u0267")
        buf.write("\u0269\3\2\2\2\u0268\u0266\3\2\2\2\u0269\u026d\7\60\2")
        buf.write("\2\u026a\u026d\7]\2\2\u026b\u026d\7J\2\2\u026c\u025f\3")
        buf.write("\2\2\2\u026c\u0260\3\2\2\2\u026c\u026a\3\2\2\2\u026c\u026b")
        buf.write("\3\2\2\2\u026d;\3\2\2\2\u026e\u0272\7J\2\2\u026f\u0272")
        buf.write("\7b\2\2\u0270\u0272\79\2\2\u0271\u026e\3\2\2\2\u0271\u026f")
        buf.write("\3\2\2\2\u0271\u0270\3\2\2\2\u0272=\3\2\2\2\u0273\u0274")
        buf.write("\7\5\2\2\u0274\u0275\5f\64\2\u0275\u0276\7,\2\2\u0276")
        buf.write("\u0279\5f\64\2\u0277\u0278\7\7\2\2\u0278\u027a\7K\2\2")
        buf.write("\u0279\u0277\3\2\2\2\u0279\u027a\3\2\2\2\u027a\u027b\3")
        buf.write("\2\2\2\u027b\u027c\7-\2\2\u027c?\3\2\2\2\u027d\u027e\7")
        buf.write("J\2\2\u027e\u027f\7C\2\2\u027f\u0280\5\\/\2\u0280\u0281")
        buf.write("\7-\2\2\u0281A\3\2\2\2\u0282\u0283\7/\2\2\u0283\u0284")
        buf.write("\5H%\2\u0284\u0285\7\60\2\2\u0285C\3\2\2\2\u0286\u0287")
        buf.write("\7\22\2\2\u0287\u0288\7\61\2\2\u0288\u0289\5^\60\2\u0289")
        buf.write('\u028a\7\62\2\2\u028a\u0294\5B"\2\u028b\u028c\7\23\2')
        buf.write("\2\u028c\u028d\7\22\2\2\u028d\u028e\7\61\2\2\u028e\u028f")
        buf.write('\5^\60\2\u028f\u0290\7\62\2\2\u0290\u0291\5B"\2\u0291')
        buf.write("\u0293\3\2\2\2\u0292\u028b\3\2\2\2\u0293\u0296\3\2\2\2")
        buf.write("\u0294\u0292\3\2\2\2\u0294\u0295\3\2\2\2\u0295\u0299\3")
        buf.write("\2\2\2\u0296\u0294\3\2\2\2\u0297\u0298\7\23\2\2\u0298")
        buf.write('\u029a\5B"\2\u0299\u0297\3\2\2\2\u0299\u029a\3\2\2\2')
        buf.write("\u029aE\3\2\2\2\u029b\u029f\5@!\2\u029c\u029f\5D#\2\u029d")
        buf.write("\u029f\7-\2\2\u029e\u029b\3\2\2\2\u029e\u029c\3\2\2\2")
        buf.write("\u029e\u029d\3\2\2\2\u029fG\3\2\2\2\u02a0\u02a2\5F$\2")
        buf.write("\u02a1\u02a0\3\2\2\2\u02a2\u02a5\3\2\2\2\u02a3\u02a1\3")
        buf.write("\2\2\2\u02a3\u02a4\3\2\2\2\u02a4I\3\2\2\2\u02a5\u02a3")
        buf.write("\3\2\2\2\u02a6\u02b1\5\b\5\2\u02a7\u02b1\5\n\6\2\u02a8")
        buf.write("\u02b1\5(\25\2\u02a9\u02b1\5*\26\2\u02aa\u02b1\5.\30\2")
        buf.write("\u02ab\u02b1\5,\27\2\u02ac\u02b1\5\60\31\2\u02ad\u02b1")
        buf.write("\5\62\32\2\u02ae\u02b1\5\64\33\2\u02af\u02b1\7-\2\2\u02b0")
        buf.write("\u02a6\3\2\2\2\u02b0\u02a7\3\2\2\2\u02b0\u02a8\3\2\2\2")
        buf.write("\u02b0\u02a9\3\2\2\2\u02b0\u02aa\3\2\2\2\u02b0\u02ab\3")
        buf.write("\2\2\2\u02b0\u02ac\3\2\2\2\u02b0\u02ad\3\2\2\2\u02b0\u02ae")
        buf.write("\3\2\2\2\u02b0\u02af\3\2\2\2\u02b1K\3\2\2\2\u02b2\u02b4")
        buf.write("\5V,\2\u02b3\u02b2\3\2\2\2\u02b4\u02b7\3\2\2\2\u02b5\u02b3")
        buf.write("\3\2\2\2\u02b5\u02b6\3\2\2\2\u02b6\u02b8\3\2\2\2\u02b7")
        buf.write("\u02b5\3\2\2\2\u02b8\u02b9\7\2\2\3\u02b9M\3\2\2\2\u02ba")
        buf.write("\u02bc\5P)\2\u02bb\u02ba\3\2\2\2\u02bc\u02bf\3\2\2\2\u02bd")
        buf.write("\u02bb\3\2\2\2\u02bd\u02be\3\2\2\2\u02be\u02c0\3\2\2\2")
        buf.write("\u02bf\u02bd\3\2\2\2\u02c0\u02c1\7\2\2\3\u02c1O\3\2\2")
        buf.write("\2\u02c2\u02c5\5R*\2\u02c3\u02c5\5T+\2\u02c4\u02c2\3\2")
        buf.write("\2\2\u02c4\u02c3\3\2\2\2\u02c5Q\3\2\2\2\u02c6\u02c7\7")
        buf.write("J\2\2\u02c7\u02c8\7*\2\2\u02c8\u02c9\5Z.\2\u02c9\u02ca")
        buf.write("\7-\2\2\u02caS\3\2\2\2\u02cb\u02cc\7J\2\2\u02cc\u02cd")
        buf.write("\7C\2\2\u02cd\u02ce\5Z.\2\u02ce\u02cf\7-\2\2\u02cfU\3")
        buf.write("\2\2\2\u02d0\u02d1\7J\2\2\u02d1\u02d2\7*\2\2\u02d2\u02d3")
        buf.write("\5\\/\2\u02d3\u02d4\7-\2\2\u02d4W\3\2\2\2\u02d5\u02d8")
        buf.write("\5\\/\2\u02d6\u02d8\5^\60\2\u02d7\u02d5\3\2\2\2\u02d7")
        buf.write("\u02d6\3\2\2\2\u02d8Y\3\2\2\2\u02d9\u02da\b.\1\2\u02da")
        buf.write("\u02db\7\63\2\2\u02db\u02dc\5Z.\2\u02dc\u02dd\7\64\2\2")
        buf.write("\u02dd\u02e8\3\2\2\2\u02de\u02e8\5`\61\2\u02df\u02e8\5")
        buf.write("d\63\2\u02e0\u02e1\t\5\2\2\u02e1\u02e8\5Z.\13\u02e2\u02e3")
        buf.write("\7I\2\2\u02e3\u02e4\7\63\2\2\u02e4\u02e5\5Z.\2\u02e5\u02e6")
        buf.write("\7\64\2\2\u02e6\u02e8\3\2\2\2\u02e7\u02d9\3\2\2\2\u02e7")
        buf.write("\u02de\3\2\2\2\u02e7\u02df\3\2\2\2\u02e7\u02e0\3\2\2\2")
        buf.write("\u02e7\u02e2\3\2\2\2\u02e8\u0300\3\2\2\2\u02e9\u02ea\f")
        buf.write("\n\2\2\u02ea\u02eb\7 \2\2\u02eb\u02ff\5Z.\n\u02ec\u02ed")
        buf.write("\f\t\2\2\u02ed\u02ee\t\6\2\2\u02ee\u02ff\5Z.\n\u02ef\u02f0")
        buf.write("\f\b\2\2\u02f0\u02f1\t\5\2\2\u02f1\u02ff\5Z.\t\u02f2\u02f3")
        buf.write("\f\7\2\2\u02f3\u02f4\t\7\2\2\u02f4\u02ff\5Z.\b\u02f5\u02f6")
        buf.write("\f\6\2\2\u02f6\u02f7\7>\2\2\u02f7\u02ff\5Z.\7\u02f8\u02f9")
        buf.write("\f\5\2\2\u02f9\u02fa\7?\2\2\u02fa\u02ff\5Z.\6\u02fb\u02fc")
        buf.write("\f\4\2\2\u02fc\u02fd\7@\2\2\u02fd\u02ff\5Z.\5\u02fe\u02e9")
        buf.write("\3\2\2\2\u02fe\u02ec\3\2\2\2\u02fe\u02ef\3\2\2\2\u02fe")
        buf.write("\u02f2\3\2\2\2\u02fe\u02f5\3\2\2\2\u02fe\u02f8\3\2\2\2")
        buf.write("\u02fe\u02fb\3\2\2\2\u02ff\u0302\3\2\2\2\u0300\u02fe\3")
        buf.write("\2\2\2\u0300\u0301\3\2\2\2\u0301[\3\2\2\2\u0302\u0300")
        buf.write("\3\2\2\2\u0303\u0304\b/\1\2\u0304\u0305\7\63\2\2\u0305")
        buf.write("\u0306\5\\/\2\u0306\u0307\7\64\2\2\u0307\u031b\3\2\2\2")
        buf.write("\u0308\u031b\5`\61\2\u0309\u031b\7J\2\2\u030a\u031b\5")
        buf.write("d\63\2\u030b\u030c\t\5\2\2\u030c\u031b\5\\/\f\u030d\u030e")
        buf.write("\7I\2\2\u030e\u030f\7\63\2\2\u030f\u0310\5\\/\2\u0310")
        buf.write("\u0311\7\64\2\2\u0311\u031b\3\2\2\2\u0312\u0313\7\63\2")
        buf.write("\2\u0313\u0314\5^\60\2\u0314\u0315\7\64\2\2\u0315\u0316")
        buf.write("\7\65\2\2\u0316\u0317\5\\/\2\u0317\u0318\7\66\2\2\u0318")
        buf.write("\u0319\5\\/\3\u0319\u031b\3\2\2\2\u031a\u0303\3\2\2\2")
        buf.write("\u031a\u0308\3\2\2\2\u031a\u0309\3\2\2\2\u031a\u030a\3")
        buf.write("\2\2\2\u031a\u030b\3\2\2\2\u031a\u030d\3\2\2\2\u031a\u0312")
        buf.write("\3\2\2\2\u031b\u0333\3\2\2\2\u031c\u031d\f\13\2\2\u031d")
        buf.write("\u031e\7 \2\2\u031e\u0332\5\\/\13\u031f\u0320\f\n\2\2")
        buf.write("\u0320\u0321\t\6\2\2\u0321\u0332\5\\/\13\u0322\u0323\f")
        buf.write("\t\2\2\u0323\u0324\t\5\2\2\u0324\u0332\5\\/\n\u0325\u0326")
        buf.write("\f\b\2\2\u0326\u0327\t\7\2\2\u0327\u0332\5\\/\t\u0328")
        buf.write("\u0329\f\7\2\2\u0329\u032a\7>\2\2\u032a\u0332\5\\/\b\u032b")
        buf.write("\u032c\f\6\2\2\u032c\u032d\7?\2\2\u032d\u0332\5\\/\7\u032e")
        buf.write("\u032f\f\5\2\2\u032f\u0330\7@\2\2\u0330\u0332\5\\/\6\u0331")
        buf.write("\u031c\3\2\2\2\u0331\u031f\3\2\2\2\u0331\u0322\3\2\2\2")
        buf.write("\u0331\u0325\3\2\2\2\u0331\u0328\3\2\2\2\u0331\u032b\3")
        buf.write("\2\2\2\u0331\u032e\3\2\2\2\u0332\u0335\3\2\2\2\u0333\u0331")
        buf.write("\3\2\2\2\u0333\u0334\3\2\2\2\u0334]\3\2\2\2\u0335\u0333")
        buf.write("\3\2\2\2\u0336\u0337\b\60\1\2\u0337\u0338\7\63\2\2\u0338")
        buf.write("\u0339\5^\60\2\u0339\u033a\7\64\2\2\u033a\u034f\3\2\2")
        buf.write("\2\u033b\u034f\5b\62\2\u033c\u033d\t\b\2\2\u033d\u034f")
        buf.write("\5^\60\13\u033e\u033f\5\\/\2\u033f\u0340\t\t\2\2\u0340")
        buf.write("\u0341\5\\/\2\u0341\u034f\3\2\2\2\u0342\u0343\5\\/\2\u0343")
        buf.write("\u0344\t\n\2\2\u0344\u0345\5\\/\2\u0345\u034f\3\2\2\2")
        buf.write("\u0346\u0347\7\63\2\2\u0347\u0348\5^\60\2\u0348\u0349")
        buf.write("\7\64\2\2\u0349\u034a\7\65\2\2\u034a\u034b\5^\60\2\u034b")
        buf.write("\u034c\7\66\2\2\u034c\u034d\5^\60\3\u034d\u034f\3\2\2")
        buf.write("\2\u034e\u0336\3\2\2\2\u034e\u033b\3\2\2\2\u034e\u033c")
        buf.write("\3\2\2\2\u034e\u033e\3\2\2\2\u034e\u0342\3\2\2\2\u034e")
        buf.write("\u0346\3\2\2\2\u034f\u0361\3\2\2\2\u0350\u0351\f\b\2\2")
        buf.write("\u0351\u0352\t\13\2\2\u0352\u0360\5^\60\t\u0353\u0354")
        buf.write("\f\7\2\2\u0354\u0355\t\f\2\2\u0355\u0360\5^\60\b\u0356")
        buf.write("\u0357\f\6\2\2\u0357\u0358\7\36\2\2\u0358\u0360\5^\60")
        buf.write("\7\u0359\u035a\f\5\2\2\u035a\u035b\t\r\2\2\u035b\u0360")
        buf.write("\5^\60\6\u035c\u035d\f\4\2\2\u035d\u035e\t\16\2\2\u035e")
        buf.write("\u0360\5^\60\4\u035f\u0350\3\2\2\2\u035f\u0353\3\2\2\2")
        buf.write("\u035f\u0356\3\2\2\2\u035f\u0359\3\2\2\2\u035f\u035c\3")
        buf.write("\2\2\2\u0360\u0363\3\2\2\2\u0361\u035f\3\2\2\2\u0361\u0362")
        buf.write("\3\2\2\2\u0362_\3\2\2\2\u0363\u0361\3\2\2\2\u0364\u0365")
        buf.write("\t\17\2\2\u0365a\3\2\2\2\u0366\u0367\t\20\2\2\u0367c\3")
        buf.write("\2\2\2\u0368\u0369\t\21\2\2\u0369e\3\2\2\2\u036a\u036c")
        buf.write("\78\2\2\u036b\u036a\3\2\2\2\u036b\u036c\3\2\2\2\u036c")
        buf.write("\u036d\3\2\2\2\u036d\u0372\7J\2\2\u036e\u036f\7\67\2\2")
        buf.write("\u036f\u0371\7J\2\2\u0370\u036e\3\2\2\2\u0371\u0374\3")
        buf.write("\2\2\2\u0372\u0370\3\2\2\2\u0372\u0373\3\2\2\2\u0373g")
        buf.write("\3\2\2\2\u0374\u0372\3\2\2\2lnu\177\u0082\u0088\u008c")
        buf.write("\u008f\u0095\u009b\u009f\u00a2\u00a8\u00b0\u00b3\u00b9")
        buf.write("\u00c1\u00c4\u00ca\u00d2\u00d4\u00e0\u00e5\u00ed\u00f5")
        buf.write("\u0101\u0106\u010e\u0116\u0122\u0126\u012c\u0135\u0145")
        buf.write("\u0149\u0159\u015d\u016b\u016f\u017d\u0180\u0183\u0187")
        buf.write("\u018e\u0195\u019a\u019e\u01a2\u01a8\u01ab\u01af\u01b6")
        buf.write("\u01bd\u01c2\u01c6\u01ca\u01d0\u01d3\u01d7\u01da\u01e1")
        buf.write("\u01e5\u01eb\u01ef\u01f3\u01f7\u01fb\u01fe\u0204\u0207")
        buf.write("\u020d\u0214\u021d\u0224\u0228\u022e\u0234\u0237\u023d")
        buf.write("\u0247\u024d\u0252\u0257\u0266\u026c\u0271\u0279\u0294")
        buf.write("\u0299\u029e\u02a3\u02b0\u02b5\u02bd\u02c4\u02d7\u02e7")
        buf.write("\u02fe\u0300\u031a\u0331\u0333\u034e\u035f\u0361\u036b")
        buf.write("\u0372")
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
        "UNTERMINATED_MULTILINE_COMMENT",
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
    UNTERMINATED_MULTILINE_COMMENT = 75
    LINE_COMMENT = 76
    PYTHON_COMMENT = 77
    WS = 78
    IMPORT_HEADER_WS = 79
    IMPORT_HEADER_MULTILINE_COMMENT = 80
    IMPORT_HEADER_LINE_COMMENT = 81
    IMPORT_HEADER_PYTHON_COMMENT = 82
    IMPORT_BLOCK_WS = 83
    IMPORT_BLOCK_MULTILINE_COMMENT = 84
    IMPORT_BLOCK_LINE_COMMENT = 85
    IMPORT_BLOCK_PYTHON_COMMENT = 86
    IMPORT_DEF_SELECTOR_WS = 87
    IMPORT_DEF_SELECTOR_MULTILINE_COMMENT = 88
    IMPORT_DEF_SELECTOR_LINE_COMMENT = 89
    IMPORT_DEF_SELECTOR_PYTHON_COMMENT = 90
    IMPORT_DEF_SELECTOR_PATTERN = 91
    IMPORT_DEF_TARGET_WS = 92
    IMPORT_DEF_TARGET_MULTILINE_COMMENT = 93
    IMPORT_DEF_TARGET_LINE_COMMENT = 94
    IMPORT_DEF_TARGET_PYTHON_COMMENT = 95
    IMPORT_DEF_TARGET_TEMPLATE = 96

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
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 108
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 0, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 105
                    self.def_assignment()
                self.state = 110
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 0, self._ctx)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.state = 115
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.MULTILINE_COMMENT:
                self.state = 114
                localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

            self.state = 117
            self.match(GrammarParser.DEF)
            self.state = 118
            localctx.deftype = self._input.LT(1)
            _la = self._input.LA(1)
            if not (_la == GrammarParser.INT_TYPE or _la == GrammarParser.FLOAT_TYPE):
                localctx.deftype = self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 119
            self.match(GrammarParser.ID)
            self.state = 120
            self.match(GrammarParser.ASSIGN)
            self.state = 121
            self.init_expression(0)
            self.state = 122
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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.state = 157
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 9, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.LeafStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 125
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 124
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 128
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.PSEUDO:
                    self.state = 127
                    localctx.pseudo = self.match(GrammarParser.PSEUDO)

                self.state = 130
                self.match(GrammarParser.STATE)
                self.state = 131
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 134
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.NAMED:
                    self.state = 132
                    self.match(GrammarParser.NAMED)
                    self.state = 133
                    localctx.extra_name = self.match(GrammarParser.STRING)

                self.state = 136
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 2:
                localctx = GrammarParser.CompositeStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 138
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 137
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 141
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.PSEUDO:
                    self.state = 140
                    localctx.pseudo = self.match(GrammarParser.PSEUDO)

                self.state = 143
                self.match(GrammarParser.STATE)
                self.state = 144
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 147
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.NAMED:
                    self.state = 145
                    self.match(GrammarParser.NAMED)
                    self.state = 146
                    localctx.extra_name = self.match(GrammarParser.STRING)

                self.state = 149
                self.match(GrammarParser.LBRACE)
                self.state = 153
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while (
                    (
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
                    )
                    or _la == GrammarParser.ID
                    or _la == GrammarParser.MULTILINE_COMMENT
                ):
                    self.state = 150
                    self.state_inner_statement()
                    self.state = 155
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 156
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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.state = 210
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 19, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EntryTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 160
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 159
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 162
                self.match(GrammarParser.INIT_MARKER)
                self.state = 163
                self.match(GrammarParser.ARROW)
                self.state = 164
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 166
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON:
                    self.state = 165
                    self.entry_combo_transition_trigger()

                self.state = 174
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.SEMI]:
                    self.state = 168
                    self.match(GrammarParser.SEMI)
                    pass
                elif token in [GrammarParser.EFFECT]:
                    self.state = 169
                    self.match(GrammarParser.EFFECT)
                    self.state = 170
                    self.match(GrammarParser.LBRACE)
                    self.state = 171
                    self.operational_statement_set()
                    self.state = 172
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
                self.state = 177
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 176
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 179
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 180
                self.match(GrammarParser.ARROW)
                self.state = 181
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 183
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON:
                    self.state = 182
                    self.combo_transition_trigger()

                self.state = 191
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.SEMI]:
                    self.state = 185
                    self.match(GrammarParser.SEMI)
                    pass
                elif token in [GrammarParser.EFFECT]:
                    self.state = 186
                    self.match(GrammarParser.EFFECT)
                    self.state = 187
                    self.match(GrammarParser.LBRACE)
                    self.state = 188
                    self.operational_statement_set()
                    self.state = 189
                    self.match(GrammarParser.RBRACE)
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 3:
                localctx = GrammarParser.ExitTransitionDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 194
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 193
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 196
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 197
                self.match(GrammarParser.ARROW)
                self.state = 198
                self.match(GrammarParser.INIT_MARKER)
                self.state = 200
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON:
                    self.state = 199
                    self.combo_transition_trigger()

                self.state = 208
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.SEMI]:
                    self.state = 202
                    self.match(GrammarParser.SEMI)
                    pass
                elif token in [GrammarParser.EFFECT]:
                    self.state = 203
                    self.match(GrammarParser.EFFECT)
                    self.state = 204
                    self.match(GrammarParser.LBRACE)
                    self.state = 205
                    self.operational_statement_set()
                    self.state = 206
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
            self.state = 222
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 20, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 212
                self.match(GrammarParser.COLONCOLON)
                self.state = 213
                self.entry_chain_combo_trigger()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 214
                self.match(GrammarParser.COLON)
                self.state = 215
                self.match(GrammarParser.IF)
                self.state = 216
                self.match(GrammarParser.LBRACK)
                self.state = 217
                self.cond_expression(0)
                self.state = 218
                self.match(GrammarParser.RBRACK)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 220
                self.match(GrammarParser.COLON)
                self.state = 221
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
            self.state = 227
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.LBRACK:
                self.state = 224
                self.entry_chain_combo_leading_guard()
                self.state = 229
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 230
            self.combo_event_term()
            self.state = 235
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.PLUS:
                self.state = 231
                self.match(GrammarParser.PLUS)
                self.state = 232
                self.entry_chain_combo_trigger_term()
                self.state = 237
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
            self.state = 238
            self.combo_guard_term()
            self.state = 239
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
            self.state = 243
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.SLASH, GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 241
                self.combo_event_term()
                pass
            elif token in [GrammarParser.LBRACK]:
                self.enterOuterAlt(localctx, 2)
                self.state = 242
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
            self.state = 255
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 24, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 245
                self.match(GrammarParser.COLONCOLON)
                self.state = 246
                self.local_combo_trigger()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 247
                self.match(GrammarParser.COLON)
                self.state = 248
                self.match(GrammarParser.IF)
                self.state = 249
                self.match(GrammarParser.LBRACK)
                self.state = 250
                self.cond_expression(0)
                self.state = 251
                self.match(GrammarParser.RBRACK)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 253
                self.match(GrammarParser.COLON)
                self.state = 254
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
            self.state = 260
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.LBRACK:
                self.state = 257
                self.local_combo_leading_guard()
                self.state = 262
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 263
            self.local_combo_event_term()
            self.state = 268
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.PLUS:
                self.state = 264
                self.match(GrammarParser.PLUS)
                self.state = 265
                self.local_combo_trigger_term()
                self.state = 270
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
            self.state = 271
            self.combo_guard_term()
            self.state = 272
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
            self.state = 276
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 274
                self.local_combo_event_term()
                pass
            elif token in [GrammarParser.LBRACK]:
                self.enterOuterAlt(localctx, 2)
                self.state = 275
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
            self.state = 278
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
            self.state = 292
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 29, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 280
                self.chain_combo_guard_alias()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 281
                self.combo_trigger_term()
                self.state = 282
                self.match(GrammarParser.PLUS)
                self.state = 283
                self.combo_trigger_term()
                self.state = 288
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == GrammarParser.PLUS:
                    self.state = 284
                    self.match(GrammarParser.PLUS)
                    self.state = 285
                    self.combo_trigger_term()
                    self.state = 290
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 291
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
            self.state = 294
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
            self.state = 298
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.SLASH, GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 296
                self.combo_event_term()
                pass
            elif token in [GrammarParser.LBRACK]:
                self.enterOuterAlt(localctx, 2)
                self.state = 297
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
            self.state = 300
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
            self.state = 302
            self.match(GrammarParser.LBRACK)
            self.state = 303
            self.cond_expression(0)
            self.state = 304
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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.state = 382
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 39, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.NormalForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 307
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 306
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 309
                self.match(GrammarParser.BANG)
                self.state = 310
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 311
                self.match(GrammarParser.ARROW)
                self.state = 312
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 323
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 32, self._ctx)
                if la_ == 1:
                    self.state = 313
                    self.match(GrammarParser.COLONCOLON)
                    self.state = 314
                    localctx.from_id = self.match(GrammarParser.ID)

                elif la_ == 2:
                    self.state = 315
                    self.match(GrammarParser.COLON)
                    self.state = 316
                    self.chain_id()

                elif la_ == 3:
                    self.state = 317
                    self.match(GrammarParser.COLON)
                    self.state = 318
                    self.match(GrammarParser.IF)
                    self.state = 319
                    self.match(GrammarParser.LBRACK)
                    self.state = 320
                    self.cond_expression(0)
                    self.state = 321
                    self.match(GrammarParser.RBRACK)

                self.state = 325
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 2:
                localctx = GrammarParser.ExitForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 2)
                self.state = 327
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 326
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 329
                self.match(GrammarParser.BANG)
                self.state = 330
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 331
                self.match(GrammarParser.ARROW)
                self.state = 332
                self.match(GrammarParser.INIT_MARKER)
                self.state = 343
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 34, self._ctx)
                if la_ == 1:
                    self.state = 333
                    self.match(GrammarParser.COLONCOLON)
                    self.state = 334
                    localctx.from_id = self.match(GrammarParser.ID)

                elif la_ == 2:
                    self.state = 335
                    self.match(GrammarParser.COLON)
                    self.state = 336
                    self.chain_id()

                elif la_ == 3:
                    self.state = 337
                    self.match(GrammarParser.COLON)
                    self.state = 338
                    self.match(GrammarParser.IF)
                    self.state = 339
                    self.match(GrammarParser.LBRACK)
                    self.state = 340
                    self.cond_expression(0)
                    self.state = 341
                    self.match(GrammarParser.RBRACK)

                self.state = 345
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.NormalAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 3)
                self.state = 347
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 346
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 349
                self.match(GrammarParser.BANG)
                self.state = 350
                self.match(GrammarParser.STAR)
                self.state = 351
                self.match(GrammarParser.ARROW)
                self.state = 352
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 361
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 36, self._ctx)
                if la_ == 1:
                    self.state = 353
                    _la = self._input.LA(1)
                    if not (
                        _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON
                    ):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 354
                    self.chain_id()

                elif la_ == 2:
                    self.state = 355
                    self.match(GrammarParser.COLON)
                    self.state = 356
                    self.match(GrammarParser.IF)
                    self.state = 357
                    self.match(GrammarParser.LBRACK)
                    self.state = 358
                    self.cond_expression(0)
                    self.state = 359
                    self.match(GrammarParser.RBRACK)

                self.state = 363
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 4:
                localctx = GrammarParser.ExitAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 4)
                self.state = 365
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 364
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 367
                self.match(GrammarParser.BANG)
                self.state = 368
                self.match(GrammarParser.STAR)
                self.state = 369
                self.match(GrammarParser.ARROW)
                self.state = 370
                self.match(GrammarParser.INIT_MARKER)
                self.state = 379
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 38, self._ctx)
                if la_ == 1:
                    self.state = 371
                    _la = self._input.LA(1)
                    if not (
                        _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON
                    ):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 372
                    self.chain_id()

                elif la_ == 2:
                    self.state = 373
                    self.match(GrammarParser.COLON)
                    self.state = 374
                    self.match(GrammarParser.IF)
                    self.state = 375
                    self.match(GrammarParser.LBRACK)
                    self.state = 376
                    self.cond_expression(0)
                    self.state = 377
                    self.match(GrammarParser.RBRACK)

                self.state = 381
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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.MULTILINE_COMMENT)
            else:
                return self.getToken(GrammarParser.MULTILINE_COMMENT, i)

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
            self.state = 422
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 47, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EnterOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 385
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 384
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 387
                self.match(GrammarParser.ENTER)
                self.state = 389
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 388
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 391
                self.match(GrammarParser.LBRACE)
                self.state = 392
                self.operational_statement_set()
                self.state = 393
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 396
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 395
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 398
                self.match(GrammarParser.ENTER)
                self.state = 399
                self.match(GrammarParser.ABSTRACT)
                self.state = 400
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 401
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 403
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 402
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 405
                self.match(GrammarParser.ENTER)
                self.state = 406
                self.match(GrammarParser.ABSTRACT)
                self.state = 408
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 407
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 410
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.EnterRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 412
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 411
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 414
                self.match(GrammarParser.ENTER)
                self.state = 416
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 415
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 418
                self.match(GrammarParser.REF)
                self.state = 419
                self.chain_id()
                self.state = 420
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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.MULTILINE_COMMENT)
            else:
                return self.getToken(GrammarParser.MULTILINE_COMMENT, i)

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
            self.state = 462
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 55, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ExitOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 425
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 424
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 427
                self.match(GrammarParser.EXIT)
                self.state = 429
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 428
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 431
                self.match(GrammarParser.LBRACE)
                self.state = 432
                self.operational_statement_set()
                self.state = 433
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 436
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 435
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 438
                self.match(GrammarParser.EXIT)
                self.state = 439
                self.match(GrammarParser.ABSTRACT)
                self.state = 440
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 441
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 443
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 442
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 445
                self.match(GrammarParser.EXIT)
                self.state = 446
                self.match(GrammarParser.ABSTRACT)
                self.state = 448
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 447
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 450
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.ExitRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 452
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 451
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 454
                self.match(GrammarParser.EXIT)
                self.state = 456
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 455
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 458
                self.match(GrammarParser.REF)
                self.state = 459
                self.chain_id()
                self.state = 460
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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.MULTILINE_COMMENT)
            else:
                return self.getToken(GrammarParser.MULTILINE_COMMENT, i)

        def BEFORE(self):
            return self.getToken(GrammarParser.BEFORE, 0)

        def AFTER(self):
            return self.getToken(GrammarParser.AFTER, 0)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.state = 514
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 67, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.DuringOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 465
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 464
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 467
                self.match(GrammarParser.DURING)
                self.state = 469
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 468
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 472
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 471
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 474
                self.match(GrammarParser.LBRACE)
                self.state = 475
                self.operational_statement_set()
                self.state = 476
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 479
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 478
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 481
                self.match(GrammarParser.DURING)
                self.state = 483
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 482
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 485
                self.match(GrammarParser.ABSTRACT)
                self.state = 486
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 487
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 489
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 488
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 491
                self.match(GrammarParser.DURING)
                self.state = 493
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 492
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 495
                self.match(GrammarParser.ABSTRACT)
                self.state = 497
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 496
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 499
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.DuringRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 501
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 500
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 503
                self.match(GrammarParser.DURING)
                self.state = 505
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 504
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 508
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 507
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 510
                self.match(GrammarParser.REF)
                self.state = 511
                self.chain_id()
                self.state = 512
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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self, i: int = None):
            if i is None:
                return self.getTokens(GrammarParser.MULTILINE_COMMENT)
            else:
                return self.getToken(GrammarParser.MULTILINE_COMMENT, i)

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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.state = 562
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 75, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.DuringAspectOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 517
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 516
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 519
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 520
                self.match(GrammarParser.DURING)
                self.state = 521
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 523
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 522
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 525
                self.match(GrammarParser.LBRACE)
                self.state = 526
                self.operational_statement_set()
                self.state = 527
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 530
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 529
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 532
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 533
                self.match(GrammarParser.DURING)
                self.state = 534
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 535
                self.match(GrammarParser.ABSTRACT)
                self.state = 536
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 537
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 539
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 538
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 541
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 542
                self.match(GrammarParser.DURING)
                self.state = 543
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 544
                self.match(GrammarParser.ABSTRACT)
                self.state = 546
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 545
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 548
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.DuringAspectRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 550
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.MULTILINE_COMMENT:
                    self.state = 549
                    localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

                self.state = 552
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 553
                self.match(GrammarParser.DURING)
                self.state = 554
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 556
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 555
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 558
                self.match(GrammarParser.REF)
                self.state = 559
                self.chain_id()
                self.state = 560
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
            self.leading_doc = None  # Token
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

        def MULTILINE_COMMENT(self):
            return self.getToken(GrammarParser.MULTILINE_COMMENT, 0)

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
            self.state = 565
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.MULTILINE_COMMENT:
                self.state = 564
                localctx.leading_doc = self.match(GrammarParser.MULTILINE_COMMENT)

            self.state = 567
            self.match(GrammarParser.EVENT)
            self.state = 568
            localctx.event_name = self.match(GrammarParser.ID)
            self.state = 571
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.NAMED:
                self.state = 569
                self.match(GrammarParser.NAMED)
                self.state = 570
                localctx.extra_name = self.match(GrammarParser.STRING)

            self.state = 573
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
            self.state = 575
            self.match(GrammarParser.IMPORT)
            self.state = 576
            localctx.import_path = self.match(GrammarParser.STRING)
            self.state = 577
            self.match(GrammarParser.AS)
            self.state = 578
            localctx.state_alias = self.match(GrammarParser.ID)
            self.state = 581
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.NAMED:
                self.state = 579
                self.match(GrammarParser.NAMED)
                self.state = 580
                localctx.extra_name = self.match(GrammarParser.STRING)

            self.state = 592
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.LBRACE]:
                self.state = 583
                self.match(GrammarParser.LBRACE)
                self.state = 587
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
                    self.state = 584
                    self.import_mapping_statement()
                    self.state = 589
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 590
                self.match(GrammarParser.RBRACE)
                pass
            elif token in [GrammarParser.SEMI]:
                self.state = 591
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
            self.state = 597
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.DEF]:
                self.enterOuterAlt(localctx, 1)
                self.state = 594
                self.import_def_mapping()
                pass
            elif token in [GrammarParser.EVENT]:
                self.enterOuterAlt(localctx, 2)
                self.state = 595
                self.import_event_mapping()
                pass
            elif token in [GrammarParser.SEMI]:
                self.enterOuterAlt(localctx, 3)
                self.state = 596
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
            self.state = 599
            self.match(GrammarParser.DEF)
            self.state = 600
            self.import_def_selector()
            self.state = 601
            self.match(GrammarParser.ARROW)
            self.state = 602
            self.import_def_target_template()
            self.state = 603
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
            self.state = 618
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.STAR]:
                localctx = GrammarParser.ImportDefFallbackSelectorContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 605
                self.match(GrammarParser.STAR)
                pass
            elif token in [GrammarParser.LBRACE]:
                localctx = GrammarParser.ImportDefSetSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 606
                self.match(GrammarParser.LBRACE)
                self.state = 607
                localctx._ID = self.match(GrammarParser.ID)
                localctx.selector_items.append(localctx._ID)
                self.state = 612
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == GrammarParser.COMMA:
                    self.state = 608
                    self.match(GrammarParser.COMMA)
                    self.state = 609
                    localctx._ID = self.match(GrammarParser.ID)
                    localctx.selector_items.append(localctx._ID)
                    self.state = 614
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 615
                self.match(GrammarParser.RBRACE)
                pass
            elif token in [GrammarParser.IMPORT_DEF_SELECTOR_PATTERN]:
                localctx = GrammarParser.ImportDefPatternSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 616
                localctx.selector_pattern = self.match(
                    GrammarParser.IMPORT_DEF_SELECTOR_PATTERN
                )
                pass
            elif token in [GrammarParser.ID]:
                localctx = GrammarParser.ImportDefExactSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 617
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
            self.state = 623
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 620
                localctx.target_text = self.match(GrammarParser.ID)
                pass
            elif token in [GrammarParser.IMPORT_DEF_TARGET_TEMPLATE]:
                self.enterOuterAlt(localctx, 2)
                self.state = 621
                localctx.target_text = self.match(
                    GrammarParser.IMPORT_DEF_TARGET_TEMPLATE
                )
                pass
            elif token in [GrammarParser.STAR]:
                self.enterOuterAlt(localctx, 3)
                self.state = 622
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
            self.state = 625
            self.match(GrammarParser.EVENT)
            self.state = 626
            localctx.source_event = self.chain_id()
            self.state = 627
            self.match(GrammarParser.ARROW)
            self.state = 628
            localctx.target_event = self.chain_id()
            self.state = 631
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.NAMED:
                self.state = 629
                self.match(GrammarParser.NAMED)
                self.state = 630
                localctx.extra_name = self.match(GrammarParser.STRING)

            self.state = 633
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
            self.state = 635
            self.match(GrammarParser.ID)
            self.state = 636
            self.match(GrammarParser.ASSIGN)
            self.state = 637
            self.num_expression(0)
            self.state = 638
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
            self.state = 640
            self.match(GrammarParser.LBRACE)
            self.state = 641
            self.operational_statement_set()
            self.state = 642
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
            self.state = 644
            self.match(GrammarParser.IF)
            self.state = 645
            self.match(GrammarParser.LBRACK)
            self.state = 646
            self.cond_expression(0)
            self.state = 647
            self.match(GrammarParser.RBRACK)
            self.state = 648
            self.operation_block()
            self.state = 658
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 86, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 649
                    self.match(GrammarParser.ELSE)
                    self.state = 650
                    self.match(GrammarParser.IF)
                    self.state = 651
                    self.match(GrammarParser.LBRACK)
                    self.state = 652
                    self.cond_expression(0)
                    self.state = 653
                    self.match(GrammarParser.RBRACK)
                    self.state = 654
                    self.operation_block()
                self.state = 660
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 86, self._ctx)

            self.state = 663
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.ELSE:
                self.state = 661
                self.match(GrammarParser.ELSE)
                self.state = 662
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
            self.state = 668
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 665
                self.operation_assignment()
                pass
            elif token in [GrammarParser.IF]:
                self.enterOuterAlt(localctx, 2)
                self.state = 666
                self.if_statement()
                pass
            elif token in [GrammarParser.SEMI]:
                self.enterOuterAlt(localctx, 3)
                self.state = 667
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
            self.state = 673
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
                self.state = 670
                self.operational_statement()
                self.state = 675
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
            self.state = 686
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 90, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 676
                self.state_definition()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 677
                self.transition_definition()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 678
                self.transition_force_definition()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 679
                self.enter_definition()
                pass

            elif la_ == 5:
                self.enterOuterAlt(localctx, 5)
                self.state = 680
                self.during_definition()
                pass

            elif la_ == 6:
                self.enterOuterAlt(localctx, 6)
                self.state = 681
                self.exit_definition()
                pass

            elif la_ == 7:
                self.enterOuterAlt(localctx, 7)
                self.state = 682
                self.during_aspect_definition()
                pass

            elif la_ == 8:
                self.enterOuterAlt(localctx, 8)
                self.state = 683
                self.event_definition()
                pass

            elif la_ == 9:
                self.enterOuterAlt(localctx, 9)
                self.state = 684
                self.import_statement()
                pass

            elif la_ == 10:
                self.enterOuterAlt(localctx, 10)
                self.state = 685
                self.match(GrammarParser.SEMI)
                pass

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
            self.state = 691
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 688
                self.operational_assignment()
                self.state = 693
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 694
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
            self.state = 699
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 696
                self.preamble_statement()
                self.state = 701
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 702
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
            self.state = 706
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 93, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 704
                self.initial_assignment()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 705
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
            self.state = 708
            self.match(GrammarParser.ID)
            self.state = 709
            self.match(GrammarParser.DECLARE_ASSIGN)
            self.state = 710
            self.init_expression(0)
            self.state = 711
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
            self.state = 713
            self.match(GrammarParser.ID)
            self.state = 714
            self.match(GrammarParser.ASSIGN)
            self.state = 715
            self.init_expression(0)
            self.state = 716
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
            self.state = 718
            self.match(GrammarParser.ID)
            self.state = 719
            self.match(GrammarParser.DECLARE_ASSIGN)
            self.state = 720
            self.num_expression(0)
            self.state = 721
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
            self.state = 725
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 94, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 723
                self.num_expression(0)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 724
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
            self.state = 741
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.LPAREN]:
                localctx = GrammarParser.ParenExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 728
                self.match(GrammarParser.LPAREN)
                self.state = 729
                self.init_expression(0)
                self.state = 730
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
                self.state = 732
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
                self.state = 733
                self.math_const()
                pass
            elif token in [GrammarParser.PLUS, GrammarParser.MINUS]:
                localctx = GrammarParser.UnaryExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 734
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.PLUS or _la == GrammarParser.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 735
                self.init_expression(9)
                pass
            elif token in [GrammarParser.UFUNC_NAME]:
                localctx = GrammarParser.FuncExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 736
                localctx.func_name = self.match(GrammarParser.UFUNC_NAME)
                self.state = 737
                self.match(GrammarParser.LPAREN)
                self.state = 738
                self.init_expression(0)
                self.state = 739
                self.match(GrammarParser.RPAREN)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 766
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 97, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 764
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 96, self._ctx)
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
                        self.state = 743
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 744
                        localctx.op = self.match(GrammarParser.POW)
                        self.state = 745
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
                        self.state = 746
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 747
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
                        self.state = 748
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
                        self.state = 749
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 750
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.PLUS or _la == GrammarParser.MINUS
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 751
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
                        self.state = 752
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 753
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
                        self.state = 754
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
                        self.state = 755
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 756
                        localctx.op = self.match(GrammarParser.AMP)
                        self.state = 757
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
                        self.state = 758
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 759
                        localctx.op = self.match(GrammarParser.CARET)
                        self.state = 760
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
                        self.state = 761
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 762
                        localctx.op = self.match(GrammarParser.PIPE)
                        self.state = 763
                        self.init_expression(3)
                        pass

                self.state = 768
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 97, self._ctx)

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
            self.state = 792
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 98, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 770
                self.match(GrammarParser.LPAREN)
                self.state = 771
                self.num_expression(0)
                self.state = 772
                self.match(GrammarParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 774
                self.num_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.IdExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 775
                self.match(GrammarParser.ID)
                pass

            elif la_ == 4:
                localctx = GrammarParser.MathConstExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 776
                self.math_const()
                pass

            elif la_ == 5:
                localctx = GrammarParser.UnaryExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 777
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.PLUS or _la == GrammarParser.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 778
                self.num_expression(10)
                pass

            elif la_ == 6:
                localctx = GrammarParser.FuncExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 779
                localctx.func_name = self.match(GrammarParser.UFUNC_NAME)
                self.state = 780
                self.match(GrammarParser.LPAREN)
                self.state = 781
                self.num_expression(0)
                self.state = 782
                self.match(GrammarParser.RPAREN)
                pass

            elif la_ == 7:
                localctx = GrammarParser.ConditionalCStyleExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 784
                self.match(GrammarParser.LPAREN)
                self.state = 785
                self.cond_expression(0)
                self.state = 786
                self.match(GrammarParser.RPAREN)
                self.state = 787
                self.match(GrammarParser.QUESTION)
                self.state = 788
                self.num_expression(0)
                self.state = 789
                self.match(GrammarParser.COLON)
                self.state = 790
                self.num_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 817
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 100, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 815
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 99, self._ctx)
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
                        self.state = 794
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 9)"
                            )
                        self.state = 795
                        localctx.op = self.match(GrammarParser.POW)
                        self.state = 796
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
                        self.state = 797
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 798
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
                        self.state = 799
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
                        self.state = 800
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 801
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.PLUS or _la == GrammarParser.MINUS
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 802
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
                        self.state = 803
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 804
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
                        self.state = 805
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
                        self.state = 806
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 807
                        localctx.op = self.match(GrammarParser.AMP)
                        self.state = 808
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
                        self.state = 809
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 810
                        localctx.op = self.match(GrammarParser.CARET)
                        self.state = 811
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
                        self.state = 812
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 813
                        localctx.op = self.match(GrammarParser.PIPE)
                        self.state = 814
                        self.num_expression(4)
                        pass

                self.state = 819
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 100, self._ctx)

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
            self.state = 844
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 101, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 821
                self.match(GrammarParser.LPAREN)
                self.state = 822
                self.cond_expression(0)
                self.state = 823
                self.match(GrammarParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 825
                self.bool_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.UnaryExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 826
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.NOT_KW or _la == GrammarParser.BANG):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 827
                self.cond_expression(9)
                pass

            elif la_ == 4:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 828
                self.num_expression(0)
                self.state = 829
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
                self.state = 830
                self.num_expression(0)
                pass

            elif la_ == 5:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 832
                self.num_expression(0)
                self.state = 833
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.EQ or _la == GrammarParser.NE):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 834
                self.num_expression(0)
                pass

            elif la_ == 6:
                localctx = GrammarParser.ConditionalCStyleCondNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 836
                self.match(GrammarParser.LPAREN)
                self.state = 837
                self.cond_expression(0)
                self.state = 838
                self.match(GrammarParser.RPAREN)
                self.state = 839
                self.match(GrammarParser.QUESTION)
                self.state = 840
                self.cond_expression(0)
                self.state = 841
                self.match(GrammarParser.COLON)
                self.state = 842
                self.cond_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 863
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 103, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 861
                    self._errHandler.sync(self)
                    la_ = self._interp.adaptivePredict(self._input, 102, self._ctx)
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
                        self.state = 846
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 847
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
                        self.state = 848
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
                        self.state = 849
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 850
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
                        self.state = 851
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
                        self.state = 852
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 853
                        localctx.op = self.match(GrammarParser.XOR_KW)
                        self.state = 854
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
                        self.state = 855
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 856
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
                        self.state = 857
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
                        self.state = 858
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 859
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
                        self.state = 860
                        self.cond_expression(2)
                        pass

                self.state = 865
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 103, self._ctx)

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
            self.state = 866
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
            self.state = 868
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
            self.state = 870
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
            self.state = 873
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.SLASH:
                self.state = 872
                localctx.isabs = self.match(GrammarParser.SLASH)

            self.state = 875
            self.match(GrammarParser.ID)
            self.state = 880
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.DOT:
                self.state = 876
                self.match(GrammarParser.DOT)
                self.state = 877
                self.match(GrammarParser.ID)
                self.state = 882
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
