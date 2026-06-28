"""Fenetre principale: barre laterale de navigation + selecteur de boutique."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from boutiquepro.models import Boutique
from boutiquepro.ui.boutiques import BoutiquesScreen
from boutiquepro.ui.clients import ClientsScreen
from boutiquepro.ui.dashboard import DashboardScreen
from boutiquepro.ui.produits import ProduitsScreen
from boutiquepro.ui.rapports import RapportsScreen
from boutiquepro.ui.stock import StockScreen
from boutiquepro.ui.ventes import VentesScreen

TOUTES_BOUTIQUES = "__toutes__"


class MainWindow(QMainWindow):
    def __init__(self, session_factory):
        super().__init__()
        self.session_factory = session_factory
        self.setWindowTitle("BoutiquePro - Gestion de boutiques")
        self.resize(1280, 800)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)

        # Top bar: boutique selector
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("Boutique active :"))
        self.boutique_combo = QComboBox()
        self.boutique_combo.currentIndexChanged.connect(self._on_boutique_changed)
        top_bar.addWidget(self.boutique_combo)
        top_bar.addStretch()
        root_layout.addLayout(top_bar)

        body_layout = QHBoxLayout()
        root_layout.addLayout(body_layout)

        # Sidebar
        self.nav_list = QListWidget()
        self.nav_list.setFixedWidth(180)
        for label in [
            "Dashboard",
            "Ventes",
            "Stock",
            "Produits",
            "Clients",
            "Boutiques",
            "Rapports",
        ]:
            QListWidgetItem(label, self.nav_list)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        body_layout.addWidget(self.nav_list)

        # Stacked screens
        self.stack = QStackedWidget()
        body_layout.addWidget(self.stack, 1)

        self.dashboard_screen = DashboardScreen(session_factory, self.get_active_boutique_id)
        self.ventes_screen = VentesScreen(
            session_factory, self.get_active_boutique_id, on_change=self._on_data_changed
        )
        self.stock_screen = StockScreen(
            session_factory, self.get_active_boutique_id, on_change=self._on_data_changed
        )
        self.produits_screen = ProduitsScreen(session_factory, on_change=self._on_data_changed)
        self.clients_screen = ClientsScreen(session_factory, on_change=self._on_data_changed)
        self.boutiques_screen = BoutiquesScreen(session_factory, on_change=self._on_boutiques_changed)
        self.rapports_screen = RapportsScreen(session_factory)

        for screen in [
            self.dashboard_screen,
            self.ventes_screen,
            self.stock_screen,
            self.produits_screen,
            self.clients_screen,
            self.boutiques_screen,
            self.rapports_screen,
        ]:
            self.stack.addWidget(screen)

        self.nav_list.setCurrentRow(0)
        self._refresh_boutique_combo()

    def get_active_boutique_id(self):
        data = self.boutique_combo.currentData()
        if data == TOUTES_BOUTIQUES or data is None:
            return None
        return data

    def _refresh_boutique_combo(self):
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

    def _on_nav_changed(self, row):
        self.stack.setCurrentIndex(row)
        self._refresh_current_screen()

    def _on_boutique_changed(self):
        self._refresh_current_screen()

    def _refresh_current_screen(self):
        widget = self.stack.currentWidget()
        if hasattr(widget, "refresh"):
            widget.refresh()

    def _on_data_changed(self):
        # Refresh dashboard numbers whenever underlying data changes
        self.dashboard_screen.refresh()

    def _on_boutiques_changed(self):
        self._refresh_boutique_combo()
        self._on_data_changed()
