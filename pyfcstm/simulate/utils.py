"""
Utility functions for simulation runtime.

This module provides helper functions used by the simulation runtime.
"""

from typing import Union

from ..model import Event, OnStage, OnAspect


def get_event_name(event: Event) -> str:
    """
    Get the full path name of an event.

    :param event: The event object
    :type event: Event
    :return: Dot-separated event path
    :rtype: str
    """
    return '.'.join(event.path)


def get_func_name(func: Union[OnStage, OnAspect]) -> str:
    """
    Get the full path name of a lifecycle action.

    :param func: The action object
    :type func: Union[OnStage, OnAspect]
    :return: Dot-separated action path
    :rtype: str
    """
    sp = func.state_path
    if sp[-1] is None:
        sp = tuple((*sp[:-1], '<unnamed>'))
    return '.'.join(sp)
