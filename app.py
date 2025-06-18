from flask import Flask, request, render_template
from twilio.twiml.messaging_response import MessagingResponse
import psycopg2
import os

app = Flask(__name__)

# Connexion à PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")  # Assurez-vous que la variable est définie sur Render

def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")

@app.route("/")
def index():
    return "✅ Askely Express est en ligne."

@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get("Body", "").strip().lower()
    sender = request.values.get("From", "")
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg in ["bonjour", "salut", "hello"]:
        msg.body("👋 *Bienvenue chez Askely Express* 🇲🇦\n\n📦 Que souhaitez-vous faire ?\n\n👉 [Envoyer un colis](https://projetcomplet.onrender.com/envoyer)\n👉 [Devenir transporteur](https://projetcomplet.onrender.com/transporteur)\n👉 [Suivre un colis](https://projetcomplet.onrender.com/suivi)")
    else:
        msg.body("🤖 Je n’ai pas compris votre message.\n\nRépondez avec :\n👉 [Envoyer un colis](https://projetcomplet.onrender.com/envoyer)\n👉 [Devenir transporteur](https://projetcomplet.onrender.com/transporteur)\n👉 [Suivre un colis](https://projetcomplet.onrender.com/suivi)")

    return str(resp)

@app.route("/envoyer")
def envoyer_colis():
    return render_template("envoyer.html")

@app.route("/transporteur")
def devenir_transporteur():
    return render_template("transporteur.html")

@app.route("/suivi")
def suivi_colis():
    return render_template("suivi.html")

@app.route("/transporteurs")
def liste_transporteurs():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("SELECT nom, ville_depart, ville_arrivee, date_depart, numero_whatsapp FROM transporteurs ORDER BY date_depart DESC")
        data = cur.fetchall()
        conn.close()
        return render_template("liste_transporteurs.html", transporteurs=data)
    except Exception as e:
        return f"Erreur : {str(e)}"

@app.route("/colis")
def liste_colis():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT c.id, c.expediteur, c.destinataire, c.date_envoi, t.nom
            FROM colis c
            JOIN transporteurs t ON c.transporteur_id = t.id
            ORDER BY c.date_envoi DESC
        """)
        data = cur.fetchall()
        conn.close()
        return render_template("liste_colis.html", colis=data)
    except Exception as e:
        return f"Erreur : {str(e)}"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
