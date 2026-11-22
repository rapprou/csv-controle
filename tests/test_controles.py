"""Tests du contrôle des champs manquants."""

from pathlib import Path

from csv_controle.controles import (
    TYPE_CHAMP_MANQUANT,
    TYPE_COLONNE_ABSENTE,
    controler_champs_manquants,
)
from csv_controle.lecture import lire_csv
from csv_controle.modeles import Regles

ENTETE = "id_mission,benevole_nom,email"
REGLES = Regles(colonnes_obligatoires=("benevole_nom", "email"))


def lire(tmp_path: Path, contenu: str):
    """Écrit puis lit un CSV de test."""
    fichier = tmp_path / "mission.csv"
    fichier.write_text(contenu, encoding="utf-8")
    return lire_csv(fichier)


def test_valeurs_considerees_manquantes(tmp_path: Path) -> None:
    """Vide, espaces, N/A, null et - sont tous des champs manquants."""
    lecture = lire(
        tmp_path,
        f"{ENTETE}\n"
        "M1,,a@example.org\n"
        "M2,   ,b@example.org\n"
        "M3,N/A,c@example.org\n"
        "M4,NULL,d@example.org\n"
        "M5,-,e@example.org\n",
    )

    anomalies = controler_champs_manquants(lecture, REGLES)

    assert [anomalie.ligne for anomalie in anomalies] == [2, 3, 4, 5, 6]
    assert {anomalie.colonne for anomalie in anomalies} == {"benevole_nom"}
    assert {anomalie.type for anomalie in anomalies} == {TYPE_CHAMP_MANQUANT}


def test_valeur_trouvee_conservee(tmp_path: Path) -> None:
    """L'anomalie garde la valeur telle qu'elle figure dans le fichier."""
    lecture = lire(tmp_path, f"{ENTETE}\nM1,  n/a  ,a@example.org\n")

    anomalie = controler_champs_manquants(lecture, REGLES)[0]

    assert anomalie.valeur == "  n/a  "
    assert anomalie.detail == "colonne obligatoire benevole_nom non renseignée"


def test_lignes_completes_sans_anomalie(tmp_path: Path) -> None:
    """Une ligne renseignée ne produit aucune anomalie."""
    lecture = lire(tmp_path, f"{ENTETE}\nM1,Dupont,a@example.org\n")

    assert controler_champs_manquants(lecture, REGLES) == []


def test_une_anomalie_par_colonne_manquante(tmp_path: Path) -> None:
    """Deux colonnes vides sur la même ligne donnent deux anomalies."""
    lecture = lire(tmp_path, f"{ENTETE}\nM1,,\n")

    anomalies = controler_champs_manquants(lecture, REGLES)

    assert [(anomalie.ligne, anomalie.colonne) for anomalie in anomalies] == [
        (2, "benevole_nom"),
        (2, "email"),
    ]


def test_colonne_obligatoire_absente_de_lentete(tmp_path: Path) -> None:
    """Une colonne obligatoire inconnue du fichier donne une anomalie en ligne 1."""
    lecture = lire(tmp_path, f"{ENTETE}\nM1,Dupont,a@example.org\n")
    regles = Regles(colonnes_obligatoires=("email", "date_debut"))

    anomalies = controler_champs_manquants(lecture, regles)

    assert len(anomalies) == 1
    anomalie = anomalies[0]
    assert anomalie.ligne == 1
    assert anomalie.colonne == "date_debut"
    assert anomalie.type == TYPE_COLONNE_ABSENTE
    assert anomalie.valeur == ""
    assert anomalie.detail == (
        "colonne obligatoire date_debut absente de l'en-tête du fichier"
    )


def test_colonne_absente_et_champs_manquants_cumules(tmp_path: Path) -> None:
    """Les deux types d'anomalies cohabitent dans le même résultat."""
    lecture = lire(tmp_path, f"{ENTETE}\nM1,,a@example.org\n")
    regles = Regles(colonnes_obligatoires=("benevole_nom", "date_debut"))

    anomalies = controler_champs_manquants(lecture, regles)

    assert [(anomalie.ligne, anomalie.type) for anomalie in anomalies] == [
        (1, TYPE_COLONNE_ABSENTE),
        (2, TYPE_CHAMP_MANQUANT),
    ]


def test_valeurs_manquantes_personnalisees(tmp_path: Path) -> None:
    """La liste des marqueurs manquants vient des règles."""
    lecture = lire(tmp_path, f"{ENTETE}\nM1,inconnu,a@example.org\n")
    regles = Regles(colonnes_obligatoires=("benevole_nom",), valeurs_manquantes=("inconnu",))

    anomalies = controler_champs_manquants(lecture, regles)

    assert [anomalie.valeur for anomalie in anomalies] == ["inconnu"]
