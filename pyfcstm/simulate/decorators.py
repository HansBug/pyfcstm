"""
Decorators for abstract handler registration.

This module provides decorators that allow users to define abstract handlers
as methods in a class, making it easy to organize complex handler logic. A
single callable may be marked for multiple abstract actions, and handlers may
be declared as instance methods, static methods, or class methods.

The module contains the following main components:

* :func:`abstract_handler` - Decorator to mark a callable as an abstract handler.
* :func:`get_handler_metadata` - Return the first abstract action path for compatibility.
* :func:`is_abstract_handler` - Check whether a callable has handler metadata.

The runtime method :meth:`pyfcstm.simulate.runtime.SimulationRuntime.register_handlers_from_object`
consumes this metadata and registers bound handlers on a runtime instance.

Example::

    >>> from pyfcstm.simulate import abstract_handler, SimulationRuntime
    >>> class MyHandlers:
    ...     def __init__(self):
    ...         self.call_count = 0
    ...
    ...     @abstract_handler('System.Active.Init')
    ...     def handle_init(self, ctx):
    ...         self.call_count += 1
    ...         print(f"Init called, counter={ctx.get_var('counter')}")
    ...
    ...     @abstract_handler('System.Active.Monitor')
    ...     def handle_monitor(self, ctx):
    ...         print(f"Monitoring: {ctx.get_full_state_path()}")
    ...
    >>> runtime = SimulationRuntime(state_machine)
    >>> handlers = MyHandlers()
    >>> runtime.register_handlers_from_object(handlers)
"""

from typing import Callable, Optional, Tuple

# Attribute name used to store handler metadata on decorated methods
_HANDLER_METADATA_ATTR = '__abstract_handler_metadata__'


def _metadata_targets(func: object) -> Tuple[object, ...]:
    """
    Return objects that should carry abstract-handler metadata.

    ``staticmethod`` and ``classmethod`` wrap an underlying function. Metadata
    is mirrored to both the descriptor and the underlying function when the
    descriptor accepts custom attributes. ``property`` metadata is stored on
    the getter so the scanner can reject it as an unsupported handler descriptor
    without executing user code.

    :param func: Callable or descriptor to annotate.
    :type func: object
    :return: Objects that should receive metadata.
    :rtype: Tuple[object, ...]

    Example::

        >>> class Handlers:
        ...     @staticmethod
        ...     def handle(ctx):
        ...         pass
        >>> targets = _metadata_targets(Handlers.__dict__['handle'])
        >>> len(targets) >= 1
        True
    """
    targets = [func]
    wrapped = getattr(func, "__func__", None)
    if wrapped is not None:
        targets.append(wrapped)

    getter = getattr(func, "fget", None)
    if getter is not None:
        targets.append(getter)

    return tuple(targets)


def _get_handler_metadata_paths(func: object) -> Tuple[str, ...]:
    """
    Return all abstract action paths attached to a callable.

    Metadata may be stored either as a single string or as a tuple of strings.
    The tuple form allows one callable to handle multiple abstract actions,
    while the string form keeps direct metadata inspection simple for single
    action handlers.

    :param func: Callable or descriptor to inspect.
    :type func: object
    :return: Abstract action paths attached to ``func``.
    :rtype: Tuple[str, ...]

    Example::

        >>> @abstract_handler('System.Active.Init')
        ... def my_handler(ctx):
        ...     pass
        >>> _get_handler_metadata_paths(my_handler)
        ('System.Active.Init',)
    """
    value = getattr(func, _HANDLER_METADATA_ATTR, None)
    if value is None:
        wrapped = getattr(func, "__func__", None)
        if wrapped is not None:
            value = getattr(wrapped, _HANDLER_METADATA_ATTR, None)

    if value is None:
        getter = getattr(func, "fget", None)
        if getter is not None:
            value = getattr(getter, _HANDLER_METADATA_ATTR, None)

    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(value)


def _set_handler_metadata_paths(func: object, paths: Tuple[str, ...]) -> None:
    """
    Store abstract action paths on a callable and supported descriptors.

    :param func: Callable or descriptor to annotate.
    :type func: object
    :param paths: Abstract action paths to store.
    :type paths: Tuple[str, ...]
    :return: ``None``.
    :rtype: None

    Example::

        >>> def handler(ctx):
        ...     pass
        >>> _set_handler_metadata_paths(handler, ('System.Active.Init',))
        >>> get_handler_metadata(handler)
        'System.Active.Init'
    """
    value = paths[0] if len(paths) == 1 else paths
    targets = _metadata_targets(func)
    stored = False
    for target in targets:
        try:
            setattr(target, _HANDLER_METADATA_ATTR, value)
        except AttributeError:
            # AttributeError: built-in descriptor wrappers such as
            # ``staticmethod``, ``classmethod``, or ``property`` may reject
            # custom attributes on some supported Python versions; their
            # underlying callable target is also attempted in this loop.
            if len(targets) == 1:
                raise
        else:
            stored = True

    if not stored:
        raise AttributeError(
            "abstract handler metadata could not be attached to %r" % (func,)
        )


def abstract_handler(action_path: str) -> Callable[[Callable], Callable]:
    """
    Decorator to mark a method as an abstract handler for a specific action path.

    This decorator attaches metadata to the method, which can later be used by
    :meth:`SimulationRuntime.register_handlers_from_object` to automatically
    register all handlers from a class instance. Applying the decorator more
    than once to the same callable registers that callable for every decorated
    action path in source order.

    :param action_path: The full path to the abstract action (e.g., 'System.Active.Init')
    :type action_path: str
    :return: Decorator function that marks the method
    :rtype: Callable[[Callable], Callable]
    :raises ValueError: If action_path is empty

    Example::

        >>> class MyHandlers:
        ...     @abstract_handler('System.Active.Init')
        ...     def handle_init(self, ctx: ReadOnlyExecutionContext):
        ...         print(f"Initializing: {ctx.get_full_state_path()}")
        ...
        ...     @abstract_handler('System.Active.Monitor')
        ...     def handle_monitor(self, ctx: ReadOnlyExecutionContext):
        ...         counter = ctx.get_var('counter')
        ...         print(f"Monitoring, counter={counter}")

    .. note::
       The decorated method must accept exactly one parameter (besides self):
       a :class:`ReadOnlyExecutionContext` instance.
    """
    if not action_path:
        raise ValueError('action_path cannot be empty')

    def decorator(func: Callable) -> Callable:
        paths = _get_handler_metadata_paths(func)
        _set_handler_metadata_paths(func, (action_path,) + paths)
        return func

    return decorator


def get_handler_metadata(func: Callable) -> Optional[str]:
    """
    Get the action path metadata from a decorated method.

    :param func: The function to check
    :type func: Callable
    :return: The first action path if the function is decorated, ``None`` otherwise.
    :rtype: Optional[str]

    Example::

        >>> @abstract_handler('System.Active.Init')
        ... def my_handler(ctx):
        ...     pass
        >>> get_handler_metadata(my_handler)
        'System.Active.Init'
    """
    paths = _get_handler_metadata_paths(func)
    return paths[0] if paths else None


def is_abstract_handler(func: Callable) -> bool:
    """
    Check if a function is decorated as an abstract handler.

    :param func: The function to check
    :type func: Callable
    :return: True if the function has handler metadata
    :rtype: bool

    Example::

        >>> @abstract_handler('System.Active.Init')
        ... def my_handler(ctx):
        ...     pass
        >>> is_abstract_handler(my_handler)
        True
    """
    return bool(_get_handler_metadata_paths(func))
