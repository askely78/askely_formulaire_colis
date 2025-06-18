from flask import Flask, request, render_template
from twilio.twiml.messaging_response import MessagingResponse
import psycopg2
import os

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

def get_connection():
    return psycopg2.connect(DATABASE_URL)

@app.route("/")
def index():
    return "Askely Express est en ligne."

@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get('Body', '').strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg in ["bonjour", "salut", "hello"]:
        msg.body("👋 Bonjour ! Bienvenue chez *Askely Express* 🇲🇦

📦 Envoyer un colis : https://projetcomplet.onrender.com/envoyer
🚚 Devenir transporteur : https://projetcomplet.onrender.com/devenir
🔎 Suivre un colis : https://projetcomplet.onrender.com/suivre")
    else:
        msg.body("🤖 Merci pour votre message. Visitez : https://projetcomplet.onrender.com")

    return str(resp)
