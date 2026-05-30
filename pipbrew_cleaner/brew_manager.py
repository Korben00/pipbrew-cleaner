# pipbrew-cleaner
# Author: Manuel DORNE - Korben (https://korben.info)
"""Manage Homebrew packages: listing, info, and uninstall."""
import json
import logging
import subprocess


def get_installed_packages():
    """Return two lists: (formulas, casks) installed via Homebrew."""
    formulas, casks = [], []
    try:
        result_formulas = subprocess.run(
            ["brew", "list", "--formula"], capture_output=True, text=True, check=False)
        if result_formulas.returncode == 0:
            formulas = [line.strip() for line in result_formulas.stdout.splitlines() if line.strip()]
        else:
            logging.error("'brew list --formula' failed: %s", result_formulas.stderr.strip())

        result_casks = subprocess.run(
            ["brew", "list", "--cask"], capture_output=True, text=True, check=False)
        if result_casks.returncode == 0:
            casks = [line.strip() for line in result_casks.stdout.splitlines() if line.strip()]
        else:
            logging.error("'brew list --cask' failed: %s", result_casks.stderr.strip())
    except FileNotFoundError:
        logging.error("Homebrew ('brew') is not installed or not on PATH.")
    except Exception as exc:  # noqa: BLE001
        logging.error("Exception while listing Homebrew packages: %s", exc)
    return formulas, casks


def get_package_info(name, is_cask=False):
    """Return an info dict for a Homebrew package, or None on error.

    Keys: 'name', 'desc', 'homepage', 'version'. Parsing is done from
    ``brew info --json=v2`` (structured data) instead of scraping the
    human-readable output, which avoids two bugs of the old text parser:
    treating the ``==> name: ...`` header as the version, and discarding any
    description that legitimately contains a colon.
    """
    try:
        cmd = ["brew", "info", "--json=v2"]
        if is_cask:
            cmd.append("--cask")
        cmd.append(name)
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not result.stdout:
            logging.error("'brew info' failed for %s: %s", name, result.stderr.strip())
            return None
        data = json.loads(result.stdout)
        if is_cask:
            entries = data.get("casks", [])
            if not entries:
                return None
            cask = entries[0]
            return {
                "name": name,
                "desc": cask.get("desc"),
                "homepage": cask.get("homepage"),
                "version": cask.get("version"),
            }
        entries = data.get("formulae", [])
        if not entries:
            return None
        formula = entries[0]
        versions = formula.get("versions") or {}
        return {
            "name": name,
            "desc": formula.get("desc"),
            "homepage": formula.get("homepage"),
            "version": versions.get("stable"),
        }
    except json.JSONDecodeError as exc:
        logging.error("Could not parse 'brew info' output for %s: %s", name, exc)
        return None
    except FileNotFoundError:
        logging.error("Homebrew ('brew') is not installed or not on PATH.")
        return None
    except Exception as exc:  # noqa: BLE001
        logging.error("Exception in get_package_info(%s): %s", name, exc)
        return None


def uninstall_package(name, is_cask=False):
    """Uninstall a Homebrew formula or cask. Return True on success.

    For formulas, refuse to proceed if other installed packages depend on the
    target. The dependency check fails *closed*: if ``brew uses`` cannot be run
    (e.g. brew error), the uninstall is aborted rather than proceeding blindly.
    """
    try:
        if not is_cask:
            uses_result = subprocess.run(
                ["brew", "uses", "--installed", name],
                capture_output=True, text=True, check=False)
            if uses_result.returncode != 0:
                logging.warning(
                    "Could not verify dependents of %s (brew uses failed: %s); uninstall aborted.",
                    name, uses_result.stderr.strip())
                return False
            dependents = [line.strip() for line in uses_result.stdout.splitlines() if line.strip()]
            if dependents:
                logging.warning(
                    "Uninstall of %s aborted, other installed packages depend on it: %s",
                    name, dependents)
                return False

        cmd = ["brew", "uninstall"]
        if is_cask:
            cmd.append("--cask")
        cmd.append(name)
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logging.info("%s (%s) uninstalled successfully.", name, "cask" if is_cask else "formula")
            return True
        logging.error("Failed to uninstall %s: %s", name, result.stderr.strip())
        return False
    except FileNotFoundError:
        logging.error("Homebrew ('brew') is not installed or not on PATH.")
        return False
    except Exception as exc:  # noqa: BLE001
        logging.error("Exception while uninstalling %s: %s", name, exc)
        return False
