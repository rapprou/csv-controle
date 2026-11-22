"""Lecture tolérante d'un CSV : encodage, séparateur, lignes mal formées."""

import csv
import logging
from pathlib import Path
from typing import TextIO

from csv_controle.modeles import Anomalie, Lecture, Ligne

logger = logging.getLogger(__name__)

#: Encodages essayés dans l'ordre ; latin-1 accepte tout octet et sert de secours.
ENCODAGES = ("utf-8-sig", "cp1252", "latin-1")

#: Séparateurs candidats, comptés dans la ligne d'en-tête.
SEPARATEURS = (";", ",")

TYPE_LIGNE_MALFORMEE = "ligne_malformee"


def detecter_encodage(chemin: Path) -> str:
    """Renvoie le premier encodage de ENCODAGES qui décode tout le fichier."""
    octets = chemin.read_bytes()
    for encodage in ENCODAGES:
        try:
            octets.decode(encodage)
        except UnicodeDecodeError:
            continue
        logger.debug("Encodage retenu pour %s : %s", chemin, encodage)
        return encodage
    # latin-1 décode n'importe quel octet : cette ligne n'est atteignable
    # que si ENCODAGES est modifié.
    raise UnicodeDecodeError("csv-controle", octets, 0, 1, "aucun encodage ne convient")


def detecter_separateur(entete: str) -> str:
    """Renvoie le séparateur le plus fréquent dans la ligne d'en-tête."""
    comptes = {sep: entete.count(sep) for sep in SEPARATEURS}
    separateur = max(SEPARATEURS, key=lambda sep: comptes[sep])
    if comptes[separateur] == 0:
        logger.warning("Aucun séparateur détecté dans l'en-tête, %r par défaut", separateur)
    return separateur


def lire_csv(chemin: Path) -> Lecture:
    """Lit un CSV et renvoie ses lignes valides et ses lignes mal formées."""
    encodage = detecter_encodage(chemin)
    with chemin.open("r", encoding=encodage, newline="") as flux:
        premiere_ligne = flux.readline()
        separateur = detecter_separateur(premiere_ligne)
        flux.seek(0)
        return _lire_flux(flux, chemin, encodage, separateur)


def _lire_flux(flux: TextIO, chemin: Path, encodage: str, separateur: str) -> Lecture:
    """Parcourt le flux déjà ouvert et construit le résultat de lecture."""
    lecteur = csv.reader(flux, delimiter=separateur)
    try:
        entetes = [colonne.strip() for colonne in next(lecteur)]
    except StopIteration:
        entetes = []
    lecture = Lecture(
        chemin=str(chemin),
        encodage=encodage,
        separateur=separateur,
        entetes=entetes,
    )
    debut = lecteur.line_num + 1
    for champs in lecteur:
        # line_num est la dernière ligne physique consommée : avant de traiter
        # l'enregistrement courant, on en déduit la ligne où il commence.
        numero = debut
        debut = lecteur.line_num + 1
        if not champs:
            continue  # ligne vide en fin de fichier
        lecture.nb_lignes_lues += 1
        if len(champs) != len(entetes):
            lecture.nb_lignes_malformees += 1
            lecture.anomalies.append(_anomalie_malformee(numero, champs, len(entetes)))
            continue
        lecture.lignes.append(Ligne(numero=numero, valeurs=dict(zip(entetes, champs))))
    logger.info(
        "%s : %d ligne(s) lue(s), %d mal formée(s), encodage %s, séparateur %r",
        chemin,
        lecture.nb_lignes_lues,
        lecture.nb_lignes_malformees,
        encodage,
        separateur,
    )
    return lecture


def _anomalie_malformee(numero: int, champs: list[str], attendu: int) -> Anomalie:
    """Construit l'anomalie décrivant une ligne au mauvais nombre de colonnes."""
    return Anomalie(
        ligne=numero,
        colonne="",
        type=TYPE_LIGNE_MALFORMEE,
        valeur="",
        detail=f"{len(champs)} colonne(s) au lieu de {attendu}",
    )
