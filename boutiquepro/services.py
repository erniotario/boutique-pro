"""Logique metier "pure" (sans Qt) pour les ventes et les mouvements de stock.

Ces fonctions prennent une session SQLAlchemy deja ouverte et font le travail
de validation + ecriture en base. Elles sont appelees par les ecrans Qt
(boutiquepro/ui/ventes.py, boutiquepro/ui/stock.py) mais sont testables de
facon independante (voir tests/).

Toutes les erreurs de validation sont signalees par `ValueError` avec un
message en francais, destine a etre affiche directement a l'utilisateur dans
une QMessageBox.
"""
from __future__ import annotations

import datetime

from sqlalchemy.orm import Session

from boutiquepro.models import (
    LigneVente,
    ModePaiement,
    MouvementStock,
    ProductStock,
    Produit,
    TypeMouvement,
    Vente,
)


def pin_is_valid(pin: str) -> bool:
    """Le PIN doit etre purement numerique et contenir entre 4 et 6 chiffres
    (cahier des charges 3.8)."""
    return pin.isdigit() and 4 <= len(pin) <= 6


def get_or_create_stock(session: Session, produit_id: int, boutique_id: int) -> ProductStock:
    """Retourne le ProductStock (produit, boutique), le cree a zero si absent."""
    stock = (
        session.query(ProductStock)
        .filter_by(produit_id=produit_id, boutique_id=boutique_id)
        .first()
    )
    if stock is None:
        stock = ProductStock(produit_id=produit_id, boutique_id=boutique_id, quantite=0.0)
        session.add(stock)
    return stock


def get_stock_quantite(session: Session, produit_id: int, boutique_id: int) -> float:
    stock = (
        session.query(ProductStock)
        .filter_by(produit_id=produit_id, boutique_id=boutique_id)
        .first()
    )
    return stock.quantite if stock else 0.0


def valider_vente(
    session: Session,
    boutique_id: int | None,
    lignes: list[dict],
    mode_paiement: ModePaiement,
    client_id: int | None,
) -> Vente:
    """Valide et enregistre une vente (et decremente le stock).

    `lignes` est une liste de dicts {produit_id, nom, quantite, prix_unitaire}.

    Leve ValueError (message francais) si la validation echoue :
    - boutique manquante
    - panier vide
    - vente a credit sans client
    - quantite invalide (<= 0)
    - stock insuffisant pour une ligne

    Ne fait aucune ecriture en base si une validation echoue (toutes les
    verifications sont faites avant le premier `session.add`).
    """
    if boutique_id is None:
        raise ValueError("Selectionnez une boutique specifique pour faire une vente.")
    if not lignes:
        raise ValueError("Le panier est vide.")
    if mode_paiement == ModePaiement.CREDIT and not client_id:
        raise ValueError("Un client est obligatoire pour une vente a credit.")

    for ligne in lignes:
        if ligne.get("quantite", 0) <= 0:
            raise ValueError(f"Quantite invalide pour {ligne.get('nom', '?')}.")

    # Verification du stock disponible (avant toute ecriture).
    for ligne in lignes:
        dispo = get_stock_quantite(session, ligne["produit_id"], boutique_id)
        if dispo < ligne["quantite"]:
            raise ValueError(
                f"Stock insuffisant pour {ligne['nom']} (disponible: {dispo:g})."
            )

    total = sum(l["quantite"] * l["prix_unitaire"] for l in lignes)
    vente = Vente(
        boutique_id=boutique_id,
        client_id=client_id,
        date=datetime.datetime.now(),
        mode_paiement=mode_paiement,
        total=total,
    )
    session.add(vente)
    session.flush()

    for ligne in lignes:
        lv = LigneVente(
            vente_id=vente.id,
            produit_id=ligne["produit_id"],
            quantite=ligne["quantite"],
            prix_unitaire=ligne["prix_unitaire"],
        )
        session.add(lv)
        stock = get_or_create_stock(session, ligne["produit_id"], boutique_id)
        stock.quantite -= ligne["quantite"]

    session.commit()
    return vente


def valider_mouvement_stock(
    session: Session,
    type_mouvement: TypeMouvement,
    produit_id: int | None,
    boutique_id: int | None,
    quantite: float,
    prix_achat: float = 0.0,
    boutique_destination_id: int | None = None,
    fournisseur: str = "",
    notes: str = "",
) -> MouvementStock:
    """Valide et enregistre un mouvement de stock (entree/sortie/perte/transfert).

    Leve ValueError (message francais) si :
    - produit ou boutique manquant
    - quantite <= 0
    - transfert sans boutique destination, ou destination == source
    - stock insuffisant a la source pour sortie/perte/transfert
    """
    if not produit_id or not boutique_id:
        raise ValueError("Produit et boutique sont obligatoires.")
    if quantite <= 0:
        raise ValueError("La quantite doit etre superieure a zero.")

    if type_mouvement == TypeMouvement.TRANSFERT:
        if not boutique_destination_id:
            raise ValueError("Une boutique destination est obligatoire pour un transfert.")
        if boutique_destination_id == boutique_id:
            raise ValueError("La boutique destination doit etre differente de la boutique source.")

    if type_mouvement in (TypeMouvement.SORTIE, TypeMouvement.PERTE, TypeMouvement.TRANSFERT):
        dispo = get_stock_quantite(session, produit_id, boutique_id)
        if dispo < quantite:
            raise ValueError(
                f"Stock insuffisant dans la boutique source (disponible: {dispo:g})."
            )

    mvt = MouvementStock(
        type=type_mouvement,
        produit_id=produit_id,
        boutique_id=boutique_id,
        boutique_destination_id=boutique_destination_id
        if type_mouvement == TypeMouvement.TRANSFERT
        else None,
        quantite=quantite,
        prix_achat=prix_achat,
        fournisseur=fournisseur,
        notes=notes,
        date=datetime.datetime.now(),
    )
    session.add(mvt)

    stock = get_or_create_stock(session, produit_id, boutique_id)

    if type_mouvement == TypeMouvement.ENTREE:
        stock.quantite += quantite
        if prix_achat:
            produit = session.get(Produit, produit_id)
            if produit:
                produit.prix_achat = prix_achat
    elif type_mouvement in (TypeMouvement.SORTIE, TypeMouvement.PERTE):
        stock.quantite -= quantite
    elif type_mouvement == TypeMouvement.TRANSFERT:
        stock.quantite -= quantite
        dest_stock = get_or_create_stock(session, produit_id, boutique_destination_id)
        dest_stock.quantite += quantite

    session.commit()
    return mvt
