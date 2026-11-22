"""Contrôles qualité appliqués aux lignes lues."""

import logging

from csv_controle.modeles import Anomalie, Lecture, Regles

logger = logging.getLogger(__name__)

TYPE_CHAMP_MANQUANT = "champ_manquant"
TYPE_COLONNE_ABSENTE = "colonne_absente"

#: L'en-tête occupe la première ligne du fichier.
LIGNE_ENTETE = 1


def est_manquante(valeur: str, valeurs_manquantes: tuple[str, ...]) -> bool:
    """Indique si une valeur est vide, blanche ou l'un des marqueurs configurés."""
    nettoyee = valeur.strip().casefold()
    return nettoyee in {marqueur.strip().casefold() for marqueur in valeurs_manquantes}


def controler_champs_manquants(lecture: Lecture, regles: Regles) -> list[Anomalie]:
    """Signale les colonnes obligatoires absentes puis les valeurs non renseignées."""
    presentes = [
        colonne for colonne in regles.colonnes_obligatoires if colonne in lecture.entetes
    ]
    anomalies = [
        _anomalie_colonne_absente(colonne)
        for colonne in regles.colonnes_obligatoires
        if colonne not in lecture.entetes
    ]
    anomalies += [
        Anomalie(
            ligne=ligne.numero,
            colonne=colonne,
            type=TYPE_CHAMP_MANQUANT,
            valeur=ligne.valeurs[colonne],
            detail=f"colonne obligatoire {colonne} non renseignée",
        )
        for ligne in lecture.lignes
        for colonne in presentes
        if est_manquante(ligne.valeurs[colonne], regles.valeurs_manquantes)
    ]
    logger.info("Champs manquants : %d anomalie(s)", len(anomalies))
    return anomalies


def _anomalie_colonne_absente(colonne: str) -> Anomalie:
    """Construit l'anomalie d'une colonne obligatoire absente de l'en-tête."""
    logger.warning("Colonne obligatoire %r absente de l'en-tête", colonne)
    return Anomalie(
        ligne=LIGNE_ENTETE,
        colonne=colonne,
        type=TYPE_COLONNE_ABSENTE,
        valeur="",
        detail=f"colonne obligatoire {colonne} absente de l'en-tête du fichier",
    )
