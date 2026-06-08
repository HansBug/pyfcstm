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
        buf.write("\u02d0\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7")
        buf.write("\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r\4\16")
        buf.write("\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23\t\23")
        buf.write("\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30\4\31")
        buf.write("\t\31\4\32\t\32\4\33\t\33\4\34\t\34\4\35\t\35\4\36\t\36")
        buf.write('\4\37\t\37\4 \t \4!\t!\4"\t"\4#\t#\4$\t$\4%\t%\4&\t')
        buf.write("&\4'\t'\3\2\3\2\3\2\3\3\7\3S\n\3\f\3\16\3V\13\3\3\3")
        buf.write("\3\3\3\3\3\4\3\4\3\4\3\4\3\4\3\4\3\4\3\5\5\5c\n\5\3\5")
        buf.write("\3\5\3\5\3\5\5\5i\n\5\3\5\3\5\5\5m\n\5\3\5\3\5\3\5\3\5")
        buf.write("\5\5s\n\5\3\5\3\5\7\5w\n\5\f\5\16\5z\13\5\3\5\5\5}\n\5")
        buf.write("\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u008a")
        buf.write("\n\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u0092\n\6\3\6\3\6\3\6")
        buf.write("\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u00a1\n\6")
        buf.write("\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u00a9\n\6\3\6\3\6\3\6\3\6")
        buf.write("\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\3\6\5\6\u00b8\n\6\3\6")
        buf.write("\3\6\3\6\3\6\3\6\3\6\5\6\u00c0\n\6\5\6\u00c2\n\6\3\7\3")
        buf.write("\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\5\7")
        buf.write("\u00d2\n\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7")
        buf.write("\3\7\3\7\3\7\3\7\5\7\u00e3\n\7\3\7\3\7\3\7\3\7\3\7\3\7")
        buf.write("\3\7\3\7\3\7\3\7\3\7\3\7\3\7\5\7\u00f2\n\7\3\7\3\7\3\7")
        buf.write("\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\3\7\5\7\u0101\n\7")
        buf.write("\3\7\5\7\u0104\n\7\3\b\3\b\5\b\u0108\n\b\3\b\3\b\3\b\3")
        buf.write("\b\3\b\3\b\3\b\3\b\3\b\3\b\3\b\5\b\u0115\n\b\3\b\3\b\3")
        buf.write("\b\5\b\u011a\n\b\3\b\3\b\3\b\3\b\5\b\u0120\n\b\3\t\3\t")
        buf.write("\5\t\u0124\n\t\3\t\3\t\3\t\3\t\3\t\3\t\3\t\3\t\3\t\3\t")
        buf.write("\3\t\5\t\u0131\n\t\3\t\3\t\3\t\5\t\u0136\n\t\3\t\3\t\3")
        buf.write("\t\3\t\5\t\u013c\n\t\3\n\3\n\5\n\u0140\n\n\3\n\5\n\u0143")
        buf.write("\n\n\3\n\3\n\3\n\3\n\3\n\3\n\5\n\u014b\n\n\3\n\3\n\3\n")
        buf.write("\3\n\3\n\5\n\u0152\n\n\3\n\3\n\5\n\u0156\n\n\3\n\3\n\3")
        buf.write("\n\5\n\u015b\n\n\3\n\5\n\u015e\n\n\3\n\3\n\3\n\3\n\5\n")
        buf.write("\u0164\n\n\3\13\3\13\3\13\3\13\5\13\u016a\n\13\3\13\3")
        buf.write("\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13\3\13")
        buf.write("\3\13\3\13\3\13\5\13\u017b\n\13\3\13\3\13\3\13\3\13\3")
        buf.write("\13\5\13\u0182\n\13\3\13\3\13\3\13\3\13\5\13\u0188\n\13")
        buf.write("\3\f\3\f\3\f\3\f\5\f\u018e\n\f\3\f\3\f\3\r\3\r\3\r\3\r")
        buf.write("\3\r\3\r\5\r\u0198\n\r\3\r\3\r\7\r\u019c\n\r\f\r\16\r")
        buf.write("\u019f\13\r\3\r\3\r\5\r\u01a3\n\r\3\16\3\16\3\16\5\16")
        buf.write("\u01a8\n\16\3\17\3\17\3\17\3\17\3\17\3\17\3\20\3\20\3")
        buf.write("\20\3\20\3\20\7\20\u01b5\n\20\f\20\16\20\u01b8\13\20\3")
        buf.write("\20\3\20\3\20\5\20\u01bd\n\20\3\21\3\21\3\21\5\21\u01c2")
        buf.write("\n\21\3\22\3\22\3\22\3\22\3\22\3\22\5\22\u01ca\n\22\3")
        buf.write("\22\3\22\3\23\3\23\3\23\3\23\3\23\3\24\3\24\3\24\3\24")
        buf.write("\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25")
        buf.write("\3\25\7\25\u01e3\n\25\f\25\16\25\u01e6\13\25\3\25\3\25")
        buf.write("\5\25\u01ea\n\25\3\26\3\26\3\26\5\26\u01ef\n\26\3\27\7")
        buf.write("\27\u01f2\n\27\f\27\16\27\u01f5\13\27\3\30\3\30\3\30\3")
        buf.write("\30\3\30\3\30\3\30\3\30\3\30\3\30\5\30\u0201\n\30\3\31")
        buf.write("\7\31\u0204\n\31\f\31\16\31\u0207\13\31\3\31\3\31\3\32")
        buf.write("\7\32\u020c\n\32\f\32\16\32\u020f\13\32\3\32\3\32\3\33")
        buf.write("\3\33\5\33\u0215\n\33\3\34\3\34\3\34\3\34\3\34\3\35\3")
        buf.write("\35\3\35\3\35\3\35\3\36\3\36\3\36\3\36\3\36\3\37\3\37")
        buf.write("\5\37\u0228\n\37\3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3")
        buf.write(" \3 \5 \u0238\n \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3 \3")
        buf.write(" \3 \3 \3 \3 \3 \3 \3 \3 \7 \u024f\n \f \16 \u0252\13")
        buf.write(" \3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3")
        buf.write("!\3!\3!\3!\3!\3!\5!\u026b\n!\3!\3!\3!\3!\3!\3!\3!\3!\3")
        buf.write("!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\3!\7!\u0282\n!\f!\16")
        buf.write('!\u0285\13!\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3')
        buf.write('"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"')
        buf.write('\5"\u029f\n"\3"\3"\3"\3"\3"\3"\3"\3"\3"\3"')
        buf.write('\3"\3"\3"\3"\3"\3"\3"\3"\7"\u02b3\n"\f"\16')
        buf.write('"\u02b6\13"\3#\3#\3#\3#\3#\5#\u02bd\n#\3$\3$\3%\3%\3')
        buf.write("&\3&\3'\5'\u02c6\n'\3'\3'\3'\7'\u02cb\n'\f'\16")
        buf.write("'\u02ce\13'\3'\2\5>@B(\2\4\6\b\n\f\16\20\22\24\26\30")
        buf.write('\32\34\36 "$&(*,.\60\62\64\668:<>@BDFHJL\2\22\3\2\24')
        buf.write('\25\4\2++\66\66\3\2\r\16\3\2;<\4\289==\3\2!"\4\2\33\33')
        buf.write("::\4\2#$AB\3\2%&\4\2\35\35%&\4\2\31\31''\4\2\32\32(")
        buf.write("(\4\2\34\34))\3\2DF\3\2GH\3\2\26\30\2\u032b\2N\3\2\2\2")
        buf.write("\4T\3\2\2\2\6Z\3\2\2\2\b|\3\2\2\2\n\u00c1\3\2\2\2\f\u0103")
        buf.write("\3\2\2\2\16\u011f\3\2\2\2\20\u013b\3\2\2\2\22\u0163\3")
        buf.write("\2\2\2\24\u0187\3\2\2\2\26\u0189\3\2\2\2\30\u0191\3\2")
        buf.write("\2\2\32\u01a7\3\2\2\2\34\u01a9\3\2\2\2\36\u01bc\3\2\2")
        buf.write('\2 \u01c1\3\2\2\2"\u01c3\3\2\2\2$\u01cd\3\2\2\2&\u01d2')
        buf.write("\3\2\2\2(\u01d6\3\2\2\2*\u01ee\3\2\2\2,\u01f3\3\2\2\2")
        buf.write(".\u0200\3\2\2\2\60\u0205\3\2\2\2\62\u020d\3\2\2\2\64\u0214")
        buf.write("\3\2\2\2\66\u0216\3\2\2\28\u021b\3\2\2\2:\u0220\3\2\2")
        buf.write("\2<\u0227\3\2\2\2>\u0237\3\2\2\2@\u026a\3\2\2\2B\u029e")
        buf.write("\3\2\2\2D\u02bc\3\2\2\2F\u02be\3\2\2\2H\u02c0\3\2\2\2")
        buf.write('J\u02c2\3\2\2\2L\u02c5\3\2\2\2NO\5B"\2OP\7\2\2\3P\3\3')
        buf.write("\2\2\2QS\5\6\4\2RQ\3\2\2\2SV\3\2\2\2TR\3\2\2\2TU\3\2\2")
        buf.write("\2UW\3\2\2\2VT\3\2\2\2WX\5\b\5\2XY\7\2\2\3Y\5\3\2\2\2")
        buf.write("Z[\7\4\2\2[\\\t\2\2\2\\]\7J\2\2]^\7C\2\2^_\5> \2_`\7-")
        buf.write("\2\2`\7\3\2\2\2ac\7\b\2\2ba\3\2\2\2bc\3\2\2\2cd\3\2\2")
        buf.write("\2de\7\t\2\2eh\7J\2\2fg\7\7\2\2gi\7K\2\2hf\3\2\2\2hi\3")
        buf.write("\2\2\2ij\3\2\2\2j}\7-\2\2km\7\b\2\2lk\3\2\2\2lm\3\2\2")
        buf.write("\2mn\3\2\2\2no\7\t\2\2or\7J\2\2pq\7\7\2\2qs\7K\2\2rp\3")
        buf.write("\2\2\2rs\3\2\2\2st\3\2\2\2tx\7/\2\2uw\5.\30\2vu\3\2\2")
        buf.write("\2wz\3\2\2\2xv\3\2\2\2xy\3\2\2\2y{\3\2\2\2zx\3\2\2\2{")
        buf.write("}\7\60\2\2|b\3\2\2\2|l\3\2\2\2}\t\3\2\2\2~\177\7\37\2")
        buf.write("\2\177\u0080\7,\2\2\u0080\u0089\7J\2\2\u0081\u0082\t\3")
        buf.write("\2\2\u0082\u008a\5L'\2\u0083\u0084\7\66\2\2\u0084\u0085")
        buf.write('\7\22\2\2\u0085\u0086\7\61\2\2\u0086\u0087\5B"\2\u0087')
        buf.write("\u0088\7\62\2\2\u0088\u008a\3\2\2\2\u0089\u0081\3\2\2")
        buf.write("\2\u0089\u0083\3\2\2\2\u0089\u008a\3\2\2\2\u008a\u0091")
        buf.write("\3\2\2\2\u008b\u0092\7-\2\2\u008c\u008d\7\21\2\2\u008d")
        buf.write("\u008e\7/\2\2\u008e\u008f\5,\27\2\u008f\u0090\7\60\2\2")
        buf.write("\u0090\u0092\3\2\2\2\u0091\u008b\3\2\2\2\u0091\u008c\3")
        buf.write("\2\2\2\u0092\u00c2\3\2\2\2\u0093\u0094\7J\2\2\u0094\u0095")
        buf.write("\7,\2\2\u0095\u00a0\7J\2\2\u0096\u0097\7+\2\2\u0097\u00a1")
        buf.write("\7J\2\2\u0098\u0099\7\66\2\2\u0099\u00a1\5L'\2\u009a")
        buf.write("\u009b\7\66\2\2\u009b\u009c\7\22\2\2\u009c\u009d\7\61")
        buf.write('\2\2\u009d\u009e\5B"\2\u009e\u009f\7\62\2\2\u009f\u00a1')
        buf.write("\3\2\2\2\u00a0\u0096\3\2\2\2\u00a0\u0098\3\2\2\2\u00a0")
        buf.write("\u009a\3\2\2\2\u00a0\u00a1\3\2\2\2\u00a1\u00a8\3\2\2\2")
        buf.write("\u00a2\u00a9\7-\2\2\u00a3\u00a4\7\21\2\2\u00a4\u00a5\7")
        buf.write("/\2\2\u00a5\u00a6\5,\27\2\u00a6\u00a7\7\60\2\2\u00a7\u00a9")
        buf.write("\3\2\2\2\u00a8\u00a2\3\2\2\2\u00a8\u00a3\3\2\2\2\u00a9")
        buf.write("\u00c2\3\2\2\2\u00aa\u00ab\7J\2\2\u00ab\u00ac\7,\2\2\u00ac")
        buf.write("\u00b7\7\37\2\2\u00ad\u00ae\7+\2\2\u00ae\u00b8\7J\2\2")
        buf.write("\u00af\u00b0\7\66\2\2\u00b0\u00b8\5L'\2\u00b1\u00b2\7")
        buf.write("\66\2\2\u00b2\u00b3\7\22\2\2\u00b3\u00b4\7\61\2\2\u00b4")
        buf.write('\u00b5\5B"\2\u00b5\u00b6\7\62\2\2\u00b6\u00b8\3\2\2\2')
        buf.write("\u00b7\u00ad\3\2\2\2\u00b7\u00af\3\2\2\2\u00b7\u00b1\3")
        buf.write("\2\2\2\u00b7\u00b8\3\2\2\2\u00b8\u00bf\3\2\2\2\u00b9\u00c0")
        buf.write("\7-\2\2\u00ba\u00bb\7\21\2\2\u00bb\u00bc\7/\2\2\u00bc")
        buf.write("\u00bd\5,\27\2\u00bd\u00be\7\60\2\2\u00be\u00c0\3\2\2")
        buf.write("\2\u00bf\u00b9\3\2\2\2\u00bf\u00ba\3\2\2\2\u00c0\u00c2")
        buf.write("\3\2\2\2\u00c1~\3\2\2\2\u00c1\u0093\3\2\2\2\u00c1\u00aa")
        buf.write("\3\2\2\2\u00c2\13\3\2\2\2\u00c3\u00c4\7:\2\2\u00c4\u00c5")
        buf.write("\7J\2\2\u00c5\u00c6\7,\2\2\u00c6\u00d1\7J\2\2\u00c7\u00c8")
        buf.write("\7+\2\2\u00c8\u00d2\7J\2\2\u00c9\u00ca\7\66\2\2\u00ca")
        buf.write("\u00d2\5L'\2\u00cb\u00cc\7\66\2\2\u00cc\u00cd\7\22\2")
        buf.write('\2\u00cd\u00ce\7\61\2\2\u00ce\u00cf\5B"\2\u00cf\u00d0')
        buf.write("\7\62\2\2\u00d0\u00d2\3\2\2\2\u00d1\u00c7\3\2\2\2\u00d1")
        buf.write("\u00c9\3\2\2\2\u00d1\u00cb\3\2\2\2\u00d1\u00d2\3\2\2\2")
        buf.write("\u00d2\u00d3\3\2\2\2\u00d3\u0104\7-\2\2\u00d4\u00d5\7")
        buf.write(":\2\2\u00d5\u00d6\7J\2\2\u00d6\u00d7\7,\2\2\u00d7\u00e2")
        buf.write("\7\37\2\2\u00d8\u00d9\7+\2\2\u00d9\u00e3\7J\2\2\u00da")
        buf.write("\u00db\7\66\2\2\u00db\u00e3\5L'\2\u00dc\u00dd\7\66\2")
        buf.write("\2\u00dd\u00de\7\22\2\2\u00de\u00df\7\61\2\2\u00df\u00e0")
        buf.write('\5B"\2\u00e0\u00e1\7\62\2\2\u00e1\u00e3\3\2\2\2\u00e2')
        buf.write("\u00d8\3\2\2\2\u00e2\u00da\3\2\2\2\u00e2\u00dc\3\2\2\2")
        buf.write("\u00e2\u00e3\3\2\2\2\u00e3\u00e4\3\2\2\2\u00e4\u0104\7")
        buf.write("-\2\2\u00e5\u00e6\7:\2\2\u00e6\u00e7\79\2\2\u00e7\u00e8")
        buf.write("\7,\2\2\u00e8\u00f1\7J\2\2\u00e9\u00ea\t\3\2\2\u00ea\u00f2")
        buf.write("\5L'\2\u00eb\u00ec\7\66\2\2\u00ec\u00ed\7\22\2\2\u00ed")
        buf.write('\u00ee\7\61\2\2\u00ee\u00ef\5B"\2\u00ef\u00f0\7\62\2')
        buf.write("\2\u00f0\u00f2\3\2\2\2\u00f1\u00e9\3\2\2\2\u00f1\u00eb")
        buf.write("\3\2\2\2\u00f1\u00f2\3\2\2\2\u00f2\u00f3\3\2\2\2\u00f3")
        buf.write("\u0104\7-\2\2\u00f4\u00f5\7:\2\2\u00f5\u00f6\79\2\2\u00f6")
        buf.write("\u00f7\7,\2\2\u00f7\u0100\7\37\2\2\u00f8\u00f9\t\3\2\2")
        buf.write("\u00f9\u0101\5L'\2\u00fa\u00fb\7\66\2\2\u00fb\u00fc\7")
        buf.write('\22\2\2\u00fc\u00fd\7\61\2\2\u00fd\u00fe\5B"\2\u00fe')
        buf.write("\u00ff\7\62\2\2\u00ff\u0101\3\2\2\2\u0100\u00f8\3\2\2")
        buf.write("\2\u0100\u00fa\3\2\2\2\u0100\u0101\3\2\2\2\u0101\u0102")
        buf.write("\3\2\2\2\u0102\u0104\7-\2\2\u0103\u00c3\3\2\2\2\u0103")
        buf.write("\u00d4\3\2\2\2\u0103\u00e5\3\2\2\2\u0103\u00f4\3\2\2\2")
        buf.write("\u0104\r\3\2\2\2\u0105\u0107\7\n\2\2\u0106\u0108\7J\2")
        buf.write("\2\u0107\u0106\3\2\2\2\u0107\u0108\3\2\2\2\u0108\u0109")
        buf.write("\3\2\2\2\u0109\u010a\7/\2\2\u010a\u010b\5,\27\2\u010b")
        buf.write("\u010c\7\60\2\2\u010c\u0120\3\2\2\2\u010d\u010e\7\n\2")
        buf.write("\2\u010e\u010f\7\17\2\2\u010f\u0110\7J\2\2\u0110\u0120")
        buf.write("\7-\2\2\u0111\u0112\7\n\2\2\u0112\u0114\7\17\2\2\u0113")
        buf.write("\u0115\7J\2\2\u0114\u0113\3\2\2\2\u0114\u0115\3\2\2\2")
        buf.write("\u0115\u0116\3\2\2\2\u0116\u0120\7L\2\2\u0117\u0119\7")
        buf.write("\n\2\2\u0118\u011a\7J\2\2\u0119\u0118\3\2\2\2\u0119\u011a")
        buf.write("\3\2\2\2\u011a\u011b\3\2\2\2\u011b\u011c\7\20\2\2\u011c")
        buf.write("\u011d\5L'\2\u011d\u011e\7-\2\2\u011e\u0120\3\2\2\2\u011f")
        buf.write("\u0105\3\2\2\2\u011f\u010d\3\2\2\2\u011f\u0111\3\2\2\2")
        buf.write("\u011f\u0117\3\2\2\2\u0120\17\3\2\2\2\u0121\u0123\7\13")
        buf.write("\2\2\u0122\u0124\7J\2\2\u0123\u0122\3\2\2\2\u0123\u0124")
        buf.write("\3\2\2\2\u0124\u0125\3\2\2\2\u0125\u0126\7/\2\2\u0126")
        buf.write("\u0127\5,\27\2\u0127\u0128\7\60\2\2\u0128\u013c\3\2\2")
        buf.write("\2\u0129\u012a\7\13\2\2\u012a\u012b\7\17\2\2\u012b\u012c")
        buf.write("\7J\2\2\u012c\u013c\7-\2\2\u012d\u012e\7\13\2\2\u012e")
        buf.write("\u0130\7\17\2\2\u012f\u0131\7J\2\2\u0130\u012f\3\2\2\2")
        buf.write("\u0130\u0131\3\2\2\2\u0131\u0132\3\2\2\2\u0132\u013c\7")
        buf.write("L\2\2\u0133\u0135\7\13\2\2\u0134\u0136\7J\2\2\u0135\u0134")
        buf.write("\3\2\2\2\u0135\u0136\3\2\2\2\u0136\u0137\3\2\2\2\u0137")
        buf.write("\u0138\7\20\2\2\u0138\u0139\5L'\2\u0139\u013a\7-\2\2")
        buf.write("\u013a\u013c\3\2\2\2\u013b\u0121\3\2\2\2\u013b\u0129\3")
        buf.write("\2\2\2\u013b\u012d\3\2\2\2\u013b\u0133\3\2\2\2\u013c\21")
        buf.write("\3\2\2\2\u013d\u013f\7\f\2\2\u013e\u0140\t\4\2\2\u013f")
        buf.write("\u013e\3\2\2\2\u013f\u0140\3\2\2\2\u0140\u0142\3\2\2\2")
        buf.write("\u0141\u0143\7J\2\2\u0142\u0141\3\2\2\2\u0142\u0143\3")
        buf.write("\2\2\2\u0143\u0144\3\2\2\2\u0144\u0145\7/\2\2\u0145\u0146")
        buf.write("\5,\27\2\u0146\u0147\7\60\2\2\u0147\u0164\3\2\2\2\u0148")
        buf.write("\u014a\7\f\2\2\u0149\u014b\t\4\2\2\u014a\u0149\3\2\2\2")
        buf.write("\u014a\u014b\3\2\2\2\u014b\u014c\3\2\2\2\u014c\u014d\7")
        buf.write("\17\2\2\u014d\u014e\7J\2\2\u014e\u0164\7-\2\2\u014f\u0151")
        buf.write("\7\f\2\2\u0150\u0152\t\4\2\2\u0151\u0150\3\2\2\2\u0151")
        buf.write("\u0152\3\2\2\2\u0152\u0153\3\2\2\2\u0153\u0155\7\17\2")
        buf.write("\2\u0154\u0156\7J\2\2\u0155\u0154\3\2\2\2\u0155\u0156")
        buf.write("\3\2\2\2\u0156\u0157\3\2\2\2\u0157\u0164\7L\2\2\u0158")
        buf.write("\u015a\7\f\2\2\u0159\u015b\t\4\2\2\u015a\u0159\3\2\2\2")
        buf.write("\u015a\u015b\3\2\2\2\u015b\u015d\3\2\2\2\u015c\u015e\7")
        buf.write("J\2\2\u015d\u015c\3\2\2\2\u015d\u015e\3\2\2\2\u015e\u015f")
        buf.write("\3\2\2\2\u015f\u0160\7\20\2\2\u0160\u0161\5L'\2\u0161")
        buf.write("\u0162\7-\2\2\u0162\u0164\3\2\2\2\u0163\u013d\3\2\2\2")
        buf.write("\u0163\u0148\3\2\2\2\u0163\u014f\3\2\2\2\u0163\u0158\3")
        buf.write("\2\2\2\u0164\23\3\2\2\2\u0165\u0166\7!\2\2\u0166\u0167")
        buf.write("\7\f\2\2\u0167\u0169\t\4\2\2\u0168\u016a\7J\2\2\u0169")
        buf.write("\u0168\3\2\2\2\u0169\u016a\3\2\2\2\u016a\u016b\3\2\2\2")
        buf.write("\u016b\u016c\7/\2\2\u016c\u016d\5,\27\2\u016d\u016e\7")
        buf.write("\60\2\2\u016e\u0188\3\2\2\2\u016f\u0170\7!\2\2\u0170\u0171")
        buf.write("\7\f\2\2\u0171\u0172\t\4\2\2\u0172\u0173\7\17\2\2\u0173")
        buf.write("\u0174\7J\2\2\u0174\u0188\7-\2\2\u0175\u0176\7!\2\2\u0176")
        buf.write("\u0177\7\f\2\2\u0177\u0178\t\4\2\2\u0178\u017a\7\17\2")
        buf.write("\2\u0179\u017b\7J\2\2\u017a\u0179\3\2\2\2\u017a\u017b")
        buf.write("\3\2\2\2\u017b\u017c\3\2\2\2\u017c\u0188\7L\2\2\u017d")
        buf.write("\u017e\7!\2\2\u017e\u017f\7\f\2\2\u017f\u0181\t\4\2\2")
        buf.write("\u0180\u0182\7J\2\2\u0181\u0180\3\2\2\2\u0181\u0182\3")
        buf.write("\2\2\2\u0182\u0183\3\2\2\2\u0183\u0184\7\20\2\2\u0184")
        buf.write("\u0185\5L'\2\u0185\u0186\7-\2\2\u0186\u0188\3\2\2\2\u0187")
        buf.write("\u0165\3\2\2\2\u0187\u016f\3\2\2\2\u0187\u0175\3\2\2\2")
        buf.write("\u0187\u017d\3\2\2\2\u0188\25\3\2\2\2\u0189\u018a\7\5")
        buf.write("\2\2\u018a\u018d\7J\2\2\u018b\u018c\7\7\2\2\u018c\u018e")
        buf.write("\7K\2\2\u018d\u018b\3\2\2\2\u018d\u018e\3\2\2\2\u018e")
        buf.write("\u018f\3\2\2\2\u018f\u0190\7-\2\2\u0190\27\3\2\2\2\u0191")
        buf.write("\u0192\7\3\2\2\u0192\u0193\7K\2\2\u0193\u0194\7\6\2\2")
        buf.write("\u0194\u0197\7J\2\2\u0195\u0196\7\7\2\2\u0196\u0198\7")
        buf.write("K\2\2\u0197\u0195\3\2\2\2\u0197\u0198\3\2\2\2\u0198\u01a2")
        buf.write("\3\2\2\2\u0199\u019d\7/\2\2\u019a\u019c\5\32\16\2\u019b")
        buf.write("\u019a\3\2\2\2\u019c\u019f\3\2\2\2\u019d\u019b\3\2\2\2")
        buf.write("\u019d\u019e\3\2\2\2\u019e\u01a0\3\2\2\2\u019f\u019d\3")
        buf.write("\2\2\2\u01a0\u01a3\7\60\2\2\u01a1\u01a3\7-\2\2\u01a2\u0199")
        buf.write("\3\2\2\2\u01a2\u01a1\3\2\2\2\u01a3\31\3\2\2\2\u01a4\u01a8")
        buf.write('\5\34\17\2\u01a5\u01a8\5"\22\2\u01a6\u01a8\7-\2\2\u01a7')
        buf.write("\u01a4\3\2\2\2\u01a7\u01a5\3\2\2\2\u01a7\u01a6\3\2\2\2")
        buf.write("\u01a8\33\3\2\2\2\u01a9\u01aa\7\4\2\2\u01aa\u01ab\5\36")
        buf.write("\20\2\u01ab\u01ac\7,\2\2\u01ac\u01ad\5 \21\2\u01ad\u01ae")
        buf.write("\7-\2\2\u01ae\35\3\2\2\2\u01af\u01bd\79\2\2\u01b0\u01b1")
        buf.write("\7/\2\2\u01b1\u01b6\7J\2\2\u01b2\u01b3\7.\2\2\u01b3\u01b5")
        buf.write("\7J\2\2\u01b4\u01b2\3\2\2\2\u01b5\u01b8\3\2\2\2\u01b6")
        buf.write("\u01b4\3\2\2\2\u01b6\u01b7\3\2\2\2\u01b7\u01b9\3\2\2\2")
        buf.write("\u01b8\u01b6\3\2\2\2\u01b9\u01bd\7\60\2\2\u01ba\u01bd")
        buf.write("\7\\\2\2\u01bb\u01bd\7J\2\2\u01bc\u01af\3\2\2\2\u01bc")
        buf.write("\u01b0\3\2\2\2\u01bc\u01ba\3\2\2\2\u01bc\u01bb\3\2\2\2")
        buf.write("\u01bd\37\3\2\2\2\u01be\u01c2\7J\2\2\u01bf\u01c2\7a\2")
        buf.write("\2\u01c0\u01c2\79\2\2\u01c1\u01be\3\2\2\2\u01c1\u01bf")
        buf.write("\3\2\2\2\u01c1\u01c0\3\2\2\2\u01c2!\3\2\2\2\u01c3\u01c4")
        buf.write("\7\5\2\2\u01c4\u01c5\5L'\2\u01c5\u01c6\7,\2\2\u01c6\u01c9")
        buf.write("\5L'\2\u01c7\u01c8\7\7\2\2\u01c8\u01ca\7K\2\2\u01c9\u01c7")
        buf.write("\3\2\2\2\u01c9\u01ca\3\2\2\2\u01ca\u01cb\3\2\2\2\u01cb")
        buf.write("\u01cc\7-\2\2\u01cc#\3\2\2\2\u01cd\u01ce\7J\2\2\u01ce")
        buf.write("\u01cf\7C\2\2\u01cf\u01d0\5@!\2\u01d0\u01d1\7-\2\2\u01d1")
        buf.write("%\3\2\2\2\u01d2\u01d3\7/\2\2\u01d3\u01d4\5,\27\2\u01d4")
        buf.write("\u01d5\7\60\2\2\u01d5'\3\2\2\2\u01d6\u01d7\7\22\2\2\u01d7")
        buf.write('\u01d8\7\61\2\2\u01d8\u01d9\5B"\2\u01d9\u01da\7\62\2')
        buf.write("\2\u01da\u01e4\5&\24\2\u01db\u01dc\7\23\2\2\u01dc\u01dd")
        buf.write('\7\22\2\2\u01dd\u01de\7\61\2\2\u01de\u01df\5B"\2\u01df')
        buf.write("\u01e0\7\62\2\2\u01e0\u01e1\5&\24\2\u01e1\u01e3\3\2\2")
        buf.write("\2\u01e2\u01db\3\2\2\2\u01e3\u01e6\3\2\2\2\u01e4\u01e2")
        buf.write("\3\2\2\2\u01e4\u01e5\3\2\2\2\u01e5\u01e9\3\2\2\2\u01e6")
        buf.write("\u01e4\3\2\2\2\u01e7\u01e8\7\23\2\2\u01e8\u01ea\5&\24")
        buf.write("\2\u01e9\u01e7\3\2\2\2\u01e9\u01ea\3\2\2\2\u01ea)\3\2")
        buf.write("\2\2\u01eb\u01ef\5$\23\2\u01ec\u01ef\5(\25\2\u01ed\u01ef")
        buf.write("\7-\2\2\u01ee\u01eb\3\2\2\2\u01ee\u01ec\3\2\2\2\u01ee")
        buf.write("\u01ed\3\2\2\2\u01ef+\3\2\2\2\u01f0\u01f2\5*\26\2\u01f1")
        buf.write("\u01f0\3\2\2\2\u01f2\u01f5\3\2\2\2\u01f3\u01f1\3\2\2\2")
        buf.write("\u01f3\u01f4\3\2\2\2\u01f4-\3\2\2\2\u01f5\u01f3\3\2\2")
        buf.write("\2\u01f6\u0201\5\b\5\2\u01f7\u0201\5\n\6\2\u01f8\u0201")
        buf.write("\5\f\7\2\u01f9\u0201\5\16\b\2\u01fa\u0201\5\22\n\2\u01fb")
        buf.write("\u0201\5\20\t\2\u01fc\u0201\5\24\13\2\u01fd\u0201\5\26")
        buf.write("\f\2\u01fe\u0201\5\30\r\2\u01ff\u0201\7-\2\2\u0200\u01f6")
        buf.write("\3\2\2\2\u0200\u01f7\3\2\2\2\u0200\u01f8\3\2\2\2\u0200")
        buf.write("\u01f9\3\2\2\2\u0200\u01fa\3\2\2\2\u0200\u01fb\3\2\2\2")
        buf.write("\u0200\u01fc\3\2\2\2\u0200\u01fd\3\2\2\2\u0200\u01fe\3")
        buf.write("\2\2\2\u0200\u01ff\3\2\2\2\u0201/\3\2\2\2\u0202\u0204")
        buf.write("\5:\36\2\u0203\u0202\3\2\2\2\u0204\u0207\3\2\2\2\u0205")
        buf.write("\u0203\3\2\2\2\u0205\u0206\3\2\2\2\u0206\u0208\3\2\2\2")
        buf.write("\u0207\u0205\3\2\2\2\u0208\u0209\7\2\2\3\u0209\61\3\2")
        buf.write("\2\2\u020a\u020c\5\64\33\2\u020b\u020a\3\2\2\2\u020c\u020f")
        buf.write("\3\2\2\2\u020d\u020b\3\2\2\2\u020d\u020e\3\2\2\2\u020e")
        buf.write("\u0210\3\2\2\2\u020f\u020d\3\2\2\2\u0210\u0211\7\2\2\3")
        buf.write("\u0211\63\3\2\2\2\u0212\u0215\5\66\34\2\u0213\u0215\5")
        buf.write("8\35\2\u0214\u0212\3\2\2\2\u0214\u0213\3\2\2\2\u0215\65")
        buf.write("\3\2\2\2\u0216\u0217\7J\2\2\u0217\u0218\7*\2\2\u0218\u0219")
        buf.write("\5> \2\u0219\u021a\7-\2\2\u021a\67\3\2\2\2\u021b\u021c")
        buf.write("\7J\2\2\u021c\u021d\7C\2\2\u021d\u021e\5> \2\u021e\u021f")
        buf.write("\7-\2\2\u021f9\3\2\2\2\u0220\u0221\7J\2\2\u0221\u0222")
        buf.write("\7*\2\2\u0222\u0223\5@!\2\u0223\u0224\7-\2\2\u0224;\3")
        buf.write('\2\2\2\u0225\u0228\5@!\2\u0226\u0228\5B"\2\u0227\u0225')
        buf.write("\3\2\2\2\u0227\u0226\3\2\2\2\u0228=\3\2\2\2\u0229\u022a")
        buf.write("\b \1\2\u022a\u022b\7\63\2\2\u022b\u022c\5> \2\u022c\u022d")
        buf.write("\7\64\2\2\u022d\u0238\3\2\2\2\u022e\u0238\5F$\2\u022f")
        buf.write("\u0238\5J&\2\u0230\u0231\t\5\2\2\u0231\u0238\5> \13\u0232")
        buf.write("\u0233\7I\2\2\u0233\u0234\7\63\2\2\u0234\u0235\5> \2\u0235")
        buf.write("\u0236\7\64\2\2\u0236\u0238\3\2\2\2\u0237\u0229\3\2\2")
        buf.write("\2\u0237\u022e\3\2\2\2\u0237\u022f\3\2\2\2\u0237\u0230")
        buf.write("\3\2\2\2\u0237\u0232\3\2\2\2\u0238\u0250\3\2\2\2\u0239")
        buf.write("\u023a\f\n\2\2\u023a\u023b\7 \2\2\u023b\u024f\5> \n\u023c")
        buf.write("\u023d\f\t\2\2\u023d\u023e\t\6\2\2\u023e\u024f\5> \n\u023f")
        buf.write("\u0240\f\b\2\2\u0240\u0241\t\5\2\2\u0241\u024f\5> \t\u0242")
        buf.write("\u0243\f\7\2\2\u0243\u0244\t\7\2\2\u0244\u024f\5> \b\u0245")
        buf.write("\u0246\f\6\2\2\u0246\u0247\7>\2\2\u0247\u024f\5> \7\u0248")
        buf.write("\u0249\f\5\2\2\u0249\u024a\7?\2\2\u024a\u024f\5> \6\u024b")
        buf.write("\u024c\f\4\2\2\u024c\u024d\7@\2\2\u024d\u024f\5> \5\u024e")
        buf.write("\u0239\3\2\2\2\u024e\u023c\3\2\2\2\u024e\u023f\3\2\2\2")
        buf.write("\u024e\u0242\3\2\2\2\u024e\u0245\3\2\2\2\u024e\u0248\3")
        buf.write("\2\2\2\u024e\u024b\3\2\2\2\u024f\u0252\3\2\2\2\u0250\u024e")
        buf.write("\3\2\2\2\u0250\u0251\3\2\2\2\u0251?\3\2\2\2\u0252\u0250")
        buf.write("\3\2\2\2\u0253\u0254\b!\1\2\u0254\u0255\7\63\2\2\u0255")
        buf.write("\u0256\5@!\2\u0256\u0257\7\64\2\2\u0257\u026b\3\2\2\2")
        buf.write("\u0258\u026b\5F$\2\u0259\u026b\7J\2\2\u025a\u026b\5J&")
        buf.write("\2\u025b\u025c\t\5\2\2\u025c\u026b\5@!\f\u025d\u025e\7")
        buf.write("I\2\2\u025e\u025f\7\63\2\2\u025f\u0260\5@!\2\u0260\u0261")
        buf.write("\7\64\2\2\u0261\u026b\3\2\2\2\u0262\u0263\7\63\2\2\u0263")
        buf.write('\u0264\5B"\2\u0264\u0265\7\64\2\2\u0265\u0266\7\65\2')
        buf.write("\2\u0266\u0267\5@!\2\u0267\u0268\7\66\2\2\u0268\u0269")
        buf.write("\5@!\3\u0269\u026b\3\2\2\2\u026a\u0253\3\2\2\2\u026a\u0258")
        buf.write("\3\2\2\2\u026a\u0259\3\2\2\2\u026a\u025a\3\2\2\2\u026a")
        buf.write("\u025b\3\2\2\2\u026a\u025d\3\2\2\2\u026a\u0262\3\2\2\2")
        buf.write("\u026b\u0283\3\2\2\2\u026c\u026d\f\13\2\2\u026d\u026e")
        buf.write("\7 \2\2\u026e\u0282\5@!\13\u026f\u0270\f\n\2\2\u0270\u0271")
        buf.write("\t\6\2\2\u0271\u0282\5@!\13\u0272\u0273\f\t\2\2\u0273")
        buf.write("\u0274\t\5\2\2\u0274\u0282\5@!\n\u0275\u0276\f\b\2\2\u0276")
        buf.write("\u0277\t\7\2\2\u0277\u0282\5@!\t\u0278\u0279\f\7\2\2\u0279")
        buf.write("\u027a\7>\2\2\u027a\u0282\5@!\b\u027b\u027c\f\6\2\2\u027c")
        buf.write("\u027d\7?\2\2\u027d\u0282\5@!\7\u027e\u027f\f\5\2\2\u027f")
        buf.write("\u0280\7@\2\2\u0280\u0282\5@!\6\u0281\u026c\3\2\2\2\u0281")
        buf.write("\u026f\3\2\2\2\u0281\u0272\3\2\2\2\u0281\u0275\3\2\2\2")
        buf.write("\u0281\u0278\3\2\2\2\u0281\u027b\3\2\2\2\u0281\u027e\3")
        buf.write("\2\2\2\u0282\u0285\3\2\2\2\u0283\u0281\3\2\2\2\u0283\u0284")
        buf.write("\3\2\2\2\u0284A\3\2\2\2\u0285\u0283\3\2\2\2\u0286\u0287")
        buf.write('\b"\1\2\u0287\u0288\7\63\2\2\u0288\u0289\5B"\2\u0289')
        buf.write("\u028a\7\64\2\2\u028a\u029f\3\2\2\2\u028b\u029f\5H%\2")
        buf.write('\u028c\u028d\t\b\2\2\u028d\u029f\5B"\f\u028e\u028f\5')
        buf.write("@!\2\u028f\u0290\t\t\2\2\u0290\u0291\5@!\2\u0291\u029f")
        buf.write("\3\2\2\2\u0292\u0293\5@!\2\u0293\u0294\t\n\2\2\u0294\u0295")
        buf.write("\5@!\2\u0295\u029f\3\2\2\2\u0296\u0297\7\63\2\2\u0297")
        buf.write('\u0298\5B"\2\u0298\u0299\7\64\2\2\u0299\u029a\7\65\2')
        buf.write('\2\u029a\u029b\5B"\2\u029b\u029c\7\66\2\2\u029c\u029d')
        buf.write('\5B"\3\u029d\u029f\3\2\2\2\u029e\u0286\3\2\2\2\u029e')
        buf.write("\u028b\3\2\2\2\u029e\u028c\3\2\2\2\u029e\u028e\3\2\2\2")
        buf.write("\u029e\u0292\3\2\2\2\u029e\u0296\3\2\2\2\u029f\u02b4\3")
        buf.write("\2\2\2\u02a0\u02a1\f\t\2\2\u02a1\u02a2\t\13\2\2\u02a2")
        buf.write('\u02b3\5B"\n\u02a3\u02a4\f\b\2\2\u02a4\u02a5\t\f\2\2')
        buf.write('\u02a5\u02b3\5B"\t\u02a6\u02a7\f\6\2\2\u02a7\u02a8\7')
        buf.write('\36\2\2\u02a8\u02b3\5B"\7\u02a9\u02aa\f\5\2\2\u02aa\u02ab')
        buf.write('\t\r\2\2\u02ab\u02b3\5B"\6\u02ac\u02ad\f\4\2\2\u02ad')
        buf.write('\u02ae\t\16\2\2\u02ae\u02b3\5B"\4\u02af\u02b0\f\7\2\2')
        buf.write("\u02b0\u02b1\7?\2\2\u02b1\u02b3\5D#\2\u02b2\u02a0\3\2")
        buf.write("\2\2\u02b2\u02a3\3\2\2\2\u02b2\u02a6\3\2\2\2\u02b2\u02a9")
        buf.write("\3\2\2\2\u02b2\u02ac\3\2\2\2\u02b2\u02af\3\2\2\2\u02b3")
        buf.write("\u02b6\3\2\2\2\u02b4\u02b2\3\2\2\2\u02b4\u02b5\3\2\2\2")
        buf.write("\u02b5C\3\2\2\2\u02b6\u02b4\3\2\2\2\u02b7\u02bd\5H%\2")
        buf.write('\u02b8\u02b9\7\63\2\2\u02b9\u02ba\5B"\2\u02ba\u02bb\7')
        buf.write("\64\2\2\u02bb\u02bd\3\2\2\2\u02bc\u02b7\3\2\2\2\u02bc")
        buf.write("\u02b8\3\2\2\2\u02bdE\3\2\2\2\u02be\u02bf\t\17\2\2\u02bf")
        buf.write("G\3\2\2\2\u02c0\u02c1\t\20\2\2\u02c1I\3\2\2\2\u02c2\u02c3")
        buf.write("\t\21\2\2\u02c3K\3\2\2\2\u02c4\u02c6\78\2\2\u02c5\u02c4")
        buf.write("\3\2\2\2\u02c5\u02c6\3\2\2\2\u02c6\u02c7\3\2\2\2\u02c7")
        buf.write("\u02cc\7J\2\2\u02c8\u02c9\7\67\2\2\u02c9\u02cb\7J\2\2")
        buf.write("\u02ca\u02c8\3\2\2\2\u02cb\u02ce\3\2\2\2\u02cc\u02ca\3")
        buf.write("\2\2\2\u02cc\u02cd\3\2\2\2\u02cdM\3\2\2\2\u02ce\u02cc")
        buf.write("\3\2\2\2GTbhlrx|\u0089\u0091\u00a0\u00a8\u00b7\u00bf\u00c1")
        buf.write("\u00d1\u00e2\u00f1\u0100\u0103\u0107\u0114\u0119\u011f")
        buf.write("\u0123\u0130\u0135\u013b\u013f\u0142\u014a\u0151\u0155")
        buf.write("\u015a\u015d\u0163\u0169\u017a\u0181\u0187\u018d\u0197")
        buf.write("\u019d\u01a2\u01a7\u01b6\u01bc\u01c1\u01c9\u01e4\u01e9")
        buf.write("\u01ee\u01f3\u0200\u0205\u020d\u0214\u0227\u0237\u024e")
        buf.write("\u0250\u026a\u0281\u0283\u029e\u02b2\u02b4\u02bc\u02c5")
        buf.write("\u02cc")
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
    RULE_cond_caret_atom = 33
    RULE_num_literal = 34
    RULE_bool_literal = 35
    RULE_math_const = 36
    RULE_chain_id = 37

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
        "cond_caret_atom",
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
            self.state = 76
            self.cond_expression(0)
            self.state = 77
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
            self.state = 82
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.DEF:
                self.state = 79
                self.def_assignment()
                self.state = 84
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 85
            self.state_definition()
            self.state = 86
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
            self.state = 88
            self.match(GrammarParser.DEF)
            self.state = 89
            localctx.deftype = self._input.LT(1)
            _la = self._input.LA(1)
            if not (_la == GrammarParser.INT_TYPE or _la == GrammarParser.FLOAT_TYPE):
                localctx.deftype = self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
            self.state = 90
            self.match(GrammarParser.ID)
            self.state = 91
            self.match(GrammarParser.ASSIGN)
            self.state = 92
            self.init_expression(0)
            self.state = 93
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
            self.state = 122
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 6, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.LeafStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 96
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.PSEUDO:
                    self.state = 95
                    localctx.pseudo = self.match(GrammarParser.PSEUDO)

                self.state = 98
                self.match(GrammarParser.STATE)
                self.state = 99
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 102
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.NAMED:
                    self.state = 100
                    self.match(GrammarParser.NAMED)
                    self.state = 101
                    localctx.extra_name = self.match(GrammarParser.STRING)

                self.state = 104
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 2:
                localctx = GrammarParser.CompositeStateDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 106
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.PSEUDO:
                    self.state = 105
                    localctx.pseudo = self.match(GrammarParser.PSEUDO)

                self.state = 108
                self.match(GrammarParser.STATE)
                self.state = 109
                localctx.state_id = self.match(GrammarParser.ID)
                self.state = 112
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.NAMED:
                    self.state = 110
                    self.match(GrammarParser.NAMED)
                    self.state = 111
                    localctx.extra_name = self.match(GrammarParser.STRING)

                self.state = 114
                self.match(GrammarParser.LBRACE)
                self.state = 118
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
                    self.state = 115
                    self.state_inner_statement()
                    self.state = 120
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 121
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
            self.state = 191
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 13, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EntryTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 124
                self.match(GrammarParser.INIT_MARKER)
                self.state = 125
                self.match(GrammarParser.ARROW)
                self.state = 126
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 135
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 7, self._ctx)
                if la_ == 1:
                    self.state = 127
                    _la = self._input.LA(1)
                    if not (
                        _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON
                    ):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 128
                    self.chain_id()

                elif la_ == 2:
                    self.state = 129
                    self.match(GrammarParser.COLON)
                    self.state = 130
                    self.match(GrammarParser.IF)
                    self.state = 131
                    self.match(GrammarParser.LBRACK)
                    self.state = 132
                    self.cond_expression(0)
                    self.state = 133
                    self.match(GrammarParser.RBRACK)

                self.state = 143
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.SEMI]:
                    self.state = 137
                    self.match(GrammarParser.SEMI)
                    pass
                elif token in [GrammarParser.EFFECT]:
                    self.state = 138
                    self.match(GrammarParser.EFFECT)
                    self.state = 139
                    self.match(GrammarParser.LBRACE)
                    self.state = 140
                    self.operational_statement_set()
                    self.state = 141
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
                self.state = 145
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 146
                self.match(GrammarParser.ARROW)
                self.state = 147
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 158
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 9, self._ctx)
                if la_ == 1:
                    self.state = 148
                    self.match(GrammarParser.COLONCOLON)
                    self.state = 149
                    localctx.from_id = self.match(GrammarParser.ID)

                elif la_ == 2:
                    self.state = 150
                    self.match(GrammarParser.COLON)
                    self.state = 151
                    self.chain_id()

                elif la_ == 3:
                    self.state = 152
                    self.match(GrammarParser.COLON)
                    self.state = 153
                    self.match(GrammarParser.IF)
                    self.state = 154
                    self.match(GrammarParser.LBRACK)
                    self.state = 155
                    self.cond_expression(0)
                    self.state = 156
                    self.match(GrammarParser.RBRACK)

                self.state = 166
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.SEMI]:
                    self.state = 160
                    self.match(GrammarParser.SEMI)
                    pass
                elif token in [GrammarParser.EFFECT]:
                    self.state = 161
                    self.match(GrammarParser.EFFECT)
                    self.state = 162
                    self.match(GrammarParser.LBRACE)
                    self.state = 163
                    self.operational_statement_set()
                    self.state = 164
                    self.match(GrammarParser.RBRACE)
                    pass
                else:
                    raise NoViableAltException(self)

                pass

            elif la_ == 3:
                localctx = GrammarParser.ExitTransitionDefinitionContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 168
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 169
                self.match(GrammarParser.ARROW)
                self.state = 170
                self.match(GrammarParser.INIT_MARKER)
                self.state = 181
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 11, self._ctx)
                if la_ == 1:
                    self.state = 171
                    self.match(GrammarParser.COLONCOLON)
                    self.state = 172
                    localctx.from_id = self.match(GrammarParser.ID)

                elif la_ == 2:
                    self.state = 173
                    self.match(GrammarParser.COLON)
                    self.state = 174
                    self.chain_id()

                elif la_ == 3:
                    self.state = 175
                    self.match(GrammarParser.COLON)
                    self.state = 176
                    self.match(GrammarParser.IF)
                    self.state = 177
                    self.match(GrammarParser.LBRACK)
                    self.state = 178
                    self.cond_expression(0)
                    self.state = 179
                    self.match(GrammarParser.RBRACK)

                self.state = 189
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [GrammarParser.SEMI]:
                    self.state = 183
                    self.match(GrammarParser.SEMI)
                    pass
                elif token in [GrammarParser.EFFECT]:
                    self.state = 184
                    self.match(GrammarParser.EFFECT)
                    self.state = 185
                    self.match(GrammarParser.LBRACE)
                    self.state = 186
                    self.operational_statement_set()
                    self.state = 187
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
            self.state = 257
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 18, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.NormalForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 193
                self.match(GrammarParser.BANG)
                self.state = 194
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 195
                self.match(GrammarParser.ARROW)
                self.state = 196
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 207
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 14, self._ctx)
                if la_ == 1:
                    self.state = 197
                    self.match(GrammarParser.COLONCOLON)
                    self.state = 198
                    localctx.from_id = self.match(GrammarParser.ID)

                elif la_ == 2:
                    self.state = 199
                    self.match(GrammarParser.COLON)
                    self.state = 200
                    self.chain_id()

                elif la_ == 3:
                    self.state = 201
                    self.match(GrammarParser.COLON)
                    self.state = 202
                    self.match(GrammarParser.IF)
                    self.state = 203
                    self.match(GrammarParser.LBRACK)
                    self.state = 204
                    self.cond_expression(0)
                    self.state = 205
                    self.match(GrammarParser.RBRACK)

                self.state = 209
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 2:
                localctx = GrammarParser.ExitForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 2)
                self.state = 210
                self.match(GrammarParser.BANG)
                self.state = 211
                localctx.from_state = self.match(GrammarParser.ID)
                self.state = 212
                self.match(GrammarParser.ARROW)
                self.state = 213
                self.match(GrammarParser.INIT_MARKER)
                self.state = 224
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 15, self._ctx)
                if la_ == 1:
                    self.state = 214
                    self.match(GrammarParser.COLONCOLON)
                    self.state = 215
                    localctx.from_id = self.match(GrammarParser.ID)

                elif la_ == 2:
                    self.state = 216
                    self.match(GrammarParser.COLON)
                    self.state = 217
                    self.chain_id()

                elif la_ == 3:
                    self.state = 218
                    self.match(GrammarParser.COLON)
                    self.state = 219
                    self.match(GrammarParser.IF)
                    self.state = 220
                    self.match(GrammarParser.LBRACK)
                    self.state = 221
                    self.cond_expression(0)
                    self.state = 222
                    self.match(GrammarParser.RBRACK)

                self.state = 226
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.NormalAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 3)
                self.state = 227
                self.match(GrammarParser.BANG)
                self.state = 228
                self.match(GrammarParser.STAR)
                self.state = 229
                self.match(GrammarParser.ARROW)
                self.state = 230
                localctx.to_state = self.match(GrammarParser.ID)
                self.state = 239
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 16, self._ctx)
                if la_ == 1:
                    self.state = 231
                    _la = self._input.LA(1)
                    if not (
                        _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON
                    ):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 232
                    self.chain_id()

                elif la_ == 2:
                    self.state = 233
                    self.match(GrammarParser.COLON)
                    self.state = 234
                    self.match(GrammarParser.IF)
                    self.state = 235
                    self.match(GrammarParser.LBRACK)
                    self.state = 236
                    self.cond_expression(0)
                    self.state = 237
                    self.match(GrammarParser.RBRACK)

                self.state = 241
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 4:
                localctx = GrammarParser.ExitAllForceTransitionDefinitionContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 4)
                self.state = 242
                self.match(GrammarParser.BANG)
                self.state = 243
                self.match(GrammarParser.STAR)
                self.state = 244
                self.match(GrammarParser.ARROW)
                self.state = 245
                self.match(GrammarParser.INIT_MARKER)
                self.state = 254
                self._errHandler.sync(self)
                la_ = self._interp.adaptivePredict(self._input, 17, self._ctx)
                if la_ == 1:
                    self.state = 246
                    _la = self._input.LA(1)
                    if not (
                        _la == GrammarParser.COLONCOLON or _la == GrammarParser.COLON
                    ):
                        self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()
                    self.state = 247
                    self.chain_id()

                elif la_ == 2:
                    self.state = 248
                    self.match(GrammarParser.COLON)
                    self.state = 249
                    self.match(GrammarParser.IF)
                    self.state = 250
                    self.match(GrammarParser.LBRACK)
                    self.state = 251
                    self.cond_expression(0)
                    self.state = 252
                    self.match(GrammarParser.RBRACK)

                self.state = 256
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
            self.state = 285
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 22, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.EnterOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 259
                self.match(GrammarParser.ENTER)
                self.state = 261
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 260
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 263
                self.match(GrammarParser.LBRACE)
                self.state = 264
                self.operational_statement_set()
                self.state = 265
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 267
                self.match(GrammarParser.ENTER)
                self.state = 268
                self.match(GrammarParser.ABSTRACT)
                self.state = 269
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 270
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.EnterAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 271
                self.match(GrammarParser.ENTER)
                self.state = 272
                self.match(GrammarParser.ABSTRACT)
                self.state = 274
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 273
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 276
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.EnterRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 277
                self.match(GrammarParser.ENTER)
                self.state = 279
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 278
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 281
                self.match(GrammarParser.REF)
                self.state = 282
                self.chain_id()
                self.state = 283
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
            self.state = 313
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 26, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ExitOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 287
                self.match(GrammarParser.EXIT)
                self.state = 289
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 288
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 291
                self.match(GrammarParser.LBRACE)
                self.state = 292
                self.operational_statement_set()
                self.state = 293
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 295
                self.match(GrammarParser.EXIT)
                self.state = 296
                self.match(GrammarParser.ABSTRACT)
                self.state = 297
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 298
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.ExitAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 299
                self.match(GrammarParser.EXIT)
                self.state = 300
                self.match(GrammarParser.ABSTRACT)
                self.state = 302
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 301
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 304
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.ExitRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 305
                self.match(GrammarParser.EXIT)
                self.state = 307
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 306
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 309
                self.match(GrammarParser.REF)
                self.state = 310
                self.chain_id()
                self.state = 311
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
            self.state = 353
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 34, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.DuringOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 315
                self.match(GrammarParser.DURING)
                self.state = 317
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 316
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 320
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 319
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 322
                self.match(GrammarParser.LBRACE)
                self.state = 323
                self.operational_statement_set()
                self.state = 324
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 326
                self.match(GrammarParser.DURING)
                self.state = 328
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 327
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 330
                self.match(GrammarParser.ABSTRACT)
                self.state = 331
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 332
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.DuringAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 333
                self.match(GrammarParser.DURING)
                self.state = 335
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 334
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 337
                self.match(GrammarParser.ABSTRACT)
                self.state = 339
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 338
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 341
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.DuringRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 342
                self.match(GrammarParser.DURING)
                self.state = 344
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.BEFORE or _la == GrammarParser.AFTER:
                    self.state = 343
                    localctx.aspect = self._input.LT(1)
                    _la = self._input.LA(1)
                    if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                        localctx.aspect = self._errHandler.recoverInline(self)
                    else:
                        self._errHandler.reportMatch(self)
                        self.consume()

                self.state = 347
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 346
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 349
                self.match(GrammarParser.REF)
                self.state = 350
                self.chain_id()
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
            self.state = 389
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 38, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.DuringAspectOperationsContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 355
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 356
                self.match(GrammarParser.DURING)
                self.state = 357
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 359
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 358
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 361
                self.match(GrammarParser.LBRACE)
                self.state = 362
                self.operational_statement_set()
                self.state = 363
                self.match(GrammarParser.RBRACE)
                pass

            elif la_ == 2:
                localctx = GrammarParser.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 365
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 366
                self.match(GrammarParser.DURING)
                self.state = 367
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 368
                self.match(GrammarParser.ABSTRACT)
                self.state = 369
                localctx.func_name = self.match(GrammarParser.ID)
                self.state = 370
                self.match(GrammarParser.SEMI)
                pass

            elif la_ == 3:
                localctx = GrammarParser.DuringAspectAbstractFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 371
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 372
                self.match(GrammarParser.DURING)
                self.state = 373
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 374
                self.match(GrammarParser.ABSTRACT)
                self.state = 376
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 375
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 378
                localctx.raw_doc = self.match(GrammarParser.MULTILINE_COMMENT)
                pass

            elif la_ == 4:
                localctx = GrammarParser.DuringAspectRefFuncContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 379
                self.match(GrammarParser.SHIFT_RIGHT)
                self.state = 380
                self.match(GrammarParser.DURING)
                self.state = 381
                localctx.aspect = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.BEFORE or _la == GrammarParser.AFTER):
                    localctx.aspect = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 383
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == GrammarParser.ID:
                    self.state = 382
                    localctx.func_name = self.match(GrammarParser.ID)

                self.state = 385
                self.match(GrammarParser.REF)
                self.state = 386
                self.chain_id()
                self.state = 387
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
            self.state = 391
            self.match(GrammarParser.EVENT)
            self.state = 392
            localctx.event_name = self.match(GrammarParser.ID)
            self.state = 395
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.NAMED:
                self.state = 393
                self.match(GrammarParser.NAMED)
                self.state = 394
                localctx.extra_name = self.match(GrammarParser.STRING)

            self.state = 397
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
            self.state = 399
            self.match(GrammarParser.IMPORT)
            self.state = 400
            localctx.import_path = self.match(GrammarParser.STRING)
            self.state = 401
            self.match(GrammarParser.AS)
            self.state = 402
            localctx.state_alias = self.match(GrammarParser.ID)
            self.state = 405
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.NAMED:
                self.state = 403
                self.match(GrammarParser.NAMED)
                self.state = 404
                localctx.extra_name = self.match(GrammarParser.STRING)

            self.state = 416
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.LBRACE]:
                self.state = 407
                self.match(GrammarParser.LBRACE)
                self.state = 411
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
                    self.state = 408
                    self.import_mapping_statement()
                    self.state = 413
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 414
                self.match(GrammarParser.RBRACE)
                pass
            elif token in [GrammarParser.SEMI]:
                self.state = 415
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
            self.state = 421
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.DEF]:
                self.enterOuterAlt(localctx, 1)
                self.state = 418
                self.import_def_mapping()
                pass
            elif token in [GrammarParser.EVENT]:
                self.enterOuterAlt(localctx, 2)
                self.state = 419
                self.import_event_mapping()
                pass
            elif token in [GrammarParser.SEMI]:
                self.enterOuterAlt(localctx, 3)
                self.state = 420
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
            self.state = 423
            self.match(GrammarParser.DEF)
            self.state = 424
            self.import_def_selector()
            self.state = 425
            self.match(GrammarParser.ARROW)
            self.state = 426
            self.import_def_target_template()
            self.state = 427
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
            self.state = 442
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.STAR]:
                localctx = GrammarParser.ImportDefFallbackSelectorContext(
                    self, localctx
                )
                self.enterOuterAlt(localctx, 1)
                self.state = 429
                self.match(GrammarParser.STAR)
                pass
            elif token in [GrammarParser.LBRACE]:
                localctx = GrammarParser.ImportDefSetSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 430
                self.match(GrammarParser.LBRACE)
                self.state = 431
                localctx._ID = self.match(GrammarParser.ID)
                localctx.selector_items.append(localctx._ID)
                self.state = 436
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == GrammarParser.COMMA:
                    self.state = 432
                    self.match(GrammarParser.COMMA)
                    self.state = 433
                    localctx._ID = self.match(GrammarParser.ID)
                    localctx.selector_items.append(localctx._ID)
                    self.state = 438
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 439
                self.match(GrammarParser.RBRACE)
                pass
            elif token in [GrammarParser.IMPORT_DEF_SELECTOR_PATTERN]:
                localctx = GrammarParser.ImportDefPatternSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 440
                localctx.selector_pattern = self.match(
                    GrammarParser.IMPORT_DEF_SELECTOR_PATTERN
                )
                pass
            elif token in [GrammarParser.ID]:
                localctx = GrammarParser.ImportDefExactSelectorContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 441
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
            self.state = 447
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 444
                localctx.target_text = self.match(GrammarParser.ID)
                pass
            elif token in [GrammarParser.IMPORT_DEF_TARGET_TEMPLATE]:
                self.enterOuterAlt(localctx, 2)
                self.state = 445
                localctx.target_text = self.match(
                    GrammarParser.IMPORT_DEF_TARGET_TEMPLATE
                )
                pass
            elif token in [GrammarParser.STAR]:
                self.enterOuterAlt(localctx, 3)
                self.state = 446
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
            self.state = 449
            self.match(GrammarParser.EVENT)
            self.state = 450
            localctx.source_event = self.chain_id()
            self.state = 451
            self.match(GrammarParser.ARROW)
            self.state = 452
            localctx.target_event = self.chain_id()
            self.state = 455
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.NAMED:
                self.state = 453
                self.match(GrammarParser.NAMED)
                self.state = 454
                localctx.extra_name = self.match(GrammarParser.STRING)

            self.state = 457
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
            self.state = 459
            self.match(GrammarParser.ID)
            self.state = 460
            self.match(GrammarParser.ASSIGN)
            self.state = 461
            self.num_expression(0)
            self.state = 462
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
            self.state = 464
            self.match(GrammarParser.LBRACE)
            self.state = 465
            self.operational_statement_set()
            self.state = 466
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
            self.state = 468
            self.match(GrammarParser.IF)
            self.state = 469
            self.match(GrammarParser.LBRACK)
            self.state = 470
            self.cond_expression(0)
            self.state = 471
            self.match(GrammarParser.RBRACK)
            self.state = 472
            self.operation_block()
            self.state = 482
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 48, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    self.state = 473
                    self.match(GrammarParser.ELSE)
                    self.state = 474
                    self.match(GrammarParser.IF)
                    self.state = 475
                    self.match(GrammarParser.LBRACK)
                    self.state = 476
                    self.cond_expression(0)
                    self.state = 477
                    self.match(GrammarParser.RBRACK)
                    self.state = 478
                    self.operation_block()
                self.state = 484
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 48, self._ctx)

            self.state = 487
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.ELSE:
                self.state = 485
                self.match(GrammarParser.ELSE)
                self.state = 486
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
            self.state = 492
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 489
                self.operation_assignment()
                pass
            elif token in [GrammarParser.IF]:
                self.enterOuterAlt(localctx, 2)
                self.state = 490
                self.if_statement()
                pass
            elif token in [GrammarParser.SEMI]:
                self.enterOuterAlt(localctx, 3)
                self.state = 491
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
            self.state = 497
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
                self.state = 494
                self.operational_statement()
                self.state = 499
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
            self.state = 510
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.PSEUDO, GrammarParser.STATE]:
                self.enterOuterAlt(localctx, 1)
                self.state = 500
                self.state_definition()
                pass
            elif token in [GrammarParser.INIT_MARKER, GrammarParser.ID]:
                self.enterOuterAlt(localctx, 2)
                self.state = 501
                self.transition_definition()
                pass
            elif token in [GrammarParser.BANG]:
                self.enterOuterAlt(localctx, 3)
                self.state = 502
                self.transition_force_definition()
                pass
            elif token in [GrammarParser.ENTER]:
                self.enterOuterAlt(localctx, 4)
                self.state = 503
                self.enter_definition()
                pass
            elif token in [GrammarParser.DURING]:
                self.enterOuterAlt(localctx, 5)
                self.state = 504
                self.during_definition()
                pass
            elif token in [GrammarParser.EXIT]:
                self.enterOuterAlt(localctx, 6)
                self.state = 505
                self.exit_definition()
                pass
            elif token in [GrammarParser.SHIFT_RIGHT]:
                self.enterOuterAlt(localctx, 7)
                self.state = 506
                self.during_aspect_definition()
                pass
            elif token in [GrammarParser.EVENT]:
                self.enterOuterAlt(localctx, 8)
                self.state = 507
                self.event_definition()
                pass
            elif token in [GrammarParser.IMPORT]:
                self.enterOuterAlt(localctx, 9)
                self.state = 508
                self.import_statement()
                pass
            elif token in [GrammarParser.SEMI]:
                self.enterOuterAlt(localctx, 10)
                self.state = 509
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
            self.state = 515
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 512
                self.operational_assignment()
                self.state = 517
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 518
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
            self.state = 523
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.ID:
                self.state = 520
                self.preamble_statement()
                self.state = 525
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 526
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
            self.state = 530
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 55, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 528
                self.initial_assignment()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 529
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
            self.state = 532
            self.match(GrammarParser.ID)
            self.state = 533
            self.match(GrammarParser.DECLARE_ASSIGN)
            self.state = 534
            self.init_expression(0)
            self.state = 535
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
            self.state = 537
            self.match(GrammarParser.ID)
            self.state = 538
            self.match(GrammarParser.ASSIGN)
            self.state = 539
            self.init_expression(0)
            self.state = 540
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
            self.state = 542
            self.match(GrammarParser.ID)
            self.state = 543
            self.match(GrammarParser.DECLARE_ASSIGN)
            self.state = 544
            self.num_expression(0)
            self.state = 545
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
            self.state = 549
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 56, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 547
                self.num_expression(0)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 548
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
            self.state = 565
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.LPAREN]:
                localctx = GrammarParser.ParenExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 552
                self.match(GrammarParser.LPAREN)
                self.state = 553
                self.init_expression(0)
                self.state = 554
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
                self.state = 556
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
                self.state = 557
                self.math_const()
                pass
            elif token in [GrammarParser.PLUS, GrammarParser.MINUS]:
                localctx = GrammarParser.UnaryExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 558
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.PLUS or _la == GrammarParser.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 559
                self.init_expression(9)
                pass
            elif token in [GrammarParser.UFUNC_NAME]:
                localctx = GrammarParser.FuncExprInitContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 560
                localctx.func_name = self.match(GrammarParser.UFUNC_NAME)
                self.state = 561
                self.match(GrammarParser.LPAREN)
                self.state = 562
                self.init_expression(0)
                self.state = 563
                self.match(GrammarParser.RPAREN)
                pass
            else:
                raise NoViableAltException(self)

            self._ctx.stop = self._input.LT(-1)
            self.state = 590
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 59, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 588
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
                        self.state = 567
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 568
                        localctx.op = self.match(GrammarParser.POW)
                        self.state = 569
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
                        self.state = 570
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 571
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
                        self.state = 572
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
                        self.state = 573
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 574
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.PLUS or _la == GrammarParser.MINUS
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 575
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
                        self.state = 576
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 577
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
                        self.state = 578
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
                        self.state = 579
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 580
                        localctx.op = self.match(GrammarParser.AMP)
                        self.state = 581
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
                        self.state = 582
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 583
                        localctx.op = self.match(GrammarParser.CARET)
                        self.state = 584
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
                        self.state = 585
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 586
                        localctx.op = self.match(GrammarParser.PIPE)
                        self.state = 587
                        self.init_expression(3)
                        pass

                self.state = 592
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
            self.state = 616
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 60, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 594
                self.match(GrammarParser.LPAREN)
                self.state = 595
                self.num_expression(0)
                self.state = 596
                self.match(GrammarParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 598
                self.num_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.IdExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 599
                self.match(GrammarParser.ID)
                pass

            elif la_ == 4:
                localctx = GrammarParser.MathConstExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 600
                self.math_const()
                pass

            elif la_ == 5:
                localctx = GrammarParser.UnaryExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 601
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.PLUS or _la == GrammarParser.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 602
                self.num_expression(10)
                pass

            elif la_ == 6:
                localctx = GrammarParser.FuncExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 603
                localctx.func_name = self.match(GrammarParser.UFUNC_NAME)
                self.state = 604
                self.match(GrammarParser.LPAREN)
                self.state = 605
                self.num_expression(0)
                self.state = 606
                self.match(GrammarParser.RPAREN)
                pass

            elif la_ == 7:
                localctx = GrammarParser.ConditionalCStyleExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 608
                self.match(GrammarParser.LPAREN)
                self.state = 609
                self.cond_expression(0)
                self.state = 610
                self.match(GrammarParser.RPAREN)
                self.state = 611
                self.match(GrammarParser.QUESTION)
                self.state = 612
                self.num_expression(0)
                self.state = 613
                self.match(GrammarParser.COLON)
                self.state = 614
                self.num_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 641
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 62, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 639
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
                        self.state = 618
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 9)"
                            )
                        self.state = 619
                        localctx.op = self.match(GrammarParser.POW)
                        self.state = 620
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
                        self.state = 621
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 622
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
                        self.state = 623
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
                        self.state = 624
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 625
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == GrammarParser.PLUS or _la == GrammarParser.MINUS
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 626
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
                        self.state = 627
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 628
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
                        self.state = 629
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
                        self.state = 630
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 631
                        localctx.op = self.match(GrammarParser.AMP)
                        self.state = 632
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
                        self.state = 633
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 634
                        localctx.op = self.match(GrammarParser.CARET)
                        self.state = 635
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
                        self.state = 636
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 637
                        localctx.op = self.match(GrammarParser.PIPE)
                        self.state = 638
                        self.num_expression(4)
                        pass

                self.state = 643
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

        def cond_caret_atom(self):
            return self.getTypedRuleContext(GrammarParser.Cond_caret_atomContext, 0)

        def CARET(self):
            return self.getToken(GrammarParser.CARET, 0)

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
            self.state = 668
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 63, self._ctx)
            if la_ == 1:
                localctx = GrammarParser.ParenExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 645
                self.match(GrammarParser.LPAREN)
                self.state = 646
                self.cond_expression(0)
                self.state = 647
                self.match(GrammarParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = GrammarParser.LiteralExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 649
                self.bool_literal()
                pass

            elif la_ == 3:
                localctx = GrammarParser.UnaryExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 650
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.NOT_KW or _la == GrammarParser.BANG):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 651
                self.cond_expression(10)
                pass

            elif la_ == 4:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 652
                self.num_expression(0)
                self.state = 653
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
                self.state = 654
                self.num_expression(0)
                pass

            elif la_ == 5:
                localctx = GrammarParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 656
                self.num_expression(0)
                self.state = 657
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == GrammarParser.EQ or _la == GrammarParser.NE):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 658
                self.num_expression(0)
                pass

            elif la_ == 6:
                localctx = GrammarParser.ConditionalCStyleCondNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 660
                self.match(GrammarParser.LPAREN)
                self.state = 661
                self.cond_expression(0)
                self.state = 662
                self.match(GrammarParser.RPAREN)
                self.state = 663
                self.match(GrammarParser.QUESTION)
                self.state = 664
                self.cond_expression(0)
                self.state = 665
                self.match(GrammarParser.COLON)
                self.state = 666
                self.cond_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 690
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 65, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 688
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
                        self.state = 670
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 671
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
                        self.state = 672
                        self.cond_expression(8)
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
                        self.state = 673
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 674
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
                        self.state = 675
                        self.cond_expression(7)
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
                        self.state = 676
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 677
                        localctx.op = self.match(GrammarParser.XOR_KW)
                        self.state = 678
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
                        self.state = 679
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 680
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
                        self.state = 681
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
                        self.state = 682
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 683
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
                        self.state = 684
                        self.cond_expression(2)
                        pass

                    elif la_ == 6:
                        localctx = GrammarParser.BinaryExprCondContext(
                            self,
                            GrammarParser.Cond_expressionContext(
                                self, _parentctx, _parentState
                            ),
                        )
                        self.pushNewRecursionContext(
                            localctx, _startState, self.RULE_cond_expression
                        )
                        self.state = 685
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 686
                        localctx.op = self.match(GrammarParser.CARET)
                        self.state = 687
                        self.cond_caret_atom()
                        pass

                self.state = 692
                self._errHandler.sync(self)
                _alt = self._interp.adaptivePredict(self._input, 65, self._ctx)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.unrollRecursionContexts(_parentctx)
        return localctx

    class Cond_caret_atomContext(ParserRuleContext):
        __slots__ = "parser"

        def __init__(
            self, parser, parent: ParserRuleContext = None, invokingState: int = -1
        ):
            super().__init__(parent, invokingState)
            self.parser = parser

        def bool_literal(self):
            return self.getTypedRuleContext(GrammarParser.Bool_literalContext, 0)

        def LPAREN(self):
            return self.getToken(GrammarParser.LPAREN, 0)

        def cond_expression(self):
            return self.getTypedRuleContext(GrammarParser.Cond_expressionContext, 0)

        def RPAREN(self):
            return self.getToken(GrammarParser.RPAREN, 0)

        def getRuleIndex(self):
            return GrammarParser.RULE_cond_caret_atom

        def enterRule(self, listener: ParseTreeListener):
            if hasattr(listener, "enterCond_caret_atom"):
                listener.enterCond_caret_atom(self)

        def exitRule(self, listener: ParseTreeListener):
            if hasattr(listener, "exitCond_caret_atom"):
                listener.exitCond_caret_atom(self)

    def cond_caret_atom(self):

        localctx = GrammarParser.Cond_caret_atomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 66, self.RULE_cond_caret_atom)
        try:
            self.state = 698
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [GrammarParser.TRUE, GrammarParser.FALSE]:
                self.enterOuterAlt(localctx, 1)
                self.state = 693
                self.bool_literal()
                pass
            elif token in [GrammarParser.LPAREN]:
                self.enterOuterAlt(localctx, 2)
                self.state = 694
                self.match(GrammarParser.LPAREN)
                self.state = 695
                self.cond_expression(0)
                self.state = 696
                self.match(GrammarParser.RPAREN)
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
        self.enterRule(localctx, 68, self.RULE_num_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 700
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
        self.enterRule(localctx, 70, self.RULE_bool_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 702
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
        self.enterRule(localctx, 72, self.RULE_math_const)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 704
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
        self.enterRule(localctx, 74, self.RULE_chain_id)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 707
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == GrammarParser.SLASH:
                self.state = 706
                localctx.isabs = self.match(GrammarParser.SLASH)

            self.state = 709
            self.match(GrammarParser.ID)
            self.state = 714
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == GrammarParser.DOT:
                self.state = 710
                self.match(GrammarParser.DOT)
                self.state = 711
                self.match(GrammarParser.ID)
                self.state = 716
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
            return self.precpred(self._ctx, 7)

        if predIndex == 15:
            return self.precpred(self._ctx, 6)

        if predIndex == 16:
            return self.precpred(self._ctx, 4)

        if predIndex == 17:
            return self.precpred(self._ctx, 3)

        if predIndex == 18:
            return self.precpred(self._ctx, 2)

        if predIndex == 19:
            return self.precpred(self._ctx, 5)
