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
class GroupeDoublons:
    """Un groupe de lignes partageant la même clé normalisée."""

    cle: tuple[str, ...]
    lignes: tuple[int, ...]

    @property
    def premiere_occurrence(self) -> int:
        """Numéro de la première ligne du groupe, celle à conserver."""
        return self.lignes[0]


@dataclass(frozen=True)
class PaireQuasiDoublons:
    """Deux lignes jugées très proches sans être identiques."""

    lignes: tuple[int, int]
    score: int
    texte: str


@dataclass(frozen=True)
class QuasiDoublons:
    """Paramètres de la recherche de quasi-doublons."""

    actif: bool = True
    seuil: int = 90
    champs: tuple[str, ...] = ()
    champ_blocage: str = ""


@dataclass(frozen=True)
class Regles:
    """Règles de contrôle lues dans regles.yaml."""

    colonnes_obligatoires: tuple[str, ...] = ()
    valeurs_manquantes: tuple[str, ...] = VALEURS_MANQUANTES_DEFAUT
    colonnes_cles: tuple[str, ...] = ()
    quasi_doublons: QuasiDoublons = QuasiDoublons()

    def colonnes_citees(self) -> list[str]:
        """Liste sans doublon des colonnes citées par les règles actives."""
        citees = [*self.colonnes_obligatoires, *self.colonnes_cles]
        if self.quasi_doublons.actif:
            citees += [*self.quasi_doublons.champs, self.quasi_doublons.champ_blocage]
        return list(dict.fromkeys(colonne for colonne in citees if colonne))


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
        colonnes_cles=_liste_de_textes(contenu, "colonnes_cles", Regles.colonnes_cles),
        quasi_doublons=_quasi_doublons(contenu.get("quasi_doublons")),
    )


def _quasi_doublons(contenu: object) -> QuasiDoublons:
    """Lit la section quasi_doublons de regles.yaml."""
    defaut = QuasiDoublons()
    if contenu is None:
        return defaut
    if not isinstance(contenu, dict):
        raise ErreurConfiguration("quasi_doublons : un dictionnaire est attendu")
    return QuasiDoublons(
        actif=_booleen(contenu, "actif", defaut.actif),
        seuil=_seuil(contenu, defaut.seuil),
        champs=_liste_de_textes(contenu, "champs", defaut.champs),
        champ_blocage=_texte(contenu, "champ_blocage", defaut.champ_blocage),
    )


def _booleen(contenu: dict, cle: str, defaut: bool) -> bool:
    """Renvoie une valeur booléenne, ou le défaut si la clé est absente."""
    if cle not in contenu or contenu[cle] is None:
        return defaut
    if not isinstance(contenu[cle], bool):
        raise ErreurConfiguration(f"{cle} : true ou false est attendu")
    return contenu[cle]


def _texte(contenu: dict, cle: str, defaut: str) -> str:
    """Renvoie une valeur texte, ou le défaut si la clé est absente."""
    if cle not in contenu or contenu[cle] is None:
        return defaut
    if not isinstance(contenu[cle], str):
        raise ErreurConfiguration(f"{cle} : un nom de colonne est attendu")
    return contenu[cle]


def _seuil(contenu: dict, defaut: int) -> int:
    """Renvoie le seuil de similarité, entier entre 0 et 100."""
    if "seuil" not in contenu or contenu["seuil"] is None:
        return defaut
    seuil = contenu["seuil"]
    if isinstance(seuil, bool) or not isinstance(seuil, (int, float)):
        raise ErreurConfiguration("seuil : un nombre entre 0 et 100 est attendu")
    if not 0 <= seuil <= 100:
        raise ErreurConfiguration("seuil : un nombre entre 0 et 100 est attendu")
    return int(seuil)


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
