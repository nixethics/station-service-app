import streamlit as st
from st_supabase_connection import SupabaseConnection
from datetime import date, timedelta


@st.cache_resource
def get_conn():
    return st.connection("supabase", type=SupabaseConnection)


conn = get_conn()


def get_stock_fin_veille(carburant_id: int, jour: date):
    """Récupère le stock_fin de la veille (équivalent Excel : référence à la ligne du dessus)"""
    hier = jour - timedelta(days=1)
    result = (conn.table("mouvements_journaliers")
              .select("stock_fin")
              .eq("carburant_id", carburant_id)
              .eq("date", hier.isoformat())
              .execute())
    if result.data:
        return float(result.data[0]["stock_fin"])
    return 0.0


def get_prix_actuel(carburant_id: int):
    """Récupère le prix de vente actuel d'un carburant"""
    result = (conn.table("carburants")
              .select("prix_vente_actuel")
              .eq("id", carburant_id)
              .execute())
    return float(result.data[0]["prix_vente_actuel"])


def get_carburants():
    result = conn.table("carburants").select("*").order("id").execute()
    return result.data


def sauvegarder_mouvement(data: dict):
    """Enregistre un mouvement, avec upsert pour éviter les doublons"""
    conn.table("mouvements_journaliers").upsert(
        data, on_conflict="date,carburant_id"
    ).execute()


def log_audit(utilisateur, table_cible, ligne_id, action, ancienne, nouvelle):
    """Enregistre une modification dans audit_log"""
    try:
        conn.table("audit_log").insert({
            "utilisateur": utilisateur or "inconnu",
            "table_cible": table_cible,
            "ligne_id": ligne_id,
            "action": action,
            "ancienne_valeur": ancienne,
            "nouvelle_valeur": nouvelle,
        }).execute()
    except Exception as e:
        st.warning(f"Impossible d'écrire dans le journal d'audit : {e}")