# Pipbrew-cleaner
Only for macOS.

# Pip & Brew cleaner

**Pip & Brew cleaner** is an interactive command-line tool for listing and uninstalling pip and Homebrew packages. It provides progressive, colorized output of package information and lets you safely remove packages from your system.

## Features

- Lists pip packages and Homebrew formulas/casks.
- Displays package descriptions.
- Allows filtering by package name.
- Interactive selection for uninstallation.
- Logs operations to a file.
- Protects critical packages from being uninstalled.

## Requirements

- Python 3.x (tested on macOS)
- Homebrew (for managing Homebrew packages)

## Installation

Once published on PyPI, install with:

```bash
pip install pipbrew-cleaner
```

Or clone this repository and run:

```bash
python3 main.py
```

Usage

Run the tool from the command line:

```bash
python3 main.py
```

Follow the prompts to list, view, and uninstall packages.
Contributing

Contributions are welcome! See CONTRIBUTING.md for details.

## Author
Manuel DORNE - Korben  
[https://korben.info](https://korben.info)