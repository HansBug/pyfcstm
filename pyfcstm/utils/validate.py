"""
Validation framework utilities for model validation workflows.

This module provides a lightweight validation framework for Python models. It
defines base exceptions for validation failures and a mixin-style interface
(:class:`IValidatable`) that allows classes to register validation rules and
perform aggregated validation.

The module contains the following main components:

* :class:`ValidationError` - Exception for a single validation rule failure
* :class:`ModelValidationError` - Aggregated exception for multiple failures
* :class:`IValidatable` - Mixin interface for defining and running validators

Example::

    >>> from pyfcstm.utils.validate import IValidatable, ValidationError
    >>>
    >>> class MyModel(IValidatable):
    ...     def __init__(self, value: int):
    ...         self.value = value
    ...
    ...     def _validate_positive(self) -> None:
    ...         if self.value <= 0:
    ...             raise ValidationError("Value must be positive.")
    ...
    ...     __validators__ = [_validate_positive]
    ...
    >>> model = MyModel(1)
    >>> model.validate()
    >>> bad_model = MyModel(0)
    >>> try:
    ...     bad_model.validate()
    ... except Exception as err:
    ...     print(type(err).__name__)
    ModelValidationError
"""

import os
from typing import Callable, List

from hbutils.string import plural_word


class ValidationError(Exception):
    """
    Base exception class for validation errors.

    This exception should be raised when a single validation rule fails. It is
    designed to be caught and collected by :class:`IValidatable`.

    Example::

        >>> raise ValidationError("Invalid value.")
        Traceback (most recent call last):
            ...
        ValidationError: Invalid value.
    """
    pass


class ModelValidationError(Exception):
    """
    Exception class for aggregating multiple validation errors.

    This exception contains a list of :class:`ValidationError` instances and
    formats them into a readable error message.

    :param errors: List of validation errors that occurred
    :type errors: List[ValidationError]

    :ivar errors: Stored validation errors
    :vartype errors: List[ValidationError]

    Example::

        >>> err = ModelValidationError([ValidationError("A"), ValidationError("B")])
        >>> "2 errors" in str(err)
        True
    """

    def __init__(self, errors: List[ValidationError]) -> None:
        super().__init__(
            f"Model validation error, {plural_word(len(errors), 'error')} in total:{os.linesep}"
            f"{os.linesep.join(map(lambda x: f'{x[0]}. {x[1]}', enumerate(map(repr, errors), start=1)))}",
        )
        self.errors = errors


class IValidatable:
    """
    Interface class for implementing validatable objects.

    Classes inheriting from :class:`IValidatable` should define their validation
    rules in the :attr:`__validators__` class variable as a list of validator
    methods. Each validator should accept the instance as the sole parameter
    and raise :class:`ValidationError` if the rule fails.

    :cvar __validators__: List of validator functions to be applied
    :type __validators__: List[Callable[["IValidatable"], None]]

    Example::

        >>> class MyModel(IValidatable):
        ...     def _validate_non_empty(self) -> None:
        ...         if not getattr(self, "value", None):
        ...             raise ValidationError("Value is empty.")
        ...
        ...     __validators__ = [_validate_non_empty]
        ...
        >>> model = MyModel()
        >>> try:
        ...     model.validate()
        ... except ModelValidationError as err:
        ...     isinstance(err.errors[0], ValidationError)
        True
    """

    __validators__: List[Callable[["IValidatable"], None]] = []

    def _validate_for_errors(self) -> List[ValidationError]:
        """
        Execute all validators and collect validation errors.

        Each validator registered in :attr:`__validators__` is called with the
        current instance. Any :class:`ValidationError` raised is collected.

        :return: List of validation errors that occurred
        :rtype: List[ValidationError]
        """
        errors: List[ValidationError] = []
        for validator in self.__validators__:
            try:
                validator(self)
            except ValidationError as err:
                errors.append(err)
        return errors

    def validate(self) -> None:
        """
        Validate the object using all registered validators.

        :raises ModelValidationError: If any validation errors occur

        Example::

            >>> class MyModel(IValidatable):
            ...     def _validate(self) -> None:
            ...         raise ValidationError("Always invalid.")
            ...
            ...     __validators__ = [_validate]
            ...
            >>> try:
            ...     MyModel().validate()
            ... except ModelValidationError as err:
            ...     len(err.errors)
            1
        """
        errors = self._validate_for_errors()
        if errors:
            raise ModelValidationError(errors)
