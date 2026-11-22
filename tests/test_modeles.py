"""Tests du chargement de regles.yaml."""

from pathlib import Path

import pytest

from csv_controle.modeles import (
    VALEURS_MANQUANTES_DEFAUT,
    ErreurConfiguration,
    charger_regles,
)


def ecrire_regles(tmp_path: Path, contenu: str) -> Path:
    """Écrit un fichier de règles de test."""
    chemin = tmp_path / "regles.yaml"
    chemin.write_text(contenu, encoding="utf-8")
    return chemin


def test_chargement_complet(tmp_path: Path) -> None:
    """Les deux clés attendues sont lues."""
    chemin = ecrire_regles(
        tmp_path,
        'colonnes_obligatoires:\n  - email\nvaleurs_manquantes:\n  - ""\n  - "inconnu"\n',
    )

    regles = charger_regles(chemin)

    assert regles.colonnes_obligatoires == ("email",)
    assert regles.valeurs_manquantes == ("", "inconnu")


def test_valeurs_manquantes_par_defaut(tmp_path: Path) -> None:
    """Sans la clé valeurs_manquantes, la liste par défaut s'applique."""
    chemin = ecrire_regles(tmp_path, "colonnes_obligatoires:\n  - email\n")

    assert charger_regles(chemin).valeurs_manquantes == VALEURS_MANQUANTES_DEFAUT


def test_fichier_introuvable(tmp_path: Path) -> None:
    """Un fichier de règles absent lève une erreur de configuration."""
    with pytest.raises(ErreurConfiguration):
        charger_regles(tmp_path / "absent.yaml")


def test_contenu_invalide(tmp_path: Path) -> None:
    """Une clé au mauvais type lève une erreur de configuration."""
    chemin = ecrire_regles(tmp_path, "colonnes_obligatoires: email\n")

    with pytest.raises(ErreurConfiguration):
        charger_regles(chemin)


def test_regles_du_projet_lisibles() -> None:
    """Le regles.yaml livré avec le projet est valide."""
    regles = charger_regles(Path(__file__).parent.parent / "regles.yaml")

    assert "email" in regles.colonnes_obligatoires
    assert "N/A" in regles.valeurs_manquantes
