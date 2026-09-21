import bcrypt
from utils import conn


# Liste des utilisateurs de démonstration
utilisateurs = [
    {
        "email": "admin@station.com",
        "nom": "Administrateur",
        "mot_de_passe": "admin123",
        "role": "admin",
    },
    {
        "email": "gerant@station.com",
        "nom": "Le Gérant",
        "mot_de_passe": "gerant123",
        "role": "gerant",
    },
    {
        "email": "comptable@station.com",
        "nom": "La Comptable",
        "mot_de_passe": "comptable123",
        "role": "comptable",
    },
    {
        "email": "pompiste@station.com",
        "nom": "Moussa (pompiste)",
        "mot_de_passe": "pompiste123",
        "role": "pompiste",
    },
    {
        "email": "secretaire@station.com",
        "nom": "La Secrétaire",
        "mot_de_passe": "secretaire123",
        "role": "secretaire",
    },
]


def creer_utilisateurs():
    for u in utilisateurs:
        # Vérifier si l'utilisateur existe déjà
        existant = (conn.table("utilisateurs")
                    .select("id")
                    .eq("email", u["email"])
                    .execute())
        if existant.data:
            print(f"⏭️  {u['email']} existe déjà, on passe.")
            continue

        # Hacher le mot de passe
        hashed = bcrypt.hashpw(
            u["mot_de_passe"].encode("utf-8"),
            bcrypt.gensalt(),
        ).decode("utf-8")

        # Insérer
        conn.table("utilisateurs").insert({
            "email": u["email"],
            "nom": u["nom"],
            "mot_de_passe_hash": hashed,
            "role": u["role"],
            "actif": True,
        }).execute()

        print(f"✅ {u['email']} créé ({u['role']})")


if __name__ == "__main__":
    creer_utilisateurs()
    print("\n🎉 Terminé.")