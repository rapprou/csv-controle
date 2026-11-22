"""Structures de données partagées par tous les contrôles."""

from dataclasses import dataclass, field


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
