
from flask import Flask, request, render_template, redirect, url_for
import sqlite3
from twilio.rest import Client
import os

app = Flask(__name__)

# Configuration Twilio (à personnaliser)
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_PHONE_NUMBER = os.getenv('TWILIO_PHONE_NUMBER')

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Initialisation de la base de données
def init_db():
    conn = sqlite3.connect('colis.db')
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transporteurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT,
            telephone TEXT,
            ville_depart TEXT,
            ville_arrivee TEXT,
            date_depart TEXT
        )
    """)
    conn.commit()
    conn.close()

@app.route('/')
def accueil():
    return "Bienvenue sur Askely Express"

@app.route('/inscription-transporteur', methods=['GET', 'POST'])
def inscription_transporteur():
    if request.method == 'POST':
        nom = request.form['nom']
        telephone = request.form['telephone']
        ville_depart = request.form['ville_depart']
        ville_arrivee = request.form['ville_arrivee']
        date_depart = request.form['date_depart']

        conn = sqlite3.connect('colis.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO transporteurs (nom, telephone, ville_depart, ville_arrivee, date_depart) VALUES (?, ?, ?, ?, ?)",
                       (nom, telephone, ville_depart, ville_arrivee, date_depart))
        conn.commit()
        conn.close()

        # Message simulé de confirmation avec Twilio
        message = client.messages.create(
            body=f"Bonjour {nom}, merci pour votre inscription en tant que transporteur. Nous vous informerons dès qu’un client sélectionnera votre trajet.",
            from_=TWILIO_PHONE_NUMBER,
            to=telephone
        )
        return "Inscription réussie. Vous serez notifié pour les prochaines demandes."
    return render_template('inscription_transporteur.html')

@app.route('/webhook/whatsapp', methods=['POST'])
def whatsapp_webhook():
    incoming_msg = request.form.get('Body').lower()
    from_number = request.form.get('From')

    from twilio.twiml.messaging_response import MessagingResponse
    resp = MessagingResponse()
    msg = resp.message()

    if "transporteur" in incoming_msg:
        msg.body("📦 Pour devenir transporteur, veuillez remplir ce formulaire : https://askely-express.onrender.com/inscription-transporteur\n💰 L'inscription est payante. Merci de votre compréhension.")
    else:
        msg.body("❓ Je n'ai pas compris votre demande. Répondez par 'transporteur' pour vous inscrire.")

    return str(resp)

if __name__ == '__main__':
    init_db()
    app.run(host="0.0.0.0", port=10000, debug=True)
