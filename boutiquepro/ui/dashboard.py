"""Ecran tableau de bord."""
from __future__ import annotations

import datetime

from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from sqlalchemy import func

from boutiquepro.models import (
    Client,
    LigneVente,
    ModePaiement,
    ProductStock,
    Produit,
    Remboursement,
    Vente,
)


class DashboardScreen(QWidget):
    def __init__(self, session_factory, get_active_boutique_id, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.get_active_boutique_id = get_active_boutique_id

        layout = QVBoxLayout(self)

        # CA group
        ca_group = QGroupBox("Chiffre d'affaires")
        ca_layout = QGridLayout(ca_group)
        self.ca_jour_label = QLabel("0 FCFA")
        self.ca_semaine_label = QLabel("0 FCFA")
        self.ca_mois_label = QLabel("0 FCFA")
        for label in (self.ca_jour_label, self.ca_semaine_label, self.ca_mois_label):
            label.setStyleSheet("font-weight: bold; font-size: 14px;")
        ca_layout.addWidget(QLabel("Aujourd'hui:"), 0, 0)
        ca_layout.addWidget(self.ca_jour_label, 0, 1)
        ca_layout.addWidget(QLabel("Cette semaine:"), 1, 0)
        ca_layout.addWidget(self.ca_semaine_label, 1, 1)
        ca_layout.addWidget(QLabel("Ce mois:"), 2, 0)
        ca_layout.addWidget(self.ca_mois_label, 2, 1)
        layout.addWidget(ca_group)

        # Creances group
        creance_group = QGroupBox("Creances clients (ardoise)")
        creance_layout = QVBoxLayout(creance_group)
        self.creances_label = QLabel("0 FCFA")
        self.creances_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        creance_layout.addWidget(self.creances_label)
        layout.addWidget(creance_group)

        # Top produits
        top_group = QGroupBox("Top produits vendus (30 derniers jours)")
        top_layout = QVBoxLayout(top_group)
        self.top_table = QTableWidget(0, 2)
        self.top_table.setHorizontalHeaderLabels(["Produit", "Quantite vendue"])
        self.top_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        top_layout.addWidget(self.top_table)
        layout.addWidget(top_group)

        # Alertes stock
        alert_group = QGroupBox("Alertes stock bas")
        alert_layout = QVBoxLayout(alert_group)
        self.alert_table = QTableWidget(0, 3)
        self.alert_table.setHorizontalHeaderLabels(["Produit", "Boutique", "Quantite"])
        self.alert_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        alert_layout.addWidget(self.alert_table)
        layout.addWidget(alert_group)

        self.refresh()

    def refresh(self):
        active_id = self.get_active_boutique_id()
        now = datetime.datetime.now()
        debut_jour = datetime.datetime(now.year, now.month, now.day)
        debut_semaine = debut_jour - datetime.timedelta(days=now.weekday())
        debut_mois = datetime.datetime(now.year, now.month, 1)

        with self.session_factory() as session:
            def ca_depuis(date_debut):
                query = session.query(func.coalesce(func.sum(Vente.total), 0.0)).filter(
                    Vente.date >= date_debut
                )
                if active_id is not None:
                    query = query.filter(Vente.boutique_id == active_id)
                return query.scalar() or 0.0

            self.ca_jour_label.setText(f"{ca_depuis(debut_jour):.0f} FCFA")
            self.ca_semaine_label.setText(f"{ca_depuis(debut_semaine):.0f} FCFA")
            self.ca_mois_label.setText(f"{ca_depuis(debut_mois):.0f} FCFA")

            # Creances: sum over clients of solde_du (only relevant to active boutique habituelle if filtered)
            clients_query = session.query(Client)
            if active_id is not None:
                clients_query = clients_query.filter(Client.boutique_habituelle_id == active_id)
            total_creances = sum(c.solde_du() for c in clients_query.all())
            self.creances_label.setText(f"{total_creances:.0f} FCFA")

            # Top produits (30 days)
            depuis_30j = now - datetime.timedelta(days=30)
            top_query = (
                session.query(
                    Produit.nom, func.sum(LigneVente.quantite).label("total_qte")
                )
                .join(LigneVente, LigneVente.produit_id == Produit.id)
                .join(Vente, Vente.id == LigneVente.vente_id)
                .filter(Vente.date >= depuis_30j)
            )
            if active_id is not None:
                top_query = top_query.filter(Vente.boutique_id == active_id)
            top_query = top_query.group_by(Produit.id).order_by(func.sum(LigneVente.quantite).desc()).limit(10)
            top_rows = top_query.all()
            self.top_table.setRowCount(len(top_rows))
            for row, (nom, qte) in enumerate(top_rows):
                self.top_table.setItem(row, 0, QTableWidgetItem(nom))
                self.top_table.setItem(row, 1, QTableWidgetItem(f"{qte:g}"))

            # Alertes stock bas
            stock_query = session.query(ProductStock).join(Produit, Produit.id == ProductStock.produit_id)
            if active_id is not None:
                stock_query = stock_query.filter(ProductStock.boutique_id == active_id)
            stocks = stock_query.all()
            alert_rows = []
            for s in stocks:
                produit = session.get(Produit, s.produit_id)
                if produit and s.quantite <= produit.seuil_alerte:
                    from boutiquepro.models import Boutique

                    boutique = session.get(Boutique, s.boutique_id)
                    alert_rows.append((produit.nom, boutique.nom if boutique else "?", s.quantite))
            self.alert_table.setRowCount(len(alert_rows))
            for row, (nom, boutique_nom, qte) in enumerate(alert_rows):
                self.alert_table.setItem(row, 0, QTableWidgetItem(nom))
                self.alert_table.setItem(row, 1, QTableWidgetItem(boutique_nom))
                self.alert_table.setItem(row, 2, QTableWidgetItem(f"{qte:g}"))
