"""Tests de la détection des doublons exacts."""

from pathlib import Path

from csv_controle.controles import (
    TYPE_DOUBLON_EXACT,
    anomalies_doublons_exacts,
    controler_doublons_exacts,
)
from csv_controle.lecture import lire_csv
from csv_controle.modeles import Lecture, Regles

ENTETE = "id_mission,benevole_nom,email,date_debut"
REGLES = Regles(colonnes_cles=("email", "date_debut"))


def lire(tmp_path: Path, lignes: list[str]) -> Lecture:
    """Écrit puis lit un CSV de test à partir de ses lignes de données."""
    fichier = tmp_path / "mission.csv"
    fichier.write_text("\n".join([ENTETE, *lignes]) + "\n", encoding="utf-8")
    return lire_csv(fichier)


def test_doublon_exact_sur_les_colonnes_cles(tmp_path: Path) -> None:
    """Deux lignes de mêmes clés forment un groupe avec sa première occurrence."""
    lecture = lire(
        tmp_path,
        [
            "M1,Dupont,jean@example.org,2026-01-05",
            "M2,Martin,sophie@example.org,2026-02-10",
            "M3,Dupont,jean@example.org,2026-01-05",
        ],
    )

    groupes = controler_doublons_exacts(lecture, REGLES)

    assert len(groupes) == 1
    assert groupes[0].lignes == (2, 4)
    assert groupes[0].premiere_occurrence == 2


def test_normalisation_avant_comparaison(tmp_path: Path) -> None:
    """Casse, espaces multiples et accents n'empêchent pas la détection."""
    lecture = lire(
        tmp_path,
        [
            "M1,Jean  Dupont,Jean@Example.ORG,2026-01-05",
            "M2,Jéan Dupont,  jean@example.org ,2026-01-05",
        ],
    )

    groupes = controler_doublons_exacts(lecture, REGLES)

    assert [groupe.lignes for groupe in groupes] == [(2, 3)]


def test_cles_manquantes_exclues(tmp_path: Path) -> None:
    """Des lignes dont une clé est vide ou N/A ne sont jamais des doublons."""
    lecture = lire(
        tmp_path,
        [
            "M1,Dupont,,2026-01-05",
            "M2,Martin,,2026-01-05",
            "M3,Durand,N/A,2026-01-05",
            "M4,Noel,jean@example.org,",
        ],
    )

    assert controler_doublons_exacts(lecture, REGLES) == []


def test_trois_lignes_dans_un_meme_groupe(tmp_path: Path) -> None:
    """Un groupe rassemble toutes les lignes concernées, dans l'ordre du fichier."""
    lecture = lire(
        tmp_path,
        [
            "M1,Dupont,jean@example.org,2026-01-05",
            "M2,Dupont,jean@example.org,2026-01-05",
            "M3,Dupont,jean@example.org,2026-01-05",
        ],
    )

    groupes = controler_doublons_exacts(lecture, REGLES)

    assert groupes[0].lignes == (2, 3, 4)


def test_cle_partiellement_differente_non_doublon(tmp_path: Path) -> None:
    """Même email mais date différente : ce n'est pas un doublon exact."""
    lecture = lire(
        tmp_path,
        [
            "M1,Dupont,jean@example.org,2026-01-05",
            "M2,Dupont,jean@example.org,2026-03-01",
        ],
    )

    assert controler_doublons_exacts(lecture, REGLES) == []


def test_colonne_cle_absente_desactive_la_detection(tmp_path: Path) -> None:
    """Une seule colonne clé absente suffit à ne pas lancer la détection."""
    lecture = lire(
        tmp_path,
        [
            "M1,Dupont,jean@example.org,2026-01-05",
            "M2,Dupont,jean@example.org,2026-03-01",
        ],
    )
    regles = Regles(colonnes_cles=("email", "numero_dossier"))

    # Comparer sur le seul email rapprocherait ces deux lignes à tort.
    assert controler_doublons_exacts(lecture, regles) == []


def test_aucune_colonne_cle_configuree(tmp_path: Path) -> None:
    """Sans colonne clé configurée, la détection renvoie une liste vide."""
    lecture = lire(tmp_path, ["M1,Dupont,jean@example.org,2026-01-05"])

    assert controler_doublons_exacts(lecture, Regles()) == []


def test_anomalies_hors_premiere_occurrence(tmp_path: Path) -> None:
    """Seules les répétitions deviennent des anomalies, pas la première ligne."""
    lecture = lire(
        tmp_path,
        [
            "M1,Dupont,jean@example.org,2026-01-05",
            "M2,Dupont,jean@example.org,2026-01-05",
            "M3,Dupont,jean@example.org,2026-01-05",
        ],
    )

    anomalies = anomalies_doublons_exacts(controler_doublons_exacts(lecture, REGLES))

    assert [anomalie.ligne for anomalie in anomalies] == [3, 4]
    assert {anomalie.type for anomalie in anomalies} == {TYPE_DOUBLON_EXACT}
    assert anomalies[0].detail == "identique à la ligne 2"
    assert anomalies[0].valeur == "jean@example.org | 2026-01-05"
