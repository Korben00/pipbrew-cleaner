# Pipbrew-cleaner
# Author: Manuel DORNE - Korben (https://korben.info)
"""Module for managing pip packages (listing, info, uninstall)."""
import subprocess
import sys
import logging

# Liste des packages critiques à ne pas désinstaller
CRITICAL_PIP_PACKAGES = {"pip", "setuptools", "wheel", "pipcleaner"}

def get_installed_packages():
    """Retourne la liste des packages pip installés (noms uniquement)."""
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "list", "--format=freeze"], 
                                  capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logging.error(f"Erreur lors de l'exécution de pip list: {result.stderr.strip()}")
            return []
        packages = []
        for line in result.stdout.splitlines():
            if line:
                # Format : package==version
                pkg_name = line.split("==")[0]
                packages.append(pkg_name)
        return packages
    except Exception as e:
        logging.error(f"Exception dans get_installed_packages: {e}")
        return []

def get_package_info(package):
    """Retourne les informations détaillées d'un package pip.
    
    Renvoie un dictionnaire contenant 'name', 'version', 'summary' et 'home_page',
    ou None en cas d'erreur.
    """
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "show", package],
                                capture_output=True, text=True, check=False)
        if result.returncode != 0 or not result.stdout:
            logging.error(f"pip show a échoué pour {package}: {result.stderr.strip()}")
            return None
        info = {"name": None, "version": None, "summary": None, "home_page": None}
        for line in result.stdout.splitlines():
            if line.startswith("Name:"):
                info["name"] = line.split("Name:", 1)[1].strip()
            elif line.startswith("Version:"):
                info["version"] = line.split("Version:", 1)[1].strip()
            elif line.startswith("Summary:"):
                info["summary"] = line.split("Summary:", 1)[1].strip()
            elif line.startswith("Home-page:"):
                info["home_page"] = line.split("Home-page:", 1)[1].strip()
        return info
    except Exception as e:
        logging.error(f"Exception dans get_package_info({package}): {e}")
        return None

def uninstall_package(package):
    """Désinstalle un package pip via pip uninstall.
    
    Renvoie True en cas de succès, False sinon.
    """
    # Empêcher la désinstallation des packages critiques
    if package in CRITICAL_PIP_PACKAGES:
        logging.warning(f"Suppression refusée pour le package critique: {package}")
        return False
    try:
        result = subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", package],
                                capture_output=True, text=True, check=False)
        if result.returncode == 0:
            logging.info(f"Package pip {package} désinstallé avec succès.")
            return True
        else:
            logging.error(f"Échec de la désinstallation de {package}: {result.stderr.strip()}")
            return False
    except Exception as e:
        logging.error(f"Exception lors de la désinstallation de {package}: {e}")
        return False
