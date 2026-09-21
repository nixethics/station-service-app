import streamlit as st
from datetime import datetime
from fpdf import FPDF
from utils import conn, get_carburants


def generer_pdf_facture(data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Station-Service", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, data["date_heure"], ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, f"Ticket n° {data['numero']}", ln=True)
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 11)
    lignes = [
        ("Pompe", f"n°{data['pompe']}"),
        ("Carburant", data["carburant"]),
        ("Litres", f"{data['litres']:.2f} L"),
        ("Prix/L", f"{data['prix']:.0f} F"),
        ("Montant", f"{data['montant']:,.0f} F"),
        ("Billet reçu", f"{data['billet']:,.0f} F"),
        ("Monnaie rendue", f"{data['monnaie']:,.0f} F"),
    ]
    if data.get("matricule"):
        lignes.append(("Matricule", data["matricule"]))
    if data.get("nom_client"):
        lignes.append(("Client", data["nom_client"]))

    for label, valeur in lignes:
        pdf.cell(60, 8, f"{label} :", border=0)
        pdf.cell(0, 8, str(valeur), ln=True)

    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 6, "Merci de votre confiance.", ln=True, align="C")

    return bytes(pdf.output())


# ==== Gestion de l'état persistant par pompe ====

def init_etat():
    """Initialise l'état global une seule fois"""
    if "pompes_data" not in st.session_state:
        # pompes_data[pompe] = dict avec toutes les valeurs du formulaire
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


def get_data(pompe):
    return st.session_state.pompes_data[pompe]


def set_data(pompe, key, value):
    st.session_state.pompes_data[pompe][key] = value


def afficher():
    st.header("⛽ Calculatrice (Pompiste)")

    init_etat()

    pompe = st.radio("Pompe active", [1, 2, 3, 4], horizontal=True,
                     key="pompe_active")
    st.caption(f"Vous travaillez sur la **pompe n°{pompe}**")
    st.markdown("---")

    data = get_data(pompe)

    # ==== Écran ticket ====
    if data["ticket"] is not None:
        ticket = data["ticket"]
        st.success(f"Vente enregistrée (pompe n°{pompe}). Ticket n° {ticket['numero']}")

        pdf_bytes = generer_pdf_facture(ticket)

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                label="📄 Télécharger PDF",
                data=pdf_bytes,
                file_name=f"facture_{ticket['numero']}.pdf",
                mime="application/pdf",
                use_container_width=True,
                key=f"pdf_btn_{pompe}_{ticket['numero']}",
            )
        with col2:
            if ticket.get("nom_client"):
                message = (
                    f"Bonjour {ticket['nom_client']}, voici votre facture "
                    f"n° {ticket['numero']} d'un montant de "
                    f"{ticket['montant']:,.0f} F. Merci de votre confiance."
                )
                st.link_button(
                    "📱 Envoyer WhatsApp",
                    f"https://wa.me/?text={message.replace(' ', '%20')}",
                    use_container_width=True,
                )
            else:
                st.caption("Ajoutez un nom client pour activer WhatsApp")

        if st.button("✅ Marquer comme envoyé",
                     use_container_width=True,
                     key=f"marq_{pompe}_{ticket['numero']}"):
            conn.table("ventes_pompe").update({
                "envoye": True,
                "envoye_par": "pompiste",
            }).eq("numero_ticket", ticket["numero"]).execute()
            st.success("Marquée comme envoyée")

        st.code(ticket["texte"])

        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Nouvelle vente sur cette pompe",
                         type="primary",
                         use_container_width=True,
                         key=f"nv_{pompe}"):
                # Réinitialiser le formulaire de cette pompe
                st.session_state.pompes_data[pompe] = {
                    "carburant": "Essence",
                    "mode": "Montant → Litres",
                    "montant": 0.0,
                    "litres": 0.0,
                    "billet": 0.0,
                    "matricule": "",
                    "nom_client": "",
                    "ticket": None,
                }
                st.rerun()
        with col2:
            if st.button("❌ Fermer le ticket",
                         use_container_width=True,
                         key=f"ferm_{pompe}"):
                st.session_state.pompes_data[pompe]["ticket"] = None
                st.rerun()
        return

    # ==== Formulaire de vente ====
    carburants = get_carburants()
    noms = [c["nom"] for c in carburants]

    # Index carburant sauvegardé
    try:
        index_carb = noms.index(data["carburant"])
    except ValueError:
        index_carb = 0

    choix = st.radio("Carburant", noms, index=index_carb,
                     horizontal=True, key=f"carb_{pompe}")
    set_data(pompe, "carburant", choix)
    c = next(x for x in carburants if x["nom"] == choix)
    prix = float(c["prix_vente_actuel"])

    st.caption(f"Prix du jour : {prix:.0f} F/L")

    # Index mode sauvegardé
    modes = ["Montant → Litres", "Litres → Prix"]
    try:
        index_mode = modes.index(data["mode"])
    except ValueError:
        index_mode = 0

    mode = st.radio("Mode", modes, index=index_mode,
                    horizontal=True, key=f"mode_{pompe}")
    set_data(pompe, "mode", mode)

    if mode == "Montant → Litres":
        montant = st.number_input(
            "Montant donné par le client (F)",
            min_value=0.0, step=100.0,
            value=float(data["montant"]),
            key=f"montant_{pompe}"
        )
        set_data(pompe, "montant", montant)
        litres = montant / prix if prix > 0 else 0
        st.metric("Litres à servir", f"{litres:.2f} L")
    else:
        litres = st.number_input(
            "Litres demandés",
            min_value=0.0, step=1.0,
            value=float(data["litres"]),
            key=f"litres_{pompe}"
        )
        set_data(pompe, "litres", litres)
        montant = litres * prix
        st.metric("Montant à payer", f"{montant:,.0f} F")

    billet = st.number_input(
        "Billet reçu (F)",
        min_value=0.0, step=100.0,
        value=float(data["billet"]),
        key=f"billet_{pompe}"
    )
    set_data(pompe, "billet", billet)

    monnaie = 0.0
    if billet > 0:
        monnaie = billet - montant
        if monnaie < 0:
            st.error(f"❌ Billet insuffisant. Manque : {abs(monnaie):,.0f} F")
        else:
            st.success(f"💰 Monnaie à rendre : {monnaie:,.0f} F")

    st.subheader("Informations client (optionnel)")
    col_a, col_b = st.columns(2)
    with col_a:
        matricule = st.text_input(
            "Matricule du véhicule",
            value=data["matricule"],
            key=f"mat_{pompe}"
        )
        set_data(pompe, "matricule", matricule)
    with col_b:
        nom_client = st.text_input(
            "Nom du client",
            value=data["nom_client"],
            key=f"nom_{pompe}"
        )
        set_data(pompe, "nom_client", nom_client)

    if st.button("✅ Valider la vente",
                 type="primary",
                 key=f"val_{pompe}") and billet >= montant and montant > 0:
        now = datetime.now()
        num = now.strftime("%Y%m%d-%H%M%S") + f"-P{pompe}"

        try:
            conn.table("ventes_pompe").insert({
                "carburant_id": c["id"],
                "pompe": pompe,
                "litres": round(litres, 2),
                "montant": round(montant, 2),
                "billet_recu": billet,
                "monnaie_rendue": round(monnaie, 2),
                "numero_ticket": num,
                "matricule": matricule if matricule else None,
                "nom_client": nom_client if nom_client else None,
            }).execute()

            lignes = [
                "=============================",
                "Station-Service",
                now.strftime("%d/%m/%Y %H:%M"),
                "=============================",
                f"Pompe     : n°{pompe}",
                f"Carburant : {choix}",
                f"Litres    : {litres:.2f} L",
                f"Prix/L    : {prix:.0f} F",
                f"Montant   : {montant:,.0f} F",
                f"Billet    : {billet:,.0f} F",
                f"Monnaie   : {monnaie:,.0f} F",
            ]
            if matricule:
                lignes.append(f"Matricule : {matricule}")
            if nom_client:
                lignes.append(f"Client    : {nom_client}")
            lignes.append(f"Ticket n° : {num}")
            lignes.append("=============================")

            # On met le ticket dans l'état de la pompe
            st.session_state.pompes_data[pompe]["ticket"] = {
                "numero": num,
                "date_heure": now.strftime("%d/%m/%Y %H:%M"),
                "pompe": pompe,
                "carburant": choix,
                "litres": round(litres, 2),
                "prix": prix,
                "montant": round(montant, 2),
                "billet": billet,
                "monnaie": round(monnaie, 2),
                "matricule": matricule,
                "nom_client": nom_client,
                "texte": "\n".join(lignes),
            }
            st.balloons()
            st.rerun()

        except Exception as e:
            st.error(f"Erreur lors de l'enregistrement : {e}")