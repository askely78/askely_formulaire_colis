
from flask import Flask, request, render_template
from twilio.twiml.messaging_response import MessagingResponse
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS transporteurs (
                        id SERIAL PRIMARY KEY,
                        nom TEXT,
                        ville_depart TEXT,
                        ville_arrivee TEXT,
                        date_depart TEXT,
                        numero_whatsapp TEXT,
                        paiement TEXT
                    )""")
    cursor.execute("""CREATE TABLE IF NOT EXISTS colis (
                        id SERIAL PRIMARY KEY,
                        expediteur TEXT,
                        destinataire TEXT,
                        date_envoi TEXT,
                        transporteur_id INTEGER REFERENCES transporteurs(id)
                    )""")
    conn.commit()
    conn.close()

@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip().lower()
    sender = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg in ["bonjour", "salut", "hello"]:
        msg.body("👋 Bonjour ! Bienvenue chez *Askely Express* 🇲🇦\n\nQue souhaitez-vous faire ? Répondez avec :\n1️⃣ Envoyer un colis\n2️⃣ Devenir transporteur\n3️⃣ Suivre un colis")
    elif incoming_msg.startswith("1") or "envoyer un colis" in incoming_msg:
        msg.body("📦 Veuillez envoyer les infos du colis au format suivant :\nNom de l’expéditeur - Nom du destinataire - Date d’envoi (JJ/MM/AAAA)")
    elif "-" in incoming_msg and len(incoming_msg.split("-")) == 3:
        expediteur, destinataire, date_str = [x.strip() for x in incoming_msg.split("-")]
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, nom, ville_depart, ville_arrivee, date_depart FROM transporteurs WHERE date_depart = %s", (date_str,))
        result = cursor.fetchall()
        conn.close()
        if result:
            reponse = f"🚚 Transporteurs disponibles le {date_str} :\n"
            for t in result:
                reponse += f"ID {t[0]} - {t[1]} ({t[2]} ➡️ {t[3]})\n"
            reponse += "\nRépondez avec :\nChoisir [ID du transporteur]"
            msg.body(reponse)
        else:
            msg.body("❌ Aucun transporteur disponible à cette date. Essayez une autre date.")
    elif incoming_msg.startswith("choisir"):
        try:
            transporteur_id = int(incoming_msg.split(" ")[1])
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO colis (expediteur, destinataire, date_envoi, transporteur_id) VALUES (%s, %s, %s, %s)",
                           (expediteur, destinataire, date_str, transporteur_id))
            conn.commit()
            cursor.execute("SELECT numero_whatsapp FROM transporteurs WHERE id = %s", (transporteur_id,))
            numero = cursor.fetchone()[0]
            conn.close()
            msg.body(f"✅ Colis enregistré avec le transporteur {transporteur_id}.\n📲 Vous pouvez le contacter au : {numero}")
        except:
            msg.body("❌ Erreur lors de l’enregistrement. Vérifiez le numéro de transporteur.")
    elif incoming_msg.startswith("2") or "devenir transporteur" in incoming_msg:
        msg.body("🚚 Pour devenir transporteur, merci d’envoyer vos infos au format :\nNom - Ville départ - Ville arrivée - Date (JJ/MM/AAAA) - Numéro WhatsApp - Paiement OK")
    elif incoming_msg.count("-") == 5:
        try:
            nom, vdep, varr, date_dep, numero, paiement = [x.strip() for x in incoming_msg.split("-")]
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO transporteurs (nom, ville_depart, ville_arrivee, date_depart, numero_whatsapp, paiement) VALUES (%s, %s, %s, %s, %s, %s)",
                           (nom, vdep, varr, date_dep, numero, paiement))
            conn.commit()
            conn.close()
            msg.body("✅ Inscription réussie ! Vous recevrez les notifications dès qu’un client choisit votre trajet.")
        except:
            msg.body("❌ Erreur d’inscription. Vérifiez le format envoyé.")
    elif incoming_msg.startswith("3") or "suivre un colis" in incoming_msg:
        msg.body("🔎 Envoyez le nom de l’expéditeur pour vérifier le statut de votre colis.")
    elif len(incoming_msg) > 2:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT c.id, t.nom, t.numero_whatsapp FROM colis c JOIN transporteurs t ON c.transporteur_id = t.id WHERE c.expediteur ILIKE %s ORDER BY c.id DESC LIMIT 1", (f"%{incoming_msg}%",))
        colis = cursor.fetchone()
        conn.close()
        if colis:
            msg.body(f"📦 Colis ID {colis[0]} en cours avec le transporteur {colis[1]}.\n📲 Contact : {colis[2]}")
        else:
            msg.body("❌ Aucun colis trouvé pour ce nom.")
    else:
        msg.body("🤖 Je n’ai pas compris. Répondez avec :\n1️⃣ Envoyer un colis\n2️⃣ Devenir transporteur\n3️⃣ Suivre un colis")

    return str(resp)

@app.route("/")
def index():
    return "Askely Express est en ligne."

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000, debug=True)
