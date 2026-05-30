# pipbrew-cleaner
# Author: Manuel DORNE - Korben (https://korben.info)
"""Manage pip packages: listing, info, and uninstall."""
import json
import logging
import re
import subprocess
import sys


def canonical_name(name):
    """Normalize a distribution name per PEP 503.

    Lowercases and collapses any run of ``-``, ``_`` or ``.`` into a single
    ``-`` so that e.g. ``Pip``, ``pipbrew_cleaner`` and ``pipbrew-cleaner`` all
    compare equal. pip itself normalizes names this way, so the protection set
    must do the same to be reliable.
    """
    return re.sub(r"[-_.]+", "-", name).strip().lower()


# Packages that must never be uninstalled. Stored in canonical form and always
# compared via is_critical() so casing / separator differences cannot bypass it.
# "pipbrew-cleaner" is the distribution name shown by `pip list`, so listing it
# here is what actually protects the tool from uninstalling itself.
CRITICAL_PIP_PACKAGES = {
    canonical_name(n) for n in ("pip", "setuptools", "wheel", "pipbrew-cleaner")
}


def is_critical(package):
    """Return True if *package* is protected from uninstallation."""
    return canonical_name(package) in CRITICAL_PIP_PACKAGES


def get_installed_packages():
    """Return the list of installed pip package names.

    Uses ``pip list --format=json`` rather than ``--format=freeze`` so that
    editable installs (``-e``) and direct-URL installs (``name @ url``) yield
    clean names instead of a whole requirement line.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logging.error("'pip list' failed: %s", result.stderr.strip())
            return []
        try:
            data = json.loads(result.stdout or "[]")
        except json.JSONDecodeError as exc:
            logging.error("Could not parse 'pip list' output: %s", exc)
            return []
        return [entry["name"] for entry in data if entry.get("name")]
    except Exception as exc:  # noqa: BLE001 - never let listing crash the CLI
        logging.error("Exception in get_installed_packages: %s", exc)
        return []


def get_package_info(package):
    """Return details for a pip package, or None on error.

    The returned dict holds 'name', 'version', 'summary' and 'home_page'.
    ``pip show --verbose`` is used so that, when the legacy ``Home-page`` field
    is empty (common on modern wheels), the homepage can be recovered from the
    ``Project-URLs`` block.
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", "--verbose", package],
            capture_output=True, text=True, check=False)
        if result.returncode != 0 or not result.stdout:
            logging.error("'pip show' failed for %s: %s", package, result.stderr.strip())
            return None
        info = {"name": None, "version": None, "summary": None, "home_page": None}
        project_urls = {}
        in_urls = False
        for line in result.stdout.splitlines():
            if in_urls:
                # Indented "Label, URL" entries that follow "Project-URLs:".
                if line[:1] in (" ", "\t") and "," in line:
                    label, _, url = line.strip().partition(",")
                    project_urls[label.strip().lower()] = url.strip()
                    continue
                in_urls = False
            if line.startswith("Name:"):
                info["name"] = line.split(":", 1)[1].strip()
            elif line.startswith("Version:"):
                info["version"] = line.split(":", 1)[1].strip()
            elif line.startswith("Summary:"):
                info["summary"] = line.split(":", 1)[1].strip()
            elif line.startswith("Home-page:"):
                info["home_page"] = line.split(":", 1)[1].strip()
            elif line.startswith("Project-URLs:"):
                in_urls = True
                rest = line.split(":", 1)[1].strip()
                if rest and "," in rest:
                    label, _, url = rest.partition(",")
                    project_urls[label.strip().lower()] = url.strip()
        if not info["home_page"]:
            for key in ("homepage", "home-page", "documentation", "source", "repository"):
                if project_urls.get(key):
                    info["home_page"] = project_urls[key]
                    break
        return info
    except Exception as exc:  # noqa: BLE001
        logging.error("Exception in get_package_info(%s): %s", package, exc)
        return None


def uninstall_package(package):
    """Uninstall a pip package. Return True on success, False otherwise."""
    if is_critical(package):
        logging.warning("Refused to uninstall critical package: %s", package)
        return False
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "uninstall", "-y", package],
            capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logging.info("pip package %s uninstalled successfully.", package)
            return True
        logging.error("Failed to uninstall %s: %s", package, result.stderr.strip())
        return False
    except Exception as exc:  # noqa: BLE001
        logging.error("Exception while uninstalling %s: %s", package, exc)
        return False
