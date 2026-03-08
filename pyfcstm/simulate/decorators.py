"""
Decorators for abstract handler registration.

This module provides decorators that allow users to define abstract handlers
as methods in a class, making it easy to organize complex handler logic.

The module contains the following main components:

* :func:`abstract_handler` - Decorator to mark a method as an abstract handler.
* :func:`register_handlers_from_object` - Register all decorated methods from an object.

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

from typing import Callable, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .context import ReadOnlyExecutionContext

# Attribute name used to store handler metadata on decorated methods
_HANDLER_METADATA_ATTR = '__abstract_handler_metadata__'


def abstract_handler(action_path: str) -> Callable[[Callable], Callable]:
    """
    Decorator to mark a method as an abstract handler for a specific action path.

    This decorator attaches metadata to the method, which can later be used by
    :meth:`SimulationRuntime.register_handlers_from_object` to automatically
    register all handlers from a class instance.

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
        # Attach metadata to the function
        setattr(func, _HANDLER_METADATA_ATTR, action_path)
        return func

    return decorator


def get_handler_metadata(func: Callable) -> Optional[str]:
    """
    Get the action path metadata from a decorated method.

    :param func: The function to check
    :type func: Callable
    :return: The action path if the function is decorated, None otherwise
    :rtype: Optional[str]

    Example::

        >>> @abstract_handler('System.Active.Init')
        ... def my_handler(ctx):
        ...     pass
        >>> get_handler_metadata(my_handler)
        'System.Active.Init'
    """
    return getattr(func, _HANDLER_METADATA_ATTR, None)


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
    return hasattr(func, _HANDLER_METADATA_ATTR)
