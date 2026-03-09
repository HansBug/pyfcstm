#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test CLI executable functionality

This script tests the built CLI executable to ensure all core functionality works correctly.
"""
import argparse
import os
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
            '-e', '/current',
            '--no-color'
        ])

        assert result.returncode == 0, f"Simulate batch mode failed: {result.stderr}"
        assert 'State:' in result.stdout or 'state' in result.stdout.lower(), \
            "Batch output doesn't contain state information"
        print("  [OK] Batch mode execution successful")
        self.test_results.append(('simulate_batch', True))

    def test_simulate_batch_cycle(self, test_dsl_file):
        """Test simulate command with cycle execution"""
        print("Testing simulate batch cycle...")

        # Test cycle command
        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', '/cycle; /current',
            '--no-color'
        ])

        assert result.returncode == 0, f"Simulate cycle failed: {result.stderr}"
        assert 'Cycle' in result.stdout or 'cycle' in result.stdout.lower(), \
            "Cycle output doesn't contain cycle information"
        print("  [OK] Cycle execution successful")
        self.test_results.append(('simulate_cycle', True))

    def test_simulate_batch_multiple_commands(self, test_dsl_file):
        """Test simulate command with multiple batch commands"""
        print("Testing simulate multiple batch commands...")

        # Test multiple commands
        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', '/current; /cycle; /current; /events',
            '--no-color'
        ])

        assert result.returncode == 0, f"Simulate multiple commands failed: {result.stderr}"
        # Should have output from multiple commands
        assert result.stdout.count('State:') >= 2 or result.stdout.count('state') >= 2, \
            "Multiple commands output doesn't show multiple states"
        print("  [OK] Multiple batch commands successful")
        self.test_results.append(('simulate_multiple', True))

    def test_simulate_batch_history(self, test_dsl_file):
        """Test simulate command with history"""
        print("Testing simulate batch history...")

        # Test history command
        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', '/cycle; /cycle; /history',
            '--no-color'
        ])

        assert result.returncode == 0, f"Simulate history failed: {result.stderr}"
        # History should show cycle information
        assert 'Cycle' in result.stdout or 'cycle' in result.stdout.lower(), \
            "History output doesn't contain cycle information"
        print("  [OK] History command successful")
        self.test_results.append(('simulate_history', True))

    def test_simulate_batch_settings(self, test_dsl_file):
        """Test simulate command with settings"""
        print("Testing simulate batch settings...")

        # Test settings command
        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', '/setting; /setting color off; /setting',
            '--no-color'
        ])

        assert result.returncode == 0, f"Simulate settings failed: {result.stderr}"
        # Should show settings
        assert 'color' in result.stdout.lower() or 'setting' in result.stdout.lower(), \
            "Settings output doesn't contain setting information"
        print("  [OK] Settings command successful")
        self.test_results.append(('simulate_settings', True))

    def test_simulate_no_color(self, test_dsl_file):
        """Test simulate command with --no-color flag"""
        print("Testing simulate --no-color...")

        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', '/current',
            '--no-color'
        ])

        assert result.returncode == 0, f"Simulate no-color failed: {result.stderr}"
        # Check that output doesn't contain ANSI escape codes
        assert '\x1b[' not in result.stdout, \
            "Output contains ANSI codes despite --no-color flag"
        print("  [OK] No-color mode working correctly")
        self.test_results.append(('simulate_no_color', True))

    def test_simulate_batch_clear(self, test_dsl_file):
        """Test simulate command with clear/reset"""
        print("Testing simulate batch clear...")

        # Test clear command
        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', '/cycle; /clear; /current',
            '--no-color'
        ])

        assert result.returncode == 0, f"Simulate clear failed: {result.stderr}"
        # Should show state after reset
        assert 'State:' in result.stdout or 'state' in result.stdout.lower(), \
            "Clear output doesn't contain state information"
        print("  [OK] Clear command successful")
        self.test_results.append(('simulate_clear', True))

    def test_simulate_error_invalid_file(self):
        """Test simulate command with invalid file"""
        print("Testing simulate with invalid file...")

        result = self.run_command([
            'simulate',
            '-i', '/nonexistent/file.fcstm',
            '-e', '/current'
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

    def test_simulate_error_invalid_command(self, test_dsl_file):
        """Test simulate command with invalid batch command"""
        print("Testing simulate with invalid command...")

        result = self.run_command([
            'simulate',
            '-i', test_dsl_file,
            '-e', '/invalid_command_xyz',
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

    def run_all_tests(self, test_dsl_file=None, template_dir=None):
        """Run all tests"""
        print(f"\n{'='*60}")
        print(f"Testing CLI: {self.cli_path}")
        print(f"{'='*60}\n")

        tests = [
            ('Version flag', self.test_version),
            ('Help flag', self.test_help),
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

    args = parser.parse_args()

    if not os.path.exists(args.cli_path):
        print(f"Error: CLI executable not found: {args.cli_path}")
        sys.exit(1)

    tester = CLITester(args.cli_path)
    success = tester.run_all_tests(
        test_dsl_file=args.test_dsl,
        template_dir=args.template_dir
    )

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
