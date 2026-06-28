"""Modeles SQLAlchemy pour BoutiquePro."""
from __future__ import annotations

import datetime
import enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TypeMouvement(str, enum.Enum):
    ENTREE = "entree"
    SORTIE = "sortie"
    PERTE = "perte"
    TRANSFERT = "transfert"


class ModePaiement(str, enum.Enum):
    COMPTANT = "comptant"
    MOBILE_MONEY = "mobile_money"
    CREDIT = "credit"


class Boutique(Base):
    __tablename__ = "boutiques"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(120), nullable=False)
    adresse: Mapped[str] = mapped_column(String(255), default="")
    responsable: Mapped[str] = mapped_column(String(120), default="")
    telephone: Mapped[str] = mapped_column(String(40), default="")

    stocks: Mapped[list["ProductStock"]] = relationship(
        "ProductStock",
        foreign_keys="ProductStock.boutique_id",
        back_populates="boutique",
        cascade="all, delete-orphan",
    )
    ventes: Mapped[list["Vente"]] = relationship(
        "Vente", back_populates="boutique", cascade="all, delete-orphan"
    )
    clients: Mapped[list["Client"]] = relationship(
        "Client", back_populates="boutique_habituelle"
    )

    def __repr__(self) -> str:
        return f"<Boutique {self.nom}>"


class Produit(Base):
    __tablename__ = "produits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(150), nullable=False)
    categorie: Mapped[str] = mapped_column(String(100), default="")
    unite: Mapped[str] = mapped_column(String(30), default="piece")
    prix_achat: Mapped[float] = mapped_column(Float, default=0.0)
    prix_vente: Mapped[float] = mapped_column(Float, default=0.0)
    seuil_alerte: Mapped[float] = mapped_column(Float, default=0.0)
    code_reference: Mapped[str] = mapped_column(String(60), default="")

    stocks: Mapped[list["ProductStock"]] = relationship(
        "ProductStock", back_populates="produit", cascade="all, delete-orphan"
    )
    mouvements: Mapped[list["MouvementStock"]] = relationship(
        "MouvementStock",
        foreign_keys="MouvementStock.produit_id",
        back_populates="produit",
        cascade="all, delete-orphan",
    )

    @property
    def marge_unitaire(self) -> float:
        """Marge en valeur (prix_vente - prix_achat) par unite."""
        return (self.prix_vente or 0.0) - (self.prix_achat or 0.0)

    @property
    def taux_marge(self) -> float:
        """Taux de marge en pourcentage du prix de vente."""
        if not self.prix_vente:
            return 0.0
        return (self.marge_unitaire / self.prix_vente) * 100.0

    def __repr__(self) -> str:
        return f"<Produit {self.nom}>"


class ProductStock(Base):
    __tablename__ = "product_stocks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    produit_id: Mapped[int] = mapped_column(ForeignKey("produits.id"), nullable=False)
    boutique_id: Mapped[int] = mapped_column(ForeignKey("boutiques.id"), nullable=False)
    quantite: Mapped[float] = mapped_column(Float, default=0.0)

    produit: Mapped["Produit"] = relationship("Produit", back_populates="stocks")
    boutique: Mapped["Boutique"] = relationship(
        "Boutique", foreign_keys=[boutique_id], back_populates="stocks"
    )

    def __repr__(self) -> str:
        return f"<ProductStock produit={self.produit_id} boutique={self.boutique_id} qte={self.quantite}>"


class MouvementStock(Base):
    __tablename__ = "mouvements_stock"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[TypeMouvement] = mapped_column(Enum(TypeMouvement), nullable=False)
    produit_id: Mapped[int] = mapped_column(ForeignKey("produits.id"), nullable=False)
    boutique_id: Mapped[int] = mapped_column(ForeignKey("boutiques.id"), nullable=False)
    boutique_destination_id: Mapped[int | None] = mapped_column(
        ForeignKey("boutiques.id"), nullable=True
    )
    quantite: Mapped[float] = mapped_column(Float, default=0.0)
    prix_achat: Mapped[float] = mapped_column(Float, default=0.0)
    fournisseur: Mapped[str] = mapped_column(String(150), default="")
    date: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )
    notes: Mapped[str] = mapped_column(Text, default="")

    produit: Mapped["Produit"] = relationship(
        "Produit", foreign_keys=[produit_id], back_populates="mouvements"
    )
    boutique: Mapped["Boutique"] = relationship(
        "Boutique", foreign_keys=[boutique_id]
    )
    boutique_destination: Mapped["Boutique | None"] = relationship(
        "Boutique", foreign_keys=[boutique_destination_id]
    )

    def __repr__(self) -> str:
        return f"<MouvementStock {self.type} produit={self.produit_id}>"


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nom: Mapped[str] = mapped_column(String(150), nullable=False)
    telephone: Mapped[str] = mapped_column(String(40), default="")
    boutique_habituelle_id: Mapped[int | None] = mapped_column(
        ForeignKey("boutiques.id"), nullable=True
    )

    boutique_habituelle: Mapped["Boutique | None"] = relationship(
        "Boutique", back_populates="clients"
    )
    ventes: Mapped[list["Vente"]] = relationship("Vente", back_populates="client")
    remboursements: Mapped[list["Remboursement"]] = relationship(
        "Remboursement", back_populates="client", cascade="all, delete-orphan"
    )

    def solde_du(self) -> float:
        """Solde du = total des ventes a credit - total des remboursements."""
        total_credit = sum(
            v.total for v in self.ventes if v.mode_paiement == ModePaiement.CREDIT
        )
        total_remb = sum(r.montant for r in self.remboursements)
        return total_credit - total_remb

    def __repr__(self) -> str:
        return f"<Client {self.nom}>"


class Vente(Base):
    __tablename__ = "ventes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    boutique_id: Mapped[int] = mapped_column(ForeignKey("boutiques.id"), nullable=False)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id"), nullable=True)
    date: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )
    mode_paiement: Mapped[ModePaiement] = mapped_column(
        Enum(ModePaiement), default=ModePaiement.COMPTANT
    )
    total: Mapped[float] = mapped_column(Float, default=0.0)

    boutique: Mapped["Boutique"] = relationship("Boutique", back_populates="ventes")
    client: Mapped["Client | None"] = relationship("Client", back_populates="ventes")
    lignes: Mapped[list["LigneVente"]] = relationship(
        "LigneVente", back_populates="vente", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Vente {self.id} total={self.total}>"


class LigneVente(Base):
    __tablename__ = "lignes_vente"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vente_id: Mapped[int] = mapped_column(ForeignKey("ventes.id"), nullable=False)
    produit_id: Mapped[int] = mapped_column(ForeignKey("produits.id"), nullable=False)
    quantite: Mapped[float] = mapped_column(Float, default=0.0)
    prix_unitaire: Mapped[float] = mapped_column(Float, default=0.0)

    vente: Mapped["Vente"] = relationship("Vente", back_populates="lignes")
    produit: Mapped["Produit"] = relationship("Produit")

    @property
    def sous_total(self) -> float:
        return self.quantite * self.prix_unitaire

    def __repr__(self) -> str:
        return f"<LigneVente produit={self.produit_id} qte={self.quantite}>"


class Remboursement(Base):
    __tablename__ = "remboursements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    date: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.now
    )
    montant: Mapped[float] = mapped_column(Float, default=0.0)

    client: Mapped["Client"] = relationship("Client", back_populates="remboursements")

    def __repr__(self) -> str:
        return f"<Remboursement client={self.client_id} montant={self.montant}>"
