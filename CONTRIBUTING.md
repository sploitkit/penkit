# Contributing to PenKit

First off, thank you for considering contributing to PenKit! It's people like you that make PenKit a great tool for the security community.

## Code of Conduct

By participating in this project, you agree to abide by our [Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## How Can I Contribute?

### Reporting Bugs

This section guides you through submitting a bug report. Following these guidelines helps maintainers understand your report, reproduce the issue, and find related reports.

* **Use the GitHub issue search** — check if the issue has already been reported
* **Check if the issue has been fixed** — try to reproduce it using the latest `main` branch
* **Use the bug report template** — when you create a new issue, you'll be presented with a template

### Suggesting Enhancements

This section guides you through submitting an enhancement suggestion, including completely new features and minor improvements to existing functionality.

* **Use the GitHub issue search** — check if the enhancement has already been suggested
* **Describe the enhancement in detail** — provide a step-by-step description of the suggested enhancement
* **Explain why this enhancement would be useful** — which use cases would it support and how would it benefit users?

### Your First Code Contribution

Unsure where to begin contributing? Look for issues labeled:

* `good first issue` - issues which should only require a few lines of code
* `help wanted` - issues which need assistance from the community
* `documentation` - help us improve the documentation

### Pull Requests

* Fill in the required template
* Do not include issue numbers in the PR title
* Follow the Python style guides
* Include appropriate tests
* Update documentation for new features
* End all files with a newline

## Development Process

### Setting Up Development Environment

1. Fork the repository
2. Clone your fork locally
3. Set up Poetry environment:
   ```bash
   poetry install
   poetry shell
   pre-commit install
   ```

### Testing

* Write tests for all new features and bug fixes
* Run the test suite before submitting a PR:
  ```bash
  poetry run pytest
  ```

### Code Style

* Code should follow PEP 8 guidelines
* Use type annotations
* Use docstrings for functions and classes
* Pre-commit hooks will enforce style guidelines

### Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Reference issues and pull requests liberally after the first line

### Branch Naming Convention

* Use descriptive branch names that reflect the changes
* Format: `type/short-description` (e.g., `feature/add-nmap-integration`, `fix/broken-cli-parser`)

## Plugin Development

We welcome new tool integrations! Please follow these guidelines:

1. Check if the tool is already on our integration roadmap
2. Use the plugin template to ensure compatibility
3. Include thorough documentation
4. Provide tests that validate the integration works as expected

## Documentation

Documentation is crucial for PenKit. When contributing, please:

* Update the README.md if needed
* Add docstrings to all functions and classes
* Provide examples of how to use new features
* Update any relevant documentation pages

## Questions?

If you have any questions, feel free to create a discussion on GitHub or reach out to the maintainers.

Thank you for your contributions!
