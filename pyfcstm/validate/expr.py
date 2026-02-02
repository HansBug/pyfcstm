from typing import Dict, List

from z3 import ExprRef, IntVal, RealVal, BoolVal, Not, And, Or, If, simplify, Then, Goal

from ..model import Expr, Integer, Float, Boolean, Variable, UnaryOp, BinaryOp, ConditionalOp, UFunc, Operation

_Z3_OP_FUNCTIONS = {
    # Unary operators
    "unary+": lambda x: x,  # Z3中正号就是原值
    "unary-": lambda x: -x,  # Z3支持负号
    "!": lambda x: Not(x),  # 逻辑非
    "not": lambda x: Not(x),  # 逻辑非

    # Binary operators
    "**": lambda x, y: x ** y,  # 幂运算
    "*": lambda x, y: x * y,  # 乘法
    "/": lambda x, y: x / y,  # 除法
    "%": lambda x, y: x % y,  # 取模（仅整数）
    "+": lambda x, y: x + y,  # 加法
    "-": lambda x, y: x - y,  # 减法
    "<<": lambda x, y: x << y,  # 左移（仅整数）
    ">>": lambda x, y: x >> y,  # 右移（仅整数）
    "&": lambda x, y: x & y,  # 按位与（仅整数）
    "^": lambda x, y: x ^ y,  # 按位异或（仅整数）
    "|": lambda x, y: x | y,  # 按位或（仅整数）
    "<": lambda x, y: x < y,  # 小于
    ">": lambda x, y: x > y,  # 大于
    "<=": lambda x, y: x <= y,  # 小于等于
    ">=": lambda x, y: x >= y,  # 大于等于
    "==": lambda x, y: x == y,  # 等于
    "!=": lambda x, y: x != y,  # 不等于
    "&&": lambda x, y: And(x, y),  # 逻辑与
    "and": lambda x, y: And(x, y),  # 逻辑与
    "||": lambda x, y: Or(x, y),  # 逻辑或
    "or": lambda x, y: Or(x, y),  # 逻辑或

    # Ternary operator
    "?:": lambda condition, true_value, false_value: If(condition, true_value, false_value)
}

_Z3_MATH_FUNCTIONS = {
    'abs': lambda x: If(x >= 0, x, -x),
    'sqrt': lambda x: x ** (RealVal(1) / RealVal(2)),
    'cbrt': lambda x: x ** (RealVal(1) / RealVal(3)),
    'sign': lambda x: If(x > 0, 1, If(x < 0, -1, 0)),
}


def _raw_model_expr_to_z3_expr(expr: Expr, variables: Dict[str, ExprRef]):
    if isinstance(expr, Integer):
        return IntVal(expr.value)
    elif isinstance(expr, Float):
        return RealVal(expr.value)
    elif isinstance(expr, Boolean):
        return BoolVal(expr.value)
    elif isinstance(expr, Variable):
        return variables[expr.name]
    elif isinstance(expr, UnaryOp):
        x = _raw_model_expr_to_z3_expr(expr.x, variables)
        return _Z3_OP_FUNCTIONS[expr.op_mark](x)
    elif isinstance(expr, BinaryOp):
        x = _raw_model_expr_to_z3_expr(expr.x, variables)
        y = _raw_model_expr_to_z3_expr(expr.y, variables)
        return _Z3_OP_FUNCTIONS[expr.op_mark](x, y)
    elif isinstance(expr, ConditionalOp):
        cond = _raw_model_expr_to_z3_expr(expr.cond, variables)
        if_true = _raw_model_expr_to_z3_expr(expr.if_true, variables)
        if_false = _raw_model_expr_to_z3_expr(expr.if_false, variables)
        return _Z3_OP_FUNCTIONS[expr.op_mark](cond, if_true, if_false)
    elif isinstance(expr, UFunc):
        if expr.func in _Z3_MATH_FUNCTIONS:
            x = _raw_model_expr_to_z3_expr(expr.x, variables)
            return _Z3_MATH_FUNCTIONS[expr.func](x)
        else:
            raise ValueError(f'Unsupported math functions for z3 solver - {expr.to_ast_node()}')
    else:
        raise TypeError(f'Unknown fcstm DSL expression type - {expr!r}')


def model_expr_to_z3_expr(x: Expr, variables: Dict[str, ExprRef]):
    return _raw_model_expr_to_z3_expr(
        expr=x,
        variables=variables,
    )


def operations_to_z3_vars(operations: List[Operation], variables: Dict[str, ExprRef]) -> Dict[str, ExprRef]:
    variables = dict(variables)
    for ef in operations:
        variables[ef.var_name] = model_expr_to_z3_expr(ef.expr, variables)
    return variables


def to_z3_expr(x):
    if isinstance(x, ExprRef):
        return x
    elif isinstance(x, int):
        return IntVal(x)
    elif isinstance(x, float):
        return RealVal(x)
    elif isinstance(x, bool):
        return BoolVal(x)
    else:
        raise TypeError(f'Unknown value type - {x!r}')


def comprehensive_simplify(expr):
    """综合化简方案"""

    # 第1步：基本化简
    result = simplify(expr, algebraic=True)

    # 第2步：使用高级策略
    tactics = Then('simplify', 'ctx-simplify', 'propagate-values', 'solve-eqs')
    goal = Goal()
    goal.add(result)
    try:
        simplified_goals = tactics(goal)
        if len(simplified_goals[0]) > 0:
            result = And(*simplified_goals[0]) if len(simplified_goals[0]) > 1 else simplified_goals[0][0]
    except:
        pass

    # # 第3步：模式匹配化简
    # result = pattern_based_simplify(result)
    #
    # # 第4步：如果提供了变量，进行区间分析
    # if variables:
    #     for var in variables:
    #         result = interval_based_simplify(result, var)

    # 第5步：最终化简
    result = simplify(result, algebraic=True)

    return result
