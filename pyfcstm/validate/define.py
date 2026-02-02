from typing import Dict, Type, Union

from z3 import Ints, Reals

try:
    from typing import Literal
except (ImportError, ModuleNotFoundError):
    from typing_extensions import Literal

NumTyping = Union[Literal['int', 'float'], Type[int], Type[float]]


def def_numbers(nums: Dict[str, NumTyping]):
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


