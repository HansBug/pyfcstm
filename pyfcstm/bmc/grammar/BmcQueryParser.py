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
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\3_")
        buf.write("\u01ac\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7\t\7")
        buf.write("\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r\4\16")
        buf.write("\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23\t\23")
        buf.write("\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30\4\31")
        buf.write("\t\31\4\32\t\32\4\33\t\33\4\34\t\34\4\35\t\35\4\36\t\36")
        buf.write("\4\37\t\37\4 \t \4!\t!\3\2\5\2D\n\2\3\2\7\2G\n\2\f\2\16")
        buf.write("\2J\13\2\3\2\3\2\3\2\3\3\3\3\3\3\3\4\3\4\3\4\3\5\3\5\3")
        buf.write("\5\5\5X\n\5\3\5\3\5\5\5\\\n\5\3\5\3\5\3\6\3\6\3\6\3\6")
        buf.write("\3\6\3\6\3\6\5\6g\n\6\3\7\3\7\3\7\3\7\3\7\3\7\3\7\7\7")
        buf.write("p\n\7\f\7\16\7s\13\7\3\7\3\7\5\7w\n\7\3\b\3\b\5\b{\n\b")
        buf.write("\3\t\3\t\3\t\5\t\u0080\n\t\3\n\3\n\3\n\3\n\5\n\u0086\n")
        buf.write("\n\3\n\3\n\3\n\3\n\3\13\3\13\3\13\3\13\3\13\3\13\3\13")
        buf.write("\3\13\3\13\3\13\3\13\3\f\3\f\3\f\3\f\3\f\3\f\3\f\3\f\3")
        buf.write("\f\5\f\u00a0\n\f\3\f\3\f\3\r\3\r\3\r\3\r\3\r\3\r\3\r\3")
        buf.write("\r\3\16\3\16\3\17\3\17\5\17\u00b0\n\17\3\20\3\20\3\20")
        buf.write("\3\20\3\20\3\20\3\20\3\21\3\21\3\21\7\21\u00bc\n\21\f")
        buf.write("\21\16\21\u00bf\13\21\3\22\3\22\3\23\3\23\3\23\3\23\3")
        buf.write("\23\3\23\3\23\5\23\u00ca\n\23\3\24\3\24\5\24\u00ce\n\24")
        buf.write("\3\25\3\25\5\25\u00d2\n\25\3\26\3\26\3\27\3\27\3\27\3")
        buf.write("\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\5\27\u00e7\n\27\3\27\3\27\3\27\3\27\3")
        buf.write("\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\5\27\u00f9\n\27\3\27\3\27\3\27\3\27\3\27\3\27\3")
        buf.write("\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\27\3\27\3\27\7\27\u0110\n\27\f\27\16\27\u0113")
        buf.write("\13\27\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3")
        buf.write("\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30")
        buf.write("\3\30\3\30\3\30\3\30\3\30\5\30\u012e\n\30\3\30\3\30\3")
        buf.write("\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30")
        buf.write("\3\30\3\30\7\30\u013f\n\30\f\30\16\30\u0142\13\30\3\31")
        buf.write("\3\31\3\31\3\31\3\31\5\31\u0149\n\31\3\31\3\31\3\31\3")
        buf.write("\31\3\31\5\31\u0150\n\31\3\31\3\31\3\31\3\31\3\31\3\31")
        buf.write("\3\31\3\31\3\31\3\31\3\31\3\31\3\31\5\31\u015f\n\31\3")
        buf.write("\31\3\31\3\31\3\31\3\31\5\31\u0166\n\31\3\31\5\31\u0169")
        buf.write("\n\31\3\32\3\32\3\32\7\32\u016e\n\32\f\32\16\32\u0171")
        buf.write("\13\32\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3")
        buf.write("\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33\3\33")
        buf.write("\3\33\3\33\3\33\3\33\5\33\u018b\n\33\3\33\3\33\5\33\u018f")
        buf.write("\n\33\3\34\3\34\3\34\3\34\5\34\u0195\n\34\3\34\3\34\5")
        buf.write("\34\u0199\n\34\5\34\u019b\n\34\3\35\3\35\3\35\3\35\3\35")
        buf.write("\5\35\u01a2\n\35\3\36\3\36\3\37\3\37\3 \3 \3!\3!\3!\2")
        buf.write('\4,."\2\4\6\b\n\f\16\20\22\24\26\30\32\34\36 "$&(*,')
        buf.write(".\60\62\64\668:<>@\2\20\3\2\22\30\3\2\678\3\2LM\4\2IJ")
        buf.write("NN\3\2\63\64\4\2..KK\4\2\65\66RS\4\2\60\60\678\4\2,,9")
        buf.write("9\4\2--::\4\2//;;\3\2TV\3\2WX\3\2)+\2\u01d5\2C\3\2\2\2")
        buf.write("\4N\3\2\2\2\6Q\3\2\2\2\bT\3\2\2\2\nf\3\2\2\2\fv\3\2\2")
        buf.write("\2\16z\3\2\2\2\20\177\3\2\2\2\22\u0081\3\2\2\2\24\u008b")
        buf.write("\3\2\2\2\26\u0096\3\2\2\2\30\u00a3\3\2\2\2\32\u00ab\3")
        buf.write("\2\2\2\34\u00af\3\2\2\2\36\u00b1\3\2\2\2 \u00b8\3\2\2")
        buf.write('\2"\u00c0\3\2\2\2$\u00c9\3\2\2\2&\u00cd\3\2\2\2(\u00d1')
        buf.write("\3\2\2\2*\u00d3\3\2\2\2,\u00f8\3\2\2\2.\u012d\3\2\2\2")
        buf.write("\60\u0168\3\2\2\2\62\u016a\3\2\2\2\64\u018e\3\2\2\2\66")
        buf.write("\u019a\3\2\2\28\u01a1\3\2\2\2:\u01a3\3\2\2\2<\u01a5\3")
        buf.write("\2\2\2>\u01a7\3\2\2\2@\u01a9\3\2\2\2BD\5\b\5\2CB\3\2\2")
        buf.write("\2CD\3\2\2\2DH\3\2\2\2EG\5\20\t\2FE\3\2\2\2GJ\3\2\2\2")
        buf.write("HF\3\2\2\2HI\3\2\2\2IK\3\2\2\2JH\3\2\2\2KL\5\30\r\2LM")
        buf.write("\7\2\2\3M\3\3\2\2\2NO\5,\27\2OP\7\2\2\3P\5\3\2\2\2QR\5")
        buf.write(".\30\2RS\7\2\2\3S\7\3\2\2\2TU\7\3\2\2UW\5\n\6\2VX\5\f")
        buf.write("\7\2WV\3\2\2\2WX\3\2\2\2X[\3\2\2\2YZ\7\7\2\2Z\\\5.\30")
        buf.write("\2[Y\3\2\2\2[\\\3\2\2\2\\]\3\2\2\2]^\7?\2\2^\t\3\2\2\2")
        buf.write("_g\7\4\2\2`g\7\5\2\2ab\7\6\2\2bc\7C\2\2cd\5@!\2de\7D\2")
        buf.write("\2eg\3\2\2\2f_\3\2\2\2f`\3\2\2\2fa\3\2\2\2g\13\3\2\2\2")
        buf.write("hi\7\b\2\2iw\7J\2\2jk\7\b\2\2kl\7A\2\2lq\5\16\b\2mn\7")
        buf.write("@\2\2np\5\16\b\2om\3\2\2\2ps\3\2\2\2qo\3\2\2\2qr\3\2\2")
        buf.write("\2rt\3\2\2\2sq\3\2\2\2tu\7B\2\2uw\3\2\2\2vh\3\2\2\2vj")
        buf.write("\3\2\2\2w\r\3\2\2\2x{\7Z\2\2y{\5@!\2zx\3\2\2\2zy\3\2\2")
        buf.write("\2{\17\3\2\2\2|\u0080\5\22\n\2}\u0080\5\24\13\2~\u0080")
        buf.write("\5\26\f\2\177|\3\2\2\2\177}\3\2\2\2\177~\3\2\2\2\u0080")
        buf.write("\21\3\2\2\2\u0081\u0085\7\t\2\2\u0082\u0086\7\n\2\2\u0083")
        buf.write("\u0084\7\13\2\2\u0084\u0086\5*\26\2\u0085\u0082\3\2\2")
        buf.write("\2\u0085\u0083\3\2\2\2\u0086\u0087\3\2\2\2\u0087\u0088")
        buf.write("\7G\2\2\u0088\u0089\5.\30\2\u0089\u008a\7?\2\2\u008a\23")
        buf.write("\3\2\2\2\u008b\u008c\7\t\2\2\u008c\u008d\7\f\2\2\u008d")
        buf.write("\u008e\7C\2\2\u008e\u008f\5@!\2\u008f\u0090\7@\2\2\u0090")
        buf.write('\u0091\5$\23\2\u0091\u0092\7D\2\2\u0092\u0093\5"\22\2')
        buf.write("\u0093\u0094\5<\37\2\u0094\u0095\7?\2\2\u0095\25\3\2\2")
        buf.write("\2\u0096\u0097\7\t\2\2\u0097\u0098\7\r\2\2\u0098\u009f")
        buf.write("\7\16\2\2\u0099\u00a0\7\17\2\2\u009a\u009b\7\20\2\2\u009b")
        buf.write("\u009c\7A\2\2\u009c\u009d\5 \21\2\u009d\u009e\7B\2\2\u009e")
        buf.write("\u00a0\3\2\2\2\u009f\u0099\3\2\2\2\u009f\u009a\3\2\2\2")
        buf.write("\u00a0\u00a1\3\2\2\2\u00a1\u00a2\7?\2\2\u00a2\27\3\2\2")
        buf.write("\2\u00a3\u00a4\7\21\2\2\u00a4\u00a5\5\32\16\2\u00a5\u00a6")
        buf.write("\7\65\2\2\u00a6\u00a7\5*\26\2\u00a7\u00a8\7G\2\2\u00a8")
        buf.write("\u00a9\5\34\17\2\u00a9\u00aa\7?\2\2\u00aa\31\3\2\2\2\u00ab")
        buf.write("\u00ac\t\2\2\2\u00ac\33\3\2\2\2\u00ad\u00b0\5\36\20\2")
        buf.write("\u00ae\u00b0\5.\30\2\u00af\u00ad\3\2\2\2\u00af\u00ae\3")
        buf.write("\2\2\2\u00b0\35\3\2\2\2\u00b1\u00b2\7\31\2\2\u00b2\u00b3")
        buf.write("\5.\30\2\u00b3\u00b4\7<\2\2\u00b4\u00b5\7\32\2\2\u00b5")
        buf.write("\u00b6\5*\26\2\u00b6\u00b7\5.\30\2\u00b7\37\3\2\2\2\u00b8")
        buf.write("\u00bd\5@!\2\u00b9\u00ba\7@\2\2\u00ba\u00bc\5@!\2\u00bb")
        buf.write("\u00b9\3\2\2\2\u00bc\u00bf\3\2\2\2\u00bd\u00bb\3\2\2\2")
        buf.write("\u00bd\u00be\3\2\2\2\u00be!\3\2\2\2\u00bf\u00bd\3\2\2")
        buf.write("\2\u00c0\u00c1\t\3\2\2\u00c1#\3\2\2\2\u00c2\u00ca\7J\2")
        buf.write("\2\u00c3\u00ca\5*\26\2\u00c4\u00c5\5*\26\2\u00c5\u00c6")
        buf.write("\7>\2\2\u00c6\u00c7\5*\26\2\u00c7\u00ca\3\2\2\2\u00c8")
        buf.write("\u00ca\7=\2\2\u00c9\u00c2\3\2\2\2\u00c9\u00c3\3\2\2\2")
        buf.write("\u00c9\u00c4\3\2\2\2\u00c9\u00c8\3\2\2\2\u00ca%\3\2\2")
        buf.write("\2\u00cb\u00ce\7!\2\2\u00cc\u00ce\5*\26\2\u00cd\u00cb")
        buf.write("\3\2\2\2\u00cd\u00cc\3\2\2\2\u00ce'\3\2\2\2\u00cf\u00d2")
        buf.write("\7!\2\2\u00d0\u00d2\5*\26\2\u00d1\u00cf\3\2\2\2\u00d1")
        buf.write("\u00d0\3\2\2\2\u00d2)\3\2\2\2\u00d3\u00d4\7V\2\2\u00d4")
        buf.write("+\3\2\2\2\u00d5\u00d6\b\27\1\2\u00d6\u00d7\7C\2\2\u00d7")
        buf.write("\u00d8\5,\27\2\u00d8\u00d9\7D\2\2\u00d9\u00f9\3\2\2\2")
        buf.write("\u00da\u00f9\5:\36\2\u00db\u00f9\7Z\2\2\u00dc\u00f9\5")
        buf.write("> \2\u00dd\u00de\7\33\2\2\u00de\u00df\7C\2\2\u00df\u00e0")
        buf.write("\5@!\2\u00e0\u00e1\7D\2\2\u00e1\u00f9\3\2\2\2\u00e2\u00f9")
        buf.write("\7\34\2\2\u00e3\u00e4\7\37\2\2\u00e4\u00e6\7C\2\2\u00e5")
        buf.write("\u00e7\5\62\32\2\u00e6\u00e5\3\2\2\2\u00e6\u00e7\3\2\2")
        buf.write("\2\u00e7\u00e8\3\2\2\2\u00e8\u00f9\7D\2\2\u00e9\u00ea")
        buf.write("\t\4\2\2\u00ea\u00f9\5,\27\f\u00eb\u00ec\7Y\2\2\u00ec")
        buf.write("\u00ed\7C\2\2\u00ed\u00ee\5,\27\2\u00ee\u00ef\7D\2\2\u00ef")
        buf.write("\u00f9\3\2\2\2\u00f0\u00f1\7C\2\2\u00f1\u00f2\5.\30\2")
        buf.write("\u00f2\u00f3\7D\2\2\u00f3\u00f4\7E\2\2\u00f4\u00f5\5,")
        buf.write("\27\2\u00f5\u00f6\7G\2\2\u00f6\u00f7\5,\27\3\u00f7\u00f9")
        buf.write("\3\2\2\2\u00f8\u00d5\3\2\2\2\u00f8\u00da\3\2\2\2\u00f8")
        buf.write("\u00db\3\2\2\2\u00f8\u00dc\3\2\2\2\u00f8\u00dd\3\2\2\2")
        buf.write("\u00f8\u00e2\3\2\2\2\u00f8\u00e3\3\2\2\2\u00f8\u00e9\3")
        buf.write("\2\2\2\u00f8\u00eb\3\2\2\2\u00f8\u00f0\3\2\2\2\u00f9\u0111")
        buf.write("\3\2\2\2\u00fa\u00fb\f\13\2\2\u00fb\u00fc\7\62\2\2\u00fc")
        buf.write("\u0110\5,\27\13\u00fd\u00fe\f\n\2\2\u00fe\u00ff\t\5\2")
        buf.write("\2\u00ff\u0110\5,\27\13\u0100\u0101\f\t\2\2\u0101\u0102")
        buf.write("\t\4\2\2\u0102\u0110\5,\27\n\u0103\u0104\f\b\2\2\u0104")
        buf.write("\u0105\t\6\2\2\u0105\u0110\5,\27\t\u0106\u0107\f\7\2\2")
        buf.write("\u0107\u0108\7O\2\2\u0108\u0110\5,\27\b\u0109\u010a\f")
        buf.write("\6\2\2\u010a\u010b\7P\2\2\u010b\u0110\5,\27\7\u010c\u010d")
        buf.write("\f\5\2\2\u010d\u010e\7Q\2\2\u010e\u0110\5,\27\6\u010f")
        buf.write("\u00fa\3\2\2\2\u010f\u00fd\3\2\2\2\u010f\u0100\3\2\2\2")
        buf.write("\u010f\u0103\3\2\2\2\u010f\u0106\3\2\2\2\u010f\u0109\3")
        buf.write("\2\2\2\u010f\u010c\3\2\2\2\u0110\u0113\3\2\2\2\u0111\u010f")
        buf.write("\3\2\2\2\u0111\u0112\3\2\2\2\u0112-\3\2\2\2\u0113\u0111")
        buf.write("\3\2\2\2\u0114\u0115\b\30\1\2\u0115\u0116\7C\2\2\u0116")
        buf.write("\u0117\5.\30\2\u0117\u0118\7D\2\2\u0118\u012e\3\2\2\2")
        buf.write("\u0119\u012e\5<\37\2\u011a\u012e\5\60\31\2\u011b\u011c")
        buf.write("\t\7\2\2\u011c\u012e\5.\30\13\u011d\u011e\5,\27\2\u011e")
        buf.write("\u011f\t\b\2\2\u011f\u0120\5,\27\2\u0120\u012e\3\2\2\2")
        buf.write("\u0121\u0122\5,\27\2\u0122\u0123\t\3\2\2\u0123\u0124\5")
        buf.write(",\27\2\u0124\u012e\3\2\2\2\u0125\u0126\7C\2\2\u0126\u0127")
        buf.write("\5.\30\2\u0127\u0128\7D\2\2\u0128\u0129\7E\2\2\u0129\u012a")
        buf.write("\5.\30\2\u012a\u012b\7G\2\2\u012b\u012c\5.\30\3\u012c")
        buf.write("\u012e\3\2\2\2\u012d\u0114\3\2\2\2\u012d\u0119\3\2\2\2")
        buf.write("\u012d\u011a\3\2\2\2\u012d\u011b\3\2\2\2\u012d\u011d\3")
        buf.write("\2\2\2\u012d\u0121\3\2\2\2\u012d\u0125\3\2\2\2\u012e\u0140")
        buf.write("\3\2\2\2\u012f\u0130\f\b\2\2\u0130\u0131\t\t\2\2\u0131")
        buf.write("\u013f\5.\30\t\u0132\u0133\f\7\2\2\u0133\u0134\t\n\2\2")
        buf.write("\u0134\u013f\5.\30\b\u0135\u0136\f\6\2\2\u0136\u0137\7")
        buf.write("\61\2\2\u0137\u013f\5.\30\7\u0138\u0139\f\5\2\2\u0139")
        buf.write("\u013a\t\13\2\2\u013a\u013f\5.\30\6\u013b\u013c\f\4\2")
        buf.write("\2\u013c\u013d\t\f\2\2\u013d\u013f\5.\30\4\u013e\u012f")
        buf.write("\3\2\2\2\u013e\u0132\3\2\2\2\u013e\u0135\3\2\2\2\u013e")
        buf.write("\u0138\3\2\2\2\u013e\u013b\3\2\2\2\u013f\u0142\3\2\2\2")
        buf.write("\u0140\u013e\3\2\2\2\u0140\u0141\3\2\2\2\u0141/\3\2\2")
        buf.write("\2\u0142\u0140\3\2\2\2\u0143\u0144\7\35\2\2\u0144\u0145")
        buf.write("\7C\2\2\u0145\u0148\5@!\2\u0146\u0147\7@\2\2\u0147\u0149")
        buf.write("\5(\25\2\u0148\u0146\3\2\2\2\u0148\u0149\3\2\2\2\u0149")
        buf.write("\u014a\3\2\2\2\u014a\u014b\7D\2\2\u014b\u0169\3\2\2\2")
        buf.write("\u014c\u014d\7\5\2\2\u014d\u014f\7C\2\2\u014e\u0150\5")
        buf.write("(\25\2\u014f\u014e\3\2\2\2\u014f\u0150\3\2\2\2\u0150\u0151")
        buf.write("\3\2\2\2\u0151\u0169\7D\2\2\u0152\u0153\7\f\2\2\u0153")
        buf.write("\u0154\7C\2\2\u0154\u0155\5@!\2\u0155\u0156\7@\2\2\u0156")
        buf.write("\u0157\5&\24\2\u0157\u0158\7D\2\2\u0158\u0169\3\2\2\2")
        buf.write("\u0159\u015a\7\36\2\2\u015a\u015b\7C\2\2\u015b\u015e\5")
        buf.write("@!\2\u015c\u015d\7@\2\2\u015d\u015f\5(\25\2\u015e\u015c")
        buf.write("\3\2\2\2\u015e\u015f\3\2\2\2\u015f\u0160\3\2\2\2\u0160")
        buf.write("\u0161\7D\2\2\u0161\u0169\3\2\2\2\u0162\u0163\7 \2\2\u0163")
        buf.write("\u0165\7C\2\2\u0164\u0166\5\62\32\2\u0165\u0164\3\2\2")
        buf.write("\2\u0165\u0166\3\2\2\2\u0166\u0167\3\2\2\2\u0167\u0169")
        buf.write("\7D\2\2\u0168\u0143\3\2\2\2\u0168\u014c\3\2\2\2\u0168")
        buf.write("\u0152\3\2\2\2\u0168\u0159\3\2\2\2\u0168\u0162\3\2\2\2")
        buf.write("\u0169\61\3\2\2\2\u016a\u016f\5\64\33\2\u016b\u016c\7")
        buf.write("@\2\2\u016c\u016e\5\64\33\2\u016d\u016b\3\2\2\2\u016e")
        buf.write("\u0171\3\2\2\2\u016f\u016d\3\2\2\2\u016f\u0170\3\2\2\2")
        buf.write("\u0170\63\3\2\2\2\u0171\u016f\3\2\2\2\u0172\u018f\5@!")
        buf.write("\2\u0173\u018f\5\66\34\2\u0174\u0175\7#\2\2\u0175\u0176")
        buf.write("\7F\2\2\u0176\u018f\5@!\2\u0177\u0178\7$\2\2\u0178\u0179")
        buf.write("\7F\2\2\u0179\u018f\5\66\34\2\u017a\u017b\7%\2\2\u017b")
        buf.write("\u017c\7F\2\2\u017c\u018f\5@!\2\u017d\u017e\7&\2\2\u017e")
        buf.write("\u017f\7F\2\2\u017f\u018f\5@!\2\u0180\u0181\7\6\2\2\u0181")
        buf.write("\u0182\7F\2\2\u0182\u018f\5@!\2\u0183\u0184\7'\2\2\u0184")
        buf.write("\u0185\7F\2\2\u0185\u018f\5@!\2\u0186\u0187\7(\2\2\u0187")
        buf.write('\u018a\7F\2\2\u0188\u018b\5@!\2\u0189\u018b\7"\2\2\u018a')
        buf.write("\u0188\3\2\2\2\u018a\u0189\3\2\2\2\u018b\u018f\3\2\2\2")
        buf.write("\u018c\u018d\7\7\2\2\u018d\u018f\5.\30\2\u018e\u0172\3")
        buf.write("\2\2\2\u018e\u0173\3\2\2\2\u018e\u0174\3\2\2\2\u018e\u0177")
        buf.write("\3\2\2\2\u018e\u017a\3\2\2\2\u018e\u017d\3\2\2\2\u018e")
        buf.write("\u0180\3\2\2\2\u018e\u0183\3\2\2\2\u018e\u0186\3\2\2\2")
        buf.write("\u018e\u018c\3\2\2\2\u018f\65\3\2\2\2\u0190\u019b\7J\2")
        buf.write("\2\u0191\u019b\7=\2\2\u0192\u019b\58\35\2\u0193\u0195")
        buf.write("\58\35\2\u0194\u0193\3\2\2\2\u0194\u0195\3\2\2\2\u0195")
        buf.write("\u0196\3\2\2\2\u0196\u0198\7>\2\2\u0197\u0199\58\35\2")
        buf.write("\u0198\u0197\3\2\2\2\u0198\u0199\3\2\2\2\u0199\u019b\3")
        buf.write("\2\2\2\u019a\u0190\3\2\2\2\u019a\u0191\3\2\2\2\u019a\u0192")
        buf.write("\3\2\2\2\u019a\u0194\3\2\2\2\u019b\67\3\2\2\2\u019c\u01a2")
        buf.write("\5*\26\2\u019d\u019e\7L\2\2\u019e\u01a2\5*\26\2\u019f")
        buf.write("\u01a0\7M\2\2\u01a0\u01a2\5*\26\2\u01a1\u019c\3\2\2\2")
        buf.write("\u01a1\u019d\3\2\2\2\u01a1\u019f\3\2\2\2\u01a29\3\2\2")
        buf.write("\2\u01a3\u01a4\t\r\2\2\u01a4;\3\2\2\2\u01a5\u01a6\t\16")
        buf.write("\2\2\u01a6=\3\2\2\2\u01a7\u01a8\t\17\2\2\u01a8?\3\2\2")
        buf.write("\2\u01a9\u01aa\7[\2\2\u01aaA\3\2\2\2%CHW[fqvz\177\u0085")
        buf.write("\u009f\u00af\u00bd\u00c9\u00cd\u00d1\u00e6\u00f8\u010f")
        buf.write("\u0111\u012d\u013e\u0140\u0148\u014f\u015e\u0165\u0168")
        buf.write("\u016f\u018a\u018e\u0194\u0198\u019a\u01a1")
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
        "'null'",
        "'action'",
        "'step'",
        "'stage'",
        "'role'",
        "'active_leaf'",
        "'named_ref'",
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
        "NULL",
        "ACTION",
        "STEP",
        "STAGE",
        "ROLE",
        "ACTIVE_LEAF",
        "NAMED_REF",
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
    RULE_call_step_selector = 26
    RULE_call_step_point = 27
    RULE_num_literal = 28
    RULE_bool_literal = 29
    RULE_math_const = 30
    RULE_string_literal = 31

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
    NULL = 32
    ACTION = 33
    STEP = 34
    STAGE = 35
    ROLE = 36
    ACTIVE_LEAF = 37
    NAMED_REF = 38
    PI_CONST = 39
    E_CONST = 40
    TAU_CONST = 41
    AND_KW = 42
    OR_KW = 43
    NOT_KW = 44
    IMPLIES_KW = 45
    IFF_KW = 46
    XOR_KW = 47
    POW = 48
    SHIFT_RIGHT = 49
    SHIFT_LEFT = 50
    LE = 51
    GE = 52
    EQ = 53
    NE = 54
    LOGICAL_AND = 55
    LOGICAL_OR = 56
    IMPLIES = 57
    ARROW = 58
    RANGE_INT = 59
    DOTDOT = 60
    SEMI = 61
    COMMA = 62
    LBRACE = 63
    RBRACE = 64
    LPAREN = 65
    RPAREN = 66
    QUESTION = 67
    ASSIGN = 68
    COLON = 69
    DOT = 70
    SLASH = 71
    STAR = 72
    BANG = 73
    PLUS = 74
    MINUS = 75
    PERCENT = 76
    AMP = 77
    CARET = 78
    PIPE = 79
    LT = 80
    GT = 81
    FLOAT = 82
    HEX_INT = 83
    INT = 84
    TRUE = 85
    FALSE = 86
    UFUNC_NAME = 87
    ID = 88
    STRING = 89
    MULTILINE_COMMENT = 90
    LINE_COMMENT = 91
    PYTHON_COMMENT = 92
    WS = 93

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
            self.state = 65
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == BmcQueryParser.INIT:
                self.state = 64
                self.init_clause()

            self.state = 70
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == BmcQueryParser.ASSUME:
                self.state = 67
                self.assume_clause()
                self.state = 72
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 73
            self.check_clause()
            self.state = 74
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
            self.state = 76
            self.bmc_num_expression(0)
            self.state = 77
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
            self.state = 79
            self.bmc_cond_expression(0)
            self.state = 80
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
            self.state = 82
            self.match(BmcQueryParser.INIT)
            self.state = 83
            self.init_target()
            self.state = 85
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == BmcQueryParser.HAVOC:
                self.state = 84
                self.init_havoc_clause()

            self.state = 89
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la == BmcQueryParser.WHERE:
                self.state = 87
                self.match(BmcQueryParser.WHERE)
                self.state = 88
                self.bmc_cond_expression(0)

            self.state = 91
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
            self.state = 100
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.COLD]:
                self.enterOuterAlt(localctx, 1)
                self.state = 93
                self.match(BmcQueryParser.COLD)
                pass
            elif token in [BmcQueryParser.TERMINATED]:
                self.enterOuterAlt(localctx, 2)
                self.state = 94
                self.match(BmcQueryParser.TERMINATED)
                pass
            elif token in [BmcQueryParser.STATE]:
                self.enterOuterAlt(localctx, 3)
                self.state = 95
                self.match(BmcQueryParser.STATE)
                self.state = 96
                self.match(BmcQueryParser.LPAREN)
                self.state = 97
                self.string_literal()
                self.state = 98
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
            self.state = 116
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 6, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 102
                self.match(BmcQueryParser.HAVOC)
                self.state = 103
                self.match(BmcQueryParser.STAR)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 104
                self.match(BmcQueryParser.HAVOC)
                self.state = 105
                self.match(BmcQueryParser.LBRACE)
                self.state = 106
                self.init_var_ref()
                self.state = 111
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la == BmcQueryParser.COMMA:
                    self.state = 107
                    self.match(BmcQueryParser.COMMA)
                    self.state = 108
                    self.init_var_ref()
                    self.state = 113
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                self.state = 114
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
            self.state = 120
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ID]:
                self.enterOuterAlt(localctx, 1)
                self.state = 118
                self.match(BmcQueryParser.ID)
                pass
            elif token in [BmcQueryParser.STRING]:
                self.enterOuterAlt(localctx, 2)
                self.state = 119
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
            self.state = 125
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 8, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 122
                self.frame_assume()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 123
                self.event_assume()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 124
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
            self.state = 127
            self.match(BmcQueryParser.ASSUME)
            self.state = 131
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ALWAYS]:
                self.state = 128
                self.match(BmcQueryParser.ALWAYS)
                pass
            elif token in [BmcQueryParser.AT]:
                self.state = 129
                self.match(BmcQueryParser.AT)
                self.state = 130
                self.integer_literal()
                pass
            else:
                raise NoViableAltException(self)

            self.state = 133
            self.match(BmcQueryParser.COLON)
            self.state = 134
            self.bmc_cond_expression(0)
            self.state = 135
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
            self.state = 137
            self.match(BmcQueryParser.ASSUME)
            self.state = 138
            self.match(BmcQueryParser.EVENT)
            self.state = 139
            self.match(BmcQueryParser.LPAREN)
            self.state = 140
            self.string_literal()
            self.state = 141
            self.match(BmcQueryParser.COMMA)
            self.state = 142
            self.event_range_selector()
            self.state = 143
            self.match(BmcQueryParser.RPAREN)
            self.state = 144
            self.bool_cmp_op()
            self.state = 145
            self.bool_literal()
            self.state = 146
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
            self.state = 148
            self.match(BmcQueryParser.ASSUME)
            self.state = 149
            self.match(BmcQueryParser.EVENTS)
            self.state = 150
            self.match(BmcQueryParser.CARDINALITY)
            self.state = 157
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ANY]:
                self.state = 151
                self.match(BmcQueryParser.ANY)
                pass
            elif token in [BmcQueryParser.AT_MOST_ONE]:
                self.state = 152
                self.match(BmcQueryParser.AT_MOST_ONE)
                self.state = 153
                self.match(BmcQueryParser.LBRACE)
                self.state = 154
                self.string_list()
                self.state = 155
                self.match(BmcQueryParser.RBRACE)
                pass
            else:
                raise NoViableAltException(self)

            self.state = 159
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
            self.state = 161
            self.match(BmcQueryParser.CHECK)
            self.state = 162
            self.property_kind()
            self.state = 163
            self.match(BmcQueryParser.LE)
            self.state = 164
            self.integer_literal()
            self.state = 165
            self.match(BmcQueryParser.COLON)
            self.state = 166
            self.property_body()
            self.state = 167
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
            self.state = 169
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
            self.state = 173
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.TRIGGER]:
                self.enterOuterAlt(localctx, 1)
                self.state = 171
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
                self.state = 172
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
            self.state = 175
            self.match(BmcQueryParser.TRIGGER)
            self.state = 176
            self.bmc_cond_expression(0)
            self.state = 177
            self.match(BmcQueryParser.ARROW)
            self.state = 178
            self.match(BmcQueryParser.WITHIN)
            self.state = 179
            self.integer_literal()
            self.state = 180
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
            self.state = 182
            self.string_literal()
            self.state = 187
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == BmcQueryParser.COMMA:
                self.state = 183
                self.match(BmcQueryParser.COMMA)
                self.state = 184
                self.string_literal()
                self.state = 189
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
            self.state = 190
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
            self.state = 199
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 13, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 192
                self.match(BmcQueryParser.STAR)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 193
                self.integer_literal()
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 194
                self.integer_literal()
                self.state = 195
                self.match(BmcQueryParser.DOTDOT)
                self.state = 196
                self.integer_literal()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 198
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
            self.state = 203
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.CURRENT]:
                self.enterOuterAlt(localctx, 1)
                self.state = 201
                self.match(BmcQueryParser.CURRENT)
                pass
            elif token in [BmcQueryParser.INT]:
                self.enterOuterAlt(localctx, 2)
                self.state = 202
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
            self.state = 207
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.CURRENT]:
                self.enterOuterAlt(localctx, 1)
                self.state = 205
                self.match(BmcQueryParser.CURRENT)
                pass
            elif token in [BmcQueryParser.INT]:
                self.enterOuterAlt(localctx, 2)
                self.state = 206
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
            self.state = 209
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
            self.state = 246
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 17, self._ctx)
            if la_ == 1:
                localctx = BmcQueryParser.ParenExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 212
                self.match(BmcQueryParser.LPAREN)
                self.state = 213
                self.bmc_num_expression(0)
                self.state = 214
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = BmcQueryParser.LiteralExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 216
                self.num_literal()
                pass

            elif la_ == 3:
                localctx = BmcQueryParser.IdExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 217
                self.match(BmcQueryParser.ID)
                pass

            elif la_ == 4:
                localctx = BmcQueryParser.MathConstExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 218
                self.math_const()
                pass

            elif la_ == 5:
                localctx = BmcQueryParser.FrameVarExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 219
                self.match(BmcQueryParser.VAR)
                self.state = 220
                self.match(BmcQueryParser.LPAREN)
                self.state = 221
                self.string_literal()
                self.state = 222
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 6:
                localctx = BmcQueryParser.CycleExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 224
                self.match(BmcQueryParser.CYCLE)
                pass

            elif la_ == 7:
                localctx = BmcQueryParser.CallCountExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 225
                self.match(BmcQueryParser.CALL_COUNT)
                self.state = 226
                self.match(BmcQueryParser.LPAREN)
                self.state = 228
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (
                    ((_la) & ~0x3F) == 0
                    and (
                        (1 << _la)
                        & (
                            (1 << BmcQueryParser.STATE)
                            | (1 << BmcQueryParser.WHERE)
                            | (1 << BmcQueryParser.ACTION)
                            | (1 << BmcQueryParser.STEP)
                            | (1 << BmcQueryParser.STAGE)
                            | (1 << BmcQueryParser.ROLE)
                            | (1 << BmcQueryParser.ACTIVE_LEAF)
                            | (1 << BmcQueryParser.NAMED_REF)
                            | (1 << BmcQueryParser.RANGE_INT)
                            | (1 << BmcQueryParser.DOTDOT)
                        )
                    )
                    != 0
                ) or (
                    ((_la - 72) & ~0x3F) == 0
                    and (
                        (1 << (_la - 72))
                        & (
                            (1 << (BmcQueryParser.STAR - 72))
                            | (1 << (BmcQueryParser.PLUS - 72))
                            | (1 << (BmcQueryParser.MINUS - 72))
                            | (1 << (BmcQueryParser.INT - 72))
                            | (1 << (BmcQueryParser.STRING - 72))
                        )
                    )
                    != 0
                ):
                    self.state = 227
                    self.call_arguments()

                self.state = 230
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 8:
                localctx = BmcQueryParser.UnaryExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 231
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == BmcQueryParser.PLUS or _la == BmcQueryParser.MINUS):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 232
                self.bmc_num_expression(10)
                pass

            elif la_ == 9:
                localctx = BmcQueryParser.FuncExprNumContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 233
                localctx.func_name = self.match(BmcQueryParser.UFUNC_NAME)
                self.state = 234
                self.match(BmcQueryParser.LPAREN)
                self.state = 235
                self.bmc_num_expression(0)
                self.state = 236
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 10:
                localctx = BmcQueryParser.ConditionalCStyleExprNumContext(
                    self, localctx
                )
                self._ctx = localctx
                _prevctx = localctx
                self.state = 238
                self.match(BmcQueryParser.LPAREN)
                self.state = 239
                self.bmc_cond_expression(0)
                self.state = 240
                self.match(BmcQueryParser.RPAREN)
                self.state = 241
                self.match(BmcQueryParser.QUESTION)
                self.state = 242
                self.bmc_num_expression(0)
                self.state = 243
                self.match(BmcQueryParser.COLON)
                self.state = 244
                self.bmc_num_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 271
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 19, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 269
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
                        self.state = 248
                        if not self.precpred(self._ctx, 9):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 9)"
                            )
                        self.state = 249
                        localctx.op = self.match(BmcQueryParser.POW)
                        self.state = 250
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
                        self.state = 251
                        if not self.precpred(self._ctx, 8):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 8)"
                            )
                        self.state = 252
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            ((_la - 71) & ~0x3F) == 0
                            and (
                                (1 << (_la - 71))
                                & (
                                    (1 << (BmcQueryParser.SLASH - 71))
                                    | (1 << (BmcQueryParser.STAR - 71))
                                    | (1 << (BmcQueryParser.PERCENT - 71))
                                )
                            )
                            != 0
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 253
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
                        self.state = 254
                        if not self.precpred(self._ctx, 7):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 7)"
                            )
                        self.state = 255
                        localctx.op = self._input.LT(1)
                        _la = self._input.LA(1)
                        if not (
                            _la == BmcQueryParser.PLUS or _la == BmcQueryParser.MINUS
                        ):
                            localctx.op = self._errHandler.recoverInline(self)
                        else:
                            self._errHandler.reportMatch(self)
                            self.consume()
                        self.state = 256
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
                        self.state = 257
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 258
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
                        self.state = 259
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
                        self.state = 260
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 261
                        localctx.op = self.match(BmcQueryParser.AMP)
                        self.state = 262
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
                        self.state = 263
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 264
                        localctx.op = self.match(BmcQueryParser.CARET)
                        self.state = 265
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
                        self.state = 266
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 267
                        localctx.op = self.match(BmcQueryParser.PIPE)
                        self.state = 268
                        self.bmc_num_expression(4)
                        pass

                self.state = 273
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
            self.state = 299
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 20, self._ctx)
            if la_ == 1:
                localctx = BmcQueryParser.ParenExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx

                self.state = 275
                self.match(BmcQueryParser.LPAREN)
                self.state = 276
                self.bmc_cond_expression(0)
                self.state = 277
                self.match(BmcQueryParser.RPAREN)
                pass

            elif la_ == 2:
                localctx = BmcQueryParser.LiteralExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 279
                self.bool_literal()
                pass

            elif la_ == 3:
                localctx = BmcQueryParser.AtomExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 280
                self.bmc_boolean_atom()
                pass

            elif la_ == 4:
                localctx = BmcQueryParser.UnaryExprCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 281
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == BmcQueryParser.NOT_KW or _la == BmcQueryParser.BANG):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 282
                self.bmc_cond_expression(9)
                pass

            elif la_ == 5:
                localctx = BmcQueryParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 283
                self.bmc_num_expression(0)
                self.state = 284
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (
                    ((_la - 51) & ~0x3F) == 0
                    and (
                        (1 << (_la - 51))
                        & (
                            (1 << (BmcQueryParser.LE - 51))
                            | (1 << (BmcQueryParser.GE - 51))
                            | (1 << (BmcQueryParser.LT - 51))
                            | (1 << (BmcQueryParser.GT - 51))
                        )
                    )
                    != 0
                ):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 285
                self.bmc_num_expression(0)
                pass

            elif la_ == 6:
                localctx = BmcQueryParser.BinaryExprFromNumCondContext(self, localctx)
                self._ctx = localctx
                _prevctx = localctx
                self.state = 287
                self.bmc_num_expression(0)
                self.state = 288
                localctx.op = self._input.LT(1)
                _la = self._input.LA(1)
                if not (_la == BmcQueryParser.EQ or _la == BmcQueryParser.NE):
                    localctx.op = self._errHandler.recoverInline(self)
                else:
                    self._errHandler.reportMatch(self)
                    self.consume()
                self.state = 289
                self.bmc_num_expression(0)
                pass

            elif la_ == 7:
                localctx = BmcQueryParser.ConditionalCStyleExprCondContext(
                    self, localctx
                )
                self._ctx = localctx
                _prevctx = localctx
                self.state = 291
                self.match(BmcQueryParser.LPAREN)
                self.state = 292
                self.bmc_cond_expression(0)
                self.state = 293
                self.match(BmcQueryParser.RPAREN)
                self.state = 294
                self.match(BmcQueryParser.QUESTION)
                self.state = 295
                self.bmc_cond_expression(0)
                self.state = 296
                self.match(BmcQueryParser.COLON)
                self.state = 297
                self.bmc_cond_expression(1)
                pass

            self._ctx.stop = self._input.LT(-1)
            self.state = 318
            self._errHandler.sync(self)
            _alt = self._interp.adaptivePredict(self._input, 22, self._ctx)
            while _alt != 2 and _alt != ATN.INVALID_ALT_NUMBER:
                if _alt == 1:
                    if self._parseListeners is not None:
                        self.triggerExitRuleEvent()
                    _prevctx = localctx
                    self.state = 316
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
                        self.state = 301
                        if not self.precpred(self._ctx, 6):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 6)"
                            )
                        self.state = 302
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
                        self.state = 303
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
                        self.state = 304
                        if not self.precpred(self._ctx, 5):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 5)"
                            )
                        self.state = 305
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
                        self.state = 306
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
                        self.state = 307
                        if not self.precpred(self._ctx, 4):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 4)"
                            )
                        self.state = 308
                        localctx.op = self.match(BmcQueryParser.XOR_KW)
                        self.state = 309
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
                        self.state = 310
                        if not self.precpred(self._ctx, 3):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 3)"
                            )
                        self.state = 311
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
                        self.state = 312
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
                        self.state = 313
                        if not self.precpred(self._ctx, 2):
                            from antlr4.error.Errors import FailedPredicateException

                            raise FailedPredicateException(
                                self, "self.precpred(self._ctx, 2)"
                            )
                        self.state = 314
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
                        self.state = 315
                        self.bmc_cond_expression(2)
                        pass

                self.state = 320
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
            self.state = 358
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.ACTIVE]:
                self.enterOuterAlt(localctx, 1)
                self.state = 321
                self.match(BmcQueryParser.ACTIVE)
                self.state = 322
                self.match(BmcQueryParser.LPAREN)
                self.state = 323
                self.string_literal()
                self.state = 326
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == BmcQueryParser.COMMA:
                    self.state = 324
                    self.match(BmcQueryParser.COMMA)
                    self.state = 325
                    self.frame_selector()

                self.state = 328
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.TERMINATED]:
                self.enterOuterAlt(localctx, 2)
                self.state = 330
                self.match(BmcQueryParser.TERMINATED)
                self.state = 331
                self.match(BmcQueryParser.LPAREN)
                self.state = 333
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == BmcQueryParser.CURRENT or _la == BmcQueryParser.INT:
                    self.state = 332
                    self.frame_selector()

                self.state = 335
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.EVENT]:
                self.enterOuterAlt(localctx, 3)
                self.state = 336
                self.match(BmcQueryParser.EVENT)
                self.state = 337
                self.match(BmcQueryParser.LPAREN)
                self.state = 338
                self.string_literal()
                self.state = 339
                self.match(BmcQueryParser.COMMA)
                self.state = 340
                self.event_cycle_selector()
                self.state = 341
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.CASE]:
                self.enterOuterAlt(localctx, 4)
                self.state = 343
                self.match(BmcQueryParser.CASE)
                self.state = 344
                self.match(BmcQueryParser.LPAREN)
                self.state = 345
                self.string_literal()
                self.state = 348
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if _la == BmcQueryParser.COMMA:
                    self.state = 346
                    self.match(BmcQueryParser.COMMA)
                    self.state = 347
                    self.frame_selector()

                self.state = 350
                self.match(BmcQueryParser.RPAREN)
                pass
            elif token in [BmcQueryParser.CALLED]:
                self.enterOuterAlt(localctx, 5)
                self.state = 352
                self.match(BmcQueryParser.CALLED)
                self.state = 353
                self.match(BmcQueryParser.LPAREN)
                self.state = 355
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if (
                    ((_la) & ~0x3F) == 0
                    and (
                        (1 << _la)
                        & (
                            (1 << BmcQueryParser.STATE)
                            | (1 << BmcQueryParser.WHERE)
                            | (1 << BmcQueryParser.ACTION)
                            | (1 << BmcQueryParser.STEP)
                            | (1 << BmcQueryParser.STAGE)
                            | (1 << BmcQueryParser.ROLE)
                            | (1 << BmcQueryParser.ACTIVE_LEAF)
                            | (1 << BmcQueryParser.NAMED_REF)
                            | (1 << BmcQueryParser.RANGE_INT)
                            | (1 << BmcQueryParser.DOTDOT)
                        )
                    )
                    != 0
                ) or (
                    ((_la - 72) & ~0x3F) == 0
                    and (
                        (1 << (_la - 72))
                        & (
                            (1 << (BmcQueryParser.STAR - 72))
                            | (1 << (BmcQueryParser.PLUS - 72))
                            | (1 << (BmcQueryParser.MINUS - 72))
                            | (1 << (BmcQueryParser.INT - 72))
                            | (1 << (BmcQueryParser.STRING - 72))
                        )
                    )
                    != 0
                ):
                    self.state = 354
                    self.call_arguments()

                self.state = 357
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
            self.state = 360
            self.call_argument()
            self.state = 365
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la == BmcQueryParser.COMMA:
                self.state = 361
                self.match(BmcQueryParser.COMMA)
                self.state = 362
                self.call_argument()
                self.state = 367
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

        def ACTION(self):
            return self.getToken(BmcQueryParser.ACTION, 0)

        def ASSIGN(self):
            return self.getToken(BmcQueryParser.ASSIGN, 0)

        def STEP(self):
            return self.getToken(BmcQueryParser.STEP, 0)

        def STAGE(self):
            return self.getToken(BmcQueryParser.STAGE, 0)

        def ROLE(self):
            return self.getToken(BmcQueryParser.ROLE, 0)

        def STATE(self):
            return self.getToken(BmcQueryParser.STATE, 0)

        def ACTIVE_LEAF(self):
            return self.getToken(BmcQueryParser.ACTIVE_LEAF, 0)

        def NAMED_REF(self):
            return self.getToken(BmcQueryParser.NAMED_REF, 0)

        def NULL(self):
            return self.getToken(BmcQueryParser.NULL, 0)

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
            self.state = 396
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.STRING]:
                self.enterOuterAlt(localctx, 1)
                self.state = 368
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
                self.state = 369
                self.call_step_selector()
                pass
            elif token in [BmcQueryParser.ACTION]:
                self.enterOuterAlt(localctx, 3)
                self.state = 370
                self.match(BmcQueryParser.ACTION)
                self.state = 371
                self.match(BmcQueryParser.ASSIGN)
                self.state = 372
                self.string_literal()
                pass
            elif token in [BmcQueryParser.STEP]:
                self.enterOuterAlt(localctx, 4)
                self.state = 373
                self.match(BmcQueryParser.STEP)
                self.state = 374
                self.match(BmcQueryParser.ASSIGN)
                self.state = 375
                self.call_step_selector()
                pass
            elif token in [BmcQueryParser.STAGE]:
                self.enterOuterAlt(localctx, 5)
                self.state = 376
                self.match(BmcQueryParser.STAGE)
                self.state = 377
                self.match(BmcQueryParser.ASSIGN)
                self.state = 378
                self.string_literal()
                pass
            elif token in [BmcQueryParser.ROLE]:
                self.enterOuterAlt(localctx, 6)
                self.state = 379
                self.match(BmcQueryParser.ROLE)
                self.state = 380
                self.match(BmcQueryParser.ASSIGN)
                self.state = 381
                self.string_literal()
                pass
            elif token in [BmcQueryParser.STATE]:
                self.enterOuterAlt(localctx, 7)
                self.state = 382
                self.match(BmcQueryParser.STATE)
                self.state = 383
                self.match(BmcQueryParser.ASSIGN)
                self.state = 384
                self.string_literal()
                pass
            elif token in [BmcQueryParser.ACTIVE_LEAF]:
                self.enterOuterAlt(localctx, 8)
                self.state = 385
                self.match(BmcQueryParser.ACTIVE_LEAF)
                self.state = 386
                self.match(BmcQueryParser.ASSIGN)
                self.state = 387
                self.string_literal()
                pass
            elif token in [BmcQueryParser.NAMED_REF]:
                self.enterOuterAlt(localctx, 9)
                self.state = 388
                self.match(BmcQueryParser.NAMED_REF)
                self.state = 389
                self.match(BmcQueryParser.ASSIGN)
                self.state = 392
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [BmcQueryParser.STRING]:
                    self.state = 390
                    self.string_literal()
                    pass
                elif token in [BmcQueryParser.NULL]:
                    self.state = 391
                    self.match(BmcQueryParser.NULL)
                    pass
                else:
                    raise NoViableAltException(self)

                pass
            elif token in [BmcQueryParser.WHERE]:
                self.enterOuterAlt(localctx, 10)
                self.state = 394
                self.match(BmcQueryParser.WHERE)
                self.state = 395
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
        self.enterRule(localctx, 52, self.RULE_call_step_selector)
        self._la = 0  # Token type
        try:
            self.state = 408
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input, 33, self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 398
                self.match(BmcQueryParser.STAR)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 399
                self.match(BmcQueryParser.RANGE_INT)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 400
                self.call_step_point()
                pass

            elif la_ == 4:
                self.enterOuterAlt(localctx, 4)
                self.state = 402
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if ((_la - 74) & ~0x3F) == 0 and (
                    (1 << (_la - 74))
                    & (
                        (1 << (BmcQueryParser.PLUS - 74))
                        | (1 << (BmcQueryParser.MINUS - 74))
                        | (1 << (BmcQueryParser.INT - 74))
                    )
                ) != 0:
                    self.state = 401
                    self.call_step_point()

                self.state = 404
                self.match(BmcQueryParser.DOTDOT)
                self.state = 406
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                if ((_la - 74) & ~0x3F) == 0 and (
                    (1 << (_la - 74))
                    & (
                        (1 << (BmcQueryParser.PLUS - 74))
                        | (1 << (BmcQueryParser.MINUS - 74))
                        | (1 << (BmcQueryParser.INT - 74))
                    )
                ) != 0:
                    self.state = 405
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
        self.enterRule(localctx, 54, self.RULE_call_step_point)
        try:
            self.state = 415
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [BmcQueryParser.INT]:
                self.enterOuterAlt(localctx, 1)
                self.state = 410
                self.integer_literal()
                pass
            elif token in [BmcQueryParser.PLUS]:
                self.enterOuterAlt(localctx, 2)
                self.state = 411
                self.match(BmcQueryParser.PLUS)
                self.state = 412
                self.integer_literal()
                pass
            elif token in [BmcQueryParser.MINUS]:
                self.enterOuterAlt(localctx, 3)
                self.state = 413
                self.match(BmcQueryParser.MINUS)
                self.state = 414
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
        self.enterRule(localctx, 56, self.RULE_num_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 417
            _la = self._input.LA(1)
            if not (
                ((_la - 82) & ~0x3F) == 0
                and (
                    (1 << (_la - 82))
                    & (
                        (1 << (BmcQueryParser.FLOAT - 82))
                        | (1 << (BmcQueryParser.HEX_INT - 82))
                        | (1 << (BmcQueryParser.INT - 82))
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
        self.enterRule(localctx, 58, self.RULE_bool_literal)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 419
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
        self.enterRule(localctx, 60, self.RULE_math_const)
        self._la = 0  # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 421
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
        self.enterRule(localctx, 62, self.RULE_string_literal)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 423
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
