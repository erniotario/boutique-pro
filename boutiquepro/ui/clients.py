"""Ecran clients / ardoise (credit)."""
from __future__ import annotations

import datetime

from PySide6.QtGui import QColor
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

from boutiquepro.models import Boutique, Client, ModePaiement, Remboursement, Vente

SEUIL_ALERTE_SOLDE = 20000  # FCFA
SEUIL_JOURS = 30


class ClientsScreen(QWidget):
    def __init__(self, session_factory, on_change=None, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.on_change = on_change
        self._editing_id: int | None = None

        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Nom", "Telephone", "Solde du (FCFA)", "Derniere vente credit"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemSelectionChanged.connect(self._on_select)
        left.addWidget(self.table)
        layout.addLayout(left, 2)

        right = QVBoxLayout()
        form = QFormLayout()
        self.nom_edit = QLineEdit()
        self.telephone_edit = QLineEdit()
        form.addRow("Nom *", self.nom_edit)
        form.addRow("Telephone", self.telephone_edit)
        right.addLayout(form)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Enregistrer")
        self.new_btn = QPushButton("Nouveau client")
        self.save_btn.clicked.connect(self._save)
        self.new_btn.clicked.connect(self._reset_form)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.new_btn)
        right.addLayout(btn_row)

        right.addWidget(QLineEdit_separator())

        remb_form = QFormLayout()
        self.remb_montant_spin = QDoubleSpinBox()
        self.remb_montant_spin.setMaximum(100_000_000)
        remb_form.addRow("Montant remboursement (FCFA)", self.remb_montant_spin)
        right.addLayout(remb_form)
        self.remb_btn = QPushButton("Enregistrer un remboursement")
        self.remb_btn.clicked.connect(self._record_remboursement)
        right.addWidget(self.remb_btn)

        right.addStretch()
        layout.addLayout(right, 1)

        self.refresh()

    def refresh(self):
        self.table.setRowCount(0)
        with self.session_factory() as session:
            clients = session.query(Client).order_by(Client.nom).all()
            self.table.setRowCount(len(clients))
            now = datetime.datetime.now()
            for row, c in enumerate(clients):
                solde = c.solde_du()
                self.table.setItem(row, 0, QTableWidgetItem(c.nom))
                self.table.setItem(row, 1, QTableWidgetItem(c.telephone or ""))
                solde_item = QTableWidgetItem(f"{solde:.0f}")

                dernieres_credits = [
                    v.date for v in c.ventes if v.mode_paiement == ModePaiement.CREDIT
                ]
                derniere_date = max(dernieres_credits) if dernieres_credits else None
                jours_ecoules = (now - derniere_date).days if derniere_date else None

                alerte = solde > SEUIL_ALERTE_SOLDE or (
                    jours_ecoules is not None and jours_ecoules > SEUIL_JOURS and solde > 0
                )
                if alerte:
                    solde_item.setBackground(QColor(255, 205, 205))
                self.table.setItem(row, 2, solde_item)

                date_str = derniere_date.strftime("%d/%m/%Y") if derniere_date else "-"
                self.table.setItem(row, 3, QTableWidgetItem(date_str))
                self.table.item(row, 0).setData(256, c.id)

    def _on_select(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        client_id = self.table.item(row, 0).data(256)
        with self.session_factory() as session:
            c = session.get(Client, client_id)
            if c:
                self._editing_id = c.id
                self.nom_edit.setText(c.nom)
                self.telephone_edit.setText(c.telephone or "")

    def _reset_form(self):
        self._editing_id = None
        self.nom_edit.clear()
        self.telephone_edit.clear()
        self.table.clearSelection()

    def _save(self):
        nom = self.nom_edit.text().strip()
        if not nom:
            QMessageBox.warning(self, "Erreur", "Le nom du client est obligatoire.")
            return
        with self.session_factory() as session:
            if self._editing_id:
                c = session.get(Client, self._editing_id)
            else:
                c = Client()
                session.add(c)
            c.nom = nom
            c.telephone = self.telephone_edit.text().strip()
            session.commit()
        self._reset_form()
        self.refresh()
        if self.on_change:
            self.on_change()

    def _record_remboursement(self):
        if not self._editing_id:
            QMessageBox.warning(self, "Erreur", "Selectionnez un client.")
            return
        montant = self.remb_montant_spin.value()
        if montant <= 0:
            QMessageBox.warning(self, "Erreur", "Le montant doit etre superieur a zero.")
            return
        with self.session_factory() as session:
            remb = Remboursement(
                client_id=self._editing_id, montant=montant, date=datetime.datetime.now()
            )
            session.add(remb)
            session.commit()
        self.remb_montant_spin.setValue(0)
        self.refresh()
        if self.on_change:
            self.on_change()


def QLineEdit_separator():
    sep = QLineEdit()
    sep.setReadOnly(True)
    sep.setText("--- Remboursement ---")
    sep.setEnabled(False)
    return sep
