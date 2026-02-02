from typing import Dict, Union

import z3

from .solve import z3_to_python


def z3_evaluate(expr: z3.ExprRef, variables: Dict[str, z3.ExprRef], values: Dict[str, Union[int, float, None]]):
    values = {key: (value if value is not None else 0) for key, value in values.items()}
    solver = z3.Solver()
    for name in variables.keys():
        solver.add(variables[name] == values[name])

    assert solver.check() == z3.sat
    model = solver.model()
    return z3_to_python(model.evaluate(expr))
