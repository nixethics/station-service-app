"""
Script d'import JSON vers Supabase.
Usage : python3 import_json.py <chemin_fichier.json>
Exemple : python3 import_json.py data/juin_2026.json
"""

import sys
import json
from utils import conn, get_carburants


def main():
    if len(sys.argv) < 2:
        print("Usage : python3 import_json.py <fichier.json>")
        print("Exemple : python3 import_json.py data/juin_2026.json")
        sys.exit(1)

    fichier = sys.argv[1]

    # Charger les carburants
    carburants = get_carburants()
    carburants_map = {c["nom"]: c["id"] for c in carburants}
    print(f"🔧 Carburants : {carburants_map}")

    # Charger le JSON
    with open(fichier, "r", encoding="utf-8") as f:
        mouvements = json.load(f)

    print(f"📂 {len(mouvements)} lignes à importer depuis {fichier}")

    # Aperçu
    print("\n--- 5 premières lignes ---")
    for m in mouvements[:5]:
        print(f"   {m['date']} | {m['carburant']} | "
              f"stock_debut={m['stock_debut']} | ventes={m['ventes']} | "
              f"stock_fin={m['stock_fin']} | recette={m['recette']}")
        if m.get("note"):
            print(f"      ⚠️ Note : {m['note']}")

    # Compter les anomalies
    anomalies = [m for m in mouvements if m.get("note")]
    print(f"\n⚠️ {len(anomalies)} lignes avec une note")

    # Confirmation
    print("\n" + "=" * 60)
    reponse = input("Confirmer l'import ? (oui/non) : ").strip().lower()
    if reponse != "oui":
        print("❌ Import annulé.")
        return

    # Insertion
    print("\n📤 Insertion dans Supabase...")
    inserted = 0
    errors = 0
    for m in mouvements:
        try:
            data = {
                "date": m["date"],
                "carburant_id": carburants_map[m["carburant"]],
                "stock_debut": m["stock_debut"],
                "entrees": m["entrees"],
                "ventes": m["ventes"],
                "stock_fin": m["stock_fin"],
                "prix_vente": m["prix_vente"],
                "recette": m["recette"],
                "notes": m.get("note"),
            }
            conn.table("mouvements_journaliers").upsert(
                data, on_conflict="date,carburant_id"
            ).execute()
            inserted += 1
        except Exception as e:
            errors += 1
            print(f"   ❌ {m['date']} {m['carburant']} : {e}")

    print(f"\n✅ {inserted} lignes insérées, {errors} erreurs")


if __name__ == "__main__":
    main()