import pytest

from pyfcstm.utils import IValidatable, ValidationError, ModelValidationError


@pytest.fixture
def create_model():
    class TestModel(IValidatable):
        def __init__(self, value1=None, value2=None):
            self.value1 = value1
            self.value2 = value2

        def _validate_property_1(self):
            if self.value1 is None:
                raise ValidationError("value1 cannot be None")

        def _validate_property_2(self):
            if self.value2 is None:
                raise ValidationError("value2 cannot be None")

        __validators__ = [_validate_property_1, _validate_property_2]

    return TestModel


@pytest.mark.unittest
class TestIValidatable:
    def test_validation_success(self, create_model):
        model = create_model(value1=1, value2=2)
        model.validate()  # should not raise exception

    def test_validation_single_error(self, create_model):
        model = create_model(value1=None, value2=2)
        with pytest.raises(ModelValidationError) as exc_info:
            model.validate()
        assert len(exc_info.value.errors) == 1
        assert str(exc_info.value.errors[0]) == "value1 cannot be None"

    def test_validation_multiple_errors(self, create_model):
        model = create_model(value1=None, value2=None)
        with pytest.raises(ModelValidationError) as exc_info:
            model.validate()
        assert len(exc_info.value.errors) == 2
        assert str(exc_info.value.errors[0]) == "value1 cannot be None"
        assert str(exc_info.value.errors[1]) == "value2 cannot be None"

    def test_validation_no_validators(self):
        class EmptyModel(IValidatable):
            pass

        model = EmptyModel()
        model.validate()  # should not raise exception

    def test_model_validation_error_message(self, create_model):
        model = create_model(value1=None, value2=None)
        with pytest.raises(ModelValidationError) as exc_info:
            model.validate()
        error_message = str(exc_info.value)
        assert "Model validation error, 2 errors in total:" in error_message
        assert "value1 cannot be None" in error_message
        assert "value2 cannot be None" in error_message
