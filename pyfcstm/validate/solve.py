from dataclasses import dataclass
from typing import Union, Dict, Optional

import z3
from z3 import Solver, sat, ExprRef, unsat

try:
    from typing import Literal
except (ImportError, ModuleNotFoundError):
    from typing_extensions import List


@dataclass
class SolveResult:
    type: Literal['sat', 'unsat', 'undetermined']
    values: Optional[Dict[str, Union[int, float]]]


def get_expr_type(expr):
    sort = expr.sort()
    sort_kind = sort.kind()

    if sort_kind == z3.Z3_INT_SORT:
        return "Integer"
    elif sort_kind == z3.Z3_REAL_SORT:
        return "Real"
    elif sort_kind == z3.Z3_BOOL_SORT:
        return "Boolean"
    elif sort_kind == z3.Z3_BV_SORT:
        return f"BitVector({sort.size()})"
    elif sort_kind == z3.Z3_ARRAY_SORT:
        return f"Array({sort.domain()}, {sort.range()})"
    else:
        return f"Unknown({sort})"


def is_concrete_value(expr):
    """
    判断Z3表达式是否为具体值（而非符号变量）
    """
    try:
        # 对于不同类型，使用不同的方法判断是否为具体值
        if z3.is_bool(expr):
            return z3.is_true(expr) or z3.is_false(expr)
        elif z3.is_int(expr):
            # 尝试获取整数值，如果成功说明是具体值
            try:
                expr.as_long()
                return True
            except:
                return False
        elif z3.is_real(expr):
            # 尝试获取实数值
            try:
                if expr.is_int():
                    expr.as_long()
                else:
                    expr.numerator_as_long()
                    expr.denominator_as_long()
                return True
            except:
                return False
        elif z3.is_bv(expr):
            # 尝试获取位向量值
            try:
                expr.as_long()
                return True
            except:
                return False
        elif z3.is_string(expr):
            # 尝试获取字符串值
            try:
                expr.as_string()
                return True
            except:
                return False
        else:
            return False
    except:
        return False


def z3_to_python(expr):
    """
    将Z3 ExprRef转换为Python原生类型

    Args:
        expr: Z3 ExprRef对象

    Returns:
        Python原生类型的值

    Raises:
        TypeError: 当类型不支持转换时
        ValueError: 当值无法转换时
    """

    # 首先检查是否是具体的值（而不是符号变量）
    if not is_concrete_value(expr):
        raise ValueError(
            f"Cannot convert symbolic expression to Python native type.\n"
            f"Expression: {expr}\n"
            f"Type: {expr.sort()}\n"
            f"The expression contains variables or is not a concrete value.\n"
            f"You may need to evaluate this expression in a model first."
        )

    # Boolean类型
    if z3.is_bool(expr):
        if z3.is_true(expr):
            return True
        elif z3.is_false(expr):
            return False
        else:
            raise ValueError(f"Unknown boolean value: {expr}")

        # Integer类型
    elif z3.is_int(expr):
        return expr.as_long()

        # Real类型
    elif z3.is_real(expr):
        # Z3的实数可能是分数形式
        if expr.is_int():
            return float(expr.as_long())
        else:
            # 获取分数的分子和分母
            numerator = expr.numerator_as_long()
            denominator = expr.denominator_as_long()
            return float(numerator) / float(denominator)

        # BitVector类型
    elif z3.is_bv(expr):
        bit_size = expr.sort().size()
        value = expr.as_long()

        # 检查是否为有符号数（如果最高位为1）
        if value >= (1 << (bit_size - 1)):
            # 转换为有符号数
            signed_value = value - (1 << bit_size)
            return {
                'unsigned': value,
                'signed': signed_value,
                'bit_size': bit_size,
                'hex': hex(value),
                'binary': bin(value)
            }
        else:
            return {
                'unsigned': value,
                'signed': value,
                'bit_size': bit_size,
                'hex': hex(value),
                'binary': bin(value)
            }

        # String类型
    elif z3.is_string(expr):
        return expr.as_string()

        # Array类型 - 通常无法直接转换
    elif z3.is_array(expr):
        raise TypeError(
            f"Array types cannot be converted to Python native types.\n"
            f"Expression: {expr}\n"
            f"Sort: {expr.sort()}\n"
            f"Arrays in Z3 are functions and don't have a direct Python equivalent.\n"
            f"Consider extracting specific array elements using model evaluation."
        )

        # 其他不支持的类型
    else:
        sort_kind = expr.sort().kind()
        raise TypeError(
            f"Unsupported Z3 type for conversion to Python native type.\n"
            f"Expression: {expr}\n"
            f"Sort: {expr.sort()}\n"
            f"Sort kind: {sort_kind}\n"
            f"Supported types: Bool, Int, Real, BitVec, String\n"
            f"For custom types, you may need to implement specific conversion logic."
        )


def solve_expr(constraint, variables: Dict[str, ExprRef]):
    solver = Solver()
    solver.push()  # 保存当前状态
    try:
        solver.add(constraint)
        result = solver.check()

        if result == sat:
            model = solver.model()
            values = {}
            for name, v in variables.items():
                val = model[v]
                if val is not None:
                    values[name] = z3_to_python(val)
                else:
                    values[name] = val

            return SolveResult(
                type='sat',
                values=values
            )
        elif result == unsat:
            return SolveResult(type='unsat', values=None)
        else:
            return SolveResult(type='undetermined', values=None)

    finally:
        solver.pop()  # 恢复状态
