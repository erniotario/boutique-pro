"""Tests des modeles: Produit (marge), Client (solde_du), Utilisateur (PIN)."""
from __future__ import annotations

import datetime

import pytest

from boutiquepro.models import (
    Client,
    ModePaiement,
    Produit,
    Remboursement,
    Utilisateur,
    Vente,
)


class TestProduitMarge:
    def test_marge_unitaire(self):
        p = Produit(nom="Savon", prix_achat=100.0, prix_vente=150.0)
        assert p.marge_unitaire == 50.0

    def test_taux_marge(self):
        p = Produit(nom="Savon", prix_achat=100.0, prix_vente=150.0)
        assert p.taux_marge == pytest.approx((50.0 / 150.0) * 100.0)

    def test_taux_marge_prix_vente_zero(self):
        """Pas de division par zero quand prix_vente == 0."""
        p = Produit(nom="Gratuit", prix_achat=10.0, prix_vente=0.0)
        assert p.taux_marge == 0.0

    def test_marge_unitaire_negative(self):
        """Vente a perte: marge negative, pas d'exception."""
        p = Produit(nom="Promo", prix_achat=200.0, prix_vente=150.0)
        assert p.marge_unitaire == -50.0
        assert p.taux_marge == pytest.approx((-50.0 / 150.0) * 100.0)

    def test_defaults_none_safe(self):
        """prix_achat/prix_vente non definis explicitement (None) ne doivent
        pas planter marge_unitaire (garde `or 0.0`)."""
        p = Produit(nom="X")
        p.prix_achat = None
        p.prix_vente = None
        assert p.marge_unitaire == 0.0
        assert p.taux_marge == 0.0


class TestClientSoldeDu:
    def test_solde_du_sans_ventes(self, session):
        c = Client(nom="Aissatou")
        session.add(c)
        session.commit()
        assert c.solde_du() == 0.0

    def test_solde_du_une_vente_credit(self, session, boutique):
        c = Client(nom="Aissatou")
        session.add(c)
        session.commit()
        v = Vente(boutique_id=boutique.id, client_id=c.id, mode_paiement=ModePaiement.CREDIT, total=5000.0)
        session.add(v)
        session.commit()
        assert c.solde_du() == 5000.0

    def test_solde_du_ignore_ventes_comptant_et_mobile_money(self, session, boutique):
        c = Client(nom="Aissatou")
        session.add(c)
        session.commit()
        session.add(Vente(boutique_id=boutique.id, client_id=c.id, mode_paiement=ModePaiement.COMPTANT, total=1000.0))
        session.add(Vente(boutique_id=boutique.id, client_id=c.id, mode_paiement=ModePaiement.MOBILE_MONEY, total=2000.0))
        session.add(Vente(boutique_id=boutique.id, client_id=c.id, mode_paiement=ModePaiement.CREDIT, total=3000.0))
        session.commit()
        assert c.solde_du() == 3000.0

    def test_solde_du_plusieurs_credits_et_remboursement_partiel(self, session, boutique):
        c = Client(nom="Moussa")
        session.add(c)
        session.commit()
        session.add(Vente(boutique_id=boutique.id, client_id=c.id, mode_paiement=ModePaiement.CREDIT, total=4000.0))
        session.add(Vente(boutique_id=boutique.id, client_id=c.id, mode_paiement=ModePaiement.CREDIT, total=6000.0))
        session.add(Remboursement(client_id=c.id, montant=3000.0, date=datetime.datetime.now()))
        session.commit()
        # total credit = 10000, remb = 3000 -> solde 7000
        assert c.solde_du() == 7000.0

    def test_solde_du_remboursement_total(self, session, boutique):
        c = Client(nom="Fatou")
        session.add(c)
        session.commit()
        session.add(Vente(boutique_id=boutique.id, client_id=c.id, mode_paiement=ModePaiement.CREDIT, total=5000.0))
        session.add(Remboursement(client_id=c.id, montant=5000.0, date=datetime.datetime.now()))
        session.commit()
        assert c.solde_du() == 0.0

    def test_solde_du_remboursement_superieur_credit(self, session, boutique):
        """Remboursement excedentaire -> solde negatif (pas d'exception, comportement defini)."""
        c = Client(nom="Karim")
        session.add(c)
        session.commit()
        session.add(Vente(boutique_id=boutique.id, client_id=c.id, mode_paiement=ModePaiement.CREDIT, total=1000.0))
        session.add(Remboursement(client_id=c.id, montant=1500.0, date=datetime.datetime.now()))
        session.commit()
        assert c.solde_du() == -500.0


class TestUtilisateurPin:
    def test_set_and_verify_pin_correct(self):
        u = Utilisateur(nom="Patron")
        u.set_pin("1234")
        assert u.verify_pin("1234") is True

    def test_verify_pin_wrong(self):
        u = Utilisateur(nom="Patron")
        u.set_pin("1234")
        assert u.verify_pin("9999") is False

    def test_verify_pin_empty(self):
        u = Utilisateur(nom="Patron")
        u.set_pin("1234")
        assert u.verify_pin("") is False

    def test_verify_pin_short(self):
        u = Utilisateur(nom="Patron")
        u.set_pin("123456")
        assert u.verify_pin("123") is False

    def test_pin_hash_is_salted_not_plaintext(self):
        u = Utilisateur(nom="Patron")
        u.set_pin("1234")
        assert u.pin_hash != "1234"
        assert u.pin_salt

    def test_same_pin_different_salts_yield_different_hashes(self):
        u1 = Utilisateur(nom="A")
        u2 = Utilisateur(nom="B")
        u1.set_pin("1234")
        u2.set_pin("1234")
        assert u1.pin_salt != u2.pin_salt
        assert u1.pin_hash != u2.pin_hash

    def test_verify_pin_empty_pin_set(self):
        """Cas limite: PIN vide enregistre (la dialog UI le bloquerait, mais
        le modele lui-meme ne doit pas planter)."""
        u = Utilisateur(nom="X")
        u.set_pin("")
        assert u.verify_pin("") is True
        assert u.verify_pin("0000") is False
