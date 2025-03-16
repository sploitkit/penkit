#!/bin/bash
# PenKit Installation Script

set -e

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

# Check if script is run as root
if [[ $EUID -eq 0 ]]; then
    print_yellow "Warning: Running as root. This is not recommended for development."
fi

# Check Python version
python_version=$(python3 --version | cut -d " " -f 2)
python_major=$(echo $python_version | cut -d. -f1)
python_minor=$(echo $python_version | cut -d. -f2)

if [ "$python_major" -lt 3 ] || ([ "$python_major" -eq 3 ] && [ "$python_minor" -lt 10 ]); then
    print_red "Error: Python 3.10 or higher is required. Found: $python_version"
    exit 1
fi

print_green "Python version $python_version found. Continuing installation..."

# Check for Poetry
if ! command -v poetry &> /dev/null; then
    print_yellow "Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install dependencies
print_green "Installing PenKit and dependencies..."
poetry install

# Create directories
print_green "Creating configuration directories..."
mkdir -p ~/.penkit/sessions
mkdir -p ~/.penkit/plugins

# Make script executable
chmod +x penkit/cli/main.py

# Create symlink if requested
if [[ "$1" == "--link" ]]; then
    print_yellow "Creating symlink to penkit in ~/.local/bin..."
    mkdir -p ~/.local/bin
    poetry run pip install -e .
    ln -sf $(pwd)/penkit/cli/main.py ~/.local/bin/penkit
    chmod +x ~/.local/bin/penkit
    print_green "Symlink created. You can now run 'penkit' from anywhere."
    print_yellow "Make sure ~/.local/bin is in your PATH."
fi

# Check for common tools
print_green "Checking for common security tools..."
tools=("nmap" "masscan")
missing_tools=()

for tool in "${tools[@]}"; do
    if ! command -v $tool &> /dev/null; then
        missing_tools+=($tool)
    fi
done

if [ ${#missing_tools[@]} -gt 0 ]; then
    print_yellow "Some recommended tools are missing: ${missing_tools[*]}"
    print_yellow "You may want to install them for full functionality."
    
    if command -v apt-get &> /dev/null; then
        print_yellow "On Debian/Ubuntu, you can install them with:"
        print_yellow "sudo apt-get install ${missing_tools[*]}"
    elif command -v dnf &> /dev/null; then
        print_yellow "On Fedora, you can install them with:"
        print_yellow "sudo dnf install ${missing_tools[*]}"
    elif command -v pacman &> /dev/null; then
        print_yellow "On Arch Linux, you can install them with:"
        print_yellow "sudo pacman -S ${missing_tools[*]}"
    fi
    
    print_yellow "Alternatively, you can use the Docker version which includes all dependencies."
fi

# Instructions
print_green "Installation complete!"
print_green "To get started, run:"
print_green "  poetry shell"
print_green "  python -m cli.main"
print_green ""
print_green "Or if you created a symlink:"
print_green "  penkit"
print_green ""
print_green "For more information, see the documentation in the docs/ directory."