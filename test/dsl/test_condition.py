import pytest

from pyfcstm.dsl import parse_condition
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestGrammarCondition:
    @pytest.mark.parametrize(['input_text', 'expected'], [
        ('true', Condition(expr=Boolean(raw='true'))),
        ('false', Condition(expr=Boolean(raw='false'))),
        ('True', Condition(expr=Boolean(raw='true'))),
        ('FALSE', Condition(expr=Boolean(raw='false'))),
        ('1 < 2', Condition(expr=BinaryOp(expr1=Integer(raw='1'), op='<', expr2=Integer(raw='2')))),
        ('3.14 > 2', Condition(expr=BinaryOp(expr1=Float(raw='3.14'), op='>', expr2=Integer(raw='2')))),
        ('5 <= 10', Condition(expr=BinaryOp(expr1=Integer(raw='5'), op='<=', expr2=Integer(raw='10')))),
        ('7.5 >= 7', Condition(expr=BinaryOp(expr1=Float(raw='7.5'), op='>=', expr2=Integer(raw='7')))),
        ('42 == 42', Condition(expr=BinaryOp(expr1=Integer(raw='42'), op='==', expr2=Integer(raw='42')))),
        ('3.14 != 3', Condition(expr=BinaryOp(expr1=Float(raw='3.14'), op='!=', expr2=Integer(raw='3')))),
        ('(true)', Condition(expr=Paren(expr=Boolean(raw='true')))),
        ('(1 < 2)', Condition(expr=Paren(expr=BinaryOp(expr1=Integer(raw='1'), op='<', expr2=Integer(raw='2'))))),
        ('((true))', Condition(expr=Paren(expr=Paren(expr=Boolean(raw='true'))))),
        ('!true', Condition(expr=UnaryOp(op='!', expr=Boolean(raw='true')))),
        ('not false', Condition(expr=UnaryOp(op='!', expr=Boolean(raw='false')))),
        ('!(1 < 2)', Condition(
            expr=UnaryOp(op='!', expr=Paren(expr=BinaryOp(expr1=Integer(raw='1'), op='<', expr2=Integer(raw='2')))))),
        ('not(3 > 4)', Condition(
            expr=UnaryOp(op='!', expr=Paren(expr=BinaryOp(expr1=Integer(raw='3'), op='>', expr2=Integer(raw='4')))))),
        ('true && true', Condition(expr=BinaryOp(expr1=Boolean(raw='true'), op='&&', expr2=Boolean(raw='true')))),
        ('false and true', Condition(expr=BinaryOp(expr1=Boolean(raw='false'), op='&&', expr2=Boolean(raw='true')))),
        ('(1 < 2) && (3 > 4)', Condition(
            expr=BinaryOp(expr1=Paren(expr=BinaryOp(expr1=Integer(raw='1'), op='<', expr2=Integer(raw='2'))), op='&&',
                          expr2=Paren(expr=BinaryOp(expr1=Integer(raw='3'), op='>', expr2=Integer(raw='4')))))),
        ('true && false && true', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Boolean(raw='true'), op='&&', expr2=Boolean(raw='false')), op='&&',
                          expr2=Boolean(raw='true')))),
        ('true || false', Condition(expr=BinaryOp(expr1=Boolean(raw='true'), op='||', expr2=Boolean(raw='false')))),
        ('false or true', Condition(expr=BinaryOp(expr1=Boolean(raw='false'), op='||', expr2=Boolean(raw='true')))),
        ('(1 < 2) || (3 > 4)', Condition(
            expr=BinaryOp(expr1=Paren(expr=BinaryOp(expr1=Integer(raw='1'), op='<', expr2=Integer(raw='2'))), op='||',
                          expr2=Paren(expr=BinaryOp(expr1=Integer(raw='3'), op='>', expr2=Integer(raw='4')))))),
        ('false || false || true', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Boolean(raw='false'), op='||', expr2=Boolean(raw='false')), op='||',
                          expr2=Boolean(raw='true')))),
        ('true && false || true', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Boolean(raw='true'), op='&&', expr2=Boolean(raw='false')), op='||',
                          expr2=Boolean(raw='true')))),
        ('false || true && true', Condition(expr=BinaryOp(expr1=Boolean(raw='false'), op='||',
                                                          expr2=BinaryOp(expr1=Boolean(raw='true'), op='&&',
                                                                         expr2=Boolean(raw='true'))))),
        ('true || false && false', Condition(expr=BinaryOp(expr1=Boolean(raw='true'), op='||',
                                                           expr2=BinaryOp(expr1=Boolean(raw='false'), op='&&',
                                                                          expr2=Boolean(raw='false'))))),
        ('(true || false) && false', Condition(
            expr=BinaryOp(expr1=Paren(expr=BinaryOp(expr1=Boolean(raw='true'), op='||', expr2=Boolean(raw='false'))),
                          op='&&', expr2=Boolean(raw='false')))),
        ('!(true && false) || true', Condition(expr=BinaryOp(expr1=UnaryOp(op='!', expr=Paren(
            expr=BinaryOp(expr1=Boolean(raw='true'), op='&&', expr2=Boolean(raw='false')))), op='||',
                                                             expr2=Boolean(raw='true')))),
        ('1 + 2 < 4', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='1'), op='+', expr2=Integer(raw='2')), op='<',
                          expr2=Integer(raw='4')))),
        ('3 * 4 > 10', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='3'), op='*', expr2=Integer(raw='4')), op='>',
                          expr2=Integer(raw='10')))),
        ('5 - 2 <= 3', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='5'), op='-', expr2=Integer(raw='2')), op='<=',
                          expr2=Integer(raw='3')))),
        ('10 / 2 >= 4', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='10'), op='/', expr2=Integer(raw='2')), op='>=',
                          expr2=Integer(raw='4')))),
        ('2 ** 3 == 8', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='2'), op='**', expr2=Integer(raw='3')), op='==',
                          expr2=Integer(raw='8')))),
        ('7 % 3 != 2', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='7'), op='%', expr2=Integer(raw='3')), op='!=',
                          expr2=Integer(raw='2')))),
        ('1 + 2 * 3 < 10', Condition(expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='1'), op='+',
                                                                  expr2=BinaryOp(expr1=Integer(raw='2'), op='*',
                                                                                 expr2=Integer(raw='3'))), op='<',
                                                   expr2=Integer(raw='10')))),
        ('(1 + 2) * 3 > 5', Condition(expr=BinaryOp(
            expr1=BinaryOp(expr1=Paren(expr=BinaryOp(expr1=Integer(raw='1'), op='+', expr2=Integer(raw='2'))), op='*',
                           expr2=Integer(raw='3')), op='>', expr2=Integer(raw='5')))),
        ('2 ** 3 + 1 == 9', Condition(expr=BinaryOp(
            expr1=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='2'), op='**', expr2=Integer(raw='3')), op='+',
                           expr2=Integer(raw='1')), op='==', expr2=Integer(raw='9')))),
        ('10 - 5 / 2.5 == 8', Condition(expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='10'), op='-',
                                                                     expr2=BinaryOp(expr1=Integer(raw='5'), op='/',
                                                                                    expr2=Float(raw='2.5'))), op='==',
                                                      expr2=Integer(raw='8')))),
        ('+1 < 2',
         Condition(expr=BinaryOp(expr1=UnaryOp(op='+', expr=Integer(raw='1')), op='<', expr2=Integer(raw='2')))),
        ('-1 > -2', Condition(expr=BinaryOp(expr1=UnaryOp(op='-', expr=Integer(raw='1')), op='>',
                                            expr2=UnaryOp(op='-', expr=Integer(raw='2'))))),
        ('-(1 + 2) < 0', Condition(expr=BinaryOp(
            expr1=UnaryOp(op='-', expr=Paren(expr=BinaryOp(expr1=Integer(raw='1'), op='+', expr2=Integer(raw='2')))),
            op='<', expr2=Integer(raw='0')))),
        ('1 << 2 == 4', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='1'), op='<<', expr2=Integer(raw='2')), op='==',
                          expr2=Integer(raw='4')))),
        ('8 >> 1 == 4', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='8'), op='>>', expr2=Integer(raw='1')), op='==',
                          expr2=Integer(raw='4')))),
        ('5 & 3 == 1', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='5'), op='&', expr2=Integer(raw='3')), op='==',
                          expr2=Integer(raw='1')))),
        ('5 | 3 == 7', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='5'), op='|', expr2=Integer(raw='3')), op='==',
                          expr2=Integer(raw='7')))),
        ('5 ^ 3 == 6', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='5'), op='^', expr2=Integer(raw='3')), op='==',
                          expr2=Integer(raw='6')))),
        ('pi > 3', Condition(expr=BinaryOp(expr1=Constant(raw='pi'), op='>', expr2=Integer(raw='3')))),
        ('e < 3', Condition(expr=BinaryOp(expr1=Constant(raw='e'), op='<', expr2=Integer(raw='3')))),
        ('tau > 6', Condition(expr=BinaryOp(expr1=Constant(raw='tau'), op='>', expr2=Integer(raw='6')))),
        ('sin(0) == 0',
         Condition(expr=BinaryOp(expr1=UFunc(func='sin', expr=Integer(raw='0')), op='==', expr2=Integer(raw='0')))),
        ('cos(0) == 1',
         Condition(expr=BinaryOp(expr1=UFunc(func='cos', expr=Integer(raw='0')), op='==', expr2=Integer(raw='1')))),
        ('sqrt(4) == 2',
         Condition(expr=BinaryOp(expr1=UFunc(func='sqrt', expr=Integer(raw='4')), op='==', expr2=Integer(raw='2')))),
        ('log(1) == 0',
         Condition(expr=BinaryOp(expr1=UFunc(func='log', expr=Integer(raw='1')), op='==', expr2=Integer(raw='0')))),
        ('sin(pi/2) > cos(pi)', Condition(expr=BinaryOp(
            expr1=UFunc(func='sin', expr=BinaryOp(expr1=Constant(raw='pi'), op='/', expr2=Integer(raw='2'))), op='>',
            expr2=UFunc(func='cos', expr=Constant(raw='pi'))))),
        ('sqrt(1 + 4) == 2 + 1', Condition(expr=BinaryOp(
            expr1=UFunc(func='sqrt', expr=BinaryOp(expr1=Integer(raw='1'), op='+', expr2=Integer(raw='4'))), op='==',
            expr2=BinaryOp(expr1=Integer(raw='2'), op='+', expr2=Integer(raw='1'))))),
        ('abs(-1) == 1', Condition(
            expr=BinaryOp(expr1=UFunc(func='abs', expr=UnaryOp(op='-', expr=Integer(raw='1'))), op='==',
                          expr2=Integer(raw='1')))),
        ('(1 < 2) && (3 <= 4) || !(5 > 6)', Condition(expr=BinaryOp(
            expr1=BinaryOp(expr1=Paren(expr=BinaryOp(expr1=Integer(raw='1'), op='<', expr2=Integer(raw='2'))), op='&&',
                           expr2=Paren(expr=BinaryOp(expr1=Integer(raw='3'), op='<=', expr2=Integer(raw='4')))),
            op='||',
            expr2=UnaryOp(op='!', expr=Paren(expr=BinaryOp(expr1=Integer(raw='5'), op='>', expr2=Integer(raw='6'))))))),
        ('sin(pi/2) > 0 && cos(pi) < 0 || sqrt(4) == 2', Condition(expr=BinaryOp(expr1=BinaryOp(expr1=BinaryOp(
            expr1=UFunc(func='sin', expr=BinaryOp(expr1=Constant(raw='pi'), op='/', expr2=Integer(raw='2'))), op='>',
            expr2=Integer(raw='0')), op='&&', expr2=BinaryOp(expr1=UFunc(func='cos', expr=Constant(raw='pi')), op='<',
                                                             expr2=Integer(raw='0'))), op='||', expr2=BinaryOp(
            expr1=UFunc(func='sqrt', expr=Integer(raw='4')), op='==', expr2=Integer(raw='2'))))),
        ('true && (false || (1 < 2) && (3 > 4))', Condition(expr=BinaryOp(expr1=Boolean(raw='true'), op='&&',
                                                                          expr2=Paren(
                                                                              expr=BinaryOp(expr1=Boolean(raw='false'),
                                                                                            op='||', expr2=BinaryOp(
                                                                                      expr1=Paren(expr=BinaryOp(
                                                                                          expr1=Integer(raw='1'),
                                                                                          op='<',
                                                                                          expr2=Integer(raw='2'))),
                                                                                      op='&&', expr2=Paren(
                                                                                          expr=BinaryOp(
                                                                                              expr1=Integer(raw='3'),
                                                                                              op='>', expr2=Integer(
                                                                                                  raw='4'))))))))),
        ('2 ** 2 ** 2 == 16', Condition(expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='2'), op='**',
                                                                     expr2=BinaryOp(expr1=Integer(raw='2'), op='**',
                                                                                    expr2=Integer(raw='2'))), op='==',
                                                      expr2=Integer(raw='16')))),
        ('2 ** 3 ** 2 == 512', Condition(expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='2'), op='**',
                                                                      expr2=BinaryOp(expr1=Integer(raw='3'), op='**',
                                                                                     expr2=Integer(raw='2'))), op='==',
                                                       expr2=Integer(raw='512')))),
        ('1 + 2 * 3 ** 2 == 19', Condition(expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='1'), op='+',
                                                                        expr2=BinaryOp(expr1=Integer(raw='2'), op='*',
                                                                                       expr2=BinaryOp(
                                                                                           expr1=Integer(raw='3'),
                                                                                           op='**',
                                                                                           expr2=Integer(raw='2')))),
                                                         op='==', expr2=Integer(raw='19')))),
        ('1 << 2 + 3 == 32', Condition(expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='1'), op='<<',
                                                                    expr2=BinaryOp(expr1=Integer(raw='2'), op='+',
                                                                                   expr2=Integer(raw='3'))), op='==',
                                                     expr2=Integer(raw='32')))),
        ('(1 << 2) + 3 == 7', Condition(expr=BinaryOp(
            expr1=BinaryOp(expr1=Paren(expr=BinaryOp(expr1=Integer(raw='1'), op='<<', expr2=Integer(raw='2'))), op='+',
                           expr2=Integer(raw='3')), op='==', expr2=Integer(raw='7')))),
        ('1 + 2 * 3 > 4 && 5 - 6 / 3 < 4', Condition(expr=BinaryOp(expr1=BinaryOp(
            expr1=BinaryOp(expr1=Integer(raw='1'), op='+',
                           expr2=BinaryOp(expr1=Integer(raw='2'), op='*', expr2=Integer(raw='3'))), op='>',
            expr2=Integer(raw='4')), op='&&', expr2=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='5'), op='-',
                                                                            expr2=BinaryOp(expr1=Integer(raw='6'),
                                                                                           op='/',
                                                                                           expr2=Integer(raw='3'))),
                                                             op='<', expr2=Integer(raw='4'))))),
        ('((1 < 2) && (3 > 4)) || (!(5 == 5) && (6 != 7))', Condition(expr=BinaryOp(expr1=Paren(
            expr=BinaryOp(expr1=Paren(expr=BinaryOp(expr1=Integer(raw='1'), op='<', expr2=Integer(raw='2'))), op='&&',
                          expr2=Paren(expr=BinaryOp(expr1=Integer(raw='3'), op='>', expr2=Integer(raw='4'))))), op='||',
            expr2=Paren(expr=BinaryOp(
                expr1=UnaryOp(op='!',
                              expr=Paren(
                                  expr=BinaryOp(
                                      expr1=Integer(
                                          raw='5'),
                                      op='==',
                                      expr2=Integer(
                                          raw='5')))),
                op='&&', expr2=Paren(
                    expr=BinaryOp(
                        expr1=Integer(raw='6'),
                        op='!=', expr2=Integer(
                            raw='7')))))))),
        ('sin(pi/2) * cos(0) > sqrt(4) / 2 && log(e) == 1', Condition(expr=BinaryOp(expr1=BinaryOp(expr1=BinaryOp(
            expr1=UFunc(func='sin', expr=BinaryOp(expr1=Constant(raw='pi'), op='/', expr2=Integer(raw='2'))), op='*',
            expr2=UFunc(func='cos', expr=Integer(raw='0'))), op='>', expr2=BinaryOp(
            expr1=UFunc(func='sqrt', expr=Integer(raw='4')), op='/', expr2=Integer(raw='2'))), op='&&', expr2=BinaryOp(
            expr1=UFunc(func='log', expr=Constant(raw='e')), op='==', expr2=Integer(raw='1'))))),
        ('true && false || true && !(false || true && false)', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Boolean(raw='true'), op='&&', expr2=Boolean(raw='false')), op='||',
                          expr2=BinaryOp(expr1=Boolean(raw='true'), op='&&', expr2=UnaryOp(op='!', expr=Paren(
                              expr=BinaryOp(expr1=Boolean(raw='false'), op='||',
                                            expr2=BinaryOp(expr1=Boolean(raw='true'), op='&&',
                                                           expr2=Boolean(raw='false'))))))))),
        ('1 + 2 * 3 ** 2 / (4 % 3) >= 10 - 5 << 1', Condition(expr=BinaryOp(
            expr1=BinaryOp(expr1=Integer(raw='1'), op='+', expr2=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='2'), op='*',
                                                                                         expr2=BinaryOp(
                                                                                             expr1=Integer(raw='3'),
                                                                                             op='**',
                                                                                             expr2=Integer(raw='2'))),
                                                                          op='/', expr2=Paren(
                    expr=BinaryOp(expr1=Integer(raw='4'), op='%', expr2=Integer(raw='3'))))), op='>=',
            expr2=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='10'), op='-', expr2=Integer(raw='5')), op='<<',
                           expr2=Integer(raw='1'))))),

    ])
    def test_positive_cases(self, input_text, expected):
        assert parse_condition(input_text) == expected

    @pytest.mark.parametrize(['input_text', 'expected_str'], [
        ('true', 'True'),
        ('false', 'False'),
        ('True', 'True'),
        ('FALSE', 'False'),
        ('1 < 2', '1 < 2'),
        ('3.14 > 2', '3.14 > 2'),
        ('5 <= 10', '5 <= 10'),
        ('7.5 >= 7', '7.5 >= 7'),
        ('42 == 42', '42 == 42'),
        ('3.14 != 3', '3.14 != 3'),
        ('(true)', '(True)'),
        ('(1 < 2)', '(1 < 2)'),
        ('((true))', '((True))'),
        ('!true', '!True'),
        ('not false', '!False'),
        ('!(1 < 2)', '!(1 < 2)'),
        ('not(3 > 4)', '!(3 > 4)'),
        ('true && true', 'True && True'),
        ('false and true', 'False && True'),
        ('(1 < 2) && (3 > 4)', '(1 < 2) && (3 > 4)'),
        ('true && false && true', 'True && False && True'),
        ('true || false', 'True || False'),
        ('false or true', 'False || True'),
        ('(1 < 2) || (3 > 4)', '(1 < 2) || (3 > 4)'),
        ('false || false || true', 'False || False || True'),
        ('true && false || true', 'True && False || True'),
        ('false || true && true', 'False || True && True'),
        ('true || false && false', 'True || False && False'),
        ('(true || false) && false', '(True || False) && False'),
        ('!(true && false) || true', '!(True && False) || True'),
        ('1 + 2 < 4', '1 + 2 < 4'),
        ('3 * 4 > 10', '3 * 4 > 10'),
        ('5 - 2 <= 3', '5 - 2 <= 3'),
        ('10 / 2 >= 4', '10 / 2 >= 4'),
        ('2 ** 3 == 8', '2 ** 3 == 8'),
        ('7 % 3 != 2', '7 % 3 != 2'),
        ('1 + 2 * 3 < 10', '1 + 2 * 3 < 10'),
        ('(1 + 2) * 3 > 5', '(1 + 2) * 3 > 5'),
        ('2 ** 3 + 1 == 9', '2 ** 3 + 1 == 9'),
        ('10 - 5 / 2.5 == 8', '10 - 5 / 2.5 == 8'),
        ('+1 < 2', '+1 < 2'),
        ('-1 > -2', '-1 > -2'),
        ('-(1 + 2) < 0', '-(1 + 2) < 0'),
        ('1 << 2 == 4', '1 << 2 == 4'),
        ('8 >> 1 == 4', '8 >> 1 == 4'),
        ('5 & 3 == 1', '5 & 3 == 1'),
        ('5 | 3 == 7', '5 | 3 == 7'),
        ('5 ^ 3 == 6', '5 ^ 3 == 6'),
        ('pi > 3', 'pi > 3'),
        ('e < 3', 'e < 3'),
        ('tau > 6', 'tau > 6'),
        ('sin(0) == 0', 'sin(0) == 0'),
        ('cos(0) == 1', 'cos(0) == 1'),
        ('sqrt(4) == 2', 'sqrt(4) == 2'),
        ('log(1) == 0', 'log(1) == 0'),
        ('sin(pi/2) > cos(pi)', 'sin(pi / 2) > cos(pi)'),
        ('sqrt(1 + 4) == 2 + 1', 'sqrt(1 + 4) == 2 + 1'),
        ('abs(-1) == 1', 'abs(-1) == 1'),
        ('(1 < 2) && (3 <= 4) || !(5 > 6)', '(1 < 2) && (3 <= 4) || !(5 > 6)'),
        ('sin(pi/2) > 0 && cos(pi) < 0 || sqrt(4) == 2', 'sin(pi / 2) > 0 && cos(pi) < 0 || sqrt(4) == 2'),
        ('true && (false || (1 < 2) && (3 > 4))', 'True && (False || (1 < 2) && (3 > 4))'),
        ('2 ** 2 ** 2 == 16', '2 ** 2 ** 2 == 16'),
        ('2 ** 3 ** 2 == 512', '2 ** 3 ** 2 == 512'),
        ('1 + 2 * 3 ** 2 == 19', '1 + 2 * 3 ** 2 == 19'),
        ('1 << 2 + 3 == 32', '1 << 2 + 3 == 32'),
        ('(1 << 2) + 3 == 7', '(1 << 2) + 3 == 7'),
        ('1 + 2 * 3 > 4 && 5 - 6 / 3 < 4', '1 + 2 * 3 > 4 && 5 - 6 / 3 < 4'),
        ('((1 < 2) && (3 > 4)) || (!(5 == 5) && (6 != 7))', '((1 < 2) && (3 > 4)) || (!(5 == 5) && (6 != 7))'),
        ('sin(pi/2) * cos(0) > sqrt(4) / 2 && log(e) == 1', 'sin(pi / 2) * cos(0) > sqrt(4) / 2 && log(e) == 1'),
        ('true && false || true && !(false || true && false)', 'True && False || True && !(False || True && False)'),
        ('1 + 2 * 3 ** 2 / (4 % 3) >= 10 - 5 << 1', '1 + 2 * 3 ** 2 / (4 % 3) >= 10 - 5 << 1'),
    ])
    def test_positive_cases_str(self, input_text, expected_str):
        assert str(parse_condition(input_text)) == expected_str
