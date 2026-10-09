# le modele est construit dans une fonction (construire_modele / resoudre) pour pouvoir
# etre reutilise par l'interface (interface_spot.py) et par analyse_spot.py.
# Le programme est generique : le jeu de donnees est passe en parametre, par exemple
#   python spotProbaPartial.py spotProba4
#   python spotProbaPartial.py spotProba5 --critere hurwicz --alpha 0.3 --diagnostic

# on charge le solveur lineaire
from pyscipopt import Model, quicksum
from itertools import product
import argparse
import os
import runpy
import tempfile

# criteres disponibles pour la fonction objectif
CRITERES = ["pessimiste", "optimiste", "hurwicz", "deterministe"]
VARIABLES = ["nbImages", "nbInstruments", "PA", "DD", "AN", "VI", "DU", "TY", "PM", "PMmax",
             "Failure", "ProbaInf", "ProbaSup"]
EPS = 1e-6

# chargement d'un jeu de donnees
def charger_jeu(nom_ou_chemin):
    chemin = nom_ou_chemin
    if not os.path.exists(chemin):
        if not chemin.endswith(".py"):
            chemin += ".py"
        # par defaut on cherche le fichier a cote de ce programme
        if not os.path.exists(chemin):
            chemin = os.path.join(os.path.dirname(os.path.abspath(__file__)), chemin)
    namespace = runpy.run_path(chemin)
    return {k: namespace[k] for k in VARIABLES if k in namespace}

# probabilite de nuage utilisee par chaque critere
def proba_nuage(critere, ProbaInf, ProbaSup, alpha=0.5):
    if critere == "pessimiste":
        return ProbaSup
    if critere == "optimiste":
        return ProbaInf
    if critere == "hurwicz":
        # alpha = coefficient d'optimisme : alpha * (valeur optimiste) + (1 - alpha) * (valeur pessimiste).
        # Le gain espere etant lineaire en la proba de nuage, cela revient a utiliser
        # p = alpha * ProbaInf + (1 - alpha) * ProbaSup pour chaque image.
        return [alpha * pinf + (1 - alpha) * psup for pinf, psup in zip(ProbaInf, ProbaSup)]
    return None

# creation du modele lineaire
def construire_modele(nbImages, nbInstruments, PA, DD, AN, VI, DU, TY, PM, PMmax,
                      Failure, ProbaInf, ProbaSup, critere="pessimiste", alpha=0.5,
                      relacher=(), forcer=()):
    if critere not in CRITERES:
        raise ValueError("critere inconnu : " + str(critere) + " (attendu : " + ", ".join(CRITERES) + ")")
    if not 0 <= alpha <= 1:
        raise ValueError("alpha doit etre entre 0 et 1")
    # les images stereo utilisent les instruments 0 et 2 : il en faut au moins 3
    if nbInstruments < 3 and any(TY[i] == 2 for i in range(nbImages)):
        raise ValueError("il y a des images stereo (TY=2) : il faut au moins 3 instruments (0, 1, 2)")

    # model
    mymodel = Model()
    # pour chaque image i,  le solveur doit affecter la variable booleen selection[i] à 1 ssi  l'image i est selectionnée
    selection = {}
    for i in range(nbImages):
        selection[i] = mymodel.addVar(vtype='B', name='select' + str(i))
    # pour chaque image i,  le solveur doit affecter la variable booleen selection[i] à 1 ssi  l'image i est selectionnée
    assignedTo = {}
    for i in range(nbImages):
        ass_i = {}
        for j in range(nbInstruments):
            ass_i[j] = mymodel.addVar(vtype='B', name='assignto' + str(i) + '_' + str(j))
        assignedTo[i] = ass_i

    # la fonction objectif
    # gain espéré d'une image pour une proba de nuage donnée :
    # - image stereo (TY=2) : les 2 instruments (0 et 2) doivent réussir, donc les probabilités
    #   de succès se multiplient ; le nuage n'est compté qu'une fois (même zone visée)
    # - image mono (TY=1)   : le gain dépend de quel instrument a effectivement été choisi (assignedTo)
    def gain_espere(i, ProbaNuage):
        if TY[i] == 2:
            return PA[i] * (1 - ProbaNuage[i]) * (1 - Failure[0]) * (1 - Failure[2]) * selection[i]
        else:
            return quicksum(PA[i] * (1 - ProbaNuage[i]) * (1 - Failure[j]) * assignedTo[i][j] for j in range(nbInstruments))

    # - critère pessimiste : pire cas de nuage (ProbaSup)
    # - critère optimiste  : meilleur cas de nuage (ProbaInf)
    # - critère de Hurwicz : compromis entre les deux (coefficient d'optimisme alpha)
    if critere == "deterministe":
        # critere deterministe (sans incertitude) : somme des payoffs des images selectionnees
        mymodel.setObjective(quicksum(PA[i] * selection[i] for i in range(nbImages)), sense='maximize')
    else:
        ProbaNuage = proba_nuage(critere, ProbaInf, ProbaSup, alpha)
        mymodel.setObjective(quicksum(gain_espere(i, ProbaNuage) for i in range(nbImages)), sense='maximize')


    # ajout des contraintes au modele

    # la contrainte de non chevauchement
    # considérons un instrument
    # si, sur cet insrument, le temps de transition entre 2 images ima1 et ima2
    # ne tient pas entre la fin de ima1 et le debut de ima2
    # alors une seule de ces deux images au plus peut etre assignée à l'instrument
    # (les valeurs de remplissage DD[i][1] = 0 des images stereo peuvent generer des contraintes
    #  sur l'instrument 1, mais elles sont toujours satisfaites puisque assignedTo[i][1] == 0)
    if "chevauchement" not in relacher:
        for ima1,ima2 in product(range(nbImages), range(nbImages)):
            if ima1 < ima2:
                for ins in range(nbInstruments):
                    if  abs(DD[ima1][ins] - DD[ima2][ins]) * VI < DU * VI + abs(AN[ima1][ins] - AN[ima2][ins]):
                        mymodel.addCons(assignedTo[ima1][ins] + assignedTo[ima2][ins] <= 1)

    # contrainte de memoire
    if "memoire" not in relacher:
        sum_memoire = 0
        for j_img in range(nbImages):
            sum_memoire += PM[j_img] * selection[j_img]
        mymodel.addCons(sum_memoire <= PMmax)

    # Les images stéréo doivent être réalisées sur les instruments 1 et 3; les images mono peuvent être réalisées par n’importe quel instrument
    # contrainte de stereo / mono + selection -> assigned == TY
    for j_img in range(nbImages):
        if TY[j_img] == 2:
            mymodel.addCons(selection[j_img] * TY[j_img] == assignedTo[j_img][0] + assignedTo[j_img][2])
            # une image stéréo n'implique pas l'instrument 2 (milieu) : on l'exclut explicitement
            mymodel.addCons(assignedTo[j_img][1] == 0)
        else:
            mymodel.addCons(selection[j_img] * TY[j_img] == quicksum(assignedTo[j_img][ins] for ins in range(nbInstruments)))

    # images imposees (diagnostic)
    for i in forcer:
        mymodel.addCons(selection[i] == 1)

    return mymodel, selection, assignedTo


# valeur (gain espéré) d'un plan donné, pour une proba de nuage donnée (ProbaInf ou ProbaSup)
def valeur_plan(affectations, TY, PA, Failure, ProbaNuage):
    """affectations : dict image -> liste des instruments utilises."""
    valeur = 0.0
    for ima, instruments in affectations.items():
        if TY[ima] == 2:
            valeur += PA[ima] * (1 - ProbaNuage[ima]) * (1 - Failure[0]) * (1 - Failure[2])
        else:
            for ins in instruments:
                valeur += PA[ima] * (1 - ProbaNuage[ima]) * (1 - Failure[ins])
    return valeur

def completer(donnees):
    # En l'absence de Failure / ProbaInf / ProbaSup, on considere qu'il n'y a pas d'incertitude.
    d = dict(donnees)
    d["Failure"] = d.get("Failure") or [0] * d["nbInstruments"]
    d["ProbaInf"] = d.get("ProbaInf") or [0] * d["nbImages"]
    d["ProbaSup"] = d.get("ProbaSup") or [0] * d["nbImages"]
    return d

def resoudre(donnees, critere="pessimiste", alpha=0.5, relacher=(), forcer=(),
             afficher_scip=False, fichier_probleme=None):
    d = completer(donnees)
    nbImages, nbInstruments = d["nbImages"], d["nbInstruments"]
    PA, TY, PM, Failure = d["PA"], d["TY"], d["PM"], d["Failure"]

    mymodel, _, assignedTo = construire_modele(
        nbImages, nbInstruments, PA, d["DD"], d["AN"], d["VI"], d["DU"], TY, PM, d["PMmax"],
        Failure, d["ProbaInf"], d["ProbaSup"], critere, alpha, relacher, forcer)

    if fichier_probleme is not None:
        mymodel.writeProblem(fichier_probleme)

    mymodel.hideOutput(not afficher_scip)
    mymodel.optimize()

    resultat = {"statut": mymodel.getStatus(), "objectif": None, "affectations": {}}
    if mymodel.getStatus() == 'optimal':
        resultat["objectif"] = mymodel.getObjVal()
        for ima in range(nbImages):
            instruments = [ins for ins in range(nbInstruments) if mymodel.getVal(assignedTo[ima][ins]) > 0.5]
            if instruments:
                resultat["affectations"][ima] = instruments
        affectations = resultat["affectations"]
        resultat["valeur_pessimiste"] = valeur_plan(affectations, TY, PA, Failure, d["ProbaSup"])
        resultat["valeur_optimiste"] = valeur_plan(affectations, TY, PA, Failure, d["ProbaInf"])
        resultat["valeur_deterministe"] = sum(PA[ima] for ima in affectations)
        resultat["memoire"] = sum(PM[ima] for ima in affectations)
    return resultat

# diagnostic : pourquoi une image est-elle ecartee ?
def gain_max_image(d, i, critere, alpha=0.5):
    # Meilleur gain espere que l'image i peut rapporter a elle seule (meilleur instrument).
    if critere == "deterministe":
        return d["PA"][i]
    p = proba_nuage(critere, d["ProbaInf"], d["ProbaSup"], alpha)[i]
    F = d["Failure"]
    if d["TY"][i] == 2:
        return d["PA"][i] * (1 - p) * (1 - F[0]) * (1 - F[2])
    return max(d["PA"][i] * (1 - p) * (1 - F[j]) for j in range(d["nbInstruments"]))

CAUSES = ("memoire", "chevauchement", "risque")

def diagnostiquer_exclusions(donnees, critere="pessimiste", alpha=0.5):
    """Pour chaque image non retenue, cherche ce qui l'empeche d'entrer dans le plan.

    On impose la selection de l'image et on mesure la perte d'objectif. On refait la meme
    mesure en supprimant une ou plusieurs causes possibles :
    - "memoire"       : sans la contrainte de memoire ;
    - "chevauchement" : sans la contrainte de non chevauchement ;
    - "risque"        : avec le critere deterministe (ni nuage ni panne).
    Les raisons retenues sont les plus petits ensembles de causes dont la suppression
    rend la perte nulle (d'abord une seule cause, puis deux, puis les trois).
    Renvoie (plan, liste de dicts par image ecartee).
    """
    d = completer(donnees)
    plan = resoudre(d, critere, alpha)
    if plan["statut"] != "optimal":
        return plan, []

    def parametres(causes):
        return {"critere": "deterministe" if "risque" in causes else critere,
                "relacher": tuple(c for c in causes if c != "risque")}

    ensembles = [()] + [(c,) for c in CAUSES] + [tuple(c for c in CAUSES if c != x) for x in reversed(CAUSES)] + [CAUSES]
    reference = {e: resoudre(d, alpha=alpha, **parametres(e))["objectif"] for e in ensembles}

    def perte(i, e):
        force = resoudre(d, alpha=alpha, forcer=(i,), **parametres(e))
        return reference[e] - force["objectif"] if force["statut"] == "optimal" else float("inf")

    diagnostics = []
    for i in range(d["nbImages"]):
        if i in plan["affectations"]:
            continue
        perte_complet = perte(i, ())
        gain = gain_max_image(d, i, critere, alpha)
        if gain <= EPS:
            raisons = ["risque (gain espéré nul)"]
        elif perte_complet <= EPS:
            raisons = ["ex æquo (peut être retenue sans perte)"]
        else:
            raisons = []
            for taille in (1, 2, 3):
                raisons = [" + ".join(e) for e in ensembles if len(e) == taille and perte(i, e) <= EPS]
                if raisons:
                    break
        diagnostics.append({
            "image": i,
            "type": "stéréo" if d["TY"][i] == 2 else "mono",
            "PA": d["PA"][i],
            "PM": d["PM"][i],
            "gain espéré max": gain,
            "perte si imposée": perte_complet if perte_complet > EPS else 0.0,
            "raisons": raisons,
        })
    return plan, diagnostics


# resolution et affichage des resulats
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Plan d'acquisition SPOT sous probabilités imprécises")
    parser.add_argument("jeu", nargs="?", default="spotProba1",
                        help="jeu de données : spotProba4, spotProba5.py ou un chemin (défaut : spotProba1)")
    parser.add_argument("--critere", choices=CRITERES, default="pessimiste")
    parser.add_argument("--alpha", type=float, default=0.5,
                        help="coefficient d'optimisme pour le critère de Hurwicz (0 = pessimiste, 1 = optimiste)")
    parser.add_argument("--diagnostic", action="store_true",
                        help="explique pourquoi chaque image non retenue est écartée")
    args = parser.parse_args()

    # on charge les données
    donnees = charger_jeu(args.jeu)

    # visualiser le problem lineaire cree
    pb_path = os.path.join(tempfile.gettempdir(), "pb.cip")
    print("Problème écrit dans : " + pb_path)

    # lancer l'optimisation
    print("Resolution de " + args.jeu + " (critere " + args.critere + ")")
    res = resoudre(donnees, critere=args.critere, alpha=args.alpha, afficher_scip=True, fichier_probleme=pb_path)

    print('statut ' + res["statut"])

    # afficher les resultats prorement
    if res["statut"] == 'optimal':
        print("\n\nProblème resolu, valeur de l'objectif (" + args.critere + ") " + str(res["objectif"]))
        for ima, instruments in res["affectations"].items():
            for ins in instruments:
                print("Image" + str(ima) + " selectionnée et  assignée à  " + str(ins) + "  (debut à " + str(donnees["DD"][ima][ins]) + ")")

        # valeurs du meme plan sous les autres hypotheses, pour comparaison
        print("Valeur pessimiste du plan (ProbaSup) " + str(res["valeur_pessimiste"]))
        print("Valeur optimiste du plan (ProbaInf) " + str(res["valeur_optimiste"]))
        print("Memoire utilisee " + str(res["memoire"]) + " / " + str(donnees["PMmax"]))

        if args.diagnostic:
            _, diagnostics = diagnostiquer_exclusions(donnees, args.critere, args.alpha)
            print("\nImages ecartees :")
            for diag in diagnostics:
                print("  image " + str(diag["image"]) + " (" + diag["type"] + ", PA=" + str(diag["PA"])
                      + ", PM=" + str(diag["PM"]) + ", gain espere max=" + str(round(diag["gain espéré max"], 3))
                      + ", perte si imposee=" + str(round(diag["perte si imposée"], 3)) + ") : "
                      + " ou ".join(diag["raisons"]))