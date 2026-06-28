"""Tests d'authentification: login PIN correct/incorrect, validation du
format de PIN, et logique de cantonnement (scoping) des gerants a leur
boutique."""
from __future__ import annotations

import pytest

from boutiquepro.models import RoleUtilisateur, Utilisateur
from boutiquepro.services import pin_is_valid as _pin_is_valid


class TestPinFormatValidation:
    @pytest.mark.parametrize("pin", ["1234", "12345", "123456"])
    def test_valid_pins(self, pin):
        assert _pin_is_valid(pin) is True

    @pytest.mark.parametrize(
        "pin",
        [
            "",
            "123",  # trop court
            "1234567",  # trop long
            "abcd",  # non numerique
            "12a4",  # partiellement non numerique
            "12 34",  # espace
            "-123",  # signe
        ],
    )
    def test_invalid_pins(self, pin):
        assert _pin_is_valid(pin) is False


class TestLoginLogic:
    def test_login_pin_correct(self, session):
        u = Utilisateur(nom="Patron", role=RoleUtilisateur.PROPRIETAIRE)
        u.set_pin("4242")
        session.add(u)
        session.commit()

        fetched = session.get(Utilisateur, u.id)
        assert fetched.verify_pin("4242") is True

    def test_login_pin_incorrect(self, session):
        u = Utilisateur(nom="Patron", role=RoleUtilisateur.PROPRIETAIRE)
        u.set_pin("4242")
        session.add(u)
        session.commit()

        fetched = session.get(Utilisateur, u.id)
        assert fetched.verify_pin("0000") is False

    def test_gerant_boutique_scoping(self, session, boutique, boutique2):
        gerant = Utilisateur(
            nom="Gerant1", role=RoleUtilisateur.GERANT, boutique_id=boutique.id
        )
        gerant.set_pin("1111")
        session.add(gerant)
        session.commit()

        assert gerant.boutique_id == boutique.id
        assert gerant.boutique_id != boutique2.id
        assert gerant.role == RoleUtilisateur.GERANT

    def test_proprietaire_has_no_boutique_restriction(self, session, boutique):
        proprio = Utilisateur(nom="Patron", role=RoleUtilisateur.PROPRIETAIRE)
        proprio.set_pin("9999")
        session.add(proprio)
        session.commit()
        assert proprio.boutique_id is None
