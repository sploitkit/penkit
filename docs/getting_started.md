# Getting Started with PenKit

This guide will help you set up and start using PenKit for your penetration testing needs.

## Installation

### Prerequisites

- Python 3.10 or higher
- Poetry (for development)
- Docker (optional, for containerized usage)

### Install from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/sploitkit/penkit.git
   cd penkit
   ```

2. Install with Poetry:
   ```bash
   poetry install
   ```

3. Activate the virtual environment:
   ```bash
   poetry shell
   ```

### Using Docker

If you prefer to use Docker:

1. Build the Docker image:
   ```bash
   docker-compose build
   ```

2. Run PenKit in a container:
   ```bash
   docker-compose run --rm penkit
   ```

## Basic Usage

### Starting the Interactive Shell

```bash
penkit
```

This will launch the interactive shell where you can run commands.

### Getting Help

```bash
penkit --help
```

Or within the shell:

```
help
```

### Using Modules

To use a module within the shell:

```
use port_scanner
```

Then set the required options:

```
set target 192.168.1.1
```

And run the module:

```
run
```

### Listing Available Modules

```
show modules
```

### Viewing Module Options

When a module is selected:

```
show options
```

### Running Scripts

You can run a script file with PenKit commands:

```bash
penkit script /path/to/script.txt
```

Example script content:
```
use port_scanner
set target 192.168.1.1
set ports 80,443,8080
run
```

## Next Steps

- Check out the [module documentation](./modules.md) for details on available modules
- Learn how to [create custom modules](./custom_modules.md)
- Explore [advanced usage patterns](./advanced_usage.md)

## Troubleshooting

### Common Issues

- **Tool not found**: Make sure the required tools are installed and in your PATH
- **Permission denied**: Some tools require elevated privileges. Try running with sudo or using the Docker image

### Getting Support

- Open an issue on GitHub
- Check the troubleshooting guide in the documentation
