# csv-controle

Contrôle qualité d'un export CSV avant intégration : doublons exacts,
quasi-doublons (fautes de frappe), champs obligatoires non renseignés, lignes
mal formées. L'outil ne modifie jamais le fichier d'entrée : il produit un
rapport lisible (`rapport.md`) et la liste des anomalies (`anomalies.csv`,
ouvrable directement dans Excel en français).

## Installation et utilisation

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m csv_controle data/missions_test.csv --config regles.yaml --sortie rapport/
```

Le jeu de démonstration contient des anomalies volontaires : la commande
ci-dessus se termine donc avec le **code de sortie 1, c'est normal**.

Pour régénérer le jeu de test (graine fixe, résultat identique à chaque fois) :

```bash
python data/generer_jeu_test.py
```

Un rapport déjà généré est consultable sans rien exécuter dans `exemple/`
(`exemple/rapport.md` et `exemple/anomalies.csv`).

## Les règles : regles.yaml

```yaml
colonnes_obligatoires:   # doivent être renseignées sur chaque ligne
  - id_mission
  - benevole_nom
  - email
  - date_debut

colonnes_cles:           # définissent un doublon exact (comparaison combinée)
  - email
  - date_debut

valeurs_manquantes:      # considérées comme « non renseigné »
  - ""
  - "N/A"
  - "n/a"
  - "null"
  - "-"

quasi_doublons:
  actif: true            # false désactive complètement cette recherche
  seuil: 90              # score de similarité minimal, de 0 à 100
  champs:                # textes comparés, concaténés
    - benevole_nom
    - email
  champ_blocage: date_debut   # seules les lignes de même valeur sont comparées
```

Points à connaître :

- Avant toute comparaison, les valeurs sont normalisées : minuscules, accents
  retirés, espaces multiples réduits. « Jéan  DUPONT » et « jean dupont » sont
  donc identiques pour l'outil.
- Une ligne dont une colonne clé est vide (ou vaut `N/A`) est **exclue** de la
  détection des doublons : deux emails vides ne sont pas un doublon.
- Toute colonne citée dans `regles.yaml` mais absente de l'en-tête du fichier
  est signalée une seule fois, en ligne 1, avec le type `colonne_absente`.
- Les numéros de ligne sont ceux du fichier (en-tête = ligne 1), y compris
  quand un champ entre guillemets court sur plusieurs lignes.

## Extrait du rapport

```markdown
- Lignes lues (hors en-tête) : 200
- Lignes mal formées : 2
- Doublons exacts : 6 groupe(s)
- Quasi-doublons à vérifier : 5 paire(s)
- Anomalies au total : 20

## Champs manquants

| Colonne | Lignes concernées |
| --- | --- |
| benevole_nom | 4 |
| email | 3 |

## Quasi-doublons à vérifier

| Lignes | Score | Valeurs comparées |
| --- | --- | --- |
| 6 et 24 | 98 | hugo fontaine hugo.fontaine@example.org / hugo fonntaine hugo.fonntaine@example.org |

## Lignes mal formées

- Ligne 149 : 8 colonne(s) au lieu de 9
- Ligne 176 : 10 colonne(s) au lieu de 9
```

Et dans `anomalies.csv` (une ligne par anomalie, séparateur `;`) :

```csv
ligne;colonne;type;detail
24;;quasi_doublon;ressemble à la ligne 6 (score 98)
33;benevole_nom;champ_manquant;colonne obligatoire benevole_nom non renseignée
99;;doublon_exact;identique à la ligne 27
149;;ligne_malformee;8 colonne(s) au lieu de 9
```

## Codes de sortie

| Code | Signification |
| --- | --- |
| 0 | aucune anomalie détectée |
| 1 | anomalies détectées (cas du jeu de démonstration) |
| 2 | erreur : fichier introuvable, ou `regles.yaml` invalide |

## Limites connues

- **Formats de date non contrôlés** : une date est traitée comme du texte. Ni
  la validité (`2026-02-31`), ni la cohérence `date_debut` / `date_fin`, ni
  l'homogénéité des formats ne sont vérifiées. À définir selon les vrais
  exports du client.
- **Colonne clé absente = détection désactivée, mais signalée** : si une
  colonne de `colonnes_cles` manque dans le fichier, les doublons exacts ne
  sont pas recherchés (comparer sur une partie de la clé rapprocherait des
  lignes à tort). L'absence apparaît dans le rapport en type
  `colonne_absente`.
- **Blocage par date exacte pour les quasi-doublons** : deux lignes ne sont
  comparées que si leur `champ_blocage` est strictement identique après
  normalisation. Une même mission saisie au 05/01 et au 06/01 ne sera donc pas
  rapprochée. C'est ce qui garde le temps de calcul raisonnable ; un blocage
  plus souple (semaine, mois) serait à ajouter si besoin.
- **Pas de contrôle sémantique** : ni format d'email, ni liste de valeurs
  autorisées pour `statut`, ni cohérence `ville` / `association`.
- Le seuil de similarité (90 par défaut) reste à calibrer sur de vraies
  données : trop bas, il produit du bruit ; trop haut, il laisse passer des
  coquilles.

## Tests

```bash
python -m pytest
```

---

Prototype de démonstration sur données fictives. © Juan Roussille, tous droits
réservés.
