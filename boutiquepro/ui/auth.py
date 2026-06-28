"""Dialogues d'authentification: creation du premier utilisateur, connexion
par PIN, et gestion legere des utilisateurs (cahier des charges 3.8)."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from boutiquepro.models import Boutique, RoleUtilisateur, Utilisateur
from boutiquepro.services import pin_is_valid as _pin_is_valid


class PremierUtilisateurDialog(QDialog):
    """Affiche au tout premier lancement (aucun utilisateur en base) pour
    creer le compte proprietaire initial."""

    def __init__(self, session_factory, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.setWindowTitle("Bienvenue - Creation du premier compte")
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.addWidget(
            QLabel(
                "Aucun utilisateur n'existe encore. Creez le compte du "
                "proprietaire pour demarrer."
            )
        )

        form = QFormLayout()
        self.nom_edit = QLineEdit()
        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.Password)
        self.pin_confirm_edit = QLineEdit()
        self.pin_confirm_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Nom *", self.nom_edit)
        form.addRow("PIN (4 a 6 chiffres) *", self.pin_edit)
        form.addRow("Confirmer le PIN *", self.pin_confirm_edit)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.create_btn = QPushButton("Creer le compte")
        self.create_btn.clicked.connect(self._create)
        btn_row.addStretch()
        btn_row.addWidget(self.create_btn)
        layout.addLayout(btn_row)

        self.utilisateur: Utilisateur | None = None

    def _create(self):
        nom = self.nom_edit.text().strip()
        pin = self.pin_edit.text().strip()
        pin_confirm = self.pin_confirm_edit.text().strip()
        if not nom:
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return
        if not _pin_is_valid(pin):
            QMessageBox.warning(self, "Erreur", "Le PIN doit contenir entre 4 et 6 chiffres.")
            return
        if pin != pin_confirm:
            QMessageBox.warning(self, "Erreur", "Les deux PIN ne correspondent pas.")
            return
        with self.session_factory() as session:
            user = Utilisateur(nom=nom, role=RoleUtilisateur.PROPRIETAIRE)
            user.set_pin(pin)
            session.add(user)
            session.commit()
            self.utilisateur = user
        self.accept()


class ConnexionDialog(QDialog):
    """Dialogue de connexion: choix de l'utilisateur + saisie du PIN."""

    def __init__(self, session_factory, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.setWindowTitle("Connexion - BoutiquePro")
        self.setModal(True)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.user_combo = QComboBox()
        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.Password)
        self.pin_edit.returnPressed.connect(self._connect)
        form.addRow("Utilisateur", self.user_combo)
        form.addRow("PIN", self.pin_edit)
        layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.connect_btn = QPushButton("Se connecter")
        self.connect_btn.clicked.connect(self._connect)
        btn_row.addStretch()
        btn_row.addWidget(self.connect_btn)
        layout.addLayout(btn_row)

        self.utilisateur: Utilisateur | None = None
        self._load_users()

    def _load_users(self):
        with self.session_factory() as session:
            users = session.query(Utilisateur).order_by(Utilisateur.nom).all()
            for u in users:
                self.user_combo.addItem(u.nom, u.id)

    def _connect(self):
        user_id = self.user_combo.currentData()
        pin = self.pin_edit.text().strip()
        if user_id is None:
            QMessageBox.warning(self, "Erreur", "Aucun utilisateur selectionne.")
            return
        with self.session_factory() as session:
            user = session.get(Utilisateur, user_id)
            if user is None or not user.verify_pin(pin):
                QMessageBox.warning(self, "Erreur", "PIN incorrect. Veuillez reessayer.")
                self.pin_edit.clear()
                self.pin_edit.setFocus()
                return
            self.utilisateur = user
        self.accept()


class UtilisateursDialog(QDialog):
    """Gestion legere des utilisateurs (creation de gerants par le proprietaire)."""

    def __init__(self, session_factory, parent=None):
        super().__init__(parent)
        self.session_factory = session_factory
        self.setWindowTitle("Gestion des utilisateurs")
        self.resize(560, 380)

        layout = QHBoxLayout(self)

        left = QVBoxLayout()
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Nom", "Role", "Boutique"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        left.addWidget(self.table)
        layout.addLayout(left, 2)

        right = QVBoxLayout()
        form = QFormLayout()
        self.nom_edit = QLineEdit()
        self.role_combo = QComboBox()
        self.role_combo.addItem("Gerant", RoleUtilisateur.GERANT)
        self.role_combo.addItem("Proprietaire", RoleUtilisateur.PROPRIETAIRE)
        self.role_combo.currentIndexChanged.connect(self._on_role_changed)
        self.boutique_combo = QComboBox()
        self.pin_edit = QLineEdit()
        self.pin_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Nom *", self.nom_edit)
        form.addRow("Role *", self.role_combo)
        form.addRow("Boutique (gerant)", self.boutique_combo)
        form.addRow("PIN (4 a 6 chiffres) *", self.pin_edit)
        right.addLayout(form)

        btn_row = QHBoxLayout()
        self.create_btn = QPushButton("Creer l'utilisateur")
        self.create_btn.clicked.connect(self._create)
        self.delete_btn = QPushButton("Supprimer")
        self.delete_btn.clicked.connect(self._delete)
        btn_row.addWidget(self.create_btn)
        btn_row.addWidget(self.delete_btn)
        right.addLayout(btn_row)
        right.addStretch()
        layout.addLayout(right, 1)

        self.table.itemSelectionChanged.connect(self._on_select)
        self._editing_id: int | None = None

        self._load_boutiques()
        self.refresh()

    def _load_boutiques(self):
        self.boutique_combo.clear()
        with self.session_factory() as session:
            for b in session.query(Boutique).order_by(Boutique.nom).all():
                self.boutique_combo.addItem(b.nom, b.id)

    def _on_role_changed(self):
        is_gerant = self.role_combo.currentData() == RoleUtilisateur.GERANT
        self.boutique_combo.setEnabled(is_gerant)

    def refresh(self):
        self.table.setRowCount(0)
        with self.session_factory() as session:
            users = session.query(Utilisateur).order_by(Utilisateur.nom).all()
            self.table.setRowCount(len(users))
            for row, u in enumerate(users):
                self.table.setItem(row, 0, QTableWidgetItem(u.nom))
                role_label = "Proprietaire" if u.role == RoleUtilisateur.PROPRIETAIRE else "Gerant"
                self.table.setItem(row, 1, QTableWidgetItem(role_label))
                boutique_nom = u.boutique.nom if u.boutique else ""
                self.table.setItem(row, 2, QTableWidgetItem(boutique_nom))
                self.table.item(row, 0).setData(256, u.id)

    def _on_select(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        self._editing_id = self.table.item(row, 0).data(256)

    def _create(self):
        nom = self.nom_edit.text().strip()
        pin = self.pin_edit.text().strip()
        role = self.role_combo.currentData()
        if not nom:
            QMessageBox.warning(self, "Erreur", "Le nom est obligatoire.")
            return
        if not _pin_is_valid(pin):
            QMessageBox.warning(self, "Erreur", "Le PIN doit contenir entre 4 et 6 chiffres.")
            return
        boutique_id = None
        if role == RoleUtilisateur.GERANT:
            boutique_id = self.boutique_combo.currentData()
            if boutique_id is None:
                QMessageBox.warning(
                    self, "Erreur", "Un gerant doit etre rattache a une boutique."
                )
                return
        with self.session_factory() as session:
            user = Utilisateur(nom=nom, role=role, boutique_id=boutique_id)
            user.set_pin(pin)
            session.add(user)
            session.commit()
        self.nom_edit.clear()
        self.pin_edit.clear()
        self.refresh()

    def _delete(self):
        if not self._editing_id:
            return
        confirm = QMessageBox.question(
            self, "Confirmer", "Supprimer cet utilisateur ?"
        )
        if confirm != QMessageBox.Yes:
            return
        with self.session_factory() as session:
            u = session.get(Utilisateur, self._editing_id)
            if u:
                session.delete(u)
                session.commit()
        self._editing_id = None
        self.refresh()
