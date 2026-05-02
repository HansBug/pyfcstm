#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test CLI executable functionality

This script tests the built CLI executable to ensure all core functionality works correctly.
"""
import argparse
import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path


# Use ASCII-safe symbols for cross-platform compatibility
CHECK_MARK = '[OK]'
CROSS_MARK = '[FAIL]'


class CLITester:
    def __init__(self, cli_path):
        self.cli_path = cli_path
        self.test_results = []
        self.failed_tests = []

    def run_command(self, args, check=True, timeout=30):
        """Run CLI command and return result"""
        cmd = [self.cli_path] + args
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            if check:
                # Surface the actual CLI stdout/stderr before re-raising so
                # CI logs let us diagnose missing-bundle / missing-binary
                # failures without a second round-trip.
                print("  [FAIL] command exited {}: {}".format(
                    e.returncode, ' '.join(cmd)
                ))
                if e.stdout:
                    print("  ----- stdout -----")
                    for line in str(e.stdout).splitlines():
                        print("    " + line)
                if e.stderr:
                    print("  ----- stderr -----")
                    for line in str(e.stderr).splitlines():
                        print("    " + line)
                raise
            return e
        except subprocess.TimeoutExpired as e:
            print(f"[FAIL] Command timed out: {' '.join(cmd)}")
            raise

    def test_version(self):
        """Test --version flag"""
        print("Testing --version...")
        result = self.run_command(['-v'])
        assert 'Pyfcstm' in result.stdout or 'pyfcstm' in result.stdout.lower(), \
            f"Version output doesn't contain 'Pyfcstm': {result.stdout}"
        print(f"  [OK] Version: {result.stdout.strip()}")
        self.test_results.append(('version', True))

    def test_help(self):
        """Test --help flag"""
        print("Testing --help...")
        result = self.run_command(['-h'])
        assert 'Usage:' in result.stdout or 'usage:' in result.stdout.lower(), \
            "Help output doesn't contain usage information"
        assert 'plantuml' in result.stdout.lower(), \
            "Help output doesn't mention plantuml command"
        assert 'generate' in result.stdout.lower(), \
            "Help output doesn't mention generate command"
        print("  [OK] Help output looks correct")
        self.test_results.append(('help', True))

    def test_plantuml_generation(self, test_dsl_file):
        """Test PlantUML generation"""
        print("Testing PlantUML generation...")

        with tempfile.NamedTemporaryFile(mode='w', suffix='.puml', delete=False) as f:
            output_file = f.name

        try:
            result = self.run_command([
                'plantuml',
                '-i', test_dsl_file,
                '-o', output_file
            ])

            # Check output file exists and has content
            assert os.path.exists(output_file), "Output file was not created"

            with open(output_file, 'r') as f:
                content = f.read()

            assert len(content) > 0, "Output file is empty"
            assert '@startuml' in content, "Output doesn't contain @startuml"
            assert '@enduml' in content, "Output doesn't contain @enduml"

            print(f"  [OK] Generated PlantUML ({len(content)} bytes)")
            self.test_results.append(('plantuml', True))
        finally:
            if os.path.exists(output_file):
                os.unlink(output_file)

    def test_code_generation(self, test_dsl_file, template_dir):
        """Test code generation with template"""
        print("Testing code generation...")

        with tempfile.TemporaryDirectory() as output_dir:
            result = self.run_command([
                'generate',
                '-i', test_dsl_file,
                '-t', template_dir,
                '-o', output_dir,
                '--clear'
            ])

            # Check that files were generated
            generated_files = list(Path(output_dir).rglob('*'))
            generated_files = [f for f in generated_files if f.is_file()]

            assert len(generated_files) > 0, "No files were generated"

            print(f"  [OK] Generated {len(generated_files)} file(s)")
            self.test_results.append(('generate', True))

    def test_builtin_python_template_generation(self):
        """Test built-in python template generation and basic generated runtime behavior"""
        print("Testing built-in python template generation...")

        dsl_code = """
def int counter = 0;
state CliBuiltin {
    state Idle {
        during { counter = counter + 1; }
    }
    state Running {
        during { counter = counter + 100; }
    }
    [*] -> Idle;
    Idle -> Running :: Start effect { counter = counter + 10; };
}
"""

        dsl_file = None
        with tempfile.TemporaryDirectory() as output_dir:
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.fcstm',
                    delete=False,
                    encoding='utf-8',
                ) as f:
                    f.write(dsl_code)
                    dsl_file = f.name

                self.run_command([
                    'generate',
                    '-i', dsl_file,
                    '--template', 'python',
                    '-o', output_dir,
                    '--clear'
                ])

                machine_file = Path(output_dir) / 'machine.py'
                readme_file = Path(output_dir) / 'README.md'
                assert machine_file.exists(), "Built-in python template did not generate machine.py"
                assert readme_file.exists(), "Built-in python template did not generate README.md"

                validation_script = """
import importlib.util
from pathlib import Path

module_path = Path('machine.py')
spec = importlib.util.spec_from_file_location('generated_machine', str(module_path))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

machine_cls = module.CliBuiltinMachine
machine = machine_cls()

assert tuple(machine.current_state_path) == ('CliBuiltin',)
assert dict(machine.vars) == {'counter': 0}
assert machine_cls.DSL_SOURCE.strip().startswith('def int counter = 0;')
assert 'CliBuiltin.Idle' in machine_cls.STATE_PATHS

machine.cycle()
assert tuple(machine.current_state_path) == ('CliBuiltin', 'Idle')
assert dict(machine.vars) == {'counter': 1}

machine.cycle(['Start'])
assert tuple(machine.current_state_path) == ('CliBuiltin', 'Running')
assert dict(machine.vars) == {'counter': 111}

print('builtin_python_template_ok')
"""
                validation = subprocess.run(
                    [sys.executable, '-c', validation_script],
                    cwd=output_dir,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,
                )
                if validation.returncode != 0:
                    print(f"  [FAIL] Generated runtime validation failed with exit code {validation.returncode}")
                    print(f"  stdout: {validation.stdout}")
                    print(f"  stderr: {validation.stderr}")
                    raise AssertionError("Generated runtime validation failed")

                assert 'builtin_python_template_ok' in validation.stdout, (
                    "Generated runtime validation script did not finish successfully"
                )

                print("  [OK] Built-in python template generated and runtime validation succeeded")
                self.test_results.append(('builtin_python_template', True))
            finally:
                if dsl_file and os.path.exists(dsl_file):
                    os.unlink(dsl_file)

    def test_error_handling(self):
        """Test error handling with invalid input"""
        print("Testing error handling...")

        # Test with non-existent file
        result = self.run_command([
            'plantuml',
            '-i', '/nonexistent/file.fcstm',
            '-o', '/tmp/output.puml'
        ], check=False)

        assert result.returncode != 0, "Should fail with non-existent file"
        print("  [OK] Correctly handles non-existent file")
        self.test_results.append(('error_handling', True))

    def test_simulate_help(self):
        """Test simulate command help"""
        print("Testing simulate --help...")
        result = self.run_command(['simulate', '-h'])
        assert 'Interactive state machine simulator' in result.stdout, \
            "Simulate help doesn't contain description"
        assert '--input-code' in result.stdout or '-i' in result.stdout, \
            "Simulate help doesn't mention input-code option"
        assert '--execute' in result.stdout or '-e' in result.stdout, \
            "Simulate help doesn't mention execute option"
        assert '--no-color' in result.stdout, \
            "Simulate help doesn't mention no-color option"
        print("  [OK] Simulate help output looks correct")
        self.test_results.append(('simulate_help', True))

    def test_simulate_batch_mode(self, test_dsl_file):
        """Test simulate command in batch mode"""
        print("Testing simulate batch mode...")

        # Test basic batch execution
        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', 'current',
            '--no-color'
        ], check=False)

        if result.returncode != 0:
            print(f"  [FAIL] Command failed with exit code {result.returncode}")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            raise AssertionError(f"Simulate batch mode failed with exit code {result.returncode}")

        assert 'State:' in result.stdout or 'state' in result.stdout.lower(), \
            f"Batch output doesn't contain state information. stdout: {result.stdout}"
        print("  [OK] Batch mode execution successful")
        self.test_results.append(('simulate_batch', True))

    def test_simulate_batch_cycle(self, test_dsl_file):
        """Test simulate command with cycle execution"""
        print("Testing simulate batch cycle...")

        # Test cycle command
        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', 'cycle; current',
            '--no-color'
        ], check=False)

        if result.returncode != 0:
            print(f"  [FAIL] Command failed with exit code {result.returncode}")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            raise AssertionError(f"Simulate cycle failed with exit code {result.returncode}")

        assert 'Cycle' in result.stdout or 'cycle' in result.stdout.lower(), \
            f"Cycle output doesn't contain cycle information. stdout: {result.stdout}"
        print("  [OK] Cycle execution successful")
        self.test_results.append(('simulate_cycle', True))

    def test_simulate_batch_multiple_commands(self, test_dsl_file):
        """Test simulate command with multiple batch commands"""
        print("Testing simulate multiple batch commands...")

        # Test multiple commands
        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', 'current; cycle; current; events',
            '--no-color'
        ], check=False)

        if result.returncode != 0:
            print(f"  [FAIL] Command failed with exit code {result.returncode}")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            raise AssertionError(f"Simulate multiple commands failed with exit code {result.returncode}")

        # Should have output from multiple commands
        assert result.stdout.count('State:') >= 2 or result.stdout.count('state') >= 2, \
            f"Multiple commands output doesn't show multiple states. stdout: {result.stdout}"
        print("  [OK] Multiple batch commands successful")
        self.test_results.append(('simulate_multiple', True))

    def test_simulate_batch_history(self, test_dsl_file):
        """Test simulate command with history"""
        print("Testing simulate batch history...")

        # Test history command
        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', 'cycle; cycle; history',
            '--no-color'
        ], check=False)

        if result.returncode != 0:
            print(f"  [FAIL] Command failed with exit code {result.returncode}")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            raise AssertionError(f"Simulate history failed with exit code {result.returncode}")

        # History should show cycle information
        assert 'Cycle' in result.stdout or 'cycle' in result.stdout.lower(), \
            f"History output doesn't contain cycle information. stdout: {result.stdout}"
        print("  [OK] History command successful")
        self.test_results.append(('simulate_history', True))

    def test_simulate_batch_settings(self, test_dsl_file):
        """Test simulate command with settings"""
        print("Testing simulate batch settings...")

        # Test settings command
        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', 'setting; setting color off; setting',
            '--no-color'
        ], check=False)

        if result.returncode != 0:
            print(f"  [FAIL] Command failed with exit code {result.returncode}")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            raise AssertionError(f"Simulate settings failed with exit code {result.returncode}")

        # Should show settings
        assert 'color' in result.stdout.lower() or 'setting' in result.stdout.lower(), \
            f"Settings output doesn't contain setting information. stdout: {result.stdout}"
        print("  [OK] Settings command successful")
        self.test_results.append(('simulate_settings', True))

    def test_simulate_no_color(self, test_dsl_file):
        """Test simulate command with --no-color flag"""
        print("Testing simulate --no-color...")

        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', 'current',
            '--no-color'
        ], check=False)

        if result.returncode != 0:
            print(f"  [FAIL] Command failed with exit code {result.returncode}")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            raise AssertionError(f"Simulate no-color failed with exit code {result.returncode}")

        # Check that output doesn't contain ANSI escape codes
        assert '\x1b[' not in result.stdout, \
            f"Output contains ANSI codes despite --no-color flag. stdout: {result.stdout}"
        print("  [OK] No-color mode working correctly")
        self.test_results.append(('simulate_no_color', True))

    def test_simulate_batch_clear(self, test_dsl_file):
        """Test simulate command with clear/reset"""
        print("Testing simulate batch clear...")

        # Test clear command
        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', 'cycle; clear; current',
            '--no-color'
        ], check=False)

        if result.returncode != 0:
            print(f"  [FAIL] Command failed with exit code {result.returncode}")
            print(f"  stdout: {result.stdout}")
            print(f"  stderr: {result.stderr}")
            raise AssertionError(f"Simulate clear failed with exit code {result.returncode}")

        # Should show state after reset
        assert 'State:' in result.stdout or 'state' in result.stdout.lower(), \
            f"Clear output doesn't contain state information. stdout: {result.stdout}"
        print("  [OK] Clear command successful")
        self.test_results.append(('simulate_clear', True))

    def test_simulate_error_invalid_file(self):
        """Test simulate command with invalid file"""
        print("Testing simulate with invalid file...")

        result = self.run_command([
            'simulate',
            '-i', '/nonexistent/file.fcstm',
            '-e', 'current'
        ], check=False)

        # Check for error message (exit code may be 0 due to graceful error handling)
        if result.returncode != 0:
            print("  [OK] Correctly handles invalid file (exit code)")
        elif 'Failed to parse' in result.stdout or 'No such file' in result.stdout or \
             'Failed to parse' in result.stderr or 'No such file' in result.stderr:
            print("  [OK] Correctly reports invalid file (error message)")
        else:
            raise AssertionError(f"Should handle invalid file. stdout: {result.stdout}, stderr: {result.stderr}")
        self.test_results.append(('simulate_error_file', True))

    def test_sysdesim_main_help(self):
        """``sysdesim -h`` lists the four subcommands."""
        print("Testing sysdesim --help...")
        result = self.run_command(['sysdesim', '-h'])
        for needle in ('sequence-render', 'validate', 'static-check'):
            assert needle in result.stdout, (
                "sysdesim help missing subcommand {!r}: {}".format(
                    needle, result.stdout
                )
            )
        print("  [OK] sysdesim help lists all subcommands")
        self.test_results.append(('sysdesim_main_help', True))

    def test_sysdesim_convert_simple(self, simple_xml):
        """``sysdesim -i linear.xml -o out`` writes the expected single .fcstm."""
        print("Testing sysdesim convert (linear fixture)...")
        with tempfile.TemporaryDirectory() as out_dir:
            self.run_command([
                'sysdesim',
                '-i', simple_xml,
                '-o', out_dir,
                '--clear',
            ], timeout=120)
            files = sorted(p.name for p in Path(out_dir).glob('*.fcstm'))
            assert files == ['Greeter.fcstm'], (
                "Expected single Greeter.fcstm, got {}".format(files)
            )
            content = (Path(out_dir) / 'Greeter.fcstm').read_text(encoding='utf-8')
            for needle in ('state Idle', 'state Greeting', 'state Done',
                           'Hello', 'Bye'):
                assert needle in content, \
                    "Greeter.fcstm missing token {!r}: {!r}".format(needle, content[:200])
            print("  [OK] sysdesim convert produced {} ({} bytes)".format(
                files[0], len(content)
            ))
            self.test_results.append(('sysdesim_convert_simple', True))

    def test_sysdesim_convert_parallel_split(self, complex_xml):
        """``sysdesim -i parallel.xml -o out`` emits the parallel-split family."""
        print("Testing sysdesim convert (parallel fixture)...")
        with tempfile.TemporaryDirectory() as out_dir:
            result = self.run_command([
                'sysdesim',
                '-i', complex_xml,
                '-o', out_dir,
                '--clear',
            ], timeout=120)
            files = sorted(p.name for p in Path(out_dir).glob('*.fcstm'))
            # Must contain the main + 2 region-split outputs.
            assert any('TimelineCoexist' in n for n in files), (
                "Expected TimelineCoexist.fcstm-family in {}".format(files)
            )
            assert len(files) >= 3, (
                "Expected >=3 outputs (main + 2 regions), got {}".format(files)
            )
            assert 'parallel-split' in result.stdout, (
                "Expected diagnostics summary mentioning parallel-split"
            )
            print("  [OK] sysdesim convert produced {} outputs".format(len(files)))
            self.test_results.append(('sysdesim_convert_parallel', True))

    def test_sysdesim_static_check_clean(self, simple_xml):
        """``sysdesim static-check`` reports OK on the linear fixture."""
        print("Testing sysdesim static-check (linear fixture)...")
        result = self.run_command([
            'sysdesim', 'static-check',
            '-i', simple_xml,
        ], timeout=120)
        assert 'OK' in result.stdout or 'no static issues' in result.stdout, (
            "static-check did not report OK: {}".format(result.stdout)
        )
        print("  [OK] static-check reports OK on linear fixture")
        self.test_results.append(('sysdesim_static_check_clean', True))

    def test_sysdesim_static_check_warns(self, complex_xml):
        """``sysdesim static-check`` surfaces the planted Sig2-dropped warning."""
        print("Testing sysdesim static-check (parallel fixture)...")
        result = self.run_command([
            'sysdesim', 'static-check',
            '-i', complex_xml,
        ], timeout=120)
        # The fixture intentionally drops Sig2 in region_left so static-check
        # has something to report. We accept any of the standard warning
        # markers, but require at least one.
        assert (
            'warning' in result.stdout.lower()
            or 'WARN' in result.stdout
            or 'signal_dropped_in_state' in result.stdout
        ), "Expected dropped-signal warning, got: {}".format(result.stdout)
        print("  [OK] static-check surfaced expected warning")
        self.test_results.append(('sysdesim_static_check_warns', True))

    def test_sysdesim_validate_simple(self, simple_xml):
        """``sysdesim validate`` produces an import report for the linear fixture."""
        print("Testing sysdesim validate (linear fixture)...")
        result = self.run_command([
            'sysdesim', 'validate',
            '-i', simple_xml,
        ], timeout=180)
        for needle in ('HandshakeScenario', 'Initial States',
                       'Greeter', 'Scenario'):
            assert needle in result.stdout, (
                "validate output missing {!r}: {}".format(needle, result.stdout)
            )
        print("  [OK] validate produced expected report")
        self.test_results.append(('sysdesim_validate_simple', True))

    def test_sysdesim_validate_with_report_file(self, simple_xml):
        """``sysdesim validate --report-file`` writes a JSON report we can parse."""
        print("Testing sysdesim validate --report-file...")
        import json as _json
        with tempfile.TemporaryDirectory() as tmp:
            report_path = os.path.join(tmp, 'report.json')
            self.run_command([
                'sysdesim', 'validate',
                '-i', simple_xml,
                '--report-file', report_path,
            ], timeout=180)
            assert os.path.exists(report_path), "report.json not written"
            payload = _json.loads(Path(report_path).read_text(encoding='utf-8'))
            for key in ('phase78', 'phase9', 'phase10', 'static_check'):
                assert key in payload, "report missing top-level key {!r}".format(key)
            print("  [OK] validate report.json parsed, top-level keys present")
            self.test_results.append(('sysdesim_validate_report', True))

    def test_sysdesim_sequence_render_help(self):
        """``sysdesim sequence-render -h`` lists the new flags."""
        print("Testing sysdesim sequence-render --help...")
        result = self.run_command(['sysdesim', 'sequence-render', '-h'])
        for needle in ('--input-xml', '--output', '--format', '--preview', '--font-file'):
            assert needle in result.stdout, (
                "sequence-render help missing {!r}: {}".format(needle, result.stdout)
            )
        print("  [OK] sysdesim sequence-render help looks correct")
        self.test_results.append(('sysdesim_sequence_render_help', True))

    def test_sysdesim_sequence_render_svg(self, xml_path, expected_signals):
        """``sysdesim sequence-render -i x.xml -o y.svg`` writes a valid SVG."""
        print("Testing sysdesim sequence-render -> SVG ({})...".format(
            Path(xml_path).name
        ))
        with tempfile.TemporaryDirectory() as tmp:
            out_svg = os.path.join(tmp, 'seq.svg')
            self.run_command([
                'sysdesim', 'sequence-render',
                '-i', xml_path,
                '-o', out_svg,
            ], timeout=120)
            assert os.path.exists(out_svg), "SVG output file not created"
            text = Path(out_svg).read_text(encoding='utf-8')
            assert text.startswith('<?xml'), \
                "SVG missing XML prolog: {!r}".format(text[:80])
            assert '<svg' in text and '</svg>' in text, "SVG missing svg tags"
            assert 'viewBox' in text, "SVG missing viewBox attr"
            for needle in expected_signals:
                assert needle in text, \
                    "SVG missing expected token {!r}".format(needle)
            print("  [OK] SVG produced {} bytes".format(len(text)))
            self.test_results.append(
                ('sysdesim_seq_render_svg__' + Path(xml_path).stem, True)
            )

    def test_sysdesim_sequence_render_png(self, xml_path):
        """``sysdesim sequence-render -i x.xml -o y.png`` produces a valid PNG via resvg-wasm."""
        print("Testing sysdesim sequence-render -> PNG ({}, mini-racer + resvg-wasm)...".format(
            Path(xml_path).name
        ))
        with tempfile.TemporaryDirectory() as tmp:
            out_png = os.path.join(tmp, 'seq.png')
            self.run_command([
                'sysdesim', 'sequence-render',
                '-i', xml_path,
                '-o', out_png,
            ], timeout=120)
            assert os.path.exists(out_png), "PNG output file not created"
            data = Path(out_png).read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n', \
                "PNG magic bytes missing: {!r}".format(data[:16])
            width, height = struct.unpack('>II', data[16:24])
            assert width > 100 and height > 100, \
                "PNG dimensions look wrong: {}x{}".format(width, height)
            # IDAT chunk ought to be sizable on a real-rendered diagram;
            # an all-white empty render would be tiny.
            assert len(data) > 1500, \
                "PNG looks suspiciously small ({} bytes); rasterizer may have rendered nothing".format(len(data))
            print("  [OK] PNG produced {}x{} ({} bytes)".format(width, height, len(data)))
            self.test_results.append(
                ('sysdesim_seq_render_png__' + Path(xml_path).stem, True)
            )

    def test_sysdesim_sequence_render_format_flag(self, xml_path):
        """``--format png`` overrides extension inference."""
        print("Testing sysdesim sequence-render --format png on .bin path...")
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, 'seq.bin')
            self.run_command([
                'sysdesim', 'sequence-render',
                '-i', xml_path,
                '-o', out_path,
                '--format', 'png',
            ], timeout=120)
            data = Path(out_path).read_bytes()
            assert data[:8] == b'\x89PNG\r\n\x1a\n', \
                "PNG magic bytes missing under --format png override"
            print("  [OK] --format png override works")
            self.test_results.append(('sysdesim_seq_render_format_flag', True))

    def test_sysdesim_sequence_render_no_output(self, xml_path):
        """Without -o or --preview, the CLI should refuse cleanly."""
        print("Testing sysdesim sequence-render with neither -o nor --preview...")
        result = self.run_command([
            'sysdesim', 'sequence-render',
            '-i', xml_path,
        ], check=False, timeout=30)
        assert result.returncode != 0, "Expected non-zero exit when no output specified"
        # Click error message is on stderr by default but click_error_exception
        # may print to stdout depending on click version. Check both.
        combined = (result.stdout or '') + (result.stderr or '')
        assert (
            '--output' in combined or '--preview' in combined or 'Provide' in combined
        ), "Expected helpful error message, got stdout={!r} stderr={!r}".format(
            result.stdout, result.stderr
        )
        print("  [OK] CLI refuses cleanly without output target")
        self.test_results.append(('sysdesim_seq_render_no_output', True))

    def test_simulate_error_invalid_command(self, test_dsl_file):
        """Test simulate command with invalid batch command"""
        print("Testing simulate with invalid command...")

        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', 'invalid_command_xyz',
            '--no-color'
        ], check=False)

        # Should either fail or show error message
        if result.returncode != 0:
            print("  [OK] Correctly rejects invalid command (exit code)")
        elif 'Unknown command' in result.stdout or 'unknown' in result.stdout.lower():
            print("  [OK] Correctly reports invalid command (error message)")
        else:
            raise AssertionError("Should handle invalid command")
        self.test_results.append(('simulate_error_command', True))

    def run_all_tests(self, test_dsl_file=None, template_dir=None,
                      sysdesim_fixtures_dir=None):
        """Run all tests"""
        print(f"\n{'='*60}")
        print(f"Testing CLI: {self.cli_path}")
        print(f"{'='*60}\n")

        tests = [
            ('Version flag', self.test_version),
            ('Help flag', self.test_help),
            ('Built-in python template generation', self.test_builtin_python_template_generation),
            ('Error handling', self.test_error_handling),
        ]

        if test_dsl_file and os.path.exists(test_dsl_file):
            tests.append(('PlantUML generation', lambda: self.test_plantuml_generation(test_dsl_file)))

            if template_dir and os.path.exists(template_dir):
                tests.append(('Code generation', lambda: self.test_code_generation(test_dsl_file, template_dir)))

            # Add simulate command tests
            tests.extend([
                ('Simulate help', self.test_simulate_help),
                ('Simulate batch mode', lambda: self.test_simulate_batch_mode(test_dsl_file)),
                ('Simulate batch cycle', lambda: self.test_simulate_batch_cycle(test_dsl_file)),
                ('Simulate multiple commands', lambda: self.test_simulate_batch_multiple_commands(test_dsl_file)),
                ('Simulate history', lambda: self.test_simulate_batch_history(test_dsl_file)),
                ('Simulate settings', lambda: self.test_simulate_batch_settings(test_dsl_file)),
                ('Simulate clear', lambda: self.test_simulate_batch_clear(test_dsl_file)),
                ('Simulate no-color', lambda: self.test_simulate_no_color(test_dsl_file)),
                ('Simulate error invalid file', self.test_simulate_error_invalid_file),
                ('Simulate error invalid command', lambda: self.test_simulate_error_invalid_command(test_dsl_file)),
            ])

        if sysdesim_fixtures_dir and os.path.isdir(sysdesim_fixtures_dir):
            simple_xml = os.path.join(
                sysdesim_fixtures_dir, 'linear_handshake_sample.xml'
            )
            complex_xml = os.path.join(
                sysdesim_fixtures_dir, 'parallel_timeline_sample.xml'
            )
            if os.path.exists(simple_xml) and os.path.exists(complex_xml):
                tests.extend([
                    ('Sysdesim main help', self.test_sysdesim_main_help),
                    # convert (both fixtures: clean single-output + parallel-split)
                    ('Sysdesim convert (linear)',
                        lambda: self.test_sysdesim_convert_simple(simple_xml)),
                    ('Sysdesim convert (parallel-split)',
                        lambda: self.test_sysdesim_convert_parallel_split(complex_xml)),
                    # static-check (clean OK + with warning)
                    ('Sysdesim static-check OK',
                        lambda: self.test_sysdesim_static_check_clean(simple_xml)),
                    ('Sysdesim static-check warns',
                        lambda: self.test_sysdesim_static_check_warns(complex_xml)),
                    # validate (text report + JSON report file)
                    ('Sysdesim validate (linear)',
                        lambda: self.test_sysdesim_validate_simple(simple_xml)),
                    ('Sysdesim validate --report-file',
                        lambda: self.test_sysdesim_validate_with_report_file(simple_xml)),
                    # sequence-render (help + SVG/PNG on both fixtures + flags)
                    ('Sysdesim sequence-render help',
                        self.test_sysdesim_sequence_render_help),
                    ('Sysdesim sequence-render SVG (linear)',
                        lambda: self.test_sysdesim_sequence_render_svg(
                            simple_xml, ['Hello', 'Bye', 'sender', 'receiver'])),
                    ('Sysdesim sequence-render SVG (parallel)',
                        lambda: self.test_sysdesim_sequence_render_svg(
                            complex_xml,
                            ['Sig1', 'Sig2', 'Sig4', 'Sig9', 'control', 'module'])),
                    ('Sysdesim sequence-render PNG (linear)',
                        lambda: self.test_sysdesim_sequence_render_png(simple_xml)),
                    ('Sysdesim sequence-render PNG (parallel)',
                        lambda: self.test_sysdesim_sequence_render_png(complex_xml)),
                    ('Sysdesim sequence-render --format flag',
                        lambda: self.test_sysdesim_sequence_render_format_flag(simple_xml)),
                    ('Sysdesim sequence-render no-output error',
                        lambda: self.test_sysdesim_sequence_render_no_output(simple_xml)),
                ])

        for test_name, test_func in tests:
            try:
                test_func()
            except Exception as e:
                print(f"  [FAIL] {test_name} failed: {e}")
                self.test_results.append((test_name, False))
                self.failed_tests.append((test_name, str(e)))

        # Print summary
        print(f"\n{'='*60}")
        print("Test Summary")
        print(f"{'='*60}")

        passed = sum(1 for _, result in self.test_results if result)
        total = len(self.test_results)

        print(f"Passed: {passed}/{total}")

        if self.failed_tests:
            print("\nFailed tests:")
            for test_name, error in self.failed_tests:
                print(f"  [FAIL] {test_name}: {error}")
            return False
        else:
            print("\n[OK] All tests passed!")
            return True


def main():
    parser = argparse.ArgumentParser(description='Test CLI executable')
    parser.add_argument('cli_path', help='Path to CLI executable')
    parser.add_argument('--test-dsl', help='Path to test DSL file')
    parser.add_argument('--template-dir', help='Path to template directory')
    parser.add_argument('--sysdesim-fixtures-dir',
                        help='Directory holding SysDeSim XML/XMI samples '
                             '(linear_handshake_sample.xml + '
                             'parallel_timeline_sample.xml). When supplied, '
                             'enables the full sysdesim CLI smoke suite '
                             '(convert / validate / static-check / sequence-render).')

    args = parser.parse_args()

    if not os.path.exists(args.cli_path):
        print(f"Error: CLI executable not found: {args.cli_path}")
        sys.exit(1)

    tester = CLITester(args.cli_path)
    success = tester.run_all_tests(
        test_dsl_file=args.test_dsl,
        template_dir=args.template_dir,
        sysdesim_fixtures_dir=args.sysdesim_fixtures_dir,
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
