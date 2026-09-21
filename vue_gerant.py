import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils import conn


# ============================================================
# Onglet 1 — Statistiques Pompiste (temps réel)
# ============================================================
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
    else:
        st.info("Aucune donnée de pompe pour l'instant.")

    st.markdown("**Dernières ventes**")
    st.dataframe(
        df[["horodatage", "pompe", "carburant", "litres",
            "montant", "monnaie_rendue", "matricule", "nom_client",
            "envoye"]],
        use_container_width=True,
        height=300,
    )


# ============================================================
# Onglet 2 — Statistiques Comptable
# ============================================================
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
        st.caption("Évolution journalière (recette et ventes)")
        st.line_chart(par_jour.set_index("date")[["recette", "ventes"]])
    elif graph_type == "Barres (par jour)":
        st.caption("Répartition journalière (barres)")
        st.bar_chart(par_jour.set_index("date")[["recette", "ventes"]])
    elif graph_type == "Histogramme (par carburant)":
        st.caption("Comparaison Essence vs Diesel")
        st.bar_chart(par_carb.set_index("carburant")[["recette"]])
    else:
        st.caption("Répartition des recettes par carburant")
        rep = par_carb.set_index("carburant")["recette"]
        st.bar_chart(rep)
        st.write("**Part de chaque carburant :**")
        total = rep.sum()
        for carb, val in rep.items():
            pct = (val / total * 100) if total > 0 else 0
            st.write(f"- {carb} : {val:,.0f} F ({pct:.1f} %)")

    st.markdown("**Détail journalier**")
    st.dataframe(
        df[["date", "carburant", "stock_debut", "entrees", "ventes",
            "stock_fin", "prix_vente", "recette",
            "montant_reel_recu", "perte"]],
        use_container_width=True,
    )


# ============================================================
# Onglet 3 — Comparatif Pompiste vs Comptable
# ============================================================
def couleur_ecart(pct):
    """Retourne un emoji couleur selon l'écart en %"""
    if pct is None:
        return "⚪"
    pct = abs(pct)
    if pct < 1:
        return "🟢"
    elif pct < 5:
        return "🟡"
    else:
        return "🔴"


def onglet_comparatif():
    st.subheader("🔍 Comparatif Pompistes vs Comptable")
    st.caption("Rapprochement entre les ventes enregistrées par les pompistes "
               "et les données saisies par le comptable. Les écarts importants "
               "sont mis en évidence.")

    col1, col2 = st.columns(2)
    with col1:
        debut = st.date_input("Du", value=date.today() - timedelta(days=7),
                              key="comp_debut")
    with col2:
        fin = st.date_input("Au", value=date.today(), key="comp_fin")

    # === Source Pompiste : ventes_pompe ===
    res_p = (conn.table("ventes_pompe")
             .select("*")
             .gte("horodatage", f"{debut.isoformat()}T00:00:00")
             .lte("horodatage", f"{fin.isoformat()}T23:59:59")
             .execute())
    df_p = pd.DataFrame(res_p.data) if res_p.data else pd.DataFrame()

    # === Source Comptable : mouvements_journaliers ===
    res_c = (conn.table("mouvements_journaliers")
             .select("*")
             .gte("date", debut.isoformat())
             .lte("date", fin.isoformat())
             .execute())
    df_c = pd.DataFrame(res_c.data) if res_c.data else pd.DataFrame()

    if df_p.empty and df_c.empty:
        st.warning("Aucune donnée sur cette période, ni côté pompiste ni côté comptable.")
        return

    # === Totaux globaux ===
    litres_pompiste = df_p["litres"].sum() if not df_p.empty else 0
    recette_pompiste = df_p["montant"].sum() if not df_p.empty else 0

    litres_comptable = df_c["ventes"].sum() if not df_c.empty else 0
    recette_comptable = df_c["recette"].sum() if not df_c.empty else 0
    montant_reel = df_c["montant_reel_recu"].fillna(0).sum() if not df_c.empty and "montant_reel_recu" in df_c else 0

    # === Indicateurs côte à côte ===
    st.markdown("### Indicateurs globaux")

    col1, col2, col3 = st.columns(3)
    col1.metric("Litres — Pompistes", f"{litres_pompiste:,.0f} L")
    col2.metric("Litres — Comptable", f"{litres_comptable:,.0f} L")
    delta_l = litres_comptable - litres_pompiste
    col3.metric("Écart litres", f"{delta_l:,.0f} L",
                delta_color="inverse" if delta_l != 0 else "normal")

    col1, col2, col3 = st.columns(3)
    col1.metric("Recette — Pompistes", f"{recette_pompiste:,.0f} F")
    col2.metric("Recette — Comptable", f"{recette_comptable:,.0f} F")
    delta_r = recette_comptable - recette_pompiste
    col3.metric("Écart recette", f"{delta_r:,.0f} F",
                delta_color="inverse" if delta_r != 0 else "normal")

    col1, col2 = st.columns(2)
    col1.metric("Montant réel reçu (comptable)", f"{montant_reel:,.0f} F")
    delta_c = montant_reel - recette_comptable
    col2.metric("Écart caisse (réel − attendu)", f"{delta_c:,.0f} F",
                delta_color="inverse" if delta_c != 0 else "normal")

    # === Analyse des écarts en % ===
    st.markdown("### Analyse des écarts")

    def pourcentage(ecart, reference):
        if reference == 0:
            return None
        return (ecart / reference) * 100

    pct_l = pourcentage(delta_l, litres_pompiste)
    pct_r = pourcentage(delta_r, recette_pompiste)

    lignes_analyse = [
        {
            "Indicateur": "Litres",
            "Pompiste": f"{litres_pompiste:,.0f} L",
            "Comptable": f"{litres_comptable:,.0f} L",
            "Écart": f"{delta_l:,.0f} L",
            "Écart %": f"{pct_l:+.1f} %" if pct_l is not None else "—",
            "Statut": couleur_ecart(pct_l),
        },
        {
            "Indicateur": "Recette attendue",
            "Pompiste": f"{recette_pompiste:,.0f} F",
            "Comptable": f"{recette_comptable:,.0f} F",
            "Écart": f"{delta_r:,.0f} F",
            "Écart %": f"{pct_r:+.1f} %" if pct_r is not None else "—",
            "Statut": couleur_ecart(pct_r),
        },
    ]
    st.dataframe(pd.DataFrame(lignes_analyse), use_container_width=True)

    # === Interprétation automatique ===
    st.markdown("### Interprétation")
    if pct_l is not None and abs(pct_l) < 1:
        st.success("✅ Les déclarations pompistes et comptables concordent sur les litres.")
    elif pct_l is not None and pct_l < -1:
        st.error(f"⚠️ Le comptable a déclaré {abs(pct_l):.1f} % de litres en MOINS "
                 f"que ce que les pompistes ont vendu. Des ventes n'ont peut-être "
                 f"pas été reportées dans le registre comptable.")
    elif pct_l is not None and pct_l > 1:
        st.warning(f"⚠️ Le comptable a déclaré {pct_l:.1f} % de litres en PLUS "
                   f"que les ventes enregistrées par les pompistes. Vérifier "
                   f"les saisies (double saisie, erreur de frappe).")

    if montant_reel > 0:
        if abs(delta_c) < 1:
            st.success("✅ La caisse est conforme à la recette attendue.")
        elif delta_c < 0:
            st.error(f"⚠️ Manque en caisse : {abs(delta_c):,.0f} F par rapport "
                     f"à la recette attendue.")
        else:
            st.warning(f"⚠️ Excédent en caisse : +{delta_c:,.0f} F. À vérifier.")

    # === Comparatif détaillé par jour ===
    st.markdown("### Comparatif détaillé par jour")

    # Côté pompiste, on regroupe par jour
    if not df_p.empty:
        df_p["jour"] = pd.to_datetime(df_p["horodatage"]).dt.date
        par_jour_p = df_p.groupby("jour").agg(
            litres_pompiste=("litres", "sum"),
            recette_pompiste=("montant", "sum"),
            nb_ventes=("id", "count"),
        ).reset_index()
    else:
        par_jour_p = pd.DataFrame(columns=["jour", "litres_pompiste",
                                            "recette_pompiste", "nb_ventes"])

    # Côté comptable, on regroupe aussi par jour
    if not df_c.empty:
        df_c["jour"] = pd.to_datetime(df_c["date"]).dt.date
        par_jour_c = df_c.groupby("jour").agg(
            litres_comptable=("ventes", "sum"),
            recette_comptable=("recette", "sum"),
            montant_reel=("montant_reel_recu", lambda x: x.fillna(0).sum()),
        ).reset_index()
    else:
        par_jour_c = pd.DataFrame(columns=["jour", "litres_comptable",
                                            "recette_comptable", "montant_reel"])

    # Fusion sur le jour
    if not par_jour_p.empty and not par_jour_c.empty:
        merge = pd.merge(par_jour_p, par_jour_c, on="jour", how="outer").fillna(0)
    elif not par_jour_p.empty:
        merge = par_jour_p.copy()
        merge["litres_comptable"] = 0
        merge["recette_comptable"] = 0
        merge["montant_reel"] = 0
    else:
        merge = par_jour_c.copy()
        merge["litres_pompiste"] = 0
        merge["recette_pompiste"] = 0
        merge["nb_ventes"] = 0

    # Calcul des écarts
    merge["ecart_litres"] = merge["litres_comptable"] - merge["litres_pompiste"]
    merge["ecart_recette"] = merge["recette_comptable"] - merge["recette_pompiste"]
    merge["statut_litres"] = merge["ecart_litres"].apply(
        lambda x: couleur_ecart(pourcentage(x, merge["litres_pompiste"].mean()))
    )

    merge = merge.sort_values("jour", ascending=False)

    st.dataframe(
        merge[[
            "jour",
            "litres_pompiste", "litres_comptable", "ecart_litres",
            "recette_pompiste", "recette_comptable", "ecart_recette",
            "montant_reel", "statut_litres",
        ]],
        use_container_width=True,
    )

    # === Graphique comparatif ===
    st.markdown("### Graphique comparatif")
    if not merge.empty and len(merge) > 1:
        chart_data = merge.set_index("jour")[[
            "litres_pompiste", "litres_comptable",
        ]]
        st.caption("Litres : pompistes vs comptable (par jour)")
        st.line_chart(chart_data)

        chart_data2 = merge.set_index("jour")[[
            "recette_pompiste", "recette_comptable",
        ]]
        st.caption("Recette : pompistes vs comptable (par jour)")
        st.line_chart(chart_data2)


# ============================================================
# Fonction principale appelée par app.py
# ============================================================
def afficher():
    st.header("📊 Tableau de bord (Gérant)")

    onglet1, onglet2, onglet3 = st.tabs([
        "🕒 Stats Pompistes (temps réel)",
        "📒 Stats Comptable",
        "🔍 Comparatif",
    ])
    with onglet1:
        onglet_pompiste()
    with onglet2:
        onglet_comptable()
    with onglet3:
        onglet_comparatif()