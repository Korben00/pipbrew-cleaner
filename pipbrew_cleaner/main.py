#!/usr/bin/env python3
# pipbrew-cleaner
# Author: Manuel DORNE - Korben (https://korben.info)
"""
Interactive CLI tool to list and uninstall pip and Homebrew packages.
Displays package information with colorized output, all in English, using
only the Python standard library (no third-party dependencies).
"""

import logging
import os

from pipbrew_cleaner import brew_manager, pip_manager

# ANSI escape codes for colors and styles
RESET     = "\033[0m"
BOLD      = "\033[1m"
UNDERLINE = "\033[4m"
RED       = "\033[91m"
GREEN     = "\033[92m"
YELLOW    = "\033[93m"
BLUE      = "\033[94m"
MAGENTA   = "\033[95m"
CYAN      = "\033[96m"

NO_DESCRIPTION = "No description available"


def color_text(text, color, bold=False, underline=False):
    """Return text wrapped in ANSI codes for color and style."""
    style = ""
    if bold:
        style += BOLD
    if underline:
        style += UNDERLINE
    return f"{style}{color}{text}{RESET}"


def main_menu():
    print("\n" + color_text("=== Main Menu ===", CYAN, bold=True))
    print(color_text("1. List/Uninstall Packages", GREEN))
    print(color_text("2. View Package Information", GREEN))
    print(color_text("3. Quit", GREEN))
    choice = input(color_text("Your choice (1-3): ", YELLOW))
    return choice.strip()


def list_and_uninstall():
    # Retrieve installed packages
    pip_packages = pip_manager.get_installed_packages()
    brew_formulas, brew_casks = brew_manager.get_installed_packages()

    # Optional filter
    filter_str = input(
        color_text("Filter packages by name (leave empty for none): ", YELLOW)).strip().lower()
    if filter_str:
        pip_packages = [p for p in pip_packages if filter_str in p.lower()]
        brew_formulas = [p for p in brew_formulas if filter_str in p.lower()]
        brew_casks = [p for p in brew_casks if filter_str in p.lower()]

    if not pip_packages and not brew_formulas and not brew_casks:
        print(color_text("No packages match the filter.", RED))
        return

    # Assign sequential numbers up front (deterministic, input order) so the
    # displayed list is always numbered in order regardless of fetch timing.
    all_packages = {}
    pip_indexed, formula_indexed, cask_indexed = [], [], []
    idx = 1
    for pkg in pip_packages:
        all_packages[idx] = ("pip", pkg)
        pip_indexed.append((idx, pkg))
        idx += 1
    for pkg in brew_formulas:
        all_packages[idx] = ("brew", pkg, False)
        formula_indexed.append((idx, pkg))
        idx += 1
    for pkg in brew_casks:
        all_packages[idx] = ("brew", pkg, True)
        cask_indexed.append((idx, pkg))
        idx += 1

    # pip packages — one `pip show` call for the whole section.
    print("\n" + color_text("=== pip Packages ===", MAGENTA, bold=True))
    if pip_indexed:
        print(color_text(f"Fetching info for {len(pip_indexed)} pip package(s)...", BLUE))
        pip_info = pip_manager.get_packages_info([pkg for _, pkg in pip_indexed])
        for i, pkg in pip_indexed:
            info = pip_info.get(pip_manager.canonical_name(pkg))
            summary = info["summary"] if info and info.get("summary") else NO_DESCRIPTION
            number = color_text(f"{i}.", BLUE)
            name = color_text(pkg, YELLOW)
            if pip_manager.is_critical(pkg):
                print(f"{number} {name} (pip) {color_text('[protected]', RED)} - {summary}")
            else:
                print(f"{number} {name} (pip) - {summary}")

    # Homebrew formulas — one `brew info` call for the whole section.
    print("\n" + color_text("=== Homebrew Formulas ===", MAGENTA, bold=True))
    if formula_indexed:
        print(color_text(
            f"Fetching info for {len(formula_indexed)} formula(s) "
            f"(one brew call, may take a few seconds for large installs)...", BLUE))
        formula_info = brew_manager.get_packages_info(
            [pkg for _, pkg in formula_indexed], is_cask=False)
        for i, pkg in formula_indexed:
            info = formula_info.get(pkg)
            desc = info["desc"] if info and info.get("desc") else NO_DESCRIPTION
            print(f"{color_text(f'{i}.', BLUE)} {color_text(pkg, YELLOW)} (brew - formula) - {desc}")

    # Homebrew casks — one `brew info --cask` call for the whole section.
    print("\n" + color_text("=== Homebrew Casks ===", MAGENTA, bold=True))
    if cask_indexed:
        print(color_text(
            f"Fetching info for {len(cask_indexed)} cask(s) (one brew call)...", BLUE))
        cask_info = brew_manager.get_packages_info(
            [pkg for _, pkg in cask_indexed], is_cask=True)
        for i, pkg in cask_indexed:
            info = cask_info.get(pkg)
            desc = info["desc"] if info and info.get("desc") else NO_DESCRIPTION
            print(f"{color_text(f'{i}.', BLUE)} {color_text(pkg, YELLOW)} (brew - cask) - {desc}")

    # Ask user to select packages to uninstall
    choice = input(
        "\n" + color_text(
            "Enter the numbers of packages to uninstall (separated by commas): ", YELLOW)).strip()
    if not choice:
        print(color_text("No packages selected.", RED))
        return

    # Parse and validate every token, surfacing typos instead of silently
    # dropping them (e.g. "3.5", "abc").
    indices, invalid = [], []
    for token in (t.strip() for t in choice.split(",")):
        if not token:
            continue
        try:
            indices.append(int(token))
        except ValueError:
            invalid.append(token)
    if invalid:
        print(color_text(f"Ignored invalid entries: {', '.join(invalid)}", RED))
    if not indices:
        print(color_text("No valid package numbers entered.", RED))
        return

    print(color_text("You have selected the following packages:", CYAN, bold=True))
    to_uninstall = []
    for i in indices:
        if i not in all_packages:
            print(f"-> {color_text('Number ' + str(i) + ' unknown', RED)}")
            continue
        item = all_packages[i]
        source, pkg = item[0], item[1]
        if source == "pip" and pip_manager.is_critical(pkg):
            print(f"-> {color_text(pkg, YELLOW)} (pip) "
                  f"{color_text('[protected, will not be uninstalled]', RED)}")
        else:
            if source == "brew":
                label = "brew cask" if item[2] else "brew formula"
            else:
                label = "pip"
            print(f"-> {color_text(pkg, YELLOW)} ({label})")
            to_uninstall.append(item)

    if not to_uninstall:
        print(color_text("Nothing to uninstall.", RED))
        return

    conf = input("\n" + color_text("Confirm uninstallation? (y/n): ", YELLOW)).strip().lower()
    if conf != "y":
        print(color_text("Operation cancelled.", RED))
        return

    # Perform uninstallation
    for item in to_uninstall:
        if item[0] == "pip":
            pkg_name = item[1]
            if pip_manager.uninstall_package(pkg_name):
                print(color_text(f"[pip] {pkg_name} uninstalled.", GREEN))
            else:
                print(color_text(f"[pip] Failed to uninstall {pkg_name}.", RED))
        elif item[0] == "brew":
            pkg_name, is_cask = item[1], item[2]
            if brew_manager.uninstall_package(pkg_name, is_cask):
                label = "cask" if is_cask else "formula"
                print(color_text(f"[brew] {pkg_name} ({label}) uninstalled.", GREEN))
            else:
                print(color_text(
                    f"[brew] Failed to uninstall {pkg_name} "
                    f"(it may have dependents or could not be verified).", RED))
    print(color_text("Operation completed.", GREEN))


def view_package_info():
    # Retrieve packages (sequentially)
    pip_packages = pip_manager.get_installed_packages()
    brew_formulas, brew_casks = brew_manager.get_installed_packages()

    choices = {}
    idx = 1
    print("\n" + color_text("=== pip Packages ===", MAGENTA, bold=True))
    for pkg in pip_packages:
        print(f"{color_text(f'{idx}.', BLUE)} {color_text(pkg, YELLOW)} (pip)")
        choices[idx] = ("pip", pkg)
        idx += 1
    print("\n" + color_text("=== Homebrew Formulas ===", MAGENTA, bold=True))
    for pkg in brew_formulas:
        print(f"{color_text(f'{idx}.', BLUE)} {color_text(pkg, YELLOW)} (brew - formula)")
        choices[idx] = ("brew", pkg, False)
        idx += 1
    print("\n" + color_text("=== Homebrew Casks ===", MAGENTA, bold=True))
    for pkg in brew_casks:
        print(f"{color_text(f'{idx}.', BLUE)} {color_text(pkg, YELLOW)} (brew - cask)")
        choices[idx] = ("brew", pkg, True)
        idx += 1

    choice = input(
        "\n" + color_text("Enter the number of a package for more information: ", YELLOW)).strip()
    if not choice.isdigit():
        print(color_text("Invalid input.", RED))
        return
    num = int(choice)
    if num not in choices:
        print(color_text("Unknown number.", RED))
        return

    item = choices[num]
    if item[0] == "pip":
        info = pip_manager.get_package_info(item[1])
        if info:
            print("\n" + color_text(f"--- Information on {info['name']} (pip) ---", CYAN, bold=True))
            print(color_text(f"Version: {info['version']}", GREEN))
            print(color_text(f"Description: {info['summary']}", GREEN))
            if info.get("home_page"):
                print(color_text(f"Homepage: {info['home_page']}", GREEN))
        else:
            print(color_text("No information found.", RED))
    elif item[0] == "brew":
        info = brew_manager.get_package_info(item[1], item[2])
        if info:
            print("\n" + color_text(f"--- Information on {item[1]} (brew) ---", CYAN, bold=True))
            if info.get("version"):
                print(color_text(f"Version: {info['version']}", GREEN))
            if info.get("desc"):
                print(color_text(f"Description: {info['desc']}", GREEN))
            if info.get("homepage"):
                print(color_text(f"Homepage: {info['homepage']}", GREEN))
        else:
            print(color_text("No information found.", RED))


def _configure_logging():
    """Configure logging to a stable per-user state directory.

    Writing to a bare ``package_manager.log`` would scatter logs in whatever
    directory the installed command happened to be run from (and fail on a
    read-only CWD). We use ``$XDG_STATE_HOME`` (or ``~/.local/state``) and fall
    back to stderr if the directory cannot be created.
    """
    fmt = "%(asctime)s - %(levelname)s - %(message)s"
    base = os.environ.get("XDG_STATE_HOME") or os.path.join(os.path.expanduser("~"), ".local", "state")
    log_dir = os.path.join(base, "pipbrew-cleaner")
    try:
        os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(filename=os.path.join(log_dir, "package_manager.log"),
                            level=logging.INFO, format=fmt)
    except OSError:
        logging.basicConfig(level=logging.INFO, format=fmt)


def main():
    _configure_logging()
    logging.info("Starting pipbrew-cleaner")
    try:
        while True:
            choice = main_menu()
            if choice == "1":
                list_and_uninstall()
            elif choice == "2":
                view_package_info()
            elif choice == "3":
                print(color_text("Goodbye.", CYAN, bold=True))
                break
            else:
                print(color_text("Invalid choice. Please try again.", RED))
    except (KeyboardInterrupt, EOFError):
        print(color_text("\nInterrupted. Goodbye.", CYAN, bold=True))
    finally:
        logging.info("Exiting pipbrew-cleaner")
        logging.shutdown()


if __name__ == "__main__":
    main()
