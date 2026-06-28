#!/usr/bin/env bash
# Construit l'executable BoutiquePro avec PyInstaller (onedir, pret pour
# l'installeur NSIS dans packaging/installer.nsi).
#
# Usage:
#   bash packaging/build_exe.sh
#
# Prerequis:
#   pip install -r requirements-dev.txt
#
# Sur Windows, lancer plutot avec un Python Windows (PyInstaller produit un
# executable pour la plateforme sur laquelle il tourne) :
#   pip install -r requirements-dev.txt
#   bash packaging/build_exe.sh   (ou git-bash / WSL)
#
# Le resultat se trouve dans dist/BoutiquePro/ (mode onedir, requis par
# l'installeur NSIS fourni).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${ROOT_DIR}"

if ! command -v pyinstaller >/dev/null 2>&1; then
    echo "PyInstaller introuvable. Installez-le avec :"
    echo "  pip install -r requirements-dev.txt"
    exit 1
fi

rm -rf "${ROOT_DIR}/build" "${ROOT_DIR}/dist"

pyinstaller \
    --name BoutiquePro \
    --windowed \
    --onedir \
    --noconfirm \
    --clean \
    boutiquepro/main.py

echo ""
echo "Build termine. Executable disponible dans : dist/BoutiquePro/"
echo "Pour generer l'installeur Windows, utilisez packaging/installer.nsi"
echo "(necessite NSIS, sous Windows ou via 'makensis' sous Linux/Wine)."
