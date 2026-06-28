"""Fixtures pytest partagees: base SQLite temporaire par test."""
from __future__ import annotations

import pytest

from boutiquepro import database
from boutiquepro.models import Boutique


@pytest.fixture()
def session_factory(tmp_path):
    """Cree une base SQLite temporaire et neuve pour chaque test, et
    reinitialise l'engine global de boutiquepro.database (qui est un
    singleton module-level) pour eviter toute fuite entre tests."""
    db_path = tmp_path / "test_boutiquepro.db"
    engine, factory = database.init_db(str(db_path))
    yield factory
    engine.dispose()
    database._engine = None
    database._SessionFactory = None


@pytest.fixture()
def session(session_factory):
    with session_factory() as s:
        yield s


@pytest.fixture()
def boutique(session):
    b = Boutique(nom="Boutique Test", adresse="Dakar")
    session.add(b)
    session.commit()
    return b


@pytest.fixture()
def boutique2(session):
    b = Boutique(nom="Boutique Test 2", adresse="Thies")
    session.add(b)
    session.commit()
    return b
