#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This script modifies requirements.txt to ensure antlr4-python3-runtime has the correct version.
It either replaces an existing entry or adds a new one if not found.
"""

import argparse
import os
import re
import sys


def update_requirements(file_path, version):
    """
    Update the requirements.txt file to set antlr4-python3-runtime to the specified version.

    Args:
        file_path (str): Path to requirements.txt
        version (str): Version to set for antlr4-python3-runtime
    """
    try:
        # Read the current requirements file
        with open(file_path, 'r') as file:
            lines = file.readlines()

        # Check if antlr4-python3-runtime is already in the file
        pattern = re.compile(r'^antlr4-python3-runtime.*$')
        found = False

        for i, line in enumerate(lines):
            if pattern.match(line.strip()):
                # Replace the existing entry
                lines[i] = f"antlr4-python3-runtime=={version}{os.linesep}"
                found = True
                break

        # If not found, add it to the end
        if not found:
            if lines and not lines[-1].endswith(os.linesep):
                lines.append(os.linesep)  # Ensure there's a newline before adding
            lines.append(f"antlr4-python3-runtime=={version}{os.linesep}")

        # Write the updated content back to the file
        with open(file_path, 'w') as file:
            file.writelines(lines)

        print(f"Successfully updated antlr4-python3-runtime to version {version} in {file_path}")

    except FileNotFoundError:
        # If the file doesn't exist, create it with just the antlr4 entry
        with open(file_path, 'w') as file:
            file.write(f"antlr4-python3-runtime=={version}{os.linesep}")
        print(f"Created {file_path} with antlr4-python3-runtime=={version}")
    except Exception as e:
        print(f"Error updating {file_path}: {e}")
        sys.exit(1)


def main():
    """Main function to parse arguments and update requirements.txt"""
    parser = argparse.ArgumentParser(description='Update antlr4-python3-runtime version in requirements.txt')
    parser.add_argument('-v', '--version', required=True, help='Version of antlr4-python3-runtime to set')

    args = parser.parse_args()

    # Update requirements.txt in the current directory
    update_requirements('requirements.txt', args.version)
    update_requirements('requirements-dev.txt', args.version)


if __name__ == "__main__":
    main()
