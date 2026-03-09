"""
Logging utilities for pyfcstm.

This module provides centralized logging configuration for the pyfcstm package.
"""
import logging


def get_logger(name: str = 'pyfcstm') -> logging.Logger:
    """
    Get a logger instance for pyfcstm.

    This helper only retrieves the logger. Handler configuration, formatter
    selection, and effective log levels are intentionally left to the caller.

    :param name: Logger name, defaults to ``'pyfcstm'``
    :type name: str, optional
    :return: Logger instance.
    :rtype: logging.Logger

    Example::

        >>> from pyfcstm.utils.logging import get_logger
        >>> logger = get_logger('pyfcstm.mymodule')
        >>> logger.name
        'pyfcstm.mymodule'
    """
    return logging.getLogger(name)
