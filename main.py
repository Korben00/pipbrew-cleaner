#!/usr/bin/env python3
# Pipbrew-cleaner
# Author: Manuel DORNE - Korben (https://korben.info)
"""
Interactive CLI tool to list and uninstall pip and Homebrew packages.
Displays package information progressively with colorized output,
all in English, and without using additional libraries.
"""

import logging
import sys
import time
import concurrent.futures

import pip_manager
import brew_manager

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

def color_text(text, color, bold=False, underline=False):
    """Return text wrapped in ANSI codes for color and style."""
    style = ""
    if bold:
        style += BOLD
    if underline:
        style += UNDERLINE
    return f"{style}{color}{text}{RESET}"

# Utility functions to fetch package info

def fetch_pip_info(pkg):
    """Fetch summary info for a pip package."""
    info = pip_manager.get_package_info(pkg)
    summary = info["summary"] if info and info.get("summary") else "No description available"
    return pkg, summary

def fetch_brew_info(pkg, is_cask):
    """Fetch description info for a Homebrew package (formula or cask)."""
    info = brew_manager.get_package_info(pkg, is_cask)
    desc = info["desc"] if info and info.get("desc") else "No description available"
    return pkg, desc

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
    filter_str = input(color_text("Filter packages by name (leave empty for none): ", YELLOW)).strip().lower()
    if filter_str:
        pip_packages = [p for p in pip_packages if filter_str in p.lower()]
        brew_formulas = [p for p in brew_formulas if filter_str in p.lower()]
        brew_casks = [p for p in brew_casks if filter_str in p.lower()]

    if not pip_packages and not brew_formulas and not brew_casks:
        print(color_text("No packages match the filter.", RED))
        return

    # Assign sequential numbers to each package across sections
    all_packages = {}
    current_index = 1

    # ---------------------------
    # Process pip packages
    print("\n" + color_text("=== pip Packages ===", MAGENTA, bold=True))
    pip_dict = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        pip_futures = {}
        for pkg in pip_packages:
            future = executor.submit(fetch_pip_info, pkg)
            pip_futures[future] = (current_index, pkg)
            current_index += 1

        # Display results as soon as each is available
        while pip_futures:
            done, _ = concurrent.futures.wait(pip_futures.keys(), timeout=0.1,
                                                return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                idx, pkg = pip_futures.pop(future)
                _, summary = future.result()
                if pkg in pip_manager.CRITICAL_PIP_PACKAGES:
                    line = f"{color_text(str(idx)+'.', BLUE)} {color_text(pkg, YELLOW)} (pip) {color_text('[protected]', RED)} - {summary}"
                else:
                    line = f"{color_text(str(idx)+'.', BLUE)} {color_text(pkg, YELLOW)} (pip) - {summary}"
                print(line)
                pip_dict[idx] = ("pip", pkg)
            time.sleep(0.05)

    # ---------------------------
    # Process Homebrew formulas
    print("\n" + color_text("=== Homebrew Formulas ===", MAGENTA, bold=True))
    brew_dict = {}
    with concurrent.futures.ThreadPoolExecutor() as executor:
        brew_futures = {}
        for pkg in brew_formulas:
            future = executor.submit(fetch_brew_info, pkg, False)
            brew_futures[future] = (current_index, pkg)
            current_index += 1

        while brew_futures:
            done, _ = concurrent.futures.wait(brew_futures.keys(), timeout=0.1,
                                                return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                idx, pkg = brew_futures.pop(future)
                _, desc = future.result()
                line = f"{color_text(str(idx)+'.', BLUE)} {color_text(pkg, YELLOW)} (brew - formula) - {desc}"
                print(line)
                brew_dict[idx] = ("brew", pkg, False)
            time.sleep(0.05)

    # ---------------------------
    # Process Homebrew casks
    print("\n" + color_text("=== Homebrew Casks ===", MAGENTA, bold=True))
    with concurrent.futures.ThreadPoolExecutor() as executor:
        cask_futures = {}
        for pkg in brew_casks:
            future = executor.submit(fetch_brew_info, pkg, True)
            cask_futures[future] = (current_index, pkg)
            current_index += 1

        while cask_futures:
            done, _ = concurrent.futures.wait(cask_futures.keys(), timeout=0.1,
                                                return_when=concurrent.futures.FIRST_COMPLETED)
            for future in done:
                idx, pkg = cask_futures.pop(future)
                _, desc = future.result()
                line = f"{color_text(str(idx)+'.', BLUE)} {color_text(pkg, YELLOW)} (brew - cask) - {desc}"
                print(line)
                brew_dict[idx] = ("brew", pkg, True)
            time.sleep(0.05)

    # Combine dictionaries for selection
    all_packages.update(pip_dict)
    all_packages.update(brew_dict)

    # Ask user to select packages to uninstall
    choice = input("\n" + color_text("Enter the numbers of packages to uninstall (separated by commas): ", YELLOW)).strip()
    if not choice:
        print(color_text("No packages selected.", RED))
        return

    try:
        indices = [int(x.strip()) for x in choice.split(",") if x.strip().isdigit()]
    except ValueError:
        print(color_text("Invalid input.", RED))
        return

    print(color_text("You have selected the following packages:", CYAN, bold=True))
    to_uninstall = []
    for i in indices:
        if i in all_packages:
            source, pkg = all_packages[i][0], all_packages[i][1]
            if source == "pip" and pkg in pip_manager.CRITICAL_PIP_PACKAGES:
                print(f"-> {color_text(pkg, YELLOW)} (pip) {color_text('[protected, will not be uninstalled]', RED)}")
            else:
                label = "brew cask" if (source == "brew" and all_packages[i][2]) else ("brew formula" if source == "brew" else "pip")
                print(f"-> {color_text(pkg, YELLOW)} ({label})")
                to_uninstall.append(all_packages[i])
        else:
            print(f"-> {color_text('Number ' + str(i) + ' unknown', RED)}")

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
            pkg_name = item[1]
            is_cask = item[2]
            if brew_manager.uninstall_package(pkg_name, is_cask):
                label = "cask" if is_cask else "formula"
                print(color_text(f"[brew] {pkg_name} ({label}) uninstalled.", GREEN))
            else:
                print(color_text(f"[brew] Failed to uninstall {pkg_name}.", RED))
    print(color_text("Operation completed.", GREEN))

def view_package_info():
    # Retrieve packages (sequentially)
    pip_packages = pip_manager.get_installed_packages()
    brew_formulas, brew_casks = brew_manager.get_installed_packages()

    choices = {}
    idx = 1
    print("\n" + color_text("=== pip Packages ===", MAGENTA, bold=True))
    for pkg in pip_packages:
        print(f"{color_text(str(idx)+'.', BLUE)} {color_text(pkg, YELLOW)} (pip)")
        choices[idx] = ("pip", pkg)
        idx += 1
    print("\n" + color_text("=== Homebrew Formulas ===", MAGENTA, bold=True))
    for pkg in brew_formulas:
        print(f"{color_text(str(idx)+'.', BLUE)} {color_text(pkg, YELLOW)} (brew - formula)")
        choices[idx] = ("brew", pkg, False)
        idx += 1
    print("\n" + color_text("=== Homebrew Casks ===", MAGENTA, bold=True))
    for pkg in brew_casks:
        print(f"{color_text(str(idx)+'.', BLUE)} {color_text(pkg, YELLOW)} (brew - cask)")
        choices[idx] = ("brew", pkg, True)
        idx += 1

    choice = input("\n" + color_text("Enter the number of a package for more information: ", YELLOW)).strip()
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
                print(color_text(info["version"], GREEN))
            if info.get("desc"):
                print(color_text(f"Description: {info['desc']}", GREEN))
            if info.get("homepage"):
                print(color_text(f"Homepage: {info['homepage']}", GREEN))
        else:
            print(color_text("No information found.", RED))

def main():
    # Setup logging to a text file
    logging.basicConfig(filename="package_manager.log", level=logging.INFO,
                        format="%(asctime)s - %(levelname)s - %(message)s")
    logging.info("Starting pipcleaner tool")
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
    logging.info("Exiting pipcleaner tool")
    logging.shutdown()

if __name__ == "__main__":
    main()
