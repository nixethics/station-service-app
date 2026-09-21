import streamlit as st
import pandas as pd
from datetime import date, timedelta
from fpdf import FPDF
from utils import conn


def generer_pdf_vente(v):
    """Génère un PDF de facture à partir d'une ligne ventes_pompe"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Station-Service", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Helvetica", "", 11)

    lignes = [
        ("Ticket n°", v["numero_ticket"]),
        ("Date", str(v["horodatage"])[:19]),
    ]
    if v.get("pompe"):
        lignes.append(("Pompe", f"n°{v['pompe']}"))
    lignes.extend([
        ("Litres", f"{v['litres']:.2f} L"),
        ("Montant", f"{v['montant']:,.0f} F"),
        ("Billet", f"{v['billet_recu']:,.0f} F"),
        ("Monnaie", f"{v['monnaie_rendue']:,.0f} F"),
    ])
    if v.get("matricule"):
        lignes.append(("Matricule", v["matricule"]))
    if v.get("nom_client"):
        lignes.append(("Client", v["nom_client"]))

    for label, valeur in lignes:
        pdf.cell(60, 8, f"{label} :", border=0)
        pdf.cell(0, 8, str(valeur), ln=True)

    return bytes(pdf.output())


def afficher():
    st.header("📨 Dashboard Secrétaire — Factures")

    col1, col2 = st.columns(2)
    with col1:
        debut = st.date_input("Du", value=date.today() - timedelta(days=7))
    with col2:
        fin = st.date_input("Au", value=date.today())

    result = (conn.table("ventes_pompe")
              .select("*")
              .gte("horodatage", f"{debut.isoformat()}T00:00:00")
              .lte("horodatage", f"{fin.isoformat()}T23:59:59")
              .order("horodatage", desc=True)
              .execute())

    if not result.data:
        st.info("Aucune vente sur cette période.")
        return

    df = pd.DataFrame(result.data)

    filtre = st.radio(
        "Afficher",
        ["À envoyer", "Envoyées par pompiste", "Envoyées par secrétaire", "Toutes"],
        horizontal=True,
    )
    if filtre == "À envoyer":
        df = df[df["envoye"] != True]
    elif filtre == "Envoyées par pompiste":
        df = df[df["envoye_par"] == "pompiste"]
    elif filtre == "Envoyées par secrétaire":
        df = df[df["envoye_par"] == "secretaire"]

    if len(df) == 0:
        st.success("Aucune facture dans cette catégorie. ✅")
        return

    st.caption(f"{len(df)} facture(s) affichée(s)")

    for _, v in df.iterrows():
        titre = f"Ticket {v['numero_ticket']} — {v['montant']:,.0f} F"
        if v.get("envoye"):
            titre += f"  ✅ ({v.get('envoye_par', '?')})"

        with st.expander(titre):
            col_info, col_action = st.columns([2, 1])

            with col_info:
                st.write(f"**Date** : {v['horodatage']}")
                st.write(f"**Litres** : {v['litres']} L")
                st.write(f"**Montant** : {v['montant']:,.0f} F")
                st.write(f"**Monnaie** : {v['monnaie_rendue']:,.0f} F")
                if v.get("pompe"):
                    st.write(f"**Pompe** : n°{v['pompe']}")
                if v.get("matricule"):
                    st.write(f"**Matricule** : {v['matricule']}")
                if v.get("nom_client"):
                    st.write(f"**Client** : {v['nom_client']}")

            with col_action:
                pdf = generer_pdf_vente(v)
                st.download_button(
                    "📄 PDF",
                    data=pdf,
                    file_name=f"facture_{v['numero_ticket']}.pdf",
                    mime="application/pdf",
                    key=f"pdf_{v['numero_ticket']}",
                    use_container_width=True,
                )

                if not v["envoye"]:
                    if st.button(
                        "✅ Marquer envoyé",
                        key=f"env_{v['numero_ticket']}",
                        use_container_width=True,
                    ):
                        conn.table("ventes_pompe").update({
                            "envoye": True,
                            "envoye_par": "secretaire",
                        }).eq("id", v["id"]).execute()
                        st.rerun()

            if v.get("nom_client"):
                message = (
                    f"Bonjour {v['nom_client']}, voici votre facture "
                    f"n° {v['numero_ticket']} d'un montant de "
                    f"{v['montant']:,.0f} F. Merci de votre confiance."
                )
                st.markdown(
                    f"[📱 Envoyer par WhatsApp](https://wa.me/?text={message.replace(' ', '%20')})",
                    unsafe_allow_html=True,
                )