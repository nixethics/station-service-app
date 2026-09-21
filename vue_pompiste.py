import streamlit as st
from datetime import datetime, date
from fpdf import FPDF
from utils import conn, get_carburants


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

    pompe = st.radio("Pompe active", [1, 2, 3, 4], horizontal=True,
                     key="pompe_active")
    st.caption(f"Vous travaillez sur la **pompe n°{pompe}**")
    st.markdown("---")

    data = st.session_state.pompes_data[pompe]

    if data["ticket"] is not None:
        ticket = data["ticket"]
        st.success(f"Vente enregistrée (pompe n°{pompe}). Ticket n° {ticket['numero']}")

        col1, col2 = st.columns(2)
        with col1:
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
        with col2:
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

    carburants = get_carburants()
    noms = [c["nom"] for c in carburants]

    try:
        index_carb = noms.index(data["carburant"])
    except ValueError:
        index_carb = 0

    choix = st.radio("Carburant", noms, index=index_carb,
                     horizontal=True, key=f"carb_{pompe}")
    data["carburant"] = choix
    c = next(x for x in carburants if x["nom"] == choix)
    prix = float(c["prix_vente_actuel"])

    st.caption(f"Prix du jour : {prix:.0f} F/L")

    modes = ["Montant → Litres", "Litres → Prix"]
    try:
        index_mode = modes.index(data["mode"])
    except ValueError:
        index_mode = 0

    mode = st.radio("Mode", modes, index=index_mode,
                    horizontal=True, key=f"mode_{pompe}")
    data["mode"] = mode

    if mode == "Montant → Litres":
        montant = st.number_input(
            "Montant donné par le client (F)",
            min_value=0.0, step=100.0,
            value=float(data["montant"]),
            key=f"montant_{pompe}"
        )
        data["montant"] = montant
        litres = montant / prix if prix > 0 else 0
        st.metric("Litres à servir", f"{litres:.2f} L")
    else:
        litres = st.number_input(
            "Litres demandés",
            min_value=0.0, step=1.0,
            value=float(data["litres"]),
            key=f"litres_{pompe}"
        )
        data["litres"] = litres
        montant = litres * prix
        st.metric("Montant à payer", f"{montant:,.0f} F")

    billet = st.number_input(
        "Billet reçu (F)",
        min_value=0.0, step=100.0,
        value=float(data["billet"]),
        key=f"billet_{pompe}"
    )
    data["billet"] = billet

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
        data["matricule"] = matricule
    with col_b:
        nom_client = st.text_input(
            "Nom du client",
            value=data["nom_client"],
            key=f"nom_{pompe}"
        )
        data["nom_client"] = nom_client

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

            data["ticket"] = {
                "numero": num,
                "texte": "\n".join(lignes),
            }
            st.balloons()
            st.rerun()

        except Exception as e:
            st.error(f"Erreur lors de l'enregistrement : {e}")

        

def onglet_facture_multi():
    st.subheader("🧾 Facture multi-lignes")
    st.caption("Utilisez ce formulaire pour les clients qui achètent "
               "plusieurs carburants ou plusieurs lignes en une fois. "
               "Cette étape est **optionnelle**.")

    if "facture_lignes" not in st.session_state:
        st.session_state.facture_lignes = []

    if "facture_validee" not in st.session_state:
        st.session_state.facture_validee = None

    if st.session_state.facture_validee is not None:
        fact = st.session_state.facture_validee
        st.success(f"Facture enregistrée. N° {fact['numero']}")

        pdf_bytes = generer_pdf_facture_multi(fact)
        st.download_button(
            "📄 Télécharger la facture (PDF)",
            data=pdf_bytes,
            file_name=f"facture_{fact['numero']}.pdf",
            mime="application/pdf",
            use_container_width=True,
            key=f"pdf_fact_{fact['numero']}",
        )

        st.markdown("### Récapitulatif")
        st.write(f"**Client** : {fact.get('client_nom', '—')}")
        if fact.get("client_societe"):
            st.write(f"**Société** : {fact['client_societe']}")
        st.write(f"**Date** : {fact['date_heure']}")
        st.write(f"**Numéro** : {fact['numero']}")
        st.write(f"**Total** : {fact['total']:,.0f} F")

        st.markdown("**Lignes**")
        for ligne in fact["lignes"]:
            st.write(
                f"- {ligne['description']} : {ligne['quantite']:.2f} × "
                f"{ligne['prix_unitaire']:,.0f} F = {ligne['total_ligne']:,.0f} F"
            )

        if st.button("🔄 Nouvelle facture", type="primary", use_container_width=True):
            st.session_state.facture_validee = None
            st.session_state.facture_lignes = []
            st.rerun()
        return

    st.markdown("#### Informations générales")
    col1, col2 = st.columns(2)
    with col1:
        reference_client = st.text_input("Référence client", key="fact_ref")
        client_nom = st.text_input("Nom du client", key="fact_cli_nom")
        client_societe = st.text_input("Société (optionnel)", key="fact_cli_soc")
    with col2:
        client_adresse = st.text_input("Adresse (optionnel)", key="fact_cli_adr")
        client_telephone = st.text_input("Téléphone (optionnel)", key="fact_cli_tel")
        vendeur = st.text_input("Vendeur (pompiste)", key="fact_vendeur")

    st.markdown("#### Lignes de la facture")

    for i, ligne in enumerate(st.session_state.facture_lignes):
        col1, col2, col3, col4, col5 = st.columns([2, 3, 1.5, 1.5, 0.5])
        with col1:
            st.write(f"**{ligne['quantite']:.2f}**")
        with col2:
            st.write(ligne["description"])
        with col3:
            st.write(f"{ligne['prix_unitaire']:,.0f} F")
        with col4:
            st.write(f"**{ligne['total_ligne']:,.0f} F**")
        with col5:
            if st.button("🗑️", key=f"del_ligne_{i}"):
                st.session_state.facture_lignes.pop(i)
                st.rerun()

    st.markdown("#### Ajouter une ligne")

    carburants = get_carburants()
    noms = [c["nom"] for c in carburants]

    with st.form("form_ajout_ligne"):
        col1, col2 = st.columns(2)
        with col1:
            carburant_choisi = st.selectbox("Carburant", noms, key="fact_carb")
            quantite_ligne = st.number_input(
                "Quantité (L)", min_value=0.0, step=1.0, key="fact_qte"
            )
        with col2:
            c_choisi = next(x for x in carburants if x["nom"] == carburant_choisi)
            prix_ligne = float(c_choisi["prix_vente_actuel"])
            st.metric("Prix unitaire", f"{prix_ligne:,.0f} F/L")
            description = st.text_input(
                "Description (optionnel)",
                value=f"{carburant_choisi}",
                key="fact_desc"
            )

        ajouter = st.form_submit_button("➕ Ajouter la ligne",
                                        use_container_width=True)

        if ajouter and quantite_ligne > 0:
            st.session_state.facture_lignes.append({
                "quantite": quantite_ligne,
                "description": description or carburant_choisi,
                "prix_unitaire": prix_ligne,
                "total_ligne": quantite_ligne * prix_ligne,
            })
            st.rerun()

    if st.session_state.facture_lignes:
        sous_total = sum(l["total_ligne"] for l in st.session_state.facture_lignes)

        st.markdown("#### Totaux")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Sous-total", f"{sous_total:,.0f} F")
        with col2:
            taux_tva = st.number_input(
                "TVA (%)", min_value=0.0, max_value=30.0, value=0.0, step=0.5,
                key="fact_tva"
            )

        tva = sous_total * (taux_tva / 100)
        total = sous_total + tva

        col1, col2 = st.columns(2)
        with col1:
            st.metric("TVA", f"{tva:,.0f} F")
        with col2:
            st.metric("Total", f"{total:,.0f} F")

        if st.button("✅ Valider la facture", type="primary",
                     use_container_width=True):
            now = datetime.now()
            num = now.strftime("FA-%Y%m%d-%H%M%S")

            try:
                res = conn.table("factures").insert({
                    "numero_facture": num,
                    "date_facture": date.today().isoformat(),
                    "client_nom": client_nom or None,
                    "client_societe": client_societe or None,
                    "client_adresse": client_adresse or None,
                    "client_telephone": client_telephone or None,
                    "reference_client": reference_client or None,
                    "vendeur": vendeur or None,
                    "poste": "Pompiste",
                    "sous_total": sous_total,
                    "tva": tva,
                    "total": total,
                }).execute()

                facture_id = res.data[0]["id"]

                for i, ligne in enumerate(st.session_state.facture_lignes):
                    conn.table("factures_lignes").insert({
                        "facture_id": facture_id,
                        "quantite": ligne["quantite"],
                        "description": ligne["description"],
                        "prix_unitaire": ligne["prix_unitaire"],
                        "total_ligne": ligne["total_ligne"],
                        "ordre": i + 1,
                    }).execute()

                st.session_state.facture_validee = {
                    "numero": num,
                    "date_heure": now.strftime("%d/%m/%Y %H:%M"),
                    "client_nom": client_nom,
                    "client_societe": client_societe,
                    "client_adresse": client_adresse,
                    "client_telephone": client_telephone,
                    "reference_client": reference_client,
                    "vendeur": vendeur,
                    "poste": "Pompiste",
                    "lignes": list(st.session_state.facture_lignes),
                    "sous_total": sous_total,
                    "tva": tva,
                    "taux_tva": taux_tva,
                    "total": total,
                }

                st.balloons()
                st.rerun()

            except Exception as e:
                st.error(f"Erreur lors de l'enregistrement : {e}")


def afficher():
    st.header("⛽ Espace Pompiste")

    tab1, tab2 = st.tabs(["💰 Vente rapide", "🧾 Facture multi-lignes"])

    with tab1:
        onglet_vente_rapide()
    with tab2:
        onglet_facture_multi()    