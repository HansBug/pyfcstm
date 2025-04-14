"""
This module provides a validation framework for model validation in Python.
It includes base classes and exceptions for implementing validation rules and handling validation errors.
The framework supports collecting multiple validation errors and provides a clean interface for validation.

Usage:
    >>> class MyModel(IValidatable):
    ...     def _my_validator_function(self):
    ...         ...
    ...
    ...     __validators__ = [my_validator_function]
    ...
    ...     def __init__(self, data):
    ...         self.data = data
"""

import os
from typing import List

from hbutils.string import plural_word


class ValidationError(Exception):
    """
    Base exception class for validation errors.

    This exception should be raised when a single validation rule fails.
    """
    pass


class ModelValidationError(Exception):
    """
    Exception class for aggregating multiple validation errors.

    This exception contains a list of ValidationError instances and formats them
    into a readable error message.

    :param errors: List of validation errors that occurred
    :type errors: List[ValidationError]

    :ivar errors: Stored validation errors
    :type errors: List[ValidationError]
    """

    def __init__(self, errors: List[ValidationError]):
        super().__init__(
            f"Model validation error, {plural_word(len(errors), 'error')} in total:{os.linesep}"
            f"{os.linesep.join(map(lambda x: f'{x[0]}. {x[1]}', enumerate(map(repr, errors), start=1)))}",
        )
        self.errors = errors


class IValidatable:
    """
    Interface class for implementing validatable objects.

    Classes inheriting from IValidatable should define their validation rules
    in the __validators__ class variable as a list of validator functions.
    Each validator function should take the instance as parameter and raise
    ValidationError if validation fails.

    :cvar __validators__: List of validator functions to be applied
    :type __validators__: List[callable]

    Usage:
        >>> class MyModel(IValidatable):
        ...     def _my_validator_function(self):
        ...         ...
        ...
        ...     __validators__ = [my_validator_function]
        ...     
        >>> model = MyModel()
        >>> model.validate()  # Raises ModelValidationError if validation fails
    """

    __validators__ = []

    def _validate_for_errors(self) -> List[ValidationError]:
        """
        Execute all validators and collect validation errors.

        :return: List of validation errors that occurred
        :rtype: List[ValidationError]
        """
        errors = []
        for validator in self.__validators__:
            try:
                validator(self)
            except ValidationError as err:
                errors.append(err)
        return errors

    def validate(self):
        """
        Validate the object using all registered validators.

        :raises ModelValidationError: If any validation errors occur
        """
        errors = self._validate_for_errors()
        if errors:
            raise ModelValidationError(errors)
