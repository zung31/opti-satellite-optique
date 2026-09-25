# Interface Streamlit pour le problème de planification de prise de vue (sans incertitude)
# Basée sur le modèle de résolution d'Hélène Fargier (oct 2025)
#
# Installation nécessaire :
#   pip install streamlit pyscipopt pandas matplotlib
#
# Lancement :
#   streamlit run interface_spot.py

import json
from itertools import product

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from pyscipopt import Model, quicksum

st.set_page_config(page_title="Planification de prise de vue", layout="wide")

# -----------------------------------------------------------------------
# Essai de chargement des données par défaut depuis spotProba3.py si présent
# -----------------------------------------------------------------------
DEFAULT_LOADED = False
try:
    from spotProba3 import (
        nbImages as D_nbImages,
        nbInstruments as D_nbInstruments,
        PA as D_PA,
        DD as D_DD,
        AN as D_AN,
        VI as D_VI,
        DU as D_DU,
        TY as D_TY,
        PM as D_PM,
        PMmax as D_PMmax,
    )
    DEFAULT_LOADED = True
except Exception:
    D_nbImages, D_nbInstruments = 8, 3
    D_PA, D_DD, D_AN, D_TY, D_PM = None, None, None, None, None
    D_VI, D_DU, D_PMmax = 1.0, 5.0, 100.0


# -----------------------------------------------------------------------
# Construction du DataFrame d'images (édition dans l'interface)
# -----------------------------------------------------------------------
def build_default_images_df(nb_images, nb_instruments):
    rows = []
    for i in range(nb_images):
        row = {"id": i, "PA": 5, "TY": 1, "PM": 10}
        for j in range(nb_instruments):
            row[f"DD_{j}"] = float(i * 10)
            row[f"AN_{j}"] = 0.0
        rows.append(row)
    df = pd.DataFrame(rows)
    if D_PA is not None:
        for i in range(min(nb_images, len(D_PA))):
            df.loc[i, "PA"] = D_PA[i]
            df.loc[i, "TY"] = D_TY[i]
            df.loc[i, "PM"] = D_PM[i]
            for j in range(nb_instruments):
                df.loc[i, f"DD_{j}"] = D_DD[i][j]
                df.loc[i, f"AN_{j}"] = D_AN[i][j]
    return df


# -----------------------------------------------------------------------
# Import d'un fichier de données au format "spotProba" (.py)
# -----------------------------------------------------------------------
ALLOWED_VARS = {
    "nbImages", "nbInstruments", "PA", "DD", "AN", "VI", "DU", "TY", "PM",
    "PMmax", "Failure", "ProbaInf", "ProbaSup",
}


def parse_spotproba_py(file_bytes):
    """Exécute un fichier .py du style spotProba3.py et renvoie ses variables.

    Le fichier ne contient que des affectations de listes/nombres (pas
    d'imports ni d'appels), il est donc exécuté sans builtins pour rester
    prudent, mais gardez à l'esprit que ce fichier doit venir d'une source
    de confiance.
    """
    code = file_bytes.decode("utf-8")
    namespace = {}
    exec(compile(code, "<donnees_spotproba>", "exec"), {"__builtins__": {}}, namespace)
    data = {k: v for k, v in namespace.items() if k in ALLOWED_VARS}
    missing = {"nbImages", "nbInstruments", "PA", "DD", "AN", "VI", "DU", "TY", "PM", "PMmax"} - data.keys()
    if missing:
        raise ValueError(f"Variables manquantes dans le fichier importé : {sorted(missing)}")
    return data


def images_df_from_spotproba(data):
    nbImages = data["nbImages"]
    nbInstruments = data["nbInstruments"]
    PA, TY, PM, DD, AN = data["PA"], data["TY"], data["PM"], data["DD"], data["AN"]
    ProbaInf = data.get("ProbaInf")
    ProbaSup = data.get("ProbaSup")
    rows = []
    for i in range(nbImages):
        row = {"id": i, "PA": PA[i], "TY": TY[i], "PM": PM[i]}
        for j in range(nbInstruments):
            row[f"DD_{j}"] = DD[i][j]
            row[f"AN_{j}"] = AN[i][j]
        if ProbaInf is not None:
            row["ProbaInf"] = ProbaInf[i]
        if ProbaSup is not None:
            row["ProbaSup"] = ProbaSup[i]
        rows.append(row)
    return pd.DataFrame(rows)


st.title("🛰️ Planification de prise de vue — interface de résolution")
st.caption(
    "Modèle : maximisation de la somme des payoffs (sans prise en compte de "
    "l'incertitude), résolu avec SCIP (`pyscipopt`)."
)

if DEFAULT_LOADED:
    st.success("Données par défaut chargées depuis spotProba3.py")
else:
    st.info(
        "Aucun module `spotProba3.py` trouvé à côté de cette app : "
        "des données d'exemple modifiables ont été générées."
    )

# -----------------------------------------------------------------------
# Valeurs initiales des paramètres (une seule fois)
# -----------------------------------------------------------------------
for key, default in [
    ("nbImages", int(D_nbImages)), ("nbInstruments", int(D_nbInstruments)),
    ("VI", float(D_VI)), ("DU", float(D_DU)), ("PMmax", float(D_PMmax)),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# -----------------------------------------------------------------------
# Paramètres globaux (barre latérale) + import du fichier de données
# -----------------------------------------------------------------------
with st.sidebar:
    st.header("Paramètres globaux")

    uploaded = st.file_uploader(
        "Importer un fichier de données Python (ex: spotProba3.py)",
        type=["py"],
        help="Le fichier doit définir nbImages, nbInstruments, PA, DD, AN, "
             "VI, DU, TY, PM, PMmax (comme spotProba3.py).",
    )

    if uploaded is not None and st.session_state.get("uploaded_name") != uploaded.name:
        try:
            data = parse_spotproba_py(uploaded.getvalue())
        except Exception as e:
            st.error(f"Impossible de lire le fichier importé : {e}")
            st.stop()

        # On met à jour l'état AVANT de créer les widgets ci-dessous, pour
        # que les champs (nombre d'images, VI, DU...) reflètent le fichier importé
        st.session_state["images_df"] = images_df_from_spotproba(data)
        st.session_state["uploaded_name"] = uploaded.name
        st.session_state["failure"] = data.get("Failure")
        st.session_state["nbImages"] = int(data["nbImages"])
        st.session_state["nbInstruments"] = int(data["nbInstruments"])
        st.session_state["VI"] = float(data["VI"])
        st.session_state["DU"] = float(data["DU"])
        st.session_state["PMmax"] = float(data["PMmax"])
        st.success(
            f"Fichier « {uploaded.name} » importé : "
            f"{data['nbImages']} images, {data['nbInstruments']} instruments."
        )

    nbImages = st.number_input("Nombre d'images", min_value=1, max_value=500,
                                step=1, key="nbImages")
    nbInstruments = st.number_input("Nombre d'instruments", min_value=1, max_value=10,
                                     step=1, key="nbInstruments")
    VI = st.number_input("VI (vitesse)", key="VI")
    DU = st.number_input("DU (durée de prise de vue)", key="DU")
    PMmax = st.number_input("PMmax (mémoire max embarquée)", key="PMmax")

    st.markdown("---")
    if st.button("🔄 Régénérer le tableau à partir des paramètres ci-dessus"):
        st.session_state.pop("images_df", None)
        st.session_state.pop("failure", None)

# -----------------------------------------------------------------------
# Chargement / édition des données d'images
# -----------------------------------------------------------------------
if "images_df" not in st.session_state or len(st.session_state["images_df"]) != nbImages:
    st.session_state["images_df"] = build_default_images_df(nbImages, nbInstruments)

st.subheader("1. Données des images (éditables)")
st.caption(
    "TY = 1 (mono) ou 2 (stéréo). DD_j = date de début sur l'instrument j, "
    "AN_j = angle sur l'instrument j. PA = payoff, PM = mémoire requise. "
    "Si le fichier importé contient ProbaInf/ProbaSup, elles sont affichées "
    "mais ne sont pas utilisées par ce modèle sans incertitude."
)
if st.session_state.get("failure"):
    st.caption(
        "Probabilité de panne par instrument (Failure), informative uniquement : "
        + ", ".join(
            f"instrument {j} = {p}" for j, p in enumerate(st.session_state["failure"])
        )
    )
edited_df = st.data_editor(
    st.session_state["images_df"],
    num_rows="fixed",
    use_container_width=True,
    key="editor",
)
st.session_state["images_df"] = edited_df

# Bouton d'export des données actuelles
export_payload = {
    "nbInstruments": int(nbInstruments),
    "VI": VI,
    "DU": DU,
    "PMmax": PMmax,
    "images": edited_df.to_dict(orient="records"),
}
st.download_button(
    "💾 Exporter les données (JSON)",
    data=json.dumps(export_payload, indent=2),
    file_name="donnees_prise_de_vue.json",
    mime="application/json",
)

# -----------------------------------------------------------------------
# Résolution
# -----------------------------------------------------------------------
st.subheader("2. Résolution")

def solve(df, nbInstruments, VI, DU, PMmax):
    nbImages = len(df)
    PA = df["PA"].tolist()
    TY = df["TY"].tolist()
    PM = df["PM"].tolist()
    DD = [[df.loc[i, f"DD_{j}"] for j in range(nbInstruments)] for i in range(nbImages)]
    AN = [[df.loc[i, f"AN_{j}"] for j in range(nbInstruments)] for i in range(nbImages)]

    mymodel = Model()
    mymodel.hideOutput(True)

    selection = {i: mymodel.addVar(vtype="B", name=f"select{i}") for i in range(nbImages)}
    assignedTo = {
        i: {j: mymodel.addVar(vtype="B", name=f"assignto{i}_{j}") for j in range(nbInstruments)}
        for i in range(nbImages)
    }

    mymodel.setObjective(
        quicksum(PA[i] * selection[i] for i in range(nbImages)), sense="maximize"
    )

    mymodel.addCons(quicksum(PM[i] * selection[i] for i in range(nbImages)) <= PMmax)

    for i in range(nbImages):
        if TY[i] == 1:
            mymodel.addCons(
                quicksum(assignedTo[i][ins] for ins in range(nbInstruments)) == selection[i]
            )

    for i in range(nbImages):
        if TY[i] == 2:
            if nbInstruments < 3:
                raise ValueError(
                    f"L'image {i} est stéréo (TY=2) mais il faut au moins 3 instruments "
                    "(indices 0, 1, 2) pour ce type."
                )
            mymodel.addCons(assignedTo[i][0] == selection[i])
            mymodel.addCons(assignedTo[i][1] == 0)
            mymodel.addCons(assignedTo[i][2] == selection[i])

    for ima1, ima2 in product(range(nbImages), range(nbImages)):
        if ima1 < ima2:
            for ins in range(nbInstruments):
                if abs(DD[ima1][ins] - DD[ima2][ins]) * VI < DU * VI + abs(
                    AN[ima1][ins] - AN[ima2][ins]
                ):
                    mymodel.addCons(assignedTo[ima1][ins] + assignedTo[ima2][ins] <= 1)

    mymodel.optimize()

    status = mymodel.getStatus()
    result_rows = []
    obj_val = None
    if status == "optimal":
        obj_val = mymodel.getObjVal()
        for ima in range(nbImages):
            for ins in range(nbInstruments):
                if mymodel.getVal(assignedTo[ima][ins]) > 0.5:
                    result_rows.append(
                        {
                            "image": ima,
                            "instrument": ins,
                            "debut": DD[ima][ins],
                            "fin": DD[ima][ins] + DU,
                            "payoff": PA[ima],
                        }
                    )
    return status, obj_val, pd.DataFrame(result_rows)


run = st.button("▶️ Lancer l'optimisation", type="primary")

if run:
    try:
        status, obj_val, res_df = solve(edited_df, int(nbInstruments), VI, DU, PMmax)
    except Exception as e:
        st.error(f"Erreur lors de la résolution : {e}")
        st.stop()

    st.write(f"**Statut du solveur : ** `{status}`")

    if status == "optimal":
        st.success(f"Solution optimale trouvée — valeur de l'objectif : {obj_val}")

        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown("**Images sélectionnées et affectées**")
            st.dataframe(res_df, use_container_width=True)
            st.metric("Images sélectionnées", len(res_df))
            st.metric("Payoff total", obj_val)

        with col2:
            st.markdown("**Planning par instrument (Gantt)**")
            if not res_df.empty:
                fig, ax = plt.subplots(figsize=(6, 3 + 0.3 * res_df["instrument"].nunique()))
                instruments = sorted(res_df["instrument"].unique())
                y_positions = {ins: k for k, ins in enumerate(instruments)}
                for _, r in res_df.iterrows():
                    y = y_positions[r["instrument"]]
                    ax.barh(y, r["fin"] - r["debut"], left=r["debut"], height=0.5)
                    ax.text(
                        r["debut"], y, f"img{int(r['image'])}",
                        va="center", ha="left", fontsize=8
                    )
                ax.set_yticks(list(y_positions.values()))
                ax.set_yticklabels([f"instrument {i}" for i in instruments])
                ax.set_xlabel("temps")
                st.pyplot(fig)
            else:
                st.write("Aucune image sélectionnée.")
    else:
        st.warning("Pas de solution optimale trouvée pour ce statut.")

st.markdown("---")
st.caption(
    "Astuce : modifiez le tableau d'images ou les paramètres globaux puis relancez "
    "l'optimisation. Vous pouvez aussi exporter/importer vos jeux de données en JSON."
)
