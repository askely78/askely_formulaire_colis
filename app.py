from flask import Flask, request, render_template
from twilio.twiml.messaging_response import MessagingResponse
import psycopg2
import os

app = Flask(__name__)

# Connexion à PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/transporteurs")
def liste_transporteurs():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nom, ville_depart, ville_arrivee, date_depart, numero_whatsapp FROM transporteurs ORDER BY date_depart")
    rows = cursor.fetchall()
    conn.close()
    return render_template("liste_transporteurs.html", transporteurs=rows)

@app.route("/colis")
def liste_colis():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.expediteur, c.destinataire, c.date_envoi, t.nom, t.numero_whatsapp
        FROM colis c
        JOIN transporteurs t ON c.transporteur_id = t.id
        ORDER BY c.date_envoi DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return render_template("liste_colis.html", colis=rows)

@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get("Body", "").strip().lower()
    sender = request.values.get("From", "")
    resp = MessagingResponse()
    msg = resp.message()

    accueil = (
        "👋 Bienvenue chez *Askely Express* 🇲🇦\n\n"
        "👇 Choisissez une option :\n"
        "1️⃣ Envoyer un colis\n"
        "2️⃣ Devenir transporteur\n"
        "3️⃣ Suivre un colis\n\n"
        "📋 Voir les listes :\n"
        "🔗 [Transporteurs](https://projetcomplet.onrender.com/transporteurs)\n"
        "🔗 [Colis](https://projetcomplet.onrender.com/colis)"
    )

    if incoming_msg in ["bonjour", "salut", "hello", "menu", "accueil"]:
        msg.body(accueil)
    else:
        msg.body("🤖 Je n’ai pas compris. Tapez *menu* pour voir les options.")

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
