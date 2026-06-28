"""Point d'entree de l'application BoutiquePro."""
from __future__ import annotations

import sys

from boutiquepro.database import init_db


def main():
    from PySide6.QtWidgets import QApplication

    from boutiquepro.ui.main_window import MainWindow

    engine, session_factory = init_db()

    app = QApplication(sys.argv)
    app.setApplicationName("BoutiquePro")

    window = MainWindow(session_factory)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
