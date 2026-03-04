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
