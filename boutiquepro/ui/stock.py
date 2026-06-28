"""Ecran de gestion du stock par boutique, avec mouvements."""
from __future__ import annotations

import datetime

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from boutiquepro.models import (
    Boutique,
    MouvementStock,
    ProductStock,
    Produit,
    TypeMouvement,
)


class MouvementDialog(QDialog):
    def __init__(self, session_factory, boutique_id: int | None, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.setWindowTitle("Nouveau mouvement de stock")
        self.resize(420, 320)

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.type_combo = QComboBox()
        self.type_combo.addItem("Entree", TypeMouvement.ENTREE)
        self.type_combo.addItem("Sortie", TypeMouvement.SORTIE)
        self.type_combo.addItem("Perte", TypeMouvement.PERTE)
        self.type_combo.addItem("Transfert", TypeMouvement.TRANSFERT)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)

        self.produit_combo = QComboBox()
        self.boutique_combo = QComboBox()
        self.boutique_dest_combo = QComboBox()
        self.quantite_spin = QDoubleSpinBox()
        self.quantite_spin.setMaximum(1_000_000)
        self.prix_achat_spin = QDoubleSpinBox()
        self.prix_achat_spin.setMaximum(100_000_000)
        self.fournisseur_edit = QLineEdit()
        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(60)

        with self.session_factory() as session:
            for p in session.query(Produit).order_by(Produit.nom).all():
                self.produit_combo.addItem(p.nom, p.id)
            for b in session.query(Boutique).order_by(Boutique.nom).all():
                self.boutique_combo.addItem(b.nom, b.id)
                self.boutique_dest_combo.addItem(b.nom, b.id)

        if boutique_id:
            idx = self.boutique_combo.findData(boutique_id)
            if idx >= 0:
                self.boutique_combo.setCurrentIndex(idx)

        form.addRow("Type de mouvement", self.type_combo)
        form.addRow("Produit", self.produit_combo)
        form.addRow("Boutique", self.boutique_combo)
        self.dest_row_label = "Boutique destination"
        form.addRow(self.dest_row_label, self.boutique_dest_combo)
        form.addRow("Quantite", self.quantite_spin)
        form.addRow("Prix d'achat (si entree)", self.prix_achat_spin)
        form.addRow("Fournisseur", self.fournisseur_edit)
        form.addRow("Notes", self.notes_edit)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._on_type_changed()

    def _on_type_changed(self):
        is_transfert = self.type_combo.currentData() == TypeMouvement.TRANSFERT
        self.boutique_dest_combo.setEnabled(is_transfert)

    def get_values(self):
        return {
            "type": self.type_combo.currentData(),
            "produit_id": self.produit_combo.currentData(),
            "boutique_id": self.boutique_combo.currentData(),
            "boutique_destination_id": self.boutique_dest_combo.currentData()
            if self.type_combo.currentData() == TypeMouvement.TRANSFERT
            else None,
            "quantite": self.quantite_spin.value(),
            "prix_achat": self.prix_achat_spin.value(),
            "fournisseur": self.fournisseur_edit.text().strip(),
            "notes": self.notes_edit.toPlainText().strip(),
        }


class StockScreen(QWidget):
    def __init__(self, session_factory, get_active_boutique_id, on_change=None, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.get_active_boutique_id = get_active_boutique_id
        self.on_change = on_change

        layout = QVBoxLayout(self)

        btn_row = QHBoxLayout()
        self.new_mvt_btn = QPushButton("Nouveau mouvement (entree/sortie/perte/transfert)")
        self.new_mvt_btn.clicked.connect(self._open_mouvement_dialog)
        btn_row.addWidget(self.new_mvt_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Produit", "Boutique", "Quantite", "Alerte"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.refresh()

    def _open_mouvement_dialog(self):
        dialog = MouvementDialog(self.session_factory, self.get_active_boutique_id(), self)
        if dialog.exec() != QDialog.Accepted:
            return
        values = dialog.get_values()
        if not values["produit_id"] or not values["boutique_id"]:
            QMessageBox.warning(self, "Erreur", "Produit et boutique sont obligatoires.")
            return
        if values["quantite"] <= 0:
            QMessageBox.warning(self, "Erreur", "La quantite doit etre superieure a zero.")
            return

        with self.session_factory() as session:
            mvt = MouvementStock(
                type=values["type"],
                produit_id=values["produit_id"],
                boutique_id=values["boutique_id"],
                boutique_destination_id=values["boutique_destination_id"],
                quantite=values["quantite"],
                prix_achat=values["prix_achat"],
                fournisseur=values["fournisseur"],
                notes=values["notes"],
                date=datetime.datetime.now(),
            )
            session.add(mvt)

            def get_or_create_stock(produit_id, boutique_id):
                stock = (
                    session.query(ProductStock)
                    .filter_by(produit_id=produit_id, boutique_id=boutique_id)
                    .first()
                )
                if stock is None:
                    stock = ProductStock(produit_id=produit_id, boutique_id=boutique_id, quantite=0.0)
                    session.add(stock)
                return stock

            stock = get_or_create_stock(values["produit_id"], values["boutique_id"])

            if values["type"] == TypeMouvement.ENTREE:
                stock.quantite += values["quantite"]
                if values["prix_achat"]:
                    produit = session.get(Produit, values["produit_id"])
                    if produit:
                        produit.prix_achat = values["prix_achat"]
            elif values["type"] in (TypeMouvement.SORTIE, TypeMouvement.PERTE):
                stock.quantite -= values["quantite"]
            elif values["type"] == TypeMouvement.TRANSFERT:
                stock.quantite -= values["quantite"]
                dest_stock = get_or_create_stock(
                    values["produit_id"], values["boutique_destination_id"]
                )
                dest_stock.quantite += values["quantite"]

            session.commit()

        self.refresh()
        if self.on_change:
            self.on_change()

    def refresh(self):
        self.table.setRowCount(0)
        active_id = self.get_active_boutique_id()
        with self.session_factory() as session:
            query = session.query(ProductStock)
            if active_id is not None:
                query = query.filter(ProductStock.boutique_id == active_id)
            stocks = query.all()
            self.table.setRowCount(len(stocks))
            for row, s in enumerate(stocks):
                produit = session.get(Produit, s.produit_id)
                boutique = session.get(Boutique, s.boutique_id)
                self.table.setItem(row, 0, QTableWidgetItem(produit.nom if produit else "?"))
                self.table.setItem(row, 1, QTableWidgetItem(boutique.nom if boutique else "?"))
                self.table.setItem(row, 2, QTableWidgetItem(f"{s.quantite:g}"))
                alerte = ""
                if produit and s.quantite <= produit.seuil_alerte:
                    alerte = "Stock bas"
                item_alerte = QTableWidgetItem(alerte)
                if alerte:
                    from PySide6.QtGui import QColor

                    item_alerte.setBackground(QColor(255, 205, 205))
                self.table.setItem(row, 3, item_alerte)
