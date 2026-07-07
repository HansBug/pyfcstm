# Generated from ./pyfcstm/bmc/grammar/BmcQueryLexer.g4 by ANTLR 4.9.3
from antlr4 import *
from io import StringIO
import sys

if sys.version_info[1] > 5:
    from typing import TextIO
else:
    from typing.io import TextIO


def serializedATN():
    with StringIO() as buf:
        buf.write("\3\u608b\ua72a\u8133\ub9ed\u417c\u3be7\u7786\u5964\2V")
        buf.write("\u0336\b\1\4\2\t\2\4\3\t\3\4\4\t\4\4\5\t\5\4\6\t\6\4\7")
        buf.write("\t\7\4\b\t\b\4\t\t\t\4\n\t\n\4\13\t\13\4\f\t\f\4\r\t\r")
        buf.write("\4\16\t\16\4\17\t\17\4\20\t\20\4\21\t\21\4\22\t\22\4\23")
        buf.write("\t\23\4\24\t\24\4\25\t\25\4\26\t\26\4\27\t\27\4\30\t\30")
        buf.write("\4\31\t\31\4\32\t\32\4\33\t\33\4\34\t\34\4\35\t\35\4\36")
        buf.write('\t\36\4\37\t\37\4 \t \4!\t!\4"\t"\4#\t#\4$\t$\4%\t%')
        buf.write("\4&\t&\4'\t'\4(\t(\4)\t)\4*\t*\4+\t+\4,\t,\4-\t-\4.")
        buf.write("\t.\4/\t/\4\60\t\60\4\61\t\61\4\62\t\62\4\63\t\63\4\64")
        buf.write("\t\64\4\65\t\65\4\66\t\66\4\67\t\67\48\t8\49\t9\4:\t:")
        buf.write("\4;\t;\4<\t<\4=\t=\4>\t>\4?\t?\4@\t@\4A\tA\4B\tB\4C\t")
        buf.write("C\4D\tD\4E\tE\4F\tF\4G\tG\4H\tH\4I\tI\4J\tJ\4K\tK\4L\t")
        buf.write("L\4M\tM\4N\tN\4O\tO\4P\tP\4Q\tQ\4R\tR\4S\tS\4T\tT\4U\t")
        buf.write("U\4V\tV\4W\tW\3\2\3\2\3\2\3\2\3\2\3\3\3\3\3\3\3\3\3\3")
        buf.write("\3\4\3\4\3\4\3\4\3\4\3\4\3\4\3\4\3\4\3\4\3\4\3\5\3\5\3")
        buf.write("\5\3\5\3\5\3\5\3\6\3\6\3\6\3\6\3\6\3\6\3\7\3\7\3\7\3\7")
        buf.write("\3\7\3\7\3\b\3\b\3\b\3\b\3\b\3\b\3\b\3\t\3\t\3\t\3\t\3")
        buf.write("\t\3\t\3\t\3\n\3\n\3\n\3\13\3\13\3\13\3\13\3\13\3\13\3")
        buf.write("\f\3\f\3\f\3\f\3\f\3\f\3\f\3\r\3\r\3\r\3\r\3\r\3\r\3\r")
        buf.write("\3\r\3\r\3\r\3\r\3\r\3\16\3\16\3\16\3\16\3\17\3\17\3\17")
        buf.write("\3\17\3\17\3\17\3\17\3\17\3\17\3\17\3\17\3\17\3\20\3\20")
        buf.write("\3\20\3\20\3\20\3\20\3\21\3\21\3\21\3\21\3\21\3\21\3\22")
        buf.write("\3\22\3\22\3\22\3\22\3\22\3\22\3\23\3\23\3\23\3\23\3\23")
        buf.write("\3\23\3\23\3\23\3\23\3\23\3\24\3\24\3\24\3\24\3\24\3\24")
        buf.write("\3\24\3\24\3\24\3\24\3\24\3\25\3\25\3\25\3\25\3\25\3\25")
        buf.write("\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\25\3\26\3\26\3\26")
        buf.write("\3\26\3\26\3\26\3\26\3\26\3\26\3\27\3\27\3\27\3\27\3\27")
        buf.write("\3\27\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\30\3\31\3\31")
        buf.write("\3\31\3\31\3\31\3\31\3\31\3\32\3\32\3\32\3\32\3\33\3\33")
        buf.write("\3\33\3\33\3\33\3\33\3\34\3\34\3\34\3\34\3\34\3\34\3\34")
        buf.write("\3\35\3\35\3\35\3\35\3\35\3\36\3\36\3\36\3\36\3\36\3\36")
        buf.write("\3\36\3\37\3\37\3\37\3\37\3\37\3\37\3\37\3\37\3 \3 \3")
        buf.write(' \3!\3!\3"\3"\3"\3"\3#\3#\3#\3#\3$\3$\3$\3%\3%\3%')
        buf.write("\3%\3&\3&\3&\3&\3&\3&\3&\3&\3'\3'\3'\3'\3(\3(\3(\3")
        buf.write("(\3)\3)\3)\3*\3*\3*\3+\3+\3+\3,\3,\3,\3-\3-\3-\3.\3.\3")
        buf.write(".\3/\3/\3/\3\60\3\60\3\60\3\61\3\61\3\61\3\62\3\62\3\62")
        buf.write("\3\63\3\63\3\63\3\64\6\64\u01d0\n\64\r\64\16\64\u01d1")
        buf.write("\3\64\3\64\3\64\3\64\7\64\u01d8\n\64\f\64\16\64\u01db")
        buf.write("\13\64\3\64\6\64\u01de\n\64\r\64\16\64\u01df\3\65\3\65")
        buf.write("\3\65\3\66\3\66\3\67\3\67\38\38\39\39\3:\3:\3;\3;\3<\3")
        buf.write("<\3=\3=\3>\3>\3?\3?\3@\3@\3A\3A\3B\3B\3C\3C\3D\3D\3E\3")
        buf.write("E\3F\3F\3G\3G\3H\3H\3I\3I\3J\6J\u020e\nJ\rJ\16J\u020f")
        buf.write("\3J\3J\7J\u0214\nJ\fJ\16J\u0217\13J\3J\3J\5J\u021b\nJ")
        buf.write("\3J\6J\u021e\nJ\rJ\16J\u021f\5J\u0222\nJ\3J\3J\6J\u0226")
        buf.write("\nJ\rJ\16J\u0227\3J\3J\5J\u022c\nJ\3J\6J\u022f\nJ\rJ\16")
        buf.write("J\u0230\5J\u0233\nJ\3J\6J\u0236\nJ\rJ\16J\u0237\3J\3J")
        buf.write("\5J\u023c\nJ\3J\6J\u023f\nJ\rJ\16J\u0240\5J\u0243\nJ\3")
        buf.write("K\3K\3K\3K\6K\u0249\nK\rK\16K\u024a\3L\6L\u024e\nL\rL")
        buf.write("\16L\u024f\3M\3M\3M\3M\3M\3M\3M\3M\3M\3M\3M\3M\5M\u025e")
        buf.write("\nM\3N\3N\3N\3N\3N\3N\3N\3N\3N\3N\3N\3N\3N\3N\3N\5N\u026f")
        buf.write("\nN\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3")
        buf.write("O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3")
        buf.write("O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3")
        buf.write("O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3")
        buf.write("O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3")
        buf.write("O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\3O\5O\u02d7\nO\3")
        buf.write("P\3P\7P\u02db\nP\fP\16P\u02de\13P\3Q\3Q\3Q\7Q\u02e3\n")
        buf.write("Q\fQ\16Q\u02e6\13Q\3Q\3Q\3Q\3Q\7Q\u02ec\nQ\fQ\16Q\u02ef")
        buf.write("\13Q\3Q\5Q\u02f2\nQ\3R\3R\3R\3R\7R\u02f8\nR\fR\16R\u02fb")
        buf.write("\13R\3R\3R\3R\3R\3R\3S\3S\3S\3S\7S\u0306\nS\fS\16S\u0309")
        buf.write("\13S\3S\3S\3T\3T\7T\u030f\nT\fT\16T\u0312\13T\3T\3T\3")
        buf.write("U\6U\u0317\nU\rU\16U\u0318\3U\3U\3V\3V\3V\3V\5V\u0321")
        buf.write("\nV\3V\5V\u0324\nV\3V\3V\3V\3V\3V\3V\3V\3V\3V\3V\3V\3")
        buf.write("V\3V\5V\u0333\nV\3W\3W\3\u02f9\2X\3\3\5\4\7\5\t\6\13\7")
        buf.write("\r\b\17\t\21\n\23\13\25\f\27\r\31\16\33\17\35\20\37\21")
        buf.write("!\22#\23%\24'\25)\26+\27-\30/\31\61\32\63\33\65\34\67")
        buf.write("\359\36;\37= ?!A\"C#E$G%I&K'M(O)Q*S+U,W-Y.[/]\60_\61")
        buf.write("a\62c\63e\64g\65i\66k\67m8o9q:s;u<w=y>{?}@\177A\u0081")
        buf.write("B\u0083C\u0085D\u0087E\u0089F\u008bG\u008dH\u008fI\u0091")
        buf.write("J\u0093K\u0095L\u0097M\u0099N\u009bO\u009dP\u009fQ\u00a1")
        buf.write("R\u00a3S\u00a5T\u00a7U\u00a9V\u00ab\2\u00ad\2\3\2\20\3")
        buf.write('\2\62;\4\2\13\13""\4\2GGgg\4\2--//\5\2C\\aac|\6\2\62')
        buf.write(";C\\aac|\6\2\f\f\17\17$$^^\6\2\f\f\17\17))^^\4\2\f\f\17")
        buf.write('\17\5\2\13\f\17\17""\n\2$$))^^ddhhppttvv\3\2\62\65\3')
        buf.write("\2\629\5\2\62;CHch\2\u0371\2\3\3\2\2\2\2\5\3\2\2\2\2\7")
        buf.write("\3\2\2\2\2\t\3\2\2\2\2\13\3\2\2\2\2\r\3\2\2\2\2\17\3\2")
        buf.write("\2\2\2\21\3\2\2\2\2\23\3\2\2\2\2\25\3\2\2\2\2\27\3\2\2")
        buf.write("\2\2\31\3\2\2\2\2\33\3\2\2\2\2\35\3\2\2\2\2\37\3\2\2\2")
        buf.write("\2!\3\2\2\2\2#\3\2\2\2\2%\3\2\2\2\2'\3\2\2\2\2)\3\2\2")
        buf.write("\2\2+\3\2\2\2\2-\3\2\2\2\2/\3\2\2\2\2\61\3\2\2\2\2\63")
        buf.write("\3\2\2\2\2\65\3\2\2\2\2\67\3\2\2\2\29\3\2\2\2\2;\3\2\2")
        buf.write("\2\2=\3\2\2\2\2?\3\2\2\2\2A\3\2\2\2\2C\3\2\2\2\2E\3\2")
        buf.write("\2\2\2G\3\2\2\2\2I\3\2\2\2\2K\3\2\2\2\2M\3\2\2\2\2O\3")
        buf.write("\2\2\2\2Q\3\2\2\2\2S\3\2\2\2\2U\3\2\2\2\2W\3\2\2\2\2Y")
        buf.write("\3\2\2\2\2[\3\2\2\2\2]\3\2\2\2\2_\3\2\2\2\2a\3\2\2\2\2")
        buf.write("c\3\2\2\2\2e\3\2\2\2\2g\3\2\2\2\2i\3\2\2\2\2k\3\2\2\2")
        buf.write("\2m\3\2\2\2\2o\3\2\2\2\2q\3\2\2\2\2s\3\2\2\2\2u\3\2\2")
        buf.write("\2\2w\3\2\2\2\2y\3\2\2\2\2{\3\2\2\2\2}\3\2\2\2\2\177\3")
        buf.write("\2\2\2\2\u0081\3\2\2\2\2\u0083\3\2\2\2\2\u0085\3\2\2\2")
        buf.write("\2\u0087\3\2\2\2\2\u0089\3\2\2\2\2\u008b\3\2\2\2\2\u008d")
        buf.write("\3\2\2\2\2\u008f\3\2\2\2\2\u0091\3\2\2\2\2\u0093\3\2\2")
        buf.write("\2\2\u0095\3\2\2\2\2\u0097\3\2\2\2\2\u0099\3\2\2\2\2\u009b")
        buf.write("\3\2\2\2\2\u009d\3\2\2\2\2\u009f\3\2\2\2\2\u00a1\3\2\2")
        buf.write("\2\2\u00a3\3\2\2\2\2\u00a5\3\2\2\2\2\u00a7\3\2\2\2\2\u00a9")
        buf.write("\3\2\2\2\3\u00af\3\2\2\2\5\u00b4\3\2\2\2\7\u00b9\3\2\2")
        buf.write("\2\t\u00c4\3\2\2\2\13\u00ca\3\2\2\2\r\u00d0\3\2\2\2\17")
        buf.write("\u00d6\3\2\2\2\21\u00dd\3\2\2\2\23\u00e4\3\2\2\2\25\u00e7")
        buf.write("\3\2\2\2\27\u00ed\3\2\2\2\31\u00f4\3\2\2\2\33\u0100\3")
        buf.write("\2\2\2\35\u0104\3\2\2\2\37\u0110\3\2\2\2!\u0116\3\2\2")
        buf.write("\2#\u011c\3\2\2\2%\u0123\3\2\2\2'\u012d\3\2\2\2)\u0138")
        buf.write("\3\2\2\2+\u0146\3\2\2\2-\u014f\3\2\2\2/\u0155\3\2\2\2")
        buf.write("\61\u015d\3\2\2\2\63\u0164\3\2\2\2\65\u0168\3\2\2\2\67")
        buf.write("\u016e\3\2\2\29\u0175\3\2\2\2;\u017a\3\2\2\2=\u0181\3")
        buf.write("\2\2\2?\u0189\3\2\2\2A\u018c\3\2\2\2C\u018e\3\2\2\2E\u0192")
        buf.write("\3\2\2\2G\u0196\3\2\2\2I\u0199\3\2\2\2K\u019d\3\2\2\2")
        buf.write("M\u01a5\3\2\2\2O\u01a9\3\2\2\2Q\u01ad\3\2\2\2S\u01b0\3")
        buf.write("\2\2\2U\u01b3\3\2\2\2W\u01b6\3\2\2\2Y\u01b9\3\2\2\2[\u01bc")
        buf.write("\3\2\2\2]\u01bf\3\2\2\2_\u01c2\3\2\2\2a\u01c5\3\2\2\2")
        buf.write("c\u01c8\3\2\2\2e\u01cb\3\2\2\2g\u01cf\3\2\2\2i\u01e1\3")
        buf.write("\2\2\2k\u01e4\3\2\2\2m\u01e6\3\2\2\2o\u01e8\3\2\2\2q\u01ea")
        buf.write("\3\2\2\2s\u01ec\3\2\2\2u\u01ee\3\2\2\2w\u01f0\3\2\2\2")
        buf.write("y\u01f2\3\2\2\2{\u01f4\3\2\2\2}\u01f6\3\2\2\2\177\u01f8")
        buf.write("\3\2\2\2\u0081\u01fa\3\2\2\2\u0083\u01fc\3\2\2\2\u0085")
        buf.write("\u01fe\3\2\2\2\u0087\u0200\3\2\2\2\u0089\u0202\3\2\2\2")
        buf.write("\u008b\u0204\3\2\2\2\u008d\u0206\3\2\2\2\u008f\u0208\3")
        buf.write("\2\2\2\u0091\u020a\3\2\2\2\u0093\u0242\3\2\2\2\u0095\u0244")
        buf.write("\3\2\2\2\u0097\u024d\3\2\2\2\u0099\u025d\3\2\2\2\u009b")
        buf.write("\u026e\3\2\2\2\u009d\u02d6\3\2\2\2\u009f\u02d8\3\2\2\2")
        buf.write("\u00a1\u02f1\3\2\2\2\u00a3\u02f3\3\2\2\2\u00a5\u0301\3")
        buf.write("\2\2\2\u00a7\u030c\3\2\2\2\u00a9\u0316\3\2\2\2\u00ab\u0332")
        buf.write("\3\2\2\2\u00ad\u0334\3\2\2\2\u00af\u00b0\7k\2\2\u00b0")
        buf.write("\u00b1\7p\2\2\u00b1\u00b2\7k\2\2\u00b2\u00b3\7v\2\2\u00b3")
        buf.write("\4\3\2\2\2\u00b4\u00b5\7e\2\2\u00b5\u00b6\7q\2\2\u00b6")
        buf.write("\u00b7\7n\2\2\u00b7\u00b8\7f\2\2\u00b8\6\3\2\2\2\u00b9")
        buf.write("\u00ba\7v\2\2\u00ba\u00bb\7g\2\2\u00bb\u00bc\7t\2\2\u00bc")
        buf.write("\u00bd\7o\2\2\u00bd\u00be\7k\2\2\u00be\u00bf\7p\2\2\u00bf")
        buf.write("\u00c0\7c\2\2\u00c0\u00c1\7v\2\2\u00c1\u00c2\7g\2\2\u00c2")
        buf.write("\u00c3\7f\2\2\u00c3\b\3\2\2\2\u00c4\u00c5\7u\2\2\u00c5")
        buf.write("\u00c6\7v\2\2\u00c6\u00c7\7c\2\2\u00c7\u00c8\7v\2\2\u00c8")
        buf.write("\u00c9\7g\2\2\u00c9\n\3\2\2\2\u00ca\u00cb\7y\2\2\u00cb")
        buf.write("\u00cc\7j\2\2\u00cc\u00cd\7g\2\2\u00cd\u00ce\7t\2\2\u00ce")
        buf.write("\u00cf\7g\2\2\u00cf\f\3\2\2\2\u00d0\u00d1\7j\2\2\u00d1")
        buf.write("\u00d2\7c\2\2\u00d2\u00d3\7x\2\2\u00d3\u00d4\7q\2\2\u00d4")
        buf.write("\u00d5\7e\2\2\u00d5\16\3\2\2\2\u00d6\u00d7\7c\2\2\u00d7")
        buf.write("\u00d8\7u\2\2\u00d8\u00d9\7u\2\2\u00d9\u00da\7w\2\2\u00da")
        buf.write("\u00db\7o\2\2\u00db\u00dc\7g\2\2\u00dc\20\3\2\2\2\u00dd")
        buf.write("\u00de\7c\2\2\u00de\u00df\7n\2\2\u00df\u00e0\7y\2\2\u00e0")
        buf.write("\u00e1\7c\2\2\u00e1\u00e2\7{\2\2\u00e2\u00e3\7u\2\2\u00e3")
        buf.write("\22\3\2\2\2\u00e4\u00e5\7c\2\2\u00e5\u00e6\7v\2\2\u00e6")
        buf.write("\24\3\2\2\2\u00e7\u00e8\7g\2\2\u00e8\u00e9\7x\2\2\u00e9")
        buf.write("\u00ea\7g\2\2\u00ea\u00eb\7p\2\2\u00eb\u00ec\7v\2\2\u00ec")
        buf.write("\26\3\2\2\2\u00ed\u00ee\7g\2\2\u00ee\u00ef\7x\2\2\u00ef")
        buf.write("\u00f0\7g\2\2\u00f0\u00f1\7p\2\2\u00f1\u00f2\7v\2\2\u00f2")
        buf.write("\u00f3\7u\2\2\u00f3\30\3\2\2\2\u00f4\u00f5\7e\2\2\u00f5")
        buf.write("\u00f6\7c\2\2\u00f6\u00f7\7t\2\2\u00f7\u00f8\7f\2\2\u00f8")
        buf.write("\u00f9\7k\2\2\u00f9\u00fa\7p\2\2\u00fa\u00fb\7c\2\2\u00fb")
        buf.write("\u00fc\7n\2\2\u00fc\u00fd\7k\2\2\u00fd\u00fe\7v\2\2\u00fe")
        buf.write("\u00ff\7{\2\2\u00ff\32\3\2\2\2\u0100\u0101\7c\2\2\u0101")
        buf.write("\u0102\7p\2\2\u0102\u0103\7{\2\2\u0103\34\3\2\2\2\u0104")
        buf.write("\u0105\7c\2\2\u0105\u0106\7v\2\2\u0106\u0107\7a\2\2\u0107")
        buf.write("\u0108\7o\2\2\u0108\u0109\7q\2\2\u0109\u010a\7u\2\2\u010a")
        buf.write("\u010b\7v\2\2\u010b\u010c\7a\2\2\u010c\u010d\7q\2\2\u010d")
        buf.write("\u010e\7p\2\2\u010e\u010f\7g\2\2\u010f\36\3\2\2\2\u0110")
        buf.write("\u0111\7e\2\2\u0111\u0112\7j\2\2\u0112\u0113\7g\2\2\u0113")
        buf.write("\u0114\7e\2\2\u0114\u0115\7m\2\2\u0115 \3\2\2\2\u0116")
        buf.write("\u0117\7t\2\2\u0117\u0118\7g\2\2\u0118\u0119\7c\2\2\u0119")
        buf.write('\u011a\7e\2\2\u011a\u011b\7j\2\2\u011b"\3\2\2\2\u011c')
        buf.write("\u011d\7h\2\2\u011d\u011e\7q\2\2\u011e\u011f\7t\2\2\u011f")
        buf.write("\u0120\7d\2\2\u0120\u0121\7k\2\2\u0121\u0122\7f\2\2\u0122")
        buf.write("$\3\2\2\2\u0123\u0124\7k\2\2\u0124\u0125\7p\2\2\u0125")
        buf.write("\u0126\7x\2\2\u0126\u0127\7c\2\2\u0127\u0128\7t\2\2\u0128")
        buf.write("\u0129\7k\2\2\u0129\u012a\7c\2\2\u012a\u012b\7p\2\2\u012b")
        buf.write("\u012c\7v\2\2\u012c&\3\2\2\2\u012d\u012e\7o\2\2\u012e")
        buf.write("\u012f\7w\2\2\u012f\u0130\7u\2\2\u0130\u0131\7v\2\2\u0131")
        buf.write("\u0132\7a\2\2\u0132\u0133\7t\2\2\u0133\u0134\7g\2\2\u0134")
        buf.write("\u0135\7c\2\2\u0135\u0136\7e\2\2\u0136\u0137\7j\2\2\u0137")
        buf.write("(\3\2\2\2\u0138\u0139\7g\2\2\u0139\u013a\7z\2\2\u013a")
        buf.write("\u013b\7k\2\2\u013b\u013c\7u\2\2\u013c\u013d\7v\2\2\u013d")
        buf.write("\u013e\7u\2\2\u013e\u013f\7a\2\2\u013f\u0140\7c\2\2\u0140")
        buf.write("\u0141\7n\2\2\u0141\u0142\7y\2\2\u0142\u0143\7c\2\2\u0143")
        buf.write("\u0144\7{\2\2\u0144\u0145\7u\2\2\u0145*\3\2\2\2\u0146")
        buf.write("\u0147\7t\2\2\u0147\u0148\7g\2\2\u0148\u0149\7u\2\2\u0149")
        buf.write("\u014a\7r\2\2\u014a\u014b\7q\2\2\u014b\u014c\7p\2\2\u014c")
        buf.write("\u014d\7u\2\2\u014d\u014e\7g\2\2\u014e,\3\2\2\2\u014f")
        buf.write("\u0150\7e\2\2\u0150\u0151\7q\2\2\u0151\u0152\7x\2\2\u0152")
        buf.write("\u0153\7g\2\2\u0153\u0154\7t\2\2\u0154.\3\2\2\2\u0155")
        buf.write("\u0156\7v\2\2\u0156\u0157\7t\2\2\u0157\u0158\7k\2\2\u0158")
        buf.write("\u0159\7i\2\2\u0159\u015a\7i\2\2\u015a\u015b\7g\2\2\u015b")
        buf.write("\u015c\7t\2\2\u015c\60\3\2\2\2\u015d\u015e\7y\2\2\u015e")
        buf.write("\u015f\7k\2\2\u015f\u0160\7v\2\2\u0160\u0161\7j\2\2\u0161")
        buf.write("\u0162\7k\2\2\u0162\u0163\7p\2\2\u0163\62\3\2\2\2\u0164")
        buf.write("\u0165\7x\2\2\u0165\u0166\7c\2\2\u0166\u0167\7t\2\2\u0167")
        buf.write("\64\3\2\2\2\u0168\u0169\7e\2\2\u0169\u016a\7{\2\2\u016a")
        buf.write("\u016b\7e\2\2\u016b\u016c\7n\2\2\u016c\u016d\7g\2\2\u016d")
        buf.write("\66\3\2\2\2\u016e\u016f\7c\2\2\u016f\u0170\7e\2\2\u0170")
        buf.write("\u0171\7v\2\2\u0171\u0172\7k\2\2\u0172\u0173\7x\2\2\u0173")
        buf.write("\u0174\7g\2\2\u01748\3\2\2\2\u0175\u0176\7e\2\2\u0176")
        buf.write("\u0177\7c\2\2\u0177\u0178\7u\2\2\u0178\u0179\7g\2\2\u0179")
        buf.write(":\3\2\2\2\u017a\u017b\7e\2\2\u017b\u017c\7c\2\2\u017c")
        buf.write("\u017d\7n\2\2\u017d\u017e\7n\2\2\u017e\u017f\7g\2\2\u017f")
        buf.write("\u0180\7f\2\2\u0180<\3\2\2\2\u0181\u0182\7e\2\2\u0182")
        buf.write("\u0183\7w\2\2\u0183\u0184\7t\2\2\u0184\u0185\7t\2\2\u0185")
        buf.write("\u0186\7g\2\2\u0186\u0187\7p\2\2\u0187\u0188\7v\2\2\u0188")
        buf.write(">\3\2\2\2\u0189\u018a\7r\2\2\u018a\u018b\7k\2\2\u018b")
        buf.write("@\3\2\2\2\u018c\u018d\7G\2\2\u018dB\3\2\2\2\u018e\u018f")
        buf.write("\7v\2\2\u018f\u0190\7c\2\2\u0190\u0191\7w\2\2\u0191D\3")
        buf.write("\2\2\2\u0192\u0193\7c\2\2\u0193\u0194\7p\2\2\u0194\u0195")
        buf.write("\7f\2\2\u0195F\3\2\2\2\u0196\u0197\7q\2\2\u0197\u0198")
        buf.write("\7t\2\2\u0198H\3\2\2\2\u0199\u019a\7p\2\2\u019a\u019b")
        buf.write("\7q\2\2\u019b\u019c\7v\2\2\u019cJ\3\2\2\2\u019d\u019e")
        buf.write("\7k\2\2\u019e\u019f\7o\2\2\u019f\u01a0\7r\2\2\u01a0\u01a1")
        buf.write("\7n\2\2\u01a1\u01a2\7k\2\2\u01a2\u01a3\7g\2\2\u01a3\u01a4")
        buf.write("\7u\2\2\u01a4L\3\2\2\2\u01a5\u01a6\7k\2\2\u01a6\u01a7")
        buf.write("\7h\2\2\u01a7\u01a8\7h\2\2\u01a8N\3\2\2\2\u01a9\u01aa")
        buf.write("\7z\2\2\u01aa\u01ab\7q\2\2\u01ab\u01ac\7t\2\2\u01acP\3")
        buf.write("\2\2\2\u01ad\u01ae\7,\2\2\u01ae\u01af\7,\2\2\u01afR\3")
        buf.write("\2\2\2\u01b0\u01b1\7@\2\2\u01b1\u01b2\7@\2\2\u01b2T\3")
        buf.write("\2\2\2\u01b3\u01b4\7>\2\2\u01b4\u01b5\7>\2\2\u01b5V\3")
        buf.write("\2\2\2\u01b6\u01b7\7>\2\2\u01b7\u01b8\7?\2\2\u01b8X\3")
        buf.write("\2\2\2\u01b9\u01ba\7@\2\2\u01ba\u01bb\7?\2\2\u01bbZ\3")
        buf.write("\2\2\2\u01bc\u01bd\7?\2\2\u01bd\u01be\7?\2\2\u01be\\\3")
        buf.write("\2\2\2\u01bf\u01c0\7#\2\2\u01c0\u01c1\7?\2\2\u01c1^\3")
        buf.write("\2\2\2\u01c2\u01c3\7(\2\2\u01c3\u01c4\7(\2\2\u01c4`\3")
        buf.write("\2\2\2\u01c5\u01c6\7~\2\2\u01c6\u01c7\7~\2\2\u01c7b\3")
        buf.write("\2\2\2\u01c8\u01c9\7?\2\2\u01c9\u01ca\7@\2\2\u01cad\3")
        buf.write("\2\2\2\u01cb\u01cc\7/\2\2\u01cc\u01cd\7@\2\2\u01cdf\3")
        buf.write("\2\2\2\u01ce\u01d0\t\2\2\2\u01cf\u01ce\3\2\2\2\u01d0\u01d1")
        buf.write("\3\2\2\2\u01d1\u01cf\3\2\2\2\u01d1\u01d2\3\2\2\2\u01d2")
        buf.write("\u01d3\3\2\2\2\u01d3\u01d4\7\60\2\2\u01d4\u01d5\7\60\2")
        buf.write("\2\u01d5\u01d9\3\2\2\2\u01d6\u01d8\t\3\2\2\u01d7\u01d6")
        buf.write("\3\2\2\2\u01d8\u01db\3\2\2\2\u01d9\u01d7\3\2\2\2\u01d9")
        buf.write("\u01da\3\2\2\2\u01da\u01dd\3\2\2\2\u01db\u01d9\3\2\2\2")
        buf.write("\u01dc\u01de\t\2\2\2\u01dd\u01dc\3\2\2\2\u01de\u01df\3")
        buf.write("\2\2\2\u01df\u01dd\3\2\2\2\u01df\u01e0\3\2\2\2\u01e0h")
        buf.write("\3\2\2\2\u01e1\u01e2\7\60\2\2\u01e2\u01e3\7\60\2\2\u01e3")
        buf.write("j\3\2\2\2\u01e4\u01e5\7=\2\2\u01e5l\3\2\2\2\u01e6\u01e7")
        buf.write("\7.\2\2\u01e7n\3\2\2\2\u01e8\u01e9\7}\2\2\u01e9p\3\2\2")
        buf.write("\2\u01ea\u01eb\7\177\2\2\u01ebr\3\2\2\2\u01ec\u01ed\7")
        buf.write("*\2\2\u01edt\3\2\2\2\u01ee\u01ef\7+\2\2\u01efv\3\2\2\2")
        buf.write("\u01f0\u01f1\7A\2\2\u01f1x\3\2\2\2\u01f2\u01f3\7<\2\2")
        buf.write("\u01f3z\3\2\2\2\u01f4\u01f5\7\60\2\2\u01f5|\3\2\2\2\u01f6")
        buf.write("\u01f7\7\61\2\2\u01f7~\3\2\2\2\u01f8\u01f9\7,\2\2\u01f9")
        buf.write("\u0080\3\2\2\2\u01fa\u01fb\7#\2\2\u01fb\u0082\3\2\2\2")
        buf.write("\u01fc\u01fd\7-\2\2\u01fd\u0084\3\2\2\2\u01fe\u01ff\7")
        buf.write("/\2\2\u01ff\u0086\3\2\2\2\u0200\u0201\7'\2\2\u0201\u0088")
        buf.write("\3\2\2\2\u0202\u0203\7(\2\2\u0203\u008a\3\2\2\2\u0204")
        buf.write("\u0205\7`\2\2\u0205\u008c\3\2\2\2\u0206\u0207\7~\2\2\u0207")
        buf.write("\u008e\3\2\2\2\u0208\u0209\7>\2\2\u0209\u0090\3\2\2\2")
        buf.write("\u020a\u020b\7@\2\2\u020b\u0092\3\2\2\2\u020c\u020e\t")
        buf.write("\2\2\2\u020d\u020c\3\2\2\2\u020e\u020f\3\2\2\2\u020f\u020d")
        buf.write("\3\2\2\2\u020f\u0210\3\2\2\2\u0210\u0211\3\2\2\2\u0211")
        buf.write("\u0215\7\60\2\2\u0212\u0214\t\2\2\2\u0213\u0212\3\2\2")
        buf.write("\2\u0214\u0217\3\2\2\2\u0215\u0213\3\2\2\2\u0215\u0216")
        buf.write("\3\2\2\2\u0216\u0221\3\2\2\2\u0217\u0215\3\2\2\2\u0218")
        buf.write("\u021a\t\4\2\2\u0219\u021b\t\5\2\2\u021a\u0219\3\2\2\2")
        buf.write("\u021a\u021b\3\2\2\2\u021b\u021d\3\2\2\2\u021c\u021e\t")
        buf.write("\2\2\2\u021d\u021c\3\2\2\2\u021e\u021f\3\2\2\2\u021f\u021d")
        buf.write("\3\2\2\2\u021f\u0220\3\2\2\2\u0220\u0222\3\2\2\2\u0221")
        buf.write("\u0218\3\2\2\2\u0221\u0222\3\2\2\2\u0222\u0243\3\2\2\2")
        buf.write("\u0223\u0225\7\60\2\2\u0224\u0226\t\2\2\2\u0225\u0224")
        buf.write("\3\2\2\2\u0226\u0227\3\2\2\2\u0227\u0225\3\2\2\2\u0227")
        buf.write("\u0228\3\2\2\2\u0228\u0232\3\2\2\2\u0229\u022b\t\4\2\2")
        buf.write("\u022a\u022c\t\5\2\2\u022b\u022a\3\2\2\2\u022b\u022c\3")
        buf.write("\2\2\2\u022c\u022e\3\2\2\2\u022d\u022f\t\2\2\2\u022e\u022d")
        buf.write("\3\2\2\2\u022f\u0230\3\2\2\2\u0230\u022e\3\2\2\2\u0230")
        buf.write("\u0231\3\2\2\2\u0231\u0233\3\2\2\2\u0232\u0229\3\2\2\2")
        buf.write("\u0232\u0233\3\2\2\2\u0233\u0243\3\2\2\2\u0234\u0236\t")
        buf.write("\2\2\2\u0235\u0234\3\2\2\2\u0236\u0237\3\2\2\2\u0237\u0235")
        buf.write("\3\2\2\2\u0237\u0238\3\2\2\2\u0238\u0239\3\2\2\2\u0239")
        buf.write("\u023b\t\4\2\2\u023a\u023c\t\5\2\2\u023b\u023a\3\2\2\2")
        buf.write("\u023b\u023c\3\2\2\2\u023c\u023e\3\2\2\2\u023d\u023f\t")
        buf.write("\2\2\2\u023e\u023d\3\2\2\2\u023f\u0240\3\2\2\2\u0240\u023e")
        buf.write("\3\2\2\2\u0240\u0241\3\2\2\2\u0241\u0243\3\2\2\2\u0242")
        buf.write("\u020d\3\2\2\2\u0242\u0223\3\2\2\2\u0242\u0235\3\2\2\2")
        buf.write("\u0243\u0094\3\2\2\2\u0244\u0245\7\62\2\2\u0245\u0246")
        buf.write("\7z\2\2\u0246\u0248\3\2\2\2\u0247\u0249\5\u00adW\2\u0248")
        buf.write("\u0247\3\2\2\2\u0249\u024a\3\2\2\2\u024a\u0248\3\2\2\2")
        buf.write("\u024a\u024b\3\2\2\2\u024b\u0096\3\2\2\2\u024c\u024e\t")
        buf.write("\2\2\2\u024d\u024c\3\2\2\2\u024e\u024f\3\2\2\2\u024f\u024d")
        buf.write("\3\2\2\2\u024f\u0250\3\2\2\2\u0250\u0098\3\2\2\2\u0251")
        buf.write("\u0252\7V\2\2\u0252\u0253\7t\2\2\u0253\u0254\7w\2\2\u0254")
        buf.write("\u025e\7g\2\2\u0255\u0256\7v\2\2\u0256\u0257\7t\2\2\u0257")
        buf.write("\u0258\7w\2\2\u0258\u025e\7g\2\2\u0259\u025a\7V\2\2\u025a")
        buf.write("\u025b\7T\2\2\u025b\u025c\7W\2\2\u025c\u025e\7G\2\2\u025d")
        buf.write("\u0251\3\2\2\2\u025d\u0255\3\2\2\2\u025d\u0259\3\2\2\2")
        buf.write("\u025e\u009a\3\2\2\2\u025f\u0260\7H\2\2\u0260\u0261\7")
        buf.write("c\2\2\u0261\u0262\7n\2\2\u0262\u0263\7u\2\2\u0263\u026f")
        buf.write("\7g\2\2\u0264\u0265\7h\2\2\u0265\u0266\7c\2\2\u0266\u0267")
        buf.write("\7n\2\2\u0267\u0268\7u\2\2\u0268\u026f\7g\2\2\u0269\u026a")
        buf.write("\7H\2\2\u026a\u026b\7C\2\2\u026b\u026c\7N\2\2\u026c\u026d")
        buf.write("\7U\2\2\u026d\u026f\7G\2\2\u026e\u025f\3\2\2\2\u026e\u0264")
        buf.write("\3\2\2\2\u026e\u0269\3\2\2\2\u026f\u009c\3\2\2\2\u0270")
        buf.write("\u0271\7u\2\2\u0271\u0272\7k\2\2\u0272\u02d7\7p\2\2\u0273")
        buf.write("\u0274\7e\2\2\u0274\u0275\7q\2\2\u0275\u02d7\7u\2\2\u0276")
        buf.write("\u0277\7v\2\2\u0277\u0278\7c\2\2\u0278\u02d7\7p\2\2\u0279")
        buf.write("\u027a\7c\2\2\u027a\u027b\7u\2\2\u027b\u027c\7k\2\2\u027c")
        buf.write("\u02d7\7p\2\2\u027d\u027e\7c\2\2\u027e\u027f\7e\2\2\u027f")
        buf.write("\u0280\7q\2\2\u0280\u02d7\7u\2\2\u0281\u0282\7c\2\2\u0282")
        buf.write("\u0283\7v\2\2\u0283\u0284\7c\2\2\u0284\u02d7\7p\2\2\u0285")
        buf.write("\u0286\7u\2\2\u0286\u0287\7k\2\2\u0287\u0288\7p\2\2\u0288")
        buf.write("\u02d7\7j\2\2\u0289\u028a\7e\2\2\u028a\u028b\7q\2\2\u028b")
        buf.write("\u028c\7u\2\2\u028c\u02d7\7j\2\2\u028d\u028e\7v\2\2\u028e")
        buf.write("\u028f\7c\2\2\u028f\u0290\7p\2\2\u0290\u02d7\7j\2\2\u0291")
        buf.write("\u0292\7c\2\2\u0292\u0293\7u\2\2\u0293\u0294\7k\2\2\u0294")
        buf.write("\u0295\7p\2\2\u0295\u02d7\7j\2\2\u0296\u0297\7c\2\2\u0297")
        buf.write("\u0298\7e\2\2\u0298\u0299\7q\2\2\u0299\u029a\7u\2\2\u029a")
        buf.write("\u02d7\7j\2\2\u029b\u029c\7c\2\2\u029c\u029d\7v\2\2\u029d")
        buf.write("\u029e\7c\2\2\u029e\u029f\7p\2\2\u029f\u02d7\7j\2\2\u02a0")
        buf.write("\u02a1\7u\2\2\u02a1\u02a2\7s\2\2\u02a2\u02a3\7t\2\2\u02a3")
        buf.write("\u02d7\7v\2\2\u02a4\u02a5\7e\2\2\u02a5\u02a6\7d\2\2\u02a6")
        buf.write("\u02a7\7t\2\2\u02a7\u02d7\7v\2\2\u02a8\u02a9\7g\2\2\u02a9")
        buf.write("\u02aa\7z\2\2\u02aa\u02d7\7r\2\2\u02ab\u02ac\7n\2\2\u02ac")
        buf.write("\u02ad\7q\2\2\u02ad\u02d7\7i\2\2\u02ae\u02af\7n\2\2\u02af")
        buf.write("\u02b0\7q\2\2\u02b0\u02b1\7i\2\2\u02b1\u02b2\7\63\2\2")
        buf.write("\u02b2\u02d7\7\62\2\2\u02b3\u02b4\7n\2\2\u02b4\u02b5\7")
        buf.write("q\2\2\u02b5\u02b6\7i\2\2\u02b6\u02d7\7\64\2\2\u02b7\u02b8")
        buf.write("\7n\2\2\u02b8\u02b9\7q\2\2\u02b9\u02ba\7i\2\2\u02ba\u02bb")
        buf.write("\7\63\2\2\u02bb\u02d7\7r\2\2\u02bc\u02bd\7c\2\2\u02bd")
        buf.write("\u02be\7d\2\2\u02be\u02d7\7u\2\2\u02bf\u02c0\7e\2\2\u02c0")
        buf.write("\u02c1\7g\2\2\u02c1\u02c2\7k\2\2\u02c2\u02d7\7n\2\2\u02c3")
        buf.write("\u02c4\7h\2\2\u02c4\u02c5\7n\2\2\u02c5\u02c6\7q\2\2\u02c6")
        buf.write("\u02c7\7q\2\2\u02c7\u02d7\7t\2\2\u02c8\u02c9\7t\2\2\u02c9")
        buf.write("\u02ca\7q\2\2\u02ca\u02cb\7w\2\2\u02cb\u02cc\7p\2\2\u02cc")
        buf.write("\u02d7\7f\2\2\u02cd\u02ce\7v\2\2\u02ce\u02cf\7t\2\2\u02cf")
        buf.write("\u02d0\7w\2\2\u02d0\u02d1\7p\2\2\u02d1\u02d7\7e\2\2\u02d2")
        buf.write("\u02d3\7u\2\2\u02d3\u02d4\7k\2\2\u02d4\u02d5\7i\2\2\u02d5")
        buf.write("\u02d7\7p\2\2\u02d6\u0270\3\2\2\2\u02d6\u0273\3\2\2\2")
        buf.write("\u02d6\u0276\3\2\2\2\u02d6\u0279\3\2\2\2\u02d6\u027d\3")
        buf.write("\2\2\2\u02d6\u0281\3\2\2\2\u02d6\u0285\3\2\2\2\u02d6\u0289")
        buf.write("\3\2\2\2\u02d6\u028d\3\2\2\2\u02d6\u0291\3\2\2\2\u02d6")
        buf.write("\u0296\3\2\2\2\u02d6\u029b\3\2\2\2\u02d6\u02a0\3\2\2\2")
        buf.write("\u02d6\u02a4\3\2\2\2\u02d6\u02a8\3\2\2\2\u02d6\u02ab\3")
        buf.write("\2\2\2\u02d6\u02ae\3\2\2\2\u02d6\u02b3\3\2\2\2\u02d6\u02b7")
        buf.write("\3\2\2\2\u02d6\u02bc\3\2\2\2\u02d6\u02bf\3\2\2\2\u02d6")
        buf.write("\u02c3\3\2\2\2\u02d6\u02c8\3\2\2\2\u02d6\u02cd\3\2\2\2")
        buf.write("\u02d6\u02d2\3\2\2\2\u02d7\u009e\3\2\2\2\u02d8\u02dc\t")
        buf.write("\6\2\2\u02d9\u02db\t\7\2\2\u02da\u02d9\3\2\2\2\u02db\u02de")
        buf.write("\3\2\2\2\u02dc\u02da\3\2\2\2\u02dc\u02dd\3\2\2\2\u02dd")
        buf.write("\u00a0\3\2\2\2\u02de\u02dc\3\2\2\2\u02df\u02e4\7$\2\2")
        buf.write("\u02e0\u02e3\n\b\2\2\u02e1\u02e3\5\u00abV\2\u02e2\u02e0")
        buf.write("\3\2\2\2\u02e2\u02e1\3\2\2\2\u02e3\u02e6\3\2\2\2\u02e4")
        buf.write("\u02e2\3\2\2\2\u02e4\u02e5\3\2\2\2\u02e5\u02e7\3\2\2\2")
        buf.write("\u02e6\u02e4\3\2\2\2\u02e7\u02f2\7$\2\2\u02e8\u02ed\7")
        buf.write(")\2\2\u02e9\u02ec\n\t\2\2\u02ea\u02ec\5\u00abV\2\u02eb")
        buf.write("\u02e9\3\2\2\2\u02eb\u02ea\3\2\2\2\u02ec\u02ef\3\2\2\2")
        buf.write("\u02ed\u02eb\3\2\2\2\u02ed\u02ee\3\2\2\2\u02ee\u02f0\3")
        buf.write("\2\2\2\u02ef\u02ed\3\2\2\2\u02f0\u02f2\7)\2\2\u02f1\u02df")
        buf.write("\3\2\2\2\u02f1\u02e8\3\2\2\2\u02f2\u00a2\3\2\2\2\u02f3")
        buf.write("\u02f4\7\61\2\2\u02f4\u02f5\7,\2\2\u02f5\u02f9\3\2\2\2")
        buf.write("\u02f6\u02f8\13\2\2\2\u02f7\u02f6\3\2\2\2\u02f8\u02fb")
        buf.write("\3\2\2\2\u02f9\u02fa\3\2\2\2\u02f9\u02f7\3\2\2\2\u02fa")
        buf.write("\u02fc\3\2\2\2\u02fb\u02f9\3\2\2\2\u02fc\u02fd\7,\2\2")
        buf.write("\u02fd\u02fe\7\61\2\2\u02fe\u02ff\3\2\2\2\u02ff\u0300")
        buf.write("\bR\2\2\u0300\u00a4\3\2\2\2\u0301\u0302\7\61\2\2\u0302")
        buf.write("\u0303\7\61\2\2\u0303\u0307\3\2\2\2\u0304\u0306\n\n\2")
        buf.write("\2\u0305\u0304\3\2\2\2\u0306\u0309\3\2\2\2\u0307\u0305")
        buf.write("\3\2\2\2\u0307\u0308\3\2\2\2\u0308\u030a\3\2\2\2\u0309")
        buf.write("\u0307\3\2\2\2\u030a\u030b\bS\2\2\u030b\u00a6\3\2\2\2")
        buf.write("\u030c\u0310\7%\2\2\u030d\u030f\n\n\2\2\u030e\u030d\3")
        buf.write("\2\2\2\u030f\u0312\3\2\2\2\u0310\u030e\3\2\2\2\u0310\u0311")
        buf.write("\3\2\2\2\u0311\u0313\3\2\2\2\u0312\u0310\3\2\2\2\u0313")
        buf.write("\u0314\bT\2\2\u0314\u00a8\3\2\2\2\u0315\u0317\t\13\2\2")
        buf.write("\u0316\u0315\3\2\2\2\u0317\u0318\3\2\2\2\u0318\u0316\3")
        buf.write("\2\2\2\u0318\u0319\3\2\2\2\u0319\u031a\3\2\2\2\u031a\u031b")
        buf.write("\bU\2\2\u031b\u00aa\3\2\2\2\u031c\u031d\7^\2\2\u031d\u0333")
        buf.write("\t\f\2\2\u031e\u0323\7^\2\2\u031f\u0321\t\r\2\2\u0320")
        buf.write("\u031f\3\2\2\2\u0320\u0321\3\2\2\2\u0321\u0322\3\2\2\2")
        buf.write("\u0322\u0324\t\16\2\2\u0323\u0320\3\2\2\2\u0323\u0324")
        buf.write("\3\2\2\2\u0324\u0325\3\2\2\2\u0325\u0333\t\16\2\2\u0326")
        buf.write("\u0327\7^\2\2\u0327\u0328\7w\2\2\u0328\u0329\5\u00adW")
        buf.write("\2\u0329\u032a\5\u00adW\2\u032a\u032b\5\u00adW\2\u032b")
        buf.write("\u032c\5\u00adW\2\u032c\u0333\3\2\2\2\u032d\u032e\7^\2")
        buf.write("\2\u032e\u032f\7z\2\2\u032f\u0330\5\u00adW\2\u0330\u0331")
        buf.write("\5\u00adW\2\u0331\u0333\3\2\2\2\u0332\u031c\3\2\2\2\u0332")
        buf.write("\u031e\3\2\2\2\u0332\u0326\3\2\2\2\u0332\u032d\3\2\2\2")
        buf.write("\u0333\u00ac\3\2\2\2\u0334\u0335\t\17\2\2\u0335\u00ae")
        buf.write("\3\2\2\2%\2\u01d1\u01d9\u01df\u020f\u0215\u021a\u021f")
        buf.write("\u0221\u0227\u022b\u0230\u0232\u0237\u023b\u0240\u0242")
        buf.write("\u024a\u024f\u025d\u026e\u02d6\u02dc\u02e2\u02e4\u02eb")
        buf.write("\u02ed\u02f1\u02f9\u0307\u0310\u0318\u0320\u0323\u0332")
        buf.write("\3\b\2\2")
        return buf.getvalue()


class BmcQueryLexer(Lexer):
    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [DFA(ds, i) for i, ds in enumerate(atn.decisionToState)]

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

    channelNames = ["DEFAULT_TOKEN_CHANNEL", "HIDDEN"]

    modeNames = ["DEFAULT_MODE"]

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

    ruleNames = [
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
        "EscapeSequence",
        "HexDigit",
    ]

    grammarFileName = "BmcQueryLexer.g4"

    def __init__(self, input=None, output: TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.9.3")
        self._interp = LexerATNSimulator(
            self, self.atn, self.decisionsToDFA, PredictionContextCache()
        )
        self._actions = None
        self._predicates = None
