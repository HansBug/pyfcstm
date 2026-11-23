"""Shared ctypes access to the generated C-family role APIs."""

import ctypes
from types import SimpleNamespace

from pyfcstm.dsl.role import VariableRole
from pyfcstm.model.configuration import Configuration
from pyfcstm.model.model import ModelLookupError, ModelValueError
from pyfcstm.model.region import Region, walk_namespaces
from pyfcstm.render.c_runtime import readonly_value_identifier
from pyfcstm.utils import to_c_identifier


def _structure_type(definitions, presence=False):
    fields = [
        (
            (readonly_value_identifier(name) if item.role in (VariableRole.INPUT, VariableRole.PARAM) else to_c_identifier(name)),
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


class SimulationRuntimeEventError(ValueError):
    """Event input of a cycle that names no event, or more than one."""


def namespace_action_groups(scope):
    """
    Group the lifecycle actions a state or a region declares, in id order.

    :param scope: A state or a region of the model.
    :type scope: Union[pyfcstm.model.model.State, pyfcstm.model.region.Region]
    :return: Lists of ``(id, item)`` pairs; a region declares only aspect actions.
    :rtype: list
    """
    if isinstance(scope, Region):
        return [
            scope.list_on_during_aspects(aspect="before", with_ids=True),
            scope.list_on_during_aspects(aspect="after", with_ids=True),
        ]
    return [
        scope.list_on_enters(with_ids=True),
        scope.list_on_durings(aspect=None, with_ids=True),
        scope.list_on_exits(with_ids=True),
        scope.list_on_durings(aspect="before", with_ids=True),
        scope.list_on_durings(aspect="after", with_ids=True),
        scope.list_on_during_aspects(aspect="before", with_ids=True),
        scope.list_on_during_aspects(aspect="after", with_ids=True),
    ]


def event_paths_in_id_order(model):
    """
    List the events of a model in the order the generated runtime numbers them.

    :param model: State machine under test.
    :type model: pyfcstm.model.model.StateMachine
    :return: Dotted event paths; the position is the event id.
    :rtype: list
    """
    return [
        event.path_name
        for scope in walk_namespaces(model.root_state)
        for event in scope.events.values()
    ]


# Byte size of the message buffer in ``..._ConfigurationError``; the generated
# header names it ``..._CONFIGURATION_ERROR_MESSAGE_SIZE``.
_CONFIGURATION_MESSAGE_SIZE = 160


class NativeRoleSupport:
    """Use typed snapshots through exported functions, never machine fields."""

    def _initialize_role_io(self):
        self._parameters_struct = _structure_type(self._model.parameters)
        self._inputs_struct = _structure_type(self._model.inputs)
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
                        _structure_type(self._model.parameters, True),
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
            for name, item in self._model.parameters.items()
        }

    def initialize_with_values(self, initial_vars=None, parameters=None):
        options = self._options_struct()
        initial_vars = {} if initial_vars is None else initial_vars
        parameters = {} if parameters is None else parameters
        options.vars = self._create_initial_vars(initial_vars)
        options.parameters = _values(
            self._parameters_struct, self._model.parameters, parameters
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
            self._model.parameters,
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
            self._inputs_struct, self._model.inputs, inputs, complete=True
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
            for name in self._model.inputs
        }

    def _configuration_functions(self):
        """
        Bind the generated configuration functions on first use.

        The configuration is a value type, so its layout is rebuilt here from the
        model: the deepest active state outside every region and one slot per
        region. Binding is lazy so that a test that never asks for a
        configuration does not depend on these symbols.

        :return: Namespace-like object holding the ctypes structure types and
            the bound functions.
        :rtype: types.SimpleNamespace
        """
        cached = getattr(self, "_configuration_binding", None)
        if cached is not None:
            return cached
        regions = max(1, len(list(self._model.walk_regions())))
        configuration = type(
            "Configuration",
            (ctypes.Structure,),
            {"_fields_": [("at", ctypes.c_int), ("regions", ctypes.c_int * regions)]},
        )
        error = type(
            "ConfigurationError",
            (ctypes.Structure,),
            {
                "_fields_": [
                    ("position", ctypes.c_size_t),
                    ("kind", ctypes.c_int),
                    ("message", ctypes.c_char * _CONFIGURATION_MESSAGE_SIZE),
                ]
            },
        )
        pointer = ctypes.POINTER
        binding = SimpleNamespace(
            configuration=configuration,
            error=error,
            get=self._bind_function(
                "{prefix}_get_configuration",
                [ctypes.c_void_p, pointer(configuration)],
                ctypes.c_int,
            ),
            format=self._bind_function(
                "{prefix}_configuration_format",
                [pointer(configuration), ctypes.c_char_p, ctypes.c_size_t],
                ctypes.c_size_t,
            ),
            parse=self._bind_function(
                "{prefix}_configuration_parse",
                [ctypes.c_char_p, pointer(configuration), pointer(error)],
                ctypes.c_int,
            ),
            hot_start_at=self._bind_function(
                "{prefix}_hot_start_at_with_parameters",
                [
                    ctypes.c_void_p,
                    pointer(configuration),
                    ctypes.c_void_p,
                    ctypes.c_void_p,
                ],
                ctypes.c_int,
            ),
        )
        self._configuration_binding = binding
        return binding

    def _format_configuration(self, value):
        """
        Print a native configuration value the way the simulator does.

        :param value: Configuration structure filled by the generated runtime.
        :type value: ctypes.Structure
        :return: The one-line configuration text.
        :rtype: str
        """
        binding = self._configuration_functions()
        size = binding.format(ctypes.byref(value), None, 0)
        buffer = ctypes.create_string_buffer(size + 1)
        binding.format(ctypes.byref(value), buffer, size + 1)
        return buffer.value.decode("utf-8")

    def parse_configuration(self, text):
        """
        Parse configuration text with the generated runtime's own parser.

        :param text: Configuration text, for example ``Root.Run{A: X, B: [init]}``.
        :type text: str
        :return: The parsed configuration structure.
        :rtype: ctypes.Structure
        :raises ValueError: If the generated parser refuses the text; the message
            is the generated runtime's own.
        """
        binding = self._configuration_functions()
        value = binding.configuration()
        error = binding.error()
        if not binding.parse(text.encode("utf-8"), ctypes.byref(value), ctypes.byref(error)):
            raise ValueError(
                "%s (at byte %d)" % (error.message.decode("utf-8"), error.position)
            )
        return value

    @property
    def configuration(self):
        """
        Text of the runtime's current configuration.

        :return: The configuration text, or ``None`` once the machine has ended.
        :rtype: Optional[str]
        """
        if self.is_ended:
            return None
        binding = self._configuration_functions()
        value = binding.configuration()
        if not binding.get(self._machine, ctypes.byref(value)):
            self._raise_last_error()
        return self._format_configuration(value)

    def hot_start_at(self, text, values, parameters=None):
        """
        Hot start from configuration text and a complete variable snapshot.

        :param text: Configuration text parsed by the generated runtime.
        :type text: str
        :param values: Initial variable structure.
        :type values: ctypes.Structure
        :param parameters: Parameter snapshot, defaults to ``None``.
        :type parameters: Optional[Mapping[str, Any]], optional
        :return: ``None``.
        :rtype: None
        :raises ValueError: If the text or the start position is refused.
        """
        binding = self._configuration_functions()
        configuration = self.parse_configuration(text)
        parameter_values = _values(
            self._parameters_struct,
            self._model.parameters,
            {} if parameters is None else parameters,
            complete=True,
        )
        if not binding.hot_start_at(
            self._machine,
            ctypes.byref(configuration),
            ctypes.byref(values),
            ctypes.byref(parameter_values),
        ):
            self._raise_last_error()

    def _resolve_event_id_by_configuration(self, event_ref):
        """
        Resolve an event name for a model with regions the way the simulator does.

        The generated runtime numbers events but does not resolve names, so the
        test adapter does: a name that depends on the position is resolved once
        for every active leaf of the current configuration, any other name is
        tried as a full path first.

        :param event_ref: Event path string given to ``cycle``.
        :type event_ref: str
        :return: The id of the event the name resolves to.
        :rtype: int
        :raises SimulationRuntimeEventError: If the name resolves to no event or
            to several.
        """
        from pyfcstm.simulate.utils import is_state_resolve_event_path

        configuration = Configuration.parse(
            self._model, self.configuration, mode="transient"
        )
        if is_state_resolve_event_path(event_ref):
            try:
                event = configuration.resolve_event(event_ref)
            except (ModelValueError, ModelLookupError) as err:
                raise SimulationRuntimeEventError(str(err)) from err
        else:
            try:
                event = self._model.resolve_event(event_ref)
            except (ModelValueError, ModelLookupError):
                try:
                    event = configuration.resolve_event(event_ref)
                except (ModelValueError, ModelLookupError) as err:
                    if len(configuration.leaves) > 1:
                        raise SimulationRuntimeEventError(str(err)) from err
                    raise SimulationRuntimeEventError(
                        "Cannot resolve event path %r: failed with both "
                        "StateMachine.resolve_event and State.resolve_event. "
                        "Last error: %s" % (event_ref, err)
                    ) from err
        return self._event_ids[event.path_name]
