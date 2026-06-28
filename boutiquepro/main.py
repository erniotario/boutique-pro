"""Point d'entree de l'application BoutiquePro."""
from __future__ import annotations

import sys

from boutiquepro.database import init_db


def main():
    from PySide6.QtWidgets import QApplication, QDialog

    from boutiquepro.models import Utilisateur
    from boutiquepro.ui.auth import ConnexionDialog, PremierUtilisateurDialog
    from boutiquepro.ui.main_window import MainWindow

    engine, session_factory = init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("BoutiquePro")

    # Premier lancement : aucun utilisateur en base -> creation du compte
    # proprietaire (cahier des charges 3.8).
    with session_factory() as session:
        has_users = session.query(Utilisateur).first() is not None

    utilisateur = None
    if not has_users:
        setup_dialog = PremierUtilisateurDialog(session_factory)
        if setup_dialog.exec() != QDialog.Accepted:
            sys.exit(0)
        utilisateur = setup_dialog.utilisateur
    else:
        login_dialog = ConnexionDialog(session_factory)
        if login_dialog.exec() != QDialog.Accepted:
            sys.exit(0)
        utilisateur = login_dialog.utilisateur

    window = MainWindow(session_factory, utilisateur=utilisateur)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
