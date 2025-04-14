import os
from typing import List

from hbutils.string import plural_word


class ValidationError(Exception):
    pass


class ModelValidationError(Exception):
    def __init__(self, errors: List[ValidationError]):
        super().__init__(
            f"Model validation error, {plural_word(len(errors), 'error')} in total:{os.linesep}"
            f"{os.linesep.join(map(lambda x: f'{x[0]}. {x[1]}', enumerate(map(repr, errors), start=1)))}",
        )
        self.errors = errors


class IValidatable:
    __validators__ = []

    def _validate_for_errors(self) -> List[ValidationError]:
        errors = []
        for validator in self.__validators__:
            try:
                validator(self)
            except ValidationError as err:
                errors.append(err)
        return errors

    def validate(self):
        errors = self._validate_for_errors()
        if errors:
            raise ModelValidationError(errors)
