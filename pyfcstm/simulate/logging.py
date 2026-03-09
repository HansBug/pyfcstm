"""
Logging utilities for the simulate module.

This module provides logging configuration specific to the simulation runtime.
"""
import logging
from typing import Optional

from ..utils.logging import get_logger as get_base_logger


def get_logger(name: str = 'pyfcstm.simulate', level: Optional[int] = None) -> logging.Logger:
    """
    Get a logger instance for the simulate module.

    :param name: Logger name, defaults to 'pyfcstm.simulate'
    :type name: str, optional
    :param level: Logging level, defaults to None (uses existing level)
    :type level: int, optional
    :return: Configured logger instance
    :rtype: logging.Logger

    Example::

        >>> from pyfcstm.simulate.logging import get_logger
        >>> logger = get_logger()
        >>> logger.info('Simulation started')
    """
    return get_base_logger(name, level)
