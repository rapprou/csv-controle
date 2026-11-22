"""Tests du contrôle centralisé de l'en-tête."""

from pathlib import Path

from csv_controle.controles import TYPE_COLONNE_ABSENTE, controler_colonnes
from csv_controle.lecture import lire_csv
from csv_controle.modeles import Lecture, QuasiDoublons, Regles

ENTETE = "id_mission,benevole_nom,email"


def lire(tmp_path: Path) -> Lecture:
    """Écrit puis lit un CSV de test minimal."""
    fichier = tmp_path / "mission.csv"
    fichier.write_text(f"{ENTETE}\nM1,Dupont,a@example.org\n", encoding="utf-8")
    return lire_csv(fichier)


def test_entete_complet_sans_anomalie(tmp_path: Path) -> None:
    """Toutes les colonnes citées sont présentes : rien à signaler."""
    regles = Regles(
        colonnes_obligatoires=("email",),
        colonnes_cles=("email",),
        quasi_doublons=QuasiDoublons(champs=("benevole_nom",), champ_blocage="email"),
    )

    assert controler_colonnes(lire(tmp_path), regles) == []


def test_une_anomalie_par_colonne_absente(tmp_path: Path) -> None:
    """Chaque colonne citée et absente donne une anomalie en ligne 1."""
    regles = Regles(
        colonnes_obligatoires=("email", "date_debut"),
        colonnes_cles=("statut",),
    )

    anomalies = controler_colonnes(lire(tmp_path), regles)

    assert [(anomalie.ligne, anomalie.colonne) for anomalie in anomalies] == [
        (1, "date_debut"),
        (1, "statut"),
    ]
    assert {anomalie.type for anomalie in anomalies} == {TYPE_COLONNE_ABSENTE}
    assert anomalies[0].valeur == ""
    assert anomalies[0].detail == (
        "colonne date_debut citée dans les règles, absente de l'en-tête"
    )


def test_colonne_citee_plusieurs_fois_signalee_une_seule_fois(tmp_path: Path) -> None:
    """Une colonne citée comme obligatoire, clé et comparée ne sort qu'une fois."""
    regles = Regles(
        colonnes_obligatoires=("date_debut",),
        colonnes_cles=("date_debut",),
        quasi_doublons=QuasiDoublons(champs=("date_debut",), champ_blocage="date_debut"),
    )

    anomalies = controler_colonnes(lire(tmp_path), regles)

    assert [anomalie.colonne for anomalie in anomalies] == ["date_debut"]


def test_colonnes_des_quasi_doublons_ignorees_si_inactifs(tmp_path: Path) -> None:
    """Quasi-doublons désactivés : leurs colonnes ne sont pas contrôlées."""
    regles = Regles(
        quasi_doublons=QuasiDoublons(
            actif=False, champs=("ville",), champ_blocage="date_debut"
        )
    )

    assert controler_colonnes(lire(tmp_path), regles) == []
