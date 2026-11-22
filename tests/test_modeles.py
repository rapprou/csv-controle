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


def test_section_quasi_doublons(tmp_path: Path) -> None:
    """La section quasi_doublons est lue avec ses quatre réglages."""
    chemin = ecrire_regles(
        tmp_path,
        "quasi_doublons:\n"
        "  actif: false\n"
        "  seuil: 95\n"
        "  champs:\n    - benevole_nom\n"
        "  champ_blocage: date_debut\n",
    )

    reglage = charger_regles(chemin).quasi_doublons

    assert reglage.actif is False
    assert reglage.seuil == 95
    assert reglage.champs == ("benevole_nom",)
    assert reglage.champ_blocage == "date_debut"


def test_seuil_par_defaut(tmp_path: Path) -> None:
    """Sans seuil configuré, la valeur par défaut est 90."""
    chemin = ecrire_regles(tmp_path, "quasi_doublons:\n  actif: true\n")

    assert charger_regles(chemin).quasi_doublons.seuil == 90


def test_seuil_hors_bornes(tmp_path: Path) -> None:
    """Un seuil hors de 0-100 lève une erreur de configuration."""
    chemin = ecrire_regles(tmp_path, "quasi_doublons:\n  seuil: 150\n")

    with pytest.raises(ErreurConfiguration):
        charger_regles(chemin)


def test_colonnes_citees_sans_doublon(tmp_path: Path) -> None:
    """Une colonne citée à plusieurs endroits n'apparaît qu'une fois."""
    chemin = ecrire_regles(
        tmp_path,
        "colonnes_obligatoires:\n  - email\n"
        "colonnes_cles:\n  - email\n  - date_debut\n"
        "quasi_doublons:\n  champs:\n    - email\n  champ_blocage: date_debut\n",
    )

    assert charger_regles(chemin).colonnes_citees() == ["email", "date_debut"]


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
    assert regles.colonnes_cles == ("email", "date_debut")
    assert regles.quasi_doublons.actif is True
    assert regles.quasi_doublons.champ_blocage == "date_debut"
