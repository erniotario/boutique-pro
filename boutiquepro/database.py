"""Configuration de la base de donnees SQLite (engine/session)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from boutiquepro.models import Base

APP_NAME = "BoutiquePro"


def get_data_dir() -> Path:
    """Repertoire de donnees utilisateur, multi-plateforme."""
    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA", str(Path.home()))
        path = Path(base) / APP_NAME
    elif sys.platform == "darwin":
        path = Path.home() / "Library" / "Application Support" / APP_NAME
    else:
        base = os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))
        path = Path(base) / APP_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_database_path() -> Path:
    return get_data_dir() / "boutiquepro.db"


def make_engine(db_path: str | Path | None = None):
    """Cree un engine SQLAlchemy. Si db_path est None, utilise le fichier
    standard du repertoire de donnees utilisateur. Passez ':memory:' ou un
    chemin de fichier temporaire pour les tests."""
    if db_path is None:
        db_path = get_database_path()
        url = f"sqlite:///{db_path}"
    elif db_path == ":memory:":
        url = "sqlite:///:memory:"
    else:
        url = f"sqlite:///{db_path}"
    engine = create_engine(url, echo=False, future=True)
    return engine


_engine = None
_SessionFactory: sessionmaker | None = None


def init_db(db_path: str | Path | None = None):
    """Initialise l'engine global, cree les tables, et retourne (engine, SessionFactory)."""
    global _engine, _SessionFactory
    _engine = make_engine(db_path)
    Base.metadata.create_all(_engine)
    _SessionFactory = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine, _SessionFactory


def get_session() -> Session:
    """Retourne une nouvelle session liee a l'engine global (initialise au besoin)."""
    global _SessionFactory
    if _SessionFactory is None:
        init_db()
    return _SessionFactory()
