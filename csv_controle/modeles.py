"""Structures de données et règles partagées par tous les contrôles."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

#: Valeurs considérées comme manquantes si regles.yaml n'en fournit pas.
VALEURS_MANQUANTES_DEFAUT = ("", "N/A", "n/a", "null", "-")


class ErreurConfiguration(Exception):
    """regles.yaml est illisible ou mal formé."""


@dataclass(frozen=True)
class Anomalie:
    """Une anomalie détectée sur une ligne du CSV."""

    ligne: int
    colonne: str
    type: str
    valeur: str
    detail: str


@dataclass
class Ligne:
    """Une ligne de données exploitable, avec son numéro réel dans le fichier."""

    numero: int
    valeurs: dict[str, str]


@dataclass
class Lecture:
    """Résultat de la lecture d'un fichier CSV."""

    chemin: str
    encodage: str
    separateur: str
    entetes: list[str]
    lignes: list[Ligne] = field(default_factory=list)
    anomalies: list[Anomalie] = field(default_factory=list)
    nb_lignes_lues: int = 0
    nb_lignes_malformees: int = 0


@dataclass(frozen=True)
class Regles:
    """Règles de contrôle lues dans regles.yaml."""

    colonnes_obligatoires: tuple[str, ...] = ()
    valeurs_manquantes: tuple[str, ...] = VALEURS_MANQUANTES_DEFAUT


def charger_regles(chemin: Path) -> Regles:
    """Lit regles.yaml et renvoie les règles de contrôle."""
    try:
        contenu = yaml.safe_load(chemin.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as erreur:
        raise ErreurConfiguration(f"{chemin} illisible : {erreur}") from erreur
    if contenu is None:
        contenu = {}
    if not isinstance(contenu, dict):
        raise ErreurConfiguration(f"{chemin} : un dictionnaire est attendu")
    return Regles(
        colonnes_obligatoires=_liste_de_textes(
            contenu, "colonnes_obligatoires", Regles.colonnes_obligatoires
        ),
        valeurs_manquantes=_liste_de_textes(
            contenu, "valeurs_manquantes", Regles.valeurs_manquantes
        ),
    )


def _liste_de_textes(
    contenu: dict, cle: str, defaut: tuple[str, ...]
) -> tuple[str, ...]:
    """Renvoie la valeur de `cle` sous forme de tuple de chaînes, ou le défaut."""
    if cle not in contenu or contenu[cle] is None:
        return defaut
    valeur = contenu[cle]
    if not isinstance(valeur, list) or not all(
        isinstance(element, (str, int, float)) for element in valeur
    ):
        raise ErreurConfiguration(f"{cle} : une liste de valeurs simples est attendue")
    return tuple(str(element) for element in valeur)
