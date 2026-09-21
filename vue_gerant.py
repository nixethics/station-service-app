import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils import conn


def onglet_pompiste():
    st.subheader("🕒 Ventes en temps réel (pompistes)")

    col1, col2 = st.columns(2)
    with col1:
        debut = st.date_input("Du", value=date.today() - timedelta(days=7),
                              key="pomp_debut")
    with col2:
        fin = st.date_input("Au", value=date.today(), key="pomp_fin")

    result = (conn.table("ventes_pompe")
              .select("*")
              .gte("horodatage", f"{debut.isoformat()}T00:00:00")
              .lte("horodatage", f"{fin.isoformat()}T23:59:59")
              .order("horodatage", desc=True)
              .execute())

    if not result.data:
        st.info("Aucune vente pompiste sur cette période.")
        return

    df = pd.DataFrame(result.data)
    df["horodatage"] = pd.to_datetime(df["horodatage"])
    df["jour"] = df["horodatage"].dt.date

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Nb ventes", len(df))
    c2.metric("Litres vendus", f"{df['litres'].sum():,.0f} L")
    c3.metric("Recette attendue", f"{df['montant'].sum():,.0f} F")
    c4.metric("Monnaie rendue", f"{df['monnaie_rendue'].sum():,.0f} F")

    if "graph_pompiste" not in st.session_state:
        st.session_state.graph_pompiste = "Courbe (évolution)"

    graph_type = st.selectbox(
        "Type de graphique",
        ["Courbe (évolution)", "Barres (par jour)", "Camembert (répartition)"],
        key="graph_pompiste",
    )

    par_jour = df.groupby("jour").agg(
        ventes=("id", "count"),
        litres=("litres", "sum"),
        recette=("montant", "sum"),
    ).reset_index()

    carburants = {c["id"]: c["nom"] for c in
                  conn.table("carburants").select("id,nom").execute().data}
    df["carburant"] = df["carburant_id"].map(carburants)

    if graph_type == "Courbe (évolution)":
        st.caption("Évolution journalière des litres et de la recette")
        st.line_chart(par_jour.set_index("jour")[["litres", "recette"]])
    elif graph_type == "Barres (par jour)":
        st.caption("Répartition journalière (barres)")
        st.bar_chart(par_jour.set_index("jour")[["litres", "recette"]])
    else:
        st.caption("Répartition par carburant")
        rep = df.groupby("carburant")["montant"].sum()
        st.bar_chart(rep)

    st.markdown("**Détail par carburant**")
    par_carb = df.groupby("carburant").agg(
        nb_ventes=("id", "count"),
        litres=("litres", "sum"),
        recette=("montant", "sum"),
    )
    st.dataframe(par_carb, use_container_width=True)

    st.markdown("**Détail par pompe**")
    if "pompe" in df.columns and df["pompe"].notna().any():
        df["pompe"] = df["pompe"].fillna(0).astype(int)
        par_pompe = df.groupby("pompe").agg(
            nb_ventes=("id", "count"),
            litres=("litres", "sum"),
            recette=("montant", "sum"),
        )
        st.dataframe(par_pompe, use_container_width=True)

    st.markdown("**Dernières ventes**")
    st.dataframe(
        df[["horodatage", "pompe", "carburant", "litres",
            "montant", "monnaie_rendue", "matricule", "nom_client",
            "envoye"]],
        use_container_width=True,
        height=300,
    )


def onglet_comptable():
    st.subheader("📒 Statistiques Comptable")

    col1, col2 = st.columns(2)
    with col1:
        debut = st.date_input("Du", value=date.today() - timedelta(days=30),
                              key="compt_debut")
    with col2:
        fin = st.date_input("Au", value=date.today(), key="compt_fin")

    result = (conn.table("mouvements_journaliers")
              .select("*")
              .gte("date", debut.isoformat())
              .lte("date", fin.isoformat())
              .order("date")
              .execute())

    if not result.data:
        st.info("Aucune donnée comptable sur cette période.")
        return

    df = pd.DataFrame(result.data)
    carburants = {c["id"]: c["nom"] for c in
                  conn.table("carburants").select("id,nom").execute().data}
    df["carburant"] = df["carburant_id"].map(carburants)

    recette_attendue = df["recette"].sum()
    montant_reel = df["montant_reel_recu"].fillna(0).sum() if "montant_reel_recu" in df else 0
    ecart = montant_reel - recette_attendue

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Recette attendue", f"{recette_attendue:,.0f} F")
    c2.metric("Montant réel reçu", f"{montant_reel:,.0f} F")
    c3.metric("Écart caisse", f"{ecart:,.0f} F")
    pertes = df[df["perte"] < 0] if "perte" in df else pd.DataFrame()
    c4.metric("Jours avec perte", len(pertes))

    if "graph_comptable" not in st.session_state:
        st.session_state.graph_comptable = "Courbe (évolution)"

    graph_type = st.selectbox(
        "Type de graphique",
        ["Courbe (évolution)", "Barres (par jour)",
         "Histogramme (par carburant)", "Camembert (répartition)"],
        key="graph_comptable",
    )

    par_jour = df.groupby("date").agg(
        recette=("recette", "sum"),
        ventes=("ventes", "sum"),
    ).reset_index()
    par_jour["date"] = pd.to_datetime(par_jour["date"])

    par_carb = df.groupby("carburant").agg(
        recette=("recette", "sum"),
        ventes=("ventes", "sum"),
    ).reset_index()

    if graph_type == "Courbe (évolution)":
        st.line_chart(par_jour.set_index("date")[["recette", "ventes"]])
    elif graph_type == "Barres (par jour)":
        st.bar_chart(par_jour.set_index("date")[["recette", "ventes"]])
    elif graph_type == "Histogramme (par carburant)":
        st.bar_chart(par_carb.set_index("carburant")[["recette"]])
    else:
        rep = par_carb.set_index("carburant")["recette"]
        st.bar_chart(rep)

    st.markdown("**Détail journalier**")
    st.dataframe(
        df[["date", "carburant", "stock_debut", "entrees", "ventes",
            "stock_fin", "prix_vente", "recette",
            "montant_reel_recu", "perte"]],
        use_container_width=True,
    )


def onglet_comparatif():
    st.subheader("🔍 Comparatif Pompistes vs Comptable")

    col1, col2 = st.columns(2)
    with col1:
        debut = st.date_input("Du", value=date.today() - timedelta(days=7),
                              key="comp_debut")
    with col2:
        fin = st.date_input("Au", value=date.today(), key="comp_fin")

    res_p = (conn.table("ventes_pompe")
             .select("*")
             .gte("horodatage", f"{debut.isoformat()}T00:00:00")
             .lte("horodatage", f"{fin.isoformat()}T23:59:59")
             .execute())
    df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame()

    res_c = (conn.table("mouvements_journaliers")
             .select("*")
             .gte("date", debut.isoformat())
             .lte("date", fin.isoformat())
             .execute())
    df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()

    if df_p.empty and df_c.empty:
        st.warning("Aucune donnée sur cette période.")
        return

    litres_pompiste = df_p["litres"].sum() if not df_p.empty else 0
    recette_pompiste = df_p["montant"].sum() if not df_p.empty else 0
    litres_comptable = df_c["ventes"].sum() if not df_c.empty else 0
    recette_comptable = df_c["recette"].sum() if not df_c.empty else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Litres — Pompistes", f"{litres_pompiste:,.0f} L")
    col2.metric("Litres — Comptable", f"{litres_comptable:,.0f} L")
    delta_l = litres_comptable - litres_pompiste
    col3.metric("Écart litres", f"{delta_l:,.0f} L")

    col1, col2, col3 = st.columns(3)
    col1.metric("Recette — Pompistes", f"{recette_pompiste:,.0f} F")
    col2.metric("Recette — Comptable", f"{recette_comptable:,.0f} F")
    delta_r = recette_comptable - recette_pompiste
    col3.metric("Écart recette", f"{delta_r:,.0f} F")

    if not df_p.empty and not df_c.empty:
        df_p["jour"] = pd.to_datetime(df_p["horodatage"]).dt.date
        par_jour_p = df_p.groupby("jour").agg(
            litres_pompiste=("litres", "sum"),
            recette_pompiste=("montant", "sum"),
        ).reset_index()
        df_c["jour"] = pd.to_datetime(df_c["date"]).dt.date
        par_jour_c = df_c.groupby("jour").agg(
            litres_comptable=("ventes", "sum"),
            recette_comptable=("recette", "sum"),
        ).reset_index()

        merge = pd.merge(par_jour_p, par_jour_c, on="jour", how="outer").fillna(0)
        merge["ecart_litres"] = merge["litres_comptable"] - merge["litres_pompiste"]
        merge["ecart_recette"] = merge["recette_comptable"] - merge["recette_pompiste"]
        merge = merge.sort_values("jour", ascending=False)

        st.dataframe(merge, use_container_width=True)


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
        key="mois_gerant",
    )

    debut_mois = mois
    if mois.month == 12:
        fin_mois = date(mois.year + 1, 1, 1) - timedelta(days=1)
    else:
        fin_mois = date(mois.year, mois.month + 1, 1) - timedelta(days=1)

    # Comparaison Pompiste vs Comptable par carburant
    res_p = (conn.table("ventes_pompe")
             .select("*")
             .gte("horodatage", f"{debut_mois.isoformat()}T00:00:00")
             .lte("horodatage", f"{fin_mois.isoformat()}T23:59:59")
             .execute())
    df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame()

    res_c = (conn.table("mouvements_journaliers")
             .select("*")
             .gte("date", debut_mois.isoformat())
             .lte("date", fin_mois.isoformat())
             .execute())
    df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()

    carburants = {c["id"]: c["nom"] for c in
                  conn.table("carburants").select("id,nom").execute().data}

    st.markdown("### Par carburant")

    # Comptable
    if not df_c.empty:
        df_c["carburant"] = df_c["carburant_id"].map(carburants)
        comp_recap = df_c.groupby("carburant").agg(
            litres=("ventes", "sum"),
            recette=("recette", "sum"),
        ).reset_index()
        comp_recap["source"] = "Comptable"

        # Pompiste
        if not df_p.empty:
            df_p["carburant"] = df_p["carburant_id"].map(carburants)
            pomp_recap = df_p.groupby("carburant").agg(
                litres=("litres", "sum"),
                recette=("montant", "sum"),
            ).reset_index()
            pomp_recap["source"] = "Pompiste"

            fusion = pd.concat([comp_recap, pomp_recap])
        else:
            fusion = comp_recap

        st.dataframe(fusion, use_container_width=True)

        total_litres = fusion["litres"].sum()
        total_recette = fusion["recette"].sum()
        c1, c2 = st.columns(2)
        c1.metric("Total litres", f"{total_litres:,.0f} L")
        c2.metric("Total recettes", f"{total_recette:,.0f} F")

        # Graphique
        pivot = fusion.pivot_table(
            index="carburant", columns="source",
            values="recette", aggfunc="sum"
        ).fillna(0)
        st.bar_chart(pivot)
    else:
        st.info("Aucune donnée pour ce mois.")


def afficher():
    st.header("📊 Tableau de bord (Gérant)")

    tab1, tab2, tab3, tab4 = st.tabs([
        "🕒 Stats Pompistes",
        "📒 Stats Comptable",
        "🔍 Comparatif",
        "📅 Totaux mensuels",
    ])
    with tab1:
        onglet_pompiste()
    with tab2:
        onglet_comptable()
    with tab3:
        onglet_comparatif()
    with tab4:
        onglet_totaux_mensuels()