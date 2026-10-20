"""Family-specific evidence text; no proof search or native solver dependency."""

from dataclasses import dataclass, replace
from fractions import Fraction
from typing import Callable, Mapping, Optional

from .core import ProofGraph


@dataclass(frozen=True)
class EvidenceTextContext:
    """Shared formula formatting and language choices for one reading."""

    graph: ProofGraph
    terms: Mapping[str, str]
    choose: Callable
    detail: str
    references: Optional[object]


def _linear_text(bound, terms):
    parts = []
    for term_id, value in bound.coefficients:
        coefficient = Fraction(value)
        parts.append(terms[term_id] if coefficient == 1 else '%s * %s' % (value, terms[term_id]))
    if Fraction(bound.constant) or not parts:
        parts.append(bound.constant)
    relation = {'le': '<=', 'lt': '<', 'eq': '='}[bound.relation]
    return '%s %s 0' % (' + '.join(parts), relation)


def _polynomial_text(coefficients, terms):
    parts = []
    for monomial, coefficient in coefficients:
        factors = [terms[key] for key in monomial]
        if Fraction(coefficient) != 1 or not factors:
            factors.insert(0, coefficient)
        parts.append(' * '.join(factors))
    return ' + '.join(parts) or '0'


def render_arithmetic(certificate, node, context):
    """Render arithmetic evidence using the shared reading context."""
    graph = context.graph
    terms = context.terms
    choose = context.choose
    detail = context.detail
    references = context.references
    lines = []
    temporary = tuple(bound for bound in certificate.bounds if bound.negated)
    if temporary:
        lines.append('  ' + choose('To refute the negated conclusion, temporarily assume:',
                                  '为反驳结论的否定，暂时假设：'))
        assumptions = []
        for bound in temporary:
            literal = graph.term(bound.term_id)
            assumption = (terms[literal.arguments[0]] if literal.operator == 'not'
                          else 'not (%s)' % terms[bound.term_id])
            assumptions.append(assumption)
        if detail == 'standard' and len(assumptions) > 16:
            lines.append('    ' + references.join(assumptions, ' and ', True))
        elif detail == 'brief' and len(assumptions) > 16:
            lines.append('    not (%s)' % terms[node.conclusion])
        else:
            lines.extend('    ' + assumption for assumption in assumptions)
    relation = '<' if certificate.strict else '<='
    if detail == 'brief':
        lines.append('  ' + choose('Combination: %d inequalities; sum ', '组合 %d 条不等式；相加得到 ') %
                     len(certificate.bounds) + '%s %s 0; ' % (certificate.constant, relation) +
                     choose('contradiction.', '矛盾。'))
    else:
        weighted = tuple('%s * [%s]' % (weight, _linear_text(bound, terms))
                         for bound, weight in zip(certificate.bounds, certificate.weights))
        if detail == 'standard' and len(weighted) > 16:
            lines.append('  ' + choose('Combination: ', '组合：') + references.join(weighted, ' + '))
        else:
            lines.extend('  ' + item for item in weighted)
        lines.append('  ' + choose('Sum: ', '相加得到：') + '%s %s 0; ' % (certificate.constant, relation) +
                     choose('contradiction.', '矛盾。'))
    if temporary:
        lines.append('  ' + choose('Discharge these temporary assumptions.', '关闭上述临时假设。'))
    return lines


def render_linear_equality(certificate, node, context):
    """Render linear equality evidence using the shared reading context."""
    graph = context.graph
    terms = context.terms
    choose = context.choose
    detail = context.detail
    lines = []
    equality = certificate
    left, right = graph.term(equality.term_id).arguments
    for first, second, certificate in ((left, right, equality.less), (right, left, equality.greater)):
        lines.append('  ' + choose('Temporarily assume: ', '暂时假设：') + '%s < %s' %
                     (terms[first], terms[second]))
        if detail != 'brief':
            for bound, weight in zip(certificate.bounds, certificate.weights):
                lines.append('    %s * [%s]' % (weight, _linear_text(bound, terms)))
        lines.append('    ' + choose('Sum: ', '相加得到：') + '%s %s 0; ' %
                     (certificate.constant, '<' if certificate.strict else '<=') +
                     choose('contradiction.', '矛盾。'))
    lines.append('  ' + choose('Both strict alternatives are impossible, so the values are equal.',
                              '两个严格大小关系均不可能成立，因此两侧相等。'))
    return lines


def render_polynomial(certificate, node, context):
    """Render polynomial evidence using the shared reading context."""
    terms = context.terms
    choose = context.choose
    detail = context.detail
    lines = []
    steps = certificate.steps
    if detail == 'brief':
        lines.append('  ' + choose('%d checked polynomial steps establish a contradiction.',
                                  '%d 个已检查的多项式步骤推出矛盾。') % len(steps))
    else:
        for index, step in enumerate(steps):
            if step.rule == 'input':
                literal = terms[step.term_id]
                if step.negated:
                    literal = 'not (%s)' % literal
                reason = choose('Normalize local premise: ', '归一化局部前提：') + literal
            elif step.rule == 'square':
                reason = choose('Square is nonnegative: ', '平方非负：') + '(%s)^2' % _polynomial_text(step.factor, terms)
            elif step.rule == 'square_zero':
                reason = choose('A square bounded above by zero has a zero factor: ', '平方不大于零，其因子必为零：') + 'Q%d' % (step.premises[0] + 1)
            elif step.rule == 'cancel_positive':
                reason = choose('Cancel the strictly positive factor: ', '消去严格正因子：') + 'Q%d / Q%d' % tuple(
                    parent + 1 for parent in step.premises)
            elif step.rule == 'positive_factor':
                reason = choose('A nonnegative factor of a nonzero product is positive: ',
                                '非零乘积中的非负因子必为正：') + ', '.join(
                    'Q%d' % (parent + 1) for parent in step.premises) + choose(
                    '; cofactor: ', '；其余因子：') + _polynomial_text(step.factor, terms)
            elif step.rule == 'power_sign':
                reason = choose('Power sign from base domain: ', '由底数定义域推导幂的符号：') + terms[step.term_id] + '; ' + ', '.join(
                    'Q%d' % (parent + 1) for parent in step.premises)
            elif step.rule == 'power_identity':
                reason = choose('Rational power identity from base domain: ', '由底数定义域推导有理数幂恒等式：') + terms[step.term_id] + '; ' + ', '.join(
                    'Q%d' % (parent + 1) for parent in step.premises)
            elif step.rule == 'equality_product':
                reason = choose('Multiply the established equality by ', '已证明的等式乘以 ') + _polynomial_text(step.factor, terms) + '; ' + ', '.join(
                    'Q%d' % (parent + 1) for parent in step.premises)
            elif step.rule == 'integer_round':
                reason = choose('Strengthen using the proved value lattice: ',
                                '按已证明的离散取值收紧：') + 'Q%d' % (step.premises[0] + 1)
            elif step.rule == 'product':
                reason = choose('Multiply nonnegative factors: ', '非负因子相乘：') + ' * '.join(
                    'Q%d' % (parent + 1) for parent in step.premises)
            else:
                reason = choose('Nonnegative linear combination: ', '非负线性组合：') + ' + '.join(
                    '%s * Q%d' % (weight, parent + 1) for parent, weight in zip(step.premises, step.weights))
            lines.append('  Q%d: %s %s 0' % (index + 1, _polynomial_text(step.coefficients, terms),
                                            '>' if step.strict else '>='))
            lines.append('    ' + reason)
        lines.append('  ' + choose('The final constant cannot have this sign; contradiction.',
                                  '最后得到的常数不可能满足该符号条件，矛盾。'))
    return lines


def render_divisibility(certificate, node, context):
    """Render divisibility evidence using the shared reading context."""
    terms = context.terms
    choose = context.choose
    lines = []
    for index, ((first, second), weight) in enumerate(zip(certificate.bound_pairs, certificate.weights)):
        lines.append('  B%d: %s; B%d: %s' % (2 * index + 1, _linear_text(first, terms),
                                           2 * index + 2, _linear_text(second, terms)))
        if Fraction(first.constant) == -Fraction(second.constant):
            lines.append('  E%d: %s' % (index + 1, _linear_text(replace(first, relation='eq'), terms)))
            lines.append('    ' + choose('Equation multiplier: ', '等式乘数：') + weight)
        else:
            lines.append('    ' + choose('Range multiplier: ', '区间乘数：') + weight)
    from .core import LinearBound
    if certificate.lower == certificate.upper:
        equation = LinearBound('', False, certificate.coefficients, str(-Fraction(certificate.lower)), 'eq')
        lines.append('  ' + choose('Sum: ', '相加得到：') + _linear_text(equation, terms))
        lines.append('  ' + choose('The variable sum is an integer; it cannot equal ',
                                  '变量的整系数和为整数，不可能等于 ') + certificate.lower + '.')
    else:
        lower = LinearBound('', False, tuple((key, str(-Fraction(v))) for key, v in certificate.coefficients),
                            certificate.lower, 'le')
        upper = LinearBound('', False, certificate.coefficients, str(-Fraction(certificate.upper)), 'le')
        lines.append('  ' + choose('Combined lower bound: ', '组合下界：') + _linear_text(lower, terms))
        lines.append('  ' + choose('Combined upper bound: ', '组合上界：') + _linear_text(upper, terms))
        lines.append('  ' + choose('The variable sum is an integer, but the closed interval ',
                                  '变量的整系数和为整数，但闭区间 ') +
                     '[%s, %s]' % (certificate.lower, certificate.upper) +
                     choose(' contains no integer; contradiction.', ' 内没有整数，矛盾。'))
    return lines


def render_interval(certificate, node, context):
    """Render interval evidence using the shared reading context."""
    graph = context.graph
    terms = context.terms
    choose = context.choose
    lines = []
    interval_rules = {
        'congruence_sum': choose('substitute equal terms and cancel opposite coefficients',
                                 '替换相等项并消去相反系数'),
        'congruence': choose('substitute equal terms in the source expression', '在原表达式中替换相等项'),
        'literal': choose('exact constant', '精确常量'),
        'linear': choose('isolate the term', '移项求界'),
        'intersection': choose('intersect ranges', '区间求交'),
        'square': choose('square the same value', '同一数值的平方'),
        'product': choose('multiply operand ranges', '操作数区间相乘'),
        'product_inverse': choose('divide the product range by a factor range that excludes zero',
                                  '用乘积区间除以不含零的因子区间'),
        'power': choose('apply the known positive integer exponent', '使用已确定的正整数指数'),
        'sum': choose('add/subtract operand ranges', '操作数区间加减'),
        'cast': choose('preserve the integer value as a real', '整数转实数，数值不变'),
        'conditional': choose('select the branch using its condition', '按条件选取分支'),
    }
    for index, bound in enumerate(certificate.bounds):
        lines.append('  B%d: %s' % (index + 1, _linear_text(bound, terms)))
        if bound.negated:
            lines.append('    ' + choose('Temporary negation of a conclusion alternative.',
                                        '临时否定结论中的一个分支。'))
    for index, step in enumerate(certificate.steps):
        for equality in step.substitutions:
            lines.append('    %s = %s; %s' % (
                terms[equality.left_id], terms[equality.right_id],
                ', '.join('B%d' % (bound + 1) for bound in equality.bound_indices)))
        interval = ('(' if step.lower_open else '[') + (step.lower or '-inf') + ', ' + (
            step.upper or '+inf') + (')' if step.upper_open else ']')
        dependencies = ['I%d' % (parent + 1) for parent in step.premises]
        if step.bound_index is not None:
            dependencies.append('B%d' % (step.bound_index + 1))
        description = interval_rules[step.rule]
        if step.rule == 'linear' and graph.term(step.term_id).sort == 'Int':
            description += choose('; round integer bounds inward', '；整数边界向内取整')
        lines.append('  I%d: %s %s %s; %s%s' % (
            index + 1, terms[step.term_id], choose('in', '范围为'), interval, description,
            ('; ' + ', '.join(dependencies)) if dependencies else ''))
    if certificate.conflict is not None:
        lines.append('  ' + choose('Incompatible ranges: ', '不相容的范围：') + ', '.join(
            'I%d' % (index + 1) for index in certificate.conflict) +
                     choose('; contradiction.', '；矛盾。'))
    else:
        lines.append('  ' + choose('Equal singleton ranges: ', '相等的单点范围：') + ', '.join(
            'I%d' % (index + 1) for index in certificate.equality) +
                     choose('; the equality follows.', '；等式成立。'))
    if any(bound.negated for bound in certificate.bounds):
        lines.append('  ' + choose('Discharge these temporary assumptions.', '关闭上述临时假设。'))
    return lines


def render_cardinality(certificate, node, context):
    """Render cardinality evidence using the shared reading context."""
    graph = context.graph
    terms = context.terms
    choose = context.choose
    lines = []
    if certificate.assumptions:
        lines.append('  ' + choose('To refute the negated conclusion, temporarily assume:',
                                  '为反驳结论的否定，暂时假设：'))
        for term_id in certificate.assumptions:
            term = graph.term(term_id)
            text = (terms[term.arguments[0]] if term.operator_kind == 'builtin' and
                    term.operator == 'not' else 'not (%s)' % terms[term_id])
            lines.append('    ' + text)
    for term_id, value in certificate.assignments:
        if term_id != certificate.constraint_id:
            lines.append('  ' + choose('Known: ', '已知：') + '%s = %s' %
                         (terms[term_id], str(value).lower()))
    for item in certificate.contributions:
        lines.append('  ' + choose('Contribution: ', '计数贡献：') +
                     '%s; %s = %d; [%d, %d]' %
                     (terms[item.term_id], choose('weight', '权重'), item.weight,
                      item.minimum, item.maximum))
    lines.append('  ' + choose('Weighted sum range: ', '加权总和范围：') +
                 '[%d, %d]' % (certificate.minimum, certificate.maximum))
    lines.append('  ' + choose('Required: ', '要求：') + '%s = %s' %
                 (terms[certificate.constraint_id], str(certificate.constraint_value).lower()))
    lines.append('  ' + choose('These bounds force the constraint to be ', '上述范围使约束为 ') +
                 str(not certificate.constraint_value).lower() +
                 choose('; contradiction.', '；矛盾。'))
    if certificate.assumptions:
        lines.append('  ' + choose('Discharge these temporary assumptions.', '关闭上述临时假设。'))
    return lines
