# Rapport de contrôle qualité

- Fichier contrôlé : `data/missions_test.csv`
- Encodage détecté : utf-8-sig
- Séparateur détecté : `;`
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

## Doublons exacts

| Clé | Lignes | Première occurrence |
| --- | --- | --- |
| fatou.sauvage@example.org + 2026-04-13 | 27, 99 | 27 |
| hugo.dupont@example.org + 2026-04-27 | 47, 140 | 47 |
| hugo.lefranc@example.org + 2026-03-16 | 58, 133 | 58 |
| karim.chastain@example.org + 2026-03-30 | 61, 91 | 61 |
| therese.oliveira@example.org + 2026-01-26 | 68, 105 | 68 |
| hugo.quentin@example.org + 2026-04-20 | 78, 93 | 78 |

## Quasi-doublons à vérifier

| Lignes | Score | Valeurs comparées |
| --- | --- | --- |
| 6 et 24 | 98 | hugo fontaine hugo.fontaine@example.org / hugo fonntaine hugo.fonntaine@example.org |
| 8 et 54 | 98 | bastien mercier bastien.mercier@example.org / bastien merrcier bastien.merrcier@example.org |
| 26 et 172 | 97 | lea quentin lea.quentin@example.org / lea queentin lea.queentin@example.org |
| 113 et 129 | 98 | fatou lemoine fatou.lemoine@example.org / fatou lemmoine fatou.lemmoine@example.org |
| 166 et 196 | 97 | lea merrcier lea.merrcier@example.org / lea mercier lea.mercier@example.org |

## Lignes mal formées

- Ligne 149 : 8 colonne(s) au lieu de 9
- Ligne 176 : 10 colonne(s) au lieu de 9

