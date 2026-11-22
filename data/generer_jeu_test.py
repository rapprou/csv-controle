"""Génère un export de missions FICTIF avec des anomalies injectées.

Toutes les données sont inventées (domaine example.org). La graine est fixe :
le fichier produit est identique d'une exécution à l'autre, et les nombres
d'anomalies injectées sont exportés comme constantes pour les tests.
"""

import csv
import random
import unicodedata
from datetime import date, timedelta
from itertools import product
from pathlib import Path

#: Graine fixe : jeu de test reproductible.
GRAINE = 2026

#: Nombres injectés volontairement, comparés au rapport par les tests.
N_LIGNES_BASE = 187
N_DOUBLONS_EXACTS = 6
N_QUASI_DOUBLONS = 5
N_CHAMPS_VIDES = 4
N_VALEURS_NA = 3
N_CHAMPS_MANQUANTS = N_CHAMPS_VIDES + N_VALEURS_NA
N_ESPACES_PARASITES = 5
N_LIGNES_MALFORMEES = 2
N_LIGNES_TOTAL = (
    N_LIGNES_BASE + N_DOUBLONS_EXACTS + N_QUASI_DOUBLONS + N_LIGNES_MALFORMEES
)

COLONNES = (
    "id_mission",
    "titre",
    "benevole_nom",
    "email",
    "association",
    "ville",
    "date_debut",
    "date_fin",
    "statut",
)

CHEMIN_DEFAUT = Path(__file__).parent / "missions_test.csv"
SEPARATEUR = ";"

#: Prénoms et noms fictifs, sans variante accentuée d'un même nom, pour que
#: deux bénévoles différents ne puissent pas produire le même email.
PRENOMS = (
    "Élodie", "Thérèse", "Jean", "Marie", "Noé", "Sophie", "Karim", "Lucie",
    "Pierre", "Amina", "Gaël", "Chloé", "Hugo", "Fatou", "Vincent", "Léa",
    "Olivier", "Nadia", "Bastien", "Clara",
)
NOMS = (
    "Dupont", "Berger", "Lemoine", "Vasseur", "Noël", "Granger", "Mercier",
    "Fontaine", "Rousseau", "Bachelet", "Oliveira", "Marchand", "Thibault",
    "Gaudin", "Lefranc", "Ponceau", "Quentin", "Sauvage", "Valois", "Chastain",
)
TITRES = (
    "Collecte alimentaire",
    "Maraude de soirée",
    "Atelier lecture",
    "Accompagnement numérique",
    "Distribution de repas",
    "Soutien scolaire",
    "Permanence d'accueil",
    "Friperie solidaire",
)
ASSOCIATIONS = (
    "Les Jardins Partagés",
    "Entraide du Quartier",
    "Solidarité Ouest",
    "Horizon Bénévole",
    "Le Fil Rouge",
)
VILLES = ("Nantes", "Orléans", "Nîmes", "Rennes", "Saint-Étienne", "Amiens", "Brest")
STATUTS = ("prévu", "en cours", "terminé", "annulé")

#: Les dates de début se répartissent sur 20 lundis à partir de cette date.
PREMIER_LUNDI = date(2026, 1, 5)
N_DATES = 20

#: Deux lignes au mauvais nombre de colonnes : une en trop, une en moins.
#: Leurs bénévoles n'existent pas ailleurs, pour ne créer aucun doublon.
LIGNES_MALFORMEES = (
    [
        "M9001",
        "Collecte alimentaire",
        "Yann Delorme",
        "yann.delorme@example.org",
        "Le Fil Rouge",
        "Brest",
        "2026-02-02",
        "2026-02-04",
        "terminé",
        "commentaire ajouté par erreur",
    ],
    [
        "M9002",
        "Atelier lecture",
        "Rose Bonnefoy",
        "rose.bonnefoy@example.org",
        "Entraide du Quartier",
        "Amiens",
        "2026-03-02",
        "2026-03-04",
    ],
)


def email_de(prenom: str, nom: str) -> str:
    """Construit l'email fictif d'un bénévole, sans accent."""
    # Le script reste autonome (exécutable depuis n'importe quel dossier) :
    # il ne dépend pas du paquet csv_controle.
    decompose = unicodedata.normalize("NFKD", f"{prenom}.{nom}")
    identifiant = "".join(c for c in decompose if not unicodedata.combining(c))
    return f"{identifiant.lower().replace(' ', '-')}@example.org"


def generer(chemin: Path = CHEMIN_DEFAUT) -> Path:
    """Écrit le jeu de test et renvoie son chemin."""
    tirage = random.Random(GRAINE)
    lignes = _lignes_de_base(tirage)
    _injecter(lignes, tirage)
    tirage.shuffle(lignes)
    enregistrements = [[ligne[colonne] for colonne in COLONNES] for ligne in lignes]
    _injecter_lignes_malformees(enregistrements, tirage)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", encoding="utf-8", newline="") as flux:
        graveur = csv.writer(flux, delimiter=SEPARATEUR)
        graveur.writerow(COLONNES)
        graveur.writerows(enregistrements)
    return chemin


def _lignes_de_base(tirage: random.Random) -> list[dict[str, str]]:
    """Construit des missions saines, aux identités toutes distinctes."""
    identites = tirage.sample(list(product(PRENOMS, NOMS)), N_LIGNES_BASE)
    lignes = []
    for rang, (prenom, nom) in enumerate(identites, start=1):
        debut = PREMIER_LUNDI + timedelta(weeks=tirage.randrange(N_DATES))
        fin = debut + timedelta(days=tirage.randint(1, 5))
        lignes.append(
            {
                "id_mission": f"M{rang:04d}",
                "titre": tirage.choice(TITRES),
                "benevole_nom": f"{prenom} {nom}",
                "email": email_de(prenom, nom),
                "association": tirage.choice(ASSOCIATIONS),
                "ville": tirage.choice(VILLES),
                "date_debut": debut.isoformat(),
                "date_fin": fin.isoformat(),
                "statut": tirage.choice(STATUTS),
            }
        )
    return lignes


def _injecter(lignes: list[dict[str, str]], tirage: random.Random) -> None:
    """Injecte doublons, quasi-doublons, champs manquants et espaces parasites."""
    besoin = (
        N_DOUBLONS_EXACTS
        + N_QUASI_DOUBLONS
        + N_CHAMPS_VIDES
        + N_VALEURS_NA
        + N_ESPACES_PARASITES
    )
    cibles = iter(tirage.sample(range(len(lignes)), besoin))
    suivant = _compteur_identifiants()
    copies = [
        _copie_doublon(lignes[next(cibles)], next(suivant), rang)
        for rang in range(N_DOUBLONS_EXACTS)
    ]
    copies += [
        _copie_quasi(lignes[next(cibles)], next(suivant))
        for _ in range(N_QUASI_DOUBLONS)
    ]
    for _ in range(N_CHAMPS_VIDES):
        lignes[next(cibles)]["benevole_nom"] = ""
    for _ in range(N_VALEURS_NA):
        lignes[next(cibles)]["email"] = "N/A"
    for _ in range(N_ESPACES_PARASITES):
        ligne = lignes[next(cibles)]
        ligne["benevole_nom"] = f"  {ligne['benevole_nom'].replace(' ', '  ')} "
        ligne["ville"] = f" {ligne['ville']} "
    lignes.extend(copies)


def _injecter_lignes_malformees(
    enregistrements: list[list[str]], tirage: random.Random
) -> None:
    """Insère les lignes mal formées à des positions tirées au hasard."""
    positions = sorted(
        tirage.sample(range(len(enregistrements)), N_LIGNES_MALFORMEES), reverse=True
    )
    for position, ligne in zip(positions, LIGNES_MALFORMEES):
        enregistrements.insert(position, list(ligne))


def _compteur_identifiants():
    """Fournit des identifiants de mission uniques pour les lignes ajoutées."""
    return (f"M{rang:04d}" for rang in range(N_LIGNES_BASE + 1, N_LIGNES_TOTAL + 1))


def _copie_doublon(ligne: dict[str, str], identifiant: str, rang: int) -> dict[str, str]:
    """Duplique une ligne à l'identique, ou avec une mise en forme différente.

    Un doublon sur deux change de casse, d'accents et d'espaces : il reste un
    doublon exact après normalisation, ce que le rapport doit montrer.
    """
    copie = dict(ligne, id_mission=identifiant)
    if rang % 2:
        copie["email"] = f" {ligne['email'].upper()} "
        copie["benevole_nom"] = ligne["benevole_nom"].replace("e", "é")
    return copie


def _copie_quasi(ligne: dict[str, str], identifiant: str) -> dict[str, str]:
    """Duplique une ligne avec une faute de frappe sur le nom et l'email."""
    prenom, nom = ligne["benevole_nom"].split(" ", 1)
    return dict(
        ligne,
        id_mission=identifiant,
        benevole_nom=f"{prenom} {_coquille(nom)}",
        email=email_de(prenom, _coquille(nom)),
    )


def _coquille(nom: str) -> str:
    """Double la troisième lettre du nom, comme une faute de saisie."""
    return nom[:3] + nom[2] + nom[3:]


if __name__ == "__main__":
    print(f"Jeu de test écrit dans {generer()}")
