"""Normalisation des valeurs avant comparaison."""

import re
import unicodedata

_ESPACES = re.compile(r"\s+")


def sans_accents(valeur: str) -> str:
    """Retire les accents en gardant les lettres de base."""
    decompose = unicodedata.normalize("NFKD", valeur)
    return "".join(c for c in decompose if not unicodedata.combining(c))


def normaliser(valeur: str) -> str:
    """Minuscule, sans accents, espaces multiples réduits et bords nettoyés."""
    return _ESPACES.sub(" ", sans_accents(valeur)).strip().casefold()


def cle_comparaison(valeurs: list[str]) -> tuple[str, ...]:
    """Construit la clé normalisée d'une ligne à partir de ses valeurs clés."""
    return tuple(normaliser(valeur) for valeur in valeurs)
