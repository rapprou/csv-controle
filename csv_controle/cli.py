"""Point d'entrée en ligne de commande."""

import argparse
import logging
from pathlib import Path

from csv_controle.controles import (
    anomalies_doublons_exacts,
    anomalies_quasi_doublons,
    controler_champs_manquants,
    controler_colonnes,
    controler_doublons_exacts,
    controler_quasi_doublons,
)
from csv_controle.lecture import lire_csv
from csv_controle.modeles import ErreurConfiguration, charger_regles
from csv_controle.rapport import Resultat, ecrire_rapport

logger = logging.getLogger(__name__)

#: Codes de sortie du programme.
CODE_OK = 0
CODE_ANOMALIES = 1
CODE_ERREUR = 2


def construire_analyseur() -> argparse.ArgumentParser:
    """Décrit les arguments acceptés sur la ligne de commande."""
    analyseur = argparse.ArgumentParser(
        prog="python -m csv_controle",
        description="Contrôle la qualité d'un export CSV et produit un rapport.",
    )
    analyseur.add_argument("fichier", type=Path, help="export CSV à contrôler")
    analyseur.add_argument(
        "--config",
        type=Path,
        default=Path("regles.yaml"),
        help="fichier de règles YAML (défaut : regles.yaml)",
    )
    analyseur.add_argument(
        "--sortie",
        type=Path,
        default=Path("rapport"),
        help="dossier où écrire le rapport (défaut : rapport/)",
    )
    return analyseur


def controler(fichier: Path, config: Path, sortie: Path) -> int:
    """Enchaîne lecture, contrôles et rapport, puis renvoie le code de sortie."""
    try:
        regles = charger_regles(config)
        if not fichier.is_file():
            raise FileNotFoundError(f"fichier introuvable : {fichier}")
        lecture = lire_csv(fichier)
    except (ErreurConfiguration, OSError) as erreur:
        logger.error("%s", erreur)
        return CODE_ERREUR

    doublons = controler_doublons_exacts(lecture, regles)
    quasi = controler_quasi_doublons(lecture, regles, doublons)
    resultat = Resultat(
        lecture=lecture,
        doublons_exacts=doublons,
        quasi_doublons=quasi,
        anomalies=[
            *lecture.anomalies,
            *controler_colonnes(lecture, regles),
            *controler_champs_manquants(lecture, regles),
            *anomalies_doublons_exacts(doublons),
            *anomalies_quasi_doublons(quasi),
        ],
    )
    ecrire_rapport(resultat, sortie)
    if resultat.nb_anomalies:
        logger.warning("%d anomalie(s) détectée(s)", resultat.nb_anomalies)
        return CODE_ANOMALIES
    logger.info("Aucune anomalie détectée")
    return CODE_OK


def main(arguments: list[str] | None = None) -> int:
    """Configure la journalisation et lance le contrôle."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    options = construire_analyseur().parse_args(arguments)
    return controler(options.fichier, options.config, options.sortie)
