from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

@app.route("/webhook/whatsapp", methods=["POST"])
def whatsapp_webhook():
    incoming_msg = request.values.get("Body", "").lower()
    resp = MessagingResponse()
    msg = resp.message()

    if "bonjour" in incoming_msg or "salut" in incoming_msg:
        msg.body("👋 Bienvenue chez *Askely Express* !\nRépondez par :\n1. Envoyer un colis\n2. Devenir transporteur\n3. Suivre un colis")
    else:
        msg.body("❓ Je n'ai pas compris votre demande. Répondez par :\n1. Envoyer un colis\n2. Devenir transporteur\n3. Suivre un colis")

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)