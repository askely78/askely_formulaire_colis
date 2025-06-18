from flask import Flask, request, render_template
from twilio.twiml.messaging_response import MessagingResponse
import psycopg2
import os
from datetime import datetime
import openai

app = Flask(__name__)

# Configuration OpenAI
openai.api_key = os.getenv("OPENAI_API_KEY")

# Connexion PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn_cursor():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    return conn, cursor

@app.route("/")
def index():
    return "✅ Askely Express est en ligne."

@app.route("/transporteurs")
def liste_transporteurs():
    conn, cursor = get_conn_cursor()
    cursor.execute("SELECT nom, ville_depart, ville_arrivee, date_depart FROM transporteurs ORDER BY date_depart")
    data = cursor.fetchall()
    conn.close()
    return render_template("liste_transporteurs.html", transporteurs=data)

@app.route("/colis")
def liste_colis():
    conn, cursor = get_conn_cursor()
    cursor.execute("""
        SELECT c.expediteur, c.destinataire, c.date_envoi, t.nom
        FROM colis c JOIN transporteurs t ON c.transporteur_id = t.id
        ORDER BY c.date_envoi DESC
    """)
    data = cursor.fetchall()
    conn.close()
    return render_template("liste_colis.html", colis=data)

@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip().lower()
    sender = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg in ["bonjour", "salut", "hello"]:
        msg.body("👋 Bonjour et bienvenue chez *Askely Express* 🇲🇦 !\n\nQue souhaitez-vous faire ?\n1️⃣ Envoyer un colis\n2️⃣ Devenir transporteur\n3️⃣ Suivre un colis\n🔗 Voir transporteurs : https://projetcomplet.onrender.com/transporteurs\n🔗 Voir colis : https://projetcomplet.onrender.com/colis")
    elif incoming_msg.startswith("1") or "envoyer un colis" in incoming_msg:
        msg.body("📦 Veuillez envoyer les infos du colis au format :\nExpéditeur - Destinataire - Date (JJ/MM/AAAA)")
    elif "-" in incoming_msg and len(incoming_msg.split("-")) == 3:
        expediteur, destinataire, date_str = [x.strip() for x in incoming_msg.split("-")]
        conn, cursor = get_conn_cursor()
        cursor.execute("SELECT id, nom, ville_depart, ville_arrivee, date_depart FROM transporteurs WHERE date_depart = %s", (date_str,))
        result = cursor.fetchall()
        conn.close()
        if result:
            reponse = f"🚚 Transporteurs disponibles le {date_str} :\n"
            for t in result:
                reponse += f"ID {t[0]} - {t[1]} ({t[2]} ➡️ {t[3]})\n"
            reponse += "\nRépondez avec :\nchoisir [ID du transporteur]"
            msg.body(reponse)
        else:
            msg.body("❌ Aucun transporteur disponible à cette date.")
    elif incoming_msg.startswith("choisir"):
        try:
            transporteur_id = int(incoming_msg.split(" ")[1])
            conn, cursor = get_conn_cursor()
            cursor.execute("INSERT INTO colis (expediteur, destinataire, date_envoi, transporteur_id) VALUES (%s, %s, %s, %s)",
                           (expediteur, destinataire, date_str, transporteur_id))
            cursor.execute("SELECT numero_whatsapp FROM transporteurs WHERE id = %s", (transporteur_id,))
            numero = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            msg.body(f"✅ Colis enregistré !\n📲 Contact du transporteur : {numero}")
        except:
            msg.body("❌ Erreur, transporteur introuvable ou mauvaise syntaxe.")
    elif incoming_msg.startswith("2") or "devenir transporteur" in incoming_msg:
        msg.body("🚚 Pour devenir transporteur, envoyez :\nNom - Ville départ - Ville arrivée - Date (JJ/MM/AAAA) - WhatsApp - Paiement OK")
    elif incoming_msg.count("-") == 5:
        try:
            nom, vdep, varr, date_dep, numero, paiement = [x.strip() for x in incoming_msg.split("-")]
            conn, cursor = get_conn_cursor()
            cursor.execute("INSERT INTO transporteurs (nom, ville_depart, ville_arrivee, date_depart, numero_whatsapp, paiement) VALUES (%s, %s, %s, %s, %s, %s)",
                           (nom, vdep, varr, date_dep, numero, paiement))
            conn.commit()
            conn.close()
            msg.body("✅ Vous êtes enregistré comme transporteur.\nVous recevrez des demandes via WhatsApp.")
        except:
            msg.body("❌ Format incorrect. Veuillez réessayer.")
    elif incoming_msg.startswith("3") or "suivre un colis" in incoming_msg:
        msg.body("🔎 Veuillez envoyer le nom de l'expéditeur.")
    elif len(incoming_msg.split()) >= 1:
        conn, cursor = get_conn_cursor()
        cursor.execute("""SELECT c.id, t.nom, t.numero_whatsapp
                          FROM colis c JOIN transporteurs t ON c.transporteur_id = t.id
                          WHERE c.expediteur ILIKE %s ORDER BY c.id DESC LIMIT 1""", (f"%{incoming_msg}%",))
        colis = cursor.fetchone()
        conn.close()
        if colis:
            msg.body(f"📦 Colis ID {colis[0]} en cours avec {colis[1]}.\n📲 Contact : {colis[2]}")
        else:
            msg.body("❌ Aucun colis trouvé.")
    else:
        # Fallback GPT
        try:
            completion = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "Tu es un assistant de transport de colis."},
                    {"role": "user", "content": incoming_msg}
                ]
            )
            msg.body(completion.choices[0].message['content'])
        except:
            msg.body("🤖 Je n’ai pas compris. Répondez par :\n1️⃣ Envoyer un colis\n2️⃣ Devenir transporteur\n3️⃣ Suivre un colis")

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
