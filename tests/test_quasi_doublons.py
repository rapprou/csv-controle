"""Tests de la détection des quasi-doublons."""

from pathlib import Path

from csv_controle.controles import (
    TYPE_QUASI_DOUBLON,
    anomalies_quasi_doublons,
    controler_doublons_exacts,
    controler_quasi_doublons,
)
from csv_controle.lecture import lire_csv
from csv_controle.modeles import Lecture, QuasiDoublons, Regles

ENTETE = "id_mission,benevole_nom,email,date_debut"
REGLES = Regles(
    colonnes_cles=("email", "date_debut"),
    quasi_doublons=QuasiDoublons(
        actif=True, seuil=90, champs=("benevole_nom", "email"), champ_blocage="date_debut"
    ),
)


def lire(tmp_path: Path, lignes: list[str]) -> Lecture:
    """Écrit puis lit un CSV de test à partir de ses lignes de données."""
    fichier = tmp_path / "mission.csv"
    fichier.write_text("\n".join([ENTETE, *lignes]) + "\n", encoding="utf-8")
    return lire_csv(fichier)


def quasi(lecture: Lecture, regles: Regles = REGLES):
    """Enchaîne doublons exacts puis quasi-doublons, comme le fera le CLI."""
    return controler_quasi_doublons(
        lecture, regles, controler_doublons_exacts(lecture, regles)
    )


def test_faute_de_frappe_detectee(tmp_path: Path) -> None:
    """Une coquille sur le nom et l'email est signalée avec son score."""
    lecture = lire(
        tmp_path,
        [
            "M1,Jean Dupont,jean.dupont@example.org,2026-01-05",
            "M2,Jean Dupond,jean.dupond@example.org,2026-01-05",
        ],
    )

    paires = quasi(lecture)

    assert [paire.lignes for paire in paires] == [(2, 3)]
    assert 90 <= paires[0].score < 100


def test_lignes_trop_differentes_ignorees(tmp_path: Path) -> None:
    """Deux bénévoles distincts ne sont pas des quasi-doublons."""
    lecture = lire(
        tmp_path,
        [
            "M1,Jean Dupont,jean.dupont@example.org,2026-01-05",
            "M2,Sophie Martin,sophie.martin@example.org,2026-01-05",
        ],
    )

    assert quasi(lecture) == []


def test_blocage_sur_date_differente(tmp_path: Path) -> None:
    """Deux lignes proches mais de dates différentes ne sont pas comparées."""
    lecture = lire(
        tmp_path,
        [
            "M1,Jean Dupont,jean.dupont@example.org,2026-01-05",
            "M2,Jean Dupond,jean.dupond@example.org,2026-03-01",
        ],
    )

    assert quasi(lecture) == []


def test_repetitions_exactes_exclues(tmp_path: Path) -> None:
    """Les répétitions d'un doublon exact ne sont comparées qu'une fois."""
    lecture = lire(
        tmp_path,
        [
            "M1,Jean Dupont,jean.dupont@example.org,2026-01-05",
            "M2,Jean Dupont,jean.dupont@example.org,2026-01-05",
            "M3,Jean Dupond,jean.dupond@example.org,2026-01-05",
        ],
    )

    paires = quasi(lecture)

    # La ligne 3 répète exactement la ligne 2 : seule la paire 2/4 subsiste.
    assert [paire.lignes for paire in paires] == [(2, 4)]


def test_une_paire_signalee_une_seule_fois(tmp_path: Path) -> None:
    """Chaque couple de lignes n'apparaît qu'une fois dans le résultat."""
    lecture = lire(
        tmp_path,
        [
            "M1,Jean Dupont,jean.dupont1@example.org,2026-01-05",
            "M2,Jean Dupont,jean.dupont2@example.org,2026-01-05",
            "M3,Jean Dupont,jean.dupont3@example.org,2026-01-05",
        ],
    )

    paires = quasi(lecture)

    # Les trois combinaisons possibles, chacune une seule fois et jamais inversée.
    assert sorted(paire.lignes for paire in paires) == [(2, 3), (2, 4), (3, 4)]


def test_seuil_configurable(tmp_path: Path) -> None:
    """Un seuil à 100 ne retient plus les lignes simplement proches."""
    lecture = lire(
        tmp_path,
        [
            "M1,Jean Dupont,jean.dupont@example.org,2026-01-05",
            "M2,Jean Dupond,jean.dupond@example.org,2026-01-05",
        ],
    )
    regles = Regles(
        colonnes_cles=REGLES.colonnes_cles,
        quasi_doublons=QuasiDoublons(
            seuil=100, champs=("benevole_nom", "email"), champ_blocage="date_debut"
        ),
    )

    assert quasi(lecture, regles) == []


def test_desactivation_sans_plantage(tmp_path: Path) -> None:
    """Désactivés dans les règles, les quasi-doublons renvoient une liste vide."""
    lecture = lire(
        tmp_path,
        [
            "M1,Jean Dupont,jean.dupont@example.org,2026-01-05",
            "M2,Jean Dupond,jean.dupond@example.org,2026-01-05",
        ],
    )
    regles = Regles(quasi_doublons=QuasiDoublons(actif=False, champs=("benevole_nom",)))

    assert quasi(lecture, regles) == []


def test_champ_de_blocage_absent_de_lentete(tmp_path: Path) -> None:
    """Sans champ de blocage exploitable, aucune comparaison n'est faite."""
    lecture = lire(tmp_path, ["M1,Jean Dupont,jean.dupont@example.org,2026-01-05"])
    regles = Regles(
        quasi_doublons=QuasiDoublons(champs=("benevole_nom",), champ_blocage="ville")
    )

    assert quasi(lecture, regles) == []


def test_valeur_de_blocage_manquante(tmp_path: Path) -> None:
    """Deux lignes sans date de début ne sont pas rapprochées."""
    lecture = lire(
        tmp_path,
        [
            "M1,Jean Dupont,jean.dupont@example.org,",
            "M2,Jean Dupond,jean.dupond@example.org,",
        ],
    )

    assert quasi(lecture) == []


def test_anomalies_portees_par_la_seconde_ligne(tmp_path: Path) -> None:
    """L'anomalie renvoie vers la première ligne de la paire et donne le score."""
    lecture = lire(
        tmp_path,
        [
            "M1,Jean Dupont,jean.dupont@example.org,2026-01-05",
            "M2,Jean Dupond,jean.dupond@example.org,2026-01-05",
        ],
    )

    paires = quasi(lecture)
    anomalie = anomalies_quasi_doublons(paires)[0]

    assert anomalie.ligne == 3
    assert anomalie.type == TYPE_QUASI_DOUBLON
    assert anomalie.detail == f"ressemble à la ligne 2 (score {paires[0].score})"
