# Analyse des resultats pour le rapport (questions ouvertes de l'enonce)
#
# Lancement :
#   python analyse_spot.py > resultats_analyse.md
#
# Produit, en Markdown :
#   1. la validation sur les jeux de test (valeurs attendues de l'enonce) ;
#   2. les plans de spotProba4 et spotProba5 selon chaque critere ;
#   3. l'ecart plan pessimiste / plan optimiste ;
#   4. la deformation du plan de spotProba5 par rapport a spotProba4 ;
#   5. les images ecartees et la raison (memoire, chevauchement, risque) ;
#   6. la sensibilite au coefficient d'optimisme du critere de Hurwicz.

from spotProbaPartial import charger_jeu, completer, resoudre, diagnostiquer_exclusions

CRITERES_PLANS = [("pessimiste", 0.5), ("optimiste", 0.5), ("hurwicz", 0.5), ("deterministe", 0.5)]
NOMS_INSTRUMENTS = {0: "1 (avant)", 1: "2 (nadir)", 2: "3 (arrière)"}


def tableau(entetes, lignes):
    sortie = ["| " + " | ".join(entetes) + " |", "|" + "---|" * len(entetes)]
    for ligne in lignes:
        sortie.append("| " + " | ".join(str(v) for v in ligne) + " |")
    return "\n".join(sortie)

def r4(x):
    return round(x, 4)

def nom_critere(critere, alpha):
    return f"hurwicz α={alpha}" if critere == "hurwicz" else critere

def usage_instruments(d, plan):
    return {j: sum(j in ins for ins in plan["affectations"].values()) for j in range(d["nbInstruments"])}

def affectation_txt(plan, i):
    return "+".join(str(j) for j in plan["affectations"].get(i, [])) or "—"

print("# Résultats de l'analyse (généré par analyse_spot.py)\n")
# 1. Validation 
print("## 1. Validation sur les jeux de test\n")
jeu1 = charger_jeu("spotProba1")
cas = [
    ("spotProba1", jeu1, 70),
    ("spotProba2", charger_jeu("spotProba2"), 60),
    ("spotProba3", charger_jeu("spotProba3"), 60),
    ("spotProba1, nuage précis 0.1", {**jeu1, "ProbaInf": [.1] * 3, "ProbaSup": [.1] * 3, "Failure": [0, 0, 0]}, 63),
    ("spotProba1, nuage [0.1, 0.3]", {**jeu1, "ProbaInf": [.1] * 3, "ProbaSup": [.3] * 3, "Failure": [0, 0, 0]}, 49),
    ("spotProba1, nadir en panne", {**jeu1, "ProbaInf": [0] * 3, "ProbaSup": [0] * 3, "Failure": [0, 1, 0]}, 60),
    ("spotProba1, tout combiné", {**jeu1, "ProbaInf": [0] * 3, "ProbaSup": [.1, .5, .9], "Failure": [.01, .9, .01]}, 14.661),
]
lignes = []
for nom, d, attendu in cas:
    obtenu = resoudre(d, "pessimiste")["objectif"]
    lignes.append((nom, attendu, r4(obtenu), "✅" if abs(obtenu - attendu) < 1e-3 else "❌"))
print(tableau(["jeu", "attendu", "obtenu (pessimiste)", ""], lignes), "\n")
# 2. Plans de spotProba4 et spotProba5 
jeux = {nom: completer(charger_jeu(nom)) for nom in ("spotProba4", "spotProba5")}
plans = {nom: {(c, a): resoudre(d, c, a) for c, a in CRITERES_PLANS} for nom, d in jeux.items()}
print("## 2. Plans de spotProba4 et spotProba5\n")
for nom, d in jeux.items():
    print(f"### {nom}\n")
    print(f"{d['nbImages']} images ({sum(t == 2 for t in d['TY'])} stéréo), PMmax = {d['PMmax']}, "
          f"Failure = {d['Failure']}\n")
    lignes = []
    for (c, a), p in plans[nom].items():
        u = usage_instruments(d, p)
        lignes.append((nom_critere(c, a), r4(p["objectif"]), r4(p["valeur_pessimiste"]), r4(p["valeur_optimiste"]),
                       p["valeur_deterministe"], f"{len(p['affectations'])}/{d['nbImages']}",
                       sum(d["TY"][i] == 2 for i in p["affectations"]),
                       " / ".join(str(u[j]) for j in range(d["nbInstruments"])),
                       f"{p['memoire']}/{d['PMmax']}"))
    print(tableau(["plan (critère)", "objectif", "valeur pess.", "valeur opt.", "Σ PA", "images",
                   "stéréo", "usage instr. 1/2/3", "mémoire"], lignes), "\n")

    pess = plans[nom][("pessimiste", 0.5)]
    print("Plan pessimiste : " + ", ".join(
        f"img{i}→{affectation_txt(pess, i)}" for i in sorted(pess["affectations"])) + "\n")
# 3. Ecart pessimiste / optimiste
print("## 3. Écart entre plan pessimiste et plan optimiste\n")
lignes = []
for nom, d in jeux.items():
    pess, opt = plans[nom][("pessimiste", 0.5)], plans[nom][("optimiste", 0.5)]
    seul_p = sorted(pess["affectations"].keys() - opt["affectations"].keys())
    seul_o = sorted(opt["affectations"].keys() - pess["affectations"].keys())
    communes = pess["affectations"].keys() & opt["affectations"].keys()
    autre_instr = sorted(i for i in communes if pess["affectations"][i] != opt["affectations"][i])
    lignes.append((nom, r4(pess["objectif"]), r4(opt["objectif"]), r4(opt["objectif"] - pess["objectif"]),
                   r4(pess["valeur_optimiste"]), r4(opt["valeur_pessimiste"]),
                   seul_p or "—", seul_o or "—", autre_instr or "—"))
print(tableau(["jeu", "plan pess. (ProbaSup)", "plan opt. (ProbaInf)", "écart",
               "plan pess. évalué ProbaInf", "plan opt. évalué ProbaSup",
               "images seulement pess.", "images seulement opt.", "mêmes images, autre instrument"], lignes), "\n")
# 4. Deformation spotProba4 -> spotProba5 
print("## 4. Déformation du plan : spotProba5 par rapport à spotProba4\n")
d4, d5 = jeux["spotProba4"], jeux["spotProba5"]
identiques = [k for k in ("TY", "PA", "PM", "DD", "AN") if d5[k][:20] == d4[k]]
print(f"Les 20 premières images de spotProba5 ont les mêmes {', '.join(identiques)} que spotProba4 ; "
      f"seules les probabilités changent. Failure : {d4['Failure']} → {d5['Failure']}, "
      f"PMmax : {d4['PMmax']} → {d5['PMmax']}.\n")
p4, p5 = plans["spotProba4"][("pessimiste", 0.5)], plans["spotProba5"][("pessimiste", 0.5)]
lignes = []
for i in range(20):
    if affectation_txt(p4, i) != affectation_txt(p5, i) or d4["TY"][i] == 2:
        lignes.append((i, "stéréo" if d4["TY"][i] == 2 else "mono", d4["PA"][i],
                       f"[{d4['ProbaInf'][i]}, {d4['ProbaSup'][i]}]", affectation_txt(p4, i),
                       f"[{d5['ProbaInf'][i]}, {d5['ProbaSup'][i]}]", affectation_txt(p5, i)))
print("Images 0–19 (stéréo, ou affectation différente), plans pessimistes :\n")
print(tableau(["image", "type", "PA", "nuage (4)", "plan 4", "nuage (5)", "plan 5"], lignes), "\n")

for nom, d in jeux.items():
    p = plans[nom][("pessimiste", 0.5)]
    u = usage_instruments(d, p)
    mono_instr3 = sum(1 for i, ins in p["affectations"].items() if d["TY"][i] == 1 and 2 in ins)
    print(f"- {nom} : {sum(d['TY'][i] == 2 for i in p['affectations'])} stéréo retenues sur "
          f"{sum(t == 2 for t in d['TY'])} ; instrument 3 utilisé {u[2]} fois, dont {mono_instr3} pour du mono.")
print()

# 5. Images ecartees
print("## 5. Images écartées et raison\n")
print("Méthode : on impose l'image et on mesure la perte d'objectif, puis on recommence en supprimant "
      "une cause (contrainte de mémoire, contrainte de chevauchement, ou risque = critère déterministe). "
      "La raison affichée est le plus petit ensemble de causes dont la suppression annule la perte ; "
      "« ou » sépare des alternatives équivalentes.\n")
ecartees = {}
for nom, d in jeux.items():
    for c in ("pessimiste", "optimiste"):
        _, diags = diagnostiquer_exclusions(d, c)
        ecartees[(nom, c)] = {diag["image"] for diag in diags if not diag["raisons"][0].startswith("ex æquo")}
        print(f"### {nom}, critère {c}\n")
        print(tableau(["image", "type", "PA", "PM", "gain espéré max", "perte si imposée", "raison"],
                      [(g["image"], g["type"], g["PA"], g["PM"], r4(g["gain espéré max"]),
                        r4(g["perte si imposée"]), " ou ".join(g["raisons"])) for g in diags]), "\n")
    systematiques = sorted(ecartees[(nom, "pessimiste")] & ecartees[(nom, "optimiste")])
    print(f"**{nom} : images écartées par les deux critères : {systematiques}**\n")

# 6. Hurwicz 
print("## 6. Sensibilité au coefficient d'optimisme (Hurwicz)\n")
print("α = 0 : pessimiste, α = 1 : optimiste.\n")
for nom, d in jeux.items():
    lignes, precedent = [], None
    for alpha in (0, 0.25, 0.5, 0.75, 1):
        p = resoudre(d, "hurwicz", alpha)
        images = sorted(p["affectations"])
        change = "—" if precedent is None else (
            "identique" if images == precedent else
            f"+{sorted(set(images) - set(precedent))} −{sorted(set(precedent) - set(images))}")
        lignes.append((alpha, r4(p["objectif"]), r4(p["valeur_pessimiste"]), r4(p["valeur_optimiste"]),
                       len(images), change))
        precedent = images
    print(f"### {nom}\n")
    print(tableau(["α", "objectif Hurwicz", "valeur pess.", "valeur opt.", "images", "images vs α précédent"],
                  lignes), "\n")