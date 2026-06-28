# BoutiquePro

Application de bureau (100% hors-ligne) pour la gestion de plusieurs boutiques
a Yaounde, Cameroun. Stack : Python 3.10+, PySide6, SQLAlchemy, SQLite.

## Installation

```bash
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sous Windows
pip install -r requirements.txt
```

## Lancement

```bash
python -m boutiquepro.main
```

La base de donnees SQLite est creee automatiquement dans le repertoire de
donnees utilisateur (ex: `~/.local/share/BoutiquePro/boutiquepro.db` sous
Linux) au premier lancement.

## Connexion et gestion des utilisateurs

Au tout premier lancement (aucun utilisateur en base), l'application affiche
une fenetre de bienvenue pour creer le compte du **proprietaire** : un nom et
un PIN (4 a 6 chiffres). Ce PIN n'est jamais stocke en clair : seul un hash
sale (SHA-256 + sel aleatoire par utilisateur) est enregistre en base.

Aux lancements suivants, une fenetre de connexion demande de choisir
l'utilisateur dans une liste puis de saisir son PIN.

Deux roles existent :

- **Proprietaire** : acces complet, toutes les boutiques + vue consolidee,
  et seul role autorise a creer d'autres utilisateurs.
- **Gerant** : rattache a une seule boutique ; le selecteur de boutique en
  haut de la fenetre principale est alors verrouille sur cette boutique
  (pas de "Toutes boutiques", pas de changement possible).

Le proprietaire peut creer des comptes gerants (et leur PIN) via le menu
**Administration > Gestion des utilisateurs** de la fenetre principale.

L'authentification reste volontairement simple, conformement au cahier des
charges : pas de jetons de session, pas de regles de complexite au-dela de
la longueur du PIN, pas de verrouillage anti-bruteforce.

## Construire l'executable (Windows)

```bash
pip install -r requirements-dev.txt
bash packaging/build_exe.sh
```

Le resultat (mode `--onedir`) se trouve dans `dist/BoutiquePro/`. Pour
generer un installeur Windows avec raccourcis menu Demarrer et
desinstalleur, utilisez le script NSIS fourni (necessite NSIS / `makensis`,
sous Windows) :

```bash
makensis packaging/installer.nsi
```

Cela produit `packaging/BoutiquePro-Setup.exe`.

## Sauvegarde et restauration de la base de donnees

Sauvegarder la base actuelle vers un dossier au choix (nom de fichier
horodate) :

```bash
python scripts/backup_db.py /chemin/vers/dossier_de_sauvegardes
```

Restaurer une sauvegarde (la base actuelle est d'abord copiee en securite
avec le suffixe `.avant_restauration`) :

```bash
python scripts/restore_db.py /chemin/vers/boutiquepro_backup_20260101_120000.db
```
