import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils import (
    get_stock_fin_veille,
    get_prix_actuel,
    get_carburants,
    sauvegarder_mouvement,
    conn,
)


def onglet_saisie_jour():
    st.subheader("Saisie du jour")

    jour = st.date_input("Date", value=date.today(), key="saisie_jour")

    carburants = get_carburants()
    saisies = []

    for c in carburants:
        st.markdown(f"### {c['nom']}")
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

    if st.button("💾 Enregistrer le jour", type="primary", key="btn_saisie"):
        for s in saisies:
            s["date"] = jour.isoformat()
            sauvegarder_mouvement(s)
        st.success("Journée enregistrée ✅")
        st.balloons()

 

def onglet_totaux_mensuels():
    st.subheader("📅 Totaux mensuels")

    mois_options = []
    today = date.today()
    for i in range(12):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        mois_options.append(date(y, m, 1))

    mois = st.selectbox(
        "Mois",
        mois_options,
        format_func=lambda d: d.strftime("%B %Y"),
        key="mois_totaux",
    )

    debut_mois = mois
    if mois.month == 12:
        fin_mois = date(mois.year + 1, 1, 1) - timedelta(days=1)
    else:
        fin_mois = date(mois.year, mois.month + 1, 1) - timedelta(days=1)

    res_c = (conn.table("mouvements_journaliers")
             .select("*")
             .gte("date", debut_mois.isoformat())
             .lte("date", fin_mois.isoformat())
             .execute())
    df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()

    res_p = (conn.table("ventes_pompe")
             .select("*")
             .gte("horodatage", f"{debut_mois.isoformat()}T00:00:00")
             .lte("horodatage", f"{fin_mois.isoformat()}T23:59:59")
             .execute())
    df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame()

    carburants = {c["id"]: c["nom"] for c in
                  conn.table("carburants").select("id,nom").execute().data}

    st.markdown("### Côté Comptable (saisie manuelle)")
    if df_c.empty:
        st.info("Aucune donnée comptable pour ce mois.")
    else:
        df_c["carburant"] = df_c["carburant_id"].map(carburants)
        recap = df_c.groupby("carburant").agg(
            litres=("ventes", "sum"),
            recette=("recette", "sum"),
            reel=("montant_reel_recu", lambda x: x.fillna(0).sum()),
        )
        recap["prix_moyen"] = (recap["recette"] / recap["litres"]).fillna(0)
        recap["ecart_caisse"] = recap["reel"] - recap["recette"]

        st.dataframe(recap, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total litres", f"{recap['litres'].sum():,.0f} L")
        col2.metric("Recette attendue", f"{recap['recette'].sum():,.0f} F")
        col3.metric("Recette réelle", f"{recap['reel'].sum():,.0f} F")

    st.markdown("### Côté Pompiste (temps réel)")
    if df_p.empty:
        st.info("Aucune vente pompiste pour ce mois.")
    else:
        df_p["carburant"] = df_p["carburant_id"].map(carburants)
        recap_p = df_p.groupby("carburant").agg(
            nb_ventes=("id", "count"),
            litres=("litres", "sum"),
            recette=("montant", "sum"),
        )
        st.dataframe(recap_p, use_container_width=True)

        col1, col2, col3 = st.columns(3)
        col1.metric("Total ventes", f"{len(df_p)}")
        col2.metric("Total litres", f"{recap_p['litres'].sum():,.0f} L")
        col3.metric("Recette totale", f"{recap_p['recette'].sum():,.0f} F")

    st.markdown("### Comparaison")
    if not df_c.empty and not df_p.empty:
        comparaison = pd.DataFrame({
            "Comptable (L)": df_c.groupby("carburant")["ventes"].sum(),
            "Pompiste (L)": df_p.groupby("carburant")["litres"].sum(),
        }).fillna(0)
        comparaison["Écart (L)"] = comparaison["Pompiste (L)"] - comparaison["Comptable (L)"]
        st.dataframe(comparaison, use_container_width=True)


def onglet_charges():
    st.subheader("💰 Charges du mois")
    st.caption("Gérez ici les charges fixes (mensuelles) et variables "
               "(ponctuelles) pour un mois donné.")

    mois_options = []
    today = date.today()
    for i in range(12):
        m = today.month - i
        y = today.year
        while m <= 0:
            m += 12
            y -= 1
        mois_options.append(date(y, m, 1))

    mois = st.selectbox(
        "Mois concerné",
        mois_options,
        format_func=lambda d: d.strftime("%B %Y"),
        key="mois_charges",
    )
    mois_iso = mois.isoformat()

    # === Ajouter une charge ===
    st.markdown("### ➕ Ajouter une charge")

    with st.form("form_charge"):
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            type_charge = st.selectbox(
                "Type", ["fixe", "variable"], key="ch_type"
            )
        with col2:
            libelle = st.text_input("Libellé", key="ch_libelle",
                                    placeholder="Ex: Électricité, Salaires...")
        with col3:
            montant = st.number_input("Montant (F)", min_value=0.0,
                                      step=1000.0, key="ch_montant")

        notes = st.text_input("Notes (optionnel)", key="ch_notes")

        submit = st.form_submit_button("💾 Enregistrer la charge",
                                       use_container_width=True)

        if submit:
            if not libelle or montant <= 0:
                st.error("Renseignez un libellé et un montant > 0.")
            else:
                try:
                    conn.table("charges").upsert({
                        "mois": mois_iso,
                        "type": type_charge,
                        "libelle": libelle.strip(),
                        "montant": montant,
                        "notes": notes or None,
                    }, on_conflict="mois,type,libelle").execute()
                    st.success("Charge enregistrée ✅")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erreur : {e}")

    # === Liste des charges du mois ===
    st.markdown("### 📋 Charges enregistrées")

    result = (conn.table("charges")
              .select("*")
              .eq("mois", mois_iso)
              .order("type")
              .order("libelle")
              .execute())

    if not result.data:
        st.info("Aucune charge pour ce mois.")
        return

    df = pd.DataFrame(result.data)

    fixes = df[df["type"] == "fixe"]
    variables = df[df["type"] == "variable"]

    st.markdown("#### 🔒 Charges fixes")
    if fixes.empty:
        st.caption("Aucune charge fixe")
    else:
        for _, c in fixes.iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(c["libelle"])
            with col2:
                st.write(f"{c['montant']:,.0f} F")
            with col3:
                if st.button("🗑️", key=f"del_fixe_{c['id']}"):
                    conn.table("charges").delete().eq("id", c["id"]).execute()
                    st.rerun()
        st.markdown(f"**Sous-total charges fixes : {fixes['montant'].sum():,.0f} F**")

    st.markdown("#### 🔄 Charges variables")
    if variables.empty:
        st.caption("Aucune charge variable")
    else:
        for _, c in variables.iterrows():
            col1, col2, col3 = st.columns([3, 2, 1])
            with col1:
                st.write(c["libelle"])
            with col2:
                st.write(f"{c['montant']:,.0f} F")
            with col3:
                if st.button("🗑️", key=f"del_var_{c['id']}"):
                    conn.table("charges").delete().eq("id", c["id"]).execute()
                    st.rerun()
        st.markdown(f"**Sous-total charges variables : {variables['montant'].sum():,.0f} F**")

    total = df["montant"].sum()
    st.markdown(f"## Total général du mois : {total:,.0f} F")

    # === Comparaison avec la recette du mois ===
    st.markdown("### 📊 Marge brute (Recettes − Charges)")

    res_m = (conn.table("mouvements_journaliers")
             .select("recette")
             .gte("date", mois_iso)
             .lte("date", (mois.replace(day=1) + timedelta(days=32)).replace(day=1).isoformat())
             .execute())
    recette_totale = sum(r["recette"] for r in res_m.data) if res_m.data else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Recettes du mois", f"{recette_totale:,.0f} F")
    col2.metric("Charges du mois", f"{total:,.0f} F")
    marge = recette_totale - total
    if marge >= 0:
        col3.metric("Marge", f"{marge:,.0f} F")
    else:
        col3.metric("Déficit", f"{marge:,.0f} F")



def onglet_receptions_commandes():
    st.subheader("📦 Réceptions et Commandes")

    carburants = get_carburants()
    noms_carb = [c["nom"] for c in carburants]

    type_op = st.radio(
        "Type d'opération",
        ["Réception (BL)", "Commande (BC)"],
        horizontal=True,
        key="type_op",
    )

    with st.form("form_operation"):
        col1, col2 = st.columns(2)
        with col1:
            carburant_nom = st.selectbox("Carburant", noms_carb, key="op_carb")
            date_op = st.date_input("Date", value=date.today(), key="op_date")
            numero = st.text_input(
                "N° BL" if "Réception" in type_op else "N° BC",
                key="op_numero"
            )
        with col2:
            quantite = st.number_input(
                "Quantité (L)", min_value=0.0, step=1.0, key="op_qte"
            )
            fournisseur = st.text_input("Fournisseur (optionnel)", key="op_fourn")

        submit = st.form_submit_button("💾 Enregistrer", use_container_width=True)

        if submit:
            c = next(x for x in carburants if x["nom"] == carburant_nom)
            data = {
                "date": date_op.isoformat(),
                "carburant_id": c["id"],
                "quantite": quantite if "Réception" in type_op else 0,
                "quantite_commandee": quantite if "Commande" in type_op else None,
                "prix_unitaire": 0,
                "montant": 0,
                "fournisseur": fournisseur or None,
                "type_operation": "reception" if "Réception" in type_op else "commande",
            }
            if "Réception" in type_op:
                data["numero_bl"] = numero or None
            else:
                data["numero_bc"] = numero or None

            try:
                conn.table("achats").insert(data).execute()
                st.success("Enregistré ✅")
                st.rerun()
            except Exception as e:
                st.error(f"Erreur : {e}")

    st.markdown("---")
    st.markdown("### Opérations du mois en cours")

    today = date.today()
    debut_mois = today.replace(day=1)
    res = (conn.table("achats")
           .select("*")
           .gte("date", debut_mois.isoformat())
           .order("date", desc=True)
           .execute())

    if res.data:
        df = pd.DataFrame(res.data)
        df["carburant"] = df["carburant_id"].map({c["id"]: c["nom"] for c in carburants})
        cols = ["date", "type_operation", "carburant", "numero_bl",
                "numero_bc", "quantite", "quantite_commandee", "fournisseur"]
        cols = [c for c in cols if c in df.columns]
        st.dataframe(df[cols], use_container_width=True)
    else:
        st.info("Aucune opération ce mois.")


def afficher():
    st.header("📝 Espace Comptable")

    tab1, tab2, tab3, tab4 = st.tabs([
        "✍️ Saisie du jour",
        "📅 Totaux mensuels",
        "💰 Charges",
        "📦 Réceptions / Commandes",
    ])
    with tab1:
        onglet_saisie_jour()
    with tab2:
        onglet_totaux_mensuels()
    with tab3:
        onglet_charges()
    with tab4:
        onglet_receptions_commandes()               