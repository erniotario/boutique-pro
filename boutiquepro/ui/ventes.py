"""Ecran de vente (mode caisse)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from boutiquepro.models import (
    Client,
    ModePaiement,
    ProductStock,
    Produit,
)
from boutiquepro.services import valider_vente


class VentesScreen(QWidget):
    def __init__(self, session_factory, get_active_boutique_id, on_change=None, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.get_active_boutique_id = get_active_boutique_id
        self.on_change = on_change
        self.lignes: list[dict] = []  # {produit_id, nom, quantite, prix_unitaire}

        layout = QVBoxLayout(self)

        # Search row
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Rechercher un produit par nom ou code...")
        self.search_edit.textChanged.connect(self._filter_products)
        search_row.addWidget(self.search_edit)
        layout.addLayout(search_row)

        body = QHBoxLayout()

        # Product list
        self.product_table = QTableWidget(0, 3)
        self.product_table.setHorizontalHeaderLabels(["Produit", "Prix vente", "Stock dispo"])
        self.product_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.product_table.doubleClicked.connect(self._add_selected_product)
        body.addWidget(self.product_table, 2)

        # Cart
        cart_layout = QVBoxLayout()
        self.cart_table = QTableWidget(0, 4)
        self.cart_table.setHorizontalHeaderLabels(["Produit", "Qte", "Prix unit.", "Sous-total"])
        self.cart_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        cart_layout.addWidget(self.cart_table)

        qty_row = QHBoxLayout()
        qty_row.addWidget(QLabel("Quantite a ajouter:"))
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setMinimum(0.01)
        self.qty_spin.setValue(1)
        self.qty_spin.setMaximum(1_000_000)
        qty_row.addWidget(self.qty_spin)
        self.add_btn = QPushButton("Ajouter au panier")
        self.add_btn.clicked.connect(self._add_selected_product)
        qty_row.addWidget(self.add_btn)
        self.remove_btn = QPushButton("Retirer la ligne")
        self.remove_btn.clicked.connect(self._remove_selected_line)
        qty_row.addWidget(self.remove_btn)
        cart_layout.addLayout(qty_row)

        total_row = QHBoxLayout()
        self.total_label = QLabel("Total: 0 FCFA")
        self.total_label.setStyleSheet("font-weight: bold; font-size: 16px;")
        total_row.addWidget(self.total_label)
        cart_layout.addLayout(total_row)

        payment_row = QHBoxLayout()
        payment_row.addWidget(QLabel("Mode de paiement:"))
        self.payment_combo = QComboBox()
        self.payment_combo.addItem("Comptant", ModePaiement.COMPTANT)
        self.payment_combo.addItem("Mobile Money", ModePaiement.MOBILE_MONEY)
        self.payment_combo.addItem("Credit", ModePaiement.CREDIT)
        self.payment_combo.currentIndexChanged.connect(self._on_payment_changed)
        payment_row.addWidget(self.payment_combo)
        cart_layout.addLayout(payment_row)

        client_row = QHBoxLayout()
        client_row.addWidget(QLabel("Client (requis si credit):"))
        self.client_combo = QComboBox()
        client_row.addWidget(self.client_combo)
        cart_layout.addLayout(client_row)

        self.validate_btn = QPushButton("Valider la vente")
        self.validate_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        self.validate_btn.clicked.connect(self._validate_sale)
        cart_layout.addWidget(self.validate_btn)

        body.addLayout(cart_layout, 2)
        layout.addLayout(body)

        self._on_payment_changed()
        self.refresh()

    def _on_payment_changed(self):
        is_credit = self.payment_combo.currentData() == ModePaiement.CREDIT
        self.client_combo.setEnabled(True)

    def refresh(self):
        self._load_products()
        self._load_clients()
        self._refresh_cart()

    def _load_products(self):
        active_id = self.get_active_boutique_id()
        self.product_table.setRowCount(0)
        with self.session_factory() as session:
            produits = session.query(Produit).order_by(Produit.nom).all()
            rows = []
            for p in produits:
                stock_qte = 0.0
                if active_id is not None:
                    stock = (
                        session.query(ProductStock)
                        .filter_by(produit_id=p.id, boutique_id=active_id)
                        .first()
                    )
                    stock_qte = stock.quantite if stock else 0.0
                rows.append((p.id, p.nom, p.prix_vente, stock_qte))
            self._all_products = rows
            self._render_products(rows)

    def _render_products(self, rows):
        self.product_table.setRowCount(len(rows))
        for row, (pid, nom, prix, stock_qte) in enumerate(rows):
            self.product_table.setItem(row, 0, QTableWidgetItem(nom))
            self.product_table.setItem(row, 1, QTableWidgetItem(f"{prix:.0f}"))
            self.product_table.setItem(row, 2, QTableWidgetItem(f"{stock_qte:g}"))
            self.product_table.item(row, 0).setData(256, pid)

    def _filter_products(self, text):
        text = text.lower().strip()
        if not text:
            self._render_products(self._all_products)
            return
        filtered = [r for r in self._all_products if text in r[1].lower()]
        self._render_products(filtered)

    def _load_clients(self):
        self.client_combo.clear()
        self.client_combo.addItem("(aucun)", None)
        with self.session_factory() as session:
            for c in session.query(Client).order_by(Client.nom).all():
                self.client_combo.addItem(c.nom, c.id)

    def _add_selected_product(self):
        rows = self.product_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "Info", "Selectionnez un produit dans la liste.")
            return
        row = rows[0].row()
        produit_id = self.product_table.item(row, 0).data(256)
        qty = self.qty_spin.value()
        with self.session_factory() as session:
            p = session.get(Produit, produit_id)
            if not p:
                return
            for ligne in self.lignes:
                if ligne["produit_id"] == produit_id:
                    ligne["quantite"] += qty
                    self._refresh_cart()
                    return
            self.lignes.append(
                {
                    "produit_id": produit_id,
                    "nom": p.nom,
                    "quantite": qty,
                    "prix_unitaire": p.prix_vente,
                }
            )
        self._refresh_cart()

    def _remove_selected_line(self):
        rows = self.cart_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        del self.lignes[row]
        self._refresh_cart()

    def _refresh_cart(self):
        self.cart_table.setRowCount(len(self.lignes))
        total = 0.0
        for row, ligne in enumerate(self.lignes):
            sous_total = ligne["quantite"] * ligne["prix_unitaire"]
            total += sous_total
            self.cart_table.setItem(row, 0, QTableWidgetItem(ligne["nom"]))
            self.cart_table.setItem(row, 1, QTableWidgetItem(f"{ligne['quantite']:g}"))
            self.cart_table.setItem(row, 2, QTableWidgetItem(f"{ligne['prix_unitaire']:.0f}"))
            self.cart_table.setItem(row, 3, QTableWidgetItem(f"{sous_total:.0f}"))
        self.total_label.setText(f"Total: {total:.0f} FCFA")

    def _validate_sale(self):
        active_id = self.get_active_boutique_id()
        mode_paiement = self.payment_combo.currentData()
        client_id = self.client_combo.currentData()

        with self.session_factory() as session:
            try:
                vente = valider_vente(
                    session, active_id, self.lignes, mode_paiement, client_id
                )
            except ValueError as exc:
                QMessageBox.warning(self, "Erreur", str(exc))
                return
            total = vente.total

        QMessageBox.information(self, "Vente validee", f"Vente enregistree. Total: {total:.0f} FCFA")
        self.lignes = []
        self.refresh()
        if self.on_change:
            self.on_change()
