# Pip & Brew cleaner

**Pip & Brew cleaner** (`pipbrew-cleaner`) is an interactive command-line tool for
listing and uninstalling pip and Homebrew packages. It provides colorized output of
package information and lets you safely remove packages from your system.

> macOS only (Homebrew features require a macOS/Homebrew install).

## Features

- Lists pip packages and Homebrew formulas/casks.
- Displays package descriptions.
- Allows filtering by package name.
- Interactive selection for uninstallation, with explicit confirmation.
- Logs operations to a per-user log file.
- Protects critical packages (pip, setuptools, wheel, and the tool itself) from being uninstalled.
- Refuses to remove a Homebrew formula that other installed packages depend on.

## Requirements

- Python 3.8+ (tested on macOS)
- Homebrew (for the Homebrew features)
- No third-party Python dependencies (standard library only)

## Installation

Once published on PyPI, install with:

```bash
pip install pipbrew-cleaner
```

Or clone this repository and run it from source (see Usage).

## Usage

If you installed it from PyPI, run the console command:

```bash
pipbrew-cleaner
```

If you cloned the repository, run it as a module from the project root:

```bash
python3 -m pipbrew_cleaner
```

Follow the prompts to list, view, and uninstall packages.

## Contributing

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

Released under the MIT License. See [LICENSE.md](LICENSE.md).

## Author

Manuel DORNE - Korben
[https://korben.info](https://korben.info)
