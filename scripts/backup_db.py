#!/usr/bin/env python3
"""Sauvegarde la base de donnees SQLite de BoutiquePro.

Usage:
    python scripts/backup_db.py [dossier_de_destination]

Si aucun dossier n'est precise, la sauvegarde est ecrite dans le repertoire
courant. Le fichier de sauvegarde est nomme avec un horodatage, par exemple :
    boutiquepro_backup_20260628_143000.db
"""
from __future__ import annotations

import datetime
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from boutiquepro.database import get_database_path


def backup(destination_dir: Path) -> Path:
    db_path = get_database_path()
    if not db_path.exists():
        print(f"Erreur : la base de donnees n'existe pas encore ({db_path}).")
        sys.exit(1)

    destination_dir.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = destination_dir / f"boutiquepro_backup_{horodatage}.db"

    shutil.copy2(db_path, backup_path)
    return backup_path


def main():
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    print(f"Sauvegarde de la base de donnees BoutiquePro vers : {destination}")
    backup_path = backup(destination)
    print(f"Sauvegarde terminee avec succes : {backup_path}")


if __name__ == "__main__":
    main()
