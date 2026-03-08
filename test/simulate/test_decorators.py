"""
Tests for decorator module functionality.

This module tests the decorator mechanism itself, without involving
the runtime or state machine execution.
"""

import pytest

from pyfcstm.simulate.decorators import (
    abstract_handler,
    get_handler_metadata,
    is_abstract_handler,
    _HANDLER_METADATA_ATTR
)


@pytest.mark.unittest
class TestAbstractHandlerDecorator:
    """Test the @abstract_handler decorator."""

    def test_decorator_attaches_metadata(self):
        """Test that decorator attaches metadata to function."""
        @abstract_handler('System.Active.Init')
        def my_handler(ctx):
            pass

        # Check metadata attribute exists
        assert hasattr(my_handler, _HANDLER_METADATA_ATTR)
        assert getattr(my_handler, _HANDLER_METADATA_ATTR) == 'System.Active.Init'

    def test_decorator_with_different_paths(self):
        """Test decorator with various action paths."""
        @abstract_handler('Root.State.Action')
        def handler1(ctx):
            pass

        @abstract_handler('A.B.C.D.E')
        def handler2(ctx):
            pass

        @abstract_handler('Simple')
        def handler3(ctx):
            pass

        assert getattr(handler1, _HANDLER_METADATA_ATTR) == 'Root.State.Action'
        assert getattr(handler2, _HANDLER_METADATA_ATTR) == 'A.B.C.D.E'
        assert getattr(handler3, _HANDLER_METADATA_ATTR) == 'Simple'

    def test_decorator_preserves_function(self):
        """Test that decorator preserves the original function."""
        def original_handler(ctx):
            return "test_result"

        decorated = abstract_handler('System.Active.Init')(original_handler)

        # Function should still be callable and work the same
        assert callable(decorated)
        assert decorated(None) == "test_result"

    def test_decorator_with_empty_path_raises_error(self):
        """Test that decorator raises ValueError for empty action path."""
        with pytest.raises(ValueError, match='action_path cannot be empty'):
            @abstract_handler('')
            def handler(ctx):
                pass

    def test_decorator_on_method(self):
        """Test decorator works on class methods."""
        class MyClass:
            @abstract_handler('System.Active.Init')
            def my_method(self, ctx):
                return "method_result"

        obj = MyClass()

        # Check metadata on unbound method
        assert hasattr(MyClass.my_method, _HANDLER_METADATA_ATTR)
        assert getattr(MyClass.my_method, _HANDLER_METADATA_ATTR) == 'System.Active.Init'

        # Check bound method still works
        assert obj.my_method(None) == "method_result"

    def test_multiple_decorators_on_different_methods(self):
        """Test multiple methods can be decorated independently."""
        class MyClass:
            @abstract_handler('Action1')
            def method1(self, ctx):
                pass

            @abstract_handler('Action2')
            def method2(self, ctx):
                pass

            @abstract_handler('Action3')
            def method3(self, ctx):
                pass

        assert getattr(MyClass.method1, _HANDLER_METADATA_ATTR) == 'Action1'
        assert getattr(MyClass.method2, _HANDLER_METADATA_ATTR) == 'Action2'
        assert getattr(MyClass.method3, _HANDLER_METADATA_ATTR) == 'Action3'

    def test_decorator_with_special_characters_in_path(self):
        """Test decorator with special characters in action path."""
        @abstract_handler('System.Active.Init_Hardware')
        def handler1(ctx):
            pass

        @abstract_handler('System.Active.Init-Hardware')
        def handler2(ctx):
            pass

        assert getattr(handler1, _HANDLER_METADATA_ATTR) == 'System.Active.Init_Hardware'
        assert getattr(handler2, _HANDLER_METADATA_ATTR) == 'System.Active.Init-Hardware'


@pytest.mark.unittest
class TestGetHandlerMetadata:
    """Test the get_handler_metadata function."""

    def test_get_metadata_from_decorated_function(self):
        """Test getting metadata from decorated function."""
        @abstract_handler('System.Active.Init')
        def handler(ctx):
            pass

        metadata = get_handler_metadata(handler)
        assert metadata == 'System.Active.Init'

    def test_get_metadata_from_undecorated_function(self):
        """Test getting metadata from undecorated function returns None."""
        def handler(ctx):
            pass

        metadata = get_handler_metadata(handler)
        assert metadata is None

    def test_get_metadata_from_decorated_method(self):
        """Test getting metadata from decorated method."""
        class MyClass:
            @abstract_handler('System.Active.Monitor')
            def my_method(self, ctx):
                pass

        metadata = get_handler_metadata(MyClass.my_method)
        assert metadata == 'System.Active.Monitor'

    def test_get_metadata_from_bound_method(self):
        """Test getting metadata from bound method."""
        class MyClass:
            @abstract_handler('System.Active.Monitor')
            def my_method(self, ctx):
                pass

        obj = MyClass()
        metadata = get_handler_metadata(obj.my_method)
        assert metadata == 'System.Active.Monitor'

    def test_get_metadata_returns_none_for_non_callable(self):
        """Test getting metadata from non-callable returns None."""
        metadata = get_handler_metadata("not a function")
        assert metadata is None

        metadata = get_handler_metadata(123)
        assert metadata is None

        metadata = get_handler_metadata(None)
        assert metadata is None


@pytest.mark.unittest
class TestIsAbstractHandler:
    """Test the is_abstract_handler function."""

    def test_is_handler_for_decorated_function(self):
        """Test is_abstract_handler returns True for decorated function."""
        @abstract_handler('System.Active.Init')
        def handler(ctx):
            pass

        assert is_abstract_handler(handler) is True

    def test_is_handler_for_undecorated_function(self):
        """Test is_abstract_handler returns False for undecorated function."""
        def handler(ctx):
            pass

        assert is_abstract_handler(handler) is False

    def test_is_handler_for_decorated_method(self):
        """Test is_abstract_handler returns True for decorated method."""
        class MyClass:
            @abstract_handler('System.Active.Monitor')
            def my_method(self, ctx):
                pass

        assert is_abstract_handler(MyClass.my_method) is True

    def test_is_handler_for_undecorated_method(self):
        """Test is_abstract_handler returns False for undecorated method."""
        class MyClass:
            def my_method(self, ctx):
                pass

        assert is_abstract_handler(MyClass.my_method) is False

    def test_is_handler_for_bound_method(self):
        """Test is_abstract_handler works with bound methods."""
        class MyClass:
            @abstract_handler('System.Active.Monitor')
            def decorated_method(self, ctx):
                pass

            def undecorated_method(self, ctx):
                pass

        obj = MyClass()

        assert is_abstract_handler(obj.decorated_method) is True
        assert is_abstract_handler(obj.undecorated_method) is False

    def test_is_handler_for_non_callable(self):
        """Test is_abstract_handler returns False for non-callable."""
        assert is_abstract_handler("not a function") is False
        assert is_abstract_handler(123) is False
        assert is_abstract_handler(None) is False
        assert is_abstract_handler([]) is False


@pytest.mark.unittest
class TestDecoratorIntegration:
    """Test decorator integration scenarios."""

    def test_scan_class_for_decorated_methods(self):
        """Test scanning a class for all decorated methods."""
        class MyHandlers:
            @abstract_handler('Action1')
            def handler1(self, ctx):
                pass

            @abstract_handler('Action2')
            def handler2(self, ctx):
                pass

            def helper_method(self):
                # Not decorated
                pass

            @abstract_handler('Action3')
            def handler3(self, ctx):
                pass

        # Scan for decorated methods
        decorated_methods = []
        for name in dir(MyHandlers):
            if name.startswith('_'):
                continue

            attr = getattr(MyHandlers, name)
            if callable(attr) and is_abstract_handler(attr):
                metadata = get_handler_metadata(attr)
                decorated_methods.append((name, metadata))

        # Should find exactly 3 decorated methods
        assert len(decorated_methods) == 3

        # Check they have correct metadata
        method_dict = dict(decorated_methods)
        assert method_dict['handler1'] == 'Action1'
        assert method_dict['handler2'] == 'Action2'
        assert method_dict['handler3'] == 'Action3'
        assert 'helper_method' not in method_dict

    def test_decorator_with_lambda(self):
        """Test decorator works with lambda functions."""
        handler = abstract_handler('System.Active.Init')(lambda ctx: "lambda_result")

        assert is_abstract_handler(handler) is True
        assert get_handler_metadata(handler) == 'System.Active.Init'
        assert handler(None) == "lambda_result"

    def test_decorator_preserves_function_attributes(self):
        """Test decorator preserves function name and docstring."""
        @abstract_handler('System.Active.Init')
        def my_handler(ctx):
            """This is my handler docstring."""
            pass

        # Function name and docstring should be preserved
        assert my_handler.__name__ == 'my_handler'
        assert my_handler.__doc__ == "This is my handler docstring."

    def test_multiple_instances_share_decorator_metadata(self):
        """Test that multiple instances of a class share the same decorator metadata."""
        class MyHandler:
            @abstract_handler('System.Active.Init')
            def handle(self, ctx):
                pass

        obj1 = MyHandler()
        obj2 = MyHandler()

        # Both instances should have the same metadata
        assert get_handler_metadata(obj1.handle) == 'System.Active.Init'
        assert get_handler_metadata(obj2.handle) == 'System.Active.Init'

    def test_decorator_with_inheritance(self):
        """Test decorator works with class inheritance."""
        class BaseHandler:
            @abstract_handler('Base.Action')
            def base_handler(self, ctx):
                pass

        class DerivedHandler(BaseHandler):
            @abstract_handler('Derived.Action')
            def derived_handler(self, ctx):
                pass

        obj = DerivedHandler()

        # Both base and derived handlers should be accessible
        assert is_abstract_handler(obj.base_handler) is True
        assert is_abstract_handler(obj.derived_handler) is True
        assert get_handler_metadata(obj.base_handler) == 'Base.Action'
        assert get_handler_metadata(obj.derived_handler) == 'Derived.Action'

    def test_decorator_with_method_override(self):
        """Test decorator behavior when method is overridden."""
        class BaseHandler:
            @abstract_handler('Base.Action')
            def handler(self, ctx):
                return "base"

        class DerivedHandler(BaseHandler):
            @abstract_handler('Derived.Action')
            def handler(self, ctx):
                return "derived"

        base_obj = BaseHandler()
        derived_obj = DerivedHandler()

        # Each should have its own metadata
        assert get_handler_metadata(base_obj.handler) == 'Base.Action'
        assert get_handler_metadata(derived_obj.handler) == 'Derived.Action'

    def test_decorator_metadata_attribute_name(self):
        """Test that the metadata attribute name is as expected."""
        @abstract_handler('System.Active.Init')
        def handler(ctx):
            pass

        # Verify the exact attribute name
        assert _HANDLER_METADATA_ATTR == '__abstract_handler_metadata__'
        assert hasattr(handler, '__abstract_handler_metadata__')


@pytest.mark.unittest
class TestDecoratorEdgeCases:
    """Test edge cases and error conditions."""

    def test_decorator_with_none_path_raises_error(self):
        """Test that decorator raises error for None action path."""
        with pytest.raises((ValueError, TypeError)):
            @abstract_handler(None)
            def handler(ctx):
                pass

    def test_decorator_with_whitespace_only_path(self):
        """Test decorator with whitespace-only path is allowed."""
        # Whitespace-only string is technically valid (though not recommended)
        @abstract_handler('   ')
        def handler(ctx):
            pass

        # Should be decorated successfully
        assert is_abstract_handler(handler) is True
        assert get_handler_metadata(handler) == '   '

    def test_get_metadata_with_manually_set_attribute(self):
        """Test get_handler_metadata with manually set attribute."""
        def handler(ctx):
            pass

        # Manually set the metadata attribute
        setattr(handler, _HANDLER_METADATA_ATTR, 'Manual.Path')

        metadata = get_handler_metadata(handler)
        assert metadata == 'Manual.Path'
        assert is_abstract_handler(handler) is True

    def test_decorator_does_not_interfere_with_other_decorators(self):
        """Test that abstract_handler can be combined with other decorators."""
        def other_decorator(func):
            func.other_attr = "other_value"
            return func

        @other_decorator
        @abstract_handler('System.Active.Init')
        def handler(ctx):
            pass

        # Both decorators should work
        assert is_abstract_handler(handler) is True
        assert get_handler_metadata(handler) == 'System.Active.Init'
        assert hasattr(handler, 'other_attr')
        assert handler.other_attr == "other_value"

    def test_decorator_order_with_other_decorators(self):
        """Test decorator order matters with other decorators."""
        def wrapper_decorator(func):
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)
            # Copy metadata to wrapper
            if hasattr(func, _HANDLER_METADATA_ATTR):
                setattr(wrapper, _HANDLER_METADATA_ATTR, getattr(func, _HANDLER_METADATA_ATTR))
            return wrapper

        @wrapper_decorator
        @abstract_handler('System.Active.Init')
        def handler(ctx):
            return "result"

        # Metadata should be preserved through wrapper
        assert is_abstract_handler(handler) is True
        assert get_handler_metadata(handler) == 'System.Active.Init'
        assert handler(None) == "result"
