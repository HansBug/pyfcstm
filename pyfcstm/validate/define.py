"""
This module provides utilities for defining Z3 symbolic variables for numeric types.

It supports creating integer and real (float) symbolic variables using the Z3 theorem prover,
allowing users to specify variable names and their corresponding numeric types through a dictionary.
The module handles type validation and creates appropriate Z3 variables based on the specified types.
"""

from typing import Dict, Type, Union

from z3 import Ints, Reals

try:
    from typing import Literal
except (ImportError, ModuleNotFoundError):
    from typing_extensions import Literal

NumTyping = Union[Literal['int', 'float'], Type[int], Type[float]]


def def_numbers(nums: Dict[str, NumTyping]):
    """
    Define Z3 symbolic variables for numeric types.

    This function takes a dictionary mapping variable names to their numeric types
    and creates corresponding Z3 symbolic variables. It supports both integer and
    floating-point (real) types, which can be specified either as type literals
    ('int', 'float') or as Python type objects (int, float).

    :param nums: A dictionary mapping variable names to their numeric types.
                 Types can be specified as 'int', 'float', int, or float.
    :type nums: Dict[str, NumTyping]

    :return: A dictionary mapping variable names to their corresponding Z3 symbolic variables.
    :rtype: Dict[str, Union[z3.ArithRef, z3.IntNumRef, z3.RatNumRef]]

    :raises ValueError: If an unsupported number type is specified for any variable.

    Example::
        >>> def_numbers({'a': int, 'b': float})  # Create integer 'a' and real 'b'
        {'a': a, 'b': b}
        
        >>> def_numbers({'x': 'int', 'y': 'float'})  # Using string literals
        {'x': x, 'y': y}
        
        >>> def_numbers({'z': str})  # Invalid type
        ValueError: Unsupported number type for 'z' - <class 'str'>.
    """
    int_names = []
    float_names = []
    for num_name, num_type in nums.items():
        if num_type == 'int' or num_type == int:
            int_names.append(num_name)
        elif num_type == 'float' or num_type == float:
            float_names.append(num_name)
        else:
            raise ValueError(f'Unsupported number type for {num_name!r} - {num_type!r}.')

    retval = {}
    if int_names:
        ints = Ints(' '.join(int_names))
        retval.update({name: v for name, v in zip(int_names, ints)})
    if float_names:
        floats = Reals(' '.join(float_names))
        retval.update({name: v for name, v in zip(float_names, floats)})
    return retval


if __name__ == '__main__':
    print(repr(def_numbers({
        'a': int,
        'b': float,
    })))
