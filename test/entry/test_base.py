import sys
from io import StringIO
from unittest.mock import patch, MagicMock

import click
import pytest
from click.testing import CliRunner

from pyfcstm.entry.base import (
    ClickWarningException,
    ClickErrorException,
    print_exception,
    KeyboardInterrupted,
    command_wrap,
)


@pytest.fixture
def cli_runner():
    return CliRunner()


@pytest.fixture
def mock_click_secho():
    with patch('click.secho') as mock:
        yield mock


@pytest.mark.unittest
class TestClickExceptions:
    def test_click_warning_exception(self, mock_click_secho):
        exception = ClickWarningException("Test warning")
        exception.show()
        mock_click_secho.assert_called_once_with("Test warning", fg='yellow', file=sys.stderr)

    def test_click_error_exception(self, mock_click_secho):
        exception = ClickErrorException("Test error")
        exception.show()
        mock_click_secho.assert_called_once_with("Test error", fg='red', file=sys.stderr)

    def test_print_exception(self, capsys):
        try:
            raise ValueError("Test error")
        except ValueError as e:
            print_exception(e)

        captured = capsys.readouterr()
        assert "Traceback (most recent call last):" in captured.out
        assert "ValueError: Test error" in captured.out

    def test_print_exception_custom_print(self):
        custom_print = MagicMock()
        try:
            raise ValueError("Test error")
        except ValueError as e:
            print_exception(e, print=custom_print)

        custom_print.assert_called()

    def test_keyboard_interrupted(self):
        exception = KeyboardInterrupted()
        assert exception.message == "Interrupted."
        assert exception.exit_code == 0x7

        custom_exception = KeyboardInterrupted("Custom message")
        assert custom_exception.message == "Custom message"

    def test_command_wrap(self, cli_runner):
        @click.command()
        @command_wrap()
        def sample_command():
            raise ValueError("Test error")

        result = cli_runner.invoke(sample_command)
        assert result.exit_code == 1
        assert "Unexpected error found when running pyfcstm!" in result.output
        assert "ValueError: Test error" in result.output

    def test_command_wrap_click_exception(self, cli_runner):
        @click.command()
        @command_wrap()
        def sample_command():
            raise click.ClickException("Test click exception")

        result = cli_runner.invoke(sample_command)
        assert result.exit_code == 1
        assert "Test click exception" in result.output

    def test_command_wrap_keyboard_interrupt(self, cli_runner):
        @click.command()
        @command_wrap()
        def sample_command():
            raise KeyboardInterrupt()

        result = cli_runner.invoke(sample_command)
        assert result.exit_code == 0x7
        assert "Interrupted." in result.output

    def test_command_wrap_success(self, cli_runner):
        @click.command()
        @command_wrap()
        def sample_command():
            click.echo("Success")

        result = cli_runner.invoke(sample_command)
        assert result.exit_code == 0
        assert "Success" in result.output

    def test_print_exception_no_args(self, capsys):
        class CustomException(Exception):
            pass

        try:
            raise CustomException()
        except CustomException as e:
            print_exception(e)

        captured = capsys.readouterr()
        assert "CustomException" in captured.out

    def test_print_exception_multiple_args(self, capsys):
        try:
            raise ValueError("First error", "Second error")
        except ValueError as e:
            print_exception(e)

        captured = capsys.readouterr()
        assert "ValueError: ('First error', 'Second error')" in captured.out

    def test_print_exception_with_traceback(self, capsys):
        def inner_function():
            raise ValueError("Test error")

        try:
            inner_function()
        except ValueError as e:
            print_exception(e)

        captured = capsys.readouterr()
        assert "Traceback (most recent call last):" in captured.out
        assert "inner_function" in captured.out
        assert "ValueError: Test error" in captured.out

    def test_print_exception_custom_print_2(self):
        custom_output = StringIO()
        custom_print = lambda x: custom_output.write(x + '\n')

        try:
            raise ValueError("Test error")
        except ValueError as e:
            print_exception(e, print=custom_print)

        output = custom_output.getvalue()
        assert "Traceback (most recent call last):" in output
        assert "ValueError: Test error" in output
