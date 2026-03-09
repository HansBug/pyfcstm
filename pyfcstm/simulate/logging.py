"""
Logging utilities for the simulate module.

This module provides logger lookup helpers specific to the simulation runtime.
"""
import logging

from ..utils.logging import get_logger as get_base_logger


def get_logger(name: str = 'pyfcstm.simulate') -> logging.Logger:
    """
    Get a logger instance for the simulate module.

    This helper only retrieves the logger. Handler configuration, formatter
    selection, and effective log levels are intentionally left to the caller.

    :param name: Logger name, defaults to ``'pyfcstm.simulate'``
    :type name: str, optional
    :return: Logger instance.
    :rtype: logging.Logger

    Example::

        >>> from pyfcstm.simulate.logging import get_logger
        >>> logger = get_logger()
        >>> logger.name
        'pyfcstm.simulate'
    """
    return get_base_logger(name)
