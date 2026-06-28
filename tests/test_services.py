"""Tests de la logique metier extraite dans boutiquepro/services.py :
ventes (creation Vente + LigneVente + decrement stock) et mouvements de
stock (entree/sortie/perte/transfert)."""
from __future__ import annotations

import pytest

from boutiquepro.models import (
    Client,
    ModePaiement,
    ProductStock,
    Produit,
    TypeMouvement,
)
from boutiquepro.services import (
    get_stock_quantite,
    valider_mouvement_stock,
    valider_vente,
)


@pytest.fixture()
def produit(session):
    p = Produit(nom="Riz 5kg", prix_achat=2000.0, prix_vente=3000.0, seuil_alerte=5)
    session.add(p)
    session.commit()
    return p


def _set_stock(session, produit_id, boutique_id, quantite):
    stock = ProductStock(produit_id=produit_id, boutique_id=boutique_id, quantite=quantite)
    session.add(stock)
    session.commit()
    return stock


class TestValiderVente:
    def test_vente_comptant_decremente_stock(self, session, boutique, produit):
        _set_stock(session, produit.id, boutique.id, 10)
        lignes = [{"produit_id": produit.id, "nom": produit.nom, "quantite": 3, "prix_unitaire": 3000.0}]
        vente = valider_vente(session, boutique.id, lignes, ModePaiement.COMPTANT, None)
        assert vente.total == 9000.0
        assert len(vente.lignes) == 1
        assert get_stock_quantite(session, produit.id, boutique.id) == 7

    def test_vente_credit_requires_client(self, session, boutique, produit):
        _set_stock(session, produit.id, boutique.id, 10)
        lignes = [{"produit_id": produit.id, "nom": produit.nom, "quantite": 1, "prix_unitaire": 3000.0}]
        with pytest.raises(ValueError, match="client"):
            valider_vente(session, boutique.id, lignes, ModePaiement.CREDIT, None)
        # No partial write: stock unchanged.
        assert get_stock_quantite(session, produit.id, boutique.id) == 10

    def test_vente_credit_with_client_ok(self, session, boutique, produit):
        _set_stock(session, produit.id, boutique.id, 10)
        client = Client(nom="Awa")
        session.add(client)
        session.commit()
        lignes = [{"produit_id": produit.id, "nom": produit.nom, "quantite": 2, "prix_unitaire": 3000.0}]
        vente = valider_vente(session, boutique.id, lignes, ModePaiement.CREDIT, client.id)
        assert vente.client_id == client.id
        assert client.solde_du() == 6000.0

    def test_vente_sans_boutique(self, session, produit):
        lignes = [{"produit_id": produit.id, "nom": produit.nom, "quantite": 1, "prix_unitaire": 3000.0}]
        with pytest.raises(ValueError, match="boutique"):
            valider_vente(session, None, lignes, ModePaiement.COMPTANT, None)

    def test_vente_panier_vide(self, session, boutique):
        with pytest.raises(ValueError, match="panier"):
            valider_vente(session, boutique.id, [], ModePaiement.COMPTANT, None)

    def test_vente_quantite_invalide(self, session, boutique, produit):
        _set_stock(session, produit.id, boutique.id, 10)
        lignes = [{"produit_id": produit.id, "nom": produit.nom, "quantite": 0, "prix_unitaire": 3000.0}]
        with pytest.raises(ValueError, match="Quantite"):
            valider_vente(session, boutique.id, lignes, ModePaiement.COMPTANT, None)

    def test_vente_quantite_negative(self, session, boutique, produit):
        _set_stock(session, produit.id, boutique.id, 10)
        lignes = [{"produit_id": produit.id, "nom": produit.nom, "quantite": -2, "prix_unitaire": 3000.0}]
        with pytest.raises(ValueError, match="Quantite"):
            valider_vente(session, boutique.id, lignes, ModePaiement.COMPTANT, None)

    def test_vente_stock_insuffisant_bloque(self, session, boutique, produit):
        _set_stock(session, produit.id, boutique.id, 2)
        lignes = [{"produit_id": produit.id, "nom": produit.nom, "quantite": 5, "prix_unitaire": 3000.0}]
        with pytest.raises(ValueError, match="Stock insuffisant"):
            valider_vente(session, boutique.id, lignes, ModePaiement.COMPTANT, None)
        # Le stock ne doit pas etre devenu negatif / ne doit pas avoir change.
        assert get_stock_quantite(session, produit.id, boutique.id) == 2

    def test_vente_stock_inexistant_traite_comme_zero(self, session, boutique, produit):
        # Aucun ProductStock cree pour ce produit/boutique.
        lignes = [{"produit_id": produit.id, "nom": produit.nom, "quantite": 1, "prix_unitaire": 3000.0}]
        with pytest.raises(ValueError, match="Stock insuffisant"):
            valider_vente(session, boutique.id, lignes, ModePaiement.COMPTANT, None)

    def test_vente_plusieurs_lignes_un_produit_insuffisant_bloque_toute_la_vente(
        self, session, boutique, produit
    ):
        p2 = Produit(nom="Sucre 1kg", prix_achat=500.0, prix_vente=800.0)
        session.add(p2)
        session.commit()
        _set_stock(session, produit.id, boutique.id, 10)
        _set_stock(session, p2.id, boutique.id, 1)
        lignes = [
            {"produit_id": produit.id, "nom": produit.nom, "quantite": 2, "prix_unitaire": 3000.0},
            {"produit_id": p2.id, "nom": p2.nom, "quantite": 5, "prix_unitaire": 800.0},
        ]
        with pytest.raises(ValueError, match="Stock insuffisant"):
            valider_vente(session, boutique.id, lignes, ModePaiement.COMPTANT, None)
        # Premiere ligne (stock suffisant) ne doit pas avoir ete appliquee non plus.
        assert get_stock_quantite(session, produit.id, boutique.id) == 10


class TestValiderMouvementStock:
    def test_entree_augmente_stock(self, session, boutique, produit):
        valider_mouvement_stock(
            session, TypeMouvement.ENTREE, produit.id, boutique.id, quantite=10, prix_achat=2200.0
        )
        assert get_stock_quantite(session, produit.id, boutique.id) == 10
        # prix_achat du produit mis a jour
        assert session.get(Produit, produit.id).prix_achat == 2200.0

    def test_sortie_diminue_stock(self, session, boutique, produit):
        _set_stock(session, produit.id, boutique.id, 10)
        valider_mouvement_stock(session, TypeMouvement.SORTIE, produit.id, boutique.id, quantite=4)
        assert get_stock_quantite(session, produit.id, boutique.id) == 6

    def test_perte_diminue_stock(self, session, boutique, produit):
        _set_stock(session, produit.id, boutique.id, 10)
        valider_mouvement_stock(session, TypeMouvement.PERTE, produit.id, boutique.id, quantite=3)
        assert get_stock_quantite(session, produit.id, boutique.id) == 7

    def test_sortie_stock_insuffisant_bloque(self, session, boutique, produit):
        _set_stock(session, produit.id, boutique.id, 2)
        with pytest.raises(ValueError, match="insuffisant"):
            valider_mouvement_stock(session, TypeMouvement.SORTIE, produit.id, boutique.id, quantite=5)
        assert get_stock_quantite(session, produit.id, boutique.id) == 2

    def test_perte_stock_insuffisant_bloque(self, session, boutique, produit):
        _set_stock(session, produit.id, boutique.id, 1)
        with pytest.raises(ValueError, match="insuffisant"):
            valider_mouvement_stock(session, TypeMouvement.PERTE, produit.id, boutique.id, quantite=2)

    def test_transfert_deplace_stock_entre_boutiques(self, session, boutique, boutique2, produit):
        _set_stock(session, produit.id, boutique.id, 10)
        valider_mouvement_stock(
            session,
            TypeMouvement.TRANSFERT,
            produit.id,
            boutique.id,
            quantite=4,
            boutique_destination_id=boutique2.id,
        )
        assert get_stock_quantite(session, produit.id, boutique.id) == 6
        assert get_stock_quantite(session, produit.id, boutique2.id) == 4

    def test_transfert_stock_insuffisant_a_la_source_bloque(self, session, boutique, boutique2, produit):
        _set_stock(session, produit.id, boutique.id, 2)
        with pytest.raises(ValueError, match="insuffisant"):
            valider_mouvement_stock(
                session,
                TypeMouvement.TRANSFERT,
                produit.id,
                boutique.id,
                quantite=5,
                boutique_destination_id=boutique2.id,
            )
        # Rien ne doit avoir change ni a la source ni a la destination.
        assert get_stock_quantite(session, produit.id, boutique.id) == 2
        assert get_stock_quantite(session, produit.id, boutique2.id) == 0

    def test_transfert_sans_destination_bloque(self, session, boutique, produit):
        _set_stock(session, produit.id, boutique.id, 10)
        with pytest.raises(ValueError, match="destination"):
            valider_mouvement_stock(
                session, TypeMouvement.TRANSFERT, produit.id, boutique.id, quantite=2,
                boutique_destination_id=None,
            )

    def test_transfert_destination_identique_source_bloque(self, session, boutique, produit):
        _set_stock(session, produit.id, boutique.id, 10)
        with pytest.raises(ValueError, match="differente"):
            valider_mouvement_stock(
                session, TypeMouvement.TRANSFERT, produit.id, boutique.id, quantite=2,
                boutique_destination_id=boutique.id,
            )

    def test_quantite_zero_bloque(self, session, boutique, produit):
        with pytest.raises(ValueError, match="superieure a zero"):
            valider_mouvement_stock(session, TypeMouvement.ENTREE, produit.id, boutique.id, quantite=0)

    def test_quantite_negative_bloque(self, session, boutique, produit):
        with pytest.raises(ValueError, match="superieure a zero"):
            valider_mouvement_stock(session, TypeMouvement.ENTREE, produit.id, boutique.id, quantite=-5)

    def test_produit_manquant_bloque(self, session, boutique):
        with pytest.raises(ValueError, match="obligatoires"):
            valider_mouvement_stock(session, TypeMouvement.ENTREE, None, boutique.id, quantite=5)

    def test_boutique_manquante_bloque(self, session, produit):
        with pytest.raises(ValueError, match="obligatoires"):
            valider_mouvement_stock(session, TypeMouvement.ENTREE, produit.id, None, quantite=5)

    def test_entree_cree_stock_si_absent(self, session, boutique, produit):
        assert get_stock_quantite(session, produit.id, boutique.id) == 0
        valider_mouvement_stock(session, TypeMouvement.ENTREE, produit.id, boutique.id, quantite=5)
        assert get_stock_quantite(session, produit.id, boutique.id) == 5
