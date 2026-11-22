"""Tests de la normalisation des valeurs."""

from csv_controle.normalisation import cle_comparaison, normaliser, sans_accents


def test_sans_accents() -> None:
    """Les accents sont retirés, les lettres conservées."""
    assert sans_accents("Thérèse Noël") == "Therese Noel"


def test_normaliser_casse_et_espaces() -> None:
    """Casse, espaces de bord et espaces multiples sont neutralisés."""
    assert normaliser("  Jean   DUPONT ") == "jean dupont"


def test_normaliser_accents_et_casse() -> None:
    """La normalisation combine accents, casse et espaces."""
    assert normaliser("ÉLODIE  Müller") == normaliser("elodie muller")


def test_cle_comparaison() -> None:
    """La clé est un tuple de valeurs normalisées, dans l'ordre reçu."""
    assert cle_comparaison(["A@Example.ORG", " 2026-01-05 "]) == (
        "a@example.org",
        "2026-01-05",
    )
