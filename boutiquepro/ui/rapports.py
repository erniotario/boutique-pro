"""Ecran rapports: exports PDF (stock, ventes, rentabilite) et Excel (stock)."""
from __future__ import annotations

import datetime

from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import QDate

from boutiquepro.models import Boutique, ProductStock, Produit
from boutiquepro import reports_pdf

TOUTES_BOUTIQUES = "__toutes__"


class RapportsScreen(QWidget):
    def __init__(self, session_factory, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory

        layout = QVBoxLayout(self)

        # Selecteur de boutique commun a tous les rapports
        boutique_row = QHBoxLayout()
        boutique_row.addWidget(QLabel("Boutique :"))
        self.boutique_combo = QComboBox()
        boutique_row.addWidget(self.boutique_combo)
        boutique_row.addStretch()
        layout.addLayout(boutique_row)

        # Rapport de stock
        stock_group = QGroupBox("Rapport de stock")
        stock_layout = QHBoxLayout(stock_group)
        pdf_stock_btn = QPushButton("Exporter en PDF")
        pdf_stock_btn.clicked.connect(self._export_stock_pdf)
        excel_stock_btn = QPushButton("Exporter en Excel (.xlsx)")
        excel_stock_btn.clicked.connect(self._export_stock_excel)
        stock_layout.addWidget(pdf_stock_btn)
        stock_layout.addWidget(excel_stock_btn)
        stock_layout.addStretch()
        layout.addWidget(stock_group)

        # Periode commune ventes/rentabilite
        periode_group = QGroupBox("Periode (ventes et rentabilite)")
        periode_layout = QHBoxLayout(periode_group)
        periode_layout.addWidget(QLabel("Du :"))
        self.date_debut = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_debut.setCalendarPopup(True)
        periode_layout.addWidget(self.date_debut)
        periode_layout.addWidget(QLabel("Au :"))
        self.date_fin = QDateEdit(QDate.currentDate())
        self.date_fin.setCalendarPopup(True)
        periode_layout.addWidget(self.date_fin)
        periode_layout.addStretch()
        layout.addWidget(periode_group)

        # Rapport de ventes
        ventes_group = QGroupBox("Rapport de ventes")
        ventes_layout = QHBoxLayout(ventes_group)
        pdf_ventes_btn = QPushButton("Exporter en PDF")
        pdf_ventes_btn.clicked.connect(self._export_ventes_pdf)
        ventes_layout.addWidget(pdf_ventes_btn)
        ventes_layout.addStretch()
        layout.addWidget(ventes_group)

        # Rapport de rentabilite
        rentabilite_group = QGroupBox("Rapport de rentabilite par produit")
        rentabilite_layout = QHBoxLayout(rentabilite_group)
        pdf_rentabilite_btn = QPushButton("Exporter en PDF")
        pdf_rentabilite_btn.clicked.connect(self._export_rentabilite_pdf)
        rentabilite_layout.addWidget(pdf_rentabilite_btn)
        rentabilite_layout.addStretch()
        layout.addWidget(rentabilite_group)

        layout.addStretch()
        self.refresh()

    def refresh(self):
        current = self.boutique_combo.currentData()
        self.boutique_combo.blockSignals(True)
        self.boutique_combo.clear()
        self.boutique_combo.addItem("Toutes boutiques", TOUTES_BOUTIQUES)
        with self.session_factory() as session:
            for b in session.query(Boutique).order_by(Boutique.nom).all():
                self.boutique_combo.addItem(b.nom, b.id)
        if current is not None:
            idx = self.boutique_combo.findData(current)
            if idx >= 0:
                self.boutique_combo.setCurrentIndex(idx)
        self.boutique_combo.blockSignals(False)

    def _selected_boutique_id(self):
        data = self.boutique_combo.currentData()
        if data == TOUTES_BOUTIQUES or data is None:
            return None
        return data

    def _periode(self):
        debut = self.date_debut.date().toPython()
        fin = self.date_fin.date().toPython()
        date_debut = datetime.datetime.combine(debut, datetime.time.min)
        date_fin = datetime.datetime.combine(fin, datetime.time.max)
        return date_debut, date_fin

    def _save_path(self, default_name: str):
        path, _ = QFileDialog.getSaveFileName(self, "Exporter le rapport", default_name, "Fichiers PDF (*.pdf)")
        if not path:
            return None
        if not path.endswith(".pdf"):
            path += ".pdf"
        return path

    def _export_stock_pdf(self):
        path = self._save_path("rapport_stock.pdf")
        if not path:
            return
        with self.session_factory() as session:
            reports_pdf.export_rapport_stock(session, path, self._selected_boutique_id())
        QMessageBox.information(self, "Export reussi", f"Rapport de stock exporte vers:\n{path}")

    def _export_ventes_pdf(self):
        path = self._save_path("rapport_ventes.pdf")
        if not path:
            return
        date_debut, date_fin = self._periode()
        with self.session_factory() as session:
            reports_pdf.export_rapport_ventes(
                session, path, date_debut, date_fin, self._selected_boutique_id()
            )
        QMessageBox.information(self, "Export reussi", f"Rapport de ventes exporte vers:\n{path}")

    def _export_rentabilite_pdf(self):
        path = self._save_path("rapport_rentabilite.pdf")
        if not path:
            return
        date_debut, date_fin = self._periode()
        with self.session_factory() as session:
            reports_pdf.export_rapport_rentabilite(
                session, path, date_debut, date_fin, self._selected_boutique_id()
            )
        QMessageBox.information(self, "Export reussi", f"Rapport de rentabilite exporte vers:\n{path}")

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

        boutique_id = self._selected_boutique_id()
        with self.session_factory() as session:
            stocks_query = (
                session.query(ProductStock)
                .join(Produit, Produit.id == ProductStock.produit_id)
                .join(Boutique, Boutique.id == ProductStock.boutique_id)
            )
            if boutique_id is not None:
                stocks_query = stocks_query.filter(ProductStock.boutique_id == boutique_id)
            stocks = stocks_query.all()
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
