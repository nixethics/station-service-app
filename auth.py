import streamlit as st
import bcrypt
from utils import conn


def verifier_identifiants(email: str, mot_de_passe: str):
    """Retourne le dict utilisateur si OK, sinon None"""
    result = (conn.table("utilisateurs")
              .select("*")
              .eq("email", email.strip().lower())
              .eq("actif", True)
              .execute())

    if not result.data:
        return None

    utilisateur = result.data[0]
    hash_stocke = utilisateur["mot_de_passe_hash"].encode("utf-8")

    if bcrypt.checkpw(mot_de_passe.encode("utf-8"), hash_stocke):
        return utilisateur

    return None


def ecran_connexion():
    """Affiche le formulaire de connexion. Retourne l'utilisateur si connecté."""
    # Si déjà connecté dans la session
    if "utilisateur" in st.session_state and st.session_state.utilisateur:
        return st.session_state.utilisateur

    st.markdown(
        """
        <div style='text-align: center; padding: 40px 0 20px 0;'>
            <h1>⛽ Station-Service</h1>
            <p style='color: #888;'>Connectez-vous pour accéder à l'application</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("form_connexion"):
            email = st.text_input("Email", placeholder="nom@station.com")
            mot_de_passe = st.text_input("Mot de passe", type="password")
            submit = st.form_submit_button("Se connecter", use_container_width=True)

            if submit:
                if not email or not mot_de_passe:
                    st.error("Veuillez remplir tous les champs.")
                else:
                    utilisateur = verifier_identifiants(email, mot_de_passe)
                    if utilisateur:
                        st.session_state.utilisateur = utilisateur
                        st.rerun()
                    else:
                        st.error("❌ Email ou mot de passe incorrect.")

    return None


def deconnexion():
    """Déconnecte l'utilisateur"""
    if "utilisateur" in st.session_state:
        del st.session_state.utilisateur
    st.rerun()


def utilisateur_actuel():
    return st.session_state.get("utilisateur")


def role_actuel():
    u = utilisateur_actuel()
    return u["role"] if u else None