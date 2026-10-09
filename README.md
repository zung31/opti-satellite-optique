# Plan d'acquisition d'un satellite SPOT sous probabilités imprécises

Étude de cas du cours *IA et Décision* (M2 Informatique, Toulouse). Chaque jour, on choisit
quelles images le satellite SPOT5 prendra le lendemain, et avec quel instrument, pour
maximiser le gain. Deux sources d'incertitude interviennent :

- le **nuage** sur chaque image, dont la probabilité n'est connue que par un intervalle
  `[ProbaInf, ProbaSup]` ;
- la **panne** de chaque instrument (`Failure`).

Le problème est modélisé en programmation linéaire mixte (MILP) et résolu avec SCIP via
`pyscipopt`.

## Contenu

| Fichier | Rôle |
|---|---|
| `spotProbaPartial.py` | Modèle (contraintes + critères) et programme en ligne de commande |
| `interface_spot.py` | Interface graphique Streamlit pour tester et comparer les plans |
| `analyse_spot.py` | Génère les tables d'analyse utilisées dans le rapport |
| `resultats_analyse.md` | Sortie de `analyse_spot.py` |
| `spotProba1.py` … `spotProba5.py` | Jeux de données fournis (1 à 3 : tests, 4 et 5 : cas à résoudre) |

## Modèle

- **Variables** : `selection[i]` (image i retenue) et `assignedTo[i][j]` (image i sur l'instrument j).
- **Contraintes** : mémoire (`Σ PM·selection ≤ PMmax`), non-chevauchement sur chaque instrument,
  stéréo sur les instruments 1 et 3 uniquement. L'exclusivité est impliquée par le non-chevauchement.
- **Critères** (gain espéré, pondéré par le nuage et les pannes) :

| Critère | Probabilité de nuage utilisée |
|---|---|
| `pessimiste` (par défaut) | `ProbaSup` : pire cas |
| `optimiste` | `ProbaInf` : meilleur cas |
| `hurwicz` | `α·ProbaInf + (1−α)·ProbaSup`, α = coefficient d'optimisme |
| `deterministe` | aucune incertitude : `Σ PA` |

Les instruments 1, 2, 3 de l'énoncé correspondent aux indices 0, 1, 2 dans le code.

## Installation

Python 3.10 ou plus récent. Depuis le dossier du projet :

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate         # Linux / macOS / Git Bash : .venv/Scripts/activate
pip install -r requirements.txt
```

Sous PowerShell, si l'activation est refusée (« running scripts is disabled ») :
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Utilisation

### Ligne de commande

```bash
python spotProbaPartial.py spotProba4                            # critère pessimiste
python spotProbaPartial.py spotProba5 --critere optimiste
python spotProbaPartial.py spotProba5 --critere hurwicz --alpha 0.3
python spotProbaPartial.py spotProba5 --diagnostic               # pourquoi chaque image est écartée
```

Le jeu peut être donné par son nom (`spotProba4`) ou par un chemin vers un fichier `.py`
au même format. Le problème linéaire est aussi écrit dans `pb.cip`, dans le dossier temporaire
du système (SCIP ne gère pas les accents du chemin du projet sous Windows).

### Interface graphique

```bash
streamlit run interface_spot.py
```

L'interface s'ouvre dans le navigateur. Elle permet de :

- charger un jeu `spotProba1` à `spotProba5`, ou importer un fichier `.py` / `.json` ;
- modifier les données dans un tableau, y compris `ProbaInf`, `ProbaSup` et `Failure` ;
- choisir le critère (et α), lancer la résolution et voir le planning (Gantt) ;
- comparer les plans pessimiste, optimiste, Hurwicz et déterministe ;
- diagnostiquer les images écartées : mémoire, chevauchement ou risque.

### Analyse pour le rapport

```bash
python analyse_spot.py > resultats_analyse.md
```

Le script produit : validation sur les jeux de test, plans de spotProba4 et spotProba5, écart
entre plans pessimiste et optimiste, déformation du plan entre spotProba4 et spotProba5,
images écartées avec leur raison, et sensibilité au coefficient α. À relancer après toute
modification du modèle.

## Validation

Valeurs de référence de l'énoncé, toutes retrouvées avec le critère pessimiste :

| Jeu | Attendu |
|---|---|
| spotProba1 / 2 / 3 | 70 / 60 / 60 |
| spotProba1, nuage précis 0.1 | 63 |
| spotProba1, nuage imprécis [0.1, 0.3] | 49 |
| spotProba1, nadir en panne | 60 |
| spotProba1, tout combiné | 14.661 |

## Crédits

Sujet : N. Ben Amor, d'après l'étude de cas de H. Fargier, M. Lemaître et G. Verfaillie.
Programme de départ (`spotProbaPartial.py`) : H. Fargier.
