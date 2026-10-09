# Interface Streamlit pour le problème de planification de prise de vue
# Le modèle (contraintes + critères) est importé depuis spotProbaPartial.py :
# l'interface ne fait que préparer les données, lancer la résolution et afficher le résultat.
#
# Installation nécessaire :
#   pip install streamlit pyscipopt pandas matplotlib
#
# Lancement :
#   streamlit run interface_spot.py

import json
from pathlib import Path

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from spotProbaPartial import resoudre, diagnostiquer_exclusions

st.set_page_config(page_title="Planification de prise de vue", layout="wide")

DOSSIER = Path(__file__).parent
JEUX_LOCAUX = sorted(p.stem for p in DOSSIER.glob("spotProba[0-9]*.py"))

VARIABLES = ["nbImages", "nbInstruments", "PA", "DD", "AN", "VI", "DU", "TY", "PM",
             "PMmax", "Failure", "ProbaInf", "ProbaSup"]
OBLIGATOIRES = {"nbImages", "nbInstruments", "PA", "DD", "AN", "VI", "DU", "TY", "PM", "PMmax"}

LIBELLES_CRITERES = {
    "pessimiste": "Pessimiste: gain espéré avec ProbaSup et Failure",
    "optimiste": "Optimiste: gain espéré avec ProbaInf et Failure",
    "hurwicz": "Hurwicz: compromis α·optimiste + (1−α)·pessimiste",
    "deterministe": "Déterministe: somme des payoffs, sans incertitude",
}


# -----------------------------------------------------------------------
# Lecture des fichiers de données (.py au format spotProba, ou .json exporté)
# -----------------------------------------------------------------------
def lire_donnees(texte, nom):
    if nom.endswith(".json"):
        namespace, notes = json.loads(texte), []
    else:
        # Le fichier ne contient que des affectations : on l'exécute sans builtins
        # (il doit tout de même venir d'une source de confiance).
        namespace = {}
        exec(compile(texte, nom, "exec"), {"__builtins__": {}}, namespace)
        notes = [ligne.lstrip("# ").strip() for ligne in texte.splitlines()
                 if ligne.startswith("#") and any(m in ligne.lower() for m in ("maximum", "optimum"))]
    donnees = {k: v for k, v in namespace.items() if k in VARIABLES}
    manquantes = OBLIGATOIRES - donnees.keys()
    if manquantes:
        raise ValueError(f"variables manquantes : {sorted(manquantes)}")
    return donnees, notes


# Passage données <-> état de l'interface (session_state + tableau)
def colonnes(nb_instruments):
    return (["id", "TY", "PA", "PM", "ProbaInf", "ProbaSup"]
            + [f"DD_{j}" for j in range(nb_instruments)]
            + [f"AN_{j}" for j in range(nb_instruments)])

def ligne_par_defaut(i, nb_instruments):
    ligne = {"id": i, "TY": 1, "PA": 10.0, "PM": 10.0, "ProbaInf": 0.0, "ProbaSup": 0.0}
    for j in range(nb_instruments):
        ligne[f"DD_{j}"] = float(100 * i)
        ligne[f"AN_{j}"] = 0.0
    return ligne

def ajuster_tableau(df, nb_images, nb_instruments):
    # Redimensionne le tableau en gardant les valeurs déjà saisies.
    lignes = []
    for i in range(nb_images):
        ligne = ligne_par_defaut(i, nb_instruments)
        if i < len(df):
            for c in ligne:
                if c in df.columns and c != "id":
                    ligne[c] = df.iloc[i][c]
        lignes.append(ligne)
    return pd.DataFrame(lignes, columns=colonnes(nb_instruments))

def donnees_vers_etat(donnees, source, notes):
    n, k = int(donnees["nbImages"]), int(donnees["nbInstruments"])
    zeros_images = [0.0] * n
    lignes = []
    for i in range(n):
        ligne = {"id": i, "TY": int(donnees["TY"][i]), "PA": float(donnees["PA"][i]),
                 "PM": float(donnees["PM"][i]),
                 "ProbaInf": float((donnees.get("ProbaInf") or zeros_images)[i]),
                 "ProbaSup": float((donnees.get("ProbaSup") or zeros_images)[i])}
        for j in range(k):
            ligne[f"DD_{j}"] = float(donnees["DD"][i][j])
            ligne[f"AN_{j}"] = float(donnees["AN"][i][j])
        lignes.append(ligne)
    ss = st.session_state
    ss["tableau"] = pd.DataFrame(lignes, columns=colonnes(k))
    ss["version_tableau"] = ss.get("version_tableau", 0) + 1
    ss["nbImages"], ss["nbInstruments"] = n, k
    ss["VI"], ss["DU"], ss["PMmax"] = float(donnees["VI"]), float(donnees["DU"]), float(donnees["PMmax"])
    failure = donnees.get("Failure") or [0.0] * k
    for j in range(k):
        ss[f"Failure_{j}"] = float(failure[j])
    ss["source"], ss["notes"] = source, notes
    ss.pop("resultat", None)

def etat_vers_donnees(df):
    ss = st.session_state
    k = int(ss["nbInstruments"])
    return {
        "nbImages": len(df),
        "nbInstruments": k,
        "TY": [int(v) for v in df["TY"]],
        "PA": [float(v) for v in df["PA"]],
        "PM": [float(v) for v in df["PM"]],
        "ProbaInf": [float(v) for v in df["ProbaInf"]],
        "ProbaSup": [float(v) for v in df["ProbaSup"]],
        "DD": [[float(df.iloc[i][f"DD_{j}"]) for j in range(k)] for i in range(len(df))],
        "AN": [[float(df.iloc[i][f"AN_{j}"]) for j in range(k)] for i in range(len(df))],
        "VI": float(ss["VI"]),
        "DU": float(ss["DU"]),
        "PMmax": float(ss["PMmax"]),
        "Failure": [float(ss.get(f"Failure_{j}", 0.0)) for j in range(k)],
    }

# callbacks (exécutés avant le rendu des widgets, donc on peut modifier leurs valeurs)
def charger_jeu_local():
    nom = st.session_state["jeu_choisi"]
    texte = (DOSSIER / f"{nom}.py").read_text(encoding="utf-8")
    donnees, notes = lire_donnees(texte, f"{nom}.py")
    donnees_vers_etat(donnees, f"{nom}.py", notes)

def charger_fichier_importe():
    fichier = st.session_state.get("fichier_importe")
    if fichier is None:
        return
    try:
        donnees, notes = lire_donnees(fichier.getvalue().decode("utf-8"), fichier.name)
    except Exception as e:
        st.session_state["erreur_import"] = f"Impossible de lire « {fichier.name} » : {e}"
        return
    st.session_state.pop("erreur_import", None)
    donnees_vers_etat(donnees, fichier.name, notes)

# Initialisation (premier affichage) : premier jeu local
if "tableau" not in st.session_state:
    if JEUX_LOCAUX:
        st.session_state["jeu_choisi"] = JEUX_LOCAUX[0]
        charger_jeu_local()
    else:
        donnees_vers_etat({"nbImages": 5, "nbInstruments": 3, "TY": [1] * 5,
                           "PA": [10] * 5, "PM": [10] * 5,
                           "DD": [[100 * i] * 3 for i in range(5)], "AN": [[0] * 3] * 5,
                           "VI": 1, "DU": 20, "PMmax": 50}, "exemple généré", [])

# Barre latérale : choix des données, paramètres globaux, critère
with st.sidebar:
    st.header("Données")
    if JEUX_LOCAUX:
        st.selectbox("Jeu de données du projet", JEUX_LOCAUX, key="jeu_choisi")
        st.button("Charger ce jeu", on_click=charger_jeu_local, width="stretch")
    st.file_uploader(
        "…ou importer un fichier (.py au format spotProba, ou .json exporté)",
        type=["py", "json"], key="fichier_importe", on_change=charger_fichier_importe,
    )
    if "erreur_import" in st.session_state:
        st.error(st.session_state["erreur_import"])

    st.header("Paramètres globaux")
    st.number_input("Nombre d'images", min_value=1, max_value=500, step=1, key="nbImages")
    st.number_input("Nombre d'instruments", min_value=1, max_value=10, step=1, key="nbInstruments",
                    help="Les images stéréo utilisent les instruments 0 et 2 : il en faut au moins 3.")
    st.number_input("VI (vitesse de pivotement du miroir)", key="VI")
    st.number_input("DU (durée d'acquisition)", key="DU")
    st.number_input("PMmax (mémoire embarquée)", key="PMmax")

    st.subheader("Probabilité de panne (Failure)")
    for j in range(int(st.session_state["nbInstruments"])):
        st.session_state.setdefault(f"Failure_{j}", 0.0)
        st.number_input(f"Instrument {j}", min_value=0.0, max_value=1.0, step=0.01,
                        key=f"Failure_{j}")

    st.header("Critère")
    critere = st.radio("Fonction objectif", list(LIBELLES_CRITERES),
                       format_func=LIBELLES_CRITERES.get, key="critere")
    alpha = st.slider("α (coefficient d'optimisme, Hurwicz)", 0.0, 1.0, 0.5, 0.05, key="alpha",
                      help="0 = pessimiste, 1 = optimiste. Utilisé par le critère de Hurwicz "
                           "et dans la comparaison des plans.",
                      disabled=critere != "hurwicz")

def nom_critere(c, a):
    return f"hurwicz (α={a:g})" if c == "hurwicz" else c

# En-tête
st.title("Planification de prise de vue")
st.caption("Modèle de `spotProbaPartial.py`, résolu avec SCIP (`pyscipopt`).")

st.markdown(f"**Source des données :** `{st.session_state['source']}`")
if st.session_state.get("notes"):
    st.info(
        "Valeurs de référence indiquées dans les commentaires du fichier "
        "(certaines concernent des variantes commentées des données) :\n\n"
        + "\n".join(f"- {note}" for note in st.session_state["notes"])
    )

# 1. Tableau des images (éditable)
st.subheader("1. Données des images")
st.caption(
    "TY = 1 (mono) ou 2 (stéréo). PA = payoff, PM = mémoire requise, "
    "ProbaInf/ProbaSup = intervalle de probabilité de nuage. "
    "DD_j / AN_j = date de début / angle de dépointage sur l'instrument j."
)

ss = st.session_state
nb_images, nb_instruments = int(ss["nbImages"]), int(ss["nbInstruments"])
if ss["tableau"].shape != (nb_images, len(colonnes(nb_instruments))):
    # nombre d'images ou d'instruments modifié : on redimensionne en gardant les saisies
    ss["tableau"] = ajuster_tableau(ss.get("tableau_courant", ss["tableau"]), nb_images, nb_instruments)
    ss["version_tableau"] += 1

tableau = st.data_editor(
    ss["tableau"],
    num_rows="fixed",
    width="stretch",
    hide_index=True,
    key=f"editeur_{ss['version_tableau']}",
    column_config={
        "id": st.column_config.NumberColumn("id", disabled=True),
        "TY": st.column_config.SelectboxColumn("TY", options=[1, 2], required=True),
        "ProbaInf": st.column_config.NumberColumn("ProbaInf", min_value=0.0, max_value=1.0, step=0.01),
        "ProbaSup": st.column_config.NumberColumn("ProbaSup", min_value=0.0, max_value=1.0, step=0.01),
    },
)
ss["tableau_courant"] = tableau

incoherentes = tableau.index[tableau["ProbaInf"] > tableau["ProbaSup"]].tolist()
if incoherentes:
    st.warning(f"ProbaInf > ProbaSup pour les images {incoherentes}.")

donnees = etat_vers_donnees(tableau)
st.download_button(
    "Exporter les données (JSON, réimportable)",
    data=json.dumps(donnees, indent=2),
    file_name="donnees_prise_de_vue.json",
    mime="application/json",
)

# 2. Résolution
st.subheader("2. Résolution")

if st.button("▶ Lancer l'optimisation", type="primary"):
    try:
        resultat = resoudre(donnees, critere=critere, alpha=alpha)
    except Exception as e:
        st.error(f"Erreur lors de la résolution : {e}")
    else:
        # on garde le résultat (et les données utilisées) pour qu'il reste affiché
        ss["resultat"] = {"res": resultat, "donnees": donnees, "critere": critere, "alpha": alpha}

if "resultat" in ss:
    res = ss["resultat"]["res"]
    d = ss["resultat"]["donnees"]
    if (ss["resultat"]["donnees"] != donnees or ss["resultat"]["critere"] != critere
            or (critere == "hurwicz" and ss["resultat"]["alpha"] != alpha)):
        st.warning("Les données ou le critère ont changé depuis cette résolution : relancez l'optimisation.")

    st.write(f"**Statut du solveur :** `{res['statut']}` — critère "
             f"*{nom_critere(ss['resultat']['critere'], ss['resultat']['alpha'])}*")

    if res["statut"] != "optimal":
        st.warning("Pas de solution optimale trouvée.")
    else:
        affectations = res["affectations"]
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Objectif", str(round(res["objectif"], 4)))
        c2.metric("Valeur pessimiste", str(round(res["valeur_pessimiste"], 4)), help="ProbaSup + Failure")
        c3.metric("Valeur optimiste", str(round(res["valeur_optimiste"], 4)), help="ProbaInf + Failure")
        c4.metric("Images sélectionnées", f"{len(affectations)} / {d['nbImages']}")
        c5.metric("Mémoire utilisée", f"{res['memoire']:g} / {d['PMmax']:g}")

        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("**Détail par image**")
            lignes = []
            for i in range(d["nbImages"]):
                instruments = affectations.get(i, [])
                lignes.append({
                    "image": i,
                    "type": "stéréo" if d["TY"][i] == 2 else "mono",
                    "sélectionnée": "✅" if instruments else "—",
                    "instrument(s)": " + ".join(str(j) for j in instruments),
                    "début(s)": " / ".join(f"{d['DD'][i][j]:g}" for j in instruments),
                    "PA": d["PA"][i],
                    "PM": d["PM"][i],
                })
            st.dataframe(pd.DataFrame(lignes), width="stretch", hide_index=True)

        with col2:
            st.markdown("**Planning par instrument (Gantt)**")
            if affectations:
                fig, ax = plt.subplots(figsize=(7, 1 + 0.6 * d["nbInstruments"]))
                couleurs = plt.get_cmap("tab20")
                for i, instruments in affectations.items():
                    for j in instruments:
                        debut = d["DD"][i][j]
                        ax.barh(j, d["DU"], left=debut, height=0.5, color=couleurs(i % 20),
                                edgecolor="black", linewidth=0.5)
                        ax.text(debut + d["DU"] / 2, j, f"img{i}", va="center", ha="center", fontsize=8)
                ax.set_yticks(range(d["nbInstruments"]))
                ax.set_yticklabels([f"instrument {j}" for j in range(d["nbInstruments"])])
                ax.set_ylim(-0.6, d["nbInstruments"] - 0.4)
                ax.invert_yaxis()
                ax.set_xlabel("temps")
                ax.grid(axis="x", alpha=0.3)
                st.pyplot(fig)
                plt.close(fig)
            else:
                st.write("Aucune image sélectionnée.")

# 3. Comparaison des plans pessimiste / optimiste
st.subheader("3. Comparaison des plans")
st.caption(
    "Résout le problème avec chaque critère, puis évalue chaque plan obtenu sous les trois "
    "hypothèses : les plans diffèrent-ils seulement par leur valeur, ou aussi par les images retenues ?"
)

if st.button("Comparer les plans"):
    try:
        plans = {nom_critere(c, alpha): resoudre(donnees, critere=c, alpha=alpha) for c in LIBELLES_CRITERES}
    except Exception as e:
        st.error(f"Erreur lors de la résolution : {e}")
    else:
        ss["comparaison"] = {"plans": plans, "donnees": donnees, "alpha": alpha}

if "comparaison" in ss:
    plans, d = ss["comparaison"]["plans"], ss["comparaison"]["donnees"]
    if d != donnees or ss["comparaison"]["alpha"] != alpha:
        st.warning("Les données ou α ont changé depuis cette comparaison : relancez-la.")
    non_optimaux = [c for c, r in plans.items() if r["statut"] != "optimal"]
    if non_optimaux:
        st.warning(f"Pas de solution optimale pour : {', '.join(non_optimaux)}.")
    else:
        st.markdown("**Valeur de chaque plan (lignes) évaluée sous chaque hypothèse (colonnes)**")
        st.dataframe(pd.DataFrame([
            {"plan": c,
             "valeur pessimiste (ProbaSup)": round(r["valeur_pessimiste"], 4),
             "valeur optimiste (ProbaInf)": round(r["valeur_optimiste"], 4),
             "valeur déterministe (Σ PA)": round(r["valeur_deterministe"], 4),
             "images retenues": len(r["affectations"]),
             "mémoire": r["memoire"]}
            for c, r in plans.items()
        ]), width="stretch", hide_index=True)

        pess, opt = plans["pessimiste"], plans["optimiste"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Plan pessimiste (sa valeur)", str(round(pess["objectif"], 4)))
        c2.metric("Plan optimiste (sa valeur)", str(round(opt["objectif"], 4)))
        c3.metric("Écart", str(round(opt["objectif"] - pess["objectif"], 4)))

        def instruments_txt(r, i):
            return " + ".join(str(j) for j in r["affectations"].get(i, [])) or "—"

        differences = [
            {"image": i, "PA": d["PA"][i], "ProbaInf": d["ProbaInf"][i], "ProbaSup": d["ProbaSup"][i],
             **{f"plan {c}": instruments_txt(r, i) for c, r in plans.items()}}
            for i in range(d["nbImages"])
            if len({instruments_txt(r, i) for r in plans.values()}) > 1
        ]
        seulement_pess = sorted(pess["affectations"].keys() - opt["affectations"].keys())
        seulement_opt = sorted(opt["affectations"].keys() - pess["affectations"].keys())
        if seulement_pess or seulement_opt:
            st.info(
                "Les plans pessimiste et optimiste **ne retiennent pas les mêmes images** — "
                f"seulement dans le plan pessimiste : {seulement_pess or 'aucune'} ; "
                f"seulement dans le plan optimiste : {seulement_opt or 'aucune'}."
            )
        elif pess["affectations"] != opt["affectations"]:
            st.info("Les plans pessimiste et optimiste retiennent les mêmes images, "
                    "mais pas toujours sur les mêmes instruments.")
        else:
            st.info("Les plans pessimiste et optimiste sont identiques : ils ne diffèrent que par leur valeur.")

        if differences:
            st.markdown("**Images traitées différemment selon le critère** (instrument(s) utilisé(s), — = non retenue)")
            st.dataframe(pd.DataFrame(differences), width="stretch", hide_index=True)

# 4. Images écartées : pourquoi ?
st.subheader("4. Images écartées : mémoire, chevauchement ou risque ?")
st.caption(
    "Pour chaque image non retenue, on impose sa sélection et on mesure la perte d'objectif, "
    "puis on recommence en supprimant une cause : contrainte de mémoire, contrainte de chevauchement, "
    "ou risque (critère déterministe, sans nuage ni panne). La raison affichée est le plus petit "
    "ensemble de causes dont la suppression annule la perte ; « ou » sépare des alternatives."
)

if st.button("Diagnostiquer les images écartées"):
    try:
        with st.spinner("Résolutions en cours…"):
            diags = {c: diagnostiquer_exclusions(donnees, c, alpha)[1]
                     for c in dict.fromkeys(["pessimiste", "optimiste", critere])}
    except Exception as e:
        st.error(f"Erreur lors du diagnostic : {e}")
    else:
        ss["diagnostic"] = {"diags": diags, "donnees": donnees, "critere": critere, "alpha": alpha}

if "diagnostic" in ss:
    diag = ss["diagnostic"]
    if diag["donnees"] != donnees or diag["critere"] != critere or diag["alpha"] != alpha:
        st.warning("Les données ou le critère ont changé depuis ce diagnostic : relancez-le.")
    lignes = diag["diags"][diag["critere"]]
    st.markdown(f"**Critère {nom_critere(diag['critere'], diag['alpha'])}**")
    if lignes:
        st.dataframe(pd.DataFrame([
            {"image": g["image"], "type": g["type"], "PA": g["PA"], "PM": g["PM"],
             "gain espéré max": round(g["gain espéré max"], 4),
             "perte si imposée": round(g["perte si imposée"], 4),
             "raison": " ou ".join(g["raisons"])}
            for g in lignes
        ]), width="stretch", hide_index=True)
    else:
        st.write("Toutes les images sont retenues.")

    def ecartees(c):
        return {g["image"] for g in diag["diags"][c] if not g["raisons"][0].startswith("ex æquo")}

    systematiques = sorted(ecartees("pessimiste") & ecartees("optimiste"))
    st.info(f"Images écartées à la fois par le plan pessimiste et par le plan optimiste "
            f"(hors ex æquo) : {systematiques or 'aucune'}")

st.markdown("---")
st.caption(
    "Astuce : chargez un jeu du projet, modifiez le tableau, les paramètres ou le critère, "
    "puis relancez l'optimisation. L'export JSON peut être réimporté par la barre latérale."
)