"""Ecran de gestion des produits."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from sqlalchemy import func

from boutiquepro.models import Produit, ProductStock


class ProduitsScreen(QWidget):
    def __init__(self, session_factory, on_change=None, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.on_change = on_change
        self._editing_id: int | None = None

        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["Nom", "Categorie", "Prix achat", "Prix vente", "Marge %", "Stock total"]
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._on_select)
        left.addWidget(self.table)
        layout.addLayout(left, 2)

        right = QVBoxLayout()
        form = QFormLayout()
        self.nom_edit = QLineEdit()
        self.categorie_edit = QLineEdit()
        self.unite_edit = QLineEdit()
        self.unite_edit.setPlaceholderText("piece, kg, litre...")
        self.code_edit = QLineEdit()
        self.prix_achat_spin = QDoubleSpinBox()
        self.prix_achat_spin.setMaximum(100_000_000)
        self.prix_vente_spin = QDoubleSpinBox()
        self.prix_vente_spin.setMaximum(100_000_000)
        self.seuil_spin = QDoubleSpinBox()
        self.seuil_spin.setMaximum(1_000_000)

        form.addRow("Nom *", self.nom_edit)
        form.addRow("Categorie", self.categorie_edit)
        form.addRow("Unite", self.unite_edit)
        form.addRow("Code/Reference", self.code_edit)
        form.addRow("Prix d'achat (FCFA)", self.prix_achat_spin)
        form.addRow("Prix de vente (FCFA)", self.prix_vente_spin)
        form.addRow("Seuil d'alerte stock", self.seuil_spin)
        right.addLayout(form)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Enregistrer")
        self.new_btn = QPushButton("Nouveau produit")
        self.delete_btn = QPushButton("Supprimer")
        self.save_btn.clicked.connect(self._save)
        self.new_btn.clicked.connect(self._reset_form)
        self.delete_btn.clicked.connect(self._delete)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.new_btn)
        btn_row.addWidget(self.delete_btn)
        right.addLayout(btn_row)
        right.addStretch()
        layout.addLayout(right, 1)

        self.refresh()

    def refresh(self):
        self.table.setRowCount(0)
        with self.session_factory() as session:
            produits = session.query(Produit).order_by(Produit.nom).all()
            self.table.setRowCount(len(produits))
            for row, p in enumerate(produits):
                stock_total = (
                    session.query(func.coalesce(func.sum(ProductStock.quantite), 0.0))
                    .filter(ProductStock.produit_id == p.id)
                    .scalar()
                    or 0.0
                )
                self.table.setItem(row, 0, QTableWidgetItem(p.nom))
                self.table.setItem(row, 1, QTableWidgetItem(p.categorie or ""))
                self.table.setItem(row, 2, QTableWidgetItem(f"{p.prix_achat:.0f}"))
                self.table.setItem(row, 3, QTableWidgetItem(f"{p.prix_vente:.0f}"))
                self.table.setItem(row, 4, QTableWidgetItem(f"{p.taux_marge:.1f}%"))
                stock_item = QTableWidgetItem(f"{stock_total:g}")
                if stock_total <= p.seuil_alerte:
                    stock_item.setBackground(_alert_color())
                self.table.setItem(row, 5, stock_item)
                self.table.item(row, 0).setData(256, p.id)

    def _on_select(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        produit_id = self.table.item(row, 0).data(256)
        with self.session_factory() as session:
            p = session.get(Produit, produit_id)
            if p:
                self._editing_id = p.id
                self.nom_edit.setText(p.nom)
                self.categorie_edit.setText(p.categorie or "")
                self.unite_edit.setText(p.unite or "")
                self.code_edit.setText(p.code_reference or "")
                self.prix_achat_spin.setValue(p.prix_achat or 0)
                self.prix_vente_spin.setValue(p.prix_vente or 0)
                self.seuil_spin.setValue(p.seuil_alerte or 0)

    def _reset_form(self):
        self._editing_id = None
        self.nom_edit.clear()
        self.categorie_edit.clear()
        self.unite_edit.clear()
        self.code_edit.clear()
        self.prix_achat_spin.setValue(0)
        self.prix_vente_spin.setValue(0)
        self.seuil_spin.setValue(0)
        self.table.clearSelection()

    def _save(self):
        nom = self.nom_edit.text().strip()
        if not nom:
            QMessageBox.warning(self, "Erreur", "Le nom du produit est obligatoire.")
            return
        with self.session_factory() as session:
            if self._editing_id:
                p = session.get(Produit, self._editing_id)
            else:
                p = Produit()
                session.add(p)
            p.nom = nom
            p.categorie = self.categorie_edit.text().strip()
            p.unite = self.unite_edit.text().strip() or "piece"
            p.code_reference = self.code_edit.text().strip()
            p.prix_achat = self.prix_achat_spin.value()
            p.prix_vente = self.prix_vente_spin.value()
            p.seuil_alerte = self.seuil_spin.value()
            session.commit()
        self._reset_form()
        self.refresh()
        if self.on_change:
            self.on_change()

    def _delete(self):
        if not self._editing_id:
            return
        confirm = QMessageBox.question(
            self, "Confirmer", "Supprimer ce produit et toutes ses donnees liees ?"
        )
        if confirm != QMessageBox.Yes:
            return
        with self.session_factory() as session:
            p = session.get(Produit, self._editing_id)
            if p:
                session.delete(p)
                session.commit()
        self._reset_form()
        self.refresh()
        if self.on_change:
            self.on_change()


def _alert_color():
    from PySide6.QtGui import QColor

    return QColor(255, 205, 205)
