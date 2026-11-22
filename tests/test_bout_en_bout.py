"""Test de bout en bout : jeu de test généré, CLI, rapport comparé aux constantes."""

import csv
import re
from pathlib import Path

from csv_controle.cli import CODE_ANOMALIES, controler
from csv_controle.rapport import ENCODAGE_EXCEL, NOM_ANOMALIES, NOM_RAPPORT
from data.generer_jeu_test import (
    COLONNES,
    N_CHAMPS_MANQUANTS,
    N_CHAMPS_VIDES,
    N_DOUBLONS_EXACTS,
    N_LIGNES_MALFORMEES,
    N_LIGNES_TOTAL,
    N_QUASI_DOUBLONS,
    N_VALEURS_NA,
    generer,
)

RACINE = Path(__file__).parent.parent
CONFIG = RACINE / "regles.yaml"


def nombre(rapport: str, libelle: str) -> int:
    """Extrait le premier nombre de la ligne de rapport commençant par libellé."""
    trouve = re.search(rf"^- {re.escape(libelle)} : (\d+)", rapport, flags=re.MULTILINE)
    assert trouve, f"libellé absent du rapport : {libelle}"
    return int(trouve.group(1))


def test_rapport_conforme_aux_constantes_injectees(tmp_path: Path) -> None:
    """Le rapport retrouve exactement les anomalies injectées par le générateur."""
    fichier = generer(tmp_path / "missions_test.csv")
    sortie = tmp_path / "rapport"

    assert controler(fichier, CONFIG, sortie) == CODE_ANOMALIES

    rapport = (sortie / NOM_RAPPORT).read_text(encoding="utf-8")
    assert nombre(rapport, "Lignes lues (hors en-tête)") == N_LIGNES_TOTAL
    assert nombre(rapport, "Lignes mal formées") == N_LIGNES_MALFORMEES
    assert nombre(rapport, "Doublons exacts") == N_DOUBLONS_EXACTS
    assert nombre(rapport, "Quasi-doublons à vérifier") == N_QUASI_DOUBLONS
    assert nombre(rapport, "Anomalies au total") == (
        N_DOUBLONS_EXACTS + N_QUASI_DOUBLONS + N_CHAMPS_MANQUANTS + N_LIGNES_MALFORMEES
    )
    assert f"| benevole_nom | {N_CHAMPS_VIDES} |" in rapport
    assert f"| email | {N_VALEURS_NA} |" in rapport
    # Une ligne a une colonne en trop, l'autre une colonne en moins.
    attendu = len(COLONNES)
    assert f"{attendu + 1} colonne(s) au lieu de {attendu}" in rapport
    assert f"{attendu - 1} colonne(s) au lieu de {attendu}" in rapport


def test_anomalies_csv_conforme_aux_constantes(tmp_path: Path) -> None:
    """anomalies.csv contient une ligne par anomalie injectée, par type."""
    fichier = generer(tmp_path / "missions_test.csv")
    sortie = tmp_path / "rapport"
    controler(fichier, CONFIG, sortie)

    with (sortie / NOM_ANOMALIES).open(encoding=ENCODAGE_EXCEL, newline="") as flux:
        anomalies = list(csv.DictReader(flux, delimiter=";"))

    attendus = {
        "doublon_exact": N_DOUBLONS_EXACTS,
        "quasi_doublon": N_QUASI_DOUBLONS,
        "champ_manquant": N_CHAMPS_MANQUANTS,
        "ligne_malformee": N_LIGNES_MALFORMEES,
    }
    comptes = {
        type_attendu: sum(1 for a in anomalies if a["type"] == type_attendu)
        for type_attendu in attendus
    }
    assert comptes == attendus


def test_generation_reproductible(tmp_path: Path) -> None:
    """La graine fixe produit deux fois le même fichier."""
    premier = generer(tmp_path / "a.csv").read_bytes()
    second = generer(tmp_path / "b.csv").read_bytes()

    assert premier == second


def test_emails_uniques_hors_injections(tmp_path: Path) -> None:
    """Les emails de base sont uniques : aucun doublon accidentel possible."""
    fichier = generer(tmp_path / "missions_test.csv")
    with fichier.open(encoding="utf-8", newline="") as flux:
        lignes = list(csv.DictReader(flux, delimiter=";"))

    emails = [ligne["email"].strip().lower() for ligne in lignes]
    # Seuls les doublons injectés répètent un email ; tous finissent en example.org.
    assert len(set(emails)) == N_LIGNES_TOTAL - N_DOUBLONS_EXACTS - N_VALEURS_NA + 1
    assert all(email.endswith("@example.org") or email == "n/a" for email in emails)
