"""Ecran rapports - export Excel du stock actuel.

TODO (hors scope v1): export PDF des ventes/factures via reportlab,
rapports de marge par periode, export consolide multi-boutiques en PDF.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from boutiquepro.models import Boutique, ProductStock, Produit


class RapportsScreen(QWidget):
    def __init__(self, session_factory, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory

        layout = QVBoxLayout(self)
        info = QLabel(
            "Exportez l'etat actuel du stock (toutes boutiques) vers un fichier Excel.\n"
            "Autres rapports (factures PDF, marges par periode) : a venir."
        )
        layout.addWidget(info)

        self.export_btn = QPushButton("Exporter le stock vers Excel (.xlsx)")
        self.export_btn.clicked.connect(self._export_stock_excel)
        layout.addWidget(self.export_btn)
        layout.addStretch()

    def _export_stock_excel(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exporter le stock", "stock_boutiquepro.xlsx", "Fichiers Excel (*.xlsx)"
        )
        if not path:
            return
        if not path.endswith(".xlsx"):
            path += ".xlsx"

        try:
            from openpyxl import Workbook
        except ImportError:
            QMessageBox.critical(self, "Erreur", "Le module openpyxl n'est pas installe.")
            return

        wb = Workbook()
        ws = wb.active
        ws.title = "Stock"
        headers = ["Boutique", "Produit", "Categorie", "Quantite", "Prix achat", "Prix vente", "Seuil alerte"]
        ws.append(headers)

        with self.session_factory() as session:
            stocks = (
                session.query(ProductStock)
                .join(Produit, Produit.id == ProductStock.produit_id)
                .join(Boutique, Boutique.id == ProductStock.boutique_id)
                .all()
            )
            for s in stocks:
                produit = session.get(Produit, s.produit_id)
                boutique = session.get(Boutique, s.boutique_id)
                ws.append(
                    [
                        boutique.nom if boutique else "",
                        produit.nom if produit else "",
                        produit.categorie if produit else "",
                        s.quantite,
                        produit.prix_achat if produit else 0,
                        produit.prix_vente if produit else 0,
                        produit.seuil_alerte if produit else 0,
                    ]
                )

        wb.save(path)
        QMessageBox.information(self, "Export reussi", f"Stock exporte vers:\n{path}")
