from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import psycopg2
import os
from urllib.parse import urlparse

app = Flask(__name__)

# Connexion à la base PostgreSQL depuis DATABASE_URL
def get_db_connection():
    result = urlparse(os.environ['DATABASE_URL'])
    username = result.username
    password = result.password
    database = result.path[1:]
    hostname = result.hostname
    port = result.port
    return psycopg2.connect(
        dbname=database,
        user=username,
        password=password,
        host=hostname,
        port=port
    )

# Initialisation des tables
def init_db():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transporteurs (
            id SERIAL PRIMARY KEY,
            nom TEXT,
            ville_depart TEXT,
            ville_arrivee TEXT,
            date_depart TEXT,
            numero_whatsapp TEXT,
            paiement TEXT
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS colis (
            id SERIAL PRIMARY KEY,
            expediteur TEXT,
            destinataire TEXT,
            date_envoi TEXT,
            transporteur_id INTEGER REFERENCES transporteurs(id)
        );
    """)
    conn.commit()
    conn.close()

# Webhook WhatsApp
@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp():
    incoming_msg = request.values.get('Body', '').strip().lower()
    sender = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg in ["bonjour", "salut", "hello"]:
        msg.body("👋 Bienvenue chez *Askely Express* 🇲🇦\n\nQue souhaitez-vous faire ? Répondez avec :\n1️⃣ Envoyer un colis\n2️⃣ Devenir transporteur\n3️⃣ Suivre un colis")
    elif incoming_msg.startswith("1") or "envoyer un colis" in incoming_msg:
        msg.body("📦 Veuillez envoyer les infos du colis au format :\nNom expéditeur - Nom destinataire - Date d’envoi (JJ/MM/AAAA)")
    elif "-" in incoming_msg and len(incoming_msg.split("-")) == 3:
        expediteur, destinataire, date_str = [x.strip() for x in incoming_msg.split("-")]
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, nom, ville_depart, ville_arrivee, numero_whatsapp FROM transporteurs WHERE date_depart = %s", (date_str,))
        result = cur.fetchall()
        conn.close()
        if result:
            reponse = f"🚚 Transporteurs disponibles le {date_str} :\n"
            for t in result:
                reponse += f"ID {t[0]} - {t[1]} ({t[2]} ➡️ {t[3]})\n"
            reponse += "\nRépondez avec :\nChoisir [ID du transporteur]"
            msg.body(reponse)
        else:
            msg.body("❌ Aucun transporteur disponible à cette date.")
    elif incoming_msg.startswith("choisir"):
        try:
            transporteur_id = int(incoming_msg.split(" ")[1])
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO colis (expediteur, destinataire, date_envoi, transporteur_id) VALUES (%s, %s, CURRENT_DATE, %s)", (expediteur, destinataire, transporteur_id))
            cur.execute("SELECT numero_whatsapp FROM transporteurs WHERE id = %s", (transporteur_id,))
            numero = cur.fetchone()[0]
            conn.commit()
            conn.close()
            msg.body(f"✅ Colis enregistré avec le transporteur {transporteur_id}.\n📲 Contactez-le : {numero}")
        except:
            msg.body("❌ Erreur. Assurez-vous d’avoir sélectionné un ID de transporteur valide.")
    elif incoming_msg.startswith("2") or "devenir transporteur" in incoming_msg:
        msg.body("🚚 Pour devenir transporteur, envoyez :\nNom - Ville départ - Ville arrivée - Date départ - Numéro WhatsApp - Paiement OK")
    elif incoming_msg.count("-") == 5:
        try:
            nom, vdep, varr, date_dep, numero, paiement = [x.strip() for x in incoming_msg.split("-")]
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute("INSERT INTO transporteurs (nom, ville_depart, ville_arrivee, date_depart, numero_whatsapp, paiement) VALUES (%s, %s, %s, %s, %s, %s)", (nom, vdep, varr, date_dep, numero, paiement))
            conn.commit()
            conn.close()
            msg.body("✅ Inscription réussie ! Vous recevrez les demandes clients sur WhatsApp.")
        except:
            msg.body("❌ Format invalide ou erreur d’enregistrement.")
    elif incoming_msg.startswith("3") or "suivre un colis" in incoming_msg:
        msg.body("🔎 Envoyez le nom de l’expéditeur pour connaître le statut.")
    elif len(incoming_msg) > 2:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, t.nom, t.numero_whatsapp FROM colis c
            JOIN transporteurs t ON c.transporteur_id = t.id
            WHERE LOWER(c.expediteur) LIKE %s
            ORDER BY c.id DESC LIMIT 1
        """, (f"%{incoming_msg}%",))
        colis = cur.fetchone()
        conn.close()
        if colis:
            msg.body(f"📦 Colis {colis[0]} pris en charge par {colis[1]}.\n📲 Contact : {colis[2]}")
        else:
            msg.body("❌ Aucun colis trouvé.")
    else:
        msg.body("❓ Je n’ai pas compris. Répondez avec :\n1️⃣ Envoyer un colis\n2️⃣ Devenir transporteur\n3️⃣ Suivre un colis")

    return str(resp)

@app.route("/")
def index():
    return "Askely Express en ligne avec PostgreSQL."

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10000, debug=True)