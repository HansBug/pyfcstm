"""Shared ctypes access to the generated C-family role APIs."""

import ctypes

from pyfcstm.dsl.role import VariableRole
from pyfcstm.render.c_runtime import readonly_value_identifier
from pyfcstm.utils import to_c_identifier


def _structure_type(definitions, presence=False):
    fields = [
        (
            (readonly_value_identifier(name) if item.role in (VariableRole.INPUT_DYNAMIC, VariableRole.INPUT_STATIC) else to_c_identifier(name)),
            ctypes.c_int
            if presence
            else ctypes.c_int64
            if item.type == "int"
            else ctypes.c_double,
        )
        for name, item in definitions.items()
    ] or [("_unused_placeholder", ctypes.c_int)]
    return type("NumericValues", (ctypes.Structure,), {"_fields_": fields})


def _values(struct_type, definitions, values, complete=False):
    unknown = set(values) - set(definitions)
    if unknown:
        raise ValueError("Unknown values: %s" % sorted(unknown))
    if complete and set(values) != set(definitions):
        raise ValueError("A complete value snapshot is required")
    result = struct_type()
    for name, value in values.items():
        if type(value) not in (int, float):
            raise ValueError("Value for %s must be numeric and must not be bool" % name)
        if definitions[name].type == "int":
            if value != int(value):
                raise ValueError("Non-integer value for %s" % name)
            value = int(value)
        setattr(result, readonly_value_identifier(name), value)
    return result


class NativeRoleSupport:
    """Use typed snapshots through exported functions, never machine fields."""

    def _initialize_role_io(self):
        self._parameters_struct = _structure_type(self._model.static_inputs)
        self._inputs_struct = _structure_type(self._model.dynamic_inputs)
        self._options_struct = type(
            "InitOptions",
            (ctypes.Structure,),
            {
                "_fields_": [
                    ("vars", self._vars_struct),
                    (
                        "vars_present",
                        _structure_type(self._model.persistent_variables, True),
                    ),
                    ("parameters", self._parameters_struct),
                    (
                        "parameters_present",
                        _structure_type(self._model.static_inputs, True),
                    ),
                ]
            },
        )
        self._init_options = self._bind_function(
            "{prefix}_init_with_options",
            [ctypes.c_void_p, ctypes.c_void_p],
            ctypes.c_int,
        )
        self._hot_parameters = self._bind_function(
            "{prefix}_hot_start_with_parameters",
            [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p],
            ctypes.c_int,
        )
        self._get_last_inputs = self._bind_function(
            "{prefix}_last_inputs",
            [ctypes.c_void_p],
            ctypes.POINTER(self._inputs_struct),
        )
        self._parameter_getters = {
            name: self._bind_function(
                "{prefix}_get_param_" + readonly_value_identifier(name),
                [ctypes.c_void_p],
                ctypes.c_int64 if item.type == "int" else ctypes.c_double,
            )
            for name, item in self._model.static_inputs.items()
        }

    def initialize_with_values(self, initial_vars=None, parameters=None):
        options = self._options_struct()
        initial_vars = {} if initial_vars is None else initial_vars
        parameters = {} if parameters is None else parameters
        options.vars = self._create_initial_vars(initial_vars)
        options.parameters = _values(
            self._parameters_struct, self._model.static_inputs, parameters
        )
        for name in initial_vars:
            setattr(options.vars_present, to_c_identifier(name), 1)
        for name in parameters:
            setattr(options.parameters_present, readonly_value_identifier(name), 1)
        if self._init_options(self._machine, ctypes.byref(options)) != 1:
            self._raise_last_error()

    def _hot_start_with_parameters(self, state_id, values, parameters):
        parameter_values = _values(
            self._parameters_struct,
            self._model.static_inputs,
            {} if parameters is None else parameters,
            complete=True,
        )
        if (
            self._hot_parameters(
                self._machine,
                state_id,
                ctypes.byref(values),
                ctypes.byref(parameter_values),
            )
            != 1
        ):
            self._raise_last_error()

    def _input_values(self, inputs):
        return _values(
            self._inputs_struct, self._model.dynamic_inputs, inputs, complete=True
        )

    @property
    def parameters(self):
        return {
            name: getter(self._machine)
            for name, getter in self._parameter_getters.items()
        }

    @property
    def outputs(self):
        values = self.vars
        return {name: values[name] for name in self._model.output_variables}

    @property
    def last_inputs(self):
        pointer = self._get_last_inputs(self._machine)
        if not pointer:
            return None
        return {
            name: getattr(pointer.contents, readonly_value_identifier(name))
            for name in self._model.dynamic_inputs
        }
