#!/bin/bash
# Run script for PenKit

# Print colored output
print_green() {
    echo -e "\e[32m$1\e[0m"
}

print_yellow() {
    echo -e "\e[33m$1\e[0m"
}

print_red() {
    echo -e "\e[31m$1\e[0m"
}

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    print_red "Poetry not found. Please install Poetry first."
    print_yellow "You can install it with: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Check if dependencies are installed
if ! poetry check 2>/dev/null; then
    print_yellow "Installing dependencies..."
    poetry install
fi

# Run PenKit with Poetry
poetry run python3 -m cli.main "$@"
