import streamlit as st
from utils import conn


def afficher():
    st.header("⚙️ Administration")
    st.warning("⚠️ Zone sensible. Les actions ci-dessous sont **irréversibles**.")

    st.subheader("Statistiques actuelles")

    tables = ["mouvements_journaliers", "ventes_pompe", "achats", "factures"]
    for t in tables:
        try:
            res = conn.table(t).select("id", count="exact").execute()
            count = res.count if res.count is not None else len(res.data)
            st.write(f"- **{t}** : {count} enregistrement(s)")
        except Exception as e:
            st.write(f"- **{t}** : erreur ({e})")

    st.markdown("---")
    st.subheader("🗑️ Vider les données de test")

    st.caption(
        "Cette action supprime **toutes** les lignes des tables : "
        "mouvements_journaliers, ventes_pompe, achats, factures, factures_lignes. "
        "Les tables carburants et utilisateurs sont conservées."
    )

    confirmation = st.text_input(
        "Tapez **SUPPRIMER** pour confirmer",
        key="confirm_suppression",
    )

    if st.button("🗑️ Vider toutes les données", type="primary",
                 disabled=(confirmation != "SUPPRIMER")):
        try:
            for t in ["factures_lignes", "factures", "ventes_pompe",
                      "mouvements_journaliers", "achats"]:
                # Supabase exige un filtre pour delete : on filtre sur id > 0
                conn.table(t).delete().gt("id", 0).execute()
            st.success("✅ Toutes les données de test ont été supprimées.")
            st.balloons()
        except Exception as e:
            st.error(f"Erreur : {e}")