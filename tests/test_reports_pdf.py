"""Tests des rapports PDF: chaque fonction doit s'executer sans erreur et
produire un fichier PDF non trivial (taille > quelques centaines d'octets)."""
from __future__ import annotations

import datetime

from boutiquepro import reports_pdf
from boutiquepro.models import (
    Client,
    LigneVente,
    ModePaiement,
    ProductStock,
    Produit,
    Vente,
)


def _seed(session, boutique):
    p1 = Produit(nom="Riz 5kg", categorie="Alimentation", prix_achat=2000.0, prix_vente=3000.0, seuil_alerte=5)
    p2 = Produit(nom="Huile 1L", categorie="Alimentation", prix_achat=800.0, prix_vente=1200.0, seuil_alerte=10)
    session.add_all([p1, p2])
    session.commit()

    session.add_all(
        [
            ProductStock(produit_id=p1.id, boutique_id=boutique.id, quantite=3),
            ProductStock(produit_id=p2.id, boutique_id=boutique.id, quantite=20),
        ]
    )

    client = Client(nom="Awa")
    session.add(client)
    session.commit()

    v1 = Vente(
        boutique_id=boutique.id,
        client_id=client.id,
        date=datetime.datetime.now(),
        mode_paiement=ModePaiement.COMPTANT,
        total=6000.0,
    )
    session.add(v1)
    session.flush()
    session.add(LigneVente(vente_id=v1.id, produit_id=p1.id, quantite=2, prix_unitaire=3000.0))

    v2 = Vente(
        boutique_id=boutique.id,
        client_id=client.id,
        date=datetime.datetime.now(),
        mode_paiement=ModePaiement.CREDIT,
        total=1200.0,
    )
    session.add(v2)
    session.flush()
    session.add(LigneVente(vente_id=v2.id, produit_id=p2.id, quantite=1, prix_unitaire=1200.0))

    session.commit()
    return p1, p2, client


def test_export_rapport_stock(session, boutique, tmp_path):
    _seed(session, boutique)
    out = tmp_path / "stock.pdf"
    reports_pdf.export_rapport_stock(session, str(out))
    assert out.exists()
    assert out.stat().st_size > 500


def test_export_rapport_stock_boutique_specifique(session, boutique, tmp_path):
    _seed(session, boutique)
    out = tmp_path / "stock_b.pdf"
    reports_pdf.export_rapport_stock(session, str(out), boutique_id=boutique.id)
    assert out.exists()
    assert out.stat().st_size > 500


def test_export_rapport_ventes(session, boutique, tmp_path):
    _seed(session, boutique)
    out = tmp_path / "ventes.pdf"
    date_debut = datetime.datetime.now() - datetime.timedelta(days=30)
    date_fin = datetime.datetime.now() + datetime.timedelta(days=1)
    reports_pdf.export_rapport_ventes(session, str(out), date_debut, date_fin)
    assert out.exists()
    assert out.stat().st_size > 500


def test_export_rapport_rentabilite(session, boutique, tmp_path):
    _seed(session, boutique)
    out = tmp_path / "rentabilite.pdf"
    date_debut = datetime.datetime.now() - datetime.timedelta(days=30)
    date_fin = datetime.datetime.now() + datetime.timedelta(days=1)
    reports_pdf.export_rapport_rentabilite(session, str(out), date_debut, date_fin)
    assert out.exists()
    assert out.stat().st_size > 500


def test_export_rapport_stock_vide(session, boutique, tmp_path):
    """Aucune donnee: ne doit pas planter (tableau avec juste l'en-tete)."""
    out = tmp_path / "stock_vide.pdf"
    reports_pdf.export_rapport_stock(session, str(out))
    assert out.exists()


def test_export_rapport_ventes_periode_vide(session, boutique, tmp_path):
    _seed(session, boutique)
    out = tmp_path / "ventes_vide.pdf"
    date_debut = datetime.datetime(2000, 1, 1)
    date_fin = datetime.datetime(2000, 1, 31)
    reports_pdf.export_rapport_ventes(session, str(out), date_debut, date_fin)
    assert out.exists()
