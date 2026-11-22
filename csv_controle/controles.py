"""Contrôles qualité appliqués aux lignes lues."""

import logging
from collections import defaultdict

from csv_controle.modeles import (
    Anomalie,
    GroupeDoublons,
    Lecture,
    Ligne,
    Regles,
)
from csv_controle.normalisation import cle_comparaison

logger = logging.getLogger(__name__)

TYPE_CHAMP_MANQUANT = "champ_manquant"
TYPE_COLONNE_ABSENTE = "colonne_absente"
TYPE_DOUBLON_EXACT = "doublon_exact"

#: L'en-tête occupe la première ligne du fichier.
LIGNE_ENTETE = 1


def est_manquante(valeur: str, valeurs_manquantes: tuple[str, ...]) -> bool:
    """Indique si une valeur est vide, blanche ou l'un des marqueurs configurés."""
    nettoyee = valeur.strip().casefold()
    return nettoyee in {marqueur.strip().casefold() for marqueur in valeurs_manquantes}


def controler_colonnes(lecture: Lecture, regles: Regles) -> list[Anomalie]:
    """Signale une fois chaque colonne citée par les règles et absente de l'en-tête.

    C'est le seul contrôle qui compare les règles à l'en-tête : les autres
    sautent silencieusement les colonnes qu'ils n'y trouvent pas.
    """
    absentes = [
        colonne for colonne in regles.colonnes_citees() if colonne not in lecture.entetes
    ]
    for colonne in absentes:
        logger.warning("Colonne %r citée dans les règles, absente de l'en-tête", colonne)
    return [
        Anomalie(
            ligne=LIGNE_ENTETE,
            colonne=colonne,
            type=TYPE_COLONNE_ABSENTE,
            valeur="",
            detail=f"colonne {colonne} citée dans les règles, absente de l'en-tête",
        )
        for colonne in absentes
    ]


def controler_champs_manquants(lecture: Lecture, regles: Regles) -> list[Anomalie]:
    """Signale les valeurs non renseignées des colonnes obligatoires présentes."""
    colonnes = _colonnes_presentes(regles.colonnes_obligatoires, lecture)
    anomalies = [
        Anomalie(
            ligne=ligne.numero,
            colonne=colonne,
            type=TYPE_CHAMP_MANQUANT,
            valeur=ligne.valeurs[colonne],
            detail=f"colonne obligatoire {colonne} non renseignée",
        )
        for ligne in lecture.lignes
        for colonne in colonnes
        if est_manquante(ligne.valeurs[colonne], regles.valeurs_manquantes)
    ]
    logger.info("Champs manquants : %d anomalie(s)", len(anomalies))
    return anomalies


def controler_doublons_exacts(lecture: Lecture, regles: Regles) -> list[GroupeDoublons]:
    """Regroupe les lignes identiques sur les colonnes clés, après normalisation."""
    colonnes = _colonnes_presentes(regles.colonnes_cles, lecture)
    if not colonnes:
        logger.info("Aucune colonne clé exploitable : doublons exacts non recherchés")
        return []
    groupes: dict[tuple[str, ...], list[int]] = defaultdict(list)
    for ligne in lecture.lignes:
        if _valeurs_incompletes(ligne, colonnes, regles):
            continue  # deux clés vides ne font pas un doublon
        groupes[cle_comparaison([ligne.valeurs[c] for c in colonnes])].append(
            ligne.numero
        )
    doublons = [
        GroupeDoublons(cle=cle, lignes=tuple(numeros))
        for cle, numeros in groupes.items()
        if len(numeros) > 1
    ]
    logger.info(
        "Doublons exacts : %d groupe(s) sur %s", len(doublons), " + ".join(colonnes)
    )
    return doublons


def anomalies_doublons_exacts(groupes: list[GroupeDoublons]) -> list[Anomalie]:
    """Traduit les groupes de doublons en anomalies, hors première occurrence."""
    return [
        Anomalie(
            ligne=numero,
            colonne="",
            type=TYPE_DOUBLON_EXACT,
            valeur=" | ".join(groupe.cle),
            detail=f"identique à la ligne {groupe.premiere_occurrence}",
        )
        for groupe in groupes
        for numero in groupe.lignes[1:]
    ]


def _colonnes_presentes(colonnes: tuple[str, ...], lecture: Lecture) -> list[str]:
    """Garde les colonnes effectivement présentes dans l'en-tête."""
    return [colonne for colonne in colonnes if colonne in lecture.entetes]


def _valeurs_incompletes(ligne: Ligne, colonnes: list[str], regles: Regles) -> bool:
    """Indique si l'une des colonnes citées de la ligne n'est pas renseignée."""
    return any(
        est_manquante(ligne.valeurs[colonne], regles.valeurs_manquantes)
        for colonne in colonnes
    )
