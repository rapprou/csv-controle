"""Écriture du rapport Markdown et du fichier d'anomalies."""

import csv
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from csv_controle.controles import TYPE_CHAMP_MANQUANT
from csv_controle.modeles import Anomalie, GroupeDoublons, Lecture, PaireQuasiDoublons

logger = logging.getLogger(__name__)

NOM_RAPPORT = "rapport.md"
NOM_ANOMALIES = "anomalies.csv"

#: Excel en français attend un point-virgule et un BOM utf-8.
ENCODAGE_EXCEL = "utf-8-sig"
SEPARATEUR_EXCEL = ";"

ENTETES_ANOMALIES = ("ligne", "colonne", "type", "detail")


@dataclass
class Resultat:
    """Tout ce qu'un contrôle complet produit, prêt à être rapporté."""

    lecture: Lecture
    doublons_exacts: list[GroupeDoublons] = field(default_factory=list)
    quasi_doublons: list[PaireQuasiDoublons] = field(default_factory=list)
    anomalies: list[Anomalie] = field(default_factory=list)

    @property
    def nb_anomalies(self) -> int:
        """Nombre total d'anomalies, lignes mal formées comprises."""
        return len(self.anomalies)


def ecrire_rapport(resultat: Resultat, dossier: Path) -> tuple[Path, Path]:
    """Écrit rapport.md et anomalies.csv dans le dossier de sortie."""
    dossier.mkdir(parents=True, exist_ok=True)
    chemin_md = dossier / NOM_RAPPORT
    chemin_csv = dossier / NOM_ANOMALIES
    chemin_md.write_text(_markdown(resultat), encoding="utf-8")
    _ecrire_anomalies(resultat.anomalies, chemin_csv)
    logger.info("Rapport écrit dans %s et %s", chemin_md, chemin_csv)
    return chemin_md, chemin_csv


def _ecrire_anomalies(anomalies: list[Anomalie], chemin: Path) -> None:
    """Écrit une ligne par anomalie, au format lisible par Excel FR."""
    with chemin.open("w", encoding=ENCODAGE_EXCEL, newline="") as flux:
        graveur = csv.writer(flux, delimiter=SEPARATEUR_EXCEL)
        graveur.writerow(ENTETES_ANOMALIES)
        for anomalie in sorted(anomalies, key=lambda a: (a.ligne, a.colonne, a.type)):
            graveur.writerow(
                [anomalie.ligne, anomalie.colonne, anomalie.type, anomalie.detail]
            )


def _markdown(resultat: Resultat) -> str:
    """Compose le rapport Markdown."""
    lecture = resultat.lecture
    lignes = [
        "# Rapport de contrôle qualité",
        "",
        f"- Fichier contrôlé : `{lecture.chemin}`",
        f"- Encodage détecté : {lecture.encodage}",
        f"- Séparateur détecté : `{lecture.separateur}`",
        f"- Lignes lues (hors en-tête) : {lecture.nb_lignes_lues}",
        f"- Lignes mal formées : {lecture.nb_lignes_malformees}",
        f"- Doublons exacts : {len(resultat.doublons_exacts)} groupe(s)",
        f"- Quasi-doublons à vérifier : {len(resultat.quasi_doublons)} paire(s)",
        f"- Anomalies au total : {resultat.nb_anomalies}",
        "",
        *_section_champs_manquants(resultat.anomalies),
        *_section_doublons_exacts(resultat.doublons_exacts),
        *_section_quasi_doublons(resultat.quasi_doublons),
        *_section_lignes_malformees(lecture),
    ]
    return "\n".join(lignes) + "\n"


def _section_champs_manquants(anomalies: list[Anomalie]) -> list[str]:
    """Tableau du nombre de champs manquants par colonne."""
    comptes = Counter(
        anomalie.colonne for anomalie in anomalies if anomalie.type == TYPE_CHAMP_MANQUANT
    )
    if not comptes:
        return ["## Champs manquants", "", "Aucun champ obligatoire non renseigné.", ""]
    return [
        "## Champs manquants",
        "",
        "| Colonne | Lignes concernées |",
        "| --- | --- |",
        *(f"| {colonne} | {compte} |" for colonne, compte in sorted(comptes.items())),
        "",
    ]


def _section_doublons_exacts(groupes: list[GroupeDoublons]) -> list[str]:
    """Tableau des groupes de doublons exacts."""
    if not groupes:
        return ["## Doublons exacts", "", "Aucun doublon exact.", ""]
    return [
        "## Doublons exacts",
        "",
        "| Clé | Lignes | Première occurrence |",
        "| --- | --- | --- |",
        *(
            # La clé est jointe sans « | » pour ne pas casser le tableau.
            f"| {' + '.join(groupe.cle)} | "
            f"{', '.join(str(n) for n in groupe.lignes)} | "
            f"{groupe.premiere_occurrence} |"
            for groupe in sorted(groupes, key=lambda g: g.premiere_occurrence)
        ),
        "",
    ]


def _section_quasi_doublons(paires: list[PaireQuasiDoublons]) -> list[str]:
    """Tableau des paires proches à vérifier à la main."""
    if not paires:
        return ["## Quasi-doublons à vérifier", "", "Aucun quasi-doublon.", ""]
    return [
        "## Quasi-doublons à vérifier",
        "",
        "| Lignes | Score | Valeurs comparées |",
        "| --- | --- | --- |",
        *(
            f"| {paire.lignes[0]} et {paire.lignes[1]} | {paire.score} | {paire.texte} |"
            for paire in sorted(paires, key=lambda p: p.lignes)
        ),
        "",
    ]


def _section_lignes_malformees(lecture: Lecture) -> list[str]:
    """Liste des lignes au mauvais nombre de colonnes."""
    if not lecture.anomalies:
        return ["## Lignes mal formées", "", "Aucune ligne mal formée.", ""]
    return [
        "## Lignes mal formées",
        "",
        *(
            f"- Ligne {anomalie.ligne} : {anomalie.detail}"
            for anomalie in lecture.anomalies
        ),
        "",
    ]
