# Contributing to pyfcstm

Thank you for your interest in contributing to pyfcstm! This document provides comprehensive guidelines for contributing
to the project, whether you're fixing bugs, adding features, improving documentation, or helping with testing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Development Workflow](#development-workflow)
- [Testing Guidelines](#testing-guidelines)
- [Code Style and Standards](#code-style-and-standards)
- [Documentation](#documentation)
- [Submitting Changes](#submitting-changes)
- [Reporting Issues](#reporting-issues)

## Code of Conduct

By participating in this project, you are expected to uphold our Code of Conduct. Please be respectful and considerate
of others when contributing.

## Development Environment Setup

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.7+**: pyfcstm supports Python 3.7 and above, and CI currently tests CPython 3.7 through 3.14
- **Git**: For version control
- **Java Runtime Environment (JRE)**: Required only if you plan to modify the ANTLR grammar

### Setting Up Your Development Environment

1. **Fork and Clone the Repository**

   ```bash
   # Fork the repository on GitHub first, then clone your fork
   git clone https://github.com/YOUR-USERNAME/pyfcstm.git
   cd pyfcstm

   # Add the original repository as an upstream remote
   git remote add upstream https://github.com/HansBug/pyfcstm.git
   ```

2. **Install Dependencies**

   ```bash
   # Install runtime dependencies
   pip install -r requirements.txt

   # Install development dependencies (includes ruff for formatting)
   pip install -r requirements-dev.txt

   # Install testing dependencies
   pip install -r requirements-test.txt

   # Install documentation dependencies (optional)
   pip install -r requirements-doc.txt
   ```

3. **Verify Installation**

   ```bash
   # Run a quick test to ensure everything is working
   make unittest RANGE_DIR=./config

   # Verify the CLI is working
   python -m pyfcstm --version
   ```

## Getting Started

### Types of Contributions

We welcome various types of contributions:

- **Bug Fixes**: Fix issues in parsing, rendering, or code generation
- **New Features**: Add DSL syntax features, expression types, or template capabilities
- **Documentation**: Improve guides, tutorials, API docs, or examples
- **Tests**: Add test coverage or improve test infrastructure
- **Templates**: Create example templates for different target languages
- **Performance**: Optimize parsing, rendering, or memory usage

### First-Time Contributors

If you're new to the project:

1. Look for issues labeled `good first issue` or `help wanted`
2. Read through [CLAUDE.md](CLAUDE.md) for architecture overview
3. Start with small changes to familiarize yourself with the codebase
4. Ask questions in issues or discussions if you need help

## Testing Guidelines

### Running Tests

pyfcstm uses pytest for testing. The test suite is comprehensive and covers all major components.

1. **Run All Tests**

   ```bash
   make unittest
   ```

2. **Run Tests in a Specific Directory**

   ```bash
   make unittest RANGE_DIR=./dsl
   make unittest RANGE_DIR=./model
   make unittest RANGE_DIR=./render
   ```

3. **Run Tests with Coverage**

   ```bash
   # Generate XML and terminal coverage reports
   make unittest COV_TYPES="xml term-missing"

   # Set minimum coverage requirement
   make unittest MIN_COVERAGE=80
   ```

4. **Run Tests in Parallel**

   ```bash
   # Use 4 workers for faster test execution
   make unittest WORKERS=4
   ```

### Writing Tests

When adding new features or fixing bugs, always include tests:

1. **Test Organization**: Tests mirror the source structure in the `test/` directory
    - `test/dsl/` - DSL parsing tests
    - `test/model/` - State machine model tests
    - `test/render/` - Template rendering tests
    - `test/entry/` - CLI tests

2. **Test Naming**: Use descriptive names that explain what is being tested
   ```python
   def test_parse_simple_state_machine():
       """Test parsing a basic state machine with two states."""
       pass

   def test_transition_with_guard_condition():
       """Test that guard conditions are correctly parsed."""
       pass
   ```

3. **Use Pytest Markers**: Mark your tests appropriately
   ```python
   import pytest

   @pytest.mark.unittest
   def test_my_feature():
       pass
   ```

4. **Sample Test Generation**: For DSL test cases, you can use the sample test generator
   ```bash
   # Add your .fcstm file to test/testfile/sample_codes/
   # Then regenerate tests
   make sample
   ```

### Test Coverage

- Aim for high test coverage on new code
- Run coverage reports to identify untested code paths
- Focus on testing edge cases and error conditions

## Code Style and Standards

### Python Code Style

pyfcstm follows PEP 8 style guidelines with automatic formatting using `ruff`.

1. **Automatic Formatting**

   ```bash
   # Format all Python files
   ruff format .

   # Format specific files
   ruff format pyfcstm/dsl/parse.py
   ```

2. **Code Style Guidelines**

    - Use 4 spaces for indentation (no tabs)
    - Maximum line length: 120 characters
    - Use descriptive variable and function names
    - Follow PEP 8 naming conventions:
        - `snake_case` for functions and variables
        - `PascalCase` for classes
        - `UPPER_CASE` for constants

3. **Docstrings**

    - Add docstrings to all public functions, classes, and modules
    - Use Google-style or NumPy-style docstrings
    - Include parameter types and return types

   ```python
   def parse_state_machine(dsl_code: str) -> StateMachine:
       """Parse DSL code into a state machine model.

       Args:
           dsl_code: The DSL source code as a string.

       Returns:
           A StateMachine model object.

       Raises:
           ParseError: If the DSL code contains syntax errors.
       """
       pass
   ```

### ANTLR Grammar Modifications

If you need to modify the DSL syntax by changing the ANTLR grammar:

1. **Prerequisites**

    - Ensure Java is installed: `java -version`
    - Install development dependencies: `pip install -r requirements-dev.txt`

2. **Download ANTLR Toolchain**

   ```bash
   # Download ANTLR jar (only needed once)
   make antlr

   # If using a different ANTLR version
   ANTLR_VERSION=4.9.3 make antlr
   pip install -r requirements-dev.txt
   ```

3. **Modify Grammar**

    - Edit `pyfcstm/dsl/grammar/Grammar.g4`
    - Follow ANTLR4 syntax and best practices
    - Test your grammar changes thoroughly

4. **Regenerate Parser Code**

   ```bash
   # Regenerate parser from grammar
   make antlr_build
   ```

5. **Update Related Code**

   After modifying the grammar, you may need to update:
    - `pyfcstm/dsl/listener.py` - ANTLR listener implementation
    - `pyfcstm/dsl/node.py` - AST node definitions
    - Tests in `test/dsl/`

6. **Test Your Changes**

   ```bash
   # Run DSL parsing tests
   make unittest RANGE_DIR=./dsl

   # Regenerate sample tests if needed
   make sample_clean
   make sample
   ```

## Documentation

### Building Documentation Locally

pyfcstm uses Sphinx for documentation generation.

```bash
# Build documentation locally
make docs

# The generated documentation will be in docs/build/html/
# Open docs/build/html/index.html in your browser

# Build production documentation
make pdocs
```

### Documentation Guidelines

When contributing code, update documentation accordingly:

1. **Docstrings**: Add or update docstrings for all public APIs
2. **README.md**: Update if adding major features or changing usage
3. **CLAUDE.md**: Update if changing architecture or development workflows
4. **Sphinx Docs**: Add tutorials or guides for significant new features

### Documentation Structure

- `docs/` - Sphinx documentation source
- `README.md` - Project overview and quick start
- `CLAUDE.md` - Development guide for AI assistants
- `CONTRIBUTING.md` - This file

## Submitting Changes

### Creating a Branch

Create a descriptive branch for your work:

```bash
# Feature branches
git checkout -b feature/add-new-expression-type
git checkout -b feature/support-rust-templates

# Bug fix branches
git checkout -b fix/parser-error-handling
git checkout -b fix/template-rendering-issue

# Documentation branches
git checkout -b docs/update-api-reference
```

### Committing Your Changes

1. **Write Clear Commit Messages**

   Follow the conventional commit format:

   ```
   type(scope): brief description

   Detailed explanation of what changed and why.
   ```

   Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

   Examples:
   ```
   feat(dsl): add support for ternary conditional expressions
   fix(render): correct expression rendering for Python style
   docs(readme): add advanced API usage examples
   test(model): add tests for nested state transitions
   ```

2. **Stage and Commit**

   ```bash
   # Stage specific files
   git add pyfcstm/dsl/parse.py
   git add test/dsl/test_parse.py

   # Commit with a descriptive message
   git commit -m "feat(dsl): add support for ternary expressions"
   ```

3. **Keep Commits Focused**

    - Each commit should represent a single logical change
    - Don't mix unrelated changes in one commit
    - Commit frequently with meaningful messages

### Pushing and Creating a Pull Request

1. **Sync with Upstream**

   Before pushing, ensure your branch is up to date:

   ```bash
   # Fetch latest changes from upstream
   git fetch upstream

   # Rebase your branch on upstream/main
   git rebase upstream/main

   # Resolve any conflicts if they occur
   ```

2. **Push Your Branch**

   ```bash
   git push origin your-branch-name

   # If you rebased, you may need to force push
   git push --force-with-lease origin your-branch-name
   ```

3. **Create a Pull Request**

    - Go to [https://github.com/HansBug/pyfcstm](https://github.com/HansBug/pyfcstm)
    - Click "Pull Requests" → "New Pull Request"
    - Select your fork and branch
    - Fill out the PR template with:
        - **Title**: Clear, concise description (e.g., "Add support for ternary expressions")
        - **Description**:
            - What problem does this solve?
            - What changes were made?
            - How to test the changes?
            - Any breaking changes or migration notes?
        - **Related Issues**: Link to any related issues (e.g., "Fixes #123")

4. **PR Checklist**

   Before submitting, ensure:
    - [ ] All tests pass (`make unittest`)
    - [ ] Code is formatted (`ruff format .`)
    - [ ] Documentation is updated if needed
    - [ ] Commit messages are clear and descriptive
    - [ ] No unrelated changes are included
    - [ ] PR description is complete and clear

### Pull Request Review Process

1. **Automated Checks**: CI/CD will run tests and checks automatically
2. **Code Review**: Maintainers will review your code and may request changes
3. **Address Feedback**: Make requested changes and push updates
4. **Approval**: Once approved, maintainers will merge your PR

### After Your PR is Merged

```bash
# Switch back to main branch
git checkout main

# Pull the latest changes
git pull upstream main

# Delete your feature branch (optional)
git branch -d your-branch-name
git push origin --delete your-branch-name
```

## Reporting Issues

### Before Creating an Issue

1. **Search Existing Issues**: Check if your issue already exists
   in [GitHub Issues](https://github.com/hansbug/pyfcstm/issues)
2. **Check Documentation**: Review the [documentation](https://pyfcstm.readthedocs.io/) to ensure it's not a usage
   question
3. **Verify Version**: Ensure you're using the latest version of pyfcstm

### Creating a Bug Report

When reporting a bug, include:

1. **Clear Title**: Descriptive summary of the issue
2. **Environment Information**:
   ```bash
   # Include output of:
   python --version
   pip show pyfcstm
   uname -a  # or OS version
   ```
3. **Steps to Reproduce**: Minimal, complete example that reproduces the issue
4. **Expected Behavior**: What you expected to happen
5. **Actual Behavior**: What actually happened
6. **Error Messages**: Full error messages and stack traces
7. **DSL Code**: If applicable, include the `.fcstm` file that causes the issue

Example bug report:

```markdown
## Bug: Parser fails on nested state with abstract action

**Environment:**

- pyfcstm version: 0.2.1
- Python version: 3.9.7
- OS: Ubuntu 20.04

**Steps to Reproduce:**

1. Create a DSL file with nested states
2. Add an abstract action to the inner state
3. Run `pyfcstm plantuml -i test.fcstm -o output.puml`

**Expected:** Parser should handle nested states with abstract actions

**Actual:** Parser throws `ParseError: unexpected token 'abstract'`

**DSL Code:**
[Attach or paste the minimal DSL code that reproduces the issue]

**Error Message:**
[Full stack trace]
```

### Feature Requests

When suggesting a feature:

1. **Use Case**: Describe the problem you're trying to solve
2. **Proposed Solution**: How you envision the feature working
3. **Alternatives**: Other approaches you've considered
4. **Examples**: Code examples showing how the feature would be used

### Questions and Discussions

For questions about usage or design discussions:

- Use [GitHub Discussions](https://github.com/hansbug/pyfcstm/discussions) (if enabled)
- Or create an issue with the "question" label

## Development Workflow

### Typical Development Cycle

Here's a typical workflow for contributing to pyfcstm:

1. **Sync with Upstream**
   ```bash
   git fetch upstream
   git checkout main
   git merge upstream/main
   ```

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/my-new-feature
   ```

3. **Make Changes**
    - Write code following style guidelines
    - Add tests for new functionality
    - Update documentation as needed

4. **Test Your Changes**
   ```bash
   # Run tests
   make unittest

   # Format code
   ruff format .

   # Run specific tests
   make unittest RANGE_DIR=./dsl
   ```

5. **Commit and Push**
   ```bash
   git add <files>
   git commit -m "feat: add new feature"
   git push origin feature/my-new-feature
   ```

6. **Create Pull Request**
    - Go to GitHub and create a PR
    - Fill out the PR template
    - Wait for review and address feedback

### Common Development Tasks

**Adding a New DSL Feature**

1. Modify `pyfcstm/dsl/grammar/Grammar.g4`
2. Run `make antlr_build` to regenerate parser
3. Update `pyfcstm/dsl/listener.py` to handle new grammar rules
4. Add AST node definitions in `pyfcstm/dsl/node.py`
5. Update model classes in `pyfcstm/model/` if needed
6. Add tests in `test/dsl/`
7. Update documentation

**Adding a New Expression Type**

1. Update grammar in `Grammar.g4`
2. Add expression node in `pyfcstm/model/expr.py`
3. Update expression rendering in `pyfcstm/render/expr.py`
4. Add tests for parsing and rendering
5. Update DSL documentation

**Creating a Template Example**

1. Create a new directory in `templates/` or `test/testfile/templates/`
2. Add `config.yaml` with expression styles and filters
3. Create `.j2` template files
4. Add static files if needed
5. Test with sample DSL files
6. Document the template usage

## License

By contributing to pyfcstm, you agree that your contributions will be licensed under the GNU Lesser General Public
License v3 (LGPLv3).

## Additional Resources

- **Documentation**: [https://pyfcstm.readthedocs.io/](https://pyfcstm.readthedocs.io/)
- **Source Code**: [https://github.com/HansBug/pyfcstm](https://github.com/HansBug/pyfcstm)
- **Issue Tracker**: [https://github.com/HansBug/pyfcstm/issues](https://github.com/HansBug/pyfcstm/issues)
- **Pull Requests**: [https://github.com/HansBug/pyfcstm/pulls](https://github.com/HansBug/pyfcstm/pulls)
- **CI/CD**: [https://github.com/HansBug/pyfcstm/actions](https://github.com/HansBug/pyfcstm/actions)
- **CLAUDE.md**: Development guide for understanding the architecture

## Questions?

If you have any questions about contributing:

- Check the [documentation](https://pyfcstm.readthedocs.io/)
- Review [CLAUDE.md](CLAUDE.md) for architecture details
- Open an issue with the "question" label
- Reach out to maintainers in existing issues or discussions

Thank you for contributing to pyfcstm! Your contributions help make state machine development easier for everyone.
