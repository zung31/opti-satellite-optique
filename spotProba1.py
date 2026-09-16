# example 1, no uncertainty, optimum 70

nbImages = 3

TY = [1, 2, 1] # type d'image: 1-mono, 2-stereo

PM = [10, 20, 10] # taille memoire de chaque image

PA = [10, 20, 40] # prix/gain pour chaque image

nbInstruments = 3

# instant de debut acquisition de l'image i par instrument j (s) -> can start at which time?
DD = [[130, 230, 330], [150, 0, 350], [220, 320, 420]] # dimension nbImages x nbInstrument

# angle depointage lateral du mirroir pour viser l'image i depuis j (deg)
AN = [[10, 10, 10], [5, 0, 5], [20, 20, 20]]

# duree acquisition (meme pour tous les images)
DU = 20

VI = 1 # vitesse de rotation du mirroir deg/s

PMmax = 50 # tallle memoire totale de satelite 




# Probability of Cloudy Weather
ProbaInf = [0, 0, 0]
ProbaSup = [0, 0, 0]
# proba of failure of each instrument
Failure = [0, 0, 0]


## other examples

# Maximum value of the objective : 63  (proba of cloud  = 0.1 during all the day; instruments ok)
#ProbaInf =   [0.1, 0.1, 0.1];
#ProbaSup =   [0.1, 0.1, 0.1];
#Failure = [0, 0, 0];



# Maximum value of the objective : 49  (proba of cloud  in  [0.1, 0,3] during all the day; instruments ok)
#ProbaInf =   [0.1, 0.1, 0.1];
#ProbaSup =   [0.3, 0.3, 0.3];
#Failure = [0, 0, 0];

# Maximum value of the objective : 60  (no cloud; instrument 2 is down )
#  no image is assigned on instrument 2 ; 
# image 1 is not selected but it would be selected if we increase its payoff
#  image 1 is assigned on instrument 2 if its probability of failure is decreased
#ProbaInf =    [0, 0, 0];
#ProbaSup =    [0, 0, 0];
#Failure = [0, 1, 0];


# Maximum value of the objective : 14.661  
#ProbaInf =    [0, 0, 0];
#ProbaSup =    [0.1, 0.5, 0.9];
#Failure = [0.01, 0.9, 0.01];
