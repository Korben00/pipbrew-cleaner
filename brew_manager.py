# Pipbrew-cleaner
# Author: Manuel DORNE - Korben (https://korben.info)
"""Module for managing Homebrew packages (listing, info, uninstall)."""
import subprocess
import logging

def get_installed_packages():
    """Retourne deux listes : (formules, casks) installés via Homebrew."""
    formulas = []
    casks = []
    try:
        # Récupérer les formules installées
        result_formulas = subprocess.run(["brew", "list", "--formula"],
                                         capture_output=True, text=True, check=False)
        if result_formulas.returncode == 0:
            for line in result_formulas.stdout.splitlines():
                if line:
                    formulas.append(line.strip())
        else:
            logging.error(f"Erreur avec 'brew list --formula': {result_formulas.stderr.strip()}")
        # Récupérer les casks installés
        result_casks = subprocess.run(["brew", "list", "--cask"],
                                      capture_output=True, text=True, check=False)
        if result_casks.returncode == 0:
            for line in result_casks.stdout.splitlines():
                if line:
                    casks.append(line.strip())
        else:
            logging.error(f"Erreur avec 'brew list --cask': {result_casks.stderr.strip()}")
    except Exception as e:
        logging.error(f"Exception lors de la récupération des packages Homebrew: {e}")
    return formulas, casks

def get_package_info(name, is_cask=False):
    """Retourne un dictionnaire d'informations pour un package Homebrew.
    
    Les clés incluent 'name', 'desc', 'homepage' et 'version'.
    Renvoie None en cas d'erreur.
    """
    try:
        cmd = ["brew", "info"]
        if is_cask:
            cmd.append("--cask")
        cmd.append(name)
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not result.stdout:
            logging.error(f"brew info a échoué pour {name}: {result.stderr.strip()}")
            return None
        info_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        info = {"name": name, "desc": None, "homepage": None, "version": None}
        if info_lines:
            info["version"] = info_lines[0]
        for line in info_lines[1:]:
            if line.startswith("http://") or line.startswith("https://"):
                info["homepage"] = line
                continue
            if line.startswith("/") or line.lower().startswith("analytics") or line.lower().startswith("dependencies"):
                continue
            if info["desc"] is None and ":" not in line:
                info["desc"] = line
                break
        return info
    except Exception as e:
        logging.error(f"Exception dans get_package_info({name}): {e}")
        return None

def uninstall_package(name, is_cask=False):
    """Désinstalle un package Homebrew (formule ou cask).
    
    Renvoie True si la désinstallation réussit, False sinon.
    """
    try:
        # Pour une formule, vérifier si d'autres packages en dépendent
        if not is_cask:
            uses_result = subprocess.run(["brew", "uses", "--installed", name],
                                         capture_output=True, text=True, check=False)
            if uses_result.returncode == 0:
                dependents = [line.strip() for line in uses_result.stdout.splitlines() if line.strip()]
                if dependents:
                    logging.warning(f"Désinstallation de {name} annulée, dépendances présentes: {dependents}")
                    return False
        # Procéder à la désinstallation
        cmd = ["brew", "uninstall"]
        if is_cask:
            cmd.append("--cask")
        cmd.append(name)
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logging.info(f"{name} ({'cask' if is_cask else 'formule'}) désinstallé avec succès.")
            return True
        else:
            logging.error(f"Échec de la désinstallation de {name}: {result.stderr.strip()}")
            return False
    except Exception as e:
        logging.error(f"Exception lors de la désinstallation de {name}: {e}")
        return False
