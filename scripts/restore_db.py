#!/usr/bin/env python3
"""Restaure la base de donnees SQLite de BoutiquePro a partir d'une sauvegarde.

Usage:
    python scripts/restore_db.py <chemin_du_fichier_de_sauvegarde>

ATTENTION : cette operation remplace le fichier de base de donnees actuel.
La base existante est d'abord copiee dans un fichier ".avant_restauration"
au cas ou, avant d'etre remplacee.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from boutiquepro.database import get_database_path


def restore(backup_path: Path) -> None:
    if not backup_path.exists():
        print(f"Erreur : le fichier de sauvegarde n'existe pas ({backup_path}).")
        sys.exit(1)

    db_path = get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        securite_path = db_path.with_suffix(db_path.suffix + ".avant_restauration")
        shutil.copy2(db_path, securite_path)
        print(f"Base de donnees actuelle sauvegardee par securite vers : {securite_path}")

    shutil.copy2(backup_path, db_path)
    print(f"Restauration terminee avec succes depuis : {backup_path}")
    print(f"Base de donnees active : {db_path}")


def main():
    if len(sys.argv) != 2:
        print("Usage : python scripts/restore_db.py <chemin_du_fichier_de_sauvegarde>")
        sys.exit(1)

    backup_path = Path(sys.argv[1])
    restore(backup_path)


if __name__ == "__main__":
    main()
