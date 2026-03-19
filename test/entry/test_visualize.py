import os
import pathlib
import textwrap

import pytest
from hbutils.system import TemporaryDirectory
from hbutils.testing import isolated_directory, simulate_entry

from pyfcstm.entry import pyfcstmcli
from pyfcstm.entry.base import ClickErrorException
from pyfcstm.entry import visualize as visualize_module


@pytest.fixture()
def input_code_file():
    with TemporaryDirectory() as td:
        code_file = os.path.join(td, 'code.fcstm')
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(textwrap.dedent("""
            def int counter = 0;

            state System {
                [*] -> Idle;
                state Idle;
            }
            """).strip())
        yield code_file


def _mock_render(output_store):
    def _render(plantuml_output, output_file, render_type, renderer, **kwargs):
        assert plantuml_output.startswith('@startuml')
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(f'{render_type}:{renderer}', encoding='utf-8')
        output_store.append((output_file, render_type, renderer, kwargs))
        return renderer

    return _render


@pytest.mark.unittest
class TestVisualizeHelpers:
    def test_resolve_visualize_output_path_append_suffix(self, input_code_file):
        output_path = visualize_module.resolve_visualize_output_path(input_code_file, 'demo/output', 'svg')
        assert output_path.name == 'output.svg'
        assert output_path.is_absolute()

    def test_resolve_visualize_output_path_reject_mismatch_suffix(self, input_code_file):
        with pytest.raises(ClickErrorException, match='does not match render type'):
            visualize_module.resolve_visualize_output_path(input_code_file, 'demo/output.png', 'svg')

    def test_detect_headless_environment_linux(self, monkeypatch):
        monkeypatch.setattr(visualize_module.sys, 'platform', 'linux')
        monkeypatch.delenv('DISPLAY', raising=False)
        monkeypatch.delenv('WAYLAND_DISPLAY', raising=False)
        monkeypatch.delenv('MIR_SOCKET', raising=False)
        monkeypatch.delenv('CI', raising=False)
        monkeypatch.delenv('PYFCSTM_NO_GUI', raising=False)

        is_headless, reason = visualize_module.detect_headless_environment()
        assert is_headless is True
        assert 'No desktop session detected' in reason

    def test_resolve_renderer_backend_auto_prefers_remote_when_local_unavailable(self, monkeypatch):
        class DummyRemote:
            def check(self):
                return None

        def _local_fail(**kwargs):
            raise RuntimeError('local unavailable')

        monkeypatch.setattr(visualize_module, 'create_local_plantuml_backend', _local_fail)
        monkeypatch.setattr(visualize_module, 'create_remote_plantuml_backend', lambda **kwargs: DummyRemote())

        renderer, backend = visualize_module.resolve_renderer_backend('auto')
        assert renderer == 'remote'
        assert isinstance(backend, DummyRemote)


@pytest.mark.unittest
class TestEntryVisualize:
    def test_visualize_render_and_open_success(self, input_code_file, monkeypatch):
        outputs = []
        monkeypatch.setattr(visualize_module, 'render_plantuml_diagram', _mock_render(outputs))
        monkeypatch.setattr(visualize_module, 'open_diagram_with_default_app', lambda _: (True, ''))

        result = simulate_entry(
            pyfcstmcli,
            [
                'pyfcstm',
                'visualize',
                '-i',
                input_code_file,
                '--renderer',
                'local',
            ],
        )

        assert result.exitcode == 0
        assert 'Diagram rendered successfully with local renderer.' in result.stdout
        assert 'Opened rendered diagram with the system default viewer.' in result.stdout
        assert outputs
        assert outputs[0][0].suffix == '.png'

    def test_visualize_no_open_with_explicit_output(self, input_code_file, monkeypatch):
        outputs = []
        monkeypatch.setattr(visualize_module, 'render_plantuml_diagram', _mock_render(outputs))

        def _should_not_open(_):
            raise AssertionError('open_diagram_with_default_app should not be called')

        monkeypatch.setattr(visualize_module, 'open_diagram_with_default_app', _should_not_open)

        with isolated_directory():
            result = simulate_entry(
                pyfcstmcli,
                [
                    'pyfcstm',
                    'visualize',
                    '-i',
                    input_code_file,
                    '-o',
                    'nested/diagram',
                    '-t',
                    'svg',
                    '--no-open',
                ],
            )

            assert result.exitcode == 0
            assert pathlib.Path('nested/diagram.svg').exists()
            assert 'Output file:' in result.stdout

    def test_visualize_open_skipped_in_headless_mode(self, input_code_file, monkeypatch):
        outputs = []
        monkeypatch.setattr(visualize_module, 'render_plantuml_diagram', _mock_render(outputs))
        monkeypatch.setattr(
            visualize_module,
            'open_diagram_with_default_app',
            lambda _: (False, 'No desktop session detected.'),
        )

        result = simulate_entry(
            pyfcstmcli,
            [
                'pyfcstm',
                'visualize',
                '-i',
                input_code_file,
            ],
        )

        assert result.exitcode == 0
        assert 'GUI display skipped: No desktop session detected.' in result.stdout

    def test_visualize_strict_open_failure(self, input_code_file, monkeypatch):
        outputs = []
        monkeypatch.setattr(visualize_module, 'render_plantuml_diagram', _mock_render(outputs))
        monkeypatch.setattr(
            visualize_module,
            'open_diagram_with_default_app',
            lambda _: (False, 'No desktop session detected.'),
        )

        result = simulate_entry(
            pyfcstmcli,
            [
                'pyfcstm',
                'visualize',
                '-i',
                input_code_file,
                '--strict-open',
            ],
        )

        assert result.exitcode != 0
        assert 'Failed to open rendered diagram automatically.' in (result.stderr or result.stdout)

    def test_visualize_missing_plantumlcli(self, input_code_file, monkeypatch):
        def _raise():
            raise ClickErrorException('Python package "plantumlcli" is not installed or failed to import: missing')

        monkeypatch.setattr(visualize_module, 'load_plantumlcli_classes', _raise)

        result = simulate_entry(
            pyfcstmcli,
            [
                'pyfcstm',
                'visualize',
                '-i',
                input_code_file,
            ],
        )

        assert result.exitcode != 0
        assert 'Python package "plantumlcli" is not installed or failed to import' in (result.stderr or result.stdout)

    def test_visualize_check_uses_builtin_check(self, monkeypatch):
        called = {}

        def _check(renderer, java=None, plantuml_jar=None, remote_host=None):
            called['args'] = (renderer, java, plantuml_jar, remote_host)
            return {
                'package': (True, 'ok'),
                'local': (True, 'available'),
                'remote': (False, 'unavailable'),
            }

        monkeypatch.setattr(visualize_module, 'run_plantumlcli_builtin_check', _check)

        result = simulate_entry(
            pyfcstmcli,
            [
                'pyfcstm',
                'visualize',
                '--check',
                '--renderer',
                'auto',
            ],
        )

        assert result.exitcode == 0
        assert called['args'][0] == 'auto'
