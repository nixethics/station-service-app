import streamlit as st
from datetime import datetime, date
from fpdf import FPDF
from utils import conn, get_carburants


# ============================================================
# Génération PDF — Facture multi-lignes
# ============================================================
def generer_pdf_facture_multi(data):
    pdf = FPDF()
    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Filling Sarl", ln=True, align="C")
    pdf.set_font("Helvetica", "I", 10)
    pdf.cell(0, 6, "La qualite, notre exigence", ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Date : {data['date_heure']}", ln=True)
    pdf.cell(0, 6, f"N° facture : {data['numero']}", ln=True)
    if data.get("reference_client"):
        pdf.cell(0, 6, f"Reference client : {data['reference_client']}", ln=True)
    pdf.ln(3)

    if data.get("client_nom") or data.get("client_societe"):
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 6, "Client :", ln=True)
        pdf.set_font("Helvetica", "", 10)
        if data.get("client_nom"):
            pdf.cell(0, 6, f"  Nom : {data['client_nom']}", ln=True)
        if data.get("client_societe"):
            pdf.cell(0, 6, f"  Societe : {data['client_societe']}", ln=True)
        if data.get("client_adresse"):
            pdf.cell(0, 6, f"  Adresse : {data['client_adresse']}", ln=True)
        if data.get("client_telephone"):
            pdf.cell(0, 6, f"  Telephone : {data['client_telephone']}", ln=True)
        pdf.ln(3)

    if data.get("vendeur"):
        pdf.set_font("Helvetica", "", 10)
        pdf.cell(0, 6, f"Vendeur : {data['vendeur']} ({data.get('poste', '')})", ln=True)
        pdf.ln(3)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(30, 8, "Qte", border=1)
    pdf.cell(90, 8, "Description", border=1)
    pdf.cell(35, 8, "Prix unit.", border=1)
    pdf.cell(0, 8, "Total", border=1, ln=True)

    pdf.set_font("Helvetica", "", 10)
    for ligne in data["lignes"]:
        pdf.cell(30, 8, f"{ligne['quantite']:.2f}", border=1)
        pdf.cell(90, 8, ligne["description"], border=1)
        pdf.cell(35, 8, f"{ligne['prix_unitaire']:,.0f}", border=1)
        pdf.cell(0, 8, f"{ligne['total_ligne']:,.0f}", border=1, ln=True)

    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)
    pdf.cell(120, 8, "", border=0)
    pdf.cell(35, 8, "Sous-total", border=1)
    pdf.cell(0, 8, f"{data['sous_total']:,.0f} F", border=1, ln=True)

    if data.get("tva", 0) > 0:
        pdf.cell(120, 8, "", border=0)
        pdf.cell(35, 8, f"TVA ({data.get('taux_tva', 0)}%)", border=1)
        pdf.cell(0, 8, f"{data['tva']:,.0f} F", border=1, ln=True)

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(120, 8, "", border=0)
    pdf.cell(35, 8, "Total", border=1)
    pdf.cell(0, 8, f"{data['total']:,.0f} F", border=1, ln=True)

    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, "Veuillez libeller tous les cheques a l'ordre de Filling Sarl", ln=True)
    pdf.cell(0, 6, "Nous vous remercions de votre confiance !", ln=True)
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(0, 5, "Immeuble Filling, Moroni - Union des Comores", ln=True)
    pdf.cell(0, 5, "Telephone : +269 332 01 04 - Mail : mahamoudkalia@gmail.com", ln=True)

    return bytes(pdf.output())


# ============================================================
# Onglet 1 — Vente rapide
# ============================================================
def onglet_vente_rapide():
    st.subheader("Vente rapide")

    if "pompes_data" not in st.session_state:
        st.session_state.pompes_data = {
            p: {
                "carburant": "Essence",
                "mode": "Montant → Litres",
                "montant": 0.0,
                "litres": 0.0,
                "billet": 0.0,
                "matricule": "",
                "nom_client": "",
                "ticket": None,
            } for p in [1, 2, 3, 4]
        }

    pompe = st.radio("Pompe active", [1, 2, 3, 4],