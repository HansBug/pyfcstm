"""
Logging utilities for pyfcstm.

This module provides centralized logging configuration for the pyfcstm package.
"""
import logging
import sys
from typing import Optional


def get_logger(name: str = 'pyfcstm', level: Optional[int] = None) -> logging.Logger:
    """
    Get a logger instance for pyfcstm.

    :param name: Logger name, defaults to 'pyfcstm'
    :type name: str, optional
    :param level: Logging level, defaults to None (uses existing level or WARNING)
    :type level: int, optional
    :return: Configured logger instance
    :rtype: logging.Logger

    Example::

        >>> from pyfcstm.utils.logging import get_logger
        >>> logger = get_logger('pyfcstm.mymodule')
        >>> logger.info('This is an info message')
    """
    logger = logging.getLogger(name)

    # Only configure if not already configured
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        # Set default level if not already set
        if logger.level == logging.NOTSET:
            logger.setLevel(level if level is not None else logging.WARNING)
    elif level is not None:
        # Update level if explicitly provided
        logger.setLevel(level)

    return logger
