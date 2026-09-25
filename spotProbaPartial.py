# Resolution d'un problème de planification de prise de vue, avec incertitude
# Helene Fargier, oct 2025
#
#  Version bootstrap, avec exemple de declaration de modele, ajout de variables de decision,
# d'une fonction objectif  ne prenant pas en compte les incertitudes
# une seule contrainte implementée


# on charge le solveur lineaire
from pyscipopt import Model, quicksum
from itertools import product
import os
import tempfile

# on charge les données
from spotProba1 import nbImages, nbInstruments, PA, DD, AN, VI, DU, TY, PM, PMmax, Failure, ProbaInf, ProbaSup


# creation du modele lineaire
#############################

#model
mymodel = Model()

# pour chaque image i ,  le solveur doit affecter la variable booleen selection[i) à 1 ssi  l'image i est selectionnée
selection = {}
for i in range(nbImages):
    selection[i] = mymodel.addVar(vtype='B', name='select' + str(i))

#### pour chaque image i ,  le solveur doit affecter la variable booleen selection[i) à 1 ssi  l'image i est selectionnée
assignedTo = {}
for i in range(nbImages):
    ass_i = {}
    for j in range(nbInstruments):
        ass_i[j] = mymodel.addVar(vtype='B', name='assignto' + str(i) + '_' + str(j))
    assignedTo[i] = ass_i

# la fonction objectif
######################

# gain espéré, critère pessimiste (on utilise ProbaSup, le pire cas de nuage) :
# - image stereo (TY=2) : les 2 instruments (0 et 2) doivent réussir, donc les probabilités
#   de succès se multiplient ; le nuage n'est compté qu'une fois (même zone visée)
# - image mono (TY=1)   : le gain dépend de quel instrument a effectivement été choisi (assignedTo)
def gain_espere_pessimiste(i):
    if TY[i] == 2:
        return PA[i] * (1 - ProbaSup[i]) * (1 - Failure[0]) * (1 - Failure[2]) * selection[i]
    else:
        return quicksum(PA[i] * (1 - ProbaSup[i]) * (1 - Failure[j]) * assignedTo[i][j] for j in range(nbInstruments))

# MAJ : la fonction objectif calcule le gain espéré en tenant compte de la proba de nuage (on prend le pire cas ProbaSup -> critère pessimiste,
# et de la probabilité Failure
# -> ce critère pessimiste qui pilote la décision (selection/assignedTo)
# la valeur optimiste est pour comparer seulement -> elle n'influence pas la décision
mymodel.setObjective(quicksum(gain_espere_pessimiste(i) for i in range(nbImages)), sense='maximize')



# ajout des contraintes au modele
################################

# la contrainte de non chevauchement
# considérons un instrument
# si, sur cet insrument, le temps de transition entre 2 images ima1 et ima2 
# ne tient pas entre la fin de ima1 et le debut de ima2 
# alors une seule de ces deux images au plus peut etre assignée à l'instrument

for ima1,ima2 in product(range(nbImages), range(nbImages)):
    if ima1 < ima2:
        for ins in range(nbInstruments):
            if  abs(DD[ima1][ins] - DD[ima2][ins]) * VI < DU * VI + abs(AN[ima1][ins] - AN[ima2][ins]):
                mymodel.addCons(assignedTo[ima1][ins] + assignedTo[ima2][ins] <= 1)

# contrainte de memoire
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
        mymodel.addCons(selection[j_img] * TY[j_img] == assignedTo[j_img][0] + assignedTo[j_img][1] + assignedTo[j_img][2])

# contraint assignedTo <= 1
for j_img in range(nbImages):
    for i_ins in range(nbInstruments):
        mymodel.addCons(assignedTo[j_img][i_ins] <= 1)

                
# resolution et affichage des resulats
#########################################

#visualiser le problem lineaire cree
# le dossier du projet contient des caractères accentués (ex: "données"),
# ce que SCIP (bibliothèque C) ne sait pas gérer pour écrire un fichier sous Windows.
# On écrit donc pb.cip dans le dossier temporaire du système, qui ne contient pas d'accents.
pb_path = os.path.join(tempfile.gettempdir(), "pb.cip")
mymodel.writeProblem(pb_path)
print("Problème écrit dans : " + pb_path)

# lancer l'optimisation
print("Resolution")
mymodel.hideOutput(False)
mymodel.optimize()

#afficiher  les resultats mode "scip"
print('statut ' + mymodel.getStatus())
print("solution", end='\t')
print(mymodel.getBestSol())

# afficher les resultats prorement
if mymodel.getStatus() == 'optimal':
    print("\n\nProblème resolu, valeur de l'objectif (pessimiste, celle qui a pilote la decision) " + str(mymodel.getObjVal()))
    sol=mymodel.getBestSol()
    for ima in range(nbImages):
        for ins in range(nbInstruments):
            if (mymodel.getVal(assignedTo[ima][ins]) > 0):
                print("Image" + str(ima) + " selectionnée et  assignée à  " + str(ins) + "  (debut à " + str( DD[ima][ins]) + ")")

    # valeur optimiste du meme plan, juste pour comparaison
    valeur_optimiste = 0.0
    for ima in range(nbImages):
        if TY[ima] == 2:
            if mymodel.getVal(selection[ima]) > 0.5:
                valeur_optimiste += PA[ima] * (1 - ProbaInf[ima]) * (1 - Failure[0]) * (1 - Failure[2])
        else:
            for ins in range(nbInstruments):
                if mymodel.getVal(assignedTo[ima][ins]) > 0.5:
                    valeur_optimiste += PA[ima] * (1 - ProbaInf[ima]) * (1 - Failure[ins])
    print("Valeur optimiste du meme plan (ProbaInf, comparaison uniquement) " + str(valeur_optimiste))
