"""
Naming helpers for the simulation runtime.

This module contains small utility functions used by :mod:`pyfcstm.simulate`
when logging execution steps, normalizing event identifiers, and presenting
lifecycle action paths in a human-readable form.

The module contains the following main components:

* :func:`get_event_name` - Convert an event object into its dot-separated path.
* :func:`get_func_name` - Convert a lifecycle or aspect action into a readable
  dot-separated path.
"""


from typing import Union

from ..model import Event, OnStage, OnAspect


def get_event_name(event: Event) -> str:
    """
    Convert an event object into its canonical dot-separated path.

    The returned string is the stable identifier used by the runtime when it
    indexes active events for transition matching and when it emits diagnostic
    logs.

    :param event: Event object to name.
    :type event: Event
    :return: Dot-separated event path.
    :rtype: str
    """
    return '.'.join(event.path)


def get_func_name(func: Union[OnStage, OnAspect]) -> str:
    """
    Convert a lifecycle or aspect action into a readable dot-separated path.

    Unnamed actions are rendered with ``<unnamed>`` in the terminal position so
    log messages can still distinguish them from named actions.

    :param func: Lifecycle or aspect action to name.
    :type func: Union[OnStage, OnAspect]
    :return: Dot-separated action path.
    :rtype: str
    """
    sp = func.state_path
    if sp[-1] is None:
        sp = tuple((*sp[:-1], '<unnamed>'))
    return '.'.join(sp)
