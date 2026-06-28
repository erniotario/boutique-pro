"""Ecran de gestion des boutiques."""
from __future__ import annotations

from PySide6.QtWidgets import (
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

from boutiquepro.models import Boutique


class BoutiquesScreen(QWidget):
    def __init__(self, session_factory, on_change=None, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.on_change = on_change
        self._editing_id: int | None = None

        layout = QHBoxLayout(self)

        # Table
        left = QVBoxLayout()
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Nom", "Adresse", "Responsable", "Telephone"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._on_select)
        left.addWidget(self.table)
        layout.addLayout(left, 2)

        # Form
        right = QVBoxLayout()
        form = QFormLayout()
        self.nom_edit = QLineEdit()
        self.adresse_edit = QLineEdit()
        self.responsable_edit = QLineEdit()
        self.telephone_edit = QLineEdit()
        form.addRow("Nom *", self.nom_edit)
        form.addRow("Adresse", self.adresse_edit)
        form.addRow("Responsable", self.responsable_edit)
        form.addRow("Telephone", self.telephone_edit)
        right.addLayout(form)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Enregistrer")
        self.new_btn = QPushButton("Nouvelle boutique")
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
            boutiques = session.query(Boutique).order_by(Boutique.nom).all()
            self.table.setRowCount(len(boutiques))
            for row, b in enumerate(boutiques):
                self.table.setItem(row, 0, QTableWidgetItem(b.nom))
                self.table.setItem(row, 1, QTableWidgetItem(b.adresse or ""))
                self.table.setItem(row, 2, QTableWidgetItem(b.responsable or ""))
                self.table.setItem(row, 3, QTableWidgetItem(b.telephone or ""))
                self.table.item(row, 0).setData(256, b.id)

    def _on_select(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        boutique_id = self.table.item(row, 0).data(256)
        with self.session_factory() as session:
            b = session.get(Boutique, boutique_id)
            if b:
                self._editing_id = b.id
                self.nom_edit.setText(b.nom)
                self.adresse_edit.setText(b.adresse or "")
                self.responsable_edit.setText(b.responsable or "")
                self.telephone_edit.setText(b.telephone or "")

    def _reset_form(self):
        self._editing_id = None
        self.nom_edit.clear()
        self.adresse_edit.clear()
        self.responsable_edit.clear()
        self.telephone_edit.clear()
        self.table.clearSelection()

    def _save(self):
        nom = self.nom_edit.text().strip()
        if not nom:
            QMessageBox.warning(self, "Erreur", "Le nom de la boutique est obligatoire.")
            return
        with self.session_factory() as session:
            if self._editing_id:
                b = session.get(Boutique, self._editing_id)
            else:
                b = Boutique()
                session.add(b)
            b.nom = nom
            b.adresse = self.adresse_edit.text().strip()
            b.responsable = self.responsable_edit.text().strip()
            b.telephone = self.telephone_edit.text().strip()
            session.commit()
        self._reset_form()
        self.refresh()
        if self.on_change:
            self.on_change()

    def _delete(self):
        if not self._editing_id:
            return
        confirm = QMessageBox.question(
            self, "Confirmer", "Supprimer cette boutique et toutes ses donnees liees ?"
        )
        if confirm != QMessageBox.Yes:
            return
        with self.session_factory() as session:
            b = session.get(Boutique, self._editing_id)
            if b:
                session.delete(b)
                session.commit()
        self._reset_form()
        self.refresh()
        if self.on_change:
            self.on_change()
