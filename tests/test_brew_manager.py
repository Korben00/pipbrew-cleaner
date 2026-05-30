"""Tests for pipbrew_cleaner.brew_manager."""
import json
import subprocess

from pipbrew_cleaner import brew_manager


def _completed(args, returncode=0, stdout="", stderr=""):
    return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)


class FakeBrew:
    """Route `brew ...` invocations to canned results, recording every call."""

    def __init__(self, handlers):
        self.handlers = handlers
        self.calls = []

    def run(self, cmd, *args, **kwargs):
        self.calls.append(list(cmd))
        for predicate, result in self.handlers:
            if predicate(cmd):
                return _completed(cmd, **result)
        return _completed(cmd, returncode=1, stderr="unhandled")

    def ran_uninstall(self):
        return any("uninstall" in c for c in self.calls)


def _install(monkeypatch, fake):
    monkeypatch.setattr(brew_manager.subprocess, "run", fake.run)


# --- get_installed_packages --------------------------------------------------

def test_get_installed_packages_splits_formula_and_cask(monkeypatch):
    fake = FakeBrew([
        (lambda c: "--formula" in c, {"stdout": "git\nwget\n"}),
        (lambda c: "--cask" in c, {"stdout": "iterm2\nalacritty\n"}),
    ])
    _install(monkeypatch, fake)
    formulas, casks = brew_manager.get_installed_packages()
    assert formulas == ["git", "wget"]
    assert casks == ["iterm2", "alacritty"]


# --- get_package_info (JSON parsing) ----------------------------------------

def test_get_package_info_formula_uses_json(monkeypatch):
    payload = json.dumps({
        "formulae": [{
            "desc": "Distributed revision control system: fast and free",
            "homepage": "https://git-scm.com",
            "versions": {"stable": "2.54.0"},
        }],
        "casks": [],
    })
    fake = FakeBrew([(lambda c: True, {"stdout": payload})])
    _install(monkeypatch, fake)
    info = brew_manager.get_package_info("git", is_cask=False)
    # Description containing a colon must survive (old text parser dropped it).
    assert info["desc"] == "Distributed revision control system: fast and free"
    assert info["homepage"] == "https://git-scm.com"
    assert info["version"] == "2.54.0"  # clean version, not the "==> ..." header


def test_get_package_info_cask_uses_json(monkeypatch):
    payload = json.dumps({
        "formulae": [],
        "casks": [{
            "desc": "Terminal emulator",
            "homepage": "https://iterm2.com",
            "version": "3.5.0",
        }],
    })
    fake = FakeBrew([(lambda c: True, {"stdout": payload})])
    _install(monkeypatch, fake)
    info = brew_manager.get_package_info("iterm2", is_cask=True)
    assert info["desc"] == "Terminal emulator"
    assert info["version"] == "3.5.0"
    assert ["brew", "info", "--json=v2", "--cask", "iterm2"] in fake.calls


def test_get_package_info_none_on_failure(monkeypatch):
    fake = FakeBrew([(lambda c: True, {"returncode": 1, "stderr": "No such keg"})])
    _install(monkeypatch, fake)
    assert brew_manager.get_package_info("ghost") is None


def test_get_packages_info_batch_maps_names_and_aliases(monkeypatch):
    payload = json.dumps({
        "formulae": [
            {"name": "git", "full_name": "git", "desc": "VCS",
             "homepage": "h1", "versions": {"stable": "2.54"}},
            {"name": "openssl@3", "full_name": "openssl@3", "aliases": ["openssl"],
             "desc": "TLS toolkit", "homepage": "h2", "versions": {"stable": "3.3"}},
        ],
        "casks": [],
    })
    fake = FakeBrew([(lambda c: True, {"stdout": payload})])
    _install(monkeypatch, fake)
    info = brew_manager.get_packages_info(["git", "openssl@3"], is_cask=False)
    assert info["git"]["desc"] == "VCS"
    assert info["openssl@3"]["version"] == "3.3"
    # Aliases are reachable too, so lookups by whatever `brew list` returned hit.
    assert info["openssl"]["desc"] == "TLS toolkit"
    # A single brew invocation for the whole batch.
    assert sum(1 for c in fake.calls if "info" in c) == 1


def test_get_packages_info_batch_casks(monkeypatch):
    payload = json.dumps({
        "formulae": [],
        "casks": [
            {"token": "iterm2", "desc": "Terminal", "homepage": "h", "version": "3.5"},
            {"token": "alacritty", "desc": "GPU terminal", "homepage": "h2", "version": "0.13"},
        ],
    })
    fake = FakeBrew([(lambda c: True, {"stdout": payload})])
    _install(monkeypatch, fake)
    info = brew_manager.get_packages_info(["iterm2", "alacritty"], is_cask=True)
    assert info["iterm2"]["version"] == "3.5"
    assert info["alacritty"]["desc"] == "GPU terminal"


# --- uninstall_package (safety) ---------------------------------------------

def test_uninstall_formula_no_dependents_succeeds(monkeypatch):
    fake = FakeBrew([
        (lambda c: "uses" in c, {"returncode": 0, "stdout": ""}),
        (lambda c: "uninstall" in c, {"returncode": 0}),
    ])
    _install(monkeypatch, fake)
    assert brew_manager.uninstall_package("wget", is_cask=False) is True
    assert fake.ran_uninstall()


def test_uninstall_formula_aborts_when_dependents_present(monkeypatch):
    fake = FakeBrew([
        (lambda c: "uses" in c, {"returncode": 0, "stdout": "curl\nhttpie\n"}),
        (lambda c: "uninstall" in c, {"returncode": 0}),
    ])
    _install(monkeypatch, fake)
    assert brew_manager.uninstall_package("openssl", is_cask=False) is False
    assert not fake.ran_uninstall()  # must not remove a depended-on formula


def test_uninstall_formula_fails_closed_when_uses_errors(monkeypatch):
    # If `brew uses` cannot run, we must NOT fall through to uninstall.
    fake = FakeBrew([
        (lambda c: "uses" in c, {"returncode": 1, "stderr": "brew error"}),
        (lambda c: "uninstall" in c, {"returncode": 0}),
    ])
    _install(monkeypatch, fake)
    assert brew_manager.uninstall_package("openssl", is_cask=False) is False
    assert not fake.ran_uninstall()


def test_uninstall_cask_skips_dependency_check(monkeypatch):
    fake = FakeBrew([(lambda c: "uninstall" in c, {"returncode": 0})])
    _install(monkeypatch, fake)
    assert brew_manager.uninstall_package("alacritty", is_cask=True) is True
    assert ["brew", "uninstall", "--cask", "alacritty"] in fake.calls
    assert not any("uses" in c for c in fake.calls)
