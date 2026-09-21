import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils import (
    get_stock_fin_veille,
    get_prix_actuel,
    get_carburants,
    sauvegarder_mouvement,
    log_audit,
    conn,
)


# ============================================================
# Onglet 1 — Saisie du jour
# ============================================================
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


# ============================================================
# Onglet 2 — Totaux mensuels
# ============================================================
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


# ============================================================
# Onglet 3 — Charges
# ============================================================
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


# ============================================================
# Onglet 4 — Réceptions / Commandes
# ============================================================
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


# ============================================================
# Onglet 5 — Historique et correction
# ============================================================
def onglet_historique():
    st.subheader("📜 Historique et correction")
    st.caption("Consultez, filtrez et corrigez les mouvements journaliers. "
               "Cliquez sur le cadenas pour déverrouiller une ligne et la modifier.")

    col1, col2 = st.columns(2)
    with col1:
        debut = st.date_input("Du", value=date.today() - timedelta(days=30),
                              key="hist_debut")
    with col2:
        fin = st.date_input("Au", value=date.today(), key="hist_fin")

    res = (conn.table("mouvements_journaliers")
           .select("*")
           .gte("date", debut.isoformat())
           .lte("date", fin.isoformat())
           .order("date", desc=True)
           .execute())

    if not res.data:
        st.info("Aucun mouvement sur cette période.")
        return

    df = pd.DataFrame(res.data)
    carburants = {c["id"]: c["nom"] for c in
                  conn.table("carburants").select("id,nom").execute().data}
    df["carburant"] = df["carburant_id"].map(carburants)

    if "lignes_deverrouillees" not in st.session_state:
        st.session_state.lignes_deverrouillees = set()

    st.caption(f"{len(df)} mouvement(s) sur la période")

    for _, m in df.iterrows():
        ligne_id = m["id"]
        deverrouillee = ligne_id in st.session_state.lignes_deverrouillees

        col1, col2, col3, col4, col5, col6 = st.columns([2, 1.5, 1.5, 1.5, 1.5, 0.8])

        with col1:
            st.write(f"**{m['date']}** — {m['carburant']}")
        with col2:
            st.write(f"Ventes : {m['ventes']:.0f} L")
        with col3:
            st.write(f"Stock fin : {m['stock_fin']:.0f} L")
        with col4:
            st.write(f"Recette : {m['recette']:,.0f} F")
        with col5:
            if m.get("notes"):
                st.caption(f"⚠️ {m['notes']}")
        with col6:
            icone = "🔓" if deverrouillee else "🔒"
            if st.button(icone, key=f"cadenas_{ligne_id}",
                         help="Déverrouiller pour modifier" if not deverrouillee
                              else "Verrouiller"):
                if deverrouillee:
                    st.session_state.lignes_deverrouillees.discard(ligne_id)
                else:
                    st.session_state.lignes_deverrouillees.add(ligne_id)
                st.rerun()

        if deverrouillee:
            with st.form(f"form_edit_{ligne_id}"):
                st.markdown(f"**Modification de la ligne du {m['date']} — {m['carburant']}**")

                c1, c2, c3 = st.columns(3)
                with c1:
                    new_stock_debut = st.number_input(
                        "Stock début", value=float(m["stock_debut"]),
                        step=1.0, key=f"sd_{ligne_id}"
                    )
                    new_entrees = st.number_input(
                        "Entrées", value=float(m["entrees"]),
                        step=1.0, key=f"en_{ligne_id}"
                    )
                with c2:
                    new_ventes = st.number_input(
                        "Ventes", value=float(m["ventes"]),
                        step=1.0, key=f"ve_{ligne_id}"
                    )
                    new_prix = st.number_input(
                        "Prix/L", value=float(m["prix_vente"]),
                        step=10.0, key=f"pr_{ligne_id}"
                    )
                with c3:
                    new_jauge = st.number_input(
                        "Jauge réelle (0 si non renseigné)",
                        value=float(m["jauge_reelle"]) if m.get("jauge_reelle") else 0.0,
                        step=1.0, key=f"ja_{ligne_id}"
                    )
                    new_montant_reel = st.number_input(
                        "Montant réel reçu (0 si non renseigné)",
                        value=float(m["montant_reel_recu"]) if m.get("montant_reel_recu") else 0.0,
                        step=100.0, key=f"mr_{ligne_id}"
                    )

                new_notes = st.text_input(
                    "Notes", value=m.get("notes") or "",
                    key=f"no_{ligne_id}"
                )

                new_stock_fin = new_stock_debut + new_entrees - new_ventes
                new_recette = new_ventes * new_prix
                new_perte = (new_jauge - new_stock_fin) if new_jauge > 0 else None

                c1, c2, c3 = st.columns(3)
                c1.metric("Nouveau stock fin", f"{new_stock_fin:,.0f} L")
                c2.metric("Nouvelle recette", f"{new_recette:,.0f} F")
                if new_perte is not None:
                    c3.metric("Nouvelle perte", f"{new_perte:,.0f} L")

                col_save, col_cancel = st.columns(2)
                with col_save:
                    save = st.form_submit_button("💾 Enregistrer les modifications",
                                                 use_container_width=True)
                with col_cancel:
                    cancel = st.form_submit_button("❌ Annuler",
                                                   use_container_width=True)

                if save:
                    nouvelle = {
                        "stock_debut": new_stock_debut,
                        "entrees": new_entrees,
                        "ventes": new_ventes,
                        "stock_fin": new_stock_fin,
                        "prix_vente": new_prix,
                        "recette": new_recette,
                        "jauge_reelle": new_jauge if new_jauge > 0 else None,
                        "perte": new_perte,
                        "montant_reel_recu": new_montant_reel if new_montant_reel > 0 else None,
                        "notes": new_notes or None,
                    }
                    ancienne = {
                        "stock_debut": m["stock_debut"],
                        "entrees": m["entrees"],
                        "ventes": m["ventes"],
                        "stock_fin": m["stock_fin"],
                        "prix_vente": m["prix_vente"],
                        "recette": m["recette"],
                        "jauge_reelle": m.get("jauge_reelle"),
                        "perte": m.get("perte"),
                        "montant_reel_recu": m.get("montant_reel_recu"),
                        "notes": m.get("notes"),
                    }
                    try:
                        conn.table("mouvements_journaliers").update(
                            nouvelle
                        ).eq("id", ligne_id).execute()

                        u = st.session_state.get("utilisateur", {})
                        nom_user = u.get("nom", "inconnu") if u else "inconnu"
                        log_audit(
                            utilisateur=nom_user,
                            table_cible="mouvements_journaliers",
                            ligne_id=ligne_id,
                            action="modification",
                            ancienne=ancienne,
                            nouvelle=nouvelle,
                        )

                        st.session_state.lignes_deverrouillees.discard(ligne_id)
                        st.success("Ligne modifiée ✅")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur : {e}")

                if cancel:
                    st.session_state.lignes_deverrouillees.discard(ligne_id)
                    st.rerun()

        st.markdown("---")

    st.markdown("### 🔍 Journal des modifications récentes")
    res_log = (conn.table("audit_log")
               .select("*")
               .eq("table_cible", "mouvements_journaliers")
               .order("date_action", desc=True)
               .limit(20)
               .execute())

    if not res_log.data:
        st.caption("Aucune modification enregistrée.")
    else:
        df_log = pd.DataFrame(res_log.data)
        df_log["date_action"] = pd.to_datetime(df_log["date_action"])
        st.dataframe(
            df_log[["date_action", "utilisateur", "ligne_id",
                    "action", "ancienne_valeur", "nouvelle_valeur"]],
            use_container_width=True,
        )


# ============================================================
# Fonction principale
# ============================================================
def afficher():
    st.header("📝 Espace Comptable")

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "✍️ Saisie du jour",
        "📅 Totaux mensuels",
        "💰 Charges",
        "📦 Réceptions / Commandes",
        "📜 Historique et correction",
    ])
    with tab1:
        onglet_saisie_jour()
    with tab2:
        onglet_totaux_mensuels()
    with tab3:
        onglet_charges()
    with tab4:
        onglet_receptions_commandes()
    with tab5:
        onglet_historique()