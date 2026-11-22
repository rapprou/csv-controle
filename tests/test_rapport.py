"""Tests du rapport et des codes de sortie du CLI."""

import csv
from pathlib import Path

from csv_controle.cli import CODE_ANOMALIES, CODE_ERREUR, CODE_OK, controler
from csv_controle.rapport import ENCODAGE_EXCEL, NOM_ANOMALIES, NOM_RAPPORT

ENTETE = "id_mission,benevole_nom,email,date_debut"

REGLES = (
    "colonnes_obligatoires:\n  - benevole_nom\n  - email\n"
    "colonnes_cles:\n  - email\n  - date_debut\n"
    "quasi_doublons:\n"
    "  actif: true\n"
    "  seuil: 90\n"
    "  champs:\n    - benevole_nom\n    - email\n"
    "  champ_blocage: date_debut\n"
)

LIGNES_AVEC_ANOMALIES = [
    "M1,Jean Dupont,jean.dupont@example.org,2026-01-05",
    "M2,Jean Dupont,jean.dupont@example.org,2026-01-05",
    "M3,Jean Dupond,jean.dupond@example.org,2026-01-05",
    "M4,,sophie.martin@example.org,2026-02-10",
    "M5,Léa Noël,N/A,2026-02-10",
    "M6,Trop,peu,de,colonnes,ici",
]


def preparer(tmp_path: Path, lignes: list[str]) -> tuple[Path, Path, Path]:
    """Écrit un CSV et un fichier de règles, et renvoie les trois chemins."""
    fichier = tmp_path / "missions.csv"
    fichier.write_text("\n".join([ENTETE, *lignes]) + "\n", encoding="utf-8")
    config = tmp_path / "regles.yaml"
    config.write_text(REGLES, encoding="utf-8")
    return fichier, config, tmp_path / "rapport"


def lire_anomalies(sortie: Path) -> list[dict[str, str]]:
    """Relit anomalies.csv comme le ferait Excel en français."""
    with (sortie / NOM_ANOMALIES).open(encoding=ENCODAGE_EXCEL, newline="") as flux:
        return list(csv.DictReader(flux, delimiter=";"))


def test_code_sortie_sans_anomalie(tmp_path: Path) -> None:
    """Un fichier propre renvoie 0 et un rapport sans anomalie."""
    fichier, config, sortie = preparer(
        tmp_path, ["M1,Jean Dupont,jean.dupont@example.org,2026-01-05"]
    )

    assert controler(fichier, config, sortie) == CODE_OK
    rapport = (sortie / NOM_RAPPORT).read_text(encoding="utf-8")
    assert "Anomalies au total : 0" in rapport
    assert lire_anomalies(sortie) == []


def test_code_sortie_avec_anomalies(tmp_path: Path) -> None:
    """Un fichier à problèmes renvoie 1."""
    fichier, config, sortie = preparer(tmp_path, LIGNES_AVEC_ANOMALIES)

    assert controler(fichier, config, sortie) == CODE_ANOMALIES


def test_code_sortie_fichier_introuvable(tmp_path: Path) -> None:
    """Un CSV absent renvoie 2 sans écrire de rapport."""
    _, config, sortie = preparer(tmp_path, [])

    assert controler(tmp_path / "absent.csv", config, sortie) == CODE_ERREUR
    assert not sortie.exists()


def test_code_sortie_config_invalide(tmp_path: Path) -> None:
    """Un fichier de règles invalide renvoie 2."""
    fichier, config, sortie = preparer(tmp_path, LIGNES_AVEC_ANOMALIES)
    config.write_text("colonnes_obligatoires: email\n", encoding="utf-8")

    assert controler(fichier, config, sortie) == CODE_ERREUR


def test_rapport_markdown_complet(tmp_path: Path) -> None:
    """Le rapport reprend les compteurs et les quatre sections attendues."""
    fichier, config, sortie = preparer(tmp_path, LIGNES_AVEC_ANOMALIES)

    controler(fichier, config, sortie)
    rapport = (sortie / NOM_RAPPORT).read_text(encoding="utf-8")

    assert "Lignes lues (hors en-tête) : 6" in rapport
    assert "Lignes mal formées : 1" in rapport
    assert "Doublons exacts : 1 groupe(s)" in rapport
    assert "Quasi-doublons à vérifier : 1 paire(s)" in rapport
    assert "| benevole_nom | 1 |" in rapport
    assert "| email | 1 |" in rapport
    # Clé composite jointe sans « | » : le tableau garde ses trois colonnes.
    assert "| jean.dupont@example.org + 2026-01-05 | 2, 3 | 2 |" in rapport
    for titre in (
        "## Champs manquants",
        "## Doublons exacts",
        "## Quasi-doublons à vérifier",
        "## Lignes mal formées",
    ):
        assert titre in rapport


def test_anomalies_csv_format_excel(tmp_path: Path) -> None:
    """anomalies.csv est en utf-8-sig, séparé par des points-virgules."""
    fichier, config, sortie = preparer(tmp_path, LIGNES_AVEC_ANOMALIES)

    controler(fichier, config, sortie)

    octets = (sortie / NOM_ANOMALIES).read_bytes()
    assert octets.startswith(b"\xef\xbb\xbf")
    assert octets.splitlines()[0] == "ligne;colonne;type;detail".encode(ENCODAGE_EXCEL)


def test_anomalies_csv_une_ligne_par_anomalie(tmp_path: Path) -> None:
    """Chaque type de contrôle apparaît dans anomalies.csv, trié par ligne."""
    fichier, config, sortie = preparer(tmp_path, LIGNES_AVEC_ANOMALIES)

    controler(fichier, config, sortie)
    anomalies = lire_anomalies(sortie)

    numeros = [int(anomalie["ligne"]) for anomalie in anomalies]
    assert numeros == sorted(numeros)
    assert {anomalie["type"] for anomalie in anomalies} == {
        "champ_manquant",
        "doublon_exact",
        "quasi_doublon",
        "ligne_malformee",
    }


def test_colonne_absente_dans_le_rapport(tmp_path: Path) -> None:
    """Une colonne citée mais absente du fichier ressort en ligne 1."""
    fichier, config, sortie = preparer(
        tmp_path, ["M1,Jean Dupont,jean.dupont@example.org,2026-01-05"]
    )
    config.write_text("colonnes_obligatoires:\n  - ville\n", encoding="utf-8")

    assert controler(fichier, config, sortie) == CODE_ANOMALIES
    anomalies = lire_anomalies(sortie)
    assert [(a["ligne"], a["colonne"], a["type"]) for a in anomalies] == [
        ("1", "ville", "colonne_absente")
    ]
