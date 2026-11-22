"""Tests de la lecture tolérante d'un CSV."""

from pathlib import Path

from csv_controle.lecture import TYPE_LIGNE_MALFORMEE, lire_csv

ENTETE = "id_mission,benevole_nom,email"


def ecrire(chemin: Path, contenu: str, encodage: str = "utf-8") -> Path:
    """Écrit un CSV de test et renvoie son chemin."""
    chemin.write_bytes(contenu.encode(encodage))
    return chemin


def test_lecture_utf8(tmp_path: Path) -> None:
    """Un fichier utf-8 simple est lu avec ses en-têtes et ses valeurs."""
    fichier = ecrire(tmp_path / "simple.csv", f"{ENTETE}\nM1,Dupont,a@example.org\n")

    lecture = lire_csv(fichier)

    assert lecture.encodage == "utf-8-sig"
    assert lecture.separateur == ","
    assert lecture.entetes == ["id_mission", "benevole_nom", "email"]
    assert lecture.nb_lignes_lues == 1
    assert lecture.lignes[0].valeurs["email"] == "a@example.org"
    assert lecture.anomalies == []


def test_lecture_cp1252_avec_accents(tmp_path: Path) -> None:
    """Un fichier cp1252 accentué est décodé sans perte."""
    fichier = ecrire(
        tmp_path / "cp1252.csv",
        f"{ENTETE}\nM1,Thérèse Noël,t@example.org\n",
        encodage="cp1252",
    )

    lecture = lire_csv(fichier)

    assert lecture.encodage == "cp1252"
    assert lecture.lignes[0].valeurs["benevole_nom"] == "Thérèse Noël"


def test_separateur_point_virgule(tmp_path: Path) -> None:
    """Le séparateur est déduit du comptage dans la ligne d'en-tête."""
    fichier = ecrire(
        tmp_path / "pv.csv",
        "id_mission;titre;ville\nM1;Collecte, tri;Nantes\n",
    )

    lecture = lire_csv(fichier)

    assert lecture.separateur == ";"
    assert lecture.lignes[0].valeurs["titre"] == "Collecte, tri"


def test_ligne_malformee_signalee_sans_planter(tmp_path: Path) -> None:
    """Une ligne au mauvais nombre de colonnes devient une anomalie."""
    fichier = ecrire(
        tmp_path / "malformee.csv",
        f"{ENTETE}\nM1,Dupont,a@example.org\nM2,Durand\nM3,Martin,c@example.org\n",
    )

    lecture = lire_csv(fichier)

    assert lecture.nb_lignes_lues == 3
    assert lecture.nb_lignes_malformees == 1
    assert len(lecture.lignes) == 2
    anomalie = lecture.anomalies[0]
    assert anomalie.ligne == 3
    assert anomalie.type == TYPE_LIGNE_MALFORMEE
    assert anomalie.detail == "2 colonne(s) au lieu de 3"


def test_numero_de_ligne_exact_avec_champ_multiligne(tmp_path: Path) -> None:
    """Chaque enregistrement est numéroté par la ligne où il commence."""
    fichier = ecrire(
        tmp_path / "multiligne.csv",
        f'{ENTETE}\nM1,"Dupont\nJean",a@example.org\nM2,Durand,b@example.org\n',
    )

    lecture = lire_csv(fichier)

    # L'enregistrement M1 occupe les lignes 2 et 3, M2 commence donc en 4.
    assert [ligne.numero for ligne in lecture.lignes] == [2, 4]
    assert lecture.lignes[0].valeurs["benevole_nom"] == "Dupont\nJean"
