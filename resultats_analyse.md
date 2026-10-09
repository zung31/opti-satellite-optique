# Résultats de l'analyse (généré par analyse_spot.py)

## 1. Validation sur les jeux de test

| jeu | attendu | obtenu (pessimiste) |  |
|---|---|---|---|
| spotProba1 | 70 | 70.0 | ✅ |
| spotProba2 | 60 | 60.0 | ✅ |
| spotProba3 | 60 | 60.0 | ✅ |
| spotProba1, nuage précis 0.1 | 63 | 63.0 | ✅ |
| spotProba1, nuage [0.1, 0.3] | 49 | 49.0 | ✅ |
| spotProba1, nadir en panne | 60 | 60.0 | ✅ |
| spotProba1, tout combiné | 14.661 | 14.661 | ✅ | 

## 2. Plans de spotProba4 et spotProba5

### spotProba4

20 images (6 stéréo), PMmax = 150, Failure = [0, 0, 0]

| plan (critère) | objectif | valeur pess. | valeur opt. | Σ PA | images | stéréo | usage instr. 1/2/3 | mémoire |
|---|---|---|---|---|---|---|---|---|
| pessimiste | 333.0 | 333.0 | 370.0 | 370 | 14/20 | 0 | 7 / 6 / 1 | 140/150 |
| optimiste | 400.0 | 324.0 | 400.0 | 400 | 13/20 | 2 | 7 / 6 / 2 | 150/150 |
| hurwicz α=0.5 | 362.0 | 324.0 | 400.0 | 400 | 13/20 | 2 | 7 / 6 / 2 | 150/150 |
| deterministe | 400.0 | 324.0 | 400.0 | 400 | 13/20 | 2 | 3 / 5 / 7 | 150/150 | 

Plan pessimiste : img0→1, img2→1, img4→0, img5→1, img6→0, img8→0, img9→1, img10→2, img12→0, img14→0, img15→1, img16→0, img18→1, img19→0

### spotProba5

40 images (14 stéréo), PMmax = 300, Failure = [0.001, 0.001, 0.7]

| plan (critère) | objectif | valeur pess. | valeur opt. | Σ PA | images | stéréo | usage instr. 1/2/3 | mémoire |
|---|---|---|---|---|---|---|---|---|
| pessimiste | 553.6458 | 553.6458 | 678.1212 | 840 | 27/40 | 3 | 15 / 12 / 3 | 300/300 |
| optimiste | 678.1212 | 551.8476 | 678.1212 | 860 | 27/40 | 3 | 16 / 11 / 3 | 300/300 |
| hurwicz α=0.5 | 615.8835 | 553.6458 | 678.1212 | 840 | 27/40 | 3 | 15 / 12 / 3 | 300/300 |
| deterministe | 890.0 | 309.3873 | 381.9369 | 890 | 25/40 | 5 | 6 / 9 / 15 | 300/300 | 

Plan pessimiste : img0→1, img1→0+2, img2→1, img4→0, img5→1, img6→0, img8→0, img9→1, img11→0+2, img12→1, img14→1, img15→0, img16→1, img18→0, img19→1, img20→0+2, img22→0, img24→0, img25→1, img26→0, img28→0, img29→1, img32→0, img34→0, img35→1, img36→0, img38→1

## 3. Écart entre plan pessimiste et plan optimiste

| jeu | plan pess. (ProbaSup) | plan opt. (ProbaInf) | écart | plan pess. évalué ProbaInf | plan opt. évalué ProbaSup | images seulement pess. | images seulement opt. | mêmes images, autre instrument |
|---|---|---|---|---|---|---|---|---|
| spotProba4 | 333.0 | 400.0 | 67.0 | 370.0 | 324.0 | [4, 10, 15] | [3, 13] | [14] |
| spotProba5 | 553.6458 | 678.1212 | 124.4754 | 678.1212 | 551.8476 | [11] | [39] | [8, 9, 12, 34, 35, 36, 38] | 

## 4. Déformation du plan : spotProba5 par rapport à spotProba4

Les 20 premières images de spotProba5 ont les mêmes TY, PA, PM, DD, AN que spotProba4 ; seules les probabilités changent. Failure : [0, 0, 0] → [0.001, 0.001, 0.7], PMmax : 150 → 300.

Images 0–19 (stéréo, ou affectation différente), plans pessimistes :

| image | type | PA | nuage (4) | plan 4 | nuage (5) | plan 5 |
|---|---|---|---|---|---|---|
| 1 | stéréo | 20 | [0, 0.7] | — | [0, 0.1] | 0+2 |
| 3 | stéréo | 30 | [0, 0.7] | — | [0, 0.1] | — |
| 7 | stéréo | 20 | [0, 0.7] | — | [0, 0.1] | — |
| 10 | mono | 10 | [0, 0.1] | 2 | [0, 0.1] | — |
| 11 | stéréo | 20 | [0, 0.7] | — | [0, 0.1] | 0+2 |
| 12 | mono | 50 | [0, 0.1] | 0 | [0, 0.1] | 1 |
| 13 | stéréo | 30 | [0, 0.7] | — | [0, 0.1] | — |
| 14 | mono | 20 | [0, 0.1] | 0 | [0, 0.1] | 1 |
| 15 | mono | 10 | [0, 0.1] | 1 | [0, 0.1] | 0 |
| 16 | mono | 40 | [0, 0.1] | 0 | [0, 0.1] | 1 |
| 17 | stéréo | 10 | [0, 0.7] | — | [0.1, 0.3] | — |
| 18 | mono | 30 | [0, 0.1] | 1 | [0.1, 0.3] | 0 |
| 19 | mono | 20 | [0, 0.1] | 0 | [0.1, 0.3] | 1 | 

- spotProba4 : 0 stéréo retenues sur 6 ; instrument 3 utilisé 1 fois, dont 1 pour du mono.
- spotProba5 : 3 stéréo retenues sur 14 ; instrument 3 utilisé 3 fois, dont 0 pour du mono.

## 5. Images écartées et raison

Méthode : on impose l'image et on mesure la perte d'objectif, puis on recommence en supprimant une cause (contrainte de mémoire, contrainte de chevauchement, ou risque = critère déterministe). La raison affichée est le plus petit ensemble de causes dont la suppression annule la perte ; « ou » sépare des alternatives équivalentes.

### spotProba4, critère pessimiste

| image | type | PA | PM | gain espéré max | perte si imposée | raison |
|---|---|---|---|---|---|---|
| 1 | stéréo | 20 | 20 | 6.0 | 3.0 | memoire |
| 3 | stéréo | 30 | 20 | 9.0 | 0.0 | ex æquo (peut être retenue sans perte) |
| 7 | stéréo | 20 | 20 | 6.0 | 30.0 | memoire + chevauchement |
| 11 | stéréo | 20 | 20 | 6.0 | 3.0 | memoire + chevauchement ou memoire + risque |
| 13 | stéréo | 30 | 20 | 9.0 | 0.0 | ex æquo (peut être retenue sans perte) |
| 17 | stéréo | 10 | 20 | 3.0 | 33.0 | memoire + chevauchement | 

### spotProba4, critère optimiste

| image | type | PA | PM | gain espéré max | perte si imposée | raison |
|---|---|---|---|---|---|---|
| 1 | stéréo | 20 | 20 | 20 | 10.0 | memoire |
| 4 | mono | 10 | 10 | 10 | 10.0 | chevauchement |
| 7 | stéréo | 20 | 20 | 20 | 20.0 | memoire + chevauchement |
| 10 | mono | 10 | 10 | 10 | 0.0 | ex æquo (peut être retenue sans perte) |
| 11 | stéréo | 20 | 20 | 20 | 10.0 | memoire |
| 15 | mono | 10 | 10 | 10 | 10.0 | chevauchement |
| 17 | stéréo | 10 | 20 | 10 | 30.0 | memoire + chevauchement | 

**spotProba4 : images écartées par les deux critères (hors ex æquo) : [1, 7, 11, 17]**

### spotProba5, critère pessimiste

| image | type | PA | PM | gain espéré max | perte si imposée | raison |
|---|---|---|---|---|---|---|
| 3 | stéréo | 30 | 20 | 8.0919 | 3.5937 | chevauchement ou risque |
| 7 | stéréo | 20 | 20 | 5.3946 | 22.4757 | memoire + chevauchement |
| 10 | mono | 10 | 10 | 8.991 | 0.8946 | chevauchement |
| 13 | stéréo | 30 | 20 | 8.0919 | 3.5937 | chevauchement ou risque |
| 17 | stéréo | 10 | 20 | 2.0979 | 25.1748 | memoire + chevauchement |
| 21 | stéréo | 20 | 20 | 4.1958 | 4.1958 | memoire + chevauchement ou memoire + risque |
| 23 | stéréo | 30 | 20 | 6.2937 | 12.2859 | memoire + chevauchement ou memoire + risque ou chevauchement + risque |
| 27 | stéréo | 20 | 20 | 3.5964 | 29.0682 | memoire + chevauchement |
| 30 | mono | 10 | 10 | 5.994 | 0.8946 | memoire ou chevauchement |
| 31 | stéréo | 20 | 20 | 2.997 | 23.6736 | memoire + chevauchement |
| 33 | stéréo | 30 | 20 | 4.4955 | 3.1941 | risque |
| 37 | stéréo | 10 | 20 | 0.8991 | 13.0869 | memoire + chevauchement |
| 39 | stéréo | 40 | 20 | 3.5964 | 1.7982 | memoire ou risque | 

### spotProba5, critère optimiste

| image | type | PA | PM | gain espéré max | perte si imposée | raison |
|---|---|---|---|---|---|---|
| 3 | stéréo | 30 | 20 | 8.991 | 3.993 | chevauchement ou risque |
| 7 | stéréo | 20 | 20 | 5.994 | 24.573 | memoire + chevauchement |
| 10 | mono | 10 | 10 | 9.99 | 0.594 | chevauchement |
| 11 | stéréo | 20 | 20 | 5.994 | 0.0 | ex æquo (peut être retenue sans perte) |
| 13 | stéréo | 30 | 20 | 8.991 | 3.993 | chevauchement ou risque |
| 17 | stéréo | 10 | 20 | 2.6973 | 31.2687 | memoire + chevauchement |
| 21 | stéréo | 20 | 20 | 5.3946 | 5.3946 | memoire + chevauchement ou memoire + risque |
| 23 | stéréo | 30 | 20 | 8.0919 | 15.6813 | memoire + chevauchement ou memoire + risque ou chevauchement + risque |
| 27 | stéréo | 20 | 20 | 4.7952 | 38.1588 | memoire + chevauchement |
| 30 | mono | 10 | 10 | 7.992 | 0.594 | memoire ou chevauchement |
| 31 | stéréo | 20 | 20 | 4.1958 | 30.7662 | memoire + chevauchement |
| 33 | stéréo | 30 | 20 | 6.2937 | 3.6933 | risque |
| 37 | stéréo | 10 | 20 | 1.4985 | 20.1798 | memoire + chevauchement | 

**spotProba5 : images écartées par les deux critères (hors ex æquo) : [3, 7, 10, 13, 17, 21, 23, 27, 30, 31, 33, 37]**

## 6. Sensibilité au coefficient d'optimisme (Hurwicz)

α = 0 : pessimiste, α = 1 : optimiste.

### spotProba4

| α | objectif Hurwicz | valeur pess. | valeur opt. | images | images vs α précédent |
|---|---|---|---|---|---|
| 0 | 333.0 | 333.0 | 370.0 | 14 | — |
| 0.25 | 347.25 | 333.0 | 390.0 | 14 | +[13] −[15] |
| 0.5 | 362.0 | 324.0 | 400.0 | 13 | +[3] −[4, 10] |
| 0.75 | 381.0 | 324.0 | 400.0 | 13 | identique |
| 1 | 400.0 | 324.0 | 400.0 | 13 | identique | 

### spotProba5

| α | objectif Hurwicz | valeur pess. | valeur opt. | images | images vs α précédent |
|---|---|---|---|---|---|
| 0 | 553.6458 | 553.6458 | 678.1212 | 27 | — |
| 0.25 | 584.7646 | 553.6458 | 678.1212 | 27 | identique |
| 0.5 | 615.8835 | 553.6458 | 678.1212 | 27 | identique |
| 0.75 | 647.0023 | 553.6458 | 678.1212 | 27 | identique |
| 1 | 678.1212 | 551.8476 | 678.1212 | 27 | +[39] −[11] | 

