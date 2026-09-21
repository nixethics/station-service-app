import streamlit as st
from datetime import date
from utils import (
    get_stock_fin_veille,
    get_prix_actuel,
    get_carburants,
    sauvegarder_mouvement,
)


def afficher():
    st.header("📝 Saisie du jour (Comptable)")

    jour = st.date_input("Date", value=date.today())

    carburants = get_carburants()
    saisies = []

    for c in carburants:
        st.subheader(c["nom"])
        stock_debut = get_stock_fin_veille(c["id"], jour)
        prix = get_prix_actuel(c["id"])

        st.caption(f"Stock début (reprise veille) : {stock_debut:.0f} L  |  "
                   f"Prix actuel : {prix:.0f} F/L")

        col1, col2, col3 = st.columns(3)
        with col1:
            entrees = st.number_input(
                f"Entrées {c['nom']} (L)",
                min_value=0.0, step=1.0, key=f"e_{c['id']}"
            )
        with col2:
            ventes = st.number_input(
                f"Ventes {c['nom']} (L)",
                min_value=0.0, step=1.0, key=f"v_{c['id']}"
            )
        with col3:
            jauge = st.number_input(
                f"Jauge réelle {c['nom']} (L)",
                min_value=0.0, step=1.0, key=f"j_{c['id']}"
            )

        stock_fin = stock_debut + entrees - ventes
        recette_attendue = ventes * prix
        perte = (jauge - stock_fin) if jauge > 0 else None

        st.markdown("**Recette**")
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric("Recette attendue (ventes × prix)",
                      f"{recette_attendue:,.0f} F")
        with col_b:
            montant_reel = st.number_input(
                f"Montant réel reçu en caisse ({c['nom']})",
                min_value=0.0, step=100.0, key=f"mr_{c['id']}"
            )

        ecart = None
        if montant_reel > 0:
            ecart = montant_reel - recette_attendue
            if abs(ecart) < 1:
                st.success(f"✅ Caisse conforme (écart : {ecart:,.0f} F)")
            elif ecart < 0:
                st.error(f"⚠️ Manque en caisse : {ecart:,.0f} F")
            else:
                st.warning(f"⚠️ Excédent en caisse : +{ecart:,.0f} F")

        c1, c2, c3 = st.columns(3)
        c1.metric("Stock fin", f"{stock_fin:.0f} L")
        c2.metric("Recette attendue", f"{recette_attendue:,.0f} F")
        if perte is not None:
            if perte < 0:
                c3.error(f"⚠️ Perte : {perte:.0f} L")
            else:
                c3.success(f"Écart : +{perte:.0f} L")

        saisies.append({
            "carburant_id": c["id"],
            "stock_debut": stock_debut,
            "entrees": entrees,
            "ventes": ventes,
            "stock_fin": stock_fin,
            "prix_vente": prix,
            "recette": recette_attendue,
            "jauge_reelle": jauge if jauge > 0 else None,
            "perte": perte,
            "montant_reel_recu": montant_reel if montant_reel > 0 else None,
        })

    if st.button("💾 Enregistrer le jour", type="primary"):
        for s in saisies:
            s["date"] = jour.isoformat()
            sauvegarder_mouvement(s)
        st.success("Journée enregistrée ✅")
        st.balloons()