from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import psycopg2
import os

app = Flask(__name__)

# Connexion PostgreSQL avec psycopg2
DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

# Création des tables si elles n'existent pas
def init_db():
    conn = get_conn()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transporteurs (
            id SERIAL PRIMARY KEY,
            nom TEXT,
            ville_depart TEXT,
            ville_arrivee TEXT,
            date_depart TEXT,
            numero_whatsapp TEXT,
            paiement TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS colis (
            id SERIAL PRIMARY KEY,
            expediteur TEXT,
            destinataire TEXT,
            date_envoi TEXT,
            transporteur_id INTEGER REFERENCES transporteurs(id)
        )
    """)
    conn.commit()
    conn.close()

# Variables globales pour suivre la saisie
utilisateurs = {}

@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip().lower()
    sender = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()

    user_state = utilisateurs.get(sender, {})

    if any(x in incoming_msg for x in ["bonjour", "salut", "hello"]):
        msg.body("👋 Bonjour ! Bienvenue chez *Askely Express* 🇲🇦\n\nQue souhaitez-vous faire ? Répondez avec :\n1️⃣ Envoyer un colis\n2️⃣ Devenir transporteur\n3️⃣ Suivre un colis")
        utilisateurs[sender] = {}

    elif incoming_msg in ["1", "envoyer un colis", "envoi colis", "je veux envoyer un colis"]:
        msg.body("📦 Veuillez envoyer les infos du colis au format :\nExpéditeur - Destinataire - Date d’envoi (JJ/MM/AAAA)")
        utilisateurs[sender] = {"étape": "envoi_infos"}

    elif incoming_msg in ["2", "devenir transporteur", "je veux devenir transporteur"]:
        msg.body("🚚 Pour devenir transporteur, envoyez vos infos :\nNom - Ville départ - Ville arrivée - Date (JJ/MM/AAAA) - Numéro WhatsApp - Paiement OK")
        utilisateurs[sender] = {"étape": "transporteur_infos"}

    elif incoming_msg in ["3", "suivre un colis", "suivi", "suivi colis"]:
        msg.body("🔎 Entrez le nom de l’expéditeur pour suivre votre colis.")
        utilisateurs[sender] = {"étape": "suivi"}

    elif user_state.get("étape") == "envoi_infos" and incoming_msg.count("-") == 2:
        expediteur, destinataire, date_str = [x.strip() for x in incoming_msg.split("-")]
        utilisateurs[sender] = {"étape": "choix_transporteur", "expediteur": expediteur, "destinataire": destinataire, "date": date_str}

        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom, ville_depart, ville_arrivee, numero_whatsapp FROM transporteurs WHERE date_depart = %s", (date_str,))
        resultats = cursor.fetchall()
        conn.close()

        if resultats:
            reponse = f"🚚 Transporteurs disponibles le {date_str} :\n"
            for r in resultats:
                reponse += f"ID {r[0]} - {r[1]} ({r[2]} ➡️ {r[3]}) 📱 {r[4]}\n"
            reponse += "\nRépondez avec : choisir [ID du transporteur]"
        else:
            reponse = "❌ Aucun transporteur disponible ce jour-là."
        msg.body(reponse)

    elif incoming_msg.startswith("choisir"):
        try:
            transporteur_id = int(incoming_msg.split(" ")[1])
            data = utilisateurs.get(sender, {})
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO colis (expediteur, destinataire, date_envoi, transporteur_id) VALUES (%s, %s, %s, %s)",
                           (data["expediteur"], data["destinataire"], data["date"], transporteur_id))
            conn.commit()
            cursor.execute("SELECT numero_whatsapp FROM transporteurs WHERE id = %s", (transporteur_id,))
            numero = cursor.fetchone()[0]
            conn.close()
            msg.body(f"✅ Colis enregistré avec le transporteur ID {transporteur_id}.\n📲 Contact : {numero}")
            utilisateurs[sender] = {}
        except:
            msg.body("❌ Erreur. Veuillez réessayer.")

    elif user_state.get("étape") == "transporteur_infos" and incoming_msg.count("-") == 5:
        try:
            nom, vdep, varr, date_dep, numero, paiement = [x.strip() for x in incoming_msg.split("-")]
            conn = get_conn()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO transporteurs (nom, ville_depart, ville_arrivee, date_depart, numero_whatsapp, paiement) VALUES (%s, %s, %s, %s, %s, %s)",
                           (nom, vdep, varr, date_dep, numero, paiement))
            conn.commit()
            conn.close()
            msg.body("✅ Inscription validée ! Vous recevrez une notification dès qu’un colis correspond à votre trajet.")
            utilisateurs[sender] = {}
        except:
            msg.body("❌ Format invalide. Vérifiez les données.")

    elif user_state.get("étape") == "suivi":
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.id, t.nom, t.numero_whatsapp 
            FROM colis c JOIN transporteurs t ON c.transporteur_id = t.id 
            WHERE c.expediteur ILIKE %s 
            ORDER BY c.id DESC LIMIT 1
        """, (f"%{incoming_msg}%",))
        resultat = cursor.fetchone()
        conn.close()
        if resultat:
            msg.body(f"📦 Colis ID {resultat[0]} en cours avec le transporteur {resultat[1]}.\n📲 Contact : {resultat[2]}")
        else:
            msg.body("❌ Aucun colis trouvé pour cet expéditeur.")
        utilisateurs[sender] = {}

    else:
        msg.body("❓ Je n’ai pas compris. Répondez avec :\n1️⃣ Envoyer un colis\n2️⃣ Devenir transporteur\n3️⃣ Suivre un colis")
        utilisateurs[sender] = {}

    return str(resp)

@app.route("/")
def index():
    return "✅ Askely Express est en ligne."

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000, debug=True)
