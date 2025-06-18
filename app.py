
from flask import Flask, request, render_template
from twilio.twiml.messaging_response import MessagingResponse
from twilio.rest import Client
import psycopg2
import os

app = Flask(__name__)

# Connexion PostgreSQL
DATABASE_URL = os.getenv('DATABASE_URL')
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

# Twilio
twilio_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
client = Client(twilio_sid, twilio_token)

@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip().lower()
    sender = request.values.get('From', '')
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg in ["bonjour", "salut", "hello", "menu"]:
        accueil = ("👋 Bonjour ! Bienvenue chez *Askely Express* 🇲🇦\n\n"
                   "📌 Cliquez sur une option :\n"
                   "🔗 Envoyer un colis : https://projetcomplet.onrender.com/formulaire_colis\n"
                   "🔗 Devenir transporteur : https://projetcomplet.onrender.com/formulaire_transporteur\n"
                   "🔗 Suivre un colis : https://projetcomplet.onrender.com/liste_colis\n"
                   "🔗 Voir les transporteurs : https://projetcomplet.onrender.com/liste_transporteurs")
        msg.body(accueil)
    else:
        msg.body("🤖 Je n’ai pas compris. Tapez *menu* pour voir les options.")

    return str(resp)

@app.route("/")
def index():
    return "Askely Express est en ligne."

@app.route("/formulaire_colis")
def formulaire_colis():
    return render_template("formulaire_colis.html")

@app.route("/formulaire_transporteur")
def formulaire_transporteur():
    return render_template("formulaire_transporteur.html")

@app.route("/liste_colis")
def liste_colis():
    cursor.execute("SELECT expediteur, destinataire, date_envoi FROM colis ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    return render_template("liste_colis.html", colis=rows)

@app.route("/liste_transporteurs")
def liste_transporteurs():
    cursor.execute("SELECT nom, ville_depart, ville_arrivee, date_depart FROM transporteurs ORDER BY id DESC LIMIT 10")
    rows = cursor.fetchall()
    return render_template("liste_transporteurs.html", transporteurs=rows)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
