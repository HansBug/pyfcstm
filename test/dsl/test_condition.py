import pytest

from pyfcstm.dsl import parse_condition, GrammarParseError, SyntaxFailError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLCondition:
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
        ('E < 3', Condition(expr=BinaryOp(expr1=Constant(raw='E'), op='<', expr2=Integer(raw='3')))),
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
        ('sin(pi/2) * cos(0) > sqrt(4) / 2 && log(E) == 1', Condition(expr=BinaryOp(expr1=BinaryOp(expr1=BinaryOp(
            expr1=UFunc(func='sin', expr=BinaryOp(expr1=Constant(raw='pi'), op='/', expr2=Integer(raw='2'))), op='*',
            expr2=UFunc(func='cos', expr=Integer(raw='0'))), op='>', expr2=BinaryOp(
            expr1=UFunc(func='sqrt', expr=Integer(raw='4')), op='/', expr2=Integer(raw='2'))), op='&&', expr2=BinaryOp(
            expr1=UFunc(func='log', expr=Constant(raw='E')), op='==', expr2=Integer(raw='1'))))),
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

        ('x < 5', Condition(expr=BinaryOp(expr1=Name(name='x'), op='<', expr2=Integer(raw='5')))),
        ('foo == bar', Condition(expr=BinaryOp(expr1=Name(name='foo'), op='==', expr2=Name(name='bar')))),
        ('a + b < c', Condition(
            expr=BinaryOp(expr1=BinaryOp(expr1=Name(name='a'), op='+', expr2=Name(name='b')), op='<',
                          expr2=Name(name='c')))),
        ('!!true', Condition(expr=UnaryOp(op='!', expr=UnaryOp(op='!', expr=Boolean(raw='true'))))),
        ('not!false', Condition(expr=UnaryOp(op='!', expr=UnaryOp(op='!', expr=Boolean(raw='false'))))),
        ('TRUE and FALSE', Condition(expr=BinaryOp(expr1=Boolean(raw='true'), op='&&', expr2=Boolean(raw='false')))),
        ('True and False', Condition(expr=BinaryOp(expr1=Boolean(raw='true'), op='&&', expr2=Boolean(raw='false')))),
        ('e < 3', Condition(expr=BinaryOp(expr1=Name(name='e'), op='<', expr2=Integer(raw='3')))),

        ('(true) ? true : true', Condition(expr=ConditionalOp(cond=Boolean(raw='true'), value_true=Boolean(raw='true'),
                                                              value_false=Boolean(raw='true')))),
        ('(true) ? true : False', Condition(expr=ConditionalOp(cond=Boolean(raw='true'), value_true=Boolean(raw='true'),
                                                               value_false=Boolean(raw='false')))),
        ('(true) ? true : x >=0', Condition(expr=ConditionalOp(cond=Boolean(raw='true'), value_true=Boolean(raw='true'),
                                                               value_false=BinaryOp(expr1=Name(name='x'), op='>=',
                                                                                    expr2=Integer(raw='0'))))),
        ('(true) ? False : true', Condition(
            expr=ConditionalOp(cond=Boolean(raw='true'), value_true=Boolean(raw='false'),
                               value_false=Boolean(raw='true')))),
        ('(true) ? False : False', Condition(
            expr=ConditionalOp(cond=Boolean(raw='true'), value_true=Boolean(raw='false'),
                               value_false=Boolean(raw='false')))),
        ('(true) ? False : x >=0', Condition(
            expr=ConditionalOp(cond=Boolean(raw='true'), value_true=Boolean(raw='false'),
                               value_false=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0'))))),
        ('(true) ? x >=0 : true', Condition(expr=ConditionalOp(cond=Boolean(raw='true'),
                                                               value_true=BinaryOp(expr1=Name(name='x'), op='>=',
                                                                                   expr2=Integer(raw='0')),
                                                               value_false=Boolean(raw='true')))),
        ('(true) ? x >=0 : False', Condition(expr=ConditionalOp(cond=Boolean(raw='true'),
                                                                value_true=BinaryOp(expr1=Name(name='x'), op='>=',
                                                                                    expr2=Integer(raw='0')),
                                                                value_false=Boolean(raw='false')))),
        ('(true) ? x >=0 : x >=0', Condition(expr=ConditionalOp(cond=Boolean(raw='true'),
                                                                value_true=BinaryOp(expr1=Name(name='x'), op='>=',
                                                                                    expr2=Integer(raw='0')),
                                                                value_false=BinaryOp(expr1=Name(name='x'), op='>=',
                                                                                     expr2=Integer(raw='0'))))),
        ('(False) ? true : true', Condition(
            expr=ConditionalOp(cond=Boolean(raw='false'), value_true=Boolean(raw='true'),
                               value_false=Boolean(raw='true')))),
        ('(False) ? true : False', Condition(
            expr=ConditionalOp(cond=Boolean(raw='false'), value_true=Boolean(raw='true'),
                               value_false=Boolean(raw='false')))),
        ('(False) ? true : x >=0', Condition(
            expr=ConditionalOp(cond=Boolean(raw='false'), value_true=Boolean(raw='true'),
                               value_false=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0'))))),
        ('(False) ? False : true', Condition(
            expr=ConditionalOp(cond=Boolean(raw='false'), value_true=Boolean(raw='false'),
                               value_false=Boolean(raw='true')))),
        ('(False) ? False : False', Condition(
            expr=ConditionalOp(cond=Boolean(raw='false'), value_true=Boolean(raw='false'),
                               value_false=Boolean(raw='false')))),
        ('(False) ? False : x >=0', Condition(
            expr=ConditionalOp(cond=Boolean(raw='false'), value_true=Boolean(raw='false'),
                               value_false=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0'))))),
        ('(False) ? x >=0 : true', Condition(expr=ConditionalOp(cond=Boolean(raw='false'),
                                                                value_true=BinaryOp(expr1=Name(name='x'), op='>=',
                                                                                    expr2=Integer(raw='0')),
                                                                value_false=Boolean(raw='true')))),
        ('(False) ? x >=0 : False', Condition(expr=ConditionalOp(cond=Boolean(raw='false'),
                                                                 value_true=BinaryOp(expr1=Name(name='x'), op='>=',
                                                                                     expr2=Integer(raw='0')),
                                                                 value_false=Boolean(raw='false')))),
        ('(False) ? x >=0 : x >=0', Condition(expr=ConditionalOp(cond=Boolean(raw='false'),
                                                                 value_true=BinaryOp(expr1=Name(name='x'), op='>=',
                                                                                     expr2=Integer(raw='0')),
                                                                 value_false=BinaryOp(expr1=Name(name='x'), op='>=',
                                                                                      expr2=Integer(raw='0'))))),
        ('(x >=0) ? true : true', Condition(
            expr=ConditionalOp(cond=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0')),
                               value_true=Boolean(raw='true'), value_false=Boolean(raw='true')))),
        ('(x >=0) ? true : False', Condition(
            expr=ConditionalOp(cond=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0')),
                               value_true=Boolean(raw='true'), value_false=Boolean(raw='false')))),
        ('(x >=0) ? true : x >=0', Condition(
            expr=ConditionalOp(cond=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0')),
                               value_true=Boolean(raw='true'),
                               value_false=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0'))))),
        ('(x >=0) ? False : true', Condition(
            expr=ConditionalOp(cond=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0')),
                               value_true=Boolean(raw='false'), value_false=Boolean(raw='true')))),
        ('(x >=0) ? False : False', Condition(
            expr=ConditionalOp(cond=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0')),
                               value_true=Boolean(raw='false'), value_false=Boolean(raw='false')))),
        ('(x >=0) ? False : x >=0', Condition(
            expr=ConditionalOp(cond=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0')),
                               value_true=Boolean(raw='false'),
                               value_false=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0'))))),
        ('(x >=0) ? x >=0 : true', Condition(
            expr=ConditionalOp(cond=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0')),
                               value_true=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0')),
                               value_false=Boolean(raw='true')))),
        ('(x >=0) ? x >=0 : False', Condition(
            expr=ConditionalOp(cond=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0')),
                               value_true=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0')),
                               value_false=Boolean(raw='false')))),
        ('(x >=0) ? x >=0 : x >=0', Condition(
            expr=ConditionalOp(cond=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0')),
                               value_true=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0')),
                               value_false=BinaryOp(expr1=Name(name='x'), op='>=', expr2=Integer(raw='0'))))),

        ('(a >1)== (a < 1)', Condition(
            expr=BinaryOp(expr1=Paren(expr=BinaryOp(expr1=Name(name='a'), op='>', expr2=Integer(raw='1'))), op='==',
                          expr2=Paren(expr=BinaryOp(expr1=Name(name='a'), op='<', expr2=Integer(raw='1')))))),
        # comparison between boolean expressions
        ('(a > 1)!= (a<1)', Condition(
            expr=BinaryOp(expr1=Paren(expr=BinaryOp(expr1=Name(name='a'), op='>', expr2=Integer(raw='1'))), op='!=',
                          expr2=Paren(expr=BinaryOp(expr1=Name(name='a'), op='<', expr2=Integer(raw='1')))))),
        # comparison between boolean expressions
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
        ('E < 3', 'E < 3'),
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
        ('sin(pi/2) * cos(0) > sqrt(4) / 2 && log(E) == 1', 'sin(pi / 2) * cos(0) > sqrt(4) / 2 && log(E) == 1'),
        ('true && false || true && !(false || true && false)', 'True && False || True && !(False || True && False)'),
        ('1 + 2 * 3 ** 2 / (4 % 3) >= 10 - 5 << 1', '1 + 2 * 3 ** 2 / (4 % 3) >= 10 - 5 << 1'),

        ('x < 5', 'x < 5'),
        ('foo == bar', 'foo == bar'),
        ('a + b < c', 'a + b < c'),
        ('!!true', '!!True'),
        ('not!false', '!!False'),
        ('TRUE and FALSE', 'True && False'),
        ('True and False', 'True && False'),
        ('e<3', 'e < 3'),

        ('(true) ? true : true', '(True) ? True : True'),
        ('(true) ? true : False', '(True) ? True : False'),
        ('(true) ? true : x >=0', '(True) ? True : x >= 0'),
        ('(true) ? False : true', '(True) ? False : True'),
        ('(true) ? False : False', '(True) ? False : False'),
        ('(true) ? False : x >=0', '(True) ? False : x >= 0'),
        ('(true) ? x >=0 : true', '(True) ? x >= 0 : True'),
        ('(true) ? x >=0 : False', '(True) ? x >= 0 : False'),
        ('(true) ? x >=0 : x >=0', '(True) ? x >= 0 : x >= 0'),
        ('(False) ? true : true', '(False) ? True : True'),
        ('(False) ? true : False', '(False) ? True : False'),
        ('(False) ? true : x >=0', '(False) ? True : x >= 0'),
        ('(False) ? False : true', '(False) ? False : True'),
        ('(False) ? False : False', '(False) ? False : False'),
        ('(False) ? False : x >=0', '(False) ? False : x >= 0'),
        ('(False) ? x >=0 : true', '(False) ? x >= 0 : True'),
        ('(False) ? x >=0 : False', '(False) ? x >= 0 : False'),
        ('(False) ? x >=0 : x >=0', '(False) ? x >= 0 : x >= 0'),
        ('(x >=0) ? true : true', '(x >= 0) ? True : True'),
        ('(x >=0) ? true : False', '(x >= 0) ? True : False'),
        ('(x >=0) ? true : x >=0', '(x >= 0) ? True : x >= 0'),
        ('(x >=0) ? False : true', '(x >= 0) ? False : True'),
        ('(x >=0) ? False : False', '(x >= 0) ? False : False'),
        ('(x >=0) ? False : x >=0', '(x >= 0) ? False : x >= 0'),
        ('(x >=0) ? x >=0 : true', '(x >= 0) ? x >= 0 : True'),
        ('(x >=0) ? x >=0 : False', '(x >= 0) ? x >= 0 : False'),
        ('(x >=0) ? x >=0 : x >=0', '(x >= 0) ? x >= 0 : x >= 0'),

        ('(a >1)== (a < 1)', '(a > 1) == (a < 1)'),  # comparison between boolean expressions
        ('(a > 1)!= (a<1)', '(a > 1) != (a < 1)'),  # comparison between boolean expressions
    ])
    def test_positive_cases_str(self, input_text, expected_str):
        assert str(parse_condition(input_text)) == expected_str

    @pytest.mark.parametrize(['input_text'], [
        ('',),
        (';',),
        ('true;',),
        ('1 + ',),
        (' < 2',),
        ('&&',),
        ('||',),
        ('(',),
        (')',),
        ('(true',),
        ('true)',),
        ('((true)',),
        ('(true))',),
        ('1 < < 2',),
        ('1 > > 2',),
        ('true && || false',),
        ('true and or false',),
        ('1 === 2',),
        ('3 !== 4',),
        ('1 && 2',),
        ('true < false',),
        ('true == 1',),
        ('3.14 || 2.71',),
        ('true + false',),
        ('! 1',),
        ('not 2',),
        ('sin',),
        ('sin()',),
        ('sin(,)',),
        ('sin(1,2)',),
        ('unknown(1)',),
        ('PI',),
        ('E',),
        ('TAU',),
        ('pi()',),
        ('1..2',),
        ('3..',),
        ('.5.6',),
        ('1e',),
        ('2e+',),
        ('3e++1',),
        ('truee',),
        ('ffalse',),
        ('TRUEE',),
        ('1 +- 2',),
        ('3 */ 4',),
        ('5 <<>> 6',),
        ('7 &| 8',),
        ('1 + (2',),
        ('sin(1',),
        ('1 + sin()',),
        ('1 + * 2',),
        ('1 + ',),
        (' * 3',),
        ('1 && ',),
        (' || true',),
        ('2 ** ** 2',),
        ('** 2',),
        ('2 **',),
        ('1 + 2 == true',),
        ('(1 < 2)) && ((3 > 4)',),
        ('sin(true) == 1',),
        ('log(false) > 0',),
        ('1 # 2',),
        ('true @ false',),
        ('1 $ 2 < 3',),
        ('1 + 2 * / 3',),
        ('(1 < 2) && (3 > ) || (5 == 5)',),
        ('sin(pi/2) * cos() > sqrt(4) / 2',),
        ('true && false || & true',),
    ])
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_condition(input_text)

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f'Found {len(err.errors)} errors during parsing:' in err.args[0]
