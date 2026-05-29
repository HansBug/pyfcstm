import os
import pathlib
import textwrap
from unittest.mock import patch

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
            # OSError mirrors a real plantumlcli local-backend failure
            # (missing java, jar not found). It is in the documented
            # _PLANTUMLCLI_RUNTIME_ERRORS whitelist; an unexpected class
            # such as TypeError would (correctly) propagate.
            raise OSError('local unavailable')

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

    def test_format_exception_message_with_text(self):
        msg = visualize_module._format_exception_message(ValueError('boom'))
        assert msg == 'ValueError: boom'

    def test_format_exception_message_blank(self):
        msg = visualize_module._format_exception_message(OSError(''))
        assert msg == 'OSError'

    def test_resolve_renderer_backend_local_failure(self, monkeypatch):
        def _local_fail(**kwargs):
            raise OSError('java missing')

        monkeypatch.setattr(visualize_module, 'create_local_plantuml_backend', _local_fail)
        with pytest.raises(ClickErrorException, match='Local PlantUML renderer is unavailable'):
            visualize_module.resolve_renderer_backend('local')

    def test_resolve_renderer_backend_remote_failure(self, monkeypatch):
        def _remote_fail(**kwargs):
            raise OSError('host unreachable')

        monkeypatch.setattr(visualize_module, 'create_remote_plantuml_backend', _remote_fail)
        with pytest.raises(ClickErrorException, match='Remote PlantUML renderer is unavailable'):
            visualize_module.resolve_renderer_backend('remote')

    def test_resolve_renderer_backend_local_success(self, monkeypatch):
        class _OkLocal:
            def check(self):
                return None

        monkeypatch.setattr(visualize_module, 'create_local_plantuml_backend',
                            lambda **kw: _OkLocal())
        name, backend = visualize_module.resolve_renderer_backend('local')
        assert name == 'local'
        assert isinstance(backend, _OkLocal)

    def test_resolve_renderer_backend_remote_success(self, monkeypatch):
        class _OkRemote:
            def check(self):
                return None

        monkeypatch.setattr(visualize_module, 'create_remote_plantuml_backend',
                            lambda **kw: _OkRemote())
        name, backend = visualize_module.resolve_renderer_backend('remote')
        assert name == 'remote'
        assert isinstance(backend, _OkRemote)

    def test_resolve_renderer_backend_auto_local_success(self, monkeypatch):
        class _OkLocal:
            def check(self):
                return None

        monkeypatch.setattr(visualize_module, 'create_local_plantuml_backend',
                            lambda **kw: _OkLocal())
        name, backend = visualize_module.resolve_renderer_backend('auto')
        assert name == 'local'

    def test_resolve_renderer_backend_auto_both_fail(self, monkeypatch):
        def _local_fail(**kwargs):
            raise OSError('java missing')

        def _remote_fail(**kwargs):
            raise OSError('host unreachable')

        monkeypatch.setattr(visualize_module, 'create_local_plantuml_backend', _local_fail)
        monkeypatch.setattr(visualize_module, 'create_remote_plantuml_backend', _remote_fail)
        with pytest.raises(ClickErrorException, match='No usable PlantUML renderer found'):
            visualize_module.resolve_renderer_backend('auto')

    def test_resolve_renderer_backend_unexpected_type_propagates(self, monkeypatch):
        # TypeError is OUTSIDE the documented whitelist -- the new policy
        # says it must surface instead of being reformatted into a
        # ClickErrorException.
        def _local_typebug(**kwargs):
            raise TypeError('bug: wrong arg type')

        monkeypatch.setattr(visualize_module, 'create_local_plantuml_backend', _local_typebug)
        with pytest.raises(TypeError, match='wrong arg type'):
            visualize_module.resolve_renderer_backend('local')

    def test_render_plantuml_diagram_success_returns_renderer(self, tmp_path, monkeypatch):
        class _OkLocal:
            def check(self):
                return None

            def dump(self, path, render_type, source):
                pathlib.Path(path).write_text('ok')

        monkeypatch.setattr(visualize_module, 'create_local_plantuml_backend',
                            lambda **kw: _OkLocal())
        out = tmp_path / 'out.png'
        name = visualize_module.render_plantuml_diagram('@startuml\n@enduml', out, 'png', 'local')
        assert name == 'local'
        assert out.exists()

    def test_load_plantumlcli_classes_import_error_propagates(self, monkeypatch):
        # Reach the (ImportError, ModuleNotFoundError) -> ClickErrorException
        # branch by injecting a sys.modules entry that fails on attribute
        # access for the symbol names plantumlcli exports.
        import sys as _sys
        bogus = type(_sys)('plantumlcli_bogus')
        monkeypatch.setitem(_sys.modules, 'plantumlcli', bogus)
        with pytest.raises(ClickErrorException, match='not installed or failed to import'):
            visualize_module.load_plantumlcli_classes()

    def test_create_local_and_remote_plantuml_backend_round_trip(self, monkeypatch):
        # Use a fake plantumlcli module to exercise both
        # create_local_plantuml_backend and create_remote_plantuml_backend
        # without depending on the real third-party check sequence.
        class FakeLocal:
            calls = []

            @classmethod
            def autoload(cls, java=None, plantuml=None):
                cls.calls.append(('local', java, plantuml))
                return cls()

        class FakeRemote:
            calls = []

            @classmethod
            def autoload(cls, host=None):
                cls.calls.append(('remote', host))
                return cls()

        monkeypatch.setattr(
            visualize_module, 'load_plantumlcli_classes',
            lambda: (FakeLocal, FakeRemote),
        )
        assert isinstance(visualize_module.create_local_plantuml_backend(), FakeLocal)
        assert isinstance(visualize_module.create_remote_plantuml_backend(), FakeRemote)
        assert FakeLocal.calls and FakeLocal.calls[0][0] == 'local'
        assert FakeRemote.calls and FakeRemote.calls[0][0] == 'remote'

    def test_run_plantumlcli_builtin_check_real_invocation_auto(self, capsys):
        # End-to-end run against the real plantumlcli library (it is a
        # required dev dependency). The ``auto`` mode prints check info
        # for both backends without raising even when one of them is
        # absent. We only assert the returned status dict has the
        # expected shape -- platform-specific outcomes are not stable
        # enough to assert on the booleans.
        status = visualize_module.run_plantumlcli_builtin_check('auto')
        assert set(status.keys()) == {'package', 'local', 'remote'}

    def test_run_plantumlcli_builtin_check_real_invocation_local_only(self, capsys):
        # plantumlcli's print_check_info raises PlantumlNotFound when the
        # selected backend is unavailable on this host. Use a stub for
        # print_check_info that records the call type, so the test
        # exercises run_plantumlcli_builtin_check's "renderer=='local'"
        # branch without depending on a real PlantUML installation.
        invocations = []

        def _stub_print_check_info(check_type, local_ok, local, remote_ok, remote):
            invocations.append((check_type, local_ok, remote_ok))

        from plantumlcli.entry import general as _gen
        # We deliberately replace the dotted attribute at import time;
        # run_plantumlcli_builtin_check imports print_check_info inside
        # the function body so the patch propagates into that scope.
        with patch.object(_gen, 'print_check_info', _stub_print_check_info):
            status = visualize_module.run_plantumlcli_builtin_check('local')
        assert 'local' in status
        assert invocations and invocations[0][0].name == 'LOCAL'

    def test_run_plantumlcli_builtin_check_real_invocation_remote_only(self, capsys):
        invocations = []

        def _stub_print_check_info(check_type, local_ok, local, remote_ok, remote):
            invocations.append((check_type, local_ok, remote_ok))

        from plantumlcli.entry import general as _gen
        with patch.object(_gen, 'print_check_info', _stub_print_check_info):
            status = visualize_module.run_plantumlcli_builtin_check('remote')
        assert 'remote' in status
        assert invocations and invocations[0][0].name == 'REMOTE'

    def test_run_plantumlcli_builtin_check_load_failure(self, monkeypatch):
        # When load_plantumlcli_classes raises ClickErrorException, the
        # check function returns the documented all-false status map.
        def _raise():
            raise ClickErrorException('plantumlcli missing in test stub')

        monkeypatch.setattr(visualize_module, 'load_plantumlcli_classes', _raise)
        status = visualize_module.run_plantumlcli_builtin_check('auto')
        assert status['package'][0] is False
        assert status['local'][0] is False
        assert status['remote'][0] is False
        assert 'plantumlcli missing' in status['package'][1]

    def test_render_plantuml_diagram_failure(self, tmp_path, monkeypatch):
        class DummyBackend:
            def check(self):
                return None

            def dump(self, *args, **kwargs):
                raise OSError('disk full')

        monkeypatch.setattr(visualize_module, 'create_local_plantuml_backend', lambda **kw: DummyBackend())
        with pytest.raises(ClickErrorException, match='Failed to render diagram with plantumlcli'):
            visualize_module.render_plantuml_diagram(
                '@startuml\n@enduml',
                tmp_path / 'out.png',
                'png',
                'local',
            )

    def test_render_plantuml_diagram_missing_output(self, tmp_path, monkeypatch):
        class SilentBackend:
            def check(self):
                return None

            def dump(self, *args, **kwargs):
                # Backend reports success but doesn't write the file.
                return None

        monkeypatch.setattr(visualize_module, 'create_local_plantuml_backend', lambda **kw: SilentBackend())
        with pytest.raises(ClickErrorException, match='plantumlcli reported success but no output file'):
            visualize_module.render_plantuml_diagram(
                '@startuml\n@enduml',
                tmp_path / 'out.png',
                'png',
                'local',
            )

    def test_detect_headless_environment_no_gui_env(self, monkeypatch):
        monkeypatch.setenv('PYFCSTM_NO_GUI', '1')
        is_headless, reason = visualize_module.detect_headless_environment()
        assert is_headless is True
        assert 'PYFCSTM_NO_GUI' in reason

    def test_detect_headless_environment_ci_env(self, monkeypatch):
        monkeypatch.delenv('PYFCSTM_NO_GUI', raising=False)
        monkeypatch.setenv('CI', '1')
        is_headless, reason = visualize_module.detect_headless_environment()
        assert is_headless is True
        assert 'CI environment' in reason

    def test_detect_headless_environment_linux_with_display(self, monkeypatch):
        monkeypatch.setattr(visualize_module.sys, 'platform', 'linux')
        monkeypatch.delenv('PYFCSTM_NO_GUI', raising=False)
        monkeypatch.delenv('CI', raising=False)
        monkeypatch.setenv('DISPLAY', ':0')
        is_headless, reason = visualize_module.detect_headless_environment()
        assert is_headless is False
        assert reason is None

    def test_open_diagram_in_headless_environment(self, tmp_path, monkeypatch):
        # Force headless so the function takes the early-return branch
        # without launching any system process.
        monkeypatch.setenv('PYFCSTM_NO_GUI', '1')
        opened, reason = visualize_module.open_diagram_with_default_app(tmp_path / 'noop.png')
        assert opened is False
        assert reason

    def test_open_diagram_no_opener_available(self, tmp_path, monkeypatch):
        # Pretend we're on linux with no xdg-open / gio in PATH -- exercises
        # the "no opener found" branch.
        monkeypatch.delenv('PYFCSTM_NO_GUI', raising=False)
        monkeypatch.delenv('CI', raising=False)
        monkeypatch.setenv('DISPLAY', ':0')
        monkeypatch.setattr(visualize_module.sys, 'platform', 'linux')
        monkeypatch.setattr(visualize_module.shutil, 'which', lambda _name: None)
        opened, reason = visualize_module.open_diagram_with_default_app(tmp_path / 'noop.png')
        assert opened is False
        assert 'No supported system opener' in reason

    def test_open_diagram_linux_xdg_open_invocation(self, tmp_path, monkeypatch):
        # Verify the xdg-open path runs subprocess.Popen with the file path
        # without leaking a real process. We replace Popen with a recorder.
        monkeypatch.delenv('PYFCSTM_NO_GUI', raising=False)
        monkeypatch.delenv('CI', raising=False)
        monkeypatch.setenv('DISPLAY', ':0')
        monkeypatch.setattr(visualize_module.sys, 'platform', 'linux')
        monkeypatch.setattr(visualize_module.shutil, 'which',
                            lambda name: '/usr/bin/xdg-open' if name == 'xdg-open' else None)
        invoked = {}

        class _RecPopen:
            def __init__(self, args, stdout=None, stderr=None):
                invoked['args'] = args

        monkeypatch.setattr(visualize_module.subprocess, 'Popen', _RecPopen)
        opened, reason = visualize_module.open_diagram_with_default_app(tmp_path / 'real.png')
        assert opened is True
        assert reason == ''
        assert invoked['args'][0] == '/usr/bin/xdg-open'
        assert invoked['args'][1].endswith('real.png')

    def test_open_diagram_linux_gio_fallback(self, tmp_path, monkeypatch):
        # When xdg-open is absent but gio is present, gio is invoked.
        monkeypatch.delenv('PYFCSTM_NO_GUI', raising=False)
        monkeypatch.delenv('CI', raising=False)
        monkeypatch.setenv('DISPLAY', ':0')
        monkeypatch.setattr(visualize_module.sys, 'platform', 'linux')
        monkeypatch.setattr(visualize_module.shutil, 'which',
                            lambda name: '/usr/bin/gio' if name == 'gio' else None)
        invoked = {}

        class _RecPopen:
            def __init__(self, args, stdout=None, stderr=None):
                invoked['args'] = args

        monkeypatch.setattr(visualize_module.subprocess, 'Popen', _RecPopen)
        opened, reason = visualize_module.open_diagram_with_default_app(tmp_path / 'real.png')
        assert opened is True
        assert invoked['args'][0] == '/usr/bin/gio'
        assert invoked['args'][1] == 'open'

    def test_open_diagram_oserror_during_launch(self, tmp_path, monkeypatch):
        monkeypatch.delenv('PYFCSTM_NO_GUI', raising=False)
        monkeypatch.delenv('CI', raising=False)
        monkeypatch.setenv('DISPLAY', ':0')
        monkeypatch.setattr(visualize_module.sys, 'platform', 'linux')
        monkeypatch.setattr(visualize_module.shutil, 'which',
                            lambda name: '/usr/bin/xdg-open' if name == 'xdg-open' else None)

        def _boom(*args, **kwargs):
            raise OSError('exec failure')

        monkeypatch.setattr(visualize_module.subprocess, 'Popen', _boom)
        opened, reason = visualize_module.open_diagram_with_default_app(tmp_path / 'real.png')
        assert opened is False
        assert 'exec failure' in reason

    def test_visualize_missing_input_without_check(self, monkeypatch):
        # Trigger the "input DSL file is required unless --check is used."
        # error branch by invoking visualize with no -i and no --check.
        result = simulate_entry(
            pyfcstmcli,
            [
                'pyfcstm',
                'visualize',
            ],
        )
        assert result.exitcode != 0
        assert 'Input DSL file is required' in (result.stderr or result.stdout)

    def test_visualize_check_local_only_unavailable(self, monkeypatch):
        def _check(renderer, **kw):
            return {
                'package': (True, 'ok'),
                'local': (False, 'unavailable'),
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
                'local',
            ],
        )
        # Local-only check, local unavailable -> exit non-zero.
        assert result.exitcode != 0

    def test_visualize_check_remote_only_available(self, monkeypatch):
        def _check(renderer, **kw):
            return {
                'package': (True, 'ok'),
                'local': (False, 'unavailable'),
                'remote': (True, 'available'),
            }

        monkeypatch.setattr(visualize_module, 'run_plantumlcli_builtin_check', _check)
        result = simulate_entry(
            pyfcstmcli,
            [
                'pyfcstm',
                'visualize',
                '--check',
                '--renderer',
                'remote',
            ],
        )
        assert result.exitcode == 0
