import streamlit as st

st.set_page_config(page_title="Station-Service", layout="wide")

import auth

# === Écran de connexion ===
utilisateur = auth.ecran_connexion()

if not utilisateur:
    st.stop()  # Rien d'autre n'est affiché tant qu'on n'est pas connecté

# === À partir d'ici, l'utilisateur est connecté ===
role = utilisateur["role"]
nom = utilisateur["nom"]

# === Barre latérale : profil + navigation ===
st.sidebar.title("⛽ Station-Service")
st.sidebar.markdown(f"**{nom}**")
st.sidebar.caption(f"Rôle : {role}")
st.sidebar.markdown("---")

# === Définition des vues accessibles selon le rôle ===
VUES_AUTORISEES = {
    "admin":      ["📝 Comptable", "📊 Gérant", "⛽ Pompiste", "📨 Secrétaire"],
    "gerant":     ["📊 Gérant"],
    "comptable":  ["📝 Comptable", "📊 Gérant"],
    "pompiste":   ["⛽ Pompiste", "📨 Secrétaire"],
    "secretaire": ["📨 Secrétaire"],
}

vues = VUES_AUTORISEES.get(role, [])

if not vues:
    st.error("Aucune vue accessible pour votre rôle. Contactez l'administrateur.")
    st.stop()

page = st.sidebar.radio("Navigation", vues)

st.sidebar.markdown("---")
if st.sidebar.button("🚪 Se déconnecter", use_container_width=True):
    auth.deconnexion()

# === Chargement des vues ===
import vue_comptable
import vue_gerant
import vue_pompiste
import vue_secretaire

if page == "📝 Comptable":
    vue_comptable.afficher()
elif page == "📊 Gérant":
    vue_gerant.afficher()
elif page == "⛽ Pompiste":
    vue_pompiste.afficher()
elif page == "📨 Secrétaire":
    vue_secretaire.afficher()