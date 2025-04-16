import pytest

from pyfcstm.dsl import parse_preamble, GrammarParseError, SyntaxFailError
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLPreamble:
    @pytest.mark.parametrize(['input_text', 'expected'], [
        ('x := 10;\ny = 20;', Preamble(stats=[InitialAssignment(name='x', expr=Integer(raw='10')),
                                              ConstantDefinition(name='y', expr=Integer(raw='20'))])),
        ('pi_val := pi;\ne_val := E;\ntau_val := tau;', Preamble(
            stats=[InitialAssignment(name='pi_val', expr=Constant(raw='pi')),
                   InitialAssignment(name='e_val', expr=Constant(raw='E')),
                   InitialAssignment(name='tau_val', expr=Constant(raw='tau'))])),
        ('int_var := 42;\nfloat_var := 3.14;\nsci_var := 1.23e-4;\n', Preamble(
            stats=[InitialAssignment(name='int_var', expr=Integer(raw='42')),
                   InitialAssignment(name='float_var', expr=Float(raw='3.14')),
                   InitialAssignment(name='sci_var', expr=Float(raw='1.23e-4'))])),
        ('pos_var := +10;\nneg_var := -20;\n', Preamble(
            stats=[InitialAssignment(name='pos_var', expr=UnaryOp(op='+', expr=Integer(raw='10'))),
                   InitialAssignment(name='neg_var', expr=UnaryOp(op='-', expr=Integer(raw='20')))])),
        ('add_var := 5 + 3;\nsub_var := 10 - 7;\nmult_var := 4 * 6;\ndiv_var := 20 / 5;\nmod_var := 7 % 3;', Preamble(
            stats=[InitialAssignment(name='add_var',
                                     expr=BinaryOp(expr1=Integer(raw='5'), op='+', expr2=Integer(raw='3'))),
                   InitialAssignment(name='sub_var',
                                     expr=BinaryOp(expr1=Integer(raw='10'), op='-', expr2=Integer(raw='7'))),
                   InitialAssignment(name='mult_var',
                                     expr=BinaryOp(expr1=Integer(raw='4'), op='*', expr2=Integer(raw='6'))),
                   InitialAssignment(name='div_var',
                                     expr=BinaryOp(expr1=Integer(raw='20'), op='/', expr2=Integer(raw='5'))),
                   InitialAssignment(name='mod_var',
                                     expr=BinaryOp(expr1=Integer(raw='7'), op='%', expr2=Integer(raw='3')))])),
        ('shift_left := 1 << 3;\nshift_right := 16 >> 2;\nbit_and := 7 & 3;\nbit_or := 4 | 2;\nbit_xor := 7 ^ 3;',
         Preamble(stats=[InitialAssignment(name='shift_left',
                                           expr=BinaryOp(expr1=Integer(raw='1'), op='<<', expr2=Integer(raw='3'))),
                         InitialAssignment(name='shift_right',
                                           expr=BinaryOp(expr1=Integer(raw='16'), op='>>', expr2=Integer(raw='2'))),
                         InitialAssignment(name='bit_and',
                                           expr=BinaryOp(expr1=Integer(raw='7'), op='&', expr2=Integer(raw='3'))),
                         InitialAssignment(name='bit_or',
                                           expr=BinaryOp(expr1=Integer(raw='4'), op='|', expr2=Integer(raw='2'))),
                         InitialAssignment(name='bit_xor',
                                           expr=BinaryOp(expr1=Integer(raw='7'), op='^', expr2=Integer(raw='3')))])),
        ('power_var := 2 ** 3;\npower_chain := 2 ** 3 ** 2;\n', Preamble(stats=[
            InitialAssignment(name='power_var', expr=BinaryOp(expr1=Integer(raw='2'), op='**', expr2=Integer(raw='3'))),
            InitialAssignment(name='power_chain', expr=BinaryOp(expr1=Integer(raw='2'), op='**',
                                                                expr2=BinaryOp(expr1=Integer(raw='3'), op='**',
                                                                               expr2=Integer(raw='2'))))])),
        ('sin_val := sin(0.5);\ncos_val := cos(pi);\nsqrt_val := sqrt(16);\nlog_val := log(10);\n', Preamble(
            stats=[InitialAssignment(name='sin_val', expr=UFunc(func='sin', expr=Float(raw='0.5'))),
                   InitialAssignment(name='cos_val', expr=UFunc(func='cos', expr=Constant(raw='pi'))),
                   InitialAssignment(name='sqrt_val', expr=UFunc(func='sqrt', expr=Integer(raw='16'))),
                   InitialAssignment(name='log_val', expr=UFunc(func='log', expr=Integer(raw='10')))])),
        ('complex_expr1 := 2 + 3 * 4;\ncomplex_expr2 := (2 + 3) * 4;\n', Preamble(stats=[
            InitialAssignment(name='complex_expr1', expr=BinaryOp(expr1=Integer(raw='2'), op='+',
                                                                  expr2=BinaryOp(expr1=Integer(raw='3'), op='*',
                                                                                 expr2=Integer(raw='4')))),
            InitialAssignment(name='complex_expr2', expr=BinaryOp(
                expr1=Paren(expr=BinaryOp(expr1=Integer(raw='2'), op='+', expr2=Integer(raw='3'))), op='*',
                expr2=Integer(raw='4')))])),
        ('nested_expr := 2 * (3 + 4 * (5 - 2)) / 3;\n', Preamble(stats=[InitialAssignment(name='nested_expr',
                                                                                          expr=BinaryOp(expr1=BinaryOp(
                                                                                              expr1=Integer(raw='2'),
                                                                                              op='*', expr2=Paren(
                                                                                                  expr=BinaryOp(
                                                                                                      expr1=Integer(
                                                                                                          raw='3'),
                                                                                                      op='+',
                                                                                                      expr2=BinaryOp(
                                                                                                          expr1=Integer(
                                                                                                              raw='4'),
                                                                                                          op='*',
                                                                                                          expr2=Paren(
                                                                                                              expr=BinaryOp(
                                                                                                                  expr1=Integer(
                                                                                                                      raw='5'),
                                                                                                                  op='-',
                                                                                                                  expr2=Integer(
                                                                                                                      raw='2'))))))),
                                                                                              op='/',
                                                                                              expr2=Integer(
                                                                                                  raw='3')))])),
        ('mixed_ops := 3 + 4 * 2 / (1 - 5) ** 2 ** 3;\n', Preamble(stats=[InitialAssignment(name='mixed_ops',
                                                                                            expr=BinaryOp(
                                                                                                expr1=Integer(raw='3'),
                                                                                                op='+', expr2=BinaryOp(
                                                                                                    expr1=BinaryOp(
                                                                                                        expr1=Integer(
                                                                                                            raw='4'),
                                                                                                        op='*',
                                                                                                        expr2=Integer(
                                                                                                            raw='2')),
                                                                                                    op='/',
                                                                                                    expr2=BinaryOp(
                                                                                                        expr1=Paren(
                                                                                                            expr=BinaryOp(
                                                                                                                expr1=Integer(
                                                                                                                    raw='1'),
                                                                                                                op='-',
                                                                                                                expr2=Integer(
                                                                                                                    raw='5'))),
                                                                                                        op='**',
                                                                                                        expr2=BinaryOp(
                                                                                                            expr1=Integer(
                                                                                                                raw='2'),
                                                                                                            op='**',
                                                                                                            expr2=Integer(
                                                                                                                raw='3'))))))])),
        ('func_nest := sin(cos(pi/4) + sqrt(2));\n', Preamble(stats=[InitialAssignment(name='func_nest',
                                                                                       expr=UFunc(func='sin',
                                                                                                  expr=BinaryOp(
                                                                                                      expr1=UFunc(
                                                                                                          func='cos',
                                                                                                          expr=BinaryOp(
                                                                                                              expr1=Constant(
                                                                                                                  raw='pi'),
                                                                                                              op='/',
                                                                                                              expr2=Integer(
                                                                                                                  raw='4'))),
                                                                                                      op='+',
                                                                                                      expr2=UFunc(
                                                                                                          func='sqrt',
                                                                                                          expr=Integer(
                                                                                                              raw='2')))))])),
        ('bit_mix := (1 << 4) | (3 & 7) ^ (10 >> 1);\n', Preamble(stats=[InitialAssignment(name='bit_mix',
                                                                                           expr=BinaryOp(expr1=BinaryOp(
                                                                                               expr1=Paren(
                                                                                                   expr=BinaryOp(
                                                                                                       expr1=Integer(
                                                                                                           raw='1'),
                                                                                                       op='<<',
                                                                                                       expr2=Integer(
                                                                                                           raw='4'))),
                                                                                               op='|', expr2=Paren(
                                                                                                   expr=BinaryOp(
                                                                                                       expr1=Integer(
                                                                                                           raw='3'),
                                                                                                       op='&',
                                                                                                       expr2=Integer(
                                                                                                           raw='7')))),
                                                                                               op='^',
                                                                                               expr2=Paren(
                                                                                                   expr=BinaryOp(
                                                                                                       expr1=Integer(
                                                                                                           raw='10'),
                                                                                                       op='>>',
                                                                                                       expr2=Integer(
                                                                                                           raw='1')))))])),
        (
                '\n    sin_val := sin(0.5);\n    cos_val := cos(0.5);\n    tan_val := tan(0.5);\n    asin_val := asin(0.5);\n    acos_val := acos(0.5);\n    atan_val := atan(0.5);\n    sinh_val := sinh(0.5);\n    cosh_val := cosh(0.5);\n    tanh_val := tanh(0.5);\n    asinh_val := asinh(0.5);\n    acosh_val := acosh(1.5);\n    atanh_val := atanh(0.5);\n    sqrt_val := sqrt(4);\n    cbrt_val := cbrt(8);\n    exp_val := exp(1);\n    log_val := log(10);\n    log10_val := log10(100);\n    log2_val := log2(8);\n    log1p_val := log1p(1);\n    abs_val := abs(-5);\n    ceil_val := ceil(4.3);\n    floor_val := floor(4.7);\n    round_val := round(4.5);\n    trunc_val := trunc(4.9);\n    sign_val := sign(-10);\n    ',
                Preamble(stats=[InitialAssignment(name='sin_val', expr=UFunc(func='sin', expr=Float(raw='0.5'))),
                                InitialAssignment(name='cos_val', expr=UFunc(func='cos', expr=Float(raw='0.5'))),
                                InitialAssignment(name='tan_val', expr=UFunc(func='tan', expr=Float(raw='0.5'))),
                                InitialAssignment(name='asin_val', expr=UFunc(func='asin', expr=Float(raw='0.5'))),
                                InitialAssignment(name='acos_val', expr=UFunc(func='acos', expr=Float(raw='0.5'))),
                                InitialAssignment(name='atan_val', expr=UFunc(func='atan', expr=Float(raw='0.5'))),
                                InitialAssignment(name='sinh_val', expr=UFunc(func='sinh', expr=Float(raw='0.5'))),
                                InitialAssignment(name='cosh_val', expr=UFunc(func='cosh', expr=Float(raw='0.5'))),
                                InitialAssignment(name='tanh_val', expr=UFunc(func='tanh', expr=Float(raw='0.5'))),
                                InitialAssignment(name='asinh_val', expr=UFunc(func='asinh', expr=Float(raw='0.5'))),
                                InitialAssignment(name='acosh_val', expr=UFunc(func='acosh', expr=Float(raw='1.5'))),
                                InitialAssignment(name='atanh_val', expr=UFunc(func='atanh', expr=Float(raw='0.5'))),
                                InitialAssignment(name='sqrt_val', expr=UFunc(func='sqrt', expr=Integer(raw='4'))),
                                InitialAssignment(name='cbrt_val', expr=UFunc(func='cbrt', expr=Integer(raw='8'))),
                                InitialAssignment(name='exp_val', expr=UFunc(func='exp', expr=Integer(raw='1'))),
                                InitialAssignment(name='log_val', expr=UFunc(func='log', expr=Integer(raw='10'))),
                                InitialAssignment(name='log10_val', expr=UFunc(func='log10', expr=Integer(raw='100'))),
                                InitialAssignment(name='log2_val', expr=UFunc(func='log2', expr=Integer(raw='8'))),
                                InitialAssignment(name='log1p_val', expr=UFunc(func='log1p', expr=Integer(raw='1'))),
                                InitialAssignment(name='abs_val',
                                                  expr=UFunc(func='abs', expr=UnaryOp(op='-', expr=Integer(raw='5')))),
                                InitialAssignment(name='ceil_val', expr=UFunc(func='ceil', expr=Float(raw='4.3'))),
                                InitialAssignment(name='floor_val', expr=UFunc(func='floor', expr=Float(raw='4.7'))),
                                InitialAssignment(name='round_val', expr=UFunc(func='round', expr=Float(raw='4.5'))),
                                InitialAssignment(name='trunc_val', expr=UFunc(func='trunc', expr=Float(raw='4.9'))),
                                InitialAssignment(name='sign_val',
                                                  expr=UFunc(func='sign',
                                                             expr=UnaryOp(op='-', expr=Integer(raw='10'))))])),
        ('bool_true := 1;\nbool_false := 0;\n', Preamble(
            stats=[InitialAssignment(name='bool_true', expr=Integer(raw='1')),
                   InitialAssignment(name='bool_false', expr=Integer(raw='0'))])),
        ('priority1 := 1 + 2 * 3;\npriority2 := 1 * 2 + 3;\n', Preamble(stats=[InitialAssignment(name='priority1',
                                                                                                 expr=BinaryOp(
                                                                                                     expr1=Integer(
                                                                                                         raw='1'),
                                                                                                     op='+',
                                                                                                     expr2=BinaryOp(
                                                                                                         expr1=Integer(
                                                                                                             raw='2'),
                                                                                                         op='*',
                                                                                                         expr2=Integer(
                                                                                                             raw='3')))),
                                                                               InitialAssignment(name='priority2',
                                                                                                 expr=BinaryOp(
                                                                                                     expr1=BinaryOp(
                                                                                                         expr1=Integer(
                                                                                                             raw='1'),
                                                                                                         op='*',
                                                                                                         expr2=Integer(
                                                                                                             raw='2')),
                                                                                                     op='+',
                                                                                                     expr2=Integer(
                                                                                                         raw='3')))])),
        ('priority3 := 2 * 3 ** 2;\npriority4 := 2 ** 3 * 2;\n', Preamble(stats=[InitialAssignment(name='priority3',
                                                                                                   expr=BinaryOp(
                                                                                                       expr1=Integer(
                                                                                                           raw='2'),
                                                                                                       op='*',
                                                                                                       expr2=BinaryOp(
                                                                                                           expr1=Integer(
                                                                                                               raw='3'),
                                                                                                           op='**',
                                                                                                           expr2=Integer(
                                                                                                               raw='2')))),
                                                                                 InitialAssignment(name='priority4',
                                                                                                   expr=BinaryOp(
                                                                                                       expr1=BinaryOp(
                                                                                                           expr1=Integer(
                                                                                                               raw='2'),
                                                                                                           op='**',
                                                                                                           expr2=Integer(
                                                                                                               raw='3')),
                                                                                                       op='*',
                                                                                                       expr2=Integer(
                                                                                                           raw='2')))])),
        ('priority5 := -2 * 3;\npriority6 := 2 * -3;\n', Preamble(stats=[InitialAssignment(name='priority5',
                                                                                           expr=BinaryOp(
                                                                                               expr1=UnaryOp(op='-',
                                                                                                             expr=Integer(
                                                                                                                 raw='2')),
                                                                                               op='*',
                                                                                               expr2=Integer(raw='3'))),
                                                                         InitialAssignment(name='priority6',
                                                                                           expr=BinaryOp(
                                                                                               expr1=Integer(raw='2'),
                                                                                               op='*',
                                                                                               expr2=UnaryOp(op='-',
                                                                                                             expr=Integer(
                                                                                                                 raw='3'))))])),
        ('right_assoc1 := 2 ** 3 ** 4;\nright_assoc2 := 2 ** (3 ** 4);\n', Preamble(stats=[
            InitialAssignment(name='right_assoc1', expr=BinaryOp(expr1=Integer(raw='2'), op='**',
                                                                 expr2=BinaryOp(expr1=Integer(raw='3'), op='**',
                                                                                expr2=Integer(raw='4')))),
            InitialAssignment(name='right_assoc2', expr=BinaryOp(expr1=Integer(raw='2'), op='**', expr2=Paren(
                expr=BinaryOp(expr1=Integer(raw='3'), op='**', expr2=Integer(raw='4')))))])),
        ('left_assoc1 := 10 - 5 - 3;\nleft_assoc2 := (10 - 5) - 3;\n', Preamble(stats=[
            InitialAssignment(name='left_assoc1',
                              expr=BinaryOp(expr1=BinaryOp(expr1=Integer(raw='10'), op='-', expr2=Integer(raw='5')),
                                            op='-', expr2=Integer(raw='3'))), InitialAssignment(name='left_assoc2',
                                                                                                expr=BinaryOp(
                                                                                                    expr1=Paren(
                                                                                                        expr=BinaryOp(
                                                                                                            expr1=Integer(
                                                                                                                raw='10'),
                                                                                                            op='-',
                                                                                                            expr2=Integer(
                                                                                                                raw='5'))),
                                                                                                    op='-',
                                                                                                    expr2=Integer(
                                                                                                        raw='3')))])),
        ('extreme_nest := ((((1 + 2) * 3) - 4) / 5) ** 6;\n', Preamble(stats=[InitialAssignment(name='extreme_nest',
                                                                                                expr=BinaryOp(
                                                                                                    expr1=Paren(
                                                                                                        expr=BinaryOp(
                                                                                                            expr1=Paren(
                                                                                                                expr=BinaryOp(
                                                                                                                    expr1=Paren(
                                                                                                                        expr=BinaryOp(
                                                                                                                            expr1=Paren(
                                                                                                                                expr=BinaryOp(
                                                                                                                                    expr1=Integer(
                                                                                                                                        raw='1'),
                                                                                                                                    op='+',
                                                                                                                                    expr2=Integer(
                                                                                                                                        raw='2'))),
                                                                                                                            op='*',
                                                                                                                            expr2=Integer(
                                                                                                                                raw='3'))),
                                                                                                                    op='-',
                                                                                                                    expr2=Integer(
                                                                                                                        raw='4'))),
                                                                                                            op='/',
                                                                                                            expr2=Integer(
                                                                                                                raw='5'))),
                                                                                                    op='**',
                                                                                                    expr2=Integer(
                                                                                                        raw='6')))])),
        ('a_1 := 10;\n_b2 := 20;\nVAR_NAME := 30;\n', Preamble(
            stats=[InitialAssignment(name='a_1', expr=Integer(raw='10')),
                   InitialAssignment(name='_b2', expr=Integer(raw='20')),
                   InitialAssignment(name='VAR_NAME', expr=Integer(raw='30'))])),
        ('float1 := 0.123;\nfloat2 := .123;\nfloat3 := 123.;\nfloat4 := 1e10;\nfloat5 := 1.5e-5;\n', Preamble(
            stats=[InitialAssignment(name='float1', expr=Float(raw='0.123')),
                   InitialAssignment(name='float2', expr=Float(raw='.123')),
                   InitialAssignment(name='float3', expr=Float(raw='123.')),
                   InitialAssignment(name='float4', expr=Float(raw='1e10')),
                   InitialAssignment(name='float5', expr=Float(raw='1.5e-5'))])),
        ('', Preamble(stats=[])),
    ])
    def test_positive_cases(self, input_text, expected):
        assert parse_preamble(input_text) == expected

    @pytest.mark.parametrize(['input_text', 'expected_str'], [
        ('x := 10;\ny = 20;', 'x := 10;\ny = 20;'),
        ('pi_val := pi;\ne_val := E;\ntau_val := tau;', 'pi_val := pi;\ne_val := E;\ntau_val := tau;'),
        ('int_var := 42;\nfloat_var := 3.14;\nsci_var := 1.23e-4;\n',
         'int_var := 42;\nfloat_var := 3.14;\nsci_var := 1.23e-4;'),
        ('pos_var := +10;\nneg_var := -20;\n', 'pos_var := +10;\nneg_var := -20;'),
        ('add_var := 5 + 3;\nsub_var := 10 - 7;\nmult_var := 4 * 6;\ndiv_var := 20 / 5;\nmod_var := 7 % 3;',
         'add_var := 5 + 3;\nsub_var := 10 - 7;\nmult_var := 4 * 6;\ndiv_var := 20 / 5;\nmod_var := 7 % 3;'),
        ('shift_left := 1 << 3;\nshift_right := 16 >> 2;\nbit_and := 7 & 3;\nbit_or := 4 | 2;\nbit_xor := 7 ^ 3;',
         'shift_left := 1 << 3;\nshift_right := 16 >> 2;\nbit_and := 7 & 3;\nbit_or := 4 | 2;\nbit_xor := 7 ^ 3;'),
        ('power_var := 2 ** 3;\npower_chain := 2 ** 3 ** 2;\n', 'power_var := 2 ** 3;\npower_chain := 2 ** 3 ** 2;'),
        ('sin_val := sin(0.5);\ncos_val := cos(pi);\nsqrt_val := sqrt(16);\nlog_val := log(10);\n',
         'sin_val := sin(0.5);\ncos_val := cos(pi);\nsqrt_val := sqrt(16);\nlog_val := log(10);'),
        ('complex_expr1 := 2 + 3 * 4;\ncomplex_expr2 := (2 + 3) * 4;\n',
         'complex_expr1 := 2 + 3 * 4;\ncomplex_expr2 := (2 + 3) * 4;'),
        ('nested_expr := 2 * (3 + 4 * (5 - 2)) / 3;\n', 'nested_expr := 2 * (3 + 4 * (5 - 2)) / 3;'),
        ('mixed_ops := 3 + 4 * 2 / (1 - 5) ** 2 ** 3;\n', 'mixed_ops := 3 + 4 * 2 / (1 - 5) ** 2 ** 3;'),
        ('func_nest := sin(cos(pi/4) + sqrt(2));\n', 'func_nest := sin(cos(pi / 4) + sqrt(2));'),
        ('bit_mix := (1 << 4) | (3 & 7) ^ (10 >> 1);\n', 'bit_mix := (1 << 4) | (3 & 7) ^ (10 >> 1);'),
        (
                '\n    sin_val := sin(0.5);\n    cos_val := cos(0.5);\n    tan_val := tan(0.5);\n    asin_val := asin(0.5);\n    acos_val := acos(0.5);\n    atan_val := atan(0.5);\n    sinh_val := sinh(0.5);\n    cosh_val := cosh(0.5);\n    tanh_val := tanh(0.5);\n    asinh_val := asinh(0.5);\n    acosh_val := acosh(1.5);\n    atanh_val := atanh(0.5);\n    sqrt_val := sqrt(4);\n    cbrt_val := cbrt(8);\n    exp_val := exp(1);\n    log_val := log(10);\n    log10_val := log10(100);\n    log2_val := log2(8);\n    log1p_val := log1p(1);\n    abs_val := abs(-5);\n    ceil_val := ceil(4.3);\n    floor_val := floor(4.7);\n    round_val := round(4.5);\n    trunc_val := trunc(4.9);\n    sign_val := sign(-10);\n    ',
                'sin_val := sin(0.5);\ncos_val := cos(0.5);\ntan_val := tan(0.5);\nasin_val := asin(0.5);\nacos_val := acos(0.5);\natan_val := atan(0.5);\nsinh_val := sinh(0.5);\ncosh_val := cosh(0.5);\ntanh_val := tanh(0.5);\nasinh_val := asinh(0.5);\nacosh_val := acosh(1.5);\natanh_val := atanh(0.5);\nsqrt_val := sqrt(4);\ncbrt_val := cbrt(8);\nexp_val := exp(1);\nlog_val := log(10);\nlog10_val := log10(100);\nlog2_val := log2(8);\nlog1p_val := log1p(1);\nabs_val := abs(-5);\nceil_val := ceil(4.3);\nfloor_val := floor(4.7);\nround_val := round(4.5);\ntrunc_val := trunc(4.9);\nsign_val := sign(-10);'),
        ('bool_true := 1;\nbool_false := 0;\n', 'bool_true := 1;\nbool_false := 0;'),
        ('priority1 := 1 + 2 * 3;\npriority2 := 1 * 2 + 3;\n', 'priority1 := 1 + 2 * 3;\npriority2 := 1 * 2 + 3;'),
        ('priority3 := 2 * 3 ** 2;\npriority4 := 2 ** 3 * 2;\n', 'priority3 := 2 * 3 ** 2;\npriority4 := 2 ** 3 * 2;'),
        ('priority5 := -2 * 3;\npriority6 := 2 * -3;\n', 'priority5 := -2 * 3;\npriority6 := 2 * -3;'),
        ('right_assoc1 := 2 ** 3 ** 4;\nright_assoc2 := 2 ** (3 ** 4);\n',
         'right_assoc1 := 2 ** 3 ** 4;\nright_assoc2 := 2 ** (3 ** 4);'),
        ('left_assoc1 := 10 - 5 - 3;\nleft_assoc2 := (10 - 5) - 3;\n',
         'left_assoc1 := 10 - 5 - 3;\nleft_assoc2 := (10 - 5) - 3;'),
        ('extreme_nest := ((((1 + 2) * 3) - 4) / 5) ** 6;\n', 'extreme_nest := ((((1 + 2) * 3) - 4) / 5) ** 6;'),
        ('a_1 := 10;\n_b2 := 20;\nVAR_NAME := 30;\n', 'a_1 := 10;\n_b2 := 20;\nVAR_NAME := 30;'),
        ('float1 := 0.123;\nfloat2 := .123;\nfloat3 := 123.;\nfloat4 := 1e10;\nfloat5 := 1.5e-5;\n',
         'float1 := 0.123;\nfloat2 := .123;\nfloat3 := 123.;\nfloat4 := 1e10;\nfloat5 := 1.5e-5;'),
        ('', ''),
    ])
    def test_positive_cases_str(self, input_text, expected_str, text_aligner):
        text_aligner.assert_equal(
            expected_str,
            str(parse_preamble(input_text)),
        )

    @pytest.mark.parametrize(['input_text'], [
        ('x := 10\ny := 20',),
        ('x = 10;\ny == 20;',),
        ('x := ;',),
        ('x := (1 + 2 * 3;',),
        ('x := 1 + 2) * 3;',),
        ('x := 1 +/ 2;',),
        ('x := sin();',),
        ('x := sin(1, 2);',),
        ('x := sinn(1);',),
        ('x := 1 + ;',),
        ('x := * 2;',),
        ('x := -;',),
        ('x := 1 < 2;',),
        ('x := true && false;',),
        ('x := if 1 > 0 then 1 else 0;',),
        ('1var := 10;',),
        ('var-name := 10;',),
        ('x := 1.2.3;',),
        ('x := 1e;',),
        ('x := PI;',),
        ('x := Pi;',),
        ('x := sin 1;',),
        ('x := 1 +;',),
        ('x := 1 2 + 3;',),
        ('x := ((1 + 2) * 3;',),
        ('x := 1 */ 2;',),
        ('if x > 0 { y := 1; }',),
        ('x := 1 ? 2;',),
        ('x := true;',),
        ('x := 1.0e+;',),
        ('sin := 1;',),
        ('pi := 3.14;',),
        ('x := 0x10;',),
        ('x := 10;\ny := x + 5;',),
        ('a := 10;\nb = 20;\nc := a + b;\nd = c * 2;\n',),
    ])
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_preamble(input_text)

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f'Found {len(err.errors)} errors during parsing:' in err.args[0]
