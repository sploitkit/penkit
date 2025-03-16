# Development Guide

This guide provides instructions for developers who want to contribute to PenKit or extend it with custom functionality.

## Setting Up Development Environment

1. Clone the repository:
   ```bash
   git clone https://github.com/sploitkit/penkit.git
   cd penkit
   ```

2. Install dependencies with Poetry:
   ```bash
   poetry install
   ```

3. Install pre-commit hooks:
   ```bash
   poetry run pre-commit install
   ```

4. Run tests to verify your setup:
   ```bash
   poetry run pytest
   ```

## Project Structure

```
penkit/
├── core/           # Core framework functionality
│   ├── plugin.py   # Plugin management system
│   ├── session.py  # Session management
│   └── models.py   # Data models
├── utils/          # Shared utilities
├── integrations/   # Tool integration framework
├── modules/        # Functional modules
└── cli/            # CLI application
```

## Creating a New Module

Modules in PenKit are plugins that implement specific functionality. To create a new module:

1. Create a directory for your module:
   ```bash
   mkdir -p penkit/modules/my_module
   touch penkit/modules/my_module/__init__.py
   ```

2. Create your module class:
   ```python
   from penkit.core.plugin import PenKitPlugin

   class MyModulePlugin(PenKitPlugin):
       name = "my_module"
       description = "Description of my module"
       version = "0.1.0"
       author = "Your Name"
       
       def __init__(self):
           super().__init__()
           self.options = {
               "option1": "default_value",
               "option2": 123,
           }
       
       def run(self):
           # Implement your module's functionality
           return {"result": "success"}
   ```

3. Test your module:
   ```python
   # Create a test file: tests/modules/test_my_module.py
   
   from penkit.modules.my_module import MyModulePlugin

   def test_my_module():
       plugin = MyModulePlugin()
       assert plugin.name == "my_module"
       
       # Test the functionality
       result = plugin.run()
       assert result["result"] == "success"
   ```

## Creating a Tool Integration

Tool integrations provide wrappers around external security tools. To create a new tool integration:

1. Create an integration file:
   ```bash
   touch penkit/integrations/my_tool_integration.py
   ```

2. Implement the integration:
   ```python
   from penkit.integrations.base import ToolIntegration
   
   class MyToolIntegration(ToolIntegration):
       name = "my_tool"
       description = "Integration for My Tool"
       binary_name = "mytool"
       version_args = ["--version"]
       default_args = ["--some-default-option"]
       container_image = "example/mytool:latest"  # Optional
       
       def parse_output(self, stdout, stderr):
           # Parse the tool output
           return {
               "parsed": True,
               "data": stdout
           }
   ```

## Code Style

PenKit follows these coding standards:

- PEP 8 style guide
- Type annotations for all functions
- Docstrings for all modules, classes, and functions
- Maximum line length of 88 characters (Black formatter)

The pre-commit hooks will check and enforce these standards.

## Testing

Write tests for all new functionality. We use pytest for testing:

```bash
# Run all tests
poetry run pytest

# Run specific tests
poetry run pytest tests/test_specific.py

# Run with coverage
poetry run pytest --cov=penkit
```

## Documentation

Update documentation when adding new features:

- Add docstrings to all public functions and classes
- Update README.md if necessary
- Add examples to the docs directory

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and ensure they pass
5. Submit a pull request

Please follow the guidelines in CONTRIBUTING.md when submitting pull requests.

## Building Distributions

To build a distribution package:

```bash
poetry build
```

This will create distributable packages in the `dist/` directory.
