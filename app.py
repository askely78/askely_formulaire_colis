from flask import Flask, request, render_template
from twilio.twiml.messaging_response import MessagingResponse
import psycopg2
import os
from datetime import datetime

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_conn():
    return psycopg2.connect(DATABASE_URL)

@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get("Body", "").strip().lower()
    sender = request.values.get("From", "")
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg in ["bonjour", "salut", "hello", "menu"]:
        msg.body(
            "👋 Bienvenue chez *Askely Express* 🇲🇦\n\n"
            "Que souhaitez-vous faire ? Cliquez ou tapez :\n\n"
            "📦 [Envoyer un colis](https://projetcomplet.onrender.com/formulaire_colis)\n"
            "🚚 [Devenir transporteur](https://projetcomplet.onrender.com/formulaire_transporteur)\n"
            "📋 [Voir les transporteurs](https://projetcomplet.onrender.com/liste_transporteurs)\n"
            "📦 [Voir les colis](https://projetcomplet.onrender.com/liste_colis)\n\n"
            "🟢 Vous pouvez taper `menu` à tout moment pour revenir ici."
        )
    else:
        msg.body("🤖 Tapez `menu` pour voir toutes les options disponibles.")

    return str(resp)

@app.route("/formulaire_colis")
def formulaire_colis():
    return render_template("formulaire_colis.html")

@app.route("/formulaire_transporteur")
def formulaire_transporteur():
    return render_template("formulaire_transporteur.html")

@app.route("/liste_colis")
def liste_colis():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT c.id, c.expediteur, c.destinataire, c.date_envoi, t.nom, t.ville_depart, t.ville_arrivee
        FROM colis c
        JOIN transporteurs t ON c.transporteur_id = t.id
        ORDER BY c.date_envoi DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("liste_colis.html", colis=rows)

@app.route("/liste_transporteurs")
def liste_transporteurs():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, nom, ville_depart, ville_arrivee, date_depart, numero_whatsapp FROM transporteurs ORDER BY date_depart ASC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return render_template("liste_transporteurs.html", transporteurs=rows)

@app.route("/")
def index():
    return "<h2>Askely Express est en ligne ✅</h2>"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
