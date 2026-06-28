"""Generation des rapports PDF (ReportLab) pour BoutiquePro."""
from __future__ import annotations

import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet
from sqlalchemy import func

from boutiquepro.models import (
    Boutique,
    LigneVente,
    ProductStock,
    Produit,
    Vente,
)

TABLE_HEADER_STYLE = TableStyle(
    [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c3e50")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f2f2f2")]),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
)


def _document(path: str, title: str):
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    elements = [
        Paragraph(title, styles["Title"]),
        Paragraph(
            f"Genere le {datetime.datetime.now():%d/%m/%Y a %H:%M}",
            styles["Normal"],
        ),
        Spacer(1, 0.5 * cm),
    ]
    return doc, styles, elements


def export_rapport_stock(session, path: str, boutique_id: int | None = None) -> None:
    """Rapport de stock, pour une boutique donnee ou consolide (toutes boutiques)."""
    query = (
        session.query(ProductStock)
        .join(Produit, Produit.id == ProductStock.produit_id)
        .join(Boutique, Boutique.id == ProductStock.boutique_id)
    )
    if boutique_id is not None:
        query = query.filter(ProductStock.boutique_id == boutique_id)
    stocks = query.all()

    boutique_nom = "Toutes boutiques"
    if boutique_id is not None:
        boutique = session.get(Boutique, boutique_id)
        boutique_nom = boutique.nom if boutique else boutique_nom

    doc, styles, elements = _document(path, f"Rapport de stock - {boutique_nom}")

    data = [["Boutique", "Produit", "Categorie", "Quantite", "Seuil alerte", "Valeur stock (FCFA)"]]
    total_valeur = 0.0
    for s in sorted(stocks, key=lambda s: (s.boutique.nom, s.produit.nom)):
        produit = s.produit
        boutique = s.boutique
        valeur = s.quantite * (produit.prix_achat or 0.0)
        total_valeur += valeur
        alerte = s.quantite <= produit.seuil_alerte
        data.append(
            [
                boutique.nom,
                produit.nom + (" *" if alerte else ""),
                produit.categorie,
                f"{s.quantite:g}",
                f"{produit.seuil_alerte:g}",
                f"{valeur:.0f}",
            ]
        )

    table = Table(data, repeatRows=1)
    table.setStyle(TABLE_HEADER_STYLE)
    elements.append(table)
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph(f"<b>Valeur totale du stock : {total_valeur:.0f} FCFA</b>", styles["Normal"]))
    elements.append(
        Paragraph("* Produit sous le seuil d'alerte stock bas.", styles["Italic"])
    )
    doc.build(elements)


def export_rapport_ventes(
    session,
    path: str,
    date_debut: datetime.datetime,
    date_fin: datetime.datetime,
    boutique_id: int | None = None,
) -> None:
    """Rapport de ventes sur une periode, pour une boutique ou consolide."""
    query = session.query(Vente).filter(Vente.date >= date_debut, Vente.date <= date_fin)
    if boutique_id is not None:
        query = query.filter(Vente.boutique_id == boutique_id)
    ventes = query.order_by(Vente.date).all()

    boutique_nom = "Toutes boutiques"
    if boutique_id is not None:
        boutique = session.get(Boutique, boutique_id)
        boutique_nom = boutique.nom if boutique else boutique_nom

    titre = (
        f"Rapport de ventes - {boutique_nom} "
        f"({date_debut:%d/%m/%Y} - {date_fin:%d/%m/%Y})"
    )
    doc, styles, elements = _document(path, titre)

    data = [["Date", "Boutique", "Client", "Mode paiement", "Total (FCFA)"]]
    total_general = 0.0
    for v in ventes:
        total_general += v.total
        data.append(
            [
                f"{v.date:%d/%m/%Y %H:%M}",
                v.boutique.nom if v.boutique else "",
                v.client.nom if v.client else "Anonyme",
                v.mode_paiement.value,
                f"{v.total:.0f}",
            ]
        )

    table = Table(data, repeatRows=1)
    table.setStyle(TABLE_HEADER_STYLE)
    elements.append(table)
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(
        Paragraph(f"<b>Nombre de ventes : {len(ventes)}</b>", styles["Normal"])
    )
    elements.append(
        Paragraph(f"<b>Chiffre d'affaires total : {total_general:.0f} FCFA</b>", styles["Normal"])
    )
    doc.build(elements)


def export_rapport_rentabilite(
    session,
    path: str,
    date_debut: datetime.datetime,
    date_fin: datetime.datetime,
    boutique_id: int | None = None,
) -> None:
    """Rapport de rentabilite par produit sur une periode."""
    query = (
        session.query(
            Produit.id,
            Produit.nom,
            Produit.categorie,
            Produit.prix_achat,
            func.sum(LigneVente.quantite).label("qte_vendue"),
            func.sum(LigneVente.quantite * LigneVente.prix_unitaire).label("ca"),
        )
        .join(LigneVente, LigneVente.produit_id == Produit.id)
        .join(Vente, Vente.id == LigneVente.vente_id)
        .filter(Vente.date >= date_debut, Vente.date <= date_fin)
    )
    if boutique_id is not None:
        query = query.filter(Vente.boutique_id == boutique_id)
    rows = query.group_by(Produit.id).order_by(func.sum(LigneVente.quantite * LigneVente.prix_unitaire).desc()).all()

    boutique_nom = "Toutes boutiques"
    if boutique_id is not None:
        boutique = session.get(Boutique, boutique_id)
        boutique_nom = boutique.nom if boutique else boutique_nom

    titre = (
        f"Rapport de rentabilite - {boutique_nom} "
        f"({date_debut:%d/%m/%Y} - {date_fin:%d/%m/%Y})"
    )
    doc, styles, elements = _document(path, titre)

    data = [["Produit", "Categorie", "Qte vendue", "Chiffre d'affaires", "Cout matiere", "Marge (FCFA)"]]
    total_ca = 0.0
    total_marge = 0.0
    for _id, nom, categorie, prix_achat, qte_vendue, ca in rows:
        qte_vendue = qte_vendue or 0.0
        ca = ca or 0.0
        cout = qte_vendue * (prix_achat or 0.0)
        marge = ca - cout
        total_ca += ca
        total_marge += marge
        data.append(
            [
                nom,
                categorie,
                f"{qte_vendue:g}",
                f"{ca:.0f}",
                f"{cout:.0f}",
                f"{marge:.0f}",
            ]
        )

    table = Table(data, repeatRows=1)
    table.setStyle(TABLE_HEADER_STYLE)
    elements.append(table)
    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph(f"<b>Chiffre d'affaires total : {total_ca:.0f} FCFA</b>", styles["Normal"]))
    elements.append(Paragraph(f"<b>Marge totale : {total_marge:.0f} FCFA</b>", styles["Normal"]))
    doc.build(elements)
