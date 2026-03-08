"""
Unit tests for is_state_resolve_event_path utility function.
"""

import pytest

from pyfcstm.simulate.utils import is_state_resolve_event_path


@pytest.mark.unittest
class TestIsStateResolveEventPath:
    """Test suite for is_state_resolve_event_path function."""

    def test_absolute_paths_return_true(self):
        """Test that absolute paths (starting with /) return True."""
        assert is_state_resolve_event_path('/global.shutdown') is True
        assert is_state_resolve_event_path('/error') is True
        assert is_state_resolve_event_path('/system.error.critical') is True

    def test_parent_relative_paths_return_true(self):
        """Test that parent-relative paths (starting with .) return True."""
        assert is_state_resolve_event_path('.error') is True
        assert is_state_resolve_event_path('..system.error') is True
        assert is_state_resolve_event_path('...global') is True
        assert is_state_resolve_event_path('.') is True
        assert is_state_resolve_event_path('..') is True

    def test_plain_paths_return_false(self):
        """Test that plain paths without special notation return False (uncertain)."""
        assert is_state_resolve_event_path('Root.System.error') is False
        assert is_state_resolve_event_path('error.critical') is False
        assert is_state_resolve_event_path('error') is False
        assert is_state_resolve_event_path('System') is False

    def test_empty_string_returns_false(self):
        """Test that empty string returns False."""
        assert is_state_resolve_event_path('') is False

    def test_edge_cases(self):
        """Test edge cases."""
        # Single character paths
        assert is_state_resolve_event_path('e') is False
        assert is_state_resolve_event_path('/e') is True
        assert is_state_resolve_event_path('.e') is True

        # Paths with numbers
        assert is_state_resolve_event_path('event123') is False
        assert is_state_resolve_event_path('/event123') is True

        # Paths with underscores
        assert is_state_resolve_event_path('error_handler') is False
        assert is_state_resolve_event_path('/error_handler') is True
