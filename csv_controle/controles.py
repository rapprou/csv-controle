"""Contrôles qualité appliqués aux lignes lues."""

import logging
from collections import defaultdict
from itertools import combinations

from rapidfuzz import fuzz

from csv_controle.modeles import (
    Anomalie,
    GroupeDoublons,
    Lecture,
    Ligne,
    PaireQuasiDoublons,
    Regles,
)
from csv_controle.normalisation import cle_comparaison, normaliser

logger = logging.getLogger(__name__)

TYPE_CHAMP_MANQUANT = "champ_manquant"
TYPE_COLONNE_ABSENTE = "colonne_absente"
TYPE_DOUBLON_EXACT = "doublon_exact"
TYPE_QUASI_DOUBLON = "quasi_doublon"

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
    colonnes = list(regles.colonnes_cles)
    # Comparer sur une partie seulement des colonnes clés rapprocherait des
    # lignes à tort : l'absence est déjà signalée par controler_colonnes.
    if not colonnes or _colonnes_presentes(regles.colonnes_cles, lecture) != colonnes:
        logger.info("Colonnes clés incomplètes : doublons exacts non recherchés")
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


def controler_quasi_doublons(
    lecture: Lecture, regles: Regles, groupes_exacts: list[GroupeDoublons]
) -> list[PaireQuasiDoublons]:
    """Compare par similarité les lignes partageant la même valeur de blocage."""
    reglage = regles.quasi_doublons
    if not reglage.actif:
        logger.info("Quasi-doublons désactivés dans les règles")
        return []
    champs = _colonnes_presentes(reglage.champs, lecture)
    blocage = reglage.champ_blocage
    if not champs or blocage not in lecture.entetes:
        logger.info("Colonnes de comparaison incomplètes : quasi-doublons non recherchés")
        return []
    paires = [
        paire
        for bloc in _blocs(_candidats(lecture, regles, groupes_exacts), blocage).values()
        for paire in _paires_proches(bloc, champs, reglage.seuil)
    ]
    logger.info(
        "Quasi-doublons : %d paire(s) au seuil %d sur %s",
        len(paires),
        reglage.seuil,
        " + ".join(champs),
    )
    return paires


def anomalies_quasi_doublons(paires: list[PaireQuasiDoublons]) -> list[Anomalie]:
    """Traduit les paires proches en anomalies portées par la seconde ligne."""
    return [
        Anomalie(
            ligne=paire.lignes[1],
            colonne="",
            type=TYPE_QUASI_DOUBLON,
            valeur=paire.texte,
            detail=f"ressemble à la ligne {paire.lignes[0]} (score {paire.score})",
        )
        for paire in paires
    ]


def _candidats(
    lecture: Lecture, regles: Regles, groupes_exacts: list[GroupeDoublons]
) -> list[Ligne]:
    """Écarte les répétitions déjà signalées comme doublons exacts."""
    repetitions = {
        numero for groupe in groupes_exacts for numero in groupe.lignes[1:]
    }
    return [ligne for ligne in lecture.lignes if ligne.numero not in repetitions]


def _blocs(lignes: list[Ligne], blocage: str) -> dict[str, list[Ligne]]:
    """Regroupe les lignes par valeur normalisée du champ de blocage."""
    blocs: dict[str, list[Ligne]] = defaultdict(list)
    for ligne in lignes:
        valeur = normaliser(ligne.valeurs[blocage])
        if not valeur:
            continue  # sans valeur de blocage, aucune comparaison fiable
        blocs[valeur].append(ligne)
    return blocs


def _paires_proches(
    bloc: list[Ligne], champs: list[str], seuil: int
) -> list[PaireQuasiDoublons]:
    """Compare deux à deux les lignes d'un bloc et garde celles au-dessus du seuil."""
    textes = {ligne.numero: _texte_compare(ligne, champs) for ligne in bloc}
    paires = []
    for gauche, droite in combinations(bloc, 2):
        texte_a, texte_b = textes[gauche.numero], textes[droite.numero]
        if not texte_a or not texte_b or texte_a == texte_b:
            continue  # rien à comparer, ou doublon exact sur ces champs
        score = fuzz.token_sort_ratio(texte_a, texte_b)
        if score >= seuil:
            paires.append(
                PaireQuasiDoublons(
                    lignes=(gauche.numero, droite.numero),
                    score=round(score),
                    texte=f"{texte_a} / {texte_b}",
                )
            )
    return paires


def _texte_compare(ligne: Ligne, champs: list[str]) -> str:
    """Concatène les champs comparés de la ligne, sous forme normalisée."""
    return normaliser(" ".join(ligne.valeurs[champ] for champ in champs))


def _colonnes_presentes(colonnes: tuple[str, ...], lecture: Lecture) -> list[str]:
    """Garde les colonnes effectivement présentes dans l'en-tête."""
    return [colonne for colonne in colonnes if colonne in lecture.entetes]


def _valeurs_incompletes(ligne: Ligne, colonnes: list[str], regles: Regles) -> bool:
    """Indique si l'une des colonnes citées de la ligne n'est pas renseignée."""
    return any(
        est_manquante(ligne.valeurs[colonne], regles.valeurs_manquantes)
        for colonne in colonnes
    )
