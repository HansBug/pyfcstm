# Contributing to pyfcstm

Thank you for your interest in contributing to pyfcstm! This document outlines the process for contributing to the project and helps you get started.

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct. Please be respectful and considerate of others when contributing.

## Getting Started

### Fork and Clone the Repository

1. Fork the repository on GitHub: [https://github.com/HansBug/pyfcstm](https://github.com/HansBug/pyfcstm)
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/pyfcstm.git
   cd pyfcstm
   ```
3. Add the original repository as an upstream remote:
   ```bash
   git remote add upstream https://github.com/HansBug/pyfcstm.git
   ```

### Setting Up the Development Environment

1. Install the basic dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. For development purposes, install additional dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

3. For running tests, install test dependencies:
   ```bash
   pip install -r requirements-test.txt
   ```

4. For building documentation, install documentation dependencies:
   ```bash
   pip install -r requirements-doc.txt
   ```

## Development Workflow

### Creating a Branch

Create a new branch for your feature or bugfix:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### Making Changes

1. Make your changes to the codebase.
2. Keep your changes focused and related to a single issue/feature.
3. Follow the project's coding style and conventions.

### DSL Syntax Modifications

If you need to modify the DSL syntax:

1. Ensure you have a Java environment installed and can use the `java -jar` command.
2. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```
3. Load the ANTLR toolchain (this will download the antlr jar file and re-edit the antlr pip requirements):
   ```bash
   make antlr
   pip install -r requirements-dev.txt  # if you assigned another antlr version via `ANTLR_VERSION` env
   ```
4. After modifying grammar files, regenerate the related code:
   ```bash
   make antlr_build
   ```

### Testing Your Changes

1. Run the test suite to ensure your changes don't break existing functionality:
   ```bash
   make unittest
   ```

2. To test only a specific subdirectory, use the `RANGE_DIR` environment variable:
   ```bash
   make unittest RANGE_DIR=./config
   ```

3. Ensure your code passes all tests before submitting a pull request.

### Building Documentation

To build the documentation locally:

```bash
make docs
```

The generated documentation will be available in the `docs/build/html` directory.

## Submitting Changes

### Committing Your Changes

1. Commit your changes with a descriptive commit message:
   ```bash
   git add .
   git commit -m "Brief description of your changes"
   ```

2. Push your branch to your fork:
   ```bash
   git push origin your-branch-name
   ```

### Creating a Pull Request

1. Go to the [pyfcstm repository](https://github.com/HansBug/pyfcstm) on GitHub.
2. Click on "Pull Requests" and then "New Pull Request".
3. Select your fork and branch.
4. Provide a clear description of your changes, including:
   - What problem you're solving
   - How your changes solve the problem
   - Any additional context or information that might be helpful

### Pull Request Review Process

1. Maintainers will review your PR as soon as possible.
2. They may ask for changes or clarification.
3. Once approved, your PR will be merged into the main codebase.

## Reporting Issues

If you find a bug or have a feature request:

1. Check if the issue already exists in the [GitHub Issues](https://github.com/HansBug/pyfcstm/issues).
2. If not, create a new issue with a descriptive title and detailed information.
3. Include steps to reproduce bugs or clear descriptions of proposed features.

## Style Guidelines

- Follow PEP 8 style guidelines for Python code.
- Write clear, descriptive commit messages.
- Include docstrings for all functions, classes, and modules.
- Add appropriate tests for new functionality.

## License

By contributing to pyfcstm, you agree that your contributions will be licensed under the project's license.

## Questions?

If you have any questions about contributing, feel free to open an issue for clarification.

Thank you for contributing to pyfcstm!
