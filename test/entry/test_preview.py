"""
Tests for the ``pyfcstm preview`` Click subcommand.
"""
import os
import textwrap
from tempfile import TemporaryDirectory

import pytest
from hbutils.testing import simulate_entry

from pyfcstm.entry import preview as preview_module
from pyfcstm.entry.base import ClickErrorException
from pyfcstm.entry.dispatch import pyfcstmcli
from pyfcstm.entry.preview import (
    _build_options,
    _format_for_output,
    _parse_kv_pairs,
)
from pyfcstm.jsruntime import reset_engine


SIMPLE_DSL = textwrap.dedent(
    """
    def int counter = 0;
    state Demo {
        state Idle;
        [*] -> Idle;
    }
    """
).strip() + '\n'


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_engine()
    yield
    reset_engine()


@pytest.fixture()
def dsl_file():
    with TemporaryDirectory() as td:
        path = os.path.join(td, 'demo.fcstm')
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(SIMPLE_DSL)
        yield path


@pytest.mark.unittest
class TestFormatForOutput:
    def test_svg(self):
        from pathlib import Path
        assert _format_for_output(Path('foo.svg')) == 'svg'

    def test_png(self):
        from pathlib import Path
        assert _format_for_output(Path('foo.PNG')) == 'png'

    def test_unsupported_extension(self):
        from pathlib import Path
        with pytest.raises(ClickErrorException, match='must end in .svg or .png'):
            _format_for_output(Path('foo.pdf'))


@pytest.mark.unittest
class TestParseKvPairs:
    def test_empty(self):
        assert _parse_kv_pairs(()) == {}

    def test_string_value(self):
        assert _parse_kv_pairs(('palette=nord',)) == {'palette': 'nord'}

    def test_json_value(self):
        out = _parse_kv_pairs(('eventNameFormat=["name","relpath"]',
                               'showEvents=false',
                               'maxStateEvents=4'))
        assert out == {
            'eventNameFormat': ['name', 'relpath'],
            'showEvents': False,
            'maxStateEvents': 4,
        }

    def test_missing_equals(self):
        with pytest.raises(ClickErrorException, match='key=value form'):
            _parse_kv_pairs(('palette',))

    def test_empty_key(self):
        with pytest.raises(ClickErrorException, match='key is empty'):
            _parse_kv_pairs(('=value',))


@pytest.mark.unittest
class TestBuildOptions:
    def test_no_options(self):
        assert _build_options(None, None, ()) is None

    def test_explicit_flags(self):
        out = _build_options('RIGHT', 'full', ())
        assert out == {'direction': 'RIGHT', 'detailLevel': 'full'}

    def test_extras_merged(self):
        out = _build_options('DOWN', None, ('palette=nord',))
        assert out == {'direction': 'DOWN', 'palette': 'nord'}

    def test_extras_override_explicit(self):
        # If both explicit flag and --option set the same key, extras win.
        out = _build_options('DOWN', None, ('direction=UP',))
        assert out == {'direction': 'UP'}


@pytest.mark.unittest
class TestPreviewCommand:
    def test_svg_default(self, dsl_file):
        with TemporaryDirectory() as td:
            out = os.path.join(td, 'demo.svg')
            result = simulate_entry(
                pyfcstmcli,
                ['pyfcstm', 'preview', '-i', dsl_file, '-o', out],
            )
            result.assert_okay()
            assert os.path.isfile(out)
            text = open(out, encoding='utf-8').read()
            assert text.startswith('<svg')
            assert 'Demo' in text

    def test_png_with_scale(self, dsl_file):
        with TemporaryDirectory() as td:
            out = os.path.join(td, 'demo.png')
            result = simulate_entry(
                pyfcstmcli,
                ['pyfcstm', 'preview', '-i', dsl_file, '-o', out,
                 '-s', '1.0', '-d', 'DOWN', '-l', 'minimal'],
            )
            result.assert_okay()
            assert os.path.isfile(out)
            data = open(out, 'rb').read()
            assert data[:8] == b'\x89PNG\r\n\x1a\n'

    def test_extra_options_pass_through(self, dsl_file):
        with TemporaryDirectory() as td:
            out = os.path.join(td, 'demo.svg')
            result = simulate_entry(
                pyfcstmcli,
                ['pyfcstm', 'preview', '-i', dsl_file, '-o', out,
                 '--option', 'direction=LEFT'],
            )
            result.assert_okay()
            text = open(out, encoding='utf-8').read()
            assert 'data-fcstm-direction="LEFT"' in text

    def test_unsupported_extension_errors(self, dsl_file):
        with TemporaryDirectory() as td:
            out = os.path.join(td, 'demo.pdf')
            result = simulate_entry(
                pyfcstmcli,
                ['pyfcstm', 'preview', '-i', dsl_file, '-o', out],
            )
            assert result.exitcode != 0

    def test_invalid_dsl_errors(self):
        with TemporaryDirectory() as td:
            bad = os.path.join(td, 'bad.fcstm')
            with open(bad, 'w', encoding='utf-8') as fh:
                fh.write('not a valid dsl')
            out = os.path.join(td, 'bad.png')
            result = simulate_entry(
                pyfcstmcli,
                ['pyfcstm', 'preview', '-i', bad, '-o', out],
            )
            assert result.exitcode != 0

    def test_creates_output_directory(self, dsl_file):
        with TemporaryDirectory() as td:
            out = os.path.join(td, 'nested', 'sub', 'demo.svg')
            result = simulate_entry(
                pyfcstmcli,
                ['pyfcstm', 'preview', '-i', dsl_file, '-o', out],
            )
            result.assert_okay()
            assert os.path.isfile(out)

    def test_engine_unavailable_propagates(self, dsl_file, monkeypatch):
        from pyfcstm.jsruntime import JsEngineUnavailableError
        from pyfcstm import visualize as visualize_module

        def _boom(*_args, **_kwargs):
            raise JsEngineUnavailableError('no engine in test')

        monkeypatch.setattr(visualize_module, 'render_svg', _boom)
        with TemporaryDirectory() as td:
            out = os.path.join(td, 'demo.svg')
            result = simulate_entry(
                pyfcstmcli,
                ['pyfcstm', 'preview', '-i', dsl_file, '-o', out],
            )
            assert result.exitcode != 0


@pytest.mark.unittest
def test_module_export():
    # Light import-coverage check.
    assert hasattr(preview_module, '_add_preview_subcommand')
