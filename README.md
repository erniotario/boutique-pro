# BoutiquePro

Application de bureau (100% hors-ligne) pour la gestion de plusieurs boutiques
a Yaounde, Cameroun. Stack : Python 3.10+, PySide6, SQLAlchemy, SQLite.

## Installation

```bash
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sous Windows
pip install -r requirements.txt
```

## Lancement

```bash
python -m boutiquepro.main
```

La base de donnees SQLite est creee automatiquement dans le repertoire de
donnees utilisateur (ex: `~/.local/share/BoutiquePro/boutiquepro.db` sous
Linux) au premier lancement.
