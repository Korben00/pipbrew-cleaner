"""Tests for pipbrew_cleaner.pip_manager."""
import json
import subprocess

import pytest

from pipbrew_cleaner import pip_manager


def _completed(args, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)


# --- canonical_name / is_critical -------------------------------------------

@pytest.mark.parametrize("name", [
    "pip", "Pip", "PIP", "setuptools", "wheel",
    "pipbrew-cleaner", "pipbrew_cleaner", "PipBrew.Cleaner",
])
def test_is_critical_protects_core_and_self(name):
    assert pip_manager.is_critical(name) is True


@pytest.mark.parametrize("name", ["numpy", "requests", "pip-tools", "wheely"])
def test_is_critical_allows_normal_packages(name):
    assert pip_manager.is_critical(name) is False


def test_canonical_name_collapses_separators():
    assert pip_manager.canonical_name("Foo._-Bar") == "foo-bar"


# --- get_installed_packages --------------------------------------------------

def test_get_installed_packages_parses_json(monkeypatch):
    payload = json.dumps([{"name": "requests", "version": "2.31.0"},
                          {"name": "rich", "version": "13.0.0"}])
    monkeypatch.setattr(pip_manager.subprocess, "run",
                        lambda *a, **k: _completed(a, stdout=payload))
    assert pip_manager.get_installed_packages() == ["requests", "rich"]


def test_get_installed_packages_empty_on_error(monkeypatch):
    monkeypatch.setattr(pip_manager.subprocess, "run",
                        lambda *a, **k: _completed(a, returncode=1, stderr="boom"))
    assert pip_manager.get_installed_packages() == []


def test_get_installed_packages_handles_bad_json(monkeypatch):
    monkeypatch.setattr(pip_manager.subprocess, "run",
                        lambda *a, **k: _completed(a, stdout="not json"))
    assert pip_manager.get_installed_packages() == []


# --- get_package_info --------------------------------------------------------

def test_get_package_info_parses_fields_and_colon_summary(monkeypatch):
    out = (
        "Name: requests\n"
        "Version: 2.31.0\n"
        "Summary: HTTP: a library for humans\n"
        "Home-page: https://requests.example\n"
    )
    monkeypatch.setattr(pip_manager.subprocess, "run",
                        lambda *a, **k: _completed(a, stdout=out))
    info = pip_manager.get_package_info("requests")
    assert info["name"] == "requests"
    assert info["version"] == "2.31.0"
    assert info["summary"] == "HTTP: a library for humans"
    assert info["home_page"] == "https://requests.example"


def test_get_package_info_homepage_falls_back_to_project_urls(monkeypatch):
    out = (
        "Name: somepkg\n"
        "Version: 1.0\n"
        "Summary: A package\n"
        "Home-page: \n"
        "Project-URLs: Homepage, https://example.org/home\n"
        "              Source, https://example.org/src\n"
    )
    monkeypatch.setattr(pip_manager.subprocess, "run",
                        lambda *a, **k: _completed(a, stdout=out))
    info = pip_manager.get_package_info("somepkg")
    assert info["home_page"] == "https://example.org/home"


def test_get_package_info_none_on_failure(monkeypatch):
    monkeypatch.setattr(pip_manager.subprocess, "run",
                        lambda *a, **k: _completed(a, returncode=1, stderr="no such package"))
    assert pip_manager.get_package_info("ghost") is None


def test_get_packages_info_batch_splits_records(monkeypatch):
    out = (
        "Name: requests\nVersion: 2.31.0\nSummary: HTTP for humans\nHome-page: https://r.ex\n"
        "---\n"
        "Name: Rich\nVersion: 13.0\nSummary: Rich text\nHome-page: https://rich.ex\n"
    )
    monkeypatch.setattr(pip_manager.subprocess, "run",
                        lambda *a, **k: _completed(a, stdout=out))
    info = pip_manager.get_packages_info(["requests", "rich"])
    assert info["requests"]["summary"] == "HTTP for humans"
    # Keyed canonically, so "Rich" is reachable as "rich".
    assert info["rich"]["summary"] == "Rich text"


# --- uninstall_package -------------------------------------------------------

def test_uninstall_refuses_critical_without_running_pip(monkeypatch):
    called = []
    monkeypatch.setattr(pip_manager.subprocess, "run",
                        lambda *a, **k: called.append(a) or _completed(a))
    assert pip_manager.uninstall_package("pip") is False
    assert called == []  # never shelled out


def test_uninstall_success(monkeypatch):
    monkeypatch.setattr(pip_manager.subprocess, "run",
                        lambda *a, **k: _completed(a, returncode=0))
    assert pip_manager.uninstall_package("requests") is True


def test_uninstall_reports_failure(monkeypatch):
    monkeypatch.setattr(pip_manager.subprocess, "run",
                        lambda *a, **k: _completed(a, returncode=1, stderr="error"))
    assert pip_manager.uninstall_package("requests") is False
